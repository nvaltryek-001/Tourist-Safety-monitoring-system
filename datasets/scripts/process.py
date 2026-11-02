"""Clean, validate and convert raw downloads into application-ready layers.

Inputs : datasets/raw/** (never modified)
Outputs: datasets/processed/** (cleaned tables), datasets/application_data/**
         (what the backend serves), datasets/synthetic_test_data/**, and
         datasets/dataset_manifest.csv.
Standard library only.
"""

from __future__ import annotations

import csv
import io
import json
import math
import random
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from xml.sax.saxutils import escape

sys.path.insert(0, str(Path(__file__).parent))
from common import (  # noqa: E402
    bbox_of,
    centroid,
    load_json,
    load_karnataka_districts,
    norm_name,
    point_in_geometry,
    ring_area_centroid,
    simplify,
)

ROOT = Path(__file__).resolve().parents[1]
RAW, PROC, APP, SYN = ROOT / "raw", ROOT / "processed", ROOT / "application_data", ROOT / "synthetic_test_data"
for d in (PROC, APP, SYN):
    d.mkdir(parents=True, exist_ok=True)
REPORT: dict[str, dict] = {}


def write_geojson(path: Path, features: list[dict], meta: dict | None = None) -> None:
    fc = {"type": "FeatureCollection", "features": features}
    if meta:
        fc["metadata"] = meta
    path.write_text(json.dumps(fc, separators=(",", ":"), ensure_ascii=False), encoding="utf-8")


def round_coords(obj, nd=5):
    if isinstance(obj, list):
        if obj and isinstance(obj[0], (int, float)):
            return [round(obj[0], nd), round(obj[1], nd)]
        return [round_coords(o, nd) for o in obj]
    return obj


# ----------------------------------------------------------------- districts
class DistrictIndex:
    def __init__(self, districts: list[dict]):
        self.items = [(d["name"], d["geometry"], bbox_of(d["geometry"])) for d in districts]

    def lookup(self, lat: float, lon: float) -> str | None:
        for name, geom, (w, s, e, n) in self.items:
            if w <= lon <= e and s <= lat <= n and point_in_geometry(lat, lon, geom):
                return name
        return None


def process_districts() -> DistrictIndex | None:
    try:
        districts = load_karnataka_districts(RAW)
    except FileNotFoundError:
        REPORT["karnataka_districts"] = {"status": "MISSING_RAW"}
        return None
    feats = []
    for d in districts:
        geom = d["geometry"]
        polys = [geom["coordinates"]] if geom["type"] == "Polygon" else geom["coordinates"]
        simple = [[simplify([tuple(p[:2]) for p in ring], 0.002) for ring in rings] for rings in polys]
        simple = [[r for r in rings if len(r) >= 4] for rings in simple]
        simple = [rings for rings in simple if rings]
        area = sum(abs(ring_area_centroid(list(rings[0]))[0]) for rings in simple) * (111.32 ** 2) * math.cos(math.radians(d["lat"]))
        feats.append({
            "type": "Feature",
            "geometry": {"type": "MultiPolygon", "coordinates": round_coords([[list(map(list, r)) for r in rings] for rings in simple])},
            "properties": {"name": d["name"], "shapeID": d["shapeID"], "centroid_lat": d["lat"], "centroid_lon": d["lon"],
                           "approx_area_km2": round(area, 1), "source": "geoBoundaries gbOpen IND ADM2"},
        })
    write_geojson(APP / "karnataka_districts.geojson", feats, {"attribution": "geoBoundaries (www.geoboundaries.org)",
                  "note": "For analysis only; official boundaries are published by the Survey of India."})
    REPORT["karnataka_districts"] = {"status": "OK", "records": len(feats), "output": "application_data/karnataka_districts.geojson",
                                     "steps": "Karnataka districts selected by centroid-in-ADM1; Douglas-Peucker simplified (0.002°)"}
    return DistrictIndex(districts)


# --------------------------------------------------------------------- OSM
def osm_elements(name: str) -> list[dict]:
    try:
        return load_json(RAW / "osm" / f"{name}.json").get("elements", [])
    except FileNotFoundError:
        REPORT[name] = {"status": "MISSING_RAW"}
        return []


def el_point(el: dict) -> tuple[float, float] | None:
    if "lat" in el and "lon" in el:
        return el["lat"], el["lon"]
    c = el.get("center")
    if c:
        return c["lat"], c["lon"]
    geom = el.get("geometry")
    if geom:
        return sum(p["lat"] for p in geom) / len(geom), sum(p["lon"] for p in geom) / len(geom)
    return None


def address(tags: dict) -> str | None:
    if tags.get("addr:full"):
        return tags["addr:full"]
    parts = [tags.get(k) for k in ("addr:housenumber", "addr:street", "addr:suburb", "addr:city", "addr:postcode")]
    joined = ", ".join(p for p in parts if p)
    return joined or None


def name_of(tags: dict) -> str | None:
    return tags.get("name:en") or tags.get("name") or tags.get("official_name")


def process_facilities(index: DistrictIndex | None) -> None:
    sources = [("osm_police", lambda t: "POLICE"),
               ("osm_hospitals", lambda t: "HOSPITAL" if t.get("amenity") == "hospital" else "CLINIC"),
               ("osm_fire_stations", lambda t: "FIRE_STATION"),
               ("osm_pharmacies", lambda t: "PHARMACY")]
    feats, seen, counts, unnamed = [], set(), Counter(), Counter()
    for src, kind in sources:
        for el in osm_elements(src):
            tags = el.get("tags") or {}
            pt = el_point(el)
            if not pt or not (11.4 <= pt[0] <= 18.6 and 74.0 <= pt[1] <= 78.7):
                continue
            ref = f"{el['type']}/{el['id']}"
            if ref in seen:
                continue
            seen.add(ref)
            ftype = kind(tags)
            nm = name_of(tags)
            if not nm:
                unnamed[ftype] += 1
            feats.append({
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [round(pt[1], 6), round(pt[0], 6)]},
                "properties": {
                    "facility_type": ftype, "name": nm or f"Unnamed {ftype.replace('_', ' ').lower()}",
                    "osm_id": ref, "phone": tags.get("phone") or tags.get("contact:phone"),
                    "address": address(tags), "opening_hours": tags.get("opening_hours"),
                    "emergency": {"yes": True, "no": False}.get(tags.get("emergency")),
                    "district": index.lookup(pt[0], pt[1]) if index else None,
                    "operator": tags.get("operator"),
                },
            })
            counts[ftype] += 1
    feats, removed = dedupe_facilities(feats)
    with (PROC / "facility_duplicates_removed.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["removed_osm_id", "kept_osm_id", "facility_type", "name", "distance_m"])
        w.writerows(removed)
    counts = Counter(f["properties"]["facility_type"] for f in feats)
    write_geojson(APP / "emergency_facilities.geojson", feats, {"attribution": "© OpenStreetMap contributors (ODbL 1.0)"})
    with (PROC / "emergency_facilities.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["osm_id", "facility_type", "name", "latitude", "longitude", "district", "phone", "address"])
        for f in feats:
            p, (lon, lat) = f["properties"], f["geometry"]["coordinates"]
            w.writerow([p["osm_id"], p["facility_type"], p["name"], lat, lon, p["district"], p["phone"], p["address"]])
    REPORT["emergency_facilities"] = {"status": "OK", "records": len(feats), "by_type": dict(counts), "unnamed": dict(unnamed),
                                      "duplicates_removed": len(removed),
                                      "output": "application_data/emergency_facilities.geojson",
                                      "steps": "nodes/ways/relations -> centre point; de-duplicated by OSM id and by same type+name within 100 m "
                                               "(e.g. a hospital mapped as both a point and a building; the record with more details is kept); "
                                               "bbox-validated; district by point-in-polygon"}


def dedupe_facilities(feats: list[dict], radius_m: float = 100) -> tuple[list[dict], list[list]]:
    """Drop OSM double-mapping: same facility type + same (non-generic) name within radius_m."""
    import math

    def dist(a, b):
        (lo1, la1), (lo2, la2) = a, b
        p1, p2 = math.radians(la1), math.radians(la2)
        h = math.sin((p2 - p1) / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(math.radians(lo2 - lo1) / 2) ** 2
        return 6371000 * 2 * math.asin(math.sqrt(min(1.0, h)))

    def richness(f):
        p = f["properties"]
        return sum(1 for k in ("phone", "address", "opening_hours", "operator") if p.get(k)) + (0.5 if p["osm_id"].startswith("node") else 0)

    groups: dict[tuple, list[dict]] = {}
    for f in feats:
        p = f["properties"]
        groups.setdefault((p["facility_type"], p["name"].strip().lower()), []).append(f)
    keep, removed = [], []
    for (ftype, name), members in groups.items():
        if name.startswith("unnamed") or len(members) == 1:
            keep += members
            continue
        members = sorted(members, key=richness, reverse=True)
        kept: list[dict] = []
        for f in members:
            twin = next((k for k in kept if dist(k["geometry"]["coordinates"], f["geometry"]["coordinates"]) < radius_m), None)
            if twin:
                removed.append([f["properties"]["osm_id"], twin["properties"]["osm_id"], ftype, f["properties"]["name"],
                                round(dist(twin["geometry"]["coordinates"], f["geometry"]["coordinates"]), 1)])
            else:
                kept.append(f)
        keep += kept
    return keep, removed


def process_attractions(index: DistrictIndex | None) -> None:
    feats = []
    for el in osm_elements("osm_tourism"):
        tags = el.get("tags") or {}
        pt = el_point(el)
        nm = name_of(tags)
        if not pt or not nm:
            continue
        cat = tags.get("tourism") or tags.get("historic")
        feats.append({"type": "Feature", "geometry": {"type": "Point", "coordinates": [round(pt[1], 6), round(pt[0], 6)]},
                      "properties": {"name": nm, "category": cat, "osm_id": f"{el['type']}/{el['id']}",
                                     "district": index.lookup(pt[0], pt[1]) if index else None,
                                     "wikidata": tags.get("wikidata"), "website": tags.get("website")}})
    write_geojson(APP / "tourist_attractions.geojson", feats, {"attribution": "© OpenStreetMap contributors (ODbL 1.0)"})
    REPORT["tourist_attractions"] = {"status": "OK", "records": len(feats), "by_category": dict(Counter(f["properties"]["category"] for f in feats)),
                                     "output": "application_data/tourist_attractions.geojson", "steps": "named POIs only; centre points"}


def stitch(ways: list[list[tuple]]) -> list[list[tuple]]:
    """Join open way segments into closed rings (for multipolygon relations)."""
    rings, pool = [], [w[:] for w in ways if len(w) >= 2]
    while pool:
        ring = pool.pop(0)
        changed = True
        while ring[0] != ring[-1] and changed:
            changed = False
            for i, seg in enumerate(pool):
                if seg[0] == ring[-1]:
                    ring += seg[1:]
                elif seg[-1] == ring[-1]:
                    ring += seg[::-1][1:]
                elif seg[-1] == ring[0]:
                    ring = seg[:-1] + ring
                elif seg[0] == ring[0]:
                    ring = seg[::-1][:-1] + ring
                else:
                    continue
                pool.pop(i)
                changed = True
                break
        if ring[0] == ring[-1] and len(ring) >= 4:
            rings.append(ring)
    return rings


def process_protected_areas(index: DistrictIndex | None) -> None:
    feats, invalid, seen = [], 0, set()
    elements = []
    for part in ("osm_protected_areas_rel_pa", "osm_protected_areas_rel_nr", "osm_protected_areas_ways"):
        if (RAW / "osm" / f"{part}.json").exists() or (RAW / "osm" / f"{part}.json.gz").exists():
            elements += osm_elements(part)
    REPORT.pop("osm_protected_areas", None)
    for el in elements:
        if (el["type"], el["id"]) in seen:
            continue
        seen.add((el["type"], el["id"]))
        tags = el.get("tags") or {}
        outers, inners = [], []
        if el["type"] == "way" and el.get("geometry"):
            ring = [(p["lon"], p["lat"]) for p in el["geometry"]]
            if ring[0] == ring[-1]:
                outers = [ring]
        elif el["type"] == "relation":
            members = el.get("members") or []
            outer_ways = [[(p["lon"], p["lat"]) for p in m["geometry"]] for m in members if m.get("role") in ("outer", "") and m.get("geometry")]
            inner_ways = [[(p["lon"], p["lat"]) for p in m["geometry"]] for m in members if m.get("role") == "inner" and m.get("geometry")]
            outers, inners = stitch(outer_ways), stitch(inner_ways)
        if not outers:
            invalid += 1
            continue
        polys = []
        for ring in outers:
            s = simplify(ring, 0.0005)
            if len(s) < 4:
                continue
            holes = [simplify(h, 0.0005) for h in inners if point_in_geometry(h[0][1], h[0][0], {"type": "Polygon", "coordinates": [ring]})]
            polys.append([list(map(list, s))] + [list(map(list, h)) for h in holes if len(h) >= 4])
        if not polys:
            invalid += 1
            continue
        geom = {"type": "MultiPolygon", "coordinates": round_coords(polys)}
        lat, lon = centroid(geom)
        area = sum(abs(ring_area_centroid([tuple(p) for p in p_[0]])[0]) for p_ in polys) * (111.32 ** 2) * math.cos(math.radians(lat))
        feats.append({"type": "Feature", "geometry": geom, "properties": {
            "name": name_of(tags) or "Unnamed protected area", "osm_id": f"{el['type']}/{el['id']}",
            "category": "PROTECTED_AREA", "protect_class": tags.get("protect_class"), "protection_title": tags.get("protection_title"),
            "leisure": tags.get("leisure"), "operator": tags.get("operator"), "approx_area_km2": round(area, 2),
            "centroid_lat": round(lat, 5), "centroid_lon": round(lon, 5),
            "district": index.lookup(lat, lon) if index else None,
            "verification_status": "OSM_COMMUNITY_DATA", "severity_suggestion": "CAUTION",
            "evidence": f"OpenStreetMap {el['type']}/{el['id']} boundary=protected_area or leisure=nature_reserve",
        }})
    write_geojson(APP / "protected_areas.geojson", feats, {"attribution": "© OpenStreetMap contributors (ODbL 1.0)",
                  "note": "Community-mapped boundaries; not legally verified. Imported zones should stay PENDING_REVIEW."})
    write_kml(APP / "protected_areas.kml", feats)
    REPORT["protected_areas"] = {"status": "OK", "records": len(feats), "unusable_geometry": invalid,
                                 "output": "application_data/protected_areas.geojson (+ .kml)",
                                 "steps": "ways + multipolygon relations stitched into rings, inner holes kept, simplified 0.0005°"}


def process_hazards(index: DistrictIndex | None) -> None:
    feats = []
    for el in osm_elements("osm_water_hazards"):
        tags = el.get("tags") or {}
        pt = el_point(el)
        if not pt:
            continue
        cat = "WATERFALL" if tags.get("waterway") == "waterfall" else "CLIFF"
        feats.append({"type": "Feature", "geometry": {"type": "Point", "coordinates": [round(pt[1], 6), round(pt[0], 6)]},
                      "properties": {"name": name_of(tags) or cat.title(), "category": cat, "osm_id": f"{el['type']}/{el['id']}",
                                     "district": index.lookup(pt[0], pt[1]) if index else None,
                                     "suggested_radius_m": 150 if cat == "WATERFALL" else 100, "verification_status": "OSM_COMMUNITY_DATA"}})
    write_geojson(APP / "natural_hazards.geojson", feats, {"attribution": "© OpenStreetMap contributors (ODbL 1.0)",
                  "note": "Natural features where tourist caution is advisable; not official danger designations."})
    REPORT["natural_hazards"] = {"status": "OK", "records": len(feats), "by_category": dict(Counter(f["properties"]["category"] for f in feats)),
                                 "output": "application_data/natural_hazards.geojson"}


def process_roads() -> None:
    feats = []
    for el in osm_elements("osm_study_roads"):
        geom = el.get("geometry")
        if not geom or len(geom) < 2:
            continue
        line = simplify([(p["lon"], p["lat"]) for p in geom], 0.00005)
        feats.append({"type": "Feature", "geometry": {"type": "LineString", "coordinates": round_coords([list(p) for p in line], 6)},
                      "properties": {"highway": (el.get("tags") or {}).get("highway"), "name": name_of(el.get("tags") or {}),
                                     "osm_id": f"way/{el['id']}"}})
    write_geojson(PROC / "study_area_roads.geojson", feats, {"attribution": "© OpenStreetMap contributors (ODbL 1.0)",
                  "bbox": "13.06,77.45,13.27,77.67 (SVIT / Rajanukunte study area)"})
    REPORT["study_area_roads"] = {"status": "OK", "records": len(feats), "by_highway": dict(Counter(f["properties"]["highway"] for f in feats)),
                                  "output": "processed/study_area_roads.geojson"}


def write_kml(path: Path, feats: list[dict]) -> None:
    out = ['<?xml version="1.0" encoding="UTF-8"?><kml xmlns="http://www.opengis.net/kml/2.2"><Document>']
    for f in feats:
        g, p = f["geometry"], f["properties"]
        polys = g["coordinates"] if g["type"] == "MultiPolygon" else [g["coordinates"]]
        body = "".join(
            "<Polygon>" + "".join(
                f"<{'outerBoundaryIs' if i == 0 else 'innerBoundaryIs'}><LinearRing><coordinates>"
                + " ".join(f"{x},{y}" for x, y in ring) + f"</coordinates></LinearRing></{'outerBoundaryIs' if i == 0 else 'innerBoundaryIs'}>"
                for i, ring in enumerate(rings)) + "</Polygon>"
            for rings in polys)
        data = "".join(f'<Data name="{escape(k)}"><value>{escape(str(v))}</value></Data>' for k, v in p.items() if v is not None)
        out.append(f"<Placemark><name>{escape(str(p.get('name')))}</name><ExtendedData>{data}</ExtendedData><MultiGeometry>{body}</MultiGeometry></Placemark>")
    out.append("</Document></kml>")
    path.write_text("".join(out), encoding="utf-8")


# ----------------------------------------------------------------- weather
def process_weather() -> None:
    try:
        rows = load_json(RAW / "open_meteo" / "karnataka_districts_daily_2024_2025.json")
    except FileNotFoundError:
        REPORT["weather_daily"] = {"status": "MISSING_RAW"}
        return
    keys = ["temperature_2m_max", "temperature_2m_min", "precipitation_sum", "rain_sum", "wind_speed_10m_max", "wind_gusts_10m_max", "weather_code"]
    n = missing = 0
    with (PROC / "weather_daily_karnataka_2024_2025.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["district", "date", *keys])
        for r in rows:
            d = r["daily"]
            for i, day in enumerate(d["time"]):
                vals = [d.get(k, [None] * len(d["time"]))[i] for k in keys]
                missing += sum(v is None for v in vals)
                w.writerow([r["district"], day, *vals])
                n += 1
    REPORT["weather_daily"] = {"status": "OK", "records": n, "missing_values": missing, "districts": len(rows),
                               "output": "processed/weather_daily_karnataka_2024_2025.csv",
                               "steps": "ERA5 reanalysis via Open-Meteo archive at district centroids; daily values, Asia/Kolkata"}


# ------------------------------------------------------- opencity tables
def sniff_csv(raw: bytes) -> list[list[str]]:
    text = raw.decode("utf-8-sig", errors="replace")
    return [row for row in csv.reader(io.StringIO(text)) if any(c.strip() for c in row)]


def process_opencity_tables() -> None:
    """Copy each OpenCity CSV to processed/ with normalised headers (raw stays untouched)."""
    base = RAW / "opencity"
    if not base.exists():
        return
    for path in sorted(base.glob("*/*.csv")):
        rows = sniff_csv(path.read_bytes())
        if not rows:
            continue
        header = [re.sub(r"[^a-z0-9]+", "_", h.strip().lower()).strip("_") or f"col{i}" for i, h in enumerate(rows[0])]
        out = PROC / "crime_and_rainfall" / path.parent.name / path.name
        out.parent.mkdir(parents=True, exist_ok=True)
        with out.open("w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh)
            w.writerow(header)
            w.writerows(r + [""] * (len(header) - len(r)) for r in rows[1:])
        REPORT[f"{path.parent.name}:{path.stem}"] = {"status": "OK", "records": len(rows) - 1, "columns": len(header),
                                                     "output": str(out.relative_to(ROOT)), "steps": "UTF-8, blank rows dropped, snake_case headers"}


# --------------------------------------------------------- synthetic data
def synthetic_demo_zones() -> None:
    """Re-derive the 200 DEMO-KA-* synthetic zones exactly as backend/app/seed_demo_zones.py creates them."""
    src = (ROOT.parent / "backend" / "app" / "seed_demo_zones.py").read_text(encoding="utf-8-sig")
    districts = re.findall(r'\("([^"]+)", ([\d.]+), ([\d.]+)\)', src)
    rng = random.Random(20261016)
    feats = []
    for i in range(1, 201):
        district, lat, lon = districts[(i - 1) % len(districts)]
        la, lo = float(lat) + rng.uniform(-0.04, 0.04), float(lon) + rng.uniform(-0.04, 0.04)
        radius = rng.choice([100, 150, 200, 250, 300, 500])
        feats.append({"type": "Feature", "geometry": {"type": "Point", "coordinates": [round(lo, 6), round(la, 6)]},
                      "properties": {"name": f"DEMO-KA-{i:03d}", "radius_meters": radius, "zone_type": "RESTRICTED",
                                     "district": district, "synthetic": True,
                                     "description": "SYNTHETIC TEST DATA ONLY; not a verified restricted or hazardous location"}})
    write_geojson(SYN / "demo_ka_synthetic_zones.geojson", feats, {"warning": "SYNTHETIC TEST DATA - never present as real hazards"})
    REPORT["demo_ka_synthetic_zones"] = {"status": "OK", "records": len(feats), "output": "synthetic_test_data/demo_ka_synthetic_zones.geojson",
                                         "steps": "same RNG seed and algorithm as seed_demo_zones.py"}


# ---------------------------------------------------------------- manifest
SOURCES = {
    "osm_": ("OpenStreetMap via Overpass API", "ODbL 1.0", "© OpenStreetMap contributors", "Karnataka (IN-KA)", "continuous (community edits)"),
    "geoboundaries": ("geoBoundaries gbOpen", "see licence column", "www.geoboundaries.org", "India ADM1/ADM2", "periodic releases"),
    "ksp_crime": ("Karnataka State Police data via OpenCity (data.opencity.in)", "Public Domain", "ksp.karnataka.gov.in / OpenCity", "Karnataka districts", "annual"),
    "ksndmc": ("KSNDMC rainfall via OpenCity", "Public Domain", "www.ksndmc.org / OpenCity", "Karnataka districts", "annual"),
    "open_meteo": ("Open-Meteo Historical Weather API (ERA5)", "CC BY 4.0", "Open-Meteo.com", "Karnataka district centroids", "daily"),
}


def write_manifest() -> None:
    log = json.loads((RAW / "fetch_log.json").read_text()) if (RAW / "fetch_log.json").exists() else []
    rows = []
    for e in log:
        sid = e["source_id"]
        meta = next((v for k, v in SOURCES.items() if sid.startswith(k)), ("", "", "", "", ""))
        rows.append({
            "dataset_id": sid, "kind": "raw", "title": e.get("title") or sid, "publisher": meta[0],
            "source_url": e.get("url"), "download_date": e.get("downloaded_at"), "status": e["status"],
            "licence": e.get("licence") or meta[1], "attribution": e.get("attribution") or meta[2],
            "coverage": meta[3], "update_frequency": meta[4], "records": e.get("records", ""),
            "file": e.get("file", ""), "processing": "original, unmodified", "notes": e.get("error", ""),
        })
    for sid, r in REPORT.items():
        rows.append({
            "dataset_id": sid, "kind": "processed", "title": sid, "publisher": "SafeTrail processing scripts",
            "source_url": "datasets/scripts/process.py", "download_date": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "status": r.get("status"), "licence": "inherits source licence", "attribution": "", "coverage": "",
            "update_frequency": "on pipeline run", "records": r.get("records", ""), "file": r.get("output", ""),
            "processing": r.get("steps", ""), "notes": json.dumps({k: v for k, v in r.items() if k not in {"status", "records", "output", "steps"}}),
        })
    rows.append({"dataset_id": "india_tourism_statistics", "kind": "raw", "title": "India Tourism Statistics (Ministry of Tourism)",
                 "publisher": "Ministry of Tourism, Government of India", "source_url": "https://tourism.gov.in/market-research-and-statistics",
                 "download_date": "", "status": "NOT_DOWNLOADED", "licence": "", "attribution": "", "coverage": "India / states",
                 "update_frequency": "annual", "records": "", "file": "",
                 "processing": "", "notes": "Published as PDF reports; no machine-readable district table found. Tourism layer uses OSM POIs instead."})
    rows.append({"dataset_id": "ncrb_crime_in_india", "kind": "raw", "title": "NCRB Crime in India", "publisher": "National Crime Records Bureau",
                 "source_url": "https://www.ncrb.gov.in/crime-in-india.html", "download_date": "", "status": "NOT_DOWNLOADED",
                 "licence": "", "attribution": "", "coverage": "India", "update_frequency": "annual", "records": "", "file": "",
                 "processing": "", "notes": "PDF/XLSX behind an interactive site; Karnataka State Police district tables (OpenCity) used instead."})
    rows.append({"dataset_id": "imd_weather", "kind": "raw", "title": "IMD observations", "publisher": "India Meteorological Department",
                 "source_url": "https://mausam.imd.gov.in", "download_date": "", "status": "NOT_DOWNLOADED", "licence": "", "attribution": "",
                 "coverage": "India", "update_frequency": "daily", "records": "", "file": "", "processing": "",
                 "notes": "Bulk station data needs a data request; ERA5 via Open-Meteo and KSNDMC rainfall used instead."})
    fields = list(rows[0].keys())
    with (ROOT / "dataset_manifest.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    (ROOT / "processed" / "processing_report.json").write_text(json.dumps(REPORT, indent=2))


def main() -> None:
    index = process_districts()
    process_facilities(index)
    process_attractions(index)
    process_protected_areas(index)
    process_hazards(index)
    process_roads()
    process_weather()
    process_opencity_tables()
    synthetic_demo_zones()
    write_manifest()
    ok = sum(1 for r in REPORT.values() if r.get("status") == "OK")
    print(f"::notice title=processing::{ok}/{len(REPORT)} outputs OK")
    for k, r in REPORT.items():
        print(k, r.get("status"), r.get("records"))


if __name__ == "__main__":
    main()
