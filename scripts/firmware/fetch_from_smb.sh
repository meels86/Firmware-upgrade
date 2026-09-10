#!/usr/bin/env bash
# fetch_from_smb.sh <dest-path>
# Pulls the firmware build from a Windows/CIFS share using smbclient (no
# privileged mount required, so it works from an unprivileged CI runner).
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/../lib/common.sh"

require_env SMB_SHARE_HOST SMB_SHARE_NAME SMB_FIRMWARE_PATH SMB_SHARE_USER SMB_SHARE_PASSWORD
DEST="${1:?usage: fetch_from_smb.sh <dest-path>}"

DEST_DIR="$(cd "$(dirname "$DEST")" && pwd)"
DEST_FILE="$(basename "$DEST")"
REMOTE_DIR="$(dirname "$SMB_FIRMWARE_PATH")"
REMOTE_FILE="$(basename "$SMB_FIRMWARE_PATH")"
[ "$REMOTE_DIR" = "." ] && REMOTE_DIR=""

log_info "Fetching //${SMB_SHARE_HOST}/${SMB_SHARE_NAME}/${SMB_FIRMWARE_PATH} -> ${DEST}"

smbclient "//${SMB_SHARE_HOST}/${SMB_SHARE_NAME}" \
  -U "${SMB_SHARE_USER}%${SMB_SHARE_PASSWORD}" \
  ${SMB_SHARE_DOMAIN:+-W "${SMB_SHARE_DOMAIN}"} \
  -c "lcd \"${DEST_DIR}\"; ${REMOTE_DIR:+cd \"${REMOTE_DIR}\";} get \"${REMOTE_FILE}\" \"${DEST_FILE}\""

log_ok "Downloaded firmware to ${DEST}"
