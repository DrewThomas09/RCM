"""Tests for improvement pass B106: final OpenAPI + E2E smoke test.

OPENAPI FINAL:
 1. Spec has counts endpoint.
 2. Spec has notes endpoint.
 3. Spec has tags endpoint.
 4. Spec has stage endpoint.
 5. Spec has health endpoint.
 6. Total path count >= 47.

E2E SMOKE:
 7. Create deal → add note → add tag → validate → checklist → counts
    all in sequence on one server.
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
from rcm_mc.portfolio.store import PortfolioStore


def _start(db_path):
    from rcm_mc.server import build_server
    s = socket.socket(); s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]; s.close()
    server, _ = build_server(port=port, db_path=db_path)
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start(); time.sleep(0.05)
    return server, port


class TestOpenAPIPathCount(unittest.TestCase):

    def test_counts_documented(self):
        spec = get_openapi_spec()
        self.assertIn("/api/deals/{deal_id}/counts", spec["paths"])

    def test_notes_documented(self):
        spec = get_openapi_spec()
        self.assertIn("/api/deals/{deal_id}/notes", spec["paths"])

    def test_tags_documented(self):
        spec = get_openapi_spec()
        self.assertIn("/api/deals/{deal_id}/tags", spec["paths"])

    def test_stage_documented(self):
        spec = get_openapi_spec()
        self.assertIn("/api/deals/{deal_id}/stage", spec["paths"])

    def test_health_documented(self):
        spec = get_openapi_spec()
        self.assertIn("/api/deals/{deal_id}/health", spec["paths"])

    def test_path_count_final(self):
        spec = get_openapi_spec()
        self.assertGreaterEqual(len(spec["paths"]), 47)


class TestE2ESmoke(unittest.TestCase):

    def test_full_deal_lifecycle(self):
        """Create → import → note → tag → validate → checklist → counts."""
        tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tf.close()
        try:
            server, port = _start(tf.name)
            base = f"http://127.0.0.1:{port}"
            try:
                # Import a deal
                req = urllib.request.Request(
                    f"{base}/api/deals/import",
                    data=json.dumps([{
                        "deal_id": "smoke1",
                        "name": "Smoke Test Hospital",
                        "profile": {"bed_count": 250, "denial_rate": 12},
                    }]).encode(),
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                with urllib.request.urlopen(req) as r:
                    body = json.loads(r.read().decode())
                self.assertEqual(body["imported"], 1)

                # Add a note
                req = urllib.request.Request(
                    f"{base}/api/deals/smoke1/notes",
                    data=b"deal_id=smoke1&body=Initial+review+complete&author=test",
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                    method="POST",
                )
                with urllib.request.urlopen(req) as r:
                    self.assertEqual(r.status, 200)

                # Add a tag
                req = urllib.request.Request(
                    f"{base}/api/deals/smoke1/tags",
                    data=b"deal_id=smoke1&tag=high-priority",
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                    method="POST",
                )
                with urllib.request.urlopen(req) as r:
                    self.assertEqual(r.status, 200)

                # Validate
                with urllib.request.urlopen(
                    f"{base}/api/deals/smoke1/validate",
                ) as r:
                    body = json.loads(r.read().decode())
                self.assertIn("valid", body)

                # Checklist
                with urllib.request.urlopen(
                    f"{base}/api/deals/smoke1/checklist",
                ) as r:
                    body = json.loads(r.read().decode())
                self.assertIn("items", body)
                self.assertIn("ready_for_ic", body)

                # Counts
                with urllib.request.urlopen(
                    f"{base}/api/deals/smoke1/counts",
                ) as r:
                    body = json.loads(r.read().decode())
                self.assertGreaterEqual(body["notes"], 1)
                self.assertGreaterEqual(body["tags"], 1)

                # Summary
                with urllib.request.urlopen(
                    f"{base}/api/deals/smoke1/summary",
                ) as r:
                    body = json.loads(r.read().decode())
                self.assertEqual(body["name"], "Smoke Test Hospital")

                # System info
                with urllib.request.urlopen(
                    f"{base}/api/system/info",
                ) as r:
                    body = json.loads(r.read().decode())
                self.assertGreaterEqual(body["deal_count"], 1)

                # API index
                with urllib.request.urlopen(f"{base}/api") as r:
                    body = json.loads(r.read().decode())
                self.assertGreater(body["count"], 40)

            finally:
                server.shutdown(); server.server_close()
        finally:
            os.unlink(tf.name)


if __name__ == "__main__":
    unittest.main()
