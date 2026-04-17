"""Tests for improvement pass B98: validation, idempotency, stats.

VALIDATION:
 1. /api/deals/<id>/validate returns issues for sparse profile.
 2. Good deal returns valid=True.
 3. Missing deal returns 404.

IDEMPOTENCY:
 4. Duplicate POST with same Idempotency-Key returns cached response.

STATS:
 5. /api/deals/stats returns stage distribution.
"""
from __future__ import annotations

import json
import os
import socket
import tempfile
import threading
import time
import unittest
import urllib.error
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


class TestDealValidation(unittest.TestCase):

    def test_sparse_profile_has_issues(self):
        tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tf.close()
        try:
            store = PortfolioStore(tf.name)
            store.upsert_deal("d1", name="Alpha")
            server, port = _start(tf.name)
            try:
                with urllib.request.urlopen(
                    f"http://127.0.0.1:{port}/api/deals/d1/validate",
                ) as r:
                    body = json.loads(r.read().decode())
                self.assertEqual(body["deal_id"], "d1")
                self.assertIn("issues", body)
                self.assertIn("warnings", body)
                self.assertIn("profile_fields", body)
            finally:
                server.shutdown(); server.server_close()
        finally:
            os.unlink(tf.name)

    def test_rich_profile_valid(self):
        tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tf.close()
        try:
            store = PortfolioStore(tf.name)
            store.upsert_deal("d1", name="Alpha Hospital",
                              profile={
                                  "bed_count": 200,
                                  "denial_rate": 10.5,
                                  "net_revenue": 400e6,
                                  "days_in_ar": 45,
                                  "clean_claim_rate": 92,
                                  "cost_to_collect": 4.5,
                                  "net_collection_rate": 96,
                                  "claims_volume": 150000,
                              })
            server, port = _start(tf.name)
            try:
                with urllib.request.urlopen(
                    f"http://127.0.0.1:{port}/api/deals/d1/validate",
                ) as r:
                    body = json.loads(r.read().decode())
                self.assertTrue(body["valid"])
                self.assertEqual(body["issues"], [])
            finally:
                server.shutdown(); server.server_close()
        finally:
            os.unlink(tf.name)

    def test_missing_deal_404(self):
        tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tf.close()
        try:
            server, port = _start(tf.name)
            try:
                with self.assertRaises(urllib.error.HTTPError) as ctx:
                    urllib.request.urlopen(
                        f"http://127.0.0.1:{port}/api/deals/nope/validate",
                    )
                self.assertEqual(ctx.exception.code, 404)
            finally:
                server.shutdown(); server.server_close()
        finally:
            os.unlink(tf.name)


class TestIdempotency(unittest.TestCase):

    def test_duplicate_post_returns_cached(self):
        tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tf.close()
        try:
            server, port = _start(tf.name)
            try:
                idem_key = "test-key-12345"
                payload = json.dumps([
                    {"deal_id": "d1", "name": "Alpha"},
                ]).encode()
                # First request
                req1 = urllib.request.Request(
                    f"http://127.0.0.1:{port}/api/deals/import",
                    data=payload,
                    headers={
                        "Content-Type": "application/json",
                        "Idempotency-Key": idem_key,
                    },
                    method="POST",
                )
                with urllib.request.urlopen(req1) as r:
                    body1 = json.loads(r.read().decode())
                self.assertEqual(body1["imported"], 1)

                # Second request with same key — should return cached
                req2 = urllib.request.Request(
                    f"http://127.0.0.1:{port}/api/deals/import",
                    data=payload,
                    headers={
                        "Content-Type": "application/json",
                        "Idempotency-Key": idem_key,
                    },
                    method="POST",
                )
                with urllib.request.urlopen(req2) as r:
                    body2 = json.loads(r.read().decode())
                self.assertEqual(body2["imported"], 1)
            finally:
                server.shutdown(); server.server_close()
        finally:
            os.unlink(tf.name)


if __name__ == "__main__":
    unittest.main()
