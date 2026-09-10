#!/usr/bin/env bash
# compare_running_config.sh - diff this device's pre/post running-config
# captures. Exit code is informational (1 = differences found); see
# ci/vpx-pipeline.yml for how the postcheck job treats it.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/../lib/common.sh"
require_env DEVICE_NAME

DIR="${ARTIFACT_DIR:-artifacts}/${DEVICE_NAME}"
python3 "${SCRIPT_DIR}/compare_running_config.py" \
  "${DIR}/running-config.pre.txt" "${DIR}/running-config.post.txt" \
  "${DIR}/running-config.diff.full.txt" "${DIR}/running-config.diff.summary.txt"
