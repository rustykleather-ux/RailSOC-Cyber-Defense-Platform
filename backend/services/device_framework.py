import json
from uuid import uuid4

from sqlalchemy import or_

from models import (
    DeviceRelationship,
    GradeCrossing,
    OTDevice,
    OTDeviceType,
    TrackBlock,
    TrackSwitch,
)
from services.timeline_service import record_event


CAPABILITY_EFFECTS = {
    "controls_track_blocks": [
        "force_stop_signal",
        "force_approach_signal",
        "disable_signal",
        "communications_loss",
        "logic_modification",
        "remote_lockout",
    ],
    "controls_switches": [
        "lock_switch",
        "misalign_switch",
        "communications_loss",
        "logic_modification",
    ],
    "controls_crossings": [
        "disable_crossing",
        "disable_warning_lights",
        "communications_loss",
        "firmware_corruption",
    ],
    "controls_power": ["power_loss", "remote_lockout", "firmware_corruption"],
    "controls_dispatch": [
        "dispatch_delay",
        "dispatch_offline",
        "queue_dispatch_commands",
        "communications_loss",
    ],
    "controls_ptc": ["ptc_degraded", "restricted_speed", "communications_loss"],
    "controls_communications": ["communications_loss", "remote_lockout"],
    "controls_sensors": [
        "sensor_offline",
        "false_sensor_reading",
        "communications_loss",
    ],
    "supports_remote_management": [
        "remote_lockout",
        "logic_modification",
        "firmware_corruption",
    ],
}

EFFECT_LABELS = {
    effect: effect.replace("_", " ").title()
    for effects in CAPABILITY_EFFECTS.values()
    for effect in effects
}

BUILTIN_DEVICE_TYPES = {
    "Signal Controller": {
        "category": "Signaling",
        "capabilities": ["controls_track_blocks", "controls_signals"],
    },
    "Switch Controller": {
        "category": "Signaling",
        "capabilities": ["controls_switches"],
    },
    "Grade Crossing Controller": {
        "category": "Crossing Protection",
        "capabilities": ["controls_crossings"],
    },
    "PTC Radio Gateway": {
        "category": "Train Control",
        "capabilities": ["controls_ptc", "controls_communications"],
    },
    "PTC Communications Gateway": {
        "category": "Train Control",
        "capabilities": ["controls_ptc", "controls_communications"],
    },
    "Dispatch SCADA": {
        "category": "Control Center",
        "capabilities": ["controls_dispatch"],
    },
    "Power Substation RTU": {
        "category": "Power",
        "capabilities": ["controls_power"],
    },
    "Traction Power PLC": {
        "category": "Power",
        "capabilities": ["controls_power"],
    },
    "Wayside Detector": {
        "category": "Wayside",
        "capabilities": ["controls_sensors"],
    },
    "Hot Box Detector": {
        "category": "Wayside",
        "capabilities": ["controls_sensors"],
    },
    "Defect Detector": {
        "category": "Wayside",
        "capabilities": ["controls_sensors"],
    },
    "AEI Reader": {
        "category": "Wayside",
        "capabilities": ["controls_sensors", "controls_communications"],
    },
    "Interlocking Controller": {
        "category": "Signaling",
        "capabilities": [
            "controls_track_blocks",
            "controls_signals",
            "controls_switches",
        ],
    },
    "SCADA Server": {
        "category": "Control Center",
        "capabilities": ["controls_dispatch"],
    },
    "Bridge Controller": {
        "category": "Infrastructure",
        "capabilities": ["controls_sensors", "supports_remote_management"],
    },
    "Tunnel Ventilation PLC": {
        "category": "Infrastructure",
        "capabilities": ["controls_sensors", "supports_remote_management"],
    },
    "HVAC Controller": {
        "category": "Facilities",
        "capabilities": ["controls_sensors"],
    },
    "Pump Station PLC": {
        "category": "Facilities",
        "capabilities": ["controls_sensors", "supports_remote_management"],
    },
    "Radio Tower": {
        "category": "Communications",
        "capabilities": ["controls_communications"],
    },
    "Fiber Multiplexer": {
        "category": "Communications",
        "capabilities": ["controls_communications"],
    },
    "Environmental Sensor": {
        "category": "Environmental",
        "capabilities": ["controls_sensors"],
    },
    "Engineering Workstation": {
        "category": "Engineering",
        "capabilities": ["supports_remote_management"],
    },
    "Historian": {
        "category": "Control Center",
        "capabilities": ["controls_sensors"],
    },
    "Jump Server": {
        "category": "Engineering",
        "capabilities": ["supports_remote_management"],
    },
    "Communications": {
        "category": "Communications",
        "capabilities": ["controls_communications"],
    },
    "Power": {
        "category": "Power",
        "capabilities": ["controls_power"],
    },
    "PLC": {
        "category": "Control",
        "capabilities": ["supports_remote_management"],
    },
    "Safety": {
        "category": "Safety",
        "capabilities": ["controls_sensors"],
    },
    "Environmental": {
        "category": "Environmental",
        "capabilities": ["controls_sensors"],
    },
    "Physical Security": {
        "category": "Security",
        "capabilities": ["controls_sensors"],
    },
    "Infrastructure": {
        "category": "Infrastructure",
        "capabilities": ["controls_sensors"],
    },
    "Custom": {"category": "Custom", "capabilities": []},
}


def loads_json(value, fallback):
    if value in (None, ""):
        return fallback.copy() if hasattr(fallback, "copy") else fallback
    if isinstance(value, (list, dict)):
        return value
    try:
        parsed = json.loads(value)
        return parsed
    except (TypeError, ValueError):
        return fallback.copy() if hasattr(fallback, "copy") else fallback


def dumps_json(value):
    return json.dumps(value or ([] if isinstance(value, list) else {}))


def effects_for_capabilities(capabilities):
    result = []
    for capability in capabilities or []:
        for effect in CAPABILITY_EFFECTS.get(capability, []):
            if effect not in result:
                result.append(effect)
    return result


def seed_device_types(db):
    for name, definition in BUILTIN_DEVICE_TYPES.items():
        device_type = db.query(OTDeviceType).filter_by(name=name).first()
        capabilities = definition["capabilities"]
        effects = effects_for_capabilities(capabilities)
        if not device_type:
            device_type = OTDeviceType(
                name=name,
                description=f"Built-in {name} asset definition.",
                category=definition["category"],
                default_capabilities_json=dumps_json(capabilities),
                default_effects_json=dumps_json(effects),
            )
            db.add(device_type)
    db.flush()

    custom_type = db.query(OTDeviceType).filter_by(name="Custom").one()
    for device in db.query(OTDevice).all():
        device_type = (
            db.query(OTDeviceType).filter_by(name=device.device_type).first()
            or custom_type
        )
        if device.device_type_id is None:
            device.device_type_id = device_type.id
        if not loads_json(device.capabilities_json, []):
            capabilities = loads_json(
                device_type.default_capabilities_json, []
            )
            device.capabilities_json = dumps_json(capabilities)
        if not loads_json(device.supported_effects_json, []):
            device.supported_effects_json = dumps_json(
                effects_for_capabilities(
                    loads_json(device.capabilities_json, [])
                )
            )


def backfill_legacy_relationships(db):
    mappings = [
        (
            TrackBlock,
            "TRACK_BLOCK",
            "CONTROLS_TRACK_BLOCK",
        ),
        (TrackSwitch, "TRACK_SWITCH", "CONTROLS_SWITCH"),
        (GradeCrossing, "GRADE_CROSSING", "CONTROLS_CROSSING"),
    ]
    for model, target_type, relationship_type in mappings:
        for target in db.query(model).filter(
            model.controlling_device_id.isnot(None)
        ):
            exists = db.query(DeviceRelationship).filter_by(
                source_device_id=target.controlling_device_id,
                target_type=target_type,
                target_id=target.id,
                relationship_type=relationship_type,
            ).first()
            if not exists:
                db.add(
                    DeviceRelationship(
                        source_device_id=target.controlling_device_id,
                        target_type=target_type,
                        target_id=target.id,
                        relationship_type=relationship_type,
                    )
                )


def initialize_device_framework(db):
    seed_device_types(db)
    backfill_legacy_relationships(db)


def capabilities_for_device(device):
    capabilities = loads_json(device.capabilities_json, [])
    if not capabilities and device.type_definition:
        capabilities = loads_json(
            device.type_definition.default_capabilities_json, []
        )
    if not capabilities:
        capabilities = BUILTIN_DEVICE_TYPES.get(
            device.device_type, {}
        ).get("capabilities", [])
    return capabilities


def supported_effects_for_device(device):
    configured = loads_json(device.supported_effects_json, [])
    derived = effects_for_capabilities(capabilities_for_device(device))
    return list(dict.fromkeys(configured + derived))


def relationship_targets(db, device, target_type, legacy_model=None):
    ids = {
        row.target_id
        for row in db.query(DeviceRelationship).filter(
            DeviceRelationship.source_device_id == device.id,
            DeviceRelationship.target_type == target_type,
        )
    }
    if legacy_model is not None:
        ids.update(
            row.id
            for row in db.query(legacy_model).filter(
                legacy_model.controlling_device_id == device.id
            )
        )
    if not ids or legacy_model is None:
        return []
    return db.query(legacy_model).filter(legacy_model.id.in_(ids)).all()


def serialize_device_type(device_type):
    return {
        "id": device_type.id,
        "name": device_type.name,
        "description": device_type.description,
        "category": device_type.category,
        "icon": device_type.icon,
        "color": device_type.color,
        "vendor": device_type.vendor,
        "model": device_type.model,
        "firmware_supported": device_type.firmware_supported,
        "default_capabilities": loads_json(
            device_type.default_capabilities_json, []
        ),
        "default_effects": loads_json(device_type.default_effects_json, []),
        "default_metadata": loads_json(
            device_type.default_metadata_json, {}
        ),
    }


def serialize_relationship(db, relationship):
    model_map = {
        "TRACK_BLOCK": TrackBlock,
        "TRACK_SWITCH": TrackSwitch,
        "GRADE_CROSSING": GradeCrossing,
        "OT_DEVICE": OTDevice,
    }
    model = model_map.get(relationship.target_type)
    target = db.get(model, relationship.target_id) if model else None
    return {
        "id": relationship.id,
        "source_device_id": relationship.source_device_id,
        "target_type": relationship.target_type,
        "target_id": relationship.target_id,
        "target_name": getattr(target, "name", None),
        "relationship_type": relationship.relationship_type,
        "created_at": relationship.created_at,
    }


def serialize_device(db, device):
    relationships = [
        serialize_relationship(db, relationship)
        for relationship in device.relationships
    ]
    counts = {}
    for relationship in relationships:
        key = relationship["target_type"]
        counts[key] = counts.get(key, 0) + 1
    readable_targets = {
        "TRACK_BLOCK": "track block",
        "TRACK_SWITCH": "switch",
        "GRADE_CROSSING": "crossing",
        "OT_DEVICE": "device",
    }
    controlled = [
        f"{count} {readable_targets.get(key, key.lower())}"
        f"{'' if count == 1 else 's'}"
        for key, count in counts.items()
    ]
    dynamic_summary = (
        f"{device.name} is a {device.device_type}"
        + (f" that controls {', '.join(controlled)}." if controlled else ".")
    )
    return {
        "id": device.id,
        "name": device.name,
        "ip_address": device.ip_address,
        "device_type": device.device_type,
        "device_type_id": device.device_type_id,
        "vendor": device.vendor,
        "model": device.model,
        "firmware_version": device.firmware_version,
        "location": device.location,
        "subdivision": device.subdivision,
        "track": device.track,
        "latitude": device.latitude,
        "longitude": device.longitude,
        "criticality": device.criticality,
        "description": device.description,
        "status": device.status,
        "risk_level": device.risk_level,
        "last_seen": device.last_seen,
        "capabilities": capabilities_for_device(device),
        "supported_effects": supported_effects_for_device(device),
        "metadata": loads_json(device.metadata_json, {}),
        "relationships": relationships,
        "relationship_counts": counts,
        "dynamic_summary": dynamic_summary,
    }


def create_device(db, payload):
    device_type = db.get(OTDeviceType, payload.device_type_id)
    if not device_type:
        raise ValueError("Device type not found")
    capabilities = payload.capabilities
    if capabilities is None:
        capabilities = loads_json(
            device_type.default_capabilities_json, []
        )
    effects = payload.supported_effects
    if effects is None:
        effects = list(
            dict.fromkeys(
                loads_json(device_type.default_effects_json, [])
                + effects_for_capabilities(capabilities)
            )
        )
    device = OTDevice(
        name=payload.name,
        ip_address=payload.ip_address or f"unassigned-{uuid4()}",
        device_type=device_type.name,
        device_type_id=device_type.id,
        vendor=payload.vendor,
        model=payload.model,
        firmware_version=payload.firmware,
        location=payload.location,
        subdivision=payload.subdivision,
        track=payload.track,
        latitude=payload.latitude,
        longitude=payload.longitude,
        criticality=payload.criticality,
        description=payload.description,
        capabilities_json=dumps_json(capabilities),
        supported_effects_json=dumps_json(effects),
        metadata_json=dumps_json(payload.metadata or {}),
        status="Online",
        risk_level="Low",
    )
    db.add(device)
    db.flush()
    record_event(
        db,
        event_type="device_created",
        title=f"{device.name} created",
        message=(
            f"{device.name} was created as a {device_type.name} with "
            f"{len(capabilities)} capabilities."
        ),
        asset_name=device.name,
        device_id=device.id,
        metadata={
            "device_type": device_type.name,
            "capabilities": capabilities,
        },
    )
    return device


def relationship_target_exists(db, target_type, target_id):
    model = {
        "TRACK_BLOCK": TrackBlock,
        "TRACK_SWITCH": TrackSwitch,
        "GRADE_CROSSING": GradeCrossing,
        "OT_DEVICE": OTDevice,
    }.get(target_type)
    return bool(model and db.get(model, target_id))
