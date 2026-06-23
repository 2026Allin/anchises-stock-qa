#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLUGIN_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-python3}"

DEFAULT_CONFIG_PATH="${HOME}/.config/anchises-stock-qa/config.toml"
DEFAULT_OUTPUTS_DIR="~/.local/share/anchises-stock-qa/outputs"
DEFAULT_REMOTE_API_URL="https://anchisesdata.com/anchises-stock-qa"

CONFIG_PATH="${DEFAULT_CONFIG_PATH}"
REMOTE_API_URL="${DEFAULT_REMOTE_API_URL}"
REMOTE_API_URL_SET="false"
API_TOKEN=""
OUTPUTS_DIR="${DEFAULT_OUTPUTS_DIR}"
CLEANUP_ENABLED="true"
CLEANUP_INTERVAL_DAYS="7"
RETENTION_DAYS="30"
PROMPT_OVERRIDE_DIR=""
FORCE="false"
PRINT_CONFIG="false"
PREPARE_RUNTIME="false"

usage() {
  cat <<'EOF'
Create ~/.config/anchises-stock-qa/config.toml without sudo.

Usage:
  bash scripts/init_config.sh [options]

Options:
  --config PATH                 Config file to create.
                                Defaults to ~/.config/anchises-stock-qa/config.toml
  --remote-api-url URL          Anchises Stock QA API URL.
                                Defaults to https://anchisesdata.com/anchises-stock-qa
  --api-token TOKEN             Your Anchises Stock QA API token. If omitted, prompts for it.
  --outputs-dir PATH            Directory for exported CSV files.
                                Defaults to ~/.local/share/anchises-stock-qa/outputs
  --cleanup-enabled true|false  Enable automatic lazy cleanup. Defaults to true.
  --cleanup-interval-days N     Run automatic cleanup at most once per N days. Defaults to 7.
  --retention-days N            Delete output run directories older than N days. Defaults to 30.
  --prompt-override-dir PATH    Optional directory containing user-edited prompt markdown files.
  --prepare-runtime             Create/update the plugin Python runtime now.
                                This installs pandas and MCP dependencies into the plugin .venv.
  --force                       Overwrite an existing config file.
  --print                       Print config text instead of writing it.
  -h, --help                    Show this help.

Examples:
  bash scripts/init_config.sh
  bash scripts/init_config.sh --prepare-runtime
  bash scripts/init_config.sh --api-token 'your_token_here'
  bash scripts/init_config.sh --api-token 'new_token_here'
  bash scripts/init_config.sh --remote-api-url 'https://example.com/anchises-stock-qa'
EOF
}

need_value() {
  local option="$1"
  local value="${2-}"
  if [[ -z "${value}" || "${value}" == --* ]]; then
    echo "${option} requires a value." >&2
    exit 2
  fi
}

expand_leading_tilde() {
  local value="$1"
  if [[ "${value}" == "~" ]]; then
    printf '%s\n' "${HOME}"
  elif [[ "${value}" == "~/"* ]]; then
    printf '%s/%s\n' "${HOME}" "${value#~/}"
  else
    printf '%s\n' "${value}"
  fi
}

toml_string() {
  local value="$1"
  if [[ "${value}" == *$'\n'* || "${value}" == *$'\r'* ]]; then
    echo "Config values must not contain newlines." >&2
    exit 2
  fi
  value="${value//\\/\\\\}"
  value="${value//\"/\\\"}"
  printf '"%s"' "${value}"
}

is_positive_int() {
  [[ "$1" =~ ^[1-9][0-9]*$ ]]
}

build_config() {
  cat <<EOF
[backend]
mode = "remote_api"
api_base_url = $(toml_string "${REMOTE_API_URL}")
api_token = $(toml_string "${API_TOKEN}")

[database]
url = ""
access_mode = "readonly"

[outputs]
dir = $(toml_string "${OUTPUTS_DIR}")
cleanup_enabled = ${CLEANUP_ENABLED}
cleanup_interval_days = ${CLEANUP_INTERVAL_DAYS}
retention_days = ${RETENTION_DAYS}

[prompts]
override_dir = $(toml_string "${PROMPT_OVERRIDE_DIR}")

[exchanges.aliases]
# Optional natural-language aliases for exchange codes discovered from table names.
# "London" = "lse"
# "伦敦" = "lse"

EOF
}

update_existing_config_token() {
  python3 - "${CONFIG_PATH}" "${API_TOKEN}" "${REMOTE_API_URL}" "${REMOTE_API_URL_SET}" <<'PY'
from __future__ import annotations

import os
import re
import sys
import tempfile

path, api_token, remote_api_url, remote_api_url_set = sys.argv[1:5]
remote_api_url_was_set = remote_api_url_set == "true"


def toml_string(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def parse_toml_string(raw: str) -> str:
    raw = raw.strip()
    try:
        try:
            import tomllib
        except ModuleNotFoundError:
            import tomli as tomllib  # type: ignore[no-redef]
        parsed = tomllib.loads(f"value = {raw}\n")["value"]
        return str(parsed)
    except Exception:
        return raw.strip('"')


def section_bounds(lines: list[str], name: str) -> tuple[int, int] | None:
    header = re.compile(r"^\s*\[" + re.escape(name) + r"\]\s*(?:#.*)?$")
    any_header = re.compile(r"^\s*\[[^\]]+\]\s*(?:#.*)?$")
    start = None
    for index, line in enumerate(lines):
        if header.match(line):
            start = index
            break
    if start is None:
        return None
    end = len(lines)
    for index in range(start + 1, len(lines)):
        if any_header.match(lines[index]):
            end = index
            break
    return start, end


def ensure_section(lines: list[str], name: str) -> tuple[int, int]:
    bounds = section_bounds(lines, name)
    if bounds is not None:
        return bounds
    if lines and not lines[-1].endswith("\n"):
        lines[-1] += "\n"
    if lines and lines[-1].strip():
        lines.append("\n")
    lines.append(f"[{name}]\n")
    return len(lines) - 1, len(lines)


def get_key(lines: list[str], bounds: tuple[int, int], key: str) -> str:
    key_pattern = re.compile(r"^\s*" + re.escape(key) + r"\s*=\s*(.*?)\s*(?:#.*)?$")
    start, end = bounds
    for line in lines[start + 1 : end]:
        match = key_pattern.match(line)
        if match:
            return parse_toml_string(match.group(1))
    return ""


def set_key(lines: list[str], section: str, key: str, value: str) -> None:
    bounds = ensure_section(lines, section)
    start, end = bounds
    key_pattern = re.compile(r"^\s*" + re.escape(key) + r"\s*=")
    replacement = f"{key} = {toml_string(value)}\n"
    for index in range(start + 1, end):
        if key_pattern.match(lines[index]):
            lines[index] = replacement
            return
    lines.insert(end, replacement)


with open(path, "r", encoding="utf-8") as handle:
    lines = handle.readlines()

backend_bounds = ensure_section(lines, "backend")
existing_api_url = get_key(lines, backend_bounds, "api_base_url")
api_url = remote_api_url if remote_api_url_was_set or not existing_api_url else existing_api_url

set_key(lines, "backend", "mode", "remote_api")
set_key(lines, "backend", "api_base_url", api_url)
set_key(lines, "backend", "api_token", api_token)
set_key(lines, "database", "url", "")
set_key(lines, "database", "access_mode", "readonly")

directory = os.path.dirname(path) or "."
fd, tmp_path = tempfile.mkstemp(prefix=".config.", suffix=".tmp", dir=directory)
try:
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        handle.writelines(lines)
    os.chmod(tmp_path, 0o600)
    os.replace(tmp_path, path)
except Exception:
    try:
        os.unlink(tmp_path)
    except FileNotFoundError:
        pass
    raise
PY
}

prepare_runtime() {
  echo "Preparing Anchises Stock QA Python runtime. This may take a few minutes the first time."
  "${PYTHON_BIN}" "${PLUGIN_ROOT}/mcp/bootstrap.py" --prepare-only
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --config)
      need_value "$1" "${2-}"
      CONFIG_PATH="$2"
      shift 2
      ;;
    --remote-api-url)
      need_value "$1" "${2-}"
      REMOTE_API_URL="$2"
      REMOTE_API_URL_SET="true"
      shift 2
      ;;
    --api-token)
      need_value "$1" "${2-}"
      API_TOKEN="$2"
      shift 2
      ;;
    --outputs-dir)
      need_value "$1" "${2-}"
      OUTPUTS_DIR="$2"
      shift 2
      ;;
    --cleanup-enabled)
      need_value "$1" "${2-}"
      CLEANUP_ENABLED="$2"
      shift 2
      ;;
    --cleanup-interval-days)
      need_value "$1" "${2-}"
      CLEANUP_INTERVAL_DAYS="$2"
      shift 2
      ;;
    --retention-days)
      need_value "$1" "${2-}"
      RETENTION_DAYS="$2"
      shift 2
      ;;
    --prompt-override-dir)
      need_value "$1" "${2-}"
      PROMPT_OVERRIDE_DIR="$2"
      shift 2
      ;;
    --prepare-runtime)
      PREPARE_RUNTIME="true"
      shift
      ;;
    --force)
      FORCE="true"
      shift
      ;;
    --print)
      PRINT_CONFIG="true"
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

if [[ "${CLEANUP_ENABLED}" != "true" && "${CLEANUP_ENABLED}" != "false" ]]; then
  echo "--cleanup-enabled must be true or false." >&2
  exit 2
fi

if ! is_positive_int "${CLEANUP_INTERVAL_DAYS}" || ! is_positive_int "${RETENTION_DAYS}"; then
  echo "Cleanup interval and retention days must be positive integers." >&2
  exit 2
fi

if [[ -z "${REMOTE_API_URL}" ]]; then
  echo "No remote API URL provided; config was not created." >&2
  exit 2
fi

if [[ -z "${API_TOKEN}" ]]; then
  if [[ ! -t 0 ]]; then
    echo "No API token provided. Re-run with --api-token or run interactively." >&2
    exit 2
  fi
  echo "Enter your Anchises Stock QA API token."
  read -r -s -p "API token (hidden): " API_TOKEN
  echo
fi

if [[ -z "${API_TOKEN}" ]]; then
  echo "No API token provided; config was not created." >&2
  exit 2
fi

CONFIG_PATH="$(expand_leading_tilde "${CONFIG_PATH}")"
CONFIG_TEXT="$(build_config)"

if [[ "${PRINT_CONFIG}" == "true" ]]; then
  printf '%s' "${CONFIG_TEXT}"
  exit 0
fi

if [[ -e "${CONFIG_PATH}" && "${FORCE}" != "true" ]]; then
  update_existing_config_token
  echo "Updated API token in existing config: ${CONFIG_PATH}"
  echo "Other settings were kept. Keep this file private."
  if [[ "${PREPARE_RUNTIME}" == "true" ]]; then
    prepare_runtime
  fi
  exit 0
fi

mkdir -p "$(dirname "${CONFIG_PATH}")"
umask 077
printf '%s' "${CONFIG_TEXT}" > "${CONFIG_PATH}"

echo "Created config: ${CONFIG_PATH}"
echo "Remote API token was written to the config file. Keep this file private."
if [[ "${PREPARE_RUNTIME}" == "true" ]]; then
  prepare_runtime
fi
