import csv
import xml.etree.ElementTree as ET
from pathlib import Path

DATA_DIR = Path("data")
OUTPUT = DATA_DIR / "kml_dataset_inventory.csv"

def local_name(tag):
    return tag.rsplit("}", 1)[-1]

rows = []

for file_path in sorted(DATA_DIR.glob("*.kml")):
    print(f"Inspecting: {file_path.name}")

    try:
        root = ET.parse(file_path).getroot()
    except ET.ParseError as exc:
        print(f"  Could not parse XML: {exc}")
        continue

    placemarks = [
        element for element in root.iter()
        if local_name(element.tag) == "Placemark"
    ]

    print(f"  Placemarks found: {len(placemarks)}")

    for placemark in placemarks:
        name = ""
        description = ""
        geometry_types = set()
        coordinates = []

        for element in placemark.iter():
            tag = local_name(element.tag)

            if tag == "name" and not name:
                name = (element.text or "").strip()

            elif tag == "description" and not description:
                description = (element.text or "").strip()

            elif tag in {
                "Point", "LineString", "Polygon",
                "MultiGeometry", "LinearRing"
            }:
                geometry_types.add(tag)

            elif tag == "coordinates" and element.text:
                for item in element.text.split():
                    parts = item.split(",")
                    if len(parts) >= 2:
                        try:
                            lon = float(parts[0])
                            lat = float(parts[1])
                            coordinates.append((lon, lat))
                        except ValueError:
                            pass

        # Average coordinate is for rough screening only,
        # not an accurate polygon centroid.
        avg_lat = (
            sum(lat for _, lat in coordinates) / len(coordinates)
            if coordinates else None
        )
        avg_lon = (
            sum(lon for lon, _ in coordinates) / len(coordinates)
            if coordinates else None
        )

        rows.append({
            "source_file": file_path.name,
            "name": name,
            "geometry_types": ", ".join(sorted(geometry_types)),
            "coordinate_count": len(coordinates),
            "average_latitude_screening_only": avg_lat,
            "average_longitude_screening_only": avg_lon,
            "description": description[:500],
            "source_year": "2022",
        })

with OUTPUT.open("w", newline="", encoding="utf-8-sig") as csvfile:
    fieldnames = [
        "source_file", "name", "geometry_types",
        "coordinate_count",
        "average_latitude_screening_only",
        "average_longitude_screening_only",
        "description", "source_year",
    ]
    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)

print("\nInspection completed.")
print(f"Total placemarks: {len(rows)}")
print(f"Inventory saved to: {OUTPUT}")
print("Note: averaged coordinates are for screening only.")
