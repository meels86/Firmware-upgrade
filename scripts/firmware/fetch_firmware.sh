#!/usr/bin/env bash
# fetch_firmware.sh <dest-path>
# Dispatches to the S3 or SMB fetcher based on $FIRMWARE_SOURCE.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/../lib/common.sh"

DEST="${1:?usage: fetch_firmware.sh <dest-path>}"
mkdir -p "$(dirname "$DEST")"

case "${FIRMWARE_SOURCE:-s3}" in
  s3)  "${SCRIPT_DIR}/fetch_from_s3.sh" "$DEST" ;;
  smb) "${SCRIPT_DIR}/fetch_from_smb.sh" "$DEST" ;;
  *)   log_error "Unknown FIRMWARE_SOURCE '${FIRMWARE_SOURCE:-}' (expected 's3' or 'smb')"; exit 1 ;;
esac
