"""In-Memory Conversational Session Storage for Enterprise Support AI Agent.

Provides thread-safe session isolation, message history persistence,
and lifecycle operations. Decoupled abstraction designed for seamless
future migration to persistent backends (Redis / PostgreSQL).
"""

import threading
from typing import Any


class InMemorySessionStore:
    """Thread-safe in-memory conversation session store."""

    def __init__(self) -> None:
        self._sessions: dict[str, list[dict[str, Any]]] = {}
        self._lock = threading.Lock()

    def get_session(self, session_id: str) -> list[dict[str, Any]]:
        """Retrieves a shallow copy of messages for a given session.

        Args:
            session_id: Unique conversation identifier.

        Returns:
            List of message dictionaries, or empty list if session does not exist.
        """
        with self._lock:
            messages = self._sessions.get(session_id, [])
            return [dict(msg) for msg in messages]

    def append_message(self, session_id: str, message: dict[str, Any]) -> None:
        """Appends a single message to a session history.

        Args:
            session_id: Unique conversation identifier.
            message: Message dictionary containing role, content, and optional metadata.
        """
        with self._lock:
            if session_id not in self._sessions:
                self._sessions[session_id] = []
            self._sessions[session_id].append(dict(message))

    def append_messages(self, session_id: str, messages: list[dict[str, Any]]) -> None:
        """Appends multiple messages to a session history.

        Args:
            session_id: Unique conversation identifier.
            messages: List of message dictionaries to append.
        """
        with self._lock:
            if session_id not in self._sessions:
                self._sessions[session_id] = []
            for msg in messages:
                self._sessions[session_id].append(dict(msg))

    def clear_session(self, session_id: str) -> bool:
        """Clears all conversation messages for a session while keeping the session entry.

        Args:
            session_id: Unique conversation identifier.

        Returns:
            True if session was found and cleared, False if session did not exist.
        """
        with self._lock:
            if session_id in self._sessions:
                self._sessions[session_id] = []
                return True
            return False

    def delete_session(self, session_id: str) -> bool:
        """Deletes a session and its entire history from the store.

        Args:
            session_id: Unique conversation identifier.

        Returns:
            True if session was deleted, False if session did not exist.
        """
        with self._lock:
            if session_id in self._sessions:
                del self._sessions[session_id]
                return True
            return False

    def has_session(self, session_id: str) -> bool:
        """Checks whether a session exists in the store."""
        with self._lock:
            return session_id in self._sessions

    def list_sessions(self) -> list[str]:
        """Returns a list of all active session IDs."""
        with self._lock:
            return list(self._sessions.keys())


# Default global in-memory session store instance
default_session_store = InMemorySessionStore()
