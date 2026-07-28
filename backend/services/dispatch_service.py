import json
from datetime import timedelta, timezone

from models import DispatchCommand, OTDevice
from services.timeline_service import record_event, utc_now


DISPATCH_DEVICE_NAME = "Dispatch SCADA Server"
COMMAND_DELAYS = {
    "online": 0,
    "degraded": 15,
    "severe": 60,
    "offline": None,
}
AVAILABILITY = {
    "online": 100.0,
    "degraded": 60.0,
    "severe": 25.0,
    "offline": 0.0,
}


def get_dispatch_device(db):
    return db.query(OTDevice).filter(
        OTDevice.name == DISPATCH_DEVICE_NAME
    ).first()


def queue_dispatch_command(db, command_type, payload=None):
    device = get_dispatch_device(db)
    if device is None:
        raise RuntimeError(f"{DISPATCH_DEVICE_NAME} was not found.")

    now = utc_now()
    status = (device.status or "Online").strip().lower()
    delay = COMMAND_DELAYS.get(status, 15)
    command = DispatchCommand(
        device_id=device.id,
        command_type=command_type,
        payload_json=json.dumps(payload or {}, default=str),
        requested_at=now,
    )
    if delay == 0:
        command.status = "Applied"
        command.apply_after = now
        command.applied_at = now
    else:
        command.status = "Queued"
        command.apply_after = (
            now + timedelta(seconds=delay)
            if delay is not None
            else None
        )
    db.add(command)
    db.flush()
    record_event(
        db,
        event_type=(
            "dispatch_command_applied"
            if command.status == "Applied"
            else "dispatch_command_queued"
        ),
        title=f"Dispatch command {command.status.lower()}",
        message=(
            f"{command_type} was {command.status.lower()} while "
            f"{device.name} was {device.status}."
        ),
        asset_name=device.name,
        device_id=device.id,
        metadata=serialize_command(command),
    )
    return command


def process_dispatch_commands(db, restore=False):
    device = get_dispatch_device(db)
    if device is None:
        return []

    now = utc_now()
    status = (device.status or "Online").strip().lower()
    if status == "offline" and not restore:
        return []

    applied = []
    queued = db.query(DispatchCommand).filter(
        DispatchCommand.status == "Queued"
    ).order_by(DispatchCommand.requested_at).all()
    for command in queued:
        apply_after = command.apply_after
        if apply_after and apply_after.tzinfo is None:
            apply_after = apply_after.replace(tzinfo=timezone.utc)
        if not restore and (apply_after is None or apply_after > now):
            continue
        command.status = "Applied"
        command.applied_at = now
        applied.append(command)
        record_event(
            db,
            event_type="dispatch_command_applied",
            title="Queued dispatch command applied",
            message=(
                f"{command.command_type} was applied after "
                "dispatch communications became available."
            ),
            asset_name=device.name,
            device_id=device.id,
            metadata=serialize_command(command),
        )
    return applied


def get_dispatch_metrics(db):
    device = get_dispatch_device(db)
    status = (device.status if device else "Offline") or "Offline"
    normalized = status.strip().lower()
    commands = db.query(DispatchCommand).all()
    queued = [command for command in commands if command.status == "Queued"]
    applied_delays = []
    for command in commands:
        if not command.applied_at or not command.requested_at:
            continue
        applied_at = command.applied_at
        requested_at = command.requested_at
        if applied_at.tzinfo is None:
            applied_at = applied_at.replace(tzinfo=timezone.utc)
        if requested_at.tzinfo is None:
            requested_at = requested_at.replace(tzinfo=timezone.utc)
        applied_delays.append((applied_at - requested_at).total_seconds())
    return {
        "dispatch_status": status,
        "dispatch_availability_percent": AVAILABILITY.get(normalized, 50.0),
        "queued_commands": len(queued),
        "average_command_delay_seconds": round(
            sum(applied_delays) / len(applied_delays), 2
        ) if applied_delays else 0.0,
    }


def serialize_command(command):
    try:
        payload = json.loads(command.payload_json or "{}")
    except (TypeError, json.JSONDecodeError):
        payload = {}
    return {
        "id": command.id,
        "device_id": command.device_id,
        "command_type": command.command_type,
        "payload": payload,
        "status": command.status,
        "requested_at": (
            command.requested_at.isoformat()
            if command.requested_at else None
        ),
        "apply_after": (
            command.apply_after.isoformat()
            if command.apply_after else None
        ),
        "applied_at": (
            command.applied_at.isoformat()
            if command.applied_at else None
        ),
    }
