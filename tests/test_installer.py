"""Installer regression checks without a Docker daemon or runtime data.

Only temporary copies of the deployment files are modified. Docker and HTTP
clients are inert stand-ins; no containers or network listeners are created.
"""

import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

REPOSITORY = Path(__file__).resolve().parents[1]


class InstallerTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(prefix="reto4v-installer-test-")
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        (self.root / "scripts").mkdir()
        (self.root / "bin").mkdir()
        for source in ("compose.yaml", ".env.example", "scripts/install.sh", "scripts/restore.sh"):
            shutil.copyfile(REPOSITORY / source, self.root / source)
        self.log = self.root / "calls.log"
        docker = self.root / "bin/docker"
        docker.write_text(
            "#!/usr/bin/env bash\n"
            "printf 'docker %s\\n' \"$*\" >> \"$RETO4V_TEST_LOG\"\n"
            "if [[ \"${RETO4V_FAIL_SEED:-0}\" == 1 && \"$*\" == *'seed_python'* ]]; then exit 17; fi\n"
            "case \"$*\" in\n"
            "  *'up --help'*) echo --wait ;;\n"
            "  *'shell -c'*) echo True ;;\n"
            "  *pg_restore*) cat >/dev/null ;;\n"
            "esac\nexit 0\n",
            encoding="utf8",
        )
        docker.chmod(0o755)
        for name in ("curl", "wget"):
            client = self.root / "bin" / name
            client.write_text(
                f"#!/usr/bin/env bash\nprintf '{name} %s\\n' \"$*\" >> \"$RETO4V_TEST_LOG\"\nexit 0\n",
                encoding="utf8",
            )
            client.chmod(0o755)
        self.environment = {
            **os.environ,
            "PATH": f"{self.root / 'bin'}:{os.environ['PATH']}",
            "RETO4V_TEST_LOG": str(self.log),
        }
        # Never inherit Compose/application settings from a developer's shell.
        for key in list(self.environment):
            if key.startswith(("COMPOSE_", "DJANGO_", "POSTGRES_", "APP_", "CADDY_")):
                self.environment.pop(key)

    def install(self, *args, success=True):
        result = subprocess.run(
            ["bash", str(self.root / "scripts/install.sh"), *args],
            cwd=self.root,
            env=self.environment,
            text=True,
            capture_output=True,
            timeout=20,
            check=False,
        )
        if success:
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        else:
            self.assertNotEqual(result.returncode, 0)
        return result

    def config(self):
        return {
            key.strip(): value.strip()
            for line in (self.root / ".env").read_text().splitlines()
            if line and not line.startswith("#") and "=" in line
            for key, value in [line.split("=", 1)]
        }

    def test_direct_install_generates_secrets_and_preserves_them(self):
        first = self.install("--host", "192.168.20.10", "--port", "8080", "--skip-admin")
        before = self.config()
        self.assertEqual(before["APP_PORT"], "8080")
        self.assertEqual(before["APP_BIND_IP"], "0.0.0.0")
        self.assertIn("192.168.20.10", before["DJANGO_ALLOWED_HOSTS"])
        self.assertEqual(before["DJANGO_CSRF_TRUSTED_ORIGINS"], "http://192.168.20.10:8080")
        self.assertNotEqual(before["POSTGRES_PASSWORD"], before["DJANGO_SECRET_KEY"])
        for key in ("POSTGRES_PASSWORD", "DJANGO_SECRET_KEY"):
            self.assertGreaterEqual(len(before[key]), 32)
            self.assertNotIn("CHANGE_ME", before[key])
            self.assertNotIn(before[key], first.stdout + first.stderr)
        self.assertEqual((self.root / ".env").stat().st_mode & 0o777, 0o600)
        self.install("--no-build", "--skip-admin")
        after = self.config()
        for key in ("POSTGRES_PASSWORD", "DJANGO_SECRET_KEY", "DJANGO_ALLOWED_HOSTS", "APP_PORT", "APP_BIND_IP", "DJANGO_CSRF_TRUSTED_ORIGINS"):
            self.assertEqual(after[key], before[key], key)
        self.assertNotIn("down", self.log.read_text())

    def test_tls_repeated_install_keeps_proxy_and_secure_cookies(self):
        self.install("--host", "reto4v.instituto.lan", "--port", "8443", "--tls", "--skip-admin")
        before = self.config()
        self.assertEqual(before["APP_BIND_IP"], "127.0.0.1")
        self.assertEqual(before["APP_PORT"], "8000")
        self.assertEqual(before["CADDY_HTTP_PORT"], "8443")
        self.assertEqual(before["DJANGO_SESSION_COOKIE_SECURE"], "1")
        self.assertEqual(before["DJANGO_CSRF_COOKIE_SECURE"], "1")
        self.assertEqual(before["DJANGO_CSRF_TRUSTED_ORIGINS"], "https://reto4v.instituto.lan:8443")
        self.log.write_text("")
        self.install("--no-build", "--skip-admin")
        after = self.config()
        for key in ("APP_PORT", "APP_BIND_IP", "CADDY_HTTP_PORT", "CADDYFILE", "CADDY_SITE_ADDRESS", "DJANGO_SESSION_COOKIE_SECURE", "DJANGO_CSRF_COOKIE_SECURE", "DJANGO_CSRF_TRUSTED_ORIGINS"):
            self.assertEqual(after[key], before[key], key)
        log = self.log.read_text()
        self.assertTrue("--profile proxy" in log or after.get("COMPOSE_PROFILES") == "proxy")
        self.assertNotIn("http://127.0.0.1:8000", log)

    def test_proxy_default_port_matches_csrf_and_health_url(self):
        self.install("--host", "reto4v.instituto.lan", "--proxy", "--skip-admin")
        config = self.config()
        port = config["CADDY_HTTP_PORT"]
        self.assertEqual(config["DJANGO_CSRF_TRUSTED_ORIGINS"], f"http://reto4v.instituto.lan:{port}")
        self.assertIn(f":{port}/health/", config["APP_URL"])

    def test_seed_python_uses_owner_and_independent_cohort(self):
        self.install(
            "--no-build", "--skip-admin", "--seed-python",
            "--owner", "profesor", "--python-cohort", "2DAM",
        )
        calls = self.log.read_text().splitlines()
        python_calls = [call for call in calls if "manage.py seed_python" in call]
        self.assertEqual(len(python_calls), 1)
        self.assertIn("--owner profesor --cohort 2DAM", python_calls[0])
        self.assertNotIn("seed_bash", self.log.read_text())

    def test_seed_bash_and_python_keep_legacy_cohort_and_run_in_order(self):
        self.install(
            "--no-build", "--skip-admin", "--seed-bash", "--seed-python",
            "--owner", "profesor", "--cohort", "2ASIR",
            "--python-cohort", "2DAM",
        )
        calls = self.log.read_text().splitlines()
        bash_index = next(i for i, call in enumerate(calls) if "manage.py seed_bash" in call)
        python_index = next(i for i, call in enumerate(calls) if "manage.py seed_python" in call)
        self.assertLess(bash_index, python_index)
        self.assertIn("--owner profesor --cohort 2ASIR", calls[bash_index])
        self.assertIn("--owner profesor --cohort 2DAM", calls[python_index])

    def test_bash_cohort_is_explicit_alias_for_legacy_cohort(self):
        self.install(
            "--no-build", "--skip-admin", "--seed-bash",
            "--owner", "profesor", "--bash-cohort", "2ASIR-B",
        )
        calls = self.log.read_text().splitlines()
        bash_call = next(call for call in calls if "manage.py seed_bash" in call)
        self.assertIn("--owner profesor --cohort 2ASIR-B", bash_call)

    def test_missing_bash_cohort_does_not_consume_next_option(self):
        result = self.install(
            "--seed-bash", "--owner", "profesor", "--cohort", "--skip-admin",
            success=False,
        )
        self.assertIn("Falta el valor de --cohort", result.stderr)
        self.assertFalse(self.log.exists())
        self.assertFalse((self.root / ".env").exists())

    def test_missing_python_cohort_does_not_consume_next_option(self):
        result = self.install(
            "--seed-python", "--owner", "profesor",
            "--python-cohort", "--skip-admin", success=False,
        )
        self.assertIn("Falta el valor de --python-cohort", result.stderr)
        self.assertFalse(self.log.exists())
        self.assertFalse((self.root / ".env").exists())

    def test_unused_empty_python_cohort_does_not_block_bash_seed(self):
        self.install(
            "--no-build", "--skip-admin", "--seed-bash", "--owner", "profesor",
            "--python-cohort", "",
        )
        log = self.log.read_text()
        self.assertIn("manage.py seed_bash --owner profesor --cohort 2ASIR", log)
        self.assertNotIn("seed_python", log)

    def test_unused_empty_bash_cohort_does_not_block_python_seed(self):
        self.install(
            "--no-build", "--skip-admin", "--seed-python", "--owner", "profesor",
            "--cohort", "",
        )
        log = self.log.read_text()
        self.assertIn("manage.py seed_python --owner profesor --cohort 2DAM", log)
        self.assertNotIn("seed_bash", log)

    def test_seed_requires_owner_before_starting_services(self):
        result = self.install("--no-build", "--skip-admin", "--seed-python", success=False)
        self.assertIn("requieren --owner", result.stderr)
        self.assertFalse(self.log.exists())
        self.assertFalse((self.root / ".env").exists())

    def test_seed_python_error_is_returned_to_operator(self):
        self.environment["RETO4V_FAIL_SEED"] = "1"
        result = self.install(
            "--no-build", "--skip-admin", "--seed-python",
            "--owner", "profesor", success=False,
        )
        self.assertIn("No se pudo ejecutar seed_python", result.stderr)

    def test_repeating_python_seed_does_not_stop_or_remove_data(self):
        self.install(
            "--no-build", "--skip-admin", "--seed-python",
            "--owner", "profesor", "--python-cohort", "2DAM",
        )
        self.log.write_text("")
        self.install(
            "--no-build", "--skip-admin", "--seed-python",
            "--owner", "profesor", "--python-cohort", "2DAM",
        )
        log = self.log.read_text()
        self.assertIn("manage.py seed_python --owner profesor --cohort 2DAM", log)
        self.assertNotIn("down", log)

    def test_invalid_host_is_rejected_before_env_is_created(self):
        self.install("--host", "https://wrong.example/path", success=False)
        self.assertFalse((self.root / ".env").exists())

    def test_invalid_port_is_rejected_before_env_is_created(self):
        self.install("--port", "70000", success=False)
        self.assertFalse((self.root / ".env").exists())

    def test_restore_restarts_the_configured_tls_proxy(self):
        self.install("--host", "reto4v.instituto.lan", "--port", "8443", "--tls", "--skip-admin")
        dump = self.root / "synthetic.dump"
        dump.write_text("Mock data consumed only by the inert Docker stand-in.")
        self.log.write_text("")
        result = subprocess.run(
            ["bash", str(self.root / "scripts/restore.sh"), str(dump)],
            cwd=self.root,
            env={**self.environment, "RESTORE_CONFIRM": "YES"},
            text=True, capture_output=True, timeout=20, check=False,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        log = self.log.read_text()
        self.assertIn("stop web caddy", log)
        self.assertIn("up -d web", log)
        self.assertIn("--profile proxy up -d caddy", log)

    def test_restore_requires_explicit_confirmation(self):
        environment = {**self.environment}
        environment.pop("RESTORE_CONFIRM", None)
        result = subprocess.run(
            ["bash", str(self.root / "scripts/restore.sh"), "not-a-real-dump"],
            cwd=self.root, env=environment,
            text=True, capture_output=True, timeout=20, check=False,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(self.log.exists())


if __name__ == "__main__":
    unittest.main()
