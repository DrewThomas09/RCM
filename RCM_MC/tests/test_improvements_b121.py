"""Tests for B121: deep health check.

 1. /api/health/deep returns component checks.
 2. DB check returns latency.
 3. Migrations check reports count.
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


def _start(db_path):
    from rcm_mc.server import build_server
    s = socket.socket(); s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]; s.close()
    server, _ = build_server(port=port, db_path=db_path)
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start(); time.sleep(0.05)
    return server, port


class TestDeepHealth(unittest.TestCase):

    def test_deep_health_returns_checks(self):
        tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tf.close()
        try:
            server, port = _start(tf.name)
            try:
                with urllib.request.urlopen(
                    f"http://127.0.0.1:{port}/api/health/deep",
                ) as r:
                    body = json.loads(r.read().decode())
                self.assertIn("status", body)
                self.assertIn("checks", body)
                self.assertIn("version", body)
                checks = body["checks"]
                self.assertIn("db", checks)
                self.assertEqual(checks["db"]["status"], "ok")
                self.assertIn("latency_ms", checks["db"])
                self.assertIn("migrations", checks)
                self.assertIn("hcris_data", checks)
                self.assertIn("disk", checks)
            finally:
                server.shutdown(); server.server_close()
        finally:
            os.unlink(tf.name)


if __name__ == "__main__":
    unittest.main()
