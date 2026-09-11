#!/usr/bin/env python3
"""Download the firmware build from S3."""
from __future__ import annotations

import sys
from pathlib import Path

import boto3

from lib.common import log_info, log_ok, require_env


def main(dest: str) -> None:
    env = require_env("S3_BUCKET", "S3_FIRMWARE_KEY")
    Path(dest).parent.mkdir(parents=True, exist_ok=True)

    log_info(f"Downloading s3://{env['S3_BUCKET']}/{env['S3_FIRMWARE_KEY']} -> {dest}")
    boto3.client("s3").download_file(env["S3_BUCKET"], env["S3_FIRMWARE_KEY"], dest)
    log_ok(f"Downloaded firmware to {dest}")


if __name__ == "__main__":
    main(sys.argv[1])
