import json
from datetime import datetime, timezone

from models import ActivityLog


def utc_now():
    return datetime.now(timezone.utc)


def record_event(
    db,
    *,
    event_type,
    title,
    message,
    severity="Info",
    source="TrackSentinel",
    asset_name="",
    device_id=None,
    train_id=None,
    track_block_id=None,
    incident_id=None,
    scenario_id=None,
    metadata=None,
):
    event = ActivityLog(
        timestamp=utc_now(),
        event_type=event_type,
        title=title,
        description=message,
        severity=severity,
        source=source,
        asset_name=asset_name,
        status="Completed",
        device_id=device_id,
        train_id=train_id,
        track_block_id=track_block_id,
        incident_id=incident_id,
        scenario_id=scenario_id,
        metadata_json=json.dumps(metadata or {}, default=str),
    )
    db.add(event)
    db.flush()
    return event


def serialize_event(event):
    try:
        metadata = json.loads(event.metadata_json or "{}")
    except (TypeError, json.JSONDecodeError):
        metadata = {}

    timestamp = event.timestamp
    if timestamp and timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=timezone.utc)

    return {
        "id": event.id,
        "timestamp": timestamp.isoformat() if timestamp else None,
        "event_type": event.event_type,
        "title": event.title,
        "message": event.description,
        "severity": event.severity,
        "source": event.source,
        "asset_name": event.asset_name,
        "device_id": event.device_id,
        "train_id": event.train_id,
        "track_block_id": event.track_block_id,
        "incident_id": event.incident_id,
        "scenario_id": event.scenario_id,
        "metadata": metadata,
    }


def get_timeline(db, limit=100):
    safe_limit = max(1, min(int(limit), 500))
    events = (
        db.query(ActivityLog)
        .order_by(ActivityLog.timestamp.desc(), ActivityLog.id.desc())
        .limit(safe_limit)
        .all()
    )
    return [serialize_event(event) for event in events]
