#!/usr/bin/env bash
# Shared helpers sourced by every pipeline script.
set -euo pipefail

log_info()  { printf '\033[1;34m[INFO]\033[0m  %s\n' "$*"; }
log_warn()  { printf '\033[1;33m[WARN]\033[0m  %s\n' "$*" >&2; }
log_error() { printf '\033[1;31m[ERROR]\033[0m %s\n' "$*" >&2; }
log_ok()    { printf '\033[1;32m[OK]\033[0m    %s\n' "$*"; }

# require_env VAR1 VAR2 ... - fail with a clear message if any are unset/empty.
require_env() {
  local missing=0 var
  for var in "$@"; do
    if [ -z "${!var:-}" ]; then
      log_error "Required variable '${var}' is not set"
      missing=1
    fi
  done
  [ "$missing" -eq 0 ] || exit 1
}

# ns_ssh <mgmt-ip> <command...> - run a command on a NetScaler appliance/SVM.
# Prefers key-based auth (NS_SSH_PRIVATE_KEY_FILE, ideally a GitLab "File"
# type CI/CD variable) and falls back to NS_SSH_PASSWORD via sshpass.
ns_ssh() {
  local host="$1"; shift
  local user="${NS_SSH_USER:-nsroot}"
  local port="${NS_SSH_PORT:-22}"
  local opts=(-o StrictHostKeyChecking="${SSH_STRICT_HOST_KEY_CHECKING:-no}" -o UserKnownHostsFile=/dev/null -p "$port")

  if [ -n "${NS_SSH_PRIVATE_KEY_FILE:-}" ] && [ -f "${NS_SSH_PRIVATE_KEY_FILE}" ]; then
    ssh -i "${NS_SSH_PRIVATE_KEY_FILE}" "${opts[@]}" "${user}@${host}" "$@"
  elif [ -n "${NS_SSH_PASSWORD:-}" ]; then
    SSHPASS="${NS_SSH_PASSWORD}" sshpass -e ssh "${opts[@]}" "${user}@${host}" "$@"
  else
    log_error "No SSH credential available (set NS_SSH_PRIVATE_KEY_FILE or NS_SSH_PASSWORD)"
    return 1
  fi
}

# ns_scp_put <mgmt-ip> <local-path> <remote-path> - copy a file to the appliance.
ns_scp_put() {
  local host="$1" local_path="$2" remote_path="$3"
  local user="${NS_SSH_USER:-nsroot}"
  local port="${NS_SSH_PORT:-22}"
  local opts=(-o StrictHostKeyChecking="${SSH_STRICT_HOST_KEY_CHECKING:-no}" -o UserKnownHostsFile=/dev/null -P "$port")

  if [ -n "${NS_SSH_PRIVATE_KEY_FILE:-}" ] && [ -f "${NS_SSH_PRIVATE_KEY_FILE}" ]; then
    scp -i "${NS_SSH_PRIVATE_KEY_FILE}" "${opts[@]}" "$local_path" "${user}@${host}:${remote_path}"
  elif [ -n "${NS_SSH_PASSWORD:-}" ]; then
    SSHPASS="${NS_SSH_PASSWORD}" sshpass -e scp "${opts[@]}" "$local_path" "${user}@${host}:${remote_path}"
  else
    log_error "No SSH credential available (set NS_SSH_PRIVATE_KEY_FILE or NS_SSH_PASSWORD)"
    return 1
  fi
}
