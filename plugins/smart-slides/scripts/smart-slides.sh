#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
PLUGIN_ROOT=$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)
RUNTIME_ROOT="$PLUGIN_ROOT/runtime"

load_env_file() {
  local env_file=$1
  [[ -f "$env_file" ]] || return 0
  while IFS= read -r raw_line || [[ -n "$raw_line" ]]; do
    local line key value current
    line=$(printf '%s' "$raw_line" | sed 's/^[[:space:]]*//; s/[[:space:]]*$//')
    [[ -n "$line" && "$line" != \#* && "$line" == *=* ]] || continue
    line=${line#export }
    key=$(printf '%s' "${line%%=*}" | sed 's/[[:space:]]*$//')
    value=$(printf '%s' "${line#*=}" | sed 's/^[[:space:]]*//')
    [[ "$key" =~ ^[A-Za-z_][A-Za-z0-9_]*$ ]] || continue
    current=${!key-}
    [[ -z "$current" ]] || continue
    case "$value" in
      \"*\") value=${value#\"}; value=${value%\"} ;;
      \'*\') value=${value#\'}; value=${value%\'} ;;
    esac
    export "$key=$value"
  done < "$env_file"
}

: "${SMART_SLIDES_HOME:=$HOME/.codex/smart-slides}"
# Explicit process environment always wins. The persisted setup-page values
# belong to the selected runtime home, which also makes isolated runs work.
load_env_file "$PLUGIN_ROOT/.env"
load_env_file "$SMART_SLIDES_HOME/.env"

: "${JOGG_BASE_URL:=https://api.jogg.ai}"
: "${SMART_SLIDES_DATA_DIR:=$SMART_SLIDES_HOME/data}"
: "${SMART_SLIDES_STATE_DIR:=$SMART_SLIDES_HOME/runs}"
: "${SMART_SLIDES_SERVICE_FILE:=$SMART_SLIDES_HOME/service.json}"
: "${SMART_SLIDES_TOOL_DIR:=$SMART_SLIDES_HOME/bin}"
: "${SMART_SLIDES_JOGG_POLL_INTERVAL_SECONDS:=10}"
: "${SMART_SLIDES_JOGG_DOWNLOAD_MAX_SECONDS:=120}"
: "${SMART_SLIDES_RENDER_POLL_INTERVAL_SECONDS:=5}"
: "${SMART_SLIDES_MAX_JOGG_WAIT_SECONDS:=1800}"
: "${SMART_SLIDES_MAX_RENDER_WAIT_SECONDS:=7200}"
readonly SMART_SLIDES_JOGG_CONCURRENCY=5
readonly SMART_SLIDES_JOGG_POST_LIMIT_PER_MINUTE=20

ACTION=""
RUN_ID=""
STATE_PATH=""
LOCK_DIR=""
TOPIC=""
DURATION_SECONDS=180
AVATAR_MODE="opening_closing"
AVATAR_STYLE="professional"
AVATAR_GENDER="female"
AVATAR_AGE="adult"
PLANNING_FILE=""
RESUME_PLANNING_FILE=""
HTML_CLIP_ID=""
HTML_FILE=""
HTML_AT_SECONDS=""
VOICE_ID="${JOGG_DEFAULT_VOICE_ID:-}"
AVATAR_ID="${JOGG_DEFAULT_AVATAR_ID:-}"
JOGG_EFFECTIVE_API_KEY=""
SMART_SLIDES_BASE_URL="${SMART_SLIDES_BASE_URL:-}"
PROJECT_JSON='{}'
HTTP_STATUS=""
HTTP_BODY=""

# A plugin-managed tool directory may hold platform-matched FFmpeg binaries.
# Never download or replace binaries implicitly during a render command.
if [[ -x "$SMART_SLIDES_TOOL_DIR/ffmpeg" || -x "$SMART_SLIDES_TOOL_DIR/ffprobe" ]]; then
  export PATH="$SMART_SLIDES_TOOL_DIR:$PATH"
fi

log() { printf '[smart-slides] %s\n' "$*" >&2; }

usage() {
  cat <<'EOF'
usage:
  smart-slides.sh preflight
  smart-slides.sh doctor
  smart-slides.sh install-deps
  smart-slides.sh settings
  smart-slides.sh run --topic TEXT [--duration-seconds 180] [--avatar-mode MODE] [--planning-file PLAN.json]
  smart-slides.sh resume --run-id RUN_ID [--planning-file PLAN.json]
  smart-slides.sh status --run-id RUN_ID
  smart-slides.sh html-status --run-id RUN_ID
  smart-slides.sh apply-html --run-id RUN_ID --clip-id CLIP_ID --html-file ASSET.json
  smart-slides.sh capture-html --run-id RUN_ID --clip-id CLIP_ID --at-seconds SECONDS
  smart-slides.sh approve-html --run-id RUN_ID --clip-id CLIP_ID
  smart-slides.sh preview --run-id RUN_ID
  smart-slides.sh refresh-broll --run-id RUN_ID
  smart-slides.sh render --run-id RUN_ID
  smart-slides.sh import --file PROJECT.json [--avatar-mode MODE]

avatar modes: none, opening, opening_closing, all
EOF
}

require_bin() { command -v "$1" >/dev/null 2>&1 || die "missing required binary: $1"; }

dependency_report() {
  local name path chrome_path dependencies='[]' missing='[]'
  for name in curl jq ffmpeg ffprobe shasum node; do
    path=$(command -v "$name" 2>/dev/null || true)
    dependencies=$(jq -c --arg name "$name" --arg path "$path" '. + [{name:$name,installed:($path != ""),path:$path}]' <<< "$dependencies")
    [[ -n "$path" ]] || missing=$(jq -c --arg name "$name" '. + [$name]' <<< "$missing")
  done
  chrome_path="${SMART_SLIDES_CHROME_BIN:-}"
  [[ -n "$chrome_path" && -x "$chrome_path" ]] || chrome_path=$(command -v google-chrome 2>/dev/null || command -v chromium 2>/dev/null || true)
  [[ -n "$chrome_path" ]] || [[ ! -x "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" ]] || chrome_path="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
  dependencies=$(jq -c --arg path "$chrome_path" '. + [{name:"chrome",installed:($path != ""),path:$path}]' <<< "$dependencies")
  [[ -n "$chrome_path" ]] || missing=$(jq -c '. + ["chrome"]' <<< "$missing")
  jq -n --argjson dependencies "$dependencies" --argjson missing "$missing" '{status:(if ($missing|length)==0 then "ready" else "dependencies_missing" end),dependencies:$dependencies,missing:$missing}'
}

install_official_ffmpeg() {
  local version=8.1.2 archive build_root source_dir prefix jobs
  require_bin curl; require_bin tar; require_bin make; require_bin cc
  version="${SMART_SLIDES_FFMPEG_VERSION:-8.1.2}"
  build_root=$(mktemp -d "$SMART_SLIDES_HOME/ffmpeg-build.XXXXXX")
  archive="$build_root/ffmpeg-$version.tar.xz"
  prefix="$SMART_SLIDES_HOME/toolchain/ffmpeg-$version"
  log "building FFmpeg $version from official ffmpeg.org source"
  curl -fsSL "https://ffmpeg.org/releases/ffmpeg-$version.tar.xz" -o "$archive"
  tar -xf "$archive" -C "$build_root"
  source_dir="$build_root/ffmpeg-$version"
  [[ -d "$source_dir" ]] || die "official FFmpeg archive did not contain its source directory"
  jobs=$(sysctl -n hw.ncpu 2>/dev/null || printf 2)
  (
    cd "$source_dir"
    ./configure --prefix="$prefix" --disable-debug --disable-doc
    make -j "$jobs"
    make install
  )
  mkdir -p "$SMART_SLIDES_TOOL_DIR"
  ln -sf "$prefix/bin/ffmpeg" "$SMART_SLIDES_TOOL_DIR/ffmpeg"
  ln -sf "$prefix/bin/ffprobe" "$SMART_SLIDES_TOOL_DIR/ffprobe"
  rm -rf "$build_root"
  export PATH="$SMART_SLIDES_TOOL_DIR:$PATH"
}

install_dependencies() {
  [[ "$(uname -s)" == Darwin ]] || die "automatic FFmpeg installation is currently supported on macOS only"
  if ! command -v ffmpeg >/dev/null 2>&1 || ! command -v ffprobe >/dev/null 2>&1; then
    install_official_ffmpeg
  fi
  require_bin curl; require_bin jq; require_bin ffmpeg; require_bin ffprobe; require_bin shasum; require_bin node
}

ensure_local_renderer() {
  local python_bin
  python_bin=$(ensure_python_runtime)
  PYTHONPATH="$RUNTIME_ROOT" "$python_bin" -c 'from render.ffmpeg_adapter import ensure_renderer_available; ensure_renderer_available(require_browser=True)' \
    || die "local FFmpeg/Chrome renderer is not ready"
}

set_stage() {
  local stage=$1
  [[ -f "$STATE_PATH" ]] || return 0
  state_mutate '.stage=$stage | .updated_at=$updated_at' --arg stage "$stage" --arg updated_at "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
}

emit_failure() {
  local message=$1
  [[ -z "$STATE_PATH" || ! -f "$STATE_PATH" ]] || {
    state_mutate '.stage="failed" | .error=$error | .updated_at=$updated_at' --arg error "$message" --arg updated_at "$(date -u +%Y-%m-%dT%H:%M:%SZ)" 2>/dev/null || true
  }
  jq -cn --arg run_id "$RUN_ID" --arg error "$message" '{run_id:$run_id,status:"failed",error:$error}'
}

die() { local message=$1; log "ERROR: $message"; emit_failure "$message"; exit 1; }

release_run_lock() {
  [[ -n "$LOCK_DIR" && -d "$LOCK_DIR" ]] || return 0
  rm -f "$LOCK_DIR/pid"
  rmdir "$LOCK_DIR" 2>/dev/null || true
}

acquire_run_lock() {
  LOCK_DIR="$STATE_PATH.lock"
  if ! mkdir "$LOCK_DIR" 2>/dev/null; then
    local owner=''
    [[ -f "$LOCK_DIR/pid" ]] && owner=$(<"$LOCK_DIR/pid")
    if [[ "$owner" =~ ^[0-9]+$ ]] && ! kill -0 "$owner" 2>/dev/null; then
      rm -f "$LOCK_DIR/pid"
      rmdir "$LOCK_DIR" 2>/dev/null || true
      mkdir "$LOCK_DIR" 2>/dev/null || owner=busy
    else
      owner=busy
    fi
    if [[ "$owner" == busy ]]; then
      log "run is already active: $RUN_ID"
      jq -cn --arg run_id "$RUN_ID" '{run_id:$run_id,status:"busy",error:"run is already active"}'
      exit 2
    fi
  fi
  printf '%s\n' "$$" > "$LOCK_DIR/pid"
  trap release_run_lock EXIT
  trap 'exit 130' INT
  trap 'exit 143' TERM
}

state_mutate() {
  local filter=$1
  shift
  local tmp_path
  tmp_path=$(mktemp "$SMART_SLIDES_STATE_DIR/.state.XXXXXX")
  jq "$@" "$filter" "$STATE_PATH" > "$tmp_path"
  mv "$tmp_path" "$STATE_PATH"
}

state_get() { jq -r "$1 // empty" "$STATE_PATH"; }

emit_state() {
  jq '{run_id,stage,topic,target_duration_seconds,actual_duration_seconds,project_id,avatar_mode,avatar_shot_ids,html_clip_checkpoints,pending_clip_ids,jogg_tasks:(.jogg_tasks|with_entries(.value|={video_id,status,audio_path,avatar_path})),broll_shot_ids,composition_preview_url,editor_url,work_id,final_video_url,error,updated_at}' "$STATE_PATH"
}

request() {
  local method=$1 url=$2 body=${3:-}
  shift 3 || true
  local body_file
  body_file=$(mktemp)
  local -a args=(-sS -o "$body_file" -w '%{http_code}' --connect-timeout 10 --max-time 180 -X "$method" "$url")
  while (($#)); do args+=(-H "$1"); shift; done
  [[ -z "$body" ]] || args+=(-H 'Content-Type: application/json' --data "$body")
  if ! HTTP_STATUS=$(curl "${args[@]}"); then rm -f "$body_file"; die "local request failed"; fi
  HTTP_BODY=$(<"$body_file")
  rm -f "$body_file"
}

local_api_request() {
  request "$1" "${SMART_SLIDES_BASE_URL%/}/api/v1/video-studio$2" "${3:-}"
  [[ "$HTTP_STATUS" =~ ^2[0-9][0-9]$ ]] || die "smart-slides local API returned HTTP $HTTP_STATUS"
}

jogg_request() {
  request "$1" "${JOGG_BASE_URL%/}$2" "${3:-}" "X-Api-Key: $JOGG_EFFECTIVE_API_KEY"
  [[ "$HTTP_STATUS" =~ ^2[0-9][0-9]$ ]] || die "Jogg returned HTTP $HTTP_STATUS"
  [[ "$(jq -r '.code // 0' <<< "$HTTP_BODY")" == 0 ]] || die "Jogg rejected the OpenAPI request"
}

jogg_submit_request() {
  local body=$1 body_file
  body_file=$(mktemp)
  if ! HTTP_STATUS=$(curl -sS -o "$body_file" -w '%{http_code}' --connect-timeout 10 --max-time 180 \
    -X POST "${JOGG_BASE_URL%/}/v2/create_video_from_avatar" \
    -H "X-Api-Key: $JOGG_EFFECTIVE_API_KEY" -H 'Content-Type: application/json' --data "$body"); then
    HTTP_STATUS=000
    HTTP_BODY=''
    rm -f "$body_file"
    return 1
  fi
  HTTP_BODY=$(<"$body_file")
  rm -f "$body_file"
  [[ "$HTTP_STATUS" =~ ^2[0-9][0-9]$ ]] || return 1
  [[ "$(jq -r '.code // 0' <<< "$HTTP_BODY")" == 0 ]] || return 1
}

http_status() { curl -sS -o /dev/null -w '%{http_code}' --connect-timeout 2 --max-time 4 "$1" 2>/dev/null || true; }
local_service_ready() { [[ "$(http_status "${SMART_SLIDES_BASE_URL%/}/health")" =~ ^2[0-9][0-9]$ ]]; }

find_free_port() {
  python3 - <<'PY'
import socket
with socket.socket() as sock:
    sock.bind(("127.0.0.1", 0))
    print(sock.getsockname()[1])
PY
}

ensure_python_runtime() {
  if [[ -n "${SMART_SLIDES_PYTHON:-}" ]]; then printf '%s' "$SMART_SLIDES_PYTHON"; return; fi
  local venv="$SMART_SLIDES_HOME/venv"
  if [[ ! -x "$venv/bin/python" ]]; then
    log "creating local Python runtime"
    python3 -m venv "$venv"
  fi
  if ! PYTHONPATH="$RUNTIME_ROOT" "$venv/bin/python" -c 'import fastapi,httpx,multipart,uvicorn' >/dev/null 2>&1; then
    [[ "${SMART_SLIDES_SKIP_DEPENDENCY_INSTALL:-}" != 1 ]] || die "smart-slides Python dependencies are missing"
    log "installing local FastAPI dependencies"
    "$venv/bin/python" -m pip install --disable-pip-version-check -q -r "$RUNTIME_ROOT/backend/requirements.txt"
  fi
  printf '%s' "$venv/bin/python"
}

load_saved_service() {
  [[ -n "$SMART_SLIDES_BASE_URL" ]] && return 0
  if [[ -f "$SMART_SLIDES_SERVICE_FILE" ]]; then
    SMART_SLIDES_BASE_URL=$(jq -r '.base_url // empty' "$SMART_SLIDES_SERVICE_FILE")
    local_service_ready || SMART_SLIDES_BASE_URL=""
  fi
}

start_local_service() {
  load_saved_service
  [[ -z "$SMART_SLIDES_BASE_URL" ]] || { local_service_ready && return 0; }
  local port python_bin
  port=$(find_free_port)
  SMART_SLIDES_BASE_URL="http://127.0.0.1:$port"
  python_bin=$(ensure_python_runtime)
  mkdir -p "$SMART_SLIDES_HOME/logs" "$SMART_SLIDES_DATA_DIR"
  log "starting bundled Video Studio at $SMART_SLIDES_BASE_URL"
  nohup env PYTHONPATH="$RUNTIME_ROOT" SMART_SLIDES_HOME="$SMART_SLIDES_HOME" SMART_SLIDES_DATA_DIR="$SMART_SLIDES_DATA_DIR" \
    "$python_bin" -m uvicorn backend.main:app --host 127.0.0.1 --port "$port" \
    > "$SMART_SLIDES_HOME/logs/service.log" 2>&1 < /dev/null &
  local pid=$! attempt
  for attempt in $(seq 1 60); do local_service_ready && break; sleep 0.5; done
  local_service_ready || die "bundled Video Studio did not start; see $SMART_SLIDES_HOME/logs/service.log"
  jq -n --arg base_url "$SMART_SLIDES_BASE_URL" --argjson pid "$pid" '{base_url:$base_url,pid:$pid}' > "$SMART_SLIDES_SERVICE_FILE"
}

settings_url() { printf '%s/settings' "${SMART_SLIDES_BASE_URL%/}"; }

open_settings_page() {
  local url
  url=$(settings_url)
  if [[ "${SMART_SLIDES_NO_BROWSER:-}" != 1 ]] && command -v open >/dev/null 2>&1; then
    open "$url" >/dev/null 2>&1 || true
  fi
  printf '%s' "$url"
}

openapi_response_ok() {
  [[ "$HTTP_STATUS" =~ ^2[0-9][0-9]$ ]] && [[ "$(jq -r '(.code // 0) == 0' <<< "$HTTP_BODY")" == true ]]
}

validate_jogg_api_key() {
  local candidate=$1
  [[ -n "$candidate" ]] || return 1
  request GET "${JOGG_BASE_URL%/}/v2/voices?language=chinese&gender=female&page=1&page_size=1" '' "X-Api-Key: $candidate"
  if openapi_response_ok; then
    JOGG_EFFECTIVE_API_KEY=$candidate
    return 0
  fi
  JOGG_EFFECTIVE_API_KEY=''
  return 1
}

resolve_jogg_api_key() {
  [[ -n "$JOGG_EFFECTIVE_API_KEY" ]] && return
  if [[ -z "${JOGG_API_KEY:-}" ]]; then
    if [[ -n "${JOGG_WEB_TOKEN:-}" ]]; then
      die "JOGG_WEB_TOKEN cannot authenticate the public Jogg API. Set JOGG_API_KEY from the Jogg OpenAPI dashboard."
    fi
    die "JOGG_API_KEY is required for ${JOGG_BASE_URL%/}. Create an OpenAPI key in Jogg, then add it to ~/.codex/smart-slides/.env."
  fi
  validate_jogg_api_key "$JOGG_API_KEY" || die "Jogg rejected JOGG_API_KEY at ${JOGG_BASE_URL%/}. Check the key and its API entitlement."
}

resolve_profile() {
  local saved_voice saved_avatar query candidate
  saved_voice=$(state_get '.avatar_profile.voice_id')
  saved_avatar=$(state_get '.avatar_profile.avatar_id')
  [[ -n "$saved_voice" ]] && VOICE_ID=$saved_voice
  [[ -n "$saved_avatar" ]] && AVATAR_ID=$saved_avatar
  if [[ -z "$VOICE_ID" ]]; then
    jogg_request GET '/v2/voices?language=chinese&gender=female&page=1&page_size=20'
    VOICE_ID=$(jq -r '(.data.voices // .voices // []) | map(.voice_id // .id // empty) | map(select(length>0)) | .[0] // empty' <<< "$HTTP_BODY")
  fi
  [[ -n "$VOICE_ID" ]] || die "Jogg has no available Chinese female voice"
  if [[ -z "$AVATAR_ID" ]]; then
    local -a queries=(
      "aspect_ratio=landscape&style=$AVATAR_STYLE&gender=$AVATAR_GENDER&age=$AVATAR_AGE"
      "aspect_ratio=landscape&style=$AVATAR_STYLE&gender=$AVATAR_GENDER"
      "aspect_ratio=landscape&gender=$AVATAR_GENDER"
      "aspect_ratio=landscape"
    )
    for query in "${queries[@]}"; do
      jogg_request GET "/v2/avatars/public?$query&page=1&page_size=20"
      candidate=$(jq -r '(.data.avatars // .avatars // []) | map(.id // .avatar_id // empty) | map(select(tostring|length>0)) | .[0] // empty' <<< "$HTTP_BODY")
      [[ -z "$candidate" ]] || { AVATAR_ID=$candidate; break; }
    done
  fi
  [[ -n "$AVATAR_ID" ]] || die "Jogg has no public landscape avatar"
  state_mutate '.avatar_profile.voice_id=$voice | .avatar_profile.avatar_id=$avatar' --arg voice "$VOICE_ID" --arg avatar "$AVATAR_ID"
}

init_run() {
  RUN_ID="ss-$(date -u +%Y%m%d%H%M%S)-$RANDOM"
  mkdir -p "$SMART_SLIDES_STATE_DIR"
  STATE_PATH="$SMART_SLIDES_STATE_DIR/$RUN_ID.json"
  jq -n --arg run_id "$RUN_ID" --arg topic "$TOPIC" --argjson duration "$DURATION_SECONDS" --arg mode "$AVATAR_MODE" --arg planning_file "$PLANNING_FILE" \
    --arg style "$AVATAR_STYLE" --arg gender "$AVATAR_GENDER" --arg age "$AVATAR_AGE" --arg now "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
    '{version:"smart_slides_run_v1",run_id:$run_id,topic:$topic,target_duration_seconds:$duration,actual_duration_seconds:0,avatar_mode:$mode,planning_file:$planning_file,planning_applied:false,html_planning_fingerprint:"",html_clip_checkpoints:{},pending_clip_ids:[],avatar_profile:{style:$style,gender:$gender,age:$age,voice_id:"",avatar_id:""},stage:"initialized",project_id:"",avatar_shot_ids:[],jogg_tasks:{},broll_shot_ids:[],composition_preview_url:"",preview_project_fingerprint:"",editor_url:"",work_id:"",render_project_fingerprint:"",final_video_url:"",error:"",created_at:$now,updated_at:$now}' > "$STATE_PATH"
}

load_run() {
  RUN_ID=$1
  STATE_PATH="$SMART_SLIDES_STATE_DIR/$RUN_ID.json"
  [[ -f "$STATE_PATH" ]] || die "run state not found: $RUN_ID"
  TOPIC=$(state_get '.topic'); DURATION_SECONDS=$(state_get '.target_duration_seconds'); AVATAR_MODE=$(state_get '.avatar_mode')
  AVATAR_STYLE=$(state_get '.avatar_profile.style'); AVATAR_GENDER=$(state_get '.avatar_profile.gender'); AVATAR_AGE=$(state_get '.avatar_profile.age')
  PLANNING_FILE=$(state_get '.planning_file')
}

planning_input_available() {
  [[ -n "$PLANNING_FILE" || "$(state_get '.planning_applied')" == true || "${SMART_SLIDES_ALLOW_DETERMINISTIC_FALLBACK:-}" == 1 ]]
}

set_blocked_planning() {
  state_mutate '.stage="blocked_planning" | .error="A Codex-authored planning JSON is required before project creation or paid Jogg requests. Resume with --planning-file PLAN.json." | .updated_at=$updated_at' \
    --arg updated_at "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
}

planning_html_clips() {
  jq -c '
    def top_level_clips:
      [(.design_plan.mg_clips[]?, .mg_layer.mg_clips[]?, .render_manifest.mg_clips[]?)
       | select(type == "object")
       | . as $clip
       | (($clip.id // "") | tostring) as $id
       | ($clip.render_strategy // $clip.html_render_strategy // "llm_bespoke_html") as $strategy
       | select($id != "" and ($clip.enabled // true) != false and $strategy == "llm_bespoke_html")
       | {id:$id,bound_shot_ids:[$clip.bound_shots[]? | tostring]}];
    def shot_clips:
      [.scene_groups[]?.shots[]?
       | select(type == "object")
       | . as $shot
       | (($shot.id // "") | tostring) as $shot_id
       | ($shot.mg_director // {}) as $director
       | ($shot.information_layer // {}) as $info
       | ($shot.html_design // {}) as $html
       | ($shot.html_render_strategy // $html.render_strategy // $director.render_strategy // "") as $strategy
       | select($shot_id != "")
       | select(($shot.scene_role // "") == "broll_backdrop_overlay")
       | select(($info.enabled // false) == true and ($director.enabled // false) == true)
       | select($strategy == "llm_bespoke_html")
       | {id:(($html.clip_id // $shot.mg_clip_id // $director.clip_id // ("mg:" + $shot_id)) | tostring),bound_shot_ids:[$shot_id]}];
    (top_level_clips + shot_clips)
    | map(select(.bound_shot_ids | length > 0))
    | sort_by(.id)
    | group_by(.id)
    | map({id:.[0].id,bound_shot_ids:([.[] | .bound_shot_ids[]] | unique)})
  ' "$PLANNING_FILE"
}

refresh_pending_clip_ids() {
  state_mutate '
    .pending_clip_ids=([.html_clip_checkpoints | to_entries[]? | select(.value.status != "approved") | .key] | sort)
    | .updated_at=$updated_at
  ' --arg updated_at "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
}

initialize_html_checkpoints() {
  [[ -n "$PLANNING_FILE" && -f "$PLANNING_FILE" ]] || return 0
  local fingerprint current clips checkpoints
  fingerprint=$(shasum -a 256 "$PLANNING_FILE" | awk '{print $1}')
  current=$(state_get '.html_planning_fingerprint')
  if [[ "$fingerprint" == "$current" && "$(jq -r 'has("html_clip_checkpoints")' "$STATE_PATH")" == true ]]; then
    refresh_pending_clip_ids
    return 0
  fi
  clips=$(planning_html_clips)
  checkpoints=$(jq -cn --argjson clips "$clips" '
    reduce $clips[] as $clip ({};
      .[$clip.id]={status:"pending",asset_path:"",keyframes:[],attempt:0,error:"",bound_shot_ids:$clip.bound_shot_ids})
  ')
  state_mutate '
    .html_planning_fingerprint=$fingerprint
    | .html_clip_checkpoints=$checkpoints
    | .pending_clip_ids=([$checkpoints | to_entries[]? | .key] | sort)
    | .updated_at=$updated_at
  ' --arg fingerprint "$fingerprint" --argjson checkpoints "$checkpoints" --arg updated_at "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
}

ensure_html_ready() {
  initialize_html_checkpoints
  refresh_pending_clip_ids
  if [[ "$(jq '.pending_clip_ids | length' "$STATE_PATH")" != 0 ]]; then
    state_mutate '.stage="waiting_html" | .error="" | .updated_at=$updated_at' \
      --arg updated_at "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    return 11
  fi
}

html_checkpoint_exists() {
  jq -e --arg id "$1" '.html_clip_checkpoints[$id] != null' "$STATE_PATH" >/dev/null
}

html_checkpoint_dir() {
  printf '%s/html/%s' "$SMART_SLIDES_HOME" "$RUN_ID"
}

html_checkpoint_stem() {
  sha256_text "$1"
}

set_html_checkpoint_error() {
  local clip_id=$1 message=$2
  state_mutate '
    .html_clip_checkpoints[$id].status="qa_failed"
    | .html_clip_checkpoints[$id].error=$error
    | .stage="waiting_html"
    | .error=""
    | .updated_at=$updated_at
  ' --arg id "$clip_id" --arg error "$message" --arg updated_at "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  refresh_pending_clip_ids
}

apply_html_asset() {
  local clip_id=$1 input_file=$2 checkpoint_dir stem asset_path page_path python_bin validation_error
  initialize_html_checkpoints
  html_checkpoint_exists "$clip_id" || die "unknown HTML clip id: $clip_id"
  state_mutate '.html_clip_checkpoints[$id].attempt=((.html_clip_checkpoints[$id].attempt // 0) + 1)' --arg id "$clip_id"
  [[ -f "$input_file" ]] || { set_html_checkpoint_error "$clip_id" "HTML asset file not found: $input_file"; emit_state; return 0; }
  checkpoint_dir=$(html_checkpoint_dir); mkdir -p "$checkpoint_dir"
  stem=$(html_checkpoint_stem "$clip_id")
  asset_path="$checkpoint_dir/$stem.json"
  page_path="$checkpoint_dir/$stem.html"
  python_bin=$(ensure_python_runtime)
  if ! validation_error=$(PYTHONPATH="$RUNTIME_ROOT" "$python_bin" - "$PLANNING_FILE" "$clip_id" "$input_file" "$asset_path" "$page_path" "$(jq -c --arg id "$clip_id" '.html_clip_checkpoints[$id].bound_shot_ids' "$STATE_PATH")" <<'PY' 2>&1
import json
import sys
from copy import deepcopy
from pathlib import Path

from backend.services import video_studio_bespoke_html
from backend.services import video_studio_visual_styles

plan_path, clip_id, input_path, output_path, page_path, bound_json = sys.argv[1:]
plan = json.loads(Path(plan_path).read_text(encoding="utf-8"))
raw = Path(input_path).read_text(encoding="utf-8")
bound_ids = [str(item) for item in json.loads(bound_json)]
try:
    parsed = json.loads(raw)
except json.JSONDecodeError:
    parsed = {"custom_html": raw, "custom_css": "", "edit_schema": {}}
if not isinstance(parsed, dict):
    raise SystemExit("HTML asset must be a JSON object or an HTML fragment")
if isinstance(parsed.get("html_design_by_shot"), dict):
    supplied_by_shot = parsed["html_design_by_shot"]
else:
    supplied = parsed.get("html_design") if isinstance(parsed.get("html_design"), dict) else parsed
    supplied_by_shot = {shot_id: supplied for shot_id in bound_ids}

shots_by_id = {
    str(shot.get("id") or ""): shot
    for group in plan.get("scene_groups") or [] if isinstance(group, dict)
    for shot in group.get("shots") or [] if isinstance(shot, dict)
}
missing = [shot_id for shot_id in bound_ids if shot_id not in shots_by_id]
if missing:
    raise SystemExit("planned shot not found for clip: " + ", ".join(missing))

candidate_shots = []
for shot_id in bound_ids:
    supplied = supplied_by_shot.get(shot_id)
    if not isinstance(supplied, dict):
        raise SystemExit(f"HTML asset is missing design for {shot_id}")
    shot = deepcopy(shots_by_id[shot_id])
    existing = shot.get("html_design") if isinstance(shot.get("html_design"), dict) else {}
    shot["html_render_strategy"] = "llm_bespoke_html"
    shot["html_design"] = {**existing, **supplied, "clip_id": clip_id, "render_strategy": "llm_bespoke_html"}
    candidate_shots.append(shot)

try:
    project_style_profile = video_studio_visual_styles.resolve_visual_style_profile_from_project(plan)
    prepared = video_studio_bespoke_html.prepare_bespoke_html_scene_groups(
        str(plan.get("topic") or ""),
        [{"id": "html-checkpoint", "shots": candidate_shots}],
        project_style_profile,
    )
except Exception as exc:
    raise SystemExit(str(exc)) from exc

designs = {str(shot["id"]): shot["html_design"] for shot in prepared[0]["shots"]}
validations = {
    shot_id: design.get("ai_html_generation", {}).get("validation", {})
    for shot_id, design in designs.items()
}
first_design = designs[bound_ids[0]]
document = """<!doctype html><html><head><meta charset=\"utf-8\"><style>
html,body{margin:0;width:1920px;height:1080px;overflow:hidden;background:transparent}
body{position:relative}
%s
</style></head><body>%s</body></html>""" % (
    first_design.get("custom_css", ""), first_design.get("custom_html", "")
)
Path(page_path).write_text(document, encoding="utf-8")
Path(output_path).write_text(json.dumps({
    "version": "smart_slides_html_checkpoint_v1",
    "clip_id": clip_id,
    "bound_shot_ids": bound_ids,
    "html_design_by_shot": designs,
    "validation_by_shot": validations,
    "preview_page_path": page_path,
}, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
PY
  ); then
    rm -f "$asset_path" "$page_path"
    validation_error=$(printf '%s' "$validation_error" | tail -n 1)
    set_html_checkpoint_error "$clip_id" "${validation_error:-HTML contract validation failed}"
    emit_state
    return 0
  fi
  state_mutate '
    .html_clip_checkpoints[$id].status="generated"
    | .html_clip_checkpoints[$id].asset_path=$asset_path
    | .html_clip_checkpoints[$id].keyframes=[]
    | .html_clip_checkpoints[$id].error=""
    | .stage="waiting_html"
    | .error=""
    | .updated_at=$updated_at
  ' --arg id "$clip_id" --arg asset_path "$asset_path" --arg updated_at "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  refresh_pending_clip_ids
  emit_state
}

capture_html_asset() {
  local clip_id=$1 at_seconds=$2 asset_path page_path output_path checkpoint_dir stem python_bin capture_error
  initialize_html_checkpoints
  html_checkpoint_exists "$clip_id" || die "unknown HTML clip id: $clip_id"
  [[ "$at_seconds" =~ ^[0-9]+([.][0-9]+)?$ ]] || die '--at-seconds must be a non-negative number'
  asset_path=$(state_get ".html_clip_checkpoints[\"$clip_id\"].asset_path")
  [[ -n "$asset_path" && -f "$asset_path" ]] || { set_html_checkpoint_error "$clip_id" "Apply a valid HTML asset before capture"; emit_state; return 0; }
  page_path=$(jq -r '.preview_page_path // empty' "$asset_path")
  [[ -n "$page_path" && -f "$page_path" ]] || { set_html_checkpoint_error "$clip_id" "HTML preview page is missing; apply the asset again"; emit_state; return 0; }
  checkpoint_dir=$(html_checkpoint_dir); stem=$(html_checkpoint_stem "$clip_id")
  output_path="$checkpoint_dir/$stem-keyframe-$(printf '%.3f' "$at_seconds" | tr '.' '_').png"
  python_bin=$(ensure_python_runtime)
  if ! capture_error=$(PYTHONPATH="$RUNTIME_ROOT" "$python_bin" - "$page_path" "$at_seconds" "$output_path" <<'PY' 2>&1
import sys
from render import ffmpeg_adapter

if not hasattr(ffmpeg_adapter, "capture_html_keyframe"):
    raise SystemExit("local renderer does not expose capture_html_keyframe; update the bundled renderer")
ffmpeg_adapter.capture_html_keyframe(sys.argv[1], float(sys.argv[2]), sys.argv[3])
PY
  ); then
    rm -f "$output_path"
    capture_error=$(printf '%s' "$capture_error" | tail -n 1)
    set_html_checkpoint_error "$clip_id" "${capture_error:-HTML keyframe capture failed}"
    emit_state
    return 0
  fi
  [[ -s "$output_path" ]] || { set_html_checkpoint_error "$clip_id" "HTML keyframe capture produced an empty image"; emit_state; return 0; }
  state_mutate '
    .html_clip_checkpoints[$id].status="generated"
    | .html_clip_checkpoints[$id].keyframes=(([
        .html_clip_checkpoints[$id].keyframes[]? | select((.at_seconds | tonumber) != $at)
      ] + [{at_seconds:$at,path:$path}]) | sort_by(.at_seconds))
    | .html_clip_checkpoints[$id].error=""
    | .stage="waiting_html"
    | .updated_at=$updated_at
  ' --arg id "$clip_id" --argjson at "$at_seconds" --arg path "$output_path" --arg updated_at "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  refresh_pending_clip_ids
  emit_state
}

approve_html_asset() {
  local clip_id=$1 asset_path keyframe_path
  initialize_html_checkpoints
  html_checkpoint_exists "$clip_id" || die "unknown HTML clip id: $clip_id"
  asset_path=$(state_get ".html_clip_checkpoints[\"$clip_id\"].asset_path")
  if [[ -z "$asset_path" || ! -f "$asset_path" ]] || ! jq -e '
    (.validation_by_shot | type == "object" and length > 0)
    and all(.validation_by_shot[]; ((.errors // []) | length) == 0)
  ' "$asset_path" >/dev/null; then
    set_html_checkpoint_error "$clip_id" "HTML asset has not passed the extracted Podcastor validation contract"
    emit_state
    return 0
  fi
  if [[ "$(jq --arg id "$clip_id" '.html_clip_checkpoints[$id].keyframes | length' "$STATE_PATH")" == 0 ]]; then
    set_html_checkpoint_error "$clip_id" "Capture and inspect at least one keyframe before approval"
    emit_state
    return 0
  fi
  while IFS= read -r keyframe_path; do
    if [[ -z "$keyframe_path" || ! -s "$keyframe_path" ]]; then
      set_html_checkpoint_error "$clip_id" "A captured HTML keyframe is missing or empty"
      emit_state
      return 0
    fi
  done < <(jq -r --arg id "$clip_id" '.html_clip_checkpoints[$id].keyframes[]?.path' "$STATE_PATH")
  state_mutate '
    .html_clip_checkpoints[$id].status="approved"
    | .html_clip_checkpoints[$id].error=""
    | .updated_at=$updated_at
  ' --arg id "$clip_id" --arg updated_at "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  refresh_pending_clip_ids
  if [[ "$(jq '.pending_clip_ids | length' "$STATE_PATH")" == 0 ]]; then
    set_stage html_ready
  else
    set_stage waiting_html
  fi
  emit_state
}

build_effective_planning_file() {
  local effective next asset_path
  effective=$(mktemp "$SMART_SLIDES_STATE_DIR/.planning.XXXXXX")
  cp "$PLANNING_FILE" "$effective"
  while IFS= read -r asset_path; do
    [[ -n "$asset_path" && -f "$asset_path" ]] || { rm -f "$effective"; die "approved HTML checkpoint asset is missing"; }
    next=$(mktemp "$SMART_SLIDES_STATE_DIR/.planning.XXXXXX")
    jq --slurpfile asset "$asset_path" '
      ($asset[0].html_design_by_shot // {}) as $designs
      | .scene_groups = [(.scene_groups // [])[]
          | .shots = [(.shots // [])[]
              | . as $shot
              | (($shot.id // "") | tostring) as $shot_id
              | if $designs[$shot_id] then
                  .html_render_strategy="llm_bespoke_html"
                  | .html_design=((.html_design // {}) + $designs[$shot_id])
                else . end]]
    ' "$effective" > "$next"
    mv "$next" "$effective"
  done < <(jq -r '.html_clip_checkpoints[]? | select(.status == "approved") | .asset_path' "$STATE_PATH")
  printf '%s' "$effective"
}

fetch_project() {
  local project_id
  project_id=$(state_get '.project_id')
  [[ -n "$project_id" ]] || die "run has no local project id"
  local_api_request GET "/projects/$project_id"
  PROJECT_JSON=$(jq -ce '.project' <<< "$HTTP_BODY") || die "local API returned an invalid project"
}

ensure_project() {
  [[ -n "$(state_get '.project_id')" ]] && return
  local body project_id
  body=$(jq -cn --arg topic "$TOPIC" --argjson duration "$DURATION_SECONDS" '{topic:$topic,format:"long",production_format:"broll_html",target_duration_seconds:$duration}')
  local_api_request POST '/projects' "$body"
  project_id=$(jq -r '.project.id // empty' <<< "$HTTP_BODY")
  [[ -n "$project_id" ]] || die "local API did not create a project"
  state_mutate '.project_id=$id | .editor_url=($base+"/?project_id="+$id)' --arg id "$project_id" --arg base "$SMART_SLIDES_BASE_URL"
  set_stage project_created
}

ensure_planning() {
  if ! planning_input_available; then
    set_blocked_planning
    return 11
  fi
  if [[ "$(state_get '.planning_applied')" != true && -n "$PLANNING_FILE" ]]; then
    [[ -f "$PLANNING_FILE" ]] || die "planning file no longer exists: $PLANNING_FILE"
    jq -e 'type=="object"' "$PLANNING_FILE" >/dev/null || die "planning file must contain one JSON object"
  fi
  ensure_project
  if [[ "$(state_get '.planning_applied')" != true && -n "$PLANNING_FILE" ]]; then
    local effective_planning_file
    effective_planning_file=$(build_effective_planning_file)
    local_api_request PATCH "/projects/$(state_get '.project_id')/planning-state" "$(jq -c . "$effective_planning_file")"
    rm -f "$effective_planning_file"
    state_mutate '.planning_applied=true'
  fi
  fetch_project
  local project_id
  project_id=$(state_get '.project_id')
  [[ "$(jq -r '.producer_analysis != null' <<< "$PROJECT_JSON")" == true ]] || local_api_request POST "/projects/$project_id/generate-producer-analysis"
  fetch_project
  [[ "$(jq -r '.production_requirement_document != null' <<< "$PROJECT_JSON")" == true ]] || local_api_request POST "/projects/$project_id/generate-requirement-document"
  fetch_project
  [[ "$(jq -r '.creative_plan != null' <<< "$PROJECT_JSON")" == true ]] || local_api_request POST "/projects/$project_id/generate-creative-plan"
  fetch_project
  [[ "$(jq -r '.director_document != null' <<< "$PROJECT_JSON")" == true ]] || local_api_request POST "/projects/$project_id/generate-director-document"
  fetch_project
  [[ "$(jq -r '(.scene_groups // []) | length > 0' <<< "$PROJECT_JSON")" == true ]] || local_api_request POST "/projects/$project_id/generate-storyboard"
  set_stage storyboard_ready
}

shots_json() {
  jq -ce '(.editor_state.shot_scripts // {}) as $scripts | [.scene_groups[]?.shots[]? | . as $shot | ($shot.id|tostring) as $id | {id,narration:($scripts[$id] // $shot.narration // $shot.voiceover // $shot.title // ""),base_narration:($shot.narration // $shot.voiceover // $shot.title // ""),has_override:($scripts|has($id)),duration_seconds:($shot.duration_seconds // 1)}]' <<< "$PROJECT_JSON"
}

sha256_text() { printf '%s' "$1" | shasum -a 256 | awk '{print $1}'; }

render_fingerprint_for_json() {
  local json=$1
  sha256_text "$(jq -S -c '{topic,production_format,target_duration_seconds:(.target_duration_seconds // ([.scene_groups[]?.shots[]? | ((.duration_seconds // 0) | tonumber? // 0)] | add // 0)),scene_groups,render_manifest,design_plan,mg_layer,asset_layer,editor_state:((.editor_state // {}) | {shot_scripts,selected_broll_by_shot,html_design_overrides,mg_design_doc_overrides,avatar_enabled,avatar_mode,selected_voice_id,selected_avatar_id,voice_assets_by_shot,avatar_assets_by_shot,bgm_enabled,bgm_volume,selected_bgm_track_id,selected_bgm_track})}' <<< "$json")"
}

project_render_fingerprint() {
  render_fingerprint_for_json "$PROJECT_JSON"
}

ensure_avatar_targets() {
  [[ "$(jq -c '.avatar_shot_ids' "$STATE_PATH")" != '[]' || "$AVATAR_MODE" == none ]] && return
  fetch_project
  local shots targets
  shots=$(shots_json)
  case "$AVATAR_MODE" in
    none) targets='[]' ;;
    opening) targets=$(jq -c '[.[0].id]' <<< "$shots") ;;
    opening_closing) targets=$(jq -c 'if length==1 then [.[0].id] else [.[0].id,.[-1].id] end|unique' <<< "$shots") ;;
    all) targets=$(jq -c '[.[].id]' <<< "$shots") ;;
    *) die "unsupported avatar mode: $AVATAR_MODE" ;;
  esac
  state_mutate '.avatar_shot_ids=$targets' --argjson targets "$targets"
}

wait_for_jogg_video() {
  local shot_id=$1 video_id=$2 started now status url
  started=$(date +%s)
  while :; do
    jogg_request GET "/v2/avatar_video/$video_id"
    status=$(jq -r '.data.status // .status // empty' <<< "$HTTP_BODY" | tr '[:upper:]' '[:lower:]')
    url=$(jq -r '.data.video_url // .video_url // empty' <<< "$HTTP_BODY")
    state_mutate '.jogg_tasks[$shot].status=$status' --arg shot "$shot_id" --arg status "$status"
    case "$status" in
      completed|success|succeeded) [[ -n "$url" ]] || die "Jogg completed without a video URL"; JOGG_VIDEO_URL=$url; return 0 ;;
      failed|error|cancelled|canceled) return 2 ;;
    esac
    now=$(date +%s)
    if (( now - started >= SMART_SLIDES_MAX_JOGG_WAIT_SECONDS )); then set_stage waiting_jogg; return 124; fi
    sleep "$SMART_SLIDES_JOGG_POLL_INTERVAL_SECONDS"
  done
}

path_data_url() {
  local path=$1
  [[ "$path" == "$SMART_SLIDES_DATA_DIR/"* ]] || die "asset is outside smart-slides data directory"
  printf '/data/%s' "${path#"$SMART_SLIDES_DATA_DIR/"}"
}

download_jogg_result() {
  local shot_id=$1 video_url=$2 destination=$3 attempt delay
  for attempt in 1 2 3 4 5; do
    if curl -fsSL --connect-timeout 15 --max-time "$SMART_SLIDES_JOGG_DOWNLOAD_MAX_SECONDS" "$video_url" -o "$destination.part"; then
      mv "$destination.part" "$destination"
      return 0
    fi
    rm -f "$destination.part"
    [[ "$attempt" == 5 ]] && break
    delay=$((attempt * 5))
    log "Jogg result for $shot_id is not downloadable yet; retrying in ${delay}s"
    sleep "$delay"
  done
  return 1
}

realize_jogg_asset() {
  local shot_id=$1 duration=$2 video_url=$3 project_id target source audio avatar_dir
  project_id=$(state_get '.project_id')
  avatar_dir="$SMART_SLIDES_DATA_DIR/video_studio_assets/$project_id/jogg"
  mkdir -p "$avatar_dir"
  source="$avatar_dir/$shot_id-source.mp4"
  audio="$avatar_dir/$shot_id-voice.m4a"
  target=$(jq -r --arg id "$shot_id" '.avatar_shot_ids|index($id)!=null' "$STATE_PATH")
  log "downloading Jogg result for $shot_id"
  download_jogg_result "$shot_id" "$video_url" "$source" || die "could not download Jogg result for $shot_id"
  ffmpeg -y -v error -i "$source" -vn -c:a aac -b:a 192k "$audio" || die "could not extract Jogg audio for $shot_id"
  if [[ "$target" == true ]]; then
    local avatar="$avatar_dir/$shot_id-avatar.mp4"
    ffmpeg -y -v error -i "$source" -map 0:v:0 -c:v copy -an "$avatar" || die "could not mute Jogg avatar for $shot_id"
    state_mutate '.jogg_tasks[$shot]+={status:"ready",last_status:"ready",audio_path:$audio,avatar_path:$avatar}' --arg shot "$shot_id" --arg audio "$audio" --arg avatar "$avatar"
  else
    state_mutate '.jogg_tasks[$shot]+={status:"ready",last_status:"ready",audio_path:$audio,avatar_path:""}' --arg shot "$shot_id" --arg audio "$audio"
  fi
  rm -f "$source"
}

sync_jogg_editor_state() {
  local voice_assets='{}' avatar_assets='{}' shot_id audio avatar body project_id current
  while IFS= read -r shot_id; do
    audio=$(state_get ".jogg_tasks[\"$shot_id\"].audio_path")
    avatar=$(state_get ".jogg_tasks[\"$shot_id\"].avatar_path")
    [[ -z "$audio" ]] || voice_assets=$(jq -c --arg id "$shot_id" --arg path "$audio" --arg url "$(path_data_url "$audio")" '.[$id]={path:$path,asset_url:$url,source:"jogg_avatar_video"}' <<< "$voice_assets")
    [[ -z "$avatar" ]] || avatar_assets=$(jq -c --arg id "$shot_id" --arg path "$avatar" --arg url "$(path_data_url "$avatar")" '.[$id]={path:$path,asset_url:$url,source:"jogg_avatar_video",muted:true}' <<< "$avatar_assets")
  done < <(jq -r '.jogg_tasks|keys[]' "$STATE_PATH")
  body=$(jq -cn --argjson voices "$voice_assets" --argjson avatars "$avatar_assets" --arg mode "$AVATAR_MODE" --arg voice "$VOICE_ID" --arg avatar "$AVATAR_ID" '{avatar_enabled:false,avatar_mode:$mode,selected_voice_id:$voice,selected_avatar_id:$avatar,voice_assets_by_shot:$voices,avatar_assets_by_shot:$avatars}')
  project_id=$(state_get '.project_id')
  fetch_project
  current=$(jq -c --argjson desired "$body" '(.editor_state // {}) as $state | reduce ($desired|keys[]) as $key ({}; .[$key]=$state[$key])' <<< "$PROJECT_JSON")
  if [[ "$(jq -S -c . <<< "$current")" == "$(jq -S -c . <<< "$body")" ]]; then return 0; fi
  local_api_request PATCH "/projects/$project_id/editor-state" "$body"
}

ensure_jogg_assets_serial() {
  ensure_avatar_targets
  fetch_project
  local shots shot shot_id narration base_narration has_override duration script_hash saved_hash task_status task video_id body result submission_name old_audio old_avatar audio_path avatar_path target
  shots=$(shots_json)
  while IFS= read -r shot; do
    shot_id=$(jq -r '.id' <<< "$shot")
    narration=$(jq -r '.narration' <<< "$shot"); base_narration=$(jq -r '.base_narration' <<< "$shot"); has_override=$(jq -r '.has_override' <<< "$shot"); duration=$(jq -r '.duration_seconds' <<< "$shot")
    script_hash=$(sha256_text "$narration")
    task=$(jq -c --arg id "$shot_id" '.jogg_tasks[$id] // {}' "$STATE_PATH")
    saved_hash=$(jq -r '.script_hash // empty' <<< "$task")
    if [[ -z "$saved_hash" && "$(jq -r '.video_id // empty' <<< "$task")$(jq -r '.audio_path // empty' <<< "$task")" != "" ]]; then
      if [[ "$has_override" == true && "$narration" != "$base_narration" ]]; then
        saved_hash=legacy-unknown
      else
        state_mutate '.jogg_tasks[$id].script_hash=$hash' --arg id "$shot_id" --arg hash "$script_hash"
        saved_hash=$script_hash
        task=$(jq -c --arg id "$shot_id" '.jogg_tasks[$id] // {}' "$STATE_PATH")
      fi
    fi
    if [[ -n "$saved_hash" && "$saved_hash" != "$script_hash" ]]; then
      task_status=$(jq -r '.status // empty' <<< "$task")
      if [[ "$task_status" == submitting || "$task_status" == submission_unknown ]]; then
        state_mutate '.stage="blocked_jogg_recovery" | .error=("Jogg submission outcome is unknown for " + $id + "; refusing to submit edited narration")' --arg id "$shot_id"
        return 11
      fi
      old_audio=$(jq -r '.audio_path // empty' <<< "$task"); old_avatar=$(jq -r '.avatar_path // empty' <<< "$task")
      [[ -z "$old_audio" ]] || rm -f "$old_audio"
      [[ -z "$old_avatar" ]] || rm -f "$old_avatar"
      state_mutate '.jogg_tasks[$id]={video_id:"",status:"planned",script_hash:$hash,audio_path:"",avatar_path:""} | .composition_preview_url="" | .preview_project_fingerprint="" | .work_id="" | .render_project_fingerprint="" | .final_video_url=""' --arg id "$shot_id" --arg hash "$script_hash"
      task=$(jq -c --arg id "$shot_id" '.jogg_tasks[$id]' "$STATE_PATH")
    fi
    video_id=$(jq -r '.video_id // empty' <<< "$task")
    audio_path=$(jq -r '.audio_path // empty' <<< "$task")
    avatar_path=$(jq -r '.avatar_path // empty' <<< "$task")
    target=$(jq -r --arg id "$shot_id" '.avatar_shot_ids|index($id)!=null' "$STATE_PATH")
    if [[ -n "$audio_path" && -f "$audio_path" ]]; then
      if [[ "$target" != true || ( -n "$avatar_path" && -f "$avatar_path" ) ]]; then
        continue
      fi
      if [[ -z "$video_id" ]]; then
        state_mutate '.stage="blocked_jogg_recovery" | .error=("Target avatar file is missing for " + $id + " and no saved Jogg video_id is available; automatic paid resubmission is disabled")' --arg id "$shot_id"
        return 11
      fi
    fi
    if [[ -z "$video_id" ]]; then
      task_status=$(jq -r '.status // empty' <<< "$task")
      if [[ "$task_status" == submitting || "$task_status" == submission_unknown ]]; then
        state_mutate '.stage="blocked_jogg_recovery" | .error=("Jogg submission outcome is unknown for " + $id + "; automatic resubmission is disabled")' --arg id "$shot_id"
        return 11
      fi
      submission_name="$RUN_ID-$shot_id"
      body=$(jq -cn --arg avatar "$AVATAR_ID" --arg voice "$VOICE_ID" --arg script "$narration" --arg name "$submission_name" '{avatar:{avatar_type:0,avatar_id:($avatar|tonumber? // $avatar)},voice:{type:"script",voice_id:$voice,script:$script},aspect_ratio:"landscape",screen_style:1,caption:false,video_name:$name}')
      state_mutate '.jogg_tasks[$id]={video_id:"",status:"submitting",script_hash:$hash,submission_name:$name,audio_path:"",avatar_path:""}' --arg id "$shot_id" --arg hash "$script_hash" --arg name "$submission_name"
      if ! jogg_submit_request "$body"; then
        state_mutate '.jogg_tasks[$id].status="submission_unknown" | .stage="blocked_jogg_recovery" | .error=("Jogg submission outcome is unknown for " + $id + "; automatic resubmission is disabled")' --arg id "$shot_id"
        return 11
      fi
      video_id=$(jq -r '.data.video_id // .video_id // empty' <<< "$HTTP_BODY")
      if [[ -z "$video_id" ]]; then
        state_mutate '.jogg_tasks[$id].status="submission_unknown" | .stage="blocked_jogg_recovery" | .error=("Jogg returned no video id for " + $id + "; automatic resubmission is disabled")' --arg id "$shot_id"
        return 11
      fi
      state_mutate '.jogg_tasks[$id]+={video_id:$video,status:"pending",script_hash:$hash}' --arg id "$shot_id" --arg video "$video_id" --arg hash "$script_hash"
    fi
    if wait_for_jogg_video "$shot_id" "$video_id"; then realize_jogg_asset "$shot_id" "$duration" "$JOGG_VIDEO_URL"; else
      result=$?; [[ $result == 124 ]] && return 10; die "Jogg generation failed for $shot_id"
    fi
  done < <(jq -c '.[]' <<< "$shots")
  sync_jogg_editor_state
  set_stage jogg_assets_ready
}

jogg_worker_dir() { printf '%s/jogg-workers' "$(html_checkpoint_dir)"; }

jogg_submit_worker() {
  local shot_id=$1 body_path=$2 result_path=$3 body_file headers_file status video_id code retry_after message
  body_file=$(mktemp)
  headers_file=$(mktemp)
  status=$(curl -sS -D "$headers_file" -o "$body_file" -w '%{http_code}' --connect-timeout 10 --max-time 180 \
    -X POST "${JOGG_BASE_URL%/}/v2/create_video_from_avatar" \
    -H "X-Api-Key: $JOGG_EFFECTIVE_API_KEY" -H 'Content-Type: application/json' --data @"$body_path" 2>/dev/null || printf '000')
  code=$(jq -r '.code // 0' "$body_file" 2>/dev/null || printf 1)
  message=$(jq -r '.msg // .message // ""' "$body_file" 2>/dev/null || true)
  if [[ "$code" == 18020 ]]; then
    jq -n --arg shot "$shot_id" --arg message "${message:-Insufficient credit}" '{outcome:"insufficient_credits",shot_id:$shot,error:$message}' > "$result_path"
  elif [[ "$status" =~ ^2[0-9][0-9]$ ]]; then
    video_id=$(jq -r '.data.video_id // .video_id // empty' "$body_file" 2>/dev/null || true)
    if [[ "$code" == 0 && -n "$video_id" ]]; then
      jq -n --arg shot "$shot_id" --arg video "$video_id" '{outcome:"accepted",shot_id:$shot,video_id:$video}' > "$result_path"
    else
      jq -n --arg shot "$shot_id" '{outcome:"unknown",shot_id:$shot}' > "$result_path"
    fi
  elif [[ "$status" == 429 ]]; then
    retry_after=$(awk 'BEGIN{IGNORECASE=1} /^retry-after:/ {gsub("\\r", ""); print $2; exit}' "$headers_file" 2>/dev/null || true)
    [[ "$retry_after" =~ ^[0-9]+$ ]] || retry_after=$(jq -r '.retryAfter // .retry_after // .data.retryAfter // 60' "$body_file" 2>/dev/null || printf 60)
    [[ "$retry_after" =~ ^[0-9]+$ ]] || retry_after=60
    jq -n --arg shot "$shot_id" --argjson retry "$retry_after" '{outcome:"rate_limited",shot_id:$shot,retry_after_seconds:$retry}' > "$result_path"
  else
    jq -n --arg shot "$shot_id" --arg status "$status" '{outcome:"unknown",shot_id:$shot,http_status:$status}' > "$result_path"
  fi
  rm -f "$body_file" "$headers_file"
}

jogg_poll_worker() {
  local shot_id=$1 video_id=$2 result_path=$3 started now body_file status url code
  started=$(date +%s)
  while :; do
    body_file=$(mktemp)
    if ! curl -sS -o "$body_file" --connect-timeout 10 --max-time 30 \
      -H "X-Api-Key: $JOGG_EFFECTIVE_API_KEY" "${JOGG_BASE_URL%/}/v2/avatar_video/$video_id"; then
      rm -f "$body_file"
      jq -n --arg shot "$shot_id" --arg video "$video_id" '{outcome:"poll_error",shot_id:$shot,video_id:$video}' > "$result_path"
      return
    fi
    code=$(jq -r '.code // 0' "$body_file" 2>/dev/null || printf 1)
    status=$(jq -r '.data.status // .status // empty' "$body_file" 2>/dev/null | tr '[:upper:]' '[:lower:]')
    url=$(jq -r '.data.video_url // .video_url // empty' "$body_file" 2>/dev/null || true)
    rm -f "$body_file"
    if [[ "$code" != 0 ]]; then
      jq -n --arg shot "$shot_id" --arg video "$video_id" '{outcome:"poll_error",shot_id:$shot,video_id:$video}' > "$result_path"
      return
    fi
    case "$status" in
      completed|success|succeeded)
        if [[ -n "$url" ]]; then jq -n --arg shot "$shot_id" --arg video "$video_id" --arg url "$url" '{outcome:"completed",shot_id:$shot,video_id:$video,video_url:$url}' > "$result_path"; else jq -n --arg shot "$shot_id" --arg video "$video_id" '{outcome:"failed",shot_id:$shot,video_id:$video,error:"Jogg completed without a video URL"}' > "$result_path"; fi
        return ;;
      failed|error|cancelled|canceled)
        jq -n --arg shot "$shot_id" --arg video "$video_id" --arg status "$status" '{outcome:"failed",shot_id:$shot,video_id:$video,error:$status}' > "$result_path"
        return ;;
    esac
    now=$(date +%s)
    if (( now - started >= SMART_SLIDES_MAX_JOGG_WAIT_SECONDS )); then
      jq -n --arg shot "$shot_id" --arg video "$video_id" --arg status "$status" '{outcome:"timeout",shot_id:$shot,video_id:$video,status:$status}' > "$result_path"
      return
    fi
    sleep "$SMART_SLIDES_JOGG_POLL_INTERVAL_SECONDS"
  done
}

jogg_submission_capacity() {
  local now=$1 cutoff=$((now - 60)) recent
  state_mutate '.jogg_submission_timestamps=((.jogg_submission_timestamps // []) | map(select(. >= $cutoff)))' --argjson cutoff "$cutoff"
  recent=$(jq '.jogg_submission_timestamps | length' "$STATE_PATH")
  printf '%s' "$((SMART_SLIDES_JOGG_POST_LIMIT_PER_MINUTE - recent))"
}

submit_jogg_batch() {
  local worker_dir=$1; shift
  local now capacity dispatched=0 shot_id task hash name result outcome video retry pid waiting=0 unknown=0
  now=$(date +%s)
  capacity=$(jogg_submission_capacity "$now")
  if (( capacity <= 0 )); then
    state_mutate '.stage="waiting_jogg" | .error="Jogg POST rate limit reached; resume after one minute"'
    return 10
  fi
  local -a pids=() submitted=()
  for shot_id in "$@"; do
    (( dispatched < capacity )) || break
    task=$(jq -c --arg id "$shot_id" '.jogg_tasks[$id] // {}' "$STATE_PATH")
    hash=$(jq -r '.script_hash // empty' <<< "$task")
    name="$RUN_ID-$shot_id"
    state_mutate '.jogg_tasks[$id]+={video_id:"",status:"submitting",last_status:"submitting",submitted_at:$now,script_hash:$hash,submission_name:$name,audio_path:"",avatar_path:""} | .jogg_submission_timestamps=((.jogg_submission_timestamps // []) + [$now])' --arg id "$shot_id" --arg hash "$hash" --arg name "$name" --argjson now "$now"
    rm -f "$worker_dir/$shot_id.submit.result.json"
    jogg_submit_worker "$shot_id" "$worker_dir/$shot_id.submit.json" "$worker_dir/$shot_id.submit.result.json" &
    pids+=("$!"); submitted+=("$shot_id"); ((dispatched+=1))
  done
  for pid in "${pids[@]}"; do wait "$pid" || true; done
  for shot_id in "${submitted[@]}"; do
    result="$worker_dir/$shot_id.submit.result.json"
    outcome=$(jq -r '.outcome // "unknown"' "$result" 2>/dev/null || printf unknown)
    case "$outcome" in
      accepted)
        video=$(jq -r '.video_id // empty' "$result")
        state_mutate '.jogg_tasks[$id]+={video_id:$video,status:"pending",last_status:"pending",retry_after_seconds:0,retry_after_at:0}' --arg id "$shot_id" --arg video "$video" ;;
      rate_limited)
        retry=$(jq -r '.retry_after_seconds // 60' "$result")
        state_mutate '.jogg_tasks[$id].status="planned" | .jogg_tasks[$id].last_status="rate_limited" | .jogg_tasks[$id].retry_after_seconds=$retry | .jogg_tasks[$id].retry_after_at=($now + $retry) | .stage="waiting_jogg" | .error="Jogg POST rate limited; resume after retry window"' --arg id "$shot_id" --argjson retry "$retry" --argjson now "$now"
        waiting=1 ;;
      insufficient_credits)
        state_mutate '.jogg_tasks[$id].status="insufficient_credits" | .jogg_tasks[$id].last_status="insufficient_credits" | .jogg_tasks[$id].error=$error | .stage="insufficient_credits" | .error=("Jogg credits are insufficient for " + $id + ": " + $error)' --arg id "$shot_id" --arg error "$(jq -r '.error // "Insufficient credit"' "$result")"
        return 10 ;;
      *)
        state_mutate '.jogg_tasks[$id].status="submission_unknown" | .jogg_tasks[$id].last_status="submission_unknown" | .stage="blocked_jogg_recovery" | .error=("Jogg submission outcome is unknown for " + $id + "; automatic resubmission is disabled")' --arg id "$shot_id"
        unknown=1 ;;
    esac
  done
  (( unknown == 0 )) || return 11
  (( waiting == 0 )) || return 10
  if (( dispatched < $# )); then
    state_mutate '.stage="waiting_jogg" | .error="Jogg POST rate window is full; resume after one minute"'
    return 10
  fi
}

poll_jogg_batch() {
  local worker_dir=$1 shots=$2; shift 2
  local shot_id video_id result outcome url duration pid failed=0 timed_out=0
  local -a pids=() ids=()
  for shot_id in "$@"; do
    video_id=$(state_get ".jogg_tasks[\"$shot_id\"].video_id")
    jogg_poll_worker "$shot_id" "$video_id" "$worker_dir/$shot_id.poll.result.json" &
    pids+=("$!"); ids+=("$shot_id")
  done
  for pid in "${pids[@]}"; do wait "$pid" || true; done
  for shot_id in "${ids[@]}"; do
    result="$worker_dir/$shot_id.poll.result.json"
    outcome=$(jq -r '.outcome // "poll_error"' "$result" 2>/dev/null || printf poll_error)
    case "$outcome" in
      completed)
        url=$(jq -r '.video_url // empty' "$result")
        duration=$(jq -r --arg id "$shot_id" '.[] | select(.id==$id) | .duration_seconds' <<< "$shots")
        state_mutate '.jogg_tasks[$id].status="completed" | .jogg_tasks[$id].last_status="completed"' --arg id "$shot_id"
        realize_jogg_asset "$shot_id" "$duration" "$url" ;;
      timeout)
        state_mutate '.jogg_tasks[$id].status=$status | .jogg_tasks[$id].last_status=$status' --arg id "$shot_id" --arg status "$(jq -r '.status // "pending"' "$result")"
        timed_out=1 ;;
      *)
        state_mutate '.jogg_tasks[$id].status="failed" | .jogg_tasks[$id].last_status="failed" | .jogg_tasks[$id].error=$error' --arg id "$shot_id" --arg error "$(jq -r '.error // .status // "Jogg status poll failed"' "$result" 2>/dev/null || printf 'Jogg status poll failed')"
        failed=1 ;;
    esac
  done
  if (( failed )); then
    state_mutate '.stage="failed" | .error="One or more Jogg tasks failed; existing video checkpoints are preserved"'
    return 1
  fi
  if (( timed_out )); then
    set_stage waiting_jogg
    return 10
  fi
}

ensure_jogg_assets() {
  ensure_avatar_targets
  fetch_project
  local shots shot shot_id narration base_narration has_override duration script_hash saved_hash task task_status video_id audio_path avatar_path target old_audio old_avatar body worker_dir now retry_after_at deferred_submission=0 submission_waiting=0 submit_result
  shots=$(shots_json)
  worker_dir=$(jogg_worker_dir); mkdir -p "$worker_dir"; : > "$worker_dir/submit.list"
  while IFS= read -r shot; do
    shot_id=$(jq -r '.id' <<< "$shot"); narration=$(jq -r '.narration' <<< "$shot"); base_narration=$(jq -r '.base_narration' <<< "$shot"); has_override=$(jq -r '.has_override' <<< "$shot"); duration=$(jq -r '.duration_seconds' <<< "$shot")
    script_hash=$(sha256_text "$narration"); task=$(jq -c --arg id "$shot_id" '.jogg_tasks[$id] // {}' "$STATE_PATH"); saved_hash=$(jq -r '.script_hash // empty' <<< "$task")
    if [[ -z "$saved_hash" && "$(jq -r '.video_id // empty' <<< "$task")$(jq -r '.audio_path // empty' <<< "$task")" != "" ]]; then
      if [[ "$has_override" == true && "$narration" != "$base_narration" ]]; then saved_hash=legacy-unknown; else state_mutate '.jogg_tasks[$id].script_hash=$hash' --arg id "$shot_id" --arg hash "$script_hash"; saved_hash=$script_hash; task=$(jq -c --arg id "$shot_id" '.jogg_tasks[$id] // {}' "$STATE_PATH"); fi
    fi
    if [[ -n "$saved_hash" && "$saved_hash" != "$script_hash" ]]; then
      task_status=$(jq -r '.status // empty' <<< "$task")
      if [[ "$task_status" == submitting || "$task_status" == submission_unknown ]]; then state_mutate '.stage="blocked_jogg_recovery" | .error=("Jogg submission outcome is unknown for " + $id + "; refusing to submit edited narration")' --arg id "$shot_id"; return 11; fi
      old_audio=$(jq -r '.audio_path // empty' <<< "$task"); old_avatar=$(jq -r '.avatar_path // empty' <<< "$task"); [[ -z "$old_audio" ]] || rm -f "$old_audio"; [[ -z "$old_avatar" ]] || rm -f "$old_avatar"
      state_mutate '.jogg_tasks[$id]={video_id:"",status:"planned",script_hash:$hash,audio_path:"",avatar_path:""} | .composition_preview_url="" | .preview_project_fingerprint="" | .work_id="" | .render_project_fingerprint="" | .final_video_url=""' --arg id "$shot_id" --arg hash "$script_hash"
      task=$(jq -c --arg id "$shot_id" '.jogg_tasks[$id]' "$STATE_PATH")
    fi
    video_id=$(jq -r '.video_id // empty' <<< "$task"); audio_path=$(jq -r '.audio_path // empty' <<< "$task"); avatar_path=$(jq -r '.avatar_path // empty' <<< "$task"); target=$(jq -r --arg id "$shot_id" '.avatar_shot_ids|index($id)!=null' "$STATE_PATH")
    if [[ -n "$audio_path" && -f "$audio_path" && ( "$target" != true || ( -n "$avatar_path" && -f "$avatar_path" ) ) ]]; then continue; fi
    if [[ -n "$video_id" && ( -n "$audio_path" || -n "$avatar_path" ) ]]; then
      # Reuse the saved Jogg task to restore a missing local asset without resubmitting it.
      state_mutate '.jogg_tasks[$id].status="pending" | .jogg_tasks[$id].last_status="pending"' --arg id "$shot_id"
    fi
    if [[ -n "$video_id" ]]; then
      # The paid Jogg task already exists. Re-poll it to rebuild a missing
      # local audio/avatar derivative without submitting another POST.
      state_mutate '.jogg_tasks[$id].status="pending" | .jogg_tasks[$id].last_status="recovering_local_asset"' --arg id "$shot_id"
    else
      task_status=$(jq -r '.status // empty' <<< "$task")
      if [[ "$task_status" == submitting || "$task_status" == submission_unknown ]]; then state_mutate '.stage="blocked_jogg_recovery" | .error=("Jogg submission outcome is unknown for " + $id + "; automatic resubmission is disabled")' --arg id "$shot_id"; return 11; fi
      retry_after_at=$(jq -r '.retry_after_at // 0' <<< "$task")
      now=$(date +%s)
      if [[ "$retry_after_at" =~ ^[0-9]+$ ]] && (( retry_after_at > now )); then
        deferred_submission=1
        continue
      fi
      body=$(jq -cn --arg avatar "$AVATAR_ID" --arg voice "$VOICE_ID" --arg script "$narration" --arg name "$RUN_ID-$shot_id" '{avatar:{avatar_type:0,avatar_id:($avatar|tonumber? // $avatar)},voice:{type:"script",voice_id:$voice,script:$script},aspect_ratio:"landscape",screen_style:1,caption:false,video_name:$name}')
      state_mutate '.jogg_tasks[$id]={video_id:"",status:"planned",script_hash:$hash,audio_path:"",avatar_path:""}' --arg id "$shot_id" --arg hash "$script_hash"
      printf '%s' "$body" > "$worker_dir/$shot_id.submit.json"; printf '%s\n' "$shot_id" >> "$worker_dir/submit.list"
    fi
  done < <(jq -c '.[]' <<< "$shots")
  local -a batch=(); local queued
  while IFS= read -r queued; do
    (( submission_waiting == 0 )) || break
    batch+=("$queued")
    if (( ${#batch[@]} == SMART_SLIDES_JOGG_CONCURRENCY )); then
      submit_jogg_batch "$worker_dir" "${batch[@]}" || { submit_result=$?; [[ "$submit_result" == 10 ]] && submission_waiting=1 || return "$submit_result"; }
      batch=()
    fi
  done < "$worker_dir/submit.list"
  if (( ${#batch[@]} )); then
    submit_jogg_batch "$worker_dir" "${batch[@]}" || { submit_result=$?; [[ "$submit_result" == 10 ]] && submission_waiting=1 || return "$submit_result"; }
  fi
  : > "$worker_dir/poll.list"
  jq -r '.jogg_tasks | to_entries[] | select((.value.status // "") == "pending" and (.value.video_id // "") != "") | .key' "$STATE_PATH" > "$worker_dir/poll.list"
  batch=()
  while IFS= read -r queued; do
    batch+=("$queued")
    if (( ${#batch[@]} == SMART_SLIDES_JOGG_CONCURRENCY )); then poll_jogg_batch "$worker_dir" "$shots" "${batch[@]}" || return $?; batch=(); fi
  done < "$worker_dir/poll.list"
  (( ${#batch[@]} == 0 )) || poll_jogg_batch "$worker_dir" "$shots" "${batch[@]}" || return $?
  if (( deferred_submission || submission_waiting )); then
    set_stage waiting_jogg
    return 10
  fi
  sync_jogg_editor_state
  set_stage jogg_assets_ready
}

audio_duration_seconds() {
  local audio_path=$1 duration
  duration=$(ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "$audio_path" 2>/dev/null | tr -d '[:space:]') || return 1
  [[ "$duration" =~ ^[0-9]+([.][0-9]+)?$ ]] || return 1
  awk -v value="$duration" 'BEGIN { if (value < 0.1 || value > 3600) exit 1; printf "%.3f", value }'
}

sync_jogg_voice_timing() {
  local project_id audio_path shot_id measured durations body actual changed
  project_id=$(state_get '.project_id')
  [[ -n "$project_id" ]] || die "run state has no project_id"
  durations='{}'
  while IFS= read -r shot_id; do
    audio_path=$(state_get ".jogg_tasks[\"$shot_id\"].audio_path")
    if [[ -z "$audio_path" || ! -f "$audio_path" ]]; then
      state_mutate '.stage="blocked_jogg_recovery" | .error=("Jogg audio is missing for " + $id + "; refusing to infer a timeline")' --arg id "$shot_id"
      return 11
    fi
    if ! measured=$(audio_duration_seconds "$audio_path"); then
      state_mutate '.stage="blocked_jogg_recovery" | .error=("Could not measure Jogg audio duration for " + $id + "; refusing to infer a timeline")' --arg id "$shot_id"
      return 11
    fi
    durations=$(jq -c --arg id "$shot_id" --argjson duration "$measured" '.[$id]=$duration' <<< "$durations")
  done < <(jq -r '.jogg_tasks|keys[]' "$STATE_PATH")
  body=$(jq -cn --argjson durations "$durations" '{voice_durations_by_shot:$durations}')
  log "synchronizing shot timing to measured Jogg narration"
  local_api_request POST "/projects/$project_id/sync-voice-timing" "$body"
  actual=$(jq -r '.actual_duration_seconds // 0' <<< "$HTTP_BODY")
  changed=$(jq '(.updated_shot_ids // []) | length' <<< "$HTTP_BODY")
  if [[ "$changed" =~ ^[1-9][0-9]*$ ]]; then
    # Timing changes invalidate only previews/works. Jogg checkpoints remain
    # intact and B-roll is re-evaluated against the new shot duration below.
    state_mutate '.actual_duration_seconds=$actual | .composition_preview_url="" | .preview_project_fingerprint="" | .work_id="" | .render_project_fingerprint="" | .final_video_url="" | .error=""' --argjson actual "$actual"
  else
    state_mutate '.actual_duration_seconds=$actual | .error=""' --argjson actual "$actual"
  fi
}

ensure_broll() {
  fetch_project
  local targets shots shot shot_id duration has_asset project_id=''
  targets=$(jq -c '.avatar_shot_ids' "$STATE_PATH"); shots=$(shots_json); project_id=$(state_get '.project_id')
  while IFS= read -r shot; do
    shot_id=$(jq -r '.id' <<< "$shot")
    duration=$(jq -r '.duration_seconds' <<< "$shot")
    jq -e --arg id "$shot_id" 'index($id)!=null' <<< "$targets" >/dev/null && continue
    fetch_project
    has_asset=$(jq -r --arg id "$shot_id" --argjson duration "$duration" '[.scene_groups[]?.shots[]?|select(.id==$id)|.broll_options[]?|select(((.asset_path//"")!="" or (.asset_url//"")!="") and ((((.duration_seconds // 0)|tonumber? // 0) + 0.25) >= $duration))]|length>0' <<< "$PROJECT_JSON")
    if [[ "$has_asset" != true ]]; then
      log "downloading B-roll for $shot_id"
      request POST "${SMART_SLIDES_BASE_URL%/}/api/v1/video-studio/projects/$project_id/shots/$shot_id/broll-assets" ''
      if [[ ! "$HTTP_STATUS" =~ ^2[0-9][0-9]$ ]]; then
        local detail
        detail=$(jq -r '.detail // "B-roll download failed"' <<< "$HTTP_BODY" 2>/dev/null || printf 'B-roll download failed')
        state_mutate '.stage="blocked_broll" | .error=$error' --arg error "$detail"
        return 11
      fi
    fi
  done < <(jq -c '.[]' <<< "$shots")
  state_mutate '.broll_shot_ids=$ids' --argjson ids "$(jq -c --argjson targets "$targets" '[.[].id]-$targets' <<< "$shots")"
  set_stage broll_ready
}

refresh_broll() {
  local project_id
  start_local_service
  project_id=$(state_get '.project_id')
  [[ -n "$project_id" ]] || die "run state has no project_id"
  log "clearing provider B-roll for explicit refresh"
  local_api_request POST "/projects/$project_id/refresh-broll"
  state_mutate '.stage="broll_refreshing" | .composition_preview_url="" | .preview_project_fingerprint="" | .work_id="" | .render_project_fingerprint="" | .final_video_url="" | .error=""'
  ensure_broll
  ensure_preview
  emit_state
}

ensure_preview() {
  local project_id preview project_fingerprint saved_fingerprint
  project_id=$(state_get '.project_id')
  fetch_project
  project_fingerprint=$(project_render_fingerprint)
  saved_fingerprint=$(state_get '.preview_project_fingerprint')
  if [[ -n "$(state_get '.composition_preview_url')" && "$project_fingerprint" == "$saved_fingerprint" ]]; then return 0; fi
  local_api_request POST "/projects/$project_id/prepare-editor-assets"
  local_api_request POST "/projects/$project_id/composition-preview"
  preview=$(jq -r '.preview_url // .project.composition_preview_url // empty' <<< "$HTTP_BODY")
  [[ -n "$preview" ]] || die "local API did not create a preview"
  [[ "$preview" =~ ^https?:// ]] || preview="${SMART_SLIDES_BASE_URL%/}$preview"
  fetch_project
  project_fingerprint=$(project_render_fingerprint)
  state_mutate '.composition_preview_url=$url | .preview_project_fingerprint=$fingerprint | .editor_url=($base+"/?project_id="+.project_id)' --arg url "$preview" --arg fingerprint "$project_fingerprint" --arg base "$SMART_SLIDES_BASE_URL"
  set_stage preview_ready
}

wait_for_render() {
  local work_id=$1 started now status url
  started=$(date +%s)
  local_api_request POST "/works/$work_id/resume"
  while :; do
    local_api_request GET "/works/$work_id"
    status=$(jq -r '.work.status // empty' <<< "$HTTP_BODY")
    case "$status" in
      success)
        url=$(jq -r '.work.output.url // empty' <<< "$HTTP_BODY")
        [[ "$url" =~ ^https?:// ]] || url="${SMART_SLIDES_BASE_URL%/}$url"
        state_mutate '.final_video_url=$url' --arg url "$url"
        return 0 ;;
      failed) state_mutate '.error=$error' --arg error "$(jq -r '.work.error // "local render failed"' <<< "$HTTP_BODY")"; return 2 ;;
    esac
    now=$(date +%s)
    if (( now - started >= SMART_SLIDES_MAX_RENDER_WAIT_SECONDS )); then set_stage waiting_render; return 124; fi
    sleep "$SMART_SLIDES_RENDER_POLL_INTERVAL_SECONDS"
  done
}

ensure_render() {
  local project_id work_id result project_fingerprint render_fingerprint work_snapshot snapshot_fingerprint
  ensure_local_renderer
  project_id=$(state_get '.project_id'); work_id=$(state_get '.work_id')
  fetch_project
  project_fingerprint=$(project_render_fingerprint)
  render_fingerprint=$(state_get '.render_project_fingerprint')
  if [[ -n "$work_id" ]]; then
    work_snapshot=''
    request GET "${SMART_SLIDES_BASE_URL%/}/api/v1/video-studio/works/$work_id" ''
    if [[ "$HTTP_STATUS" =~ ^2[0-9][0-9]$ ]]; then
      work_snapshot=$(jq -ce '.work.render_snapshot | select(type=="object")' <<< "$HTTP_BODY" 2>/dev/null || true)
    fi
    if [[ -n "$work_snapshot" ]]; then
      snapshot_fingerprint=$(render_fingerprint_for_json "$work_snapshot")
    else
      snapshot_fingerprint=''
    fi
    if [[ -n "$snapshot_fingerprint" && "$snapshot_fingerprint" == "$project_fingerprint" ]]; then
      render_fingerprint=$snapshot_fingerprint
      state_mutate '.render_project_fingerprint=$fingerprint' --arg fingerprint "$snapshot_fingerprint"
    else
      log "saved work snapshot no longer matches current render inputs"
      work_id=''
      state_mutate '.work_id="" | .render_project_fingerprint="" | .final_video_url=""'
    fi
  fi
  if [[ -n "$work_id" && "$project_fingerprint" != "$render_fingerprint" ]]; then
    work_id=''
    state_mutate '.work_id="" | .render_project_fingerprint="" | .final_video_url=""'
  fi
  if [[ -z "$work_id" ]]; then
    local_api_request POST "/projects/$project_id/works"
    work_id=$(jq -r '.work.id // empty' <<< "$HTTP_BODY")
    [[ -n "$work_id" ]] || die "local API did not create a work"
    state_mutate '.work_id=$id | .render_project_fingerprint=$fingerprint' --arg id "$work_id" --arg fingerprint "$project_fingerprint"
  fi
  if wait_for_render "$work_id"; then set_stage completed; return; fi
  result=$?; [[ $result == 124 ]] && return 10; die "local render failed"
}

run_until_preview() {
  ensure_html_ready || return $?
  start_local_service
  ensure_planning || return $?
  resolve_jogg_api_key; resolve_profile
  ensure_jogg_assets || return $?
  sync_jogg_voice_timing || return $?
  ensure_broll || return $?
  ensure_preview
}

parse_run_args() {
  while (($#)); do
    case "$1" in
      --topic) TOPIC=${2:-}; shift 2 ;;
      --duration-seconds) DURATION_SECONDS=${2:-}; shift 2 ;;
      --avatar-mode) AVATAR_MODE=${2:-}; shift 2 ;;
      --avatar-style) AVATAR_STYLE=${2:-}; shift 2 ;;
      --avatar-gender) AVATAR_GENDER=${2:-}; shift 2 ;;
      --avatar-age) AVATAR_AGE=${2:-}; shift 2 ;;
      --planning-file) PLANNING_FILE=${2:-}; shift 2 ;;
      --voice-id) VOICE_ID=${2:-}; shift 2 ;;
      --avatar-id) AVATAR_ID=${2:-}; shift 2 ;;
      *) die "unknown option: $1" ;;
    esac
  done
}

parse_run_id() { [[ "${1:-}" == --run-id && -n "${2:-}" ]] || die '--run-id is required'; load_run "$2"; }

parse_resume_args() {
  local requested_run_id='' supplied_planning_file=''
  while (($#)); do
    case "$1" in
      --run-id) requested_run_id=${2:-}; shift 2 ;;
      --planning-file) supplied_planning_file=${2:-}; shift 2 ;;
      *) die "unknown resume option: $1" ;;
    esac
  done
  [[ -n "$requested_run_id" ]] || die '--run-id is required'
  load_run "$requested_run_id"
  if [[ -n "$supplied_planning_file" ]]; then
    PLANNING_FILE=$supplied_planning_file
    RESUME_PLANNING_FILE=$supplied_planning_file
  fi
}

parse_html_action_args() {
  local requested_run_id=''
  while (($#)); do
    case "$1" in
      --run-id) requested_run_id=${2:-}; shift 2 ;;
      --clip-id) HTML_CLIP_ID=${2:-}; shift 2 ;;
      --html-file) HTML_FILE=${2:-}; shift 2 ;;
      --at-seconds) HTML_AT_SECONDS=${2:-}; shift 2 ;;
      *) die "unknown $ACTION option: $1" ;;
    esac
  done
  [[ -n "$requested_run_id" ]] || die '--run-id is required'
  load_run "$requested_run_id"
}

handle_checkpoint() {
  local result=$1
  case "$result" in
    10|11) emit_state; return 0 ;;
    *)
      [[ -n "$STATE_PATH" && -f "$STATE_PATH" ]] && emit_state
      return "$result"
      ;;
  esac
}

refresh_status() {
  local work_id status url
  work_id=$(state_get '.work_id')
  [[ -n "$work_id" ]] || return 0
  load_saved_service
  [[ -n "$SMART_SLIDES_BASE_URL" ]] && local_service_ready || return 0
  request GET "${SMART_SLIDES_BASE_URL%/}/api/v1/video-studio/works/$work_id" ''
  [[ "$HTTP_STATUS" =~ ^2[0-9][0-9]$ ]] || return 0
  status=$(jq -r '.work.status // empty' <<< "$HTTP_BODY")
  case "$status" in
    success)
      url=$(jq -r '.work.output.url // empty' <<< "$HTTP_BODY")
      [[ "$url" =~ ^https?:// ]] || url="${SMART_SLIDES_BASE_URL%/}$url"
      state_mutate '.stage="completed" | .final_video_url=$url | .error=""' --arg url "$url" ;;
    failed) state_mutate '.stage="failed" | .error=$error' --arg error "$(jq -r '.work.error // "local render failed"' <<< "$HTTP_BODY")" ;;
  esac
}

main() {
  ACTION=${1:-}; shift || true
  if [[ "$ACTION" == install-deps ]]; then
    install_dependencies
    dependency_report
    return 0
  fi
  require_bin curl; require_bin jq
  if [[ "$ACTION" == doctor ]]; then
    dependency_report
    return 0
  fi
  if [[ "$ACTION" != preflight && "$ACTION" != settings ]]; then
    require_bin ffmpeg; require_bin ffprobe; require_bin shasum
  fi
  mkdir -p "$SMART_SLIDES_HOME" "$SMART_SLIDES_DATA_DIR" "$SMART_SLIDES_STATE_DIR"
  case "$ACTION" in
    preflight)
      start_local_service
      if [[ -z "${JOGG_API_KEY:-}" ]]; then
        jq -n --arg local "$SMART_SLIDES_BASE_URL" --arg settings "$(open_settings_page)" '{status:"configuration_required",local_base_url:$local,settings_url:$settings,jogg_api_key_configured:false}'
        return 0
      fi
      if [[ "$(dependency_report | jq -r '.status')" != ready ]]; then
        log "installing missing local render dependencies"
        install_dependencies
      fi
      require_bin ffmpeg; require_bin ffprobe; require_bin shasum
      ensure_local_renderer; resolve_jogg_api_key
      jq -n --arg local "$SMART_SLIDES_BASE_URL" --arg jogg "$JOGG_BASE_URL" --arg data "$SMART_SLIDES_DATA_DIR" '{status:"ready",local_base_url:$local,jogg_base_url:$jogg,data_dir:$data,jogg_api_key_configured:true,ffprobe_available:true}' ;;
    settings)
      start_local_service
      jq -n --arg local "$SMART_SLIDES_BASE_URL" --arg settings "$(open_settings_page)" '{status:"ready",local_base_url:$local,settings_url:$settings}' ;;
    run)
      parse_run_args "$@"; [[ -n "$TOPIC" ]] || die '--topic is required'; [[ "$DURATION_SECONDS" =~ ^[0-9]+$ ]] || die 'duration must be an integer'
      [[ "$AVATAR_MODE" =~ ^(none|opening|opening_closing|all)$ ]] || die 'invalid avatar mode'; init_run; acquire_run_lock
      if ! planning_input_available; then set_blocked_planning; emit_state; return 0; fi
      if run_until_preview && ensure_render; then emit_state; else handle_checkpoint "$?"; fi ;;
    resume)
      parse_resume_args "$@"; acquire_run_lock
      if [[ -n "$RESUME_PLANNING_FILE" ]]; then
        state_mutate '.planning_file=$planning_file | .planning_applied=false | .html_planning_fingerprint="" | .html_clip_checkpoints={} | .pending_clip_ids=[] | .avatar_shot_ids=[] | .error=""' --arg planning_file "$RESUME_PLANNING_FILE"
      fi
      if run_until_preview && ensure_render; then emit_state; else handle_checkpoint "$?"; fi ;;
    html-status)
      parse_html_action_args "$@"; acquire_run_lock; initialize_html_checkpoints; refresh_pending_clip_ids; emit_state ;;
    apply-html)
      parse_html_action_args "$@"; acquire_run_lock
      [[ -n "$HTML_CLIP_ID" ]] || die '--clip-id is required'
      [[ -n "$HTML_FILE" ]] || die '--html-file is required'
      apply_html_asset "$HTML_CLIP_ID" "$HTML_FILE" ;;
    capture-html)
      parse_html_action_args "$@"; acquire_run_lock
      [[ -n "$HTML_CLIP_ID" ]] || die '--clip-id is required'
      [[ -n "$HTML_AT_SECONDS" ]] || die '--at-seconds is required'
      capture_html_asset "$HTML_CLIP_ID" "$HTML_AT_SECONDS" ;;
    approve-html)
      parse_html_action_args "$@"; acquire_run_lock
      [[ -n "$HTML_CLIP_ID" ]] || die '--clip-id is required'
      approve_html_asset "$HTML_CLIP_ID" ;;
    preview)
      parse_run_id "$@"; acquire_run_lock
      if run_until_preview; then emit_state; else handle_checkpoint "$?"; fi ;;
    refresh-broll)
      parse_run_id "$@"; acquire_run_lock
      refresh_broll ;;
    render)
      parse_run_id "$@"; acquire_run_lock
      if ensure_html_ready; then :; else handle_checkpoint "$?"; return; fi
      ensure_local_renderer; start_local_service
      if ensure_render; then emit_state; else handle_checkpoint "$?"; fi ;;
    status)
      parse_run_id "$@"; acquire_run_lock; refresh_status; emit_state ;;
    import)
      local file=''
      while (($#)); do case "$1" in --file) file=${2:-}; shift 2 ;; --avatar-mode) AVATAR_MODE=${2:-}; shift 2 ;; *) die "unknown import option: $1" ;; esac; done
      [[ -f "$file" ]] || die 'import --file must point to a project JSON'; jq -e 'type=="object" and (.id|type=="string")' "$file" >/dev/null || die 'invalid Video Studio project JSON'
      start_local_service; TOPIC=$(jq -r '.topic // "Imported Video Studio project"' "$file"); DURATION_SECONDS=$(jq -r '.target_duration_seconds // 180' "$file"); init_run; acquire_run_lock
      local_api_request POST '/projects/import' "$(jq -c '{project:.}' "$file")"
      state_mutate '.project_id=$id | .planning_applied=true | .stage="project_imported" | .editor_url=($base+"/?project_id="+$id)' --arg id "$(jq -r '.project.id' <<< "$HTTP_BODY")" --arg base "$SMART_SLIDES_BASE_URL"
      emit_state ;;
    help|-h|--help|'') usage ;;
    *) die "unknown action: $ACTION" ;;
  esac
}

main "$@"
