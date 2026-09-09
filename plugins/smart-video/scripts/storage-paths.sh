#!/usr/bin/env bash
# Sourced by smart-video.sh before managed Node or npm is available.

log() { printf '[smart-video] %s\n' "$*" >&2; }
die() { log "ERROR: $*"; exit 1; }

is_windows() {
  [[ "${OS:-}" == Windows_NT ]] || [[ "$(uname -s)" =~ ^(MINGW|MSYS|CYGWIN) ]]
}

shell_path() {
  if is_windows; then
    command -v cygpath >/dev/null 2>&1 || die "Git for Windows cygpath is required"
    cygpath -au -- "$1"
  elif [[ "$1" == /* ]]; then
    printf '%s' "$1"
  else
    printf '%s/%s' "$PWD" "$1"
  fi
}

native_path() {
  if is_windows; then cygpath -am -- "$1"; else printf '%s' "$1"; fi
}

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
if [[ "${1:-}" == --config ]]; then
  [[ -n "${2:-}" && "$2" != --* ]] || die "--config requires a file path"
fi

STORAGE_WRITE_PROBE=true
case "$ACTION" in
  doctor|help|-h|--help|version|--version) STORAGE_WRITE_PROBE=false ;;
esac

storage_error() {
  log "ERROR: smartvideo_storage_unavailable: cannot read/write directory: $(native_path "$1")"
  log "Check filesystem permissions and the Codex session's writable paths. Allow this directory, or set SMARTVIDEO_HOME to an absolute path inside an authorized workspace for every Smart Video command."
  log "The current npm runtime also needs the adjacent SMARTVIDEO_HOME.migration.lock path. Directory creation alone is insufficient; ongoing read/write access is required."
  die "A local filesystem access failure does not establish a Jogg MCP, account, or plan entitlement problem."
}

storage_directory_accessible() {
  local directory=$1 existing probe
  existing=$directory
  while [[ ! -e "$existing" ]]; do
    [[ "$existing" != / ]] || break
    existing=$(dirname "$existing")
  done
  [[ -d "$existing" && -r "$existing" && -w "$existing" && -x "$existing" ]] || return 1
  # Keep doctor free of write probes. Mutating commands verify actual writes,
  # since mode bits alone cannot detect all sandbox and Windows ACL denials.
  [[ "$STORAGE_WRITE_PROBE" == true ]] || return 0
  mkdir -p "$directory" || return 1
  probe=$(mktemp "$directory/.smartvideo-write-check.XXXXXX") || return 1
  rm -- "$probe" || return 1
}

check_storage_directory() {
  storage_directory_accessible "$1" || storage_error "$1"
}

select_storage_home() {
  local directory candidate user_home default_home workspace_home
  if [[ -n "${SMARTVIDEO_HOME:-}" ]]; then
    shell_path "$SMARTVIDEO_HOME"
    return
  fi

  # Reuse a workspace root even if Home permissions later change, including
  # commands launched from a generated project's subdirectory.
  directory=$(pwd -P)
  while :; do
    candidate="$directory/.smartvideo"
    case "$candidate/" in
      "$PLUGIN_ROOT/"*) ;;
      *)
        if [[ -e "$candidate" || -L "$candidate" ]]; then
          log "Using workspace data directory: $(native_path "$candidate")"
          printf '%s' "$candidate"
          return
        fi
        ;;
    esac
    [[ "$directory" != / ]] || break
    directory=$(dirname "$directory")
  done

  if is_windows; then
    user_home=${USERPROFILE:-${HOME:-}}
  else
    user_home=${HOME:-}
  fi
  if [[ -n "$user_home" ]]; then
    default_home=$(shell_path "$user_home/.codex/smartvideo")
    if storage_directory_accessible "$(dirname "$default_home")" 2>/dev/null \
      && storage_directory_accessible "$default_home" 2>/dev/null; then
      printf '%s' "$default_home"
      return
    fi
    log "Default data directory is unavailable: $(native_path "$default_home")"
  fi

  directory=$(pwd -P)
  case "$directory/" in
    "$PLUGIN_ROOT/"*) die "Start Smart Video from your writable workspace, or set SMARTVIDEO_HOME; the plugin installation cannot be used for automatic storage." ;;
  esac
  workspace_home="$directory/.smartvideo"
  check_storage_directory "$directory"
  check_storage_directory "$workspace_home"
  log "Using workspace data directory: $(native_path "$workspace_home"). Existing Home data has not been moved; use its original root to resume existing runs."
  printf '%s' "$workspace_home"
}

check_storage() {
  check_storage_directory "$(dirname "$SMARTVIDEO_HOME")"
  check_storage_directory "$SMARTVIDEO_HOME"
  check_storage_directory "$(dirname "$SMARTVIDEO_CONFIG_FILE")"
  if [[ -e "$SMARTVIDEO_CONFIG_FILE" ]]; then
    [[ -f "$SMARTVIDEO_CONFIG_FILE" && -r "$SMARTVIDEO_CONFIG_FILE" && -w "$SMARTVIDEO_CONFIG_FILE" ]] \
      || storage_error "$(dirname "$SMARTVIDEO_CONFIG_FILE")"
  fi
}
