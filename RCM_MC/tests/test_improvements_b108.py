"""Tests for B108: OpenAPI final, CORS PATCH, path count.

 1. OpenAPI has profile PATCH endpoint.
 2. OpenAPI has diffs endpoint.
 3. Path count >= 49.
 4. CORS allows PATCH method.
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


class TestOpenAPIB108(unittest.TestCase):

    def test_profile_patch_documented(self):
        spec = get_openapi_spec()
        self.assertIn("/api/deals/{deal_id}/profile", spec["paths"])
        self.assertIn("patch", spec["paths"]["/api/deals/{deal_id}/profile"])

    def test_diffs_documented(self):
        spec = get_openapi_spec()
        self.assertIn("/api/deals/{deal_id}/diffs", spec["paths"])

    def test_path_count(self):
        spec = get_openapi_spec()
        self.assertGreaterEqual(len(spec["paths"]), 49)

    def test_cors_allows_patch(self):
        tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tf.close()
        try:
            server, port = _start(tf.name)
            try:
                conn = http.client.HTTPConnection("127.0.0.1", port)
                conn.request("OPTIONS", "/api/deals/d1/profile")
                resp = conn.getresponse()
                methods = resp.getheader("Access-Control-Allow-Methods")
                self.assertIn("PATCH", methods)
                conn.close()
            finally:
                server.shutdown(); server.server_close()
        finally:
            os.unlink(tf.name)


if __name__ == "__main__":
    unittest.main()
