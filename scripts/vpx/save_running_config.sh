#!/usr/bin/env bash
# save_running_config.sh <pre|post>
# Saves the config to disk and captures the running configuration text for
# later comparison.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/../lib/common.sh"
require_env DEVICE_NAME MGMT_IP

PHASE="${1:?usage: save_running_config.sh <pre|post>}"
OUT_DIR="${ARTIFACT_DIR:-artifacts}/${DEVICE_NAME}"
mkdir -p "$OUT_DIR"

log_info "Saving configuration on ${DEVICE_NAME} (${MGMT_IP})"
ns_ssh "${MGMT_IP}" "save ns config" >/dev/null 2>&1 \
  || log_warn "'save ns config' returned non-zero on ${DEVICE_NAME} - continuing to capture the running config anyway"

log_info "Capturing running configuration (${PHASE}-upgrade) from ${DEVICE_NAME}"
ns_ssh "${MGMT_IP}" "show ns runningConfig" > "${OUT_DIR}/running-config.${PHASE}.txt"

log_ok "Saved ${OUT_DIR}/running-config.${PHASE}.txt"
