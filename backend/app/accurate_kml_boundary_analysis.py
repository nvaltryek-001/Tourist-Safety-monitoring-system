import csv
import math
import re
import xml.etree.ElementTree as ET
from pathlib import Path

from pyproj import CRS, Transformer
from shapely.geometry import Polygon, MultiPolygon, Point
from shapely.ops import transform
from shapely.validation import make_valid

DATA_DIR = Path("data")
OUTPUT_FILE = DATA_DIR / "accurate_near_rajanukunte.csv"

# Approximate Rajanukunte reference point; not live GPS.
REFERENCE_LAT = 13.1665
REFERENCE_LON = 77.5611

# UTM Zone 43N is suitable for this Bengaluru-area analysis.
project = Transformer.from_crs(
    "EPSG:4326", "EPSG:32643", always_xy=True
).transform

reference = transform(
    project, Point(REFERENCE_LON, REFERENCE_LAT)
)

def local_name(tag):
    return tag.rsplit("}", 1)[-1]

def parse_coordinates(text):
    points = []
    if not text:
        return points

    for item in text.strip().split():
        parts = item.split(",")
        if len(parts) >= 2:
            try:
                lon, lat = float(parts[0]), float(parts[1])
                if -180 <= lon <= 180 and -90 <= lat <= 90:
                    points.append((lon, lat))
            except ValueError:
                continue
    return points

def parse_ring(element):
    for child in element.iter():
        if local_name(child.tag) == "coordinates":
            coords = parse_coordinates(child.text)
            if len(coords) >= 3:
                if coords[0] != coords[-1]:
                    coords.append(coords[0])
                return coords
    return []

def parse_polygon(element):
    outer = []
    holes = []

    for child in element.iter():
        if local_name(child.tag) == "outerBoundaryIs":
            outer = parse_ring(child)
        elif local_name(child.tag) == "innerBoundaryIs":
            ring = parse_ring(child)
            if ring:
                holes.append(ring)

    if len(outer) < 4:
        return None

    try:
        polygon = Polygon(outer, holes)
        if not polygon.is_valid:
            polygon = make_valid(polygon)
        if polygon.is_empty:
            return None
        return polygon
    except Exception:
        return None

def geometry_from_placemark(placemark):
    polygons = []

    for element in placemark.iter():
        if local_name(element.tag) == "Polygon":
            polygon = parse_polygon(element)
            if polygon is not None:
                if polygon.geom_type == "Polygon":
                    polygons.append(polygon)
                elif polygon.geom_type == "MultiPolygon":
                    polygons.extend(list(polygon.geoms))
                elif polygon.geom_type == "GeometryCollection":
                    polygons.extend(
                        g for g in polygon.geoms
                        if g.geom_type == "Polygon"
                    )

    if not polygons:
        return None

    return polygons[0] if len(polygons) == 1 else MultiPolygon(polygons)

def read_name(placemark):
    for child in placemark:
        if local_name(child.tag) == "name":
            return (child.text or "").strip()
    return ""

def normalize_name(name):
    name = re.sub(r"^\s*ESZ\s*", "", name, flags=re.I)
    return re.sub(r"[^A-Z0-9]+", " ", name.upper()).strip()

rows = []
seen = set()

kml_files = sorted(DATA_DIR.glob("*.kml"))
if not kml_files:
    raise SystemExit(
        "No .kml files found in data/. Check your current folder."
    )

for kml_file in kml_files:
    print(f"Reading: {kml_file.name}")
    try:
        root = ET.parse(kml_file).getroot()
    except ET.ParseError as exc:
        print(f"  Skipped invalid KML: {exc}")
        continue

    for placemark in root.iter():
        if local_name(placemark.tag) != "Placemark":
            continue

        name = read_name(placemark)
        if not name:
            continue

        geometry = geometry_from_placemark(placemark)
        if geometry is None:
            continue

        # Project actual polygon geometry into metres.
        projected_geometry = transform(project, geometry)

        # Distance is zero when the reference point lies inside a polygon.
        distance_m = reference.distance(projected_geometry)
        nearest = projected_geometry.boundary.interpolate(
            projected_geometry.boundary.project(reference)
        ) if distance_m > 0 else reference

        nearest_lon, nearest_lat = Transformer.from_crs(
            "EPSG:32643", "EPSG:4326", always_xy=True
        ).transform(nearest.x, nearest.y)

        key = (
            normalize_name(name),
            round(distance_m / 1000, 1),
            kml_file.name.lower().replace("bengaluru urban ", "")
        )

        # Avoid identical repeats within the same source file.
        if (normalize_name(name), kml_file.name, geometry.wkb) in seen:
            continue
        seen.add((normalize_name(name), kml_file.name, geometry.wkb))

        rows.append({
            "name": name,
            "normalized_name": normalize_name(name),
            "distance_to_boundary_km": round(distance_m / 1000, 3),
            "nearest_boundary_latitude": round(nearest_lat, 6),
            "nearest_boundary_longitude": round(nearest_lon, 6),
            "source_file": kml_file.name,
            "source_year": 2022,
            "geometry_type": geometry.geom_type,
            "legal_status": "VERIFY CURRENT OFFICIAL NOTIFICATION",
            "distance_method": "Projected KML polygon boundary",
        })

rows.sort(key=lambda row: row["distance_to_boundary_km"])

fields = [
    "name", "normalized_name", "distance_to_boundary_km",
    "nearest_boundary_latitude", "nearest_boundary_longitude",
    "source_file", "source_year", "geometry_type",
    "legal_status", "distance_method"
]

with OUTPUT_FILE.open("w", newline="", encoding="utf-8-sig") as f:
    writer = csv.DictWriter(f, fieldnames=fields)
    writer.writeheader()
    writer.writerows(rows)

print(f"\nPolygon records analysed: {len(rows)}")
print(f"Saved to: {OUTPUT_FILE}")
print("Distances are to actual polygon boundaries, not averaged vertices.")
print("Source data is from 2022; verify current legal notifications.")
