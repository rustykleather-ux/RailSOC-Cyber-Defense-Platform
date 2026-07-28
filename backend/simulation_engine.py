from services.alert_service import create_alert
from services.digital_twin_service import apply_digital_twin_effect


def apply_attack(
    db,
    attack,
    targets,
):
    simulation_results = []

    effect = attack.get("simulation_effect", {})
    new_status = effect.get("status", "Compromised")

    for target in targets:
        previous_status = target.status

        target.status = new_status
        affected_blocks = apply_digital_twin_effect(
            db=db,
            attack=attack,
            target=target,
        )

        alert = create_alert(
            db=db,
            device=target,
            attack=attack,
        )

        simulation_results.append(
            {
                "device_id": target.id,
                "device_name": target.name,
                "previous_status": previous_status,
                "new_status": new_status,
                "detected_condition": attack.get("condition"),
                "alert_id": alert.id,
                "alert_type": alert.alert_type,
                "alert_severity": alert.severity,
                "affected_track_blocks": affected_blocks,
            }
        )

    return simulation_results
