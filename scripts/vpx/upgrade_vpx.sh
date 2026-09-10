#!/usr/bin/env bash
# upgrade_vpx.sh <local-firmware-tgz>
# Standard Citrix ADC VPX/MPX upgrade sequence: copy the build to
# /var/nsinstall, verify its checksum, extract and run installns, then
# reboot and wait for the appliance to come back.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/../lib/common.sh"
require_env DEVICE_NAME MGMT_IP

LOCAL_FILE="${1:?usage: upgrade_vpx.sh <local-firmware-tgz>}"
REMOTE_DIR="/var/nsinstall"
REMOTE_FILE="${REMOTE_DIR}/$(basename "$LOCAL_FILE")"
OUT_DIR="${ARTIFACT_DIR:-artifacts}/${DEVICE_NAME}"
mkdir -p "$OUT_DIR"

log_info "Uploading firmware to ${DEVICE_NAME} (${MGMT_IP})"
ns_scp_put "${MGMT_IP}" "${LOCAL_FILE}" "${REMOTE_FILE}"

LOCAL_SHA="$(sha256sum "$LOCAL_FILE" | awk '{print $1}')"
REMOTE_SHA="$(ns_ssh "${MGMT_IP}" "shell sha256sum ${REMOTE_FILE}" 2>/dev/null | awk '{print $1}' | tail -1)"

cat > "${OUT_DIR}/upload-checksum.json" <<EOF
{
  "device": "${DEVICE_NAME}",
  "mgmt_ip": "${MGMT_IP}",
  "file": "$(basename "$LOCAL_FILE")",
  "remote_path": "${REMOTE_FILE}",
  "sha256_local": "${LOCAL_SHA}",
  "sha256_remote": "${REMOTE_SHA}",
  "match": $([ "${LOCAL_SHA,,}" = "${REMOTE_SHA,,}" ] && echo true || echo false),
  "timestamp": "$(date -u +%FT%TZ)"
}
EOF

if [ "${LOCAL_SHA,,}" != "${REMOTE_SHA,,}" ]; then
  log_error "Checksum mismatch after upload to ${DEVICE_NAME}: local=${LOCAL_SHA} remote=${REMOTE_SHA}"
  exit 1
fi
log_ok "Upload verified on ${DEVICE_NAME}: sha256=${LOCAL_SHA}"

log_info "Extracting and installing build on ${DEVICE_NAME}"
ns_ssh "${MGMT_IP}" "shell tar -xzf ${REMOTE_FILE} -C ${REMOTE_DIR} && cd ${REMOTE_DIR} && ./installns -y"

# `installns` schedules the reboot needed to complete the upgrade on most
# firmware versions; the explicit reboot below is a safety net for versions
# where it does not, and is expected to fail/disconnect if installns
# already rebooted the box - hence `|| true`.
log_info "Ensuring ${DEVICE_NAME} reboots to complete the upgrade"
ns_ssh "${MGMT_IP}" "reboot -w" || true

"${SCRIPT_DIR}/../lib/wait_for_online.sh" "${MGMT_IP}"
log_ok "${DEVICE_NAME} upgrade sequence complete"
