#!/usr/bin/env bash
# compare_checks.sh - compare this device's health-pre.json and
# health-post.json artifacts and write health-compare.{json,md}.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/../lib/common.sh"
require_env DEVICE_NAME

DIR="${ARTIFACT_DIR:-artifacts}/${DEVICE_NAME}"
python3 "${SCRIPT_DIR}/../checks/compare_checks.py" \
  "${DIR}/health-pre.json" "${DIR}/health-post.json" "${DIR}/health-compare.json"
