#!/usr/bin/env bash
set -euo pipefail
PLUGIN_ROOT=$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
PYTHON_BIN=${SMART_SLIDES_TEST_PYTHON:-$HOME/.codex/smart-slides/venv/bin/python}

[[ -x "$PYTHON_BIN" ]] || { printf 'missing test Python: %s\n' "$PYTHON_BIN" >&2; exit 1; }
bash "$PLUGIN_ROOT/tests/test-smart-slides.sh"
PYTHONPATH="$PLUGIN_ROOT/runtime" "$PYTHON_BIN" "$PLUGIN_ROOT/tests/test_runtime.py"
PYTHONPATH="$PLUGIN_ROOT/runtime" "$PYTHON_BIN" "$PLUGIN_ROOT/tests/test_mg_director_contract.py"
PYTHONPATH="$PLUGIN_ROOT/runtime" "$PYTHON_BIN" "$PLUGIN_ROOT/tests/test_visual_style_profiles.py"
python3 "$PLUGIN_ROOT/tests/test_source_parity.py"
(
  cd "$PLUGIN_ROOT/runtime/frontend"
  [[ -d node_modules ]] || npm ci --ignore-scripts
  npm run test
  npm run build
)
