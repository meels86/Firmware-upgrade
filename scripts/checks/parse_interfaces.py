#!/usr/bin/env python3
"""Parse `show interface` output from a NetScaler CLI session on stdin.

Expects the standard per-interface block format, e.g.:

    Interface 0/1 (Gig Ethernet Interface) #2
        flags=0xc020 <ENABLED, UP, UP, HAMON, 802.1q>
        ...

An interface only counts as a fault if it is administratively ENABLED but
not operationally UP - administratively disabled interfaces are recorded
but not treated as failures, since being down is expected for them.
"""
import json
import re
import sys

IFACE_RE = re.compile(r"^\s*Interface\s+(\S+)\s*\(")
FLAGS_RE = re.compile(r"flags=0x[0-9a-fA-F]+\s*<([^>]*)>")


def parse(raw: str) -> dict:
    interfaces = []
    current = None

    for line in raw.splitlines():
        m = IFACE_RE.match(line)
        if m:
            if current:
                interfaces.append(current)
            current = {"name": m.group(1), "admin_state": "UNKNOWN", "oper_state": "UNKNOWN"}
            continue
        m = FLAGS_RE.search(line)
        if m and current is not None:
            tokens = [t.strip().upper() for t in m.group(1).split(",")]
            current["admin_state"] = "ENABLED" if "ENABLED" in tokens else "DISABLED"
            current["oper_state"] = "UP" if "UP" in tokens else "DOWN"
    if current:
        interfaces.append(current)

    enabled_but_down = [
        iface["name"]
        for iface in interfaces
        if iface["admin_state"] == "ENABLED" and iface["oper_state"] != "UP"
    ]

    status = "PASS"
    if not interfaces or enabled_but_down:
        status = "FAIL"

    return {"status": status, "interfaces": interfaces, "enabled_but_down": enabled_but_down}


if __name__ == "__main__":
    print(json.dumps(parse(sys.stdin.read())))
