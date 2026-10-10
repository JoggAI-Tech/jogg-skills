#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
node_binary=${SMARTVIDEO_NODE_BINARY:-}
if [[ -z "$node_binary" ]]; then node_binary=$(command -v node 2>/dev/null || true); fi
if [[ -z "$node_binary" && -x "${SMARTVIDEO_HOME:-$HOME/.codex/smartvideo-beta}/node/current/bin/node" ]]; then
  node_binary="${SMARTVIDEO_HOME:-$HOME/.codex/smartvideo-beta}/node/current/bin/node"
fi
if [[ -z "$node_binary" || ! -x "$node_binary" ]]; then
  printf '%s\n' '{"schema":"smartvideo_environment_v1","status":"blocked","capability":"product-install","dependencies":[{"id":"node","status":"missing","install_guidance":{"official_url":"https://nodejs.org/en/download","environment_variable":"SMARTVIDEO_NODE_BINARY","user_choices":["agent","manual","existing_path","skip"]}}]}'
  exit 2
fi
exec "$node_binary" "$SCRIPT_DIR/launcher.mjs" "$@"
