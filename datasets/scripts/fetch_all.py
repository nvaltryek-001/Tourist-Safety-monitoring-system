"""Download open datasets for SafeTrail into datasets/raw/.

Runs in GitHub Actions (datasets.yml) or locally:  python datasets/scripts/fetch_all.py
Standard library only. Every attempt - success or failure - is written to
datasets/raw/fetch_log.json and later merged into dataset_manifest.csv, so a
failed download is never reported as a success.
"""

from __future__ import annotations

import gzip
import json
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "raw"
UA = "SafeTrail-academic-project/2.0 (github.com/nvaltryek-001/Tourist-Safety-monitoring-system)"
LOG: list[dict] = []

OVERPASS = ["https://overpass-api.de/api/interpreter", "https://overpass.kumi.systems/api/interpreter"]
KA = 'area["ISO3166-2"="IN-KA"][admin_level=4]->.ka;'
# SVIT / Rajanukunte study area used for the local road network (about 12 km box)
STUDY_BBOX = (13.06, 77.45, 13.27, 77.67)  # south, west, north, east

OVERPASS_QUERIES = {
    "osm_police": f'[out:json][timeout:300];{KA}nwr["amenity"="police"](area.ka);out center tags;',
    "osm_hospitals": f'[out:json][timeout:300];{KA}nwr["amenity"~"^(hospital|clinic)$"](area.ka);out center tags;',
    "osm_fire_stations": f'[out:json][timeout:300];{KA}nwr["amenity"="fire_station"](area.ka);out center tags;',
    "osm_pharmacies": f'[out:json][timeout:300];{KA}nwr["amenity"="pharmacy"](area.ka);out center tags;',
    "osm_tourism": (
        f'[out:json][timeout:300];{KA}'
        'nwr["tourism"~"^(attraction|viewpoint|museum|zoo|theme_park|picnic_site|camp_site)$"](area.ka);'
        'nwr["historic"~"^(fort|monument|castle|ruins)$"](area.ka);out center tags;'
    ),
    # Split into small queries: one combined query timed out (HTTP 504) on the public servers.
    "osm_protected_areas_rel_pa": f'[out:json][timeout:900];{KA}relation["boundary"="protected_area"](area.ka);out geom;',
    "osm_protected_areas_rel_nr": f'[out:json][timeout:900];{KA}relation["leisure"="nature_reserve"](area.ka);out geom;',
    "osm_protected_areas_ways": f'[out:json][timeout:900];{KA}(way["boundary"="protected_area"](area.ka);way["leisure"="nature_reserve"](area.ka););out geom;',
    "osm_water_hazards": (
        f'[out:json][timeout:300];{KA}'
        '(way["waterway"="waterfall"](area.ka);node["waterway"="waterfall"](area.ka);'
        'node["natural"="cliff"](area.ka);way["natural"="cliff"](area.ka););out center tags;'
    ),
    "osm_study_roads": (
        '[out:json][timeout:300];'
        f'way["highway"~"^(motorway|trunk|primary|secondary|tertiary|residential|footway|path)$"]{STUDY_BBOX};out geom tags;'
    ),
}

OPENCITY_DATASETS = {
    "ksp_crime_2022": "karnataka-crime-data-2022",
    "ksp_crime_2024": "karnataka-crime-data-2024",
    "ksp_crime_2025": "karnataka-crime-data-2025",
    "ksndmc_rainfall": "karnataka-annual-rainfall-districts-taluks-and-hoblis",
}


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def http(url: str, data: bytes | None = None, timeout: int = 900, tries: int = 3) -> bytes:
    last = None
    for attempt in range(1, tries + 1):
        try:
            req = urllib.request.Request(url, data=data, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.read()
        except Exception as exc:  # network errors are logged, never hidden
            last = exc
            time.sleep(10 * attempt)
    raise RuntimeError(f"{type(last).__name__}: {last}")


def save(path: Path, content: bytes, compress: bool = False) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    if compress:
        path = path.with_suffix(path.suffix + ".gz")
        path.write_bytes(gzip.compress(content, 9))
    else:
        path.write_bytes(content)
    return path


def record(source_id: str, url: str, status: str, **extra) -> None:
    entry = {"source_id": source_id, "url": url, "status": status, "downloaded_at": now(), **extra}
    LOG.append(entry)
    print(json.dumps(entry), flush=True)


# ---------------------------------------------------------------- sources
def fetch_overpass(only_prefix: str | None = None) -> None:
    for name, query in OVERPASS_QUERIES.items():
        if only_prefix and not name.startswith(only_prefix):
            continue
        body = urllib.parse.urlencode({"data": query}).encode()
        for endpoint in OVERPASS:
            try:
                raw = http(endpoint, body, tries=2)
                data = json.loads(raw)
                count = len(data.get("elements", []))
                path = save(RAW / "osm" / f"{name}.json", raw, compress=len(raw) > 2_000_000)
                record(name, endpoint, "DOWNLOADED", records=count, bytes=len(raw), file=str(path.relative_to(ROOT)),
                       licence="ODbL 1.0", attribution="© OpenStreetMap contributors", query=query)
                break
            except Exception as exc:
                record(name, endpoint, "FAILED", error=str(exc)[:300])
            time.sleep(5)
        time.sleep(15)  # be polite to the public Overpass servers


def fetch_geoboundaries() -> None:
    for level in ("ADM1", "ADM2"):
        meta_url = f"https://www.geoboundaries.org/api/current/gbOpen/IND/{level}/"
        try:
            meta = json.loads(http(meta_url))
            save(RAW / "geoboundaries" / f"IND_{level}_metadata.json", json.dumps(meta, indent=2).encode())
            url = meta.get("simplifiedGeometryGeoJSON") or meta["gjDownloadURL"]
            raw = http(url)
            count = len(json.loads(raw).get("features", []))
            path = save(RAW / "geoboundaries" / f"IND_{level}.geojson", raw, compress=len(raw) > 2_000_000)
            record(f"geoboundaries_IND_{level}", url, "DOWNLOADED", records=count, bytes=len(raw),
                   file=str(path.relative_to(ROOT)), licence=meta.get("boundaryLicense"),
                   attribution=meta.get("boundarySource"), year=meta.get("boundaryYearRepresented"))
        except Exception as exc:
            record(f"geoboundaries_IND_{level}", meta_url, "FAILED", error=str(exc)[:300])


def fetch_opencity() -> None:
    for source_id, package in OPENCITY_DATASETS.items():
        api = f"https://data.opencity.in/api/3/action/package_show?id={package}"
        try:
            pkg = json.loads(http(api))["result"]
            save(RAW / "opencity" / source_id / "package.json", json.dumps(pkg, indent=2).encode())
        except Exception as exc:
            record(source_id, api, "FAILED", error=str(exc)[:300])
            continue
        for res in pkg.get("resources", []):
            fmt = (res.get("format") or "").upper()
            url = res.get("url") or ""
            if fmt != "CSV" or not url:
                continue
            name = (res.get("name") or res["id"]).strip()
            safe = "".join(c if c.isalnum() else "_" for c in name.lower()).strip("_")[:80]
            try:
                raw = http(url)
                path = save(RAW / "opencity" / source_id / f"{safe}.csv", raw)
                record(f"{source_id}:{safe}", url, "DOWNLOADED", bytes=len(raw), file=str(path.relative_to(ROOT)),
                       title=name, licence=pkg.get("license_title"), publisher=(pkg.get("organization") or {}).get("title"),
                       original_source=next((e["value"] for e in pkg.get("extras", []) if e.get("key", "").lower() == "source"), None))
            except Exception as exc:
                record(f"{source_id}:{safe}", url, "FAILED", error=str(exc)[:300])


def district_points() -> list[tuple[str, float, float]]:
    """Centroids of Karnataka districts from the downloaded geoBoundaries ADM2 file."""
    sys.path.insert(0, str(Path(__file__).parent))
    from common import load_karnataka_districts  # noqa: E402

    return [(d["name"], d["lat"], d["lon"]) for d in load_karnataka_districts(RAW)]


def fetch_open_meteo() -> None:
    try:
        points = district_points()
    except Exception as exc:
        record("open_meteo_daily", "", "FAILED", error=f"no district centroids: {exc}"[:300])
        return
    daily = "temperature_2m_max,temperature_2m_min,precipitation_sum,rain_sum,wind_speed_10m_max,wind_gusts_10m_max,weather_code"
    rows = []
    for i in range(0, len(points), 10):
        chunk = points[i:i + 10]
        params = {
            "latitude": ",".join(f"{p[1]:.4f}" for p in chunk),
            "longitude": ",".join(f"{p[2]:.4f}" for p in chunk),
            "start_date": "2024-01-01", "end_date": "2025-12-31",
            "daily": daily, "timezone": "Asia/Kolkata",
        }
        url = "https://archive-api.open-meteo.com/v1/archive?" + urllib.parse.urlencode(params)
        try:
            data = json.loads(http(url))
            data = data if isinstance(data, list) else [data]
            for (name, lat, lon), loc in zip(chunk, data):
                rows.append({"district": name, "lat": lat, "lon": lon, "daily": loc["daily"]})
        except Exception as exc:
            record("open_meteo_daily", url, "FAILED", error=str(exc)[:300])
            return
        time.sleep(3)
    raw = json.dumps(rows).encode()
    path = save(RAW / "open_meteo" / "karnataka_districts_daily_2024_2025.json", raw, compress=True)
    record("open_meteo_daily", "https://archive-api.open-meteo.com/v1/archive", "DOWNLOADED",
           records=sum(len(r["daily"]["time"]) for r in rows), locations=len(rows), bytes=len(raw),
           file=str(path.relative_to(ROOT)), licence="CC BY 4.0", attribution="Weather data by Open-Meteo.com (ERA5 reanalysis)")


def main() -> None:
    only = set(sys.argv[1:])
    steps = [("osm", fetch_overpass), ("protected", lambda: fetch_overpass("osm_protected_areas")),
             ("geoboundaries", fetch_geoboundaries), ("opencity", fetch_opencity), ("weather", fetch_open_meteo)]
    for key, func in steps:
        if (not only and key != "protected") or key in only:
            func()
    log_path = RAW / "fetch_log.json"
    previous = json.loads(log_path.read_text()) if log_path.exists() else []
    # keep the newest entry per source_id
    merged = {e["source_id"]: e for e in previous + LOG}
    if any(e["source_id"].startswith("osm_protected_areas_") and e["status"] == "DOWNLOADED" for e in merged.values()):
        merged.pop("osm_protected_areas", None)  # superseded by the split queries
    log_path.write_text(json.dumps(sorted(merged.values(), key=lambda e: e["source_id"]), indent=2))
    ok = sum(1 for e in merged.values() if e["status"] == "DOWNLOADED")
    print(f"::notice title=datasets::{ok} downloaded, {len(merged) - ok} failed")


if __name__ == "__main__":
    main()
