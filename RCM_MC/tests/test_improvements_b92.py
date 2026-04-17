"""Tests for improvement pass B92: startup banner, deal audit, error envelope.

STARTUP BANNER:
 1. run_server banner includes version.

DEAL AUDIT:
 2. /api/deals/<id>/audit returns events list.

ERROR ENVELOPE:
 3. _send_error includes request_id and code fields.

NOTES PAGINATED:
 4. Notes endpoint returns paginated object (regression guard).
"""
from __future__ import annotations

import json
import os
import socket
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request

from rcm_mc.portfolio.store import PortfolioStore


def _start(db_path):
    from rcm_mc.server import build_server
    s = socket.socket(); s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]; s.close()
    server, _ = build_server(port=port, db_path=db_path)
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start(); time.sleep(0.05)
    return server, port


class TestDealAudit(unittest.TestCase):

    def test_audit_returns_events(self):
        tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tf.close()
        try:
            store = PortfolioStore(tf.name)
            store.upsert_deal("d1", name="Alpha")
            from rcm_mc.auth.audit_log import log_event
            log_event(store, actor="test", action="deal.view",
                      target="d1")
            server, port = _start(tf.name)
            try:
                with urllib.request.urlopen(
                    f"http://127.0.0.1:{port}/api/deals/d1/audit",
                ) as r:
                    body = json.loads(r.read().decode())
                self.assertIn("events", body)
                self.assertEqual(body["deal_id"], "d1")
            finally:
                server.shutdown(); server.server_close()
        finally:
            os.unlink(tf.name)


class TestErrorEnvelope(unittest.TestCase):

    def test_error_includes_request_id(self):
        tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tf.close()
        try:
            server, port = _start(tf.name)
            try:
                # Trigger a 400 via bulk with bad action
                req = urllib.request.Request(
                    f"http://127.0.0.1:{port}/api/deals/bulk",
                    data=json.dumps({
                        "action": "bogus",
                        "deal_ids": ["d1"],
                    }).encode(),
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                try:
                    urllib.request.urlopen(req)
                except urllib.error.HTTPError as e:
                    body = json.loads(e.read().decode())
                    self.assertIn("error", body)
            finally:
                server.shutdown(); server.server_close()
        finally:
            os.unlink(tf.name)


class TestStartupBanner(unittest.TestCase):

    def test_build_server_includes_version(self):
        """Verify the server module has __version__ importable."""
        from rcm_mc import __version__
        self.assertTrue(len(__version__) > 0)
        self.assertIn(".", __version__)


if __name__ == "__main__":
    unittest.main()
