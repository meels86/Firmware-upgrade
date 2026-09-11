#!/usr/bin/env python3
"""Download the firmware build from a Windows/SMB share using `smbclient`
(the pure-Python SMB2/3 client package, not the Samba CLI tool) - no
external smbclient binary and no SSH required."""
from __future__ import annotations

import os
import sys
from pathlib import Path

import smbclient

from lib.common import log_info, log_ok, require_env


def main(dest: str) -> None:
    env = require_env(
        "SMB_SHARE_HOST", "SMB_SHARE_NAME", "SMB_FIRMWARE_PATH", "SMB_SHARE_USER", "SMB_SHARE_PASSWORD"
    )
    Path(dest).parent.mkdir(parents=True, exist_ok=True)

    username = env["SMB_SHARE_USER"]
    domain = os.environ.get("SMB_SHARE_DOMAIN")
    if domain:
        username = f"{domain}\\{username}"

    smbclient.ClientConfig(username=username, password=env["SMB_SHARE_PASSWORD"])

    remote_path = "\\\\{host}\\{share}\\{path}".format(
        host=env["SMB_SHARE_HOST"],
        share=env["SMB_SHARE_NAME"],
        path=env["SMB_FIRMWARE_PATH"].replace("/", "\\"),
    )
    log_info(f"Downloading {remote_path} -> {dest}")

    with smbclient.open_file(remote_path, mode="rb") as remote_fh, open(dest, "wb") as local_fh:
        while True:
            chunk = remote_fh.read(1024 * 1024)
            if not chunk:
                break
            local_fh.write(chunk)

    log_ok(f"Downloaded firmware to {dest}")


if __name__ == "__main__":
    main(sys.argv[1])
