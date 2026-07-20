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

        simulation_results.append(
            {
                "device_id": target.id,
                "device_name": target.name,
                "previous_status": previous_status,
                "new_status": new_status,
                "detected_condition": attack.get("condition"),
            }
        )

    db.commit()

    for target in targets:
        db.refresh(target)

    return simulation_results