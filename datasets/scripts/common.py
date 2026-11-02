"""Shared helpers for dataset scripts (standard library only)."""

from __future__ import annotations

import gzip
import json
import math
import re
from pathlib import Path


def read_maybe_gz(path: Path) -> bytes:
    gz = path.with_suffix(path.suffix + ".gz")
    if path.exists():
        return path.read_bytes()
    if gz.exists():
        return gzip.decompress(gz.read_bytes())
    raise FileNotFoundError(path)


def load_json(path: Path):
    return json.loads(read_maybe_gz(path))


# --------------------------------------------------------------- geometry
def ring_area_centroid(ring: list) -> tuple[float, float, float]:
    """Signed area (deg^2) and centroid of a lon/lat ring (shoelace)."""
    a = cx = cy = 0.0
    for (x1, y1), (x2, y2) in zip(ring, ring[1:] + ring[:1]):
        cross = x1 * y2 - x2 * y1
        a += cross
        cx += (x1 + x2) * cross
        cy += (y1 + y2) * cross
    a /= 2
    if abs(a) < 1e-15:
        xs, ys = [p[0] for p in ring], [p[1] for p in ring]
        return 0.0, sum(xs) / len(xs), sum(ys) / len(ys)
    return a, cx / (6 * a), cy / (6 * a)


def outer_rings(geometry: dict) -> list:
    if geometry["type"] == "Polygon":
        return [geometry["coordinates"][0]]
    if geometry["type"] == "MultiPolygon":
        return [p[0] for p in geometry["coordinates"]]
    return []


def centroid(geometry: dict) -> tuple[float, float]:
    best = None
    for ring in outer_rings(geometry):
        a, x, y = ring_area_centroid([tuple(p[:2]) for p in ring])
        if best is None or abs(a) > abs(best[0]):
            best = (a, x, y)
    return best[2], best[1]  # lat, lon


def point_in_ring(lon: float, lat: float, ring: list) -> bool:
    inside, j = False, len(ring) - 1
    for i in range(len(ring)):
        xi, yi = ring[i][0], ring[i][1]
        xj, yj = ring[j][0], ring[j][1]
        if (yi > lat) != (yj > lat) and lon < (xj - xi) * (lat - yi) / ((yj - yi) or 1e-15) + xi:
            inside = not inside
        j = i
    return inside


def point_in_geometry(lat: float, lon: float, geometry: dict) -> bool:
    polys = [geometry["coordinates"]] if geometry["type"] == "Polygon" else geometry.get("coordinates", [])
    for rings in polys:
        if rings and point_in_ring(lon, lat, rings[0]) and not any(point_in_ring(lon, lat, h) for h in rings[1:]):
            return True
    return False


def haversine_m(lat1, lon1, lat2, lon2) -> float:
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dlat, dlon = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlon / 2) ** 2
    return 6371000 * 2 * math.asin(math.sqrt(min(1.0, a)))


def simplify(points: list, tolerance: float) -> list:
    """Douglas-Peucker on lon/lat (tolerance in degrees)."""
    if len(points) < 3:
        return points

    def perp(p, a, b):
        if a == b:
            return math.dist(p, a)
        (x, y), (x1, y1), (x2, y2) = p, a, b
        return abs((y2 - y1) * x - (x2 - x1) * y + x2 * y1 - y2 * x1) / math.dist(a, b)

    stack, keep = [(0, len(points) - 1)], {0, len(points) - 1}
    while stack:
        s, e = stack.pop()
        dmax, idx = 0.0, None
        for i in range(s + 1, e):
            d = perp(points[i], points[s], points[e])
            if d > dmax:
                dmax, idx = d, i
        if idx is not None and dmax > tolerance:
            keep.add(idx)
            stack += [(s, idx), (idx, e)]
    return [points[i] for i in sorted(keep)]


def bbox_of(geometry: dict) -> tuple[float, float, float, float]:
    xs, ys = [], []
    for ring in outer_rings(geometry):
        xs += [p[0] for p in ring]
        ys += [p[1] for p in ring]
    return min(xs), min(ys), max(xs), max(ys)


# -------------------------------------------------------------- districts
def norm_name(value: str) -> str:
    value = (value or "").lower()
    value = re.sub(r"\b(district|dist|city|urban|rural|police|commissionerate|ps)\b", " ", value)
    return re.sub(r"[^a-z]", "", value)


def load_karnataka_districts(raw: Path) -> list[dict]:
    """Karnataka ADM2 polygons from geoBoundaries (district centroid inside the Karnataka ADM1 shape)."""
    adm1 = load_json(raw / "geoboundaries" / "IND_ADM1.geojson")
    karnataka = next(f for f in adm1["features"] if "karnataka" in json.dumps(f["properties"]).lower())
    adm2 = load_json(raw / "geoboundaries" / "IND_ADM2.geojson")
    out = []
    for f in adm2["features"]:
        lat, lon = centroid(f["geometry"])
        if point_in_geometry(lat, lon, karnataka["geometry"]):
            name = f["properties"].get("shapeName") or f["properties"].get("name")
            out.append({"name": name, "lat": round(lat, 5), "lon": round(lon, 5), "geometry": f["geometry"],
                        "shapeID": f["properties"].get("shapeID")})
    return sorted(out, key=lambda d: d["name"])
