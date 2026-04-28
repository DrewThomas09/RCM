"""Test the App-Service deploy-readiness behaviors landed in cycle 10.

These pin the small operational guarantees needed for a clean
Azure App Service deploy — distinct from the Docker-VM deploy
covered by ``test_azure_deploy.py``:

- ``LOG_LEVEL`` env var configures the rcm_mc logger.
- ``demo.py`` auto-binds ``0.0.0.0`` when Azure App Service env
  vars (WEBSITE_HOSTNAME / WEBSITES_PORT) are present.
- ``/static/*`` responses carry ``Cache-Control`` so Azure CDN /
  browser cache spare the origin on every page load.
- Session + CSRF cookies set the right flag posture (HttpOnly,
  SameSite=Lax, Secure-only-on-HTTPS).

Each test exercises real code — no mocks for our own modules.
"""
from __future__ import annotations

import importlib
import logging
import os
import socket
import tempfile
import threading
import time
import unittest
import urllib.request
from contextlib import contextmanager


@contextmanager
def _env(**kwargs):
    """Temporarily set env vars; restore exact prior state on exit."""
    snapshot = {k: os.environ.get(k) for k in kwargs}
    try:
        for k, v in kwargs.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        yield
    finally:
        for k, v in snapshot.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


class LogLevelEnvTests(unittest.TestCase):
    """Reload rcm_mc.infra.logger with various LOG_LEVEL values."""

    def _reload_with(self, env_value):
        with _env(LOG_LEVEL=env_value):
            existing = logging.getLogger("rcm_mc")
            existing.handlers.clear()
            mod = importlib.reload(
                importlib.import_module("rcm_mc.infra.logger"),
            )
            return mod.logger.level

    def test_default_level_is_info(self):
        self.assertEqual(self._reload_with(None), logging.INFO)

    def test_named_level_debug(self):
        self.assertEqual(self._reload_with("DEBUG"), logging.DEBUG)

    def test_named_level_warning(self):
        self.assertEqual(self._reload_with("WARNING"), logging.WARNING)

    def test_named_level_lowercase_accepted(self):
        self.assertEqual(self._reload_with("error"), logging.ERROR)

    def test_numeric_level_accepted(self):
        # Deployment templates may pass integer levels.
        self.assertEqual(self._reload_with("30"), logging.WARNING)

    def test_unknown_level_falls_back_to_info(self):
        # Garbage env shouldn't crash boot or mute everything.
        self.assertEqual(self._reload_with("BOGUS"), logging.INFO)


class AzureHostDetectionTests(unittest.TestCase):
    """demo.py auto-binds 0.0.0.0 when Azure App Service env present."""

    def _reload_demo(self):
        import sys
        sys.modules.pop("demo", None)
        # demo.py lives at the project root next to rcm_mc/.
        proj_root = os.path.dirname(
            os.path.dirname(os.path.abspath(
                __import__("rcm_mc").__file__,
            )),
        )
        if proj_root not in sys.path:
            sys.path.insert(0, proj_root)
        return importlib.import_module("demo")

    def test_local_default_binds_loopback(self):
        with _env(
            RCM_MC_HOST=None,
            WEBSITE_HOSTNAME=None,
            WEBSITES_PORT=None,
            PORT=None,
        ):
            demo = self._reload_demo()
            self.assertEqual(demo.HOST, "127.0.0.1")

    def test_azure_website_hostname_triggers_bind_all(self):
        with _env(
            RCM_MC_HOST=None,
            WEBSITE_HOSTNAME="rcm-mc.azurewebsites.net",
            WEBSITES_PORT=None,
        ):
            demo = self._reload_demo()
            self.assertEqual(demo.HOST, "0.0.0.0")

    def test_azure_websites_port_triggers_bind_all(self):
        with _env(
            RCM_MC_HOST=None,
            WEBSITE_HOSTNAME=None,
            WEBSITES_PORT="8000",
        ):
            demo = self._reload_demo()
            self.assertEqual(demo.HOST, "0.0.0.0")

    def test_explicit_rcm_mc_host_overrides_azure_default(self):
        with _env(
            RCM_MC_HOST="10.0.0.5",
            WEBSITE_HOSTNAME="rcm-mc.azurewebsites.net",
        ):
            demo = self._reload_demo()
            self.assertEqual(demo.HOST, "10.0.0.5")


class StaticCacheControlTests(unittest.TestCase):
    """/static/* responses carry Cache-Control for CDN friendliness."""

    def _start(self, tmp):
        from rcm_mc.server import build_server
        s = socket.socket()
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
        s.close()
        server, _ = build_server(
            port=port, db_path=os.path.join(tmp, "p.db"),
        )
        t = threading.Thread(target=server.serve_forever, daemon=True)
        t.start()
        time.sleep(0.05)
        return server, port

    def test_chartis_tokens_carries_cache_control(self):
        with tempfile.TemporaryDirectory() as tmp:
            server, port = self._start(tmp)
            try:
                with urllib.request.urlopen(
                    f"http://127.0.0.1:{port}/static/chartis_tokens.css"
                ) as r:
                    cc = r.headers.get("Cache-Control") or ""
                    self.assertIn("max-age=", cc)
                    self.assertIn("public", cc)
            finally:
                server.shutdown(); server.server_close()


class SessionCookieFlagsTests(unittest.TestCase):
    """Login/logout flows set cookies with the right flag posture."""

    def _start(self, tmp):
        from rcm_mc.auth.auth import create_user
        from rcm_mc.portfolio.store import PortfolioStore
        from rcm_mc.server import build_server
        store = PortfolioStore(os.path.join(tmp, "p.db"))
        create_user(store, "alice", "AlicePass!1", role="admin")
        s = socket.socket()
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
        s.close()
        server, _ = build_server(
            port=port, db_path=os.path.join(tmp, "p.db"),
        )
        t = threading.Thread(target=server.serve_forever, daemon=True)
        t.start()
        time.sleep(0.05)
        return server, port

    def _login(self, port):
        import urllib.parse
        body = urllib.parse.urlencode({
            "username": "alice", "password": "AlicePass!1",
        }).encode()
        req = urllib.request.Request(
            f"http://127.0.0.1:{port}/api/login",
            data=body,
            method="POST",
            headers={"Accept": "application/json"},
        )
        with urllib.request.urlopen(req) as r:
            cookies = r.headers.get_all("Set-Cookie") or []
            return r.status, cookies

    def test_session_cookie_has_httponly_and_samesite(self):
        with tempfile.TemporaryDirectory() as tmp:
            server, port = self._start(tmp)
            try:
                _, cookies = self._login(port)
                session = next(
                    (c for c in cookies if c.startswith("rcm_session=")),
                    None,
                )
                self.assertIsNotNone(session, "rcm_session cookie missing")
                self.assertIn("HttpOnly", session)
                self.assertIn("SameSite=Lax", session)
            finally:
                server.shutdown(); server.server_close()

    def test_csrf_cookie_has_samesite_but_no_httponly(self):
        # CSRF cookie is intentionally non-HttpOnly so the CSRF
        # patching JS can read it; SameSite must still be set.
        with tempfile.TemporaryDirectory() as tmp:
            server, port = self._start(tmp)
            try:
                _, cookies = self._login(port)
                csrf = next(
                    (c for c in cookies if c.startswith("rcm_csrf=")),
                    None,
                )
                self.assertIsNotNone(csrf, "rcm_csrf cookie missing")
                self.assertNotIn("HttpOnly", csrf)
                self.assertIn("SameSite=Lax", csrf)
            finally:
                server.shutdown(); server.server_close()

    def test_no_secure_flag_on_plain_http(self):
        # On plain HTTP (local dev), Secure must not be set or the
        # browser would reject the cookie. Production HTTPS comes
        # via X-Forwarded-Proto and is exercised separately.
        with tempfile.TemporaryDirectory() as tmp:
            server, port = self._start(tmp)
            try:
                _, cookies = self._login(port)
                for c in cookies:
                    self.assertNotIn(
                        "; Secure", c,
                        f"Secure flag should not be set on plain HTTP: {c}",
                    )
            finally:
                server.shutdown(); server.server_close()


class CSRFSecretEnvTests(unittest.TestCase):
    """RCM_MC_CSRF_SECRET env var sources the CSRF HMAC secret.

    Lets Azure App Service Configuration persist the secret across
    container restarts so partners stay logged in across deploys.
    Documented Phase-3 limitation in CLAUDE.md is that sessions
    invalidate on restart in the no-env mode; this test class pins
    the env-override path that lifts that limitation.
    """

    def _resolve(self):
        # Re-import the resolver each call so it re-reads env state.
        import importlib
        import sys
        sys.modules.pop("rcm_mc.server", None)
        # The resolver itself doesn't depend on the rest of server.py,
        # but it's defined in that module. Importing the module is
        # cheap (already-resolved imports are cached) and gives us
        # the real production code path.
        from rcm_mc.server import _resolve_csrf_secret
        return _resolve_csrf_secret()

    def test_no_env_returns_random_32_bytes(self):
        with _env(RCM_MC_CSRF_SECRET=None):
            secret = self._resolve()
            self.assertEqual(len(secret), 32)
            # A second call returns a different secret (randomness).
            self.assertNotEqual(secret, self._resolve())

    def test_valid_env_value_used_verbatim(self):
        good = "a" * 48
        with _env(RCM_MC_CSRF_SECRET=good):
            secret = self._resolve()
            self.assertEqual(secret, good.encode("utf-8"))

    def test_too_short_env_falls_back_to_random(self):
        # The fallback is silent at the test level (warning goes to
        # stderr) — the key invariant is that a weak env doesn't
        # weaken the HMAC.
        with _env(RCM_MC_CSRF_SECRET="too-short"):
            secret = self._resolve()
            # Random fallback is 32 bytes
            self.assertEqual(len(secret), 32)
            self.assertNotEqual(secret, b"too-short")

    def test_minimum_length_boundary(self):
        # Exactly 32 chars must be accepted
        boundary = "x" * 32
        with _env(RCM_MC_CSRF_SECRET=boundary):
            secret = self._resolve()
            self.assertEqual(secret, boundary.encode("utf-8"))


class AzureManifestTests(unittest.TestCase):
    """deploy/azure-app-service.json carries every required env var."""

    def _load_manifest(self):
        import json
        import pathlib
        here = pathlib.Path(__file__).parent.parent
        manifest_path = here / "deploy" / "azure-app-service.json"
        with manifest_path.open() as f:
            return json.load(f)

    def test_manifest_is_valid_json_array(self):
        manifest = self._load_manifest()
        self.assertIsInstance(manifest, list)
        self.assertGreater(len(manifest), 0)

    def test_each_entry_has_required_keys(self):
        manifest = self._load_manifest()
        for entry in manifest:
            self.assertIn("name", entry)
            self.assertIn("value", entry)
            self.assertIn("slotSetting", entry)

    def test_chartis_ui_v2_set_to_one(self):
        manifest = self._load_manifest()
        entry = next(
            (e for e in manifest if e["name"] == "CHARTIS_UI_V2"),
            None,
        )
        self.assertIsNotNone(entry, "CHARTIS_UI_V2 missing from manifest")
        self.assertEqual(entry["value"], "1")

    def test_required_env_vars_present(self):
        manifest = self._load_manifest()
        names = {e["name"] for e in manifest}
        for required in (
            "CHARTIS_UI_V2",
            "RCM_MC_HOST",
            "LOG_LEVEL",
            "RCM_MC_CSRF_SECRET",
            "RCM_MC_DB_PATH",
            "WEBSITES_PORT",
            "WEBSITES_ENABLE_APP_SERVICE_STORAGE",
        ):
            self.assertIn(
                required, names,
                f"manifest missing required env var: {required}",
            )

    def test_csrf_secret_marked_slot_setting(self):
        # SlotSetting=true keeps the secret bound to its slot during
        # slot swaps so blue-green deploys don't accidentally rotate
        # secrets.
        manifest = self._load_manifest()
        entry = next(
            (e for e in manifest if e["name"] == "RCM_MC_CSRF_SECRET"),
            None,
        )
        self.assertIsNotNone(entry)
        self.assertTrue(entry["slotSetting"])


class DBPathEnvTests(unittest.TestCase):
    """demo.py reads RCM_MC_DB_PATH env to enable persistent storage."""

    def _reload_demo(self):
        import sys
        sys.modules.pop("demo", None)
        proj_root = os.path.dirname(
            os.path.dirname(os.path.abspath(
                __import__("rcm_mc").__file__,
            )),
        )
        if proj_root not in sys.path:
            sys.path.insert(0, proj_root)
        return importlib.import_module("demo")

    def test_demo_module_imports_clean(self):
        # demo.py is the production entry; smoke-test its import
        # path under both env states.
        with _env(RCM_MC_DB_PATH=None):
            demo = self._reload_demo()
            self.assertTrue(hasattr(demo, "main"))
        with _env(RCM_MC_DB_PATH="/tmp/rcm_test/portfolio.db"):
            demo = self._reload_demo()
            self.assertTrue(hasattr(demo, "main"))


if __name__ == "__main__":
    unittest.main()
