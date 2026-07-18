from models import OTDevice


def apply_attack(
    db,
    attack,
    targets,
):

    simulation_results = []

    for target in targets:
        previous_status = target.status
        
        target.status = "Compromised"

        simulation_results.append(
            {
                "device_id": target.id,
                "device_name": target.name,
                "previous_status": previous_status,
                "new_status": "Compromised",

        }
    )


    
    db.commit()

    for target in targets:
        db.refresh(target)

    return simulation_results
