from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship
from datetime import datetime


from database import Base


class OTDeviceType(Base):
    __tablename__ = "ot_device_types"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, unique=True, index=True)
    description = Column(Text, default="")
    category = Column(String, default="Custom")
    icon = Column(String, default="cpu")
    color = Column(String, default="#38bdf8")
    vendor = Column(String, default="")
    model = Column(String, default="")
    firmware_supported = Column(String, default="")
    default_capabilities_json = Column(Text, default="[]")
    default_effects_json = Column(Text, default="[]")
    default_metadata_json = Column(Text, default="{}")

    devices = relationship("OTDevice", back_populates="type_definition")


class OTDevice(Base):
    __tablename__ = "ot_devices"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    ip_address = Column(String, nullable=False, unique=True, index=True)
    device_type = Column(String, nullable=False)
    device_type_id = Column(
        Integer, ForeignKey("ot_device_types.id"), nullable=True, index=True
    )
    vendor = Column(String, nullable=False)
    model = Column(String, default="")
    status = Column(String, default="Unknown")
    risk_level = Column(String, default="Low")
    firmware_version = Column(String, default="Unknown")
    location = Column(String, default="Unknown")
    subdivision = Column(String, default="")
    track = Column(String, default="")
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    criticality = Column(String, default="Medium")
    description = Column(Text, default="")
    capabilities_json = Column(Text, default="[]")
    supported_effects_json = Column(Text, default="[]")
    metadata_json = Column(Text, default="{}")
    last_seen = Column(DateTime, default=datetime.utcnow)

    alerts = relationship("Alert", back_populates="device")
    type_definition = relationship("OTDeviceType", back_populates="devices")
    relationships = relationship(
        "DeviceRelationship",
        back_populates="source_device",
        cascade="all, delete-orphan",
    )
    network_nodes = relationship("NetworkNode", back_populates="ot_device")


class NetworkZone(Base):
    __tablename__ = "network_zones"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, unique=True, index=True)
    zone_type = Column(String, nullable=False, index=True)
    description = Column(Text, default="")
    trust_level = Column(String, default="Medium")
    color_key = Column(String, default="#38bdf8")
    security_policy = Column(Text, default="")
    location = Column(String, default="")

    nodes = relationship("NetworkNode", back_populates="zone")


class NetworkNode(Base):
    __tablename__ = "network_nodes"

    id = Column(Integer, primary_key=True, index=True)
    zone_id = Column(Integer, ForeignKey("network_zones.id"), nullable=False, index=True)
    ot_device_id = Column(Integer, ForeignKey("ot_devices.id"), nullable=True, index=True)
    name = Column(String, nullable=False, unique=True, index=True)
    display_name = Column(String, nullable=False)
    node_type = Column(String, nullable=False, index=True)
    device_type = Column(String, default="")
    security_zone = Column(String, nullable=False, index=True)
    network_segment = Column(String, default="")
    ip_address = Column(String, default="")
    hostname = Column(String, default="")
    operating_system = Column(String, default="")
    vendor = Column(String, default="")
    model = Column(String, default="")
    firmware_version = Column(String, default="")
    protocol = Column(String, default="")
    status = Column(String, default="Healthy", index=True)
    health = Column(String, default="Healthy")
    risk_level = Column(String, default="Low", index=True)
    criticality = Column(String, default="Medium")
    location = Column(String, default="")
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    last_seen = Column(DateTime, default=datetime.utcnow)
    is_managed = Column(Boolean, default=True)
    is_ot_asset = Column(Boolean, default=False)
    layout_x = Column(Float, nullable=True)
    layout_y = Column(Float, nullable=True)
    metadata_json = Column(Text, default="{}")

    zone = relationship("NetworkZone", back_populates="nodes")
    ot_device = relationship("OTDevice", back_populates="network_nodes")
    outgoing_connections = relationship(
        "NetworkConnection",
        foreign_keys="NetworkConnection.source_node_id",
        back_populates="source_node",
        cascade="all, delete-orphan",
    )
    incoming_connections = relationship(
        "NetworkConnection",
        foreign_keys="NetworkConnection.target_node_id",
        back_populates="target_node",
        cascade="all, delete-orphan",
    )


class NetworkConnection(Base):
    __tablename__ = "network_connections"
    __table_args__ = (
        UniqueConstraint(
            "source_node_id",
            "target_node_id",
            "connection_type",
            name="uq_network_connection",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    source_node_id = Column(
        Integer, ForeignKey("network_nodes.id"), nullable=False, index=True
    )
    target_node_id = Column(
        Integer, ForeignKey("network_nodes.id"), nullable=False, index=True
    )
    connection_type = Column(String, nullable=False)
    protocol = Column(String, default="")
    port = Column(Integer, nullable=True)
    direction = Column(String, default="Bidirectional")
    bandwidth_mbps = Column(Float, default=100.0)
    latency_ms = Column(Float, default=1.0)
    packet_loss_percent = Column(Float, default=0.0)
    status = Column(String, default="Healthy", index=True)
    encrypted = Column(Boolean, default=True)
    security_boundary_crossing = Column(Boolean, default=False)
    last_activity = Column(DateTime, default=datetime.utcnow)
    risk_level = Column(String, default="Low")
    metadata_json = Column(Text, default="{}")

    source_node = relationship(
        "NetworkNode",
        foreign_keys=[source_node_id],
        back_populates="outgoing_connections",
    )
    target_node = relationship(
        "NetworkNode",
        foreign_keys=[target_node_id],
        back_populates="incoming_connections",
    )


class NetworkTrafficEvent(Base):
    __tablename__ = "network_traffic_events"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    source_node_id = Column(
        Integer, ForeignKey("network_nodes.id"), nullable=True, index=True
    )
    target_node_id = Column(
        Integer, ForeignKey("network_nodes.id"), nullable=True, index=True
    )
    connection_id = Column(
        Integer, ForeignKey("network_connections.id"), nullable=True, index=True
    )
    network_path_id = Column(
        Integer, ForeignKey("network_paths.id"), nullable=True, index=True
    )
    protocol = Column(String, default="")
    port = Column(Integer, nullable=True)
    bytes_sent = Column(Integer, default=0)
    bytes_received = Column(Integer, default=0)
    severity = Column(String, default="Info", index=True)
    event_type = Column(String, nullable=False, index=True)
    description = Column(Text, default="")
    related_alert_id = Column(Integer, ForeignKey("alerts.id"), nullable=True, index=True)
    related_incident_id = Column(
        Integer, ForeignKey("incidents.id"), nullable=True, index=True
    )
    is_suspicious = Column(Boolean, default=False, index=True)


class NetworkPath(Base):
    __tablename__ = "network_paths"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    source_node_id = Column(
        Integer, ForeignKey("network_nodes.id"), nullable=False, index=True
    )
    destination_node_id = Column(
        Integer, ForeignKey("network_nodes.id"), nullable=False, index=True
    )
    hops_json = Column(Text, default="[]")
    path_status = Column(String, default="Healthy")
    total_latency_ms = Column(Float, default=0.0)
    total_packet_loss = Column(Float, default=0.0)
    updated_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class DeviceRelationship(Base):
    __tablename__ = "device_relationships"
    __table_args__ = (
        UniqueConstraint(
            "source_device_id",
            "target_type",
            "target_id",
            "relationship_type",
            name="uq_device_relationship",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    source_device_id = Column(
        Integer, ForeignKey("ot_devices.id"), nullable=False, index=True
    )
    target_type = Column(String, nullable=False, index=True)
    target_id = Column(Integer, nullable=False, index=True)
    relationship_type = Column(String, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    source_device = relationship("OTDevice", back_populates="relationships")


class Alert(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(Integer, ForeignKey("ot_devices.id"), nullable=True)
    exercise_run_id = Column(
        Integer, ForeignKey("exercise_runs.id"), nullable=True, index=True
    )

    severity = Column(String, nullable=False)
    alert_type = Column(String, default="General")
    message = Column(String, nullable=False)
    status = Column(String, default="Open")
    acknowledged = Column(Boolean, default=False)
    assigned_to = Column(String, default="Unassigned")
    investigation_notes = Column(String, default="")
    closed_by = Column(String, default="")
    closed_at = Column(DateTime, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    

    device = relationship("OTDevice", back_populates="alerts")


class Incident(Base):
    __tablename__ = "incidents"

    id = Column(Integer, primary_key=True, index=True)

    alert_id = Column(
        Integer,
        ForeignKey("alerts.id"),
        nullable=True,
        index=True
    )

    device_id = Column(
        Integer,
        ForeignKey("ot_devices.id"),
        nullable=True,
        index=True
    )
    exercise_run_id = Column(
        Integer, ForeignKey("exercise_runs.id"), nullable=True, index=True
    )

    time = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )

    severity = Column(
        String,
        default="Medium",
        nullable=False
    )

    device = Column(
        String,
        default="Unknown"
    )

    alert_type = Column(
        String,
        default="General"
    )

    message = Column(
        String,
        nullable=False
    )

    status = Column(
        String,
        default="Open"
    )

    acknowledged = Column(
        Boolean,
        default=False
    )

    assigned_to = Column(
        String,
        default="Unassigned"
    )

    investigation_notes = Column(
        String,
        default=""
    )

    closed_by = Column(
        String,
        default=""
    )

    closed_at = Column(
        DateTime,
        nullable=True
    )

    mitre_technique = Column(
        String,
        default=""
    )

    source_alert = relationship(
        "Alert",
        foreign_keys=[alert_id]
    )

    source_device = relationship(
        "OTDevice",
        foreign_keys=[device_id]
    )

class Vulnerability(Base):
    __tablename__ = "vulnerabilities"

    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(Integer, ForeignKey("ot_devices.id"), nullable=True)

    cve_id = Column(String, default="Unknown")
    title = Column(String, nullable=False)
    severity = Column(String, default="Medium")
    cvss_score = Column(Float, default=0.0)
    status = Column(String, default="Open")
    recommendation = Column(String, default="Review and remediate.")

    created_at = Column(DateTime, default=datetime.utcnow)

class Train(Base):
    __tablename__ = "trains"
   
    id = Column(Integer, primary_key=True, index=True)

    # Railroad Information
    symbol = Column(String, nullable=False)
    subdivision = Column(String, nullable=False)
    
    train_type =Column(String, default="Freight")

    direction = Column(String, default="Eastbound")
    destination = Column(String)



    # Live Operations
    milepost = Column(Float, default=80.0)
    speed = Column(Integer, default=40)
    status = Column(String, default="Moving")
    ptc_enabled = Column(Boolean, default=True)
    authority = Column(String, default="Main Track")

    # Train Information
    locomotive = Column(String)
    train_length = Column(Integer)
    weight_tons = Column(Integer)
    crew = Column(String)

    # Operational
    current_signal = Column(String, default="Clear")
    track = Column(String, default="Main")
    last_updated = Column(
    DateTime,
    default=datetime.utcnow,
    onupdate=datetime.utcnow
    )

class TrainHistory(Base):
    __tablename__ = "train_history"

    id = Column(Integer, primary_key=True, index=True)

    train_id = Column(
        Integer,
        ForeignKey("trains.id"),
        nullable=False
    )

    timestamp = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )

    milepost = Column(Float, nullable=False)
    speed = Column(Integer, nullable=False)
    status = Column(String)
    current_signal = Column(String)
    authority = Column(String)
    ptc_enabled = Column(Boolean)

    train = relationship("Train", backref="history")



class ActivityLog(Base):
    __tablename__ = "activity_log"

    id = Column(Integer, primary_key=True, index=True)

    timestamp = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
        index=True
    )

    event_type = Column(String, nullable=False)
    title = Column(String, nullable=False)
    description = Column(String, nullable=False)
    severity = Column(String, default="Info")
    source = Column(String, default="TrackSentinel")
    asset_name = Column(String, default="")
    status = Column(String, default="Completed")
    device_id = Column(Integer, nullable=True, index=True)
    train_id = Column(Integer, nullable=True, index=True)
    track_block_id = Column(Integer, nullable=True, index=True)
    incident_id = Column(Integer, nullable=True, index=True)
    scenario_id = Column(String, nullable=True, index=True)
    metadata_json = Column(Text, default="{}")


class TrackBlock(Base):
    __tablename__ = "track_blocks"

    id = Column(Integer, primary_key=True, index=True)

    # Railroad Identity
    name = Column(String, nullable=False, unique=True)
    subdivision = Column(String, nullable=False)
    track = Column(String, default="Main")

    # Territory
    start_milepost = Column(Float, nullable=False)
    end_milepost = Column(Float, nullable=False)

    # Occupancy
    occupied = Column(Boolean, default=False)

    occupied_train_id = Column(
        Integer,
        ForeignKey("trains.id"),
        nullable=True
    )

    # Operations
    signal_aspect = Column(
        String,
        default="Clear"
    )

    authority = Column(
        String,
        default="Main Track"
    )

    speed_limit = Column(
        Integer,
        default=49
    )

    # Cyber / OT
    controlling_device_id = Column(
        Integer,
        ForeignKey("ot_devices.id"),
        nullable=True
    )

    communications_status = Column(
        String,
        default="Online"
    )

    security_status = Column(
        String,
        default="Healthy"
    )

    # Maintenance
    maintenance = Column(
        Boolean,
        default=False
    )

    notes = Column(String, default="")

    # Time
    last_updated = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )

    # Relationships
    occupied_train = relationship(
        "Train",
        foreign_keys=[occupied_train_id]
    )

    controlling_device = relationship(
        "OTDevice",
        foreign_keys=[controlling_device_id]
    )


class TrackSwitch(Base):
    __tablename__ = "track_switches"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, unique=True)
    subdivision = Column(String, nullable=False)
    track = Column(String, default="Main")
    milepost = Column(Float, nullable=False)
    track_block_id = Column(
        Integer,
        ForeignKey("track_blocks.id"),
        nullable=True,
    )
    controlling_device_id = Column(
        Integer,
        ForeignKey("ot_devices.id"),
        nullable=False,
    )
    position = Column(String, default="Normal")
    commanded_position = Column(String, default="Normal")
    locked = Column(Boolean, default=False)
    communications_status = Column(String, default="Online")
    security_status = Column(String, default="Healthy")
    last_updated = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    track_block = relationship("TrackBlock")
    controlling_device = relationship("OTDevice")


class GradeCrossing(Base):
    __tablename__ = "grade_crossings"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, unique=True)
    subdivision = Column(String, nullable=False)
    milepost = Column(Float, nullable=False)
    controlling_device_id = Column(
        Integer,
        ForeignKey("ot_devices.id"),
        nullable=False,
    )
    gate_state = Column(String, default="Raised")
    lights_active = Column(Boolean, default=False)
    warning_time_seconds = Column(Integer, default=30)
    communications_status = Column(String, default="Online")
    security_status = Column(String, default="Healthy")
    last_updated = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    controlling_device = relationship("OTDevice")


class DispatchCommand(Base):
    __tablename__ = "dispatch_commands"

    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(
        Integer,
        ForeignKey("ot_devices.id"),
        nullable=True,
    )
    command_type = Column(String, nullable=False)
    target_type = Column(String, default="OT_DEVICE", nullable=False, index=True)
    target_id = Column(Integer, nullable=True, index=True)
    requested_state = Column(String, default="")
    requested_by = Column(String, default="Dispatcher")
    payload_json = Column(Text, default="{}")
    metadata_json = Column(Text, default="{}")
    status = Column(String, default="Queued")
    priority = Column(String, default="Normal")
    requested_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    queued_at = Column(DateTime, nullable=True)
    executed_at = Column(DateTime, nullable=True)
    failed_at = Column(DateTime, nullable=True)
    cancelled_at = Column(DateTime, nullable=True)
    apply_after = Column(DateTime, nullable=True)
    applied_at = Column(DateTime, nullable=True)
    delay_seconds = Column(Integer, default=0)
    failure_reason = Column(Text, default="")
    incident_id = Column(Integer, ForeignKey("incidents.id"), nullable=True)
    scenario_id = Column(String, nullable=True)
    retry_of_id = Column(Integer, ForeignKey("dispatch_commands.id"), nullable=True)

    device = relationship("OTDevice")


class DispatchRoute(Base):
    __tablename__ = "dispatch_routes"

    id = Column(Integer, primary_key=True, index=True)
    train_id = Column(Integer, ForeignKey("trains.id"), nullable=False, index=True)
    start_block_id = Column(
        Integer, ForeignKey("track_blocks.id"), nullable=False, index=True
    )
    destination_block_id = Column(
        Integer, ForeignKey("track_blocks.id"), nullable=False, index=True
    )
    requested_path_json = Column(Text, default="[]")
    required_signal_states_json = Column(Text, default="{}")
    required_switch_positions_json = Column(Text, default="{}")
    status = Column(String, default="Requested", nullable=False, index=True)
    blocking_reason = Column(Text, default="")
    requested_by = Column(String, default="Dispatcher")
    requested_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    established_at = Column(DateTime, nullable=True)
    released_at = Column(DateTime, nullable=True)
    metadata_json = Column(Text, default="{}")

    train = relationship("Train")
    start_block = relationship("TrackBlock", foreign_keys=[start_block_id])
    destination_block = relationship(
        "TrackBlock", foreign_keys=[destination_block_id]
    )


class RouteTopologySegment(Base):
    __tablename__ = "route_topology_segments"
    __table_args__ = (
        UniqueConstraint(
            "from_block_id",
            "to_block_id",
            name="uq_route_topology_direction",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    from_block_id = Column(
        Integer, ForeignKey("track_blocks.id"), nullable=False, index=True
    )
    to_block_id = Column(
        Integer, ForeignKey("track_blocks.id"), nullable=False, index=True
    )
    signal_block_id = Column(
        Integer, ForeignKey("track_blocks.id"), nullable=True
    )
    required_signal_aspect = Column(String, default="Clear")
    switch_id = Column(
        Integer, ForeignKey("track_switches.id"), nullable=True, index=True
    )
    required_switch_position = Column(String, nullable=True)
    enabled = Column(Boolean, default=True, nullable=False, index=True)
    metadata_json = Column(Text, default="{}")

    from_block = relationship("TrackBlock", foreign_keys=[from_block_id])
    to_block = relationship("TrackBlock", foreign_keys=[to_block_id])
    signal_block = relationship("TrackBlock", foreign_keys=[signal_block_id])
    track_switch = relationship("TrackSwitch", foreign_keys=[switch_id])


class OperationalRestriction(Base):
    __tablename__ = "operational_restrictions"

    id = Column(Integer, primary_key=True, index=True)
    restriction_type = Column(String, nullable=False, index=True)
    target_type = Column(String, nullable=False, index=True)
    target_id = Column(Integer, nullable=False, index=True)
    reason = Column(Text, nullable=False)
    severity = Column(String, default="Medium")
    active = Column(Boolean, default=True, nullable=False, index=True)
    created_by = Column(String, default="Dispatcher")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    cleared_by = Column(String, nullable=True)
    cleared_at = Column(DateTime, nullable=True)
    incident_id = Column(Integer, ForeignKey("incidents.id"), nullable=True)
    metadata_json = Column(Text, default="{}")


class Exercise(Base):
    __tablename__ = "exercises"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, unique=True, index=True)
    description = Column(Text, default="")
    category = Column(String, default="Custom", nullable=False, index=True)
    difficulty = Column(String, default="Medium", nullable=False, index=True)
    estimated_duration = Column(Integer, default=20)
    recommended_players = Column(Integer, default=1)
    enabled = Column(Boolean, default=True, nullable=False)
    favorite = Column(Boolean, default=False, nullable=False)
    known_intelligence = Column(Text, default="")
    success_criteria = Column(Text, default="")
    failure_conditions = Column(Text, default="")
    metadata_json = Column(Text, default="{}")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    objectives = relationship(
        "ExerciseObjective", back_populates="exercise",
        cascade="all, delete-orphan", order_by="ExerciseObjective.sort_order"
    )
    script_events = relationship(
        "ExerciseScriptEvent", back_populates="exercise",
        cascade="all, delete-orphan", order_by="ExerciseScriptEvent.offset_seconds"
    )
    hints = relationship(
        "ExerciseHint", back_populates="exercise",
        cascade="all, delete-orphan", order_by="ExerciseHint.available_after_seconds"
    )
    walkthrough = relationship(
        "ExerciseWalkthrough", back_populates="exercise",
        cascade="all, delete-orphan", uselist=False
    )


class ExerciseWalkthrough(Base):
    __tablename__ = "exercise_walkthroughs"

    id = Column(Integer, primary_key=True, index=True)
    exercise_id = Column(
        Integer, ForeignKey("exercises.id"), nullable=False, unique=True, index=True
    )
    overview = Column(Text, default="")
    prerequisites_json = Column(Text, default="[]")
    troubleshooting_json = Column(Text, default="[]")
    expected_end_state_json = Column(Text, default="[]")
    instructor_notes = Column(Text, default="")
    version = Column(Integer, default=1, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    exercise = relationship("Exercise", back_populates="walkthrough")
    steps = relationship(
        "ExerciseWalkthroughStep", back_populates="walkthrough",
        cascade="all, delete-orphan", order_by="ExerciseWalkthroughStep.step_number"
    )


class ExerciseWalkthroughStep(Base):
    __tablename__ = "exercise_walkthrough_steps"

    id = Column(Integer, primary_key=True, index=True)
    walkthrough_id = Column(
        Integer, ForeignKey("exercise_walkthroughs.id"), nullable=False, index=True
    )
    step_number = Column(Integer, nullable=False)
    title = Column(String, nullable=False)
    purpose = Column(Text, default="")
    player_action = Column(Text, default="")
    navigation_location = Column(String, default="")
    target_asset = Column(String, default="")
    expected_result = Column(Text, default="")
    verification_condition = Column(String, default="")
    linked_objective_id = Column(
        Integer, ForeignKey("exercise_objectives.id"), nullable=True, index=True
    )
    action_id = Column(String, default="")
    hint = Column(Text, default="")
    common_mistakes_json = Column(Text, default="[]")
    recovery_path = Column(Text, default="")
    instructor_notes = Column(Text, default="")
    player_visible = Column(Boolean, default=True)

    walkthrough = relationship("ExerciseWalkthrough", back_populates="steps")
    linked_objective = relationship("ExerciseObjective")


class ExerciseObjective(Base):
    __tablename__ = "exercise_objectives"

    id = Column(Integer, primary_key=True, index=True)
    exercise_id = Column(Integer, ForeignKey("exercises.id"), nullable=False, index=True)
    description = Column(Text, nullable=False)
    objective_type = Column(String, nullable=False)
    target_type = Column(String, nullable=True)
    target_id = Column(Integer, nullable=True)
    target_value = Column(Float, nullable=True)
    comparison = Column(String, default="eq")
    optional = Column(Boolean, default=False)
    hidden = Column(Boolean, default=False)
    weight = Column(Float, default=1.0)
    sort_order = Column(Integer, default=0)
    metadata_json = Column(Text, default="{}")

    exercise = relationship("Exercise", back_populates="objectives")


class ExerciseScriptEvent(Base):
    __tablename__ = "exercise_script_events"

    id = Column(Integer, primary_key=True, index=True)
    exercise_id = Column(Integer, ForeignKey("exercises.id"), nullable=False, index=True)
    event_type = Column(String, nullable=False)
    offset_seconds = Column(Integer, default=0, nullable=False)
    condition_json = Column(Text, default="{}")
    payload_json = Column(Text, default="{}")
    one_time = Column(Boolean, default=True)
    sort_order = Column(Integer, default=0)

    exercise = relationship("Exercise", back_populates="script_events")


class ExerciseHint(Base):
    __tablename__ = "exercise_hints"

    id = Column(Integer, primary_key=True, index=True)
    exercise_id = Column(Integer, ForeignKey("exercises.id"), nullable=False, index=True)
    message = Column(Text, nullable=False)
    available_after_seconds = Column(Integer, default=0)
    automatic = Column(Boolean, default=False)
    condition_json = Column(Text, default="{}")

    exercise = relationship("Exercise", back_populates="hints")


class ExerciseRun(Base):
    __tablename__ = "exercise_runs"

    id = Column(Integer, primary_key=True, index=True)
    exercise_id = Column(Integer, ForeignKey("exercises.id"), nullable=False, index=True)
    status = Column(String, default="Ready", nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    started_at = Column(DateTime, nullable=True)
    paused_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    elapsed_seconds = Column(Integer, default=0)
    accumulated_seconds = Column(Integer, default=0)
    score = Column(Float, default=100.0)
    cyber_score = Column(Float, default=100.0)
    operations_score = Column(Float, default=100.0)
    safety_score = Column(Float, default=100.0)
    availability_score = Column(Float, default=100.0)
    response_score = Column(Float, default=100.0)
    current_phase = Column(String, default="Mission Briefing")
    terminal_reason = Column(Text, default="")
    final_evaluated_at = Column(DateTime, nullable=True)
    walkthrough_revealed_at = Column(DateTime, nullable=True)
    metadata_json = Column(Text, default="{}")

    exercise = relationship("Exercise")
    objectives = relationship(
        "ExerciseRunObjective", back_populates="run",
        cascade="all, delete-orphan"
    )
    event_states = relationship(
        "ExerciseRunEvent", back_populates="run",
        cascade="all, delete-orphan"
    )
    checkpoints = relationship(
        "ExerciseCheckpoint", back_populates="run",
        cascade="all, delete-orphan"
    )


class ExerciseRunObjective(Base):
    __tablename__ = "exercise_run_objectives"

    id = Column(Integer, primary_key=True, index=True)
    run_id = Column(Integer, ForeignKey("exercise_runs.id"), nullable=False, index=True)
    objective_id = Column(
        Integer, ForeignKey("exercise_objectives.id"), nullable=False
    )
    status = Column(String, default="Pending")
    progress = Column(Float, default=0.0)
    current_value = Column(Float, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    failed_at = Column(DateTime, nullable=True)
    last_evaluated_at = Column(DateTime, nullable=True)
    last_state_change_at = Column(DateTime, nullable=True)
    metadata_json = Column(Text, default="{}")

    run = relationship("ExerciseRun", back_populates="objectives")
    objective = relationship("ExerciseObjective")


class ExerciseRunEvent(Base):
    __tablename__ = "exercise_run_events"
    __table_args__ = (
        UniqueConstraint("run_id", "script_event_id", name="uq_run_script_event"),
    )

    id = Column(Integer, primary_key=True, index=True)
    run_id = Column(Integer, ForeignKey("exercise_runs.id"), nullable=False, index=True)
    script_event_id = Column(
        Integer, ForeignKey("exercise_script_events.id"), nullable=False
    )
    status = Column(String, default="Pending")
    executed_at = Column(DateTime, nullable=True)
    result_json = Column(Text, default="{}")

    run = relationship("ExerciseRun", back_populates="event_states")
    script_event = relationship("ExerciseScriptEvent")


class ExerciseCheckpoint(Base):
    __tablename__ = "exercise_checkpoints"

    id = Column(Integer, primary_key=True, index=True)
    run_id = Column(Integer, ForeignKey("exercise_runs.id"), nullable=False, index=True)
    name = Column(String, default="Checkpoint")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    elapsed_seconds = Column(Integer, default=0)
    state_json = Column(Text, nullable=False)

    run = relationship("ExerciseRun", back_populates="checkpoints")
