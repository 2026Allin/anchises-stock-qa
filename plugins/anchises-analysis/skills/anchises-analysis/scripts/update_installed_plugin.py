#!/usr/bin/env python3
"""Run the one supported Anchises Analysis plugin update sequence."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Sequence


METADATA_PATH = Path(__file__).resolve().parents[1] / "references" / "client-release.json"
VERSION_RE = re.compile(
    r"^(?P<core>0|[1-9]\d*)\.(?P<minor>0|[1-9]\d*)\.(?P<patch>0|[1-9]\d*)"
    r"(?:-(?P<pre>[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?$"
)
RELEASE_RE = re.compile(r"^codex\.(?P<stamp>\d{14})$")
COMMAND_TIMEOUT_SECONDS = 180
ALLOWED_IDENTITY = {
    "schema_version": 1,
    "name": "anchises-analysis",
    "platform": "codex",
    "channel": "qa-v2-auth",
    "plugin_id": "anchises-analysis@Anchises-Analysis",
    "marketplace": "Anchises-Analysis",
    "repository": "https://github.com/2026Allin/anchises-stock-qa.git",
    "git_ref": "qa-v2-auth",
}


@dataclass(frozen=True)
class CommandResult:
    returncode: int
    stdout: str
    stderr: str


Runner = Callable[[Sequence[str]], CommandResult]


def _default_runner(command: Sequence[str]) -> CommandResult:
    try:
        completed = subprocess.run(
            list(command),
            check=False,
            capture_output=True,
            text=True,
            timeout=COMMAND_TIMEOUT_SECONDS,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return CommandResult(126, "", str(exc))
    return CommandResult(completed.returncode, completed.stdout, completed.stderr)


def _load_metadata(path: Path = METADATA_PATH) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    required = {
        "schema_version",
        "name",
        "platform",
        "version",
        "release_id",
        "channel",
        "plugin_id",
        "marketplace",
        "repository",
        "git_ref",
    }
    if not isinstance(value, dict) or set(value) != required:
        raise ValueError("client release metadata has an unexpected shape")
    for key, expected in ALLOWED_IDENTITY.items():
        if value.get(key) != expected:
            raise ValueError(f"client release metadata has unsupported {key}")
    _version_parts(value.get("version"))
    if not isinstance(value.get("release_id"), str) or not RELEASE_RE.fullmatch(
        value["release_id"]
    ):
        raise ValueError("client release metadata has an invalid release_id")
    return value


def _version_parts(version: str) -> tuple[tuple[int, int, int], list[str] | None]:
    if not isinstance(version, str):
        raise ValueError("target version must be a valid SemVer base version")
    match = VERSION_RE.fullmatch(version)
    if not match:
        raise ValueError("target version must be a valid SemVer base version")
    core = (
        int(match.group("core")),
        int(match.group("minor")),
        int(match.group("patch")),
    )
    pre = match.group("pre")
    return core, pre.split(".") if pre else None


def _compare_identifiers(left: list[str] | None, right: list[str] | None) -> int:
    if left is None or right is None:
        if left is right:
            return 0
        return 1 if left is None else -1
    for left_item, right_item in zip(left, right):
        if left_item == right_item:
            continue
        left_numeric = left_item.isdigit()
        right_numeric = right_item.isdigit()
        if left_numeric and right_numeric:
            return 1 if int(left_item) > int(right_item) else -1
        if left_numeric != right_numeric:
            return -1 if left_numeric else 1
        return 1 if left_item > right_item else -1
    return (len(left) > len(right)) - (len(left) < len(right))


def compare_releases(left: str, right: str) -> int:
    """Compare full `<semver>+codex.<timestamp>` release strings."""

    try:
        left_version, left_release = left.split("+", 1)
        right_version, right_release = right.split("+", 1)
    except ValueError as exc:
        raise ValueError("release must contain exactly one +codex suffix") from exc
    left_core, left_pre = _version_parts(left_version)
    right_core, right_pre = _version_parts(right_version)
    if left_core != right_core:
        return (left_core > right_core) - (left_core < right_core)
    prerelease_comparison = _compare_identifiers(left_pre, right_pre)
    if prerelease_comparison:
        return prerelease_comparison
    left_match = RELEASE_RE.fullmatch(left_release)
    right_match = RELEASE_RE.fullmatch(right_release)
    if not left_match or not right_match:
        raise ValueError("release ID must be codex followed by a 14-digit timestamp")
    left_stamp = left_match.group("stamp")
    right_stamp = right_match.group("stamp")
    return (left_stamp > right_stamp) - (left_stamp < right_stamp)


def _decode(command: Sequence[str], result: CommandResult) -> dict[str, Any] | None:
    if result.returncode != 0:
        return None
    try:
        value = json.loads(result.stdout)
    except json.JSONDecodeError:
        return None
    return value if isinstance(value, dict) else None


def _installed_plugin(payload: dict[str, Any], plugin_id: str) -> dict[str, Any] | None:
    installed = payload.get("installed")
    if not isinstance(installed, list):
        return None
    matches = [
        item
        for item in installed
        if isinstance(item, dict) and item.get("pluginId") == plugin_id
    ]
    return matches[0] if len(matches) == 1 else None


def _marketplace(payload: dict[str, Any], name: str) -> dict[str, Any] | None:
    marketplaces = payload.get("marketplaces")
    if not isinstance(marketplaces, list):
        return None
    matches = [
        item
        for item in marketplaces
        if isinstance(item, dict) and item.get("name") == name
    ]
    return matches[0] if len(matches) == 1 else None


def _result(
    status: str,
    step: str,
    *,
    target: str,
    installed: str | None = None,
) -> dict[str, Any]:
    value: dict[str, Any] = {
        "status": status,
        "step": step,
        "target_release": target,
    }
    if installed is not None:
        value["installed_release"] = installed
    return value


def run_update(
    target_version: str,
    target_release_id: str,
    *,
    runner: Runner = _default_runner,
    metadata_path: Path = METADATA_PATH,
) -> dict[str, Any]:
    """Execute the fixed update state machine and return one structured result."""

    metadata = _load_metadata(metadata_path)
    _version_parts(target_version)
    if not RELEASE_RE.fullmatch(target_release_id):
        raise ValueError("target release ID must be codex followed by a 14-digit timestamp")
    target = f"{target_version}+{target_release_id}"
    compare_releases(target, target)

    list_command = ("codex", "plugin", "list", "--json")
    marketplace_list_command = (
        "codex",
        "plugin",
        "marketplace",
        "list",
        "--json",
    )
    upgrade_command = (
        "codex",
        "plugin",
        "marketplace",
        "upgrade",
        metadata["marketplace"],
        "--json",
    )
    install_command = (
        "codex",
        "plugin",
        "add",
        metadata["plugin_id"],
        "--json",
    )

    initial_payload = _decode(list_command, runner(list_command))
    if initial_payload is None:
        return _result("preflight_failed", "plugin_list_preflight", target=target)
    initial = _installed_plugin(initial_payload, metadata["plugin_id"])
    if initial is None or not initial.get("installed") or not initial.get("enabled"):
        return _result("preflight_failed", "plugin_list_preflight", target=target)
    initial_version = initial.get("version")
    if not isinstance(initial_version, str):
        return _result("preflight_failed", "plugin_list_preflight", target=target)

    marketplace_payload = _decode(
        marketplace_list_command,
        runner(marketplace_list_command),
    )
    if marketplace_payload is None:
        return _result(
            "preflight_failed",
            "marketplace_list_preflight",
            target=target,
            installed=initial_version,
        )
    marketplace = _marketplace(marketplace_payload, metadata["marketplace"])
    source = marketplace.get("marketplaceSource") if marketplace else None
    if not isinstance(source, dict) or (
        source.get("sourceType") != "git"
        or source.get("source") != metadata["repository"]
        or source.get("refName") != metadata["git_ref"]
    ):
        return _result(
            "unsupported_source",
            "source_validation",
            target=target,
            installed=initial_version,
        )

    try:
        if compare_releases(initial_version, target) >= 0:
            return _result(
                "already_current",
                "preflight",
                target=target,
                installed=initial_version,
            )
    except ValueError:
        return _result(
            "preflight_failed",
            "plugin_list_preflight",
            target=target,
            installed=initial_version,
        )

    if _decode(upgrade_command, runner(upgrade_command)) is None:
        return _result(
            "upgrade_failed",
            "marketplace_upgrade",
            target=target,
            installed=initial_version,
        )
    if _decode(install_command, runner(install_command)) is None:
        return _result(
            "install_failed",
            "plugin_install",
            target=target,
            installed=initial_version,
        )

    final_payload = _decode(list_command, runner(list_command))
    if final_payload is None:
        return _result(
            "verification_failed",
            "verification",
            target=target,
            installed=initial_version,
        )
    final = _installed_plugin(final_payload, metadata["plugin_id"])
    final_version = final.get("version") if final else None
    if (
        not final
        or not final.get("installed")
        or not final.get("enabled")
        or not isinstance(final_version, str)
    ):
        return _result(
            "verification_failed",
            "verification",
            target=target,
            installed=initial_version,
        )
    try:
        verified = compare_releases(final_version, target) >= 0
    except ValueError:
        verified = False
    if not verified:
        return _result(
            "verification_failed",
            "verification",
            target=target,
            installed=final_version,
        )
    return _result(
        "updated",
        "verification",
        target=target,
        installed=final_version,
    )


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target-version", required=True)
    parser.add_argument("--target-release-id", required=True)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        result = run_update(args.target_version, args.target_release_id)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        result = {
            "status": "preflight_failed",
            "step": "release_validation",
            "error": str(exc),
        }
    print(json.dumps(result, sort_keys=True))
    return 0 if result["status"] in {"already_current", "updated"} else 1


if __name__ == "__main__":
    sys.exit(main())
