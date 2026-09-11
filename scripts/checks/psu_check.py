"""Power-supply health check via SNMP (NETSCALER-MIB sysHealth table).

This is a read-only network-management API query (UDP GET), not a shell
command - the only thing sent to the appliance is an SNMP GET, using the
pure-Python `pysnmp` library rather than shelling out to the net-snmp
`snmpget` binary. Only meaningful on SDX/MPX hardware; VPX is virtual and
has no PSUs (skipped - see PLATFORM handling in health_check.py).

CAVEAT: OID indices and status encodings can differ by chassis model -
confirm against your platform's MIB/OID reference (or an `snmpwalk`
against a real appliance) and adjust PSU_STATUS_OIDS / OK_VALUES below if
needed. See docs/citrix-api-notes.md.
"""
from __future__ import annotations

from pysnmp.hlapi import (
    CommunityData,
    ContextData,
    ObjectIdentity,
    ObjectType,
    SnmpEngine,
    UdpTransportTarget,
    getCmd,
)

PSU_STATUS_OIDS = {
    "power_supply_1": "1.3.6.1.4.1.5951.4.1.1.41.1.1.1.2.1",
    "power_supply_2": "1.3.6.1.4.1.5951.4.1.1.41.1.1.1.2.2",
}
OK_VALUES = {"1", "up", "ok", "good", "normal"}


def _snmp_get(host: str, community: str, oid: str) -> str:
    iterator = getCmd(
        SnmpEngine(),
        CommunityData(community, mpModel=1),  # mpModel=1 -> SNMPv2c
        UdpTransportTarget((host, 161), timeout=5, retries=1),
        ContextData(),
        ObjectType(ObjectIdentity(oid)),
    )
    try:
        error_indication, error_status, error_index, var_binds = next(iterator)
    except Exception as exc:  # noqa: BLE001 - report the failure, don't crash the check
        return f"__ERROR__:{exc}"

    if error_indication:
        return f"__ERROR__:{error_indication}"
    if error_status:
        return f"__ERROR__:{error_status.prettyPrint()}"
    return str(var_binds[0][1]).strip()


def check(host: str, community: str) -> dict:
    results = {}
    status = "PASS"
    for name, oid in PSU_STATUS_OIDS.items():
        value = _snmp_get(host, community, oid)
        if value.startswith("__ERROR__"):
            results[name] = {"raw": value, "healthy": None}
            status = "UNKNOWN"
            continue
        healthy = value.strip('"').lower() in OK_VALUES
        results[name] = {"raw": value, "healthy": healthy}
        if not healthy:
            status = "FAIL"
    return {"status": status, "power_supplies": results}
