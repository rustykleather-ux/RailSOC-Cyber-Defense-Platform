import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool


BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from database import Base
from main import (
    CustomScenario,
    get_track_blocks,
    launch_custom_scenario,
    reset_demo,
    simulate_attack,
)
from models import Alert, Incident, OTDevice, TrackBlock, Train
from seed_track_blocks import (
    SIGNAL_CONTROLLER_BLOCK_NAMES,
    seed_track_blocks,
)
from train_simulation import TrainSimulationEngine
from services.digital_twin_service import apply_signal_controller_effect


class SignalControllerWorkflowTests(unittest.TestCase):
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
            ip_address="192.0.2.14",
            device_type="Signal Controller",
            vendor="Test Vendor",
            status="Online",
            risk_level="Low",
            firmware_version="4.1.3",
            location="Test Territory",
        )
        self.db.add(self.controller)
        self.db.commit()
        seed_track_blocks(self.db)

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def assigned_blocks(self):
        return (
            self.db.query(TrackBlock)
            .filter(
                TrackBlock.controlling_device_id
                == self.controller.id
            )
            .order_by(TrackBlock.start_milepost)
            .all()
        )

    def test_track_block_assignment_is_idempotent_and_exposed(self):
        initial_count = self.db.query(TrackBlock).count()

        seed_track_blocks(self.db)

        self.assertEqual(self.db.query(TrackBlock).count(), initial_count)
        self.assertEqual(
            {block.name for block in self.assigned_blocks()},
            SIGNAL_CONTROLLER_BLOCK_NAMES,
        )

        response = get_track_blocks(self.db)
        assigned_response = [
            block
            for block in response
            if block["name"] in SIGNAL_CONTROLLER_BLOCK_NAMES
        ]
        self.assertTrue(assigned_response)
        self.assertTrue(
            all(
                block["controlling_device_id"] == self.controller.id
                and block["controlling_device"]
                == self.controller.name
                for block in assigned_response
            )
        )

    def test_signal_attack_changes_every_assigned_block(self):
        with patch(
            "main.apply_signal_controller_effect",
            wraps=apply_signal_controller_effect,
        ) as shared_effect:
            response = simulate_attack("signal", self.db)

        shared_effect.assert_called_once_with(
            db=self.db,
            device=self.controller,
        )
        assigned_blocks = self.assigned_blocks()

        self.assertEqual(self.controller.status, "Degraded")
        self.assertEqual(self.controller.risk_level, "Critical")
        self.assertEqual(
            {block["id"] for block in response["affected_track_blocks"]},
            {block.id for block in assigned_blocks},
        )
        self.assertTrue(
            all(
                block.signal_aspect == "Stop"
                and block.communications_status == "Degraded"
                and block.security_status == "Compromised"
                and block.last_updated is not None
                for block in assigned_blocks
            )
        )
        self.assertEqual(self.db.query(Alert).count(), 1)
        self.assertEqual(self.db.query(Incident).count(), 1)
        self.assertEqual(
            self.db.query(Incident).one().mitre_technique,
            "T0859 - Modify Controller Tasking",
        )

    def test_custom_signal_scenario_changes_every_assigned_block(self):
        response = launch_custom_scenario(
            CustomScenario(
                attack_id="logic_modification",
                target_ids=[self.controller.id],
            ),
            self.db,
        )
        affected_blocks = response["simulation"][0][
            "affected_track_blocks"
        ]

        self.assertEqual(
            {block["name"] for block in affected_blocks},
            {"Block E82", "Block E84"},
        )
        self.assertTrue(
            all(
                block.signal_aspect == "Stop"
                and block.communications_status == "Degraded"
                and block.security_status == "Compromised"
                for block in self.assigned_blocks()
            )
        )
        self.assertEqual(self.db.query(Alert).count(), 1)
        self.assertEqual(self.db.query(Incident).count(), 1)

    def test_signal_attack_returns_409_without_assigned_blocks(self):
        for block in self.assigned_blocks():
            block.controlling_device_id = None
        self.db.commit()

        with self.assertRaises(HTTPException) as context:
            simulate_attack("signal", self.db)

        self.assertEqual(context.exception.status_code, 409)
        self.assertIn(
            "no assigned track blocks",
            context.exception.detail,
        )
        self.db.refresh(self.controller)
        self.assertEqual(self.controller.status, "Online")
        self.assertEqual(self.db.query(Alert).count(), 0)
        self.assertEqual(self.db.query(Incident).count(), 0)

    def test_custom_signal_scenario_returns_409_without_blocks(self):
        for block in self.assigned_blocks():
            block.controlling_device_id = None
        self.db.commit()

        with self.assertRaises(HTTPException) as context:
            launch_custom_scenario(
                CustomScenario(
                    attack_id="logic_modification",
                    target_ids=[self.controller.id],
                ),
                self.db,
            )

        self.assertEqual(context.exception.status_code, 409)
        self.assertIn(self.controller.name, context.exception.detail)
        self.db.refresh(self.controller)
        self.assertEqual(self.controller.status, "Online")
        self.assertEqual(self.db.query(Alert).count(), 0)
        self.assertEqual(self.db.query(Incident).count(), 0)

    def test_non_signal_custom_scenario_does_not_change_blocks(self):
        response = launch_custom_scenario(
            CustomScenario(
                attack_id="communication_failure",
                target_ids=[self.controller.id],
            ),
            self.db,
        )

        self.assertEqual(
            response["simulation"][0]["affected_track_blocks"],
            [],
        )
        self.assertTrue(
            all(
                block.signal_aspect == "Clear"
                and block.communications_status == "Online"
                and block.security_status == "Healthy"
                for block in self.assigned_blocks()
            )
        )

    def test_reset_restores_operational_baseline(self):
        launch_custom_scenario(
            CustomScenario(
                attack_id="logic_modification",
                target_ids=[self.controller.id],
            ),
            self.db,
        )

        response = reset_demo(self.db)

        self.db.refresh(self.controller)
        self.assertEqual(response["message"], "Operational baseline restored")
        self.assertEqual(self.controller.status, "Online")
        self.assertEqual(self.controller.risk_level, "Low")
        self.assertTrue(
            all(
                block.signal_aspect == "Clear"
                and block.communications_status == "Online"
                and block.security_status == "Healthy"
                for block in self.assigned_blocks()
            )
        )
        self.assertEqual(self.db.query(Alert).count(), 0)
        self.assertEqual(self.db.query(Incident).count(), 0)

    def test_train_stops_before_stop_signal(self):
        block = (
            self.db.query(TrackBlock)
            .filter(TrackBlock.name == "Block E82")
            .one()
        )
        block.signal_aspect = "Stop"
        block.communications_status = "Degraded"
        block.security_status = "Compromised"
        train = Train(
            symbol="TEST-STOP",
            subdivision="East Subdivision",
            direction="Eastbound",
            milepost=81.99,
            speed=40,
            status="Moving",
            current_signal="Clear",
        )
        self.db.add(train)
        self.db.commit()
        previous_milepost = train.milepost
        simulation = TrainSimulationEngine(interval_seconds=3)

        simulation._update_train(train, self.db)
        self.db.flush()

        self.assertEqual(train.current_signal, "Stop")
        self.assertEqual(train.status, "Stopped at Signal")
        self.assertEqual(train.speed, 0)
        self.assertLess(train.milepost, block.start_milepost)
        self.assertLessEqual(
            abs(train.milepost - previous_milepost),
            simulation._calculate_milepost_change(40),
        )

    def test_train_resumes_after_signal_clears(self):
        block = (
            self.db.query(TrackBlock)
            .filter(TrackBlock.name == "Block E82")
            .one()
        )
        train = Train(
            symbol="TEST-RESUME",
            subdivision="East Subdivision",
            direction="Eastbound",
            milepost=81.99,
            speed=0,
            status="Stopped at Signal",
            current_signal="Stop",
        )
        self.db.add(train)
        block.signal_aspect = "Clear"
        block.communications_status = "Online"
        block.security_status = "Healthy"
        self.db.commit()
        previous_milepost = train.milepost
        simulation = TrainSimulationEngine(interval_seconds=3)

        simulation._update_train(train, self.db)
        self.db.flush()

        self.assertEqual(train.current_signal, "Clear")
        self.assertEqual(train.status, "Moving")
        self.assertEqual(train.speed, simulation.NORMAL_SPEED_MPH)
        self.assertGreater(train.milepost, previous_milepost)
        self.assertLessEqual(
            train.milepost - previous_milepost,
            simulation._calculate_milepost_change(
                simulation.NORMAL_SPEED_MPH
            )
            + 0.001,
        )


if __name__ == "__main__":
    unittest.main()
