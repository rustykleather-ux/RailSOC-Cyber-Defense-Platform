from datetime import timezone

from models import ActivityLog, GradeCrossing, TrackBlock, TrackSwitch, Train
from services.dispatch_service import get_dispatch_metrics
from services.timeline_service import utc_now


HEALTHY_COMMUNICATIONS = {"online", "normal", "healthy"}
HEALTHY_SECURITY = {"healthy", "normal", "low"}
SLOWED_STATUSES = {
    "approach",
    "braking for signal",
    "restricted",
    "restricted - ptc communications",
}
STOPPED_STATUSES = {"stopped at signal", "stopped at unsafe switch"}


def _normalized(value):
    return str(value or "").strip().lower()


def _event_timestamp(event):
    timestamp = event.timestamp
    if timestamp and timestamp.tzinfo is None:
        return timestamp.replace(tzinfo=timezone.utc)
    return timestamp


def get_delay_window(db):
    boundary = (
        db.query(ActivityLog)
        .filter(
            ActivityLog.event_type.in_(["demo_reset", "exercise_started"])
        )
        .order_by(ActivityLog.timestamp.desc(), ActivityLog.id.desc())
        .first()
    )
    return {
        "timestamp": _event_timestamp(boundary) if boundary else None,
        "event_type": boundary.event_type if boundary else "platform_history",
        "event_id": boundary.id if boundary else None,
    }


def calculate_cumulative_delay_minutes(db):
    window = get_delay_window(db)
    query = (
        db.query(ActivityLog)
        .filter(
            ActivityLog.event_type.in_(
                ["train_stopped_signal", "train_resumed"]
            )
        )
    )
    if window["timestamp"] is not None:
        query = query.filter(ActivityLog.timestamp >= window["timestamp"])
    events = query.order_by(ActivityLog.timestamp, ActivityLog.id).all()
    stopped_at = {}
    total_seconds = 0.0

    for event in events:
        if event.train_id is None:
            continue

        timestamp = _event_timestamp(event)
        if timestamp is None:
            continue

        if event.event_type == "train_stopped_signal":
            stopped_at.setdefault(event.train_id, timestamp)
        elif event.event_type == "train_resumed":
            start = stopped_at.pop(event.train_id, None)
            if start:
                total_seconds += max(
                    0.0,
                    (timestamp - start).total_seconds(),
                )

    now = utc_now()
    active_stopped_ids = {
        train.id
        for train in db.query(Train).all()
        if _normalized(train.status) in STOPPED_STATUSES
    }
    for train_id in active_stopped_ids:
        if train_id not in stopped_at:
            stopped_at[train_id] = window["timestamp"] or now
    for start in stopped_at.values():
        total_seconds += max(0.0, (now - start).total_seconds())

    return round(total_seconds / 60.0, 2)


def get_operational_impact(db):
    blocks = db.query(TrackBlock).all()
    trains = db.query(Train).all()
    switches = db.query(TrackSwitch).all()
    crossings = db.query(GradeCrossing).all()

    affected_blocks = [
        block
        for block in blocks
        if (
            _normalized(block.communications_status)
            not in HEALTHY_COMMUNICATIONS
            or _normalized(block.security_status) not in HEALTHY_SECURITY
            or bool(block.maintenance)
        )
    ]
    stopped_trains = [
        train
        for train in trains
        if _normalized(train.status) in STOPPED_STATUSES
    ]
    slowed_trains = [
        train
        for train in trains
        if (
            _normalized(train.status) in SLOWED_STATUSES
            and int(train.speed or 0) > 0
        )
    ]
    delayed_ids = {
        train.id for train in stopped_trains + slowed_trains
    }
    total_miles = sum(
        max(0.0, float(block.end_milepost) - float(block.start_milepost))
        for block in blocks
    )
    blocked_miles = sum(
        max(0.0, float(block.end_milepost) - float(block.start_milepost))
        for block in affected_blocks
    )
    availability = (
        100.0
        if total_miles == 0
        else max(0.0, (total_miles - blocked_miles) / total_miles * 100)
    )

    unsafe_switches = [
        track_switch
        for track_switch in switches
        if (
            track_switch.locked
            or track_switch.position != track_switch.commanded_position
            or _normalized(track_switch.security_status) != "healthy"
        )
    ]
    affected_crossings = [
        crossing
        for crossing in crossings
        if (
            _normalized(crossing.communications_status)
            not in HEALTHY_COMMUNICATIONS
            or _normalized(crossing.security_status) not in HEALTHY_SECURITY
            or _normalized(crossing.gate_state) == "unavailable"
        )
    ]
    dispatch_metrics = get_dispatch_metrics(db)
    delay_window = get_delay_window(db)

    return {
        "affected_blocks": len(affected_blocks),
        "affected_block_names": [block.name for block in affected_blocks],
        "stopped_trains": len(stopped_trains),
        "stopped_train_symbols": [
            train.symbol for train in stopped_trains
        ],
        "slowed_trains": len(slowed_trains),
        "slowed_train_symbols": [
            train.symbol for train in slowed_trains
        ],
        "delayed_trains": len(delayed_ids),
        "cumulative_delay_minutes": calculate_cumulative_delay_minutes(db),
        "delay_window_started_at": (
            delay_window["timestamp"].isoformat()
            if delay_window["timestamp"] else None
        ),
        "delay_window_reason": delay_window["event_type"],
        "blocked_track_miles": round(blocked_miles, 2),
        "track_availability_percent": round(availability, 1),
        "estimated_recovery": (
            "Awaiting operational-system restoration"
            if affected_blocks or unsafe_switches or affected_crossings
            else "Operational baseline restored"
        ),
        "unsafe_switches": len(unsafe_switches),
        "unsafe_switch_names": [
            track_switch.name for track_switch in unsafe_switches
        ],
        "affected_crossings": len(affected_crossings),
        "affected_crossing_names": [
            crossing.name for crossing in affected_crossings
        ],
        "ptc_restricted_trains": len(
            [
                train
                for train in trains
                if _normalized(train.status)
                == "restricted - ptc communications"
            ]
        ),
        **dispatch_metrics,
        "train_details": [
            {
                "id": train.id,
                "symbol": train.symbol,
                "milepost": train.milepost,
                "speed": train.speed,
                "status": train.status,
                "current_signal": train.current_signal,
            }
            for train in stopped_trains + slowed_trains
        ],
        "block_details": [
            {
                "id": block.id,
                "name": block.name,
                "signal_aspect": block.signal_aspect,
                "communications_status": block.communications_status,
                "security_status": block.security_status,
                "controlling_device_id": block.controlling_device_id,
            }
            for block in affected_blocks
        ],
        "switch_details": [
            {
                "id": track_switch.id,
                "name": track_switch.name,
                "milepost": track_switch.milepost,
                "position": track_switch.position,
                "commanded_position": track_switch.commanded_position,
                "locked": track_switch.locked,
                "communications_status": track_switch.communications_status,
                "security_status": track_switch.security_status,
            }
            for track_switch in unsafe_switches
        ],
        "crossing_details": [
            {
                "id": crossing.id,
                "name": crossing.name,
                "milepost": crossing.milepost,
                "gate_state": crossing.gate_state,
                "lights_active": crossing.lights_active,
                "communications_status": crossing.communications_status,
                "security_status": crossing.security_status,
            }
            for crossing in affected_crossings
        ],
    }


def build_operational_summary(impact):
    if not any(
        [
            impact["affected_blocks"],
            impact["delayed_trains"],
            impact.get("unsafe_switches", 0),
            impact.get("affected_crossings", 0),
            impact.get("queued_commands", 0),
            impact.get("ptc_restricted_trains", 0),
            impact.get("dispatch_availability_percent", 100) < 100,
        ]
    ):
        return "Railroad operations are at the normal service baseline."

    block_names = ", ".join(impact["affected_block_names"]) or "No blocks"
    train_details = impact.get("train_details", [])
    block_details = impact.get("block_details", [])
    train_text = "; ".join(
        (
            f"{train['symbol']} at MP {float(train['milepost']):.2f} "
            f"({train['status']}, {train['speed']} mph)"
        )
        for train in train_details
        if train.get("milepost") is not None
    )
    summary = (
        f"{impact['affected_blocks']} track blocks are operationally "
        f"affected: {block_names}. "
        f"Blocked track mileage is {impact['blocked_track_miles']:.1f} miles "
        f"and track availability is "
        f"{impact['track_availability_percent']:.1f}%. "
        f"Cumulative delay is "
        f"{impact['cumulative_delay_minutes']:.2f} minutes."
    )
    if train_text:
        summary += f" Train impact: {train_text}."
    if block_details:
        block_states = "; ".join(
            (
                f"{block['name']} communications "
                f"{block['communications_status']}, security "
                f"{block['security_status']}"
            )
            for block in block_details
        )
        summary += f" Block state: {block_states}."
    if impact.get("unsafe_switch_names"):
        summary += (
            " Unsafe switches: "
            + ", ".join(impact["unsafe_switch_names"])
            + "."
        )
    if impact.get("affected_crossing_names"):
        summary += (
            " Affected crossings: "
            + ", ".join(impact["affected_crossing_names"])
            + "."
        )
    if impact.get("ptc_restricted_trains"):
        summary += (
            f" {impact['ptc_restricted_trains']} train(s) are operating "
            "under PTC communications restriction."
        )
    summary += (
        f" Dispatch availability is "
        f"{impact.get('dispatch_availability_percent', 100):.1f}% "
        f"with {impact.get('queued_commands', 0)} queued command(s)."
    )
    summary += f" Recovery status: {impact['estimated_recovery']}."
    return summary
