from models import Alert


def create_alert(
    db,
    device,
    attack,
):
    alert = Alert(
        device_id=device.id,
        severity=attack["severity"],
        alert_type=attack["name"],
        message=attack["description"],
    )

    db.add(alert)
    db.flush()

    return alert