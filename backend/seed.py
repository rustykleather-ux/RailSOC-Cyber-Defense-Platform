from database import Base, engine, SessionLocal
from models import OTDevice, Alert, Vulnerability

Base.metadata.create_all(bind=engine)

db = SessionLocal()

# Clear old demo data
db.query(Vulnerability).delete()
db.query(Alert).delete()
db.query(OTDevice).delete()
db.commit()


dispatch_scada = OTDevice(
    name="Dispatch SCADA Server",
    ip_address="192.168.50.5",
    device_type="Dispatch SCADA",
    vendor="Inductive Automation Ignition",
    status="Online",
    risk_level="Low",
    firmware_version="8.1.35",
    location="Operations Control Center"
)

historian = OTDevice(
    name="Operations Historian",
    ip_address="192.168.50.6",
    device_type="Historian",
    vendor="OSIsoft PI",
    status="Online",
    risk_level="Low",
    firmware_version="2024",
    location="Operations Control Center"
)

jump_server = OTDevice(
    name="OT Jump Server",
    ip_address="192.168.50.7",
    device_type="Jump Server",
    vendor="Microsoft",
    status="Online",
    risk_level="Medium",
    firmware_version="Windows Server 2022",
    location="Operations Control Center"
)

signal14a = OTDevice(
    name="Signal Controller 14A",
    ip_address="192.168.50.10",
    device_type="Signal Controller",
    vendor="Siemens Rail Automation",
    status="Online",
    risk_level="Low",
    firmware_version="4.1.3",
    location="East Signal District"
)

signal14b = OTDevice(
    name="Signal Controller 14B",
    ip_address="192.168.50.11",
    device_type="Signal Controller",
    vendor="Siemens Rail Automation",
    status="Online",
    risk_level="Low",
    firmware_version="4.1.3",
    location="East Signal District"
)

signal15c = OTDevice(
    name="Signal Controller 15C",
    ip_address="192.168.50.12",
    device_type="Signal Controller",
    vendor="Siemens Rail Automation",
    status="Online",
    risk_level="Low",
    firmware_version="4.1.3",
    location="West Signal District"
)

crossing82 = OTDevice(
    name="Grade Crossing Controller MP 82.4",
    ip_address="192.168.50.20",
    device_type="Grade Crossing Controller",
    vendor="Wabtec",
    status="Online",
    risk_level="Medium",
    firmware_version="6.3.1",
    location="Prairie Subdivision MP 82.4"
)

crossing87 = OTDevice(
    name="Grade Crossing Controller MP 87.1",
    ip_address="192.168.50.21",
    device_type="Grade Crossing Controller",
    vendor="Wabtec",
    status="Online",
    risk_level="Medium",
    firmware_version="6.3.1",
    location="Prairie Subdivision MP 87.1"
)

switch_controller = OTDevice(
    name="Switch Machine Controller",
    ip_address="192.168.50.30",
    device_type="Switch Controller",
    vendor="Alstom",
    status="Online",
    risk_level="Low",
    firmware_version="3.8.2",
    location="Yard Lead"
)

ptc_gateway = OTDevice(
    name="PTC Radio Gateway",
    ip_address="192.168.50.40",
    device_type="PTC Communications Gateway",
    vendor="Meteorcomm",
    status="Online",
    risk_level="Medium",
    firmware_version="5.2.1",
    location="Wayside Communications Hut"
)

microwave = OTDevice(
    name="Microwave Radio",
    ip_address="192.168.50.41",
    device_type="Communications",
    vendor="Cambium",
    status="Online",
    risk_level="Low",
    firmware_version="2.5.8",
    location="Communications Tower"
)

fiber_switch = OTDevice(
    name="Fiber Distribution Switch",
    ip_address="192.168.50.42",
    device_type="Communications",
    vendor="Cisco",
    status="Online",
    risk_level="Low",
    firmware_version="17.9",
    location="Dispatch Communications Room"
)

ups = OTDevice(
    name="UPS System",
    ip_address="192.168.50.50",
    device_type="Power",
    vendor="APC",
    status="Online",
    risk_level="Low",
    firmware_version="3.2",
    location="Dispatch UPS Room"
)

generator = OTDevice(
    name="Backup Generator PLC",
    ip_address="192.168.50.51",
    device_type="PLC",
    vendor="Schneider Electric",
    status="Online",
    risk_level="Low",
    firmware_version="2.9",
    location="Generator Building"
)

fire_panel = OTDevice(
    name="Fire Detection Panel",
    ip_address="192.168.50.60",
    device_type="Safety",
    vendor="Honeywell",
    status="Online",
    risk_level="Low",
    firmware_version="5.3",
    location="Operations Control Center"
)

gas_detector = OTDevice(
    name="Hydrogen Gas Detector",
    ip_address="192.168.50.61",
    device_type="Environmental",
    vendor="Honeywell",
    status="Online",
    risk_level="Low",
    firmware_version="2.4",
    location="Battery Room"
)

flood_sensor = OTDevice(
    name="Flood Detection Sensor",
    ip_address="192.168.50.62",
    device_type="Environmental",
    vendor="Banner Engineering",
    status="Online",
    risk_level="Low",
    firmware_version="1.8",
    location="Cable Vault"
)

cabinet_sensor = OTDevice(
    name="Cabinet Intrusion Sensor",
    ip_address="192.168.50.63",
    device_type="Physical Security",
    vendor="Bosch",
    status="Online",
    risk_level="Low",
    firmware_version="3.0",
    location="Wayside Equipment Hut"
)

bridge_monitor = OTDevice(
    name="Bridge Structural Monitor",
    ip_address="192.168.50.70",
    device_type="Infrastructure",
    vendor="Mistras",
    status="Online",
    risk_level="Low",
    firmware_version="2.8",
    location="Missouri River Bridge"
)

bearing_detector = OTDevice(
    name="Hot Bearing Detector",
    ip_address="192.168.50.71",
    device_type="Infrastructure",
    vendor="HBD Inc.",
    status="Online",
    risk_level="Low",
    firmware_version="4.2",
    location="Prairie Subdivision MP 95.2"
)

engineering_ws = OTDevice(
    name="Rail Engineering Workstation",
    ip_address="192.168.50.100",
    device_type="Engineering Workstation",
    vendor="Dell",
    status="Online",
    risk_level="Medium",
    firmware_version="Windows 11 24H2",
    location="Engineering Office"
)

devices = [
    dispatch_scada,
    historian,
    jump_server,
    signal14a,
    signal14b,
    signal15c,
    crossing82,
    crossing87,
    switch_controller,
    ptc_gateway,
    microwave,
    fiber_switch,
    ups,
    generator,
    fire_panel,
    gas_detector,
    flood_sensor,
    cabinet_sensor,
    bridge_monitor,
    bearing_detector,
    engineering_ws,
]

db.add_all(devices)
db.commit()

for device in devices:
    db.refresh(device)

# RailSOC Alerts
alerts = [
    Alert(
        device_id=crossing82.id,
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
        device_id=engineering_ws.id,
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
        device_id=crossing82.id,
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