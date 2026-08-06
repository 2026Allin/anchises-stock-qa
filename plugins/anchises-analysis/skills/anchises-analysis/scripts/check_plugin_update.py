#!/usr/bin/env python3
"""Parse fixed Git refs and cache the Anchises Codex plugin release state.

This helper is deliberately network-free. The owning Skill must execute the
allowlisted ``git ls-remote`` command directly, then pipe its stdout to this
script with ``--remote-refs-stdin``.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Sequence


METADATA_PATH = Path(__file__).resolve().parents[1] / "references" / "plugin-release.json"
VERSION_PATTERN = (
    r"(?P<major>0|[1-9]\d*)\.(?P<minor>0|[1-9]\d*)\."
    r"(?P<patch>0|[1-9]\d*)"
    r"(?:-(?P<pre>[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?"
)
VERSION_RE = re.compile(rf"^{VERSION_PATTERN}$")
RELEASE_RE = re.compile(r"^codex\.\d{14}$")
OBJECT_ID_RE = re.compile(r"^(?:[0-9a-f]{40}|[0-9a-f]{64})$")
MAX_REMOTE_OUTPUT_BYTES = 1024 * 1024
SUCCESS_CACHE_SECONDS = 3600
FAILURE_CACHE_SECONDS = 600
CACHE_SCHEMA_VERSION = 2
CHECK_REQUIRED = "check_required"
KNOWN_STATUSES = {
    CHECK_REQUIRED,
    "current",
    "update_available",
    "release_inconsistent",
    "unsupported_source",
    "unknown",
}
KNOWN_REASONS = {
    None,
    "cache_miss",
    "empty_remote_refs",
    "invalid_remote_refs",
    "remote_refs_too_large",
    "release_validation",
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
    "reason",
    "installed_version",
    "target_version",
    "target_tag",
    "target_commit",
}
RELEASE_CHECK_JUSTIFICATION = (
    "允许只读检查 Anchises Analysis 的已发布版本吗？"
)


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


def release_check_command(
    metadata_path: Path = METADATA_PATH,
) -> tuple[str, ...]:
    """Return the only network command the Skill may use for Tag discovery."""

    metadata = _load_metadata(metadata_path)
    return ("git", "ls-remote", "--", metadata["repository"])


def release_check_prefix_rule(
    metadata_path: Path = METADATA_PATH,
) -> tuple[str, ...]:
    """Return the narrow reusable approval prefix for release discovery."""

    return release_check_command(metadata_path)


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
    installed_version: str | None,
    *,
    reason: str | None = None,
    target_version: str | None = None,
    target_tag: str | None = None,
    target_commit: str | None = None,
) -> dict[str, Any]:
    if status not in KNOWN_STATUSES:
        raise ValueError("unknown plugin update status")
    if reason not in KNOWN_REASONS:
        raise ValueError("unknown plugin update reason")
    return {
        "status": status,
        "reason": reason,
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
    if value.get("status") not in KNOWN_STATUSES - {CHECK_REQUIRED}:
        return False
    if value.get("reason") not in KNOWN_REASONS:
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
    installed_version = result.get("installed_version")
    if not isinstance(installed_version, str) or not _valid_cached_result(
        result,
        installed_version,
    ):
        raise ValueError("refusing to cache an invalid release result")
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


def check_cached_result(
    *,
    metadata_path: Path = METADATA_PATH,
    cache_path: Path | None = None,
    use_cache: bool = True,
    now: float | None = None,
) -> dict[str, Any]:
    """Return a valid cached result or request one direct remote lookup."""

    metadata = _load_metadata(metadata_path)
    installed_version = metadata["version"]
    current_time = time.time() if now is None else now
    if use_cache:
        cached = _read_cache(
            cache_path or _default_cache_path(),
            installed_version=installed_version,
            now=current_time,
        )
        if cached is not None:
            cached["cache"] = "hit"
            return cached
    result = _result(
        CHECK_REQUIRED,
        installed_version,
        reason="cache_miss",
    )
    result["cache"] = "miss"
    return result


def check_remote_refs(
    remote_output: str,
    *,
    metadata_path: Path = METADATA_PATH,
    cache_path: Path | None = None,
    use_cache: bool = True,
    now: float | None = None,
) -> dict[str, Any]:
    """Validate captured ``git ls-remote`` output without opening the network."""

    metadata = _load_metadata(metadata_path)
    installed_version = metadata["version"]
    current_time = time.time() if now is None else now
    encoded_size = len(remote_output.encode("utf-8"))
    if encoded_size > MAX_REMOTE_OUTPUT_BYTES:
        result = _result(
            "unknown",
            installed_version,
            reason="remote_refs_too_large",
        )
    elif not remote_output.strip():
        result = _result(
            "unknown",
            installed_version,
            reason="empty_remote_refs",
        )
    else:
        branch_ref = f"refs/heads/{metadata['git_ref']}"
        try:
            branch_commit, tags = _parse_remote_refs(
                remote_output,
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
            result = _result(
                "unknown",
                installed_version,
                reason="invalid_remote_refs",
            )

    if use_cache:
        try:
            _write_cache(
                cache_path or _default_cache_path(),
                result=result,
                now=current_time,
            )
        except OSError:
            pass
    result = dict(result)
    result["cache"] = "miss"
    return result


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--cache-only", action="store_true")
    mode.add_argument("--remote-refs-stdin", action="store_true")
    parser.add_argument("--no-cache", action="store_true")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        if args.remote_refs_stdin:
            raw = sys.stdin.buffer.read(MAX_REMOTE_OUTPUT_BYTES + 1)
            if len(raw) > MAX_REMOTE_OUTPUT_BYTES:
                remote_output = "x" * (MAX_REMOTE_OUTPUT_BYTES + 1)
            else:
                remote_output = raw.decode("utf-8")
            result = check_remote_refs(
                remote_output,
                use_cache=not args.no_cache,
            )
        else:
            result = check_cached_result(use_cache=not args.no_cache)
    except (OSError, UnicodeDecodeError, ValueError, json.JSONDecodeError):
        result = _result(
            "unknown",
            None,
            reason="release_validation",
        )
        result["cache"] = "miss"
    print(json.dumps(result, separators=(",", ":"), sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
