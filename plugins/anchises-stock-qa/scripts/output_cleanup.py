"""Output cleanup helpers for Anchises Stock QA."""

from __future__ import annotations

import json
import shutil
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List

from config import OutputsConfig


STATE_FILE = ".cleanup_state.json"


@dataclass(frozen=True)
class CleanupCandidate:
    path: Path
    created_at: datetime
    size_bytes: int


def maybe_cleanup_outputs(outputs: OutputsConfig) -> Dict[str, Any]:
    if not outputs.cleanup_enabled:
        return {
            "cleanup_ran": False,
            "reason": "disabled",
            "cleanup_enabled": False,
            "outputs_root": str(outputs.dir),
        }

    state = _read_state(outputs.dir)
    now = datetime.now(timezone.utc)
    last_cleanup = _parse_datetime(state.get("last_cleanup_utc", ""))
    if last_cleanup:
        next_due = last_cleanup + timedelta(days=outputs.cleanup_interval_days)
        if now < next_due:
            return {
                "cleanup_ran": False,
                "reason": "not_due",
                "cleanup_enabled": True,
                "last_cleanup_utc": last_cleanup.isoformat(),
                "next_cleanup_after_utc": next_due.isoformat(),
                "outputs_root": str(outputs.dir),
            }

    return cleanup_outputs(outputs, dry_run=False)


def cleanup_outputs(outputs: OutputsConfig, *, dry_run: bool = True) -> Dict[str, Any]:
    root = outputs.dir
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=outputs.retention_days)
    candidates = [
        candidate
        for candidate in _iter_cleanup_candidates(root)
        if candidate.created_at < cutoff
    ]
    total_bytes = sum(candidate.size_bytes for candidate in candidates)
    deleted: List[Dict[str, Any]] = []
    errors: List[Dict[str, str]] = []

    if not dry_run:
        root.mkdir(parents=True, exist_ok=True)
        for candidate in candidates:
            try:
                shutil.rmtree(candidate.path)
                deleted.append(_candidate_as_dict(candidate))
            except Exception as exc:  # pragma: no cover - filesystem dependent
                errors.append({"path": str(candidate.path), "error": str(exc)})
        _write_state(
            root,
            {
                "last_cleanup_utc": now.isoformat(),
                "retention_days": outputs.retention_days,
                "cleanup_interval_days": outputs.cleanup_interval_days,
                "deleted_run_dirs": len(deleted),
                "deleted_bytes": sum(item["size_bytes"] for item in deleted),
                "error_count": len(errors),
            },
        )

    return {
        "cleanup_ran": not dry_run,
        "dry_run": dry_run,
        "cleanup_enabled": outputs.cleanup_enabled,
        "outputs_root": str(root),
        "retention_days": outputs.retention_days,
        "cleanup_interval_days": outputs.cleanup_interval_days,
        "cutoff_utc": cutoff.isoformat(),
        "candidate_run_dirs": len(candidates),
        "candidate_bytes": total_bytes,
        "deleted_run_dirs": len(deleted),
        "deleted_bytes": sum(item["size_bytes"] for item in deleted),
        "candidates": [_candidate_as_dict(candidate) for candidate in candidates[:200]],
        "candidate_list_truncated": len(candidates) > 200,
        "errors": errors,
        "next_cleanup_after_utc": (
            now + timedelta(days=outputs.cleanup_interval_days)
        ).isoformat(),
    }


def _iter_cleanup_candidates(root: Path) -> Iterable[CleanupCandidate]:
    if not root.exists():
        return []
    candidates: List[CleanupCandidate] = []
    for conversation_dir in root.iterdir():
        if not conversation_dir.is_dir() or conversation_dir.name.startswith("."):
            continue
        for run_dir in conversation_dir.iterdir():
            if not run_dir.is_dir():
                continue
            metadata_path = run_dir / "metadata.json"
            if not metadata_path.exists():
                continue
            created_at = _created_at(metadata_path, run_dir)
            candidates.append(
                CleanupCandidate(
                    path=run_dir,
                    created_at=created_at,
                    size_bytes=_directory_size(run_dir),
                )
            )
    return candidates


def _created_at(metadata_path: Path, run_dir: Path) -> datetime:
    try:
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        created = _parse_datetime(str(metadata.get("created_at_utc", "")))
        if created:
            return created
    except Exception:
        pass
    return datetime.fromtimestamp(run_dir.stat().st_mtime, tz=timezone.utc)


def _parse_datetime(value: str) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _directory_size(path: Path) -> int:
    total = 0
    for item in path.rglob("*"):
        if item.is_file():
            try:
                total += item.stat().st_size
            except OSError:
                continue
    return total


def _candidate_as_dict(candidate: CleanupCandidate) -> Dict[str, Any]:
    return {
        "path": str(candidate.path),
        "created_at_utc": candidate.created_at.isoformat(),
        "size_bytes": candidate.size_bytes,
    }


def _read_state(root: Path) -> Dict[str, Any]:
    state_path = root / STATE_FILE
    if not state_path.exists():
        return {}
    try:
        return json.loads(state_path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _write_state(root: Path, state: Dict[str, Any]) -> None:
    root.mkdir(parents=True, exist_ok=True)
    (root / STATE_FILE).write_text(
        json.dumps(state, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
