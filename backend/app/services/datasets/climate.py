"""Validation and publication of climate indicator datasets.

The rules mirror the portal's loader (frontend/lib/data/climate.ts) and the
format document (frontend/data/climate/README.md): a file that passes here is
guaranteed to load on the site.
"""

from __future__ import annotations

import json
import math
import os
import tempfile
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any, TypeGuard

from app.core.config import settings

CLIMATE_THEMES: dict[str, str] = {
    "wetland-drought": "Wetland Drought",
    "precipitation-extremes": "Precipitation Extremes",
    "heat-waves": "Heat Waves",
    "cold-waves": "Cold Waves",
}

# Stop reporting after this many problems — enough to fix a file, not a flood.
_MAX_ERRORS = 50


@dataclass
class ValidationResult:
    errors: list[str] = field(default_factory=list)
    summary: dict[str, Any] | None = None

    @property
    def ok(self) -> bool:
        return not self.errors


@lru_cache
def ramsar_site_ids(path: Path | None = None) -> frozenset[str]:
    """Official Ramsar Site numbers (as strings) from the portal's site list."""
    source = path or settings.RAMSAR_SITES_FILE
    data = json.loads(Path(source).read_text(encoding="utf-8"))
    return frozenset(str(site["id"]) for site in data["sites"])


def _is_non_empty_str(value: Any) -> TypeGuard[str]:
    return isinstance(value, str) and value.strip() != ""


def validate_climate_dataset(raw: bytes, theme: str) -> ValidationResult:
    result = ValidationResult()
    errors = result.errors

    def add(message: str) -> None:
        if len(errors) < _MAX_ERRORS:
            errors.append(message)

    if theme not in CLIMATE_THEMES:
        add(f'Unknown theme "{theme}".')
        return result

    try:
        data = json.loads(raw.decode("utf-8-sig"))
    except UnicodeDecodeError:
        add("The file is not UTF-8 text.")
        return result
    except json.JSONDecodeError as exc:
        add(f"The file is not valid JSON (line {exc.lineno}, column {exc.colno}: {exc.msg}).")
        return result

    if not isinstance(data, dict):
        add("The top level of the file must be a JSON object.")
        return result

    if data.get("theme") != theme:
        add(f'"theme" must be "{theme}" for this upload (found {json.dumps(data.get("theme"))}).')
    for name in ("source", "baseline"):
        if not _is_non_empty_str(data.get(name)):
            add(f'"{name}" is required and must be non-empty text.')
    for name in ("method", "updated"):
        if name in data and not isinstance(data[name], str):
            add(f'"{name}" must be text if present.')

    years = data.get("years")
    if (
        not isinstance(years, list)
        or not years
        or not all(isinstance(y, int) and not isinstance(y, bool) for y in years)
    ):
        add('"years" must be a non-empty list of whole numbers.')
        years = None
    elif any(b <= a for a, b in zip(years, years[1:], strict=False)):
        add('"years" must be in increasing order without repeats.')

    metrics = data.get("metrics")
    if not isinstance(metrics, list) or not metrics:
        add('"metrics" must be a non-empty list.')
        return result

    known_ids = ramsar_site_ids()
    seen_keys: set[str] = set()
    covered_sites: set[str] = set()
    for i, metric in enumerate(metrics, start=1):
        where = f"metrics[{i}]"
        if not isinstance(metric, dict):
            add(f"{where} must be an object.")
            continue
        key = metric.get("key")
        if _is_non_empty_str(key):
            where = f'metric "{key}"'
            if key in seen_keys:
                add(f"{where} appears more than once.")
            seen_keys.add(key)
        for prop in ("key", "label", "unit"):
            if not _is_non_empty_str(metric.get(prop)):
                add(f'{where}: "{prop}" is required and must be non-empty text.')
        if "description" in metric and not isinstance(metric["description"], str):
            add(f'{where}: "description" must be text if present.')

        values = metric.get("values")
        if not isinstance(values, dict) or not values:
            add(f'{where}: "values" must be an object keyed by Ramsar Site number.')
            continue
        for site_id, series in values.items():
            if not site_id.isdigit() or site_id not in known_ids:
                add(f'{where}: "{site_id}" is not a Ramsar Site number in the portal\'s site list.')
                continue
            covered_sites.add(site_id)
            if not isinstance(series, list):
                add(f"{where}, site {site_id}: values must be a list.")
                continue
            if years is not None and len(series) != len(years):
                add(
                    f"{where}, site {site_id}: {len(series)} values for {len(years)} years "
                    "(use null for a missing year)."
                )
            for v in series:
                if v is None:
                    continue
                if isinstance(v, bool) or not isinstance(v, int | float) or not math.isfinite(v):
                    add(f"{where}, site {site_id}: values must be numbers or null (found {v!r}).")
                    break

    if len(errors) >= _MAX_ERRORS:
        errors.append("Further problems were not listed. Fix the ones above and upload again.")
    if not errors:
        result.summary = {
            "source": data["source"],
            "baseline": data["baseline"],
            "years": [years[0], years[-1]] if years else None,
            "metrics": [{"key": m["key"], "label": m["label"], "unit": m["unit"]} for m in metrics],
            "siteCount": len(covered_sites),
        }
    return result


def publish_climate_file(raw: bytes, theme: str) -> Path:
    """Atomically writes the file the portal serves for `theme`."""
    target_dir = Path(settings.CLIMATE_PUBLISH_DIR)
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / f"{theme}.json"
    fd, tmp = tempfile.mkstemp(dir=target_dir, prefix=f".{theme}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "wb") as fh:
            fh.write(raw)
        os.replace(tmp, target)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise
    return target


def unpublish_climate_file(theme: str) -> None:
    (Path(settings.CLIMATE_PUBLISH_DIR) / f"{theme}.json").unlink(missing_ok=True)
