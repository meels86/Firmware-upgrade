#!/usr/bin/env python3
"""
Check power-supply health on a Citrix ADC/SDX hardware appliance via SNMP.

Uses the NetScaler enterprise MIB's sysHealth power-supply status table
(base OID 1.3.6.1.4.1.5951.4.1.1.41). PSU OID indices and status encodings
have shifted slightly between platform/firmware revisions - confirm the
exact OIDs for your appliance model before relying on this in production.
See docs/citrix-api-notes.md.

Only meaningful on hardware (SDX/MPX); VPX is virtual and has no PSUs, so
callers pass PLATFORM=vpx to skip this check entirely (see
scripts/checks/run_health_checks.sh).
"""
import json
import subprocess
import sys

PSU_STATUS_OIDS = {
    "power_supply_1": "1.3.6.1.4.1.5951.4.1.1.41.1.1.1.2.1",
    "power_supply_2": "1.3.6.1.4.1.5951.4.1.1.41.1.1.1.2.2",
}
OK_VALUES = {"1", "up", "ok", "good", "normal"}


def snmp_get(host: str, community: str, oid: str) -> str:
    try:
        result = subprocess.run(
            ["snmpget", "-v2c", "-c", community, "-Ovq", "-t", "5", "-r", "1", host, oid],
            capture_output=True,
            text=True,
            timeout=15,
            check=True,
        )
        return result.stdout.strip()
    except Exception as exc:  # noqa: BLE001 - report the failure, don't crash the check
        return f"__ERROR__:{exc}"


def check(host: str, community: str) -> dict:
    results = {}
    status = "PASS"
    for name, oid in PSU_STATUS_OIDS.items():
        value = snmp_get(host, community, oid)
        if value.startswith("__ERROR__"):
            results[name] = {"raw": value, "healthy": None}
            status = "UNKNOWN"
            continue
        healthy = value.strip().strip('"').lower() in OK_VALUES
        results[name] = {"raw": value, "healthy": healthy}
        if not healthy:
            status = "FAIL"
    return {"status": status, "power_supplies": results}


if __name__ == "__main__":
    print(json.dumps(check(sys.argv[1], sys.argv[2])))
