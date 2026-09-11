#!/usr/bin/env python3
"""trigger_upgrade.py

Triggers a NetScaler firmware upgrade via the NITRO API and waits for the
appliance to come back online. No SSH/SCP is used. Shared by both the SDX
and VPX pipelines - requires upload_firmware.py to have run first for this
device (reads the remote path it recorded).

CAVEAT: see docs/citrix-api-notes.md - the exact NITRO action for
triggering an install from an already-uploaded systemfile is not
uniformly documented across ADC/SDX firmware versions. Confirm it for
your environment and override via NS_UPGRADE_ACTION if it differs from
the default "upgrade" used here.

Reads DEVICE_NAME, MGMT_IP, NS_API_USERNAME, NS_API_PASSWORD,
ARTIFACT_DIR, NS_UPGRADE_ACTION, NS_REBOOT_TIMEOUT_SECONDS from the
environment.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from lib.common import log_error, log_info, log_ok, require_env
from lib.nitro_client import NitroClient, NitroError


def main() -> int:
    env = require_env("DEVICE_NAME", "MGMT_IP", "NS_API_USERNAME", "NS_API_PASSWORD")
    device, host = env["DEVICE_NAME"], env["MGMT_IP"]

    out_dir = Path(os.environ.get("ARTIFACT_DIR", "artifacts")) / device
    remote_path_file = out_dir / ".remote_firmware_path"
    if not remote_path_file.exists():
        log_error(f"No uploaded firmware path recorded for {device} - run upload_firmware.py first")
        return 1
    remote_path = remote_path_file.read_text().strip()
    remote_dir, filename = remote_path.rsplit("/", 1)

    action = os.environ.get("NS_UPGRADE_ACTION", "upgrade")
    reboot_timeout = int(os.environ.get("NS_REBOOT_TIMEOUT_SECONDS", "1800"))

    client = NitroClient(
        host,
        env["NS_API_USERNAME"],
        env["NS_API_PASSWORD"],
        verify_ssl=os.environ.get("NS_API_VERIFY_SSL", "false").lower() == "true",
    )

    log_info(f"Submitting upgrade request for {device} using {remote_path} (action={action})")
    try:
        response = client.trigger_upgrade(remote_dir, filename, action=action)
    except NitroError as exc:
        log_error(f"Upgrade request for {device} failed: {exc}")
        return 1

    (out_dir / "upgrade-request-response.json").write_text(json.dumps(response, indent=2))
    log_ok(f"Upgrade request submitted for {device}; rebooting and waiting for it to come back online")

    client.reboot(warm=True)
    if not client.wait_online(timeout=reboot_timeout):
        log_error(f"{device} did not come back online within {reboot_timeout}s")
        return 1

    log_ok(f"{device} is back online")
    return 0


if __name__ == "__main__":
    sys.exit(main())
