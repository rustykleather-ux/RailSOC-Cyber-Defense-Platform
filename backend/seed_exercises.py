import json

from models import Exercise, OTDevice
from services.exercise_service import _replace_walkthrough, create_exercise


EXERCISE_SEEDS = [
    ("Operation Broken Rail", "Incident Response", "Hard",
     "Contain a controller compromise while preserving safe train operations.",
     "logic_modification", "Signal Controller 14A"),
    ("Signal Failure Recovery", "Signals", "Medium",
     "Restore trusted signal control and safely recover affected blocks.",
     "logic_modification", "Signal Controller 14A"),
    ("Communications Blackout", "Communications", "Hard",
     "Manage degraded field communications and restore service availability.",
     "communication_failure", "PTC Radio Gateway"),
    ("Dispatch Under Attack", "Dispatcher", "Expert",
     "Maintain safe operations while Dispatch SCADA command handling degrades.",
     "denial_of_service", "Dispatch SCADA Server"),
    ("Dark Territory", "Operations", "Hard",
     "Respond to unavailable signal indications without unsafe routing.",
     "communication_failure", "Signal Controller 14A"),
    ("PTC Outage", "PTC", "Hard",
     "Restore PTC communications while controlling train delay.",
     "communication_failure", "PTC Radio Gateway"),
    ("Switch Chaos", "Operations", "Expert",
     "Contain malicious switch control and prevent unsafe movement.",
     "logic_modification", "Switch Machine Controller"),
    ("Grade Crossing Failure", "Signals", "Medium",
     "Protect the public and restore a compromised grade crossing controller.",
     "firmware_tampering", "Grade Crossing Controller MP 82.4"),
]


def seed_exercises(db):
    seeded = []
    for name, category, difficulty, description, attack_id, target_name in EXERCISE_SEEDS:
        existing = db.query(Exercise).filter(Exercise.name == name).first()
        if existing:
            _reconcile_seeded_exercise(db, existing, target_name)
            seeded.append(existing)
            continue
        target = db.query(OTDevice).filter(OTDevice.name == target_name).first()
        target_id = target.id if target else None
        exercise = create_exercise(db, {
            "name": name,
            "description": description,
            "category": category,
            "difficulty": difficulty,
            "estimated_duration": 20,
            "recommended_players": 2,
            "known_intelligence": (
                "Abnormal OT behavior has been reported. Initial information "
                "may be incomplete; validate conditions using live system state."
            ),
            "success_criteria": (
                "Restore trusted operations, complete required objectives, "
                "and maintain modeled safety constraints."
            ),
            "failure_conditions": (
                "Exercise time expires with required objectives incomplete or "
                "an unsafe routing condition occurs."
            ),
            "objectives": [
                {
                    "description": f"Restore {target_name} to Online.",
                    "objective_type": "device_status",
                    "target_type": "OT_DEVICE",
                    "target_id": target_id,
                    "metadata": {"status": "Online"},
                },
                {
                    "description": "Maintain track availability at or above 90%.",
                    "objective_type": "track_availability_min",
                    "target_value": 90,
                    "comparison": "gte",
                },
                {
                    "description": "Prevent unsafe switch or routing conditions.",
                    "objective_type": "no_unsafe_routing",
                    "target_value": 0,
                    "comparison": "eq",
                    "metadata": {"mode": "prevention"},
                },
                {
                    "description": "Resolve all active incidents.",
                    "objective_type": "incidents_resolved",
                    "target_value": 0,
                    "comparison": "eq",
                    "metadata": {"mode": "resolution", "scope": "exercise_run"},
                },
            ],
            "script_events": [
                {
                    "event_type": "display_message",
                    "offset_seconds": 0,
                    "payload": {
                        "title": "Mission briefing",
                        "message": description,
                    },
                },
                {
                    "event_type": "inject_alert",
                    "offset_seconds": 30,
                    "payload": {
                        "device_id": target_id,
                        "severity": "Medium",
                        "alert_type": "Exercise Intelligence",
                        "message": f"Abnormal activity detected at {target_name}.",
                    },
                },
                {
                    "event_type": "launch_attack",
                    "offset_seconds": 120,
                    "payload": {
                        "attack_id": attack_id,
                        "target_ids": [target_id] if target_id else [],
                    },
                },
                {
                    "event_type": "display_hint",
                    "offset_seconds": 300,
                    "payload": {
                        "title": "Instructor hint",
                        "message": f"Review the security and communications state of {target_name}.",
                    },
                },
                {
                    "event_type": "end_exercise",
                    "offset_seconds": 1200,
                    "payload": {
                        "status": "Failed",
                        "reason": "Exercise timer expired before completion.",
                    },
                },
            ],
            "hints": [
                {
                    "message": f"Investigate {target_name} and its controlled assets.",
                    "available_after_seconds": 180,
                },
                {
                    "message": "Compare dispatcher, incident, and operational-impact state before recovery.",
                    "available_after_seconds": 360,
                },
            ],
        })
        _replace_walkthrough(db, exercise, _walkthrough_definition(exercise, target_name))
        seeded.append(exercise)
    db.flush()
    return seeded


def _reconcile_seeded_exercise(db, exercise, target_name):
    target = db.query(OTDevice).filter(OTDevice.name == target_name).first()
    for objective in exercise.objectives:
        metadata = {}
        try:
            metadata = json.loads(objective.metadata_json or "{}")
        except (TypeError, ValueError):
            metadata = {}
        if objective.objective_type == "no_unsafe_routing":
            metadata["mode"] = "prevention"
        if objective.objective_type == "incidents_resolved":
            metadata.update({"mode": "resolution", "scope": "exercise_run"})
        if objective.objective_type in {"device_status", "communications_restored"}:
            objective.target_type = "OT_DEVICE"
            objective.target_id = target.id if target else objective.target_id
            metadata["status"] = "Online"
        objective.metadata_json = json.dumps(metadata)
    for event in exercise.script_events:
        if event.event_type == "end_exercise":
            event.payload_json = json.dumps({
                "status": "Failed",
                "reason": "Exercise timer expired before completion.",
            })
    if not exercise.walkthrough:
        _replace_walkthrough(db, exercise, _walkthrough_definition(exercise, target_name))


def _walkthrough_definition(exercise, target_name):
    objectives = list(exercise.objectives)
    by_type = {item.objective_type: index for index, item in enumerate(objectives)}
    return {
        "overview": (
            f"Complete {exercise.name} by investigating the exercise inject, "
            f"restoring {target_name}, maintaining safe operations, and closing "
            "only the incidents created by this run."
        ),
        "prerequisites": [
            "Start from the TrackSentinel operational baseline.",
            "Allow the scripted exercise inject to execute.",
        ],
        "expected_end_state": [
            f"{target_name} is Online.",
            "Track availability is at least 90%.",
            "No unsafe switch or route violation was recorded.",
            "All incidents linked to this run are Closed.",
            "The run transitions automatically to Completed.",
        ],
        "troubleshooting": [
            "Use Show current blocker to identify an unresolved incident or unsafe condition.",
            "If recovery is blocked, review the Incident Center and Dispatcher Operations state.",
        ],
        "instructor_notes": (
            "This answer sheet is configuration guidance, not an automated playbook. "
            "Do not perform learner actions on their behalf."
        ),
        "steps": [
            {
                "title": "Inspect the affected asset",
                "purpose": "Confirm the scripted cyber and operational condition.",
                "player_action": f"Open OT Assets and inspect {target_name}.",
                "navigation_location": "/assets",
                "target_asset": target_name,
                "expected_result": "The affected status, risk, and relationships are visible.",
                "verification_condition": "device_exists",
                "action_id": "VIEW_ASSET",
                "hint": "Compare the asset with its controlled operational systems.",
                "common_mistakes": ["Restoring before reviewing the incident and impact."],
            },
            {
                "title": "Triage the exercise incident",
                "purpose": "Establish incident ownership before recovery.",
                "player_action": "Open Incident Center, acknowledge the run incident, assign an analyst, and add notes.",
                "navigation_location": "/incidents",
                "target_asset": target_name,
                "expected_result": "The incident is acknowledged and has an owner and investigation notes.",
                "verification_condition": "exercise_incident_triaged",
                "action_id": "ACKNOWLEDGE_INCIDENT",
                "common_mistakes": ["Working an unrelated historical incident."],
            },
            {
                "title": "Restore trusted asset state",
                "purpose": "Return the targeted controller or gateway to its trusted baseline.",
                "player_action": "Use the approved Restore Known Good recovery action.",
                "navigation_location": "/dispatcher",
                "target_asset": target_name,
                "expected_result": f"{target_name} reports Online.",
                "verification_condition": "device_status == Online",
                "objective_index": by_type.get("device_status"),
                "action_id": "RESTORE_KNOWN_GOOD",
                "recovery_path": "If restoration is blocked, clear the active operational restriction first.",
            },
            {
                "title": "Verify operational availability",
                "purpose": "Confirm the railroad remains available after recovery.",
                "player_action": "Review Operational Impact and controlled assets.",
                "navigation_location": "/dispatcher",
                "target_asset": target_name,
                "expected_result": "Track availability is at least 90%.",
                "verification_condition": "track_availability >= 90",
                "objective_index": by_type.get("track_availability_min"),
                "action_id": "VIEW_OPERATIONAL_IMPACT",
            },
            {
                "title": "Maintain routing safety",
                "purpose": "Preserve the prevention objective throughout the run.",
                "player_action": "Do not issue a conflicting route or move a switch beneath a train.",
                "navigation_location": "/dispatcher",
                "expected_result": "Unsafe-operation count remains zero and the objective shows Maintained/Completed.",
                "verification_condition": "unsafe_operation_count == 0",
                "objective_index": by_type.get("no_unsafe_routing"),
                "action_id": "VIEW_OBJECTIVES",
                "common_mistakes": ["Treating a blocked unsafe route request as harmless."],
            },
            {
                "title": "Close run incidents",
                "purpose": "Resolve only the incidents generated by this exercise run.",
                "player_action": "Close every remaining exercise incident in Incident Center.",
                "navigation_location": "/incidents",
                "target_asset": target_name,
                "expected_result": "Exercise open incident count is zero.",
                "verification_condition": "exercise_open_incident_count == 0",
                "objective_index": by_type.get("incidents_resolved"),
                "action_id": "CLOSE_INCIDENT",
            },
            {
                "title": "Verify automatic completion",
                "purpose": "Confirm the run-state engine has accepted all required outcomes.",
                "player_action": "Return to Exercise Center and verify every required objective is complete.",
                "navigation_location": "/exercises",
                "expected_result": "The run transitions to Completed and the AAR reports Completed.",
                "verification_condition": "all_required_objectives_completed",
                "action_id": "FINISH_EXERCISE",
            },
        ],
    }
