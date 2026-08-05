#!/usr/bin/env python3
"""Synchronize the Skill client-release metadata with the plugin manifest."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Sequence


PLUGIN_ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = PLUGIN_ROOT / ".codex-plugin" / "plugin.json"
RELEASE_PATH = (
    PLUGIN_ROOT
    / "skills"
    / "anchises-analysis"
    / "references"
    / "client-release.json"
)
FULL_VERSION_RE = re.compile(
    r"^(?P<version>(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)"
    r"(?:-[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?)"
    r"\+(?P<release_id>codex\.\d{14})$"
)
STATIC_RELEASE_FIELDS = {
    "schema_version": 1,
    "name": "anchises-analysis",
    "platform": "codex",
    "channel": "qa-v2-auth",
    "plugin_id": "anchises-analysis@Anchises-Analysis",
    "marketplace": "Anchises-Analysis",
    "repository": "https://github.com/2026Allin/anchises-stock-qa.git",
    "git_ref": "qa-v2-auth",
}
EXPECTED_RELEASE_KEYS = {*STATIC_RELEASE_FIELDS, "version", "release_id"}


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def expected_release(
    manifest_path: Path = MANIFEST_PATH,
    release_path: Path = RELEASE_PATH,
) -> dict[str, Any]:
    manifest = _load(manifest_path)
    release = _load(release_path)
    if set(release) != EXPECTED_RELEASE_KEYS:
        raise ValueError("client release metadata has an unexpected shape")
    for key, expected in STATIC_RELEASE_FIELDS.items():
        if release.get(key) != expected:
            raise ValueError(f"client release metadata has unsupported {key}")
    full_version = manifest.get("version")
    match = FULL_VERSION_RE.fullmatch(full_version) if isinstance(full_version, str) else None
    if not match:
        raise ValueError("manifest version must have one +codex.<14-digit timestamp> suffix")
    expected = dict(release)
    expected["version"] = match.group("version")
    expected["release_id"] = match.group("release_id")
    return expected


def sync_release(
    *,
    check: bool,
    manifest_path: Path = MANIFEST_PATH,
    release_path: Path = RELEASE_PATH,
) -> bool:
    current = _load(release_path)
    expected = expected_release(manifest_path, release_path)
    if current == expected:
        return False
    if check:
        raise ValueError("client release metadata is out of sync with plugin manifest")
    release_path.write_text(
        json.dumps(expected, indent=2) + "\n",
        encoding="utf-8",
    )
    return True


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        changed = sync_release(check=args.check)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print("client release metadata updated" if changed else "client release metadata matches")
    return 0


if __name__ == "__main__":
    sys.exit(main())
