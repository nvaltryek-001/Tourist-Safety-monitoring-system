"""Karnataka State Police district tables (2022, 2024, 2025) and KSNDMC rainfall.

Police "units" (commissionerates, police districts, K.G.F., Railways) are
mapped explicitly onto the 30 geoBoundaries district polygons (2021 edition).
The mapping is written out in full so it can be audited; unmapped units are
reported rather than guessed.
"""

from __future__ import annotations

import csv
import re
from collections import defaultdict
from pathlib import Path

# police unit (normalised) -> geoBoundaries district polygon name
UNIT_TO_DISTRICT = {
    "bengaluru": "Bangalore", "bengalurucity": "Bangalore",
    "bengaluru dist": "Bangalore Rural", "bengaluru district": "Bangalore Rural", "bengalurudist": "Bangalore Rural",
    "bengalurudistrict": "Bangalore Rural",
    "bengalurusouth": "Ramanagara", "ramanagara": "Ramanagara",
    "mysuru": "Mysore", "mysurucity": "Mysore", "mysurudist": "Mysore", "mysurudistrict": "Mysore",
    "hubballidharwad": "Dharwad", "hubballidharwadcity": "Dharwad", "dharwad": "Dharwad",
    "mangaluru": "Dakshina Kannada", "mangalurucity": "Dakshina Kannada", "dakshinakannada": "Dakshina Kannada",
    "belagavi": "Belgaum", "belagavicity": "Belgaum", "belagavidist": "Belgaum", "belagavidistrict": "Belgaum",
    "kalaburagi": "Gulbarga", "kalaburagicity": "Gulbarga", "kalaburgi": "Gulbarga", "kalaburgicity": "Gulbarga",
    "kgf": "Kolar", "kolar": "Kolar",
    "chickballapura": "Chikkaballapura", "chikkaballapura": "Chikkaballapura",
    "tumakuru": "Tumkur", "chitradurga": "Chitradurga", "davanagere": "Davanagere",
    "shivamogga": "Shimoga", "shimoga": "Shimoga", "haveri": "Haveri", "udupi": "Udupi",
    "chikkamagaluru": "Chikmagalur", "uttarakannada": "Uttara Kannada", "bagalkot": "Bagalkot", "bagalkote": "Bagalkot",
    "vijayapura": "Bijapur", "vijayapur": "Bijapur", "gadag": "Gadag", "bidar": "Bidar",
    "yadgir": "Yadgir", "yadgiri": "Yadgir", "mandya": "Mandya",
    "chamarajanagar": "Chamarajanagar", "chamarajnagar": "Chamarajanagar", "chamarajanagara": "Chamarajanagar",
    "hassan": "Hassan", "kodagu": "Kodagu", "ballari": "Bellary", "koppal": "Koppal", "koppala": "Koppal",
    "raichur": "Raichur",
    # Vijayanagara was carved out of Ballari in 2021; the 2021 boundary file has no separate polygon.
    "vijayanagara": "Bellary",
    # KSNDMC spelling
    "bengalururural": "Bangalore Rural", "bengaluruurban": "Bangalore",
}
EXCLUDED_UNITS = {"krailways", "karnatakarailways", "railways", "total", "totaldistricts", "totalcities", "state", "commissionerates",
                  "cid", "coastalsecuritypolice"}  # statewide / specialised units with no single district


def unit_key(name: str) -> str:
    v = (name or "").lower().replace(".", "")
    v = re.sub(r"[^a-z ]", " ", v)
    v = re.sub(r"\s+", " ", v).strip()
    compact = v.replace(" ", "")
    return compact


def map_unit(name: str) -> str | None:
    k = unit_key(name)
    if k in UNIT_TO_DISTRICT:
        return UNIT_TO_DISTRICT[k]
    return None


def is_excluded(name: str) -> bool:
    k = unit_key(name)
    return not k or k in EXCLUDED_UNITS or k.endswith("range")


def num(v) -> float | None:
    try:
        return float(str(v).replace(",", "").strip())
    except (TypeError, ValueError):
        return None


def read(path: Path) -> list[dict]:
    with path.open(encoding="utf-8-sig") as fh:
        return list(csv.DictReader(fh))


def find(base: Path, folder: str, pattern: str) -> Path | None:
    hits = sorted((base / folder).glob(f"*{pattern}*.csv")) if (base / folder).exists() else []
    return hits[0] if hits else None


def aggregate(rows: list[dict], unit_col: str, value_cols: list[str], unmapped: set) -> dict[str, dict]:
    out: dict[str, dict] = defaultdict(lambda: defaultdict(float))
    for r in rows:
        unit = r.get(unit_col, "")
        if is_excluded(unit):
            continue
        district = map_unit(unit)
        if district is None:
            unmapped.add(unit)
            continue
        for c in value_cols:
            v = num(r.get(c))
            if v is not None:
                out[district][c] += v
        out[district]["_units"] = out[district].get("_units", 0) + 1
    return {k: dict(v) for k, v in out.items()}


def analyse_crime(proc_dir: Path, district_names: list[str], out_dir: Path, plt, summary: dict) -> dict:
    """proc_dir = datasets/processed/crime_and_rainfall; raw files are re-read with original headers."""
    raw = proc_dir.parents[1] / "raw" / "opencity"
    unmapped: set[str] = set()
    result: dict = {"years": [], "charts": [], "unmapped_units": []}

    p22 = find(raw, "ksp_crime_2022", "total_crimes_registered")
    p24 = find(raw, "ksp_crime_2024", "district_wise_ipc")
    p25 = find(raw, "ksp_crime_2025", "district_and_commissionerate")
    p22acc = find(raw, "ksp_crime_2022", "road_accidents")

    y22 = aggregate(read(p22), "Districts", ["IPC Cases", "SLL Cases", "Total"], unmapped) if p22 else {}
    y25 = aggregate(read(p25), "Districts/Units", ["IPC/BNS Crimes", "SLL Crimes"], unmapped) if p25 else {}
    heads24 = ["THEFT", "ROBBERY", "MOLESTATION", "CYBER CRIME", "FATAL MOTOR ACCIDENTS", "MURDER", "RAPE", "CASES OF HURT"]
    y24 = aggregate(read(p24), "DISTRICT/UNITS", heads24, unmapped) if p24 else {}
    acc22 = aggregate(read(p22acc), "Districts", ["Total Road Accidents - Incidence", "Total Road Accidents - Victims"], unmapped) if p22acc else {}

    rows, by_polygon = [], {}
    for name in district_names:
        a, b, h, acc = y22.get(name, {}), y25.get(name, {}), y24.get(name, {}), acc22.get(name, {})
        total22 = a.get("Total")
        total25 = (b.get("IPC/BNS Crimes", 0) + b.get("SLL Crimes", 0)) if b else None
        change = round((total25 - total22) / total22 * 100, 1) if total22 and total25 is not None else None
        row = {"district": name, "total_2022": total22 and int(total22), "ipc_2022": a.get("IPC Cases") and int(a["IPC Cases"]),
               "total_2025": total25 and int(total25), "ipc_bns_2025": b.get("IPC/BNS Crimes") and int(b["IPC/BNS Crimes"]),
               "change_2022_2025_pct": change, "police_units_2025": int(b.get("_units", 0)) if b else 0,
               **{f"{k.lower().replace(' ', '_')}_2024": int(h[k]) for k in heads24 if k in h},
               "road_accidents_2022": acc.get("Total Road Accidents - Incidence") and int(acc["Total Road Accidents - Incidence"])}
        rows.append(row)
        by_polygon[name] = {"total": total25 if total25 is not None else total22}
    result["years"] = [y for y, d in ((2022, y22), (2024, y24), (2025, y25)) if d]
    result["unmapped_units"] = sorted(unmapped)
    result["by_polygon"] = by_polygon
    result["by_district"] = rows
    result["state_totals"] = {
        "total_2022": int(sum(r["total_2022"] or 0 for r in rows)),
        "total_2025": int(sum(r["total_2025"] or 0 for r in rows)),
        "theft_2024": int(sum(r.get("theft_2024", 0) for r in rows)),
        "cyber_crime_2024": int(sum(r.get("cyber_crime_2024", 0) for r in rows)),
    }
    top = sorted((r for r in rows if r["total_2025"]), key=lambda r: -r["total_2025"])
    result["top_districts"] = [{"district": r["district"], "total": r["total_2025"], "year": 2025} for r in top]
    with (out_dir / "crime_by_district.csv").open("w", newline="", encoding="utf-8") as fh:
        keys = sorted({k for r in rows for k in r}, key=lambda k: (k != "district", k))
        w = csv.DictWriter(fh, fieldnames=keys)
        w.writeheader()
        w.writerows(rows)

    st = result["state_totals"]
    change = round((st["total_2025"] - st["total_2022"]) / st["total_2022"] * 100, 1) if st["total_2022"] else None
    big = top[0] if top else None
    result["narrative"] = (
        f"Registered crimes (IPC/BNS + SLL) across the mapped districts: {st['total_2022']:,} in 2022 and {st['total_2025']:,} in 2025"
        f"{f' ({change:+}%)' if change is not None else ''}. "
        + (f"{big['district']} (incl. Bengaluru City commissionerate) records the most: {big['total_2025']:,} in 2025. " if big else "")
        + f"2024 head-wise data: {st['theft_2024']:,} thefts and {st['cyber_crime_2024']:,} cyber crimes. "
        "Counts are not population-adjusted; IPC was replaced by BNS from July 2024, so 2025 figures combine both codes."
    )
    if plt and top:
        fig, ax = plt.subplots(figsize=(8, 7))
        names = [r["district"] for r in top][::-1]
        ax.barh(names, [r["total_2022"] or 0 for r in top][::-1], color="#94a3b8", label="2022")
        ax.barh(names, [r["total_2025"] or 0 for r in top][::-1], color="#dc2626", alpha=0.75, label="2025", height=0.45)
        ax.set_title("Registered crimes by district (KSP): 2022 vs 2025", loc="left", fontsize=11, fontweight="bold")
        ax.spines[["top", "right"]].set_visible(False)
        ax.legend(frameon=False)
        fig.tight_layout()
        fig.savefig(out_dir / "crime_by_district.png", dpi=140)
        plt.close(fig)
        result["charts"].append("crime_by_district.png")

        tourist_heads = ["theft_2024", "robbery_2024", "molestation_2024", "cyber_crime_2024"]
        top10 = sorted(rows, key=lambda r: -sum(r.get(k, 0) for k in tourist_heads))[:10][::-1]
        fig, ax = plt.subplots(figsize=(8, 5))
        left = [0] * len(top10)
        for k, color in zip(tourist_heads, ["#dc2626", "#ea580c", "#7c3aed", "#1d4ed8"]):
            vals = [r.get(k, 0) for r in top10]
            ax.barh([r["district"] for r in top10], vals, left=left, color=color, label=k.replace("_2024", "").replace("_", " "))
            left = [a + b for a, b in zip(left, vals)]
        ax.set_title("Tourist-relevant crime heads, 2024 (top 10 districts)", loc="left", fontsize=11, fontweight="bold")
        ax.spines[["top", "right"]].set_visible(False)
        ax.legend(frameon=False, fontsize=8)
        fig.tight_layout()
        fig.savefig(out_dir / "tourist_relevant_crime_2024.png", dpi=140)
        plt.close(fig)
        result["charts"].append("tourist_relevant_crime_2024.png")
    summary["limitations"].append(
        "Police units are mapped to 2021 district polygons; Vijayanagara is merged into Ballari and Bengaluru South into Ramanagara; Railways is excluded."
    )
    return result


def analyse_ksndmc(raw_dir: Path, district_names: list[str], out_dir: Path, plt) -> dict:
    """Annual district rainfall (KSNDMC, official station network) - actual vs normal."""
    files = {y: sorted((raw_dir / "ksndmc_rainfall").glob(f"*{y}_for_districts.csv")) for y in (2020, 2021, 2022, 2023, 2024)}
    files[2025] = sorted((raw_dir / "ksndmc_rainfall").glob("district_level_rainfall_in_2025.csv"))
    rows = []
    for year, hits in sorted(files.items()):
        if not hits:
            continue
        data = read(hits[0])
        if not data:
            continue
        cols = list(data[0].keys())
        low = [c.lower() for c in cols]

        def pick(*needles, avoid=("pre", "swm", "nem", "south", "north", "monsoon")):
            for c, lc in zip(cols, low):
                if all(n in lc for n in needles) and not any(a in lc for a in avoid):
                    return c
            return None

        actual = pick("annual", "actual") or pick("total", "actual") or pick("actual")
        normal = pick("annual", "normal") or pick("total", "normal") or pick("normal")
        # departure column: the one right after "actual" when headers repeat %DEP
        dep = pick("annual", "dep") or pick("total", "dep") or pick("departure")
        if dep is None and actual in cols and cols.index(actual) + 1 < len(cols):
            dep = cols[cols.index(actual) + 1]
        name_col = next((c for c in cols if "district" in c.lower()), None)
        if not actual or not name_col:
            continue
        for r in data:
            name = map_unit(r.get(name_col, ""))
            if name:
                rows.append({"year": year, "district": name, "actual_mm": num(r.get(actual)),
                             "normal_mm": num(r.get(normal)) if normal else None, "departure_pct": num(r.get(dep)) if dep else None})
    if not rows:
        return {}
    with (out_dir / "ksndmc_rainfall_by_district.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    latest = max(r["year"] for r in rows)
    excess = sorted((r for r in rows if r["year"] == latest and (r["departure_pct"] or 0) >= 20), key=lambda r: -(r["departure_pct"] or 0))
    state = defaultdict(list)
    for r in rows:
        if r["actual_mm"] is not None:
            state[r["year"]].append(r["actual_mm"])
    result = {"years": sorted(state), "latest_year": latest,
              "state_mean_annual_mm": {y: round(sum(v) / len(v), 1) for y, v in sorted(state.items())},
              "excess_districts_latest": [{"district": r["district"], "departure_pct": r["departure_pct"]} for r in excess],
              "by_district": rows}
    if plt:
        fig, ax = plt.subplots(figsize=(7, 3.2))
        ys = sorted(state)
        ax.plot(ys, [result["state_mean_annual_mm"][y] for y in ys], marker="o", color="#0f766a")
        ax.set_xticks(ys)
        ax.set_title("Mean annual district rainfall, Karnataka (KSNDMC, mm)", loc="left", fontsize=11, fontweight="bold")
        ax.spines[["top", "right"]].set_visible(False)
        fig.tight_layout()
        fig.savefig(out_dir / "ksndmc_annual_rainfall.png", dpi=140)
        plt.close(fig)
        result["chart"] = "ksndmc_annual_rainfall.png"
    return result
