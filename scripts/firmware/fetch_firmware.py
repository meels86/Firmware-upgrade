#!/usr/bin/env python3
"""fetch_firmware.py <dest-path>

Dispatches to the S3 or SMB fetcher based on $FIRMWARE_SOURCE.
"""
from __future__ import annotations

import os
import sys

from lib.common import log_error


def main(dest: str) -> None:
    source = os.environ.get("FIRMWARE_SOURCE", "s3")
    if source == "s3":
        from firmware.fetch_from_s3 import main as fetch
    elif source == "smb":
        from firmware.fetch_from_smb import main as fetch
    else:
        log_error(f"Unknown FIRMWARE_SOURCE '{source}' (expected 's3' or 'smb')")
        sys.exit(1)
    fetch(dest)


if __name__ == "__main__":
    main(sys.argv[1])
