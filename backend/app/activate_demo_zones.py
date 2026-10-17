from app.database import SessionLocal
from app.models.models import SafetyZone

db = SessionLocal()

try:
    zones = db.query(SafetyZone).filter(
        SafetyZone.name.like("DEMO-KA-%")
    ).all()

    for zone in zones:
        zone.active = True

    db.commit()

    print(f"Total demo zones activated: {len(zones)}")
    print("Dataset label: SYNTHETIC TEST DATA")
    print("Use for analysis and testing, not real-world safety decisions.")

except Exception:
    db.rollback()
    raise

finally:
    db.close()
