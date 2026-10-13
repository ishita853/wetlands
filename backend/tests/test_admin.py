import json

from tests.conftest import PUBLISH_DIR

NEW_PASSWORD = "Sedge-Heron-2026!"


def login(client, username="admin", password="admin@wetlands"):
    return client.post("/api/v1/auth/login", json={"username": username, "password": password})


def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def ready_admin(client) -> str:
    """Signs in with the initial password and completes the forced change."""
    token = login(client).json()["access_token"]
    res = client.post(
        "/api/v1/auth/change-password",
        json={"current_password": "admin@wetlands", "new_password": NEW_PASSWORD},
        headers=auth(token),
    )
    assert res.status_code == 200, res.text
    return res.json()["access_token"]


def climate_file(**overrides) -> bytes:
    data = {
        "theme": "heat-waves",
        "source": "Test source",
        "baseline": "1991–2020",
        "years": [2020, 2021],
        "metrics": [
            {
                "key": "hw_days",
                "label": "Heat-wave days",
                "unit": "days/year",
                "values": {"2441": [3, None], "229": [1.5, 2]},
            }
        ],
    }
    data.update(overrides)
    return json.dumps(data).encode()


def upload(client, token, raw: bytes, theme="heat-waves", publish=True):
    return client.post(
        "/api/v1/admin/datasets/climate",
        data={"theme": theme, "publish": str(publish).lower()},
        files={"file": ("heat-waves.json", raw, "application/json")},
        headers=auth(token),
    )


# --- authentication --------------------------------------------------------


def test_initial_admin_must_change_password(client):
    res = login(client)
    assert res.status_code == 200
    body = res.json()
    assert body["must_change_password"] is True

    # Everything except /me and change-password is refused until then.
    assert (
        client.get("/api/v1/admin/datasets", headers=auth(body["access_token"])).status_code == 403
    )
    me = client.get("/api/v1/auth/me", headers=auth(body["access_token"]))
    assert me.json() == {"username": "admin", "role": "SUPER_ADMIN", "must_change_password": True}


def test_wrong_password_is_generic_and_locks_out(client):
    for _ in range(3):
        res = login(client, password="wrong")
        assert res.status_code == 401
        assert res.json()["detail"] == "Incorrect username or password."
    assert login(client, username="nobody", password="x").json()["detail"] == (
        "Incorrect username or password."
    )
    # LOGIN_MAX_ATTEMPTS=3 in tests: now locked, even with the right password.
    assert login(client).status_code == 429


def test_password_policy_and_old_tokens_revoked(client):
    token = login(client).json()["access_token"]
    for weak in ("short1!", "admin@wetlands", "alllowercaseletters", "Admin-Password-99"):
        res = client.post(
            "/api/v1/auth/change-password",
            json={"current_password": "admin@wetlands", "new_password": weak},
            headers=auth(token),
        )
        assert res.status_code == 422, weak

    new_token = ready_admin(client)
    # The pre-change token is no longer accepted.
    assert client.get("/api/v1/auth/me", headers=auth(token)).status_code == 401
    assert client.get("/api/v1/admin/datasets", headers=auth(new_token)).status_code == 200
    # The initial password no longer works.
    assert login(client).status_code == 401
    assert login(client, password=NEW_PASSWORD).json()["must_change_password"] is False


def test_admin_routes_require_a_token(client):
    assert client.get("/api/v1/admin/datasets").status_code == 401
    assert client.get("/api/v1/admin/datasets", headers=auth("not-a-jwt")).status_code == 401


# --- climate datasets ------------------------------------------------------


def test_valid_upload_is_published(client):
    token = ready_admin(client)
    res = upload(client, token, climate_file())
    assert res.status_code == 201, res.text
    body = res.json()
    assert body["status"] == "PUBLISHED"
    assert body["summary"]["siteCount"] == 2
    assert body["uploaded_by_username"] == "admin"
    published = json.loads((PUBLISH_DIR / "heat-waves.json").read_text(encoding="utf-8"))
    assert published["metrics"][0]["key"] == "hw_days"

    public = client.get("/api/v1/datasets").json()
    assert [d["theme"] for d in public] == ["heat-waves"]


def test_invalid_upload_is_recorded_not_published(client):
    token = ready_admin(client)
    (PUBLISH_DIR / "heat-waves.json").unlink(missing_ok=True)
    bad = climate_file(
        theme="cold-waves",
        years=[2021, 2020],
        metrics=[
            {"key": "x", "label": "X", "unit": "d", "values": {"9999": [1], "2441": [1, "a"]}}
        ],
    )
    res = upload(client, token, bad)
    assert res.status_code == 201
    body = res.json()
    assert body["status"] == "FAILED"
    errors = " | ".join(body["validation_errors"])
    assert '"theme" must be "heat-waves"' in errors
    assert "increasing order" in errors
    assert '"9999" is not a Ramsar Site number' in errors
    assert "numbers or null" in errors
    assert not (PUBLISH_DIR / "heat-waves.json").exists()

    publish = client.post(f"/api/v1/admin/datasets/{body['id']}/publish", headers=auth(token))
    assert publish.status_code == 409


def test_not_json(client):
    token = ready_admin(client)
    res = upload(client, token, b"{not json")
    assert res.json()["status"] == "FAILED"
    assert "not valid JSON" in res.json()["validation_errors"][0]


def test_republish_older_version_and_unpublish(client):
    token = ready_admin(client)
    first = upload(client, token, climate_file(source="Version 1")).json()
    second = upload(client, token, climate_file(source="Version 2")).json()

    listed = {
        d["id"]: d["status"]
        for d in client.get("/api/v1/admin/datasets", headers=auth(token)).json()
    }
    assert listed == {first["id"]: "SUPERSEDED", second["id"]: "PUBLISHED"}

    # Roll back to version 1.
    res = client.post(f"/api/v1/admin/datasets/{first['id']}/publish", headers=auth(token))
    assert res.json()["status"] == "PUBLISHED"
    assert (
        json.loads((PUBLISH_DIR / "heat-waves.json").read_text(encoding="utf-8"))["source"]
        == "Version 1"
    )

    res = client.post(f"/api/v1/admin/datasets/{first['id']}/unpublish", headers=auth(token))
    assert res.json()["status"] == "VALIDATED"
    assert not (PUBLISH_DIR / "heat-waves.json").exists()
