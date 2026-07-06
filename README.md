# 🚆 TrackSentinel – RailSOC Training & Simulation Platform

> A full-stack Operational Technology cybersecurity platform that simulates the monitoring, protection, and incident response workflows of a modern railroad Security Operations Center.

---

## Overview

RailSOC is a portfolio project designed to demonstrate practical cybersecurity engineering skills applied to railroad Operational Technology (OT) environments.

The platform simulates a Security Operations Center (SOC) responsible for protecting critical railroad infrastructure including:

- Signal Controllers
- Grade Crossing Controllers
- Positive Train Control (PTC) Communications
- Dispatch SCADA Systems
- Engineering Workstations

Rather than serving as a simple dashboard, RailSOC demonstrates how OT cybersecurity concepts can be implemented across an end-to-end platform including backend APIs, real-time telemetry, incident management, risk scoring, and analyst workflows.

---

## Features

### 🚦 Railroad OT Asset Inventory

Maintain visibility into simulated railroad operational assets.

- Signal Controllers
- Grade Crossing Controllers
- Dispatch SCADA
- PTC Radio Gateways
- Engineering Workstations

Displays:

- Operational Status
- Firmware Version
- Risk Score
- Vendor
- Last Communication
- Asset Location

---

### 🛰 Live Asset Telemetry

Continuously monitors simulated OT infrastructure.

Examples include:

- Equipment Temperature
- Controller CPU Usage
- Memory Utilization
- Network Latency
- Active Sessions
- Authentication Activity
- Communication Status

---

### 🛡 RailSOC Incident Center

SOC-style incident management platform.

Capabilities include:

- Incident Assignment
- Acknowledgement Workflow
- Investigation Notes
- Analyst Timeline
- MITRE ATT&CK for ICS Mapping
- Incident Resolution Tracking

---

### 🚨 Security Alert Management

Generate and investigate simulated security events including:

- Unauthorized Logic Modification
- OT Network Reconnaissance
- PTC Communication Failure
- Unauthorized Engineering Login
- Signal Controller Communication Loss

---

### ⚠ Vulnerability Management

Track simulated OT vulnerabilities.

Includes:

- CVE Tracking
- CVSS Scoring
- Severity Classification
- Analyst Recommendations
- Risk Prioritization

---

### 🌐 Railroad OT Network Topology

Visual representation of the simulated OT environment.

```
Enterprise Network
        │
Enterprise / OT Firewall
        │
Dispatch SCADA Server
        │
 ├── Signal Controller
 ├── Grade Crossing Controller
 ├── PTC Radio Gateway
 └── Engineering Workstation
```

---

### 🎯 Attack Simulation Engine

Generate realistic cybersecurity scenarios for analyst training.

Current simulations include:

- Unauthorized Logic Modification
- OT Network Reconnaissance
- PTC Communication Failure
- Unauthorized Engineering Login

Future planned scenarios:

- Ransomware
- Rogue Engineering Laptop
- Insider Threat
- Unauthorized Remote Vendor Access
- Denial of Service
- Supply Chain Compromise

---

## Technology Stack

### Backend

- Python
- FastAPI
- SQLAlchemy
- SQLite
- Pydantic

### Frontend

- React
- Vite
- JavaScript
- CSS

### API

REST API providing:

- Devices
- Alerts
- Incidents
- Vulnerabilities
- Dashboard Metrics
- Plant Telemetry
- Simulation Engine

---

## Platform Architecture

```
             React Frontend
                    │
             FastAPI REST API
                    │
      ┌─────────────┴─────────────┐
      │                           │
 Simulation Engine         Risk Engine
      │                           │
 Incident Manager      Device Scoring
      │                           │
      └─────────────┬─────────────┘
                    │
                SQLite Database
```

---

## Simulated Railroad Assets

| Asset | Purpose |
|---------|---------|
| Dispatch SCADA Server | Central Operations |
| Signal Controller 14A | Signal Control |
| Grade Crossing Controller MP 82.4 | Crossing Protection |
| PTC Radio Gateway | Positive Train Control Communications |
| Rail Engineering Workstation | Engineering Maintenance |

---

## Example Workflow

1. Analyst launches simulation.

2. OT event generated.

3. Alert created.

4. Incident opened.

5. Asset risk recalculated.

6. Live telemetry changes.

7. Analyst investigates.

8. Incident assigned.

9. Investigation notes documented.

10. Incident resolved.

---

## MITRE ATT&CK for ICS

RailSOC demonstrates integration with the MITRE ATT&CK for ICS framework including techniques such as:

- T0842 Network Service Scanning
- T0859 Modify Controller Tasking
- T0881 Service Stop

---

## Current Project Status

Current capabilities include:

- OT Asset Inventory
- Risk Scoring Engine
- Live Operational Telemetry
- Incident Management
- Railroad Network Topology
- Attack Simulation
- Vulnerability Tracking
- Analyst Assignment
- Investigation Notes
- MITRE ATT&CK Mapping

---

## Planned Enhancements

- Interactive Railroad Map
- Digital Twin Visualization
- Threat Intelligence Feed
- Purple Team Exercise Mode
- Active Directory Integration
- Syslog Collection
- Zeek Integration
- Suricata Integration
- Splunk Integration
- SIEM Dashboard
- Asset History
- Configuration Drift Detection
- Multi-Site Railroad Support
- Role-Based Authentication
- Reporting Dashboard
- Executive Summary Reports

---

## Educational Purpose

RailSOC is a fictional cybersecurity engineering platform developed for portfolio, research, and educational purposes.

No actual railroad infrastructure, operational data, or proprietary systems are represented.

---

## Author

**Rusty D. Folsom**

Cybersecurity • Operational Technology • Incident Response • Infrastructure Engineering

Kansas, USA

---

## License

MIT License