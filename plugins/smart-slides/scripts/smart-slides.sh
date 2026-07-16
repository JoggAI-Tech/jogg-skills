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

load_env_file "$PLUGIN_ROOT/.env"
load_env_file "$HOME/.codex/smart-slides/.env"

: "${JOGG_REPO:=/Users/cds-dn-137/Documents/golang/jogg-backend-srv}"
: "${JOGG_BASE_URL:=http://127.0.0.1:8000}"
: "${SMART_SLIDES_HOME:=$HOME/.codex/smart-slides}"
: "${SMART_SLIDES_DATA_DIR:=$SMART_SLIDES_HOME/data}"
: "${SMART_SLIDES_STATE_DIR:=$SMART_SLIDES_HOME/runs}"
: "${SMART_SLIDES_SERVICE_FILE:=$SMART_SLIDES_HOME/service.json}"
: "${SMART_SLIDES_TOOL_DIR:=$SMART_SLIDES_HOME/bin}"
: "${SMART_SLIDES_JOGG_POLL_INTERVAL_SECONDS:=10}"
: "${SMART_SLIDES_RENDER_POLL_INTERVAL_SECONDS:=5}"
: "${SMART_SLIDES_MAX_JOGG_WAIT_SECONDS:=1800}"
: "${SMART_SLIDES_MAX_RENDER_WAIT_SECONDS:=7200}"

ACTION=""
RUN_ID=""
STATE_PATH=""
LOCK_DIR=""
TOPIC=""
DURATION_SECONDS=600
AVATAR_MODE="opening_closing"
AVATAR_STYLE="professional"
AVATAR_GENDER="female"
AVATAR_AGE="adult"
PLANNING_FILE=""
RESUME_PLANNING_FILE=""
VOICE_ID="${JOGG_DEFAULT_VOICE_ID:-}"
AVATAR_ID="${JOGG_DEFAULT_AVATAR_ID:-}"
JOGG_EFFECTIVE_API_KEY=""
SMART_SLIDES_BASE_URL="${SMART_SLIDES_BASE_URL:-}"
PROJECT_JSON='{}'
HTTP_STATUS=""
HTTP_BODY=""

[[ -x "$SMART_SLIDES_TOOL_DIR/ffprobe" ]] && export PATH="$SMART_SLIDES_TOOL_DIR:$PATH"

log() { printf '[smart-slides] %s\n' "$*" >&2; }

usage() {
  cat <<'EOF'
usage:
  smart-slides.sh preflight
  smart-slides.sh run --topic TEXT [--duration-seconds 600] [--avatar-mode MODE] [--planning-file PLAN.json]
  smart-slides.sh resume --run-id RUN_ID [--planning-file PLAN.json]
  smart-slides.sh status --run-id RUN_ID
  smart-slides.sh preview --run-id RUN_ID
  smart-slides.sh render --run-id RUN_ID
  smart-slides.sh import --file PROJECT.json [--avatar-mode MODE]

avatar modes: none, opening, opening_closing, all
EOF
}

require_bin() { command -v "$1" >/dev/null 2>&1 || die "missing required binary: $1"; }

ensure_local_renderer() {
  local python_bin
  python_bin=$(ensure_python_runtime)
  PYTHONPATH="$RUNTIME_ROOT" "$python_bin" -c 'from render.ffmpeg_adapter import ensure_renderer_available; ensure_renderer_available()' \
    || die "local FFmpeg renderer is not ready"
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
  jq '{run_id,stage,topic,target_duration_seconds,project_id,avatar_mode,avatar_shot_ids,jogg_tasks:(.jogg_tasks|with_entries(.value|={video_id,status,audio_path,avatar_path})),broll_shot_ids,composition_preview_url,editor_url,work_id,final_video_url,error,updated_at}' "$STATE_PATH"
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
    -X POST "${JOGG_BASE_URL%/}/open/v2/create_video_from_avatar" \
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
jogg_reachable() { [[ "$(http_status "${JOGG_BASE_URL%/}/openapi_key")" =~ ^(200|401|403|405)$ ]]; }

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
  (
    export PYTHONPATH="$RUNTIME_ROOT"
    export SMART_SLIDES_DATA_DIR
    exec "$python_bin" -m uvicorn backend.main:app --host 127.0.0.1 --port "$port"
  ) > "$SMART_SLIDES_HOME/logs/service.log" 2>&1 &
  local pid=$! attempt
  for attempt in $(seq 1 60); do local_service_ready && break; sleep 0.5; done
  local_service_ready || die "bundled Video Studio did not start; see $SMART_SLIDES_HOME/logs/service.log"
  jq -n --arg base_url "$SMART_SLIDES_BASE_URL" --argjson pid "$pid" '{base_url:$base_url,pid:$pid}' > "$SMART_SLIDES_SERVICE_FILE"
}

start_jogg_if_needed() {
  jogg_reachable && return 0
  [[ -d "$JOGG_REPO" ]] || die "Jogg is not reachable and JOGG_REPO does not exist"
  mkdir -p "$SMART_SLIDES_HOME/logs"
  log "starting local Jogg service"
  if [[ -n "${JOGG_START_CMD:-}" ]]; then
    (cd "$JOGG_REPO" && exec /bin/bash -lc "$JOGG_START_CMD") > "$SMART_SLIDES_HOME/logs/jogg.log" 2>&1 &
  else
    (cd "$JOGG_REPO" && exec go run .) > "$SMART_SLIDES_HOME/logs/jogg.log" 2>&1 &
  fi
  local attempt
  for attempt in $(seq 1 60); do jogg_reachable && return 0; sleep 1; done
  die "Jogg did not become ready; see $SMART_SLIDES_HOME/logs/jogg.log"
}

openapi_response_ok() {
  [[ "$HTTP_STATUS" =~ ^2[0-9][0-9]$ ]] && [[ "$(jq -r '(.code // 0) == 0' <<< "$HTTP_BODY")" == true ]]
}

validate_jogg_api_key() {
  local candidate=$1
  [[ -n "$candidate" ]] || return 1
  request GET "${JOGG_BASE_URL%/}/open/v2/voices?language=chinese&gender=female&page=1&page_size=1" '' "X-Api-Key: $candidate"
  if openapi_response_ok; then
    JOGG_EFFECTIVE_API_KEY=$candidate
    return 0
  fi
  JOGG_EFFECTIVE_API_KEY=''
  return 1
}

resolve_jogg_api_key() {
  [[ -n "$JOGG_EFFECTIVE_API_KEY" ]] && return
  if [[ -n "${JOGG_API_KEY:-}" ]] && validate_jogg_api_key "$JOGG_API_KEY"; then return; fi
  [[ -z "${JOGG_API_KEY:-}" ]] || log "configured Jogg OpenAPI key was rejected; trying the browser-login token"
  [[ -n "${JOGG_WEB_TOKEN:-}" ]] || die "Jogg OpenAPI key is invalid. Sign in to Jogg again, then set a fresh JOGG_WEB_TOKEN or JOGG_API_KEY."
  request GET "${JOGG_BASE_URL%/}/openapi_key" '' "Authorization: Bearer $JOGG_WEB_TOKEN"
  openapi_response_ok || die "Jogg browser-login token is expired or invalid. Sign in again, then update JOGG_WEB_TOKEN."
  local access_key
  access_key=$(jq -r '.data.access_key // .access_key // empty' <<< "$HTTP_BODY")
  if [[ -z "$access_key" ]]; then
    request POST "${JOGG_BASE_URL%/}/openapi_key/generate" '' "Authorization: Bearer $JOGG_WEB_TOKEN"
    openapi_response_ok || die "Jogg browser-login token cannot generate an OpenAPI key. Sign in again, then update JOGG_WEB_TOKEN."
    access_key=$(jq -r '.data.access_key // .access_key // empty' <<< "$HTTP_BODY")
  fi
  [[ -n "$access_key" ]] || die "Jogg did not return an OpenAPI key. Sign in again, then update JOGG_WEB_TOKEN."
  validate_jogg_api_key "$access_key" || die "Jogg returned an OpenAPI key without /open/v2 permission. Sign in again, then retry."
}

resolve_profile() {
  local saved_voice saved_avatar query candidate
  saved_voice=$(state_get '.avatar_profile.voice_id')
  saved_avatar=$(state_get '.avatar_profile.avatar_id')
  [[ -n "$saved_voice" ]] && VOICE_ID=$saved_voice
  [[ -n "$saved_avatar" ]] && AVATAR_ID=$saved_avatar
  if [[ -z "$VOICE_ID" ]]; then
    jogg_request GET '/open/v2/voices?language=chinese&gender=female&page=1&page_size=20'
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
      jogg_request GET "/open/v2/avatars/public?$query&page=1&page_size=20"
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
    '{version:"smart_slides_run_v1",run_id:$run_id,topic:$topic,target_duration_seconds:$duration,avatar_mode:$mode,planning_file:$planning_file,planning_applied:false,avatar_profile:{style:$style,gender:$gender,age:$age,voice_id:"",avatar_id:""},stage:"initialized",project_id:"",avatar_shot_ids:[],jogg_tasks:{},broll_shot_ids:[],composition_preview_url:"",preview_project_fingerprint:"",editor_url:"",work_id:"",render_project_fingerprint:"",final_video_url:"",error:"",created_at:$now,updated_at:$now}' > "$STATE_PATH"
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
    local_api_request PATCH "/projects/$(state_get '.project_id')/planning-state" "$(jq -c . "$PLANNING_FILE")"
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
    jogg_request GET "/open/v2/avatar_video/$video_id"
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

realize_jogg_asset() {
  local shot_id=$1 duration=$2 video_url=$3 project_id target source audio avatar_dir
  project_id=$(state_get '.project_id')
  avatar_dir="$SMART_SLIDES_DATA_DIR/video_studio_assets/$project_id/jogg"
  mkdir -p "$avatar_dir"
  source="$avatar_dir/$shot_id-source.mp4"
  audio="$avatar_dir/$shot_id-voice.m4a"
  target=$(jq -r --arg id "$shot_id" '.avatar_shot_ids|index($id)!=null' "$STATE_PATH")
  log "downloading Jogg result for $shot_id"
  curl -fsSL --connect-timeout 15 --max-time 900 "$video_url" -o "$source" || die "could not download Jogg result for $shot_id"
  ffmpeg -y -v error -i "$source" -vn -c:a aac -b:a 192k "$audio" || die "could not extract Jogg audio for $shot_id"
  if [[ "$target" == true ]]; then
    local avatar="$avatar_dir/$shot_id-avatar.mp4"
    ffmpeg -y -v error -i "$source" -map 0:v:0 -c:v copy -an "$avatar" || die "could not mute Jogg avatar for $shot_id"
    state_mutate '.jogg_tasks[$shot]+={status:"ready",audio_path:$audio,avatar_path:$avatar}' --arg shot "$shot_id" --arg audio "$audio" --arg avatar "$avatar"
  else
    state_mutate '.jogg_tasks[$shot]+={status:"ready",audio_path:$audio,avatar_path:""}' --arg shot "$shot_id" --arg audio "$audio"
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

ensure_jogg_assets() {
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

ensure_broll() {
  fetch_project
  local targets shots shot_id has_asset project_id=''
  targets=$(jq -c '.avatar_shot_ids' "$STATE_PATH"); shots=$(shots_json); project_id=$(state_get '.project_id')
  while IFS= read -r shot_id; do
    jq -e --arg id "$shot_id" 'index($id)!=null' <<< "$targets" >/dev/null && continue
    fetch_project
    has_asset=$(jq -r --arg id "$shot_id" '[.scene_groups[]?.shots[]?|select(.id==$id)|.broll_options[]?|select((.asset_path//"")!="" or (.asset_url//"")!="")]|length>0' <<< "$PROJECT_JSON")
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
  done < <(jq -r '.[].id' <<< "$shots")
  state_mutate '.broll_shot_ids=$ids' --argjson ids "$(jq -c --argjson targets "$targets" '[.[].id]-$targets' <<< "$shots")"
  set_stage broll_ready
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
  if [[ -n "$work_id" && -z "$render_fingerprint" ]]; then
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
  start_local_service
  ensure_planning || return $?
  start_jogg_if_needed; resolve_jogg_api_key; resolve_profile
  ensure_jogg_assets || return $?
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

handle_checkpoint() {
  local result=$1
  case "$result" in 10|11) emit_state; return 0 ;; *) return "$result" ;; esac
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
  require_bin curl; require_bin jq; require_bin ffmpeg; require_bin ffprobe; require_bin shasum
  mkdir -p "$SMART_SLIDES_HOME" "$SMART_SLIDES_DATA_DIR" "$SMART_SLIDES_STATE_DIR"
  case "$ACTION" in
    preflight)
      ensure_local_renderer; start_local_service; start_jogg_if_needed; resolve_jogg_api_key
      jq -n --arg local "$SMART_SLIDES_BASE_URL" --arg jogg "$JOGG_BASE_URL" --arg data "$SMART_SLIDES_DATA_DIR" '{status:"ready",local_base_url:$local,jogg_base_url:$jogg,data_dir:$data,ffprobe_available:true}' ;;
    run)
      parse_run_args "$@"; [[ -n "$TOPIC" ]] || die '--topic is required'; [[ "$DURATION_SECONDS" =~ ^[0-9]+$ ]] || die 'duration must be an integer'
      [[ "$AVATAR_MODE" =~ ^(none|opening|opening_closing|all)$ ]] || die 'invalid avatar mode'; init_run; acquire_run_lock
      if ! planning_input_available; then set_blocked_planning; emit_state; return 0; fi
      if run_until_preview && ensure_render; then emit_state; else handle_checkpoint "$?"; fi ;;
    resume)
      parse_resume_args "$@"; acquire_run_lock
      if [[ -n "$RESUME_PLANNING_FILE" ]]; then
        state_mutate '.planning_file=$planning_file | .planning_applied=false | .error=""' --arg planning_file "$RESUME_PLANNING_FILE"
      fi
      if run_until_preview && ensure_render; then emit_state; else handle_checkpoint "$?"; fi ;;
    preview)
      parse_run_id "$@"; acquire_run_lock
      if run_until_preview; then emit_state; else handle_checkpoint "$?"; fi ;;
    render)
      parse_run_id "$@"; acquire_run_lock; ensure_local_renderer; start_local_service
      if ensure_render; then emit_state; else handle_checkpoint "$?"; fi ;;
    status)
      parse_run_id "$@"; acquire_run_lock; refresh_status; emit_state ;;
    import)
      local file=''
      while (($#)); do case "$1" in --file) file=${2:-}; shift 2 ;; --avatar-mode) AVATAR_MODE=${2:-}; shift 2 ;; *) die "unknown import option: $1" ;; esac; done
      [[ -f "$file" ]] || die 'import --file must point to a project JSON'; jq -e 'type=="object" and (.id|type=="string")' "$file" >/dev/null || die 'invalid Video Studio project JSON'
      start_local_service; TOPIC=$(jq -r '.topic // "Imported Video Studio project"' "$file"); DURATION_SECONDS=$(jq -r '.target_duration_seconds // 600' "$file"); init_run; acquire_run_lock
      local_api_request POST '/projects/import' "$(jq -c '{project:.}' "$file")"
      state_mutate '.project_id=$id | .planning_applied=true | .stage="project_imported" | .editor_url=($base+"/?project_id="+$id)' --arg id "$(jq -r '.project.id' <<< "$HTTP_BODY")" --arg base "$SMART_SLIDES_BASE_URL"
      emit_state ;;
    help|-h|--help|'') usage ;;
    *) die "unknown action: $ACTION" ;;
  esac
}

main "$@"
