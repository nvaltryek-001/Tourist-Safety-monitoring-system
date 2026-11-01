"""Pure-Python geofencing: Haversine distance, point-in-polygon and status.

This module has no database or framework imports so it can be unit tested
in isolation and reused by scripts.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, field

EARTH_RADIUS_M = 6371000


def distance_meters(lat1, lon1, lat2, lon2):
    radius = EARTH_RADIUS_M
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlon / 2) ** 2
    return radius * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def valid_coordinate(lat, lon) -> bool:
    try:
        return -90 <= float(lat) <= 90 and -180 <= float(lon) <= 180 and not (
            math.isnan(float(lat)) or math.isnan(float(lon))
        )
    except (TypeError, ValueError):
        return False


# ------------------------------------------------------------- polygons
def _point_in_ring(lon: float, lat: float, ring: list) -> bool:
    inside = False
    n = len(ring)
    if n < 3:
        return False
    j = n - 1
    for i in range(n):
        xi, yi = ring[i][0], ring[i][1]
        xj, yj = ring[j][0], ring[j][1]
        if (yi > lat) != (yj > lat):
            x_cross = (xj - xi) * (lat - yi) / ((yj - yi) or 1e-15) + xi
            if lon < x_cross:
                inside = not inside
        j = i
    return inside


def point_in_polygon(lat: float, lon: float, geometry: dict) -> bool:
    """GeoJSON Polygon / MultiPolygon containment (holes respected)."""
    gtype = geometry.get("type")
    if gtype == "Polygon":
        polygons = [geometry.get("coordinates") or []]
    elif gtype == "MultiPolygon":
        polygons = geometry.get("coordinates") or []
    else:
        return False
    for rings in polygons:
        if not rings:
            continue
        if _point_in_ring(lon, lat, rings[0]) and not any(
            _point_in_ring(lon, lat, hole) for hole in rings[1:]
        ):
            return True
    return False


def ring_is_valid(ring: list) -> list[str]:
    problems = []
    if len(ring) < 4:
        problems.append("ring needs at least 4 positions (closed)")
        return problems
    if list(ring[0][:2]) != list(ring[-1][:2]):
        problems.append("ring is not closed")
    for pos in ring:
        if len(pos) < 2 or not valid_coordinate(pos[1], pos[0]):
            problems.append(f"invalid position {pos}")
            break
    # simple self-intersection check (O(n^2), fine for zone polygons)
    segs = [(ring[i], ring[i + 1]) for i in range(len(ring) - 1)]
    for i in range(len(segs)):
        for j in range(i + 2, len(segs)):
            if i == 0 and j == len(segs) - 1:
                continue
            if _segments_intersect(segs[i][0], segs[i][1], segs[j][0], segs[j][1]):
                problems.append("ring self-intersects")
                return problems
    return problems


def _orient(a, b, c):
    return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])


def _segments_intersect(p1, p2, p3, p4) -> bool:
    d1, d2 = _orient(p3, p4, p1), _orient(p3, p4, p2)
    d3, d4 = _orient(p1, p2, p3), _orient(p1, p2, p4)
    return (d1 * d2 < 0) and (d3 * d4 < 0)


def validate_geometry(geometry: dict) -> list[str]:
    gtype = geometry.get("type")
    if gtype == "Polygon":
        polys = [geometry.get("coordinates") or []]
    elif gtype == "MultiPolygon":
        polys = geometry.get("coordinates") or []
    else:
        return [f"unsupported geometry type {gtype!r}; use Polygon or MultiPolygon"]
    problems = []
    if not polys:
        return ["geometry has no coordinates"]
    for rings in polys:
        if not rings:
            problems.append("polygon has no rings")
        for ring in rings:
            problems.extend(ring_is_valid(ring))
    return problems


def polygon_centroid_and_radius(geometry: dict) -> tuple[float, float, float]:
    """Approximate centroid (vertex mean) and enclosing radius in metres."""
    gtype = geometry.get("type")
    polys = [geometry["coordinates"]] if gtype == "Polygon" else geometry["coordinates"]
    points = [pos for rings in polys for pos in rings[0][:-1]]
    lon = sum(p[0] for p in points) / len(points)
    lat = sum(p[1] for p in points) / len(points)
    radius = max(distance_meters(lat, lon, p[1], p[0]) for p in points)
    return lat, lon, radius


# ------------------------------------------------------------- evaluation
@dataclass
class ZoneShape:
    id: int
    name: str
    zone_type: str
    latitude: float
    longitude: float
    radius_meters: float
    risk_level: str | None = None
    geometry: dict | None = None

    @classmethod
    def from_row(cls, row) -> "ZoneShape":
        geometry = None
        raw = getattr(row, "geometry_geojson", None)
        if raw:
            try:
                geometry = json.loads(raw)
            except (TypeError, ValueError):
                geometry = None
        return cls(
            id=row.id,
            name=row.name,
            zone_type=(row.zone_type or "SAFE").upper(),
            latitude=row.latitude,
            longitude=row.longitude,
            radius_meters=row.radius_meters,
            risk_level=(getattr(row, "risk_level", None) or None),
            geometry=geometry,
        )

    def contains(self, lat: float, lon: float) -> tuple[bool, float]:
        distance = distance_meters(lat, lon, self.latitude, self.longitude)
        if self.geometry:
            return point_in_polygon(lat, lon, self.geometry), distance
        return distance <= self.radius_meters, distance


@dataclass
class GeofenceResult:
    status: str
    inside: list[dict] = field(default_factory=list)
    nearby: list[dict] = field(default_factory=list)
    nearest: dict | None = None

    @property
    def inside_ids(self) -> set[int]:
        return {z["zone_id"] for z in self.inside}


DANGER_TYPES = {"RESTRICTED", "HIGH_RISK"}


def evaluate(lat: float, lon: float, zones: list[ZoneShape], caution_ratio: float = 1.5) -> GeofenceResult:
    """Classify a position against active zones.

    * DANGER  – inside a RESTRICTED zone or a zone with risk_level HIGH
    * CAUTION – inside a MEDIUM-risk / HIGH_RISK-adjacent buffer, or within
      ``caution_ratio`` × radius of a restricted zone
    * SAFE    – none of the above (it only means "no known zone hazard")
    """
    result = GeofenceResult(status="SAFE")
    nearest_restricted = None
    for zone in zones:
        inside, distance = zone.contains(lat, lon)
        record = {
            "zone_id": zone.id,
            "zone_name": zone.name,
            "zone_type": zone.zone_type,
            "risk_level": zone.risk_level,
            "distance_meters": round(distance, 2),
            "radius_meters": zone.radius_meters,
        }
        dangerous = zone.zone_type in DANGER_TYPES or (zone.risk_level or "").upper() == "HIGH"
        if inside:
            result.inside.append(record)
        elif dangerous and distance <= zone.radius_meters * caution_ratio:
            result.nearby.append(record)
        if dangerous and (nearest_restricted is None or distance < nearest_restricted["distance_meters"]):
            nearest_restricted = record

    result.nearest = nearest_restricted
    if any(
        z["zone_type"] in DANGER_TYPES or (z["risk_level"] or "").upper() == "HIGH"
        for z in result.inside
    ):
        result.status = "DANGER"
    elif result.nearby or any((z["risk_level"] or "").upper() == "MEDIUM" for z in result.inside):
        result.status = "CAUTION"
    return result


def transitions(previous_inside: set[int], current_inside: set[int]) -> tuple[set[int], set[int]]:
    """Return (entered, exited) zone ids."""
    return current_inside - previous_inside, previous_inside - current_inside


def circles_overlap(a: ZoneShape, b: ZoneShape) -> tuple[bool, float]:
    d = distance_meters(a.latitude, a.longitude, b.latitude, b.longitude)
    return d < (a.radius_meters + b.radius_meters), d
