from services.alert_service import create_alert


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
            }
        )

    db.commit()

    for target in targets:
        db.refresh(target)

    return simulation_results