import random
from datetime import datetime
from typing import Optional, Any, Dict, List
from urllib import request

from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from scenario_manager import scenario_manager
from simulation_engine import apply_attack
from attack_catalog import Attack_Catalog   
from attack_manager import launch_attack, get_active_attacks 
from database import Base, engine, SessionLocal
from models import (
    OTDevice,
    Alert,
    Vulnerability,
    Train,
    TrainHistory,
)
from services.risk_engine import calculate_device_risk
from train_simulation import train_simulation
from railroad import TRACK_BLOCKS

class ScenarioCreateRequest(BaseModel):
    attack_id: str
    target_ids: List[int] = Field(min_length=1)
    notes: Optional[str] = None
    created_by: Optional[str] = None


class ScenarioProgressRequest(BaseModel):
    progress: int = Field(ge=0, le=100)
    current_step: Optional[str] = None


class ScenarioTimelineEventRequest(BaseModel):
    event_type: str
    title: str
    message: str
    severity: str = "Info"
    progress: Optional[int] = Field(default=None, ge=0, le=100)
    metadata: Optional[Dict[str, Any]] = None


    
# =========================================================
# Database setup
# =========================================================

Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()


# =========================================================
# FastAPI application
# =========================================================

app = FastAPI(
    title="TrackSentinel",
    description="RailSOC Training & Simulation Platform",
    version="1.0.0",
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# =========================================================
# Scenario endpoint
# =========================================================

@app.post("/training/scenarios")
def create_training_scenario(request: ScenarioCreateRequest):
    attack = Attack_Catalog.get(request.attack_id)

    if attack is None:
        raise HTTPException(
            status_code=404,
            detail=f'Attack "{request.attack_id}" was not found.',
        )

    scenario = scenario_manager.create_scenario(
        attack_id=request.attack_id,
        attack_name=attack["name"],
        target_ids=request.target_ids,
        notes=request.notes,
        created_by=request.created_by,
    )

    return {
        "message": "Scenario created successfully.",
        "scenario": scenario,
    }
# =========================================================
# Track Blocks API endpoint
# =========================================================

@app.get("/track-blocks")
def get_track_blocks():

    return [
        {
            "id": b.id,
            "name": b.name,
            "start_mp": b.start_mp,
            "end_mp": b.end_mp,
            "occupied": b.occupied,
            "occupied_by": b.occupied_by,
        }
        for b in TRACK_BLOCKS
    ]

# =========================================================
# Custom Scenario Base models
# =========================================================

class CustomScenario(BaseModel):
    attack_id: str
    target_ids: list[int]
    notes: Optional[str] = None

 


# =========================================================
# Request models
# =========================================================

class TrainCreate(BaseModel):
    symbol: str
    subdivision: str
    train_type: str = "Freight"
    direction: str = "Eastbound"
    destination: Optional[str] = None
    milepost: float = 80.0
    speed: int = 40
    status: str = "Moving"
    ptc_enabled: bool = True
    authority: str = "Main Track"
    locomotive: Optional[str] = None
    train_length: Optional[int] = None
    weight_tons: Optional[int] = None
    crew: Optional[str] = None
    current_signal: str = "Clear"
    track: str = "Main"


class AssignIncidentRequest(BaseModel):
    assigned_to: str


class CloseIncidentRequest(BaseModel):
    closed_by: str


class IncidentNotesRequest(BaseModel):
    investigation_notes: str

# =========================================================
# Track Active Attacks API endpoint
# =========================================================
@app.get("/active-attacks")
def read_active_attacks():
    attacks = get_active_attacks()
    return {
        "count": len(attacks),
        "attacks": attacks
    }
# =========================================================
# Attack Catalog Endpoint
# ======================================================

@app.get("/attacks")
def get_attacks():
    return {
        "attacks": [
            {
                "id": attack["attack_id"],
                "attack_id": attack["attack_id"],
                "name": attack["name"],
                "description": attack["description"],
                "severity": attack["severity"],
                "mitre_id": attack.get("mitre_id"),
                "mitre_name": attack.get("mitre_name"),
                "compatible_types": attack.get("compatible_types", []),
                "condition": attack.get("condition"),
            }
            for attack in Attack_Catalog.values()
        ]
    }
# =========================================================
# Attack Simulation API endpoint
# ======================================================
@app.post("/training/custom-scenario")
def launch_custom_scenario(
    request: CustomScenario,
    db: Session = Depends(get_db),
):
    attack = Attack_Catalog.get(request.attack_id)

    if not attack:
        raise HTTPException(
            status_code=404,
            detail="Attack definition not found",
        )

    if not request.target_ids:
        raise HTTPException(
            status_code=400,
            detail="Select at least one target",
        )

    targets = (
        db.query(OTDevice)
        .filter(
            OTDevice.id.in_(request.target_ids)
        )
        .all()
    )

    if not targets:
        raise HTTPException(
            status_code=404,
            detail="No matching targets were found",
        )

    invalid_targets = []

    for target in targets:
        print("===================================")
        print("Target Name:", target.name)
        print("Target Type:", target.device_type)
        print("Compatible Types:", attack["compatible_types"])
        print("Comparison Result:", target.device_type in attack["compatible_types"])
        print("===================================")
        if target.device_type not in attack["compatible_types"]:
            invalid_targets.append(target)

    if invalid_targets:
        invalid_target_names = []

        for target in invalid_targets:
            invalid_target_names.append(target.name)

        raise HTTPException(
            status_code=400,
            detail={
                "message": (
                    "One or more targets are incompatible "
                    "with this attack"
                ),
                "invalid_targets": invalid_target_names,
                "compatible_types": attack["compatible_types"],
            },
        )

    simulation_results = apply_attack(
        db=db,
        attack=attack,
        targets=targets,
   )   
    
    attack_instance = launch_attack(
        attack=attack,
        targets=targets,
        notes=request.notes,
    )

    return {
    "message": "Custom scenario launched successfully",
    "scenario": attack_instance,
    "simulation": simulation_results,
}
# =========================================================
# Train API endpoints
# =========================================================

@app.get("/trains")
def get_trains(db: Session = Depends(get_db)):
    return db.query(Train).order_by(Train.id).all()


@app.get("/trains/{train_id}")
def get_train(
    train_id: int,
    db: Session = Depends(get_db),
):
    train = (
        db.query(Train)
        .filter(Train.id == train_id)
        .first()
    )

    if not train:
        raise HTTPException(
            status_code=404,
            detail="Train not found",
        )

    return train


@app.post("/trains")
def create_train(
    payload: TrainCreate,
    db: Session = Depends(get_db),
):
    existing = (
        db.query(Train)
        .filter(Train.symbol == payload.symbol)
        .first()
    )

    if existing:
        raise HTTPException(
            status_code=400,
            detail="A train with that symbol already exists",
        )

    train = Train(
        symbol=payload.symbol,
        subdivision=payload.subdivision,
        train_type=payload.train_type,
        direction=payload.direction,
        destination=payload.destination,
        milepost=payload.milepost,
        speed=payload.speed,
        status=payload.status,
        ptc_enabled=payload.ptc_enabled,
        authority=payload.authority,
        locomotive=payload.locomotive,
        train_length=payload.train_length,
        weight_tons=payload.weight_tons,
        crew=payload.crew,
        current_signal=payload.current_signal,
        track=payload.track,
        last_updated=datetime.utcnow(),
    )

    db.add(train)
    db.commit()
    db.refresh(train)

    return train



def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.get("/")
def root():
   return {
    "product": "TrackSentinel",
    "platform": "RailSOC Training & Simulation Platform",
    "version": "1.0.0"
}


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

class CloseIncidentRequest(BaseModel):
    closed_by: str


@app.post("/incidents/{incident_id}/close")
def close_incident(
    incident_id: int,
    request: CloseIncidentRequest,
    db: Session = Depends(get_db)
):
    alert = db.query(Alert).filter(Alert.id == incident_id).first()

    if not alert:
        return {"error": "Incident not found"}

    alert.status = "Closed"
    alert.closed_by = request.closed_by
    alert.closed_at = datetime.utcnow()

    db.add(alert)
    db.commit()
    db.refresh(alert)

    return {
        "message": "Incident closed",
        "incident_id": alert.id,
        "status": alert.status,
        "closed_by": alert.closed_by,
        "closed_at": alert.closed_at.isoformat()
    }

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

    scenarios = {
        "firmware": {
            "device": "Grade Crossing Controller MP 82.4",
            "status": "Online",
            "risk": "Critical",
            "severity": "Critical",
            "alert_type": "Unauthorized Logic Modification",
            "message": "Simulated rail OT event: Unauthorized logic or firmware modification detected on grade crossing controller MP 82.4.",
            "firmware": "UNKNOWN",
        },
        "recon": {
            "device": "Dispatch SCADA Server",
            "status": "Online",
            "risk": "High",
            "severity": "High",
            "alert_type": "OT Network Reconnaissance",
            "message": "Simulated rail OT event: Network reconnaissance detected against the dispatch SCADA environment.",
        },
        "dos": {
            "device": "Dispatch SCADA Server",
            "status": "Degraded",
            "risk": "Critical",
            "severity": "Critical",
            "alert_type": "Rail OT Denial of Service",
            "message": "Simulated rail OT event: Denial of service condition causing degraded dispatch SCADA communications.",
        },
        "auth": {
            "device": "Rail Engineering Workstation",
            "status": "Online",
            "risk": "High",
            "severity": "High",
            "alert_type": "Unauthorized Engineering Login",
            "message": "Simulated rail OT event: Repeated authentication attempts detected against rail engineering workstation.",
        },
        "ptc": {
            "device": "PTC Radio Gateway",
            "status": "Offline",
            "risk": "High",
            "severity": "High",
            "alert_type": "PTC Radio Failure",
            "message": "Simulated rail OT event: PTC radio gateway communication loss detected from the wayside communications hut.",
        },
        "malware": {
            "device": "Rail Engineering Workstation",
            "status": "Degraded",
            "risk": "Critical",
            "severity": "Critical",
            "alert_type": "Engineering Workstation Malware",
            "message": "Simulated rail OT event: Malware-like behavior detected on rail engineering workstation.",
        },
    }

    scenario = scenarios.get(attack_type)

    if not scenario:
        return {
            "error": "Unknown attack type",
            "valid_attack_types": list(scenarios.keys())
        }

    device = db.query(OTDevice).filter(
        OTDevice.name == scenario["device"]
    ).first()

    if not device:
        return {"error": f"{scenario['device']} not found"}

    device.status = scenario["status"]
    device.risk_level = scenario["risk"]
    device.last_seen = datetime.utcnow()

    if "firmware" in scenario:
        device.firmware_version = scenario["firmware"]

    alert = Alert(
        device_id=device.id,
        severity=scenario["severity"],
        alert_type=scenario["alert_type"],
        message=scenario["message"],
        status="Open",
        acknowledged=False
    )

    db.add(alert)
    db.commit()

    return {
        "message": f"{scenario['alert_type']} simulation created.",
        "device": device.name,
        "severity": scenario["severity"]
    }

@app.post("/train-simulation/start")
def start_train_simulation():
    started = train_simulation.start()

    return {
        "running": train_simulation.is_running,
        "message": (
            "Train simulation started."
            if started
            else "Train simulation is already running."
        ),
    }

@app.post("/train-simulation/stop")
def stop_train_simulation():
    stopped = train_simulation.stop()
    return{
        "running": train_simulation.is_running,
        "message":(
        "Train simulation stopped."
        if stopped
        else "Train simulation was already stopped"
        ),
    }

@app.post("/train-simulation/restart")
def restart_traing_simulation():
    train_simulation.stop()
    train_simulation.reset_trains()
    train_simulation.start()

    return{
        "running": train_simulation.is_running,
        "message": "Train simulation restarted"
    }


@app.get("/train-simulation/status")
def train_simulation_status():
    return {
        "running": train_simulation.is_running,
        "interval_seconds": train_simulation.interval_seconds,
        "minimum_milepost": train_simulation.minimum_milepost,
        "maximum_milepost": train_simulation.maximum_milepost,
    }

@app.post("/train-simulation/reset")
def reset_train_simulation():
    train_simulation.reset_trains()

    return {
        "success": True,
        "message": "Train simulation reset.",
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

        if device.device_type in [
            "Signal Controller",
            "Grade Crossing Controller",
            "Switch Controller"
        ]:
            logic_attack = "Unauthorized Logic Modification" in alert_types

            status_data.append({
                "device": device.name,
                "type": device.device_type,
                "status": device.status,
                "temperature": random.randint(82, 105) if logic_attack else random.randint(68, 88),
                "cpu_usage": random.randint(75, 98) if logic_attack else random.randint(15, 75),
                "memory_usage": random.randint(70, 95) if logic_attack else random.randint(25, 85),
                "network_latency": random.randint(20, 80) if logic_attack else random.randint(1, 15),
                "condition": "Configuration Drift" if logic_attack else "Normal",
                "timestamp": datetime.utcnow().isoformat()
            })

        elif device.device_type == "PTC Communications Gateway":
            comm_loss = "PTC Radio Failure" in alert_types

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

        elif device.device_type == "Dispatch SCADA":
            scan_detected = "OT Network Reconnaissance" in alert_types
            dos_attack = "Rail OT Denial of Service" in alert_types

            status_data.append({
                "device": device.name,
                "type": device.device_type,
                "status": device.status,
                "cpu_usage": random.randint(85, 99) if dos_attack else random.randint(70, 95) if scan_detected else random.randint(20, 65),
                "memory_usage": random.randint(80, 96) if dos_attack else random.randint(65, 90) if scan_detected else random.randint(35, 80),
                "active_sessions": random.randint(12, 30) if dos_attack or scan_detected else random.randint(1, 8),
                "network_latency": random.randint(500, 999) if dos_attack else random.randint(25, 90) if scan_detected else random.randint(1, 10),
                "condition": "Denial of Service" if dos_attack else "Reconnaissance Detected" if scan_detected else "Normal",
                "timestamp": datetime.utcnow().isoformat()
            })

        elif device.device_type == "Engineering Workstation":
            auth_attack = "Unauthorized Engineering Login" in alert_types
            malware_attack = "Engineering Workstation Malware" in alert_types

            status_data.append({
                "device": device.name,
                "type": device.device_type,
                "status": device.status,
                "cpu_usage": random.randint(85, 99) if malware_attack else random.randint(50, 90) if auth_attack else random.randint(10, 90),
                "memory_usage": random.randint(80, 98) if malware_attack else random.randint(50, 90) if auth_attack else random.randint(30, 90),
                "failed_logins": random.randint(8, 25) if auth_attack else random.randint(0, 5),
                "network_latency": random.randint(40, 120) if malware_attack else random.randint(10, 40) if auth_attack else random.randint(1, 25),
                "condition": "Malware Activity" if malware_attack else "Authentication Attack" if auth_attack else "Normal",
                "timestamp": datetime.utcnow().isoformat()
            })

        elif device.device_type in ["Historian", "Jump Server"]:
            status_data.append({
                "device": device.name,
                "type": device.device_type,
                "status": device.status,
                "cpu_usage": random.randint(20, 70),
                "memory_usage": random.randint(35, 85),
                "active_sessions": random.randint(1, 12),
                "network_latency": random.randint(1, 20),
                "condition": "Normal",
                "timestamp": datetime.utcnow().isoformat()
            })

        elif device.device_type == "Communications":
            status_data.append({
                "device": device.name,
                "type": device.device_type,
                "status": device.status,
                "signal_quality": random.randint(82, 100),
                "packet_loss": round(random.uniform(0.0, 1.8), 2),
                "bandwidth_utilization": random.randint(20, 78),
                "network_latency": random.randint(3, 35),
                "condition": "Normal",
                "timestamp": datetime.utcnow().isoformat()
            })

        elif device.device_type in ["Power", "PLC"]:
            status_data.append({
                "device": device.name,
                "type": device.device_type,
                "status": device.status,
                "voltage": random.randint(116, 124),
                "load_percent": random.randint(20, 75),
                "battery_percent": random.randint(75, 100),
                "runtime_minutes": random.randint(45, 180),
                "network_latency": random.randint(1, 20),
                "condition": "Normal",
                "timestamp": datetime.utcnow().isoformat()
            })

        elif device.device_type == "Safety":
            status_data.append({
                "device": device.name,
                "type": device.device_type,
                "status": device.status,
                "smoke_level": random.randint(0, 2),
                "heat_alarm": "No",
                "panel_battery": random.randint(80, 100),
                "network_latency": random.randint(1, 20),
                "condition": "Normal",
                "timestamp": datetime.utcnow().isoformat()
            })

        elif device.device_type == "Environmental":
            status_data.append({
                "device": device.name,
                "type": device.device_type,
                "status": device.status,
                "temperature": random.randint(62, 82),
                "humidity": random.randint(35, 62),
                "gas_ppm": random.randint(0, 3),
                "water_detected": "No",
                "network_latency": random.randint(1, 20),
                "condition": "Normal",
                "timestamp": datetime.utcnow().isoformat()
            })

        elif device.device_type == "Physical Security":
            status_data.append({
                "device": device.name,
                "type": device.device_type,
                "status": device.status,
                "door_state": "Closed",
                "tamper_alarm": "No",
                "network_latency": random.randint(1, 20),
                "condition": "Normal",
                "timestamp": datetime.utcnow().isoformat()
            })

        elif device.device_type == "Infrastructure":
            status_data.append({
                "device": device.name,
                "type": device.device_type,
                "status": device.status,
                "vibration": round(random.uniform(0.1, 1.8), 2),
                "temperature": random.randint(55, 88),
                "bearing_temperature": random.randint(90, 145),
                "network_latency": random.randint(1, 25),
                "condition": "Normal",
                "timestamp": datetime.utcnow().isoformat()
            })

        else:
            status_data.append({
                "device": device.name,
                "type": device.device_type,
                "status": device.status,
                "network_latency": random.randint(1, 25),
                "condition": "Normal",
                "timestamp": datetime.utcnow().isoformat()
            })

    return status_data

@app.get("/incidents")
def get_incidents(db: Session = Depends(get_db)):
    alerts = (
        db.query(Alert)
        .filter(Alert.status != "Closed")
        .order_by(Alert.timestamp.desc())
        .all()
    )

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
            "assigned_to": alert.assigned_to,
            "investigation_notes": alert.investigation_notes,
            "closed_by": alert.closed_by,
            "closed_at": alert.closed_at.isoformat() if alert.closed_at else None,
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



class IncidentNotesRequest(BaseModel):
    investigation_notes: str


@app.post("/incidents/{incident_id}/notes")
def update_incident_notes(
    incident_id: int,
    request: IncidentNotesRequest,
    db: Session = Depends(get_db)
):
    alert = db.query(Alert).filter(Alert.id == incident_id).first()

    if not alert:
        return {"error": "Incident not found"}

    alert.investigation_notes = request.investigation_notes

    db.add(alert)
    db.commit()
    db.refresh(alert)

    return {
        "message": "Investigation notes updated",
        "incident_id": alert.id,
        "investigation_notes": alert.investigation_notes
    }

class AssignIncidentRequest(BaseModel):
    assigned_to: str


@app.post("/incidents/{incident_id}/assign")
def assign_incident(
    incident_id: int,
    request: AssignIncidentRequest,
    db: Session = Depends(get_db)
):
    alert = db.query(Alert).filter(Alert.id == incident_id).first()

    if not alert:
        return {"error": "Incident not found"}

    alert.assigned_to = request.assigned_to
    db.add(alert)
    db.commit()
    db.refresh(alert)

    return {
        "message": "Incident assigned",
        "incident_id": alert.id,
        "assigned_to": alert.assigned_to
    }

@app.post("/reset-demo")
def reset_demo(db: Session = Depends(get_db)):
    devices = db.query(OTDevice).all()

    for device in devices:
        device.status = "Online"
        device.risk_level = "Low"
        device.last_seen = datetime.utcnow()

        if device.name == "Grade Crossing Controller MP 82.4":
            device.firmware_version = "6.3.1"

        if device.name == "PTC Radio Gateway":
            device.firmware_version = "5.2.1"

        if device.name == "Rail Engineering Workstation":
            device.firmware_version = "Windows 11 24H2"

    db.query(Alert).delete()
    db.commit()

    return {"message": "TrackSentinel environment restored to operational baseline."}