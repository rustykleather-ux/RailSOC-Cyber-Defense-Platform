import inspect
import math
import sys
import unittest
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool


BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from database import Base
from main import app, network_topology
from models import (
    Incident,
    NetworkConnection,
    NetworkNode,
    NetworkTrafficEvent,
    NetworkZone,
    OTDevice,
)
from seed_network_visibility import seed_network_visibility
from services import network_visibility_service as service


class NetworkVisibilityTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.db = self.Session()
        self.controller = OTDevice(
            name="Signal Controller 14A",
            ip_address="192.168.50.10",
            device_type="Signal Controller",
            vendor="TrackSentinel Test",
            model="SIM-SIG",
            status="Online",
            risk_level="Low",
            firmware_version="4.1",
            criticality="Critical",
            location="Test Territory",
        )
        self.db.add(self.controller)
        self.db.flush()
        seed_network_visibility(self.db)
        self.db.commit()

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def node(self, name):
        return self.db.query(NetworkNode).filter(NetworkNode.name == name).one()

    def test_seed_creates_nodes_connections_and_zone_relationships_idempotently(self):
        counts = (
            self.db.query(NetworkZone).count(),
            self.db.query(NetworkNode).count(),
            self.db.query(NetworkConnection).count(),
        )
        self.assertEqual(counts[0], 6)
        self.assertGreaterEqual(counts[1], 30)
        self.assertGreaterEqual(counts[2], 30)
        seed_network_visibility(self.db)
        self.db.flush()
        self.assertEqual(
            counts,
            (
                self.db.query(NetworkZone).count(),
                self.db.query(NetworkNode).count(),
                self.db.query(NetworkConnection).count(),
            ),
        )
        signal = self.node("Signal Controller 14A")
        self.assertEqual(signal.ot_device_id, self.controller.id)
        self.assertEqual(signal.zone.name, "Railroad OT")
        self.assertTrue(signal.metadata_json.find("simulation_only") >= 0)

    def test_topology_endpoint_and_websocket_payload_have_validated_schema(self):
        topology = network_topology(event_limit=20, db=self.db)
        self.assertTrue(topology["simulation_only"])
        self.assertEqual(topology["schema_version"], "1.0")
        self.assertEqual(len(topology["nodes"]), self.db.query(NetworkNode).count())
        payload = service.websocket_payload(self.db)
        self.assertEqual(payload["type"], "network_snapshot")
        self.assertTrue(payload["simulation_only"])
        self.assertIsInstance(payload["topology"]["connections"], list)
        paths = app.openapi()["paths"]
        for path in (
            "/api/network/topology",
            "/api/network/path/trace",
            "/api/network/layout",
            "/api/network/nodes/{node_id}/{action}",
            "/api/network/connections/{connection_id}/{action}",
            "/api/network/simulate",
        ):
            self.assertIn(path, paths)

    def test_path_trace_is_deterministic_and_calculates_latency_and_loss(self):
        source = self.node("Dispatch SCADA Server")
        target = self.node("Signal Controller 14A")
        first = service.trace_path(self.db, source.id, target.id)
        second = service.trace_path(self.db, source.id, target.id)
        self.assertEqual(
            [hop["id"] for hop in first["hops"]],
            [hop["id"] for hop in second["hops"]],
        )
        links = [
            self.db.get(NetworkConnection, link_id)
            for link_id in first["connection_ids"]
        ]
        self.assertAlmostEqual(
            first["total_latency_ms"],
            sum(link.latency_ms for link in links),
        )
        for link in links:
            link.packet_loss_percent = 10
        result = service.trace_path(self.db, source.id, target.id)
        expected = (1 - math.prod(0.9 for _ in links)) * 100
        self.assertAlmostEqual(result["total_packet_loss"], expected, places=4)

    def test_connection_failure_marks_dependency_impact_not_compromise(self):
        firewall = self.node("OT Firewall")
        backbone = self.node("Fiber Backbone Router")
        connection = self.db.query(NetworkConnection).filter(
            NetworkConnection.source_node_id == firewall.id,
            NetworkConnection.target_node_id == backbone.id,
        ).one()
        result = service.apply_connection_action(self.db, connection.id, "fail")
        self.assertEqual(result["status"], "Down")
        self.assertNotEqual(firewall.status, "Compromised")
        self.assertNotEqual(backbone.status, "Compromised")
        self.assertIn(
            "Loss of Communications",
            {firewall.health, backbone.health},
        )
        service.restore_baseline(self.db)
        self.assertEqual(connection.status, "Healthy")
        self.assertEqual(connection.packet_loss_percent, 0)
        self.assertNotIn("dependency_impact", firewall.metadata_json)
        self.assertNotIn("dependency_impact", backbone.metadata_json)

    def test_suspicious_simulation_links_alert_incident_and_traffic_event(self):
        result = service.run_simulation(
            self.db, "unauthorized_remote_access"
        )
        event = self.db.get(NetworkTrafficEvent, result["event"]["id"])
        incident = self.db.get(Incident, result["incident_id"])
        self.assertTrue(event.is_suspicious)
        self.assertEqual(event.related_incident_id, incident.id)
        self.assertEqual(event.related_alert_id, incident.alert_id)

    def test_invalid_nodes_connections_and_actions_are_rejected(self):
        cases = [
            lambda: service.get_node(self.db, 99999),
            lambda: service.get_connection(self.db, 99999),
            lambda: service.apply_node_action(self.db, self.node("Internet").id, "delete"),
            lambda: service.apply_connection_action(self.db, 99999, "fail"),
            lambda: service.run_simulation(self.db, "real_network_scan"),
        ]
        for operation in cases:
            with self.subTest(operation=operation):
                with self.assertRaises(service.NetworkValidationError):
                    operation()

    def test_service_has_no_real_network_or_shell_capabilities(self):
        source = inspect.getsource(service)
        banned_imports = (
            "import socket",
            "import subprocess",
            "import requests",
            "import scapy",
            "import nmap",
            "os.system",
            "Popen(",
        )
        for banned in banned_imports:
            self.assertNotIn(banned, source)
        frontend_service = (
            BACKEND_DIR.parent
            / "frontend"
            / "src"
            / "services"
            / "networkService.js"
        ).read_text(encoding="utf-8")
        self.assertNotIn("fetch(", frontend_service)
        self.assertNotIn("indexedDB", frontend_service)
        self.assertNotIn("sqlite", frontend_service.lower())
        self.assertIn('import API from "../api"', frontend_service)

    def test_bounded_snapshot_supports_target_graph_size(self):
        zone = self.db.query(NetworkZone).first()
        existing_nodes = self.db.query(NetworkNode).count()
        generated = []
        for index in range(100 - existing_nodes):
            node = NetworkNode(
                zone_id=zone.id,
                name=f"Scale Test Node {index}",
                display_name=f"Scale Test Node {index}",
                node_type="Server",
                device_type="Simulated",
                security_zone=zone.name,
                status="Healthy",
                health="Healthy",
                risk_level="Low",
                criticality="Low",
                is_managed=True,
                is_ot_asset=False,
                metadata_json='{"simulation_only": true}',
            )
            self.db.add(node)
            generated.append(node)
        self.db.flush()
        all_nodes = self.db.query(NetworkNode).order_by(NetworkNode.id).all()
        needed_connections = 250 - self.db.query(NetworkConnection).count()
        for index in range(needed_connections):
            source = all_nodes[index % len(all_nodes)]
            target = all_nodes[(index * 7 + 3) % len(all_nodes)]
            if source.id == target.id:
                target = all_nodes[(target.id + 1) % len(all_nodes)]
            self.db.add(NetworkConnection(
                source_node_id=source.id,
                target_node_id=target.id,
                connection_type=f"Scale-{index}",
                protocol="SIM",
                latency_ms=1,
                packet_loss_percent=0,
                status="Healthy",
                metadata_json='{"simulation_only": true}',
            ))
        for index in range(500):
            self.db.add(NetworkTrafficEvent(
                source_node_id=all_nodes[index % len(all_nodes)].id,
                target_node_id=all_nodes[(index + 1) % len(all_nodes)].id,
                event_type="scale_test",
                description="Simulated scale validation event.",
                is_suspicious=False,
            ))
        self.db.flush()
        snapshot = service.get_topology(self.db, event_limit=500)
        self.assertEqual(len(snapshot["nodes"]), 100)
        self.assertEqual(len(snapshot["connections"]), 250)
        self.assertEqual(len(snapshot["events"]), 500)


if __name__ == "__main__":
    unittest.main()
