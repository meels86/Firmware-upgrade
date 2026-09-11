"""Interface up/up health check via the NITRO `config/Interface` and
`stat/Interface` resources.

An interface only counts as a fault if it is administratively ENABLED but
not operationally UP - administratively disabled interfaces are recorded
but not treated as failures, since being down is expected for them.

CAVEAT: field names for admin/operational state below are the ones most
commonly seen in NITRO Interface payloads, but are not uniformly
documented across firmware versions. Confirm against a live
`GET /nitro/v1/config/Interface` and `GET /nitro/v1/stat/Interface`
response for your appliance and adjust ADMIN_STATE_FIELD /
OPER_STATE_FIELD below if they differ. See docs/citrix-api-notes.md.
"""
from __future__ import annotations

from lib.nitro_client import NitroClient, NitroError

ADMIN_STATE_FIELD = "state"  # config/Interface: "ENABLED" / "DISABLED"
OPER_STATE_FIELD = "linkstate"  # stat/Interface: "UP" / "DOWN"


def check(client: NitroClient) -> dict:
    try:
        config_rows = client.get_config("Interface").get("Interface", [])
        stat_rows = client.get_stat("Interface").get("Interface", [])
    except NitroError as exc:
        return {"status": "UNKNOWN", "error": str(exc), "interfaces": [], "enabled_but_down": []}

    stat_by_id = {row.get("id"): row for row in stat_rows}

    interfaces = []
    enabled_but_down = []
    for row in config_rows:
        iface_id = row.get("id")
        admin_state = str(row.get(ADMIN_STATE_FIELD, "UNKNOWN")).upper()
        oper_state = str(stat_by_id.get(iface_id, {}).get(OPER_STATE_FIELD, "UNKNOWN")).upper()

        interfaces.append({"name": iface_id, "admin_state": admin_state, "oper_state": oper_state})
        if admin_state == "ENABLED" and oper_state != "UP":
            enabled_but_down.append(iface_id)

    status = "PASS"
    if not interfaces or enabled_but_down:
        status = "FAIL"

    return {"status": status, "interfaces": interfaces, "enabled_but_down": enabled_but_down}
