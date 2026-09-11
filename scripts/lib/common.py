"""Shared logging and environment helpers used by every pipeline script."""
from __future__ import annotations

import os
import sys


def log_info(msg: str) -> None:
    print(f"\033[1;34m[INFO]\033[0m  {msg}")


def log_warn(msg: str) -> None:
    print(f"\033[1;33m[WARN]\033[0m  {msg}", file=sys.stderr)


def log_error(msg: str) -> None:
    print(f"\033[1;31m[ERROR]\033[0m {msg}", file=sys.stderr)


def log_ok(msg: str) -> None:
    print(f"\033[1;32m[OK]\033[0m    {msg}")


def require_env(*names: str) -> dict[str, str]:
    """Return the requested environment variables, or exit(1) with a clear
    message listing whichever ones are missing/empty."""
    values: dict[str, str] = {}
    missing: list[str] = []
    for name in names:
        value = os.environ.get(name, "")
        if not value:
            missing.append(name)
        values[name] = value
    if missing:
        log_error(f"Required variable(s) not set: {', '.join(missing)}")
        sys.exit(1)
    return values
