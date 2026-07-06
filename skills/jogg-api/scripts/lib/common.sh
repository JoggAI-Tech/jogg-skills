#!/usr/bin/env bash
set -euo pipefail

COMMON_DIR=$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
SKILL_ROOT=$(CDPATH= cd -- "$COMMON_DIR/../.." && pwd)
ENV_FILE="$SKILL_ROOT/.env"

RESPONSE_STATUS=""
RESPONSE_BODY=""

load_default_env() {
  [[ -f "$ENV_FILE" ]] || return 0

  while IFS= read -r raw_line || [[ -n "$raw_line" ]]; do
    local line key value existing_value

    line=$(printf '%s' "$raw_line" | sed 's/^[[:space:]]*//; s/[[:space:]]*$//')
    [[ -n "$line" ]] || continue
    case "$line" in
      \#*) continue ;;
      export\ *) line=${line#export } ;;
    esac
    [[ "$line" == *=* ]] || continue

    key=${line%%=*}
    value=${line#*=}
    key=$(printf '%s' "$key" | sed 's/[[:space:]]*$//')
    value=$(printf '%s' "$value" | sed 's/^[[:space:]]*//')

    case "$key" in
      ''|[0-9]*|*[!A-Za-z0-9_]*)
        continue
        ;;
    esac

    existing_value=${!key-}
    if [[ -n "${existing_value:-}" ]]; then
      continue
    fi

    case "$value" in
      \"*\") value=${value#\"}; value=${value%\"} ;;
      \'*\') value=${value#\'}; value=${value%\'} ;;
    esac

    export "$key=$value"
  done < "$ENV_FILE"
}

require_bin() {
  local bin_name=$1
  command -v "$bin_name" >/dev/null 2>&1 || {
    jq -cn --arg error "missing required binary: $bin_name" '{error:$error}' >&2
    exit 1
  }
}

require_env() {
  local var_name=$1
  local value=${!var_name-}
  value=$(printf '%s' "$value" | sed 's/^[[:space:]]*//; s/[[:space:]]*$//')
  if [[ -z "$value" ]]; then
    jq -cn \
      --arg error "missing required configuration: $var_name" \
      --arg missing_key "$var_name" \
      --arg env_file ".env" \
      '{error:$error, missing_key:$missing_key, env_file:$env_file}' >&2
    exit 1
  fi
}

json_error() {
  local message=$1
  local detail=${2:-}
  if [[ -n "$detail" ]]; then
    jq -cn --arg error "$message" --arg detail "$detail" '{error:$error, detail:$detail}' >&2
  else
    jq -cn --arg error "$message" '{error:$error}' >&2
  fi
  exit 1
}

log_progress() {
  printf '[jogg-api] %s\n' "$*" >&2
}

guess_content_type() {
  local file_name=$1
  case "$(printf '%s' "$file_name" | tr '[:upper:]' '[:lower:]')" in
    *.jpg|*.jpeg) printf '%s' 'image/jpeg' ;;
    *.png) printf '%s' 'image/png' ;;
    *.gif) printf '%s' 'image/gif' ;;
    *.webp) printf '%s' 'image/webp' ;;
    *.mp4) printf '%s' 'video/mp4' ;;
    *.mov) printf '%s' 'video/quicktime' ;;
    *.m4v) printf '%s' 'video/x-m4v' ;;
    *.webm) printf '%s' 'video/webm' ;;
    *.mp3) printf '%s' 'audio/mpeg' ;;
    *.wav) printf '%s' 'audio/wav' ;;
    *.m4a) printf '%s' 'audio/mp4' ;;
    *.aac) printf '%s' 'audio/aac' ;;
    *.ogg) printf '%s' 'audio/ogg' ;;
    *.json) printf '%s' 'application/json' ;;
    *) printf '%s' 'application/octet-stream' ;;
  esac
}

resolve_path_template() {
  local template=$1
  local path_json=${2:-{}}
  local resolved=$template
  local placeholder value

  while IFS= read -r placeholder; do
    [[ -n "$placeholder" ]] || continue
    value=$(jq -r --arg key "$placeholder" '.[$key] // empty' <<<"$path_json")
    [[ -n "$value" ]] || json_error "missing path parameter" "$placeholder"
    resolved=${resolved//\{$placeholder\}/$value}
  done < <(grep -o '{[^}][^}]*}' <<<"$template" | tr -d '{}' | sort -u || true)

  printf '%s' "$resolved"
}

api_request_json() {
  local method=$1
  local path=$2
  local body_json=${3:-}
  local query_json=${4:-{}}
  local url="${JOGG_BASE_URL%/}$path"
  local body_file
  body_file=$(mktemp)

  local -a cmd
  cmd=(curl -sS -o "$body_file" -w "%{http_code}" -X "$method" "$url" -H "X-Api-Key: ${JOGG_API_KEY}")

  if [[ -n "${JOGG_API_PLATFORM:-}" ]]; then
    cmd+=(-H "x-api-platform: ${JOGG_API_PLATFORM}")
  fi

  if [[ "$method" == "GET" && -n "${query_json:-}" && "$query_json" != "{}" ]]; then
    cmd=(curl -sS -o "$body_file" -w "%{http_code}" -G "$url" -H "X-Api-Key: ${JOGG_API_KEY}")
    if [[ -n "${JOGG_API_PLATFORM:-}" ]]; then
      cmd+=(-H "x-api-platform: ${JOGG_API_PLATFORM}")
    fi
    while IFS=$'\t' read -r key value; do
      [[ -n "$key" ]] || continue
      cmd+=(--data-urlencode "$key=$value")
    done < <(jq -r 'to_entries[] | select(.value != null) | [.key, (.value|tostring)] | @tsv' <<<"$query_json")
  elif [[ -n "${body_json:-}" ]]; then
    cmd+=(-H "Content-Type: application/json" -d "$body_json")
  fi

  RESPONSE_STATUS=$("${cmd[@]}") || {
    rm -f "$body_file"
    json_error "request failed" "$path"
  }
  RESPONSE_BODY=$(cat "$body_file")
  rm -f "$body_file"
}

api_expect_success() {
  local api_code api_message
  api_code=$(jq -r '.code // empty' <<<"$RESPONSE_BODY")
  if [[ "$api_code" == "0" ]]; then
    return 0
  fi

  api_message=$(jq -r '.msg // .message // "api request failed"' <<<"$RESPONSE_BODY")
  json_error "$api_message" "code=$api_code"
}

put_binary_to_signed_url() {
  local sign_url=$1
  local file_path=$2
  local content_type=$3
  local status

  status=$(curl -sS -o /dev/null -w "%{http_code}" -X PUT "$sign_url" -H "Content-Type: $content_type" --data-binary "@$file_path") || {
    json_error "upload failed" "$file_path"
  }

  case "$status" in
    2*) ;;
    *) json_error "upload failed with status $status" "$file_path" ;;
  esac
}

upload_local_asset() {
  local file_path=$1
  local content_type=${2:-}
  local filename=${3:-}
  local body_json sign_url asset_url file_size

  [[ -f "$file_path" ]] || json_error "file does not exist" "$file_path"
  [[ -n "$content_type" ]] || content_type=$(guess_content_type "$file_path")
  [[ -n "$filename" ]] || filename=$(basename "$file_path")
  file_size=$(wc -c < "$file_path" | tr -d ' ')

  body_json=$(jq -cn \
    --arg filename "$filename" \
    --arg content_type "$content_type" \
    --argjson file_size "$file_size" \
    '{filename:$filename, content_type:$content_type, file_size:$file_size}')

  log_progress "requesting signed upload url for $filename"
  api_request_json "POST" "/v2/upload/asset" "$body_json" "{}"
  api_expect_success

  sign_url=$(jq -r '.data.sign_url // empty' <<<"$RESPONSE_BODY")
  asset_url=$(jq -r '.data.asset_url // empty' <<<"$RESPONSE_BODY")
  [[ -n "$sign_url" && -n "$asset_url" ]] || json_error "upload signing response missing urls" "$filename"

  log_progress "uploading binary for $filename"
  put_binary_to_signed_url "$sign_url" "$file_path" "$content_type"

  jq -cn \
    --arg file_path "$file_path" \
    --arg filename "$filename" \
    --arg content_type "$content_type" \
    --arg sign_url "$sign_url" \
    --arg asset_url "$asset_url" \
    '{
      file_path: $file_path,
      filename: $filename,
      content_type: $content_type,
      sign_url: $sign_url,
      asset_url: $asset_url
    }'
}

normalize_remote_or_local_asset() {
  local input_value=$1
  local content_type=${2:-}
  if [[ "$input_value" =~ ^https?:// ]]; then
    jq -cn --arg asset_url "$input_value" '{asset_url:$asset_url, uploaded:false}'
    return 0
  fi

  local upload_json
  upload_json=$(upload_local_asset "$input_value" "$content_type")
  jq -c '. + {uploaded:true}' <<<"$upload_json"
}
