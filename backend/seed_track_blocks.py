from datetime import datetime

from database import SessionLocal
from models import OTDevice, TrackBlock


SIGNAL_CONTROLLER_NAME = "Signal Controller 14A"
SIGNAL_CONTROLLER_BLOCK_NAMES = {
    "Block E82",
    "Block E84",
}


TRACK_BLOCK_DATA = [
    {
        "name": "Block E80",
        "subdivision": "East Subdivision",
        "track": "Main",
        "start_milepost": 80.0,
        "end_milepost": 82.0,
        "speed_limit": 49,
    },
    {
        "name": "Block E82",
        "subdivision": "East Subdivision",
        "track": "Main",
        "start_milepost": 82.0,
        "end_milepost": 84.0,
        "speed_limit": 49,
    },
    {
        "name": "Block E84",
        "subdivision": "East Subdivision",
        "track": "Main",
        "start_milepost": 84.0,
        "end_milepost": 86.0,
        "speed_limit": 49,
    },
    {
        "name": "Block E86",
        "subdivision": "East Subdivision",
        "track": "Main",
        "start_milepost": 86.0,
        "end_milepost": 88.0,
        "speed_limit": 49,
    },
    {
        "name": "Block E88",
        "subdivision": "East Subdivision",
        "track": "Main",
        "start_milepost": 88.0,
        "end_milepost": 90.0,
        "speed_limit": 49,
    },
    {
        "name": "Block E90",
        "subdivision": "East Subdivision",
        "track": "Main",
        "start_milepost": 90.0,
        "end_milepost": 92.0,
        "speed_limit": 45,
    },
    {
        "name": "Block E92",
        "subdivision": "East Subdivision",
        "track": "Main",
        "start_milepost": 92.0,
        "end_milepost": 94.0,
        "speed_limit": 45,
    },
    {
        "name": "Block E94",
        "subdivision": "East Subdivision",
        "track": "Main",
        "start_milepost": 94.0,
        "end_milepost": 96.0,
        "speed_limit": 40,
    },
    {
        "name": "Block E96",
        "subdivision": "East Subdivision",
        "track": "Main",
        "start_milepost": 96.0,
        "end_milepost": 98.0,
        "speed_limit": 40,
    },
    {
        "name": "Block E98",
        "subdivision": "East Subdivision",
        "track": "Main",
        "start_milepost": 98.0,
        "end_milepost": 100.0,
        "speed_limit": 35,
    },
]


def assign_signal_controller_track_blocks(db):
    controller = (
        db.query(OTDevice)
        .filter(OTDevice.name == SIGNAL_CONTROLLER_NAME)
        .first()
    )

    if controller is None:
        return []

    assigned_blocks = (
        db.query(TrackBlock)
        .filter(TrackBlock.name.in_(SIGNAL_CONTROLLER_BLOCK_NAMES))
        .all()
    )

    for block in assigned_blocks:
        block.controlling_device_id = controller.id

    return assigned_blocks


def seed_track_blocks(db=None):
    owns_session = db is None
    db = db or SessionLocal()

    try:
        created_count = 0

        for block_data in TRACK_BLOCK_DATA:
            block = (
                db.query(TrackBlock)
                .filter(TrackBlock.name == block_data["name"])
                .first()
            )

            if block is None:
                block = TrackBlock(
                    name=block_data["name"],
                    subdivision=block_data["subdivision"],
                    track=block_data["track"],
                    start_milepost=block_data["start_milepost"],
                    end_milepost=block_data["end_milepost"],
                    occupied=False,
                    occupied_train_id=None,
                    signal_aspect="Clear",
                    authority="Main Track",
                    speed_limit=block_data["speed_limit"],
                    communications_status="Online",
                    security_status="Healthy",
                    maintenance=False,
                    notes="",
                    last_updated=datetime.utcnow(),
                )
                db.add(block)
                created_count += 1

        db.flush()
        assigned_blocks = assign_signal_controller_track_blocks(db)

        if not assigned_blocks:
            raise RuntimeError(
                f"{SIGNAL_CONTROLLER_NAME} must exist before "
                "track blocks can be seeded."
            )

        db.commit()

        print(
            f"Track-block setup complete: {created_count} created, "
            f"{len(assigned_blocks)} assigned to "
            f"{SIGNAL_CONTROLLER_NAME}."
        )

        return assigned_blocks

    except Exception as exc:
        db.rollback()
        print(f"Track block seeding failed: {exc}")
        raise

    finally:
        if owns_session:
            db.close()


if __name__ == "__main__":
    seed_track_blocks()
