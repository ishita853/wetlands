"""Imported ROIs: polygons supplied by the project team as shapefiles (2026-09-30).

Kept as their own source (`imported_roi`), separate from the provided dataset and
from GEE ROIs: nothing establishes that they were exported from the GEE application.
Each file's origin and Ramsar-site mapping is recorded in IMPORTED_ROI_DIR/manifest.json
(written by app.tools.import_roi_shapefiles).

Features are collected into one MultiPolygon without dissolving; nothing is repaired,
simplified, buffered or reprojected. Invalid geometry is rejected.
"""

import hashlib
import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal

from shapely.geometry import MultiPolygon, shape

from app.core.config import settings
from app.services.wetlands.boundaries import (
    assemble_parts,
    geodesic_area_ha,
    geometry_sha256,
    validate_parts,
)

ImportedStatus = Literal["available", "invalid", "missing"]


@dataclass(frozen=True)
class ImportedEntry:
    ramsar_site_id: int
    file: str
    file_sha256: str
    source_archive: str
    origin: str
    origin_evidence: str
    mapping: str
    mapping_evidence: str


@dataclass(frozen=True)
class ImportedRoi:
    site_id: int
    status: ImportedStatus
    entry: ImportedEntry | None
    geometry: MultiPolygon | None
    version: str | None
    geometry_sha256: str | None
    area_ha: float | None
    feature_count: int
    reason: str | None


def load_manifest() -> dict[int, ImportedEntry]:
    source = Path(settings.IMPORTED_ROI_DIR) / "manifest.json"
    if not source.is_file():
        return {}
    return _load_manifest(source, source.stat().st_mtime_ns)


@lru_cache(maxsize=4)
def _load_manifest(source: Path, _mtime: int) -> dict[int, ImportedEntry]:
    data = json.loads(source.read_text(encoding="utf-8"))
    return {
        int(raw["ramsarSiteId"]): ImportedEntry(
            ramsar_site_id=int(raw["ramsarSiteId"]),
            file=raw["file"],
            file_sha256=raw["fileSha256"],
            source_archive=raw["sourceArchive"],
            origin=raw["origin"],
            origin_evidence=raw["originEvidence"],
            mapping=raw["mapping"],
            mapping_evidence=raw["mappingEvidence"],
        )
        for raw in data.get("imports", [])
    }


def lookup_imported(site_id: int) -> ImportedRoi:
    entry = load_manifest().get(site_id)
    if entry is None:
        return ImportedRoi(
            site_id, "missing", None, None, None, None, None, 0, "No imported ROI for this site."
        )
    path = Path(settings.IMPORTED_ROI_DIR) / entry.file
    if not path.is_file():
        return ImportedRoi(
            site_id, "missing", entry, None, None, None, None, 0, f"{entry.file} is not present."
        )
    return _lookup(entry, path, path.stat().st_mtime_ns)


@lru_cache(maxsize=128)
def _lookup(entry: ImportedEntry, path: Path, _mtime: int) -> ImportedRoi:
    raw = path.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    if digest != entry.file_sha256:
        raise ValueError(
            f"{path.name}: SHA-256 {digest} does not match the imported ROI manifest; "
            "re-run app.tools.import_roi_shapefiles."
        )
    data: dict[str, Any] = json.loads(raw.decode("utf-8"))
    crs_name = ((data.get("crs") or {}).get("properties") or {}).get("name")
    features = data.get("features") or []
    parts = [shape(f["geometry"]) for f in features if f.get("geometry")]
    validation = validate_parts(parts, crs_name)
    geometry = assemble_parts(parts)
    version = f"imported-{digest[:12]}"
    if validation.errors:
        return ImportedRoi(
            entry.ramsar_site_id,
            "invalid",
            entry,
            geometry,
            version,
            geometry_sha256(geometry),
            None,
            len(features),
            "; ".join(validation.errors),
        )
    return ImportedRoi(
        entry.ramsar_site_id,
        "available",
        entry,
        geometry,
        version,
        geometry_sha256(geometry),
        round(geodesic_area_ha(geometry), 2),
        len(features),
        None,
    )
