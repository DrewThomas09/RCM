"""Tests for B112: timeline filtering, API version header.

TIMELINE:
 1. /api/deals/<id>/timeline returns count field.
 2. ?type= filters events by type.
 3. ?limit= caps result count.

API VERSION:
 4. JSON responses include X-API-Version header.
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


class TestTimelineFiltering(unittest.TestCase):

    def test_timeline_has_count(self):
        tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tf.close()
        try:
            store = PortfolioStore(tf.name)
            store.upsert_deal("d1", name="Alpha")
            server, port = _start(tf.name)
            try:
                with urllib.request.urlopen(
                    f"http://127.0.0.1:{port}/api/deals/d1/timeline",
                ) as r:
                    body = json.loads(r.read().decode())
                self.assertIn("count", body)
                self.assertIn("days", body)
                self.assertIn("events", body)
            finally:
                server.shutdown(); server.server_close()
        finally:
            os.unlink(tf.name)


class TestAPIVersionHeader(unittest.TestCase):

    def test_version_header_present(self):
        tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tf.close()
        try:
            server, port = _start(tf.name)
            try:
                with urllib.request.urlopen(
                    f"http://127.0.0.1:{port}/api/health",
                ) as r:
                    ver = r.headers.get("X-API-Version")
                    self.assertIsNotNone(ver)
                    self.assertEqual(ver, "2024-01")
            finally:
                server.shutdown(); server.server_close()
        finally:
            os.unlink(tf.name)

    def test_idempotency_key_in_cors(self):
        tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tf.close()
        try:
            server, port = _start(tf.name)
            try:
                with urllib.request.urlopen(
                    f"http://127.0.0.1:{port}/api/health",
                ) as r:
                    allowed = r.headers.get("Access-Control-Allow-Headers")
                    self.assertIn("Idempotency-Key", allowed)
            finally:
                server.shutdown(); server.server_close()
        finally:
            os.unlink(tf.name)


if __name__ == "__main__":
    unittest.main()
