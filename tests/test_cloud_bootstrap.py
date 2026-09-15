"""Deterministic tests for Cloud Deployment Blueprint & Database Bootstrap (Phase 11 Task 2).

Verifies:
1. render.yaml syntax, service definitions, persistent disk configuration, and secret hygiene.
2. DatabaseConfig DATABASE_URL parsing and fallback handling.
3. Database bootstrap idempotency, safe schema creation, and demo data isolation.
4. Frontend configuration security (no private secrets exposed).
5. Existing local Docker Compose configuration preservation.
"""

import os
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

import yaml

from app.database.config import DatabaseConfig
from app.database.bootstrap import bootstrap_database, BootstrapResult
from app.database.seed import seed_db, is_database_seeded


class TestRenderBlueprint(unittest.TestCase):
    """Validates the structure, syntax, and security hygiene of render.yaml."""

    def setUp(self):
        self.repo_root = Path(__file__).resolve().parent.parent
        self.render_file = self.repo_root / "render.yaml"

    def test_render_yaml_exists_and_parses(self):
        """Verifies render.yaml exists and is valid YAML."""
        self.assertTrue(self.render_file.exists(), "render.yaml does not exist in repo root.")
        content = self.render_file.read_text(encoding="utf-8")
        data = yaml.safe_load(content)
        self.assertIsInstance(data, dict)
        self.assertIn("services", data)
        self.assertIn("databases", data)

    def test_database_definition(self):
        """Verifies managed PostgreSQL database specification."""
        content = self.render_file.read_text(encoding="utf-8")
        data = yaml.safe_load(content)
        dbs = data.get("databases", [])
        self.assertEqual(len(dbs), 1)
        db = dbs[0]
        self.assertEqual(db.get("name"), "enterprise-support-db")
        self.assertEqual(db.get("databaseName"), "enterprise_support")

    def test_backend_service_specification(self):
        """Verifies backend service has single instance and persistent disk."""
        content = self.render_file.read_text(encoding="utf-8")
        data = yaml.safe_load(content)
        services = {s["name"]: s for s in data.get("services", [])}
        self.assertIn("enterprise-support-backend", services)
        backend = services["enterprise-support-backend"]

        # Docker runtime
        self.assertEqual(backend.get("runtime"), "docker")
        self.assertEqual(backend.get("dockerfilePath"), "Dockerfile")

        # Crucial single-instance constraint for embedded ChromaDB SQLite
        self.assertEqual(backend.get("numInstances"), 1, "Backend must be strictly 1 instance for ChromaDB.")

        # Healthcheck
        self.assertEqual(backend.get("healthCheckPath"), "/health")

        # Persistent disk configuration
        disk = backend.get("disk", {})
        self.assertEqual(disk.get("mountPath"), "/app/data/chroma")
        self.assertGreaterEqual(disk.get("sizeGB", 0), 1)

        # Pre-deploy command for schema bootstrap
        self.assertIn("bootstrap", backend.get("preDeployCommand", ""))

    def test_secret_hygiene_in_render_blueprint(self):
        """Ensures NO real secrets or API keys are embedded in render.yaml."""
        content = self.render_file.read_text(encoding="utf-8")
        data = yaml.safe_load(content)

        raw_text = self.render_file.read_text(encoding="utf-8")
        self.assertNotIn("gsk_", raw_text, "Found Groq API key pattern in render.yaml!")
        self.assertNotIn("sk-proj-", raw_text, "Found OpenAI API key pattern in render.yaml!")

        services = {s["name"]: s for s in data.get("services", [])}
        backend = services["enterprise-support-backend"]
        env_vars = {e["key"]: e for e in backend.get("envVars", [])}

        # LLM_API_KEY and GROQ_API_KEY must have sync: false
        self.assertIn("LLM_API_KEY", env_vars)
        self.assertFalse(env_vars["LLM_API_KEY"].get("sync", True))
        self.assertIn("GROQ_API_KEY", env_vars)
        self.assertFalse(env_vars["GROQ_API_KEY"].get("sync", True))

        # DATABASE_URL must come from database reference, not hardcoded
        self.assertIn("DATABASE_URL", env_vars)
        self.assertIn("fromDatabase", env_vars["DATABASE_URL"])
        self.assertEqual(
            env_vars["DATABASE_URL"]["fromDatabase"]["property"],
            "connectionString",
        )

        # SEED_DEMO_DATA must default to 0
        self.assertIn("SEED_DEMO_DATA", env_vars)
        self.assertEqual(env_vars["SEED_DEMO_DATA"].get("value"), "0")

    def test_frontend_service_specification(self):
        """Verifies frontend service does not expose backend private secrets."""
        content = self.render_file.read_text(encoding="utf-8")
        data = yaml.safe_load(content)
        services = {s["name"]: s for s in data.get("services", [])}
        self.assertIn("enterprise-support-frontend", services)
        frontend = services["enterprise-support-frontend"]

        self.assertEqual(frontend.get("runtime"), "docker")
        self.assertEqual(frontend.get("healthCheckPath"), "/")

        env_keys = [e["key"] for e in frontend.get("envVars", [])]
        self.assertNotIn("LLM_API_KEY", env_keys)
        self.assertNotIn("GROQ_API_KEY", env_keys)
        self.assertNotIn("DATABASE_URL", env_keys)
        self.assertNotIn("DB_PASSWORD", env_keys)

        # NEXT_PUBLIC_API_BASE_URL should point to backend URL
        fe_env = {e["key"]: e.get("value") for e in frontend.get("envVars", [])}
        self.assertIn("NEXT_PUBLIC_API_BASE_URL", fe_env)
        self.assertTrue(
            "enterprise-support-backend" in fe_env["NEXT_PUBLIC_API_BASE_URL"]
            or fe_env["NEXT_PUBLIC_API_BASE_URL"].startswith("https://")
        )


class TestDatabaseConfigUrlParsing(unittest.TestCase):
    """Validates parsing of DATABASE_URL and fallback behaviors."""

    def test_database_url_parsing(self):
        """Verifies that setting DATABASE_URL overrides individual components."""
        test_url = "postgresql://myuser:mypassword@dbhost.internal:5433/custom_db?sslmode=require"
        with patch.dict(os.environ, {"DATABASE_URL": test_url}):
            cfg = DatabaseConfig()
            self.assertEqual(cfg.host, "dbhost.internal")
            self.assertEqual(cfg.port, 5433)
            self.assertEqual(cfg.name, "custom_db")
            self.assertEqual(cfg.user, "myuser")
            self.assertEqual(cfg.password, "mypassword")
            self.assertEqual(cfg.sslmode, "require")
            self.assertEqual(cfg.connection_kwargs["dbname"], "custom_db")

    def test_fallback_to_individual_params_when_no_url(self):
        """Verifies individual params are respected when DATABASE_URL is not set."""
        env_override = {
            "DATABASE_URL": "",
            "DB_HOST": "fallback.host",
            "DB_PORT": "5432",
            "DB_NAME": "fallback_db",
            "DB_USER": "fallback_user",
            "DB_PASSWORD": "fallback_password",
            "DB_SSLMODE": "prefer",
        }
        with patch.dict(os.environ, env_override):
            cfg = DatabaseConfig(
                host="fallback.host",
                port=5432,
                name="fallback_db",
                user="fallback_user",
                password="fallback_password",
                sslmode="prefer",
            )
            self.assertEqual(cfg.host, "fallback.host")
            self.assertEqual(cfg.name, "fallback_db")
            self.assertEqual(cfg.user, "fallback_user")


class TestDatabaseBootstrapDeterminism(unittest.TestCase):
    """Validates schema idempotency and safe separation of demo data seeding."""

    @patch("app.database.bootstrap.test_connection", return_value=True)
    @patch("app.database.bootstrap.init_db", return_value=True)
    @patch("app.database.bootstrap.init_checkpoint_tables", return_value=True)
    @patch("app.database.bootstrap.seed_db")
    def test_default_bootstrap_does_not_seed_demo_data(
        self,
        mock_seed,
        mock_ckpt,
        mock_init,
        mock_test,
    ):
        """Verifies standard production bootstrap does NOT trigger demo data seeding."""
        with patch.dict(os.environ, {"SEED_DEMO_DATA": "0"}):
            res = bootstrap_database(seed_demo=False)
            self.assertTrue(res.connection_ok)
            self.assertTrue(res.schema_initialized)
            self.assertFalse(res.demo_seeded, "Default bootstrap must NOT seed demo data.")
            mock_seed.assert_not_called()
            mock_init.assert_called_once()

    @patch("app.database.bootstrap.test_connection", return_value=True)
    @patch("app.database.bootstrap.init_db", return_value=True)
    @patch("app.database.bootstrap.init_checkpoint_tables", return_value=True)
    @patch("app.database.bootstrap.seed_db", return_value=True)
    def test_explicit_seed_request_triggers_seeding(
        self,
        mock_seed,
        mock_ckpt,
        mock_init,
        mock_test,
    ):
        """Verifies demo data is seeded ONLY when explicitly requested."""
        res = bootstrap_database(seed_demo=True, only_seed_if_empty=True)
        self.assertTrue(res.connection_ok)
        self.assertTrue(res.demo_seeded)
        mock_seed.assert_called_once_with(mock_init.call_args[0][0], only_if_empty=True)

    @patch("app.database.seed.is_database_seeded", return_value=True)
    @patch("app.database.seed.init_db", return_value=True)
    def test_seed_db_with_only_if_empty_skips_existing_data(self, mock_init, mock_is_seeded):
        """Verifies seed_db with only_if_empty=True preserves existing database rows."""
        cfg = DatabaseConfig()
        result = seed_db(config=cfg, only_if_empty=True)
        self.assertFalse(result, "Should skip seeding when database already contains data.")

    def test_bootstrap_has_no_chroma_or_torch_dependency(self):
        """Step 2 regression test: verifies bootstrap module does not load ChromaDB or ML models.
        
        Render persistent disks are NOT mounted during pre-deploy execution.
        Therefore python -m app.database.bootstrap must remain strictly PostgreSQL-only.
        """
        import sys
        # Check that importing app.database.bootstrap does not load chromadb, torch, or sentence_transformers
        forbidden = [
            m for m in sys.modules
            if any(k in m for k in ("chromadb", "torch", "sentence_transformers"))
        ]
        self.assertEqual(forbidden, [], f"Bootstrap module loaded forbidden ML/Chroma packages: {forbidden}")


class TestDockerComposePreservation(unittest.TestCase):
    """Verifies that cloud additions do not modify or break local Docker Compose."""

    def test_docker_compose_intact(self):
        """Verifies docker-compose.yml services, volumes, and ports remain intact."""
        repo_root = Path(__file__).resolve().parent.parent
        compose_file = repo_root / "docker-compose.yml"
        self.assertTrue(compose_file.exists())
        content = compose_file.read_text(encoding="utf-8")
        data = yaml.safe_load(content)

        services = data.get("services", {})
        self.assertIn("postgres", services)
        self.assertIn("backend", services)
        self.assertIn("frontend", services)

        volumes = data.get("volumes", {})
        self.assertIn("postgres_data", volumes)
        self.assertIn("chroma_data", volumes)

        networks = data.get("networks", {})
        self.assertIn("enterprise_network", networks)


if __name__ == "__main__":
    unittest.main()
