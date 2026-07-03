from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from services.risk_engine import calculate_device_risk
from database import Base, engine, SessionLocal
from models import OTDevice, Alert, Vulnerability
from datetime import datetime
import random

app = FastAPI(title="Industrial Cyber Defense Platform")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.get("/")
def root():
    return {"message": "Industrial Cyber Defense Platform API"}


@app.get("/devices")
def get_devices(db: Session = Depends(get_db)):
    devices = db.query(OTDevice).all()
    results = []

    for device in devices:
        device_alerts = db.query(Alert).filter(Alert.device_id == device.id).all()
        device_vulns = db.query(Vulnerability).filter(Vulnerability.device_id == device.id).all()

        risk = calculate_device_risk(device, device_alerts, device_vulns)

        results.append({
            "id": device.id,
            "name": device.name,
            "ip_address": device.ip_address,
            "device_type": device.device_type,
            "vendor": device.vendor,
            "status": device.status,
            "risk_level": device.risk_level,
            "firmware_version": device.firmware_version,
            "location": device.location,
            "last_seen": device.last_seen,
            "risk_score": risk["risk_score"],
            "calculated_risk": risk["calculated_risk"]
        })

    return results


@app.get("/alerts")
def get_alerts(db: Session = Depends(get_db)):
    alerts = db.query(Alert).all()

    results = []

    for alert in alerts:
        results.append({
            "id": alert.id,
            "severity": alert.severity,
            "alert_type": alert.alert_type,
            "message": alert.message,
            "status": alert.status,
            "acknowledged": alert.acknowledged,
            "time": alert.timestamp,
            "device_id": alert.device_id,
            "device": alert.device.name if alert.device else "Unknown"
        })

    return results


@app.get("/vulnerabilities")
def get_vulnerabilities(db: Session = Depends(get_db)):
    vulnerabilities = db.query(Vulnerability).all()

    results = []

    for vuln in vulnerabilities:
        results.append({
            "id": vuln.id,
            "device_id": vuln.device_id,
            "cve_id": vuln.cve_id,
            "title": vuln.title,
            "severity": vuln.severity,
            "cvss_score": vuln.cvss_score,
            "status": vuln.status,
            "recommendation": vuln.recommendation,
            "created_at": vuln.created_at
        })

    return results


@app.get("/dashboard")
def dashboard(db: Session = Depends(get_db)):
    devices = db.query(OTDevice).all()
    alerts = db.query(Alert).all()
    vulnerabilities = db.query(Vulnerability).all()

    total = len(devices)
    online = len([d for d in devices if d.status == "Online"])
    offline = len([d for d in devices if d.status == "Offline"])
    high_risk = len([d for d in devices if d.risk_level in ["High", "Critical"]])
    open_alerts = len([a for a in alerts if a.status == "Open"])
    critical_alerts = len([a for a in alerts if a.severity == "Critical"])
    open_vulnerabilities = len([v for v in vulnerabilities if v.status == "Open"])

    return {
        "total_devices": total,
        "online_devices": online,
        "offline_devices": offline,
        "high_risk_devices": high_risk,
        "open_alerts": open_alerts,
        "critical_alerts": critical_alerts,
        "open_vulnerabilities": open_vulnerabilities,
        "overall_status": "Attention Required" if offline or high_risk or critical_alerts else "Healthy"
    }
@app.post("/simulate-attack/{attack_type}")
def simulate_attack(attack_type: str, db: Session = Depends(get_db)):
    attack_type = attack_type.lower()

    if attack_type == "inverter-offline":
        device = db.query(OTDevice).filter(OTDevice.name == "Solar Inverter").first()

        if not device:
            return {"error": "Solar Inverter not found"}

        device.status = "Offline"
        device.risk_level = "High"
        device.last_seen = datetime.utcnow()

        alert = Alert(
            device_id=device.id,
            severity="High",
            alert_type="Communication Loss",
            message="Simulated attack: Solar inverter communication lost.",
            status="Open",
            acknowledged=False
        )

        db.add(alert)
        db.commit()

        return {"message": "Simulated inverter communication loss created."}

    if attack_type == "plc-firmware":
        device = db.query(OTDevice).filter(OTDevice.name == "PLC-2").first()

        if not device:
            return {"error": "PLC-2 not found"}

        device.firmware_version = "UNKNOWN"
        device.risk_level = "Critical"
        device.last_seen = datetime.utcnow()

        alert = Alert(
            device_id=device.id,
            severity="Critical",
            alert_type="Firmware Change",
            message="Simulated attack: PLC firmware changed unexpectedly.",
            status="Open",
            acknowledged=False
        )

        db.add(alert)
        db.commit()

        return {"message": "Simulated PLC firmware change created."}

    if attack_type == "failed-logins":
        device = db.query(OTDevice).filter(OTDevice.name == "Engineering Workstation").first()

        if not device:
            return {"error": "Engineering Workstation not found"}

        device.risk_level = "Medium"
        device.last_seen = datetime.utcnow()

        alert = Alert(
            device_id=device.id,
            severity="Medium",
            alert_type="Authentication",
            message="Simulated attack: Multiple failed login attempts detected.",
            status="Open",
            acknowledged=False
        )

        db.add(alert)
        db.commit()

        return {"message": "Simulated failed login attack created."}

    if attack_type == "network-scan":
        device = db.query(OTDevice).filter(OTDevice.name == "SCADA Server").first()

        if not device:
            return {"error": "SCADA Server not found"}

        device.risk_level = "High"
        device.last_seen = datetime.utcnow()

        alert = Alert(
            device_id=device.id,
            severity="High",
            alert_type="Network Reconnaissance",
            message="Simulated attack: Network scan detected against SCADA environment.",
            status="Open",
            acknowledged=False
        )

        db.add(alert)
        db.commit()

        return {"message": "Simulated network scan created."}

    return {
        "error": "Unknown attack type",
        "valid_attack_types": [
            "inverter-offline",
            "plc-firmware",
            "failed-logins",
            "network-scan"
        ]
    }

@app.get("/plant-status")
def plant_status(db: Session = Depends(get_db)):
    devices = db.query(OTDevice).all()
    status_data = []

    for device in devices:
        device_alerts = db.query(Alert).filter(
            Alert.device_id == device.id,
            Alert.status == "Open"
        ).all()

        alert_types = [alert.alert_type for alert in device_alerts]

        if device.device_type == "PLC":
            firmware_attack = "Firmware Change" in alert_types

            status_data.append({
                "device": device.name,
                "type": device.device_type,
                "status": device.status,
                "temperature": random.randint(82, 105) if firmware_attack else random.randint(68, 88),
                "cpu_usage": random.randint(75, 98) if firmware_attack else random.randint(15, 75),
                "memory_usage": random.randint(70, 95) if firmware_attack else random.randint(25, 85),
                "network_latency": random.randint(20, 80) if firmware_attack else random.randint(1, 15),
                "condition": "Abnormal" if firmware_attack else "Normal",
                "timestamp": datetime.utcnow().isoformat()
            })

        elif device.device_type == "Inverter":
            comm_loss = "Communication Loss" in alert_types

            status_data.append({
                "device": device.name,
                "type": device.device_type,
                "status": device.status,
                "power_output_kw": 0 if device.status == "Offline" or comm_loss else random.randint(350, 475),
                "voltage": 0 if device.status == "Offline" or comm_loss else random.randint(380, 480),
                "network_latency": 999 if device.status == "Offline" or comm_loss else random.randint(1, 20),
                "condition": "Communication Lost" if device.status == "Offline" or comm_loss else "Normal",
                "timestamp": datetime.utcnow().isoformat()
            })

        elif device.device_type == "SCADA":
            scan_detected = "Network Reconnaissance" in alert_types

            status_data.append({
                "device": device.name,
                "type": device.device_type,
                "status": device.status,
                "cpu_usage": random.randint(70, 95) if scan_detected else random.randint(20, 65),
                "memory_usage": random.randint(65, 90) if scan_detected else random.randint(35, 80),
                "active_sessions": random.randint(8, 20) if scan_detected else random.randint(1, 8),
                "network_latency": random.randint(25, 90) if scan_detected else random.randint(1, 10),
                "condition": "Network Scan Detected" if scan_detected else "Normal",
                "timestamp": datetime.utcnow().isoformat()
            })

        elif device.device_type == "Workstation":
            auth_attack = "Authentication" in alert_types

            status_data.append({
                "device": device.name,
                "type": device.device_type,
                "status": device.status,
                "cpu_usage": random.randint(50, 90) if auth_attack else random.randint(10, 90),
                "memory_usage": random.randint(50, 90) if auth_attack else random.randint(30, 90),
                "failed_logins": random.randint(8, 25) if auth_attack else random.randint(0, 5),
                "network_latency": random.randint(10, 40) if auth_attack else random.randint(1, 25),
                "condition": "Authentication Attack" if auth_attack else "Normal",
                "timestamp": datetime.utcnow().isoformat()
            })

    return status_data

@app.get("/incidents")
def get_incidents(db: Session = Depends(get_db)):
    alerts = db.query(Alert).order_by(Alert.timestamp.desc()).all()

    incidents = []

    for alert in alerts:
        incidents.append({
            "id": alert.id,
            "time": alert.timestamp.isoformat() if alert.timestamp else None,
            "severity": alert.severity,
            "device": alert.device.name if alert.device else "Unknown Device",
            "alert_type": alert.alert_type,
            "message": alert.message,
            "status": alert.status,
            "acknowledged": alert.acknowledged,
            "mitre_technique": get_mitre_mapping(alert.alert_type)
        })

    return incidents

@app.post("/incidents/{incident_id}/acknowledge")
def acknowledge_incident(incident_id: int, db: Session = Depends(get_db)):
    alert = db.query(Alert).filter(Alert.id == incident_id).first()

    if not alert:
        return {"error": "Incident not found"}

    alert.acknowledged = True
    alert.status = "Acknowledged"

    db.add(alert)
    db.commit()
    db.refresh(alert)

    return {
        "message": "Incident acknowledged",
        "incident_id": alert.id,
        "status": alert.status,
        "acknowledged": alert.acknowledged
    }

def get_mitre_mapping(alert_type):
    mappings = {
        "Communication Loss": "T0881 - Service Stop",
        "Firmware Change": "T0859 - Modify Controller Tasking",
        "Authentication": "T0812 - Default Credentials / Valid Accounts",
        "Network Reconnaissance": "T0842 - Network Service Scanning",
        "General": "T0800 - Activate Firmware Update Mode"
    }

    return mappings.get(alert_type, "Unmapped")

@app.post("/reset-demo")
def reset_demo(db: Session = Depends(get_db)):
    baseline_devices = {
        "PLC-1": {
            "status": "Online",
            "risk_level": "Low",
            "firmware_version": "1.0.3"
        },
        "PLC-2": {
            "status": "Online",
            "risk_level": "Low",
            "firmware_version": "3.2.1"
        },
        "Solar Inverter": {
            "status": "Online",
            "risk_level": "Low",
            "firmware_version": "2.4.8"
        },
        "Engineering Workstation": {
            "status": "Online",
            "risk_level": "Low",
            "firmware_version": "Windows 11 24H2"
        },
        "SCADA Server": {
            "status": "Online",
            "risk_level": "Low",
            "firmware_version": "8.1.35"
        }
    }

    

    for name, values in baseline_devices.items():
        device = db.query(OTDevice).filter(OTDevice.name == name).first()
        if device:
            device.status = values["status"]
            device.risk_level = values["risk_level"]
            device.firmware_version = values["firmware_version"]
            device.last_seen = datetime.utcnow()

    # Remove alerts so they no longer affect calculated risk/topology color
    db.query(Alert).delete()

    # Remove vulnerabilities so reset returns topology to green baseline
    db.query(Vulnerability).delete()

    db.commit()

    return {"message": "Demo environment reset to normal baseline."}