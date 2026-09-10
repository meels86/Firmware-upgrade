#!/usr/bin/env bash
# trigger_upgrade.sh
# Triggers a Citrix ADC SDX Management Service (SVM) software upgrade via
# the SVM's NITRO API, then waits for the appliance to come back online.
#
# CAVEAT: unlike the VPX/MPX `installns` procedure (stable and well
# documented across firmware versions), the exact NITRO resource/action for
# a *headless, scripted* SDX platform upgrade has varied between SVM
# releases. Before running this against anything but a lab appliance,
# confirm the correct NITRO endpoint and payload for your SVM version
# against Citrix's official SDX upgrade documentation and adjust
# SDX_UPGRADE_NITRO_PATH / the request body below accordingly.
# See docs/citrix-api-notes.md.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/../lib/common.sh"
require_env DEVICE_NAME MGMT_IP NS_SVM_USERNAME NS_SVM_PASSWORD

OUT_DIR="${ARTIFACT_DIR:-artifacts}/${DEVICE_NAME}"
mkdir -p "$OUT_DIR"

REMOTE_FILE="$(cat "${OUT_DIR}/.remote_firmware_path" 2>/dev/null || true)"
if [ -z "$REMOTE_FILE" ]; then
  log_error "No uploaded firmware path recorded for ${DEVICE_NAME} - run upload_firmware.sh first"
  exit 1
fi

NITRO_PATH="${SDX_UPGRADE_NITRO_PATH:-/nitro/v1/config/systemfile}"

log_info "Authenticating to SDX SVM ${DEVICE_NAME} (${MGMT_IP}) NITRO API"
SESSION_ID="$(curl -sk -X POST "https://${MGMT_IP}/nitro/v1/config/login" \
  -H 'Content-Type: application/json' \
  -d "{\"login\": {\"username\": \"${NS_SVM_USERNAME}\", \"password\": \"${NS_SVM_PASSWORD}\"}}" \
  | jq -r '.login[0].sessionid // empty')"

if [ -z "$SESSION_ID" ]; then
  log_error "Failed to authenticate to SDX SVM ${DEVICE_NAME} NITRO API"
  exit 1
fi

log_info "Submitting upgrade request for ${DEVICE_NAME} using firmware ${REMOTE_FILE}"
RESPONSE="$(curl -sk -X POST "https://${MGMT_IP}${NITRO_PATH}" \
  -H "Cookie: SESSID=${SESSION_ID}" \
  -H 'Content-Type: application/json' \
  -d "{\"systemfile\": {\"filelocation\": \"$(dirname "$REMOTE_FILE")\", \"filename\": \"$(basename "$REMOTE_FILE")\", \"action\": \"upgrade\"}}")"

echo "$RESPONSE" | jq . 2>/dev/null | tee "${OUT_DIR}/upgrade-request-response.json" || echo "$RESPONSE" | tee "${OUT_DIR}/upgrade-request-response.json"

ERROR_CODE="$(echo "$RESPONSE" | jq -r '.errorcode // "0"' 2>/dev/null || echo "-1")"
if [ "$ERROR_CODE" != "0" ]; then
  log_error "SDX upgrade request for ${DEVICE_NAME} returned errorcode=${ERROR_CODE}"
  exit 1
fi

log_ok "Upgrade request submitted for ${DEVICE_NAME}; waiting for SVM to complete the upgrade and reboot"
"${SCRIPT_DIR}/../lib/wait_for_online.sh" "${MGMT_IP}" "${SDX_REBOOT_TIMEOUT_SECONDS:-1800}"
