#!/usr/bin/env bash
set -euo pipefail

export PYTHONDONTWRITEBYTECODE=1
PLUGIN_ROOT=$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
RUNNER="$PLUGIN_ROOT/scripts/smart-slides.sh"
MOCK="$PLUGIN_ROOT/tests/mock_server.py"
TMP_DIR=$(mktemp -d)
SERVER_PID=""

cleanup() { [[ -z "$SERVER_PID" ]] || kill "$SERVER_PID" 2>/dev/null || true; rm -rf "$TMP_DIR"; }
trap cleanup EXIT
fail() { printf 'test failure: %s\n' "$*" >&2; exit 1; }

start_mock() {
  local avatar_status=$1 port_file="$TMP_DIR/port"
  rm -f "$port_file" "$TMP_DIR/requests.json"
  python3 "$MOCK" --port 0 --port-file "$port_file" --request-log "$TMP_DIR/requests.json" --avatar-status "$avatar_status" &
  SERVER_PID=$!
  for _ in $(seq 1 50); do [[ -s "$port_file" ]] && break; sleep 0.1; done
  [[ -s "$port_file" ]] || fail 'mock server did not start'
  local port; port=$(<"$port_file")
  export JOGG_BASE_URL="http://127.0.0.1:$port" SMART_SLIDES_BASE_URL="http://127.0.0.1:$port"
}

stop_mock() { kill "$SERVER_PID" 2>/dev/null || true; wait "$SERVER_PID" 2>/dev/null || true; SERVER_PID=""; }

make_fake_ffmpeg() {
  mkdir -p "$TMP_DIR/bin"
  cat > "$TMP_DIR/bin/ffmpeg" <<'EOF'
#!/usr/bin/env sh
set -eu
input="" previous="" output=""
for arg in "$@"; do [ "$previous" = "-i" ] && input="$arg"; previous="$arg"; output="$arg"; done
cp "$input" "$output"
EOF
  chmod +x "$TMP_DIR/bin/ffmpeg"
  cat > "$TMP_DIR/bin/ffprobe" <<'EOF'
#!/usr/bin/env sh
exit 0
EOF
  chmod +x "$TMP_DIR/bin/ffprobe"
  export PATH="$TMP_DIR/bin:$PATH"
}

configure_paths() {
  local suffix=$1
  export SMART_SLIDES_HOME="$TMP_DIR/home-$suffix"
  export SMART_SLIDES_STATE_DIR="$SMART_SLIDES_HOME/runs"
  export SMART_SLIDES_DATA_DIR="$SMART_SLIDES_HOME/data"
  export JOGG_API_KEY=mock-openapi-key
  unset JOGG_WEB_TOKEN
  export SMART_SLIDES_ALLOW_DETERMINISTIC_FALLBACK=1
}

planning_required_path() {
  start_mock completed; configure_paths planning-required
  unset SMART_SLIDES_ALLOW_DETERMINISTIC_FALLBACK
  local result run_id state plan creates
  result=$(bash "$RUNNER" run --topic '需要 Codex 规划' --duration-seconds 60 --avatar-mode opening)
  run_id=$(jq -r '.run_id' <<< "$result"); state="$SMART_SLIDES_STATE_DIR/$run_id.json"
  [[ "$(jq -r '.stage' <<< "$result")" == blocked_planning ]] || fail 'run without planning was not blocked'
  [[ -z "$(jq -r '.project_id' "$state")" ]] || fail 'blocked planning created a project'
  if [[ -f "$TMP_DIR/requests.json" ]]; then
    creates=$(jq '[.[]|select(.path=="/v2/create_video_from_avatar")]|length' "$TMP_DIR/requests.json")
    [[ "$creates" == 0 ]] || fail 'blocked planning submitted a paid Jogg task'
  fi

  plan="$TMP_DIR/planning.json"
  jq -n '{
    producer_analysis:{summary:"Codex-authored fixture"},
    production_requirement_document:{target_audience:"test"},
    creative_plan:{script:"opening middle ending"},
    script:"opening middle ending",
    director_document:{visual_strategy:"fixture"},
    scene_groups:[{id:"group-1",shots:[
      {id:"shot-01",title:"Opening",narration:"planned opening",duration_seconds:20,broll_options:[]},
      {id:"shot-02",title:"Middle",narration:"planned middle",duration_seconds:20,broll_options:[]},
      {id:"shot-03",title:"Ending",narration:"planned ending",duration_seconds:20,broll_options:[]}
    ]}]
  }' > "$plan"
  result=$(bash "$RUNNER" resume --run-id "$run_id" --planning-file "$plan")
  [[ "$(jq -r '.stage' <<< "$result")" == completed ]] || fail 'resume with planning file did not complete'
  [[ "$(jq -r '.planning_file' "$state")" == "$plan" ]] || fail 'resume did not persist the planning file'
  [[ "$(jq -r '.planning_applied' "$state")" == true ]] || fail 'resume did not apply the planning file'
  jq -e '[.[]|select(.path|endswith("/planning-state"))]|length==1' "$TMP_DIR/requests.json" >/dev/null || fail 'planning file was not sent to the local API'
  jq -e '[.[]|select(.path=="/v2/create_video_from_avatar")|.body|fromjson|select(.voice.script=="planned opening")]|length==1' "$TMP_DIR/requests.json" >/dev/null || fail 'planned narration did not reach Jogg'
  stop_mock
}

happy_path() {
  start_mock completed; configure_paths happy
  local preflight result run_id creates_before creates_after works_before works_after state busy_result busy_status edited_result lock_plan
  preflight=$(bash "$RUNNER" preflight)
  [[ "$(jq -r '.status' <<< "$preflight")" == ready ]] || fail 'preflight failed'
  jq -e '[.[]|select(.path|test("^/openapi_key"))]|length==0' "$TMP_DIR/requests.json" >/dev/null || fail 'public API mode attempted browser-token key exchange'
  result=$(bash "$RUNNER" run --topic '测试主题' --duration-seconds 600 --avatar-mode opening_closing)
  run_id=$(jq -r '.run_id' <<< "$result"); state="$SMART_SLIDES_STATE_DIR/$run_id.json"
  [[ "$(jq -r '.stage' <<< "$result")" == completed ]] || fail 'happy path did not complete'
  [[ "$(jq -r '.target_duration_seconds' "$state")" == 600 ]] || fail 'duration was not preserved'
  jq -e '.jogg_tasks|length==3' "$state" >/dev/null || fail 'every shot must have a Jogg task'
  jq -e '[.jogg_tasks[].audio_path|select(length>0)]|length==3' "$state" >/dev/null || fail 'every shot must have extracted audio'
  jq -e '[.jogg_tasks[].avatar_path|select(length>0)]|length==2' "$state" >/dev/null || fail 'only opening and closing should retain avatar video'
  ! rg -q 'web-token|mock-openapi-key' "$state" || fail 'secret leaked into state'
  jq -e '[.[]|select(.path=="/v2/create_video_from_avatar")]|length==3' "$TMP_DIR/requests.json" >/dev/null || fail 'wrong Jogg create count'
  jq -e '[.[]|select(.path=="/v2/create_video_from_avatar")|.body|fromjson|select(.voice.type=="script")]|length==3' "$TMP_DIR/requests.json" >/dev/null || fail 'Jogg did not use script voice'
  jq -e '[.[]|select(.path|test("tts";"i"))]|length==0' "$TMP_DIR/requests.json" >/dev/null || fail 'standalone TTS was requested'
  jq -e '[.[]|select(.path=="/api/v1/video-studio/projects/project-1/editor-state")|.body|fromjson|select((.voice_assets_by_shot|length)==3 and (.avatar_assets_by_shot|length)==2 and .avatar_enabled==false)]|length==1' "$TMP_DIR/requests.json" >/dev/null || fail 'editor state asset maps are wrong'
  jq -e '[.[]|select(.path=="/api/v1/video-studio/projects/project-1/shots/shot-02/broll-assets")]|length==1' "$TMP_DIR/requests.json" >/dev/null || fail 'middle B-roll was not downloaded'
  jq -e '[.[]|select(.path|test("shots/(shot-01|shot-03)/broll-assets"))]|length==0' "$TMP_DIR/requests.json" >/dev/null || fail 'avatar shots downloaded B-roll'
  creates_before=$(jq '[.[]|select(.path=="/v2/create_video_from_avatar")]|length' "$TMP_DIR/requests.json")
  works_before=$(jq '[.[]|select(.path|endswith("/projects/project-1/works"))]|length' "$TMP_DIR/requests.json")

  lock_plan="$TMP_DIR/locked-plan.json"
  jq -n '{}' > "$lock_plan"
  mkdir "$state.lock"
  printf '%s\n' "$$" > "$state.lock/pid"
  set +e
  busy_result=$(bash "$RUNNER" resume --run-id "$run_id" --planning-file "$lock_plan" 2>/dev/null)
  busy_status=$?
  set -e
  [[ "$busy_status" == 2 ]] || fail 'locked resume did not return the busy exit status'
  [[ "$(jq -r '.status' <<< "$busy_result")" == busy ]] || fail 'locked resume did not return busy JSON'
  [[ "$(jq -r '.stage' "$state")" == completed ]] || fail 'locked resume changed the persisted run stage'
  [[ -z "$(jq -r '.planning_file' "$state")" ]] || fail 'locked resume changed the planning file before acquiring the lock'
  [[ "$(jq '[.[]|select(.path=="/v2/create_video_from_avatar")]|length' "$TMP_DIR/requests.json")" == "$creates_before" ]] || fail 'locked resume duplicated a paid Jogg task'
  set +e
  busy_result=$(bash "$RUNNER" status --run-id "$run_id" 2>/dev/null)
  busy_status=$?
  set -e
  [[ "$busy_status" == 2 && "$(jq -r '.status' <<< "$busy_result")" == busy ]] || fail 'status did not respect the active run lock'
  rm -rf "$state.lock"

  bash "$RUNNER" resume --run-id "$run_id" >/dev/null
  creates_after=$(jq '[.[]|select(.path=="/v2/create_video_from_avatar")]|length' "$TMP_DIR/requests.json")
  works_after=$(jq '[.[]|select(.path|endswith("/projects/project-1/works"))]|length' "$TMP_DIR/requests.json")
  [[ "$creates_before" == "$creates_after" ]] || fail 'resume duplicated paid Jogg tasks'
  [[ "$works_before" == "$works_after" ]] || fail 'resume duplicated local work'

  jq 'del(.render_project_fingerprint)' "$state" > "$state.tmp"; mv "$state.tmp" "$state"
  bash "$RUNNER" resume --run-id "$run_id" >/dev/null
  works_after=$(jq '[.[]|select(.path|endswith("/projects/project-1/works"))]|length' "$TMP_DIR/requests.json")
  [[ "$works_before" == "$works_after" ]] || fail 'legacy work with a matching snapshot was not reused'
  jq -e '.render_project_fingerprint|length>0' "$state" >/dev/null || fail 'legacy work fingerprint was not restored from its snapshot'

  jq 'del(.render_project_fingerprint)' "$state" > "$state.tmp"; mv "$state.tmp" "$state"
  curl -fsS -X PATCH "$SMART_SLIDES_BASE_URL/api/v1/video-studio/projects/project-1/editor-state" \
    -H 'Content-Type: application/json' --data '{"bgm_enabled":true,"bgm_volume":0.42}' >/dev/null
  bash "$RUNNER" resume --run-id "$run_id" >/dev/null
  works_after=$(jq '[.[]|select(.path|endswith("/projects/project-1/works"))]|length' "$TMP_DIR/requests.json")
  [[ "$works_after" == $((works_before + 1)) ]] || fail 'legacy stale work was reused after render inputs changed'
  works_before=$works_after

  local avatar_path
  avatar_path=$(jq -r '.jogg_tasks["shot-01"].avatar_path' "$state")
  rm -f "$avatar_path"
  creates_before=$(jq '[.[]|select(.path=="/v2/create_video_from_avatar")]|length' "$TMP_DIR/requests.json")
  bash "$RUNNER" resume --run-id "$run_id" >/dev/null
  [[ -f "$avatar_path" ]] || fail 'resume did not restore a missing target avatar file'
  creates_after=$(jq '[.[]|select(.path=="/v2/create_video_from_avatar")]|length' "$TMP_DIR/requests.json")
  [[ "$creates_before" == "$creates_after" ]] || fail 'missing avatar recovery submitted a duplicate paid Jogg task'

  curl -fsS -X PATCH "$SMART_SLIDES_BASE_URL/api/v1/video-studio/projects/project-1/editor-state" \
    -H 'Content-Type: application/json' --data '{"shot_scripts":{"shot-02":"编辑后的中段口播"}}' >/dev/null
  edited_result=$(bash "$RUNNER" resume --run-id "$run_id")
  [[ "$(jq -r '.stage' <<< "$edited_result")" == completed ]] || fail 'edited narration did not complete'
  creates_after=$(jq '[.[]|select(.path=="/v2/create_video_from_avatar")]|length' "$TMP_DIR/requests.json")
  works_after=$(jq '[.[]|select(.path|endswith("/projects/project-1/works"))]|length' "$TMP_DIR/requests.json")
  [[ "$creates_after" == $((creates_before + 1)) ]] || fail 'edited narration did not regenerate exactly one Jogg task'
  [[ "$works_after" == $((works_before + 1)) ]] || fail 'edited narration did not create a fresh local work'
  jq -e '[.[]|select(.path=="/v2/create_video_from_avatar")|.body|fromjson|select(.voice.script=="编辑后的中段口播")]|length==1' "$TMP_DIR/requests.json" >/dev/null || fail 'edited narration did not reach Jogg'

  creates_before=$creates_after
  jq 'del(.jogg_tasks["shot-03"].script_hash)' "$state" > "$state.tmp"; mv "$state.tmp" "$state"
  curl -fsS -X PATCH "$SMART_SLIDES_BASE_URL/api/v1/video-studio/projects/project-1/editor-state" \
    -H 'Content-Type: application/json' --data '{"shot_scripts":{"shot-02":"编辑后的中段口播","shot-03":"升级前编辑的结尾口播"}}' >/dev/null
  edited_result=$(bash "$RUNNER" resume --run-id "$run_id")
  [[ "$(jq -r '.stage' <<< "$edited_result")" == completed ]] || fail 'legacy narration edit did not complete'
  creates_after=$(jq '[.[]|select(.path=="/v2/create_video_from_avatar")]|length' "$TMP_DIR/requests.json")
  [[ "$creates_after" == $((creates_before + 1)) ]] || fail 'legacy task without script hash silently reused stale audio'
  jq -e '[.[]|select(.path=="/v2/create_video_from_avatar")|.body|fromjson|select(.voice.script=="升级前编辑的结尾口播")]|length==1' "$TMP_DIR/requests.json" >/dev/null || fail 'legacy narration edit did not reach Jogg'
  stop_mock
}

failure_path() {
  start_mock failed; configure_paths failed
  local result run_id
  if result=$(bash "$RUNNER" run --topic '失败测试' --duration-seconds 60 --avatar-mode opening 2>/dev/null); then fail 'failed Jogg task unexpectedly succeeded'; fi
  run_id=$(jq -r '.run_id' <<< "$result")
  [[ "$(jq -r '.stage' "$SMART_SLIDES_STATE_DIR/$run_id.json")" == failed ]] || fail 'failure was not persisted'
  stop_mock
}

timeout_path() {
  start_mock pending; configure_paths timeout; export SMART_SLIDES_MAX_JOGG_WAIT_SECONDS=0
  local result run_id state creates_before creates_after
  result=$(bash "$RUNNER" run --topic '超时测试' --duration-seconds 60 --avatar-mode opening)
  run_id=$(jq -r '.run_id' <<< "$result"); state="$SMART_SLIDES_STATE_DIR/$run_id.json"
  [[ "$(jq -r '.stage' <<< "$result")" == waiting_jogg ]] || fail 'timeout is not resumable'
  jq -e '.jogg_tasks["shot-01"].video_id|length>0' "$state" >/dev/null || fail 'timeout lost video id'
  creates_before=$(jq '[.[]|select(.path=="/v2/create_video_from_avatar")]|length' "$TMP_DIR/requests.json")
  jq '.jogg_tasks["shot-01"] |= (.video_id="" | .status="submission_unknown")' "$state" > "$state.tmp"
  mv "$state.tmp" "$state"
  result=$(bash "$RUNNER" resume --run-id "$run_id")
  [[ "$(jq -r '.stage' <<< "$result")" == blocked_jogg_recovery ]] || fail 'unknown Jogg submission was not blocked'
  creates_after=$(jq '[.[]|select(.path=="/v2/create_video_from_avatar")]|length' "$TMP_DIR/requests.json")
  [[ "$creates_before" == "$creates_after" ]] || fail 'unknown Jogg submission was automatically resubmitted'
  unset SMART_SLIDES_MAX_JOGG_WAIT_SECONDS; stop_mock
}

no_avatar_visual_path() {
  start_mock completed; configure_paths none
  local result run_id state
  result=$(bash "$RUNNER" run --topic '无数字人画面' --duration-seconds 60 --avatar-mode none)
  run_id=$(jq -r '.run_id' <<< "$result"); state="$SMART_SLIDES_STATE_DIR/$run_id.json"
  jq -e '.jogg_tasks|length==3' "$state" >/dev/null || fail 'none mode still needs Jogg audio for every shot'
  jq -e '[.jogg_tasks[].avatar_path|select(length>0)]|length==0' "$state" >/dev/null || fail 'none mode retained avatar visuals'
  jq -e '[.[]|select(.path|test("/broll-assets$"))]|length==3' "$TMP_DIR/requests.json" >/dev/null || fail 'none mode did not download all B-roll'
  stop_mock
}

make_fake_ffmpeg
planning_required_path
happy_path
failure_path
timeout_path
no_avatar_visual_path
printf 'smart-slides orchestration tests passed\n'
