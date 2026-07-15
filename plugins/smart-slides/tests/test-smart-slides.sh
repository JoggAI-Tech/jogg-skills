#!/usr/bin/env bash
set -euo pipefail

export PYTHONDONTWRITEBYTECODE=1

PLUGIN_ROOT=$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
RUNNER="$PLUGIN_ROOT/scripts/video-studio.sh"
MOCK="$PLUGIN_ROOT/tests/mock_server.py"
TMP_DIR=$(mktemp -d)
SERVER_PID=""

cleanup() {
  [[ -z "$SERVER_PID" ]] || kill "$SERVER_PID" 2>/dev/null || true
  rm -rf "$TMP_DIR"
}
trap cleanup EXIT

fail() {
  printf 'test failure: %s\n' "$*" >&2
  exit 1
}

start_mock() {
  local avatar_status=$1
  local port_file="$TMP_DIR/port"
  rm -f "$port_file"
  python3 "$MOCK" --port 0 --port-file "$port_file" --request-log "$TMP_DIR/requests.json" --avatar-status "$avatar_status" &
  SERVER_PID=$!
  for _ in $(seq 1 50); do
    [[ -s "$port_file" ]] && break
    sleep 0.1
  done
  [[ -s "$port_file" ]] || fail "mock server did not start"
  local port
  port=$(<"$port_file")
  export JOGG_BASE_URL="http://127.0.0.1:$port"
  export PODCASTOR_BASE_URL="http://127.0.0.1:$port"
}

stop_mock() {
  kill "$SERVER_PID" 2>/dev/null || true
  wait "$SERVER_PID" 2>/dev/null || true
  SERVER_PID=""
}

make_fake_ffmpeg() {
  mkdir -p "$TMP_DIR/bin"
  cat >"$TMP_DIR/bin/ffmpeg" <<'EOF'
#!/usr/bin/env sh
set -eu
input=""
previous=""
output=""
for arg in "$@"; do
  if [ "$previous" = "-i" ]; then input="$arg"; fi
  previous="$arg"
  output="$arg"
done
cp "$input" "$output"
EOF
  chmod +x "$TMP_DIR/bin/ffmpeg"
  export PATH="$TMP_DIR/bin:$PATH"
}

run_happy_path() {
  start_mock completed
  make_fake_ffmpeg
  export VIDEO_STUDIO_STATE_DIR="$TMP_DIR/state-happy"
  export JOGG_WEB_TOKEN="web-token"
  local preflight result run_id created_count resumed_count
  preflight=$(bash "$RUNNER" preflight)
  [[ "$(jq -r '.status' <<<"$preflight")" == "ready" ]] || fail "preflight did not report ready"
  result=$(bash "$RUNNER" run --topic "测试主题" --duration-seconds 600 --avatar-mode opening_closing)
  run_id=$(jq -r '.run_id' <<<"$result")
  [[ "$(jq -r '.stage' <<<"$result")" == "completed" ]] || fail "happy path did not complete"
  [[ "$(jq -r '.final_video_url' <<<"$result")" == "/final/video.mp4" ]] || fail "missing final video URL"
  [[ "$(jq -r '.target_duration_seconds' "$VIDEO_STUDIO_STATE_DIR/$run_id/state.json")" == "600" ]] || fail "incorrect duration state"
  [[ "$(jq -r '.avatar_tasks | length' "$VIDEO_STUDIO_STATE_DIR/$run_id/state.json")" == "2" ]] || fail "expected only opening and closing avatars"
  ! rg -q 'web-token|mock-openapi-key' "$VIDEO_STUDIO_STATE_DIR/$run_id/state.json" || fail "sensitive value found in run state"
  jq -e '[.[] | select(.path == "/open/v2/create_video_from_avatar")] | length == 2' "$TMP_DIR/requests.json" >/dev/null || fail "expected two Jogg avatar creates"
  jq -e '[.[] | select(.path == "/api/v1/video-studio/projects/project-1/editor-state" and (.body | contains("\"avatar_enabled\":false")))] | length == 1' "$TMP_DIR/requests.json" >/dev/null || fail "global avatar was not disabled"
  jq -e '[.[] | select(.path == "/api/v1/video-studio/projects/project-1/shots/shot-02/broll-assets")] | length == 1' "$TMP_DIR/requests.json" >/dev/null || fail "middle B-roll was not downloaded"
  created_count=$(jq '[.[] | select(.path == "/open/v2/create_video_from_avatar")] | length' "$TMP_DIR/requests.json")
  bash "$RUNNER" resume --run-id "$run_id" >/dev/null
  resumed_count=$(jq '[.[] | select(.path == "/open/v2/create_video_from_avatar")] | length' "$TMP_DIR/requests.json")
  [[ "$created_count" == "$resumed_count" ]] || fail "resume created a duplicate Jogg task"
  stop_mock
}

run_failure_path() {
  start_mock failed
  make_fake_ffmpeg
  export VIDEO_STUDIO_STATE_DIR="$TMP_DIR/state-failed"
  export JOGG_WEB_TOKEN="web-token"
  local result run_id
  if result=$(bash "$RUNNER" run --topic "失败测试" --duration-seconds 60 --avatar-mode opening 2>/dev/null); then
    fail "failed Jogg avatar task unexpectedly succeeded"
  fi
  run_id=$(jq -r '.run_id' <<<"$result")
  [[ "$(jq -r '.stage' "$VIDEO_STUDIO_STATE_DIR/$run_id/state.json")" == "failed" ]] || fail "failure state was not persisted"
  stop_mock
}

run_timeout_path() {
  start_mock pending
  make_fake_ffmpeg
  export VIDEO_STUDIO_STATE_DIR="$TMP_DIR/state-timeout"
  export JOGG_WEB_TOKEN="web-token"
  export VIDEO_STUDIO_MAX_JOGG_WAIT_SECONDS=0
  local result run_id
  result=$(bash "$RUNNER" run --topic "超时测试" --duration-seconds 60 --avatar-mode opening)
  run_id=$(jq -r '.run_id' <<<"$result")
  [[ "$(jq -r '.stage' <<<"$result")" == "waiting_avatar" ]] || fail "timeout did not produce resumable state"
  [[ "$(jq -r '.avatar_tasks["shot-01"].video_id' "$VIDEO_STUDIO_STATE_DIR/$run_id/state.json")" != "" ]] || fail "timeout state lost Jogg task ID"
  unset VIDEO_STUDIO_MAX_JOGG_WAIT_SECONDS
  stop_mock
}

run_no_avatar_path() {
  start_mock completed
  make_fake_ffmpeg
  export VIDEO_STUDIO_STATE_DIR="$TMP_DIR/state-none"
  export JOGG_WEB_TOKEN="web-token"
  local result
  result=$(bash "$RUNNER" run --topic "无数字人测试" --duration-seconds 60 --avatar-mode none)
  [[ "$(jq -r '.stage' <<<"$result")" == "completed" ]] || fail "no-avatar path did not complete"
  [[ "$(jq -r '.avatar_tasks | length' "$VIDEO_STUDIO_STATE_DIR/$(jq -r '.run_id' <<<"$result")/state.json")" == "0" ]] || fail "no-avatar path created Jogg work"
  jq -e '[.[] | select(.path == "/open/v2/create_video_from_avatar")] | length == 0' "$TMP_DIR/requests.json" >/dev/null || fail "no-avatar path created a Jogg task"
  jq -e '[.[] | select(.path == "/api/v1/video-studio/projects/project-1/editor-state" and (.body | contains("\"avatar_enabled\":false")))] | length == 1' "$TMP_DIR/requests.json" >/dev/null || fail "no-avatar path left the global avatar enabled"
  stop_mock
}

run_happy_path
run_failure_path
run_timeout_path
run_no_avatar_path
printf 'smart-slides mock tests passed\n'
