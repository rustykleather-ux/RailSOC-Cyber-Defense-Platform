import sys
import unittest
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool


BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from database import Base
from models import (
    ActivityLog,
    OTDevice,
    RouteTopologySegment,
    TrackBlock,
    TrackSwitch,
    Train,
)
from seed_operational_assets import seed_operational_assets
from seed_track_blocks import seed_track_blocks
from seed_route_topology import seed_route_topology
from services.dispatch_service import (
    DispatchValidationError,
    create_dispatch_command,
    create_restriction,
    create_route,
    get_dispatch_status,
    perform_recovery_action,
    process_dispatch_commands,
)
from services.map_service import get_map_snapshot
from train_simulation import TrainSimulationEngine


class DispatcherOperationsTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.db = self.Session()
        self.devices = {}
        for name, kind in [
            ("Signal Controller 14A", "Signal Controller"),
            ("Switch Machine Controller", "Switch Controller"),
            ("Grade Crossing Controller MP 82.4", "Grade Crossing Controller"),
            ("Dispatch SCADA Server", "Dispatch SCADA"),
        ]:
            device = OTDevice(
                name=name, ip_address=f"198.51.100.{len(self.devices) + 10}",
                device_type=kind, vendor="Test", status="Online",
                risk_level="Low", firmware_version="1", location="East Subdivision",
            )
            self.db.add(device)
            self.devices[name] = device
        self.db.commit()
        seed_track_blocks(self.db)
        seed_operational_assets(self.db)
        self.train = Train(
            symbol="DSP-101", subdivision="East Subdivision", track="Main",
            direction="Eastbound", milepost=80.5, speed=30, status="Moving",
            ptc_enabled=True, current_signal="Clear",
        )
        self.db.add(self.train)
        self.db.commit()
        self.blocks = self.db.query(TrackBlock).order_by(
            TrackBlock.start_milepost
        ).all()
        self.switch = self.db.query(TrackSwitch).one()

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def command(self, kind, target_type, target_id, state, **extra):
        return create_dispatch_command(self.db, {
            "command_type": kind, "target_type": target_type,
            "target_id": target_id, "requested_state": state,
            "requested_by": "Test Dispatcher", "priority": extra.get("priority", "Normal"),
            "payload": extra.get("payload", {}),
        })

    def assertBlocked(self, callback, text):
        with self.assertRaises(DispatchValidationError) as context:
            callback()
        self.assertIn(text.lower(), str(context.exception).lower())

    def test_signal_cannot_clear_into_occupied_block(self):
        block = self.blocks[1]
        block.occupied = True
        self.assertBlocked(
            lambda: self.command("SET_SIGNAL", "TRACK_BLOCK", block.id, "Clear"),
            "occupied",
        )

    def test_switch_cannot_move_beneath_train_or_when_locked(self):
        self.switch.track_block.occupied = True
        self.switch.track_block.occupied_train_id = self.train.id
        self.assertBlocked(
            lambda: self.command("MOVE_SWITCH", "TRACK_SWITCH", self.switch.id, "Reverse"),
            "occupying train",
        )
        self.switch.track_block.occupied = False
        self.switch.locked = True
        self.assertBlocked(
            lambda: self.command("MOVE_SWITCH", "TRACK_SWITCH", self.switch.id, "Reverse"),
            "locked",
        )

    def test_train_cannot_release_into_stop_block(self):
        self.blocks[1].signal_aspect = "Stop"
        self.assertBlocked(
            lambda: self.command("RELEASE_TRAIN", "TRAIN", self.train.id, "Released"),
            "Stop",
        )

    def test_normal_degraded_severe_offline_and_compromised_scada(self):
        scada = self.devices["Dispatch SCADA Server"]
        completed = self.command("HOLD_TRAIN", "TRAIN", self.train.id, "Held")
        self.assertEqual(completed.status, "Completed")
        self.train.status = "Moving"

        scada.status = "Degraded"
        delayed = self.command("HOLD_TRAIN", "TRAIN", self.train.id, "Held")
        self.assertEqual(delayed.status, "Queued")
        self.assertIsNotNone(delayed.apply_after)

        scada.status = "Severe"
        queued = self.command("SET_SIGNAL", "TRACK_BLOCK", self.blocks[2].id, "Stop")
        self.assertEqual(queued.status, "Queued")
        safety = self.command(
            "HOLD_TRAIN", "TRAIN", self.train.id, "Held", priority="Safety"
        )
        self.assertEqual(safety.status, "Completed")

        scada.status = "Offline"
        offline = self.command("SET_SIGNAL", "TRACK_BLOCK", self.blocks[3].id, "Stop")
        self.assertEqual(offline.status, "Queued")
        self.assertIsNone(offline.apply_after)

        scada.status = "Compromised"
        blocked = self.command("SET_SIGNAL", "TRACK_BLOCK", self.blocks[4].id, "Stop")
        self.assertEqual(blocked.status, "Blocked")

    def test_queued_command_revalidates_and_stale_command_fails(self):
        scada = self.devices["Dispatch SCADA Server"]
        scada.status = "Degraded"
        command = self.command("SET_SIGNAL", "TRACK_BLOCK", self.blocks[2].id, "Clear")
        self.blocks[2].occupied = True
        scada.status = "Online"
        process_dispatch_commands(self.db, restore=True)
        self.assertEqual(command.status, "Failed")
        self.assertIn("occupied", command.failure_reason)

    def test_route_establishes_and_is_blocked_by_occupancy_or_switch(self):
        safe = create_route(self.db, {
            "train_id": self.train.id,
            "start_block_id": self.blocks[0].id,
            "destination_block_id": self.blocks[1].id,
            "requested_by": "Test",
        })
        self.assertEqual(safe.status, "Established")

        self.blocks[2].occupied = True
        occupied = create_route(self.db, {
            "train_id": self.train.id,
            "start_block_id": self.blocks[1].id,
            "destination_block_id": self.blocks[2].id,
        })
        self.assertEqual(occupied.status, "Blocked")
        self.blocks[2].occupied = False

        self.switch.locked = True
        switch_route = create_route(self.db, {
            "train_id": self.train.id,
            "start_block_id": self.switch.track_block_id,
            "destination_block_id": next(
                b.id for b in self.blocks if b.id != self.switch.track_block_id
                and b.start_milepost >= self.switch.track_block.end_milepost
            ),
        })
        self.assertEqual(switch_route.status, "Blocked")

    def test_explicit_topology_enforces_switch_and_signal_requirements(self):
        start = self.switch.track_block
        destination = next(
            block for block in self.blocks
            if block.start_milepost >= start.end_milepost
        )
        segment = RouteTopologySegment(
            name="Test junction reverse route",
            from_block_id=start.id,
            to_block_id=destination.id,
            signal_block_id=destination.id,
            required_signal_aspect="Clear",
            switch_id=self.switch.id,
            required_switch_position="Reverse",
            enabled=True,
        )
        self.db.add(segment)
        self.db.flush()

        blocked = create_route(self.db, {
            "train_id": self.train.id,
            "start_block_id": start.id,
            "destination_block_id": destination.id,
        })
        self.assertEqual(blocked.status, "Blocked")
        self.assertIn("Reverse", blocked.blocking_reason)

        self.switch.position = self.switch.commanded_position = "Reverse"
        established = create_route(self.db, {
            "train_id": self.train.id,
            "start_block_id": start.id,
            "destination_block_id": destination.id,
        })
        self.assertEqual(established.status, "Established")
        self.assertEqual(
            established.required_switch_positions_json,
            f'{{"{self.switch.id}": "Reverse"}}',
        )
        self.assertEqual(destination.signal_aspect, "Clear")

    def test_seeded_topology_is_explicit_bidirectional_and_idempotent(self):
        seed_route_topology(self.db)
        seed_route_topology(self.db)
        segments = self.db.query(RouteTopologySegment).all()
        self.assertEqual(len(segments), (len(self.blocks) - 1) * 2)
        self.assertTrue(any(item.switch_id == self.switch.id for item in segments))

    def test_restriction_affects_movement_and_map(self):
        restriction = create_restriction(self.db, {
            "restriction_type": "HOLD_TRAIN", "target_type": "TRAIN",
            "target_id": self.train.id, "reason": "Incident protection",
        })
        TrainSimulationEngine()._update_train(self.train, self.db)
        self.assertEqual(self.train.speed, 0)
        snapshot = get_map_snapshot(self.db)
        self.assertEqual(snapshot["operational_restrictions"][0]["id"], restriction.id)

    def test_recovery_restores_device_and_timeline_records_lifecycle(self):
        device = self.devices["Signal Controller 14A"]
        device.status, device.risk_level = "Compromised", "Critical"
        result = perform_recovery_action(self.db, {
            "action_type": "RESTORE_KNOWN_GOOD", "target_id": device.id,
        })
        self.assertEqual(result["status"], "Completed")
        self.assertEqual(device.status, "Online")
        events = [row.event_type for row in self.db.query(ActivityLog).all()]
        self.assertIn("dispatch_recovery_started", events)
        self.assertIn("dispatch_recovery_completed", events)

    def test_status_metrics_are_documented(self):
        status = get_dispatch_status(self.db)
        self.assertIn(status["dispatcher_workload_level"], {"Normal", "Elevated", "High"})
        self.assertIn("Training score", status["workload_method"])


if __name__ == "__main__":
    unittest.main()
