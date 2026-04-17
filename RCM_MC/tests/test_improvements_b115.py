"""Tests for B115: HEAD method, final OpenAPI count.

HEAD:
 1. HEAD /api/health returns 200 with headers but no body.
 2. HEAD /settings returns 200.

OPENAPI:
 3. Final path count >= 52.
"""
from __future__ import annotations

import http.client
import os
import socket
import tempfile
import threading
import time
import unittest

from rcm_mc.infra.openapi import get_openapi_spec


def _start(db_path):
    from rcm_mc.server import build_server
    s = socket.socket(); s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]; s.close()
    server, _ = build_server(port=port, db_path=db_path)
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start(); time.sleep(0.05)
    return server, port


class TestHeadMethod(unittest.TestCase):

    def test_head_health_returns_200(self):
        tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tf.close()
        try:
            server, port = _start(tf.name)
            try:
                conn = http.client.HTTPConnection("127.0.0.1", port)
                conn.request("HEAD", "/api/health")
                resp = conn.getresponse()
                self.assertEqual(resp.status, 200)
                body = resp.read()
                self.assertEqual(len(body), 0)
                conn.close()
            finally:
                server.shutdown(); server.server_close()
        finally:
            os.unlink(tf.name)

    def test_head_settings_returns_200(self):
        tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tf.close()
        try:
            server, port = _start(tf.name)
            try:
                conn = http.client.HTTPConnection("127.0.0.1", port)
                conn.request("HEAD", "/settings")
                resp = conn.getresponse()
                self.assertEqual(resp.status, 200)
                conn.close()
            finally:
                server.shutdown(); server.server_close()
        finally:
            os.unlink(tf.name)


class TestFinalOpenAPI(unittest.TestCase):

    def test_final_path_count(self):
        spec = get_openapi_spec()
        self.assertGreaterEqual(len(spec["paths"]), 52)
        methods = sum(len(m) for m in spec["paths"].values())
        self.assertGreaterEqual(methods, 56)


if __name__ == "__main__":
    unittest.main()
