"""The 101 Ramsar sites from the Ramsar Sites Information Service export.

Point coordinates (latitude/longitude) locate a wetland; they are never used
as analysis geometry.
"""

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

from app.core.config import settings


@dataclass(frozen=True)
class RamsarSite:
    id: int
    name: str
    state: str | None
    district: str | None
    latitude: float | None
    longitude: float | None
    designation_year: int | None
    area_ha: float | None
    summary: str | None


def load_sites(path: Path | None = None) -> dict[int, RamsarSite]:
    source = Path(path or settings.RAMSAR_SITES_FILE)
    return _load(source, source.stat().st_mtime_ns)


def get_site(site_id: int) -> RamsarSite | None:
    return load_sites().get(site_id)


@lru_cache(maxsize=4)
def _load(source: Path, _mtime: int) -> dict[int, RamsarSite]:
    data = json.loads(source.read_text(encoding="utf-8"))
    sites: dict[int, RamsarSite] = {}
    for raw in data.get("sites", []):
        site = _to_site(raw)
        if site is not None:
            sites[site.id] = site
    return sites


def _to_site(raw: dict[str, Any]) -> RamsarSite | None:
    if not isinstance(raw.get("id"), int):
        return None
    return RamsarSite(
        id=raw["id"],
        name=str(raw.get("name") or f"Ramsar site {raw['id']}"),
        state=raw.get("state"),
        district=raw.get("district"),
        latitude=raw.get("latitude"),
        longitude=raw.get("longitude"),
        designation_year=raw.get("designationYear"),
        area_ha=raw.get("areaHa"),
        summary=raw.get("summary"),
    )
