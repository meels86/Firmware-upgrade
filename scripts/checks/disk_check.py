"""Disk-space health check via the NITRO `stat/system` resource.

CAVEAT: field names (disk0size/disk0perusage/disk1size/disk1perusage) are
the ones commonly seen in the standard NetScaler system stat object used
by NITRO-based monitoring integrations. Confirm them against a live
`GET /nitro/v1/stat/system` response for your firmware version and adjust
DISK_PARTITIONS below if they differ. See docs/citrix-api-notes.md.
"""
from __future__ import annotations

from lib.nitro_client import NitroClient, NitroError

DISK_PARTITIONS = [
    {"label": "/flash", "size_field": "disk0size", "used_pct_field": "disk0perusage"},
    {"label": "/var", "size_field": "disk1size", "used_pct_field": "disk1perusage"},
]


def check(client: NitroClient, warn_threshold_pct: int) -> dict:
    try:
        stats = client.get_stat("system")
    except NitroError as exc:
        return {"status": "UNKNOWN", "error": str(exc), "filesystems": []}

    system = stats.get("system", {})
    filesystems = []
    status = "PASS"

    for part in DISK_PARTITIONS:
        used_pct = system.get(part["used_pct_field"])
        size = system.get(part["size_field"])
        if used_pct is None:
            status = "UNKNOWN"
            filesystems.append({"mount": part["label"], "used_pct": None, "size_kb": size})
            continue
        used_pct = float(used_pct)
        filesystems.append({"mount": part["label"], "used_pct": used_pct, "size_kb": size})
        if used_pct >= warn_threshold_pct:
            status = "FAIL"

    if not filesystems:
        status = "FAIL"

    return {"status": status, "warn_threshold_pct": warn_threshold_pct, "filesystems": filesystems}
