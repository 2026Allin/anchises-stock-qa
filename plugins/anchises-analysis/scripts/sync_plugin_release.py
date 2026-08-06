#!/usr/bin/env python3
"""Synchronize platform release metadata with each plugin manifest."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Sequence


PLUGIN_ROOT = Path(__file__).resolve().parents[1]
REFERENCE_ROOT = PLUGIN_ROOT / "skills" / "anchises-analysis" / "references"
PLATFORM_PATHS = {
    "codex": (
        PLUGIN_ROOT / ".codex-plugin" / "plugin.json",
        REFERENCE_ROOT / "plugin-release.json",
    ),
    "claude": (
        PLUGIN_ROOT / ".claude-plugin" / "plugin.json",
        REFERENCE_ROOT / "plugin-release-claude.json",
    ),
}
MANIFEST_PATH, RELEASE_PATH = PLATFORM_PATHS["codex"]
FULL_VERSION_RES = {
    platform: re.compile(
        r"^(?P<version>(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)"
        r"(?:-[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?)"
        rf"\+(?P<release_id>{platform}\.\d{{14}})$"
    )
    for platform in PLATFORM_PATHS
}
FULL_VERSION_RE = FULL_VERSION_RES["codex"]
STATIC_RELEASE_FIELDS_BY_PLATFORM = {
    "codex": {
        "schema_version": 2,
        "name": "anchises-analysis",
        "platform": "codex",
        "plugin_id": "anchises-analysis@Anchises-Analysis",
        "marketplace": "Anchises-Analysis",
        "repository": "https://github.com/2026Allin/anchises-stock-qa.git",
        "git_ref": "main",
        "tag_prefix": "anchises-analysis/codex/v",
    },
    "claude": {
        "schema_version": 2,
        "name": "anchises-analysis",
        "platform": "claude",
        "plugin_id": "anchises-analysis@anchises-capital",
        "marketplace": "anchises-capital",
        "repository": "https://github.com/2026Allin/anchises-stock-qa.git",
        "git_ref": "main",
        "tag_prefix": "anchises-analysis/claude/v",
    },
}
STATIC_RELEASE_FIELDS = STATIC_RELEASE_FIELDS_BY_PLATFORM["codex"]
EXPECTED_RELEASE_KEYS = {*STATIC_RELEASE_FIELDS, "version", "release_id"}


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def _platform_paths(platform: str) -> tuple[Path, Path]:
    try:
        return PLATFORM_PATHS[platform]
    except KeyError as exc:
        raise ValueError("unsupported plugin platform") from exc


def expected_release(
    manifest_path: Path | None = None,
    release_path: Path | None = None,
    *,
    platform: str = "codex",
) -> dict[str, Any]:
    default_manifest, default_release = _platform_paths(platform)
    selected_manifest = manifest_path or default_manifest
    selected_release = release_path or default_release
    static_fields = STATIC_RELEASE_FIELDS_BY_PLATFORM[platform]

    manifest = _load(selected_manifest)
    release = _load(selected_release)
    if set(release) != EXPECTED_RELEASE_KEYS:
        raise ValueError("plugin release metadata has an unexpected shape")
    for key, expected in static_fields.items():
        if release.get(key) != expected:
            raise ValueError(f"plugin release metadata has unsupported {key}")
    full_version = manifest.get("version")
    version_re = FULL_VERSION_RES[platform]
    match = version_re.fullmatch(full_version) if isinstance(full_version, str) else None
    if not match:
        raise ValueError(
            f"manifest version must have one +{platform}.<14-digit timestamp> suffix"
        )
    expected = dict(release)
    expected["version"] = match.group("version")
    expected["release_id"] = match.group("release_id")
    return expected


def sync_release(
    *,
    check: bool,
    manifest_path: Path | None = None,
    release_path: Path | None = None,
    platform: str = "codex",
) -> bool:
    default_manifest, default_release = _platform_paths(platform)
    selected_manifest = manifest_path or default_manifest
    selected_release = release_path or default_release
    current = _load(selected_release)
    expected = expected_release(
        selected_manifest,
        selected_release,
        platform=platform,
    )
    if current == expected:
        return False
    if check:
        raise ValueError("plugin release metadata is out of sync with plugin manifest")
    selected_release.write_text(
        json.dumps(expected, indent=2) + "\n",
        encoding="utf-8",
    )
    return True


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    parser.add_argument(
        "--platform",
        choices=("codex", "claude", "all"),
        default="codex",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    platforms = tuple(PLATFORM_PATHS) if args.platform == "all" else (args.platform,)
    changed: list[str] = []
    try:
        for platform in platforms:
            if sync_release(check=args.check, platform=platform):
                changed.append(platform)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    if changed:
        print(f"plugin release metadata updated: {', '.join(changed)}")
    else:
        print("plugin release metadata matches")
    return 0


if __name__ == "__main__":
    sys.exit(main())
