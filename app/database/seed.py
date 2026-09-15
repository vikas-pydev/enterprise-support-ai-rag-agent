import logging
from pathlib import Path
from app.database.config import DatabaseConfig, DEFAULT_DB_CONFIG
from app.database.connection import get_db_connection
from app.database.schema import init_db

logger = logging.getLogger(__name__)

_BASE_DIR = Path(__file__).resolve().parent.parent.parent
SEED_SQL_PATH = _BASE_DIR / "database" / "seed.sql"
if not SEED_SQL_PATH.exists():
    SEED_SQL_PATH = Path("database/seed.sql")


def is_database_seeded(config: DatabaseConfig = DEFAULT_DB_CONFIG) -> bool:
    """Checks whether the employees table already contains records."""
    try:
        with get_db_connection(config) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM employees;")
                count = cur.fetchone()[0]
                return count > 0
    except Exception:
        return False


def seed_db(config: DatabaseConfig = DEFAULT_DB_CONFIG, only_if_empty: bool = False) -> bool:
    """Seed the database with deterministic enterprise test records.

    Args:
        config: Database connection configuration.
        only_if_empty: If True, only seeds if the employees table is currently empty,
                       preventing accidental overwrites of existing production data.
    """
    init_db(config)

    if only_if_empty and is_database_seeded(config):
        logger.info("Database already contains records. Skipping demo seed (only_if_empty=True).")
        return False

    if not SEED_SQL_PATH.exists():
        raise FileNotFoundError(f"Seed file not found at {SEED_SQL_PATH}")

    seed_sql = SEED_SQL_PATH.read_text(encoding="utf-8")

    with get_db_connection(config) as conn:
        with conn.cursor() as cur:
            cur.execute(seed_sql)
        conn.commit()

    logger.info("Database seeded successfully with enterprise demo records.")
    return True


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Seed PostgreSQL database with enterprise demo records.")
    parser.add_argument("--only-if-empty", action="store_true", help="Only seed if database is empty")
    args = parser.parse_args()

    print("Initializing schema and seeding PostgreSQL database...")
    seed_db(only_if_empty=args.only_if_empty)
    print("Database seeded successfully with enterprise test records.")
