# TrackSentinel  
## RailSOC Training & Simulation Platform

TrackSentinel is a railroad-focused Operational Technology cybersecurity simulation platform built to demonstrate SOC monitoring, incident response, threat intelligence, executive reporting, and purple team training workflows in a simulated rail OT environment.

This project is designed as a cybersecurity portfolio platform showing how IT, OT, safety systems, communications, and railroad operations can be monitored from a unified security operations view.

---

## Purpose

TrackSentinel simulates a railroad OT cyber defense environment where analysts can:

- Monitor railroad OT assets
- View live operational telemetry
- Launch safe purple team simulations
- Investigate alerts and incidents
- Track vulnerabilities
- Review MITRE ATT&CK for ICS mappings
- View executive security posture
- Generate leadership-style security reports

No real attacks or network traffic are generated. All scenarios are simulated for training and demonstration purposes.

---

## Key Features

### Executive Security Operations Dashboard

- Dynamic security score
- Current threat level
- Open incident counts
- Critical alert counts
- Protected asset percentage
- Simulated MTTD and MTTR
- Compliance posture indicators
- Executive recommendations
- Print/export-ready dashboard

### RailSOC Dashboard

- Environment overview
- Interactive railroad operations map
- Recent incidents
- Top active alerts
- Dynamic threat posture

### Railroad OT Asset Inventory

Includes simulated assets such as:

- Dispatch SCADA Server
- Operations Historian
- OT Jump Server
- Signal Controllers
- Grade Crossing Controllers
- PTC Radio Gateway
- Microwave Radio
- Fiber Distribution Switch
- UPS System
- Backup Generator PLC
- Fire Detection Panel
- Hydrogen Gas Detector
- Flood Detection Sensor
- Cabinet Intrusion Sensor
- Bridge Structural Monitor
- Hot Bearing Detector
- Rail Engineering Workstation

### Live Telemetry

Telemetry is grouped by operational category:

- Operations Systems
- Signal & Crossing Systems
- Communications
- Power Systems
- Safety & Environmental
- Infrastructure
- Engineering Access

Telemetry includes simulated values such as:

- CPU and memory usage
- Network latency
- Signal quality
- Packet loss
- Voltage
- Battery runtime
- Smoke level
- Gas PPM
- Water detection
- Door state
- Vibration
- Bearing temperature

### Incident Center

- View active incidents
- Acknowledge incidents
- Assign analyst ownership
- Add investigation notes
- Close incidents
- View MITRE ATT&CK for ICS mapping
- Review recommended response actions

### Investigation Workspace

- Active investigation summary
- Affected asset
- MITRE mapping
- Analyst guidance
- Evidence table
- IOC summary
- Investigation timeline
- Links to incident workflow

### Threat Intelligence Center

- Current threat posture
- MITRE ATT&CK for ICS coverage
- Simulated IOC feed
- Vendor advisory watch
- Threat posture statistics

### Purple Team Attack Library

Safe simulated attack scenarios include:

- Unauthorized PLC / controller logic modification
- OT network reconnaissance
- Rail OT denial of service simulation
- Engineering workstation credential abuse
- PTC communications failure
- Malware-like activity on engineering workstation

These scenarios update alerts, incidents, telemetry, threat level, dashboards, and investigation views.

### Vulnerability Management

- Simulated railroad OT CVEs
- Severity ratings
- CVSS scores
- Status tracking
- Remediation recommendations

### Reports

- Executive summary
- Asset health summary
- Alert summary
- Incident summary
- Vulnerability summary
- Threat posture summary
- Platform roadmap

---

## Technology Stack

### Frontend

- React
- Vite
- React Router
- CSS

### Backend

- Python
- FastAPI
- SQLAlchemy
- SQLite

### Security Concepts

- SOC operations
- OT asset monitoring
- Incident response
- Vulnerability management
- MITRE ATT&CK for ICS
- Threat intelligence
- Purple team exercises
- Executive cyber risk reporting

---

## Project Structure

```text
TrackSentinel/
├── backend/
│   ├── main.py
│   ├── models.py
│   ├── database.py
│   ├── seed.py
│   └── ot_platform.db
│
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── Header.jsx
│   │   │   ├── EnvironmentOverview.jsx
│   │   │   ├── RailroadMap.jsx
│   │   │   ├── NetworkTopology.jsx
│   │   │   ├── LivePlantStatus.jsx
│   │   │   ├── DeviceInventory.jsx
│   │   │   ├── VulnerabilityTable.jsx
│   │   │   ├── AlertsPanel.jsx
│   │   │   ├── IncidentCenter.jsx
│   │   │   └── Roadmap.jsx
│   │   │
│   │   ├── pages/
│   │   │   ├── Dashboard.jsx
│   │   │   ├── ExecutiveDashboard.jsx
│   │   │   ├── Telemetry.jsx
│   │   │   ├── Topology.jsx
│   │   │   ├── Assets.jsx
│   │   │   ├── Alerts.jsx
│   │   │   ├── Incidents.jsx
│   │   │   ├── InvestigationWorkspace.jsx
│   │   │   ├── IncidentTimeline.jsx
│   │   │   ├── ThreatIntel.jsx
│   │   │   ├── Training.jsx
│   │   │   ├── Reports.jsx
│   │   │   ├── Vulnerabilities.jsx
│   │   │   └── Settings.jsx
│   │   │
│   │   ├── services/
│   │   ├── App.jsx
│   │   └── App.css
│   │
│   └── package.json
│
└── README.md
```
---

# Installation

## Getting Started

```bash
1. Clone the repository
git clone https://github.com/YOUR-USERNAME/TrackSentinel.git
cd TrackSentinel
```
## Backend Setup
```bash
cd backend
python -m venv venv
venv\Scripts\activate
pip install fastapi uvicorn sqlalchemy
python seed.py
uvicorn main:app --reload
```
---

## Backend will run at:
http://127.0.0.1:8000

##Test Telemetry
Invoke-RestMethod http://127.0.0.1:8000/plant-status

---
## Frontend Setup
Open Second Terminal
```bash
cd frontend
npm install
npm run dev
```

## Frontend will run at:
http://localhost:5173

---
##Example Simulation Workflow

1. Open TrackSentinel.
2. to Training Exercises.
3. Launch a purple team scenario.
4. Watch the environment update:
        -Threat level changes
        -Alerts are created
        -Incidents appear
        -Telemetry changes
        -Digital twin map updates
        -Investigation workspace populates
5. Open the Incident Center.
6. Acknowledge, assign, document, and close the incident.
7. Restore the operational baseline.

---
## Simulated MITRE ATT&CK for ICS Techniques

Examples used in the platform:

| Scenario                          | MITRE ATT&CK for ICS              |
| --------------------------------- | --------------------------------- |
| Network Reconnaissance            | T0842 - Network Service Scanning  |
| Unauthorized Logic Modification   | T0859 - Modify Controller Tasking |
| PTC Radio Failure                 | T0881 - Service Stop              |
| Unauthorized Engineering Login    | T0812 - Valid Accounts            |
| Denial of Service Simulation      | T0814 - Denial of Service         |
| Malware-like Engineering Activity | T0809 - Data Destruction          |

---
## Screenshots

![Executive Dashboard](screenshots/executive-dashboard.png)
![RailSOC Dashboard](screenshots/dashboard.png)
![Live Telemetry](screenshots/live-telemetry.png)
![Incident Center](screenshots/incident-center.png)
![Investigation Workspace](screenshots/investigation-workspace.png)
![Purple Team Library](screenshots/purple-team-library.png)

---
## Roadmap
TrackSentinel v1.0
Railroad OT asset inventory
Live telemetry
Incident management
Executive dashboard
Threat intelligence
Investigation workspace
Purple team attack library
MITRE ATT&CK for ICS mapping
Vulnerability management
Reports and settings pages

##Future TrackSentinel v2.0
Planned future enhancements:

Moving train digital twin
Signal indication logic
Animated grade crossings
Location-based asset clustering
Multi-subdivision monitoring
Role-based access control
Audit logging
IOC database
Threat hunting interface
Docker Compose deployment
AI-assisted incident summaries
PDF incident report generation

---
## Safety Notice

TrackSentinel is a simulated cybersecurity training and portfolio project.

It does not perform real exploitation, packet flooding, denial of service activity, malware execution, 
or unauthorized access. All attacks, telemetry, indicators, alerts, and incidents 
are simulated for educational and demonstration purposes only.

---
## Author
Created by Rusty Folsom as a railroad OT cybersecurity portfolio project.

Focus areas:

Operational Technology cybersecurity
Railroad cyber defense
SOC operations
Incident response
Threat intelligence
Purple team training
Executive cyber risk reporting