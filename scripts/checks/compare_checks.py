#!/usr/bin/env python3
"""compare_checks.py

Compares this device's health-pre.json and health-post.json artifacts and
writes health-compare.{json,md}. Reads DEVICE_NAME and ARTIFACT_DIR from
the environment.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from lib.common import require_env

OK_STATUSES = {"PASS", "SKIPPED"}


def compare(pre: dict, post: dict) -> dict:
    findings = []

    def check_section(name: str, pre_status: str, post_status: str) -> None:
        if pre_status in OK_STATUSES and post_status not in OK_STATUSES:
            findings.append(f"{name}: regressed from {pre_status} to {post_status}")
        elif post_status not in OK_STATUSES and pre_status not in OK_STATUSES:
            findings.append(f"{name}: still not healthy after upgrade ({post_status})")

    check_section("disk_space", pre["disk_space"]["status"], post["disk_space"]["status"])
    check_section("interfaces", pre["interfaces"]["status"], post["interfaces"]["status"])
    check_section(
        "power_supplies",
        pre["power_supplies"].get("status", "SKIPPED"),
        post["power_supplies"].get("status", "SKIPPED"),
    )

    pre_up = {i["name"] for i in pre["interfaces"].get("interfaces", []) if i.get("oper_state") == "UP"}
    post_up = {i["name"] for i in post["interfaces"].get("interfaces", []) if i.get("oper_state") == "UP"}
    dropped = sorted(pre_up - post_up)
    recovered = sorted(post_up - pre_up)
    if dropped:
        findings.append(f"Interfaces that went DOWN after upgrade: {', '.join(dropped)}")

    return {
        "result": "PASS" if not findings else "FAIL",
        "findings": findings,
        "interfaces_dropped": dropped,
        "interfaces_recovered": recovered,
    }


def main() -> int:
    env = require_env("DEVICE_NAME")
    out_dir = Path(os.environ.get("ARTIFACT_DIR", "artifacts")) / env["DEVICE_NAME"]

    pre = json.loads((out_dir / "health-pre.json").read_text())
    post = json.loads((out_dir / "health-post.json").read_text())

    comparison = compare(pre, post)
    (out_dir / "health-compare.json").write_text(json.dumps(comparison, indent=2))

    lines = [f"# Health check comparison ({comparison['result']})", ""]
    if comparison["findings"]:
        lines += ["## Findings", ""] + [f"- {f}" for f in comparison["findings"]]
    else:
        lines += ["All pre/post health checks match or improved. No regressions detected."]
    (out_dir / "health-compare.md").write_text("\n".join(lines) + "\n")

    print(json.dumps(comparison, indent=2))
    return 0 if comparison["result"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
