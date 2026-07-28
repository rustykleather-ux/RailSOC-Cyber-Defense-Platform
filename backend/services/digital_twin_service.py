from datetime import datetime

from models import TrackBlock


SIGNAL_CONTROLLER_EFFECT = "signal_controller_compromise"
SIGNAL_LOGIC_ATTACK_IDS = {"logic_modification"}


class DigitalTwinConflictError(RuntimeError):
    """Raised when an attack cannot be applied to the digital twin."""


def is_signal_logic_modification(attack, target):
    if (target.device_type or "").strip().lower() != "signal controller":
        return False

    configured_effect = attack.get("digital_twin_effect")
    attack_id = (attack.get("attack_id") or "").strip().lower()

    return (
        configured_effect == SIGNAL_CONTROLLER_EFFECT
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

    timestamp = datetime.utcnow()
    results = []

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

    return results


def apply_digital_twin_effect(db, attack, target):
    if is_signal_logic_modification(attack, target):
        return apply_signal_controller_effect(db, target)

    return []
