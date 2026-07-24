from models import Alert, Incident


def create_alert(
    db,
    device,
    attack,
):
    print("CREATE_ALERT CALLED")

    alert = Alert(
        device_id=device.id,
        severity=attack["severity"],
        alert_type=attack["name"],
        message=attack["description"],
    )

    db.add(alert)
    db.flush()

    incident = Incident(
        alert_id=alert.id,
        device_id=device.id,
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

    print("Created Alert ID:", alert.id)
    print("Created Incident ID:", incident.id)

    return alert