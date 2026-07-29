import sys
import unittest
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool


BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from database import Base
from main import CustomScenario, launch_custom_scenario, reset_demo
from models import OTDevice, TrackBlock, Train
from seed_operational_assets import seed_operational_assets
from seed_track_blocks import seed_track_blocks
from services.device_framework import initialize_device_framework
from services.map_service import get_map_snapshot


class DigitalTwinMapTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        self.Session = sessionmaker(bind=self.engine)
        Base.metadata.create_all(self.engine)
        self.db = self.Session()
        self.devices = {}
        for name, device_type in [
            ("Signal Controller 14A", "Signal Controller"),
            ("Switch Machine Controller", "Switch Controller"),
            (
                "Grade Crossing Controller MP 82.4",
                "Grade Crossing Controller",
            ),
            ("PTC Radio Gateway", "PTC Communications Gateway"),
            ("Dispatch SCADA Server", "Dispatch SCADA"),
        ]:
            device = OTDevice(
                name=name,
                ip_address=f"192.0.2.{len(self.devices) + 10}",
                device_type=device_type,
                vendor="Test Vendor",
                status="Online",
                risk_level="Low",
                firmware_version="1.0",
                location="East Subdivision",
            )
            self.db.add(device)
            self.devices[name] = device
        self.db.commit()
        seed_track_blocks(self.db)
        seed_operational_assets(self.db)
        initialize_device_framework(self.db)
        self.train = Train(
            symbol="MAP-218",
            subdivision="East Subdivision",
            track="Main",
            direction="Eastbound",
            milepost=82.5,
            speed=35,
            status="Moving",
            ptc_enabled=True,
            current_signal="Clear",
        )
        self.db.add(self.train)
        self.db.commit()

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def test_map_snapshot_returns_all_live_asset_groups(self):
        snapshot = get_map_snapshot(self.db)
        self.assertTrue(snapshot["subdivisions"])
        self.assertTrue(snapshot["blocks"])
        self.assertEqual(len(snapshot["signals"]), len(snapshot["blocks"]))
        self.assertEqual(len(snapshot["trains"]), 1)
        self.assertEqual(len(snapshot["switches"]), 1)
        self.assertEqual(len(snapshot["crossings"]), 1)
        self.assertEqual(len(snapshot["devices"]), 5)
        self.assertIn("operational_impact", snapshot)
        self.assertIn("timeline", snapshot)

        block = snapshot["blocks"][0]
        self.assertLess(block["start_mp"], block["end_mp"])
        self.assertIn("controlling_device", block)
        self.assertIn("security_status", block)

        train = snapshot["trains"][0]
        self.assertIn("current_block", train)
        self.assertIn("next_block", train)
        self.assertIn("target_speed", train)
        self.assertIn("delay_minutes", train)

    def test_signal_attack_and_reset_are_visible_in_snapshot(self):
        controller = self.devices["Signal Controller 14A"]
        controlled_blocks = (
            self.db.query(TrackBlock)
            .filter(TrackBlock.controlling_device_id == controller.id)
            .order_by(TrackBlock.start_milepost)
            .all()
        )
        self.assertEqual(len(controlled_blocks), 2)
        self.assertEqual(
            [block.name for block in controlled_blocks],
            ["Block E82", "Block E84"],
        )

        launch_custom_scenario(
            CustomScenario(
                attack_id="logic_modification",
                target_ids=[controller.id],
            ),
            self.db,
        )
        compromised = get_map_snapshot(self.db)
        mapped_device = next(
            item
            for item in compromised["devices"]
            if item["id"] == controller.id
        )
        mapped_blocks = [
            item
            for item in compromised["blocks"]
            if item["id"] in {block.id for block in controlled_blocks}
        ]
        self.assertEqual(mapped_device["status"], "Compromised")
        self.assertEqual(mapped_device["security_status"], "Compromised")
        self.assertTrue(
            all(block["signal_aspect"] == "Stop" for block in mapped_blocks)
        )
        self.assertTrue(
            all(
                block["security_status"] == "Compromised"
                for block in mapped_blocks
            )
        )

        reset_demo(self.db)
        restored = get_map_snapshot(self.db)
        restored_device = next(
            item
            for item in restored["devices"]
            if item["id"] == controller.id
        )
        restored_blocks = [
            item
            for item in restored["blocks"]
            if item["id"] in {block.id for block in controlled_blocks}
        ]
        self.assertEqual(restored_device["status"], "Online")
        self.assertTrue(
            all(block["security_status"] == "Healthy" for block in restored_blocks)
        )

    def test_ptc_switch_crossing_and_stopped_train_states_are_normalized(self):
        self.train.status = "Stopped at Signal"
        self.train.speed = 0
        track_switch = get_map_snapshot(self.db)["switches"][0]
        crossing = get_map_snapshot(self.db)["crossings"][0]
        self.assertFalse(track_switch["locked"])
        self.assertEqual(crossing["gate_state"], "Raised")

        launch_custom_scenario(
            CustomScenario(
                attack_id="communication_failure",
                target_ids=[self.devices["PTC Radio Gateway"].id],
            ),
            self.db,
        )
        snapshot = get_map_snapshot(self.db)
        train = snapshot["trains"][0]
        self.assertEqual(train["status"], "Restricted - PTC Communications")
        self.assertIn(
            "Restricted - PTC Communications",
            train["operational_restrictions"],
        )


if __name__ == "__main__":
    unittest.main()
