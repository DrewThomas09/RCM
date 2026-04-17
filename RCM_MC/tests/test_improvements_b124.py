"""Tests for B124: surrogate page + API.

 1. GET /surrogate renders HTML with model status.
 2. GET /api/surrogate/schema returns training schema.
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


class TestSurrogatePage(unittest.TestCase):

    def test_surrogate_renders(self):
        tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tf.close()
        try:
            server, port = _start(tf.name)
            try:
                with urllib.request.urlopen(
                    f"http://127.0.0.1:{port}/surrogate",
                ) as r:
                    body = r.read().decode()
                self.assertIn("Surrogate Model", body)
                self.assertIn("Not Trained", body)
            finally:
                server.shutdown(); server.server_close()
        finally:
            os.unlink(tf.name)

    def test_surrogate_api_schema(self):
        tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tf.close()
        try:
            server, port = _start(tf.name)
            try:
                with urllib.request.urlopen(
                    f"http://127.0.0.1:{port}/api/surrogate/schema",
                ) as r:
                    body = json.loads(r.read().decode())
                self.assertIn("schema", body)
                self.assertIn("model_status", body)
                self.assertEqual(body["model_status"], "not_trained")
                self.assertIn("suggested_features", body["schema"])
            finally:
                server.shutdown(); server.server_close()
        finally:
            os.unlink(tf.name)


if __name__ == "__main__":
    unittest.main()
