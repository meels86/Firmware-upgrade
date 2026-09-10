#!/usr/bin/env bash
# verify_checksum.sh <file> [expected-sha256]
# Records the SHA256 of the downloaded firmware next to it, and verifies it
# against a known-good value when one is provided (EXPECTED_SHA256).
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/../lib/common.sh"

FILE="${1:?usage: verify_checksum.sh <file> [expected-sha256]}"
EXPECTED="${2:-}"

ACTUAL="$(sha256sum "$FILE" | awk '{print $1}')"
log_info "SHA256(${FILE}) = ${ACTUAL}"
echo "${ACTUAL}  $(basename "$FILE")" > "${FILE}.sha256"

if [ -n "$EXPECTED" ]; then
  if [ "${ACTUAL,,}" != "${EXPECTED,,}" ]; then
    log_error "Checksum mismatch: expected ${EXPECTED}, got ${ACTUAL}"
    exit 1
  fi
  log_ok "Checksum verified against expected value"
else
  log_warn "No EXPECTED_SHA256 provided - recorded checksum only, did not verify against a known-good value"
fi
