#!/usr/bin/env bash
# wait_for_online.sh <mgmt-ip> [timeout-seconds]
# Polls an appliance over SSH until it responds to a trivial CLI command
# again, used after triggering a reboot/upgrade.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/common.sh"

HOST="${1:?usage: wait_for_online.sh <mgmt-ip> [timeout-seconds]}"
TIMEOUT="${2:-${REBOOT_TIMEOUT_SECONDS:-900}}"
INTERVAL=15
elapsed=0

log_info "Waiting up to ${TIMEOUT}s for ${HOST} to accept SSH again"
# Give the appliance a head start to actually go down before we start
# polling, otherwise the first few checks can succeed against the
# not-yet-rebooted appliance.
sleep 30
elapsed=30

while [ "$elapsed" -lt "$TIMEOUT" ]; do
  if ns_ssh "${HOST}" "show ns hardware" >/dev/null 2>&1; then
    log_ok "${HOST} is back online after ${elapsed}s"
    exit 0
  fi
  sleep "$INTERVAL"
  elapsed=$((elapsed + INTERVAL))
done

log_error "${HOST} did not come back online within ${TIMEOUT}s"
exit 1
