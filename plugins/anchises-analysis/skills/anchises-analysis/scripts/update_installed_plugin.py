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


METADATA_PATH = tag_checker.METADATA_PATH
FULL_RELEASE_RES = {
    platform: re.compile(
        r"^(?P<version>(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)"
        r"(?:-[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?)"
        rf"\+{platform}\.\d{{14}}$"
    )
    for platform in tag_checker.METADATA_PATHS
}
FULL_RELEASE_RE = FULL_RELEASE_RES["codex"]
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


def _decode(command: Sequence[str], result: CommandResult) -> Any | None:
    if result.returncode != 0:
        return None
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return None


def _installed_plugin(
    payload: Any,
    plugin_id: str,
    *,
    platform: str = "codex",
) -> dict[str, Any] | None:
    if isinstance(payload, dict):
        installed = payload.get("installed")
    elif platform == "claude":
        installed = payload
    else:
        installed = None
    if not isinstance(installed, list):
        return None
    matches = [
        item
        for item in installed
        if isinstance(item, dict)
        and (
            item.get("pluginId") == plugin_id
            or (platform == "claude" and item.get("id") == plugin_id)
        )
    ]
    return matches[0] if len(matches) == 1 else None


def _marketplace(
    payload: Any,
    name: str,
    *,
    platform: str = "codex",
) -> dict[str, Any] | None:
    if isinstance(payload, dict):
        marketplaces = payload.get("marketplaces")
    elif platform == "claude":
        marketplaces = payload
    else:
        marketplaces = None
    if not isinstance(marketplaces, list):
        return None
    matches = [
        item
        for item in marketplaces
        if isinstance(item, dict) and item.get("name") == name
    ]
    return matches[0] if len(matches) == 1 else None


def _base_version(full_release: Any, *, platform: str = "codex") -> str:
    if not isinstance(full_release, str):
        raise ValueError("installed plugin release is invalid")
    try:
        release_re = FULL_RELEASE_RES[platform]
    except KeyError as exc:
        raise ValueError("installed plugin platform is invalid") from exc
    match = release_re.fullmatch(full_release)
    if match is None:
        raise ValueError("installed plugin release is invalid")
    return match.group("version")


def _installed_and_enabled(item: dict[str, Any], *, platform: str) -> bool:
    installed = item.get("installed", platform == "claude")
    return installed is True and item.get("enabled") is True


def _command_succeeded(result: CommandResult) -> bool:
    return result.returncode == 0


def _source_is_supported(
    marketplace: dict[str, Any] | None,
    *,
    metadata: dict[str, Any],
    remote_refs: str,
    target_commit: str,
    metadata_path: Path,
) -> bool:
    if marketplace is None:
        return False

    platform = metadata["platform"]
    if platform == "codex":
        source = marketplace.get("marketplaceSource")
        source_matches = (
            isinstance(source, dict)
            and source.get("sourceType") == "git"
            and source.get("source") == metadata["repository"]
        )
        ref_name = source.get("refName") if isinstance(source, dict) else None
    elif platform == "claude":
        source_type = marketplace.get("source")
        github_repo = metadata["repository"].removeprefix(
            "https://github.com/"
        ).removesuffix(".git")
        source_matches = (
            source_type == "github" and marketplace.get("repo") == github_repo
        ) or (
            source_type in {"git", "url"}
            and marketplace.get("url") == metadata["repository"]
        )
        ref_name = marketplace.get("ref")
    else:
        return False

    ref_matches = ref_name == metadata["git_ref"]
    if source_matches and ref_name is None:
        ref_matches = tag_checker.default_branch_matches_release(
            remote_refs,
            target_commit=target_commit,
            metadata_path=metadata_path,
        )
    return source_matches and ref_matches


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
    platform = metadata["platform"]
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

    if platform == "codex":
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
    elif platform == "claude":
        list_command = ("claude", "plugin", "list", "--json")
        marketplace_list_command = (
            "claude",
            "plugin",
            "marketplace",
            "list",
            "--json",
        )
        upgrade_command = (
            "claude",
            "plugin",
            "marketplace",
            "update",
            metadata["marketplace"],
        )
        install_command = (
            "claude",
            "plugin",
            "update",
            metadata["plugin_id"],
        )
    else:
        raise ValueError("unsupported plugin platform")

    initial_payload = _decode(list_command, runner(list_command))
    if initial_payload is None:
        return _result(
            "preflight_failed",
            "plugin_list_preflight",
            target_version=target_version,
            target_tag=target_tag,
            target_commit=target_commit,
        )
    initial = _installed_plugin(
        initial_payload,
        metadata["plugin_id"],
        platform=platform,
    )
    if initial is None or not _installed_and_enabled(initial, platform=platform):
        return _result(
            "preflight_failed",
            "plugin_list_preflight",
            target_version=target_version,
            target_tag=target_tag,
            target_commit=target_commit,
        )
    initial_version = initial.get("version")
    try:
        initial_base = _base_version(initial_version, platform=platform)
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
    marketplace = _marketplace(
        marketplace_payload,
        metadata["marketplace"],
        platform=platform,
    )
    if not _source_is_supported(
        marketplace,
        metadata=metadata,
        remote_refs=remote_refs,
        target_commit=target_commit,
        metadata_path=metadata_path,
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

    upgrade_result = runner(upgrade_command)
    upgrade_succeeded = (
        _decode(upgrade_command, upgrade_result) is not None
        if platform == "codex"
        else _command_succeeded(upgrade_result)
    )
    if not upgrade_succeeded:
        return _result(
            "upgrade_failed",
            "marketplace_upgrade",
            target_version=target_version,
            target_tag=target_tag,
            target_commit=target_commit,
            installed=initial_version,
        )
    install_result = runner(install_command)
    install_succeeded = (
        _decode(install_command, install_result) is not None
        if platform == "codex"
        else _command_succeeded(install_result)
    )
    if not install_succeeded:
        return _result(
            "install_failed",
            "plugin_install",
            target_version=target_version,
            target_tag=target_tag,
            target_commit=target_commit,
            installed=initial_version,
        )

    final_payload = _decode(list_command, runner(list_command))
    final = (
        _installed_plugin(
            final_payload,
            metadata["plugin_id"],
            platform=platform,
        )
        if final_payload is not None
        else None
    )
    final_version = final.get("version") if final else None
    if (
        not final
        or not _installed_and_enabled(final, platform=platform)
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
            tag_checker.compare_versions(
                _base_version(final_version, platform=platform),
                target_version,
            )
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
    parser.add_argument(
        "--platform",
        choices=tuple(tag_checker.METADATA_PATHS),
        default="codex",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        if not args.remote_refs_stdin:
            raise ValueError("fresh remote refs are required")
        raw = sys.stdin.buffer.read(tag_checker.MAX_REMOTE_OUTPUT_BYTES + 1)
        if len(raw) > tag_checker.MAX_REMOTE_OUTPUT_BYTES:
            raise ValueError("remote refs are too large")
        result = run_update(
            remote_refs=raw.decode("utf-8"),
            metadata_path=tag_checker.metadata_path_for_platform(args.platform),
        )
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
