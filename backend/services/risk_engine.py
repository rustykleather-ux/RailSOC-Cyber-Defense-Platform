def calculate_device_risk(device, alerts=None, vulnerabilities=None):
    score = 0
    alerts = alerts or []
    vulnerabilities =  vulnerabilities or []

    # Device Status
    if device.status == "Ofline":
        score += 25

        # Existing risk lable
        if device.risk_level == "Critical":
            score += 30
        elif device.risk_level == "High":
            score += 20
        elif device.risk_level == "Medium":
            score += 10

    # Alerts
    for alert in alerts:
        if alert.severity == "Critical":
            score += 25
        elif alert.severity == "High":
            score += 15
        elif alert.severity == "Medium":
            score += 8
        elif alert.severity == "Low":
            score += 3

    # Vulnerabilities
    for vuln in vulnerabilities:
        if vuln.severity == "Critical":
            score += 25
        elif vuln.severity == "High":
            score += 15
        elif vuln.severity == "Medium":
            score += 8
        elif vuln.severity == "Low":
            score += 3

    score = min(score, 100)

    if score >= 80:
        rating = "Critical"
    elif score >= 60:
        rating = "High"
    elif score >= 35:
        rating = "Medium"
    else:
        rating = "Low"

    return {
        "risk_score": score,
        "calculated_risk": rating
    }