import json
import xml.etree.ElementTree as ET
from pathlib import Path
from shapely.geometry import Polygon, MultiPolygon, mapping
from shapely.validation import make_valid

DATA = Path("data")
OUTPUT = DATA / "karnataka_boundary_review.geojson"

def tag(element):
    return element.tag.rsplit("}", 1)[-1]

def coordinates(text):
    result = []
    for item in (text or "").strip().split():
        parts = item.split(",")
        if len(parts) >= 2:
            try:
                lon, lat = float(parts[0]), float(parts[1])
                if -180 <= lon <= 180 and -90 <= lat <= 90:
                    result.append((lon, lat))
            except ValueError:
                pass
    return result

def read_ring(boundary):
    for element in boundary.iter():
        if tag(element) == "coordinates":
            points = coordinates(element.text)
            if len(points) >= 3:
                if points[0] != points[-1]:
                    points.append(points[0])
                return points
    return []

def read_polygon(element):
    outer = []
    holes = []
    for child in element:
        if tag(child) == "outerBoundaryIs":
            outer = read_ring(child)
        elif tag(child) == "innerBoundaryIs":
            ring = read_ring(child)
            if ring:
                holes.append(ring)

    if len(outer) < 4:
        return None
    polygon = Polygon(outer, holes)
    if not polygon.is_valid:
        polygon = make_valid(polygon)
    return polygon if not polygon.is_empty else None

features = []
for path in sorted(DATA.glob("*.kml")):
    root = ET.parse(path).getroot()
    for placemark in root.iter():
        if tag(placemark) != "Placemark":
            continue

        name = ""
        for child in placemark:
            if tag(child) == "name":
                name = (child.text or "").strip()
                break

        polygons = []
        for element in placemark.iter():
            if tag(element) == "Polygon":
                polygon = read_polygon(element)
                if polygon is None:
                    continue
                if polygon.geom_type == "Polygon":
                    polygons.append(polygon)
                elif polygon.geom_type == "MultiPolygon":
                    polygons.extend(polygon.geoms)
                elif polygon.geom_type == "GeometryCollection":
                    polygons.extend(
                        g for g in polygon.geoms
                        if g.geom_type == "Polygon"
                    )

        if not polygons:
            continue

        geometry = polygons[0] if len(polygons) == 1 else MultiPolygon(polygons)
        if not geometry.is_valid:
            geometry = make_valid(geometry)

        features.append({
            "type": "Feature",
            "geometry": mapping(geometry),
            "properties": {
                "name": name,
                "source_file": path.name,
                "source_year": 2022,
                "zone_category": (
                    "ECO_SENSITIVE_ZONE"
                    if "eco-sensitive" in path.name.lower()
                    else "PROTECTED_AREA"
                ),
                "verification_status": "PENDING_OFFICIAL_REVIEW",
                "alert_enabled": False
            }
        })

collection = {
    "type": "FeatureCollection",
    "features": features
}
OUTPUT.write_text(json.dumps(collection), encoding="utf-8")
print("Polygon features exported:", len(features))
print("Output:", OUTPUT)
print("Status: pending review; alerts disabled.")
