"""Prompt bundle loading for Stock Data Desk."""

from __future__ import annotations

import difflib
import hashlib
import os
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Sequence

from config import PLUGIN_ROOT


PROMPT_DIR = PLUGIN_ROOT / "prompts"
USER_PROMPT_DIR = Path.home() / ".config" / "anchises-stock-qa" / "prompts"
PROMPT_FILES = (
    "query-planning.md",
    "sql-generation.md",
    "csv-analysis.md",
    "final-answer.md",
)
PROMPT_METADATA: Dict[str, Dict[str, str]] = {
    "query-planning.md": {
        "title": "Query Planning",
        "purpose": (
            "Turns a user's stock question into a concrete query plan, including "
            "exchange scope, date handling, filters, and which tables are needed."
        ),
        "when_to_edit": (
            "Edit this when you want to change question interpretation, default "
            "screening assumptions, date interpretation, or exchange handling."
        ),
    },
    "sql-generation.md": {
        "title": "SQL Generation",
        "purpose": (
            "Controls how Codex writes safe read-only SQL from the query plan and "
            "schema context."
        ),
        "when_to_edit": (
            "Edit this when you want to change SQL strategy, table union behavior, "
            "field mapping, or safety guidance."
        ),
    },
    "csv-analysis.md": {
        "title": "CSV Analysis",
        "purpose": (
            "Controls how Codex analyzes exported CSV data with pandas, including "
            "filtering, scoring, shell-risk checks, and result CSV creation."
        ),
        "when_to_edit": (
            "Edit this when you want to change scoring formulas, filter logic, "
            "shell-risk behavior, Top 30 selection, or saved result rules."
        ),
    },
    "final-answer.md": {
        "title": "Final Answer",
        "purpose": (
            "Controls the visible markdown answer shown to the user, including "
            "section order, tone, tables, caveats, file references, and takeaways."
        ),
        "when_to_edit": (
            "Edit this when you want to change answer length, language, tone, "
            "section order, table display, disclaimers, or bilingual output."
        ),
    },
}


def _user_prompt_dir() -> Path:
    return USER_PROMPT_DIR


def _normalize_prompt_name(name: str) -> str:
    raw = str(name or "").strip()
    if not raw:
        raise ValueError("prompt_name is required")
    prompt_name = Path(raw).name
    if not prompt_name.endswith(".md"):
        prompt_name = f"{prompt_name}.md"
    if prompt_name not in PROMPT_FILES:
        allowed = ", ".join(PROMPT_FILES)
        raise ValueError(f"Unknown prompt file: {raw}. Allowed prompt files: {allowed}")
    return prompt_name


def _normalize_prompt_names(names: Sequence[str] | None) -> List[str]:
    if not names:
        return list(PROMPT_FILES)
    normalized: List[str] = []
    for name in names:
        prompt_name = _normalize_prompt_name(name)
        if prompt_name not in normalized:
            normalized.append(prompt_name)
    return normalized


def _atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=str(path.parent),
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(content)
        os.replace(tmp_path, path)
    except Exception:
        try:
            os.unlink(tmp_path)
        except FileNotFoundError:
            pass
        raise


def _sha256_text(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def _preview_text(content: str, max_chars: int) -> str:
    if max_chars <= 0:
        return ""
    if len(content) <= max_chars:
        return content
    return content[:max_chars].rstrip() + "\n..."


def _prompt_paths(name: str) -> Dict[str, Path]:
    user_prompt_dir = _user_prompt_dir()
    return {
        "built_in": PROMPT_DIR / name,
        "user": user_prompt_dir / name,
    }


def _read_prompt_state(name: str) -> Dict[str, Any]:
    paths = _prompt_paths(name)
    built_in_path = paths["built_in"]
    user_path = paths["user"]
    built_in_content = built_in_path.read_text(encoding="utf-8")
    user_file_exists = user_path.exists()
    user_content = user_path.read_text(encoding="utf-8") if user_file_exists else ""
    active_content = user_content if user_file_exists else built_in_content
    active_path = user_path if user_file_exists else built_in_path
    active_source = "custom" if user_file_exists else "built-in"

    return {
        "name": name,
        "metadata": PROMPT_METADATA[name],
        "active_source": active_source,
        "active_path": active_path,
        "active_content": active_content,
        "active_hash": _sha256_text(active_content),
        "built_in_path": built_in_path,
        "built_in_content": built_in_content,
        "built_in_hash": _sha256_text(built_in_content),
        "user_path": user_path,
        "user_file_exists": user_file_exists,
        "user_content": user_content,
        "user_hash": _sha256_text(user_content) if user_file_exists else "",
    }


def get_prompt_bundle() -> Dict[str, Any]:
    prompts: List[Dict[str, str]] = []
    user_prompt_dir = _user_prompt_dir()

    for name in PROMPT_FILES:
        user_path = user_prompt_dir / name
        if user_path.exists():
            path = user_path
            source = "custom"
        else:
            path = PROMPT_DIR / name
            source = "built-in"
        prompts.append(
            {
                "name": name,
                "source": source,
                "path": str(path),
                "content": path.read_text(encoding="utf-8"),
            }
        )

    return {
        "user_prompt_dir": str(user_prompt_dir),
        "built_in_dir": str(PROMPT_DIR),
        "available_prompt_files": list(PROMPT_FILES),
        "prompts": prompts,
        "customization": {
            "upgrade_safe": True,
            "user_files_take_precedence": True,
            "missing_user_files_fall_back_to_built_in": True,
            "manage_with_tools": [
                "get_prompt_catalog",
                "read_custom_prompt",
                "preview_custom_prompt_update",
                "list_custom_prompts",
                "initialize_custom_prompts",
                "write_custom_prompt",
                "reset_custom_prompt",
            ],
        },
    }


def get_prompt_catalog(
    include_preview: bool = True,
    preview_chars: int = 500,
) -> Dict[str, Any]:
    prompts: List[Dict[str, Any]] = []

    for name in PROMPT_FILES:
        state = _read_prompt_state(name)
        item = {
            "name": name,
            "title": state["metadata"]["title"],
            "purpose": state["metadata"]["purpose"],
            "when_to_edit": state["metadata"]["when_to_edit"],
            "active_source": state["active_source"],
            "active_path": str(state["active_path"]),
            "active_hash": state["active_hash"],
            "built_in_path": str(state["built_in_path"]),
            "user_path": str(state["user_path"]),
            "user_file_exists": state["user_file_exists"],
            "editable": True,
        }
        if include_preview:
            item["preview"] = _preview_text(state["active_content"], preview_chars)
        prompts.append(item)

    return {
        "ok": True,
        "built_in_dir": str(PROMPT_DIR),
        "user_prompt_dir": str(_user_prompt_dir()),
        "available_prompt_files": list(PROMPT_FILES),
        "prompts": prompts,
        "workflow": [
            "Show this catalog to the user before editing prompts.",
            "Ask which prompt they want to change and what behavior they want.",
            "Read the selected prompt with read_custom_prompt.",
            "Propose a specific edit and preview it with preview_custom_prompt_update.",
            "Only write with write_custom_prompt after the user confirms.",
        ],
    }


def read_custom_prompt(prompt_name: str) -> Dict[str, Any]:
    name = _normalize_prompt_name(prompt_name)
    state = _read_prompt_state(name)
    return {
        "ok": True,
        "name": name,
        "title": state["metadata"]["title"],
        "purpose": state["metadata"]["purpose"],
        "when_to_edit": state["metadata"]["when_to_edit"],
        "active_source": state["active_source"],
        "active_path": str(state["active_path"]),
        "active_hash": state["active_hash"],
        "active_content": state["active_content"],
        "built_in_path": str(state["built_in_path"]),
        "built_in_hash": state["built_in_hash"],
        "built_in_content": state["built_in_content"],
        "user_path": str(state["user_path"]),
        "user_file_exists": state["user_file_exists"],
        "user_hash": state["user_hash"],
        "user_content": state["user_content"],
    }


def preview_custom_prompt_update(prompt_name: str, content: str) -> Dict[str, Any]:
    name = _normalize_prompt_name(prompt_name)
    if not str(content or "").strip():
        raise ValueError("content must not be empty")

    state = _read_prompt_state(name)
    new_content = str(content)
    diff = "".join(
        difflib.unified_diff(
            state["active_content"].splitlines(keepends=True),
            new_content.splitlines(keepends=True),
            fromfile=f"{name} ({state['active_source']})",
            tofile=f"{name} (proposed custom)",
        )
    )

    return {
        "ok": True,
        "name": name,
        "title": state["metadata"]["title"],
        "active_source": state["active_source"],
        "active_path": str(state["active_path"]),
        "target_path": str(state["user_path"]),
        "will_create_user_file": not state["user_file_exists"],
        "will_update_user_file": state["user_file_exists"],
        "current_hash": state["active_hash"],
        "new_hash": _sha256_text(new_content),
        "changed": state["active_content"] != new_content,
        "diff": diff,
    }


def list_custom_prompts() -> Dict[str, Any]:
    user_prompt_dir = _user_prompt_dir()
    prompts: List[Dict[str, Any]] = []

    for name in PROMPT_FILES:
        state = _read_prompt_state(name)
        prompts.append(
            {
                "name": name,
                "title": state["metadata"]["title"],
                "purpose": state["metadata"]["purpose"],
                "when_to_edit": state["metadata"]["when_to_edit"],
                "active_source": state["active_source"],
                "active_hash": state["active_hash"],
                "built_in_path": str(state["built_in_path"]),
                "user_path": str(state["user_path"]),
                "user_file_exists": state["user_file_exists"],
                "user_size_bytes": state["user_path"].stat().st_size
                if state["user_file_exists"]
                else 0,
                "editable": True,
            }
        )

    return {
        "ok": True,
        "built_in_dir": str(PROMPT_DIR),
        "user_prompt_dir": str(user_prompt_dir),
        "available_prompt_files": list(PROMPT_FILES),
        "prompts": prompts,
        "upgrade_safe": True,
        "note": (
            "Custom prompt files live outside the plugin install. Plugin upgrades "
            "replace built-in prompt files but do not overwrite these user files."
        ),
    }


def initialize_custom_prompts(
    prompt_names: Sequence[str] | None = None,
    *,
    overwrite: bool = False,
) -> Dict[str, Any]:
    user_prompt_dir = _user_prompt_dir()
    user_prompt_dir.mkdir(parents=True, exist_ok=True)
    selected_names = _normalize_prompt_names(prompt_names)
    results: List[Dict[str, Any]] = []

    for name in selected_names:
        built_in_path = PROMPT_DIR / name
        user_path = user_prompt_dir / name
        existed = user_path.exists()
        if existed and not overwrite:
            status = "skipped_existing"
        else:
            _atomic_write(
                user_path,
                built_in_path.read_text(encoding="utf-8"),
            )
            status = "overwritten" if existed else "created"
        results.append(
            {
                "name": name,
                "status": status,
                "built_in_path": str(built_in_path),
                "user_path": str(user_path),
            }
        )

    return {
        "ok": True,
        "user_prompt_dir": str(user_prompt_dir),
        "overwrite": overwrite,
        "prompts": results,
    }


def write_custom_prompt(
    prompt_name: str,
    content: str,
    expected_current_hash: str = "",
) -> Dict[str, Any]:
    user_prompt_dir = _user_prompt_dir()
    name = _normalize_prompt_name(prompt_name)
    if not str(content or "").strip():
        raise ValueError("content must not be empty")

    state = _read_prompt_state(name)
    expected_hash = str(expected_current_hash or "").strip()
    if expected_hash and expected_hash != state["active_hash"]:
        raise ValueError(
            "Current prompt content changed after preview. "
            "Read the prompt again before writing."
        )

    user_path = user_prompt_dir / name
    existed = user_path.exists()
    _atomic_write(user_path, str(content))
    new_content = user_path.read_text(encoding="utf-8")

    return {
        "ok": True,
        "name": name,
        "status": "updated" if existed else "created",
        "user_prompt_dir": str(user_prompt_dir),
        "user_path": str(user_path),
        "bytes": user_path.stat().st_size,
        "active_source": "custom",
        "previous_hash": state["active_hash"],
        "current_hash": _sha256_text(new_content),
    }


def reset_custom_prompt(
    prompt_name: str,
) -> Dict[str, Any]:
    user_prompt_dir = _user_prompt_dir()
    name = _normalize_prompt_name(prompt_name)
    user_path = user_prompt_dir / name
    existed = user_path.exists()
    if existed:
        user_path.unlink()

    return {
        "ok": True,
        "name": name,
        "status": "deleted" if existed else "already_built_in",
        "user_prompt_dir": str(user_prompt_dir),
        "user_path": str(user_path),
        "active_source": "built-in",
    }
