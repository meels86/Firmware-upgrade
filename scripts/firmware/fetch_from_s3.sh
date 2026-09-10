#!/usr/bin/env bash
# fetch_from_s3.sh <dest-path>
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/../lib/common.sh"

require_env S3_BUCKET S3_FIRMWARE_KEY
DEST="${1:?usage: fetch_from_s3.sh <dest-path>}"

log_info "Downloading s3://${S3_BUCKET}/${S3_FIRMWARE_KEY} -> ${DEST}"
python3 "${SCRIPT_DIR}/s3_download.py" "$S3_BUCKET" "$S3_FIRMWARE_KEY" "$DEST"
log_ok "Downloaded firmware to ${DEST}"
