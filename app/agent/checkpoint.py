"""LangGraph Checkpointing & Durable Workflow State Module.

Provides official PostgreSQL-backed checkpointer (PostgresSaver) with
resilient in-memory fallback (MemorySaver), thread/session isolation,
durable Human-in-the-Loop (HITL) approval pause/resume state management,
and clean separation from application business tables.
"""

import os
import re
import socket
import logging
import uuid
from typing import Any
from urllib.parse import urlparse
from dotenv import load_dotenv

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import MemorySaver

logger = logging.getLogger(__name__)

load_dotenv()

# Global default checkpointer instance
_DEFAULT_CHECKPOINTER: BaseCheckpointSaver | None = None


def is_postgres_accessible(conn_string: str, timeout_sec: float = 1.0) -> bool:
    """Fast non-blocking TCP socket check to verify PostgreSQL host/port is reachable."""
    try:
        parsed = urlparse(conn_string)
        host = parsed.hostname or "localhost"
        port = parsed.port or 5432
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout_sec)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except Exception:
        return False


def get_checkpoint_db_url() -> str | None:
    """Resolves the PostgreSQL connection string for LangGraph checkpointing if configured.

    Checks:
    1. CHECKPOINT_DB_URL (dedicated checkpoint DB URL)
    2. DATABASE_URL / standard params if USE_POSTGRES_CHECKPOINT=true
    """
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


def mask_connection_string(conn_string: str) -> str:
    """Masks database passwords in connection URLs for safe logging."""
    if not conn_string:
        return ""
    try:
        # Regex pattern matching ://<user>:<password>@<host...> handling literal @ in passwords
        masked = re.sub(r"://([^:@/]+):(.*)@([^/@:]+(?::\d+)?(?:/.*)?$)", r"://\1:***@\3", conn_string)
        if masked != conn_string:
            return masked

        parsed = urlparse(conn_string)
        if parsed.password:
            netloc = parsed.netloc.replace(f":{parsed.password}@", ":***@")
            return parsed._replace(netloc=netloc).geturl()
        return conn_string
    except Exception:
        return "<connection_string>"


def create_postgres_checkpointer(
    conn_string: str,
    connect_timeout: int = 2,
) -> BaseCheckpointSaver | None:
    """Attempts to initialize and setup a PostgresSaver instance.

    Calls checkpointer.setup() to ensure checkpoint persistence tables
    ('checkpoints', 'checkpoint_blobs', 'checkpoint_writes') exist.
    """
    masked_url = mask_connection_string(conn_string)
    if not is_postgres_accessible(conn_string, timeout_sec=1.0):
        logger.warning(
            "PostgreSQL server at target '%s' is not reachable on TCP port. Falling back to MemorySaver.",
            masked_url,
        )
        return None

    try:
        from langgraph.checkpoint.postgres import PostgresSaver
        import psycopg

        conn = psycopg.connect(conn_string, autocommit=True, connect_timeout=connect_timeout)
        checkpointer = PostgresSaver(conn)
        checkpointer.setup()
        logger.info("Successfully initialized PostgreSQL LangGraph checkpointer for '%s'.", masked_url)
        return checkpointer
    except Exception as e:
        logger.warning(
            "Failed to initialize PostgreSQL checkpointer: %s. Falling back to MemorySaver.",
            e,
        )
        return None


def create_checkpointer(
    conn_string: str | None = None,
    use_postgres_if_available: bool = True,
) -> BaseCheckpointSaver:
    """Factory creating a LangGraph checkpointer (PostgresSaver when configured & reachable, else MemorySaver).

    Args:
        conn_string: Optional explicit PostgreSQL connection URL.
        use_postgres_if_available: If True, attempts PostgresSaver when DB is configured.

    Returns:
        Configured BaseCheckpointSaver instance (PostgresSaver or MemorySaver).
    """
    if use_postgres_if_available:
        target_url = conn_string or get_checkpoint_db_url()
        if target_url:
            pg_saver = create_postgres_checkpointer(target_url)
            if pg_saver is not None:
                return pg_saver

    logger.info("Using in-memory LangGraph checkpointer (MemorySaver).")
    return MemorySaver()


def get_default_checkpointer() -> BaseCheckpointSaver:
    """Retrieves or initializes the global default checkpointer singleton."""
    global _DEFAULT_CHECKPOINTER
    if _DEFAULT_CHECKPOINTER is None:
        _DEFAULT_CHECKPOINTER = create_checkpointer()
    return _DEFAULT_CHECKPOINTER


def set_default_checkpointer(checkpointer: BaseCheckpointSaver) -> None:
    """Sets the global default checkpointer (useful for testing or switching backends)."""
    global _DEFAULT_CHECKPOINTER
    _DEFAULT_CHECKPOINTER = checkpointer


def reset_default_checkpointer() -> None:
    """Resets the global checkpointer singleton to None so a new instance is created on next call."""
    global _DEFAULT_CHECKPOINTER
    _DEFAULT_CHECKPOINTER = None


def get_thread_id_for_session(session_id: str | None) -> str:
    """Maps an application session_id to a stable LangGraph thread_id.

    If session_id is None or empty, generates an ephemeral unique thread ID.
    """
    if session_id and str(session_id).strip():
        return str(session_id).strip()
    return f"thread_{uuid.uuid4().hex[:12]}"


def build_thread_config(thread_id: str) -> dict[str, Any]:
    """Constructs the standard LangGraph runnable config dict for a given thread_id."""
    return {"configurable": {"thread_id": str(thread_id).strip()}}


def format_approval_id(thread_id: str) -> str:
    """Generates a structured, deterministic approval identifier embedding the thread ID.

    Format: appr_<short_random_token>_<thread_id>
    This allows O(1) thread identity resolution on resume while remaining unique.
    """
    token = uuid.uuid4().hex[:8]
    clean_thread = str(thread_id).strip()
    return f"appr_{token}_{clean_thread}"


def resolve_thread_from_approval_id(
    approval_id: str,
    checkpointer: BaseCheckpointSaver | None = None,
) -> str | None:
    """Resolves the LangGraph thread_id associated with a given approval_id.

    Resolution strategy:
    1. Check for standard formatted approval_id (appr_<token>_<thread_id> or appr_<thread_id>).
    2. If checkpointer is provided, scan checkpoints for matching approval_id in state channel_values.
    """
    if not approval_id or not str(approval_id).strip():
        return None

    clean_appr = str(approval_id).strip()

    # 1. Check formatted pattern: appr_<token>_<thread_id>
    if clean_appr.startswith("appr_"):
        parts = clean_appr.split("_", 2)
        if len(parts) == 3 and parts[2]:
            candidate_thread = parts[2]
            if checkpointer is not None:
                try:
                    cfg = build_thread_config(candidate_thread)
                    state_tuple = checkpointer.get_tuple(cfg)
                    if state_tuple is not None:
                        return candidate_thread
                except Exception:
                    pass
            else:
                return candidate_thread
        elif len(parts) == 2 and parts[1]:
            candidate_thread = parts[1]
            if checkpointer is not None:
                try:
                    cfg = build_thread_config(candidate_thread)
                    state_tuple = checkpointer.get_tuple(cfg)
                    if state_tuple is not None:
                        return candidate_thread
                except Exception:
                    pass
            else:
                return candidate_thread

    # 2. Checkpointer checkpoint scan fallback
    target_checkpointer = checkpointer or get_default_checkpointer()
    try:
        for cp in target_checkpointer.list(None):
            cfg = getattr(cp, "config", {})
            config_dict = cfg.get("configurable", {}) if isinstance(cfg, dict) else {}
            thread_id = config_dict.get("thread_id")
            channel_vals = getattr(cp, "checkpoint", {}).get("channel_values", {})
            if isinstance(channel_vals, dict) and channel_vals.get("approval_id") == clean_appr:
                return thread_id
    except Exception as e:
        logger.warning("Error searching checkpointer for approval_id '%s': %s", clean_appr, e)

    return None


def get_thread_state(checkpointer: BaseCheckpointSaver, thread_id: str) -> dict[str, Any] | None:
    """Retrieves the latest checkpoint channel_values state for a given thread_id."""
    try:
        cfg = build_thread_config(thread_id)
        state_tuple = checkpointer.get_tuple(cfg)
        if state_tuple and getattr(state_tuple, "checkpoint", None):
            return state_tuple.checkpoint.get("channel_values")
    except Exception as e:
        logger.warning("Error getting thread state for '%s': %s", thread_id, e)
    return None


def delete_thread_checkpoints(checkpointer: BaseCheckpointSaver, thread_id: str) -> bool:
    """Deletes or clears all checkpoints associated with a given thread_id."""
    if not checkpointer or not thread_id:
        return False
    clean_thread = str(thread_id).strip()
    if not clean_thread:
        return False
    try:
        try:
            from app.agent.multi_agent import cleanup_pending_approvals_for_thread
            cleanup_pending_approvals_for_thread(clean_thread)
        except Exception:
            pass

        if hasattr(checkpointer, "delete_thread"):
            checkpointer.delete_thread(clean_thread)
            return True
        # For MemorySaver and dictionary-backed checkpointers
        if hasattr(checkpointer, "storage") and isinstance(checkpointer.storage, dict):
            keys_to_remove = [k for k in list(checkpointer.storage.keys()) if (k == clean_thread or (isinstance(k, tuple) and k[0] == clean_thread))]
            for k in keys_to_remove:
                checkpointer.storage.pop(k, None)
            if hasattr(checkpointer, "writes") and isinstance(checkpointer.writes, dict):
                w_keys = [k for k in list(checkpointer.writes.keys()) if (k == clean_thread or (isinstance(k, tuple) and k[0] == clean_thread))]
                for k in w_keys:
                    checkpointer.writes.pop(k, None)
            if hasattr(checkpointer, "blobs") and isinstance(checkpointer.blobs, dict):
                b_keys = [k for k in list(checkpointer.blobs.keys()) if (k == clean_thread or (isinstance(k, tuple) and k[0] == clean_thread))]
                for k in b_keys:
                    checkpointer.blobs.pop(k, None)
            return True
    except Exception as e:
        logger.warning("Error deleting checkpoints for thread '%s': %s", clean_thread, e)
    return False
