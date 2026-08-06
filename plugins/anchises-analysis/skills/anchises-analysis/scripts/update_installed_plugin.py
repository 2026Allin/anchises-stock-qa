#!/usr/bin/env python3
"""Run the supported update sequence from fresh, externally captured Git refs.

The owning Skill performs the fixed read-only network lookup. This helper
validates stdin locally and never executes Git.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Sequence

import check_plugin_update as tag_checker


METADATA_PATH = Path(__file__).resolve().parents[1] / "references" / "plugin-release.json"
FULL_RELEASE_RE = re.compile(
    r"^(?P<version>(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)"
    r"(?:-[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?)"
    r"\+codex\.\d{14}$"
)
COMMAND_TIMEOUT_SECONDS = 180


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


def _base_version(full_release: Any) -> str:
    if not isinstance(full_release, str):
        raise ValueError("installed plugin release is invalid")
    match = FULL_RELEASE_RE.fullmatch(full_release)
    if match is None:
        raise ValueError("installed plugin release is invalid")
    return match.group("version")


def _result(
    status: str,
    step: str,
    *,
    target_version: str | None,
    target_tag: str | None,
    target_commit: str | None,
    installed: str | None = None,
) -> dict[str, Any]:
    value: dict[str, Any] = {
        "status": status,
        "step": step,
        "target_version": target_version,
        "target_tag": target_tag,
        "target_commit": target_commit,
    }
    if installed is not None:
        value["installed_release"] = installed
    return value


def run_update(
    *,
    remote_refs: str,
    runner: Runner = _default_runner,
    metadata_path: Path = METADATA_PATH,
) -> dict[str, Any]:
    """Validate fresh captured refs, then execute the fixed CLI sequence."""

    metadata = tag_checker._load_metadata(metadata_path)
    release_check = tag_checker.check_remote_refs(
        remote_refs,
        metadata_path=metadata_path,
        use_cache=False,
    )
    check_status = release_check["status"]
    target_version = release_check.get("target_version")
    target_tag = release_check.get("target_tag")
    target_commit = release_check.get("target_commit")

    if check_status == "current":
        return _result(
            "already_current",
            "tag_check",
            target_version=None,
            target_tag=None,
            target_commit=None,
            installed=f"{metadata['version']}+{metadata['release_id']}",
        )
    if check_status == "release_inconsistent":
        return _result(
            "preflight_failed",
            "release_consistency",
            target_version=target_version,
            target_tag=target_tag,
            target_commit=target_commit,
        )
    if (
        check_status != "update_available"
        or not isinstance(target_version, str)
        or not isinstance(target_tag, str)
        or not isinstance(target_commit, str)
    ):
        return _result(
            "preflight_failed",
            "tag_check",
            target_version=None,
            target_tag=None,
            target_commit=None,
        )

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
        return _result(
            "preflight_failed",
            "plugin_list_preflight",
            target_version=target_version,
            target_tag=target_tag,
            target_commit=target_commit,
        )
    initial = _installed_plugin(initial_payload, metadata["plugin_id"])
    if initial is None or not initial.get("installed") or not initial.get("enabled"):
        return _result(
            "preflight_failed",
            "plugin_list_preflight",
            target_version=target_version,
            target_tag=target_tag,
            target_commit=target_commit,
        )
    initial_version = initial.get("version")
    try:
        initial_base = _base_version(initial_version)
    except ValueError:
        return _result(
            "preflight_failed",
            "plugin_list_preflight",
            target_version=target_version,
            target_tag=target_tag,
            target_commit=target_commit,
        )

    marketplace_payload = _decode(
        marketplace_list_command,
        runner(marketplace_list_command),
    )
    if marketplace_payload is None:
        return _result(
            "preflight_failed",
            "marketplace_list_preflight",
            target_version=target_version,
            target_tag=target_tag,
            target_commit=target_commit,
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
            target_version=target_version,
            target_tag=target_tag,
            target_commit=target_commit,
            installed=initial_version,
        )

    if tag_checker.compare_versions(initial_base, target_version) >= 0:
        return _result(
            "already_current",
            "preflight",
            target_version=target_version,
            target_tag=target_tag,
            target_commit=target_commit,
            installed=initial_version,
        )

    if _decode(upgrade_command, runner(upgrade_command)) is None:
        return _result(
            "upgrade_failed",
            "marketplace_upgrade",
            target_version=target_version,
            target_tag=target_tag,
            target_commit=target_commit,
            installed=initial_version,
        )
    if _decode(install_command, runner(install_command)) is None:
        return _result(
            "install_failed",
            "plugin_install",
            target_version=target_version,
            target_tag=target_tag,
            target_commit=target_commit,
            installed=initial_version,
        )

    final_payload = _decode(list_command, runner(list_command))
    final = _installed_plugin(final_payload, metadata["plugin_id"]) if final_payload else None
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
            target_version=target_version,
            target_tag=target_tag,
            target_commit=target_commit,
            installed=initial_version,
        )
    try:
        verified = (
            tag_checker.compare_versions(_base_version(final_version), target_version)
            >= 0
        )
    except ValueError:
        verified = False
    if not verified:
        return _result(
            "verification_failed",
            "verification",
            target_version=target_version,
            target_tag=target_tag,
            target_commit=target_commit,
            installed=final_version,
        )
    return _result(
        "updated",
        "verification",
        target_version=target_version,
        target_tag=target_tag,
        target_commit=target_commit,
        installed=final_version,
    )


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--remote-refs-stdin", action="store_true")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        if not args.remote_refs_stdin:
            raise ValueError("fresh remote refs are required")
        raw = sys.stdin.buffer.read(tag_checker.MAX_REMOTE_OUTPUT_BYTES + 1)
        if len(raw) > tag_checker.MAX_REMOTE_OUTPUT_BYTES:
            raise ValueError("remote refs are too large")
        result = run_update(remote_refs=raw.decode("utf-8"))
    except (OSError, UnicodeDecodeError, ValueError, json.JSONDecodeError):
        result = {
            "status": "preflight_failed",
            "step": "release_validation",
            "target_version": None,
            "target_tag": None,
            "target_commit": None,
        }
    print(json.dumps(result, separators=(",", ":"), sort_keys=True))
    return 0 if result["status"] in {"already_current", "updated"} else 1


if __name__ == "__main__":
    sys.exit(main())
