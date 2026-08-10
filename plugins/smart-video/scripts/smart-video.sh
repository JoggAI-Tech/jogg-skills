#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
PLUGIN_ROOT=$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)
SMARTVIDEO_HOME=${SMARTVIDEO_HOME:-"$HOME/.codex/smartvideo"}
SMARTVIDEO_RELEASES_ROOT="$SMARTVIDEO_HOME/node-runtime/releases"
SMARTVIDEO_ACTIVE_FILE="$SMARTVIDEO_HOME/active-runtime.json"
SMARTVIDEO_NODE_HOME=${SMARTVIDEO_NODE_HOME:-"$SMARTVIDEO_HOME/node"}
SMARTVIDEO_NODE_CURRENT="$SMARTVIDEO_NODE_HOME/current"
SMARTVIDEO_BOM="$PLUGIN_ROOT/runtime-bom.json"
SMARTVIDEO_PACKAGE_NAME="@joggai/smartvideo"
SMARTVIDEO_VERSION=""
SMARTVIDEO_INSTALL_ROOT_OVERRIDE=${SMARTVIDEO_INSTALL_ROOT:-}
SMARTVIDEO_PACKAGE_SPEC_OVERRIDE=${SMARTVIDEO_PACKAGE_SPEC:-}
SMARTVIDEO_INSTALL_ROOT=""
SMARTVIDEO_PACKAGE_SPEC=""

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

load_runtime_contract() {
  local contract
  command -v node >/dev/null 2>&1 || return 1
  contract=$(SMARTVIDEO_BOM="$SMARTVIDEO_BOM" node <<'NODE'
const fs = require('node:fs');
try {
  const bom = JSON.parse(fs.readFileSync(process.env.SMARTVIDEO_BOM, 'utf8'));
  const name = bom.aggregate && bom.aggregate.name;
  const version = bom.aggregate && bom.aggregate.version;
  if (typeof name !== 'string' || !name || typeof version !== 'string' || !version) process.exit(1);
  process.stdout.write(`${name}\t${version}`);
} catch {
  process.exit(1);
}
NODE
  ) || die "runtime-bom.json is missing or invalid"
  IFS=$'\t' read -r SMARTVIDEO_PACKAGE_NAME SMARTVIDEO_VERSION <<< "$contract"
  SMARTVIDEO_INSTALL_ROOT=${SMARTVIDEO_INSTALL_ROOT_OVERRIDE:-"$SMARTVIDEO_RELEASES_ROOT/$SMARTVIDEO_VERSION"}
  SMARTVIDEO_PACKAGE_SPEC=${SMARTVIDEO_PACKAGE_SPEC_OVERRIDE:-"$SMARTVIDEO_PACKAGE_NAME@$SMARTVIDEO_VERSION"}
}

minimum_node_version() {
  local version
  version=$(awk -F '"' '$2 == "minimum_node" { print $4; exit }' "$SMARTVIDEO_BOM")
  [[ "$version" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]] || die \
    "runtime-bom.json minimum_node is missing or invalid"
  printf '%s' "$version"
}

version_at_least() {
  local installed=$1 required=$2 installed_major installed_minor installed_patch required_major required_minor required_patch
  IFS=. read -r installed_major installed_minor installed_patch <<< "${installed%%-*}"
  IFS=. read -r required_major required_minor required_patch <<< "$required"
  ((installed_major > required_major)) && return 0
  ((installed_major < required_major)) && return 1
  ((installed_minor > required_minor)) && return 0
  ((installed_minor < required_minor)) && return 1
  ((installed_patch >= required_patch))
}

node_version() {
  local version
  command -v node >/dev/null 2>&1 || return 1
  version=$(node --version 2>/dev/null) || return 1
  printf '%s' "${version#v}"
}

node_ready() {
  local installed required
  installed=$(node_version 2>/dev/null) || return 1
  required=$(minimum_node_version)
  [[ "$installed" =~ ^[0-9]+\.[0-9]+\.[0-9]+ ]] || return 1
  version_at_least "$installed" "$required" && command -v npm >/dev/null 2>&1
}

use_managed_node() {
  if [[ -x "$SMARTVIDEO_NODE_CURRENT/bin/node" && -x "$SMARTVIDEO_NODE_CURRENT/bin/npm" ]]; then
    export PATH="$SMARTVIDEO_NODE_CURRENT/bin:$PATH"
    hash -r
  fi
}

smartvideo_binary() {
  printf '%s/node_modules/.bin/smartvideo' "$SMARTVIDEO_INSTALL_ROOT"
}

runtime_root_ready() {
  local runtime_root=$1 binary
  binary="$runtime_root/node_modules/.bin/smartvideo"
  [[ -x "$binary" ]] || return 1
  [[ "$("$binary" --version 2>/dev/null || true)" == "$SMARTVIDEO_VERSION" ]] || return 1
  SMARTVIDEO_BOM="$SMARTVIDEO_BOM" \
  SMARTVIDEO_INSTALL_ROOT="$runtime_root" \
  SMARTVIDEO_EXPECTED_NAME="$SMARTVIDEO_PACKAGE_NAME" \
  SMARTVIDEO_EXPECTED_VERSION="$SMARTVIDEO_VERSION" \
    node <<'NODE'
const fs = require('node:fs');
const path = require('node:path');
try {
  const bom = JSON.parse(fs.readFileSync(process.env.SMARTVIDEO_BOM, 'utf8'));
  if (bom.aggregate?.name !== process.env.SMARTVIDEO_EXPECTED_NAME) process.exit(1);
  if (bom.aggregate?.version !== process.env.SMARTVIDEO_EXPECTED_VERSION) process.exit(1);
  const expected = { [bom.aggregate.name]: bom.aggregate.version, ...bom.packages };
  for (const [name, version] of Object.entries(expected)) {
    const manifest = path.join(process.env.SMARTVIDEO_INSTALL_ROOT, 'node_modules', ...name.split('/'), 'package.json');
    const installed = JSON.parse(fs.readFileSync(manifest, 'utf8'));
    if (installed.name !== name || installed.version !== version) process.exit(1);
  }
} catch {
  process.exit(1);
}
NODE
}

runtime_ready() {
  runtime_root_ready "$SMARTVIDEO_INSTALL_ROOT"
}

bootstrap_command() {
  printf 'bash "%s" bootstrap' "$SCRIPT_DIR/smart-video.sh"
}

emit_runtime_missing() {
  local reason=$1
  local command required
  command=$(bootstrap_command)
  command=${command//\\/\\\\}
  command=${command//\"/\\\"}
  required="$SMARTVIDEO_PACKAGE_NAME"
  [[ -z "$SMARTVIDEO_VERSION" ]] || required="$required@$SMARTVIDEO_VERSION"
  printf '{"status":"dependencies_missing","runtime":"npm","required":"%s","missing":["%s"],"bootstrap_command":"%s"}\n' \
    "$required" "$reason" "$command"
}

ensure_managed_node() {
  local required
  required=$(minimum_node_version)
  SMARTVIDEO_HOME="$SMARTVIDEO_HOME" SMARTVIDEO_NODE_HOME="$SMARTVIDEO_NODE_HOME" \
    bash "$SCRIPT_DIR/install-node-official.sh" --minimum "$required" >/dev/null
  use_managed_node
  node_ready || die "official Node.js installation completed, but Node.js $required+ is unavailable"
}

activate_runtime() {
  mkdir -p "$SMARTVIDEO_HOME"
  SMARTVIDEO_ACTIVE_TEMP="$SMARTVIDEO_ACTIVE_FILE.tmp.$$" \
  SMARTVIDEO_ACTIVE_TARGET="$SMARTVIDEO_INSTALL_ROOT" \
  SMARTVIDEO_ACTIVE_PACKAGE="$SMARTVIDEO_PACKAGE_NAME" \
  SMARTVIDEO_ACTIVE_VERSION="$SMARTVIDEO_VERSION" \
  SMARTVIDEO_ACTIVE_PLUGIN="$PLUGIN_ROOT" \
  SMARTVIDEO_ACTIVE_FILE="$SMARTVIDEO_ACTIVE_FILE" \
    node <<'NODE'
const fs = require('node:fs');
const payload = {
  schema: 'smartvideo_active_runtime_v1',
  package: process.env.SMARTVIDEO_ACTIVE_PACKAGE,
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
  if runtime_ready; then
    activate_runtime
    return
  fi
  mkdir -p "$SMARTVIDEO_RELEASES_ROOT"
  local staging backup
  staging=$(mktemp -d "$SMARTVIDEO_RELEASES_ROOT/.install-$SMARTVIDEO_VERSION.XXXXXX")
  log "Installing SmartVideo $SMARTVIDEO_VERSION into a managed runtime..."
  if ! npm install --prefix "$staging" --ignore-scripts --no-audit --no-fund --no-package-lock "$SMARTVIDEO_PACKAGE_SPEC"; then
    log "installation staging directory retained for diagnosis: $staging"
    return 1
  fi
  [[ -x "$staging/node_modules/.bin/smartvideo" ]] || die "installed package has no smartvideo executable"
  [[ "$("$staging/node_modules/.bin/smartvideo" --version)" == "$SMARTVIDEO_VERSION" ]] || die \
    "installed SmartVideo version does not match $SMARTVIDEO_VERSION"
  runtime_root_ready "$staging" || die "installed SmartVideo package set does not match runtime-bom.json"
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

use_managed_node

case "$ACTION" in
  bootstrap|install-deps)
    node_ready || ensure_managed_node
    load_runtime_contract
    install_runtime
    delegate "$@"
    ;;
  upgrade)
    node_ready || ensure_managed_node
    load_runtime_contract
    install_runtime
    delegate doctor
    ;;
  doctor)
    if ! node_ready; then
      emit_runtime_missing "node>=$(minimum_node_version),npm"
      exit 0
    fi
    load_runtime_contract
    if ! runtime_ready; then
      emit_runtime_missing "$SMARTVIDEO_PACKAGE_NAME"
      exit 0
    fi
    delegate "$@"
    ;;
  *)
    node_ready || die "Node.js $(minimum_node_version)+ is required. Run $(bootstrap_command)"
    load_runtime_contract
    runtime_ready || die "SmartVideo runtime is not installed. Run $(bootstrap_command)"
    delegate "$@"
    ;;
esac
