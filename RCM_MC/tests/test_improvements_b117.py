"""Tests for B117: scenario explorer page + API.

 1. GET /scenarios returns HTML with preset shocks.
 2. GET /api/scenarios returns JSON preset list.
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


class TestScenarioExplorer(unittest.TestCase):

    def test_scenarios_page_renders(self):
        tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tf.close()
        try:
            server, port = _start(tf.name)
            try:
                with urllib.request.urlopen(
                    f"http://127.0.0.1:{port}/scenarios",
                ) as r:
                    body = r.read().decode()
                self.assertIn("Scenario Explorer", body)
                self.assertIn("commercial_idr_20", body)
            finally:
                server.shutdown(); server.server_close()
        finally:
            os.unlink(tf.name)

    def test_api_scenarios_returns_presets(self):
        tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tf.close()
        try:
            server, port = _start(tf.name)
            try:
                with urllib.request.urlopen(
                    f"http://127.0.0.1:{port}/api/scenarios",
                ) as r:
                    body = json.loads(r.read().decode())
                self.assertIn("presets", body)
                self.assertIn("count", body)
                self.assertGreater(body["count"], 0)
                self.assertEqual(body["presets"][0]["id"], "commercial_idr_20")
            finally:
                server.shutdown(); server.server_close()
        finally:
            os.unlink(tf.name)


if __name__ == "__main__":
    unittest.main()
