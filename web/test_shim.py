"""Tests for the `web/` Heroku shim.

Verifies the two claims the shim makes:
  1. bootstrap.ensure_ready() delegates to the real rcm_mc.auth + migrations
  2. heroku_adapter imports cleanly and wires build_server correctly

No network, no real signals fired — unittest.mock patches the real calls.
"""
from __future__ import annotations

import os
import tempfile
import unittest
from unittest.mock import patch, MagicMock


class TestBootstrap(unittest.TestCase):
    def test_exits_when_env_missing(self):
        from web import bootstrap
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(SystemExit) as cm:
                bootstrap.ensure_ready()
            self.assertEqual(cm.exception.code, 1)

    def test_delegates_to_create_user(self):
        from web import bootstrap
        with tempfile.TemporaryDirectory() as td:
            db_path = os.path.join(td, "t.db")
            env = {"ADMIN_USERNAME": "alice", "ADMIN_PASSWORD": "x" * 12,
                   "RCM_MC_DB": db_path}
            with patch.dict(os.environ, env, clear=True), \
                 patch("web.bootstrap.create_user") as m_create, \
                 patch("web.bootstrap.migrations.run_pending") as m_migrate:
                out = bootstrap.ensure_ready()
                self.assertEqual(out, db_path)
                m_migrate.assert_called_once()
                m_create.assert_called_once()
                _, kwargs = m_create.call_args
                self.assertEqual(kwargs.get("role"), "admin")

    def test_idempotent_on_existing_user(self):
        from web import bootstrap
        with tempfile.TemporaryDirectory() as td:
            env = {"ADMIN_USERNAME": "alice", "ADMIN_PASSWORD": "x" * 12,
                   "RCM_MC_DB": os.path.join(td, "t.db")}
            with patch.dict(os.environ, env, clear=True), \
                 patch("web.bootstrap.migrations.run_pending"), \
                 patch("web.bootstrap.create_user",
                       side_effect=ValueError("name clash")):
                # Must NOT raise — duplicate user is the idempotent case
                bootstrap.ensure_ready()


class TestHerokuAdapter(unittest.TestCase):
    def test_imports_cleanly(self):
        from web import heroku_adapter
        self.assertTrue(hasattr(heroku_adapter, "main"))
        self.assertEqual(heroku_adapter.HOST, "0.0.0.0")

    def test_main_passes_port_and_host_to_build_server(self):
        from web import heroku_adapter
        env = {"PORT": "9999", "ADMIN_USERNAME": "a", "ADMIN_PASSWORD": "x" * 12}
        fake_server = MagicMock()
        fake_server.serve_forever.side_effect = KeyboardInterrupt
        with patch.dict(os.environ, env, clear=True), \
             patch("web.heroku_adapter.bootstrap.ensure_ready",
                   return_value="/tmp/x.db"), \
             patch("web.heroku_adapter.build_server",
                   return_value=(fake_server, None)) as m_build, \
             patch("web.heroku_adapter.signal.signal"):
            # Expect KeyboardInterrupt to bubble through serve_forever;
            # the finally clause still waits on shutdown_done.
            try:
                heroku_adapter.main()
            except KeyboardInterrupt:
                pass
            kwargs = m_build.call_args.kwargs
            self.assertEqual(kwargs["port"], 9999)
            self.assertEqual(kwargs["host"], "0.0.0.0")
            self.assertEqual(kwargs["db_path"], "/tmp/x.db")
            self.assertIsNone(kwargs["auth"])


if __name__ == "__main__":
    unittest.main()
