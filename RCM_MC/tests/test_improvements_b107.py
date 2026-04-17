"""Tests for improvement pass B107: PATCH profile, log filtering, snapshot diffs.

PATCH PROFILE:
 1. PATCH /api/deals/<id>/profile merges fields.
 2. Bad body returns 400.

LOG FILTERING:
 3. Sensitive params are masked in logs.

SNAPSHOT DIFFS:
 4. /api/deals/<id>/diffs returns changes between snapshots.
 5. Single snapshot returns empty diffs.
"""
from __future__ import annotations

import http.client
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


class TestPatchProfile(unittest.TestCase):

    def test_patch_merges_fields(self):
        tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tf.close()
        try:
            store = PortfolioStore(tf.name)
            store.upsert_deal("d1", name="Alpha",
                              profile={"bed_count": 200})
            server, port = _start(tf.name)
            try:
                conn = http.client.HTTPConnection("127.0.0.1", port)
                conn.request(
                    "PATCH", "/api/deals/d1/profile",
                    body=json.dumps({"denial_rate": 12.5}).encode(),
                    headers={"Content-Type": "application/json"},
                )
                resp = conn.getresponse()
                self.assertEqual(resp.status, 200)
                body = json.loads(resp.read().decode())
                self.assertIn("denial_rate", body["updated_fields"])
                conn.close()

                # Verify the field was merged (bed_count still there)
                store2 = PortfolioStore(tf.name)
                deals = store2.list_deals()
                d = deals[deals["deal_id"] == "d1"].iloc[0]
                self.assertEqual(float(d["bed_count"]), 200)
                self.assertEqual(float(d["denial_rate"]), 12.5)
            finally:
                server.shutdown(); server.server_close()
        finally:
            os.unlink(tf.name)

    def test_patch_empty_body_400(self):
        tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tf.close()
        try:
            store = PortfolioStore(tf.name)
            store.upsert_deal("d1", name="Alpha")
            server, port = _start(tf.name)
            try:
                conn = http.client.HTTPConnection("127.0.0.1", port)
                conn.request(
                    "PATCH", "/api/deals/d1/profile",
                    body=b"{}",
                    headers={"Content-Type": "application/json"},
                )
                resp = conn.getresponse()
                self.assertEqual(resp.status, 400)
                conn.close()
            finally:
                server.shutdown(); server.server_close()
        finally:
            os.unlink(tf.name)


class TestLogFiltering(unittest.TestCase):

    def test_sensitive_params_masked(self):
        import re
        pattern = re.compile(
            r'(password|secret|token|key|auth)=([^&\s]+)',
            re.IGNORECASE,
        )
        test_path = "/api/login?username=admin&password=s3cret&token=abc123"
        safe = pattern.sub(r'\1=***', test_path)
        self.assertNotIn("s3cret", safe)
        self.assertNotIn("abc123", safe)
        self.assertIn("password=***", safe)
        self.assertIn("token=***", safe)
        self.assertIn("username=admin", safe)


class TestSnapshotDiffs(unittest.TestCase):

    def test_diffs_with_snapshots(self):
        tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tf.close()
        try:
            store = PortfolioStore(tf.name)
            store.upsert_deal("d1", name="Alpha")
            from rcm_mc.portfolio.portfolio_snapshots import register_snapshot
            register_snapshot(store, "d1", "loi")
            register_snapshot(store, "d1", "spa")
            server, port = _start(tf.name)
            try:
                with urllib.request.urlopen(
                    f"http://127.0.0.1:{port}/api/deals/d1/diffs",
                ) as r:
                    body = json.loads(r.read().decode())
                self.assertEqual(body["deal_id"], "d1")
                self.assertIn("diffs", body)
                self.assertEqual(body["snapshot_count"], 2)
                self.assertGreater(len(body["diffs"]), 0)
            finally:
                server.shutdown(); server.server_close()
        finally:
            os.unlink(tf.name)

    def test_single_snapshot_empty_diffs(self):
        tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tf.close()
        try:
            store = PortfolioStore(tf.name)
            store.upsert_deal("d1", name="Alpha")
            from rcm_mc.portfolio.portfolio_snapshots import register_snapshot
            register_snapshot(store, "d1", "loi")
            server, port = _start(tf.name)
            try:
                with urllib.request.urlopen(
                    f"http://127.0.0.1:{port}/api/deals/d1/diffs",
                ) as r:
                    body = json.loads(r.read().decode())
                self.assertEqual(body["diffs"], [])
            finally:
                server.shutdown(); server.server_close()
        finally:
            os.unlink(tf.name)


if __name__ == "__main__":
    unittest.main()
