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
        nullable=False,
    )
    command_type = Column(String, nullable=False)
    payload_json = Column(Text, default="{}")
    status = Column(String, default="Queued")
    requested_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    apply_after = Column(DateTime, nullable=True)
    applied_at = Column(DateTime, nullable=True)

    device = relationship("OTDevice")
