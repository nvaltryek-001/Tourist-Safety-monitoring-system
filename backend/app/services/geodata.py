"""GeoJSON / KML parsing and export, duplicate detection and dataset audit.

Pure Python (xml.etree + json); no database imports.
"""

from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from xml.sax.saxutils import escape

from app.services.geofence import (
    ZoneShape,
    circles_overlap,
    polygon_centroid_and_radius,
    valid_coordinate,
    validate_geometry,
)

ZONE_TYPES = {"SAFE", "RESTRICTED", "HIGH_RISK", "CAUTION"}
RISK_LEVELS = {"LOW", "MEDIUM", "HIGH"}
MAX_IMPORT_BYTES = 5 * 1024 * 1024
MAX_IMPORT_FEATURES = 5000
DEFAULT_POINT_RADIUS = 200.0


@dataclass
class ParsedZone:
    name: str
    latitude: float
    longitude: float
    radius_meters: float
    zone_type: str = "RESTRICTED"
    risk_level: str | None = None
    description: str | None = None
    geometry: dict | None = None
    problems: list[str] = field(default_factory=list)

    def dedupe_key(self) -> tuple:
        return dedupe_key(self.name, self.latitude, self.longitude)


def dedupe_key(name: str, lat: float, lon: float) -> tuple:
    return ((name or "").strip().upper(), round(float(lat), 6), round(float(lon), 6))


def is_synthetic(name: str | None, description: str | None) -> bool:
    text = f"{name or ''} {description or ''}".upper()
    return "SYNTHETIC" in text or (name or "").upper().startswith("DEMO-KA-")


def is_college_demo(name: str | None) -> bool:
    return (name or "").strip().lower().startswith("college demo zone")


def _clean_type(value, default="RESTRICTED") -> str:
    value = (str(value or default)).strip().upper().replace(" ", "_")
    return value if value in ZONE_TYPES else default


def _clean_risk(value) -> str | None:
    if not value:
        return None
    value = str(value).strip().upper()
    return value if value in RISK_LEVELS else None


def _zone_from_geometry(name, geometry, props) -> ParsedZone:
    gtype = (geometry or {}).get("type")
    radius = props.get("radius_meters") or props.get("radius")
    zone_type = _clean_type(props.get("zone_type") or props.get("type"))
    risk = _clean_risk(props.get("risk_level"))
    desc = props.get("description")
    if gtype == "Point":
        coords = geometry.get("coordinates") or []
        if len(coords) < 2 or not valid_coordinate(coords[1], coords[0]):
            return ParsedZone(name, 0, 0, 0, problems=["invalid point coordinates"])
        try:
            radius = float(radius) if radius else DEFAULT_POINT_RADIUS
        except (TypeError, ValueError):
            radius = DEFAULT_POINT_RADIUS
        zone = ParsedZone(name, float(coords[1]), float(coords[0]), radius, zone_type, risk, desc)
        if not 0 < radius <= 100000:
            zone.problems.append("radius must be between 0 and 100000 metres")
        return zone
    if gtype in {"Polygon", "MultiPolygon"}:
        problems = validate_geometry(geometry)
        if problems:
            return ParsedZone(name, 0, 0, 0, problems=problems)
        lat, lon, enclosing = polygon_centroid_and_radius(geometry)
        return ParsedZone(name, lat, lon, round(enclosing, 2), zone_type, risk, desc, geometry)
    return ParsedZone(name, 0, 0, 0, problems=[f"unsupported geometry {gtype!r}"])


def parse_geojson(raw: bytes | str) -> list[ParsedZone]:
    data = json.loads(raw)
    if data.get("type") == "Feature":
        features = [data]
    elif data.get("type") == "FeatureCollection":
        features = data.get("features") or []
    else:
        raise ValueError("GeoJSON must be a Feature or FeatureCollection")
    if len(features) > MAX_IMPORT_FEATURES:
        raise ValueError(f"too many features (max {MAX_IMPORT_FEATURES})")
    zones = []
    for index, feature in enumerate(features, start=1):
        props = feature.get("properties") or {}
        name = str(props.get("name") or f"Imported zone {index}")[:100]
        zones.append(_zone_from_geometry(name, feature.get("geometry"), props))
    return zones


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _kml_coords(text: str | None) -> list[list[float]]:
    out = []
    for item in (text or "").split():
        parts = item.split(",")
        if len(parts) >= 2:
            try:
                out.append([float(parts[0]), float(parts[1])])
            except ValueError:
                continue
    return out


def parse_kml(raw: bytes | str) -> list[ParsedZone]:
    if isinstance(raw, str):
        raw = raw.encode()
    upper = raw[:2000].upper()
    if b"<!DOCTYPE" in upper or b"<!ENTITY" in upper:
        # refuse DTDs: blocks entity-expansion (billion laughs) attacks
        raise ValueError("KML with DTD/ENTITY declarations is not accepted")
    root = ET.fromstring(raw)
    zones = []
    placemarks = [el for el in root.iter() if _local(el.tag) == "Placemark"]
    if len(placemarks) > MAX_IMPORT_FEATURES:
        raise ValueError(f"too many placemarks (max {MAX_IMPORT_FEATURES})")
    for index, pm in enumerate(placemarks, start=1):
        name, desc = f"Imported zone {index}", None
        props: dict = {}
        polygons, point = [], None
        for child in pm:
            tag = _local(child.tag)
            if tag == "name" and child.text:
                name = child.text.strip()[:100]
            elif tag == "description" and child.text:
                desc = child.text.strip()[:2000]
            elif tag == "ExtendedData":
                for data in child.iter():
                    if _local(data.tag) == "Data":
                        value = next((v.text for v in data if _local(v.tag) == "value"), None)
                        props[data.get("name", "")] = value
        for el in pm.iter():
            tag = _local(el.tag)
            if tag == "Polygon":
                rings = []
                for boundary in el:
                    btag = _local(boundary.tag)
                    coords_el = next((c for c in boundary.iter() if _local(c.tag) == "coordinates"), None)
                    ring = _kml_coords(coords_el.text if coords_el is not None else "")
                    if ring and ring[0] != ring[-1]:
                        ring.append(list(ring[0]))
                    if btag == "outerBoundaryIs":
                        rings.insert(0, ring)
                    elif btag == "innerBoundaryIs":
                        rings.append(ring)
                if rings:
                    polygons.append(rings)
            elif tag == "Point" and point is None:
                coords_el = next((c for c in el.iter() if _local(c.tag) == "coordinates"), None)
                pts = _kml_coords(coords_el.text if coords_el is not None else "")
                if pts:
                    point = pts[0]
        props.setdefault("description", desc)
        if polygons:
            geometry = (
                {"type": "Polygon", "coordinates": polygons[0]}
                if len(polygons) == 1
                else {"type": "MultiPolygon", "coordinates": polygons}
            )
        elif point:
            geometry = {"type": "Point", "coordinates": point}
        else:
            zones.append(ParsedZone(name, 0, 0, 0, problems=["placemark has no Point or Polygon"]))
            continue
        zones.append(_zone_from_geometry(name, geometry, props))
    return zones


def parse_upload(filename: str, raw: bytes) -> list[ParsedZone]:
    if len(raw) > MAX_IMPORT_BYTES:
        raise ValueError("file is larger than 5 MB")
    lower = (filename or "").lower()
    if lower.endswith((".geojson", ".json")):
        return parse_geojson(raw)
    if lower.endswith(".kml"):
        return parse_kml(raw)
    raise ValueError("only .geojson, .json and .kml files are accepted")


# ----------------------------------------------------------------- export
def zone_to_feature(zone) -> dict:
    geometry = None
    if getattr(zone, "geometry_geojson", None):
        try:
            geometry = json.loads(zone.geometry_geojson)
        except ValueError:
            geometry = None
    if geometry is None:
        geometry = {"type": "Point", "coordinates": [zone.longitude, zone.latitude]}
    return {
        "type": "Feature",
        "geometry": geometry,
        "properties": {
            "id": zone.id,
            "name": zone.name,
            "zone_type": zone.zone_type,
            "risk_level": getattr(zone, "risk_level", None),
            "radius_meters": zone.radius_meters,
            "active": zone.active,
            "description": zone.description,
            "source": getattr(zone, "source", None),
            "synthetic": is_synthetic(zone.name, zone.description),
        },
    }


def export_geojson(zones) -> dict:
    return {"type": "FeatureCollection", "features": [zone_to_feature(z) for z in zones]}


def export_kml(zones) -> str:
    parts = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<kml xmlns="http://www.opengis.net/kml/2.2"><Document><name>Safety zones</name>',
    ]
    for z in zones:
        feature = zone_to_feature(z)
        geom = feature["geometry"]
        props = feature["properties"]
        data = "".join(
            f'<Data name="{escape(str(k))}"><value>{escape(str(v))}</value></Data>'
            for k, v in props.items()
            if v is not None and k not in {"name", "description"}
        )
        if geom["type"] == "Point":
            body = f"<Point><coordinates>{geom['coordinates'][0]},{geom['coordinates'][1]}</coordinates></Point>"
        else:
            polys = [geom["coordinates"]] if geom["type"] == "Polygon" else geom["coordinates"]
            chunks = []
            for rings in polys:
                ring_xml = []
                for i, ring in enumerate(rings):
                    coords = " ".join(f"{p[0]},{p[1]}" for p in ring)
                    wrapper = "outerBoundaryIs" if i == 0 else "innerBoundaryIs"
                    ring_xml.append(f"<{wrapper}><LinearRing><coordinates>{coords}</coordinates></LinearRing></{wrapper}>")
                chunks.append("<Polygon>" + "".join(ring_xml) + "</Polygon>")
            body = chunks[0] if len(chunks) == 1 else "<MultiGeometry>" + "".join(chunks) + "</MultiGeometry>"
        parts.append(
            f"<Placemark><name>{escape(z.name)}</name>"
            f"<description>{escape(z.description or '')}</description>"
            f"<ExtendedData>{data}</ExtendedData>{body}</Placemark>"
        )
    parts.append("</Document></kml>")
    return "".join(parts)


# ------------------------------------------------------------------ audit
def find_overlaps(shapes: list[ZoneShape], limit: int = 500) -> list[dict]:
    """Pairwise circle overlap with a cheap latitude pre-filter."""
    items = sorted(shapes, key=lambda s: s.latitude)
    overlaps = []
    for i, a in enumerate(items):
        for b in items[i + 1:]:
            # 1 degree latitude ~ 111 km
            if (b.latitude - a.latitude) * 111_000 > a.radius_meters + b.radius_meters:
                break
            hit, d = circles_overlap(a, b)
            if hit:
                overlaps.append({
                    "zone_a": {"id": a.id, "name": a.name},
                    "zone_b": {"id": b.id, "name": b.name},
                    "centre_distance_m": round(d, 1),
                    "combined_radius_m": a.radius_meters + b.radius_meters,
                })
                if len(overlaps) >= limit:
                    return overlaps
    return overlaps


def audit_zones(zones) -> dict:
    """Summarise zone records without changing anything."""
    shapes, invalid, keys, duplicates = [], [], {}, []
    coord_keys: dict = {}
    synthetic = college = 0
    by_type: dict[str, int] = {}
    college_rows = []
    for z in zones:
        by_type[z.zone_type] = by_type.get(z.zone_type, 0) + 1
        if is_synthetic(z.name, z.description):
            synthetic += 1
        if is_college_demo(z.name):
            college += 1
            college_rows.append({
                "id": z.id,
                "name": z.name,
                "radius_meters": z.radius_meters,
                "zone_type": z.zone_type,
                "active": z.active,
            })
        if not valid_coordinate(z.latitude, z.longitude) or not z.radius_meters or z.radius_meters <= 0:
            invalid.append({"id": z.id, "name": z.name})
            continue
        key = dedupe_key(z.name, z.latitude, z.longitude)
        if key in keys:
            duplicates.append({"id": z.id, "duplicate_of": keys[key], "kind": "name+coordinates"})
        else:
            keys[key] = z.id
        ckey = (round(z.latitude, 6), round(z.longitude, 6))
        if ckey in coord_keys and coord_keys[ckey] != z.id:
            duplicates.append({"id": z.id, "duplicate_of": coord_keys[ckey], "kind": "same coordinates"})
        else:
            coord_keys.setdefault(ckey, z.id)
        shapes.append(ZoneShape.from_row(z))

    college_shapes = [s for s in shapes if is_college_demo(s.name)]
    radii = sorted({row["radius_meters"] for row in college_rows})
    return {
        "total_zones": len(zones),
        "active_zones": sum(1 for z in zones if z.active),
        "by_type": by_type,
        "synthetic_zones": synthetic,
        "college_demo_zones": college,
        "college_demo_zone_rows": sorted(college_rows, key=lambda r: r["name"]),
        "college_demo_radii_found": radii,
        "college_demo_radius_note": (
            "Stored radii differ from the later 50 m specification; not changed automatically."
            if radii and radii != [50.0] else None
        ),
        "college_demo_overlaps": find_overlaps(college_shapes),
        "invalid_records": invalid,
        "duplicates": duplicates,
        "overlap_pairs_sample": find_overlaps([s for s in shapes], limit=100),
    }
