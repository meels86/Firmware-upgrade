#!/usr/bin/env python3
"""Combine disk/interface/PSU check results into one health-check report,
write it to disk as the pipeline artifact, and exit non-zero on failure."""
import datetime
import json
import sys

OK_STATUSES = {"PASS", "SKIPPED"}


def main() -> None:
    host, disk_json, if_json, psu_json, out_file = sys.argv[1:6]
    disk = json.loads(disk_json)
    interfaces = json.loads(if_json)
    psu = json.loads(psu_json)

    overall = (
        "PASS"
        if disk.get("status") in OK_STATUSES
        and interfaces.get("status") in OK_STATUSES
        and psu.get("status", "SKIPPED") in OK_STATUSES
        else "FAIL"
    )

    report = {
        "host": host,
        "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
        "overall_status": overall,
        "disk_space": disk,
        "interfaces": interfaces,
        "power_supplies": psu,
    }

    with open(out_file, "w") as fh:
        json.dump(report, fh, indent=2)

    print(json.dumps(report, indent=2))
    sys.exit(0 if overall == "PASS" else 1)


if __name__ == "__main__":
    main()
