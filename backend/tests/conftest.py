"""Test configuration: an isolated SQLite database and temporary folders.

Environment variables are set before the app is imported, because settings
are read once at import time.
"""

import json
import os
import tempfile
from pathlib import Path

_TMP = Path(tempfile.mkdtemp(prefix="wetlands-tests-"))
_SITES = _TMP / "ramsar-sites.json"
_SITES.write_text(
    json.dumps(
        {
            "sites": [
                {
                    "id": 2441,
                    "name": "Lonar Lake",
                    "state": "Maharashtra",
                    "latitude": 19.97594,
                    "longitude": 76.508413,
                    "areaHa": 427.0,
                },
                {
                    "id": 229,
                    "name": "Chilika Lake",
                    "state": "Odisha",
                    "latitude": 19.7,
                    "longitude": 85.35,
                    "areaHa": 116500.0,
                },
                {
                    "id": 2534,
                    "name": "Aghanashini Estuary",
                    "state": "Karnataka",
                    "latitude": 14.51045,
                    "longitude": 74.383096,
                    "areaHa": 4801.0,
                },
                {
                    "id": 1207,
                    "name": "Deepor Beel",
                    "state": "Assam",
                    "latitude": 26.133333,
                    "longitude": 91.65,
                    "areaHa": 4000.0,
                },
                {
                    "id": 2408,
                    "name": "Beas Conservation Reserve",
                    "state": "Punjab",
                    "latitude": 31.394839,
                    "longitude": 75.19469,
                    "areaHa": 6428.92,
                },
            ]
        }
    ),
    encoding="utf-8",
)
ROI_DIR = _TMP / "roi"
ROI_DIR.mkdir()
IMPORTED_ROI_DIR = _TMP / "imported-roi"
IMPORTED_ROI_DIR.mkdir()

os.environ.update(
    {
        "DATABASE_URL": f"sqlite:///{(_TMP / 'test.db').as_posix()}",
        "INITIAL_ADMIN_USERNAME": "admin",
        "INITIAL_ADMIN_PASSWORD": "admin@wetlands",
        "DATA_STORAGE_DIR": str(_TMP / "storage"),
        "CLIMATE_PUBLISH_DIR": str(_TMP / "published"),
        "RAMSAR_SITES_FILE": str(_SITES),
        "LOGIN_MAX_ATTEMPTS": "3",
        "WETLAND_ROI_DIR": str(ROI_DIR),
        # Real imported ROIs are opted into per test (test_imported_roi, test_coverage).
        "IMPORTED_ROI_DIR": str(IMPORTED_ROI_DIR),
        # Tests never call Copernicus; clients with credentials are built explicitly.
        "COPERNICUS_CLIENT_ID": "",
        "COPERNICUS_CLIENT_SECRET": "",
        # Isolated per-process result cache; cleared before every test below.
        "RESULT_CACHE_BACKEND": "memory",
    }
)

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.db.base import Base  # noqa: E402
from app.db.session import engine  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Dataset, User  # noqa: E402

PUBLISH_DIR = _TMP / "published"


@pytest.fixture
def client():
    # Fresh tables per test; the lifespan hook re-seeds the admin account.
    Base.metadata.drop_all(engine, tables=[Dataset.__table__, User.__table__])
    with TestClient(app) as c:
        yield c


@pytest.fixture(autouse=True)
def _clear_result_cache():
    from app.services.result_cache import get_result_cache

    get_result_cache().clear()
    yield
    get_result_cache().clear()
