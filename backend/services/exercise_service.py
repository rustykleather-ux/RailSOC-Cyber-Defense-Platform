import json
from datetime import timezone

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
    merged = {**serialize_exercise(exercise, include_definition=True), **data}
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
    if any(key in data for key in ["objectives", "script_events", "hints"]):
        _replace_children(db, exercise, merged)
    exercise.updated_at = utc_now()
    db.flush()
    return exercise


def _replace_children(db, exercise, data):
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
    db.flush()


def clone_exercise(db, exercise, name=None):
    data = serialize_exercise(exercise, include_definition=True)
    data["name"] = name or f"{exercise.name} Copy"
    data.pop("id", None)
    return create_exercise(db, data)


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
    run.elapsed_seconds = _elapsed(run)
    run.status, run.completed_at, run.current_phase = "Cancelled", utc_now(), "Cancelled"
    record_event(
        db, event_type="exercise_cancelled", title="Exercise cancelled",
        message=f"{run.exercise.name} was cancelled.",
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
    if operator == "gte":
        return float(value) >= float(expected)
    if operator == "lte":
        return float(value) <= float(expected)
    if operator == "gt":
        return float(value) > float(expected)
    if operator == "lt":
        return float(value) < float(expected)
    if operator == "ne":
        return value != expected
    return str(value).lower() == str(expected).lower()


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
        if (
            mission_started
            and required
            and all(item.status == "Completed" for item in required)
        ):
            complete_run(db, run, "Completed")
        elif run.elapsed_seconds >= run.exercise.estimated_duration * 60:
            for item in required:
                if item.status != "Completed":
                    item.status, item.failed_at = "Failed", utc_now()
            complete_run(db, run, "Failed")
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
        result = {"simulation": apply_attack(db, attack, targets)}
    elif kind in {"spawn_incident", "inject_alert"}:
        device = db.query(OTDevice).filter(
            OTDevice.id == payload.get("device_id")
        ).first()
        alert = Alert(
            device_id=device.id if device else None,
            severity=payload.get("severity", "High"),
            alert_type=payload.get("alert_type", "Exercise Inject"),
            message=payload.get("message", "Instructor-generated exercise inject."),
        )
        db.add(alert)
        db.flush()
        incident = Incident(
            alert_id=alert.id, device_id=device.id if device else None,
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
        complete_run(db, run, payload.get("status", "Completed"))
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
    open_incidents = db.query(Incident).filter(Incident.status != "Closed").count()
    return {
        "track_availability": impact.get("track_availability_percent", 100),
        "train_delay_minutes": impact.get("cumulative_delay_minutes", 0),
        "dispatch_availability": dispatch.get("dispatch_availability_percent", 100),
        "unsafe_switches": impact.get("unsafe_switches", 0),
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
        if objective.objective_type in {"device_status", "communications_restored"}:
            device = db.query(OTDevice).filter(OTDevice.id == objective.target_id).first()
            current = device.status if device else "Missing"
            target = _loads(objective.metadata_json, {}).get("status", "Online")
            complete = device is not None and str(current).lower() == str(target).lower()
            progress = 100 if complete else 25
        else:
            metric_map = {
                "track_availability_min": ("track_availability", "gte"),
                "train_delay_max": ("train_delay_minutes", "lte"),
                "dispatch_availability_min": ("dispatch_availability", "gte"),
                "no_unsafe_routing": ("unsafe_switches", "eq"),
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
        state.current_value = current if isinstance(current, (int, float)) else None
        state.progress = round(progress, 1)
        if complete:
            if state.status != "Completed":
                state.completed_at = utc_now()
            state.status = "Completed"
        elif failed:
            state.status, state.failed_at = "Failed", utc_now()
        else:
            state.status = "Hidden" if objective.hidden else "In Progress"
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
    run.safety_score = max(0, 100 - metrics["unsafe_switches"] * 30)
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
    return serialize_score(run)


def complete_run(db, run, status="Completed"):
    if status not in {"Completed", "Failed"}:
        status = "Completed"
    run.elapsed_seconds = _elapsed(run)
    run.status, run.completed_at, run.current_phase = status, utc_now(), "After Action"
    calculate_score(db, run)
    record_event(
        db, event_type=f"exercise_{status.lower()}",
        title=f"Exercise {status.lower()}",
        message=f"{run.exercise.name} ended with a score of {run.score:.1f}.",
        severity="Info" if status == "Completed" else "High",
        source="Exercise Engine", scenario_id=str(run.id),
        metadata=serialize_score(run),
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


def after_action_report(db, run):
    process_run(db, run)
    impact = get_operational_impact(db)
    events = [
        item for item in get_timeline(db, 500)
        if item.get("scenario_id") == str(run.id)
    ]
    objectives = [serialize_run_objective(item) for item in run.objectives]
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
        "elapsed_seconds": run.elapsed_seconds,
        "response_time_seconds": response_seconds,
        "scores": serialize_score(run),
        "objectives": objectives,
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


def serialize_exercise(exercise, include_definition=False):
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
        payload["objectives"] = [serialize_objective(item) for item in exercise.objectives]
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
    return {
        **serialize_objective(item.objective),
        "run_objective_id": item.id, "status": item.status,
        "progress": item.progress, "current_value": item.current_value,
        "completed_at": item.completed_at.isoformat() if item.completed_at else None,
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


def serialize_run(db, run, detail=True):
    if run.status == "Running":
        process_run(db, run)
    payload = {
        "id": run.id, "exercise_id": run.exercise_id,
        "exercise_name": run.exercise.name, "status": run.status,
        "created_at": run.created_at.isoformat() if run.created_at else None,
        "started_at": run.started_at.isoformat() if run.started_at else None,
        "completed_at": run.completed_at.isoformat() if run.completed_at else None,
        "elapsed_seconds": _elapsed(run),
        "current_phase": run.current_phase,
        "metadata": _loads(run.metadata_json, {}),
        **serialize_score(run),
    }
    if detail:
        briefing_impact = get_operational_impact(db)
        briefing_impact["summary"] = build_operational_summary(briefing_impact)
        payload["objectives"] = [serialize_run_objective(item) for item in run.objectives]
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
        payload["briefing"] = {
            **serialize_exercise(run.exercise, include_definition=True),
            "current_railroad_status": briefing_impact,
        }
    return payload
