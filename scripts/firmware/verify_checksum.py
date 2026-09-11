#!/usr/bin/env python3
"""verify_checksum.py <file>

Records the SHA256 of the downloaded firmware next to it, and verifies it
against a known-good value when one is provided (EXPECTED_SHA256).
"""
from __future__ import annotations

import hashlib
import os
import sys
from pathlib import Path

from lib.common import log_error, log_info, log_ok, log_warn


def sha256_of(path: str) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main(path: str) -> None:
    expected = os.environ.get("EXPECTED_SHA256", "")
    actual = sha256_of(path)
    log_info(f"SHA256({path}) = {actual}")
    Path(f"{path}.sha256").write_text(f"{actual}  {Path(path).name}\n")

    if expected:
        if actual.lower() != expected.lower():
            log_error(f"Checksum mismatch: expected {expected}, got {actual}")
            sys.exit(1)
        log_ok("Checksum verified against expected value")
    else:
        log_warn("No EXPECTED_SHA256 provided - recorded checksum only, did not verify against a known-good value")


if __name__ == "__main__":
    main(sys.argv[1])
