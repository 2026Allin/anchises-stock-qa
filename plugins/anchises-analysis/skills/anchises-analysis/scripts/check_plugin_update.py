#!/usr/bin/env python3
"""Check the fixed Git repository for a newer published Codex plugin tag."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Sequence


METADATA_PATH = Path(__file__).resolve().parents[1] / "references" / "plugin-release.json"
VERSION_PATTERN = (
    r"(?P<major>0|[1-9]\d*)\.(?P<minor>0|[1-9]\d*)\."
    r"(?P<patch>0|[1-9]\d*)"
    r"(?:-(?P<pre>[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?"
)
VERSION_RE = re.compile(rf"^{VERSION_PATTERN}$")
RELEASE_RE = re.compile(r"^codex\.\d{14}$")
OBJECT_ID_RE = re.compile(r"^(?:[0-9a-f]{40}|[0-9a-f]{64})$")
CHECK_TIMEOUT_SECONDS = 8
SUCCESS_CACHE_SECONDS = 3600
FAILURE_CACHE_SECONDS = 600
CACHE_SCHEMA_VERSION = 1
KNOWN_STATUSES = {
    "current",
    "update_available",
    "release_inconsistent",
    "unsupported_source",
    "unknown",
}
ALLOWED_IDENTITY = {
    "schema_version": 2,
    "name": "anchises-analysis",
    "platform": "codex",
    "plugin_id": "anchises-analysis@Anchises-Analysis",
    "marketplace": "Anchises-Analysis",
    "repository": "https://github.com/2026Allin/anchises-stock-qa.git",
    "git_ref": "main",
    "tag_prefix": "anchises-analysis/codex/v",
}
METADATA_KEYS = {*ALLOWED_IDENTITY, "version", "release_id"}
RESULT_KEYS = {
    "status",
    "installed_version",
    "target_version",
    "target_tag",
    "target_commit",
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
            timeout=CHECK_TIMEOUT_SECONDS,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return CommandResult(126, "", str(exc))
    return CommandResult(completed.returncode, completed.stdout, completed.stderr)


def _load_metadata(path: Path = METADATA_PATH) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict) or set(value) != METADATA_KEYS:
        raise ValueError("plugin release metadata has an unexpected shape")
    for key, expected in ALLOWED_IDENTITY.items():
        if value.get(key) != expected:
            raise ValueError(f"plugin release metadata has unsupported {key}")
    _version_parts(value.get("version"))
    release_id = value.get("release_id")
    if not isinstance(release_id, str) or not RELEASE_RE.fullmatch(release_id):
        raise ValueError("plugin release metadata has an invalid release_id")
    return value


def _version_parts(version: Any) -> tuple[tuple[int, int, int], list[str] | None]:
    if not isinstance(version, str):
        raise ValueError("version must be a valid SemVer base version")
    match = VERSION_RE.fullmatch(version)
    if not match:
        raise ValueError("version must be a valid SemVer base version")
    core = tuple(int(match.group(name)) for name in ("major", "minor", "patch"))
    prerelease = match.group("pre")
    return core, prerelease.split(".") if prerelease else None


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
            return (int(left_item) > int(right_item)) - (
                int(left_item) < int(right_item)
            )
        if left_numeric != right_numeric:
            return -1 if left_numeric else 1
        return (left_item > right_item) - (left_item < right_item)
    return (len(left) > len(right)) - (len(left) < len(right))


def compare_versions(left: str, right: str) -> int:
    """Compare two strict SemVer base versions."""

    left_core, left_pre = _version_parts(left)
    right_core, right_pre = _version_parts(right)
    if left_core != right_core:
        return (left_core > right_core) - (left_core < right_core)
    return _compare_identifiers(left_pre, right_pre)


def _result(
    status: str,
    installed_version: str,
    *,
    target_version: str | None = None,
    target_tag: str | None = None,
    target_commit: str | None = None,
) -> dict[str, Any]:
    if status not in KNOWN_STATUSES:
        raise ValueError("unknown plugin update status")
    return {
        "status": status,
        "installed_version": installed_version,
        "target_version": target_version,
        "target_tag": target_tag,
        "target_commit": target_commit,
    }


def _parse_remote_refs(
    output: str,
    *,
    branch_ref: str,
    tag_prefix: str,
) -> tuple[str, list[tuple[str, str, str]]]:
    direct: dict[str, str] = {}
    peeled: dict[str, str] = {}
    for raw_line in output.splitlines():
        parts = raw_line.split("\t")
        if len(parts) != 2:
            raise ValueError("git ls-remote returned an invalid line")
        object_id, ref = parts
        if not OBJECT_ID_RE.fullmatch(object_id):
            raise ValueError("git ls-remote returned an invalid object ID")
        if ref.endswith("^{}"):
            base_ref = ref[:-3]
            if base_ref in peeled and peeled[base_ref] != object_id:
                raise ValueError("git ls-remote returned duplicate peeled refs")
            peeled[base_ref] = object_id
            continue
        if ref in direct and direct[ref] != object_id:
            raise ValueError("git ls-remote returned duplicate refs")
        direct[ref] = object_id

    branch_commit = direct.get(branch_ref)
    if branch_commit is None:
        raise ValueError("release branch was not found")

    tag_re = re.compile(
        rf"^refs/tags/(?P<tag>{re.escape(tag_prefix)}(?P<version>{VERSION_PATTERN}))$"
    )
    tags: list[tuple[str, str, str]] = []
    for ref, object_id in direct.items():
        match = tag_re.fullmatch(ref)
        if match is None:
            continue
        version = match.group("version")
        _version_parts(version)
        tags.append((version, match.group("tag"), peeled.get(ref, object_id)))
    return branch_commit, tags


def _latest_tag(tags: Sequence[tuple[str, str, str]]) -> tuple[str, str, str] | None:
    latest: tuple[str, str, str] | None = None
    for candidate in tags:
        if latest is None or compare_versions(candidate[0], latest[0]) > 0:
            latest = candidate
    return latest


def _default_cache_path() -> Path:
    uid = str(os.getuid()) if hasattr(os, "getuid") else "user"
    return Path(tempfile.gettempdir()) / f"anchises-analysis-codex-tags-{uid}.json"


def _valid_cached_result(value: Any, installed_version: str) -> bool:
    if not isinstance(value, dict) or set(value) != RESULT_KEYS:
        return False
    if value.get("status") not in KNOWN_STATUSES:
        return False
    if value.get("installed_version") != installed_version:
        return False
    for key in ("target_version", "target_tag", "target_commit"):
        if value.get(key) is not None and not isinstance(value.get(key), str):
            return False
    return True


def _read_cache(
    path: Path,
    *,
    installed_version: str,
    now: float,
) -> dict[str, Any] | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(value, dict) or value.get("schema_version") != CACHE_SCHEMA_VERSION:
        return None
    checked_at = value.get("checked_at")
    result = value.get("result")
    if not isinstance(checked_at, (int, float)):
        return None
    if not _valid_cached_result(result, installed_version):
        return None
    ttl = (
        FAILURE_CACHE_SECONDS
        if result["status"] in {"unknown", "release_inconsistent"}
        else SUCCESS_CACHE_SECONDS
    )
    if checked_at > now or now - checked_at >= ttl:
        return None
    return dict(result)


def _write_cache(path: Path, *, result: dict[str, Any], now: float) -> None:
    payload = {
        "schema_version": CACHE_SCHEMA_VERSION,
        "checked_at": now,
        "result": result,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, separators=(",", ":"), sort_keys=True)
            handle.write("\n")
        os.chmod(temporary, 0o600)
        os.replace(temporary, path)
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass


def check_for_update(
    *,
    metadata_path: Path = METADATA_PATH,
    runner: Runner = _default_runner,
    cache_path: Path | None = None,
    refresh: bool = False,
    use_cache: bool = True,
    now: float | None = None,
) -> dict[str, Any]:
    """Return a structured, fail-closed comparison with published Codex tags."""

    metadata = _load_metadata(metadata_path)
    installed_version = metadata["version"]
    current_time = time.time() if now is None else now
    selected_cache = cache_path or _default_cache_path()
    if use_cache and not refresh:
        cached = _read_cache(
            selected_cache,
            installed_version=installed_version,
            now=current_time,
        )
        if cached is not None:
            cached["cache"] = "hit"
            return cached

    branch_ref = f"refs/heads/{metadata['git_ref']}"
    tag_pattern = f"refs/tags/{metadata['tag_prefix']}*"
    command = (
        "git",
        "ls-remote",
        metadata["repository"],
        branch_ref,
        tag_pattern,
    )
    command_result = runner(command)
    if command_result.returncode != 0:
        result = _result("unknown", installed_version)
    else:
        try:
            branch_commit, tags = _parse_remote_refs(
                command_result.stdout,
                branch_ref=branch_ref,
                tag_prefix=metadata["tag_prefix"],
            )
            latest = _latest_tag(tags)
            if latest is None or compare_versions(latest[0], installed_version) <= 0:
                result = _result("current", installed_version)
            elif latest[2] != branch_commit:
                result = _result(
                    "release_inconsistent",
                    installed_version,
                    target_version=latest[0],
                    target_tag=latest[1],
                    target_commit=latest[2],
                )
            else:
                result = _result(
                    "update_available",
                    installed_version,
                    target_version=latest[0],
                    target_tag=latest[1],
                    target_commit=latest[2],
                )
        except ValueError:
            result = _result("unknown", installed_version)

    if use_cache:
        try:
            _write_cache(selected_cache, result=result, now=current_time)
        except OSError:
            pass
    result = dict(result)
    result["cache"] = "miss"
    return result


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--refresh", action="store_true")
    parser.add_argument("--no-cache", action="store_true")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        result = check_for_update(
            refresh=args.refresh,
            use_cache=not args.no_cache,
        )
    except (OSError, ValueError, json.JSONDecodeError):
        result = {
            "status": "unknown",
            "installed_version": None,
            "target_version": None,
            "target_tag": None,
            "target_commit": None,
            "cache": "miss",
        }
    print(json.dumps(result, separators=(",", ":"), sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
