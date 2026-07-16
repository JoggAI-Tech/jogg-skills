#!/usr/bin/env bash
set -euo pipefail

PLUGIN_ROOT=$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
SOURCE_REPO=${PODCASTOR_SOURCE_REPO:-/Users/cds-dn-137/Documents/golang/operation-Podcastor}
JOGG_SOURCE_REPO=${JOGG_SOURCE_REPO:-/Users/cds-dn-137/Documents/golang/jogg-backend-srv}
MODE=check

usage() {
  cat >&2 <<'EOF'
Usage: sync-from-podcastor.sh [--check|--refresh] [--source PATH] [--jogg-source PATH]

The default mode only reports source drift. --refresh updates files that are
declared as verbatim snapshots; adapted files are never overwritten.
EOF
}

while (($#)); do
  case "$1" in
    --check) MODE=check ;;
    --refresh) MODE=refresh ;;
    --source)
      shift
      [[ $# -gt 0 ]] || { usage; exit 2; }
      SOURCE_REPO=$1
      ;;
    --jogg-source)
      shift
      [[ $# -gt 0 ]] || { usage; exit 2; }
      JOGG_SOURCE_REPO=$1
      ;;
    -h|--help) usage; exit 0 ;;
    *) printf 'Unknown argument: %s\n' "$1" >&2; usage; exit 2 ;;
  esac
  shift
done

[[ -f "$SOURCE_REPO/backend/services/video_studio_store.py" ]] || {
  printf 'Podcastor source not found: %s\n' "$SOURCE_REPO" >&2
  exit 1
}

drift=0
check_snapshot() {
  local source=$1 destination=$2
  if cmp -s "$SOURCE_REPO/$source" "$PLUGIN_ROOT/$destination"; then
    printf 'same      %s\n' "$source"
    return
  fi
  drift=1
  if [[ "$MODE" == refresh ]]; then
    mkdir -p "$(dirname -- "$PLUGIN_ROOT/$destination")"
    cp "$SOURCE_REPO/$source" "$PLUGIN_ROOT/$destination"
    printf 'refreshed %s\n' "$source"
  else
    printf 'drift     %s\n' "$source"
  fi
}

check_adapted() {
  local source=$1 destination=$2
  if cmp -s "$SOURCE_REPO/$source" "$PLUGIN_ROOT/$destination"; then
    printf 'warning   %s is marked adapted but currently matches source\n' "$source"
  else
    printf 'adapted   %s (manual review required)\n' "$source"
  fi
}

check_snapshot backend/services/video_studio_store.py runtime/backend/services/video_studio_store.py
check_snapshot backend/services/video_studio_mg_design.py runtime/backend/services/video_studio_mg_design.py
check_snapshot backend/services/video_studio_mg_templates.py runtime/backend/services/video_studio_mg_templates.py
check_snapshot frontend/src/features/video-studio/model.ts runtime/frontend/src/features/video-studio/model.ts
check_snapshot frontend/src/features/video-studio/model.test.ts runtime/frontend/src/features/video-studio/model.test.ts
check_snapshot frontend/src/features/video-studio/htmlEditor.ts runtime/frontend/src/features/video-studio/htmlEditor.ts
check_snapshot frontend/src/features/video-studio/htmlEditor.test.ts runtime/frontend/src/features/video-studio/htmlEditor.test.ts

check_adapted backend/services/video_studio_broll.py runtime/backend/services/video_studio_broll.py
check_adapted backend/services/video_studio_bgm.py runtime/backend/services/video_studio_bgm.py
check_adapted backend/services/video_studio_works.py runtime/backend/services/video_studio_works.py
check_adapted frontend/src/api/videoStudio.ts runtime/frontend/src/api/videoStudio.ts

planner_tmp=$(mktemp)
trap 'rm -f "$planner_tmp"' EXIT
python3 "$PLUGIN_ROOT/scripts/extract-planner.py" \
  "$SOURCE_REPO/backend/services/video_studio_planner.py" \
  "$planner_tmp"
if cmp -s "$planner_tmp" "$PLUGIN_ROOT/runtime/backend/services/video_studio_planner.py"; then
  printf 'same      %s (symbol extraction)\n' backend/services/video_studio_planner.py
else
  drift=1
  if [[ "$MODE" == refresh ]]; then
    cp "$planner_tmp" "$PLUGIN_ROOT/runtime/backend/services/video_studio_planner.py"
    printf 'refreshed %s (symbol extraction)\n' backend/services/video_studio_planner.py
  else
    printf 'drift     %s (symbol extraction)\n' backend/services/video_studio_planner.py
  fi
fi

source_commit=$(git -C "$SOURCE_REPO" rev-parse HEAD 2>/dev/null || printf unknown)
printf 'source    %s @ %s\n' "$SOURCE_REPO" "$source_commit"
jogg_commit=$(git -C "$JOGG_SOURCE_REPO" rev-parse HEAD 2>/dev/null || printf unknown)
printf 'source    %s @ %s\n' "$JOGG_SOURCE_REPO" "$jogg_commit"

if PODCASTOR_SOURCE_REPO="$SOURCE_REPO" JOGG_SOURCE_REPO="$JOGG_SOURCE_REPO" python3 "$PLUGIN_ROOT/tests/test_source_parity.py" >/dev/null; then
  printf 'same      extraction manifest source and destination hashes\n'
else
  drift=1
  printf 'drift     extraction manifest source or destination hashes\n'
fi

if [[ "$MODE" == check && "$drift" -ne 0 ]]; then
  printf 'Source drift detected. Review it, then run with --refresh for verbatim/extracted files.\n' >&2
  exit 3
fi
