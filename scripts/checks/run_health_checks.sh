#!/usr/bin/env bash
# run_health_checks.sh <mgmt-ip> <out-file> [--with-psu]
# Runs the disk-space, interface, and (optionally) power-supply checks
# against one appliance and writes the combined JSON report to <out-file>.
# Exits non-zero if any check failed.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/../lib/common.sh"

HOST="${1:?usage: run_health_checks.sh <mgmt-ip> <out-file> [--with-psu]}"
OUT_FILE="${2:?usage: run_health_checks.sh <mgmt-ip> <out-file> [--with-psu]}"
WITH_PSU="${3:-}"
DISK_WARN="${DISK_WARN_THRESHOLD_PCT:-80}"

mkdir -p "$(dirname "$OUT_FILE")"

log_info "Checking disk space on ${HOST}"
DISK_JSON="$(ns_ssh "${HOST}" "shell df -Pk /flash /var" 2>/dev/null | python3 "${SCRIPT_DIR}/parse_df.py" "$DISK_WARN")"

log_info "Checking interface status on ${HOST}"
IF_JSON="$(ns_ssh "${HOST}" "show interface" 2>/dev/null | python3 "${SCRIPT_DIR}/parse_interfaces.py")"

if [ "$WITH_PSU" = "--with-psu" ]; then
  log_info "Checking power supply health on ${HOST} via SNMP"
  PSU_JSON="$(python3 "${SCRIPT_DIR}/check_psu_snmp.py" "${HOST}" "${SNMP_COMMUNITY:-public}")"
else
  PSU_JSON='{"status": "SKIPPED", "reason": "not applicable to virtual (VPX) platform"}'
fi

set +e
python3 "${SCRIPT_DIR}/build_report.py" "$HOST" "$DISK_JSON" "$IF_JSON" "$PSU_JSON" "$OUT_FILE"
RESULT=$?
set -e

if [ "$RESULT" -eq 0 ]; then
  log_ok "Health checks PASSED on ${HOST} (report: ${OUT_FILE})"
else
  log_error "Health checks FAILED on ${HOST} (report: ${OUT_FILE})"
fi
exit "$RESULT"
