#!/usr/bin/env python3
"""Validate the maintainer-owned Anchises Analysis plugin policy."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Sequence


DEFAULT_POLICY = Path(__file__).resolve().parents[1] / "references" / "plugin-policy.json"
VALID_RESTRICTION_VALUES = {"enabled", "disabled"}


def load_policy(path: Path = DEFAULT_POLICY) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("plugin policy must be a JSON object")
    if set(value) != {"schema_version", "market_data"}:
        raise ValueError("plugin policy has an unexpected top-level shape")
    if value["schema_version"] != 1:
        raise ValueError("plugin policy has an unsupported schema_version")

    market_data = value["market_data"]
    if not isinstance(market_data, dict) or set(market_data) != {"restrictions"}:
        raise ValueError("plugin policy has an unexpected market_data shape")
    if market_data["restrictions"] not in VALID_RESTRICTION_VALUES:
        raise ValueError("plugin policy has an unsupported restrictions value")
    return value


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--policy", type=Path, default=DEFAULT_POLICY)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        policy = load_policy(args.policy)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print(
        "plugin policy valid: market_data.restrictions="
        f"{policy['market_data']['restrictions']}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
