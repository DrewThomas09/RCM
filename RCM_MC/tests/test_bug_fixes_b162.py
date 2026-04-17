"""Regression tests for B162 observability fixes."""
from __future__ import annotations

import io
import json
import os
import sys
import tempfile
import threading
import unittest
import urllib.parse as _p
import urllib.request as _u

from rcm_mc.auth.audit_log import list_events
from rcm_mc.auth.auth import create_user
from rcm_mc.portfolio.store import PortfolioStore


def _store(tmp: str) -> PortfolioStore:
    return PortfolioStore(os.path.join(tmp, "p.db"))


def _start(tmp):
    import socket as _socket, time as _time
    from rcm_mc.server import RCMHandler, build_server
    RCMHandler._login_fail_log = {}
    s = _socket.socket(); s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]; s.close()
    server, _ = build_server(port=port,
                             db_path=os.path.join(tmp, "p.db"))
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start(); _time.sleep(0.05)
    return server, port


class TestLoginAudit(unittest.TestCase):
    def test_successful_login_is_audited(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _store(tmp)
            create_user(store, "at", "supersecret1")
            server, port = _start(tmp)
            try:
                body = _p.urlencode({
                    "username": "at", "password": "supersecret1",
                }).encode()
                req = _u.Request(
                    f"http://127.0.0.1:{port}/api/login",
                    data=body, method="POST",
                    headers={
                        "Content-Type": "application/x-www-form-urlencoded",
                        "Accept": "application/json",
                    },
                )
                _u.urlopen(req)
                # Audit log should have a login.success row
                df = list_events(store, action="login.success")
                self.assertEqual(len(df), 1)
                self.assertEqual(df.iloc[0]["actor"], "at")
            finally:
                server.shutdown(); server.server_close()

    def test_failed_login_is_audited_with_username(self):
        from urllib.error import HTTPError
        with tempfile.TemporaryDirectory() as tmp:
            store = _store(tmp)
            create_user(store, "at", "supersecret1")
            server, port = _start(tmp)
            try:
                body = _p.urlencode({
                    "username": "at", "password": "wrong",
                }).encode()
                req = _u.Request(
                    f"http://127.0.0.1:{port}/api/login",
                    data=body, method="POST",
                    headers={
                        "Content-Type": "application/x-www-form-urlencoded",
                        "Accept": "application/json",
                    },
                )
                with self.assertRaises(HTTPError):
                    _u.urlopen(req)
                df = list_events(store, action="login.failure")
                self.assertEqual(len(df), 1)
                self.assertEqual(df.iloc[0]["actor"], "at")
            finally:
                server.shutdown(); server.server_close()


class TestEvaluatorFailureVisible(unittest.TestCase):
    def test_raising_evaluator_increments_counter_and_writes_stderr(self):
        import rcm_mc.alerts.alerts as alerts_mod
        from rcm_mc.alerts.alerts import evaluate_all

        def _boom(store):
            raise RuntimeError("simulated evaluator crash")

        # Reset counters
        alerts_mod.EVALUATOR_FAILURES.clear()
        # Patch an evaluator in
        original = list(alerts_mod._EVALUATORS)
        alerts_mod._EVALUATORS.append(_boom)

        captured = io.StringIO()
        old_stderr = sys.stderr
        try:
            sys.stderr = captured
            with tempfile.TemporaryDirectory() as tmp:
                store = _store(tmp)
                store.init_db()
                # Should not raise — other evaluators still run
                alerts = evaluate_all(store)
                # Counter must have incremented
                self.assertEqual(
                    alerts_mod.EVALUATOR_FAILURES.get("_boom"), 1,
                )
                # Stderr must have a breadcrumb
                err_text = captured.getvalue()
                self.assertIn("evaluator _boom FAILED", err_text)
                self.assertIn("simulated evaluator crash", err_text)
        finally:
            sys.stderr = old_stderr
            # Restore original evaluator list
            alerts_mod._EVALUATORS[:] = original
            alerts_mod.EVALUATOR_FAILURES.clear()


class TestHttpAccessLog(unittest.TestCase):
    def test_request_log_written_to_stderr(self):
        """A non-health request should produce one stderr line."""
        captured = io.StringIO()
        old_stderr = sys.stderr
        with tempfile.TemporaryDirectory() as tmp:
            server, port = _start(tmp)
            try:
                # Swap stderr AFTER server started (server thread
                # inherits the original, but our test reads what the
                # handler writes, which uses the current sys.stderr).
                sys.stderr = captured
                with _u.urlopen(f"http://127.0.0.1:{port}/login") as r:
                    r.read()
                # Give the handler a moment to flush
                import time; time.sleep(0.05)
            finally:
                sys.stderr = old_stderr
                server.shutdown(); server.server_close()
        text = captured.getvalue()
        # Prompt 21 replaced the ``[rcm-http] …`` format with a
        # structured JSON line per request. Assert against the new
        # shape — method + path still present, just via JSON keys.
        self.assertIn('"method": "GET"', text)
        self.assertIn('"path": "/login"', text)

    def test_health_path_is_not_logged(self):
        """/health is polled by monitors; logging would flood stderr."""
        captured = io.StringIO()
        old_stderr = sys.stderr
        with tempfile.TemporaryDirectory() as tmp:
            server, port = _start(tmp)
            try:
                sys.stderr = captured
                with _u.urlopen(f"http://127.0.0.1:{port}/health") as r:
                    r.read()
                import time; time.sleep(0.05)
            finally:
                sys.stderr = old_stderr
                server.shutdown(); server.server_close()
        self.assertNotIn("/health", captured.getvalue())


if __name__ == "__main__":
    unittest.main()
