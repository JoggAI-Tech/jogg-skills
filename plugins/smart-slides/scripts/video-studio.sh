#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
PLUGIN_ROOT=$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)

: "${JOGG_REPO:=/Users/cds-dn-137/Documents/golang/jogg-backend-srv}"
: "${PODCASTOR_REPO:=/Users/cds-dn-137/Documents/golang/operation-Podcastor}"
: "${JOGG_BASE_URL:=http://127.0.0.1:8000}"
: "${PODCASTOR_BASE_URL:=http://127.0.0.1:8001}"
: "${PODCASTOR_PYTHON:=python3}"
: "${VIDEO_STUDIO_STATE_DIR:=$HOME/.codex/video-studio/runs}"
: "${VIDEO_STUDIO_PODCASTOR_POLL_INTERVAL_SECONDS:=10}"
: "${VIDEO_STUDIO_JOGG_POLL_INTERVAL_SECONDS:=10}"
: "${VIDEO_STUDIO_RENDER_POLL_INTERVAL_SECONDS:=15}"
: "${VIDEO_STUDIO_MAX_PLANNING_WAIT_SECONDS:=1800}"
: "${VIDEO_STUDIO_MAX_JOGG_WAIT_SECONDS:=1800}"
: "${VIDEO_STUDIO_MAX_HTML_WAIT_SECONDS:=1800}"
: "${VIDEO_STUDIO_MAX_RENDER_WAIT_SECONDS:=7200}"

ACTION=""
RUN_ID=""
STATE_PATH=""
TOPIC=""
DURATION_SECONDS="600"
AVATAR_MODE="opening_closing"
AVATAR_STYLE="professional"
AVATAR_GENDER="female"
AVATAR_AGE="adult"
JOGG_EFFECTIVE_API_KEY=""
VOICE_ID=""
AVATAR_ID=""
PROJECT_JSON="{}"
HTTP_STATUS=""
HTTP_BODY=""

log() {
  printf '[video-studio] %s\n' "$*" >&2
}

emit_failure() {
  local message=$1
  if [[ -n "$STATE_PATH" && -f "$STATE_PATH" ]]; then
    set_stage "failed" 2>/dev/null || true
  fi
  jq -cn --arg run_id "${RUN_ID:-}" --arg error "$message" \
    '{run_id:$run_id,status:"failed",error:$error}'
}

die() {
  local message=$1
  log "ERROR: $message"
  emit_failure "$message"
  exit 1
}

usage() {
  cat <<'EOF'
usage:
  video-studio.sh preflight
  video-studio.sh run --topic TEXT [--duration-seconds 600] [--avatar-mode MODE]
  video-studio.sh resume --run-id RUN_ID
  video-studio.sh status --run-id RUN_ID

avatar modes: none, opening, opening_closing, all
EOF
}

require_bin() {
  command -v "$1" >/dev/null 2>&1 || die "missing required binary: $1"
}

validate_positive_int() {
  local value=$1
  local label=$2
  [[ "$value" =~ ^[0-9]+$ ]] && (( value > 0 )) || die "$label must be a positive integer"
}

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

http_status() {
  local url=$1
  curl -sS -o /dev/null -w '%{http_code}' --connect-timeout 2 --max-time 5 "$url" 2>/dev/null || true
}

podcastor_ready() {
  local status
  status=$(http_status "$PODCASTOR_BASE_URL/api/v1/video-studio/projects")
  [[ "$status" =~ ^2[0-9][0-9]$ ]]
}

jogg_reachable() {
  local status
  status=$(http_status "$JOGG_BASE_URL/openapi_key")
  [[ "$status" =~ ^[1-5][0-9][0-9]$ ]]
}

base_port() {
  local base_url=$1
  printf '%s' "$base_url" | sed -E 's#^[a-z]+://[^:]+:([0-9]+).*#\1#; t; s#.*#0#'
}

wait_for_service() {
  local label=$1
  local command_name=$2
  local attempts=${3:-30}
  local attempt=0
  while (( attempt < attempts )); do
    if "$command_name"; then
      return 0
    fi
    attempt=$((attempt + 1))
    sleep 1
  done
  die "$label did not become ready"
}

start_jogg_if_needed() {
  jogg_reachable && return 0
  [[ -d "$JOGG_REPO" ]] || die "JOGG_REPO does not exist: $JOGG_REPO"
  [[ "$(base_port "$JOGG_BASE_URL")" == "8000" ]] || die "set JOGG_START_CMD when JOGG_BASE_URL does not use Jogg's default port 8000"
  mkdir -p "$VIDEO_STUDIO_STATE_DIR/logs"
  log "starting local Jogg service"
  if [[ -n "${JOGG_START_CMD:-}" ]]; then
    (cd "$JOGG_REPO" && exec bash -lc "$JOGG_START_CMD") >"$VIDEO_STUDIO_STATE_DIR/logs/jogg.log" 2>&1 &
  else
    (cd "$JOGG_REPO" && exec go run .) >"$VIDEO_STUDIO_STATE_DIR/logs/jogg.log" 2>&1 &
  fi
  wait_for_service "Jogg" jogg_reachable
}

start_podcastor_if_needed() {
  local selected_voice=${1:-}
  podcastor_ready && return 0
  [[ -d "$PODCASTOR_REPO" ]] || die "PODCASTOR_REPO does not exist: $PODCASTOR_REPO"
  [[ "$(base_port "$PODCASTOR_BASE_URL")" == "8001" ]] || die "set PODCASTOR_START_CMD when PODCASTOR_BASE_URL does not use port 8001"
  load_env_file "${PODCASTOR_ENV_FILE:-$PODCASTOR_REPO/.env}"
  mkdir -p "$VIDEO_STUDIO_STATE_DIR/logs"
  log "starting local Podcastor Video Studio service"
  (
    cd "$PODCASTOR_REPO"
    export VIDEO_STUDIO_RENDER_BACKEND="${VIDEO_STUDIO_RENDER_BACKEND:-hermes}"
    [[ -z "$selected_voice" ]] || export VIDEO_STUDIO_HERMES_VOICE_ID="$selected_voice"
    if [[ -n "${PODCASTOR_START_CMD:-}" ]]; then
      exec bash -lc "$PODCASTOR_START_CMD"
    fi
    exec "$PODCASTOR_PYTHON" -m uvicorn backend.main:app --host 127.0.0.1 --port 8001
  ) >"$VIDEO_STUDIO_STATE_DIR/logs/podcastor.log" 2>&1 &
  wait_for_service "Podcastor" podcastor_ready
}

state_mutate() {
  local filter=$1
  shift
  local tmp_path
  tmp_path=$(mktemp "$VIDEO_STUDIO_STATE_DIR/.state.XXXXXX")
  jq "$@" "$filter" "$STATE_PATH" >"$tmp_path"
  mv "$tmp_path" "$STATE_PATH"
}

state_get() {
  local filter=$1
  jq -r "$filter // empty" "$STATE_PATH"
}

set_stage() {
  local stage=$1
  state_mutate '.stage = $stage | .updated_at = $updated_at' \
    --arg stage "$stage" --arg updated_at "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
}

init_run() {
  RUN_ID="vs-$(date -u +%Y%m%d%H%M%S)-$RANDOM"
  mkdir -p "$VIDEO_STUDIO_STATE_DIR/$RUN_ID/work"
  STATE_PATH="$VIDEO_STUDIO_STATE_DIR/$RUN_ID/state.json"
  jq -n \
    --arg run_id "$RUN_ID" \
    --arg topic "$TOPIC" \
    --argjson duration "$DURATION_SECONDS" \
    --arg avatar_mode "$AVATAR_MODE" \
    --arg avatar_style "$AVATAR_STYLE" \
    --arg avatar_gender "$AVATAR_GENDER" \
    --arg avatar_age "$AVATAR_AGE" \
    --arg created_at "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
    '{version:"video_studio_run_v1",run_id:$run_id,topic:$topic,target_duration_seconds:$duration,avatar_mode:$avatar_mode,avatar_profile:{style:$avatar_style,gender:$avatar_gender,age:$avatar_age},stage:"initialized",project_id:"",avatar_shot_ids:[],avatar_tasks:{},broll_shot_ids:[],work_id:"",composition_preview_url:"",final_video_url:"",created_at:$created_at,updated_at:$created_at}' \
    >"$STATE_PATH"
}

load_run() {
  RUN_ID=$1
  STATE_PATH="$VIDEO_STUDIO_STATE_DIR/$RUN_ID/state.json"
  [[ -f "$STATE_PATH" ]] || die "run state not found: $RUN_ID"
  TOPIC=$(state_get '.topic')
  DURATION_SECONDS=$(state_get '.target_duration_seconds')
  AVATAR_MODE=$(state_get '.avatar_mode')
  AVATAR_STYLE=$(state_get '.avatar_profile.style')
  AVATAR_GENDER=$(state_get '.avatar_profile.gender')
  AVATAR_AGE=$(state_get '.avatar_profile.age')
}

emit_state() {
  jq '{run_id,stage,project_id,avatar_shot_ids,avatar_tasks:(.avatar_tasks | with_entries(.value |= {video_id,status,upload_option_id})),broll_shot_ids,composition_preview_url,work_id,final_video_url,updated_at}' "$STATE_PATH"
}

request() {
  local method=$1
  local url=$2
  local body=${3:-}
  shift 3 || true
  local body_file
  body_file=$(mktemp)
  local -a curl_args
  curl_args=(-sS -o "$body_file" -w '%{http_code}' --connect-timeout 10 --max-time 120 -X "$method" "$url")
  while (( $# > 0 )); do
    curl_args+=(-H "$1")
    shift
  done
  [[ -z "$body" ]] || curl_args+=(-H 'Content-Type: application/json' --data "$body")
  if ! HTTP_STATUS=$(curl "${curl_args[@]}"); then
    rm -f "$body_file"
    die "request failed while contacting a local service"
  fi
  HTTP_BODY=$(<"$body_file")
  rm -f "$body_file"
}

require_success_status() {
  [[ "$HTTP_STATUS" =~ ^2[0-9][0-9]$ ]] || die "local service returned HTTP $HTTP_STATUS"
}

podcastor_request() {
  local method=$1
  local route=$2
  local body=${3:-}
  request "$method" "$PODCASTOR_BASE_URL/api/v1/video-studio$route" "$body"
  require_success_status
}

jogg_request() {
  local method=$1
  local route=$2
  local body=${3:-}
  request "$method" "$JOGG_BASE_URL$route" "$body" "X-Api-Key: $JOGG_EFFECTIVE_API_KEY"
  require_success_status
  [[ "$(jq -r '.code // 0' <<<"$HTTP_BODY")" == "0" ]] || die "Jogg OpenAPI request was rejected"
}

resolve_jogg_api_key() {
  [[ -n "$JOGG_EFFECTIVE_API_KEY" ]] && return 0
  if [[ -n "${JOGG_API_KEY:-}" ]]; then
    JOGG_EFFECTIVE_API_KEY=$JOGG_API_KEY
    return 0
  fi
  [[ -n "${JOGG_WEB_TOKEN:-}" ]] || die "set JOGG_WEB_TOKEN or JOGG_API_KEY before creating Jogg avatar video"
  request GET "$JOGG_BASE_URL/openapi_key" "" "Authorization: Bearer $JOGG_WEB_TOKEN"
  require_success_status
  JOGG_EFFECTIVE_API_KEY=$(jq -r '.data.access_key // .access_key // empty' <<<"$HTTP_BODY")
  if [[ -z "$JOGG_EFFECTIVE_API_KEY" ]]; then
    request POST "$JOGG_BASE_URL/openapi_key/generate" "" "Authorization: Bearer $JOGG_WEB_TOKEN"
    require_success_status
    JOGG_EFFECTIVE_API_KEY=$(jq -r '.data.access_key // .access_key // empty' <<<"$HTTP_BODY")
  fi
  [[ -n "$JOGG_EFFECTIVE_API_KEY" ]] || die "local Jogg login did not return an OpenAPI access key"
}

resolve_profile() {
  local stored_voice stored_avatar
  stored_voice=$(state_get '.avatar_profile.voice_id')
  stored_avatar=$(state_get '.avatar_profile.avatar_id')
  if [[ -n "$stored_voice" && -n "$stored_avatar" ]]; then
    VOICE_ID=$stored_voice
    AVATAR_ID=$stored_avatar
    return 0
  fi

  VOICE_ID=${JOGG_DEFAULT_VOICE_ID:-}
  if [[ -z "$VOICE_ID" ]]; then
    jogg_request GET '/open/v2/voices?language=chinese&gender=female&page=1&page_size=20'
    VOICE_ID=$(jq -r '(.data.voices // .voices // []) | map(.voice_id // empty) | map(select(length > 0)) | .[0] // empty' <<<"$HTTP_BODY")
  fi
  [[ -n "$VOICE_ID" ]] || die "Jogg has no available Chinese female voice"

  AVATAR_ID=${JOGG_DEFAULT_AVATAR_ID:-}
  if [[ -z "$AVATAR_ID" ]]; then
    local query avatar_list
    local -a queries=(
      "aspect_ratio=landscape&style=$AVATAR_STYLE&gender=$AVATAR_GENDER&age=$AVATAR_AGE"
      "aspect_ratio=landscape&style=$AVATAR_STYLE&gender=$AVATAR_GENDER"
      "aspect_ratio=landscape&gender=$AVATAR_GENDER"
      'aspect_ratio=landscape'
    )
    for query in "${queries[@]}"; do
      jogg_request GET "/open/v2/avatars/public?$query&page=1&page_size=20"
      avatar_list=$(jq -r '(.data.avatars // .avatars // []) | map(.id // .avatar_id // empty) | map(select(tostring | length > 0)) | .[0] // empty' <<<"$HTTP_BODY")
      if [[ -n "$avatar_list" ]]; then
        AVATAR_ID=$avatar_list
        break
      fi
    done
  fi
  [[ "$AVATAR_ID" =~ ^[0-9]+$ ]] || die "Jogg has no public landscape avatar for the requested profile"
  state_mutate '.avatar_profile.voice_id = $voice_id | .avatar_profile.avatar_id = ($avatar_id | tonumber)' \
    --arg voice_id "$VOICE_ID" --arg avatar_id "$AVATAR_ID"
}

fetch_project() {
  local project_id
  project_id=$(state_get '.project_id')
  [[ -n "$project_id" ]] || die "run has no Podcastor project ID"
  podcastor_request GET "/projects/$project_id"
  PROJECT_JSON=$(jq -ce '.project' <<<"$HTTP_BODY") || die "Podcastor returned an invalid project payload"
}

ensure_project() {
  [[ -n "$(state_get '.project_id')" ]] && return 0
  local body project_id
  body=$(jq -cn --arg topic "$TOPIC" --argjson duration "$DURATION_SECONDS" '{topic:$topic,format:"long",production_format:"broll_html",target_duration_seconds:$duration}')
  podcastor_request POST '/projects' "$body"
  project_id=$(jq -r '.project.id // empty' <<<"$HTTP_BODY")
  [[ -n "$project_id" ]] || die "Podcastor did not create a Video Studio project"
  state_mutate '.project_id = $project_id' --arg project_id "$project_id"
  set_stage "project_created"
}

wait_for_project_state() {
  local filter=$1
  local max_seconds=$2
  local pending_stage=$3
  local started_at now elapsed value
  started_at=$(date +%s)
  while :; do
    fetch_project
    value=$(jq -r "$filter // empty" <<<"$PROJECT_JSON")
    case "$value" in
      ready|success|completed|skipped) return 0 ;;
      failed|error) return 2 ;;
    esac
    now=$(date +%s)
    elapsed=$((now - started_at))
    if (( elapsed >= max_seconds )); then
      set_stage "$pending_stage"
      return 124
    fi
    sleep "$VIDEO_STUDIO_PODCASTOR_POLL_INTERVAL_SECONDS"
  done
}

ensure_planning() {
  ensure_project
  fetch_project
  local project_id
  project_id=$(state_get '.project_id')
  if [[ "$(jq -r '.producer_analysis != null' <<<"$PROJECT_JSON")" != "true" ]]; then
    podcastor_request POST "/projects/$project_id/generate-producer-analysis"
  fi
  fetch_project
  if [[ "$(jq -r '.production_requirement_document != null' <<<"$PROJECT_JSON")" != "true" ]]; then
    podcastor_request POST "/projects/$project_id/generate-requirement-document"
  fi
  fetch_project
  if [[ "$(jq -r '.creative_plan != null and .workflow_state.creative_plan.status == "ready"' <<<"$PROJECT_JSON")" != "true" ]]; then
    podcastor_request POST "/projects/$project_id/generate-creative-plan"
    if wait_for_project_state '.workflow_state.creative_plan.status' "$VIDEO_STUDIO_MAX_PLANNING_WAIT_SECONDS" "waiting_creative_plan"; then
      :
    else
      local result=$?
      [[ $result == 124 ]] && return 10
      die "Podcastor creative planning failed"
    fi
  fi
  fetch_project
  if [[ "$(jq -r '.director_document != null' <<<"$PROJECT_JSON")" != "true" ]]; then
    podcastor_request POST "/projects/$project_id/generate-director-document"
  fi
  fetch_project
  if [[ "$(jq -r '(.scene_groups | length) > 0' <<<"$PROJECT_JSON")" != "true" ]]; then
    podcastor_request POST "/projects/$project_id/generate-storyboard"
  fi
  set_stage "storyboard_ready"
}

shots_json() {
  jq -ce '[.scene_groups[]?.shots[]? | {id,narration,duration_seconds}]' <<<"$PROJECT_JSON"
}

ensure_avatar_targets() {
  local current targets shots
  current=$(jq -c '.avatar_shot_ids // []' "$STATE_PATH")
  [[ "$current" != "[]" ]] && return 0
  fetch_project
  shots=$(shots_json)
  [[ "$(jq 'length' <<<"$shots")" -gt 0 ]] || die "Podcastor storyboard has no shots"
  case "$AVATAR_MODE" in
    none) targets='[]' ;;
    opening) targets=$(jq -c '[.[0].id]' <<<"$shots") ;;
    opening_closing)
      targets=$(jq -c 'if length == 1 then [.[0].id] else [.[0].id, .[-1].id] end | unique' <<<"$shots")
      ;;
    all) targets=$(jq -c '[.[].id]' <<<"$shots") ;;
    *) die "unsupported avatar mode: $AVATAR_MODE" ;;
  esac
  state_mutate '.avatar_shot_ids = $targets' --argjson targets "$targets"
}

wait_for_jogg_video() {
  local shot_id=$1
  local video_id=$2
  local started_at now elapsed status video_url
  started_at=$(date +%s)
  while :; do
    jogg_request GET "/open/v2/avatar_video/$video_id"
    status=$(jq -r '.data.status // .status // empty' <<<"$HTTP_BODY" | tr '[:upper:]' '[:lower:]')
    video_url=$(jq -r '.data.video_url // .video_url // empty' <<<"$HTTP_BODY")
    state_mutate '.avatar_tasks[$shot_id].status = $status' --arg shot_id "$shot_id" --arg status "$status"
    case "$status" in
      completed|success|succeeded)
        [[ -n "$video_url" ]] || die "Jogg marked avatar video complete without a video URL"
        JOGG_VIDEO_URL=$video_url
        return 0
        ;;
      failed|error|cancelled|canceled) return 2 ;;
    esac
    now=$(date +%s)
    elapsed=$((now - started_at))
    if (( elapsed >= VIDEO_STUDIO_MAX_JOGG_WAIT_SECONDS )); then
      set_stage "waiting_avatar"
      return 124
    fi
    sleep "$VIDEO_STUDIO_JOGG_POLL_INTERVAL_SECONDS"
  done
}

upload_avatar_asset() {
  local shot_id=$1
  local duration_seconds=$2
  local video_url=$3
  local project_id source_path muted_path body_file status option_id upload_body
  project_id=$(state_get '.project_id')
  source_path="$VIDEO_STUDIO_STATE_DIR/$RUN_ID/work/$shot_id-jogg-source.mp4"
  muted_path="$VIDEO_STUDIO_STATE_DIR/$RUN_ID/work/$shot_id-jogg-muted.mp4"
  log "downloading Jogg avatar asset for $shot_id"
  curl -fsSL --connect-timeout 15 --max-time 600 "$video_url" -o "$source_path" || die "could not download completed Jogg avatar video"
  ffmpeg -y -v error -i "$source_path" -map 0:v:0 -c:v copy -an "$muted_path" || die "could not remove audio from Jogg avatar video"

  body_file=$(mktemp)
  status=$(curl -sS -o "$body_file" -w '%{http_code}' --connect-timeout 15 --max-time 600 \
    -X POST "$PODCASTOR_BASE_URL/api/v1/video-studio/projects/$project_id/shots/$shot_id/materials" \
    -F "title=Jogg avatar $shot_id" \
    -F "duration_seconds=$duration_seconds" \
    -F "file_media=@$muted_path;type=video/mp4") || {
      rm -f "$body_file"
      die "could not upload Jogg avatar asset to Podcastor"
    }
  upload_body=$(<"$body_file")
  rm -f "$body_file"
  [[ "$status" =~ ^2[0-9][0-9]$ ]] || die "Podcastor rejected the Jogg avatar upload"
  option_id=$(jq -r --arg shot_id "$shot_id" '[.project.scene_groups[]?.shots[]? | select(.id == $shot_id) | .broll_options[0].id] | .[0] // empty' <<<"$upload_body")
  [[ -n "$option_id" ]] || die "Podcastor did not return the uploaded Jogg avatar asset"
  state_mutate '.avatar_tasks[$shot_id] += {status:"uploaded",local_path:$local_path,upload_option_id:$option_id}' \
    --arg shot_id "$shot_id" --arg local_path "$muted_path" --arg option_id "$option_id"
}

ensure_avatar_assets() {
  ensure_avatar_targets
  local targets shots shot_id shot duration task video_id narration duration_seconds body result
  targets=$(jq -c '.avatar_shot_ids' "$STATE_PATH")
  if [[ "$targets" == "[]" ]]; then
    fetch_project
    body=$(jq -cn --argjson selected "$(jq -c '.editor_state.selected_broll_by_shot // {}' <<<"$PROJECT_JSON")" '{avatar_enabled:false,selected_broll_by_shot:$selected}')
    podcastor_request PATCH "/projects/$(state_get '.project_id')/editor-state" "$body"
    set_stage "avatar_assets_ready"
    return 0
  fi
  fetch_project
  shots=$(shots_json)
  while IFS= read -r shot_id; do
    [[ -n "$shot_id" ]] || continue
    task=$(jq -c --arg shot_id "$shot_id" '.avatar_tasks[$shot_id] // {}' "$STATE_PATH")
    [[ "$(jq -r '.upload_option_id // empty' <<<"$task")" != "" ]] && continue
    shot=$(jq -c --arg shot_id "$shot_id" '.[] | select(.id == $shot_id)' <<<"$shots")
    [[ -n "$shot" ]] || die "avatar shot no longer exists: $shot_id"
    narration=$(jq -r '.narration' <<<"$shot")
    duration_seconds=$(jq -r '.duration_seconds' <<<"$shot")
    video_id=$(jq -r '.video_id // empty' <<<"$task")
    if [[ -z "$video_id" ]]; then
      body=$(jq -cn --argjson avatar_id "$AVATAR_ID" --arg voice_id "$VOICE_ID" --arg script "$narration" --arg name "$RUN_ID-$shot_id" '{avatar:{avatar_type:0,avatar_id:$avatar_id},voice:{type:"script",voice_id:$voice_id,script:$script},aspect_ratio:"landscape",screen_style:1,caption:false,video_name:$name}')
      jogg_request POST '/open/v2/create_video_from_avatar' "$body"
      video_id=$(jq -r '.data.video_id // .video_id // empty' <<<"$HTTP_BODY")
      [[ -n "$video_id" ]] || die "Jogg did not return an avatar video ID"
      state_mutate '.avatar_tasks[$shot_id] = {video_id:$video_id,status:"pending"}' --arg shot_id "$shot_id" --arg video_id "$video_id"
    fi
    if wait_for_jogg_video "$shot_id" "$video_id"; then
      upload_avatar_asset "$shot_id" "$duration_seconds" "$JOGG_VIDEO_URL"
    else
      result=$?
      [[ $result == 124 ]] && return 10
      die "Jogg avatar generation failed for $shot_id"
    fi
  done < <(jq -r '.[]' <<<"$targets")

  fetch_project
  local selected
  selected=$(jq -c '.editor_state.selected_broll_by_shot // {}' <<<"$PROJECT_JSON")
  while IFS= read -r shot_id; do
    option_id=$(state_get ".avatar_tasks[\"$shot_id\"].upload_option_id")
    selected=$(jq -c --arg shot_id "$shot_id" --arg option_id "$option_id" '.[$shot_id] = $option_id' <<<"$selected")
  done < <(jq -r '.[]' <<<"$targets")
  body=$(jq -cn --argjson selected "$selected" '{avatar_enabled:false,selected_broll_by_shot:$selected}')
  podcastor_request PATCH "/projects/$(state_get '.project_id')/editor-state" "$body"
  set_stage "avatar_assets_ready"
}

ensure_broll() {
  fetch_project
  local shots targets shot_id has_asset project_id
  shots=$(shots_json)
  targets=$(jq -c '.avatar_shot_ids' "$STATE_PATH")
  project_id=$(state_get '.project_id')
  while IFS= read -r shot_id; do
    [[ -n "$shot_id" ]] || continue
    jq -e --arg shot_id "$shot_id" 'index($shot_id) != null' <<<"$targets" >/dev/null && continue
    fetch_project
    has_asset=$(jq -r --arg shot_id "$shot_id" '[.scene_groups[]?.shots[]? | select(.id == $shot_id) | .broll_options[]? | select((.asset_url // "") != "" or (.asset_path // "") != "")] | length > 0' <<<"$PROJECT_JSON")
    if [[ "$has_asset" != "true" ]]; then
      log "downloading B-roll for $shot_id"
      podcastor_request POST "/projects/$project_id/shots/$shot_id/broll-assets"
    fi
  done < <(jq -r '.[].id' <<<"$shots")
  state_mutate '.broll_shot_ids = $shot_ids' --argjson shot_ids "$(jq -c --argjson targets "$targets" '[.[].id] - $targets' <<<"$shots")"
  set_stage "broll_ready"
}

ensure_html_and_preview() {
  local project_id html_state result
  project_id=$(state_get '.project_id')
  fetch_project
  html_state=$(jq -r '.editor_asset_status.html_generation.state // empty' <<<"$PROJECT_JSON")
  if [[ "$html_state" != "ready" && "$html_state" != "skipped" ]]; then
    podcastor_request POST "/projects/$project_id/prepare-editor-assets"
    if wait_for_project_state '.editor_asset_status.html_generation.state' "$VIDEO_STUDIO_MAX_HTML_WAIT_SECONDS" "waiting_html"; then
      :
    else
      result=$?
      [[ $result == 124 ]] && return 10
      die "Podcastor HTML/MG generation failed"
    fi
  fi
  podcastor_request POST "/projects/$project_id/composition-preview"
  local preview_url
  preview_url=$(jq -r '.preview_url // .project.composition_preview_url // empty' <<<"$HTTP_BODY")
  [[ -n "$preview_url" ]] || die "Podcastor did not return a composition preview"
  state_mutate '.composition_preview_url = $preview_url' --arg preview_url "$preview_url"
  set_stage "preview_ready"
}

wait_for_render() {
  local work_id=$1
  local started_at now elapsed status final_url
  started_at=$(date +%s)
  while :; do
    podcastor_request GET "/works/$work_id"
    status=$(jq -r '.work.status // empty' <<<"$HTTP_BODY")
    case "$status" in
      success)
        final_url=$(jq -r '.work.output.url // empty' <<<"$HTTP_BODY")
        [[ -n "$final_url" ]] || die "Hermes marked the work successful without a final MP4 URL"
        state_mutate '.final_video_url = $final_video_url' --arg final_video_url "$final_url"
        return 0
        ;;
      failed|needs_user_decision) return 2 ;;
      waiting_render_worker) return 3 ;;
    esac
    now=$(date +%s)
    elapsed=$((now - started_at))
    if (( elapsed >= VIDEO_STUDIO_MAX_RENDER_WAIT_SECONDS )); then
      set_stage "waiting_render"
      return 124
    fi
    sleep "$VIDEO_STUDIO_RENDER_POLL_INTERVAL_SECONDS"
  done
}

ensure_final_render() {
  local project_id work_id result
  project_id=$(state_get '.project_id')
  work_id=$(state_get '.work_id')
  if [[ -z "$work_id" ]]; then
    podcastor_request POST "/projects/$project_id/works"
    work_id=$(jq -r '.work.id // empty' <<<"$HTTP_BODY")
    [[ -n "$work_id" ]] || die "Podcastor did not create a render work item"
    state_mutate '.work_id = $work_id' --arg work_id "$work_id"
  fi
  if wait_for_render "$work_id"; then
    set_stage "completed"
    return 0
  fi
  result=$?
  case "$result" in
    124) return 10 ;;
    3) die "Hermes render worker is not configured" ;;
    *) die "Hermes render failed or needs user decision" ;;
  esac
}

run_pipeline() {
  validate_positive_int "$DURATION_SECONDS" "--duration-seconds"
  [[ "$AVATAR_MODE" =~ ^(none|opening|opening_closing|all)$ ]] || die "unsupported avatar mode: $AVATAR_MODE"
  start_jogg_if_needed
  resolve_jogg_api_key
  resolve_profile
  start_podcastor_if_needed "$VOICE_ID"
  ensure_planning || return $?
  ensure_avatar_assets || return $?
  ensure_broll || return $?
  ensure_html_and_preview || return $?
  ensure_final_render || return $?
}

parse_run_args() {
  while (( $# > 0 )); do
    case "$1" in
      --topic) TOPIC=${2:-}; shift 2 ;;
      --duration-seconds) DURATION_SECONDS=${2:-}; shift 2 ;;
      --avatar-mode) AVATAR_MODE=${2:-}; shift 2 ;;
      --avatar-style) AVATAR_STYLE=${2:-}; shift 2 ;;
      --avatar-gender) AVATAR_GENDER=${2:-}; shift 2 ;;
      --avatar-age) AVATAR_AGE=${2:-}; shift 2 ;;
      *) die "unknown run option: $1" ;;
    esac
  done
}

parse_run_id() {
  [[ "${1:-}" == "--run-id" && -n "${2:-}" ]] || die "--run-id is required"
  RUN_ID=$2
}

main() {
  ACTION=${1:-}
  shift || true
  require_bin curl
  require_bin jq
  require_bin ffmpeg
  mkdir -p "$VIDEO_STUDIO_STATE_DIR"
  case "$ACTION" in
    preflight)
      (( $# == 0 )) || die "preflight takes no arguments"
      start_jogg_if_needed
      resolve_jogg_api_key
      start_podcastor_if_needed ""
      jq -n --arg jogg "$JOGG_BASE_URL" --arg podcastor "$PODCASTOR_BASE_URL" '{status:"ready",jogg_base_url:$jogg,podcastor_base_url:$podcastor}'
      ;;
    run)
      parse_run_args "$@"
      [[ -n "$TOPIC" ]] || die "--topic is required"
      init_run
      if run_pipeline; then
        emit_state
      else
        local result=$?
        [[ $result == 10 ]] && { emit_state; return 0; }
        return "$result"
      fi
      ;;
    resume)
      parse_run_id "$@"
      load_run "$RUN_ID"
      if run_pipeline; then
        emit_state
      else
        local result=$?
        [[ $result == 10 ]] && { emit_state; return 0; }
        return "$result"
      fi
      ;;
    status)
      parse_run_id "$@"
      load_run "$RUN_ID"
      emit_state
      ;;
    -h|--help|help|'') usage ;;
    *) die "unknown action: $ACTION" ;;
  esac
}

main "$@"
