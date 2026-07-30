"""Simulation-only network visibility and control services.

This module intentionally contains no host discovery, packet I/O, shell execution,
or outbound HTTP. It projects TrackSentinel state into a simulated network graph.
"""

import heapq
import json
import math
from datetime import datetime, timezone

from models import (
    Alert,
    Incident,
    NetworkConnection,
    NetworkNode,
    NetworkPath,
    NetworkTrafficEvent,
    NetworkZone,
)
from services.dispatch_service import DispatchValidationError, perform_recovery_action
from services.timeline_service import record_event


DOWN_STATUSES = {"down", "blocked", "offline"}
ALLOWED_NODE_ACTIONS = {"isolate", "restore", "investigate"}
ALLOWED_CONNECTION_ACTIONS = {"fail", "restore"}
ALLOWED_SIMULATIONS = {
    "high_latency",
    "packet_loss",
    "fiber_failure",
    "radio_outage",
    "unauthorized_remote_access",
    "network_scan",
    "lateral_movement",
    "firewall_block",
    "restore_baseline",
}


class NetworkValidationError(ValueError):
    def __init__(self, message, status_code=400):
        super().__init__(message)
        self.status_code = status_code


def utc_now():
    return datetime.now(timezone.utc)


def _loads(value, fallback):
    try:
        return json.loads(value or "")
    except (TypeError, json.JSONDecodeError):
        return fallback


def _iso(value):
    if not value:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.isoformat()


def _node_state(device_status):
    normalized = (device_status or "Unknown").strip().lower()
    return {
        "online": "Healthy",
        "healthy": "Healthy",
        "operational": "Healthy",
        "warning": "Warning",
        "safe mode": "Warning",
        "degraded": "Degraded",
        "severe": "Degraded",
        "offline": "Offline",
        "compromised": "Compromised",
        "isolated": "Isolated",
    }.get(normalized, "Unknown")


def synchronize_linked_nodes(db):
    """Mirror approved TrackSentinel OT state; never inspect a real network."""
    nodes = db.query(NetworkNode).filter(NetworkNode.ot_device_id.isnot(None)).all()
    for node in nodes:
        device = node.ot_device
        if not device:
            continue
        node.ip_address = device.ip_address
        node.vendor = device.vendor
        node.model = device.model
        node.firmware_version = device.firmware_version
        node.risk_level = device.risk_level
        node.criticality = device.criticality
        node.location = device.location
        node.latitude = device.latitude
        node.longitude = device.longitude
        node.last_seen = device.last_seen
        node.status = _node_state(device.status)
        metadata = _loads(node.metadata_json, {})
        node.health = (
            metadata.get("dependency_impact", {}).get("label")
            or _node_state(device.status)
        )
    db.flush()


def serialize_zone(zone):
    return {
        "id": zone.id,
        "name": zone.name,
        "zone_type": zone.zone_type,
        "description": zone.description,
        "trust_level": zone.trust_level,
        "color_key": zone.color_key,
        "security_policy": zone.security_policy,
        "location": zone.location,
    }


def serialize_node(node, *, include_details=False):
    result = {
        "id": node.id,
        "zone_id": node.zone_id,
        "ot_device_id": node.ot_device_id,
        "name": node.name,
        "display_name": node.display_name,
        "node_type": node.node_type,
        "device_type": node.device_type,
        "security_zone": node.security_zone,
        "network_segment": node.network_segment,
        "ip_address": node.ip_address,
        "hostname": node.hostname,
        "operating_system": node.operating_system,
        "vendor": node.vendor,
        "model": node.model,
        "firmware_version": node.firmware_version,
        "protocol": node.protocol,
        "status": node.status,
        "health": node.health,
        "risk_level": node.risk_level,
        "criticality": node.criticality,
        "location": node.location,
        "latitude": node.latitude,
        "longitude": node.longitude,
        "last_seen": _iso(node.last_seen),
        "is_managed": node.is_managed,
        "is_ot_asset": node.is_ot_asset,
        "position": {"x": node.layout_x or 0, "y": node.layout_y or 0},
        "metadata": _loads(node.metadata_json, {}),
    }
    if include_details:
        connections = list(node.outgoing_connections) + list(node.incoming_connections)
        result["connected_node_ids"] = sorted({
            item.target_node_id if item.source_node_id == node.id else item.source_node_id
            for item in connections
        })
        result["active_alerts"] = sum(
            alert.status == "Open" for alert in (node.ot_device.alerts if node.ot_device else [])
        )
        result["open_incidents"] = 0
    return result


def serialize_connection(connection):
    return {
        "id": connection.id,
        "source_node_id": connection.source_node_id,
        "target_node_id": connection.target_node_id,
        "source_name": connection.source_node.display_name,
        "target_name": connection.target_node.display_name,
        "connection_type": connection.connection_type,
        "protocol": connection.protocol,
        "port": connection.port,
        "direction": connection.direction,
        "bandwidth_mbps": connection.bandwidth_mbps,
        "latency_ms": round(connection.latency_ms or 0, 2),
        "packet_loss_percent": round(connection.packet_loss_percent or 0, 3),
        "status": connection.status,
        "encrypted": connection.encrypted,
        "security_boundary_crossing": connection.security_boundary_crossing,
        "last_activity": _iso(connection.last_activity),
        "risk_level": connection.risk_level,
        "metadata": _loads(connection.metadata_json, {}),
    }


def serialize_event(event):
    return {
        "id": event.id,
        "timestamp": _iso(event.timestamp),
        "source_node_id": event.source_node_id,
        "target_node_id": event.target_node_id,
        "connection_id": event.connection_id,
        "network_path_id": event.network_path_id,
        "protocol": event.protocol,
        "port": event.port,
        "bytes_sent": event.bytes_sent,
        "bytes_received": event.bytes_received,
        "severity": event.severity,
        "event_type": event.event_type,
        "description": event.description,
        "related_alert_id": event.related_alert_id,
        "related_incident_id": event.related_incident_id,
        "is_suspicious": event.is_suspicious,
    }


def get_topology(db, event_limit=100):
    synchronize_linked_nodes(db)
    nodes = db.query(NetworkNode).order_by(NetworkNode.id).all()
    connections = db.query(NetworkConnection).order_by(NetworkConnection.id).all()
    events = (
        db.query(NetworkTrafficEvent)
        .order_by(NetworkTrafficEvent.timestamp.desc(), NetworkTrafficEvent.id.desc())
        .limit(max(1, min(int(event_limit), 500)))
        .all()
    )
    return {
        "schema_version": "1.0",
        "simulation_only": True,
        "generated_at": _iso(utc_now()),
        "zones": [serialize_zone(zone) for zone in db.query(NetworkZone).order_by(NetworkZone.id)],
        "nodes": [serialize_node(node) for node in nodes],
        "connections": [serialize_connection(item) for item in connections],
        "events": [serialize_event(item) for item in events],
        "summary": {
            "nodes": len(nodes),
            "connections": len(connections),
            "degraded_nodes": sum(node.status not in {"Healthy", "Online"} for node in nodes),
            "affected_links": sum(item.status != "Healthy" for item in connections),
            "suspicious_events": sum(item.is_suspicious for item in events),
        },
    }


def get_node(db, node_id):
    synchronize_linked_nodes(db)
    node = db.get(NetworkNode, node_id)
    if not node:
        raise NetworkValidationError(f"Network node {node_id} was not found.", 404)
    result = serialize_node(node, include_details=True)
    recent = db.query(NetworkTrafficEvent).filter(
        (NetworkTrafficEvent.source_node_id == node.id)
        | (NetworkTrafficEvent.target_node_id == node.id)
    ).order_by(NetworkTrafficEvent.timestamp.desc()).limit(25).all()
    result["recent_traffic"] = [serialize_event(item) for item in recent]
    if node.ot_device_id:
        result["open_incidents"] = db.query(Incident).filter(
            Incident.device_id == node.ot_device_id,
            Incident.status != "Closed",
        ).count()
    return result


def get_connection(db, connection_id):
    connection = db.get(NetworkConnection, connection_id)
    if not connection:
        raise NetworkValidationError(
            f"Network connection {connection_id} was not found.", 404
        )
    result = serialize_connection(connection)
    events = db.query(NetworkTrafficEvent).filter(
        NetworkTrafficEvent.connection_id == connection.id
    ).order_by(NetworkTrafficEvent.timestamp.desc()).limit(50).all()
    result["recent_traffic"] = [serialize_event(item) for item in events]
    return result


def list_events(
    db, *, limit=100, node_id=None, connection_id=None, severity=None,
    protocol=None, event_type=None, incident_id=None,
):
    query = db.query(NetworkTrafficEvent)
    if node_id is not None:
        query = query.filter(
            (NetworkTrafficEvent.source_node_id == node_id)
            | (NetworkTrafficEvent.target_node_id == node_id)
        )
    if connection_id is not None:
        query = query.filter(NetworkTrafficEvent.connection_id == connection_id)
    if severity:
        query = query.filter(NetworkTrafficEvent.severity == severity)
    if protocol:
        query = query.filter(NetworkTrafficEvent.protocol == protocol)
    if event_type:
        query = query.filter(NetworkTrafficEvent.event_type == event_type)
    if incident_id is not None:
        query = query.filter(NetworkTrafficEvent.related_incident_id == incident_id)
    return [
        serialize_event(item)
        for item in query.order_by(
            NetworkTrafficEvent.timestamp.desc(), NetworkTrafficEvent.id.desc()
        ).limit(max(1, min(int(limit), 500))).all()
    ]


def _find_path(db, source_id, destination_id):
    if not db.get(NetworkNode, source_id):
        raise NetworkValidationError(f"Source node {source_id} was not found.", 404)
    if not db.get(NetworkNode, destination_id):
        raise NetworkValidationError(
            f"Destination node {destination_id} was not found.", 404
        )
    adjacency = {}
    for connection in db.query(NetworkConnection).all():
        if (connection.status or "").lower() in DOWN_STATUSES:
            continue
        adjacency.setdefault(connection.source_node_id, []).append(
            (connection.target_node_id, connection)
        )
        if (connection.direction or "").lower() != "unidirectional":
            adjacency.setdefault(connection.target_node_id, []).append(
                (connection.source_node_id, connection)
            )
    queue = [(0.0, source_id, [source_id], [])]
    best = {}
    while queue:
        cost, node_id, hops, links = heapq.heappop(queue)
        if node_id in best and best[node_id] <= cost:
            continue
        best[node_id] = cost
        if node_id == destination_id:
            return hops, links
        for neighbor, link in adjacency.get(node_id, []):
            heapq.heappush(
                queue,
                (cost + max(0.0, link.latency_ms or 0.0), neighbor,
                 hops + [neighbor], links + [link]),
            )
    raise NetworkValidationError(
        f"No available simulated path exists between nodes {source_id} and "
        f"{destination_id}.",
        409,
    )


def trace_path(db, source_id, destination_id, name=None):
    hops, links = _find_path(db, source_id, destination_id)
    nodes = {node.id: node for node in db.query(NetworkNode).filter(NetworkNode.id.in_(hops))}
    total_latency = sum(link.latency_ms or 0 for link in links)
    success_probability = math.prod(
        1 - min(100.0, max(0.0, link.packet_loss_percent or 0)) / 100
        for link in links
    )
    total_loss = (1 - success_probability) * 100
    states = {(link.status or "Healthy").lower() for link in links}
    path_status = "Degraded" if states - {"healthy"} else "Healthy"
    path = NetworkPath(
        name=name or f"{nodes[source_id].display_name} to {nodes[destination_id].display_name}",
        source_node_id=source_id,
        destination_node_id=destination_id,
        hops_json=json.dumps(hops),
        path_status=path_status,
        total_latency_ms=total_latency,
        total_packet_loss=total_loss,
        updated_at=utc_now(),
    )
    db.add(path)
    db.flush()
    record_event(
        db,
        event_type="network_path_traced",
        title="Simulated network path traced",
        message=f"{path.name}: {len(hops)} hops, {total_latency:.1f} ms latency.",
        metadata={"network_path_id": path.id, "hops": hops, "simulation_only": True},
    )
    return {
        "id": path.id,
        "name": path.name,
        "source_node_id": source_id,
        "destination_node_id": destination_id,
        "hops": [
            {
                "id": node_id,
                "name": nodes[node_id].display_name,
                "zone": nodes[node_id].security_zone,
                "node_type": nodes[node_id].node_type,
                "suspicious": nodes[node_id].status == "Compromised",
            }
            for node_id in hops
        ],
        "connection_ids": [link.id for link in links],
        "zones_crossed": list(dict.fromkeys(nodes[node_id].security_zone for node_id in hops)),
        "firewalls_crossed": [
            nodes[node_id].display_name for node_id in hops
            if nodes[node_id].node_type == "Firewall"
        ],
        "protocols": list(dict.fromkeys(link.protocol for link in links if link.protocol)),
        "total_latency_ms": round(total_latency, 2),
        "total_packet_loss": round(total_loss, 4),
        "path_status": path_status,
        "degraded_connection_ids": [
            link.id for link in links if link.status != "Healthy"
        ],
    }


def save_layout(db, positions):
    if not isinstance(positions, list) or len(positions) > 250:
        raise NetworkValidationError("Layout must contain at most 250 node positions.")
    updated = 0
    for item in positions:
        node = db.get(NetworkNode, item.get("id"))
        if not node:
            raise NetworkValidationError(
                f"Network node {item.get('id')} was not found.", 404
            )
        x, y = item.get("x"), item.get("y")
        if not all(isinstance(value, (int, float)) and math.isfinite(value) for value in (x, y)):
            raise NetworkValidationError("Layout coordinates must be finite numbers.")
        if abs(x) > 100000 or abs(y) > 100000:
            raise NetworkValidationError("Layout coordinates are outside allowed bounds.")
        node.layout_x, node.layout_y = float(x), float(y)
        updated += 1
    record_event(
        db,
        event_type="network_layout_saved",
        title="Network map layout saved",
        message=f"Saved {updated} simulated network node positions.",
    )
    return {"updated": updated}


def _traffic_event(
    db, *, source, target, event_type, description, severity="Info",
    suspicious=False, connection=None, alert_id=None, incident_id=None,
):
    event = NetworkTrafficEvent(
        timestamp=utc_now(),
        source_node_id=source.id if source else None,
        target_node_id=target.id if target else None,
        connection_id=connection.id if connection else None,
        protocol=(connection.protocol if connection else source.protocol if source else ""),
        port=connection.port if connection else None,
        bytes_sent=4096 if suspicious else 16384,
        bytes_received=1024 if suspicious else 32768,
        severity=severity,
        event_type=event_type,
        description=description,
        related_alert_id=alert_id,
        related_incident_id=incident_id,
        is_suspicious=suspicious,
    )
    db.add(event)
    db.flush()
    return event


def _create_network_incident(db, source, target, event_type, description, severity):
    device = target.ot_device if target and target.ot_device else (
        source.ot_device if source and source.ot_device else None
    )
    alert = Alert(
        device_id=device.id if device else None,
        severity=severity,
        alert_type=event_type.replace("_", " ").title(),
        message=description,
    )
    db.add(alert)
    db.flush()
    incident = Incident(
        alert_id=alert.id,
        device_id=device.id if device else None,
        severity=severity,
        device=device.name if device else (target or source).display_name,
        alert_type=alert.alert_type,
        message=description,
        status="Open",
        acknowledged=False,
        assigned_to="Unassigned",
        investigation_notes="Generated by simulated Network Visibility telemetry.",
        mitre_technique="Simulated network behavior",
    )
    db.add(incident)
    db.flush()
    return alert, incident


def _set_dependency_impact(node, source, label):
    metadata = _loads(node.metadata_json, {})
    metadata["dependency_impact"] = {
        "source_node_id": source.id,
        "source": source.display_name,
        "label": label,
    }
    node.metadata_json = json.dumps(metadata)
    if node.status not in {"Compromised", "Isolated", "Offline"}:
        node.health = label
        node.status = "Degraded"
    node.risk_level = "High" if node.risk_level == "Low" else node.risk_level


def propagate_dependency_impact(db, connection):
    impacted = []
    for node in (connection.source_node, connection.target_node):
        other = (
            connection.target_node
            if node.id == connection.source_node_id
            else connection.source_node
        )
        if other.node_type in {"Firewall", "Router", "Radio", "SCADA"}:
            _set_dependency_impact(node, other, "Loss of Communications")
            impacted.append(node.id)
    return impacted


def apply_node_action(db, node_id, action):
    action = (action or "").strip().lower()
    if action not in ALLOWED_NODE_ACTIONS:
        raise NetworkValidationError(f"Unsupported network node action: {action}.", 403)
    node = db.get(NetworkNode, node_id)
    if not node:
        raise NetworkValidationError(f"Network node {node_id} was not found.", 404)
    try:
        if action in {"isolate", "restore"} and node.ot_device_id:
            perform_recovery_action(
                db,
                {
                    "action_type": (
                        "ISOLATE_DEVICE" if action == "isolate" else "RESTORE_KNOWN_GOOD"
                    ),
                    "target_id": node.ot_device_id,
                },
            )
            synchronize_linked_nodes(db)
        elif action == "isolate":
            node.status, node.health, node.risk_level = "Isolated", "Isolated", "High"
        elif action == "restore":
            node.status, node.health, node.risk_level = "Healthy", "Healthy", "Low"
            metadata = _loads(node.metadata_json, {})
            metadata.pop("dependency_impact", None)
            node.metadata_json = json.dumps(metadata)
        else:
            node.risk_level = "High" if node.risk_level == "Critical" else "Medium"
            metadata = _loads(node.metadata_json, {})
            metadata["under_investigation"] = True
            node.metadata_json = json.dumps(metadata)
    except DispatchValidationError as exc:
        raise NetworkValidationError(str(exc), getattr(exc, "status_code", 400)) from exc
    record_event(
        db,
        event_type=f"network_node_{action}",
        title=f"Network node {action}",
        message=f"{node.display_name} was marked {action} in the simulation.",
        device_id=node.ot_device_id,
        asset_name=node.display_name,
        metadata={"network_node_id": node.id, "simulation_only": True},
    )
    return serialize_node(node, include_details=True)


def apply_connection_action(db, connection_id, action):
    action = (action or "").strip().lower()
    if action not in ALLOWED_CONNECTION_ACTIONS:
        raise NetworkValidationError(
            f"Unsupported network connection action: {action}.", 403
        )
    connection = db.get(NetworkConnection, connection_id)
    if not connection:
        raise NetworkValidationError(
            f"Network connection {connection_id} was not found.", 404
        )
    metadata = _loads(connection.metadata_json, {})
    if action == "fail":
        connection.status = "Down"
        connection.packet_loss_percent = 100.0
        impacted = propagate_dependency_impact(db, connection)
    else:
        connection.status = metadata.get("baseline_status", "Healthy")
        connection.latency_ms = metadata.get(
            "baseline_latency_ms", connection.latency_ms
        )
        connection.packet_loss_percent = metadata.get(
            "baseline_packet_loss_percent", 0.0
        )
        impacted = []
    connection.last_activity = utc_now()
    event = _traffic_event(
        db,
        source=connection.source_node,
        target=connection.target_node,
        connection=connection,
        event_type=f"connection_{action}",
        description=(
            f"Simulated connection between {connection.source_node.display_name} "
            f"and {connection.target_node.display_name} was {action}ed."
        ),
        severity="High" if action == "fail" else "Info",
        suspicious=False,
    )
    record_event(
        db,
        event_type=f"network_connection_{action}",
        title=f"Network connection {action}",
        message=event.description,
        metadata={
            "network_connection_id": connection.id,
            "impacted_node_ids": impacted,
            "simulation_only": True,
        },
    )
    return serialize_connection(connection)


def _named_node(db, name):
    node = db.query(NetworkNode).filter(NetworkNode.name == name).one_or_none()
    if not node:
        raise NetworkValidationError(f"Seeded network node '{name}' was not found.", 409)
    return node


def _connection_between(db, first, second):
    return db.query(NetworkConnection).filter(
        (
            (NetworkConnection.source_node_id == first.id)
            & (NetworkConnection.target_node_id == second.id)
        )
        | (
            (NetworkConnection.source_node_id == second.id)
            & (NetworkConnection.target_node_id == first.id)
        )
    ).first()


def run_simulation(db, simulation_type, source_node_id=None, target_node_id=None):
    simulation_type = (simulation_type or "").strip().lower()
    if simulation_type not in ALLOWED_SIMULATIONS:
        raise NetworkValidationError(
            f"Unsupported network simulation: {simulation_type}.", 403
        )
    if simulation_type == "restore_baseline":
        return restore_baseline(db)

    source = db.get(NetworkNode, source_node_id) if source_node_id else None
    target = db.get(NetworkNode, target_node_id) if target_node_id else None
    if source_node_id and not source:
        raise NetworkValidationError(f"Source node {source_node_id} was not found.", 404)
    if target_node_id and not target:
        raise NetworkValidationError(f"Target node {target_node_id} was not found.", 404)

    suspicious = simulation_type in {
        "unauthorized_remote_access", "network_scan", "lateral_movement"
    }
    severity = "High" if suspicious else "Medium"
    connection = None
    if simulation_type == "fiber_failure":
        source, target = _named_node(db, "OT Firewall"), _named_node(db, "Fiber Backbone Router")
        connection = _connection_between(db, source, target)
        apply_connection_action(db, connection.id, "fail")
    elif simulation_type == "radio_outage":
        source, target = _named_node(db, "PTC Radio Gateway"), _named_node(db, "Radio Tower Sector 3")
        connection = _connection_between(db, source, target)
        apply_connection_action(db, connection.id, "fail")
    elif simulation_type == "firewall_block":
        source, target = _named_node(db, "Corporate Firewall"), _named_node(db, "Dispatch Firewall")
        connection = _connection_between(db, source, target)
        connection.status = "Blocked"
        connection.packet_loss_percent = 100
        propagate_dependency_impact(db, connection)
    elif simulation_type in {"high_latency", "packet_loss"}:
        connection = db.get(NetworkConnection, target_node_id) if target_node_id else (
            db.query(NetworkConnection).filter(
                NetworkConnection.connection_type == "Backbone"
            ).first()
        )
        if not connection:
            raise NetworkValidationError("A target connection is required.", 422)
        source, target = connection.source_node, connection.target_node
        if simulation_type == "high_latency":
            connection.latency_ms = max(250, (connection.latency_ms or 0) * 10)
            connection.status = "High latency"
        else:
            connection.packet_loss_percent = 35
            connection.status = "Packet loss"
    else:
        source = source or _named_node(
            db,
            "Simulated Threat Actor Infrastructure"
            if simulation_type != "lateral_movement"
            else "Engineering Workstation",
        )
        target = target or _named_node(
            db,
            "Remote Access Gateway"
            if simulation_type == "unauthorized_remote_access"
            else "Signal Controller 14A",
        )
        if simulation_type == "lateral_movement":
            path_result = trace_path(db, source.id, target.id, "Simulated lateral movement")
            connection = db.get(NetworkConnection, path_result["connection_ids"][-1])
        else:
            connection = _connection_between(db, source, target)
        target.risk_level = "High" if target.risk_level != "Critical" else "Critical"

    description = (
        f"TrackSentinel simulated {simulation_type.replace('_', ' ')} from "
        f"{source.display_name} to {target.display_name}."
    )
    alert = incident = None
    if suspicious:
        alert, incident = _create_network_incident(
            db, source, target, simulation_type, description, severity
        )
    event = _traffic_event(
        db,
        source=source,
        target=target,
        connection=connection,
        event_type=simulation_type,
        description=description,
        severity=severity,
        suspicious=suspicious,
        alert_id=alert.id if alert else None,
        incident_id=incident.id if incident else None,
    )
    record_event(
        db,
        event_type=f"network_{simulation_type}",
        title=simulation_type.replace("_", " ").title(),
        message=description,
        severity=severity,
        device_id=target.ot_device_id,
        incident_id=incident.id if incident else None,
        metadata={
            "network_event_id": event.id,
            "source_node_id": source.id,
            "target_node_id": target.id,
            "connection_id": connection.id if connection else None,
            "simulation_only": True,
        },
    )
    return {
        "simulation_type": simulation_type,
        "event": serialize_event(event),
        "incident_id": incident.id if incident else None,
        "topology": get_topology(db, event_limit=25),
    }


def restore_baseline(db):
    for connection in db.query(NetworkConnection).all():
        metadata = _loads(connection.metadata_json, {})
        connection.status = metadata.get("baseline_status", "Healthy")
        connection.latency_ms = metadata.get(
            "baseline_latency_ms", connection.latency_ms
        )
        connection.packet_loss_percent = metadata.get(
            "baseline_packet_loss_percent", 0.0
        )
        connection.risk_level = "Low"
        connection.last_activity = utc_now()
    for node in db.query(NetworkNode).all():
        metadata = _loads(node.metadata_json, {})
        metadata.pop("dependency_impact", None)
        metadata.pop("under_investigation", None)
        node.metadata_json = json.dumps(metadata)
        if not node.ot_device_id:
            node.status, node.health, node.risk_level = "Healthy", "Healthy", "Low"
    synchronize_linked_nodes(db)
    record_event(
        db,
        event_type="network_baseline_restored",
        title="Network simulation baseline restored",
        message="All simulated network links and dependency impacts were restored.",
        metadata={"simulation_only": True},
    )
    return {"simulation_type": "restore_baseline", "topology": get_topology(db, 25)}


def websocket_payload(db):
    snapshot = get_topology(db, event_limit=50)
    return {
        "type": "network_snapshot",
        "schema_version": snapshot["schema_version"],
        "simulation_only": True,
        "generated_at": snapshot["generated_at"],
        "topology": snapshot,
    }

