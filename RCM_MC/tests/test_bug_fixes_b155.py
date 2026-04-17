"""Regression tests for B155: audit-log silent-failure fix."""
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

from rcm_mc.alerts.alert_acks import trigger_key_for
from rcm_mc.alerts.alerts import evaluate_all
from tests.test_alerts import _seed_with_pe_math


class TestAuditFailureSurfaces(unittest.TestCase):
    def setUp(self):
        # Reset the class-level counter between tests
        from rcm_mc.server import RCMHandler
        RCMHandler._audit_failure_count = 0
        RCMHandler._audit_last_failure = None

    def tearDown(self):
        from rcm_mc.server import RCMHandler
        RCMHandler._audit_failure_count = 0
        RCMHandler._audit_last_failure = None

    def _start(self, tmp):
        import socket as _socket, time as _time
        from rcm_mc.server import build_server
        s = _socket.socket(); s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]; s.close()
        server, _ = build_server(port=port,
                                 db_path=os.path.join(tmp, "p.db"))
        t = threading.Thread(target=server.serve_forever, daemon=True)
        t.start(); _time.sleep(0.05)
        return server, port

    def test_api_health_exposes_audit_counter(self):
        with tempfile.TemporaryDirectory() as tmp:
            server, port = self._start(tmp)
            try:
                with _u.urlopen(
                    f"http://127.0.0.1:{port}/api/health"
                ) as r:
                    data = json.loads(r.read().decode())
                    # Prompt 66 enhanced the health endpoint to return
                    # "healthy" instead of "ok" and added db_ok/version.
                    self.assertIn(data["status"], ("ok", "healthy"))
                    self.assertEqual(data["audit_failure_count"], 0)
                    self.assertIsNone(data["audit_last_failure"])
            finally:
                server.shutdown(); server.server_close()

    def test_audit_failure_increments_counter_and_writes_stderr(self):
        """Simulate a disk-full / locked-DB by monkey-patching log_event
        to raise. The primary op must still succeed, but the counter
        must increment and a stderr breadcrumb must be emitted."""
        from rcm_mc.auth import audit_log
        import rcm_mc.server as _server

        original_log = audit_log.log_event

        def _boom(*args, **kwargs):
            raise OSError("disk full (simulated)")

        # Capture stderr
        captured = io.StringIO()
        old_stderr = sys.stderr

        with tempfile.TemporaryDirectory() as tmp:
            store = _seed_with_pe_math(tmp, "ccf", headroom=-0.5)
            server, port = self._start(tmp)
            try:
                audit_log.log_event = _boom
                sys.stderr = captured
                try:
                    # Trigger any audited action — an ack will do
                    alert = next(a for a in evaluate_all(store)
                                 if a.kind == "covenant_tripped")
                    body = _p.urlencode({
                        "kind": alert.kind,
                        "deal_id": alert.deal_id,
                        "trigger_key": trigger_key_for(alert),
                    }).encode()
                    req = _u.Request(
                        f"http://127.0.0.1:{port}/api/alerts/ack",
                        data=body, method="POST",
                        headers={
                            "Content-Type":
                                "application/x-www-form-urlencoded",
                            "Accept": "application/json",
                        },
                    )
                    # Primary op must still succeed (201 Created)
                    with _u.urlopen(req) as r:
                        self.assertEqual(r.status, 201)
                finally:
                    sys.stderr = old_stderr
                    audit_log.log_event = original_log

                # Counter must have incremented
                self.assertGreaterEqual(
                    _server.RCMHandler._audit_failure_count, 1,
                )
                # Stderr must have a breadcrumb
                err_text = captured.getvalue()
                self.assertIn("[rcm-mc audit] FAILED", err_text)
                self.assertIn("alert.ack", err_text)
                self.assertIn("disk full (simulated)", err_text)

                # And /api/health surfaces the count
                with _u.urlopen(
                    f"http://127.0.0.1:{port}/api/health"
                ) as r:
                    data = json.loads(r.read().decode())
                    self.assertGreaterEqual(data["audit_failure_count"], 1)
                    self.assertIsNotNone(data["audit_last_failure"])
            finally:
                server.shutdown(); server.server_close()


if __name__ == "__main__":
    unittest.main()
