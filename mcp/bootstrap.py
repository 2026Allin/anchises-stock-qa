#!/usr/bin/env python3
"""Bootstrap the plugin-local Python runtime, then start the MCP server."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


PLUGIN_ROOT = Path(__file__).resolve().parent.parent
VENV_DIR = PLUGIN_ROOT / ".venv"
REQUIREMENTS = PLUGIN_ROOT / "requirements.txt"
SERVER = PLUGIN_ROOT / "mcp" / "server.py"
INSTALL_MARKER = VENV_DIR / ".anchises-stock-qa-requirements-installed"


def _venv_python() -> Path:
    if os.name == "nt":
        return VENV_DIR / "Scripts" / "python.exe"
    return VENV_DIR / "bin" / "python"


def _ensure_venv() -> Path:
    python = _venv_python()
    if not python.exists():
        subprocess.check_call([sys.executable, "-m", "venv", str(VENV_DIR)])
    requirements_mtime = str(REQUIREMENTS.stat().st_mtime_ns)
    if not INSTALL_MARKER.exists() or INSTALL_MARKER.read_text() != requirements_mtime:
        subprocess.check_call(
            [
                str(python),
                "-m",
                "pip",
                "install",
                "--disable-pip-version-check",
                "-r",
                str(REQUIREMENTS),
            ],
            cwd=str(PLUGIN_ROOT),
        )
        INSTALL_MARKER.write_text(requirements_mtime)
    return python


def main() -> None:
    python = _ensure_venv()
    os.execv(str(python), [str(python), str(SERVER)])


if __name__ == "__main__":
    main()
