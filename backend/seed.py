from database import Base, engine, SessionLocal
from models import OTDevice, Alert, Vulnerability

Base.metadata.create_all(bind=engine)

db = SessionLocal()

# Clear old demo data
db.query(Vulnerability).delete()
db.query(Alert).delete()
db.query(OTDevice).delete()
db.commit()

# Railroad OT Assets
signal_controller = OTDevice(
    name="Signal Controller 14A",
    ip_address="192.168.50.10",
    device_type="Signal Controller",
    vendor="Siemens Rail Automation",
    status="Online",
    risk_level="Low",
    firmware_version="4.1.3",
    location="East Signal District"
)

crossing_controller = OTDevice(
    name="Grade Crossing Controller MP 82.4",
    ip_address="192.168.50.11",
    device_type="Grade Crossing Controller",
    vendor="Wabtec",
    status="Online",
    risk_level="Critical",
    firmware_version="3.2.1",
    location="Prairie Subdivision - MP 82.4"
)

ptc_gateway = OTDevice(
    name="PTC Radio Gateway",
    ip_address="192.168.50.25",
    device_type="PTC Communications Gateway",
    vendor="Meteorcomm",
    status="Offline",
    risk_level="High",
    firmware_version="2.4.8",
    location="Wayside Communications Hut"
)

engineering_workstation = OTDevice(
    name="Rail Engineering Workstation",
    ip_address="192.168.50.100",
    device_type="Engineering Workstation",
    vendor="Dell",
    status="Online",
    risk_level="Medium",
    firmware_version="Windows 11 24H2",
    location="Maintenance Facility Alpha"
)

dispatch_scada = OTDevice(
    name="Dispatch SCADA Server",
    ip_address="192.168.50.200",
    device_type="Dispatch SCADA",
    vendor="Ignition",
    status="Online",
    risk_level="Low",
    firmware_version="8.1.35",
    location="West Dispatch Center"
)

db.add_all([
    signal_controller,
    crossing_controller,
    ptc_gateway,
    engineering_workstation,
    dispatch_scada
])
db.commit()

db.refresh(signal_controller)
db.refresh(crossing_controller)
db.refresh(ptc_gateway)
db.refresh(engineering_workstation)
db.refresh(dispatch_scada)

# RailSOC Alerts
alerts = [
    Alert(
        device_id=crossing_controller.id,
        severity="Critical",
        alert_type="Unauthorized Logic Modification",
        message="Grade crossing controller firmware/configuration drift detected at fictional milepost MP 82.4.",
        status="Open",
        acknowledged=False
    ),
    Alert(
        device_id=ptc_gateway.id,
        severity="High",
        alert_type="PTC Radio Failure",
        message="PTC radio gateway communication loss detected from wayside communications hut.",
        status="Open",
        acknowledged=False
    ),
    Alert(
        device_id=engineering_workstation.id,
        severity="Medium",
        alert_type="Unauthorized Engineering Login",
        message="Multiple failed authentication attempts detected against rail engineering workstation.",
        status="Open",
        acknowledged=False
    )
]

db.add_all(alerts)

# RailSOC Vulnerabilities
vulnerabilities = [
    Vulnerability(
        device_id=crossing_controller.id,
        cve_id="CVE-DEMO-RAIL-0001",
        title="Outdated Grade Crossing Controller Firmware",
        severity="Critical",
        cvss_score=9.1,
        status="Open",
        recommendation="Validate firmware version with vendor, coordinate with signal engineering, and schedule a controlled maintenance window."
    ),
    Vulnerability(
        device_id=ptc_gateway.id,
        cve_id="CVE-DEMO-RAIL-0002",
        title="PTC Gateway Communication Failure",
        severity="High",
        cvss_score=7.5,
        status="Open",
        recommendation="Check radio path, switch port, firewall rules, and remote access logs before restoring service."
    )
]

db.add_all(vulnerabilities)
db.commit()

db.close()

print("RailSOC database seeded successfully.")