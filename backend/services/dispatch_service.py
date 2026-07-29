import json
import os
from datetime import timedelta, timezone

from models import (
    DispatchCommand,
    DispatchRoute,
    GradeCrossing,
    Incident,
    OperationalRestriction,
    OTDevice,
    TrackBlock,
    TrackSwitch,
    Train,
)
from services.timeline_service import record_event, utc_now


DISPATCH_DEVICE_NAME = "Dispatch SCADA Server"
COMMAND_TYPES = {
    "SET_SIGNAL",
    "MOVE_SWITCH",
    "HOLD_TRAIN",
    "RELEASE_TRAIN",
    "APPLY_SPEED_RESTRICTION",
    "REMOVE_SPEED_RESTRICTION",
    "ACTIVATE_CROSSING_SAFE_MODE",
    "RESTORE_DEVICE",
    "ISOLATE_DEVICE",
    "TRANSFER_TO_BACKUP",
}
COMMAND_STATUSES = {
    "Pending", "Queued", "Executing", "Completed", "Failed", "Cancelled", "Blocked"
}
TARGET_MODELS = {
    "TRACK_BLOCK": TrackBlock,
    "TRACK_SWITCH": TrackSwitch,
    "TRAIN": Train,
    "GRADE_CROSSING": GradeCrossing,
    "OT_DEVICE": OTDevice,
}
VALID_STATES = {
    "SET_SIGNAL": {"Clear", "Approach", "Stop"},
    "MOVE_SWITCH": {"Normal", "Reverse"},
    "HOLD_TRAIN": {"Held"},
    "RELEASE_TRAIN": {"Released"},
    "APPLY_SPEED_RESTRICTION": set(),
    "REMOVE_SPEED_RESTRICTION": {"Removed"},
    "ACTIVATE_CROSSING_SAFE_MODE": {"Safe"},
    "RESTORE_DEVICE": {"Online"},
    "ISOLATE_DEVICE": {"Isolated"},
    "TRANSFER_TO_BACKUP": {"Backup"},
}
RESTRICTION_TYPES = {
    "HOLD_TRAIN",
    "BLOCK_TRACK",
    "SPEED_RESTRICTION",
    "SWITCH_OUT_OF_SERVICE",
    "CROSSING_OUT_OF_SERVICE",
    "LOCAL_CONTROL_REQUIRED",
    "PTC_RESTRICTED_OPERATION",
}
PRIORITY_ORDER = {"Safety": 0, "High": 1, "Normal": 2, "Low": 3}
SAFETY_COMMANDS = {
    "HOLD_TRAIN", "ACTIVATE_CROSSING_SAFE_MODE", "ISOLATE_DEVICE"
}
COMMAND_DELAYS = {
    "online": 0,
    "degraded": int(os.getenv("TRACKSENTINEL_DISPATCH_DELAY_SECONDS", "15")),
    "severe": None,
    "offline": None,
    "compromised": None,
}
AVAILABILITY = {
    "online": 100.0, "degraded": 60.0, "severe": 25.0,
    "offline": 0.0, "compromised": 0.0,
}


class DispatchValidationError(RuntimeError):
    def __init__(self, message, status_code=409):
        super().__init__(message)
        self.status_code = status_code


def _loads(value, default):
    try:
        return json.loads(value or "")
    except (TypeError, json.JSONDecodeError):
        return default


def _norm(value):
    return str(value or "").strip().lower()


def get_dispatch_device(db):
    return db.query(OTDevice).filter(OTDevice.name == DISPATCH_DEVICE_NAME).first()


def _target(db, target_type, target_id):
    model = TARGET_MODELS.get(str(target_type or "").upper())
    if model is None:
        raise DispatchValidationError("Unsupported dispatch target type.", 400)
    target = db.query(model).filter(model.id == target_id).first()
    if target is None:
        raise DispatchValidationError("Dispatch target was not found.", 404)
    return target


def _active_restrictions(db, target_type=None, target_id=None):
    query = db.query(OperationalRestriction).filter(
        OperationalRestriction.active.is_(True)
    )
    if target_type:
        query = query.filter(OperationalRestriction.target_type == target_type)
    if target_id is not None:
        query = query.filter(OperationalRestriction.target_id == target_id)
    return query.all()


def _validate_requested_state(command_type, requested_state, payload):
    if command_type == "APPLY_SPEED_RESTRICTION":
        try:
            speed = int(payload.get("speed_mph", requested_state))
        except (TypeError, ValueError):
            raise DispatchValidationError("Speed restriction must be a whole mph value.", 400)
        if speed < 1 or speed > 79:
            raise DispatchValidationError("Speed restriction must be between 1 and 79 mph.", 400)
        return str(speed)
    allowed = VALID_STATES[command_type]
    canonical = next(
        (item for item in allowed if _norm(item) == _norm(requested_state)), None
    )
    if canonical is None:
        raise DispatchValidationError(
            f"Requested state is invalid for {command_type}.", 400
        )
    return canonical


def _validate_safety(db, command_type, target, requested_state):
    if command_type == "SET_SIGNAL" and requested_state == "Clear":
        if target.occupied:
            raise DispatchValidationError(
                f"{target.name} is occupied; its entrance signal cannot be cleared."
            )
        if target.maintenance:
            raise DispatchValidationError(
                f"{target.name} is under maintenance and cannot be cleared."
            )
        unsafe_switch = db.query(TrackSwitch).filter(
            TrackSwitch.track_block_id == target.id
        ).filter(
            (TrackSwitch.locked.is_(True))
            | (TrackSwitch.position != TrackSwitch.commanded_position)
        ).first()
        if unsafe_switch:
            raise DispatchValidationError(
                f"{unsafe_switch.name} is locked or misaligned; signal remains Stop."
            )
        if _norm(target.communications_status) not in {"online", "normal", "healthy"}:
            raise DispatchValidationError(
                f"{target.name} communications are unavailable."
            )
        if _norm(target.security_status) == "compromised":
            raise DispatchValidationError(
                f"{target.name} is controlled by an untrusted device; recover or transfer dispatch first."
            )
    elif command_type == "MOVE_SWITCH":
        if target.locked:
            raise DispatchValidationError(f"{target.name} is locked.")
        if _norm(target.communications_status) not in {"online", "normal", "healthy"}:
            raise DispatchValidationError(f"{target.name} communications have failed.")
        if target.track_block and target.track_block.occupied:
            raise DispatchValidationError(
                f"{target.name} cannot move beneath an occupying train."
            )
        if _norm(target.security_status) == "compromised":
            raise DispatchValidationError(f"{target.name} command integrity is untrusted.")
    elif command_type == "RELEASE_TRAIN":
        blocks = db.query(TrackBlock).filter(
            TrackBlock.subdivision == target.subdivision,
            TrackBlock.track == target.track,
        ).order_by(TrackBlock.start_milepost).all()
        ahead = next(
            (b for b in blocks if float(b.start_milepost) > float(target.milepost)), None
        )
        if ahead and _norm(ahead.signal_aspect) == "stop":
            raise DispatchValidationError(
                f"{target.symbol} cannot be released into Stop at {ahead.name}."
            )
    elif command_type == "REMOVE_SPEED_RESTRICTION":
        if (not target.ptc_enabled) or "ptc" in _norm(target.status):
            raise DispatchValidationError(
                f"{target.symbol} still requires restricted operation because of PTC state."
            )


def _apply_command(db, command):
    target = _target(db, command.target_type, command.target_id)
    payload = _loads(command.payload_json, {})
    state = _validate_requested_state(
        command.command_type, command.requested_state, payload
    )
    _validate_safety(db, command.command_type, target, state)
    kind = command.command_type
    if kind == "SET_SIGNAL":
        target.signal_aspect = state
    elif kind == "MOVE_SWITCH":
        target.commanded_position = state
        target.position = state
    elif kind == "HOLD_TRAIN":
        target.status, target.speed = "Held by Dispatcher", 0
    elif kind == "RELEASE_TRAIN":
        target.status = "Moving"
    elif kind == "APPLY_SPEED_RESTRICTION":
        target.speed = min(int(target.speed or 0), int(state))
        target.status = "Restricted"
        create_restriction(db, {
            "restriction_type": "SPEED_RESTRICTION",
            "target_type": "TRAIN", "target_id": target.id,
            "reason": payload.get("reason", "Dispatcher speed restriction"),
            "severity": payload.get("severity", "Medium"),
            "created_by": command.requested_by,
            "metadata": {"speed_mph": int(state), "command_id": command.id},
        }, record=False)
    elif kind == "REMOVE_SPEED_RESTRICTION":
        for restriction in _active_restrictions(db, "TRAIN", target.id):
            if restriction.restriction_type == "SPEED_RESTRICTION":
                restriction.active, restriction.cleared_at = False, utc_now()
        target.status = "Moving"
    elif kind == "ACTIVATE_CROSSING_SAFE_MODE":
        target.gate_state, target.lights_active = "Lowered", True
    elif kind == "ISOLATE_DEVICE":
        target.status, target.risk_level = "Isolated", "High"
    elif kind == "RESTORE_DEVICE":
        _restore_device(db, target)
    elif kind == "TRANSFER_TO_BACKUP":
        target.status = "Online"
        metadata = _loads(target.metadata_json, {})
        metadata["dispatch_mode"] = "Backup"
        target.metadata_json = json.dumps(metadata)
    command.status = "Completed"
    command.executed_at = command.applied_at = utc_now()
    command.delay_seconds = max(
        0, int((command.executed_at - _aware(command.requested_at)).total_seconds())
    )
    record_event(
        db, event_type="dispatch_command_executed",
        title=f"{kind.replace('_', ' ').title()} completed",
        message=f"Command {command.id} completed for {getattr(target, 'name', getattr(target, 'symbol', command.target_id))}.",
        train_id=target.id if isinstance(target, Train) else None,
        track_block_id=target.id if isinstance(target, TrackBlock) else None,
        device_id=target.id if isinstance(target, OTDevice) else None,
        incident_id=command.incident_id, metadata=serialize_command(command),
    )
    return command


def _aware(value):
    if value and value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def create_dispatch_command(db, data):
    command_type = str(data.get("command_type", "")).upper()
    if command_type not in COMMAND_TYPES:
        raise DispatchValidationError("Unsupported dispatch command type.", 400)
    target_type = str(data.get("target_type", "")).upper()
    target = _target(db, target_type, data.get("target_id"))
    payload = data.get("payload") or {}
    requested_state = _validate_requested_state(
        command_type, data.get("requested_state", ""), payload
    )
    _validate_safety(db, command_type, target, requested_state)
    device = get_dispatch_device(db)
    if device is None:
        raise DispatchValidationError("Dispatch SCADA was not found.", 404)
    now = utc_now()
    status = _norm(device.status)
    priority = str(data.get("priority", "Normal")).title()
    if priority not in PRIORITY_ORDER:
        raise DispatchValidationError("Priority must be Safety, High, Normal, or Low.", 400)
    command = DispatchCommand(
        device_id=device.id, command_type=command_type, target_type=target_type,
        target_id=target.id, requested_state=requested_state,
        requested_by=data.get("requested_by") or "Dispatcher",
        requested_at=now, priority=priority, payload_json=json.dumps(payload),
        metadata_json=json.dumps(data.get("metadata") or {}),
        incident_id=data.get("incident_id"), scenario_id=data.get("scenario_id"),
        status="Pending",
    )
    db.add(command)
    db.flush()
    record_event(
        db, event_type="dispatch_command_requested",
        title="Dispatcher command requested",
        message=f"{command_type} requested for {getattr(target, 'name', getattr(target, 'symbol', target.id))}.",
        incident_id=command.incident_id, metadata=serialize_command(command),
    )
    immediate = status == "online" or (
        status == "severe" and priority in {"Safety", "High"}
        and command_type in SAFETY_COMMANDS
    )
    if status == "compromised":
        command.status = "Blocked"
        command.failure_reason = "Dispatch command integrity is untrusted; recover or transfer to backup."
        record_event(db, event_type="dispatch_command_blocked", title="Command blocked",
                     message=command.failure_reason, severity="High",
                     metadata=serialize_command(command))
    elif immediate:
        command.status = "Executing"
        _apply_command(db, command)
    else:
        command.status = "Queued"
        command.queued_at = now
        delay = COMMAND_DELAYS.get(status)
        command.apply_after = now + timedelta(seconds=delay) if delay is not None else None
        command.delay_seconds = delay or 0
        record_event(db, event_type="dispatch_command_queued", title="Command queued",
                     message=f"{command_type} queued while Dispatch SCADA is {device.status}.",
                     severity="Medium", metadata=serialize_command(command))
    return command


def queue_dispatch_command(db, command_type, payload=None):
    """Legacy queue API retained for existing scenarios and tests."""
    device = get_dispatch_device(db)
    if device is None:
        raise RuntimeError(f"{DISPATCH_DEVICE_NAME} was not found.")
    now, status = utc_now(), _norm(device.status)
    delay = {"online": 0, "degraded": 15, "severe": 60, "offline": None}.get(status, 15)
    command = DispatchCommand(
        device_id=device.id, command_type=command_type,
        target_type="OT_DEVICE", target_id=device.id,
        payload_json=json.dumps(payload or {}, default=str), requested_at=now,
    )
    if delay == 0:
        command.status, command.apply_after, command.applied_at = "Applied", now, now
    else:
        command.status, command.queued_at = "Queued", now
        command.apply_after = now + timedelta(seconds=delay) if delay is not None else None
    db.add(command)
    db.flush()
    record_event(db, event_type="dispatch_command_applied" if command.status == "Applied" else "dispatch_command_queued",
                 title=f"Dispatch command {command.status.lower()}",
                 message=f"{command_type} was {command.status.lower()} while {device.name} was {device.status}.",
                 asset_name=device.name, device_id=device.id, metadata=serialize_command(command))
    return command


def process_dispatch_commands(db, restore=False):
    device = get_dispatch_device(db)
    if device is None:
        return []
    now, status = utc_now(), _norm(device.status)
    if status in {"offline", "compromised"} and not restore:
        return []
    queued = db.query(DispatchCommand).filter(
        DispatchCommand.status == "Queued"
    ).all()
    queued.sort(key=lambda c: (
        PRIORITY_ORDER.get(c.priority or "Normal", 2),
        c.requested_at or now, c.id,
    ))
    processed = []
    for command in queued:
        due = _aware(command.apply_after)
        if not restore and (due is None or due > now):
            continue
        if command.command_type not in COMMAND_TYPES or command.target_id is None:
            command.status, command.applied_at = "Applied", now
            processed.append(command)
            continue
        try:
            command.status = "Executing"
            _apply_command(db, command)
        except DispatchValidationError as exc:
            command.status, command.failed_at = "Failed", now
            command.failure_reason = str(exc)
            record_event(db, event_type="dispatch_command_failed", title="Queued command failed revalidation",
                         message=str(exc), severity="High", metadata=serialize_command(command))
        processed.append(command)
    return processed


def cancel_command(db, command_id, requested_by="Dispatcher"):
    command = db.query(DispatchCommand).filter(DispatchCommand.id == command_id).first()
    if not command:
        raise DispatchValidationError("Dispatch command was not found.", 404)
    if command.status not in {"Pending", "Queued", "Blocked", "Failed"}:
        raise DispatchValidationError("Only pending, queued, blocked, or failed commands can be cancelled.")
    command.status, command.cancelled_at = "Cancelled", utc_now()
    record_event(db, event_type="dispatch_command_cancelled", title="Command cancelled",
                 message=f"Command {command.id} was cancelled by {requested_by}.",
                 metadata=serialize_command(command))
    return command


def retry_command(db, command_id, requested_by="Dispatcher"):
    old = db.query(DispatchCommand).filter(DispatchCommand.id == command_id).first()
    if not old:
        raise DispatchValidationError("Dispatch command was not found.", 404)
    if old.status not in {"Failed", "Blocked", "Cancelled"}:
        raise DispatchValidationError("Only failed, blocked, or cancelled commands can be retried.")
    data = {
        "command_type": old.command_type, "target_type": old.target_type,
        "target_id": old.target_id, "requested_state": old.requested_state,
        "requested_by": requested_by, "priority": old.priority,
        "payload": _loads(old.payload_json, {}), "metadata": {"retry_of_id": old.id},
        "incident_id": old.incident_id, "scenario_id": old.scenario_id,
    }
    command = create_dispatch_command(db, data)
    command.retry_of_id = old.id
    return command


def create_route(db, data):
    train = _target(db, "TRAIN", data.get("train_id"))
    start = _target(db, "TRACK_BLOCK", data.get("start_block_id"))
    destination = _target(db, "TRACK_BLOCK", data.get("destination_block_id"))
    route = DispatchRoute(
        train_id=train.id, start_block_id=start.id, destination_block_id=destination.id,
        requested_by=data.get("requested_by") or "Dispatcher",
        requested_path_json=json.dumps(data.get("requested_path") or []),
        status="Validating",
    )
    db.add(route)
    db.flush()
    blocks = db.query(TrackBlock).filter(
        TrackBlock.subdivision == start.subdivision,
        TrackBlock.track == start.track,
    ).order_by(TrackBlock.start_milepost).all()
    ids = [b.id for b in blocks]
    if start.id not in ids or destination.id not in ids:
        reason = "Route blocks must be on the same subdivision and track."
        path = []
    else:
        a, b = ids.index(start.id), ids.index(destination.id)
        path = blocks[min(a, b):max(a, b) + 1]
        reason = ""
    requested_ids = data.get("requested_path") or [b.id for b in path]
    if [b.id for b in path] != requested_ids:
        reason = "Requested path must contain adjacent blocks in territory order."
    unsafe = next((b for b in path if b.occupied and b.occupied_train_id != train.id), None)
    unsafe = unsafe or next((b for b in path if b.maintenance), None)
    if unsafe:
        reason = f"{unsafe.name} is occupied or under maintenance."
    for switch in db.query(TrackSwitch).filter(
        TrackSwitch.track_block_id.in_([b.id for b in path] or [-1])
    ):
        if switch.locked or switch.position != switch.commanded_position:
            reason = f"{switch.name} is locked or misaligned."
            break
    if any(r.restriction_type == "BLOCK_TRACK" for b in path for r in _active_restrictions(db, "TRACK_BLOCK", b.id)):
        reason = "The requested path contains a blocked-track restriction."
    route.requested_path_json = json.dumps([b.id for b in path])
    if reason:
        route.status, route.blocking_reason = "Blocked", reason
        event_type = "dispatch_route_blocked"
    else:
        route.status, route.established_at = "Established", utc_now()
        signal_blocks = path[1:] if len(path) > 1 else path
        route.required_signal_states_json = json.dumps(
            {str(b.id): "Clear" for b in signal_blocks}
        )
        for block in signal_blocks:
            _validate_safety(db, "SET_SIGNAL", block, "Clear")
            block.signal_aspect = "Clear"
        event_type = "dispatch_route_established"
    record_event(db, event_type=event_type, title=f"Route {route.status.lower()}",
                 message=reason or f"Route established for {train.symbol}.",
                 train_id=train.id, metadata=serialize_route(route))
    return route


def release_cleared_routes(db):
    released = []
    for route in db.query(DispatchRoute).filter(
        DispatchRoute.status.in_(["Established", "Occupied"])
    ):
        destination = route.destination_block
        if route.status == "Established" and any(
            b.occupied_train_id == route.train_id
            for b in (route.start_block, route.destination_block)
        ):
            route.status = "Occupied"
        if route.status == "Occupied" and (
            not destination.occupied or destination.occupied_train_id != route.train_id
        ):
            route.status, route.released_at = "Released", utc_now()
            released.append(route)
    return released


def create_restriction(db, data, record=True):
    kind = str(data.get("restriction_type", "")).upper()
    if kind not in RESTRICTION_TYPES:
        raise DispatchValidationError("Unsupported operational restriction type.", 400)
    target_type = str(data.get("target_type", "")).upper()
    target = _target(db, target_type, data.get("target_id"))
    restriction = OperationalRestriction(
        restriction_type=kind, target_type=target_type, target_id=target.id,
        reason=str(data.get("reason") or "").strip(),
        severity=str(data.get("severity") or "Medium").title(),
        created_by=data.get("created_by") or "Dispatcher",
        incident_id=data.get("incident_id"),
        metadata_json=json.dumps(data.get("metadata") or {}),
    )
    if not restriction.reason:
        raise DispatchValidationError("Restriction reason is required.", 400)
    db.add(restriction)
    db.flush()
    if kind == "HOLD_TRAIN" and isinstance(target, Train):
        target.status, target.speed = "Held by Dispatcher", 0
    elif kind == "BLOCK_TRACK" and isinstance(target, TrackBlock):
        target.signal_aspect = "Stop"
    elif kind == "SWITCH_OUT_OF_SERVICE" and isinstance(target, TrackSwitch):
        target.locked = True
    if record:
        record_event(db, event_type="operational_restriction_applied",
                     title="Operational restriction applied",
                     message=f"{kind.replace('_', ' ').title()}: {restriction.reason}",
                     incident_id=restriction.incident_id, metadata=serialize_restriction(restriction))
    return restriction


def clear_restriction(db, restriction_id, cleared_by="Dispatcher"):
    item = db.query(OperationalRestriction).filter(
        OperationalRestriction.id == restriction_id
    ).first()
    if not item:
        raise DispatchValidationError("Operational restriction was not found.", 404)
    if not item.active:
        raise DispatchValidationError("Operational restriction is already cleared.")
    item.active, item.cleared_by, item.cleared_at = False, cleared_by, utc_now()
    target = _target(db, item.target_type, item.target_id)
    if item.restriction_type == "HOLD_TRAIN" and isinstance(target, Train):
        if target.status == "Held by Dispatcher":
            target.status = "Moving"
    elif (
        item.restriction_type == "SWITCH_OUT_OF_SERVICE"
        and isinstance(target, TrackSwitch)
    ):
        target.locked = False
    record_event(db, event_type="operational_restriction_cleared",
                 title="Operational restriction cleared",
                 message=f"{item.restriction_type.replace('_', ' ').title()} cleared by {cleared_by}.",
                 incident_id=item.incident_id, metadata=serialize_restriction(item))
    return item


def _restore_device(db, device):
    device.status, device.risk_level = "Online", "Low"
    for block in db.query(TrackBlock).filter(TrackBlock.controlling_device_id == device.id):
        block.communications_status, block.security_status = "Online", "Healthy"
    for switch in db.query(TrackSwitch).filter(TrackSwitch.controlling_device_id == device.id):
        switch.communications_status, switch.security_status = "Online", "Healthy"
        switch.locked, switch.commanded_position = False, switch.position
    for crossing in db.query(GradeCrossing).filter(GradeCrossing.controlling_device_id == device.id):
        crossing.communications_status, crossing.security_status = "Online", "Healthy"


def perform_recovery_action(db, data):
    action = str(data.get("action_type", "")).upper()
    allowed = {
        "ISOLATE_DEVICE", "RESTORE_COMMUNICATIONS", "RESTORE_KNOWN_GOOD",
        "TRANSFER_TO_BACKUP", "PLACE_IN_SAFE_MODE", "REVOKE_REMOTE_ACCESS",
        "CLEAR_ATTACK_EFFECT",
    }
    if action not in allowed:
        raise DispatchValidationError("Unsupported recovery action.", 400)
    device = _target(db, "OT_DEVICE", data.get("target_id"))
    record_event(db, event_type="dispatch_recovery_started", title="Recovery action started",
                 message=f"{action.replace('_', ' ').title()} started for {device.name}.",
                 device_id=device.id, incident_id=data.get("incident_id"))
    if action == "ISOLATE_DEVICE":
        device.status, device.risk_level = "Isolated", "High"
    elif action in {"RESTORE_COMMUNICATIONS", "RESTORE_KNOWN_GOOD", "CLEAR_ATTACK_EFFECT"}:
        _restore_device(db, device)
    elif action == "TRANSFER_TO_BACKUP":
        _restore_device(db, device)
        metadata = _loads(device.metadata_json, {})
        metadata["dispatch_mode"] = "Backup"
        device.metadata_json = json.dumps(metadata)
        process_dispatch_commands(db, restore=True)
    elif action == "PLACE_IN_SAFE_MODE":
        device.status = "Safe Mode"
    elif action == "REVOKE_REMOTE_ACCESS":
        metadata = _loads(device.metadata_json, {})
        metadata["remote_access"] = "Revoked"
        device.metadata_json = json.dumps(metadata)
    incident_id = data.get("incident_id")
    if incident_id:
        incident = db.query(Incident).filter(Incident.id == incident_id).first()
        if incident:
            incident.investigation_notes = (
                (incident.investigation_notes or "") +
                f"\nRecovery action completed: {action}."
            ).strip()
    record_event(db, event_type="dispatch_recovery_completed",
                 title="Recovery action completed",
                 message=f"{action.replace('_', ' ').title()} completed for {device.name}.",
                 device_id=device.id, incident_id=incident_id,
                 metadata={"action_type": action, "target_id": device.id})
    return {"action_type": action, "target_id": device.id, "status": "Completed"}


def get_dispatch_metrics(db):
    device = get_dispatch_device(db)
    status = (device.status if device else "Offline") or "Offline"
    commands = db.query(DispatchCommand).all()
    queued = [c for c in commands if c.status == "Queued"]
    delays = [
        max(0, (_aware(c.executed_at or c.applied_at) - _aware(c.requested_at)).total_seconds())
        for c in commands if (c.executed_at or c.applied_at) and c.requested_at
    ]
    oldest = min((_aware(c.requested_at) for c in queued), default=None)
    metadata = _loads(device.metadata_json, {}) if device else {}
    return {
        "dispatch_status": status,
        "scada_state": status,
        "dispatch_availability_percent": AVAILABILITY.get(_norm(status), 50.0),
        "queued_commands": len(queued),
        "command_queue_depth": len(queued),
        "average_command_delay_seconds": round(sum(delays) / len(delays), 2) if delays else 0.0,
        "oldest_queued_command": oldest.isoformat() if oldest else None,
        "failed_commands": sum(c.status == "Failed" for c in commands),
        "blocked_commands": sum(c.status == "Blocked" for c in commands),
        "pending_commands": sum(c.status == "Pending" for c in commands),
        "backup_status": metadata.get("dispatch_mode", "Primary"),
    }


def get_dispatch_status(db):
    metrics = get_dispatch_metrics(db)
    trains = db.query(Train).all()
    restrictions = _active_restrictions(db)
    routes = db.query(DispatchRoute).all()
    incidents = db.query(Incident).filter(Incident.status != "Closed").count()
    delayed = sum(_norm(t.status) not in {"moving", "arrived"} for t in trains)
    score = incidents * 3 + metrics["queued_commands"] * 2 + delayed * 2 + len(restrictions)
    metrics.update({
        "active_trains": sum(_norm(t.status) != "arrived" for t in trains),
        "delayed_trains": delayed,
        "active_restrictions": len(restrictions),
        "established_routes": sum(r.status == "Established" for r in routes),
        "dispatcher_workload_level": "High" if score >= 12 else "Elevated" if score >= 6 else "Normal",
        "workload_score": score,
        "workload_method": "Training score: incidents×3 + queued commands×2 + delayed trains×2 + active restrictions.",
    })
    return metrics


def serialize_command(command):
    return {
        "id": command.id, "device_id": command.device_id,
        "command_type": command.command_type, "target_type": command.target_type,
        "target_id": command.target_id, "requested_state": command.requested_state,
        "requested_by": command.requested_by, "priority": command.priority,
        "payload": _loads(command.payload_json, {}),
        "metadata": _loads(command.metadata_json, {}),
        "status": command.status, "failure_reason": command.failure_reason,
        "delay_seconds": command.delay_seconds,
        **{name: getattr(command, name).isoformat() if getattr(command, name) else None
           for name in ["requested_at", "queued_at", "executed_at", "failed_at",
                        "cancelled_at", "apply_after", "applied_at"]},
        "incident_id": command.incident_id, "scenario_id": command.scenario_id,
        "retry_of_id": command.retry_of_id,
    }


def serialize_route(route):
    return {
        "id": route.id, "train_id": route.train_id,
        "train": route.train.symbol if route.train else None,
        "start_block_id": route.start_block_id,
        "destination_block_id": route.destination_block_id,
        "requested_path": _loads(route.requested_path_json, []),
        "required_signal_states": _loads(route.required_signal_states_json, {}),
        "required_switch_positions": _loads(route.required_switch_positions_json, {}),
        "status": route.status, "blocking_reason": route.blocking_reason,
        "requested_by": route.requested_by,
        "requested_at": route.requested_at.isoformat() if route.requested_at else None,
        "established_at": route.established_at.isoformat() if route.established_at else None,
        "released_at": route.released_at.isoformat() if route.released_at else None,
    }


def serialize_restriction(item):
    return {
        "id": item.id, "restriction_type": item.restriction_type,
        "target_type": item.target_type, "target_id": item.target_id,
        "reason": item.reason, "severity": item.severity, "active": item.active,
        "created_by": item.created_by,
        "created_at": item.created_at.isoformat() if item.created_at else None,
        "cleared_by": item.cleared_by,
        "cleared_at": item.cleared_at.isoformat() if item.cleared_at else None,
        "incident_id": item.incident_id, "metadata": _loads(item.metadata_json, {}),
    }
