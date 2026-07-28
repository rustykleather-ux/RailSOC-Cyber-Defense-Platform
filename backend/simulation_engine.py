from services.alert_service import create_alert
from services.digital_twin_service import apply_digital_twin_effect
from services.timeline_service import record_event


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
        operational_effects = apply_digital_twin_effect(
            db=db,
            attack=attack,
            target=target,
        )
        affected_blocks = operational_effects.get(
            "affected_track_blocks", []
        )

        alert = create_alert(
            db=db,
            device=target,
            attack=attack,
        )
        record_event(
            db,
            event_type="attack_launched",
            title=attack["name"],
            message=attack["description"],
            severity=attack["severity"],
            source="Training Scenario",
            asset_name=target.name,
            device_id=target.id,
            incident_id=getattr(alert, "created_incident_id", None),
            metadata={"attack_id": attack.get("attack_id")},
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
                "operational_effects": operational_effects,
            }
        )

    return simulation_results
