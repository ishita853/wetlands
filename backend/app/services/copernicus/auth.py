"""OAuth2 client-credentials tokens for Copernicus Data Space.

The token is cached in process memory until shortly before it expires. The
client secret is only ever sent to the identity service and is never logged
or returned by the API.
"""

import threading
import time
from collections.abc import Callable

import httpx

from app.services.copernicus.errors import CopernicusAuthError, CopernicusUnavailable

# Refresh this many seconds before the token's stated expiry.
_EXPIRY_LEEWAY_SECONDS = 60.0
_DEFAULT_EXPIRES_IN = 300.0


class TokenProvider:
    def __init__(
        self,
        http: httpx.Client,
        token_url: str,
        client_id: str,
        client_secret: str,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._http = http
        self._token_url = token_url
        self._client_id = client_id
        self._client_secret = client_secret
        self._clock = clock
        self._lock = threading.Lock()
        self._token: str | None = None
        self._expires_at = 0.0

    def get_token(self) -> str:
        with self._lock:
            if self._token is None or self._clock() >= self._expires_at:
                self._token, self._expires_at = self._fetch()
            return self._token

    def invalidate(self) -> None:
        with self._lock:
            self._token = None

    def _fetch(self) -> tuple[str, float]:
        try:
            response = self._http.post(
                self._token_url,
                data={
                    "grant_type": "client_credentials",
                    "client_id": self._client_id,
                    "client_secret": self._client_secret,
                },
            )
        except httpx.HTTPError as exc:
            raise CopernicusUnavailable(f"Token request failed: {type(exc).__name__}") from exc

        if response.status_code in (400, 401, 403):
            raise CopernicusAuthError(
                f"Copernicus identity service rejected the client credentials "
                f"(HTTP {response.status_code}, {_oauth_error(response)})."
            )
        if response.status_code >= 400:
            raise CopernicusUnavailable(f"Token request failed (HTTP {response.status_code}).")

        body = response.json()
        token = body.get("access_token")
        if not isinstance(token, str) or not token:
            raise CopernicusAuthError("Token response did not contain an access_token.")
        expires_in = float(body.get("expires_in") or _DEFAULT_EXPIRES_IN)
        return token, self._clock() + max(expires_in - _EXPIRY_LEEWAY_SECONDS, 0.0)


def _oauth_error(response: httpx.Response) -> str:
    try:
        return str(response.json().get("error", "unknown error"))
    except ValueError:
        return "unknown error"
