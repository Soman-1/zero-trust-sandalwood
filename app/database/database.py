"""Database connection engine and session management."""

from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from app.core.config import settings
from app.core.logging import logger
from app.database.base import Base

from sqlalchemy import event

connect_args = {}
engine_kwargs = {
    "echo": settings.DB_ECHO,
}

if settings.DATABASE_URL.startswith("sqlite"):
    connect_args["check_same_thread"] = False
    connect_args["timeout"] = 30
    engine_kwargs["connect_args"] = connect_args
else:
    # Enterprise connection pooling for PostgreSQL / MySQL / TimescaleDB
    engine_kwargs["pool_size"] = 20
    engine_kwargs["max_overflow"] = 10
    engine_kwargs["pool_timeout"] = 30
    engine_kwargs["pool_recycle"] = 1800
    engine_kwargs["pool_pre_ping"] = True

engine = create_engine(
    settings.DATABASE_URL,
    **engine_kwargs,
)

if settings.DATABASE_URL.startswith("sqlite"):
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.execute("PRAGMA cache_size=-64000")  # 64MB RAM cache
        cursor.execute("PRAGMA temp_store=MEMORY")
        cursor.execute("PRAGMA mmap_size=268435456") # 256MB memory-mapped I/O
        cursor.close()

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency for obtaining a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Initialize database tables."""
    # Import all models to ensure they are registered with Base.metadata
    import app.database.models  # noqa: F401

    logger.info("Initializing database tables...")
    Base.metadata.create_all(bind=engine)
    _ensure_device_salt_column()
    _ensure_tree_assessment_columns()
    _ensure_optional_region_fks()
    logger.info("Database tables initialized successfully.")


def _ensure_device_salt_column() -> None:
    """Add devices.api_key_salt on databases created before the column existed."""
    from sqlalchemy import inspect, text

    inspector = inspect(engine)
    if "devices" not in inspector.get_table_names():
        return
    columns = {col["name"] for col in inspector.get_columns("devices")}
    if "api_key_salt" in columns:
        return
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE devices ADD COLUMN api_key_salt VARCHAR(64)"))
    logger.info("Added devices.api_key_salt column")


def _ensure_tree_assessment_columns() -> None:
    """Add age/host/survival columns on databases created before this decision."""
    from sqlalchemy import inspect, text

    inspector = inspect(engine)
    if "trees" not in inspector.get_table_names():
        return
    columns = {col["name"] for col in inspector.get_columns("trees")}
    statements = []
    if "planting_year" not in columns:
        statements.append("ALTER TABLE trees ADD COLUMN planting_year INTEGER")
    if "host_notes" not in columns:
        statements.append("ALTER TABLE trees ADD COLUMN host_notes TEXT")
    if "last_observed_on" not in columns:
        statements.append("ALTER TABLE trees ADD COLUMN last_observed_on VARCHAR(40)")
    if "survival_confirmed" not in columns:
        statements.append("ALTER TABLE trees ADD COLUMN survival_confirmed BOOLEAN")
    if not statements:
        return
    with engine.begin() as conn:
        for statement in statements:
            conn.execute(text(statement))
    logger.info(f"Added tree assessment columns: {', '.join(statements)}")


def _ensure_optional_region_fks() -> None:
    """Allow trees and weather rows with no reserve. Existing SQLite columns were NOT NULL."""
    from sqlalchemy import text

    if engine.dialect.name != "sqlite":
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE trees ALTER COLUMN region_id DROP NOT NULL"))
            conn.execute(text("ALTER TABLE environmental_measurements ALTER COLUMN region_id DROP NOT NULL"))
            conn.execute(text("ALTER TABLE alerts ALTER COLUMN region_id DROP NOT NULL"))
        logger.info("trees and environmental_measurements region_id are optional")
        return

    def relax(conn, table: str) -> None:
        rows = list(conn.exec_driver_sql(f"PRAGMA table_info({table})").fetchall())
        target = next((row for row in rows if row[1] == "region_id"), None)
        if target is None or not bool(target[3]):
            return
        defs = []
        for _cid, name, ctype, notn, _dflt, pk in rows:
            if name == "region_id":
                defs.append("region_id INTEGER")
            elif pk:
                defs.append(f"{name} INTEGER NOT NULL PRIMARY KEY")
            else:
                typ = ctype or "TEXT"
                defs.append(f"{name} {typ}{' NOT NULL' if notn else ''}")
        for fk in conn.exec_driver_sql(f"PRAGMA foreign_key_list({table})").fetchall():
            dest_table, src_col, dest_col = fk[2], fk[3], fk[4]
            on_update = fk[5] or "NO ACTION"
            on_delete = fk[6] or "NO ACTION"
            defs.append(
                f"FOREIGN KEY({src_col}) REFERENCES {dest_table}({dest_col}) "
                f"ON UPDATE {on_update} ON DELETE {on_delete}"
            )
        cols = ", ".join(row[1] for row in rows)
        tmp = f"{table}__nullable"
        conn.execute(text(f"CREATE TABLE {tmp} ({', '.join(defs)})"))
        conn.execute(text(f"INSERT INTO {tmp} ({cols}) SELECT {cols} FROM {table}"))
        conn.execute(text(f"DROP TABLE {table}"))
        conn.execute(text(f"ALTER TABLE {tmp} RENAME TO {table}"))
        logger.info(f"{table}.region_id is now optional")

    with engine.begin() as conn:
        conn.execute(text("PRAGMA foreign_keys=OFF"))
        tables = {r[0] for r in conn.execute(text("SELECT name FROM sqlite_master WHERE type='table'"))}
        if "trees" in tables:
            relax(conn, "trees")
            conn.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS ix_trees_tree_uid ON trees (tree_uid)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_trees_region_id ON trees (region_id)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_trees_lat_lon ON trees (latitude, longitude)"))
        if "alerts" in tables:
            relax(conn, "alerts")
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_alerts_region_id ON alerts (region_id)"))
        if "environmental_measurements" in tables:
            relax(conn, "environmental_measurements")
            conn.execute(text(
                "CREATE UNIQUE INDEX IF NOT EXISTS ix_environmental_measurements_measurement_uid ON environmental_measurements (measurement_uid)"
            ))
            conn.execute(text(
                "CREATE INDEX IF NOT EXISTS ix_environmental_measurements_region_id ON environmental_measurements (region_id)"
            ))
        conn.execute(text("PRAGMA foreign_keys=ON"))
