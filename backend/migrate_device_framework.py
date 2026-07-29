"""Idempotent additive migration for the data-driven OT device framework."""

from database import Base, SessionLocal, engine, ensure_sqlite_schema
import models
from services.device_framework import initialize_device_framework


def migrate():
    Base.metadata.create_all(bind=engine)
    ensure_sqlite_schema()
    db = SessionLocal()
    try:
        initialize_device_framework(db)
        db.commit()
        return {
            "device_types": db.query(models.OTDeviceType).count(),
            "relationships": db.query(models.DeviceRelationship).count(),
            "devices": db.query(models.OTDevice).count(),
        }
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    result = migrate()
    print(
        "OT device framework migration complete: "
        f"{result['device_types']} types, "
        f"{result['relationships']} relationships, "
        f"{result['devices']} devices."
    )
