import math
import random

from app.database import SessionLocal
from app.models.models import SafetyZone

# Approximate district-centre coordinates used only to generate
# synthetic test records. These are NOT restricted-zone locations.
DISTRICTS = [
    ("Bagalkot", 16.18, 75.70),
    ("Ballari", 15.14, 76.92),
    ("Belagavi", 15.85, 74.50),
    ("Bengaluru Urban", 12.97, 77.59),
    ("Bengaluru Rural", 13.28, 77.53),
    ("Bidar", 17.91, 77.52),
    ("Chamarajanagar", 11.92, 76.94),
    ("Chikkaballapur", 13.44, 77.73),
    ("Chikkamagaluru", 13.32, 75.77),
    ("Chitradurga", 14.23, 76.40),
    ("Dakshina Kannada", 12.87, 74.88),
    ("Davanagere", 14.47, 75.92),
    ("Dharwad", 15.46, 75.01),
    ("Gadag", 15.43, 75.63),
    ("Hassan", 13.01, 76.10),
    ("Haveri", 14.79, 75.40),
    ("Kalaburagi", 17.33, 76.83),
    ("Kodagu", 12.42, 75.74),
    ("Kolar", 13.14, 78.13),
    ("Koppal", 15.35, 76.15),
    ("Mandya", 12.52, 76.90),
    ("Mysuru", 12.30, 76.64),
    ("Raichur", 16.21, 77.36),
    ("Ramanagara", 12.72, 77.28),
    ("Shivamogga", 13.93, 75.57),
    ("Tumakuru", 13.34, 77.10),
    ("Udupi", 13.34, 74.75),
    ("Uttara Kannada", 14.80, 74.13),
    ("Vijayapura", 16.83, 75.71),
    ("Yadgir", 16.77, 77.14),
]

rng = random.Random(20261016)
db = SessionLocal()
created = 0
skipped = 0

try:
    for i in range(1, 201):
        code = f"DEMO-KA-{i:03d}"

        exists = db.query(SafetyZone).filter(
            SafetyZone.name == code
        ).first()

        if exists:
            skipped += 1
            continue

        district, lat, lon = DISTRICTS[(i - 1) % len(DISTRICTS)]

        # Small synthetic offset from the district centre.
        # These points are for software testing only.
        latitude = lat + rng.uniform(-0.04, 0.04)
        longitude = lon + rng.uniform(-0.04, 0.04)

        zone = SafetyZone(
            name=code,
            latitude=latitude,
            longitude=longitude,
            radius_meters=rng.choice([100, 150, 200, 250, 300, 500]),
            zone_type="RESTRICTED",
            description=(
                f"SYNTHETIC TEST DATA ONLY; district={district}; "
                "not a verified restricted or hazardous location"
            ),
            active=False,
        )

        db.add(zone)
        created += 1

    db.commit()
    print(f"New synthetic records inserted: {created}")
    print(f"Existing records skipped: {skipped}")
    print("All DEMO-KA records are inactive.")
    print("These records must not be presented as real restricted zones.")

except Exception:
    db.rollback()
    raise
finally:
    db.close()
