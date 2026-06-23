"""Configuration loading for Anchises Stock QA."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict
from urllib.parse import SplitResult, urlsplit, urlunsplit

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - Python < 3.11
    import tomli as tomllib  # type: ignore[no-redef]


PLUGIN_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG_PATH = Path.home() / ".config" / "anchises-stock-qa" / "config.toml"
DEFAULT_OUTPUTS_DIR = Path.home() / ".local" / "share" / "anchises-stock-qa" / "outputs"


class ConfigError(RuntimeError):
    """Raised when the user configuration is missing or invalid."""


@dataclass(frozen=True)
class BackendConfig:
    mode: str = "local_mysql"
    api_base_url: str = ""
    api_token: str = ""


@dataclass(frozen=True)
class DatabaseConfig:
    url: str
    access_mode: str = "readonly"


@dataclass(frozen=True)
class OutputsConfig:
    dir: Path = DEFAULT_OUTPUTS_DIR
    cleanup_enabled: bool = True
    cleanup_interval_days: int = 7
    retention_days: int = 30


@dataclass(frozen=True)
class PromptsConfig:
    override_dir: Path | None = None


@dataclass(frozen=True)
class ExchangesConfig:
    aliases: Dict[str, str]


@dataclass(frozen=True)
class StockQAConfig:
    config_path: Path
    config_exists: bool
    backend: BackendConfig
    database: DatabaseConfig
    outputs: OutputsConfig
    prompts: PromptsConfig
    exchanges: ExchangesConfig
    missing_config_message: str = ""


def config_path() -> Path:
    override = os.getenv("ANCHISES_STOCK_QA_CONFIG", "").strip()
    if override:
        return Path(override).expanduser().resolve()
    return DEFAULT_CONFIG_PATH


def _as_bool(value: Any, default: bool) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    if text in {"1", "true", "yes", "y", "on"}:
        return True
    if text in {"0", "false", "no", "n", "off"}:
        return False
    raise ConfigError(f"Expected boolean value, got {value!r}")


def _as_int(value: Any, default: int, *, minimum: int = 1) -> int:
    if value is None or str(value).strip() == "":
        return default
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise ConfigError(f"Expected integer value, got {value!r}") from exc
    if parsed < minimum:
        raise ConfigError(f"Expected integer >= {minimum}, got {parsed}")
    return parsed


def _optional_path(value: Any) -> Path | None:
    if value is None or str(value).strip() == "":
        return None
    return Path(str(value)).expanduser().resolve()


def _path_value(value: Any, default: Path) -> Path:
    if value is None or str(value).strip() == "":
        return default
    return Path(str(value)).expanduser().resolve()


def _exchange_aliases(value: Any) -> Dict[str, str]:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ConfigError("[exchanges.aliases] must be a table")
    aliases: Dict[str, str] = {}
    for raw_key, raw_target in value.items():
        key = str(raw_key).strip()
        target = str(raw_target).strip().lower()
        if not key or not target:
            raise ConfigError("[exchanges.aliases] entries must not be empty")
        aliases[key] = target
    return aliases


def _missing_config_message(path: Path) -> str:
    return (
        f"Anchises Stock QA config file not found: {path}. "
        "From the plugin folder, run scripts/init_config.sh and enter your API token. "
        "You can also create it from config.example.toml and configure [backend].api_token. "
        "You can also set ANCHISES_STOCK_QA_CONFIG to another config.toml path."
    )


def load_config(*, require_database_url: bool = True) -> StockQAConfig:
    path = config_path()
    config_exists = path.exists()
    raw: Dict[str, Any] = {}
    missing_message = ""

    if config_exists:
        try:
            raw = tomllib.loads(path.read_text(encoding="utf-8"))
        except tomllib.TOMLDecodeError as exc:
            raise ConfigError(f"Invalid TOML in {path}: {exc}") from exc
    else:
        missing_message = _missing_config_message(path)
        if require_database_url:
            raise ConfigError(missing_message)

    backend_raw = raw.get("backend", {})
    database_raw = raw.get("database", {})
    outputs_raw = raw.get("outputs", {})
    prompts_raw = raw.get("prompts", {})
    exchanges_raw = raw.get("exchanges", {})

    if not isinstance(backend_raw, dict):
        raise ConfigError("[backend] must be a table")
    if not isinstance(database_raw, dict):
        raise ConfigError("[database] must be a table")
    if not isinstance(outputs_raw, dict):
        raise ConfigError("[outputs] must be a table")
    if not isinstance(prompts_raw, dict):
        raise ConfigError("[prompts] must be a table")
    if not isinstance(exchanges_raw, dict):
        raise ConfigError("[exchanges] must be a table")

    backend_mode = str(backend_raw.get("mode", "local_mysql")).strip().lower()
    if not backend_mode:
        backend_mode = "local_mysql"
    if backend_mode not in {"local_mysql", "remote_api"}:
        raise ConfigError('[backend].mode must be "local_mysql" or "remote_api"')
    api_base_url = str(backend_raw.get("api_base_url", "")).strip().rstrip("/")
    api_token = str(backend_raw.get("api_token", "")).strip()

    db_url = str(database_raw.get("url", "")).strip()
    access_mode = str(database_raw.get("access_mode", "readonly")).strip().lower()
    if access_mode != "readonly":
        raise ConfigError('[database].access_mode must be "readonly"')
    if require_database_url and backend_mode == "local_mysql" and not db_url:
        raise ConfigError("[database].url is required and must be a read-only MySQL URL")
    if require_database_url and backend_mode == "remote_api":
        missing = []
        if not api_base_url:
            missing.append("[backend].api_base_url")
        if not api_token:
            missing.append("[backend].api_token")
        if missing:
            raise ConfigError(
                "remote_api backend requires " + " and ".join(missing)
            )

    cleanup_interval_days = _as_int(
        outputs_raw.get("cleanup_interval_days"),
        7,
        minimum=1,
    )
    retention_days = _as_int(outputs_raw.get("retention_days"), 30, minimum=1)

    return StockQAConfig(
        config_path=path,
        config_exists=config_exists,
        backend=BackendConfig(
            mode=backend_mode,
            api_base_url=api_base_url,
            api_token=api_token,
        ),
        database=DatabaseConfig(url=db_url, access_mode=access_mode),
        outputs=OutputsConfig(
            dir=_path_value(outputs_raw.get("dir"), DEFAULT_OUTPUTS_DIR),
            cleanup_enabled=_as_bool(outputs_raw.get("cleanup_enabled"), True),
            cleanup_interval_days=cleanup_interval_days,
            retention_days=retention_days,
        ),
        prompts=PromptsConfig(
            override_dir=_optional_path(prompts_raw.get("override_dir")),
        ),
        exchanges=ExchangesConfig(
            aliases=_exchange_aliases(exchanges_raw.get("aliases")),
        ),
        missing_config_message=missing_message,
    )


def redact_url(url: str) -> str:
    if not url:
        return ""
    try:
        parsed = urlsplit(url)
    except ValueError:
        return _fallback_redact(url)
    if not parsed.netloc:
        return _fallback_redact(url)

    user = parsed.username or ""
    host = parsed.hostname or ""
    port = f":{parsed.port}" if parsed.port else ""
    if user:
        netloc = f"{user}:***@{host}{port}"
    else:
        netloc = f"{host}{port}"
    return urlunsplit(
        SplitResult(parsed.scheme, netloc, parsed.path, parsed.query, parsed.fragment)
    )


def _fallback_redact(value: str) -> str:
    redacted = re.sub(r":([^:@/]+)@", r":***@", value)
    redacted = re.sub(r"(password=)[^&\s]+", r"\1***", redacted, flags=re.I)
    redacted = re.sub(
        r"((?:api[_-]?token|token|api[_-]?key|key)=)[^&\s]+",
        r"\1***",
        redacted,
        flags=re.I,
    )
    return redacted


def sanitize_error_text(text: str, config: StockQAConfig | None = None) -> str:
    sanitized = str(text)
    if config and config.database.url:
        sanitized = sanitized.replace(config.database.url, redact_url(config.database.url))
    if config and config.backend.api_token:
        sanitized = sanitized.replace(config.backend.api_token, "***")
    sanitized = re.sub(r"(Authorization:\s*Bearer\s+)[^\s]+", r"\1***", sanitized, flags=re.I)
    sanitized = re.sub(r"(Bearer\s+)[A-Za-z0-9._~+/=-]+", r"\1***", sanitized, flags=re.I)
    sanitized = re.sub(r"(api_token\s*=\s*)[^\s&]+", r"\1***", sanitized, flags=re.I)
    sanitized = _fallback_redact(sanitized)
    return sanitized


def config_as_dict(
    config: StockQAConfig,
    *,
    redact_secrets: bool = True,
) -> Dict[str, Any]:
    # Secrets are always redacted, even when callers request the raw shape.
    return {
        "config_path": str(config.config_path),
        "config_exists": config.config_exists,
        "missing_config_message": config.missing_config_message,
        "backend": {
            "mode": config.backend.mode,
            "api_base_url": _fallback_redact(config.backend.api_base_url),
            "api_token_configured": bool(config.backend.api_token),
            "api_token": "***" if config.backend.api_token else "",
            "secrets_redacted": True,
        },
        "database": {
            "url": redact_url(config.database.url),
            "access_mode": config.database.access_mode,
            "secrets_redacted": True,
            "redact_secrets_requested": bool(redact_secrets),
        },
        "outputs": {
            "dir": str(config.outputs.dir),
            "cleanup_enabled": config.outputs.cleanup_enabled,
            "cleanup_interval_days": config.outputs.cleanup_interval_days,
            "retention_days": config.outputs.retention_days,
        },
        "prompts": {
            "override_dir": str(config.prompts.override_dir)
            if config.prompts.override_dir
            else "",
        },
        "exchanges": {
            "aliases": dict(config.exchanges.aliases),
        },
    }
