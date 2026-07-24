from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Float
from sqlalchemy.orm import relationship
from datetime import datetime


from database import Base


class OTDevice(Base):
    __tablename__ = "ot_devices"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    ip_address = Column(String, nullable=False, unique=True, index=True)
    device_type = Column(String, nullable=False)
    vendor = Column(String, nullable=False)
    status = Column(String, default="Unknown")
    risk_level = Column(String, default="Low")
    firmware_version = Column(String, default="Unknown")
    location = Column(String, default="Unknown")
    last_seen = Column(DateTime, default=datetime.utcnow)

    alerts = relationship("Alert", back_populates="device")


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