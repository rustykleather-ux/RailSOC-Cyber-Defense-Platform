import sys
import unittest
from datetime import timedelta
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool


BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from database import Base
from models import (
    ActivityLog,
    Exercise,
    ExerciseCheckpoint,
    ExerciseRun,
    ExerciseRunEvent,
    ExerciseRunObjective,
    ExerciseObjective,
    Incident,
    OTDevice,
    Train,
)
from seed_exercises import seed_exercises
from seed_operational_assets import seed_operational_assets
from seed_track_blocks import seed_track_blocks
from services.exercise_service import (
    after_action_report,
    cancel_run,
    clear_exercise_history,
    clone_exercise,
    create_exercise,
    create_run,
    evaluate_objectives,
    finish_run,
    pause_run,
    process_run,
    request_objective_reevaluation,
    reveal_walkthrough,
    restore_checkpoint,
    resume_run,
    save_checkpoint,
    simple_pdf,
    start_run,
    update_exercise,
    serialize_run,
    serialize_walkthrough,
    validate_exercise_configuration,
    ExerciseValidationError,
)
from services.dispatch_service import perform_recovery_action
from services.operational_impact import get_operational_impact
from services.timeline_service import record_event
from services.timeline_service import utc_now


class ExerciseEngineTests(unittest.TestCase):
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
            ("PTC Radio Gateway", "PTC Communications Gateway"),
            ("Dispatch SCADA Server", "Dispatch SCADA"),
        ]:
            device = OTDevice(
                name=name, ip_address=f"203.0.113.{len(self.devices) + 10}",
                device_type=kind, vendor="Test", status="Online",
                risk_level="Low", firmware_version="1",
                location="East Subdivision",
            )
            self.db.add(device)
            self.devices[name] = device
        self.db.commit()
        seed_track_blocks(self.db)
        seed_operational_assets(self.db)
        self.train = Train(
            symbol="EX-101", subdivision="East Subdivision", track="Main",
            direction="Eastbound", milepost=80.5, speed=25,
            status="Moving", ptc_enabled=True, current_signal="Clear",
        )
        self.db.add(self.train)
        self.db.commit()

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def definition(self, **changes):
        data = {
            "name": "Test Exercise",
            "description": "Exercise engine test",
            "category": "Incident Response",
            "difficulty": "Medium",
            "estimated_duration": 5,
            "recommended_players": 2,
            "objectives": [{
                "description": "Resolve all incidents",
                "objective_type": "incidents_resolved",
                "target_value": 0,
                "comparison": "eq",
            }],
            "script_events": [{
                "event_type": "inject_alert",
                "offset_seconds": 10,
                "payload": {
                    "device_id": self.devices["Signal Controller 14A"].id,
                    "severity": "High",
                    "alert_type": "Timed Test Alert",
                    "message": "Timed exercise inject",
                },
            }],
            "hints": [{
                "message": "Investigate the signal controller.",
                "available_after_seconds": 5,
            }],
        }
        data.update(changes)
        return data

    def assert_seed_happy_path(self, exercise_name):
        seed_exercises(self.db)
        exercise = self.db.query(Exercise).filter(
            Exercise.name == exercise_name
        ).one()
        run = create_run(self.db, exercise.id)
        start_run(self.db, run.id)
        run.started_at = utc_now() - timedelta(seconds=121)
        process_run(self.db, run)

        target = self.db.get(OTDevice, exercise.objectives[0].target_id)
        self.assertIsNotNone(target)
        perform_recovery_action(self.db, {
            "action_type": "RESTORE_KNOWN_GOOD",
            "target_id": target.id,
            "exercise_run_id": run.id,
        })
        for incident in self.db.query(Incident).filter(
            Incident.exercise_run_id == run.id
        ):
            incident.status = "Closed"
        request_objective_reevaluation(self.db, "test_walkthrough_completed")

        self.assertEqual(run.status, "Completed")
        self.assertTrue(all(
            state.status == "Completed"
            for state in run.objectives
            if not state.objective.optional
        ))
        report = after_action_report(self.db, run)
        self.assertEqual(report["status"], "Completed")
        self.assertGreaterEqual(run.score, 50)
        self.assertLessEqual(run.score, 100)

    def test_prevention_objective_maintains_then_fails_on_run_violation(self):
        exercise = create_exercise(self.db, self.definition(
            name="Safety Prevention",
            objectives=[{
                "description": "No unsafe route",
                "objective_type": "no_unsafe_routing",
                "target_value": 0,
            }],
        ))
        run = create_run(self.db, exercise.id)
        start_run(self.db, run.id)
        state = run.objectives[0]
        self.assertEqual(state.status, "Completed")
        self.assertEqual(state.progress, 100)

        record_event(
            self.db,
            event_type="dispatch_route_blocked",
            title="Unsafe route rejected",
            message="A conflicting route was attempted.",
            scenario_id=str(run.id),
        )
        request_objective_reevaluation(self.db, "unsafe_route")
        self.assertEqual(state.status, "Failed")
        self.assertEqual(run.status, "Failed")

    def test_numeric_equality_objective_survives_database_reload(self):
        exercise = create_exercise(self.db, self.definition(
            name="Persisted Numeric Equality",
            objectives=[{
                "description": "No unsafe route",
                "objective_type": "no_unsafe_routing",
                "target_value": 0,
                "comparison": "eq",
            }],
            script_events=[],
        ))
        run = create_run(self.db, exercise.id)
        start_run(self.db, run.id)
        self.db.commit()
        run_id = run.id
        self.db.expire_all()

        restored = self.db.get(ExerciseRun, run_id)
        evaluate_objectives(self.db, restored)
        state = restored.objectives[0]
        serialized = serialize_run(self.db, restored, instructor=True)[
            "objectives"
        ][0]

        self.assertEqual(state.current_value, 0)
        self.assertEqual(state.status, "Completed")
        self.assertEqual(serialized["blocking_reasons"], [])

    def test_incident_resolution_is_run_scoped_and_event_driven(self):
        historical = Incident(
            device="Historical Asset", alert_type="Old Incident",
            message="Unrelated historical incident", status="Open",
        )
        self.db.add(historical)
        exercise = create_exercise(self.db, self.definition(
            name="Scoped Incident Exercise",
            objectives=[{
                "description": "Close run incidents",
                "objective_type": "incidents_resolved",
                "target_value": 0,
            }],
        ))
        run = create_run(self.db, exercise.id)
        start_run(self.db, run.id)
        run.started_at = utc_now() - timedelta(seconds=11)
        process_run(self.db, run)
        state = run.objectives[0]
        self.assertEqual(state.current_value, 1)
        self.assertEqual(len(serialize_run(self.db, run, instructor=True)[
            "objectives"
        ][0]["blocking_reasons"]), 1)

        incident = self.db.query(Incident).filter(
            Incident.exercise_run_id == run.id
        ).one()
        incident.status = "Closed"
        request_objective_reevaluation(self.db, "incident_closed")
        self.assertEqual(state.current_value, 0)
        self.assertEqual(run.status, "Completed")
        self.assertEqual(historical.status, "Open")

    def test_finish_semantics_and_completion_event_are_idempotent(self):
        exercise = create_exercise(self.db, self.definition(
            name="Manual Finish",
            objectives=[{
                "description": "Impossible status",
                "objective_type": "device_status",
                "target_id": self.devices["Signal Controller 14A"].id,
                "metadata": {"status": "Offline"},
            }],
            script_events=[],
        ))
        run = create_run(self.db, exercise.id)
        start_run(self.db, run.id)
        with self.assertRaises(ExerciseValidationError) as context:
            finish_run(self.db, run.id)
        self.assertEqual(context.exception.status_code, 409)
        finish_run(self.db, run.id, confirm_cancel=True)
        self.assertEqual(run.status, "Cancelled")

        complete_exercise = create_exercise(self.db, self.definition(
            name="Automatic Finish",
            objectives=[{
                "description": "Controller online",
                "objective_type": "device_status",
                "target_id": self.devices["Signal Controller 14A"].id,
                "metadata": {"status": "Online"},
            }],
            script_events=[],
        ))
        completed = create_run(self.db, complete_exercise.id)
        start_run(self.db, completed.id)
        self.assertEqual(finish_run(self.db, completed.id).status, "Completed")
        request_objective_reevaluation(self.db, "repeat")
        process_run(self.db, completed)
        completion_events = self.db.query(ActivityLog).filter(
            ActivityLog.scenario_id == str(completed.id),
            ActivityLog.event_type == "exercise_completed",
        ).count()
        self.assertEqual(completion_events, 1)

    def test_walkthrough_spoiler_controls_reveal_and_live_blockers(self):
        exercise = create_exercise(self.db, self.definition(
            name="Hidden Walkthrough",
            objectives=[{
                "description": "Hidden close incidents",
                "objective_type": "incidents_resolved",
                "hidden": True,
            }],
            walkthrough={
                "overview": "Instructor answer",
                "instructor_notes": "Never expose this note.",
                "steps": [{
                    "title": "Hidden step",
                    "objective_index": 0,
                    "action_id": "CLOSE_INCIDENT",
                    "verification_condition": "exercise_open_incident_count == 0",
                    "player_visible": False,
                    "instructor_notes": "Instructor-only detail.",
                }],
            },
        ))
        run = create_run(self.db, exercise.id)
        start_run(self.db, run.id)
        player_run = serialize_run(self.db, run, instructor=False)
        instructor_run = serialize_run(self.db, run, instructor=True)
        self.assertEqual(player_run["objectives"], [])
        self.assertEqual(len(instructor_run["objectives"]), 1)
        self.assertEqual(
            serialize_walkthrough(exercise.walkthrough, run, False)["steps"], []
        )
        revealed = reveal_walkthrough(self.db, run.id)
        reveal_walkthrough(self.db, run.id)
        self.assertEqual(revealed["steps"], [])
        self.assertEqual(self.db.query(ActivityLog).filter(
            ActivityLog.scenario_id == str(run.id),
            ActivityLog.event_type == "exercise_walkthrough_revealed",
        ).count(), 1)

    def test_custom_exercise_without_walkthrough_remains_usable(self):
        exercise = create_exercise(self.db, self.definition(
            name="Legacy Imported Exercise", walkthrough=None
        ))
        run = create_run(self.db, exercise.id)
        start_run(self.db, run.id)
        self.assertIsNone(exercise.walkthrough)
        self.assertIn(run.status, {"Running", "Completed"})

    def test_custom_edit_preserves_walkthrough_links_and_hidden_content(self):
        definition = self.definition(
            name="Editable Walkthrough",
            objectives=[{
                "description": "Hidden objective",
                "objective_type": "incidents_resolved",
                "hidden": True,
            }],
            walkthrough={
                "overview": "Private guidance",
                "steps": [{
                    "title": "Resolve incident",
                    "objective_index": 0,
                    "action_id": "CLOSE_INCIDENT",
                    "verification_condition": "exercise_open_incident_count == 0",
                    "player_visible": False,
                }],
            },
        )
        exercise = create_exercise(self.db, definition)
        update_exercise(self.db, exercise, {
            **definition,
            "description": "Updated description",
        })
        self.assertEqual(
            exercise.walkthrough.steps[0].linked_objective_id,
            exercise.objectives[0].id,
        )
        run = create_run(self.db, exercise.id)
        player = serialize_run(self.db, run, instructor=False)
        instructor = serialize_run(self.db, run, instructor=True)
        self.assertEqual(player["objectives"], [])
        self.assertEqual(len(instructor["objectives"]), 1)

    def test_validator_covers_seeded_walkthroughs_and_rejects_bad_config(self):
        exercises = seed_exercises(self.db)
        for exercise in exercises:
            with self.subTest(exercise=exercise.name):
                result = validate_exercise_configuration(self.db, exercise)
                self.assertTrue(result["completion_readiness"], result)
                self.assertEqual(
                    result["objective_coverage"]["required"],
                    result["objective_coverage"]["covered"],
                )

        broken = create_exercise(self.db, self.definition(
            name="Broken Validation", walkthrough=None
        ))
        broken.objectives[0].objective_type = "unsupported_evaluator"
        result = validate_exercise_configuration(self.db, broken)
        self.assertFalse(result["completion_readiness"])
        self.assertTrue(any("unsupported evaluator" in error for error in result["errors"]))

    def test_seeded_objectives_wait_for_their_scripted_injects(self):
        exercises = seed_exercises(self.db)
        for exercise in exercises:
            with self.subTest(exercise=exercise.name):
                run = create_run(self.db, exercise.id)
                start_run(self.db, run.id)
                statuses = {
                    state.objective.objective_type: state.status
                    for state in run.objectives
                }
                self.assertEqual(statuses["device_status"], "Pending")
                self.assertEqual(statuses["track_availability_min"], "Pending")
                self.assertEqual(statuses["no_unsafe_routing"], "Pending")
                self.assertEqual(statuses["incidents_resolved"], "Pending")
                self.assertEqual(run.status, "Running")

                hints = sorted(
                    exercise.hints,
                    key=lambda item: item.available_after_seconds,
                )
                self.assertGreaterEqual(len(hints), 4)
                self.assertEqual(hints[0].available_after_seconds, 0)
                self.assertIn("Launch Attack", hints[0].message)
                self.assertTrue(any(
                    "Dispatcher Operations" in hint.message
                    and exercise.objectives[0].target_id is not None
                    for hint in hints
                ))

    def test_seeded_restore_objective_opens_after_attack_inject(self):
        exercise = seed_exercises(self.db)[0]
        run = create_run(self.db, exercise.id)
        start_run(self.db, run.id)
        run.started_at = utc_now() - timedelta(seconds=121)
        process_run(self.db, run)

        states = {
            state.objective.objective_type: state
            for state in run.objectives
        }
        self.assertNotEqual(states["device_status"].status, "Completed")
        self.assertGreaterEqual(states["incidents_resolved"].current_value, 1)
        self.assertEqual(states["incidents_resolved"].status, "In Progress")
        self.assertEqual(run.status, "Running")

    def test_after_action_report_refreshes_final_diagnostics(self):
        exercise = create_exercise(self.db, self.definition(
            name="AAR Diagnostics",
            objectives=[{
                "description": "Close run incidents",
                "objective_type": "incidents_resolved",
            }],
        ))
        run = create_run(self.db, exercise.id)
        start_run(self.db, run.id)
        run.started_at = utc_now() - timedelta(seconds=11)
        process_run(self.db, run)
        cancel_run(self.db, run.id)
        report = after_action_report(self.db, run)
        self.assertEqual(report["status"], "Cancelled")
        self.assertTrue(report["objectives"][0]["blocking_reasons"])
        self.assertTrue(report["cancellation_reason"])

    def test_exercise_creation_clone_and_deletion(self):
        exercise = create_exercise(self.db, self.definition())
        cloned = clone_exercise(self.db, exercise, "Cloned Exercise")
        self.db.commit()
        self.assertEqual(len(exercise.objectives), 1)
        self.assertEqual(len(cloned.script_events), 1)
        self.db.delete(cloned)
        self.db.commit()
        self.assertIsNone(
            self.db.query(Exercise).filter(Exercise.id == cloned.id).first()
        )

    def test_timed_event_executes_once_and_updates_objective(self):
        exercise = create_exercise(self.db, self.definition())
        run = create_run(self.db, exercise.id)
        start_run(self.db, run.id)
        run.started_at = utc_now() - timedelta(seconds=11)
        process_run(self.db, run)
        process_run(self.db, run)
        self.assertEqual(
            self.db.query(Incident).filter(
                Incident.alert_type == "Timed Test Alert"
            ).count(),
            1,
        )
        self.assertEqual(run.objectives[0].status, "In Progress")
        incident = self.db.query(Incident).one()
        incident.status = "Closed"
        process_run(self.db, run)
        self.assertEqual(run.status, "Completed")
        self.assertEqual(run.objectives[0].status, "Completed")

    def test_scripted_attack_reuses_attack_engine(self):
        definition = self.definition(
            name="Attack Exercise",
            script_events=[{
                "event_type": "launch_attack",
                "offset_seconds": 2,
                "payload": {
                    "attack_id": "logic_modification",
                    "target_ids": [self.devices["Signal Controller 14A"].id],
                },
            }],
        )
        run = create_run(self.db, create_exercise(self.db, definition).id)
        start_run(self.db, run.id)
        run.started_at = utc_now() - timedelta(seconds=3)
        process_run(self.db, run)
        self.assertEqual(
            self.devices["Signal Controller 14A"].status, "Compromised"
        )
        self.assertTrue(
            self.db.query(ActivityLog).filter(
                ActivityLog.event_type == "exercise_launch_attack"
            ).first()
        )

    def test_pause_resume_and_cancel(self):
        run = create_run(
            self.db, create_exercise(self.db, self.definition()).id
        )
        start_run(self.db, run.id)
        pause_run(self.db, run.id)
        self.assertEqual(run.status, "Paused")
        elapsed = run.elapsed_seconds
        resume_run(self.db, run.id)
        self.assertEqual(run.status, "Running")
        self.assertEqual(run.accumulated_seconds, elapsed)
        cancel_run(self.db, run.id)
        self.assertEqual(run.status, "Cancelled")

    def test_checkpoint_save_and_restore(self):
        run = create_run(
            self.db, create_exercise(self.db, self.definition()).id
        )
        start_run(self.db, run.id)
        checkpoint = save_checkpoint(self.db, run.id, "Before disruption")
        original_milepost = self.train.milepost
        self.train.milepost = 99.0
        self.train.status = "Arrived"
        restore_checkpoint(self.db, run.id, checkpoint.id)
        self.assertEqual(self.train.milepost, original_milepost)
        self.assertEqual(self.train.status, "Moving")

    def test_score_uses_live_incident_and_operational_state(self):
        run = create_run(
            self.db, create_exercise(self.db, self.definition()).id
        )
        start_run(self.db, run.id)
        baseline = run.score
        run.started_at = utc_now() - timedelta(seconds=11)
        process_run(self.db, run)
        self.assertLess(run.cyber_score, 100)
        self.assertLess(run.score, baseline)

    def test_time_expiry_fails_incomplete_mission(self):
        definition = self.definition(
            name="Failure Exercise",
            estimated_duration=1,
            objectives=[{
                "description": "Impossible status",
                "objective_type": "device_status",
                "target_id": self.devices["Signal Controller 14A"].id,
                "metadata": {"status": "Impossible"},
            }],
            script_events=[],
        )
        run = create_run(self.db, create_exercise(self.db, definition).id)
        start_run(self.db, run.id)
        run.started_at = utc_now() - timedelta(seconds=61)
        process_run(self.db, run)
        self.assertEqual(run.status, "Failed")
        self.assertEqual(run.objectives[0].status, "Failed")

    def test_after_action_report_json_markdown_and_pdf(self):
        run = create_run(
            self.db, create_exercise(self.db, self.definition()).id
        )
        start_run(self.db, run.id)
        cancel_run(self.db, run.id)
        report = after_action_report(self.db, run)
        self.assertIn("mission_summary", report)
        self.assertIn("# After-Action Report", report["markdown"])
        self.assertTrue(simple_pdf(report["markdown"]).startswith(b"%PDF"))

    def test_seed_library_has_all_requested_exercises(self):
        seed_exercises(self.db)
        seed_exercises(self.db)
        names = {item.name for item in self.db.query(Exercise).all()}
        self.assertTrue({
            "Operation Broken Rail", "Signal Failure Recovery",
            "Communications Blackout", "Dispatch Under Attack",
            "Dark Territory", "PTC Outage", "Switch Chaos",
            "Grade Crossing Failure",
        }.issubset(names))
        self.assertEqual(self.db.query(Exercise).count(), 8)

    def test_run_history_is_persisted(self):
        exercise = create_exercise(self.db, self.definition())
        run = create_run(self.db, exercise.id, {"instructor": "Test"})
        self.db.commit()
        self.db.expire_all()
        restored = self.db.query(ExerciseRun).filter(
            ExerciseRun.id == run.id
        ).one()
        self.assertEqual(restored.status, "Ready")
        self.assertEqual(len(restored.objectives), 1)

    def test_clear_history_removes_run_state_and_preserves_definitions(self):
        exercise = create_exercise(self.db, self.definition())
        run = create_run(self.db, exercise.id)
        run_id = run.id
        start_run(self.db, run.id)
        save_checkpoint(self.db, run.id, "Before clear")
        cancel_run(self.db, run.id)
        self.db.commit()

        result = clear_exercise_history(self.db)
        self.db.commit()

        self.assertEqual(result["deleted_runs"], 1)
        self.assertEqual(result["deleted_checkpoints"], 1)
        self.assertEqual(self.db.query(ExerciseRun).count(), 0)
        self.assertEqual(self.db.query(ExerciseRunObjective).count(), 0)
        self.assertEqual(self.db.query(ExerciseRunEvent).count(), 0)
        self.assertEqual(self.db.query(ExerciseCheckpoint).count(), 0)
        self.assertEqual(self.db.query(Exercise).count(), 1)
        self.assertEqual(self.db.query(Exercise).one().name, "Test Exercise")
        self.assertEqual(
            self.db.query(ActivityLog).filter(
                ActivityLog.scenario_id == str(run_id)
            ).count(),
            0,
        )

    def test_clear_history_rejects_active_runs(self):
        exercise = create_exercise(self.db, self.definition())
        run = create_run(self.db, exercise.id)
        start_run(self.db, run.id)

        with self.assertRaisesRegex(
            RuntimeError, "Cancel or complete all active exercises"
        ):
            clear_exercise_history(self.db)

        self.assertEqual(self.db.query(ExerciseRun).count(), 1)

    def test_starting_exercise_resets_delay_measurement_window(self):
        stopped = record_event(
            self.db,
            event_type="train_stopped_signal",
            title="Historical stop",
            message="Historical train delay",
            train_id=self.train.id,
        )
        stopped.timestamp = utc_now() - timedelta(minutes=10)
        resumed = record_event(
            self.db,
            event_type="train_resumed",
            title="Historical resume",
            message="Historical train resumed",
            train_id=self.train.id,
        )
        resumed.timestamp = utc_now() - timedelta(minutes=5)
        self.db.flush()
        self.assertGreater(
            get_operational_impact(self.db)["cumulative_delay_minutes"], 0
        )

        run = create_run(
            self.db, create_exercise(self.db, self.definition()).id
        )
        start_run(self.db, run.id)
        impact = get_operational_impact(self.db)
        self.assertEqual(impact["cumulative_delay_minutes"], 0)
        self.assertEqual(impact["delay_window_reason"], "exercise_started")


def _seed_playthrough_test(exercise_name):
    def test(self):
        self.assert_seed_happy_path(exercise_name)
    test.__name__ = "test_seed_playthrough_" + exercise_name.lower().replace(" ", "_")
    return test


for _seed_name in [
    "Operation Broken Rail",
    "Signal Failure Recovery",
    "Communications Blackout",
    "Dispatch Under Attack",
    "Dark Territory",
    "PTC Outage",
    "Switch Chaos",
    "Grade Crossing Failure",
]:
    setattr(
        ExerciseEngineTests,
        "test_seed_playthrough_" + _seed_name.lower().replace(" ", "_"),
        _seed_playthrough_test(_seed_name),
    )


if __name__ == "__main__":
    unittest.main()
