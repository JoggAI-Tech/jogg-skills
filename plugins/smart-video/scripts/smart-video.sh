#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
PLUGIN_ROOT=$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)
SMARTVIDEO_VERSION=0.1.0
SMARTVIDEO_HOME=${SMARTVIDEO_HOME:-"$HOME/.codex/smartvideo"}
SMARTVIDEO_RELEASES_ROOT="$SMARTVIDEO_HOME/node-runtime/releases"
SMARTVIDEO_INSTALL_ROOT=${SMARTVIDEO_INSTALL_ROOT:-"$SMARTVIDEO_RELEASES_ROOT/$SMARTVIDEO_VERSION"}
SMARTVIDEO_ACTIVE_FILE="$SMARTVIDEO_HOME/active-runtime.json"
SMARTVIDEO_PACKAGE_SPEC=${SMARTVIDEO_PACKAGE_SPEC:-"@jogg-ai/smartvideo@$SMARTVIDEO_VERSION"}
SMARTVIDEO_BUNDLED_PACKAGE_DIR="$PLUGIN_ROOT/npm"
SMARTVIDEO_BUNDLED_PACKAGES=(
  smartvideo-cli-0.0.7.tgz
  jogg-ai-smartvideo-registry-0.1.0.tgz
  jogg-ai-smartvideo-editor-0.1.0.tgz
  jogg-ai-smartvideo-renderer-0.1.0.tgz
  jogg-ai-smartvideo-speech-0.1.0.tgz
  jogg-ai-smartvideo-avatar-0.1.0.tgz
  jogg-ai-smartvideo-runtime-0.1.0.tgz
  jogg-ai-smartvideo-0.1.0.tgz
)

detect_action() {
  local skip=false argument
  for argument in "$@"; do
    if [[ "$skip" == true ]]; then skip=false; continue; fi
    if [[ "$argument" == --config ]]; then skip=true; continue; fi
    if [[ "$argument" != --* ]]; then printf '%s' "$argument"; return; fi
  done
  printf doctor
}

ACTION=$(detect_action "$@")

log() { printf '[smart-video] %s\n' "$*" >&2; }
die() { log "ERROR: $*"; exit 1; }

node_major() {
  local version
  command -v node >/dev/null 2>&1 || return 1
  version=$(node --version 2>/dev/null) || return 1
  version=${version#v}
  printf '%s' "${version%%.*}"
}

node_ready() {
  local major
  major=$(node_major 2>/dev/null) || return 1
  [[ "$major" =~ ^[0-9]+$ ]] && ((major >= 22)) && command -v npm >/dev/null 2>&1
}

smartvideo_binary() {
  printf '%s/node_modules/.bin/smartvideo' "$SMARTVIDEO_INSTALL_ROOT"
}

runtime_ready() {
  local binary
  binary=$(smartvideo_binary)
  [[ -x "$binary" ]] || return 1
  [[ "$("$binary" --version 2>/dev/null || true)" == "$SMARTVIDEO_VERSION" ]] || return 1
  local package
  for package in smartvideo smartvideo-runtime smartvideo-editor smartvideo-registry \
    smartvideo-renderer smartvideo-speech smartvideo-avatar; do
    [[ -f "$SMARTVIDEO_INSTALL_ROOT/node_modules/@jogg-ai/$package/package.json" ]] || return 1
  done
}

bootstrap_command() {
  printf 'bash "%s" bootstrap' "$SCRIPT_DIR/smart-video.sh"
}

emit_runtime_missing() {
  local reason=$1
  local command
  command=$(bootstrap_command)
  command=${command//\\/\\\\}
  command=${command//\"/\\\"}
  printf '{"status":"dependencies_missing","runtime":"npm","required":"@jogg-ai/smartvideo@%s","missing":["%s"],"bootstrap_command":"%s"}\n' \
    "$SMARTVIDEO_VERSION" "$reason" "$command"
}

ensure_macos_node() {
  [[ "$(uname -s 2>/dev/null || true)" == Darwin ]] || die \
    "Node.js 22+ and npm are required. Install them, then run $(bootstrap_command)"
  command -v brew >/dev/null 2>&1 || die \
    "Node.js 22+ is missing and Homebrew is unavailable. Install Homebrew, then run $(bootstrap_command)"
  log 'Installing or upgrading Node.js with Homebrew...'
  if brew list --versions node >/dev/null 2>&1; then
    brew upgrade node || true
  else
    brew install node
  fi
  hash -r
  node_ready || die "Homebrew completed, but Node.js 22+ is not available in this shell"
}

package_specs() {
  if [[ -n "${SMARTVIDEO_PACKAGE_DIR:-}" ]]; then
    [[ -d "$SMARTVIDEO_PACKAGE_DIR" ]] || die "SMARTVIDEO_PACKAGE_DIR does not exist: $SMARTVIDEO_PACKAGE_DIR"
    find "$SMARTVIDEO_PACKAGE_DIR" -maxdepth 1 -type f -name '*.tgz' -print0
    return
  fi
  if [[ -d "$SMARTVIDEO_BUNDLED_PACKAGE_DIR" ]]; then
    local archive
    for archive in "${SMARTVIDEO_BUNDLED_PACKAGES[@]}"; do
      [[ -f "$SMARTVIDEO_BUNDLED_PACKAGE_DIR/$archive" ]] \
        || die "bundled npm package is missing: $archive"
      printf '%s\0' "$SMARTVIDEO_BUNDLED_PACKAGE_DIR/$archive"
    done
    return
  fi
  printf '%s\0' "$SMARTVIDEO_PACKAGE_SPEC"
}

activate_runtime() {
  mkdir -p "$SMARTVIDEO_HOME"
  SMARTVIDEO_ACTIVE_TEMP="$SMARTVIDEO_ACTIVE_FILE.tmp.$$" \
  SMARTVIDEO_ACTIVE_TARGET="$SMARTVIDEO_INSTALL_ROOT" \
  SMARTVIDEO_ACTIVE_VERSION="$SMARTVIDEO_VERSION" \
  SMARTVIDEO_ACTIVE_PLUGIN="$PLUGIN_ROOT" \
  SMARTVIDEO_ACTIVE_FILE="$SMARTVIDEO_ACTIVE_FILE" \
    node <<'NODE'
const fs = require('node:fs');
const payload = {
  schema: 'smartvideo_active_runtime_v1',
  version: process.env.SMARTVIDEO_ACTIVE_VERSION,
  install_root: process.env.SMARTVIDEO_ACTIVE_TARGET,
  plugin_root: process.env.SMARTVIDEO_ACTIVE_PLUGIN,
  activated_at: new Date().toISOString(),
};
fs.writeFileSync(process.env.SMARTVIDEO_ACTIVE_TEMP, `${JSON.stringify(payload, null, 2)}\n`, { mode: 0o600 });
fs.renameSync(process.env.SMARTVIDEO_ACTIVE_TEMP, process.env.SMARTVIDEO_ACTIVE_FILE);
NODE
}

install_runtime() {
  if [[ -z "${SMARTVIDEO_PACKAGE_DIR:-}" ]] && runtime_ready; then
    activate_runtime
    return
  fi
  mkdir -p "$SMARTVIDEO_RELEASES_ROOT"
  local staging backup
  staging=$(mktemp -d "$SMARTVIDEO_RELEASES_ROOT/.install-$SMARTVIDEO_VERSION.XXXXXX")
  local -a specs=()
  while IFS= read -r -d '' spec; do specs+=("$spec"); done < <(package_specs)
  ((${#specs[@]} > 0)) || die "no SmartVideo package tarballs were found"
  log "Installing SmartVideo $SMARTVIDEO_VERSION into a managed runtime..."
  if ! npm install --prefix "$staging" --ignore-scripts --no-audit --no-fund --no-package-lock "${specs[@]}"; then
    log "installation staging directory retained for diagnosis: $staging"
    return 1
  fi
  [[ -x "$staging/node_modules/.bin/smartvideo" ]] || die "installed package has no smartvideo executable"
  [[ "$("$staging/node_modules/.bin/smartvideo" --version)" == "$SMARTVIDEO_VERSION" ]] || die \
    "installed SmartVideo version does not match $SMARTVIDEO_VERSION"
  if [[ -e "$SMARTVIDEO_INSTALL_ROOT" ]]; then
    backup="$SMARTVIDEO_INSTALL_ROOT.replaced.$(date +%Y%m%d%H%M%S)"
    mv "$SMARTVIDEO_INSTALL_ROOT" "$backup"
  fi
  mv "$staging" "$SMARTVIDEO_INSTALL_ROOT"
  runtime_ready || die "SmartVideo package set is incomplete after installation"
  activate_runtime
}

plugin_version() {
  node -e 'const fs=require("node:fs"); const p=process.argv[1]; process.stdout.write(JSON.parse(fs.readFileSync(p,"utf8")).version || "")' \
    "$PLUGIN_ROOT/.codex-plugin/plugin.json"
}

delegate() {
  local binary
  binary=$(smartvideo_binary)
  export PATH="$SMARTVIDEO_INSTALL_ROOT/node_modules/.bin:$PATH"
  export SMARTVIDEO_HOME SMARTVIDEO_PLUGIN_ROOT="$PLUGIN_ROOT"
  export SMARTVIDEO_PLUGIN_VERSION="$(plugin_version)"
  export SMARTVIDEO_SKILL_ROOT="$PLUGIN_ROOT/skills/smart-video"
  export SMARTVIDEO_AVATAR_CATALOG_PATH="${SMARTVIDEO_AVATAR_CATALOG_PATH:-$PLUGIN_ROOT/assets/avatar-packs/catalog.json}"
  export SMARTVIDEO_RELEASE_MANIFEST="$PLUGIN_ROOT/release-manifest.json"
  export SMARTVIDEO_CLI_COMMAND="bash \"$SCRIPT_DIR/smart-video.sh\""
  exec "$binary" "$@"
}

case "$ACTION" in
  bootstrap|install-deps)
    node_ready || ensure_macos_node
    install_runtime
    delegate "$@"
    ;;
  doctor)
    if ! node_ready; then
      emit_runtime_missing 'node>=22,npm'
      exit 0
    fi
    if ! runtime_ready; then
      emit_runtime_missing '@jogg-ai/smartvideo'
      exit 0
    fi
    delegate "$@"
    ;;
  *)
    node_ready || die "Node.js 22+ is required. Run $(bootstrap_command)"
    runtime_ready || die "SmartVideo runtime is not installed. Run $(bootstrap_command)"
    delegate "$@"
    ;;
esac
