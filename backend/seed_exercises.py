from models import Exercise, OTDevice
from services.exercise_service import create_exercise


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
                },
                {
                    "description": "Resolve all active incidents.",
                    "objective_type": "incidents_resolved",
                    "target_value": 0,
                    "comparison": "eq",
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
                    "payload": {"status": "Completed"},
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
        seeded.append(exercise)
    db.flush()
    return seeded
