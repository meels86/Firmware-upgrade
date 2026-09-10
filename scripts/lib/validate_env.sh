#!/usr/bin/env bash
# validate_env.sh <sdx|vpx> - fail fast in the validate stage if required
# CI/CD variables for the chosen firmware source and platform are missing.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/common.sh"

PLATFORM="${1:?usage: validate_env.sh <sdx|vpx>}"

case "${FIRMWARE_SOURCE:-}" in
  s3)  require_env S3_BUCKET S3_FIRMWARE_KEY AWS_ACCESS_KEY_ID AWS_SECRET_ACCESS_KEY ;;
  smb) require_env SMB_SHARE_HOST SMB_SHARE_NAME SMB_FIRMWARE_PATH SMB_SHARE_USER SMB_SHARE_PASSWORD ;;
  *)   log_error "FIRMWARE_SOURCE must be 's3' or 'smb', got '${FIRMWARE_SOURCE:-}'"; exit 1 ;;
esac

if [ -z "${NS_SSH_PRIVATE_KEY_FILE:-}" ] && [ -z "${NS_SSH_PASSWORD:-}" ]; then
  log_error "Set either NS_SSH_PRIVATE_KEY_FILE (recommended - a GitLab 'File' type CI/CD variable) or NS_SSH_PASSWORD"
  exit 1
fi

if [ "$PLATFORM" = "sdx" ]; then
  require_env NS_SVM_USERNAME NS_SVM_PASSWORD
fi

if [ -z "${EXPECTED_SHA256:-}" ]; then
  log_warn "EXPECTED_SHA256 is not set - the firmware checksum will be recorded but not verified against a known-good value"
fi

log_ok "Environment validation passed for platform=${PLATFORM}, firmware_source=${FIRMWARE_SOURCE}"
