from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "ot_platform.db")

DATABASE_URL = os.getenv(
    "TRACKSENTINEL_DATABASE_URL",
    f"sqlite:///{DB_PATH}",
)

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

Base = declarative_base()


ACTIVITY_LOG_COLUMNS = {
    "device_id": "INTEGER",
    "train_id": "INTEGER",
    "track_block_id": "INTEGER",
    "incident_id": "INTEGER",
    "scenario_id": "VARCHAR",
    "metadata_json": "TEXT DEFAULT '{}'",
}

OT_DEVICE_FRAMEWORK_COLUMNS = {
    "device_type_id": "INTEGER",
    "model": "VARCHAR DEFAULT ''",
    "subdivision": "VARCHAR DEFAULT ''",
    "track": "VARCHAR DEFAULT ''",
    "latitude": "FLOAT",
    "longitude": "FLOAT",
    "criticality": "VARCHAR DEFAULT 'Medium'",
    "description": "TEXT DEFAULT ''",
    "capabilities_json": "TEXT DEFAULT '[]'",
    "supported_effects_json": "TEXT DEFAULT '[]'",
    "metadata_json": "TEXT DEFAULT '{}'",
}

DISPATCH_COMMAND_COLUMNS = {
    "target_type": "VARCHAR DEFAULT 'OT_DEVICE'",
    "target_id": "INTEGER",
    "requested_state": "VARCHAR DEFAULT ''",
    "requested_by": "VARCHAR DEFAULT 'Dispatcher'",
    "metadata_json": "TEXT DEFAULT '{}'",
    "priority": "VARCHAR DEFAULT 'Normal'",
    "queued_at": "DATETIME",
    "executed_at": "DATETIME",
    "failed_at": "DATETIME",
    "cancelled_at": "DATETIME",
    "delay_seconds": "INTEGER DEFAULT 0",
    "failure_reason": "TEXT DEFAULT ''",
    "incident_id": "INTEGER",
    "scenario_id": "VARCHAR",
    "retry_of_id": "INTEGER",
}


def ensure_sqlite_schema():
    """Apply the small additive SQLite changes used by the demo app."""
    if engine.dialect.name != "sqlite":
        return

    with engine.begin() as connection:
        additive_tables = {
            "activity_log": ACTIVITY_LOG_COLUMNS,
            "ot_devices": OT_DEVICE_FRAMEWORK_COLUMNS,
            "dispatch_commands": DISPATCH_COMMAND_COLUMNS,
        }
        for table_name, columns in additive_tables.items():
            existing_columns = {
                row[1]
                for row in connection.execute(
                    text(f"PRAGMA table_info({table_name})")
                )
            }
            for column_name, column_type in columns.items():
                if column_name in existing_columns:
                    continue
                connection.execute(
                    text(
                        f"ALTER TABLE {table_name} "
                        f"ADD COLUMN {column_name} {column_type}"
                    )
                )
