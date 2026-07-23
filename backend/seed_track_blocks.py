from datetime import datetime

from database import SessionLocal
from models import TrackBlock


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


def seed_track_blocks():
    db = SessionLocal()

    try:
        existing_count = db.query(TrackBlock).count()

        if existing_count > 0:
            print(
                f"Track blocks already exist. "
                f"Current count: {existing_count}"
            )
            return

        for block_data in TRACK_BLOCK_DATA:
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
                controlling_device_id=None,
                communications_status="Online",
                security_status="Healthy",
                maintenance=False,
                notes="",
                last_updated=datetime.utcnow(),
            )

            db.add(block)

        db.commit()

        print(
            f"Successfully seeded "
            f"{len(TRACK_BLOCK_DATA)} track blocks."
        )

    except Exception as exc:
        db.rollback()
        print(f"Track block seeding failed: {exc}")
        raise

    finally:
        db.close()


if __name__ == "__main__":
    seed_track_blocks()