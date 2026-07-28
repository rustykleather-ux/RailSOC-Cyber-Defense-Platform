from datetime import datetime, timezone

from models import GradeCrossing, OTDevice, TrackBlock, TrackSwitch


def seed_operational_assets(db):
    """Create the minimum switch and crossing digital-twin relationships."""
    now = datetime.now(timezone.utc)
    switch_controller = db.query(OTDevice).filter(
        OTDevice.name == "Switch Machine Controller"
    ).first()
    crossing_controller = db.query(OTDevice).filter(
        OTDevice.name == "Grade Crossing Controller MP 82.4"
    ).first()
    block_e84 = db.query(TrackBlock).filter(
        TrackBlock.name == "Block E84"
    ).first()

    seeded = {"switches": [], "crossings": []}

    if switch_controller and block_e84:
        track_switch = db.query(TrackSwitch).filter(
            TrackSwitch.name == "Switch E86"
        ).first()
        if track_switch is None:
            track_switch = TrackSwitch(
                name="Switch E86",
                subdivision=block_e84.subdivision,
                track=block_e84.track,
                milepost=block_e84.end_milepost,
                track_block_id=block_e84.id,
                controlling_device_id=switch_controller.id,
                position="Normal",
                commanded_position="Normal",
                locked=False,
                communications_status="Online",
                security_status="Healthy",
                last_updated=now,
            )
            db.add(track_switch)
        else:
            track_switch.track_block_id = block_e84.id
            track_switch.controlling_device_id = switch_controller.id
        seeded["switches"].append(track_switch)

    if crossing_controller:
        crossing = db.query(GradeCrossing).filter(
            GradeCrossing.name == "Crossing MP 82.4"
        ).first()
        if crossing is None:
            crossing = GradeCrossing(
                name="Crossing MP 82.4",
                subdivision="East Subdivision",
                milepost=82.4,
                controlling_device_id=crossing_controller.id,
                gate_state="Raised",
                lights_active=False,
                warning_time_seconds=30,
                communications_status="Online",
                security_status="Healthy",
                last_updated=now,
            )
            db.add(crossing)
        else:
            crossing.controlling_device_id = crossing_controller.id
        seeded["crossings"].append(crossing)

    db.flush()
    return seeded
