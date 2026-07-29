from datetime import datetime, timezone

from models import GradeCrossing, TrackBlock, TrackSwitch, Train
from services.device_framework import (
    capabilities_for_device,
    relationship_targets,
    supported_effects_for_device,
)
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
    affected_blocks = sorted(
        relationship_targets(
            db, device, "TRACK_BLOCK", TrackBlock
        ),
        key=lambda block: block.start_milepost,
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
    switches = sorted(
        relationship_targets(
            db, device, "TRACK_SWITCH", TrackSwitch
        ),
        key=lambda track_switch: track_switch.milepost,
    )
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
    crossings = sorted(
        relationship_targets(
            db, device, "GRADE_CROSSING", GradeCrossing
        ),
        key=lambda crossing: crossing.milepost,
    )
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


def _apply_signal_effect(db, device, effect_id):
    if effect_id == "force_stop_signal":
        affected_blocks = apply_signal_controller_effect(db, device)
        return {
            "effect_type": effect_id,
            "affected_track_blocks": affected_blocks,
        }
    else:
        blocks = relationship_targets(
            db, device, "TRACK_BLOCK", TrackBlock
        )
        if not blocks:
            raise DigitalTwinConflictError(
                f"{device.name} has no assigned track blocks."
            )
        aspect = {
            "force_approach_signal": "Approach",
            "disable_signal": "Dark",
        }.get(effect_id, "Stop")
        for block in blocks:
            block.signal_aspect = aspect
            block.communications_status = "Degraded"
            block.security_status = "Compromised"
    return {
        "effect_type": effect_id,
        "affected_track_blocks": [
            {
                "id": block.id,
                "name": block.name,
                "signal_aspect": block.signal_aspect,
                "communications_status": block.communications_status,
                "security_status": block.security_status,
            }
            for block in blocks
        ],
    }


def _apply_switch_effect(db, device, effect_id):
    return {
        "effect_type": effect_id,
        "affected_switches": apply_switch_controller_effect(db, device),
    }


def _apply_crossing_effect(db, device, effect_id):
    return {
        "effect_type": effect_id,
        "affected_crossings": apply_grade_crossing_effect(db, device),
    }


def _apply_ptc_effect(db, device, effect_id):
    return {
        "effect_type": effect_id,
        "affected_trains": apply_ptc_communications_effect(db, device),
    }


def _apply_dispatch_effect(db, device, effect_id):
    if effect_id == "dispatch_offline":
        device.status = "Offline"
    elif effect_id in {"dispatch_delay", "queue_dispatch_commands"}:
        device.status = "Degraded"
    return {
        "effect_type": effect_id,
        "dispatch": apply_dispatch_scada_effect(db, device),
    }


def _apply_device_state_effect(db, device, effect_id):
    if effect_id in {"communications_loss", "sensor_offline", "remote_lockout"}:
        device.status = "Offline"
    else:
        device.status = "Compromised"
    device.risk_level = "Critical"
    result = {
        "effect_type": effect_id,
        "device": {
            "id": device.id,
            "name": device.name,
            "status": device.status,
            "risk_level": device.risk_level,
        },
    }
    record_event(
        db,
        event_type="effect_applied",
        title=f"{effect_id.replace('_', ' ').title()} applied",
        message=f"{effect_id.replace('_', ' ').title()} affected {device.name}.",
        severity="High",
        asset_name=device.name,
        device_id=device.id,
        metadata=result,
    )
    return result


EFFECT_HANDLERS = {
    "force_stop_signal": _apply_signal_effect,
    "force_approach_signal": _apply_signal_effect,
    "disable_signal": _apply_signal_effect,
    "lock_switch": _apply_switch_effect,
    "misalign_switch": _apply_switch_effect,
    "disable_crossing": _apply_crossing_effect,
    "disable_warning_lights": _apply_crossing_effect,
    "ptc_degraded": _apply_ptc_effect,
    "restricted_speed": _apply_ptc_effect,
    "dispatch_delay": _apply_dispatch_effect,
    "dispatch_offline": _apply_dispatch_effect,
    "queue_dispatch_commands": _apply_dispatch_effect,
    "communications_loss": _apply_device_state_effect,
    "sensor_offline": _apply_device_state_effect,
    "false_sensor_reading": _apply_device_state_effect,
    "power_loss": _apply_device_state_effect,
    "firmware_corruption": _apply_device_state_effect,
    "logic_modification": _apply_device_state_effect,
    "remote_lockout": _apply_device_state_effect,
}


ATTACK_EFFECT_BY_CAPABILITY = {
    "logic_modification": {
        "controls_track_blocks": "force_stop_signal",
        "controls_switches": "misalign_switch",
        "supports_remote_management": "logic_modification",
    },
    "firmware_tampering": {
        "controls_crossings": "disable_crossing",
        "supports_remote_management": "firmware_corruption",
    },
    "communication_failure": {
        "controls_crossings": "disable_crossing",
        "controls_ptc": "ptc_degraded",
        "controls_communications": "communications_loss",
    },
    "denial_of_service": {
        "controls_dispatch": "dispatch_delay",
        "controls_communications": "communications_loss",
    },
}


def resolve_attack_effect(attack, target):
    configured = attack.get("effect_id") or attack.get("digital_twin_effect")
    if configured in EFFECT_HANDLERS:
        return configured
    attack_id = (attack.get("attack_id") or "").strip().lower()
    mapping = ATTACK_EFFECT_BY_CAPABILITY.get(attack_id, {})
    capabilities = capabilities_for_device(target)
    for capability in capabilities:
        if capability in mapping:
            return mapping[capability]
    return None


def apply_effect(db, device, effect_id):
    if effect_id not in supported_effects_for_device(device):
        raise DigitalTwinConflictError(
            f"{device.name} does not support effect '{effect_id}'."
        )
    handler = EFFECT_HANDLERS.get(effect_id)
    if not handler:
        raise DigitalTwinConflictError(
            f"No handler is registered for effect '{effect_id}'."
        )
    result = handler(db, device, effect_id)
    record_event(
        db,
        event_type="effect_applied",
        title=f"{effect_id.replace('_', ' ').title()} applied",
        message=f"The configured effect was applied to {device.name}.",
        severity="High",
        asset_name=device.name,
        device_id=device.id,
        metadata={"effect_id": effect_id},
    )
    return result


def apply_digital_twin_effect(db, attack, target):
    effect_id = resolve_attack_effect(attack, target)
    if not effect_id:
        return {"effect_type": None, "affected_track_blocks": []}
    result = apply_effect(db, target, effect_id)

    # Preserve the established response names consumed by the demo UI/tests.
    legacy_names = {
        "force_stop_signal": "signal_controller_compromise",
        "misalign_switch": "switch_controller_compromise",
        "disable_crossing": "grade_crossing_compromise",
        "ptc_degraded": "ptc_communications_failure",
        "dispatch_delay": "dispatch_scada_degradation",
    }
    result["configured_effect"] = effect_id
    result["effect_type"] = legacy_names.get(effect_id, effect_id)
    return result
