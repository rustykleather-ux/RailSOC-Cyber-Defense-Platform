import json

from models import Exercise, ExerciseHint, OTDevice
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
                    "metadata": {
                        "status": "Online",
                        "activate_after_event_type": "launch_attack",
                    },
                },
                {
                    "description": "Maintain track availability at or above 90%.",
                    "objective_type": "track_availability_min",
                    "target_value": 90,
                    "comparison": "gte",
                    "metadata": {
                        "activate_after_event_type": "launch_attack",
                    },
                },
                {
                    "description": "Prevent unsafe switch or routing conditions.",
                    "objective_type": "no_unsafe_routing",
                    "target_value": 0,
                    "comparison": "eq",
                    "metadata": {
                        "mode": "prevention",
                        "activate_after_event_type": "launch_attack",
                    },
                },
                {
                    "description": "Resolve all active incidents.",
                    "objective_type": "incidents_resolved",
                    "target_value": 0,
                    "comparison": "eq",
                    "metadata": {
                        "mode": "resolution",
                        "scope": "exercise_run",
                        "activate_after_event_type": "inject_alert",
                    },
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
                    "offset_seconds": 150,
                    "payload": {
                        "title": "Instructor hint",
                        "message": (
                            f"The attack inject has run. Open Dispatcher Operations, "
                            f"select OT_DEVICE and {target_name}, then use Restore selected "
                            "device to known-good. Close the run incident only after recovery."
                        ),
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
            "hints": _hint_definitions(target_name),
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
            metadata.update({
                "mode": "prevention",
                "activate_after_event_type": "launch_attack",
            })
        if objective.objective_type == "incidents_resolved":
            metadata.update({
                "mode": "resolution",
                "scope": "exercise_run",
                "activate_after_event_type": "inject_alert",
            })
        if objective.objective_type == "track_availability_min":
            metadata["activate_after_event_type"] = "launch_attack"
        if objective.objective_type in {"device_status", "communications_restored"}:
            objective.target_type = "OT_DEVICE"
            objective.target_id = target.id if target else objective.target_id
            metadata["status"] = "Online"
            metadata["activate_after_event_type"] = "launch_attack"
        objective.metadata_json = json.dumps(metadata)
    for event in exercise.script_events:
        if event.event_type == "end_exercise":
            event.payload_json = json.dumps({
                "status": "Failed",
                "reason": "Exercise timer expired before completion.",
            })
        elif event.event_type == "display_hint":
            event.offset_seconds = 150
            event.payload_json = json.dumps({
                "title": "Instructor hint",
                "message": (
                    f"The attack inject has run. Open Dispatcher Operations, "
                    f"select OT_DEVICE and {target_name}, then use Restore selected "
                    "device to known-good. Close the run incident only after recovery."
                ),
            })
    hint_definitions = _hint_definitions(target_name)
    existing_hints = sorted(exercise.hints, key=lambda item: item.id or 0)
    for index, definition in enumerate(hint_definitions):
        if index < len(existing_hints):
            hint = existing_hints[index]
            hint.message = definition["message"]
            hint.available_after_seconds = definition["available_after_seconds"]
            hint.automatic = definition.get("automatic", False)
        else:
            exercise.hints.append(ExerciseHint(**definition))
    _replace_walkthrough(db, exercise, _walkthrough_definition(exercise, target_name))


def _hint_definitions(target_name):
    return [
        {
            "message": (
                "First, open Exercise Timeline and wait for the Launch Attack entry. "
                "Restore, availability, and safety objectives intentionally remain "
                "Waiting until that inject runs."
            ),
            "available_after_seconds": 0,
        },
        {
            "message": (
                f"Open Incident Center and select the incident for {target_name} "
                "that belongs to this exercise run. Acknowledge it, assign an analyst, "
                "and add an investigation note. Do not close it until recovery is verified."
            ),
            "available_after_seconds": 30,
        },
        {
            "message": (
                f"After Launch Attack appears in the timeline, open Dispatcher Operations. "
                f"In Command center choose Target type OT_DEVICE, select {target_name}, "
                "and click Restore selected device to known-good."
            ),
            "available_after_seconds": 120,
        },
        {
            "message": (
                "Finish by checking Operational impact in Dispatcher Operations: track "
                "availability must be at least 90% and no unsafe route request may have "
                "been attempted. Then close only this run's incidents in Incident Center "
                "and return to Exercise Center; completion is automatic."
            ),
            "available_after_seconds": 150,
        },
    ]


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
            "If an objective says Waiting, keep the run active until Exercise Timeline shows Launch Attack.",
            "If Restore is disabled, choose Target type OT_DEVICE and select the named target first.",
            "If recovery is rejected, read the error and clear the named operational restriction before retrying.",
            "A blocked unsafe route request is still a safety violation; restart the run if one was attempted.",
        ],
        "instructor_notes": (
            "This answer sheet is configuration guidance, not an automated playbook. "
            "Do not perform learner actions on their behalf."
        ),
        "steps": [
            {
                "title": "Inspect the affected asset",
                "purpose": "Confirm the scripted cyber and operational condition.",
                "player_action": (
                    "In Exercise Center, open Timeline and wait for Launch Attack. "
                    f"Then open OT Assets, find {target_name}, and review its Status, "
                    "Risk, and controlled systems."
                ),
                "navigation_location": "/assets",
                "target_asset": target_name,
                "expected_result": "The affected status, risk, and relationships are visible.",
                "verification_condition": "device_exists",
                "action_id": "VIEW_ASSET",
                "hint": "The recovery objective should remain Waiting until Launch Attack executes.",
                "common_mistakes": ["Restoring before reviewing the incident and impact."],
            },
            {
                "title": "Triage the exercise incident",
                "purpose": "Establish incident ownership before recovery.",
                "player_action": (
                    f"Open Incident Center, select the incident for {target_name} created "
                    "by this run, click Acknowledge, assign an analyst, and save an "
                    "investigation note. Leave the incident open for now."
                ),
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
                "player_action": (
                    "Open Dispatcher Operations. Under Command center, set Target type "
                    f"to OT_DEVICE, select {target_name}, and click Restore selected "
                    "device to known-good."
                ),
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
                "player_action": (
                    "In Dispatcher Operations, read Operational impact. Confirm Track "
                    "available is 90% or higher. If it already meets 90% after the attack, "
                    "no dispatch command is required."
                ),
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
                "player_action": (
                    "Do not submit a route that crosses an occupied, restricted, or "
                    "reserved block, and do not move a switch on an occupied block. "
                    "No action is required while the unsafe-operation count stays zero."
                ),
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
                "player_action": (
                    f"After {target_name} is Online, return to Incident Center. Filter or "
                    "identify incidents from the current exercise run and set each one to "
                    "Closed. Do not close unrelated historical incidents."
                ),
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
