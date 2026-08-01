from models import Alert, Incident


def create_alert(
    db,
    device,
    attack,
    exercise_run_id=None,
):
    print("CREATE_ALERT CALLED")

    alert = Alert(
        device_id=device.id,
        exercise_run_id=exercise_run_id,
        severity=attack["severity"],
        alert_type=attack["name"],
        message=attack["description"],
    )

    db.add(alert)
    db.flush()

    incident = Incident(
        alert_id=alert.id,
        device_id=device.id,
        exercise_run_id=exercise_run_id,
        severity=alert.severity,
        device=device.name,
        alert_type=alert.alert_type,
        message=alert.message,
        status="Open",
        acknowledged=False,
        assigned_to="Unassigned",
        investigation_notes="",
        closed_by="",
        closed_at=None,
        mitre_technique=attack.get("mitre_technique", ""),
    )

    db.add(incident)
    db.flush()
    alert.created_incident_id = incident.id

    print("Created Alert ID:", alert.id)
    print("Created Incident ID:", incident.id)

    return alert
