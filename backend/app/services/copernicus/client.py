"""Copernicus Data Space / Sentinel Hub HTTP client.

Credentials are read from environment variables (COPERNICUS_CLIENT_ID,
COPERNICUS_CLIENT_SECRET) via app.core.config.settings and must never be
exposed to the frontend. All Sentinel Hub calls go through `post`, which adds
the bearer token, refreshes it once on 401 and backs off on rate limiting.
"""

import time
from collections.abc import Callable
from functools import lru_cache
from typing import Any

import httpx

from app.core.config import Settings, settings
from app.services.copernicus.auth import TokenProvider
from app.services.copernicus.errors import (
    CopernicusInvalidResponse,
    CopernicusNotConfigured,
    CopernicusRateLimited,
    CopernicusRequestError,
    CopernicusUnavailable,
)

_MAX_RATE_LIMIT_RETRIES = 2
_MAX_BACKOFF_SECONDS = 10.0


class CopernicusClient:
    def __init__(
        self,
        config: Settings = settings,
        transport: httpx.BaseTransport | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self.config = config
        self._sleep = sleep
        self._http = httpx.Client(timeout=config.COPERNICUS_TIMEOUT_SECONDS, transport=transport)
        self._tokens: TokenProvider | None = None
        if config.COPERNICUS_CLIENT_ID and config.COPERNICUS_CLIENT_SECRET:
            self._tokens = TokenProvider(
                self._http,
                config.COPERNICUS_TOKEN_URL,
                config.COPERNICUS_CLIENT_ID,
                config.COPERNICUS_CLIENT_SECRET,
            )

    def is_configured(self) -> bool:
        return self._tokens is not None

    def post(
        self, url: str, body: dict[str, Any], accept: str = "application/json"
    ) -> httpx.Response:
        if self._tokens is None:
            raise CopernicusNotConfigured(
                "Copernicus Data Space credentials are not configured on the server."
            )

        refreshed = False
        rate_limit_retries = 0
        while True:
            headers = {"Authorization": f"Bearer {self._tokens.get_token()}", "Accept": accept}
            try:
                response = self._http.post(url, json=body, headers=headers)
            except httpx.HTTPError as exc:
                raise CopernicusUnavailable(
                    f"Request to Sentinel Hub failed: {type(exc).__name__}"
                ) from exc

            if response.status_code == 401 and not refreshed:
                self._tokens.invalidate()
                refreshed = True
                continue
            if response.status_code in (429, 503):
                retry_after = _retry_after(response)
                if rate_limit_retries >= _MAX_RATE_LIMIT_RETRIES:
                    if response.status_code == 503:
                        raise CopernicusUnavailable("Sentinel Hub is temporarily unavailable.")
                    raise CopernicusRateLimited(
                        "Sentinel Hub rate limit or processing quota reached.", retry_after
                    )
                rate_limit_retries += 1
                self._sleep(min(retry_after or 2.0**rate_limit_retries, _MAX_BACKOFF_SECONDS))
                continue
            if response.status_code >= 400:
                raise CopernicusRequestError(response.status_code, _error_message(response))
            return response

    def post_json(
        self, url: str, body: dict[str, Any], accept: str = "application/json"
    ) -> dict[str, Any]:
        response = self.post(url, body, accept=accept)
        try:
            data = response.json()
        except ValueError as exc:
            raise CopernicusInvalidResponse("Sentinel Hub returned a non-JSON response.") from exc
        if not isinstance(data, dict):
            raise CopernicusInvalidResponse("Sentinel Hub returned an unexpected JSON document.")
        return data


def _retry_after(response: httpx.Response) -> float | None:
    value = response.headers.get("Retry-After")
    try:
        return float(value) if value is not None else None
    except ValueError:
        return None


def _error_message(response: httpx.Response) -> str:
    try:
        body = response.json()
    except ValueError:
        return response.text[:500] or "no details"
    error = body.get("error") if isinstance(body, dict) else None
    if isinstance(error, dict):
        return str(error.get("message") or error.get("reason") or error)[:500]
    return str(body)[:500]


@lru_cache
def get_copernicus_client() -> CopernicusClient:
    return CopernicusClient()
