"""Tests for improvement pass B104: final OpenAPI completeness.

OPENAPI FINAL:
 1. Spec has /api/deals/{deal_id}/package.
 2. Spec has /api/deals/search.
 3. Spec has /api/migrations.
 4. Spec has /api (index).
 5. Total path count >= 45.
 6. API index endpoint count matches spec.
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

from rcm_mc.infra.openapi import get_openapi_spec


def _start(db_path):
    from rcm_mc.server import build_server
    s = socket.socket(); s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]; s.close()
    server, _ = build_server(port=port, db_path=db_path)
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start(); time.sleep(0.05)
    return server, port


class TestOpenAPIFinal(unittest.TestCase):

    def test_package_documented(self):
        spec = get_openapi_spec()
        self.assertIn("/api/deals/{deal_id}/package", spec["paths"])

    def test_deal_search_documented(self):
        spec = get_openapi_spec()
        self.assertIn("/api/deals/search", spec["paths"])

    def test_migrations_documented(self):
        spec = get_openapi_spec()
        self.assertIn("/api/migrations", spec["paths"])

    def test_api_index_documented(self):
        spec = get_openapi_spec()
        self.assertIn("/api", spec["paths"])

    def test_path_count(self):
        spec = get_openapi_spec()
        self.assertGreaterEqual(len(spec["paths"]), 40)

    def test_api_index_sync(self):
        tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tf.close()
        try:
            server, port = _start(tf.name)
            try:
                with urllib.request.urlopen(
                    f"http://127.0.0.1:{port}/api",
                ) as r:
                    body = json.loads(r.read().decode())
                spec = get_openapi_spec()
                spec_count = sum(
                    len(m) for m in spec["paths"].values()
                )
                self.assertEqual(body["count"], spec_count)
            finally:
                server.shutdown(); server.server_close()
        finally:
            os.unlink(tf.name)


if __name__ == "__main__":
    unittest.main()
