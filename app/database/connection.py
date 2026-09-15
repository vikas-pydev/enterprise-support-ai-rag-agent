import contextlib
try:
    import psycopg2
    from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
except ImportError:
    psycopg2 = None
    ISOLATION_LEVEL_AUTOCOMMIT = None

from app.database.config import DatabaseConfig, DEFAULT_DB_CONFIG
from app.database.exceptions import DatabaseError


def test_connection(config: DatabaseConfig = DEFAULT_DB_CONFIG) -> bool:
    """Test whether a connection can be established to the target database."""
    if psycopg2 is None:
        return False
    try:
        with get_db_connection(config) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1;")
                res = cur.fetchone()
                return res == (1,)
    except Exception:
        return False


def ensure_database_exists(config: DatabaseConfig = DEFAULT_DB_CONFIG) -> bool:
    """Ensure the target PostgreSQL database exists; create it if missing.

    First checks if target database is already accessible (standard for managed cloud databases).
    If not accessible, connects to the server-level 'postgres' maintenance database to check
    and create the application database.
    """
    if psycopg2 is None:
        return False
    # If connection to target database already works, avoid connecting to maintenance database
    if test_connection(config):
        return True
    try:
        conn = psycopg2.connect(**config.server_connection_kwargs)
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        with conn.cursor() as cur:
            cur.execute(
                "SELECT 1 FROM pg_database WHERE datname = %s;",
                (config.name,),
            )
            exists = cur.fetchone()
            if not exists:
                cur.execute(f'CREATE DATABASE "{config.name}";')
        conn.close()
        return True
    except Exception as e:
        print(f"[DB Warning] Could not ensure database '{config.name}' exists: {e}")
        return False


@contextlib.contextmanager
def get_db_connection(config: DatabaseConfig = DEFAULT_DB_CONFIG):
    """Context manager yielding an active database connection with autocommit/transaction handling."""
    if psycopg2 is None:
        raise DatabaseError("psycopg2 is not installed. Database connection unavailable.")
    conn = psycopg2.connect(**config.connection_kwargs)
    try:
        yield conn
    finally:
        conn.close()
