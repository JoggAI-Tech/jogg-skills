#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
source "$SCRIPT_DIR/lib/common.sh"

load_default_env
require_bin curl
require_bin jq
require_env JOGG_API_KEY

: "${JOGG_BASE_URL:=https://api.jogg.ai}"
: "${JOGG_API_PLATFORM:=openclaw}"
: "${JOGG_API_DEFAULT_POLL_INTERVAL_SECONDS:=15}"
: "${JOGG_API_DEFAULT_MAX_WAIT_SECONDS:=1800}"
: "${JOGG_API_DEFAULT_MAX_POLL_ATTEMPTS:=90}"

OP=""
WORKFLOW=""
BODY_JSON=""
BODY_FILE=""
QUERY_JSON="{}"
PATH_JSON="{}"
POLL_MODE="auto"
POLL_INTERVAL_SECONDS="${JOGG_API_DEFAULT_POLL_INTERVAL_SECONDS}"
MAX_WAIT_SECONDS="${JOGG_API_DEFAULT_MAX_WAIT_SECONDS}"
MAX_POLL_ATTEMPTS="${JOGG_API_DEFAULT_MAX_POLL_ATTEMPTS}"

print_help() {
  cat <<'EOF'
usage:
  jogg-v2.sh --list-ops
  jogg-v2.sh --list-workflows
  jogg-v2.sh --op <operation> [--body-json JSON | --body-file FILE] [--query-json JSON] [--path-json JSON] [--poll]
  jogg-v2.sh --workflow <workflow> [--body-json JSON | --body-file FILE] [--poll | --no-poll]

examples:
  jogg-v2.sh --op voices-list --query-json '{"language":"en-US"}'
  jogg-v2.sh --op avatar-video-get --path-json '{"id":"video_123"}' --poll
  jogg-v2.sh --workflow ai-scripts --body-json '{"language":"english","video_length_seconds":"30","script_style":"Storytime","product_info":{"source_type":"details","data":{"name":"Bottle","description":"Insulated bottle"}}}'
  jogg-v2.sh --workflow upload-media --body-json '{"file_path":"/tmp/demo.mp3"}'
EOF
}

list_ops() {
  cat <<'EOF'
ai-scripts-create
ai-scripts-result-get
avatar-video-create
avatar-video-get
avatars-custom-list
avatars-photo-list
avatars-product-list
avatars-public-list
asset-upload-sign
music-list
photo-avatar-generate
photo-avatar-motion-add
photo-avatar-motion-get
photo-avatar-status-get
product-avatar-image-generate
product-avatar-image-status-get
product-avatar-motion-add
product-avatar-motion-get
product-create
product-previews-list
product-update
product-video-create
product-video-get
product-video-preview-render
product-video-preview-submit
product-videos-list
template-custom-get
template-video-create
template-video-get
template-videos-list
templates-custom-list
templates-list
user-quota-get
user-whoami
video-translate-create
video-translate-get
video-translate-target-languages-list
visual-styles-list
voices-custom-list
voices-list
webhook-endpoint-create
webhook-endpoint-delete
webhook-endpoint-update
webhook-endpoints-list
webhook-events-list
EOF
}

list_workflows() {
  cat <<'EOF'
ai-scripts
avatar-video
avatar-video-transparent
avatar-video-with-custom-audio
avatar-video-with-photo-avatar
create-photo-avatar
create-template-video
get-result
photo-avatar-motion
product-avatar
upload-media
url-to-video
video-translation
webhook-integration
EOF
}

normalize_positive_int() {
  local raw_value=$1
  local label=$2
  [[ "$raw_value" =~ ^[0-9]+$ ]] || json_error "$label must be a positive integer" "$raw_value"
  (( raw_value > 0 )) || json_error "$label must be greater than 0" "$raw_value"
}

normalize_poll_settings() {
  normalize_positive_int "$POLL_INTERVAL_SECONDS" "--poll-interval-seconds"
  normalize_positive_int "$MAX_WAIT_SECONDS" "--max-wait-seconds"
  normalize_positive_int "$MAX_POLL_ATTEMPTS" "--max-poll-attempts"

  if (( POLL_INTERVAL_SECONDS < 10 )); then
    log_progress "poll interval ${POLL_INTERVAL_SECONDS}s is too aggressive, clamping to 10s"
    POLL_INTERVAL_SECONDS=10
  fi
}

load_body_json() {
  if [[ -n "$BODY_JSON" && -n "$BODY_FILE" ]]; then
    json_error "use either --body-json or --body-file"
  fi

  if [[ -n "$BODY_FILE" ]]; then
    [[ -f "$BODY_FILE" ]] || json_error "body file does not exist" "$BODY_FILE"
    BODY_JSON=$(cat "$BODY_FILE")
  fi

  if [[ -n "$BODY_JSON" ]]; then
    jq -ce . >/dev/null <<<"$BODY_JSON" || json_error "body json is invalid"
  fi
  jq -ce . >/dev/null <<<"$QUERY_JSON" || json_error "query json is invalid"
  jq -ce . >/dev/null <<<"$PATH_JSON" || json_error "path json is invalid"
}

endpoint_config() {
  local op_name=$1
  METHOD=""
  PATH_TEMPLATE=""
  POLLABLE="false"
  STATUS_FILTER=""

  case "$op_name" in
    ai-scripts-create) METHOD="POST"; PATH_TEMPLATE="/v2/ai_scripts" ;;
    ai-scripts-result-get) METHOD="GET"; PATH_TEMPLATE="/v2/ai_scripts/results/{task_id}"; POLLABLE="true"; STATUS_FILTER='.data.status // empty' ;;
    avatar-video-create) METHOD="POST"; PATH_TEMPLATE="/v2/create_video_from_avatar" ;;
    avatar-video-get) METHOD="GET"; PATH_TEMPLATE="/v2/avatar_video/{id}"; POLLABLE="true"; STATUS_FILTER='.data.status // empty' ;;
    avatars-custom-list) METHOD="GET"; PATH_TEMPLATE="/v2/avatars/custom" ;;
    avatars-photo-list) METHOD="GET"; PATH_TEMPLATE="/v2/avatars/photo_avatars" ;;
    avatars-product-list) METHOD="GET"; PATH_TEMPLATE="/v2/avatars/product_avatars" ;;
    avatars-public-list) METHOD="GET"; PATH_TEMPLATE="/v2/avatars/public" ;;
    asset-upload-sign) METHOD="POST"; PATH_TEMPLATE="/v2/upload/asset" ;;
    music-list) METHOD="GET"; PATH_TEMPLATE="/v2/musics" ;;
    photo-avatar-generate) METHOD="POST"; PATH_TEMPLATE="/v2/photo_avatar/photo/generate" ;;
    photo-avatar-motion-add) METHOD="POST"; PATH_TEMPLATE="/v2/photo_avatar/add_motion" ;;
    photo-avatar-motion-get) METHOD="GET"; PATH_TEMPLATE="/v2/photo_avatar"; POLLABLE="true"; STATUS_FILTER='.data.status // empty' ;;
    photo-avatar-status-get) METHOD="GET"; PATH_TEMPLATE="/v2/photo_avatar/photo"; POLLABLE="true"; STATUS_FILTER='.data.status // empty' ;;
    product-avatar-image-generate) METHOD="POST"; PATH_TEMPLATE="/v2/product_avatar/generation" ;;
    product-avatar-image-status-get) METHOD="GET"; PATH_TEMPLATE="/v2/product_avatar/generation/{batch_id}"; POLLABLE="true"; STATUS_FILTER='if ((.data.summary.pending // 0) + (.data.summary.processing // 0)) > 0 then "processing" elif (.data.summary.completed // 0) > 0 then "completed" elif (.data.summary.failed // 0) > 0 then "failed" else "unknown" end' ;;
    product-avatar-motion-add) METHOD="POST"; PATH_TEMPLATE="/v2/product_avatar/add_motion" ;;
    product-avatar-motion-get) METHOD="GET"; PATH_TEMPLATE="/v2/product_avatar"; POLLABLE="true"; STATUS_FILTER='.data.status // empty' ;;
    product-create) METHOD="POST"; PATH_TEMPLATE="/v2/product" ;;
    product-previews-list) METHOD="GET"; PATH_TEMPLATE="/v2/product_previews" ;;
    product-update) METHOD="PUT"; PATH_TEMPLATE="/v2/product" ;;
    product-video-create) METHOD="POST"; PATH_TEMPLATE="/v2/create_video_from_product" ;;
    product-video-get) METHOD="GET"; PATH_TEMPLATE="/v2/product_video/{product_video_id}"; POLLABLE="true"; STATUS_FILTER='.data.status // empty' ;;
    product-video-preview-render) METHOD="POST"; PATH_TEMPLATE="/v2/create_video_from_product/render_single_preview" ;;
    product-video-preview-submit) METHOD="POST"; PATH_TEMPLATE="/v2/create_video_from_product/preview_list" ;;
    product-videos-list) METHOD="GET"; PATH_TEMPLATE="/v2/product_videos" ;;
    template-custom-get) METHOD="GET"; PATH_TEMPLATE="/v2/template/custom/{id}" ;;
    template-video-create) METHOD="POST"; PATH_TEMPLATE="/v2/create_video_with_template" ;;
    template-video-get) METHOD="GET"; PATH_TEMPLATE="/v2/template_video/{video_id}"; POLLABLE="true"; STATUS_FILTER='.data.status // empty' ;;
    template-videos-list) METHOD="GET"; PATH_TEMPLATE="/v2/template_videos" ;;
    templates-custom-list) METHOD="GET"; PATH_TEMPLATE="/v2/templates/custom" ;;
    templates-list) METHOD="GET"; PATH_TEMPLATE="/v2/templates" ;;
    user-quota-get) METHOD="GET"; PATH_TEMPLATE="/v2/user/remaining_quota" ;;
    user-whoami) METHOD="GET"; PATH_TEMPLATE="/v2/user/whoami" ;;
    video-translate-create) METHOD="POST"; PATH_TEMPLATE="/v2/video_translate/" ;;
    video-translate-get) METHOD="GET"; PATH_TEMPLATE="/v2/video_translate/{video_translate_id}"; POLLABLE="true"; STATUS_FILTER='.data.status // empty' ;;
    video-translate-target-languages-list) METHOD="GET"; PATH_TEMPLATE="/v2/video_translate/target_languages" ;;
    visual-styles-list) METHOD="GET"; PATH_TEMPLATE="/v2/visual_styles" ;;
    voices-custom-list) METHOD="GET"; PATH_TEMPLATE="/v2/voices/custom" ;;
    voices-list) METHOD="GET"; PATH_TEMPLATE="/v2/voices" ;;
    webhook-endpoint-create) METHOD="POST"; PATH_TEMPLATE="/v2/endpoint" ;;
    webhook-endpoint-delete) METHOD="DELETE"; PATH_TEMPLATE="/v2/endpoint/{endpoint_id}" ;;
    webhook-endpoint-update) METHOD="PUT"; PATH_TEMPLATE="/v2/endpoint/{endpoint_id}" ;;
    webhook-endpoints-list) METHOD="GET"; PATH_TEMPLATE="/v2/endpoints" ;;
    webhook-events-list) METHOD="GET"; PATH_TEMPLATE="/v2/events" ;;
    *) json_error "unknown operation" "$op_name" ;;
  esac
}

status_is_terminal() {
  local status_value
  status_value=$(printf '%s' "$1" | tr '[:upper:]' '[:lower:]')
  case "$status_value" in
    success|succeeded|completed|failed|error|cancelled|canceled)
      return 0
      ;;
    *)
      return 1
      ;;
  esac
}

poll_existing_endpoint() {
  local op_name=$1
  local path=$2
  local query_json=$3
  local status_filter=$4
  local attempts=0
  local started_at now elapsed status

  started_at=$(date +%s)
  while :; do
    attempts=$((attempts + 1))
    api_request_json "$METHOD" "$path" "" "$query_json"
    api_expect_success
    status=$(jq -r "$status_filter" <<<"$RESPONSE_BODY" | tr '[:upper:]' '[:lower:]')
    now=$(date +%s)
    elapsed=$((now - started_at))
    log_progress "poll $attempts for $op_name -> status=${status:-unknown}"

    if [[ -n "$status" ]] && status_is_terminal "$status"; then
      jq -c \
        --arg op "$op_name" \
        --arg method "$METHOD" \
        --arg path "$path" \
        --arg status "$status" \
        --argjson poll_attempts "$attempts" \
        --argjson poll_elapsed_seconds "$elapsed" \
        '. + {op:$op, method:$method, path:$path, poll_attempts:$poll_attempts, poll_elapsed_seconds:$poll_elapsed_seconds, last_status:$status}' <<<"$RESPONSE_BODY"
      return 0
    fi

    if (( attempts >= MAX_POLL_ATTEMPTS || elapsed >= MAX_WAIT_SECONDS )); then
      jq -c \
        --arg op "$op_name" \
        --arg method "$METHOD" \
        --arg path "$path" \
        --arg status "${status:-unknown}" \
        --argjson poll_attempts "$attempts" \
        --argjson poll_elapsed_seconds "$elapsed" \
        '. + {op:$op, method:$method, path:$path, poll_attempts:$poll_attempts, poll_elapsed_seconds:$poll_elapsed_seconds, poll_timeout:true, last_status:$status}' <<<"$RESPONSE_BODY"
      return 0
    fi

    sleep "$POLL_INTERVAL_SECONDS"
  done
}

perform_operation() {
  local op_name=$1
  local should_poll=${2:-false}
  local resolved_path

  endpoint_config "$op_name"
  resolved_path=$(resolve_path_template "$PATH_TEMPLATE" "$PATH_JSON")
  api_request_json "$METHOD" "$resolved_path" "$BODY_JSON" "$QUERY_JSON"
  api_expect_success

  if [[ "$should_poll" == "true" ]]; then
    [[ "$POLLABLE" == "true" ]] || json_error "operation does not support polling" "$op_name"
    poll_existing_endpoint "$op_name" "$resolved_path" "$QUERY_JSON" "$STATUS_FILTER"
    return 0
  fi

  jq -c --arg op "$op_name" --arg method "$METHOD" --arg path "$resolved_path" '. + {op:$op, method:$method, path:$path}' <<<"$RESPONSE_BODY"
}

json_get_required() {
  local json_input=$1
  local jq_filter=$2
  local label=$3
  local value
  value=$(jq -r "$jq_filter // empty" <<<"$json_input")
  [[ -n "$value" && "$value" != "null" ]] || json_error "missing required field" "$label"
  printf '%s' "$value"
}

json_get_optional() {
  local json_input=$1
  local jq_filter=$2
  jq -r "$jq_filter // empty" <<<"$json_input"
}

normalize_avatar_audio_body() {
  local json_input=$1
  local audio_path audio_json audio_url

  audio_path=$(json_get_optional "$json_input" '.voice.audio_path')
  if [[ -n "$audio_path" ]]; then
    audio_json=$(normalize_remote_or_local_asset "$audio_path")
    audio_url=$(jq -r '.asset_url' <<<"$audio_json")
    json_input=$(jq --arg audio_url "$audio_url" 'del(.voice.audio_path) | .voice.audio_url = $audio_url' <<<"$json_input")
  fi

  printf '%s' "$json_input"
}

normalize_template_variable_assets() {
  local json_input=$1
  local count i local_path upload_json asset_url

  count=$(jq '.variables | length // 0' <<<"$json_input")
  for ((i = 0; i < count; i++)); do
    local_path=$(jq -r ".variables[$i].properties.local_path // empty" <<<"$json_input")
    [[ -n "$local_path" ]] || continue
    upload_json=$(normalize_remote_or_local_asset "$local_path")
    asset_url=$(jq -r '.asset_url' <<<"$upload_json")
    json_input=$(jq --argjson idx "$i" --arg url "$asset_url" '.variables[$idx].properties.url = $url | del(.variables[$idx].properties.local_path)' <<<"$json_input")
  done

  printf '%s' "$json_input"
}

normalize_product_media_assets() {
  local json_input=$1
  local count i local_path upload_json asset_url

  count=$(jq '.media | length // 0' <<<"$json_input")
  for ((i = 0; i < count; i++)); do
    local_path=$(jq -r ".media[$i].local_path // empty" <<<"$json_input")
    [[ -n "$local_path" ]] || continue
    upload_json=$(normalize_remote_or_local_asset "$local_path")
    asset_url=$(jq -r '.asset_url' <<<"$upload_json")
    json_input=$(jq --argjson idx "$i" --arg url "$asset_url" '.media[$idx].url = $url | del(.media[$idx].local_path)' <<<"$json_input")
  done

  printf '%s' "$json_input"
}

run_workflow_upload_media() {
  local file_path content_type result_json
  file_path=$(json_get_required "$BODY_JSON" '.file_path' 'file_path')
  content_type=$(json_get_optional "$BODY_JSON" '.content_type')
  result_json=$(upload_local_asset "$file_path" "$content_type")
  jq -c --arg workflow "upload-media" '{workflow:$workflow, uploaded:true, result:.}' <<<"$result_json"
}

run_workflow_ai_scripts() {
  local submit_json task_id result_json
  submit_json=$(perform_operation "ai-scripts-create" "false")
  task_id=$(json_get_required "$submit_json" '.data.task_id' 'task_id')

  if [[ "$POLL_MODE" == "false" ]]; then
    jq -c --arg workflow "ai-scripts" '{workflow:$workflow, submit:.}' <<<"$submit_json"
    return 0
  fi

  PATH_JSON=$(jq -cn --arg task_id "$task_id" '{task_id:$task_id}')
  QUERY_JSON="{}"
  BODY_JSON=""
  result_json=$(perform_operation "ai-scripts-result-get" "true")
  jq -c --arg workflow "ai-scripts" --arg task_id "$task_id" '{workflow:$workflow, task_id:$task_id, result:.}' <<<"$result_json"
}

run_workflow_create_photo_avatar() {
  local working_json image_path upload_json image_url submit_json photo_id result_json
  working_json=$BODY_JSON
  image_path=$(json_get_optional "$working_json" '.image_path')
  if [[ -n "$image_path" ]]; then
    upload_json=$(normalize_remote_or_local_asset "$image_path")
    image_url=$(jq -r '.asset_url' <<<"$upload_json")
    working_json=$(jq --arg image_url "$image_url" 'del(.image_path) | .image_url = $image_url' <<<"$working_json")
  fi

  BODY_JSON=$working_json
  submit_json=$(perform_operation "photo-avatar-generate" "false")
  photo_id=$(json_get_required "$submit_json" '.data.photo_id' 'photo_id')

  if [[ "$POLL_MODE" == "false" ]]; then
    jq -c --arg workflow "create-photo-avatar" '{workflow:$workflow, submit:.}' <<<"$submit_json"
    return 0
  fi

  BODY_JSON=""
  QUERY_JSON=$(jq -cn --arg photo_id "$photo_id" '{photo_id:$photo_id}')
  PATH_JSON="{}"
  result_json=$(perform_operation "photo-avatar-status-get" "true")
  jq -c --arg workflow "create-photo-avatar" --arg photo_id "$photo_id" '{workflow:$workflow, photo_id:$photo_id, result:.}' <<<"$result_json"
}

run_workflow_photo_avatar_motion() {
  local working_json image_url photo_id photo_status_json submit_json motion_id result_json
  working_json=$BODY_JSON
  image_url=$(json_get_optional "$working_json" '.image_url')
  photo_id=$(json_get_optional "$working_json" '.photo_id')

  if [[ -z "$image_url" && -n "$photo_id" ]]; then
    BODY_JSON=""
    QUERY_JSON=$(jq -cn --arg photo_id "$photo_id" '{photo_id:$photo_id}')
    PATH_JSON="{}"
    photo_status_json=$(perform_operation "photo-avatar-status-get" "true")
    image_url=$(jq -r '.data.image_url_list[0] // .result.data.image_url_list[0] // empty' <<<"$photo_status_json")
    [[ -n "$image_url" ]] || json_error "photo avatar image url not found after polling" "$photo_id"
    working_json=$(jq --arg image_url "$image_url" '.image_url = $image_url' <<<"$working_json")
  fi

  BODY_JSON=$working_json
  QUERY_JSON="{}"
  submit_json=$(perform_operation "photo-avatar-motion-add" "false")
  motion_id=$(json_get_required "$submit_json" '.data.motion_id' 'motion_id')

  if [[ "$POLL_MODE" == "false" ]]; then
    jq -c --arg workflow "photo-avatar-motion" '{workflow:$workflow, submit:.}' <<<"$submit_json"
    return 0
  fi

  BODY_JSON=""
  QUERY_JSON=$(jq -cn --arg motion_id "$motion_id" '{motion_id:$motion_id}')
  result_json=$(perform_operation "photo-avatar-motion-get" "true")
  jq -c --arg workflow "photo-avatar-motion" --arg motion_id "$motion_id" '{workflow:$workflow, motion_id:$motion_id, result:.}' <<<"$result_json"
}

run_workflow_avatar_video() {
  local working_json submit_json video_id result_json
  working_json=$(normalize_avatar_audio_body "$BODY_JSON")
  BODY_JSON=$working_json
  QUERY_JSON="{}"
  PATH_JSON="{}"

  submit_json=$(perform_operation "avatar-video-create" "false")
  video_id=$(json_get_required "$submit_json" '.data.video_id' 'video_id')

  if [[ "$POLL_MODE" == "false" ]]; then
    jq -c --arg workflow "avatar-video" '{workflow:$workflow, submit:.}' <<<"$submit_json"
    return 0
  fi

  BODY_JSON=""
  PATH_JSON=$(jq -cn --arg id "$video_id" '{id:$id}')
  QUERY_JSON="{}"
  result_json=$(perform_operation "avatar-video-get" "true")
  jq -c --arg workflow "avatar-video" --arg video_id "$video_id" '{workflow:$workflow, video_id:$video_id, result:.}' <<<"$result_json"
}

run_workflow_avatar_video_with_photo_avatar() {
  BODY_JSON=$(jq '.avatar.avatar_type = 1' <<<"$BODY_JSON")
  run_workflow_avatar_video
}

run_workflow_avatar_video_with_custom_audio() {
  BODY_JSON=$(jq '.voice.type = "audio"' <<<"$BODY_JSON")
  run_workflow_avatar_video
}

run_workflow_avatar_video_transparent() {
  BODY_JSON=$(jq 'if .screen_style == null then .screen_style = 3 else . end' <<<"$BODY_JSON")
  run_workflow_avatar_video
}

run_workflow_template_video() {
  local working_json submit_json video_id result_json
  working_json=$(normalize_template_variable_assets "$BODY_JSON")
  BODY_JSON=$working_json
  QUERY_JSON="{}"
  PATH_JSON="{}"

  submit_json=$(perform_operation "template-video-create" "false")
  video_id=$(json_get_required "$submit_json" '.data.video_id' 'video_id')

  if [[ "$POLL_MODE" == "false" ]]; then
    jq -c --arg workflow "create-template-video" '{workflow:$workflow, submit:.}' <<<"$submit_json"
    return 0
  fi

  BODY_JSON=""
  PATH_JSON=$(jq -cn --arg video_id "$video_id" '{video_id:$video_id}')
  result_json=$(perform_operation "template-video-get" "true")
  jq -c --arg workflow "create-template-video" --arg video_id "$video_id" '{workflow:$workflow, video_id:$video_id, result:.}' <<<"$result_json"
}

run_workflow_video_translation() {
  local working_json video_path upload_json video_url submit_json task_id result_json
  working_json=$BODY_JSON
  video_path=$(json_get_optional "$working_json" '.video_path')
  if [[ -n "$video_path" ]]; then
    upload_json=$(normalize_remote_or_local_asset "$video_path")
    video_url=$(jq -r '.asset_url' <<<"$upload_json")
    working_json=$(jq --arg video_url "$video_url" 'del(.video_path) | .video_url = $video_url' <<<"$working_json")
  fi

  BODY_JSON=$working_json
  QUERY_JSON="{}"
  PATH_JSON="{}"
  submit_json=$(perform_operation "video-translate-create" "false")
  task_id=$(json_get_required "$submit_json" '.data.video_translate_id' 'video_translate_id')

  if [[ "$POLL_MODE" == "false" ]]; then
    jq -c --arg workflow "video-translation" '{workflow:$workflow, submit:.}' <<<"$submit_json"
    return 0
  fi

  BODY_JSON=""
  PATH_JSON=$(jq -cn --arg video_translate_id "$task_id" '{video_translate_id:$video_translate_id}')
  result_json=$(perform_operation "video-translate-get" "true")
  jq -c --arg workflow "video-translation" --arg video_translate_id "$task_id" '{workflow:$workflow, video_translate_id:$video_translate_id, result:.}' <<<"$result_json"
}

run_workflow_webhook_integration() {
  local action endpoint_id
  action=$(json_get_optional "$BODY_JSON" '.action')
  action=${action:-list}

  case "$action" in
    list)
      BODY_JSON=""
      QUERY_JSON="{}"
      PATH_JSON="{}"
      perform_operation "webhook-endpoints-list" "false"
      ;;
    events)
      BODY_JSON=""
      QUERY_JSON="{}"
      PATH_JSON="{}"
      perform_operation "webhook-events-list" "false"
      ;;
    create)
      BODY_JSON=$(jq 'del(.action)' <<<"$BODY_JSON")
      QUERY_JSON="{}"
      PATH_JSON="{}"
      perform_operation "webhook-endpoint-create" "false"
      ;;
    update)
      endpoint_id=$(json_get_required "$BODY_JSON" '.endpoint_id' 'endpoint_id')
      BODY_JSON=$(jq 'del(.action, .endpoint_id)' <<<"$BODY_JSON")
      PATH_JSON=$(jq -cn --arg endpoint_id "$endpoint_id" '{endpoint_id:$endpoint_id}')
      QUERY_JSON="{}"
      perform_operation "webhook-endpoint-update" "false"
      ;;
    delete)
      endpoint_id=$(json_get_required "$BODY_JSON" '.endpoint_id' 'endpoint_id')
      BODY_JSON=""
      PATH_JSON=$(jq -cn --arg endpoint_id "$endpoint_id" '{endpoint_id:$endpoint_id}')
      QUERY_JSON="{}"
      perform_operation "webhook-endpoint-delete" "false"
      ;;
    *)
      json_error "unsupported webhook action" "$action"
      ;;
  esac
}

run_workflow_get_result() {
  local kind lookup_json should_poll
  lookup_json=$BODY_JSON
  kind=$(json_get_required "$lookup_json" '.kind' 'kind')
  BODY_JSON=""
  QUERY_JSON="{}"
  should_poll="true"
  if [[ "$POLL_MODE" == "false" ]]; then
    should_poll="false"
  fi

  case "$kind" in
    ai-scripts)
      PATH_JSON=$(jq -cn --arg task_id "$(json_get_required "$lookup_json" '.task_id' 'task_id')" '{task_id:$task_id}')
      perform_operation "ai-scripts-result-get" "$should_poll"
      ;;
    avatar-video)
      PATH_JSON=$(jq -cn --arg id "$(json_get_required "$lookup_json" '.video_id' 'video_id')" '{id:$id}')
      perform_operation "avatar-video-get" "$should_poll"
      ;;
    photo-avatar)
      QUERY_JSON=$(jq -cn --arg photo_id "$(json_get_required "$lookup_json" '.photo_id' 'photo_id')" '{photo_id:$photo_id}')
      PATH_JSON="{}"
      perform_operation "photo-avatar-status-get" "$should_poll"
      ;;
    photo-avatar-motion)
      QUERY_JSON=$(jq -cn --arg motion_id "$(json_get_required "$lookup_json" '.motion_id' 'motion_id')" '{motion_id:$motion_id}')
      PATH_JSON="{}"
      perform_operation "photo-avatar-motion-get" "$should_poll"
      ;;
    product-avatar-image)
      PATH_JSON=$(jq -cn --arg batch_id "$(json_get_required "$lookup_json" '.batch_id' 'batch_id')" '{batch_id:$batch_id}')
      perform_operation "product-avatar-image-status-get" "$should_poll"
      ;;
    product-avatar-motion)
      QUERY_JSON=$(jq -cn --arg motion_id "$(json_get_required "$lookup_json" '.motion_id' 'motion_id')" '{motion_id:$motion_id}')
      PATH_JSON="{}"
      perform_operation "product-avatar-motion-get" "$should_poll"
      ;;
    product-video)
      PATH_JSON=$(jq -cn --arg product_video_id "$(json_get_required "$lookup_json" '.product_video_id' 'product_video_id')" '{product_video_id:$product_video_id}')
      perform_operation "product-video-get" "$should_poll"
      ;;
    template-video)
      PATH_JSON=$(jq -cn --arg video_id "$(json_get_required "$lookup_json" '.video_id' 'video_id')" '{video_id:$video_id}')
      perform_operation "template-video-get" "$should_poll"
      ;;
    video-translation)
      PATH_JSON=$(jq -cn --arg video_translate_id "$(json_get_required "$lookup_json" '.video_translate_id' 'video_translate_id')" '{video_translate_id:$video_translate_id}')
      perform_operation "video-translate-get" "$should_poll"
      ;;
    *)
      json_error "unsupported get-result kind" "$kind"
      ;;
  esac
}

run_workflow_url_to_video() {
  local workflow_json product_json product_update_json create_json preview_json render_mode preview_index create_response product_id product_submit_json update_response preview_submit_json preview_id render_response video_id result_json
  workflow_json=$BODY_JSON
  product_json=$(jq -c '.product // {}' <<<"$workflow_json")
  product_update_json=$(jq -c '.product_update // {}' <<<"$workflow_json")
  render_mode=$(jq -r '.render_mode // "direct"' <<<"$workflow_json")
  preview_index=$(jq -r '.preview_index // "0"' <<<"$workflow_json")

  product_json=$(normalize_product_media_assets "$product_json")
  BODY_JSON=$product_json
  QUERY_JSON="{}"
  PATH_JSON="{}"
  product_submit_json=$(perform_operation "product-create" "false")
  product_id=$(json_get_required "$product_submit_json" '.data.product_id // .data.id' 'product_id')

  if [[ "$product_update_json" != "{}" ]]; then
    BODY_JSON=$(jq --arg product_id "$product_id" '. + {product_id:$product_id}' <<<"$product_update_json")
    perform_operation "product-update" "false" >/dev/null
  fi

  if [[ "$render_mode" == "preview" ]]; then
    preview_json=$(jq -c '.preview_request // {}' <<<"$workflow_json")
    BODY_JSON=$(jq --arg product_id "$product_id" '. + {product_id:$product_id}' <<<"$preview_json")
    preview_submit_json=$(perform_operation "product-video-preview-submit" "false")
    preview_id=$(jq -r --argjson idx "$preview_index" '.data.previews[$idx].preview_id // empty' <<<"$preview_submit_json")
    [[ -n "$preview_id" ]] || json_error "preview_id not found in preview response"
    BODY_JSON=$(jq -cn --arg preview_id "$preview_id" '{preview_id:$preview_id}')
    render_response=$(perform_operation "product-video-preview-render" "false")
    video_id=$(json_get_required "$render_response" '.data.video_id' 'video_id')
    create_response=$(jq -cn --arg preview_id "$preview_id" --argjson preview_submit "$preview_submit_json" --argjson render_submit "$render_response" '{preview_id:$preview_id, preview_submit:$preview_submit, render_submit:$render_submit}')
  else
    create_json=$(jq -c '.create_request // {}' <<<"$workflow_json")
    BODY_JSON=$(jq --arg product_id "$product_id" '. + {product_id:$product_id}' <<<"$create_json")
    render_response=$(perform_operation "product-video-create" "false")
    video_id=$(json_get_required "$render_response" '.data.video_id' 'video_id')
    create_response=$render_response
  fi

  if [[ "$POLL_MODE" == "false" ]]; then
    jq -c \
      --arg workflow "url-to-video" \
      --arg product_id "$product_id" \
      --arg video_id "$video_id" \
      --arg render_mode "$render_mode" \
      --argjson product_submit "$product_submit_json" \
      --argjson create_submit "$create_response" \
      '{workflow:$workflow, product_id:$product_id, video_id:$video_id, render_mode:$render_mode, product_submit:$product_submit, create_submit:$create_submit}'
    return 0
  fi

  BODY_JSON=""
  QUERY_JSON="{}"
  PATH_JSON=$(jq -cn --arg product_video_id "$video_id" '{product_video_id:$product_video_id}')
  result_json=$(perform_operation "product-video-get" "true")
  jq -c \
    --arg workflow "url-to-video" \
    --arg product_id "$product_id" \
    --arg video_id "$video_id" \
    --arg render_mode "$render_mode" \
    --argjson product_submit "$product_submit_json" \
    --argjson create_submit "$create_response" \
    --argjson result "$result_json" \
    '{workflow:$workflow, product_id:$product_id, video_id:$video_id, render_mode:$render_mode, product_submit:$product_submit, create_submit:$create_submit, result:$result}'
}

run_workflow_product_avatar() {
  local workflow_json generation_json product_image_path upload_json product_image_url generation_submit_json batch_id generation_status_json generation_id motion_json motion_submit_json motion_id result_json
  workflow_json=$BODY_JSON
  generation_json=$(jq -c '.generation // {}' <<<"$workflow_json")
  product_image_path=$(jq -r '.product_image_path // .generation.product_image_path // empty' <<<"$workflow_json")

  if [[ -n "$product_image_path" ]]; then
    upload_json=$(normalize_remote_or_local_asset "$product_image_path")
    product_image_url=$(jq -r '.asset_url' <<<"$upload_json")
    generation_json=$(jq --arg product_image_url "$product_image_url" 'del(.product_image_path) | .product_image_url = $product_image_url' <<<"$generation_json")
  fi

  BODY_JSON=$generation_json
  QUERY_JSON="{}"
  PATH_JSON="{}"
  generation_submit_json=$(perform_operation "product-avatar-image-generate" "false")
  batch_id=$(json_get_required "$generation_submit_json" '.data.batch_id' 'batch_id')

  BODY_JSON=""
  PATH_JSON=$(jq -cn --arg batch_id "$batch_id" '{batch_id:$batch_id}')
  generation_status_json=$(perform_operation "product-avatar-image-status-get" "true")
  generation_id=$(jq -r '.data.generations[] | select(.status == "completed") | .generation_id' <<<"$generation_status_json" | head -n 1)
  [[ -n "$generation_id" ]] || json_error "no completed generation_id found" "$batch_id"

  motion_json=$(jq -c '.motion // {}' <<<"$workflow_json")
  BODY_JSON=$(jq --arg generation_id "$generation_id" '. + {generation_id:$generation_id}' <<<"$motion_json")
  QUERY_JSON="{}"
  PATH_JSON="{}"
  motion_submit_json=$(perform_operation "product-avatar-motion-add" "false")
  motion_id=$(json_get_required "$motion_submit_json" '.data.motion_id' 'motion_id')

  if [[ "$POLL_MODE" == "false" ]]; then
    jq -c \
      --arg workflow "product-avatar" \
      --arg batch_id "$batch_id" \
      --arg generation_id "$generation_id" \
      --arg motion_id "$motion_id" \
      --argjson generation_submit "$generation_submit_json" \
      --argjson generation_result "$generation_status_json" \
      --argjson motion_submit "$motion_submit_json" \
      '{workflow:$workflow, batch_id:$batch_id, generation_id:$generation_id, motion_id:$motion_id, generation_submit:$generation_submit, generation_result:$generation_result, motion_submit:$motion_submit}'
    return 0
  fi

  BODY_JSON=""
  QUERY_JSON=$(jq -cn --arg motion_id "$motion_id" '{motion_id:$motion_id}')
  PATH_JSON="{}"
  result_json=$(perform_operation "product-avatar-motion-get" "true")
  jq -c \
    --arg workflow "product-avatar" \
    --arg batch_id "$batch_id" \
    --arg generation_id "$generation_id" \
    --arg motion_id "$motion_id" \
    --argjson generation_submit "$generation_submit_json" \
    --argjson generation_result "$generation_status_json" \
    --argjson motion_submit "$motion_submit_json" \
    --argjson result "$result_json" \
    '{workflow:$workflow, batch_id:$batch_id, generation_id:$generation_id, motion_id:$motion_id, generation_submit:$generation_submit, generation_result:$generation_result, motion_submit:$motion_submit, result:$result}'
}

run_workflow() {
  local workflow_name=$1
  case "$workflow_name" in
    ai-scripts) run_workflow_ai_scripts ;;
    avatar-video) run_workflow_avatar_video ;;
    avatar-video-transparent) run_workflow_avatar_video_transparent ;;
    avatar-video-with-custom-audio) run_workflow_avatar_video_with_custom_audio ;;
    avatar-video-with-photo-avatar) run_workflow_avatar_video_with_photo_avatar ;;
    create-photo-avatar) run_workflow_create_photo_avatar ;;
    create-template-video) run_workflow_template_video ;;
    get-result) run_workflow_get_result ;;
    photo-avatar-motion) run_workflow_photo_avatar_motion ;;
    product-avatar) run_workflow_product_avatar ;;
    upload-media) run_workflow_upload_media ;;
    url-to-video) run_workflow_url_to_video ;;
    video-translation) run_workflow_video_translation ;;
    webhook-integration) run_workflow_webhook_integration ;;
    *) json_error "unknown workflow" "$workflow_name" ;;
  esac
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --op)
      OP=$2
      shift 2
      ;;
    --workflow)
      WORKFLOW=$2
      shift 2
      ;;
    --body-json)
      BODY_JSON=$2
      shift 2
      ;;
    --body-file)
      BODY_FILE=$2
      shift 2
      ;;
    --query-json)
      QUERY_JSON=$2
      shift 2
      ;;
    --path-json)
      PATH_JSON=$2
      shift 2
      ;;
    --poll)
      POLL_MODE="true"
      shift
      ;;
    --no-poll)
      POLL_MODE="false"
      shift
      ;;
    --poll-interval-seconds)
      POLL_INTERVAL_SECONDS=$2
      shift 2
      ;;
    --max-wait-seconds)
      MAX_WAIT_SECONDS=$2
      shift 2
      ;;
    --max-poll-attempts)
      MAX_POLL_ATTEMPTS=$2
      shift 2
      ;;
    --list-ops)
      list_ops
      exit 0
      ;;
    --list-workflows)
      list_workflows
      exit 0
      ;;
    -h|--help)
      print_help
      exit 0
      ;;
    *)
      json_error "unknown argument" "$1"
      ;;
  esac
done

load_body_json
normalize_poll_settings

if [[ -n "$OP" && -n "$WORKFLOW" ]]; then
  json_error "choose either --op or --workflow"
fi

if [[ -n "$OP" ]]; then
  should_poll="false"
  if [[ "$POLL_MODE" == "true" ]]; then
    should_poll="true"
  fi
  perform_operation "$OP" "$should_poll"
  exit 0
fi

if [[ -n "$WORKFLOW" ]]; then
  if [[ "$POLL_MODE" == "auto" ]]; then
    POLL_MODE="true"
  fi
  run_workflow "$WORKFLOW"
  exit 0
fi

print_help
exit 1
