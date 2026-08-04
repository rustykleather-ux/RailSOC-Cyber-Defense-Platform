import asyncio
import json
import os
import random
from datetime import datetime, timezone
from typing import Optional, Any, Dict, List
from urllib import request

from fastapi import FastAPI, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.responses import Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from ai_assistant import build_operations_brief
from ai_assistant import analyze_single_incident
from services.alert_service import create_alert

from scenario_manager import scenario_manager
from simulation_engine import apply_attack
from attack_catalog import Attack_Catalog   
from attack_manager import launch_attack, get_active_attacks 
from database import Base, engine, SessionLocal, ensure_sqlite_schema
import models
from models import (
    OTDevice,
    Alert,
    Vulnerability,
    Train,
    TrainHistory,
    Incident,
    TrackBlock,
    TrackSwitch,
    GradeCrossing,
    DispatchCommand,
    DispatchRoute,
    OperationalRestriction,
    RouteTopologySegment,
    Exercise,
    ExerciseRun,
    ExerciseCheckpoint,
    DeviceRelationship,
    OTDeviceType,
    NetworkConnection,
    NetworkNode,
    NetworkPath,
    NetworkTrafficEvent,
    NetworkZone,
    
)
from services.risk_engine import calculate_device_risk
from services.digital_twin_service import (
    DigitalTwinConflictError,
    apply_effect,
    apply_digital_twin_effect,
    apply_signal_controller_effect,
)
from services.device_framework import (
    CAPABILITY_EFFECTS,
    EFFECT_LABELS,
    create_device,
    dumps_json,
    initialize_device_framework,
    loads_json,
    relationship_target_exists,
    serialize_device,
    serialize_device_type,
    serialize_relationship,
    supported_effects_for_device,
)
from services.operational_impact import (
    build_operational_summary,
    get_operational_impact,
)
from services.timeline_service import get_timeline, record_event
from services.map_service import get_map_snapshot
from seed_track_blocks import assign_signal_controller_track_blocks
from seed_operational_assets import seed_operational_assets
from seed_route_topology import seed_route_topology
from seed_exercises import seed_exercises
from seed_network_visibility import seed_network_visibility
from services.network_visibility_service import (
    NetworkValidationError,
    apply_connection_action,
    apply_node_action,
    get_connection as get_network_connection,
    get_node as get_network_node,
    get_topology as get_network_topology,
    list_events as list_network_events,
    restore_baseline as restore_network_baseline,
    run_simulation as run_network_simulation,
    save_layout as save_network_layout,
    serialize_connection as serialize_network_connection,
    serialize_node as serialize_network_node,
    serialize_zone as serialize_network_zone,
    trace_path as trace_network_path,
    websocket_payload as network_websocket_payload,
)
from services.exercise_service import (
    ExerciseValidationError,
    after_action_report,
    cancel_run,
    clone_exercise,
    clear_exercise_history,
    create_exercise,
    create_run,
    pause_run,
    process_exercise_runs,
    finish_run,
    request_objective_reevaluation,
    request_hint,
    reveal_walkthrough,
    restart_run,
    restore_checkpoint,
    resume_run,
    save_checkpoint,
    serialize_checkpoint,
    serialize_exercise,
    serialize_run,
    serialize_score,
    serialize_walkthrough,
    simple_pdf,
    start_run,
    update_exercise,
    validate_exercise_configuration,
)
from services.dispatch_service import (
    DispatchValidationError,
    cancel_command,
    clear_restriction,
    create_dispatch_command as create_dispatch_command_service,
    create_restriction,
    create_route,
    get_dispatch_status as build_dispatch_status,
    get_dispatch_device,
    perform_recovery_action,
    process_dispatch_commands,
    queue_dispatch_command,
    retry_command,
    serialize_command,
    serialize_restriction,
    serialize_route,
    serialize_topology_segment,
)
from train_simulation import train_simulation


class ScenarioCreateRequest(BaseModel):
    attack_id: str
    target_ids: List[int] = Field(min_length=1)
    notes: Optional[str] = None
    created_by: Optional[str] = None


class ScenarioProgressRequest(BaseModel):
    progress: int = Field(ge=0, le=100)
    current_step: Optional[str] = None


class ScenarioTimelineEventRequest(BaseModel):
    event_type: str
    title: str
    message: str
    severity: str = "Info"
    progress: Optional[int] = Field(default=None, ge=0, le=100)
    metadata: Optional[Dict[str, Any]] = None


class DispatchCommandRequest(BaseModel):
    command_type: str
    target_type: Optional[str] = None
    target_id: Optional[int] = None
    requested_state: Optional[str] = None
    requested_by: str = "Dispatcher"
    priority: str = "Normal"
    payload: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None
    incident_id: Optional[int] = None
    scenario_id: Optional[str] = None


class DispatchStatusRequest(BaseModel):
    status: str


class DispatchRouteRequest(BaseModel):
    train_id: int
    start_block_id: int
    destination_block_id: int
    requested_path: Optional[List[int]] = None
    requested_by: str = "Dispatcher"


class DispatchRestrictionRequest(BaseModel):
    restriction_type: str
    target_type: str
    target_id: int
    reason: str = Field(min_length=1)
    severity: str = "Medium"
    created_by: str = "Dispatcher"
    incident_id: Optional[int] = None
    metadata: Optional[Dict[str, Any]] = None


class DispatchActorRequest(BaseModel):
    requested_by: str = "Dispatcher"


class RecoveryActionRequest(BaseModel):
    action_type: str
    target_id: int
    requested_by: str = "Dispatcher"
    incident_id: Optional[int] = None
    metadata: Optional[Dict[str, Any]] = None


class ExerciseDefinitionRequest(BaseModel):
    name: str = Field(min_length=1)
    description: str = ""
    category: str = "Custom"
    difficulty: str = "Medium"
    estimated_duration: int = Field(default=20, ge=1, le=480)
    recommended_players: int = Field(default=1, ge=1, le=50)
    enabled: bool = True
    favorite: bool = False
    known_intelligence: str = ""
    success_criteria: str = ""
    failure_conditions: str = ""
    objectives: List[Dict[str, Any]] = []
    script_events: List[Dict[str, Any]] = []
    hints: List[Dict[str, Any]] = []
    walkthrough: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = {}


class ExerciseRunRequest(BaseModel):
    exercise_id: int
    metadata: Dict[str, Any] = {}


class ExerciseCheckpointRequest(BaseModel):
    name: str = "Checkpoint"


class ExerciseCloneRequest(BaseModel):
    name: Optional[str] = None


class ExerciseFinishRequest(BaseModel):
    confirm_cancel: bool = False


class DeviceTypeRequest(BaseModel):
    name: str
    description: str = ""
    category: str = "Custom"
    icon: str = "cpu"
    color: str = "#38bdf8"
    vendor: str = ""
    model: str = ""
    firmware_supported: str = ""
    default_capabilities: List[str] = []
    default_effects: List[str] = []
    default_metadata: Dict[str, Any] = {}


class DeviceCreateRequest(BaseModel):
    name: str
    device_type_id: int
    vendor: str
    model: str
    firmware: str
    location: str
    subdivision: str
    track: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    criticality: str
    description: str
    ip_address: Optional[str] = None
    capabilities: Optional[List[str]] = None
    supported_effects: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None


class DeviceRelationshipRequest(BaseModel):
    target_type: str
    target_id: int
    relationship_type: str


class DeviceCapabilitiesRequest(BaseModel):
    capabilities: List[str]
    supported_effects: Optional[List[str]] = None


class DeviceEffectRequest(BaseModel):
    effect_id: str


class NetworkPathRequest(BaseModel):
    source_node_id: int
    destination_node_id: int
    name: Optional[str] = Field(default=None, max_length=160)


class NetworkLayoutPosition(BaseModel):
    id: int
    x: float
    y: float


class NetworkLayoutRequest(BaseModel):
    positions: List[NetworkLayoutPosition] = Field(max_length=250)


class NetworkSimulationRequest(BaseModel):
    simulation_type: str
    source_node_id: Optional[int] = None
    target_node_id: Optional[int] = None

# =========================================================
# FastAPI application
# =========================================================

app = FastAPI(
    title="TrackSentinel",
    description="RailSOC Training & Simulation Platform",
    version="1.0.0",
)


cors_origins = [
    origin.strip()
    for origin in os.getenv(
        "TRACKSENTINEL_CORS_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173",
    ).split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# =========================================================
# Database setup
# =========================================================

Base.metadata.create_all(bind=engine)
ensure_sqlite_schema()


def get_db():
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()


def _active_exercise_run_id(db):
    run = db.query(ExerciseRun).filter(
        ExerciseRun.status.in_(["Running", "Paused"])
    ).order_by(ExerciseRun.started_at.desc(), ExerciseRun.id.desc()).first()
    return run.id if run else None


@app.on_event("startup")
def initialize_track_block_controller_assignments():
    db = SessionLocal()

    try:
        assign_signal_controller_track_blocks(db)
        seed_operational_assets(db)
        seed_route_topology(db)
        initialize_device_framework(db)
        seed_exercises(db)
        seed_network_visibility(db)
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def _network_http_error(db, exc):
    db.rollback()
    if isinstance(exc, NetworkValidationError):
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    raise exc


@app.get("/api/network/nodes")
def network_nodes(db: Session = Depends(get_db)):
    try:
        get_network_topology(db, event_limit=1)
        return [
            serialize_network_node(node)
            for node in db.query(NetworkNode).order_by(NetworkNode.id).all()
        ]
    except Exception as exc:
        _network_http_error(db, exc)


@app.get("/api/network/nodes/{node_id}")
def network_node(node_id: int, db: Session = Depends(get_db)):
    try:
        return get_network_node(db, node_id)
    except Exception as exc:
        _network_http_error(db, exc)


@app.get("/api/network/connections")
def network_connections(db: Session = Depends(get_db)):
    return [
        serialize_network_connection(item)
        for item in db.query(NetworkConnection).order_by(NetworkConnection.id).all()
    ]


@app.get("/api/network/connections/{connection_id}")
def network_connection(connection_id: int, db: Session = Depends(get_db)):
    try:
        return get_network_connection(db, connection_id)
    except Exception as exc:
        _network_http_error(db, exc)


@app.get("/api/network/zones")
def network_zones(db: Session = Depends(get_db)):
    return [
        serialize_network_zone(zone)
        for zone in db.query(NetworkZone).order_by(NetworkZone.id).all()
    ]


@app.get("/api/network/topology")
def network_topology(
    event_limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    try:
        return get_network_topology(db, event_limit)
    except Exception as exc:
        _network_http_error(db, exc)


@app.get("/api/network/events")
@app.get("/api/network/traffic")
def network_events(
    limit: int = Query(default=100, ge=1, le=500),
    node_id: Optional[int] = None,
    connection_id: Optional[int] = None,
    severity: Optional[str] = None,
    protocol: Optional[str] = None,
    event_type: Optional[str] = None,
    incident_id: Optional[int] = None,
    db: Session = Depends(get_db),
):
    return list_network_events(
        db,
        limit=limit,
        node_id=node_id,
        connection_id=connection_id,
        severity=severity,
        protocol=protocol,
        event_type=event_type,
        incident_id=incident_id,
    )


@app.get("/api/network/path")
def network_paths(db: Session = Depends(get_db)):
    return [
        {
            "id": item.id,
            "name": item.name,
            "source_node_id": item.source_node_id,
            "destination_node_id": item.destination_node_id,
            "hops": json.loads(item.hops_json or "[]"),
            "path_status": item.path_status,
            "total_latency_ms": item.total_latency_ms,
            "total_packet_loss": item.total_packet_loss,
            "updated_at": item.updated_at.isoformat() if item.updated_at else None,
        }
        for item in db.query(NetworkPath)
        .order_by(NetworkPath.updated_at.desc(), NetworkPath.id.desc())
        .limit(50)
        .all()
    ]


@app.post("/api/network/path/trace")
def network_trace_path(
    request: NetworkPathRequest,
    db: Session = Depends(get_db),
):
    try:
        result = trace_network_path(
            db,
            request.source_node_id,
            request.destination_node_id,
            request.name,
        )
        db.commit()
        return result
    except Exception as exc:
        _network_http_error(db, exc)


@app.post("/api/network/layout")
def network_save_layout(
    request: NetworkLayoutRequest,
    db: Session = Depends(get_db),
):
    try:
        result = save_network_layout(
            db, [position.model_dump() for position in request.positions]
        )
        db.commit()
        return result
    except Exception as exc:
        _network_http_error(db, exc)


@app.post("/api/network/nodes/{node_id}/{action}")
def network_node_action(
    node_id: int,
    action: str,
    db: Session = Depends(get_db),
):
    try:
        result = apply_node_action(db, node_id, action)
        db.commit()
        return result
    except Exception as exc:
        _network_http_error(db, exc)


@app.post("/api/network/connections/{connection_id}/{action}")
def network_connection_action(
    connection_id: int,
    action: str,
    db: Session = Depends(get_db),
):
    try:
        result = apply_connection_action(db, connection_id, action)
        db.commit()
        return result
    except Exception as exc:
        _network_http_error(db, exc)


@app.post("/api/network/simulate")
def network_simulate(
    request: NetworkSimulationRequest,
    db: Session = Depends(get_db),
):
    try:
        result = run_network_simulation(
            db,
            request.simulation_type,
            request.source_node_id,
            request.target_node_id,
        )
        db.commit()
        return result
    except Exception as exc:
        _network_http_error(db, exc)


@app.post("/api/network/reset")
def network_reset(db: Session = Depends(get_db)):
    try:
        result = restore_network_baseline(db)
        db.commit()
        return result
    except Exception as exc:
        _network_http_error(db, exc)


@app.websocket("/ws/network")
async def network_websocket(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            db = SessionLocal()
            try:
                await websocket.send_json(network_websocket_payload(db))
            finally:
                db.close()
            await asyncio.sleep(4)
    except WebSocketDisconnect:
        return



# =========================================================
# AI Operations Brief
# =========================================================

@app.get("/ai/operations-brief")
def get_ai_operations_brief(
    db: Session = Depends(get_db),
):
    devices = db.query(models.OTDevice).all()
    alerts = db.query(models.Alert).all()
    vulnerabilities = db.query(
        models.Vulnerability
    ).all()
    trains = db.query(models.Train).all()
    track_blocks = db.query(models.TrackBlock).all()

    activity_logs = (
        db.query(models.ActivityLog)
        .order_by(models.ActivityLog.timestamp.desc())
        .limit(50)
        .all()
    )

    incidents = db.query(models.Incident).all()
    result = build_operations_brief(
        devices=devices,
        alerts=alerts,
        vulnerabilities=vulnerabilities,
        trains=trains,
        track_blocks=track_blocks,
        activity_logs=activity_logs,
        incidents=incidents,
    )
    impact = get_operational_impact(db)
    result["operational_impact"] = impact
    result["operational_summary"] = build_operational_summary(impact)
    dispatch_status = build_dispatch_status(db)
    result["dispatch"] = dispatch_status
    result["dispatch_brief"] = (
        f"Dispatch SCADA is {dispatch_status['scada_state']}. "
        f"{dispatch_status['queued_commands']} command(s) are queued and "
        f"{dispatch_status['blocked_commands']} are blocked. "
        f"{dispatch_status['active_restrictions']} restriction(s) are active; "
        f"{dispatch_status['delayed_trains']} train(s) are delayed. "
        + (
            "Defensive priority: restore trusted dispatch communications or transfer to backup."
            if dispatch_status["dispatch_availability_percent"] < 100
            else "Defensive priority: continue monitoring command integrity."
        )
    )
    result["asset_capability_summaries"] = [
        serialize_device(db, device)["dynamic_summary"]
        for device in devices
    ]
    return result
# =========================================================
# Scenario endpoint
# =========================================================

@app.post("/training/scenarios")
def create_training_scenario(request: ScenarioCreateRequest):
    attack = Attack_Catalog.get(request.attack_id)

    if attack is None:
        raise HTTPException(
            status_code=404,
            detail=f'Attack "{request.attack_id}" was not found.',
        )

    scenario = scenario_manager.create_scenario(
        attack_id=request.attack_id,
        attack_name=attack["name"],
        target_ids=request.target_ids,
        notes=request.notes,
        created_by=request.created_by,
    )

    return {
        "message": "Scenario created successfully.",
        "scenario": scenario,
    }


# =========================================================
# Persisted Exercise Engine
# =========================================================

@app.get("/exercises")
def list_exercises(
    category: Optional[str] = None,
    difficulty: Optional[str] = None,
    enabled: Optional[bool] = None,
    favorite: Optional[bool] = None,
    completed: Optional[bool] = None,
    instructor: bool = False,
    db: Session = Depends(get_db),
):
    query = db.query(Exercise)
    if category:
        query = query.filter(Exercise.category == category)
    if difficulty:
        query = query.filter(Exercise.difficulty == difficulty)
    if enabled is not None:
        query = query.filter(Exercise.enabled == enabled)
    if favorite is not None:
        query = query.filter(Exercise.favorite == favorite)
    exercises = query.order_by(Exercise.name).all()
    if completed is not None:
        completed_ids = {
            row.exercise_id
            for row in db.query(ExerciseRun).filter(
                ExerciseRun.status == "Completed"
            ).all()
        }
        exercises = [
            item for item in exercises
            if (item.id in completed_ids) == completed
        ]
    return {
        "exercises": [
            serialize_exercise(
                item, include_definition=True, instructor=instructor
            )
            for item in exercises
        ]
    }


@app.post("/exercises", status_code=201)
def add_exercise(
    request: ExerciseDefinitionRequest,
    db: Session = Depends(get_db),
):
    try:
        exercise = create_exercise(db, request.model_dump())
        db.commit()
        return serialize_exercise(exercise, include_definition=True, instructor=True)
    except ExerciseValidationError as exc:
        db.rollback()
        raise HTTPException(status_code=exc.status_code, detail=str(exc))


@app.put("/exercises/{exercise_id}")
def edit_exercise(
    exercise_id: int,
    request: ExerciseDefinitionRequest,
    db: Session = Depends(get_db),
):
    exercise = db.query(Exercise).filter(Exercise.id == exercise_id).first()
    if not exercise:
        raise HTTPException(status_code=404, detail="Exercise not found.")
    if db.query(ExerciseRun).filter(
        ExerciseRun.exercise_id == exercise.id
    ).first():
        raise HTTPException(
            status_code=409,
            detail="Exercise history exists; clone the exercise before editing its definition.",
        )
    try:
        exercise = update_exercise(db, exercise, request.model_dump())
        db.commit()
        return serialize_exercise(exercise, include_definition=True, instructor=True)
    except ExerciseValidationError as exc:
        db.rollback()
        raise HTTPException(status_code=exc.status_code, detail=str(exc))


@app.delete("/exercises/{exercise_id}")
def remove_exercise(exercise_id: int, db: Session = Depends(get_db)):
    exercise = db.query(Exercise).filter(Exercise.id == exercise_id).first()
    if not exercise:
        raise HTTPException(status_code=404, detail="Exercise not found.")
    if db.query(ExerciseRun).filter(
        ExerciseRun.exercise_id == exercise.id
    ).first():
        raise HTTPException(
            status_code=409,
            detail="Exercise history exists; disable the exercise instead of deleting it.",
        )
    db.delete(exercise)
    db.commit()
    return {"deleted": True, "exercise_id": exercise_id}


@app.post("/exercises/{exercise_id}/clone", status_code=201)
def clone_exercise_endpoint(
    exercise_id: int,
    request: ExerciseCloneRequest,
    db: Session = Depends(get_db),
):
    exercise = db.query(Exercise).filter(Exercise.id == exercise_id).first()
    if not exercise:
        raise HTTPException(status_code=404, detail="Exercise not found.")
    try:
        cloned = clone_exercise(db, exercise, request.name)
        db.commit()
        return serialize_exercise(cloned, include_definition=True, instructor=True)
    except ExerciseValidationError as exc:
        db.rollback()
        raise HTTPException(status_code=exc.status_code, detail=str(exc))


@app.get("/exercises/{exercise_id}/export")
def export_exercise(
    exercise_id: int,
    instructor: bool = False,
    db: Session = Depends(get_db),
):
    exercise = db.query(Exercise).filter(Exercise.id == exercise_id).first()
    if not exercise:
        raise HTTPException(status_code=404, detail="Exercise not found.")
    return serialize_exercise(
        exercise, include_definition=True, instructor=instructor
    )


@app.post("/exercises/import", status_code=201)
def import_exercise(
    request: ExerciseDefinitionRequest,
    db: Session = Depends(get_db),
):
    return add_exercise(request, db)


@app.get("/exercise-runs")
def list_exercise_runs(
    status: Optional[str] = None,
    db: Session = Depends(get_db),
):
    process_exercise_runs(db)
    query = db.query(ExerciseRun)
    if status:
        query = query.filter(ExerciseRun.status == status)
    runs = query.order_by(ExerciseRun.created_at.desc()).all()
    db.commit()
    return {"runs": [serialize_run(db, item, detail=False) for item in runs]}


@app.delete("/exercise-runs")
def remove_exercise_run_history(db: Session = Depends(get_db)):
    try:
        result = clear_exercise_history(db)
        db.commit()
        return {
            "message": "Exercise history cleared.",
            **result,
        }
    except ExerciseValidationError as exc:
        db.rollback()
        raise HTTPException(status_code=exc.status_code, detail=str(exc))


@app.post("/exercise-runs", status_code=201)
def add_exercise_run(
    request: ExerciseRunRequest,
    db: Session = Depends(get_db),
):
    try:
        run = create_run(db, request.exercise_id, request.metadata)
        db.commit()
        return serialize_run(db, run)
    except ExerciseValidationError as exc:
        db.rollback()
        raise HTTPException(status_code=exc.status_code, detail=str(exc))


@app.get("/exercise-runs/{run_id}")
def get_exercise_run(
    run_id: int,
    instructor: bool = False,
    db: Session = Depends(get_db),
):
    run = db.query(ExerciseRun).filter(ExerciseRun.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Exercise run not found.")
    process_exercise_runs(db)
    db.commit()
    return serialize_run(db, run, instructor=instructor)


def _exercise_run_action(db, action, run_id):
    try:
        run = action(db, run_id)
        db.commit()
        return serialize_run(db, run)
    except ExerciseValidationError as exc:
        db.rollback()
        raise HTTPException(status_code=exc.status_code, detail=str(exc))


@app.post("/exercise-runs/{run_id}/start")
def start_exercise_run(run_id: int, db: Session = Depends(get_db)):
    return _exercise_run_action(db, start_run, run_id)


@app.post("/exercise-runs/{run_id}/pause")
def pause_exercise_run(run_id: int, db: Session = Depends(get_db)):
    return _exercise_run_action(db, pause_run, run_id)


@app.post("/exercise-runs/{run_id}/resume")
def resume_exercise_run(run_id: int, db: Session = Depends(get_db)):
    return _exercise_run_action(db, resume_run, run_id)


@app.post("/exercise-runs/{run_id}/cancel")
def cancel_exercise_run(run_id: int, db: Session = Depends(get_db)):
    return _exercise_run_action(db, cancel_run, run_id)


@app.post("/exercise-runs/{run_id}/finish")
def finish_exercise_run(
    run_id: int,
    request: ExerciseFinishRequest,
    db: Session = Depends(get_db),
):
    try:
        run = finish_run(db, run_id, confirm_cancel=request.confirm_cancel)
        db.commit()
        return serialize_run(db, run)
    except ExerciseValidationError as exc:
        db.rollback()
        raise HTTPException(status_code=exc.status_code, detail=str(exc))


@app.post("/exercise-runs/{run_id}/restart", status_code=201)
def restart_exercise_run(run_id: int, db: Session = Depends(get_db)):
    return _exercise_run_action(db, restart_run, run_id)


@app.get("/exercise-runs/{run_id}/score")
def get_exercise_score(run_id: int, db: Session = Depends(get_db)):
    run = db.query(ExerciseRun).filter(ExerciseRun.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Exercise run not found.")
    process_exercise_runs(db)
    db.commit()
    return serialize_score(run)


@app.get("/exercise-runs/{run_id}/timeline")
def get_exercise_timeline(run_id: int, db: Session = Depends(get_db)):
    run = db.query(ExerciseRun).filter(ExerciseRun.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Exercise run not found.")
    return {
        "events": [
            item for item in get_timeline(db, 500)
            if item.get("scenario_id") == str(run.id)
        ]
    }


@app.get("/exercise-runs/{run_id}/checkpoints")
def get_exercise_checkpoints(run_id: int, db: Session = Depends(get_db)):
    return {
        "checkpoints": [
            serialize_checkpoint(item)
            for item in db.query(ExerciseCheckpoint).filter(
                ExerciseCheckpoint.run_id == run_id
            ).order_by(ExerciseCheckpoint.created_at.desc()).all()
        ]
    }


@app.post("/exercise-runs/{run_id}/checkpoints", status_code=201)
def create_exercise_checkpoint(
    run_id: int,
    request: ExerciseCheckpointRequest,
    db: Session = Depends(get_db),
):
    try:
        checkpoint = save_checkpoint(db, run_id, request.name)
        db.commit()
        return serialize_checkpoint(checkpoint)
    except ExerciseValidationError as exc:
        db.rollback()
        raise HTTPException(status_code=exc.status_code, detail=str(exc))


@app.post("/exercise-runs/{run_id}/checkpoints/{checkpoint_id}/restore")
def restore_exercise_checkpoint(
    run_id: int,
    checkpoint_id: int,
    db: Session = Depends(get_db),
):
    try:
        run = restore_checkpoint(db, run_id, checkpoint_id)
        db.commit()
        return serialize_run(db, run)
    except ExerciseValidationError as exc:
        db.rollback()
        raise HTTPException(status_code=exc.status_code, detail=str(exc))


@app.post("/exercise-runs/{run_id}/hints")
def request_exercise_hint(run_id: int, db: Session = Depends(get_db)):
    try:
        hint = request_hint(db, run_id)
        db.commit()
        return hint
    except ExerciseValidationError as exc:
        db.rollback()
        raise HTTPException(status_code=exc.status_code, detail=str(exc))


@app.get("/exercises/{exercise_id}/walkthrough")
def get_exercise_walkthrough(
    exercise_id: int,
    instructor: bool = False,
    run_id: Optional[int] = None,
    db: Session = Depends(get_db),
):
    exercise = db.query(Exercise).filter(Exercise.id == exercise_id).first()
    if not exercise:
        raise HTTPException(status_code=404, detail="Exercise not found.")
    run = None
    if run_id is not None:
        run = db.query(ExerciseRun).filter(
            ExerciseRun.id == run_id,
            ExerciseRun.exercise_id == exercise.id,
        ).first()
        if not run:
            raise HTTPException(status_code=404, detail="Exercise run not found.")
        request_objective_reevaluation(db, "walkthrough_view")
    if not instructor and not (run and run.walkthrough_revealed_at):
        return {"available": exercise.walkthrough is not None, "revealed": False}
    return serialize_walkthrough(exercise.walkthrough, run=run, instructor=instructor)


@app.post("/exercise-runs/{run_id}/walkthrough/reveal")
def reveal_exercise_walkthrough(run_id: int, db: Session = Depends(get_db)):
    try:
        result = reveal_walkthrough(db, run_id)
        db.commit()
        return result
    except ExerciseValidationError as exc:
        db.rollback()
        raise HTTPException(status_code=exc.status_code, detail=str(exc))


@app.post("/exercises/{exercise_id}/validate")
def validate_exercise(
    exercise_id: int,
    instructor: bool = Query(default=False),
    db: Session = Depends(get_db),
):
    if not instructor:
        raise HTTPException(status_code=403, detail="Instructor mode is required.")
    exercise = db.query(Exercise).filter(Exercise.id == exercise_id).first()
    if not exercise:
        raise HTTPException(status_code=404, detail="Exercise not found.")
    return validate_exercise_configuration(db, exercise)


@app.get("/exercise-runs/{run_id}/after-action-report")
def get_exercise_after_action_report(
    run_id: int,
    format: str = Query(default="json", pattern="^(json|markdown|pdf)$"),
    db: Session = Depends(get_db),
):
    run = db.query(ExerciseRun).filter(ExerciseRun.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Exercise run not found.")
    report = after_action_report(db, run)
    db.commit()
    if format == "markdown":
        return Response(
            report["markdown"], media_type="text/markdown",
            headers={"Content-Disposition": f'attachment; filename="exercise-{run.id}-aar.md"'},
        )
    if format == "pdf":
        return Response(
            simple_pdf(report["markdown"]), media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="exercise-{run.id}-aar.pdf"'},
        )
    return report
# =========================================================
# AI Incidence Analysis
# =========================================================

@app.get("/incidents/{incident_id}/analysis")
def get_incident_analysis(
    incident_id: int,
    db: Session = Depends(get_db)
):
    incident = db.query(Incident).filter(
        Incident.id == incident_id
    ).first()

    if not incident:
        raise HTTPException(
            status_code=404,
            detail="Incident not found"
        )

    device = None

    if incident.device_id:
        device = db.query(OTDevice).filter(
            OTDevice.id == incident.device_id
        ).first()

    vulnerabilities = []

    if incident.device_id:
        vulnerabilities = db.query(Vulnerability).filter(
            Vulnerability.device_id == incident.device_id
        ).all()

    open_vulnerabilities = 0

    for vulnerability in vulnerabilities:
        vulnerability_status = (
            vulnerability.status or "Open"
        ).lower()

        if vulnerability_status not in {
            "closed",
            "resolved",
            "remediated"
        }:
            open_vulnerabilities += 1

    previous_incidents = 0

    if incident.device_id:
        previous_incidents = db.query(Incident).filter(
            Incident.device_id == incident.device_id,
            Incident.id != incident.id
        ).count()

    incident_data = {
        "id": incident.id,
        "severity": incident.severity,
        "device": incident.device,
        "alert_type": incident.alert_type,
        "message": incident.message,
        "status": incident.status,
        "acknowledged": incident.acknowledged,
        "assigned_to": incident.assigned_to,
        "investigation_notes": incident.investigation_notes,
        "mitre_technique": incident.mitre_technique,
        "closed_by": incident.closed_by,
        "closed_at": (
            incident.closed_at.isoformat()
            if incident.closed_at
            else None
        )
    }

    device_context = {
        "status": device.status if device else "Unknown",
        "risk_level": device.risk_level if device else "Unknown",
        "firmware_version": (
            device.firmware_version
            if device
            else None
        ),
        "last_seen": (
            device.last_seen.isoformat()
            if device and device.last_seen
            else None
        ),
        "open_vulnerabilities": open_vulnerabilities,
        "previous_incidents": previous_incidents
    }
    import json

    print(json.dumps(incident_data, indent=2, default=str))                        

    result = analyze_single_incident(
        incident=incident_data,
        device_context=device_context
    )
    impact = get_operational_impact(db)
    summary = build_operational_summary(impact)
    result.setdefault("operational_impact", {})
    result["operational_impact"]["description"] = summary
    result["operational_impact"]["metrics"] = impact
    result["operational_summary"] = summary
    return result
# =========================================================
# Track Blocks API endpoint
# =========================================================

@app.get("/track-blocks")
def get_track_blocks(
    db: Session = Depends(get_db),
):
    blocks = (
        db.query(models.TrackBlock)
        .order_by(models.TrackBlock.start_milepost)
        .all()
    )

    return [
        {
            "id": block.id,
            "name": block.name,
            "subdivision": block.subdivision,
            "track": block.track,
            "start_mp": block.start_milepost,
            "end_mp": block.end_milepost,
            "occupied": block.occupied,
            "occupied_train_id": (
                block.occupied_train_id
            ),
            "controlling_device_id": block.controlling_device_id,
            "controlling_device": (
                block.controlling_device.name
                if block.controlling_device
                else None
            ),
            "occupied_by": (
                block.occupied_train.symbol
                if block.occupied_train
                else None
            ),
            "signal_aspect": block.signal_aspect,
            "authority": block.authority,
            "speed_limit": block.speed_limit,
            "communications_status": (
                block.communications_status
            ),
            "security_status": block.security_status,
            "maintenance": block.maintenance,
            "last_updated": block.last_updated,
        }
        for block in blocks
    ]


@app.get("/operations/impact")
def get_operations_impact(db: Session = Depends(get_db)):
    impact = get_operational_impact(db)
    return {
        **impact,
        "summary": build_operational_summary(impact),
    }


@app.get("/operations/timeline")
def get_operations_timeline(
    limit: int = 100,
    db: Session = Depends(get_db),
):
    return {"events": get_timeline(db, limit=limit)}


@app.get("/digital-twin/map")
def get_digital_twin_map(db: Session = Depends(get_db)):
    return get_map_snapshot(db)


@app.get("/track-switches")
def get_track_switches(db: Session = Depends(get_db)):
    switches = db.query(TrackSwitch).order_by(TrackSwitch.milepost).all()
    return [
        {
            "id": track_switch.id,
            "name": track_switch.name,
            "subdivision": track_switch.subdivision,
            "track": track_switch.track,
            "milepost": track_switch.milepost,
            "track_block_id": track_switch.track_block_id,
            "controlling_device_id": track_switch.controlling_device_id,
            "controlling_device": track_switch.controlling_device.name,
            "position": track_switch.position,
            "commanded_position": track_switch.commanded_position,
            "locked": track_switch.locked,
            "communications_status": track_switch.communications_status,
            "security_status": track_switch.security_status,
            "last_updated": track_switch.last_updated,
        }
        for track_switch in switches
    ]


@app.get("/grade-crossings")
def get_grade_crossings(db: Session = Depends(get_db)):
    crossings = db.query(GradeCrossing).order_by(GradeCrossing.milepost).all()
    return [
        {
            "id": crossing.id,
            "name": crossing.name,
            "subdivision": crossing.subdivision,
            "milepost": crossing.milepost,
            "controlling_device_id": crossing.controlling_device_id,
            "controlling_device": crossing.controlling_device.name,
            "gate_state": crossing.gate_state,
            "lights_active": crossing.lights_active,
            "warning_time_seconds": crossing.warning_time_seconds,
            "communications_status": crossing.communications_status,
            "security_status": crossing.security_status,
            "last_updated": crossing.last_updated,
        }
        for crossing in crossings
    ]


@app.get("/dispatch/commands")
def get_dispatch_commands(db: Session = Depends(get_db)):
    return {
        "commands": [
            serialize_command(command)
            for command in db.query(DispatchCommand)
            .order_by(DispatchCommand.requested_at.desc())
            .all()
        ]
    }


@app.get("/dispatch/status")
def get_dispatch_status_endpoint(db: Session = Depends(get_db)):
    return build_dispatch_status(db)


@app.get("/dispatch/commands/{command_id}")
def get_dispatch_command(command_id: int, db: Session = Depends(get_db)):
    command = db.query(DispatchCommand).filter(
        DispatchCommand.id == command_id
    ).first()
    if not command:
        raise HTTPException(status_code=404, detail="Dispatch command not found.")
    return serialize_command(command)


@app.post("/dispatch/commands")
def create_dispatch_command(
    request: DispatchCommandRequest,
    db: Session = Depends(get_db),
):
    try:
        if request.target_type is None or request.target_id is None:
            command = queue_dispatch_command(
                db, request.command_type, request.payload
            )
        else:
            command = create_dispatch_command_service(
                db, request.model_dump()
            )
        request_objective_reevaluation(db, "dispatch_command_changed")
        db.commit()
        db.refresh(command)
        return serialize_command(command)
    except DispatchValidationError as exc:
        db.rollback()
        raise HTTPException(status_code=exc.status_code, detail=str(exc))
    except Exception:
        db.rollback()
        raise


@app.post("/dispatch/commands/{command_id}/cancel")
def cancel_dispatch_command(
    command_id: int,
    request: DispatchActorRequest,
    db: Session = Depends(get_db),
):
    try:
        command = cancel_command(db, command_id, request.requested_by)
        request_objective_reevaluation(db, "dispatch_command_cancelled")
        db.commit()
        return serialize_command(command)
    except DispatchValidationError as exc:
        db.rollback()
        raise HTTPException(status_code=exc.status_code, detail=str(exc))


@app.post("/dispatch/commands/{command_id}/retry")
def retry_dispatch_command(
    command_id: int,
    request: DispatchActorRequest,
    db: Session = Depends(get_db),
):
    try:
        command = retry_command(db, command_id, request.requested_by)
        request_objective_reevaluation(db, "dispatch_command_retried")
        db.commit()
        return serialize_command(command)
    except DispatchValidationError as exc:
        db.rollback()
        raise HTTPException(status_code=exc.status_code, detail=str(exc))


@app.get("/dispatch/routes")
def get_dispatch_routes(db: Session = Depends(get_db)):
    return {"routes": [
        serialize_route(route)
        for route in db.query(DispatchRoute)
        .order_by(DispatchRoute.requested_at.desc()).all()
    ]}


@app.get("/dispatch/topology")
def get_dispatch_topology(db: Session = Depends(get_db)):
    return {"segments": [
        serialize_topology_segment(segment)
        for segment in db.query(RouteTopologySegment)
        .order_by(RouteTopologySegment.id).all()
    ]}


@app.post("/dispatch/routes")
def request_dispatch_route(
    request: DispatchRouteRequest,
    db: Session = Depends(get_db),
):
    try:
        route = create_route(db, request.model_dump())
        if route.status == "Blocked":
            active_run_id = _active_exercise_run_id(db)
            if active_run_id:
                record_event(
                    db,
                    event_type="dispatch_route_blocked",
                    title="Unsafe or invalid route prevented",
                    message=route.blocking_reason or "A route request was blocked.",
                    severity="High",
                    source="Exercise Engine",
                    scenario_id=str(active_run_id),
                    metadata={"route_id": route.id, "safety_violation": True},
                )
        request_objective_reevaluation(db, "dispatch_route_changed")
        db.commit()
        return serialize_route(route)
    except DispatchValidationError as exc:
        db.rollback()
        raise HTTPException(status_code=exc.status_code, detail=str(exc))


@app.get("/dispatch/restrictions")
def get_dispatch_restrictions(
    active: Optional[bool] = None,
    db: Session = Depends(get_db),
):
    query = db.query(OperationalRestriction)
    if active is not None:
        query = query.filter(OperationalRestriction.active == active)
    return {"restrictions": [
        serialize_restriction(item)
        for item in query.order_by(
            OperationalRestriction.created_at.desc()
        ).all()
    ]}


@app.post("/dispatch/restrictions")
def add_dispatch_restriction(
    request: DispatchRestrictionRequest,
    db: Session = Depends(get_db),
):
    try:
        item = create_restriction(db, request.model_dump())
        request_objective_reevaluation(db, "restriction_applied")
        db.commit()
        return serialize_restriction(item)
    except DispatchValidationError as exc:
        db.rollback()
        raise HTTPException(status_code=exc.status_code, detail=str(exc))


@app.post("/dispatch/restrictions/{restriction_id}/clear")
def clear_dispatch_restriction(
    restriction_id: int,
    request: DispatchActorRequest,
    db: Session = Depends(get_db),
):
    try:
        item = clear_restriction(db, restriction_id, request.requested_by)
        request_objective_reevaluation(db, "restriction_cleared")
        db.commit()
        return serialize_restriction(item)
    except DispatchValidationError as exc:
        db.rollback()
        raise HTTPException(status_code=exc.status_code, detail=str(exc))


@app.post("/dispatch/recovery-actions")
def dispatch_recovery_action(
    request: RecoveryActionRequest,
    db: Session = Depends(get_db),
):
    try:
        payload = request.model_dump()
        payload["exercise_run_id"] = _active_exercise_run_id(db)
        result = perform_recovery_action(db, payload)
        request_objective_reevaluation(db, "recovery_action_completed")
        db.commit()
        return result
    except DispatchValidationError as exc:
        db.rollback()
        raise HTTPException(status_code=exc.status_code, detail=str(exc))


@app.post("/dispatch/status")
def set_dispatch_status(
    request: DispatchStatusRequest,
    db: Session = Depends(get_db),
):
    normalized = request.status.strip().title()
    if normalized not in {"Online", "Degraded", "Severe", "Offline"}:
        raise HTTPException(
            status_code=400,
            detail="Status must be Online, Degraded, Severe, or Offline.",
        )
    device = get_dispatch_device(db)
    if device is None:
        raise HTTPException(status_code=404, detail="Dispatch SCADA not found.")
    device.status = normalized
    if normalized == "Online":
        process_dispatch_commands(db, restore=True)
    record_event(
        db,
        event_type="dispatch_status_changed",
        title=f"Dispatch SCADA {normalized.lower()}",
        message=f"Dispatch SCADA status changed to {normalized}.",
        severity="Info" if normalized == "Online" else "High",
        device_id=device.id,
        asset_name=device.name,
        metadata={"status": normalized},
    )
    request_objective_reevaluation(db, "dispatch_status_changed")
    db.commit()
    return {"device": device.name, "status": device.status}

# =========================================================
# Custom Scenario Base models
# =========================================================

class CustomScenario(BaseModel):
    attack_id: str
    target_ids: list[int]
    notes: Optional[str] = None
    effect_id: Optional[str] = None

 


# =========================================================
# Request models
# =========================================================

class TrainCreate(BaseModel):
    symbol: str
    subdivision: str
    train_type: str = "Freight"
    direction: str = "Eastbound"
    destination: Optional[str] = None
    milepost: float = 80.0
    speed: int = 40
    status: str = "Moving"
    ptc_enabled: bool = True
    authority: str = "Main Track"
    locomotive: Optional[str] = None
    train_length: Optional[int] = None
    weight_tons: Optional[int] = None
    crew: Optional[str] = None
    current_signal: str = "Clear"
    track: str = "Main"


class AssignIncidentRequest(BaseModel):
    assigned_to: str


class CloseIncidentRequest(BaseModel):
    closed_by: str


class IncidentNotesRequest(BaseModel):
    investigation_notes: str

# =========================================================
# Track Active Attacks API endpoint
# =========================================================
@app.get("/active-attacks")
def read_active_attacks():
    attacks = get_active_attacks()
    return {
        "count": len(attacks),
        "attacks": attacks
    }
# =========================================================
# Attack Catalog Endpoint
# ======================================================

@app.get("/attacks")
def get_attacks():
    return {
        "attacks": [
            {
                "id": attack["attack_id"],
                "attack_id": attack["attack_id"],
                "name": attack["name"],
                "description": attack["description"],
                "severity": attack["severity"],
                "mitre_id": attack.get("mitre_id"),
                "mitre_name": attack.get("mitre_name"),
                "compatible_types": attack.get("compatible_types", []),
                "condition": attack.get("condition"),
            }
            for attack in Attack_Catalog.values()
        ]
    }
# =========================================================
# Attack Simulation API endpoint
# ======================================================
@app.post("/training/custom-scenario")
def launch_custom_scenario(
    request: CustomScenario,
    db: Session = Depends(get_db),
):
    attack = Attack_Catalog.get(request.attack_id)

    if not attack:
        raise HTTPException(
            status_code=404,
            detail="Attack definition not found",
        )

    if not request.target_ids:
        raise HTTPException(
            status_code=400,
            detail="Select at least one target",
        )

    targets = (
        db.query(OTDevice)
        .filter(
            OTDevice.id.in_(request.target_ids)
        )
        .all()
    )

    if not targets:
        raise HTTPException(
            status_code=404,
            detail="No matching targets were found",
        )

    if request.effect_id:
        attack = {**attack, "effect_id": request.effect_id}

    invalid_targets = []

    for target in targets:
        if request.effect_id:
            compatible = (
                request.effect_id in supported_effects_for_device(target)
            )
        else:
            compatible = target.device_type in attack["compatible_types"]
        if not compatible:
            invalid_targets.append(target)

    if invalid_targets:
        invalid_target_names = []

        for target in invalid_targets:
            invalid_target_names.append(target.name)

        raise HTTPException(
            status_code=400,
            detail={
                "message": (
                    "One or more targets are incompatible "
                    "with this attack"
                ),
                "invalid_targets": invalid_target_names,
                "compatible_types": attack["compatible_types"],
            },
        )

    try:
        simulation_results = apply_attack(
            db=db,
            attack=attack,
            targets=targets,
            exercise_run_id=_active_exercise_run_id(db),
        )
        request_objective_reevaluation(db, "attack_launched")
        db.commit()

        for target in targets:
            db.refresh(target)

        attack_instance = launch_attack(
            attack=attack,
            targets=targets,
            notes=request.notes,
        )

        return {
            "message": "Custom scenario launched successfully",
            "scenario": attack_instance,
            "simulation": simulation_results,
        }
    except DigitalTwinConflictError as exc:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail=str(exc),
        ) from exc
    except Exception:
        db.rollback()
        raise
# =========================================================
# Train API endpoints
# =========================================================

@app.get("/trains")
def get_trains(db: Session = Depends(get_db)):
    return db.query(Train).order_by(Train.id).all()


@app.get("/trains/{train_id}")
def get_train(
    train_id: int,
    db: Session = Depends(get_db),
):
    train = (
        db.query(Train)
        .filter(Train.id == train_id)
        .first()
    )

    if not train:
        raise HTTPException(
            status_code=404,
            detail="Train not found",
        )

    return train


@app.post("/trains")
def create_train(
    payload: TrainCreate,
    db: Session = Depends(get_db),
):
    existing = (
        db.query(Train)
        .filter(Train.symbol == payload.symbol)
        .first()
    )

    if existing:
        raise HTTPException(
            status_code=400,
            detail="A train with that symbol already exists",
        )

    train = Train(
        symbol=payload.symbol,
        subdivision=payload.subdivision,
        train_type=payload.train_type,
        direction=payload.direction,
        destination=payload.destination,
        milepost=payload.milepost,
        speed=payload.speed,
        status=payload.status,
        ptc_enabled=payload.ptc_enabled,
        authority=payload.authority,
        locomotive=payload.locomotive,
        train_length=payload.train_length,
        weight_tons=payload.weight_tons,
        crew=payload.crew,
        current_signal=payload.current_signal,
        track=payload.track,
        last_updated=datetime.utcnow(),
    )

    db.add(train)
    db.commit()
    db.refresh(train)

    return train
@app.get("/")
def root():
   return {
    "product": "TrackSentinel",
    "platform": "RailSOC Training & Simulation Platform",
    "version": "1.0.0"
}


@app.get("/devices")
def get_devices(db: Session = Depends(get_db)):
    devices = db.query(OTDevice).all()
    results = []

    for device in devices:
        device_alerts = db.query(Alert).filter(Alert.device_id == device.id).all()
        device_vulns = db.query(Vulnerability).filter(Vulnerability.device_id == device.id).all()

        risk = calculate_device_risk(device, device_alerts, device_vulns)

        result = serialize_device(db, device)
        result.update({
            "risk_score": risk["risk_score"],
            "calculated_risk": risk["calculated_risk"]
        })
        results.append(result)

    return results


@app.post("/devices", status_code=201)
def add_device(
    request: DeviceCreateRequest,
    db: Session = Depends(get_db),
):
    try:
        device = create_device(db, request)
        db.commit()
        db.refresh(device)
        return serialize_device(db, device)
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/device-types")
def get_device_types(db: Session = Depends(get_db)):
    return [
        serialize_device_type(device_type)
        for device_type in db.query(OTDeviceType)
        .order_by(OTDeviceType.category, OTDeviceType.name)
        .all()
    ]


@app.post("/device-types", status_code=201)
def add_device_type(
    request: DeviceTypeRequest,
    db: Session = Depends(get_db),
):
    if db.query(OTDeviceType).filter_by(name=request.name).first():
        raise HTTPException(
            status_code=409, detail="A device type with this name exists."
        )
    device_type = OTDeviceType(
        name=request.name,
        description=request.description,
        category=request.category,
        icon=request.icon,
        color=request.color,
        vendor=request.vendor,
        model=request.model,
        firmware_supported=request.firmware_supported,
        default_capabilities_json=dumps_json(
            request.default_capabilities
        ),
        default_effects_json=dumps_json(request.default_effects),
        default_metadata_json=dumps_json(request.default_metadata),
    )
    db.add(device_type)
    db.commit()
    db.refresh(device_type)
    return serialize_device_type(device_type)


@app.get("/capabilities")
def get_capabilities():
    return [
        {
            "id": capability,
            "label": capability.replace("_", " ").title(),
            "effects": [
                {"id": effect, "label": EFFECT_LABELS[effect]}
                for effect in effects
            ],
        }
        for capability, effects in CAPABILITY_EFFECTS.items()
    ]


@app.put("/devices/{device_id}/capabilities")
def update_device_capabilities(
    device_id: int,
    request: DeviceCapabilitiesRequest,
    db: Session = Depends(get_db),
):
    device = db.get(OTDevice, device_id)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    previous = loads_json(device.capabilities_json, [])
    device.capabilities_json = dumps_json(request.capabilities)
    if request.supported_effects is not None:
        device.supported_effects_json = dumps_json(
            request.supported_effects
        )
    record_event(
        db,
        event_type="capability_changed",
        title=f"{device.name} capabilities changed",
        message=(
            f"Capabilities changed from {len(previous)} to "
            f"{len(request.capabilities)}."
        ),
        asset_name=device.name,
        device_id=device.id,
        metadata={
            "previous": previous,
            "current": request.capabilities,
        },
    )
    db.commit()
    db.refresh(device)
    return serialize_device(db, device)


@app.get("/devices/{device_id}/supported-effects")
def get_device_supported_effects(
    device_id: int,
    db: Session = Depends(get_db),
):
    device = db.get(OTDevice, device_id)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    return [
        {"id": effect, "label": EFFECT_LABELS.get(
            effect, effect.replace("_", " ").title()
        )}
        for effect in supported_effects_for_device(device)
    ]


@app.post("/devices/{device_id}/effects")
def run_device_effect(
    device_id: int,
    request: DeviceEffectRequest,
    db: Session = Depends(get_db),
):
    device = db.get(OTDevice, device_id)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    try:
        result = apply_effect(db, device, request.effect_id)
        record_event(
            db,
            event_type="custom_attack",
            title=f"Custom attack on {device.name}",
            message=(
                f"A custom scenario applied {request.effect_id} to "
                f"{device.name}."
            ),
            severity="High",
            asset_name=device.name,
            device_id=device.id,
            metadata={"effect_id": request.effect_id},
        )
        request_objective_reevaluation(db, "device_effect_applied")
        db.commit()
        return result
    except DigitalTwinConflictError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@app.get("/relationship-targets")
def get_relationship_targets(db: Session = Depends(get_db)):
    return {
        "TRACK_BLOCK": [
            {"id": item.id, "name": item.name}
            for item in db.query(TrackBlock).order_by(TrackBlock.name)
        ],
        "TRACK_SWITCH": [
            {"id": item.id, "name": item.name}
            for item in db.query(TrackSwitch).order_by(TrackSwitch.name)
        ],
        "GRADE_CROSSING": [
            {"id": item.id, "name": item.name}
            for item in db.query(GradeCrossing).order_by(GradeCrossing.name)
        ],
        "OT_DEVICE": [
            {"id": item.id, "name": item.name}
            for item in db.query(OTDevice).order_by(OTDevice.name)
        ],
    }


@app.post("/devices/{device_id}/relationships", status_code=201)
def add_device_relationship(
    device_id: int,
    request: DeviceRelationshipRequest,
    db: Session = Depends(get_db),
):
    device = db.get(OTDevice, device_id)
    target_type = request.target_type.upper()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    if not relationship_target_exists(db, target_type, request.target_id):
        raise HTTPException(
            status_code=404, detail="Relationship target not found"
        )
    existing = db.query(DeviceRelationship).filter_by(
        source_device_id=device_id,
        target_type=target_type,
        target_id=request.target_id,
        relationship_type=request.relationship_type.upper(),
    ).first()
    if existing:
        return serialize_relationship(db, existing)
    relationship = DeviceRelationship(
        source_device_id=device_id,
        target_type=target_type,
        target_id=request.target_id,
        relationship_type=request.relationship_type.upper(),
    )
    db.add(relationship)
    db.flush()
    serialized = serialize_relationship(db, relationship)
    record_event(
        db,
        event_type="relationship_added",
        title=f"Relationship added for {device.name}",
        message=(
            f"{device.name} now {request.relationship_type.lower().replace('_', ' ')} "
            f"{serialized['target_name']}."
        ),
        asset_name=device.name,
        device_id=device.id,
        metadata=serialized,
    )
    db.commit()
    return serialized


@app.delete("/devices/{device_id}/relationships/{relationship_id}")
def delete_device_relationship(
    device_id: int,
    relationship_id: int,
    db: Session = Depends(get_db),
):
    relationship = db.query(DeviceRelationship).filter_by(
        id=relationship_id, source_device_id=device_id
    ).first()
    if not relationship:
        raise HTTPException(status_code=404, detail="Relationship not found")
    db.delete(relationship)
    db.commit()
    return {"deleted": relationship_id}

@app.post("/incidents/{incident_id}/close")
def close_incident(
    incident_id: int,
    request: CloseIncidentRequest,
    db: Session = Depends(get_db)
):
    incident = (
        db.query(Incident)
        .filter(Incident.id == incident_id)
        .first()
    )

    if not incident:
        raise HTTPException(
            status_code=404,
            detail="Incident not found"
        )

    incident.status = "Closed"
    incident.closed_by = request.closed_by
    incident.closed_at = datetime.now(timezone.utc)
    record_event(
        db,
        event_type="incident_closed",
        title=f"Incident {incident.id} closed",
        message=(
            f"{request.closed_by} closed {incident.alert_type} "
            f"for {incident.device}."
        ),
        asset_name=incident.device or "",
        device_id=incident.device_id,
        incident_id=incident.id,
        scenario_id=(
            str(incident.exercise_run_id) if incident.exercise_run_id else None
        ),
    )

    request_objective_reevaluation(db, "incident_closed")

    db.commit()
    db.refresh(incident)

    return {
        "message": "Incident closed",
        "incident_id": incident.id,
        "status": incident.status,
        "closed_by": incident.closed_by,
        "closed_at": (
            incident.closed_at.isoformat()
            if incident.closed_at
            else None
        ),
    }

@app.get("/alerts")
def get_alerts(db: Session = Depends(get_db)):
    alerts = db.query(Alert).all()

    results = []

    for alert in alerts:
        results.append({
            "id": alert.id,
            "severity": alert.severity,
            "alert_type": alert.alert_type,
            "message": alert.message,
            "status": alert.status,
            "acknowledged": alert.acknowledged,
            "time": alert.timestamp,
            "device_id": alert.device_id,
            "device": alert.device.name if alert.device else "Unknown"
        })

    return results


@app.get("/vulnerabilities")
def get_vulnerabilities(db: Session = Depends(get_db)):
    vulnerabilities = db.query(Vulnerability).all()

    results = []

    for vuln in vulnerabilities:
        results.append({
            "id": vuln.id,
            "device_id": vuln.device_id,
            "cve_id": vuln.cve_id,
            "title": vuln.title,
            "severity": vuln.severity,
            "cvss_score": vuln.cvss_score,
            "status": vuln.status,
            "recommendation": vuln.recommendation,
            "created_at": vuln.created_at
        })

    return results


@app.get("/dashboard")
def dashboard(db: Session = Depends(get_db)):
    devices = db.query(OTDevice).all()
    alerts = db.query(Alert).all()
    vulnerabilities = db.query(Vulnerability).all()

    total = len(devices)
    online = len([d for d in devices if d.status == "Online"])
    offline = len([d for d in devices if d.status == "Offline"])
    high_risk = len([d for d in devices if d.risk_level in ["High", "Critical"]])
    open_alerts = len([a for a in alerts if a.status == "Open"])
    critical_alerts = len([a for a in alerts if a.severity == "Critical"])
    open_vulnerabilities = len([v for v in vulnerabilities if v.status == "Open"])

    return {
        "total_devices": total,
        "online_devices": online,
        "offline_devices": offline,
        "high_risk_devices": high_risk,
        "open_alerts": open_alerts,
        "critical_alerts": critical_alerts,
        "open_vulnerabilities": open_vulnerabilities,
        "overall_status": "Attention Required" if offline or high_risk or critical_alerts else "Healthy"
    }

@app.post("/simulate-attack/{attack_type}")
def simulate_attack(attack_type: str, db: Session = Depends(get_db)):
    attack_type = attack_type.lower()

    scenarios = {
        "firmware": {
            "attack_id": "firmware_tampering",
            "device": "Grade Crossing Controller MP 82.4",
            "status": "Degraded",
            "risk": "Critical",
            "severity": "Critical",
            "alert_type": "Unauthorized Logic Modification",
            "message": "Simulated rail OT event: Unauthorized logic or firmware modification detected on grade crossing controller MP 82.4.",
            "firmware": "UNKNOWN",
        },
        "recon": {
            "attack_id": "network_recon",
            "device": "Dispatch SCADA Server",
            "status": "Online",
            "risk": "High",
            "severity": "High",
            "alert_type": "OT Network Reconnaissance",
            "message": "Simulated rail OT event: Network reconnaissance detected against the dispatch SCADA environment.",
        },
        "dos": {
            "attack_id": "denial_of_service",
            "device": "Dispatch SCADA Server",
            "status": "Degraded",
            "risk": "Critical",
            "severity": "Critical",
            "alert_type": "Rail OT Denial of Service",
            "message": "Simulated rail OT event: Denial of service condition causing degraded dispatch SCADA communications.",
        },
        "auth": {
            "attack_id": "credential_abuse",
            "device": "Rail Engineering Workstation",
            "status": "Online",
            "risk": "High",
            "severity": "High",
            "alert_type": "Unauthorized Engineering Login",
            "message": "Simulated rail OT event: Repeated authentication attempts detected against rail engineering workstation.",
        },
        "ptc": {
            "attack_id": "communication_failure",
            "device": "PTC Radio Gateway",
            "status": "Offline",
            "risk": "High",
            "severity": "High",
            "alert_type": "PTC Radio Failure",
            "message": "Simulated rail OT event: PTC radio gateway communication loss detected from the wayside communications hut.",
        },
        "malware": {
            "attack_id": "malware_injection",
            "device": "Rail Engineering Workstation",
            "status": "Degraded",
            "risk": "Critical",
            "severity": "Critical",
            "alert_type": "Engineering Workstation Malware",
            "message": "Simulated rail OT event: Malware-like behavior detected on rail engineering workstation.",
        },
        "signal": {
            "attack_id": "logic_modification",
            "device": "Signal Controller 14A",
            "status": "Degraded",
            "risk": "Critical",
            "severity": "Critical",
            "alert_type": "Unauthorized Signal Logic Modification",
            "message": (
                "Simulated rail OT event: Unauthorized logic "
                "modification detected on Signal Controller 14A. "
                "The controlled signal has been forced to Stop."
            ),
            "signal_aspect": "Stop",
            "communications_status": "Degraded",
            "security_status": "Compromised",
            "mitre_technique": (
                "T0859 - Modify Controller Tasking"
            ),
        },
        "switch": {
            "attack_id": "logic_modification",
            "device": "Switch Machine Controller",
            "status": "Degraded",
            "risk": "Critical",
            "severity": "Critical",
            "alert_type": "Unauthorized Switch Logic Modification",
            "message": (
                "Simulated rail OT event: Unauthorized switch logic "
                "left the controlled switch locked and misaligned."
            ),
            "mitre_technique": "T0859 - Modify Controller Tasking",
        },
    }

    scenario = scenarios.get(attack_type)

    if not scenario:
        return {
            "error": "Unknown attack type",
            "valid_attack_types": list(scenarios.keys())
        }

    device = db.query(OTDevice).filter(
        OTDevice.name == scenario["device"]
    ).first()

    if not device:
        return {"error": f"{scenario['device']} not found"}

    try:
        device.status = scenario["status"]
        device.risk_level = scenario["risk"]
        device.last_seen = datetime.now(timezone.utc)

        if "firmware" in scenario:
            device.firmware_version = scenario["firmware"]

        affected_blocks = []
        operational_effects = {
            "effect_type": None,
            "affected_track_blocks": [],
        }

        if attack_type == "signal":
            affected_blocks = apply_signal_controller_effect(
                db=db,
                device=device,
            )
            operational_effects = {
                "effect_type": "signal_controller_compromise",
                "affected_track_blocks": affected_blocks,
            }
        else:
            operational_effects = apply_digital_twin_effect(
                db=db,
                attack={
                    "attack_id": scenario["attack_id"],
                    "digital_twin_effect": Attack_Catalog.get(
                        scenario["attack_id"], {}
                    ).get("digital_twin_effect"),
                },
                target=device,
            )
            affected_blocks = operational_effects.get(
                "affected_track_blocks", []
            )

        alert = create_alert(
            db=db,
            device=device,
            attack={
                "severity": scenario["severity"],
                "name": scenario["alert_type"],
                "description": scenario["message"],
                "mitre_technique": scenario.get(
                    "mitre_technique",
                    "",
                ),
            },
            exercise_run_id=_active_exercise_run_id(db),
        )
        record_event(
            db,
            event_type="attack_launched",
            title=scenario["alert_type"],
            message=scenario["message"],
            severity=scenario["severity"],
            source="Direct Simulation",
            asset_name=device.name,
            device_id=device.id,
            incident_id=getattr(alert, "created_incident_id", None),
            metadata={"attack_type": attack_type},
        )

        request_objective_reevaluation(db, "attack_launched")

        db.commit()

        return {
            "message": (
                f"{scenario['alert_type']} simulation created."
            ),
            "device": device.name,
            "severity": scenario["severity"],
            "affected_track_blocks": affected_blocks,
            "operational_effects": operational_effects,
        }
    except DigitalTwinConflictError as exc:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail=str(exc),
        ) from exc
    except HTTPException:
        db.rollback()
        raise
    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Attack simulation failed; no changes were committed.",
        ) from exc

@app.post("/train-simulation/start")
def start_train_simulation():
    started = train_simulation.start()

    return {
        "running": train_simulation.is_running,
        "message": (
            "Train simulation started."
            if started
            else "Train simulation is already running."
        ),
    }

@app.post("/train-simulation/stop")
def stop_train_simulation():
    stopped = train_simulation.stop()
    return{
        "running": train_simulation.is_running,
        "message":(
        "Train simulation stopped."
        if stopped
        else "Train simulation was already stopped"
        ),
    }

@app.post("/train-simulation/restart")
def restart_traing_simulation():
    train_simulation.stop()
    train_simulation.reset_trains()
    train_simulation.start()

    return{
        "running": train_simulation.is_running,
        "message": "Train simulation restarted"
    }


@app.get("/train-simulation/status")
def train_simulation_status():
    return {
        "running": train_simulation.is_running,
        "interval_seconds": train_simulation.interval_seconds,
        "minimum_milepost": train_simulation.minimum_milepost,
        "maximum_milepost": train_simulation.maximum_milepost,
    }

@app.post("/train-simulation/reset")
def reset_train_simulation():
    train_simulation.reset_trains()

    return {
        "success": True,
        "message": "Train simulation reset.",
    }

@app.get("/plant-status")
def plant_status(db: Session = Depends(get_db)):
    devices = db.query(OTDevice).all()
    status_data = []

    for device in devices:
        device_alerts = db.query(Alert).filter(
            Alert.device_id == device.id,
            Alert.status == "Open"
        ).all()

        alert_types = [alert.alert_type for alert in device_alerts]

        if device.device_type in [
            "Signal Controller",
            "Grade Crossing Controller",
            "Switch Controller"
        ]:
            logic_attack = "Unauthorized Logic Modification" in alert_types

            status_data.append({
                "device": device.name,
                "type": device.device_type,
                "status": device.status,
                "temperature": random.randint(82, 105) if logic_attack else random.randint(68, 88),
                "cpu_usage": random.randint(75, 98) if logic_attack else random.randint(15, 75),
                "memory_usage": random.randint(70, 95) if logic_attack else random.randint(25, 85),
                "network_latency": random.randint(20, 80) if logic_attack else random.randint(1, 15),
                "condition": "Configuration Drift" if logic_attack else "Normal",
                "timestamp": datetime.utcnow().isoformat()
            })

        elif device.device_type == "PTC Communications Gateway":
            comm_loss = "PTC Radio Failure" in alert_types

            status_data.append({
                "device": device.name,
                "type": device.device_type,
                "status": device.status,
                "power_output_kw": 0 if device.status == "Offline" or comm_loss else random.randint(350, 475),
                "voltage": 0 if device.status == "Offline" or comm_loss else random.randint(380, 480),
                "network_latency": 999 if device.status == "Offline" or comm_loss else random.randint(1, 20),
                "condition": "Communication Lost" if device.status == "Offline" or comm_loss else "Normal",
                "timestamp": datetime.utcnow().isoformat()
            })

        elif device.device_type == "Dispatch SCADA":
            scan_detected = "OT Network Reconnaissance" in alert_types
            dos_attack = "Rail OT Denial of Service" in alert_types

            status_data.append({
                "device": device.name,
                "type": device.device_type,
                "status": device.status,
                "cpu_usage": random.randint(85, 99) if dos_attack else random.randint(70, 95) if scan_detected else random.randint(20, 65),
                "memory_usage": random.randint(80, 96) if dos_attack else random.randint(65, 90) if scan_detected else random.randint(35, 80),
                "active_sessions": random.randint(12, 30) if dos_attack or scan_detected else random.randint(1, 8),
                "network_latency": random.randint(500, 999) if dos_attack else random.randint(25, 90) if scan_detected else random.randint(1, 10),
                "condition": "Denial of Service" if dos_attack else "Reconnaissance Detected" if scan_detected else "Normal",
                "timestamp": datetime.utcnow().isoformat()
            })

        elif device.device_type == "Engineering Workstation":
            auth_attack = "Unauthorized Engineering Login" in alert_types
            malware_attack = "Engineering Workstation Malware" in alert_types

            status_data.append({
                "device": device.name,
                "type": device.device_type,
                "status": device.status,
                "cpu_usage": random.randint(85, 99) if malware_attack else random.randint(50, 90) if auth_attack else random.randint(10, 90),
                "memory_usage": random.randint(80, 98) if malware_attack else random.randint(50, 90) if auth_attack else random.randint(30, 90),
                "failed_logins": random.randint(8, 25) if auth_attack else random.randint(0, 5),
                "network_latency": random.randint(40, 120) if malware_attack else random.randint(10, 40) if auth_attack else random.randint(1, 25),
                "condition": "Malware Activity" if malware_attack else "Authentication Attack" if auth_attack else "Normal",
                "timestamp": datetime.utcnow().isoformat()
            })

        elif device.device_type in ["Historian", "Jump Server"]:
            status_data.append({
                "device": device.name,
                "type": device.device_type,
                "status": device.status,
                "cpu_usage": random.randint(20, 70),
                "memory_usage": random.randint(35, 85),
                "active_sessions": random.randint(1, 12),
                "network_latency": random.randint(1, 20),
                "condition": "Normal",
                "timestamp": datetime.utcnow().isoformat()
            })

        elif device.device_type == "Communications":
            status_data.append({
                "device": device.name,
                "type": device.device_type,
                "status": device.status,
                "signal_quality": random.randint(82, 100),
                "packet_loss": round(random.uniform(0.0, 1.8), 2),
                "bandwidth_utilization": random.randint(20, 78),
                "network_latency": random.randint(3, 35),
                "condition": "Normal",
                "timestamp": datetime.utcnow().isoformat()
            })

        elif device.device_type in ["Power", "PLC"]:
            status_data.append({
                "device": device.name,
                "type": device.device_type,
                "status": device.status,
                "voltage": random.randint(116, 124),
                "load_percent": random.randint(20, 75),
                "battery_percent": random.randint(75, 100),
                "runtime_minutes": random.randint(45, 180),
                "network_latency": random.randint(1, 20),
                "condition": "Normal",
                "timestamp": datetime.utcnow().isoformat()
            })

        elif device.device_type == "Safety":
            status_data.append({
                "device": device.name,
                "type": device.device_type,
                "status": device.status,
                "smoke_level": random.randint(0, 2),
                "heat_alarm": "No",
                "panel_battery": random.randint(80, 100),
                "network_latency": random.randint(1, 20),
                "condition": "Normal",
                "timestamp": datetime.utcnow().isoformat()
            })

        elif device.device_type == "Environmental":
            status_data.append({
                "device": device.name,
                "type": device.device_type,
                "status": device.status,
                "temperature": random.randint(62, 82),
                "humidity": random.randint(35, 62),
                "gas_ppm": random.randint(0, 3),
                "water_detected": "No",
                "network_latency": random.randint(1, 20),
                "condition": "Normal",
                "timestamp": datetime.utcnow().isoformat()
            })

        elif device.device_type == "Physical Security":
            status_data.append({
                "device": device.name,
                "type": device.device_type,
                "status": device.status,
                "door_state": "Closed",
                "tamper_alarm": "No",
                "network_latency": random.randint(1, 20),
                "condition": "Normal",
                "timestamp": datetime.utcnow().isoformat()
            })

        elif device.device_type == "Infrastructure":
            status_data.append({
                "device": device.name,
                "type": device.device_type,
                "status": device.status,
                "vibration": round(random.uniform(0.1, 1.8), 2),
                "temperature": random.randint(55, 88),
                "bearing_temperature": random.randint(90, 145),
                "network_latency": random.randint(1, 25),
                "condition": "Normal",
                "timestamp": datetime.utcnow().isoformat()
            })

        else:
            status_data.append({
                "device": device.name,
                "type": device.device_type,
                "status": device.status,
                "network_latency": random.randint(1, 25),
                "condition": "Normal",
                "timestamp": datetime.utcnow().isoformat()
            })

    return status_data

@app.get("/incidents")
def get_incidents(db: Session = Depends(get_db)):
    incidents = (
        db.query(Incident)
        .filter(Incident.status != "Closed")
        .order_by(Incident.time.desc())
        .all()
    )

    return [
        {
            "id": incident.id,
            "alert_id": incident.alert_id,
            "device_id": incident.device_id,
            "exercise_run_id": incident.exercise_run_id,
            "time": (
                incident.time.isoformat()
                if incident.time
                else None
            ),
            "severity": incident.severity,
            "device": incident.device,
            "alert_type": incident.alert_type,
            "message": incident.message,
            "status": incident.status,
            "acknowledged": incident.acknowledged,
            "assigned_to": incident.assigned_to,
            "investigation_notes": incident.investigation_notes,
            "closed_by": incident.closed_by,
            "closed_at": (
                incident.closed_at.isoformat()
                if incident.closed_at
                else None
            ),
            "mitre_technique": (
                incident.mitre_technique
                or get_mitre_mapping(incident.alert_type)
            ),
        }
        for incident in incidents
    ]

@app.post("/incidents/{incident_id}/acknowledge")
def acknowledge_incident(
    incident_id: int,
    db: Session = Depends(get_db)
):
    incident = (
        db.query(Incident)
        .filter(Incident.id == incident_id)
        .first()
    )

    if not incident:
        raise HTTPException(
            status_code=404,
            detail="Incident not found"
        )

    incident.acknowledged = True
    incident.status = "Acknowledged"
    record_event(
        db,
        event_type="incident_acknowledged",
        title=f"Incident {incident.id} acknowledged",
        message=f"{incident.alert_type} for {incident.device} was acknowledged.",
        severity=incident.severity or "Info",
        asset_name=incident.device or "",
        device_id=incident.device_id,
        incident_id=incident.id,
        scenario_id=(
            str(incident.exercise_run_id) if incident.exercise_run_id else None
        ),
    )

    request_objective_reevaluation(db, "incident_acknowledged")

    db.commit()
    db.refresh(incident)

    return {
        "message": "Incident acknowledged",
        "incident_id": incident.id,
        "status": incident.status,
        "acknowledged": incident.acknowledged
    }
def get_mitre_mapping(alert_type):
    mappings = {
        "Communication Loss": "T0881 - Service Stop",
        "Firmware Change": "T0859 - Modify Controller Tasking",
        "Authentication": "T0812 - Default Credentials / Valid Accounts",
        "Network Reconnaissance": "T0842 - Network Service Scanning",
        "General": "T0800 - Activate Firmware Update Mode"
    }

    return mappings.get(alert_type, "Unmapped")



@app.post("/incidents/{incident_id}/notes")
def update_incident_notes(
    incident_id: int,
    request: IncidentNotesRequest,
    db: Session = Depends(get_db)
):
    incident = (
        db.query(Incident)
        .filter(Incident.id == incident_id)
        .first()
    )

    if not incident:
        raise HTTPException(
            status_code=404,
            detail="Incident not found"
        )

    incident.investigation_notes = request.investigation_notes

    request_objective_reevaluation(db, "incident_notes_updated")

    db.commit()
    db.refresh(incident)

    return {
        "message": "Investigation notes updated",
        "incident_id": incident.id,
        "investigation_notes": incident.investigation_notes
    }

@app.post("/incidents/{incident_id}/assign")
def assign_incident(
    incident_id: int,
    request: AssignIncidentRequest,
    db: Session = Depends(get_db)
):
    incident = (
        db.query(Incident)
        .filter(Incident.id == incident_id)
        .first()
    )

    if not incident:
        raise HTTPException(
            status_code=404,
            detail="Incident not found"
        )

    incident.assigned_to = request.assigned_to

    request_objective_reevaluation(db, "incident_assigned")

    db.commit()
    db.refresh(incident)

    return {
        "message": "Incident assigned",
        "incident_id": incident.id,
        "assigned_to": incident.assigned_to
    }

@app.post("/reset-demo")
def reset_demo(db: Session = Depends(get_db)):
    try:
        timestamp = datetime.now(timezone.utc)
        devices = db.query(OTDevice).all()

        for device in devices:
            device.status = "Online"
            device.risk_level = "Low"
            device.last_seen = timestamp

            if device.name == "Grade Crossing Controller MP 82.4":
                device.firmware_version = "6.3.1"
            elif device.name == "PTC Radio Gateway":
                device.firmware_version = "5.2.1"
            elif device.name == "Rail Engineering Workstation":
                device.firmware_version = "Windows 11 24H2"

        restored_blocks = []
        for block in db.query(TrackBlock).all():
            was_affected = (
                block.signal_aspect != "Clear"
                or block.communications_status != "Online"
                or block.security_status != "Healthy"
            )
            block.signal_aspect = "Clear"
            block.communications_status = "Online"
            block.security_status = "Healthy"
            block.last_updated = timestamp
            if was_affected:
                restored_blocks.append(block.name)
                record_event(
                    db,
                    event_type="signal_restored",
                    title=f"{block.name} restored",
                    message=(
                        f"{block.name} signal, communications, and "
                        "security state returned to baseline."
                    ),
                    asset_name=block.name,
                    track_block_id=block.id,
                    device_id=block.controlling_device_id,
                )

        restored_switches = []
        for track_switch in db.query(TrackSwitch).all():
            was_affected = (
                track_switch.locked
                or track_switch.position != "Normal"
                or track_switch.commanded_position != "Normal"
                or track_switch.communications_status != "Online"
                or track_switch.security_status != "Healthy"
            )
            track_switch.position = "Normal"
            track_switch.commanded_position = "Normal"
            track_switch.locked = False
            track_switch.communications_status = "Online"
            track_switch.security_status = "Healthy"
            track_switch.last_updated = timestamp
            if was_affected:
                restored_switches.append(track_switch.name)
                record_event(
                    db,
                    event_type="switch_restored",
                    title=f"{track_switch.name} restored",
                    message=(
                        f"{track_switch.name} returned to its normal, "
                        "unlocked operational state."
                    ),
                    asset_name=track_switch.name,
                    device_id=track_switch.controlling_device_id,
                    track_block_id=track_switch.track_block_id,
                )

        restored_crossings = []
        for crossing in db.query(GradeCrossing).all():
            was_affected = (
                crossing.gate_state == "Unavailable"
                or crossing.communications_status != "Online"
                or crossing.security_status != "Healthy"
            )
            crossing.gate_state = "Raised"
            crossing.lights_active = False
            crossing.warning_time_seconds = 30
            crossing.communications_status = "Online"
            crossing.security_status = "Healthy"
            crossing.last_updated = timestamp
            if was_affected:
                restored_crossings.append(crossing.name)
                record_event(
                    db,
                    event_type="crossing_restored",
                    title=f"{crossing.name} restored",
                    message=(
                        f"{crossing.name} warning-system availability "
                        "returned to baseline."
                    ),
                    asset_name=crossing.name,
                    device_id=crossing.controlling_device_id,
                )

        resumed_trains = []
        for train in db.query(Train).all():
            if train.status not in {
                "Stopped at Signal",
                "Stopped at Unsafe Switch",
                "Restricted - PTC Communications",
            }:
                continue
            was_stopped = train.speed == 0
            train.status = "Moving"
            train.current_signal = "Clear"
            if was_stopped:
                train.speed = 0
            train.last_updated = timestamp
            resumed_trains.append(train.symbol)
            record_event(
                db,
                event_type="train_resumed",
                title=f"{train.symbol} authorized to resume",
                message=(
                    f"{train.symbol} was released from its signal stop "
                    "or operating restriction."
                ),
                asset_name=train.symbol,
                train_id=train.id,
                metadata={"milepost": train.milepost, "reset_demo": True},
            )

        applied_dispatch_commands = process_dispatch_commands(
            db, restore=True
        )
        network_reset_result = restore_network_baseline(db)
        db.query(NetworkTrafficEvent).update(
            {
                NetworkTrafficEvent.related_alert_id: None,
                NetworkTrafficEvent.related_incident_id: None,
            },
            synchronize_session=False,
        )
        db.query(Incident).delete(synchronize_session=False)
        db.query(Alert).delete(synchronize_session=False)
        request_objective_reevaluation(db, "demo_reset")
        record_event(
            db,
            event_type="demo_reset",
            title="Operational baseline restored",
            message=(
                "Active alerts and incidents were cleared; historical "
                "timeline events remain available for training review."
            ),
            severity="Info",
            metadata={"reset_demo": True},
        )
        db.commit()

        return {
            "message": "Operational baseline restored",
            "alerts_cleared": True,
            "incidents_cleared": True,
            "restored_track_blocks": restored_blocks,
            "restored_switches": restored_switches,
            "restored_crossings": restored_crossings,
            "resumed_trains": resumed_trains,
            "applied_dispatch_commands": len(applied_dispatch_commands),
            "network_baseline_restored": (
                network_reset_result["simulation_type"] == "restore_baseline"
            ),
        }
    except Exception:
        db.rollback()
        raise
