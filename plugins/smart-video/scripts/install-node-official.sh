#!/usr/bin/env bash
set -euo pipefail

SMARTVIDEO_HOME=${SMARTVIDEO_HOME:-"$HOME/.codex/smartvideo"}
NODE_HOME=${SMARTVIDEO_NODE_HOME:-"$SMARTVIDEO_HOME/node"}
NODE_DIST_BASE=${SMARTVIDEO_NODE_DIST_BASE:-"https://nodejs.org/dist"}
MINIMUM_VERSION=22.0.0

log() { printf '[smart-video/node] %s\n' "$*" >&2; }
die() { log "ERROR: $*"; exit 1; }

while (($#)); do
  case "$1" in
    --minimum)
      (($# >= 2)) || die '--minimum requires a version'
      MINIMUM_VERSION=$2
      shift 2
      ;;
    --help|-h)
      printf 'Usage: %s [--minimum VERSION]\n' "$0"
      exit 0
      ;;
    *) die "unknown argument: $1" ;;
  esac
done

[[ "$MINIMUM_VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]] || die \
  "minimum Node.js version must use major.minor.patch format"
NODE_MAJOR=${MINIMUM_VERSION%%.*}

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

if [[ -x "$NODE_HOME/current/bin/node" && -x "$NODE_HOME/current/bin/npm" ]]; then
  CURRENT_VERSION=$("$NODE_HOME/current/bin/node" --version 2>/dev/null || true)
  CURRENT_VERSION=${CURRENT_VERSION#v}
  if [[ "$CURRENT_VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+ ]] && \
      version_at_least "$CURRENT_VERSION" "$MINIMUM_VERSION"; then
    log "Managed Node.js v$CURRENT_VERSION already satisfies $MINIMUM_VERSION"
    printf '%s\n' "$NODE_HOME/current"
    exit 0
  fi
fi

command -v curl >/dev/null 2>&1 || die 'curl is required to download Node.js'
command -v tar >/dev/null 2>&1 || die 'tar is required to install Node.js'

case "$(uname -s 2>/dev/null || true)" in
  Darwin) NODE_PLATFORM=darwin ;;
  Linux) NODE_PLATFORM=linux ;;
  *) die 'the managed Node.js installer supports macOS and Linux' ;;
esac

case "$(uname -m 2>/dev/null || true)" in
  arm64|aarch64) NODE_ARCH=arm64 ;;
  x86_64|amd64) NODE_ARCH=x64 ;;
  *) die "unsupported CPU architecture: $(uname -m 2>/dev/null || printf unknown)" ;;
esac

WORK_ROOT=$(mktemp -d "${TMPDIR:-/tmp}/smartvideo-node.XXXXXX")
STAGING=
cleanup() {
  [[ -z "$STAGING" || ! -d "$STAGING" ]] || rm -rf "$STAGING"
  rm -rf "$WORK_ROOT"
}
trap cleanup EXIT INT TERM

INDEX_FILE="$WORK_ROOT/index.tab"
curl -fsSL --retry 3 --connect-timeout 15 -o "$INDEX_FILE" "$NODE_DIST_BASE/index.tab"
NODE_VERSION=$(awk -F '\t' -v major="$NODE_MAJOR" '
  NR > 1 && $1 ~ ("^v" major "\\.") { print $1; exit }
' "$INDEX_FILE")
[[ -n "$NODE_VERSION" ]] || die "Node.js $NODE_MAJOR.x is not available from $NODE_DIST_BASE"
version_at_least "${NODE_VERSION#v}" "$MINIMUM_VERSION" || die \
  "latest official Node.js $NODE_MAJOR.x ($NODE_VERSION) is older than required $MINIMUM_VERSION"

ARCHIVE="node-$NODE_VERSION-$NODE_PLATFORM-$NODE_ARCH.tar.gz"
RELEASE_URL="$NODE_DIST_BASE/$NODE_VERSION"
ARCHIVE_PATH="$WORK_ROOT/$ARCHIVE"
CHECKSUMS_PATH="$WORK_ROOT/SHASUMS256.txt"

log "Downloading official Node.js $NODE_VERSION for $NODE_PLATFORM-$NODE_ARCH..."
curl -fsSL --retry 3 --connect-timeout 15 -o "$ARCHIVE_PATH" "$RELEASE_URL/$ARCHIVE"
curl -fsSL --retry 3 --connect-timeout 15 -o "$CHECKSUMS_PATH" "$RELEASE_URL/SHASUMS256.txt"

EXPECTED_SHA=$(awk -v archive="$ARCHIVE" '$2 == archive { print $1; exit }' "$CHECKSUMS_PATH")
[[ "$EXPECTED_SHA" =~ ^[0-9a-fA-F]{64}$ ]] || die "official checksum is missing for $ARCHIVE"
if command -v shasum >/dev/null 2>&1; then
  ACTUAL_SHA=$(shasum -a 256 "$ARCHIVE_PATH" | awk '{print $1}')
elif command -v sha256sum >/dev/null 2>&1; then
  ACTUAL_SHA=$(sha256sum "$ARCHIVE_PATH" | awk '{print $1}')
elif command -v openssl >/dev/null 2>&1; then
  ACTUAL_SHA=$(openssl dgst -sha256 "$ARCHIVE_PATH" | awk '{print $NF}')
else
  die 'shasum, sha256sum, or openssl is required to verify Node.js'
fi
ACTUAL_SHA=$(printf '%s' "$ACTUAL_SHA" | tr '[:upper:]' '[:lower:]')
EXPECTED_SHA=$(printf '%s' "$EXPECTED_SHA" | tr '[:upper:]' '[:lower:]')
[[ "$ACTUAL_SHA" == "$EXPECTED_SHA" ]] || die "checksum verification failed for $ARCHIVE"

VERSIONS_ROOT="$NODE_HOME/versions"
INSTALL_ROOT="$VERSIONS_ROOT/$NODE_VERSION"
mkdir -p "$VERSIONS_ROOT"

if [[ ! -x "$INSTALL_ROOT/bin/node" || ! -x "$INSTALL_ROOT/bin/npm" ]]; then
  STAGING=$(mktemp -d "$VERSIONS_ROOT/.install-$NODE_VERSION.XXXXXX")
  tar -xzf "$ARCHIVE_PATH" -C "$STAGING" --strip-components=1
  [[ "$($STAGING/bin/node --version)" == "$NODE_VERSION" ]] || die 'installed Node.js version is invalid'
  "$STAGING/bin/npm" --version >/dev/null || die 'official Node.js archive does not contain a working npm'
  if [[ -e "$INSTALL_ROOT" ]]; then
    mv "$INSTALL_ROOT" "$INSTALL_ROOT.replaced.$(date +%Y%m%d%H%M%S)"
  fi
  mv "$STAGING" "$INSTALL_ROOT"
fi

CURRENT_TEMP="$NODE_HOME/.current.$$"
ln -s "$INSTALL_ROOT" "$CURRENT_TEMP"
SMARTVIDEO_NODE_CURRENT_TEMP="$CURRENT_TEMP" \
SMARTVIDEO_NODE_CURRENT="$NODE_HOME/current" \
  "$INSTALL_ROOT/bin/node" <<'NODE'
const fs = require('node:fs');
fs.renameSync(process.env.SMARTVIDEO_NODE_CURRENT_TEMP, process.env.SMARTVIDEO_NODE_CURRENT);
NODE
log "Node.js $NODE_VERSION is active at $NODE_HOME/current"
printf '%s\n' "$NODE_HOME/current"
