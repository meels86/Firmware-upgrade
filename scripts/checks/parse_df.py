#!/usr/bin/env python3
"""Parse `df -Pk` output captured from a NetScaler appliance shell into a
disk-space health-check block. Reads raw df output on stdin."""
import json
import sys


def parse(raw: str, warn_pct: int) -> dict:
    filesystems = []
    status = "PASS"
    for line in raw.strip().splitlines():
        parts = line.split()
        if len(parts) < 6 or parts[0] == "Filesystem":
            continue
        try:
            used_pct = int(parts[4].rstrip("%"))
        except ValueError:
            continue
        filesystems.append(
            {
                "filesystem": parts[0],
                "size_kb": int(parts[1]),
                "used_kb": int(parts[2]),
                "avail_kb": int(parts[3]),
                "used_pct": used_pct,
                "mount": parts[5],
            }
        )
        if used_pct >= warn_pct:
            status = "FAIL"

    if not filesystems:
        status = "FAIL"

    return {"status": status, "warn_threshold_pct": warn_pct, "filesystems": filesystems}


if __name__ == "__main__":
    threshold = int(sys.argv[1]) if len(sys.argv) > 1 else 80
    print(json.dumps(parse(sys.stdin.read(), threshold)))
