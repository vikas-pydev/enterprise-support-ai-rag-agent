from pathlib import Path
from app.database.config import DatabaseConfig, DEFAULT_DB_CONFIG
from app.database.connection import get_db_connection, ensure_database_exists

_BASE_DIR = Path(__file__).resolve().parent.parent.parent
SCHEMA_SQL_PATH = _BASE_DIR / "database" / "schema.sql"
if not SCHEMA_SQL_PATH.exists():
    SCHEMA_SQL_PATH = Path("database/schema.sql")


def init_db(config: DatabaseConfig = DEFAULT_DB_CONFIG) -> bool:
    """Initialize database tables and indexes from schema.sql idempotently."""
    ensure_database_exists(config)

    if not SCHEMA_SQL_PATH.exists():
        raise FileNotFoundError(f"Schema file not found at {SCHEMA_SQL_PATH}")

    schema_sql = SCHEMA_SQL_PATH.read_text(encoding="utf-8")

    with get_db_connection(config) as conn:
        with conn.cursor() as cur:
            cur.execute(schema_sql)
        conn.commit()

    return True


def drop_tables(config: DatabaseConfig = DEFAULT_DB_CONFIG) -> bool:
    """Drop all application tables (used primarily for test cleanup)."""
    drop_sql = """
    DROP TABLE IF EXISTS travel_expenses CASCADE;
    DROP TABLE IF EXISTS leave_balances CASCADE;
    DROP TABLE IF EXISTS employees CASCADE;
    """
    with get_db_connection(config) as conn:
        with conn.cursor() as cur:
            cur.execute(drop_sql)
        conn.commit()

    return True
