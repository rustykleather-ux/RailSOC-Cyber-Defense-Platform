import re
from datetime import datetime, timezone

from models import (
    Alert,
    DispatchCommand,
    DispatchRoute,
    GradeCrossing,
    Incident,
    OTDevice,
    OperationalRestriction,
    TrackBlock,
    TrackSwitch,
    Train,
    Vulnerability,
)
from services.device_framework import loads_json, serialize_device
from services.operational_impact import (
    build_operational_summary,
    get_operational_impact,
)
from services.risk_engine import calculate_device_risk
from services.timeline_service import get_timeline
from services.dispatch_service import (
    serialize_command,
    serialize_restriction,
    serialize_route,
)


def _normalized(value):
    return str(value or "").strip().lower()


def _block_payload(block):
    return {
        "id": block.id,
        "name": block.name,
        "subdivision": block.subdivision,
        "track": block.track,
        "start_mp": block.start_milepost,
        "end_mp": block.end_milepost,
        "occupied": block.occupied,
        "occupied_train_id": block.occupied_train_id,
        "occupied_by": (
            block.occupied_train.symbol if block.occupied_train else None
        ),
        "controlling_device_id": block.controlling_device_id,
        "controlling_device": (
            block.controlling_device.name
            if block.controlling_device
            else None
        ),
        "signal_aspect": block.signal_aspect,
        "authority": block.authority,
        "speed_limit": block.speed_limit,
        "communications_status": block.communications_status,
        "security_status": block.security_status,
        "maintenance": block.maintenance,
        "last_updated": block.last_updated,
    }


def _route_blocks(blocks, subdivision, track):
    exact = [
        block
        for block in blocks
        if block.subdivision == subdivision and block.track == track
    ]
    if exact:
        return sorted(exact, key=lambda item: item.start_milepost)
    return sorted(
        [block for block in blocks if block.track == track],
        key=lambda item: item.start_milepost,
    )


def _current_and_next_block(train, blocks):
    route = _route_blocks(blocks, train.subdivision, train.track)
    milepost = float(train.milepost or 0)
    current = next(
        (
            block
            for block in route
            if float(block.start_milepost)
            <= milepost
            <= float(block.end_milepost)
        ),
        None,
    )
    westbound = _normalized(train.direction) == "westbound"
    if westbound:
        candidates = [
            block for block in route if float(block.end_milepost) < milepost
        ]
        next_block = candidates[-1] if candidates else None
    else:
        next_block = next(
            (
                block
                for block in route
                if float(block.start_milepost) > milepost
            ),
            None,
        )
    return current, next_block


def _train_payload(train, blocks):
    current, next_block = _current_and_next_block(train, blocks)
    status = train.status or "Unknown"
    restrictions = []
    if _normalized(status) not in {"moving", "arrived"}:
        restrictions.append(status)
    if not train.ptc_enabled:
        restrictions.append("PTC disabled")
    return {
        "id": train.id,
        "symbol": train.symbol,
        "subdivision": train.subdivision,
        "track": train.track,
        "direction": train.direction,
        "milepost": train.milepost,
        "speed": train.speed,
        "target_speed": None,
        "current_block": current.name if current else None,
        "current_block_id": current.id if current else None,
        "next_block": next_block.name if next_block else None,
        "next_block_id": next_block.id if next_block else None,
        "current_signal": train.current_signal,
        "status": status,
        "ptc_enabled": train.ptc_enabled,
        "communications_status": None,
        "delay_minutes": None,
        "authority": train.authority,
        "operational_restrictions": restrictions,
        "last_updated": train.last_updated,
    }


def _device_milepost(device, relationships, target_lookup):
    metadata = loads_json(device.metadata_json, {})
    explicit = metadata.get("milepost")
    try:
        if explicit is not None:
            return float(explicit)
    except (TypeError, ValueError):
        pass

    positions = []
    for relationship in relationships:
        target = target_lookup.get(
            (relationship["target_type"], relationship["target_id"])
        )
        if not target:
            continue
        if "milepost" in target:
            positions.append(float(target["milepost"]))
        elif "start_mp" in target and "end_mp" in target:
            positions.append(
                (float(target["start_mp"]) + float(target["end_mp"])) / 2
            )
    if positions:
        return round(sum(positions) / len(positions), 3)

    match = re.search(
        r"\bMP\s*([0-9]+(?:\.[0-9]+)?)",
        " ".join([device.name or "", device.location or ""]),
        re.IGNORECASE,
    )
    return float(match.group(1)) if match else None


def _device_payload(db, device, target_lookup):
    payload = serialize_device(db, device)
    alerts = db.query(Alert).filter(Alert.device_id == device.id).all()
    vulnerabilities = db.query(Vulnerability).filter(
        Vulnerability.device_id == device.id
    ).all()
    risk = calculate_device_risk(device, alerts, vulnerabilities)
    status = _normalized(device.status)
    metadata = payload["metadata"]
    linked_targets = [
        target_lookup.get(
            (relationship["target_type"], relationship["target_id"])
        )
        for relationship in payload["relationships"]
    ]
    linked_target = next((target for target in linked_targets if target), None)
    payload.update(
        {
            "type": device.device_type,
            "risk": risk["calculated_risk"],
            "risk_score": risk["risk_score"],
            "milepost": _device_milepost(
                device, payload["relationships"], target_lookup
            ),
            "subdivision": (
                device.subdivision
                or metadata.get("subdivision")
                or (linked_target or {}).get("subdivision")
                or ""
            ),
            "track": (
                device.track
                or metadata.get("track")
                or (linked_target or {}).get("track")
                or "Main"
            ),
            "communications_status": metadata.get(
                "communications_status",
                (
                    device.status
                    if status in {"offline", "degraded", "severe"}
                    else "Online"
                ),
            ),
            "security_status": metadata.get(
                "security_status",
                (
                    "Compromised"
                    if status == "compromised"
                    or _normalized(device.risk_level) == "critical"
                    else "Healthy"
                ),
            ),
        }
    )
    return payload


def _subdivision_payload(blocks):
    subdivisions = {}
    for block in blocks:
        subdivision = subdivisions.setdefault(
            block.subdivision,
            {
                "name": block.subdivision,
                "minimum_milepost": float(block.start_milepost),
                "maximum_milepost": float(block.end_milepost),
                "tracks": set(),
            },
        )
        subdivision["minimum_milepost"] = min(
            subdivision["minimum_milepost"], float(block.start_milepost)
        )
        subdivision["maximum_milepost"] = max(
            subdivision["maximum_milepost"], float(block.end_milepost)
        )
        subdivision["tracks"].add(block.track or "Main")
    return [
        {**subdivision, "tracks": sorted(subdivision["tracks"])}
        for subdivision in sorted(
            subdivisions.values(), key=lambda item: item["name"]
        )
    ]


def get_map_snapshot(db):
    blocks = db.query(TrackBlock).order_by(
        TrackBlock.subdivision,
        TrackBlock.track,
        TrackBlock.start_milepost,
    ).all()
    block_payloads = [_block_payload(block) for block in blocks]

    switches = db.query(TrackSwitch).order_by(
        TrackSwitch.subdivision, TrackSwitch.track, TrackSwitch.milepost
    ).all()
    switch_payloads = [
        {
            "id": item.id,
            "name": item.name,
            "subdivision": item.subdivision,
            "track": item.track,
            "milepost": item.milepost,
            "track_block_id": item.track_block_id,
            "position": item.position,
            "commanded_position": item.commanded_position,
            "locked": item.locked,
            "controlling_device_id": item.controlling_device_id,
            "controlling_device": item.controlling_device.name,
            "communications_status": item.communications_status,
            "security_status": item.security_status,
            "last_updated": item.last_updated,
        }
        for item in switches
    ]

    crossings = db.query(GradeCrossing).order_by(
        GradeCrossing.subdivision, GradeCrossing.milepost
    ).all()
    crossing_payloads = [
        {
            "id": item.id,
            "name": item.name,
            "subdivision": item.subdivision,
            "track": (
                item.controlling_device.track
                if item.controlling_device
                and item.controlling_device.track
                else "Main"
            ),
            "milepost": item.milepost,
            "gate_state": item.gate_state,
            "lights_active": item.lights_active,
            "warning_time_seconds": item.warning_time_seconds,
            "controlling_device_id": item.controlling_device_id,
            "controlling_device": item.controlling_device.name,
            "communications_status": item.communications_status,
            "security_status": item.security_status,
            "last_updated": item.last_updated,
        }
        for item in crossings
    ]

    target_lookup = {
        **{
            ("TRACK_BLOCK", item["id"]): item for item in block_payloads
        },
        **{
            ("TRACK_SWITCH", item["id"]): item for item in switch_payloads
        },
        **{
            ("GRADE_CROSSING", item["id"]): item
            for item in crossing_payloads
        },
    }
    devices = [
        _device_payload(db, device, target_lookup)
        for device in db.query(OTDevice).order_by(OTDevice.name)
    ]
    trains = [
        _train_payload(train, blocks)
        for train in db.query(Train).order_by(Train.id)
    ]
    signals = [
        {
            "id": f"block-{block['id']}-entrance",
            "block_id": block["id"],
            "name": f"{block['name']} entrance signal",
            "subdivision": block["subdivision"],
            "track": block["track"],
            "milepost": block["start_mp"],
            "aspect": block["signal_aspect"],
            "controlling_device_id": block["controlling_device_id"],
            "controlling_device": block["controlling_device"],
            "communications_status": block["communications_status"],
            "security_status": block["security_status"],
        }
        for block in block_payloads
    ]

    impact = get_operational_impact(db)
    impact["summary"] = build_operational_summary(impact)
    timeline = get_timeline(db, limit=20)
    alerts = db.query(Alert).order_by(Alert.timestamp.desc()).limit(50).all()
    incidents = (
        db.query(Incident).order_by(Incident.time.desc()).limit(50).all()
    )
    commands = db.query(DispatchCommand).filter(
        DispatchCommand.status.in_(["Pending", "Queued", "Blocked"])
    ).all()
    routes = db.query(DispatchRoute).filter(
        DispatchRoute.status.in_(["Established", "Occupied", "Blocked"])
    ).all()
    restrictions = db.query(OperationalRestriction).filter(
        OperationalRestriction.active.is_(True)
    ).all()

    return {
        "generated_at": datetime.now(timezone.utc),
        "subdivisions": _subdivision_payload(blocks),
        "blocks": block_payloads,
        "signals": signals,
        "trains": trains,
        "switches": switch_payloads,
        "crossings": crossing_payloads,
        "devices": devices,
        "operational_impact": impact,
        "timeline": timeline,
        "alerts": [
            {
                "id": item.id,
                "device_id": item.device_id,
                "device_name": item.device.name if item.device else None,
                "severity": item.severity,
                "alert_type": item.alert_type,
                "message": item.message,
                "status": item.status,
                "timestamp": item.timestamp,
            }
            for item in alerts
        ],
        "incidents": [
            {
                "id": item.id,
                "device_id": item.device_id,
                "device": item.device,
                "severity": item.severity,
                "alert_type": item.alert_type,
                "message": item.message,
                "status": item.status,
                "time": item.time,
            }
            for item in incidents
        ],
        "dispatch_commands": [serialize_command(item) for item in commands],
        "dispatch_routes": [serialize_route(item) for item in routes],
        "operational_restrictions": [
            serialize_restriction(item) for item in restrictions
        ],
    }
