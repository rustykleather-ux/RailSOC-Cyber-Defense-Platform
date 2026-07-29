import sys
import unittest
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool


BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from database import Base
from main import (
    DeviceCreateRequest,
    DeviceRelationshipRequest,
    DeviceTypeRequest,
    add_device,
    add_device_relationship,
    add_device_type,
    get_ai_operations_brief,
)
from models import ActivityLog, DeviceRelationship, OTDevice, TrackBlock
from seed_track_blocks import seed_track_blocks
from services.device_framework import (
    initialize_device_framework,
    serialize_device,
)
from services.digital_twin_service import apply_effect


class DataDrivenDeviceFrameworkTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.db = self.Session()
        self.legacy = OTDevice(
            name="Signal Controller 14A",
            ip_address="192.0.2.14",
            device_type="Signal Controller",
            vendor="Legacy",
        )
        self.db.add(self.legacy)
        self.db.commit()
        seed_track_blocks(self.db)
        initialize_device_framework(self.db)
        self.db.commit()

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def create_type(self, name, capabilities, effects):
        return add_device_type(
            DeviceTypeRequest(
                name=name,
                description="Test-defined controller.",
                category="Test",
                default_capabilities=capabilities,
                default_effects=effects,
            ),
            self.db,
        )

    def create_controller(self, name, device_type):
        return add_device(
            DeviceCreateRequest(
                name=name,
                device_type_id=device_type["id"],
                vendor="Test Rail",
                model="XR-1",
                firmware="1.2.3",
                location="Test District",
                subdivision="East",
                track="Main",
                latitude=38.5,
                longitude=-96.5,
                criticality="High",
                description="Created entirely through the API.",
            ),
            self.db,
        )

    def test_create_device_type_and_custom_device(self):
        device_type = self.create_type(
            "Test Signal Controller",
            ["controls_track_blocks"],
            ["force_stop_signal"],
        )
        device = self.create_controller("Signal Controller 22B", device_type)
        self.assertEqual(device["device_type"], "Test Signal Controller")
        self.assertIn("controls_track_blocks", device["capabilities"])
        self.assertIn("force_stop_signal", device["supported_effects"])
        self.assertIsNotNone(
            self.db.query(ActivityLog)
            .filter_by(event_type="device_created")
            .first()
        )

    def test_many_to_many_relationship_and_signal_effect(self):
        device_type = self.create_type(
            "Multi-block Controller",
            ["controls_track_blocks"],
            ["force_stop_signal"],
        )
        device = self.create_controller("Signal Controller 22B", device_type)
        blocks = self.db.query(TrackBlock).order_by(TrackBlock.id).limit(2).all()
        for block in blocks:
            add_device_relationship(
                device["id"],
                DeviceRelationshipRequest(
                    target_type="TRACK_BLOCK",
                    target_id=block.id,
                    relationship_type="CONTROLS_TRACK_BLOCK",
                ),
                self.db,
            )

        controller = self.db.get(OTDevice, device["id"])
        result = apply_effect(
            self.db, controller, "force_stop_signal"
        )
        self.db.commit()

        self.assertEqual(len(result["affected_track_blocks"]), 2)
        self.assertTrue(all(block.signal_aspect == "Stop" for block in blocks))
        self.assertTrue(
            all(block.security_status == "Compromised" for block in blocks)
        )
        serialized = serialize_device(self.db, controller)
        self.assertIn("controls 2 track blocks", serialized["dynamic_summary"])
        event_types = {
            event.event_type for event in self.db.query(ActivityLog).all()
        }
        self.assertIn("relationship_added", event_types)
        self.assertIn("effect_applied", event_types)

    def test_legacy_assignments_backfill_without_removing_foreign_key(self):
        block = self.db.query(TrackBlock).first()
        block.controlling_device_id = self.legacy.id
        initialize_device_framework(self.db)
        self.db.commit()

        relationship = self.db.query(DeviceRelationship).filter_by(
            source_device_id=self.legacy.id,
            target_type="TRACK_BLOCK",
            target_id=block.id,
        ).one()
        self.assertEqual(
            relationship.relationship_type, "CONTROLS_TRACK_BLOCK"
        )
        self.assertEqual(block.controlling_device_id, self.legacy.id)

    def test_ai_operations_brief_describes_custom_relationships(self):
        device_type = self.create_type(
            "AI Summary Controller",
            ["controls_track_blocks"],
            ["force_stop_signal"],
        )
        device = self.create_controller("Summary Controller", device_type)
        block = self.db.query(TrackBlock).first()
        add_device_relationship(
            device["id"],
            DeviceRelationshipRequest(
                target_type="TRACK_BLOCK",
                target_id=block.id,
                relationship_type="CONTROLS_TRACK_BLOCK",
            ),
            self.db,
        )
        result = get_ai_operations_brief(self.db)
        self.assertTrue(
            any(
                "Summary Controller" in summary
                and "1 track block" in summary
                for summary in result["asset_capability_summaries"]
            )
        )


if __name__ == "__main__":
    unittest.main()
