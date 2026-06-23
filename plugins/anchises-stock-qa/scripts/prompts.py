"""Prompt bundle loading for Anchises Stock QA."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from config import PLUGIN_ROOT, StockQAConfig, load_config


PROMPT_DIR = PLUGIN_ROOT / "prompts"
PROMPT_FILES = (
    "query-planning.md",
    "sql-generation.md",
    "csv-analysis.md",
    "final-answer.md",
)


def get_prompt_bundle(config: StockQAConfig | None = None) -> Dict[str, Any]:
    active_config = config or load_config(require_database_url=False)
    prompts: List[Dict[str, str]] = []
    override_dir = active_config.prompts.override_dir

    for name in PROMPT_FILES:
        override_path = override_dir / name if override_dir else None
        if override_path and override_path.exists():
            path = override_path
            source = "override"
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
        "override_dir": str(override_dir) if override_dir else "",
        "built_in_dir": str(PROMPT_DIR),
        "prompts": prompts,
    }
