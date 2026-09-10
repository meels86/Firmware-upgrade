#!/usr/bin/env bash
# upload_firmware.sh <local-firmware-file>
# Copies the firmware build to the SDX Management Service (SVM) and
# verifies a remote SHA256 against the local one so a corrupted/truncated
# transfer is caught before the upgrade is triggered.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/../lib/common.sh"
require_env DEVICE_NAME MGMT_IP

LOCAL_FILE="${1:?usage: upload_firmware.sh <local-firmware-file>}"
REMOTE_DIR="${SDX_FIRMWARE_REMOTE_DIR:-/var/mps/mps_images}"
REMOTE_FILE="${REMOTE_DIR}/$(basename "$LOCAL_FILE")"
OUT_DIR="${ARTIFACT_DIR:-artifacts}/${DEVICE_NAME}"
mkdir -p "$OUT_DIR"

LOCAL_SHA="$(sha256sum "$LOCAL_FILE" | awk '{print $1}')"
log_info "Uploading $(basename "$LOCAL_FILE") to SDX SVM ${DEVICE_NAME} (${MGMT_IP}:${REMOTE_DIR})"
ns_scp_put "${MGMT_IP}" "${LOCAL_FILE}" "${REMOTE_FILE}"

log_info "Computing remote SHA256 on ${DEVICE_NAME} to verify transfer integrity"
REMOTE_SHA="$(ns_ssh "${MGMT_IP}" "shell sha256sum ${REMOTE_FILE}" 2>/dev/null | awk '{print $1}' | tail -1)"

MATCH=true
if [ "${LOCAL_SHA,,}" != "${REMOTE_SHA,,}" ]; then
  MATCH=false
fi

cat > "${OUT_DIR}/upload-checksum.json" <<EOF
{
  "device": "${DEVICE_NAME}",
  "mgmt_ip": "${MGMT_IP}",
  "file": "$(basename "$LOCAL_FILE")",
  "remote_path": "${REMOTE_FILE}",
  "sha256_local": "${LOCAL_SHA}",
  "sha256_remote": "${REMOTE_SHA}",
  "match": ${MATCH},
  "timestamp": "$(date -u +%FT%TZ)"
}
EOF

if [ "$MATCH" != true ]; then
  log_error "Checksum mismatch after upload to ${DEVICE_NAME}: local=${LOCAL_SHA} remote=${REMOTE_SHA}"
  exit 1
fi

log_ok "Upload verified on ${DEVICE_NAME}: sha256=${LOCAL_SHA}"
echo "${REMOTE_FILE}" > "${OUT_DIR}/.remote_firmware_path"
