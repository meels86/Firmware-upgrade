#!/usr/bin/env python3
"""save_running_config.py <pre|post>

Saves the configuration to disk and captures the running configuration
text via the NITRO API (`nsconfig` save action + `nsrunningconfig`
resource) - no SSH.

Reads DEVICE_NAME, MGMT_IP, NS_API_USERNAME, NS_API_PASSWORD, ARTIFACT_DIR
from the environment.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

from lib.common import log_info, log_ok, log_warn, require_env
from lib.nitro_client import NitroClient, NitroError


def main(phase: str) -> None:
    env = require_env("DEVICE_NAME", "MGMT_IP", "NS_API_USERNAME", "NS_API_PASSWORD")
    device, host = env["DEVICE_NAME"], env["MGMT_IP"]

    out_dir = Path(os.environ.get("ARTIFACT_DIR", "artifacts")) / device
    out_dir.mkdir(parents=True, exist_ok=True)

    client = NitroClient(
        host,
        env["NS_API_USERNAME"],
        env["NS_API_PASSWORD"],
        verify_ssl=os.environ.get("NS_API_VERIFY_SSL", "false").lower() == "true",
    )

    log_info(f"Saving configuration on {device} ({host})")
    try:
        client.save_config()
    except NitroError as exc:
        log_warn(f"'save' action on nsconfig returned an error on {device} ({exc}) - continuing to capture the running config anyway")

    log_info(f"Capturing running configuration ({phase}-upgrade) from {device}")
    running_config = client.get_running_config()
    out_file = out_dir / f"running-config.{phase}.txt"
    out_file.write_text(running_config)

    log_ok(f"Saved {out_file}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "pre")
