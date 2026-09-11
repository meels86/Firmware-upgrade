#!/usr/bin/env python3
"""validate_env.py <sdx|vpx>

Fails fast in the validate stage if required CI/CD variables for the
chosen firmware source and platform are missing.
"""
from __future__ import annotations

import os
import sys

from lib.common import log_error, log_ok, log_warn, require_env


def main(platform: str) -> None:
    source = os.environ.get("FIRMWARE_SOURCE", "")
    if source == "s3":
        require_env("S3_BUCKET", "S3_FIRMWARE_KEY", "AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY")
    elif source == "smb":
        require_env("SMB_SHARE_HOST", "SMB_SHARE_NAME", "SMB_FIRMWARE_PATH", "SMB_SHARE_USER", "SMB_SHARE_PASSWORD")
    else:
        log_error(f"FIRMWARE_SOURCE must be 's3' or 'smb', got '{source}'")
        sys.exit(1)

    require_env("NS_API_USERNAME", "NS_API_PASSWORD")

    if not os.environ.get("EXPECTED_SHA256"):
        log_warn("EXPECTED_SHA256 is not set - the firmware checksum will be recorded but not verified against a known-good value")

    log_ok(f"Environment validation passed for platform={platform}, firmware_source={source}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "")
