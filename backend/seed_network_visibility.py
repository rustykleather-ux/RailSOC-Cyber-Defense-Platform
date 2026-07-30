"""Idempotent seed data for the simulated TrackSentinel network."""

import json

from models import NetworkConnection, NetworkNode, NetworkZone, OTDevice


ZONES = [
    ("Enterprise IT", "IT", "Corporate services and analyst systems", "Medium", "#3b82f6"),
    ("Dispatch Center", "Operations", "Rail dispatch applications and workstations", "High", "#8b5cf6"),
    ("Railroad OT", "OT", "Wayside and train-control systems", "Restricted", "#f59e0b"),
    ("Communications", "Communications", "Simulated railroad WAN and radio transport", "High", "#06b6d4"),
    ("Security", "Security", "Monitoring and controlled administrative access", "Restricted", "#22c55e"),
    ("External / Untrusted", "External", "Simulated systems outside railroad trust", "Untrusted", "#ef4444"),
]


NODES = [
    # name, zone, type, device type, ip, host, protocol, criticality, managed, OT link
    ("Corporate Firewall", "Enterprise IT", "Firewall", "Firewall", "10.10.0.1", "corp-fw-01", "HTTPS", "Critical", True, None),
    ("Active Directory Domain Controller", "Enterprise IT", "Server", "Identity Server", "10.10.1.10", "ad-01", "LDAP/Kerberos", "High", True, None),
    ("Security Information and Event Management Server", "Enterprise IT", "Server", "SIEM", "10.10.1.20", "siem-01", "Syslog", "High", True, None),
    ("Email Gateway", "Enterprise IT", "Server", "Email Gateway", "10.10.1.30", "mail-gw-01", "SMTP", "Medium", True, None),
    ("Analyst Workstation", "Enterprise IT", "Workstation", "Security Workstation", "10.10.2.15", "soc-ws-01", "HTTPS", "Medium", True, None),
    ("Backup Server", "Enterprise IT", "Server", "Backup Server", "10.10.1.40", "backup-01", "SMB", "High", True, None),
    ("Dispatch Firewall", "Dispatch Center", "Firewall", "Firewall", "10.20.0.1", "dispatch-fw-01", "HTTPS", "Critical", True, None),
    ("Dispatch SCADA Server", "Dispatch Center", "SCADA", "Dispatch SCADA", "192.168.50.5", "scada-01", "DNP3", "Critical", True, "Dispatch SCADA Server"),
    ("Dispatcher Workstation 1", "Dispatch Center", "Workstation", "Dispatcher Workstation", "10.20.2.11", "dispatch-ws-01", "HTTPS", "High", True, None),
    ("Dispatcher Workstation 2", "Dispatch Center", "Workstation", "Dispatcher Workstation", "10.20.2.12", "dispatch-ws-02", "HTTPS", "High", True, None),
    ("Operations Database", "Dispatch Center", "Server", "Database", "10.20.1.20", "ops-db-01", "PostgreSQL", "Critical", True, None),
    ("Historian", "Dispatch Center", "Server", "Historian", "192.168.50.6", "historian-01", "OPC-UA", "High", True, "Operations Historian"),
    ("Application Server", "Dispatch Center", "Server", "Application Server", "10.20.1.30", "dispatch-app-01", "HTTPS", "High", True, None),
    ("Signal Controller 14A", "Railroad OT", "Controller", "Signal Controller", "192.168.50.10", "sig-14a", "DNP3", "Critical", True, "Signal Controller 14A"),
    ("Grade Crossing Controller MP 82.4", "Railroad OT", "Controller", "Grade Crossing Controller", "192.168.50.20", "gx-82-4", "DNP3", "Critical", True, "Grade Crossing Controller MP 82.4"),
    ("Switch Controller 9", "Railroad OT", "Controller", "Switch Controller", "192.168.50.30", "sw-09", "DNP3", "Critical", True, "Switch Machine Controller"),
    ("PTC Radio Gateway", "Railroad OT", "Radio", "PTC Communications Gateway", "192.168.50.40", "ptc-gw-01", "PTC", "Critical", True, "PTC Radio Gateway"),
    ("Wayside Interface Unit", "Railroad OT", "Controller", "Wayside Interface Unit", "192.168.50.80", "wiu-82", "DNP3", "High", True, None),
    ("Track Circuit Controller", "Railroad OT", "Controller", "Track Circuit Controller", "192.168.50.81", "tc-82", "DNP3", "Critical", True, None),
    ("Engineering Workstation", "Railroad OT", "Workstation", "Engineering Workstation", "192.168.50.100", "rail-eng-01", "RDP", "High", True, "Rail Engineering Workstation"),
    ("Maintenance Laptop", "Railroad OT", "Workstation", "Maintenance Laptop", "192.168.50.110", "maint-lt-01", "SSH", "Medium", True, None),
    ("Fiber Backbone Router", "Communications", "Router", "Backbone Router", "172.20.0.1", "fiber-rtr-01", "OSPF", "Critical", True, None),
    ("Radio Tower Sector 3", "Communications", "Radio", "Radio Tower", "172.20.3.1", "radio-s3", "PTC", "Critical", True, None),
    ("Microwave Link", "Communications", "Radio", "Microwave Radio", "192.168.50.41", "micro-01", "Microwave", "High", True, "Microwave Radio"),
    ("LTE Gateway", "Communications", "Router", "LTE Gateway", "172.20.4.1", "lte-gw-01", "IPsec", "High", True, None),
    ("Network Management Server", "Communications", "Server", "Network Management", "172.20.1.10", "nms-01", "SNMP", "High", True, None),
    ("Remote Access Gateway", "Communications", "Firewall", "Remote Access Gateway", "172.20.2.1", "remote-gw-01", "VPN", "Critical", True, None),
    ("IDS Sensor", "Security", "IDS", "Intrusion Detection", "10.30.1.10", "ids-ot-01", "Syslog", "High", True, None),
    ("OT Firewall", "Security", "Firewall", "OT Firewall", "10.30.0.1", "ot-fw-01", "HTTPS", "Critical", True, None),
    ("Jump Server", "Security", "Server", "Jump Server", "192.168.50.7", "ot-jump-01", "RDP/SSH", "Critical", True, "OT Jump Server"),
    ("Log Collector", "Security", "Server", "Log Collector", "10.30.1.20", "logs-01", "Syslog", "High", True, None),
    ("Vendor Remote Support", "External / Untrusted", "External", "Vendor Support", "203.0.113.20", "vendor-support", "VPN", "Medium", False, None),
    ("Internet", "External / Untrusted", "Cloud", "Internet", "198.51.100.1", "simulated-internet", "IP", "High", False, None),
    ("Simulated Threat Actor Infrastructure", "External / Untrusted", "External", "Threat Infrastructure", "203.0.113.66", "sim-threat-01", "HTTPS", "High", False, None),
]


CONNECTIONS = [
    # source, target, type, protocol, port, bandwidth, latency, encrypted
    ("Internet", "Corporate Firewall", "WAN", "HTTPS", 443, 1000, 18, True),
    ("Corporate Firewall", "Dispatch Firewall", "Security Boundary", "IPsec", 500, 1000, 6, True),
    ("Active Directory Domain Controller", "Dispatch Firewall", "Authentication", "Kerberos", 88, 1000, 5, True),
    ("Security Information and Event Management Server", "Log Collector", "Logging", "Syslog-TLS", 6514, 1000, 4, True),
    ("Email Gateway", "Corporate Firewall", "Application", "SMTP", 25, 500, 2, True),
    ("Analyst Workstation", "Security Information and Event Management Server", "Application", "HTTPS", 443, 1000, 2, True),
    ("Backup Server", "Operations Database", "Backup", "SMB", 445, 1000, 8, True),
    ("Dispatch Firewall", "Application Server", "Application", "HTTPS", 443, 1000, 2, True),
    ("Application Server", "Dispatch SCADA Server", "Control", "HTTPS", 443, 1000, 1, True),
    ("Application Server", "Operations Database", "Database", "PostgreSQL", 5432, 1000, 1, True),
    ("Dispatcher Workstation 1", "Application Server", "Application", "HTTPS", 443, 1000, 1, True),
    ("Dispatcher Workstation 2", "Application Server", "Application", "HTTPS", 443, 1000, 1, True),
    ("Dispatch SCADA Server", "Historian", "Telemetry", "OPC-UA", 4840, 1000, 1, True),
    ("Dispatch SCADA Server", "OT Firewall", "Control", "DNP3", 20000, 1000, 2, True),
    ("OT Firewall", "Fiber Backbone Router", "Backbone", "MPLS", 0, 10000, 3, True),
    ("Fiber Backbone Router", "Signal Controller 14A", "Control", "DNP3", 20000, 100, 12, True),
    ("Fiber Backbone Router", "Grade Crossing Controller MP 82.4", "Control", "DNP3", 20000, 100, 14, True),
    ("Fiber Backbone Router", "Switch Controller 9", "Control", "DNP3", 20000, 100, 11, True),
    ("Fiber Backbone Router", "Wayside Interface Unit", "Telemetry", "DNP3", 20000, 100, 13, True),
    ("Wayside Interface Unit", "Track Circuit Controller", "Field Bus", "DNP3", 20000, 10, 2, False),
    ("PTC Radio Gateway", "Radio Tower Sector 3", "Radio", "PTC", 0, 50, 22, True),
    ("Radio Tower Sector 3", "Fiber Backbone Router", "Backhaul", "IPsec", 500, 100, 17, True),
    ("Microwave Link", "Fiber Backbone Router", "Backhaul", "Microwave", 0, 300, 9, True),
    ("LTE Gateway", "Fiber Backbone Router", "Backup WAN", "IPsec", 500, 100, 28, True),
    ("Network Management Server", "Fiber Backbone Router", "Management", "SNMPv3", 161, 1000, 2, True),
    ("Remote Access Gateway", "Jump Server", "Remote Access", "SSH", 22, 100, 6, True),
    ("Jump Server", "Engineering Workstation", "Administration", "RDP", 3389, 100, 3, True),
    ("Engineering Workstation", "Signal Controller 14A", "Engineering", "SFTP", 22, 100, 5, True),
    ("Engineering Workstation", "Switch Controller 9", "Engineering", "SFTP", 22, 100, 5, True),
    ("Maintenance Laptop", "Wayside Interface Unit", "Maintenance", "SSH", 22, 100, 4, True),
    ("IDS Sensor", "OT Firewall", "Traffic Mirror", "SPAN", 0, 1000, 1, False),
    ("IDS Sensor", "Fiber Backbone Router", "Traffic Mirror", "SPAN", 0, 1000, 1, False),
    ("Log Collector", "IDS Sensor", "Logging", "Syslog-TLS", 6514, 1000, 1, True),
    ("Vendor Remote Support", "Remote Access Gateway", "Remote Access", "VPN", 443, 50, 35, True),
    ("Internet", "Remote Access Gateway", "WAN", "HTTPS", 443, 500, 24, True),
    ("Simulated Threat Actor Infrastructure", "Internet", "Simulated External", "HTTPS", 443, 20, 42, True),
]


def seed_network_visibility(db):
    zones = {}
    for name, zone_type, description, trust, color in ZONES:
        zone = db.query(NetworkZone).filter(NetworkZone.name == name).one_or_none()
        if zone is None:
            zone = NetworkZone(name=name)
            db.add(zone)
        zone.zone_type = zone_type
        zone.description = description
        zone.trust_level = trust
        zone.color_key = color
        zone.security_policy = f"Simulated {trust.lower()} trust policy"
        zone.location = "TrackSentinel Simulation"
        zones[name] = zone
    db.flush()

    devices = {device.name: device for device in db.query(OTDevice).all()}
    nodes = {}
    zone_counts = {}
    for (
        name, zone_name, node_type, device_type, ip_address, hostname, protocol,
        criticality, managed, device_name,
    ) in NODES:
        node = db.query(NetworkNode).filter(NetworkNode.name == name).one_or_none()
        linked = devices.get(device_name)
        count = zone_counts.get(zone_name, 0)
        zone_counts[zone_name] = count + 1
        if node is None:
            node = NetworkNode(
                name=name,
                display_name=name,
                status=linked.status if linked else "Healthy",
                health="Healthy",
                risk_level=linked.risk_level if linked else "Low",
                layout_x=(list(zones).index(zone_name) % 3) * 620 + (count % 3) * 165,
                layout_y=(list(zones).index(zone_name) // 3) * 520 + (count // 3) * 120,
            )
            db.add(node)
        node.zone_id = zones[zone_name].id
        node.ot_device_id = linked.id if linked else None
        node.display_name = name
        node.node_type = node_type
        node.device_type = device_type
        node.security_zone = zone_name
        node.network_segment = f"{zone_name} simulated segment"
        node.ip_address = linked.ip_address if linked else ip_address
        node.hostname = hostname
        node.operating_system = "Embedded RTOS" if node_type in {"Controller", "Radio"} else "Hardened Linux"
        node.vendor = linked.vendor if linked else "TrackSentinel Simulated"
        node.model = linked.model if linked else f"SIM-{node_type.upper()}"
        node.firmware_version = linked.firmware_version if linked else "SIM-1.0"
        node.protocol = protocol
        node.criticality = linked.criticality if linked else criticality
        node.location = linked.location if linked else "Simulated Railroad Network"
        node.latitude = linked.latitude if linked else None
        node.longitude = linked.longitude if linked else None
        node.last_seen = linked.last_seen if linked else node.last_seen
        node.is_managed = managed
        node.is_ot_asset = zone_name == "Railroad OT" or linked is not None
        node.metadata_json = json.dumps({"simulation_only": True, "source": "seed"})
        nodes[name] = node
    db.flush()

    for source, target, kind, protocol, port, bandwidth, latency, encrypted in CONNECTIONS:
        source_node, target_node = nodes[source], nodes[target]
        connection = db.query(NetworkConnection).filter(
            NetworkConnection.source_node_id == source_node.id,
            NetworkConnection.target_node_id == target_node.id,
            NetworkConnection.connection_type == kind,
        ).one_or_none()
        if connection is None:
            connection = NetworkConnection(
                source_node_id=source_node.id,
                target_node_id=target_node.id,
                connection_type=kind,
                status="Healthy",
                packet_loss_percent=0.0,
                risk_level="Low",
            )
            db.add(connection)
        connection.protocol = protocol
        connection.port = port or None
        connection.direction = "Bidirectional"
        connection.bandwidth_mbps = bandwidth
        connection.latency_ms = latency
        connection.encrypted = encrypted
        connection.security_boundary_crossing = source_node.zone_id != target_node.zone_id
        connection.metadata_json = json.dumps(
            {
                "simulation_only": True,
                "baseline_latency_ms": latency,
                "baseline_packet_loss_percent": 0.0,
                "baseline_status": "Healthy",
            }
        )
    db.flush()

