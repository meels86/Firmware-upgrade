#!/usr/bin/env python3
"""health_check.py <pre|post>

Runs the disk-space, interface, and (SDX only) power-supply checks against
one device entirely over the NITRO API (and SNMP for the PSU check - no
SSH) and writes the combined JSON report as a pipeline artifact.

Reads DEVICE_NAME, MGMT_IP, PLATFORM, NS_API_USERNAME, NS_API_PASSWORD,
ARTIFACT_DIR, DISK_WARN_THRESHOLD_PCT, SNMP_COMMUNITY from the
environment (set by the CI job / matrix). Exits non-zero if any check
failed.
"""
from __future__ import annotations

import datetime
import json
import os
import sys
from pathlib import Path

from checks import disk_check, interface_check, psu_check
from lib.common import log_error, log_info, log_ok, require_env
from lib.nitro_client import NitroClient

OK_STATUSES = {"PASS", "SKIPPED"}


def main(phase: str) -> int:
    env = require_env("DEVICE_NAME", "MGMT_IP", "PLATFORM", "NS_API_USERNAME", "NS_API_PASSWORD")
    device, host, platform = env["DEVICE_NAME"], env["MGMT_IP"], env["PLATFORM"]

    out_dir = Path(os.environ.get("ARTIFACT_DIR", "artifacts")) / device
    out_dir.mkdir(parents=True, exist_ok=True)

    client = NitroClient(
        host,
        env["NS_API_USERNAME"],
        env["NS_API_PASSWORD"],
        verify_ssl=os.environ.get("NS_API_VERIFY_SSL", "false").lower() == "true",
    )
    warn_pct = int(os.environ.get("DISK_WARN_THRESHOLD_PCT", "80"))

    log_info(f"Checking disk space on {device} ({host})")
    disk = disk_check.check(client, warn_pct)

    log_info(f"Checking interface status on {device} ({host})")
    interfaces = interface_check.check(client)

    if platform == "sdx":
        log_info(f"Checking power supply health on {device} ({host}) via SNMP")
        psu = psu_check.check(host, os.environ.get("SNMP_COMMUNITY", "public"))
    else:
        psu = {"status": "SKIPPED", "reason": "not applicable to virtual (VPX) platform"}

    overall = "PASS" if all(section.get("status") in OK_STATUSES for section in (disk, interfaces, psu)) else "FAIL"

    report = {
        "device": device,
        "host": host,
        "phase": phase,
        "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
        "overall_status": overall,
        "disk_space": disk,
        "interfaces": interfaces,
        "power_supplies": psu,
    }

    out_file = out_dir / f"health-{phase}.json"
    out_file.write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))

    if overall == "PASS":
        log_ok(f"Health checks PASSED on {device} (report: {out_file})")
    else:
        log_error(f"Health checks FAILED on {device} (report: {out_file})")

    return 0 if overall == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "pre"))
