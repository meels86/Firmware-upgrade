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
"""
import difflib
import re
import sys

NOISE_PATTERNS = [
    re.compile(r"^#.*"),
    re.compile(r"^\s*$"),
    re.compile(r"^-\s*Done\s*-?\s*$", re.IGNORECASE),
]


def is_noise(line: str) -> bool:
    return any(p.match(line) for p in NOISE_PATTERNS)


def main() -> None:
    pre_file, post_file, full_out, summary_out = sys.argv[1:5]

    with open(pre_file) as fh:
        pre_lines = fh.read().splitlines()
    with open(post_file) as fh:
        post_lines = fh.read().splitlines()

    full_diff = list(
        difflib.unified_diff(
            pre_lines,
            post_lines,
            fromfile="running-config.pre",
            tofile="running-config.post",
            lineterm="",
        )
    )
    with open(full_out, "w") as fh:
        fh.write("\n".join(full_diff) + ("\n" if full_diff else ""))

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

    with open(summary_out, "w") as fh:
        fh.write("\n".join(summary_lines) + "\n")

    print(f"Full diff: {len(full_diff)} lines -> {full_out}")
    print(f"Summary: {len(removed)} removed / {len(added)} added -> {summary_out}")

    sys.exit(1 if (removed or added) else 0)


if __name__ == "__main__":
    main()
