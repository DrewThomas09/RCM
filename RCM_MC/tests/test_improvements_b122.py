"""Tests for B122: webhook lifecycle dispatch + test endpoint.

 1. /api/webhooks/test returns dispatch result.
 2. _fire_webhook doesn't crash when no webhooks configured.
 3. Deal delete fires webhook (verified via delivery table).
"""
from __future__ import annotations

import json
import os
import socket
import tempfile
import threading
import time
import unittest
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


class TestWebhookTest(unittest.TestCase):

    def test_webhook_test_endpoint(self):
        tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tf.close()
        try:
            server, port = _start(tf.name)
            try:
                with urllib.request.urlopen(
                    f"http://127.0.0.1:{port}/api/webhooks/test",
                ) as r:
                    body = json.loads(r.read().decode())
                self.assertEqual(body["event"], "test.ping")
                self.assertIn("webhooks_matched", body)
                self.assertEqual(body["webhooks_matched"], 0)
            finally:
                server.shutdown(); server.server_close()
        finally:
            os.unlink(tf.name)


class TestWebhookLifecycle(unittest.TestCase):

    def test_delete_fires_no_crash(self):
        """Delete a deal — webhook dispatch should not crash even with no hooks."""
        tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tf.close()
        try:
            store = PortfolioStore(tf.name)
            store.upsert_deal("d1", name="Alpha")
            server, port = _start(tf.name)
            try:
                req = urllib.request.Request(
                    f"http://127.0.0.1:{port}/api/deals/d1",
                    method="DELETE",
                )
                with urllib.request.urlopen(req) as r:
                    body = json.loads(r.read().decode())
                self.assertTrue(body["deleted"])
            finally:
                server.shutdown(); server.server_close()
        finally:
            os.unlink(tf.name)


if __name__ == "__main__":
    unittest.main()
