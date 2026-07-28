import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool


BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from database import Base
from main import (
    CustomScenario,
    launch_custom_scenario,
    reset_demo,
    simulate_attack,
)
from models import (
    ActivityLog,
    GradeCrossing,
    Incident,
    OTDevice,
    TrackSwitch,
    Train,
)
from seed_operational_assets import seed_operational_assets
from seed_track_blocks import seed_track_blocks
from services.digital_twin_service import apply_digital_twin_effect
from services.dispatch_service import (
    get_dispatch_metrics,
    process_dispatch_commands,
    queue_dispatch_command,
)
from services.operational_impact import get_operational_impact
from train_simulation import TrainSimulationEngine


class OperationalControllerEffectTests(unittest.TestCase):
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
        self.db.commit()

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def test_operational_asset_seed_is_idempotent(self):
        seed_operational_assets(self.db)
        seed_operational_assets(self.db)
        self.assertEqual(self.db.query(TrackSwitch).count(), 1)
        self.assertEqual(self.db.query(GradeCrossing).count(), 1)
        self.assertEqual(
            self.db.query(TrackSwitch).one().controlling_device_id,
            self.devices["Switch Machine Controller"].id,
        )

    def test_switch_attack_locks_switch_and_stops_train(self):
        response = launch_custom_scenario(
            CustomScenario(
                attack_id="logic_modification",
                target_ids=[
                    self.devices["Switch Machine Controller"].id
                ],
            ),
            self.db,
        )
        track_switch = self.db.query(TrackSwitch).one()
        effect = response["simulation"][0]["operational_effects"]
        self.assertEqual(effect["effect_type"], "switch_controller_compromise")
        self.assertTrue(track_switch.locked)
        self.assertNotEqual(
            track_switch.position, track_switch.commanded_position
        )

        train = Train(
            symbol="SWITCH-TEST",
            subdivision="East Subdivision",
            track="Main",
            direction="Eastbound",
            milepost=85.94,
            speed=40,
            status="Moving",
            ptc_enabled=True,
        )
        self.db.add(train)
        self.db.commit()
        simulation = TrainSimulationEngine(interval_seconds=3)
        for _ in range(10):
            simulation._update_train(train, self.db)
            if train.status == "Stopped at Unsafe Switch":
                break

        self.assertEqual(train.status, "Stopped at Unsafe Switch")
        self.assertLess(train.milepost, track_switch.milepost)
        self.assertEqual(train.speed, 0)

    def test_crossing_attack_updates_warning_system_and_incident(self):
        response = launch_custom_scenario(
            CustomScenario(
                attack_id="firmware_tampering",
                target_ids=[
                    self.devices[
                        "Grade Crossing Controller MP 82.4"
                    ].id
                ],
            ),
            self.db,
        )
        crossing = self.db.query(GradeCrossing).one()
        self.assertEqual(
            response["simulation"][0]["operational_effects"]["effect_type"],
            "grade_crossing_compromise",
        )
        self.assertEqual(crossing.gate_state, "Unavailable")
        self.assertFalse(crossing.lights_active)
        self.assertEqual(crossing.communications_status, "Degraded")
        self.assertEqual(crossing.security_status, "Compromised")
        self.assertEqual(self.db.query(Incident).count(), 1)
        self.assertIsNotNone(
            self.db.query(ActivityLog).filter(
                ActivityLog.event_type
                == "crossing_warning_unavailable"
            ).first()
        )

    def test_ptc_failure_restricts_and_reset_restores_train(self):
        train = Train(
            symbol="PTC-TEST",
            subdivision="East Subdivision",
            track="Main",
            direction="Eastbound",
            milepost=81.0,
            speed=40,
            status="Moving",
            ptc_enabled=True,
        )
        self.db.add(train)
        self.db.commit()
        launch_custom_scenario(
            CustomScenario(
                attack_id="communication_failure",
                target_ids=[self.devices["PTC Radio Gateway"].id],
            ),
            self.db,
        )
        simulation = TrainSimulationEngine(interval_seconds=3)
        simulation._update_train(train, self.db)

        self.assertEqual(
            train.status, "Restricted - PTC Communications"
        )
        self.assertGreater(train.speed, simulation.RESTRICTED_SPEED_MPH)
        self.assertLess(train.speed, 40)

        restricted_speed = train.speed
        reset_demo(self.db)
        simulation._update_train(train, self.db)
        self.assertEqual(train.status, "Moving")
        self.assertGreater(train.speed, restricted_speed)

    def test_scada_progression_queues_and_recovers_commands(self):
        scada = self.devices["Dispatch SCADA Server"]
        launch_custom_scenario(
            CustomScenario(
                attack_id="denial_of_service",
                target_ids=[scada.id],
            ),
            self.db,
        )
        degraded = queue_dispatch_command(
            self.db, "set_route", {"route": "E80-E86"}
        )
        self.assertEqual(degraded.status, "Queued")
        self.assertIsNotNone(degraded.apply_after)

        scada.status = "Severe"
        severe = queue_dispatch_command(
            self.db, "hold_route", {"route": "E84-E86"}
        )
        self.assertEqual(severe.status, "Queued")
        self.assertAlmostEqual(
            (severe.apply_after - severe.requested_at).total_seconds(),
            60,
            delta=0.01,
        )

        scada.status = "Offline"
        offline = queue_dispatch_command(
            self.db, "clear_signal", {"block": "Block E82"}
        )
        self.assertEqual(offline.status, "Queued")
        self.assertIsNone(offline.apply_after)
        self.db.commit()

        process_dispatch_commands(self.db)
        self.assertEqual(get_dispatch_metrics(self.db)["queued_commands"], 3)
        impact = get_operational_impact(self.db)
        self.assertEqual(impact["dispatch_availability_percent"], 0.0)

        response = reset_demo(self.db)
        self.assertEqual(response["applied_dispatch_commands"], 3)
        self.assertEqual(get_dispatch_metrics(self.db)["queued_commands"], 0)
        self.assertEqual(
            get_dispatch_metrics(self.db)[
                "dispatch_availability_percent"
            ],
            100.0,
        )

    def test_direct_phase_7_to_10_attacks_use_shared_effect_dispatch(self):
        with patch(
            "main.apply_digital_twin_effect",
            wraps=apply_digital_twin_effect,
        ) as shared_effect:
            for attack_type in ["switch", "firmware", "ptc", "dos"]:
                reset_demo(self.db)
                response = simulate_attack(attack_type, self.db)
                self.assertIsNotNone(
                    response["operational_effects"]["effect_type"]
                )

        self.assertEqual(shared_effect.call_count, 4)

    def test_non_operational_attack_does_not_change_operational_assets(self):
        track_switch = self.db.query(TrackSwitch).one()
        crossing = self.db.query(GradeCrossing).one()
        train = Train(
            symbol="NO-EFFECT",
            subdivision="East Subdivision",
            track="Main",
            direction="Eastbound",
            milepost=81.0,
            speed=40,
            status="Moving",
            ptc_enabled=True,
        )
        self.db.add(train)
        self.db.commit()

        response = simulate_attack("recon", self.db)

        self.assertIsNone(
            response["operational_effects"]["effect_type"]
        )
        self.assertFalse(track_switch.locked)
        self.assertEqual(track_switch.position, "Normal")
        self.assertEqual(crossing.gate_state, "Raised")
        self.assertEqual(train.speed, 40)
        self.assertEqual(train.status, "Moving")


if __name__ == "__main__":
    unittest.main()
