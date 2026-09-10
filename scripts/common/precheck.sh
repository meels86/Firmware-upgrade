#!/usr/bin/env bash
# precheck.sh <pre|post>
# Runs the health-check suite for the current job's device (DEVICE_NAME /
# MGMT_IP, set by the CI matrix) and includes the power-supply check only
# when PLATFORM=sdx.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/../lib/common.sh"
require_env DEVICE_NAME MGMT_IP PLATFORM

PHASE="${1:?usage: precheck.sh <pre|post>}"
OUT_FILE="${ARTIFACT_DIR:-artifacts}/${DEVICE_NAME}/health-${PHASE}.json"

WITH_PSU=""
[ "$PLATFORM" = "sdx" ] && WITH_PSU="--with-psu"

"${SCRIPT_DIR}/../checks/run_health_checks.sh" "${MGMT_IP}" "${OUT_FILE}" "${WITH_PSU}"
