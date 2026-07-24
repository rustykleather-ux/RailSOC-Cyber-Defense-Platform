from datetime import datetime
from typing import Any, Dict, List, Optional



# =========================================================
# Severity and status helpers
# =========================================================

SEVERITY_WEIGHTS = {
    "Critical": 40,
    "High": 25,
    "Medium": 15,
    "Low": 5,
    "Info": 0,
}


def get_value(
    obj: Any,
    attribute: str,
    default: Any = None,
) -> Any:
    """
    Safely retrieve a value from either:

    - A SQLAlchemy model object
    - A Python dictionary

    This allows the AI assistant to work with database models
    and structured test data.
    """

    if obj is None:
        return default

    if isinstance(obj, dict):
        return obj.get(attribute, default)

    return getattr(obj, attribute, default)


def normalize_text(value: Any) -> str:
    """
    Convert a value into a clean lowercase string for comparisons.
    """

    if value is None:
        return ""

    return str(value).strip().lower()


def serialize_datetime(value: Any) -> Optional[str]:
    """
    Convert datetime values to ISO 8601 strings.
    """

    if value is None:
        return None

    if isinstance(value, datetime):
        return value.isoformat()

    return str(value)


# =========================================================
# Alert analysis
# =========================================================

def analyze_alerts(alerts: List[Any]) -> Dict[str, Any]:
    open_alerts = []
    critical_alerts = []
    high_alerts = []
    acknowledged_alerts = []

    for alert in alerts:
        status = normalize_text(
            get_value(alert, "status", "Open")
        )

        severity = normalize_text(
            get_value(alert, "severity", "Info")
        )

        acknowledged = bool(
            get_value(alert, "acknowledged", False)
        )

        if status != "closed":
            open_alerts.append(alert)

        if severity == "critical" and status != "closed":
            critical_alerts.append(alert)

        if severity == "high" and status != "closed":
            high_alerts.append(alert)

        if acknowledged:
            acknowledged_alerts.append(alert)

    return {
        "total": len(alerts),
        "open": len(open_alerts),
        "critical": len(critical_alerts),
        "high": len(high_alerts),
        "acknowledged": len(acknowledged_alerts),
        "items": open_alerts,
    }


# =========================================================
# Device analysis
# =========================================================

def analyze_devices(devices: List[Any]) -> Dict[str, Any]:
    offline_devices = []
    degraded_devices = []
    high_risk_devices = []

    for device in devices:
        status = normalize_text(
            get_value(device, "status", "Unknown")
        )

        risk_level = normalize_text(
            get_value(device, "risk_level", "Low")
        )

        if status == "offline":
            offline_devices.append(device)

        if status == "degraded":
            degraded_devices.append(device)

        if risk_level in {"high", "critical"}:
            high_risk_devices.append(device)

    return {
        "total": len(devices),
        "offline": len(offline_devices),
        "degraded": len(degraded_devices),
        "high_risk": len(high_risk_devices),
        "offline_items": offline_devices,
        "degraded_items": degraded_devices,
        "high_risk_items": high_risk_devices,
    }


# =========================================================
# Train analysis
# =========================================================

def analyze_trains(trains: List[Any]) -> Dict[str, Any]:
    stopped_trains = []
    restricted_trains = []
    ptc_disabled_trains = []

    for train in trains:
        status = normalize_text(
            get_value(train, "status", "Unknown")
        )

        authority = normalize_text(
            get_value(train, "authority", "")
        )

        ptc_enabled = get_value(
            train,
            "ptc_enabled",
            True,
        )

        speed = get_value(train, "speed", 0) or 0

        if status in {
            "stopped",
            "held",
            "emergency stop",
            "emergency",
        } or speed == 0:
            stopped_trains.append(train)

        if authority in {
            "restricted",
            "restricted speed",
            "stop",
            "hold",
        }:
            restricted_trains.append(train)

        if ptc_enabled is False:
            ptc_disabled_trains.append(train)

    return {
        "total": len(trains),
        "stopped": len(stopped_trains),
        "restricted": len(restricted_trains),
        "ptc_disabled": len(ptc_disabled_trains),
        "stopped_items": stopped_trains,
        "restricted_items": restricted_trains,
        "ptc_disabled_items": ptc_disabled_trains,
    }


# =========================================================
# Track-block analysis
# =========================================================

def analyze_track_blocks(
    track_blocks: List[Any],
) -> Dict[str, Any]:
    occupied_blocks = []
    communication_failures = []
    security_issues = []
    maintenance_blocks = []
    restrictive_signals = []

    for block in track_blocks:
        occupied = bool(
            get_value(block, "occupied", False)
        )

        communications_status = normalize_text(
            get_value(
                block,
                "communications_status",
                "Online",
            )
        )

        security_status = normalize_text(
            get_value(
                block,
                "security_status",
                "Healthy",
            )
        )

        maintenance = bool(
            get_value(block, "maintenance", False)
        )

        signal_aspect = normalize_text(
            get_value(block, "signal_aspect", "Clear")
        )

        if occupied:
            occupied_blocks.append(block)

        if communications_status not in {
            "online",
            "normal",
            "healthy",
        }:
            communication_failures.append(block)

        if security_status not in {
            "healthy",
            "normal",
            "low",
        }:
            security_issues.append(block)

        if maintenance:
            maintenance_blocks.append(block)

        if signal_aspect in {
            "stop",
            "restricting",
            "restricted",
            "approach",
            "dark",
            "unknown",
        }:
            restrictive_signals.append(block)

    return {
        "total": len(track_blocks),
        "occupied": len(occupied_blocks),
        "communications_issues": len(
            communication_failures
        ),
        "security_issues": len(security_issues),
        "maintenance": len(maintenance_blocks),
        "restrictive_signals": len(
            restrictive_signals
        ),
        "occupied_items": occupied_blocks,
        "communications_items": communication_failures,
        "security_items": security_issues,
        "maintenance_items": maintenance_blocks,
        "restrictive_signal_items": restrictive_signals,
    }


# =========================================================
# Vulnerability analysis
# =========================================================

def analyze_vulnerabilities(
    vulnerabilities: List[Any],
) -> Dict[str, Any]:
    open_vulnerabilities = []
    critical_vulnerabilities = []
    high_vulnerabilities = []

    for vulnerability in vulnerabilities:
        status = normalize_text(
            get_value(vulnerability, "status", "Open")
        )

        severity = normalize_text(
            get_value(vulnerability, "severity", "Low")
        )

        if status != "closed":
            open_vulnerabilities.append(vulnerability)

        if severity == "critical" and status != "closed":
            critical_vulnerabilities.append(vulnerability)

        if severity == "high" and status != "closed":
            high_vulnerabilities.append(vulnerability)

    return {
        "total": len(vulnerabilities),
        "open": len(open_vulnerabilities),
        "critical": len(critical_vulnerabilities),
        "high": len(high_vulnerabilities),
        "open_items": open_vulnerabilities,
    }


# =========================================================
# Future incident analysis
# =========================================================

def analyze_incidents(
    incidents: Optional[List[Any]],
) -> Dict[str, Any]:
    """
    Prepared for the future Incident model.

    Until the Incident table exists, pass an empty list.
    """

    incidents = incidents or []

    open_incidents = []
    critical_incidents = []
    unassigned_incidents = []

    for incident in incidents:
        status = normalize_text(
            get_value(incident, "status", "Open")
        )

        severity = normalize_text(
            get_value(incident, "severity", "Medium")
        )

        assigned_to = get_value(
            incident,
            "assigned_to",
            None,
        )

        if status not in {"closed", "resolved"}:
            open_incidents.append(incident)

        if (
            severity == "critical"
            and status not in {"closed", "resolved"}
        ):
            critical_incidents.append(incident)

        if (
            not assigned_to
            and status not in {"closed", "resolved"}
        ):
            unassigned_incidents.append(incident)

    return {
        "total": len(incidents),
        "open": len(open_incidents),
        "critical": len(critical_incidents),
        "unassigned": len(unassigned_incidents),
        "open_items": open_incidents,
    }
# =========================================================
# Single incident analysis
# =========================================================
def analyze_single_incident(incident, device_context=None):
    """
    Generate deterministic AI-assisted analysis for one incident.

    incident:
        Dictionary containing the incident fields.

    device_context:
        Optional dictionary containing device risk, vulnerability,
        and historical incident information.
    """

    if not incident:
        return {
            "error": "Incident data was not provided."
        }

    device_context = device_context or {}

    incident_id = incident.get("id")
    device = incident.get("device") or "Unknown railroad asset"
    alert_type = incident.get("alert_type") or "Unknown event"
    message = incident.get("message") or "No incident description provided."
    severity = (incident.get("severity") or "Unknown").title()
    status = incident.get("status") or "Open"
    acknowledged = bool(incident.get("acknowledged"))
    assigned_to = incident.get("assigned_to")
    mitre_technique = incident.get("mitre_technique") or "Not mapped"

    assigned = bool(
        assigned_to
        and assigned_to.strip()
        and assigned_to.lower() not in {
            "unassigned",
            "none",
            "null"
        }
    )

    is_open = status.lower() not in {
        "closed",
        "resolved"
    }

    device_risk = device_context.get("risk_level", "Unknown")
    open_vulnerabilities = device_context.get(
        "open_vulnerabilities",
        0
    )
    previous_incidents = device_context.get(
        "previous_incidents",
        0
    )
    device_status = device_context.get(
        "status",
        "Unknown"
    )
    last_seen = device_context.get("last_seen")

    alert_text = f"{alert_type} {message}".lower()
    device_text = device.lower()

    # ---------------------------------------
    # Priority
    # ---------------------------------------

    priority_map = {
        "Critical": "Critical",
        "High": "High",
        "Medium": "Moderate",
        "Low": "Low"
    }

    priority = priority_map.get(severity, "Moderate")

    if severity == "High" and open_vulnerabilities >= 2:
        priority = "Critical"

    if not assigned and severity in {"Critical", "High"}:
        priority = "Critical"

    # ---------------------------------------
    # Operational impact
    # ---------------------------------------

    impact_level = "Low"
    impact_description = (
        "No immediate railroad operational impact has been identified."
    )

    if "ptc" in device_text or "radio gateway" in device_text:
        impact_level = "High"
        impact_description = (
            "The affected asset supports Positive Train Control "
            "communications. Loss or degradation of this system may reduce "
            "the availability of safety-critical train-control messaging."
        )

    elif "signal" in device_text or "signal controller" in device_text:
        impact_level = "High"
        impact_description = (
            "The affected signal-control asset may reduce signal visibility "
            "or require railroad operations to use restrictive procedures "
            "until normal service is restored."
        )

    elif "grade crossing" in device_text:
        impact_level = "High"
        impact_description = (
            "The affected grade-crossing system may require immediate "
            "operational verification and coordination with railroad "
            "dispatch or maintenance personnel."
        )

    elif "dispatch" in device_text or "scada" in device_text:
        impact_level = "High"
        impact_description = (
            "The affected dispatch system may reduce centralized monitoring "
            "and control visibility across railroad operations."
        )

    elif "engineering workstation" in device_text:
        impact_level = "Moderate"
        impact_description = (
            "The affected engineering workstation may provide access to "
            "railroad control assets and should be evaluated for unauthorized "
            "administrative activity."
        )

    elif severity in {"Critical", "High"}:
        impact_level = "Moderate"
        impact_description = (
            "The incident may affect the reliability or availability of a "
            "railroad operational technology asset."
        )

    # ---------------------------------------
    # Likely causes
    # ---------------------------------------

    causes = []
    confidence = 55

    if any(term in alert_text for term in [
        "communication loss",
        "offline",
        "unreachable",
        "connection"
    ]):
        causes = [
            "Network communication failure",
            "Loss of power or hardware availability",
            "Firewall, routing, or switching disruption",
            "Unauthorized service interruption"
        ]
        confidence = 78

    elif any(term in alert_text for term in [
        "firmware",
        "configuration",
        "modified",
        "change"
    ]):
        causes = [
            "Unauthorized firmware or configuration change",
            "Incomplete maintenance activity",
            "Compromised engineering credentials",
            "Malicious modification of the controller"
        ]
        confidence = 82

    elif any(term in alert_text for term in [
        "failed login",
        "authentication",
        "brute force",
        "credential"
    ]):
        causes = [
            "Invalid or expired credentials",
            "Brute-force authentication activity",
            "Unauthorized account access attempt",
            "Misconfigured service or scheduled process"
        ]
        confidence = 84

    elif any(term in alert_text for term in [
        "scan",
        "reconnaissance",
        "port"
    ]):
        causes = [
            "Unauthorized network reconnaissance",
            "Asset discovery activity",
            "Vulnerability scanning",
            "Misconfigured monitoring or management tool"
        ]
        confidence = 80

    else:
        causes = [
            "Equipment or service failure",
            "Network or configuration issue",
            "Authorized maintenance activity",
            "Potential malicious activity"
        ]

    # ---------------------------------------
    # Recommended actions
    # ---------------------------------------

    recommended_actions = []

    if not acknowledged:
        recommended_actions.append(
            "Acknowledge the incident and begin analyst triage."
        )

    if not assigned:
        recommended_actions.append(
            "Assign the incident to an OT cybersecurity analyst."
        )

    if device_status.lower() != "online":
        recommended_actions.append(
            "Verify the operational status and network reachability of the "
            "affected asset."
        )

    if any(term in alert_text for term in [
        "communication loss",
        "offline",
        "connection"
    ]):
        recommended_actions.extend([
            "Review switch, router, firewall, and communications gateway logs.",
            "Verify power, cabling, radio, and network-path availability.",
            "Confirm whether dispatch or train-control communications are degraded."
        ])

    elif any(term in alert_text for term in [
        "firmware",
        "configuration",
        "modified"
    ]):
        recommended_actions.extend([
            "Compare the current firmware and configuration to the approved baseline.",
            "Review recent engineering workstation and administrator activity.",
            "Validate whether an authorized maintenance change was scheduled."
        ])

    elif any(term in alert_text for term in [
        "failed login",
        "authentication",
        "credential"
    ]):
        recommended_actions.extend([
            "Review authentication logs and identify the source account and host.",
            "Check for successful logins following the failed attempts.",
            "Temporarily restrict suspicious accounts or remote-access paths."
        ])

    elif any(term in alert_text for term in [
        "scan",
        "reconnaissance",
        "port"
    ]):
        recommended_actions.extend([
            "Identify the source system responsible for the scan.",
            "Review network flows for lateral movement or additional discovery.",
            "Confirm whether the activity came from an authorized security tool."
        ])

    else:
        recommended_actions.extend([
            "Review recent asset, network, and authentication activity.",
            "Compare the affected asset with its approved operational baseline.",
            "Document findings and escalate if operational impact is confirmed."
        ])

    if open_vulnerabilities > 0:
        recommended_actions.append(
            f"Review the {open_vulnerabilities} open vulnerability record(s) "
            "associated with this asset."
        )

    # Remove duplicates while preserving order
    recommended_actions = list(dict.fromkeys(recommended_actions))

    # ---------------------------------------
    # Executive summary
    # ---------------------------------------

    executive_summary = (
        f"A {severity.lower()}-severity {alert_type.lower()} incident was "
        f"detected on {device}. The incident is currently {status.lower()}."
    )

    if not acknowledged:
        executive_summary += " It has not yet been acknowledged."

    if not assigned:
        executive_summary += " No analyst is currently assigned."

    if open_vulnerabilities:
        executive_summary += (
            f" The affected asset also has {open_vulnerabilities} open "
            f"vulnerability record(s)."
        )

    executive_summary += f" {impact_description}"

    # ---------------------------------------
    # AI recommendation
    # ---------------------------------------

    if priority == "Critical":
        ai_recommendation = (
            "Begin immediate investigation and operational coordination. "
            "Assign an analyst, verify the asset's current state, and determine "
            "whether railroad safety or train-control functions are affected."
        )

    elif priority == "High":
        ai_recommendation = (
            "Prioritize this incident for prompt investigation. Validate the "
            "affected asset, review related logs, and confirm whether the event "
            "has broader operational consequences."
        )

    elif priority == "Moderate":
        ai_recommendation = (
            "Investigate during the current analyst workflow and monitor the "
            "asset for escalation, repeated alerts, or operational degradation."
        )

    else:
        ai_recommendation = (
            "Continue monitoring and document the incident. Escalate if related "
            "alerts or operational symptoms develop."
        )

    return {
        "incident_id": incident_id,
        "executive_summary": executive_summary,
        "priority": priority,
        "operational_impact": {
            "level": impact_level,
            "description": impact_description
        },
        "likely_cause": {
            "confidence": confidence,
            "causes": causes
        },
        "mitre": {
            "technique": mitre_technique
        },
        "recommended_actions": recommended_actions,
        "device_context": {
            "device": device,
            "status": device_status,
            "risk_level": device_risk,
            "open_vulnerabilities": open_vulnerabilities,
            "previous_incidents": previous_incidents,
            "last_seen": last_seen
        },
        "assessment": {
            "open": is_open,
            "acknowledged": acknowledged,
            "assigned": assigned,
            "assigned_to": assigned_to or "Unassigned"
        },
        "ai_recommendation": ai_recommendation
    }
# =========================================================
# Risk score
# =========================================================

def calculate_operational_risk_score(
    device_analysis: Dict[str, Any],
    alert_analysis: Dict[str, Any],
    train_analysis: Dict[str, Any],
    track_block_analysis: Dict[str, Any],
    vulnerability_analysis: Dict[str, Any],
    incident_analysis: Dict[str, Any],
) -> int:
    """
    Produce a deterministic operational risk score.

    This is currently a rule-based scoring engine rather than
    a machine-learning model or LLM.
    """

    score = 0

    score += alert_analysis["critical"] * 20
    score += alert_analysis["high"] * 10

    score += device_analysis["offline"] * 18
    score += device_analysis["degraded"] * 10
    score += device_analysis["high_risk"] * 8

    score += train_analysis["stopped"] * 12
    score += train_analysis["restricted"] * 8
    score += train_analysis["ptc_disabled"] * 20

    score += (
        track_block_analysis["communications_issues"] * 15
    )

    score += track_block_analysis["security_issues"] * 12
    score += track_block_analysis["restrictive_signals"] * 8

    score += vulnerability_analysis["critical"] * 8
    score += vulnerability_analysis["high"] * 4

    score += incident_analysis["critical"] * 20
    score += incident_analysis["open"] * 5

    return min(score, 100)


def determine_risk_level(score: int) -> str:
    if score >= 80:
        return "Critical"

    if score >= 60:
        return "High"

    if score >= 30:
        return "Medium"

    return "Low"


# =========================================================
# Findings
# =========================================================

def build_findings(
    device_analysis: Dict[str, Any],
    alert_analysis: Dict[str, Any],
    train_analysis: Dict[str, Any],
    track_block_analysis: Dict[str, Any],
    vulnerability_analysis: Dict[str, Any],
    incident_analysis: Dict[str, Any],
) -> List[Dict[str, Any]]:
    findings = []

    if alert_analysis["critical"] > 0:
        findings.append({
            "severity": "Critical",
            "category": "Cybersecurity",
            "title": "Critical security alerts detected",
            "description": (
                f'{alert_analysis["critical"]} critical alert(s) '
                "remain active."
            ),
        })

    if device_analysis["offline"] > 0:
        names = [
            get_value(device, "name", "Unknown device")
            for device in device_analysis["offline_items"]
        ]

        findings.append({
            "severity": "Critical",
            "category": "OT Availability",
            "title": "Railroad OT devices offline",
            "description": (
                "Offline devices: " + ", ".join(names)
            ),
        })

    if track_block_analysis["communications_issues"] > 0:
        names = [
            get_value(block, "name", "Unknown block")
            for block
            in track_block_analysis["communications_items"]
        ]

        findings.append({
            "severity": "Critical",
            "category": "Rail Operations",
            "title": "Track-block communications degraded",
            "description": (
                "Affected blocks: " + ", ".join(names)
            ),
        })

    if train_analysis["ptc_disabled"] > 0:
        symbols = [
            get_value(train, "symbol", "Unknown train")
            for train
            in train_analysis["ptc_disabled_items"]
        ]

        findings.append({
            "severity": "Critical",
            "category": "Train Safety",
            "title": "PTC disabled on active train records",
            "description": (
                "Affected trains: " + ", ".join(symbols)
            ),
        })

    if train_analysis["stopped"] > 0:
        symbols = [
            get_value(train, "symbol", "Unknown train")
            for train in train_analysis["stopped_items"]
        ]

        findings.append({
            "severity": "High",
            "category": "Rail Operations",
            "title": "Stopped or held trains detected",
            "description": (
                "Affected trains: " + ", ".join(symbols)
            ),
        })

    if track_block_analysis["restrictive_signals"] > 0:
        names = [
            get_value(block, "name", "Unknown block")
            for block
            in track_block_analysis[
                "restrictive_signal_items"
            ]
        ]

        findings.append({
            "severity": "High",
            "category": "Signal Operations",
            "title": "Restrictive signal aspects detected",
            "description": (
                "Affected blocks: " + ", ".join(names)
            ),
        })

    if vulnerability_analysis["critical"] > 0:
        findings.append({
            "severity": "High",
            "category": "Vulnerability Management",
            "title": "Critical vulnerabilities remain open",
            "description": (
                f'{vulnerability_analysis["critical"]} critical '
                "vulnerability record(s) require remediation."
            ),
        })

    if incident_analysis["unassigned"] > 0:
        findings.append({
            "severity": "Medium",
            "category": "Incident Management",
            "title": "Unassigned incidents detected",
            "description": (
                f'{incident_analysis["unassigned"]} open '
                "incident(s) do not have an assigned analyst."
            ),
        })

    if not findings:
        findings.append({
            "severity": "Info",
            "category": "Environment",
            "title": "No immediate operational threats detected",
            "description": (
                "Current railroad OT, train, and track-block "
                "conditions appear stable."
            ),
        })

    return findings


# =========================================================
# Recommendations
# =========================================================

def build_recommendations(
    device_analysis: Dict[str, Any],
    alert_analysis: Dict[str, Any],
    train_analysis: Dict[str, Any],
    track_block_analysis: Dict[str, Any],
    vulnerability_analysis: Dict[str, Any],
    incident_analysis: Dict[str, Any],
) -> List[Dict[str, Any]]:
    recommendations = []

    if alert_analysis["critical"] > 0:
        recommendations.append({
            "priority": 1,
            "action": (
                "Review and acknowledge all critical alerts."
            ),
            "reason": (
                "Critical alerts may represent an active threat "
                "to railroad OT operations."
            ),
        })

    if device_analysis["offline"] > 0:
        recommendations.append({
            "priority": 1,
            "action": (
                "Validate communications, power, and network "
                "reachability for offline devices."
            ),
            "reason": (
                "Offline field devices may affect dispatch, "
                "signal, crossing, or PTC visibility."
            ),
        })

    if track_block_analysis["communications_issues"] > 0:
        recommendations.append({
            "priority": 1,
            "action": (
                "Notify dispatch and verify affected track-block "
                "status through an independent channel."
            ),
            "reason": (
                "Loss of block communications can reduce trust "
                "in occupancy and signal information."
            ),
        })

    if train_analysis["ptc_disabled"] > 0:
        recommendations.append({
            "priority": 1,
            "action": (
                "Verify PTC status and apply railroad operating "
                "rules before allowing continued movement."
            ),
            "reason": (
                "Disabled PTC may increase operational safety risk."
            ),
        })

    if track_block_analysis["restrictive_signals"] > 0:
        recommendations.append({
            "priority": 2,
            "action": (
                "Correlate restrictive signal aspects with block "
                "occupancy, device health, and open alerts."
            ),
            "reason": (
                "A restrictive signal may be operationally valid "
                "or caused by a degraded cyber-physical system."
            ),
        })

    if vulnerability_analysis["critical"] > 0:
        recommendations.append({
            "priority": 2,
            "action": (
                "Prioritize remediation or compensating controls "
                "for critical OT vulnerabilities."
            ),
            "reason": (
                "Critical vulnerabilities may allow disruption "
                "or unauthorized controller changes."
            ),
        })

    if incident_analysis["unassigned"] > 0:
        recommendations.append({
            "priority": 2,
            "action": (
                "Assign ownership for all open incidents."
            ),
            "reason": (
                "Unassigned incidents are more likely to remain "
                "uninvestigated or unresolved."
            ),
        })

    if not recommendations:
        recommendations.append({
            "priority": 3,
            "action": (
                "Continue monitoring trains, track blocks, "
                "alerts, and OT device health."
            ),
            "reason": (
                "No immediate escalation conditions are present."
            ),
        })

    return sorted(
        recommendations,
        key=lambda item: item["priority"],
    )


# =========================================================
# Executive summary
# =========================================================

def build_executive_summary(
    risk_level: str,
    risk_score: int,
    device_analysis: Dict[str, Any],
    alert_analysis: Dict[str, Any],
    train_analysis: Dict[str, Any],
    track_block_analysis: Dict[str, Any],
    incident_analysis: Dict[str, Any],
) -> str:
    summary_parts = [
        (
            f"TrackSentinel currently rates the railroad "
            f"environment at {risk_level} risk "
            f"with a score of {risk_score}/100."
        )
    ]

    if alert_analysis["open"] > 0:
        summary_parts.append(
            f'{alert_analysis["open"]} open security alert(s) '
            "require review."
        )

    if device_analysis["offline"] > 0:
        summary_parts.append(
            f'{device_analysis["offline"]} OT device(s) are '
            "offline."
        )

    if train_analysis["stopped"] > 0:
        summary_parts.append(
            f'{train_analysis["stopped"]} train(s) are stopped '
            "or held."
        )

    if track_block_analysis["communications_issues"] > 0:
        summary_parts.append(
            f'{track_block_analysis["communications_issues"]} '
            "track block(s) have communications issues."
        )

    if incident_analysis["open"] > 0:
        summary_parts.append(
            f'{incident_analysis["open"]} incident(s) remain open.'
        )

    if (
        alert_analysis["open"] == 0
        and device_analysis["offline"] == 0
        and track_block_analysis[
            "communications_issues"
        ] == 0
        and incident_analysis["open"] == 0
    ):
        summary_parts.append(
            "No immediate cyber-operational disruption is detected."
        )

    return " ".join(summary_parts)


# =========================================================
# Main operations brief
# =========================================================

def build_operations_brief(
    devices: Optional[List[Any]] = None,
    alerts: Optional[List[Any]] = None,
    vulnerabilities: Optional[List[Any]] = None,
    trains: Optional[List[Any]] = None,
    track_blocks: Optional[List[Any]] = None,
    activity_logs: Optional[List[Any]] = None,
    incidents: Optional[List[Any]] = None,
) -> Dict[str, Any]:
    """
    Build the TrackSentinel AI Operations Brief.

    Current implementation:
        Deterministic rule-based reasoning engine

    Future implementation:
        The structured output from this function can be supplied
        to a local LLM for natural-language analysis.
    """

    devices = devices or []
    alerts = alerts or []
    vulnerabilities = vulnerabilities or []
    trains = trains or []
    track_blocks = track_blocks or []
    activity_logs = activity_logs or []
    incidents = incidents or []

    device_analysis = analyze_devices(devices)
    alert_analysis = analyze_alerts(alerts)
    train_analysis = analyze_trains(trains)
    track_block_analysis = analyze_track_blocks(
        track_blocks
    )
    vulnerability_analysis = analyze_vulnerabilities(
        vulnerabilities
    )
    incident_analysis = analyze_incidents(incidents)

    risk_score = calculate_operational_risk_score(
        device_analysis=device_analysis,
        alert_analysis=alert_analysis,
        train_analysis=train_analysis,
        track_block_analysis=track_block_analysis,
        vulnerability_analysis=vulnerability_analysis,
        incident_analysis=incident_analysis,
    )

    risk_level = determine_risk_level(risk_score)

    findings = build_findings(
        device_analysis=device_analysis,
        alert_analysis=alert_analysis,
        train_analysis=train_analysis,
        track_block_analysis=track_block_analysis,
        vulnerability_analysis=vulnerability_analysis,
        incident_analysis=incident_analysis,
    )

    recommendations = build_recommendations(
        device_analysis=device_analysis,
        alert_analysis=alert_analysis,
        train_analysis=train_analysis,
        track_block_analysis=track_block_analysis,
        vulnerability_analysis=vulnerability_analysis,
        incident_analysis=incident_analysis,
    )

    executive_summary = build_executive_summary(
        risk_level=risk_level,
        risk_score=risk_score,
        device_analysis=device_analysis,
        alert_analysis=alert_analysis,
        train_analysis=train_analysis,
        track_block_analysis=track_block_analysis,
        incident_analysis=incident_analysis,
    )

    recent_activity = []

    for activity in activity_logs[:10]:
        recent_activity.append({
            "id": get_value(activity, "id"),
            "timestamp": serialize_datetime(
                get_value(activity, "timestamp")
            ),
            "event_type": get_value(
                activity,
                "event_type",
                "Unknown",
            ),
            "title": get_value(
                activity,
                "title",
                "Activity",
            ),
            "severity": get_value(
                activity,
                "severity",
                "Info",
            ),
            "asset_name": get_value(
                activity,
                "asset_name",
                "",
            ),
        })

    return {
        "generated_at": datetime.utcnow().isoformat(),
        "engine": {
            "name": "TrackSentinel Operations Reasoning Engine",
            "version": "1.0.0",
            "type": "Rule-Based",
            "llm_enabled": False,
        },
        "overall_assessment": {
            "risk_score": risk_score,
            "risk_level": risk_level,
            "status": (
                "Immediate Attention Required"
                if risk_level in {"Critical", "High"}
                else "Monitoring Required"
                if risk_level == "Medium"
                else "Operational"
            ),
        },
        "executive_summary": executive_summary,
        "environment": {
            "devices": {
                "total": device_analysis["total"],
                "offline": device_analysis["offline"],
                "degraded": device_analysis["degraded"],
                "high_risk": device_analysis["high_risk"],
            },
            "alerts": {
                "total": alert_analysis["total"],
                "open": alert_analysis["open"],
                "critical": alert_analysis["critical"],
                "high": alert_analysis["high"],
                "acknowledged": alert_analysis[
                    "acknowledged"
                ],
            },
            "trains": {
                "total": train_analysis["total"],
                "stopped": train_analysis["stopped"],
                "restricted": train_analysis["restricted"],
                "ptc_disabled": train_analysis[
                    "ptc_disabled"
                ],
            },
            "track_blocks": {
                "total": track_block_analysis["total"],
                "occupied": track_block_analysis["occupied"],
                "communications_issues": (
                    track_block_analysis[
                        "communications_issues"
                    ]
                ),
                "security_issues": (
                    track_block_analysis["security_issues"]
                ),
                "maintenance": (
                    track_block_analysis["maintenance"]
                ),
                "restrictive_signals": (
                    track_block_analysis[
                        "restrictive_signals"
                    ]
                ),
            },
            "vulnerabilities": {
                "total": vulnerability_analysis["total"],
                "open": vulnerability_analysis["open"],
                "critical": vulnerability_analysis[
                    "critical"
                ],
                "high": vulnerability_analysis["high"],
            },
            "incidents": {
                "total": incident_analysis["total"],
                "open": incident_analysis["open"],
                "critical": incident_analysis["critical"],
                "unassigned": incident_analysis[
                    "unassigned"
                ],
            },
        },
        "findings": findings,
        "recommendations": recommendations,
        "recent_activity": recent_activity,
    }