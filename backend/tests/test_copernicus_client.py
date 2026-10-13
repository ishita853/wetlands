"""OAuth token handling and request retries against a mocked Copernicus Data Space."""

from typing import Any

import httpx
import pytest

from app.core.config import Settings
from app.services.copernicus.auth import TokenProvider
from app.services.copernicus.client import CopernicusClient
from app.services.copernicus.errors import (
    CopernicusAuthError,
    CopernicusNotConfigured,
    CopernicusRateLimited,
    CopernicusRequestError,
)

TOKEN_URL = "https://identity.example/token"
API_URL = "https://sh.example/api"


def _settings(**overrides: Any) -> Settings:
    values: dict[str, Any] = {
        "COPERNICUS_CLIENT_ID": "client-id",
        "COPERNICUS_CLIENT_SECRET": "client-secret",
        "COPERNICUS_TOKEN_URL": TOKEN_URL,
    }
    values.update(overrides)
    return Settings(**values)


class FakeCdse:
    """Records requests; token endpoint issues tok-1, tok-2, ..."""

    def __init__(self, api_responses: list[httpx.Response] | None = None, expires_in: int = 3600):
        self.token_requests: list[httpx.Request] = []
        self.api_requests: list[httpx.Request] = []
        self.api_responses = api_responses or []
        self.expires_in = expires_in

    def __call__(self, request: httpx.Request) -> httpx.Response:
        if str(request.url) == TOKEN_URL:
            self.token_requests.append(request)
            token = f"tok-{len(self.token_requests)}"
            return httpx.Response(200, json={"access_token": token, "expires_in": self.expires_in})
        self.api_requests.append(request)
        if self.api_responses:
            return self.api_responses.pop(0)
        return httpx.Response(200, json={"ok": True})


def test_client_not_configured_raises_and_sends_nothing():
    fake = FakeCdse()
    client = CopernicusClient(
        _settings(COPERNICUS_CLIENT_ID="", COPERNICUS_CLIENT_SECRET=""),
        transport=httpx.MockTransport(fake),
    )
    assert not client.is_configured()
    with pytest.raises(CopernicusNotConfigured):
        client.post(API_URL, {})
    assert fake.token_requests == [] and fake.api_requests == []


def test_client_credentials_grant_and_bearer_header():
    fake = FakeCdse()
    client = CopernicusClient(_settings(), transport=httpx.MockTransport(fake))
    client.post(API_URL, {"a": 1})
    form = dict(httpx.QueryParams(fake.token_requests[0].content.decode()))
    assert form == {
        "grant_type": "client_credentials",
        "client_id": "client-id",
        "client_secret": "client-secret",
    }
    api_request = fake.api_requests[0]
    assert api_request.headers["Authorization"] == "Bearer tok-1"
    # The secret goes only to the identity service.
    assert b"client-secret" not in api_request.content
    assert "client-secret" not in str(api_request.headers)


def test_token_is_cached_between_requests():
    fake = FakeCdse()
    client = CopernicusClient(_settings(), transport=httpx.MockTransport(fake))
    client.post(API_URL, {})
    client.post(API_URL, {})
    assert len(fake.token_requests) == 1


def test_token_refreshed_after_expiry():
    now = [1000.0]
    fake = FakeCdse(expires_in=300)
    http = httpx.Client(transport=httpx.MockTransport(fake))
    provider = TokenProvider(http, TOKEN_URL, "id", "secret", clock=lambda: now[0])
    assert provider.get_token() == "tok-1"
    now[0] += 200  # within 300 s minus 60 s leeway
    assert provider.get_token() == "tok-1"
    now[0] += 50  # past the refresh point
    assert provider.get_token() == "tok-2"


def test_401_refreshes_token_once_and_retries():
    fake = FakeCdse([httpx.Response(401, json={"error": "expired"}), httpx.Response(200, json={})])
    client = CopernicusClient(_settings(), transport=httpx.MockTransport(fake))
    client.post(API_URL, {})
    assert len(fake.token_requests) == 2
    assert fake.api_requests[1].headers["Authorization"] == "Bearer tok-2"


def test_rejected_credentials():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"error": "invalid_client"})

    client = CopernicusClient(_settings(), transport=httpx.MockTransport(handler))
    with pytest.raises(CopernicusAuthError, match="invalid_client"):
        client.post(API_URL, {})


def test_rate_limit_backs_off_then_gives_up():
    sleeps: list[float] = []
    fake = FakeCdse([httpx.Response(429, headers={"Retry-After": "3"})] * 3)
    client = CopernicusClient(_settings(), transport=httpx.MockTransport(fake), sleep=sleeps.append)
    with pytest.raises(CopernicusRateLimited) as exc_info:
        client.post(API_URL, {})
    assert sleeps == [3.0, 3.0]
    assert exc_info.value.retry_after == 3.0


def test_rate_limit_recovers():
    fake = FakeCdse([httpx.Response(429), httpx.Response(200, json={"ok": 1})])
    client = CopernicusClient(
        _settings(), transport=httpx.MockTransport(fake), sleep=lambda s: None
    )
    assert client.post(API_URL, {}).json() == {"ok": 1}


def test_sentinel_hub_error_message_is_surfaced():
    fake = FakeCdse(
        [httpx.Response(400, json={"error": {"status": 400, "message": "Invalid evalscript"}})]
    )
    client = CopernicusClient(_settings(), transport=httpx.MockTransport(fake))
    with pytest.raises(CopernicusRequestError) as exc_info:
        client.post(API_URL, {})
    assert exc_info.value.status_code == 400
    assert exc_info.value.message == "Invalid evalscript"
