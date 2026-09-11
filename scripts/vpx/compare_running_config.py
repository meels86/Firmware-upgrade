#!/usr/bin/env python3
"""
Compare pre- and post-upgrade NetScaler running configuration.

Produces two artifacts:
  * a full unified diff (running-config.diff.full.txt) - useful to see
    exactly where in the config file any change occurred.
  * a consolidated diff (running-config.diff.summary.txt) that lists only
    configuration lines that were actually added or removed, ignoring pure
    re-ordering (NetScaler can rewrite ns.conf line order across an
    upgrade without any functional change) and blank/comment noise.

A non-empty diff is not necessarily a failure - VPX config is expected to
survive an upgrade unchanged, but this is treated as informational so an
operator can review it (see the postcheck job wiring in ci/vpx-pipeline.yml).

Reads DEVICE_NAME and ARTIFACT_DIR from the environment; reads/writes the
running-config.*.txt / running-config.diff.*.txt files under that device's
artifact directory.
"""
from __future__ import annotations

import difflib
import os
import re
import sys
from pathlib import Path

from lib.common import require_env

NOISE_PATTERNS = [
    re.compile(r"^#.*"),
    re.compile(r"^\s*$"),
    re.compile(r"^-\s*Done\s*-?\s*$", re.IGNORECASE),
]


def is_noise(line: str) -> bool:
    return any(p.match(line) for p in NOISE_PATTERNS)


def main() -> int:
    env = require_env("DEVICE_NAME")
    out_dir = Path(os.environ.get("ARTIFACT_DIR", "artifacts")) / env["DEVICE_NAME"]

    pre_lines = (out_dir / "running-config.pre.txt").read_text().splitlines()
    post_lines = (out_dir / "running-config.post.txt").read_text().splitlines()

    full_diff = list(
        difflib.unified_diff(
            pre_lines,
            post_lines,
            fromfile="running-config.pre",
            tofile="running-config.post",
            lineterm="",
        )
    )
    full_out = out_dir / "running-config.diff.full.txt"
    full_out.write_text("\n".join(full_diff) + ("\n" if full_diff else ""))

    pre_set = {line.strip() for line in pre_lines if line.strip() and not is_noise(line)}
    post_set = {line.strip() for line in post_lines if line.strip() and not is_noise(line)}

    removed = sorted(pre_set - post_set)
    added = sorted(post_set - pre_set)

    summary_lines = [
        "# Running configuration diff summary",
        "",
        f"Lines only in PRE-upgrade config (removed): {len(removed)}",
        f"Lines only in POST-upgrade config (added):  {len(added)}",
        "",
    ]
    if removed:
        summary_lines += ["## Removed", ""] + [f"- {line}" for line in removed] + [""]
    if added:
        summary_lines += ["## Added", ""] + [f"+ {line}" for line in added] + [""]
    if not removed and not added:
        summary_lines += ["No configuration differences detected after normalizing for ordering and noise."]

    summary_out = out_dir / "running-config.diff.summary.txt"
    summary_out.write_text("\n".join(summary_lines) + "\n")

    print(f"Full diff: {len(full_diff)} lines -> {full_out}")
    print(f"Summary: {len(removed)} removed / {len(added)} added -> {summary_out}")

    return 1 if (removed or added) else 0


if __name__ == "__main__":
    sys.exit(main())
