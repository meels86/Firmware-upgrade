#!/usr/bin/env python3
"""Compare pre- and post-upgrade NetScaler health-check reports and produce
a pass/fail verdict plus a human-readable summary."""
import json
import sys

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


def main() -> None:
    pre_file, post_file, out_file = sys.argv[1:4]
    with open(pre_file) as fh:
        pre = json.load(fh)
    with open(post_file) as fh:
        post = json.load(fh)

    comparison = compare(pre, post)
    comparison["pre_file"] = pre_file
    comparison["post_file"] = post_file

    with open(out_file, "w") as fh:
        json.dump(comparison, fh, indent=2)

    lines = [f"# Health check comparison ({comparison['result']})", ""]
    if comparison["findings"]:
        lines += ["## Findings", ""] + [f"- {f}" for f in comparison["findings"]]
    else:
        lines += ["All pre/post health checks match or improved. No regressions detected."]
    with open(out_file.rsplit(".", 1)[0] + ".md", "w") as fh:
        fh.write("\n".join(lines) + "\n")

    print(json.dumps(comparison, indent=2))
    sys.exit(0 if comparison["result"] == "PASS" else 1)


if __name__ == "__main__":
    main()
