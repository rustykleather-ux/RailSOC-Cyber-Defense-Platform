from datetime import datetime, timezone

from models import GradeCrossing, TrackBlock, TrackSwitch, Train
from services.timeline_service import record_event


SIGNAL_CONTROLLER_EFFECTS = {
    "signal_controller_compromise",
    "controller_logic_compromise",
}
SIGNAL_LOGIC_ATTACK_IDS = {"logic_modification"}


class DigitalTwinConflictError(RuntimeError):
    """Raised when an attack cannot be applied to the digital twin."""


def is_signal_logic_modification(attack, target):
    if (target.device_type or "").strip().lower() != "signal controller":
        return False

    configured_effect = attack.get("digital_twin_effect")
    attack_id = (attack.get("attack_id") or "").strip().lower()

    return (
        configured_effect in SIGNAL_CONTROLLER_EFFECTS
        or attack_id in SIGNAL_LOGIC_ATTACK_IDS
    )


def apply_signal_controller_effect(db, device):
    affected_blocks = (
        db.query(TrackBlock)
        .filter(TrackBlock.controlling_device_id == device.id)
        .order_by(TrackBlock.start_milepost)
        .all()
    )

    if not affected_blocks:
        raise DigitalTwinConflictError(
            f"{device.name} has no assigned track blocks. "
            "Run the track-block seed/setup before simulating this attack."
        )

    timestamp = datetime.now(timezone.utc)
    results = []

    record_event(
        db,
        event_type="controller_compromised",
        title="Signal controller compromised",
        message=(
            f"{device.name} was compromised by unauthorized "
            "logic modification."
        ),
        severity="Critical",
        asset_name=device.name,
        device_id=device.id,
    )

    for block in affected_blocks:
        block.signal_aspect = "Stop"
        block.communications_status = "Degraded"
        block.security_status = "Compromised"
        block.last_updated = timestamp
        results.append(
            {
                "id": block.id,
                "name": block.name,
                "signal_aspect": block.signal_aspect,
                "communications_status": block.communications_status,
                "security_status": block.security_status,
            }
        )
        record_event(
            db,
            event_type="signal_forced_stop",
            title=f"{block.name} forced to Stop",
            message=(
                f"{device.name} forced {block.name} to Stop; "
                "communications are degraded and security is compromised."
            ),
            severity="Critical",
            asset_name=block.name,
            device_id=device.id,
            track_block_id=block.id,
            metadata={
                "signal_aspect": block.signal_aspect,
                "communications_status": block.communications_status,
                "security_status": block.security_status,
            },
        )

    return results


def apply_switch_controller_effect(db, device):
    switches = db.query(TrackSwitch).filter(
        TrackSwitch.controlling_device_id == device.id
    ).order_by(TrackSwitch.milepost).all()
    if not switches:
        raise DigitalTwinConflictError(
            f"{device.name} has no assigned track switches."
        )

    now = datetime.now(timezone.utc)
    device.status = "Compromised"
    device.risk_level = "Critical"
    results = []
    for track_switch in switches:
        track_switch.position = (
            "Reverse"
            if track_switch.commanded_position == "Normal"
            else "Normal"
        )
        track_switch.locked = True
        track_switch.communications_status = "Degraded"
        track_switch.security_status = "Compromised"
        track_switch.last_updated = now
        results.append(_serialize_switch(track_switch))
        record_event(
            db,
            event_type="switch_locked_unsafe",
            title=f"{track_switch.name} locked unsafe",
            message=(
                f"{device.name} left {track_switch.name} locked and "
                "misaligned; train movement is prohibited."
            ),
            severity="Critical",
            asset_name=track_switch.name,
            device_id=device.id,
            track_block_id=track_switch.track_block_id,
            metadata=_serialize_switch(track_switch),
        )
    return results


def apply_grade_crossing_effect(db, device):
    crossings = db.query(GradeCrossing).filter(
        GradeCrossing.controlling_device_id == device.id
    ).order_by(GradeCrossing.milepost).all()
    if not crossings:
        raise DigitalTwinConflictError(
            f"{device.name} has no assigned grade crossings."
        )

    now = datetime.now(timezone.utc)
    device.status = "Compromised"
    device.risk_level = "Critical"
    results = []
    for crossing in crossings:
        crossing.gate_state = "Unavailable"
        crossing.lights_active = False
        crossing.warning_time_seconds = 0
        crossing.communications_status = "Degraded"
        crossing.security_status = "Compromised"
        crossing.last_updated = now
        result = _serialize_crossing(crossing)
        results.append(result)
        record_event(
            db,
            event_type="crossing_warning_unavailable",
            title=f"{crossing.name} warning unavailable",
            message=(
                f"{device.name} compromise made the crossing warning "
                "system unavailable."
            ),
            severity="Critical",
            asset_name=crossing.name,
            device_id=device.id,
            metadata=result,
        )
    return results


def apply_ptc_communications_effect(db, device):
    trains = db.query(Train).filter(Train.ptc_enabled.is_(True)).all()
    results = []
    for train in trains:
        if train.status in {"Arrived", "Stopped"}:
            continue
        train.status = "Restricted - PTC Communications"
        results.append(
            {
                "id": train.id,
                "symbol": train.symbol,
                "status": train.status,
                "speed": train.speed,
            }
        )
        record_event(
            db,
            event_type="ptc_restricted_operation",
            title=f"{train.symbol} entered restricted operation",
            message=(
                f"{device.name} communications are unavailable; "
                f"{train.symbol} is restricted."
            ),
            severity="High",
            asset_name=train.symbol,
            device_id=device.id,
            train_id=train.id,
        )
    return results


def apply_dispatch_scada_effect(db, device):
    status = (device.status or "Degraded").strip().title()
    result = {
        "device_id": device.id,
        "device_name": device.name,
        "dispatch_status": status,
        "command_delay_seconds": {
            "Degraded": 15,
            "Severe": 60,
            "Offline": None,
        }.get(status, 15),
    }
    record_event(
        db,
        event_type="dispatch_scada_degraded",
        title=f"{device.name} {status.lower()}",
        message=(
            f"Dispatcher command handling is {status.lower()}; "
            "new commands may be delayed or queued."
        ),
        severity="High",
        asset_name=device.name,
        device_id=device.id,
        metadata=result,
    )
    return result


def _serialize_switch(track_switch):
    return {
        "id": track_switch.id,
        "name": track_switch.name,
        "milepost": track_switch.milepost,
        "position": track_switch.position,
        "commanded_position": track_switch.commanded_position,
        "locked": track_switch.locked,
        "communications_status": track_switch.communications_status,
        "security_status": track_switch.security_status,
    }


def _serialize_crossing(crossing):
    return {
        "id": crossing.id,
        "name": crossing.name,
        "milepost": crossing.milepost,
        "gate_state": crossing.gate_state,
        "lights_active": crossing.lights_active,
        "warning_time_seconds": crossing.warning_time_seconds,
        "communications_status": crossing.communications_status,
        "security_status": crossing.security_status,
    }


def apply_digital_twin_effect(db, attack, target):
    if is_signal_logic_modification(attack, target):
        blocks = apply_signal_controller_effect(db, target)
        return {
            "effect_type": "signal_controller_compromise",
            "affected_track_blocks": blocks,
        }

    target_type = (target.device_type or "").strip().lower()
    attack_id = (attack.get("attack_id") or "").strip().lower()

    if target_type == "switch controller" and attack_id == "logic_modification":
        return {
            "effect_type": "switch_controller_compromise",
            "affected_switches": apply_switch_controller_effect(db, target),
        }
    if (
        target_type == "grade crossing controller"
        and attack_id in {"firmware_tampering", "communication_failure"}
    ):
        return {
            "effect_type": "grade_crossing_compromise",
            "affected_crossings": apply_grade_crossing_effect(db, target),
        }
    if (
        target_type == "ptc communications gateway"
        and attack_id == "communication_failure"
    ):
        return {
            "effect_type": "ptc_communications_failure",
            "affected_trains": apply_ptc_communications_effect(db, target),
        }
    if target_type == "dispatch scada" and attack_id == "denial_of_service":
        return {
            "effect_type": "dispatch_scada_degradation",
            "dispatch": apply_dispatch_scada_effect(db, target),
        }

    return {"effect_type": None, "affected_track_blocks": []}
