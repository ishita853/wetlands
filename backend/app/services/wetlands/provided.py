"""The provided ROI dataset ("India Ramsar Sites September 2026").

A polygon file supplied by the project team and approved as the primary
water-quality analysis ROI. Its content is RSIS-derived (see
data/provided-roi.meta.json); it is neither a GEE ROI nor the raw RSIS copy,
so it is kept as its own source.

Features are matched to Ramsar sites by `ramsarid` only. A site's features are
collected into one MultiPolygon without dissolving; nothing is repaired,
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
    GeometryValidation,
    assemble_parts,
    geodesic_area_ha,
    geometry_sha256,
    validate_parts,
)

ProvidedStatus = Literal["available", "invalid", "missing"]
SOURCE_LABEL = "provided_roi"


@dataclass(frozen=True)
class ProvidedDataset:
    path: Path
    sha256: str
    name: str | None
    crs_name: str | None
    features_by_site: dict[int, list[dict[str, Any]]]
    features_without_id: int


@dataclass(frozen=True)
class ProvidedRoi:
    site_id: int
    status: ProvidedStatus
    geometry: MultiPolygon | None
    validation: GeometryValidation | None
    version: str | None
    geometry_sha256: str | None
    area_ha: float | None
    feature_count: int
    source_ids: dict[str, Any]
    reason: str | None


def load_dataset(path: Path | None = None) -> ProvidedDataset | None:
    source = Path(path or settings.PROVIDED_ROI_FILE)
    if not source.is_file():
        return None
    return _load(source, source.stat().st_mtime_ns)


@lru_cache(maxsize=4)
def _load(source: Path, _mtime: int) -> ProvidedDataset:
    raw = source.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    meta_path = Path(settings.PROVIDED_ROI_META_FILE)
    if meta_path.is_file():
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        expected = (meta.get("files", {}).get(source.name) or {}).get("sha256")
        if expected and expected != digest:
            raise ValueError(
                f"{source.name}: SHA-256 {digest} does not match {meta_path.name}; "
                "the provided ROI file changed. Re-inspect it and update its provenance record."
            )
    data = json.loads(raw.decode("utf-8-sig"))
    crs_name = ((data.get("crs") or {}).get("properties") or {}).get("name")
    by_site: dict[int, list[dict[str, Any]]] = {}
    without_id = 0
    for feature in data.get("features", []):
        site_id = (feature.get("properties") or {}).get("ramsarid")
        if isinstance(site_id, int):
            by_site.setdefault(site_id, []).append(feature)
        else:
            without_id += 1
    return ProvidedDataset(source, digest, data.get("name"), crs_name, by_site, without_id)


def lookup_provided(site_id: int) -> ProvidedRoi:
    source = Path(settings.PROVIDED_ROI_FILE)
    mtime = source.stat().st_mtime_ns if source.is_file() else 0
    return _lookup(site_id, source, mtime)


@lru_cache(maxsize=256)
def _lookup(site_id: int, _source: Path, _mtime: int) -> ProvidedRoi:
    # Validation (geodesic area, validity) is computed once per site and file version.
    dataset = load_dataset()
    if dataset is None:
        return ProvidedRoi(
            site_id,
            "missing",
            None,
            None,
            None,
            None,
            None,
            0,
            {},
            "The provided ROI dataset is not installed.",
        )
    features = dataset.features_by_site.get(site_id, [])
    if not features:
        return ProvidedRoi(
            site_id,
            "missing",
            None,
            None,
            None,
            None,
            None,
            0,
            {},
            "The provided ROI dataset has no polygon for this Ramsar site.",
        )
    parts = [shape(f["geometry"]) for f in features if f.get("geometry")]
    validation = validate_parts(parts, dataset.crs_name)
    geometry = assemble_parts(parts)
    version = f"provided-{dataset.sha256[:12]}"
    ids = {"ramsarid": site_id, "v_idris": [f["properties"].get("v_idris") for f in features]}
    if validation.errors:
        return ProvidedRoi(
            site_id,
            "invalid",
            geometry,
            validation,
            version,
            geometry_sha256(geometry),
            None,
            len(features),
            ids,
            "; ".join(validation.errors),
        )
    return ProvidedRoi(
        site_id,
        "available",
        geometry,
        validation,
        version,
        geometry_sha256(geometry),
        round(geodesic_area_ha(geometry), 2),
        len(features),
        ids,
        None,
    )
