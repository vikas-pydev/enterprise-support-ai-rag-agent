"""Database Bootstrap & Schema Initialization Module.

Provides deterministic, idempotent initialization for production cloud deployment:
1. Validates PostgreSQL connectivity.
2. Creates business relational tables (employees, leave_balances, travel_expenses) idempotently.
3. Initializes LangGraph checkpoint tables (checkpoints, checkpoint_blobs, checkpoint_writes)
   via the official LangGraph PostgresSaver implementation when PostgreSQL checkpointing is enabled.
4. Optionally seeds demo data ONLY when explicitly requested (seed_demo=True or SEED_DEMO_DATA=1).
"""

import os
import sys
import logging
import argparse
from typing import NamedTuple

from app.database.config import DatabaseConfig, DEFAULT_DB_CONFIG
from app.database.connection import test_connection
from app.database.schema import init_db
from app.database.seed import seed_db, is_database_seeded

logger = logging.getLogger(__name__)


class BootstrapResult(NamedTuple):
    connection_ok: bool
    schema_initialized: bool
    checkpoints_initialized: bool
    demo_seeded: bool
    message: str


import socket
from urllib.parse import urlparse


def get_checkpoint_db_url() -> str | None:
    """Resolves PostgreSQL connection string for LangGraph checkpointing without importing app.agent."""
    ckpt_url = os.getenv("CHECKPOINT_DB_URL", "").strip()
    if ckpt_url:
        return ckpt_url

    if os.getenv("USE_POSTGRES_CHECKPOINT", "false").lower() in ("true", "1", "yes"):
        db_url = os.getenv("DATABASE_URL", "").strip()
        if db_url:
            return db_url

        host = os.getenv("DB_HOST", "").strip()
        port = os.getenv("DB_PORT", "5432").strip()
        name = os.getenv("DB_NAME", "").strip()
        user = os.getenv("DB_USER", "").strip()
        password = os.getenv("DB_PASSWORD", "").strip()

        if host and name and user:
            if password:
                return f"postgresql://{user}:{password}@{host}:{port}/{name}"
            return f"postgresql://{user}@{host}:{port}/{name}"

    return None


def init_checkpoint_tables() -> bool:
    """Initializes LangGraph checkpoint tables in PostgreSQL idempotently without importing ChromaDB or models."""
    try:
        ckpt_url = get_checkpoint_db_url()
        if not ckpt_url:
            logger.info("PostgreSQL checkpointing is not configured. Skipping checkpoint table initialization.")
            return False

        # Fast non-blocking TCP socket check
        try:
            parsed = urlparse(ckpt_url)
            host = parsed.hostname or "localhost"
            port = parsed.port or 5432
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1.0)
            res = sock.connect_ex((host, port))
            sock.close()
            if res != 0:
                logger.warning("PostgreSQL server at target is not reachable on TCP port. Skipping checkpoint table init.")
                return False
        except Exception:
            return False

        from langgraph.checkpoint.postgres import PostgresSaver
        import psycopg

        conn = psycopg.connect(ckpt_url, autocommit=True, connect_timeout=3)
        checkpointer = PostgresSaver(conn)
        checkpointer.setup()
        conn.close()
        logger.info("LangGraph PostgreSQL checkpoint tables successfully initialized/verified.")
        return True
    except Exception as e:
        logger.warning(f"Error during LangGraph checkpoint table initialization: {e}")
        return False


def bootstrap_database(
    config: DatabaseConfig = DEFAULT_DB_CONFIG,
    seed_demo: bool = False,
    init_checkpoints: bool = True,
    only_seed_if_empty: bool = True,
) -> BootstrapResult:
    """Performs deterministic, idempotent bootstrap of database schemas.

    Args:
        config: Database connection configuration.
        seed_demo: If True, seeds enterprise demo records (default: False).
                   Can also be enabled via environment variable SEED_DEMO_DATA=1.
        init_checkpoints: If True, initializes LangGraph checkpoint tables (default: True).
        only_seed_if_empty: If True, prevents seeding if records already exist.

    Returns:
        BootstrapResult detailing actions performed.
    """
    logger.info("Starting database bootstrap...")

    # 1. Test connectivity
    if not test_connection(config):
        msg = f"Failed to connect to PostgreSQL database '{config.name}' at {config.host}:{config.port}."
        logger.error(msg)
        return BootstrapResult(
            connection_ok=False,
            schema_initialized=False,
            checkpoints_initialized=False,
            demo_seeded=False,
            message=msg,
        )

    # 2. Initialize business schema (idempotent CREATE TABLE IF NOT EXISTS)
    try:
        init_db(config)
        logger.info("Business relational schema successfully verified/initialized.")
    except Exception as e:
        msg = f"Failed to initialize business schema: {e}"
        logger.error(msg)
        return BootstrapResult(
            connection_ok=True,
            schema_initialized=False,
            checkpoints_initialized=False,
            demo_seeded=False,
            message=msg,
        )

    # 3. Initialize LangGraph checkpoint tables
    checkpoints_ok = False
    if init_checkpoints:
        checkpoints_ok = init_checkpoint_tables()

    # 4. Handle demo seeding (explicit opt-in only)
    should_seed = seed_demo or os.getenv("SEED_DEMO_DATA", "").lower() in ("1", "true", "yes")
    demo_seeded = False
    if should_seed:
        demo_seeded = seed_db(config, only_if_empty=only_seed_if_empty)
    else:
        logger.info("Demo data seeding not requested. Preserving existing database state.")

    return BootstrapResult(
        connection_ok=True,
        schema_initialized=True,
        checkpoints_initialized=checkpoints_ok,
        demo_seeded=demo_seeded,
        message="Database bootstrap completed successfully.",
    )


def main():
    """CLI entrypoint for database bootstrap (e.g. Render pre-deploy or container startup)."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    parser = argparse.ArgumentParser(description="Idempotent PostgreSQL bootstrap for Enterprise Support AI Agent.")
    parser.add_argument(
        "--seed-demo",
        action="store_true",
        default=os.getenv("SEED_DEMO_DATA", "").lower() in ("1", "true", "yes"),
        help="Seed enterprise demo records (employees, leave, travel). Default: False.",
    )
    parser.add_argument(
        "--force-seed",
        action="store_true",
        help="Force reseeding even if database already contains records.",
    )
    parser.add_argument(
        "--skip-checkpoints",
        action="store_true",
        help="Skip LangGraph checkpoint table initialization.",
    )

    args = parser.parse_args()

    res = bootstrap_database(
        seed_demo=args.seed_demo or args.force_seed,
        init_checkpoints=not args.skip_checkpoints,
        only_seed_if_empty=not args.force_seed,
    )

    if not res.connection_ok or not res.schema_initialized:
        print(f"BOOTSTRAP FAILED: {res.message}", file=sys.stderr)
        sys.exit(1)

    print(f"BOOTSTRAP SUCCESS: {res.message}")
    print(f" - Connection: OK")
    print(f" - Business Schema: OK")
    print(f" - Checkpoints: {'OK' if res.checkpoints_initialized else 'Skipped/Memory'}")
    print(f" - Demo Data Seeded: {res.demo_seeded}")
    sys.exit(0)


if __name__ == "__main__":
    main()
