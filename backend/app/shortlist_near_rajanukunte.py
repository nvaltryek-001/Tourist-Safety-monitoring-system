import csv
import math
from pathlib import Path

INPUT = Path("data/kml_dataset_inventory.csv")
OUTPUT = Path("data/near_rajanukunte_shortlist.csv")

# Approximate reference point, not live GPS.
REFERENCE_LAT = 13.1665
REFERENCE_LON = 77.5611

def haversine_km(lat1, lon1, lat2, lon2):
    radius = 6371.0
    p1 = math.radians(lat1)
    p2 = math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)

    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(p1) * math.cos(p2) * math.sin(dlon / 2) ** 2
    )
    return 2 * radius * math.asin(math.sqrt(min(1, a)))

with INPUT.open(encoding="utf-8-sig", newline="") as f:
    records = list(csv.DictReader(f))

candidates = []

for row in records:
    try:
        lat = float(row["average_latitude_screening_only"])
        lon = float(row["average_longitude_screening_only"])
    except (ValueError, TypeError):
        continue

    row["approx_distance_km"] = round(
        haversine_km(REFERENCE_LAT, REFERENCE_LON, lat, lon), 2
    )
    candidates.append(row)

# Remove exact duplicates by normalized name and rounded screening point.
unique = {}
for row in candidates:
    key = (
        row["name"].strip().upper(),
        round(float(row["average_latitude_screening_only"]), 3),
        round(float(row["average_longitude_screening_only"]), 3),
    )
    if key not in unique or row["source_file"].startswith("Bengaluru Urban"):
        unique[key] = row

shortlist = sorted(
    unique.values(),
    key=lambda r: float(r["approx_distance_km"])
)[:30]

fields = list(shortlist[0].keys()) if shortlist else [
    "source_file", "name", "approx_distance_km"
]

with OUTPUT.open("w", encoding="utf-8-sig", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=fields)
    writer.writeheader()
    writer.writerows(shortlist)

print(f"Candidate records written: {len(shortlist)}")
print(f"Saved to: {OUTPUT}")
print("Distances use averaged polygon coordinates for screening only.")
