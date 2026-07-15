"""Remote Stock QA API client for shared-user deployments."""

from __future__ import annotations

import base64
import json
from typing import Any, Dict
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin
from urllib.request import Request, urlopen

from config import StockQAConfig, sanitize_error_text


DEFAULT_TIMEOUT_SECONDS = 60
MAX_REMOTE_CSV_BYTES = 100 * 1024 * 1024


class RemoteAPIError(RuntimeError):
    """Raised when the remote Stock QA API cannot satisfy a request."""


def _endpoint(config: StockQAConfig, path: str) -> str:
    base_url = config.backend.api_base_url.rstrip("/") + "/"
    return urljoin(base_url, path.lstrip("/"))


def _decode_error_body(body: bytes) -> str:
    if not body:
        return ""
    text = body.decode("utf-8", errors="replace")
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return text[:1000]
    if isinstance(payload, dict):
        for key in ("error", "message", "detail"):
            if payload.get(key):
                return str(payload[key])
    return text[:1000]


def _normalize_response(payload: Any, *, allow_ok_false: bool = False) -> Dict[str, Any]:
    if not isinstance(payload, dict):
        raise RemoteAPIError("Remote API returned a non-object JSON response")
    if payload.get("ok") is False and not allow_ok_false:
        message = payload.get("error") or payload.get("message") or "remote request failed"
        raise RemoteAPIError(str(message))
    if isinstance(payload.get("data"), dict):
        return payload["data"]
    return payload


def request_json(
    config: StockQAConfig,
    method: str,
    path: str,
    payload: Dict[str, Any] | None = None,
    *,
    allow_ok_false: bool = False,
) -> Dict[str, Any]:
    if config.backend.mode != "remote_api":
        raise RemoteAPIError("Remote API client requires [backend].mode = remote_api")
    if not config.backend.api_base_url:
        raise RemoteAPIError("[backend].api_base_url is required for remote_api mode")
    if not config.backend.api_token:
        raise RemoteAPIError("[backend].api_token is required for remote_api mode")

    data = None
    headers = {
        "Accept": "application/json",
        "Authorization": f"Bearer {config.backend.api_token}",
        "User-Agent": "anchises-stock-qa-plugin/remote-api",
    }
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    request = Request(
        _endpoint(config, path),
        data=data,
        headers=headers,
        method=method.upper(),
    )
    try:
        with urlopen(request, timeout=DEFAULT_TIMEOUT_SECONDS) as response:
            response_body = response.read()
    except HTTPError as exc:
        status = exc.code
        reason = exc.reason
        try:
            body = exc.read(4096)
        finally:
            exc.close()
        message = _decode_error_body(body) or reason or "HTTP error"
        safe = sanitize_error_text(message, config)
        raise RemoteAPIError(f"Remote API HTTP {status}: {safe}") from exc
    except URLError as exc:
        safe = sanitize_error_text(str(exc.reason), config)
        raise RemoteAPIError(f"Remote API connection failed: {safe}") from exc
    except TimeoutError as exc:
        raise RemoteAPIError("Remote API request timed out") from exc

    try:
        decoded = json.loads(response_body.decode("utf-8"))
    except json.JSONDecodeError as exc:
        raise RemoteAPIError("Remote API returned invalid JSON") from exc
    try:
        return _normalize_response(decoded, allow_ok_false=allow_ok_false)
    except RemoteAPIError as exc:
        raise RemoteAPIError(sanitize_error_text(str(exc), config)) from exc


def csv_bytes_from_response(response: Dict[str, Any]) -> bytes:
    if isinstance(response.get("csv_base64"), str):
        try:
            data = base64.b64decode(response["csv_base64"], validate=True)
        except Exception as exc:
            raise RemoteAPIError("Remote API returned invalid csv_base64") from exc
    elif isinstance(response.get("csv_text"), str):
        data = response["csv_text"].encode("utf-8")
    else:
        raise RemoteAPIError("Remote API run-sql response must include csv_base64 or csv_text")

    if len(data) > MAX_REMOTE_CSV_BYTES:
        raise RemoteAPIError(
            f"Remote API CSV is too large ({len(data)} bytes; limit {MAX_REMOTE_CSV_BYTES})"
        )
    return data
