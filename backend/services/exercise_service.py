import json
from datetime import datetime, timezone

from attack_catalog import Attack_Catalog
from models import (
    ActivityLog,
    Alert,
    DispatchCommand,
    DispatchRoute,
    Exercise,
    ExerciseCheckpoint,
    ExerciseHint,
    ExerciseObjective,
    ExerciseRun,
    ExerciseRunEvent,
    ExerciseRunObjective,
    ExerciseScriptEvent,
    ExerciseWalkthrough,
    ExerciseWalkthroughStep,
    GradeCrossing,
    Incident,
    OTDevice,
    OperationalRestriction,
    TrackBlock,
    TrackSwitch,
    Train,
)
from services.dispatch_service import (
    create_dispatch_command,
    get_dispatch_status,
    perform_recovery_action,
)
from services.operational_impact import build_operational_summary, get_operational_impact
from services.timeline_service import get_timeline, record_event, utc_now
from simulation_engine import apply_attack


CATEGORIES = {
    "Incident Response", "Signals", "PTC", "Communications", "SCADA",
    "Dispatcher", "Operations", "Power", "Custom",
}
DIFFICULTIES = {"Easy", "Medium", "Hard", "Expert"}
RUN_STATUSES = {"Ready", "Running", "Paused", "Completed", "Failed", "Cancelled"}
EVENT_TYPES = {
    "wait", "display_message", "launch_attack", "spawn_incident",
    "restore_asset", "dispatch_train", "spawn_train", "inject_alert",
    "display_hint", "change_weather", "pause", "resume", "end_exercise",
}
OBJECTIVE_TYPES = {
    "device_status", "communications_restored", "track_availability_min",
    "train_delay_max", "dispatch_availability_min", "no_unsafe_routing",
    "incidents_resolved", "command_queue_max", "elapsed_max",
    "action_count", "event_sequence", "sustained_metric",
}
OBJECTIVE_MODES = {
    "device_status": "achievement",
    "communications_restored": "achievement",
    "track_availability_min": "threshold",
    "train_delay_max": "threshold",
    "dispatch_availability_min": "threshold",
    "no_unsafe_routing": "prevention",
    "incidents_resolved": "resolution",
    "command_queue_max": "threshold",
    "elapsed_max": "timed",
    "action_count": "count",
    "event_sequence": "sequence",
    "sustained_metric": "sustained",
}
TERMINAL_INCIDENT_STATUSES = {"closed", "resolved"}
UNSAFE_EVENT_TYPES = {
    "dispatch_route_blocked",
    "unsafe_operation_detected",
    "switch_under_train_attempt",
    "unsafe_switch_movement",
    "route_conflict_detected",
}
WALKTHROUGH_ACTIONS = {
    "VIEW_ASSET", "ACKNOWLEDGE_INCIDENT", "ASSIGN_INCIDENT",
    "ADD_INVESTIGATION_NOTES", "ISOLATE_DEVICE", "RESTORE_KNOWN_GOOD",
    "RESTORE_COMMUNICATIONS", "CLEAR_ATTACK_EFFECT", "CLOSE_INCIDENT",
    "VIEW_OPERATIONAL_IMPACT", "VIEW_OBJECTIVES", "FINISH_EXERCISE",
}
COMPARISON_OPERATORS = {"eq", "ne", "gt", "gte", "lt", "lte"}
SUPPORTED_DEVICE_STATUSES = {
    "online", "offline", "degraded", "compromised", "isolated", "safe mode",
}
WALKTHROUGH_VERIFICATIONS = {
    "device_exists", "exercise_incident_triaged", "device_status == online",
    "track_availability >= 90", "unsafe_operation_count == 0",
    "exercise_open_incident_count == 0", "all_required_objectives_completed",
}


class ExerciseValidationError(RuntimeError):
    def __init__(self, message, status_code=400):
        super().__init__(message)
        self.status_code = status_code


def _loads(value, default):
    try:
        return json.loads(value or "")
    except (TypeError, json.JSONDecodeError):
        return default


def _aware(value):
    if value and value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def _elapsed(run, now=None):
    total = int(run.accumulated_seconds or 0)
    if run.status == "Running" and run.started_at:
        total += max(0, int(((now or utc_now()) - _aware(run.started_at)).total_seconds()))
    return total


def _validate_definition(data):
    requested_category = str(data.get("category", "Custom")).strip()
    category = next(
        (item for item in CATEGORIES if item.lower() == requested_category.lower()),
        None,
    )
    if category is None:
        raise ExerciseValidationError(f"Category must be one of: {', '.join(sorted(CATEGORIES))}.")
    requested_difficulty = str(data.get("difficulty", "Medium")).strip()
    difficulty = next(
        (item for item in DIFFICULTIES if item.lower() == requested_difficulty.lower()),
        None,
    )
    if difficulty is None:
        raise ExerciseValidationError("Difficulty must be Easy, Medium, Hard, or Expert.")
    for objective in data.get("objectives") or []:
        if objective.get("objective_type") not in OBJECTIVE_TYPES:
            raise ExerciseValidationError(
                f"Unsupported objective type: {objective.get('objective_type')}."
            )
    for event in data.get("script_events") or []:
        if event.get("event_type") not in EVENT_TYPES:
            raise ExerciseValidationError(
                f"Unsupported script event type: {event.get('event_type')}."
            )
        if int(event.get("offset_seconds", 0)) < 0:
            raise ExerciseValidationError("Event time cannot be negative.")
    return category, difficulty


def create_exercise(db, data):
    category, difficulty = _validate_definition(data)
    name = str(data.get("name") or "").strip()
    if not name:
        raise ExerciseValidationError("Exercise name is required.")
    if db.query(Exercise).filter(Exercise.name == name).first():
        raise ExerciseValidationError("An exercise with this name already exists.", 409)
    exercise = Exercise(
        name=name,
        description=data.get("description") or "",
        category=category,
        difficulty=difficulty,
        estimated_duration=max(1, int(data.get("estimated_duration", 20))),
        recommended_players=max(1, int(data.get("recommended_players", 1))),
        enabled=bool(data.get("enabled", True)),
        favorite=bool(data.get("favorite", False)),
        known_intelligence=data.get("known_intelligence") or "",
        success_criteria=data.get("success_criteria") or "",
        failure_conditions=data.get("failure_conditions") or "",
        metadata_json=json.dumps(data.get("metadata") or {}),
    )
    db.add(exercise)
    db.flush()
    _replace_children(db, exercise, data)
    return exercise


def update_exercise(db, exercise, data):
    existing = serialize_exercise(
        exercise, include_definition=True, instructor=True
    )
    if exercise.walkthrough:
        existing["walkthrough"] = _walkthrough_definition_data(exercise)
    merged = {**existing, **data}
    category, difficulty = _validate_definition(merged)
    for field in [
        "name", "description", "estimated_duration", "recommended_players",
        "enabled", "favorite", "known_intelligence", "success_criteria",
        "failure_conditions",
    ]:
        if field in data:
            setattr(exercise, field, data[field])
    exercise.category, exercise.difficulty = category, difficulty
    if "metadata" in data:
        exercise.metadata_json = json.dumps(data["metadata"] or {})
    if any(key in data for key in ["objectives", "script_events", "hints", "walkthrough"]):
        _replace_children(db, exercise, merged)
    exercise.updated_at = utc_now()
    db.flush()
    return exercise


def _replace_children(db, exercise, data):
    if exercise.walkthrough:
        db.delete(exercise.walkthrough)
        exercise.walkthrough = None
        db.flush()
    exercise.objectives.clear()
    exercise.script_events.clear()
    exercise.hints.clear()
    db.flush()
    for index, item in enumerate(data.get("objectives") or []):
        exercise.objectives.append(ExerciseObjective(
            description=item.get("description") or item["objective_type"].replace("_", " ").title(),
            objective_type=item["objective_type"],
            target_type=item.get("target_type"),
            target_id=item.get("target_id"),
            target_value=item.get("target_value"),
            comparison=item.get("comparison", "eq"),
            optional=bool(item.get("optional", False)),
            hidden=bool(item.get("hidden", False)),
            weight=float(item.get("weight", 1)),
            sort_order=index,
            metadata_json=json.dumps(item.get("metadata") or {}),
        ))
    for index, item in enumerate(data.get("script_events") or []):
        exercise.script_events.append(ExerciseScriptEvent(
            event_type=item["event_type"],
            offset_seconds=int(item.get("offset_seconds", 0)),
            condition_json=json.dumps(item.get("condition") or {}),
            payload_json=json.dumps(item.get("payload") or {}),
            one_time=bool(item.get("one_time", True)),
            sort_order=index,
        ))
    for item in data.get("hints") or []:
        exercise.hints.append(ExerciseHint(
            message=item.get("message") or "Review current railroad state.",
            available_after_seconds=int(item.get("available_after_seconds", 0)),
            automatic=bool(item.get("automatic", False)),
            condition_json=json.dumps(item.get("condition") or {}),
        ))
    if "walkthrough" in data:
        _replace_walkthrough(db, exercise, data.get("walkthrough"))
    db.flush()


def _replace_walkthrough(db, exercise, data):
    if exercise.walkthrough:
        db.delete(exercise.walkthrough)
        db.flush()
    if not data:
        return None
    walkthrough = ExerciseWalkthrough(
        exercise_id=exercise.id,
        overview=data.get("overview") or "",
        prerequisites_json=json.dumps(data.get("prerequisites") or []),
        troubleshooting_json=json.dumps(data.get("troubleshooting") or []),
        expected_end_state_json=json.dumps(data.get("expected_end_state") or []),
        instructor_notes=data.get("instructor_notes") or "",
        version=max(1, int(data.get("version", 1))),
    )
    exercise.walkthrough = walkthrough
    db.add(walkthrough)
    db.flush()
    objectives = list(exercise.objectives)
    for index, item in enumerate(data.get("steps") or []):
        objective_index = item.get("objective_index")
        linked_id = item.get("linked_objective_id")
        if linked_id is None and isinstance(objective_index, int) and 0 <= objective_index < len(objectives):
            linked_id = objectives[objective_index].id
        walkthrough.steps.append(ExerciseWalkthroughStep(
            step_number=int(item.get("step_number", index + 1)),
            title=item.get("title") or f"Step {index + 1}",
            purpose=item.get("purpose") or "",
            player_action=item.get("player_action") or "",
            navigation_location=item.get("navigation_location") or "",
            target_asset=item.get("target_asset") or "",
            expected_result=item.get("expected_result") or "",
            verification_condition=item.get("verification_condition") or "",
            linked_objective_id=linked_id,
            action_id=str(item.get("action_id") or "").upper(),
            hint=item.get("hint") or "",
            common_mistakes_json=json.dumps(item.get("common_mistakes") or []),
            recovery_path=item.get("recovery_path") or "",
            instructor_notes=item.get("instructor_notes") or "",
            player_visible=bool(item.get("player_visible", True)),
        ))
    db.flush()
    return walkthrough


def clone_exercise(db, exercise, name=None):
    data = serialize_exercise(exercise, include_definition=True, instructor=True)
    if exercise.walkthrough:
        data["walkthrough"] = _walkthrough_definition_data(exercise)
    data["name"] = name or f"{exercise.name} Copy"
    data.pop("id", None)
    return create_exercise(db, data)


def _walkthrough_definition_data(exercise):
    """Serialize authoring data while remapping objective links by list index."""
    objective_indexes = {
        objective.id: index for index, objective in enumerate(exercise.objectives)
    }
    walkthrough = exercise.walkthrough
    if not walkthrough:
        return None
    return {
        "overview": walkthrough.overview,
        "prerequisites": _loads(walkthrough.prerequisites_json, []),
        "troubleshooting": _loads(walkthrough.troubleshooting_json, []),
        "expected_end_state": _loads(walkthrough.expected_end_state_json, []),
        "instructor_notes": walkthrough.instructor_notes,
        "version": walkthrough.version,
        "steps": [
            {
                "step_number": step.step_number,
                "title": step.title,
                "purpose": step.purpose,
                "player_action": step.player_action,
                "navigation_location": step.navigation_location,
                "target_asset": step.target_asset,
                "expected_result": step.expected_result,
                "verification_condition": step.verification_condition,
                "objective_index": objective_indexes.get(step.linked_objective_id),
                "action_id": step.action_id,
                "hint": step.hint,
                "common_mistakes": _loads(step.common_mistakes_json, []),
                "recovery_path": step.recovery_path,
                "instructor_notes": step.instructor_notes,
                "player_visible": step.player_visible,
            }
            for step in walkthrough.steps
        ],
    }


def create_run(db, exercise_id, metadata=None):
    exercise = db.query(Exercise).filter(Exercise.id == exercise_id).first()
    if not exercise:
        raise ExerciseValidationError("Exercise was not found.", 404)
    if not exercise.enabled:
        raise ExerciseValidationError("Exercise is disabled.", 409)
    run = ExerciseRun(exercise_id=exercise.id, metadata_json=json.dumps(metadata or {}))
    db.add(run)
    db.flush()
    for objective in exercise.objectives:
        db.add(ExerciseRunObjective(
            run_id=run.id, objective_id=objective.id,
            status="Hidden" if objective.hidden else "Pending",
        ))
    for event in exercise.script_events:
        db.add(ExerciseRunEvent(
            run_id=run.id, script_event_id=event.id, status="Pending"
        ))
    db.flush()
    return run


def clear_exercise_history(db):
    """Delete run-specific history without deleting exercise definitions."""
    active_count = db.query(ExerciseRun).filter(
        ExerciseRun.status.in_(["Running", "Paused"])
    ).count()
    if active_count:
        raise ExerciseValidationError(
            "Cancel or complete all active exercises before clearing history.",
            409,
        )

    run_ids = [row.id for row in db.query(ExerciseRun.id).all()]
    if not run_ids:
        return {
            "deleted_runs": 0,
            "deleted_checkpoints": 0,
            "deleted_objective_states": 0,
            "deleted_event_states": 0,
            "deleted_timeline_events": 0,
            "deleted_dispatch_commands": 0,
            "deleted_incidents": 0,
            "deleted_alerts": 0,
        }

    scenario_ids = [str(run_id) for run_id in run_ids]
    deleted_incidents = db.query(Incident).filter(
        Incident.exercise_run_id.in_(run_ids)
    ).delete(synchronize_session=False)
    deleted_alerts = db.query(Alert).filter(
        Alert.exercise_run_id.in_(run_ids)
    ).delete(synchronize_session=False)
    deleted_checkpoints = db.query(ExerciseCheckpoint).filter(
        ExerciseCheckpoint.run_id.in_(run_ids)
    ).delete(synchronize_session=False)
    deleted_objectives = db.query(ExerciseRunObjective).filter(
        ExerciseRunObjective.run_id.in_(run_ids)
    ).delete(synchronize_session=False)
    deleted_events = db.query(ExerciseRunEvent).filter(
        ExerciseRunEvent.run_id.in_(run_ids)
    ).delete(synchronize_session=False)
    deleted_commands = db.query(DispatchCommand).filter(
        DispatchCommand.scenario_id.in_(scenario_ids)
    ).delete(synchronize_session=False)
    deleted_timeline = db.query(ActivityLog).filter(
        ActivityLog.scenario_id.in_(scenario_ids)
    ).delete(synchronize_session=False)
    deleted_runs = db.query(ExerciseRun).filter(
        ExerciseRun.id.in_(run_ids)
    ).delete(synchronize_session=False)

    result = {
        "deleted_runs": deleted_runs,
        "deleted_checkpoints": deleted_checkpoints,
        "deleted_objective_states": deleted_objectives,
        "deleted_event_states": deleted_events,
        "deleted_timeline_events": deleted_timeline,
        "deleted_dispatch_commands": deleted_commands,
        "deleted_incidents": deleted_incidents,
        "deleted_alerts": deleted_alerts,
    }
    record_event(
        db,
        event_type="exercise_history_cleared",
        title="Exercise history cleared",
        message=f"{deleted_runs} exercise run(s) were removed.",
        source="Exercise Engine",
        metadata=result,
    )
    return result


def _run(db, run_id):
    run = db.query(ExerciseRun).filter(ExerciseRun.id == run_id).first()
    if not run:
        raise ExerciseValidationError("Exercise run was not found.", 404)
    return run


def start_run(db, run_id):
    run = _run(db, run_id)
    if run.status not in {"Ready", "Paused"}:
        raise ExerciseValidationError("Only ready or paused exercises can start.", 409)
    now = utc_now()
    run.status, run.started_at, run.paused_at = "Running", now, None
    run.current_phase = "Exercise Running"
    record_event(
        db, event_type="exercise_started", title=f"{run.exercise.name} started",
        message="The exercise clock and scripted event engine are running.",
        source="Exercise Engine", scenario_id=str(run.id),
        metadata={"exercise_id": run.exercise_id, "run_id": run.id},
    )
    process_run(db, run)
    return run


def pause_run(db, run_id, scripted=False):
    run = _run(db, run_id)
    if run.status != "Running":
        raise ExerciseValidationError("Only a running exercise can be paused.", 409)
    run.accumulated_seconds = _elapsed(run)
    run.elapsed_seconds = run.accumulated_seconds
    run.status, run.paused_at, run.started_at = "Paused", utc_now(), None
    run.current_phase = "Paused"
    record_event(
        db, event_type="exercise_paused", title="Exercise paused",
        message="The exercise clock is paused.",
        source="Exercise Engine", scenario_id=str(run.id),
        metadata={"scripted": scripted},
    )
    return run


def resume_run(db, run_id):
    run = _run(db, run_id)
    if run.status != "Paused":
        raise ExerciseValidationError("Only a paused exercise can resume.", 409)
    run.status, run.started_at, run.paused_at = "Running", utc_now(), None
    run.current_phase = "Exercise Running"
    record_event(
        db, event_type="exercise_resumed", title="Exercise resumed",
        message="The exercise clock resumed.",
        source="Exercise Engine", scenario_id=str(run.id),
    )
    return run


def cancel_run(db, run_id):
    run = _run(db, run_id)
    if run.status in {"Completed", "Failed", "Cancelled"}:
        raise ExerciseValidationError("Exercise run is already terminal.", 409)
    evaluate_objectives(db, run)
    required = [item for item in run.objectives if not item.objective.optional]
    gating = [
        item for item in run.event_states
        if item.script_event.event_type in {
            "launch_attack", "spawn_incident", "inject_alert",
            "dispatch_train", "spawn_train",
        }
    ]
    mission_started = not gating or any(item.status == "Executed" for item in gating)
    if mission_started and required and all(
        item.status == "Completed" for item in required
    ):
        return complete_run(db, run, "Completed", "All required objectives were satisfied before cancellation.")
    run.elapsed_seconds = _elapsed(run)
    run.status, run.completed_at, run.current_phase = "Cancelled", utc_now(), "Cancelled"
    run.terminal_reason = "Explicitly cancelled before required objectives were complete."
    run.final_evaluated_at = utc_now()
    record_event(
        db, event_type="exercise_cancelled", title="Exercise cancelled",
        message=f"{run.exercise.name} was cancelled before completion.",
        source="Exercise Engine", scenario_id=str(run.id),
    )
    return run


def restart_run(db, run_id):
    original = _run(db, run_id)
    return create_run(db, original.exercise_id, {
        "restarted_from_run_id": original.id
    })


def _condition_met(db, condition, run):
    if not condition:
        return True
    metric = condition.get("metric")
    value = _metric_values(db, run).get(metric)
    expected = condition.get("value")
    if value is None:
        return False
    return _compare(value, expected, condition.get("comparison", "eq"))


def _compare(value, expected, operator):
    operator = str(operator or "eq").lower()
    if operator == "gte":
        return float(value) >= float(expected)
    if operator == "lte":
        return float(value) <= float(expected)
    if operator == "gt":
        return float(value) > float(expected)
    if operator == "lt":
        return float(value) < float(expected)
    try:
        equal = float(value) == float(expected)
    except (TypeError, ValueError):
        equal = str(value).strip().casefold() == str(expected).strip().casefold()
    return not equal if operator == "ne" else equal


def process_exercise_runs(db):
    processed = []
    for run in db.query(ExerciseRun).filter(ExerciseRun.status == "Running").all():
        process_run(db, run)
        processed.append(run)
    return processed


def process_run(db, run):
    if run.status != "Running":
        return run
    run.elapsed_seconds = _elapsed(run)
    states = db.query(ExerciseRunEvent).filter(
        ExerciseRunEvent.run_id == run.id,
        ExerciseRunEvent.status == "Pending",
    ).all()
    states.sort(key=lambda item: (
        item.script_event.offset_seconds,
        item.script_event.sort_order,
        item.id,
    ))
    for state in states:
        event = state.script_event
        if event.offset_seconds > run.elapsed_seconds:
            continue
        if not _condition_met(db, _loads(event.condition_json, {}), run):
            continue
        try:
            result = _execute_event(db, run, event)
            state.status, state.executed_at = "Executed", utc_now()
            state.result_json = json.dumps(result or {}, default=str)
        except ExerciseValidationError as exc:
            state.status = "Failed"
            state.result_json = json.dumps({"error": str(exc)})
            record_event(
                db, event_type="exercise_event_failed",
                title="Scripted event failed", message=str(exc),
                severity="High", source="Exercise Engine",
                scenario_id=str(run.id), metadata={"script_event_id": event.id},
            )
    shown_hint_ids = {
        item.get("metadata", {}).get("hint_id")
        for item in get_timeline(db, 500)
        if item.get("scenario_id") == str(run.id)
    }
    for hint in run.exercise.hints:
        if (
            hint.automatic
            and hint.id not in shown_hint_ids
            and hint.available_after_seconds <= run.elapsed_seconds
            and _condition_met(db, _loads(hint.condition_json, {}), run)
        ):
            record_event(
                db, event_type="exercise_hint", title="Automatic hint",
                message=hint.message, source="Exercise Engine",
                scenario_id=str(run.id), metadata={"hint_id": hint.id},
            )
    evaluate_objectives(db, run)
    calculate_score(db, run)
    if run.status == "Running":
        required = [
            item for item in run.objectives if not item.objective.optional
        ]
        gating_types = {
            "launch_attack", "spawn_incident", "inject_alert",
            "dispatch_train", "spawn_train",
        }
        gating = [
            item for item in run.event_states
            if item.script_event.event_type in gating_types
        ]
        mission_started = not gating or any(
            item.status == "Executed" for item in gating
        )
        evaluate_run_state(db, run, mission_started=mission_started)
    return run


def _execute_event(db, run, event):
    payload = _loads(event.payload_json, {})
    kind = event.event_type
    result = {}
    if kind in {"wait", "display_message", "display_hint", "change_weather"}:
        if kind == "change_weather":
            metadata = _loads(run.metadata_json, {})
            metadata["weather"] = payload
            run.metadata_json = json.dumps(metadata)
    elif kind == "launch_attack":
        attack = Attack_Catalog.get(payload.get("attack_id"))
        if not attack:
            raise ExerciseValidationError("Scripted attack was not found.")
        query = db.query(OTDevice)
        if payload.get("target_ids"):
            query = query.filter(OTDevice.id.in_(payload["target_ids"]))
        elif payload.get("target_name"):
            query = query.filter(OTDevice.name == payload["target_name"])
        elif payload.get("device_type"):
            query = query.filter(OTDevice.device_type == payload["device_type"])
        targets = query.all()
        if not targets:
            raise ExerciseValidationError("Scripted attack has no valid targets.")
        result = {
            "simulation": apply_attack(
                db, attack, targets, exercise_run_id=run.id
            )
        }
    elif kind in {"spawn_incident", "inject_alert"}:
        device = db.query(OTDevice).filter(
            OTDevice.id == payload.get("device_id")
        ).first()
        alert = Alert(
            device_id=device.id if device else None,
            exercise_run_id=run.id,
            severity=payload.get("severity", "High"),
            alert_type=payload.get("alert_type", "Exercise Inject"),
            message=payload.get("message", "Instructor-generated exercise inject."),
        )
        db.add(alert)
        db.flush()
        incident = Incident(
            alert_id=alert.id, device_id=device.id if device else None,
            exercise_run_id=run.id,
            severity=alert.severity, device=device.name if device else "Exercise",
            alert_type=alert.alert_type, message=alert.message,
        )
        db.add(incident)
        db.flush()
        result = {"alert_id": alert.id, "incident_id": incident.id}
    elif kind == "restore_asset":
        result = perform_recovery_action(db, {
            "action_type": payload.get("action_type", "RESTORE_KNOWN_GOOD"),
            "target_id": payload.get("target_id"),
        })
    elif kind == "dispatch_train":
        result = {"command_id": create_dispatch_command(db, payload).id}
    elif kind == "spawn_train":
        train = Train(
            symbol=payload["symbol"],
            subdivision=payload.get("subdivision", "East Subdivision"),
            track=payload.get("track", "Main"),
            direction=payload.get("direction", "Eastbound"),
            milepost=float(payload.get("milepost", 80)),
            speed=int(payload.get("speed", 0)),
            status=payload.get("status", "Held by Dispatcher"),
            ptc_enabled=bool(payload.get("ptc_enabled", True)),
            current_signal="Clear",
        )
        db.add(train)
        db.flush()
        result = {"train_id": train.id}
    elif kind == "pause":
        pause_run(db, run.id, scripted=True)
    elif kind == "resume":
        if run.status == "Paused":
            resume_run(db, run.id)
    elif kind == "end_exercise":
        finish_run(
            db,
            run.id,
            confirm_cancel=False,
            timed=True,
            reason=payload.get("reason") or "Scheduled exercise end reached.",
        )
    record_event(
        db, event_type=f"exercise_{kind}",
        title=payload.get("title") or kind.replace("_", " ").title(),
        message=payload.get("message") or f"Script event {kind} executed.",
        severity=payload.get("severity", "Info"), source="Exercise Engine",
        scenario_id=str(run.id),
        metadata={"script_event_id": event.id, **result},
    )
    return result


def _metric_values(db, run):
    impact = get_operational_impact(db)
    dispatch = get_dispatch_status(db)
    devices = db.query(OTDevice).all()
    scoped_incidents = db.query(Incident).filter(
        Incident.exercise_run_id == run.id
    ).all()
    open_incidents = sum(
        str(item.status or "").strip().lower() not in TERMINAL_INCIDENT_STATUSES
        for item in scoped_incidents
    )
    unsafe_timeline_events = db.query(ActivityLog).filter(
        ActivityLog.scenario_id == str(run.id),
        ActivityLog.event_type.in_(UNSAFE_EVENT_TYPES),
    ).count()
    return {
        "track_availability": impact.get("track_availability_percent", 100),
        "train_delay_minutes": impact.get("cumulative_delay_minutes", 0),
        "dispatch_availability": dispatch.get("dispatch_availability_percent", 100),
        "unsafe_switches": impact.get("unsafe_switches", 0),
        # A prevention objective measures actions attributable to this run. An
        # unsafe asset state injected by the scenario is operational impact,
        # not a player safety violation.
        "unsafe_operation_count": unsafe_timeline_events,
        "queued_commands": dispatch.get("queued_commands", 0),
        "open_incidents": open_incidents,
        "compromised_devices": sum(
            str(item.status).lower() in {"compromised", "offline", "degraded"}
            for item in devices
        ),
        "elapsed_seconds": _elapsed(run),
    }


def evaluate_objectives(db, run):
    metrics = _metric_values(db, run)
    for state in run.objectives:
        objective = state.objective
        complete, failed, current, progress = False, False, None, 0.0
        now = utc_now()
        metadata = _loads(state.metadata_json, {})
        objective_config = _loads(objective.metadata_json, {})
        diagnostics = {
            "mode": OBJECTIVE_MODES.get(objective.objective_type, "achievement"),
            "blocking_reasons": [],
        }
        activation_event_type = objective_config.get("activate_after_event_type")
        if activation_event_type:
            activation_events = [
                item for item in run.event_states
                if item.script_event.event_type == activation_event_type
            ]
            if not any(item.status == "Executed" for item in activation_events):
                previous_status = state.status
                state.current_value = None
                state.progress = 0
                state.status = "Hidden" if objective.hidden else "Pending"
                state.last_evaluated_at = now
                if state.status != previous_status:
                    state.last_state_change_at = now
                diagnostics.update({
                    "expected_condition": (
                        f"Wait for the {activation_event_type.replace('_', ' ')} "
                        "exercise inject before evaluating this objective."
                    ),
                    "target_value": objective.target_value,
                    "current_value": None,
                    "activation_event_type": activation_event_type,
                    "completion_guidance": (
                        "Keep the exercise running and watch Timeline. This objective "
                        f"will begin after {activation_event_type.replace('_', ' ').title()}."
                    ),
                    "blocking_reasons": [{
                        "type": "exercise_phase",
                        "label": "Scripted exercise inject",
                        "status": "Waiting",
                    }],
                    "last_evaluated_at": now.isoformat(),
                })
                state.metadata_json = json.dumps(
                    {**metadata, "diagnostics": diagnostics}, default=str
                )
                continue
        if objective.objective_type in {"device_status", "communications_restored"}:
            device = db.query(OTDevice).filter(OTDevice.id == objective.target_id).first()
            current = device.status if device else "Missing"
            target = objective_config.get("status", "Online")
            complete = device is not None and str(current).lower() == str(target).lower()
            progress = 100 if complete else 25
            diagnostics["expected_condition"] = f"device_status == {target}"
            diagnostics["target_value"] = target
            diagnostics["completion_guidance"] = (
                f"Restore {device.name if device else 'the target device'} until its "
                f"Status reads {target}."
            )
            if not complete:
                diagnostics["blocking_reasons"] = [{
                    "type": "device", "id": objective.target_id,
                    "label": device.name if device else "Missing target device",
                    "status": current,
                }]
        elif objective.objective_type == "action_count":
            config = _loads(objective.metadata_json, {})
            event_types = config.get("event_types") or [config.get("event_type")]
            event_types = [item for item in event_types if item]
            current = db.query(ActivityLog).filter(
                ActivityLog.scenario_id == str(run.id),
                ActivityLog.event_type.in_(event_types or ["__none__"]),
            ).count()
            target = objective.target_value if objective.target_value is not None else 1
            complete = current >= target
            progress = min(100, current / max(target, 1) * 100)
            diagnostics["expected_condition"] = f"event_count >= {target}"
            diagnostics["target_value"] = target
        elif objective.objective_type == "event_sequence":
            config = _loads(objective.metadata_json, {})
            expected = config.get("event_types") or []
            actual = [
                item.event_type for item in db.query(ActivityLog).filter(
                    ActivityLog.scenario_id == str(run.id),
                    ActivityLog.event_type.in_(expected or ["__none__"]),
                ).order_by(ActivityLog.timestamp, ActivityLog.id).all()
            ]
            matched = 0
            for event_type in actual:
                if matched < len(expected) and event_type == expected[matched]:
                    matched += 1
            current = matched
            target = len(expected)
            complete = bool(expected) and matched == len(expected)
            progress = 100 if complete else matched / max(len(expected), 1) * 100
            diagnostics["expected_condition"] = " -> ".join(expected)
            diagnostics["target_value"] = target
        elif objective.objective_type == "sustained_metric":
            config = _loads(objective.metadata_json, {})
            metric = config.get("metric")
            if metric not in metrics:
                current, complete, progress = None, False, 0
                diagnostics["blocking_reasons"] = [{
                    "type": "configuration", "label": f"Unsupported metric {metric}",
                    "status": "Invalid",
                }]
            else:
                current = metrics[metric]
                target = config.get("value", objective.target_value or 0)
                condition_ok = _compare(
                    current, target, config.get("comparison", objective.comparison or "eq")
                )
                required_seconds = max(1, int(config.get("duration_seconds", 60)))
                started_at = metadata.get("sustain_started_at")
                if condition_ok and not started_at:
                    metadata["sustain_started_at"] = now.isoformat()
                    started_at = metadata["sustain_started_at"]
                if not condition_ok:
                    metadata.pop("sustain_started_at", None)
                    started_at = None
                sustained_seconds = max(
                    0,
                    int((now - datetime.fromisoformat(started_at)).total_seconds())
                    if started_at else 0,
                )
                complete = condition_ok and sustained_seconds >= required_seconds
                progress = min(100, sustained_seconds / required_seconds * 100)
                diagnostics["expected_condition"] = (
                    f"{metric} {config.get('comparison', objective.comparison)} {target} "
                    f"for {required_seconds}s"
                )
                diagnostics["target_value"] = required_seconds
        else:
            metric_map = {
                "track_availability_min": ("track_availability", "gte"),
                "train_delay_max": ("train_delay_minutes", "lte"),
                "dispatch_availability_min": ("dispatch_availability", "gte"),
                "no_unsafe_routing": ("unsafe_operation_count", "eq"),
                "incidents_resolved": ("open_incidents", "eq"),
                "command_queue_max": ("queued_commands", "lte"),
                "elapsed_max": ("elapsed_seconds", "lte"),
            }
            metric, default_operator = metric_map[objective.objective_type]
            current = metrics[metric]
            target = objective.target_value if objective.target_value is not None else 0
            complete = _compare(current, target, objective.comparison or default_operator)
            if objective.objective_type == "no_unsafe_routing" and float(current) > 0:
                failed = True
            if default_operator == "gte":
                progress = min(100, max(0, float(current) / max(float(target), 1) * 100))
            elif default_operator == "lte":
                progress = 100 if complete else max(0, 100 - (float(current) - float(target)) * 5)
            else:
                progress = 100 if complete else 0
            diagnostics["expected_condition"] = (
                f"{metric} {objective.comparison or default_operator} {target}"
            )
            diagnostics["target_value"] = target
            if objective.objective_type == "track_availability_min":
                diagnostics["completion_guidance"] = (
                    f"In Dispatcher Operations, keep Track available at {target:g}% or higher."
                )
            elif objective.objective_type == "no_unsafe_routing":
                diagnostics["completion_guidance"] = (
                    "Do not submit conflicting routes or switch movements on occupied "
                    "track; the unsafe-operation count must remain zero."
                )
            elif objective.objective_type == "incidents_resolved":
                diagnostics["completion_guidance"] = (
                    "After recovery is verified, close every incident created by this "
                    "exercise run in Incident Center."
                )
            if objective.objective_type == "incidents_resolved" and not complete:
                diagnostics["blocking_reasons"] = [
                    {
                        "type": "incident", "id": incident.id,
                        "label": incident.alert_type, "status": incident.status,
                    }
                    for incident in db.query(Incident).filter(
                        Incident.exercise_run_id == run.id
                    ).all()
                    if str(incident.status or "").strip().lower()
                    not in TERMINAL_INCIDENT_STATUSES
                ]
            elif objective.objective_type == "no_unsafe_routing" and not complete:
                diagnostics["blocking_reasons"] = [{
                    "type": "safety",
                    "label": "Unsafe switch or routing condition recorded",
                    "status": "Violation",
                    "count": current,
                }]
        state.current_value = current if isinstance(current, (int, float)) else None
        state.progress = round(progress, 1)
        previous_status = state.status
        if complete:
            if state.status != "Completed":
                state.completed_at = utc_now()
            state.status = "Completed"
        elif failed:
            state.status, state.failed_at = "Failed", utc_now()
        elif run.status == "Failed" and previous_status == "Failed":
            # Terminal AAR refreshes must not erase the failure decision that
            # ended the run merely because the current snapshot later changed.
            state.status = "Failed"
        else:
            state.status = "Hidden" if objective.hidden else "In Progress"
        state.last_evaluated_at = now
        if state.status != previous_status:
            state.last_state_change_at = now
        diagnostics["current_value"] = current
        diagnostics["last_evaluated_at"] = now.isoformat()
        state.metadata_json = json.dumps({**metadata, "diagnostics": diagnostics}, default=str)
    run.final_evaluated_at = utc_now()
    return run.objectives


def calculate_score(db, run):
    metrics = _metric_values(db, run)
    total_devices = max(1, db.query(OTDevice).count())
    run.cyber_score = max(
        0, 100 - metrics["open_incidents"] * 12 - metrics["compromised_devices"] / total_devices * 40
    )
    run.operations_score = max(
        0, 100 - metrics["train_delay_minutes"] * 3 - metrics["queued_commands"] * 4
    )
    run.safety_score = max(0, 100 - metrics["unsafe_operation_count"] * 30)
    run.availability_score = max(
        0, min(metrics["track_availability"], metrics["dispatch_availability"])
    )
    required = [item for item in run.objectives if not item.objective.optional]
    completed = sum(item.status == "Completed" for item in required)
    run.response_score = 100 if not required else completed / len(required) * 100
    run.score = round(
        run.cyber_score * .25 + run.operations_score * .2 +
        run.safety_score * .25 + run.availability_score * .2 +
        run.response_score * .1,
        1,
    )
    if run.walkthrough_revealed_at:
        penalty = float(_loads(run.exercise.metadata_json, {}).get(
            "walkthrough_penalty", 5
        ))
        run.score = max(0, round(run.score - penalty, 1))
    return serialize_score(run)


def evaluate_run_state(db, run, mission_started=True):
    """Apply the single idempotent run-state transition policy."""
    if run.status not in {"Running", "Paused"}:
        return run
    required = [item for item in run.objectives if not item.objective.optional]
    failed = [item for item in required if item.status == "Failed"]
    if failed:
        return complete_run(
            db, run, "Failed",
            f"Required objective failed: {failed[0].objective.description}",
        )
    if mission_started and required and all(
        item.status == "Completed" for item in required
    ):
        return complete_run(
            db, run, "Completed", "All required objectives completed."
        )
    if _elapsed(run) >= run.exercise.estimated_duration * 60:
        now = utc_now()
        for item in required:
            if item.status != "Completed":
                item.status = "Failed"
                item.failed_at = item.failed_at or now
                item.last_state_change_at = now
        return complete_run(
            db, run, "Failed", "Exercise timer expired with required objectives incomplete."
        )
    return run


def finish_run(db, run_id, confirm_cancel=False, timed=False, reason=""):
    run = _run(db, run_id)
    if run.status in {"Completed", "Failed", "Cancelled"}:
        return run
    evaluate_objectives(db, run)
    required = [item for item in run.objectives if not item.objective.optional]
    failed = [item for item in required if item.status == "Failed"]
    incomplete = [item for item in required if item.status != "Completed"]
    if failed or timed:
        return complete_run(
            db, run, "Failed",
            reason or (
                f"Required objective failed: {failed[0].objective.description}"
                if failed else "Exercise ended before required objectives completed."
            ),
        )
    if not incomplete:
        return complete_run(
            db, run, "Completed", reason or "All required objectives completed."
        )
    if not confirm_cancel:
        labels = [item.objective.description for item in incomplete]
        raise ExerciseValidationError(
            "Required objectives remain incomplete. Confirm cancellation to end the run: "
            + "; ".join(labels),
            409,
        )
    return cancel_run(db, run.id)


def request_objective_reevaluation(db, trigger="state_change"):
    """Reevaluate active runs after a committed-domain mutation, without committing."""
    runs = db.query(ExerciseRun).filter(
        ExerciseRun.status.in_(["Running", "Paused"])
    ).all()
    for run in runs:
        evaluate_objectives(db, run)
        calculate_score(db, run)
        if run.status == "Running":
            gating = [
                item for item in run.event_states
                if item.script_event.event_type in {
                    "launch_attack", "spawn_incident", "inject_alert",
                    "dispatch_train", "spawn_train",
                }
            ]
            mission_started = not gating or any(
                item.status == "Executed" for item in gating
            )
            evaluate_run_state(db, run, mission_started=mission_started)
    return runs


def complete_run(db, run, status="Completed", reason=""):
    if run.status in {"Completed", "Failed", "Cancelled"}:
        return run
    if status not in {"Completed", "Failed"}:
        status = "Completed"
    run.elapsed_seconds = _elapsed(run)
    run.status, run.completed_at, run.current_phase = status, utc_now(), "After Action"
    run.terminal_reason = reason or (
        "All required objectives completed."
        if status == "Completed"
        else "A configured exercise failure condition occurred."
    )
    run.final_evaluated_at = utc_now()
    calculate_score(db, run)
    record_event(
        db, event_type=f"exercise_{status.lower()}",
        title=f"Exercise {status.lower()}",
        message=(
            f"{run.exercise.name} ended with a score of {run.score:.1f}. "
            f"{run.terminal_reason}"
        ),
        severity="Info" if status == "Completed" else "High",
        source="Exercise Engine", scenario_id=str(run.id),
        metadata={**serialize_score(run), "reason": run.terminal_reason},
    )
    return run


def save_checkpoint(db, run_id, name="Checkpoint"):
    run = _run(db, run_id)
    state = {
        "devices": [_row(item, ["id", "status", "risk_level", "firmware_version"])
                    for item in db.query(OTDevice).all()],
        "trains": [_row(item, ["id", "milepost", "speed", "status", "current_signal", "ptc_enabled"])
                   for item in db.query(Train).all()],
        "blocks": [_row(item, ["id", "occupied", "occupied_train_id", "signal_aspect",
                               "speed_limit", "communications_status", "security_status", "maintenance"])
                   for item in db.query(TrackBlock).all()],
        "switches": [_row(item, ["id", "position", "commanded_position", "locked",
                                 "communications_status", "security_status"])
                     for item in db.query(TrackSwitch).all()],
        "crossings": [_row(item, ["id", "gate_state", "lights_active",
                                  "communications_status", "security_status"])
                      for item in db.query(GradeCrossing).all()],
        "incidents": [_row(item, ["id", "status", "acknowledged", "assigned_to",
                                  "investigation_notes"])
                      for item in db.query(Incident).all()],
        "dispatch_commands": [_row(item, [
            "id", "status", "delay_seconds", "failure_reason",
        ]) for item in db.query(DispatchCommand).all()],
        "dispatch_routes": [_row(item, ["id", "status", "blocking_reason"])
                            for item in db.query(DispatchRoute).all()],
        "restrictions": [_row(item, ["id", "active", "cleared_by"])
                         for item in db.query(OperationalRestriction).all()],
        "objectives": [_row(item, ["id", "status", "progress", "current_value"])
                       for item in run.objectives],
        "score": serialize_score(run),
        "timeline": [
            item for item in get_timeline(db, 500)
            if item.get("scenario_id") == str(run.id)
        ],
        "run": {
            "status": run.status, "elapsed_seconds": _elapsed(run),
            "current_phase": run.current_phase,
        },
    }
    checkpoint = ExerciseCheckpoint(
        run_id=run.id, name=name, elapsed_seconds=_elapsed(run),
        state_json=json.dumps(state, default=str),
    )
    db.add(checkpoint)
    db.flush()
    record_event(
        db, event_type="exercise_checkpoint_saved", title="Checkpoint saved",
        message=f"{name} saved at {checkpoint.elapsed_seconds} seconds.",
        source="Exercise Engine", scenario_id=str(run.id),
    )
    return checkpoint


def _row(item, fields):
    return {field: getattr(item, field) for field in fields}


def restore_checkpoint(db, run_id, checkpoint_id):
    run = _run(db, run_id)
    checkpoint = db.query(ExerciseCheckpoint).filter(
        ExerciseCheckpoint.id == checkpoint_id,
        ExerciseCheckpoint.run_id == run.id,
    ).first()
    if not checkpoint:
        raise ExerciseValidationError("Checkpoint was not found.", 404)
    state = _loads(checkpoint.state_json, {})
    collections = [
        ("devices", OTDevice), ("trains", Train), ("blocks", TrackBlock),
        ("switches", TrackSwitch), ("crossings", GradeCrossing),
        ("incidents", Incident), ("objectives", ExerciseRunObjective),
        ("dispatch_commands", DispatchCommand),
        ("dispatch_routes", DispatchRoute),
        ("restrictions", OperationalRestriction),
    ]
    for key, model in collections:
        for saved in state.get(key, []):
            row = db.query(model).filter(model.id == saved["id"]).first()
            if row:
                for field, value in saved.items():
                    if field != "id":
                        setattr(row, field, value)
    score = state.get("score", {})
    for field in [
        "score", "cyber_score", "operations_score", "safety_score",
        "availability_score", "response_score",
    ]:
        if field in score:
            setattr(run, field, score[field])
    run.accumulated_seconds = checkpoint.elapsed_seconds
    run.elapsed_seconds = checkpoint.elapsed_seconds
    run.started_at = utc_now() if run.status == "Running" else None
    run.current_phase = state.get("run", {}).get("current_phase", "Exercise Running")
    record_event(
        db, event_type="exercise_checkpoint_restored",
        title="Checkpoint restored", message=f"{checkpoint.name} was restored.",
        source="Exercise Engine", scenario_id=str(run.id),
    )
    return run


def request_hint(db, run_id):
    run = _run(db, run_id)
    elapsed = _elapsed(run)
    shown = {
        event.get("metadata", {}).get("hint_id")
        for event in get_timeline(db, 500)
        if event.get("scenario_id") == str(run.id)
    }
    hint = next(
        (item for item in run.exercise.hints
         if item.available_after_seconds <= elapsed and item.id not in shown),
        None,
    )
    if not hint:
        raise ExerciseValidationError("No additional hint is currently available.", 409)
    record_event(
        db, event_type="exercise_hint", title="Exercise hint",
        message=hint.message, source="Exercise Engine",
        scenario_id=str(run.id), metadata={"hint_id": hint.id},
    )
    return {"id": hint.id, "message": hint.message}


def reveal_walkthrough(db, run_id):
    run = _run(db, run_id)
    if not run.exercise.walkthrough:
        raise ExerciseValidationError("No walkthrough is provided for this exercise.", 404)
    if run.walkthrough_revealed_at is None:
        run.walkthrough_revealed_at = utc_now()
        record_event(
            db,
            event_type="exercise_walkthrough_revealed",
            title="Answer sheet revealed",
            message="The player revealed the exercise walkthrough.",
            source="Exercise Engine",
            scenario_id=str(run.id),
            metadata={"score_penalty": _loads(run.exercise.metadata_json, {}).get(
                "walkthrough_penalty", 5
            )},
        )
        calculate_score(db, run)
    return serialize_walkthrough(run.exercise.walkthrough, run=run, instructor=False)


def serialize_walkthrough(walkthrough, run=None, instructor=False):
    if not walkthrough:
        return None
    state_by_objective = {
        item.objective_id: item for item in (run.objectives if run else [])
    }
    steps = []
    for step in walkthrough.steps:
        if not instructor and not step.player_visible:
            continue
        if not instructor and step.linked_objective and step.linked_objective.hidden:
            continue
        state = state_by_objective.get(step.linked_objective_id)
        verification_status = "Not Started"
        blockers = []
        if state:
            diagnostics = _loads(state.metadata_json, {}).get("diagnostics", {})
            blockers = diagnostics.get("blocking_reasons", [])
            verification_status = {
                "Completed": "Completed",
                "Failed": "Failed",
                "In Progress": "Blocked" if blockers else "Ready",
                "Hidden": "Not Started",
                "Pending": "Ready",
            }.get(state.status, "Not Started")
        payload = {
            "id": step.id,
            "step_number": step.step_number,
            "title": step.title,
            "purpose": step.purpose,
            "player_action": step.player_action,
            "navigation_location": step.navigation_location,
            "target_asset": step.target_asset,
            "expected_result": step.expected_result,
            "verification_condition": step.verification_condition,
            "linked_objective_id": step.linked_objective_id,
            "action_id": step.action_id,
            "hint": step.hint,
            "common_mistakes": _loads(step.common_mistakes_json, []),
            "recovery_path": step.recovery_path,
            "player_visible": step.player_visible,
            "verification_status": verification_status,
            "blocking_reasons": blockers,
        }
        if instructor:
            payload["instructor_notes"] = step.instructor_notes
        steps.append(payload)
    result = {
        "id": walkthrough.id,
        "exercise_id": walkthrough.exercise_id,
        "overview": walkthrough.overview,
        "prerequisites": _loads(walkthrough.prerequisites_json, []),
        "troubleshooting": _loads(walkthrough.troubleshooting_json, []),
        "expected_end_state": _loads(walkthrough.expected_end_state_json, []),
        "version": walkthrough.version,
        "steps": steps,
        "revealed": bool(run and run.walkthrough_revealed_at),
    }
    if instructor:
        result["instructor_notes"] = walkthrough.instructor_notes
    return result


def validate_exercise_configuration(db, exercise):
    errors, warnings = [], []
    objective_ids = [item.id for item in exercise.objectives]
    duplicates = {item for item in objective_ids if objective_ids.count(item) > 1}
    if duplicates:
        errors.append(f"Duplicate objective IDs: {sorted(duplicates)}")
    steps = list(exercise.walkthrough.steps) if exercise.walkthrough else []
    covered = {step.linked_objective_id for step in steps if step.linked_objective_id}
    configured_event_types = {
        event.event_type for event in exercise.script_events
    }
    for objective in exercise.objectives:
        objective_metadata = _loads(objective.metadata_json, {})
        if objective.objective_type not in OBJECTIVE_TYPES:
            errors.append(
                f"Objective {objective.id} uses unsupported evaluator {objective.objective_type}."
            )
        if objective.target_type == "OT_DEVICE" and objective.target_id and not db.get(OTDevice, objective.target_id):
            errors.append(f"Objective {objective.id} references missing device {objective.target_id}.")
        if objective.comparison not in COMPARISON_OPERATORS:
            errors.append(
                f"Objective {objective.id} uses unsupported comparison {objective.comparison}."
            )
        if objective.objective_type in {"device_status", "communications_restored"}:
            status = str(objective_metadata.get("status", "Online"))
            if status.strip().lower() not in SUPPORTED_DEVICE_STATUSES:
                errors.append(
                    f"Objective {objective.id} uses unsupported device status '{status}'."
                )
        visible_coverage = any(
            step.linked_objective_id == objective.id and step.player_visible
            for step in steps
        )
        if not objective.optional and not visible_coverage:
            errors.append(f"Required objective {objective.id} has no walkthrough coverage.")
        if objective.objective_type == "incidents_resolved":
            if objective_metadata.get("scope", "exercise_run") != "exercise_run":
                warnings.append(
                    f"Objective {objective.id} should use exercise_run incident scope."
                )
        activation_event_type = objective_metadata.get("activate_after_event_type")
        if activation_event_type and activation_event_type not in configured_event_types:
            errors.append(
                f"Objective {objective.id} waits for missing script event "
                f"{activation_event_type}."
            )
    for event in exercise.script_events:
        if event.event_type not in EVENT_TYPES:
            errors.append(f"Script event {event.id} has unsupported handler {event.event_type}.")
        payload = _loads(event.payload_json, {})
        if event.event_type == "launch_attack" and payload.get("attack_id") not in Attack_Catalog:
            errors.append(f"Script event {event.id} references an unknown attack.")
    for step in steps:
        if step.action_id and step.action_id not in WALKTHROUGH_ACTIONS:
            errors.append(f"Walkthrough step {step.step_number} references unsupported action {step.action_id}.")
        if step.target_asset and not db.query(OTDevice).filter(OTDevice.name == step.target_asset).first():
            warnings.append(
                f"Walkthrough target '{step.target_asset}' is dynamically described or not an OTDevice."
            )
        if (
            step.verification_condition
            and step.verification_condition.strip().lower()
            not in WALKTHROUGH_VERIFICATIONS
        ):
            errors.append(
                f"Walkthrough step {step.step_number} has unsupported verification "
                f"condition '{step.verification_condition}'."
            )
    required = [item for item in exercise.objectives if not item.optional]
    return {
        "exercise_id": exercise.id,
        "exercise_name": exercise.name,
        "validation_type": "configuration_and_reachability",
        "errors": errors,
        "warnings": warnings,
        "objective_coverage": {
            "required": len(required),
            "covered": sum(item.id in covered for item in required),
        },
        "walkthrough_coverage": len(steps),
        "evaluator_coverage": sum(
            item.objective_type in OBJECTIVE_TYPES for item in exercise.objectives
        ),
        "completion_readiness": not errors,
    }


def after_action_report(db, run):
    if run.status == "Running":
        process_run(db, run)
    else:
        evaluate_objectives(db, run)
        calculate_score(db, run)
    impact = get_operational_impact(db)
    events = [
        item for item in get_timeline(db, 500)
        if item.get("scenario_id") == str(run.id)
    ]
    objectives = [serialize_run_objective(item) for item in run.objectives]
    unresolved_incidents = [
        {
            "id": item.id, "alert_type": item.alert_type,
            "device": item.device, "status": item.status,
        }
        for item in db.query(Incident).filter(
            Incident.exercise_run_id == run.id
        ).all()
        if str(item.status or "").strip().lower() not in TERMINAL_INCIDENT_STATUSES
    ]
    hint_events = [
        item for item in events
        if item["event_type"] in {"exercise_hint", "exercise_walkthrough_revealed"}
    ]
    first_cyber = next(
        (item for item in reversed(events)
         if "attack" in item["event_type"] or "alert" in item["event_type"]),
        None,
    )
    first_recovery = next(
        (item for item in reversed(events)
         if "recovery" in item["event_type"] or "restore" in item["event_type"]),
        None,
    )
    response_seconds = None
    if first_cyber and first_recovery:
        from datetime import datetime
        response_seconds = max(
            0,
            int((
                datetime.fromisoformat(first_recovery["timestamp"])
                - datetime.fromisoformat(first_cyber["timestamp"])
            ).total_seconds()),
        )
    report = {
        "run_id": run.id,
        "exercise": run.exercise.name,
        "mission_summary": (
            f"{run.exercise.name} finished with status {run.status} "
            f"and an overall score of {run.score:.1f}."
        ),
        "status": run.status,
        "completion_reason": run.terminal_reason if run.status == "Completed" else "",
        "failure_reason": run.terminal_reason if run.status == "Failed" else "",
        "cancellation_reason": run.terminal_reason if run.status == "Cancelled" else "",
        "final_evaluated_at": (
            run.final_evaluated_at.isoformat() if run.final_evaluated_at else None
        ),
        "elapsed_seconds": run.elapsed_seconds,
        "response_time_seconds": response_seconds,
        "scores": serialize_score(run),
        "objectives": objectives,
        "unresolved_incidents": unresolved_incidents,
        "safety_violations": _metric_values(db, run)["unsafe_operation_count"],
        "walkthrough_revealed": run.walkthrough_revealed_at is not None,
        "hint_usage": hint_events,
        "timeline": events,
        "cyber_events": [item for item in events if "attack" in item["event_type"] or "alert" in item["event_type"]],
        "operational_events": [item for item in events if any(word in item["event_type"] for word in ["train", "dispatch", "route", "signal"])],
        "recovery_actions": [item for item in events if "recovery" in item["event_type"] or "restore" in item["event_type"]],
        "operational_impact": impact,
        "lessons_learned": _lessons(run, objectives, impact),
        "recommendations": _recommendations(run, impact),
        "generated_at": utc_now().isoformat(),
    }
    report["markdown"] = report_markdown(report)
    return report


def _lessons(run, objectives, impact):
    lessons = []
    if any(item["status"] == "Failed" for item in objectives):
        lessons.append("Review failed objectives and the timeline around their first degraded state.")
    if impact.get("cumulative_delay_minutes", 0) > 0:
        lessons.append("Cyber containment decisions had measurable train-delay consequences.")
    if run.safety_score == 100:
        lessons.append("The team maintained modeled railroad safety constraints.")
    return lessons or ["The team maintained the modeled operating baseline."]


def _recommendations(run, impact):
    recommendations = []
    if run.cyber_score < 80:
        recommendations.append("Practice faster asset isolation and incident closure.")
    if run.operations_score < 80:
        recommendations.append("Coordinate recovery actions with dispatcher workload and train delay.")
    if impact.get("dispatch_availability_percent", 100) < 100:
        recommendations.append("Exercise transfer-to-backup dispatch procedures.")
    return recommendations or ["Repeat at a higher difficulty with fewer automatic hints."]


def report_markdown(report):
    objective_lines = "\n".join(
        f"- [{ 'x' if item['status'] == 'Completed' else ' ' }] "
        f"{item['description']} — {item['status']} ({item['progress']:.0f}%)"
        for item in report["objectives"]
    )
    return (
        f"# After-Action Report: {report['exercise']}\n\n"
        f"## Mission Summary\n\n{report['mission_summary']}\n\n"
        f"- Final reason: {report.get('completion_reason') or report.get('failure_reason') or report.get('cancellation_reason') or 'Not recorded'}\n"
        f"- Final evaluation: {report.get('final_evaluated_at') or 'Not recorded'}\n\n"
        f"## Objectives\n\n{objective_lines or '- No objectives defined.'}\n\n"
        f"## Operational Impact\n\n"
        f"- Track availability: {report['operational_impact'].get('track_availability_percent', 100)}%\n"
        f"- Train delay: {report['operational_impact'].get('cumulative_delay_minutes', 0)} minutes\n"
        f"- Dispatch availability: {report['operational_impact'].get('dispatch_availability_percent', 100)}%\n\n"
        f"## Lessons Learned\n\n" +
        "\n".join(f"- {item}" for item in report["lessons_learned"]) +
        "\n\n## Recommendations\n\n" +
        "\n".join(f"- {item}" for item in report["recommendations"])
    )


def simple_pdf(markdown):
    lines = markdown.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)").splitlines()
    commands = ["BT /F1 10 Tf 45 760 Td"]
    for index, line in enumerate(lines[:58]):
        if index:
            commands.append("0 -12 Td")
        commands.append(f"({line[:110]}) Tj")
    commands.append("ET")
    stream = "\n".join(commands).encode("latin-1", "replace")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>",
        b"<< /Length %d >>\nstream\n" % len(stream) + stream + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    output = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for index, obj in enumerate(objects, 1):
        offsets.append(len(output))
        output.extend(f"{index} 0 obj\n".encode() + obj + b"\nendobj\n")
    xref = len(output)
    output.extend(f"xref\n0 {len(objects)+1}\n0000000000 65535 f \n".encode())
    for offset in offsets[1:]:
        output.extend(f"{offset:010d} 00000 n \n".encode())
    output.extend(
        f"trailer << /Size {len(objects)+1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF".encode()
    )
    return bytes(output)


def serialize_exercise(exercise, include_definition=False, instructor=False):
    payload = {
        "id": exercise.id, "name": exercise.name,
        "description": exercise.description, "category": exercise.category,
        "difficulty": exercise.difficulty,
        "estimated_duration": exercise.estimated_duration,
        "recommended_players": exercise.recommended_players,
        "enabled": exercise.enabled, "favorite": exercise.favorite,
        "known_intelligence": exercise.known_intelligence,
        "success_criteria": exercise.success_criteria,
        "failure_conditions": exercise.failure_conditions,
        "metadata": _loads(exercise.metadata_json, {}),
        "created_at": exercise.created_at.isoformat() if exercise.created_at else None,
        "updated_at": exercise.updated_at.isoformat() if exercise.updated_at else None,
    }
    if include_definition:
        payload["objectives"] = [
            serialize_objective(item) for item in exercise.objectives
            if instructor or not item.hidden
        ]
        payload["script_events"] = [{
            "id": item.id, "event_type": item.event_type,
            "offset_seconds": item.offset_seconds,
            "condition": _loads(item.condition_json, {}),
            "payload": _loads(item.payload_json, {}),
            "one_time": item.one_time,
        } for item in exercise.script_events]
        payload["hints"] = [{
            "id": item.id, "message": item.message,
            "available_after_seconds": item.available_after_seconds,
            "automatic": item.automatic,
            "condition": _loads(item.condition_json, {}),
        } for item in exercise.hints]
        payload["walkthrough_available"] = exercise.walkthrough is not None
        if instructor and exercise.walkthrough:
            payload["walkthrough"] = _walkthrough_definition_data(exercise)
    return payload


def serialize_objective(item):
    return {
        "id": item.id, "description": item.description,
        "objective_type": item.objective_type,
        "target_type": item.target_type, "target_id": item.target_id,
        "target_value": item.target_value, "comparison": item.comparison,
        "optional": item.optional, "hidden": item.hidden,
        "weight": item.weight, "metadata": _loads(item.metadata_json, {}),
    }


def serialize_run_objective(item):
    metadata = _loads(item.metadata_json, {})
    diagnostics = metadata.get("diagnostics", {})
    return {
        **serialize_objective(item.objective),
        "run_objective_id": item.id, "status": item.status,
        "progress": item.progress, "progress_percent": item.progress,
        "current_value": item.current_value,
        "completed_at": item.completed_at.isoformat() if item.completed_at else None,
        "failed_at": item.failed_at.isoformat() if item.failed_at else None,
        "mode": diagnostics.get(
            "mode", OBJECTIVE_MODES.get(item.objective.objective_type, "achievement")
        ),
        "target_value_display": diagnostics.get("target_value"),
        "expected_condition": diagnostics.get("expected_condition", ""),
        "completion_guidance": diagnostics.get("completion_guidance", ""),
        "blocking_reasons": diagnostics.get("blocking_reasons", []),
        "last_evaluated_at": (
            item.last_evaluated_at.isoformat() if item.last_evaluated_at else None
        ),
        "last_state_change_at": (
            item.last_state_change_at.isoformat() if item.last_state_change_at else None
        ),
        "is_required": not item.objective.optional,
    }


def serialize_score(run):
    return {
        "score": round(run.score or 0, 1),
        "cyber_score": round(run.cyber_score or 0, 1),
        "operations_score": round(run.operations_score or 0, 1),
        "safety_score": round(run.safety_score or 0, 1),
        "availability_score": round(run.availability_score or 0, 1),
        "response_score": round(run.response_score or 0, 1),
    }


def serialize_checkpoint(item):
    return {
        "id": item.id, "name": item.name,
        "created_at": item.created_at.isoformat() if item.created_at else None,
        "elapsed_seconds": item.elapsed_seconds,
    }


def serialize_run(db, run, detail=True, instructor=False):
    if run.status == "Running":
        process_run(db, run)
    payload = {
        "id": run.id, "exercise_id": run.exercise_id,
        "exercise_name": run.exercise.name, "status": run.status,
        "created_at": run.created_at.isoformat() if run.created_at else None,
        "started_at": run.started_at.isoformat() if run.started_at else None,
        "completed_at": run.completed_at.isoformat() if run.completed_at else None,
        "terminal_reason": run.terminal_reason or "",
        "final_evaluated_at": (
            run.final_evaluated_at.isoformat() if run.final_evaluated_at else None
        ),
        "walkthrough_revealed": run.walkthrough_revealed_at is not None,
        "elapsed_seconds": _elapsed(run),
        "current_phase": run.current_phase,
        "metadata": _loads(run.metadata_json, {}),
        **serialize_score(run),
    }
    if detail:
        briefing_impact = get_operational_impact(db)
        briefing_impact["summary"] = build_operational_summary(briefing_impact)
        payload["objectives"] = [
            serialize_run_objective(item) for item in run.objectives
            if instructor or not item.objective.hidden
        ]
        payload["checkpoints"] = [serialize_checkpoint(item) for item in run.checkpoints]
        payload["timeline"] = [
            item for item in get_timeline(db, 150)
            if item.get("scenario_id") == str(run.id)
        ]
        elapsed = _elapsed(run)
        payload["hints"] = [{
            "id": item.id, "message": item.message,
            "available": item.available_after_seconds <= elapsed,
            "automatic": item.automatic,
        } for item in run.exercise.hints]
        briefing = serialize_exercise(
            run.exercise, include_definition=True, instructor=instructor
        )
        payload["briefing"] = {
            **briefing,
            "current_railroad_status": briefing_impact,
        }
        payload["walkthrough_available"] = run.exercise.walkthrough is not None
        if instructor or run.walkthrough_revealed_at:
            payload["walkthrough"] = serialize_walkthrough(
                run.exercise.walkthrough, run=run, instructor=instructor
            )
    return payload
