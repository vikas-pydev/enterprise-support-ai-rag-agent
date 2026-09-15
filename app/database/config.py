import os
from dataclasses import dataclass
from urllib.parse import urlparse, parse_qs
from dotenv import load_dotenv

load_dotenv()


@dataclass
class DatabaseConfig:
    """PostgreSQL connection configuration supporting individual parameters or DATABASE_URL."""
    host: str = os.getenv("DB_HOST", "localhost")
    port: int = int(os.getenv("DB_PORT", "5432"))
    name: str = os.getenv("DB_NAME", "enterprise_support")
    user: str = os.getenv("DB_USER", "postgres")
    password: str = os.getenv("DB_PASSWORD", "postgres")
    sslmode: str = os.getenv("DB_SSLMODE", "prefer")
    connect_timeout: int = int(os.getenv("DB_CONNECT_TIMEOUT", "5"))

    def __post_init__(self):
        # Allow DATABASE_URL to override individual connection settings if provided
        db_url = os.getenv("DATABASE_URL", "").strip()
        if db_url:
            self._apply_database_url(db_url)

    def _apply_database_url(self, db_url: str):
        """Parses a full PostgreSQL connection URL and sets internal fields."""
        try:
            parsed = urlparse(db_url)
            if parsed.hostname:
                self.host = parsed.hostname
            if parsed.port:
                self.port = parsed.port
            if parsed.path and parsed.path.lstrip("/"):
                self.name = parsed.path.lstrip("/")
            if parsed.username:
                self.user = parsed.username
            if parsed.password is not None:
                self.password = parsed.password
            query_params = parse_qs(parsed.query)
            if "sslmode" in query_params:
                self.sslmode = query_params["sslmode"][0]
        except Exception:
            pass

    @property
    def connection_kwargs(self) -> dict:
        return {
            "host": self.host,
            "port": self.port,
            "dbname": self.name,
            "user": self.user,
            "password": self.password,
            "sslmode": self.sslmode,
            "connect_timeout": self.connect_timeout,
        }

    @property
    def server_connection_kwargs(self) -> dict:
        """Connection kwargs targeting the default 'postgres' database (used for creating target DB)."""
        kwargs = self.connection_kwargs.copy()
        kwargs["dbname"] = "postgres"
        return kwargs


DEFAULT_DB_CONFIG = DatabaseConfig()
