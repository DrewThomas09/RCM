"""Tests for improvement pass B100: API index, OpenAPI completeness.

API INDEX:
 1. GET /api returns endpoint listing.
 2. Listing includes docs_url and openapi_url.
 3. Count matches OpenAPI spec paths.

OPENAPI FINAL:
 4. Spec includes all B97-B99 endpoints.
 5. Total path count >= 35.
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


class TestAPIIndex(unittest.TestCase):

    def test_api_index_returns_endpoints(self):
        tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tf.close()
        try:
            server, port = _start(tf.name)
            try:
                with urllib.request.urlopen(
                    f"http://127.0.0.1:{port}/api",
                ) as r:
                    body = json.loads(r.read().decode())
                self.assertIn("endpoints", body)
                self.assertIn("count", body)
                self.assertIn("docs_url", body)
                self.assertIn("openapi_url", body)
                self.assertGreater(body["count"], 20)
            finally:
                server.shutdown(); server.server_close()
        finally:
            os.unlink(tf.name)

    def test_api_index_matches_spec(self):
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
                spec_method_count = sum(
                    len(methods) for methods in spec["paths"].values()
                )
                self.assertEqual(body["count"], spec_method_count)
            finally:
                server.shutdown(); server.server_close()
        finally:
            os.unlink(tf.name)


class TestOpenAPIFinalCompleteness(unittest.TestCase):

    def test_spec_has_checklist(self):
        spec = get_openapi_spec()
        self.assertIn("/api/deals/{deal_id}/checklist", spec["paths"])

    def test_spec_has_validate(self):
        spec = get_openapi_spec()
        self.assertIn("/api/deals/{deal_id}/validate", spec["paths"])

    def test_spec_has_similar(self):
        spec = get_openapi_spec()
        self.assertIn("/api/deals/{deal_id}/similar", spec["paths"])

    def test_spec_has_portfolio_summary(self):
        spec = get_openapi_spec()
        self.assertIn("/api/portfolio/summary", spec["paths"])

    def test_spec_has_portfolio_health(self):
        spec = get_openapi_spec()
        self.assertIn("/api/portfolio/health", spec["paths"])

    def test_spec_path_count(self):
        spec = get_openapi_spec()
        self.assertGreaterEqual(len(spec["paths"]), 35)


if __name__ == "__main__":
    unittest.main()
