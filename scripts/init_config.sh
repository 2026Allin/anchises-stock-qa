#!/usr/bin/env bash
set -euo pipefail

DEFAULT_CONFIG_PATH="${HOME}/.config/anchises-stock-qa/config.toml"
DEFAULT_OUTPUTS_DIR="~/.local/share/anchises-stock-qa/outputs"

CONFIG_PATH="${DEFAULT_CONFIG_PATH}"
DB_URL=""
OUTPUTS_DIR="${DEFAULT_OUTPUTS_DIR}"
CLEANUP_ENABLED="true"
CLEANUP_INTERVAL_DAYS="7"
RETENTION_DAYS="30"
PROMPT_OVERRIDE_DIR=""
FORCE="false"
PRINT_CONFIG="false"

usage() {
  cat <<'EOF'
Create ~/.config/anchises-stock-qa/config.toml without sudo.

Usage:
  bash scripts/init_config.sh [options]

Options:
  --config PATH                 Config file to create.
                                Defaults to ~/.config/anchises-stock-qa/config.toml
  --db-url URL                  Read-only MySQL URL. If omitted, prompts for it.
  --outputs-dir PATH            Directory for exported CSV files.
                                Defaults to ~/.local/share/anchises-stock-qa/outputs
  --cleanup-enabled true|false  Enable automatic lazy cleanup. Defaults to true.
  --cleanup-interval-days N     Run automatic cleanup at most once per N days. Defaults to 7.
  --retention-days N            Delete output run directories older than N days. Defaults to 30.
  --prompt-override-dir PATH    Optional directory containing user-edited prompt markdown files.
  --force                       Overwrite an existing config file.
  --print                       Print config text instead of writing it.
  -h, --help                    Show this help.

Examples:
  bash scripts/init_config.sh
  bash scripts/init_config.sh --force
  bash scripts/init_config.sh --db-url 'mysql+pymysql://stock_reader:password@127.0.0.1:3306/Stocks_Tracker?charset=utf8mb4'
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
[database]
url = $(toml_string "${DB_URL}")
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

while [[ $# -gt 0 ]]; do
  case "$1" in
    --config)
      need_value "$1" "${2-}"
      CONFIG_PATH="$2"
      shift 2
      ;;
    --db-url)
      need_value "$1" "${2-}"
      DB_URL="$2"
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

if [[ -z "${DB_URL}" ]]; then
  if [[ ! -t 0 ]]; then
    echo "No database URL provided. Re-run with --db-url or run interactively." >&2
    exit 2
  fi
  echo "Enter the read-only MySQL URL for Stocks_Tracker."
  echo "Example: mysql+pymysql://stock_reader:password@127.0.0.1:3306/Stocks_Tracker?charset=utf8mb4"
  read -r -s -p "Database URL (hidden): " DB_URL
  echo
fi

if [[ -z "${DB_URL}" ]]; then
  echo "No database URL provided; config was not created." >&2
  exit 2
fi

CONFIG_PATH="$(expand_leading_tilde "${CONFIG_PATH}")"
CONFIG_TEXT="$(build_config)"

if [[ "${PRINT_CONFIG}" == "true" ]]; then
  printf '%s' "${CONFIG_TEXT}"
  exit 0
fi

if [[ -e "${CONFIG_PATH}" && "${FORCE}" != "true" ]]; then
  echo "Config already exists: ${CONFIG_PATH}. Re-run with --force to overwrite." >&2
  exit 1
fi

mkdir -p "$(dirname "${CONFIG_PATH}")"
umask 077
printf '%s' "${CONFIG_TEXT}" > "${CONFIG_PATH}"

echo "Created config: ${CONFIG_PATH}"
echo "Database URL was written to the config file. Keep this file private."
