#!/usr/bin/env python3
"""upload_firmware.py <local-firmware-file>

Uploads the firmware build to a NetScaler appliance/SVM via the NITRO
`systemfile` resource (base64 body over HTTPS) - no SSH/SCP. Shared by
both the SDX and VPX pipelines; PLATFORM selects the default remote
directory.

NITRO has no generic "compute a remote file's hash" action, so there is
no way to do a true remote SHA256 comparison without shell access. The
strongest integrity check available over the API alone is comparing the
uploaded file's size (read back via NITRO) to the local file - this
catches truncation/corruption in transit. The SHA256 of the build itself
remains the checksum of record, computed and verified against
EXPECTED_SHA256 when it was fetched (see scripts/firmware/verify_checksum.py)
and carried forward here for the artifact record. See
docs/citrix-api-notes.md.

Reads DEVICE_NAME, MGMT_IP, PLATFORM, NS_API_USERNAME, NS_API_PASSWORD,
ARTIFACT_DIR, NS_FIRMWARE_REMOTE_DIR (optional override) from the
environment.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from lib.common import log_error, log_info, log_ok, require_env
from lib.nitro_client import NitroClient, NitroError

REMOTE_DIRS = {"sdx": "/var/mps/mps_images", "vpx": "/var/nsinstall"}


def main(local_file: str) -> int:
    env = require_env("DEVICE_NAME", "MGMT_IP", "PLATFORM", "NS_API_USERNAME", "NS_API_PASSWORD")
    device, host, platform = env["DEVICE_NAME"], env["MGMT_IP"], env["PLATFORM"]

    remote_dir = os.environ.get("NS_FIRMWARE_REMOTE_DIR") or REMOTE_DIRS.get(platform)
    if not remote_dir:
        log_error(f"No default remote directory for PLATFORM='{platform}' - set NS_FIRMWARE_REMOTE_DIR")
        return 1

    filename = Path(local_file).name
    local_size = Path(local_file).stat().st_size

    sha256_file = Path(f"{local_file}.sha256")
    sha256_local = sha256_file.read_text().split()[0] if sha256_file.exists() else None

    out_dir = Path(os.environ.get("ARTIFACT_DIR", "artifacts")) / device
    out_dir.mkdir(parents=True, exist_ok=True)

    client = NitroClient(
        host,
        env["NS_API_USERNAME"],
        env["NS_API_PASSWORD"],
        verify_ssl=os.environ.get("NS_API_VERIFY_SSL", "false").lower() == "true",
    )

    log_info(f"Uploading {filename} ({local_size} bytes) to {device} ({host}:{remote_dir}) via NITRO")
    try:
        client.upload_file(remote_dir, filename, local_file)
        info = client.get_file_info(remote_dir, filename)
    except NitroError as exc:
        log_error(f"Upload to {device} failed: {exc}")
        return 1

    remote_size = info.get("filesize")
    size_match = remote_size is not None and int(remote_size) == local_size

    report = {
        "device": device,
        "mgmt_ip": host,
        "file": filename,
        "remote_path": f"{remote_dir}/{filename}",
        "sha256_local": sha256_local,
        "local_size_bytes": local_size,
        "remote_size_bytes": remote_size,
        "size_match": size_match,
    }
    (out_dir / "upload-checksum.json").write_text(json.dumps(report, indent=2))

    if not size_match:
        log_error(f"Uploaded file size mismatch on {device}: local={local_size} remote={remote_size}")
        return 1

    (out_dir / ".remote_firmware_path").write_text(f"{remote_dir}/{filename}")
    log_ok(f"Upload verified on {device} (size match: {local_size} bytes, sha256={sha256_local})")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
