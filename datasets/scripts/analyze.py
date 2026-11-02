"""Dataset analysis: crime trends, facility coverage, weather hazards, district risk.

Outputs datasets/analysis/ (report.md, *.png, *.csv) and
datasets/application_data/analysis_summary.json + district_risk.geojson.
Every number is computed from files under datasets/; nothing is invented.
Explainable composite index only - no trained model (no labelled outcomes).
"""

from __future__ import annotations

import csv
import json
import statistics
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from common import haversine_m, norm_name  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
APP, PROC, OUT = ROOT / "application_data", ROOT / "processed", ROOT / "analysis"
OUT.mkdir(exist_ok=True)

try:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
except Exception:  # charts are optional when running locally
    plt = None

TEAL, RED, BLUE, AMBER, GREY = "#0f766a", "#dc2626", "#1d4ed8", "#d97706", "#64748b"
SUMMARY: dict = {"generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "limitations": []}
REPORT: list[str] = []


def geo(name: str) -> list[dict]:
    p = APP / name
    return json.loads(p.read_text(encoding="utf-8"))["features"] if p.exists() else []


def save_chart(fig, name: str) -> str:
    fig.tight_layout()
    fig.savefig(OUT / name, dpi=140)
    plt.close(fig)
    return name


def style(ax, title: str):
    ax.set_title(title, loc="left", fontsize=11, fontweight="bold")
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(axis="x", alpha=0.2)


# -------------------------------------------------------------- facilities
def facility_coverage(districts: list[dict]) -> dict:
    facilities = geo("emergency_facilities.geojson")
    attractions = geo("tourist_attractions.geojson")
    by_district = defaultdict(Counter)
    for f in facilities:
        by_district[f["properties"].get("district") or "Unassigned"][f["properties"]["facility_type"]] += 1
    area = {d["properties"]["name"]: d["properties"]["approx_area_km2"] for d in districts}
    rows = []
    for name in sorted(area):
        c = by_district.get(name, Counter())
        rows.append({"district": name, "police": c["POLICE"], "hospitals": c["HOSPITAL"] + c["CLINIC"], "fire_stations": c["FIRE_STATION"],
                     "area_km2": area[name], "police_per_1000km2": round(c["POLICE"] / area[name] * 1000, 2) if area[name] else None})
    write_csv("facility_coverage_by_district.csv", rows)

    # nearest police / hospital from each named tourist attraction
    police = [(f["geometry"]["coordinates"][1], f["geometry"]["coordinates"][0]) for f in facilities if f["properties"]["facility_type"] == "POLICE"]
    hosp = [(f["geometry"]["coordinates"][1], f["geometry"]["coordinates"][0]) for f in facilities if f["properties"]["facility_type"] in ("HOSPITAL", "CLINIC")]

    def nearest(lat, lon, pts):
        # 0.5° box pre-filter keeps this fast; widen if nothing is nearby
        for box in (0.25, 0.75, 3.0):
            cand = [p for p in pts if abs(p[0] - lat) < box and abs(p[1] - lon) < box]
            if cand:
                return min(haversine_m(lat, lon, a, b) for a, b in cand)
        return None

    gaps, dp, dh = [], [], []
    for a in attractions:
        lon, lat = a["geometry"]["coordinates"]
        p, h = nearest(lat, lon, police), nearest(lat, lon, hosp)
        if p is not None:
            dp.append(p)
        if h is not None:
            dh.append(h)
        if p is not None and p > 15000:
            gaps.append({"attraction": a["properties"]["name"], "category": a["properties"]["category"],
                         "district": a["properties"].get("district"), "nearest_police_km": round(p / 1000, 1),
                         "nearest_hospital_km": round(h / 1000, 1) if h else None, "latitude": lat, "longitude": lon})
    gaps.sort(key=lambda g: -g["nearest_police_km"])
    write_csv("attractions_far_from_police.csv", gaps)

    def pct(vals, q):
        return round(statistics.quantiles(vals, n=100)[q - 1] / 1000, 2) if len(vals) > 2 else None

    result = {
        "facility_counts": dict(Counter(f["properties"]["facility_type"] for f in facilities)),
        "attractions": len(attractions),
        "attraction_to_police_km": {"median": pct(dp, 50), "p90": pct(dp, 90)},
        "attraction_to_hospital_km": {"median": pct(dh, 50), "p90": pct(dh, 90)},
        "attractions_over_15km_from_police": len(gaps),
        "top_gaps": gaps[:15],
        "by_district": rows,
    }
    if plt and rows:
        top = sorted(rows, key=lambda r: r["police"], reverse=True)
        fig, ax = plt.subplots(figsize=(8, 7))
        names = [r["district"] for r in top][::-1]
        ax.barh(names, [r["police"] for r in top][::-1], color=BLUE, label="Police")
        ax.barh(names, [r["hospitals"] for r in top][::-1], left=[r["police"] for r in top][::-1], color=RED, alpha=0.75, label="Hospitals & clinics")
        style(ax, "Emergency facilities mapped in OpenStreetMap, by district")
        ax.legend(frameon=False, fontsize=8)
        result["chart"] = save_chart(fig, "facilities_by_district.png")
        if dp:
            fig, ax = plt.subplots(figsize=(7, 3.5))
            ax.hist([d / 1000 for d in dp], bins=40, color=TEAL)
            style(ax, "Distance from tourist attractions to the nearest police station (km)")
            result["distance_chart"] = save_chart(fig, "attraction_police_distance.png")
    SUMMARY["limitations"].append("OSM facility coverage is community-mapped and uneven; low counts can mean missing data, not missing facilities.")
    return result


# ----------------------------------------------------------------- weather
def weather_hazards() -> dict:
    path = PROC / "weather_daily_karnataka_2024_2025.csv"
    if not path.exists():
        return {}
    per = defaultdict(lambda: {"heavy_rain_days": 0, "very_heavy_rain_days": 0, "heat_days": 0, "gust_days": 0, "thunder_days": 0, "total_rain_mm": 0.0, "days": 0})
    monthly = defaultdict(float)
    with path.open(encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            d = per[r["district"]]
            d["days"] += 1
            rain = float(r["precipitation_sum"] or 0)
            d["total_rain_mm"] += rain
            # IMD categories: heavy >= 64.5 mm/day, very heavy >= 115.6 mm/day
            d["heavy_rain_days"] += rain >= 64.5
            d["very_heavy_rain_days"] += rain >= 115.6
            d["heat_days"] += float(r["temperature_2m_max"] or 0) >= 40
            d["gust_days"] += float(r["wind_gusts_10m_max"] or 0) >= 60
            d["thunder_days"] += int(float(r["weather_code"] or 0)) in (95, 96, 99)
            monthly[r["date"][:7]] += rain
    rows = [{"district": k, **{kk: (round(v, 1) if isinstance(v, float) else v) for kk, v in d.items()}} for k, d in sorted(per.items())]
    write_csv("weather_hazard_days_by_district.csv", rows)
    n = len(per) or 1
    result = {"districts": len(per), "period": "2024-01-01 to 2025-12-31", "by_district": rows,
              "state_mean_monthly_rain_mm": {m: round(v / n, 1) for m, v in sorted(monthly.items())}}
    if plt and monthly:
        fig, ax = plt.subplots(figsize=(9, 3.5))
        months = sorted(monthly)
        ax.bar(months, [monthly[m] / n for m in months], color=TEAL)
        ax.set_xticks(months[::2])
        ax.tick_params(axis="x", rotation=60, labelsize=7)
        style(ax, "Mean monthly rainfall across Karnataka districts (mm, ERA5 via Open-Meteo)")
        result["chart"] = save_chart(fig, "monthly_rainfall.png")
        top = sorted(rows, key=lambda r: r["heavy_rain_days"], reverse=True)[:15][::-1]
        fig, ax = plt.subplots(figsize=(8, 5))
        ax.barh([r["district"] for r in top], [r["heavy_rain_days"] for r in top], color=AMBER)
        style(ax, "Heavy-rain days (≥64.5 mm) 2024–2025, top districts")
        result["heavy_rain_chart"] = save_chart(fig, "heavy_rain_days.png")
    SUMMARY["limitations"].append("ERA5 reanalysis at one centroid per district smooths local extremes; it is not station data.")
    return result


# ------------------------------------------------------------------- crime
def crime_tables(district_names: list[str]) -> dict:
    """District-wise crime totals from the Karnataka State Police tables (filled in by analyse_crime)."""
    from crime import analyse_crime  # local module, written after inspecting the real CSV layout

    return analyse_crime(PROC / "crime_and_rainfall", district_names, OUT, plt, SUMMARY)


# ------------------------------------------------------------- composite
def district_risk(districts: list[dict], cover: dict, weather: dict, crime: dict) -> list[dict]:
    """Explainable 0-100 index. Components are percentile-ranked across districts."""
    w = {r["district"]: r for r in weather.get("by_district", [])}
    c = {r["district"]: r for r in cover.get("by_district", [])}
    k = crime.get("by_polygon", {})

    def scale(values: dict) -> dict:
        """Percentile rank in [0, 1] (ties share a rank): robust to the Bengaluru outlier."""
        vals = sorted(v for v in values.values() if v is not None)
        if len(vals) < 2:
            return {}
        n = len(vals) - 1

        def rank(v):
            below = sum(1 for x in vals if x < v)
            equal = sum(1 for x in vals if x == v)
            return (below + (equal - 1) / 2) / n

        return {key: (None if v is None else rank(v)) for key, v in values.items()}

    names = [d["properties"]["name"] for d in districts]
    crime_s = scale({n: (k.get(n) or {}).get("total") for n in names})
    rain_s = scale({n: (w.get(n) or {}).get("heavy_rain_days") for n in names})
    heat_s = scale({n: (w.get(n) or {}).get("heat_days") for n in names})
    # Police density from OSM is NOT used as a risk input: OSM police mapping is
    # very incomplete in several districts, so it measures mapping gaps, not safety.
    weights = {"crime": 0.55, "heavy_rain": 0.3, "heat": 0.15}
    feats, rows = [], []
    for d in districts:
        n = d["properties"]["name"]
        parts = {"crime": crime_s.get(n), "heavy_rain": rain_s.get(n), "heat": heat_s.get(n)}
        used = {key: v for key, v in parts.items() if v is not None}
        total_w = sum(weights[key] for key in used) or 1
        score = round(100 * sum(weights[key] * v for key, v in used.items()) / total_w, 1) if used else None
        # percentile-based index -> tertiles
        level = None if score is None else "HIGH" if score >= 66.7 else "MEDIUM" if score >= 33.3 else "LOW"
        props = {"name": n, "risk_index": score, "risk_level": level,
                 "components": {key: (round(v, 3) if v is not None else None) for key, v in parts.items()}, "weights": weights,
                 "crime_total": (k.get(n) or {}).get("total"), "heavy_rain_days": (w.get(n) or {}).get("heavy_rain_days"),
                 "police_stations": (c.get(n) or {}).get("police"), "kind": "EXPLAINABLE_INDEX"}
        feats.append({"type": "Feature", "geometry": d["geometry"], "properties": props})
        rows.append({key: v for key, v in props.items() if key not in ("components", "weights")})
    (APP / "district_risk.geojson").write_text(json.dumps({"type": "FeatureCollection", "features": feats}, separators=(",", ":")), encoding="utf-8")
    write_csv("district_risk_index.csv", sorted(rows, key=lambda r: -(r["risk_index"] or 0)))
    SUMMARY["limitations"].append("District risk index uses raw crime counts (no population denominator available in the downloaded data), so populous districts rank higher.")
    return sorted(rows, key=lambda r: -(r["risk_index"] or 0))


def write_csv(name: str, rows: list[dict]) -> None:
    if not rows:
        return
    with (OUT / name).open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)


def main() -> None:
    districts = geo("karnataka_districts.geojson")
    names = [d["properties"]["name"] for d in districts]
    cover = facility_coverage(districts) if districts else {}
    weather = weather_hazards()
    try:
        crime = crime_tables(names)
    except ImportError:
        crime = {}
    try:
        from crime import analyse_ksndmc

        ksndmc = analyse_ksndmc(ROOT / "raw" / "opencity", names, OUT, plt)
    except ImportError:
        ksndmc = {}
    risk = district_risk(districts, cover, weather, crime) if districts else []
    SUMMARY.update({"facilities": cover, "weather": weather, "ksndmc_rainfall": {k: v for k, v in ksndmc.items() if k != "by_district"}, "crime": {k: v for k, v in crime.items() if k != "by_polygon"},
                    "district_risk": risk, "districts": len(districts),
                    "ml_evaluation": "Not trained: no labelled incident outcomes or incident coordinates are available; "
                                     "district crime data is aggregated counts. Rule-based, explainable scoring is used instead."})
    SUMMARY["limitations"].append("No geocoded crime incidents exist in the open data, so incident hotspot maps cannot be produced from it; "
                                  "hotspots are computed only from SafeTrail's own SOS records in the app.")
    (APP / "analysis_summary.json").write_text(json.dumps(SUMMARY, indent=2, default=str), encoding="utf-8")
    write_report(cover, weather, crime, risk, ksndmc)
    print("::notice title=analysis::", json.dumps({"districts": len(districts), "facilities": cover.get("facility_counts"),
                                                    "risk_rows": len(risk), "crime_years": crime.get("years")}))


def write_report(cover: dict, weather: dict, crime: dict, risk: list[dict], ksndmc: dict | None = None) -> None:
    L = REPORT
    L += ["# SafeTrail dataset analysis", "", f"Generated {SUMMARY['generated_at']} by `datasets/scripts/analyze.py` from the files in `datasets/`.", ""]
    if crime:
        L += ["## 1. District-wise crime (Karnataka State Police)", "", crime.get("narrative", ""), ""]
        for ch in crime.get("charts", []):
            L.append(f"![{ch}]({ch})")
        L.append("")
    if cover:
        L += ["## 2. Emergency facility coverage (OpenStreetMap)", "",
              f"Facilities mapped: {cover['facility_counts']}. Named tourist attractions: {cover['attractions']}.",
              f"Median distance from an attraction to the nearest police station: **{cover['attraction_to_police_km']['median']} km** "
              f"(90th percentile {cover['attraction_to_police_km']['p90']} km); to a hospital/clinic: **{cover['attraction_to_hospital_km']['median']} km**.",
              f"{cover['attractions_over_15km_from_police']} attractions are more than 15 km from any mapped police station "
              "(see `attractions_far_from_police.csv`).", ""]
        for key in ("chart", "distance_chart"):
            if cover.get(key):
                L.append(f"![{cover[key]}]({cover[key]})")
        L.append("")
    if weather:
        L += ["## 3. Weather hazards (Open-Meteo / ERA5, 2024–2025)", "",
              "Heavy rain uses the IMD threshold of 64.5 mm/day; heat ≥ 40 °C; gusts ≥ 60 km/h. Per-district counts in "
              "`weather_hazard_days_by_district.csv`.", ""]
        for key in ("chart", "heavy_rain_chart"):
            if weather.get(key):
                L.append(f"![{weather[key]}]({weather[key]})")
        L.append("")
    if ksndmc:
        L += ["### Official rainfall (KSNDMC)", "",
              f"Mean annual district rainfall by year (mm): {ksndmc['state_mean_annual_mm']}. Districts ≥20 % above normal in "
              f"{ksndmc['latest_year']}: " + (", ".join(f"{d['district']} ({d['departure_pct']:+.0f}%)" for d in ksndmc['excess_districts_latest']) or "none") + ".", ""]
        if ksndmc.get("chart"):
            L.append(f"![{ksndmc['chart']}]({ksndmc['chart']})")
        L.append("")
    if risk:
        L += ["## 4. Explainable district risk index", "",
              "Weighted mean of percentile-ranked components: registered crimes 55 %, heavy-rain days 30 %, heat days 15 %. "
              "OSM police density is reported separately as a mapping-coverage gap and is not a risk input. "
              "Missing components are dropped and weights renormalised.", "", "| District | Index | Level | Crime total | Heavy-rain days | Police stations |",
              "|---|---|---|---|---|---|"]
        for r in risk[:15]:
            L.append(f"| {r['name']} | {r['risk_index']} | {r['risk_level']} | {r['crime_total']} | {r['heavy_rain_days']} | {r['police_stations']} |")
        L.append("")
    L += ["## 5. Machine learning", "", SUMMARY["ml_evaluation"], "", "## 6. Limitations", ""]
    L += [f"- {x}" for x in SUMMARY["limitations"]]
    (OUT / "report.md").write_text("\n".join(L) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
