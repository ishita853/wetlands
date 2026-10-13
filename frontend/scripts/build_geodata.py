"""Build the portal's static geodata from the project-supplied sources.

Inputs  (data/source/):
  ramsar-sites-india.xlsx          Ramsar Sites Information Service export (101 sites)
  india-boundaries/*.shp           India state / district boundaries

Outputs:
  data/ramsar-sites.json           Full site records (read at build time by the app)
  public/data/india-states.geojson     Simplified state boundaries (WGS84)
  public/data/india-districts.geojson  Simplified district boundaries (WGS84)

State and district are derived by point-in-polygon against the full-resolution
boundaries (not from the free-text "large administrative region" field). Sites
whose point falls just offshore are assigned to the nearest polygon and flagged.

Run from frontend/ with the backend virtualenv (geopandas, openpyxl):
  ../backend/.venv/Scripts/python.exe scripts/build_geodata.py
"""

from __future__ import annotations

import html
import json
import re
from pathlib import Path

import geopandas as gpd
import pandas as pd
from shapely.geometry import Point, mapping

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "data" / "source"
OUT_DATA = ROOT / "data"
OUT_PUBLIC = ROOT / "public" / "data"

STATE_TOLERANCE = 0.005  # degrees (~500 m) — national/state zoom
DISTRICT_TOLERANCE = 0.01
COORD_PRECISION = 4

# The boundary file's state labels, corrected to official names.
STATE_NAMES = {
    "Tamilnadu": "Tamil Nadu",
    "Chhattishgarh": "Chhattisgarh",
    "Telengana": "Telangana",
    "Andaman & Nicobar": "Andaman and Nicobar Islands",
    "Daman and Diu and Dadra and Nagar Haveli": "Dadra and Nagar Haveli and Daman and Diu",
}


def round_coords(obj):
    if isinstance(obj, float):
        return round(obj, COORD_PRECISION)
    if isinstance(obj, (list, tuple)):
        return [round_coords(v) for v in obj]
    return obj


def write_geojson(gdf: gpd.GeoDataFrame, props: list[str], path: Path) -> None:
    features = []
    for _, row in gdf.iterrows():
        geom = row.geometry
        if geom is None or geom.is_empty:
            continue
        g = mapping(geom)
        features.append(
            {
                "type": "Feature",
                "properties": {p: row[p] for p in props},
                "geometry": {"type": g["type"], "coordinates": round_coords(g["coordinates"])},
            }
        )
    path.write_text(
        json.dumps({"type": "FeatureCollection", "features": features}, separators=(",", ":")),
        encoding="utf-8",
    )
    print(f"  wrote {path.relative_to(ROOT)}  ({path.stat().st_size / 1024:.0f} KB, {len(features)} features)")


def clean_text(value) -> str | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    text = str(value).replace("�", "").strip()  # drop encoding-damage glyphs
    return text or None


def summary_paragraphs(raw) -> list[str]:
    text = clean_text(raw)
    if not text:
        return []
    parts = re.split(r"</p>\s*|<br\s*/?>", text)
    paragraphs = []
    for part in parts:
        plain = html.unescape(re.sub(r"<[^>]+>", "", part)).replace("\xa0", " ")
        plain = re.sub(r"\s+", " ", plain).strip()
        if plain:
            paragraphs.append(plain)
    return paragraphs


def split_list(raw) -> list[str]:
    text = clean_text(raw)
    return [t.strip() for t in text.split(",") if t.strip()] if text else []


WETLAND_GROUPS = ["Inland wetlands", "Marine or coastal wetlands", "Human-made wetlands"]


def wetland_types(raw) -> dict[str, list[str]]:
    """'Inland wetlands, Q: …, Human-made wetlands, 6: …' → {group: [types]}"""
    groups: dict[str, list[str]] = {}
    current = None
    for token in split_list(raw):
        if token in WETLAND_GROUPS:
            current = token
            groups.setdefault(current, [])
        elif current:
            # Type names contain commas ("E: Sand, shingle or pebble shores"):
            # a token without a "X:" code continues the previous type.
            if groups[current] and not re.match(r"^[A-Za-z0-9]{1,3}:", token):
                groups[current][-1] += f", {token}"
            else:
                groups[current].append(token)
    return groups


def main() -> None:
    OUT_PUBLIC.mkdir(parents=True, exist_ok=True)

    print("Boundaries")
    states = gpd.read_file(SRC / "india-boundaries" / "India_State_Boundary.shp").to_crs(4326)
    states = states.rename(columns={"State_Name": "name"})[["name", "geometry"]]
    states["name"] = states["name"].replace(STATE_NAMES)
    states["geometry"] = states.geometry.make_valid()
    # Some states are split across several records (e.g. Puducherry).
    states = states.dissolve(by="name", as_index=False)

    districts = gpd.read_file(SRC / "india-boundaries" / "India_District_Boundary.shp")
    districts = districts.set_crs(4326, allow_override=True)
    districts = districts.rename(columns={"NAME_2": "name", "NAME_1": "state"})[["name", "state", "geometry"]]
    districts["geometry"] = districts.geometry.make_valid()

    simple_states = states.copy()
    simple_states["geometry"] = simple_states.geometry.simplify(STATE_TOLERANCE, preserve_topology=True)
    write_geojson(simple_states, ["name"], OUT_PUBLIC / "india-states.geojson")

    simple_districts = districts.copy()
    simple_districts["geometry"] = simple_districts.geometry.simplify(DISTRICT_TOLERANCE, preserve_topology=True)
    write_geojson(simple_districts, ["name", "state"], OUT_PUBLIC / "india-districts.geojson")

    print("Ramsar sites")
    df = pd.read_excel(SRC / "ramsar-sites-india.xlsx")
    assert len(df) == 101, f"expected 101 sites, found {len(df)}"
    assert df["Ramsar Site No."].is_unique

    # Metric CRS for nearest-polygon distances.
    states_m = states.to_crs(7755)
    districts_m = districts.to_crs(7755)

    sites = []
    for _, r in df.iterrows():
        lat, lon = float(r["Latitude"]), float(r["Longitude"])
        pt = gpd.GeoSeries([Point(lon, lat)], crs=4326).to_crs(7755).iloc[0]

        def locate(layer_m: gpd.GeoDataFrame, field: str):
            hit = layer_m[layer_m.contains(pt)]
            if len(hit):
                return hit.iloc[0][field], 0.0
            d = layer_m.distance(pt)
            i = d.idxmin()
            return layer_m.loc[i, field], round(float(d[i]) / 1000, 1)

        state, state_km = locate(states_m, "name")
        district, district_km = locate(districts_m, "name")
        designation = pd.Timestamp(r["Designation date"]).date()

        criteria = [n for n in range(1, 10) if str(r.get(f"Criterion{n}", "")).strip().lower() == "yes"]
        sites.append(
            {
                "id": int(r["Ramsar Site No."]),
                "name": clean_text(r["Site name"]),
                "designationDate": designation.isoformat(),
                "designationYear": designation.year,
                "lastPublicationDate": (
                    pd.Timestamp(r["Last publication date"]).date().isoformat()
                    if not pd.isna(r["Last publication date"])
                    else None
                ),
                "areaHa": float(r["Area (ha)"]),
                "latitude": round(lat, 6),
                "longitude": round(lon, 6),
                "state": state,
                "district": district,
                # >0 means the point lies outside every polygon (typically
                # coastal/marine sites); value is the distance in km to the
                # polygon it was assigned to.
                "stateOffsetKm": state_km,
                "districtOffsetKm": district_km,
                "administrativeRegion": clean_text(r["large administrative region"]),
                "wetlandTypes": wetland_types(r["Wetland Type"]),
                "criteria": criteria,
                "elevationMaxM": None if pd.isna(r["Maximum elevation"]) else float(r["Maximum elevation"]),
                "elevationMinM": None if pd.isna(r["Minimum elevation"]) else float(r["Minimum elevation"]),
                "montreuxListed": clean_text(r["Montreux listed"]),
                "managementPlanImplemented": clean_text(r["Management plan implemented"]),
                "managementPlanAvailable": clean_text(r["Management plan available"]),
                "ecosystemServices": split_list(r["Ecosystem services"]),
                "threats": split_list(r["Threats"]),
                "globalDesignations": clean_text(r["Global international legal designations"]),
                "nationalDesignation": clean_text(r["National conservation designation"]),
                "summary": summary_paragraphs(r["Annotated summary"]),
            }
        )

    sites.sort(key=lambda s: s["name"].lower())
    out = OUT_DATA / "ramsar-sites.json"
    out.write_text(
        json.dumps(
            {
                "source": "Ramsar Sites Information Service — India (project-supplied export)",
                "siteCount": len(sites),
                "sites": sites,
            },
            ensure_ascii=False,
            indent=1,
        ),
        encoding="utf-8",
    )
    print(f"  wrote {out.relative_to(ROOT)}  ({out.stat().st_size / 1024:.0f} KB, {len(sites)} sites)")

    offshore = [s for s in sites if s["stateOffsetKm"] > 0]
    print(f"  {len(offshore)} site points outside all state polygons (assigned to nearest):")
    for s in offshore:
        print(f"    {s['name']}: {s['state']} ({s['stateOffsetKm']} km)")


if __name__ == "__main__":
    main()
