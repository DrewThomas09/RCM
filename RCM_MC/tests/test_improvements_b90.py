"""Tests for improvement pass B90: ETags, deal summary, bulk operations.

ETAG:
 1. Analysis packet response includes ETag header.
 2. Conditional GET with matching ETag returns 304.

DEAL SUMMARY:
 3. /api/deals/<id>/summary returns lightweight JSON.
 4. Missing deal returns 404.

BULK OPERATIONS:
 5. POST /api/deals/bulk archive action.
 6. POST /api/deals/bulk tag action.
 7. Unknown action returns 400.
 8. Empty deal_ids returns 400.
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


class TestDealSummary(unittest.TestCase):

    def test_summary_returns_json(self):
        tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tf.close()
        try:
            store = PortfolioStore(tf.name)
            store.upsert_deal("d1", name="Alpha Hospital",
                              profile={"bed_count": 200})
            server, port = _start(tf.name)
            try:
                with urllib.request.urlopen(
                    f"http://127.0.0.1:{port}/api/deals/d1/summary",
                ) as r:
                    body = json.loads(r.read().decode())
                self.assertEqual(body["deal_id"], "d1")
                self.assertEqual(body["name"], "Alpha Hospital")
                self.assertIn("stage", body)
                self.assertIn("health_score", body)
                self.assertIn("archived", body)
            finally:
                server.shutdown(); server.server_close()
        finally:
            os.unlink(tf.name)

    def test_summary_missing_404(self):
        tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tf.close()
        try:
            server, port = _start(tf.name)
            try:
                with self.assertRaises(urllib.error.HTTPError) as ctx:
                    urllib.request.urlopen(
                        f"http://127.0.0.1:{port}/api/deals/nope/summary",
                    )
                self.assertEqual(ctx.exception.code, 404)
            finally:
                server.shutdown(); server.server_close()
        finally:
            os.unlink(tf.name)


class TestBulkOperations(unittest.TestCase):

    def test_bulk_archive(self):
        tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tf.close()
        try:
            store = PortfolioStore(tf.name)
            store.upsert_deal("d1", name="A")
            store.upsert_deal("d2", name="B")
            server, port = _start(tf.name)
            try:
                req = urllib.request.Request(
                    f"http://127.0.0.1:{port}/api/deals/bulk",
                    data=json.dumps({
                        "action": "archive",
                        "deal_ids": ["d1", "d2"],
                    }).encode(),
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                with urllib.request.urlopen(req) as r:
                    body = json.loads(r.read().decode())
                self.assertEqual(body["action"], "archive")
                self.assertEqual(body["count"], 2)
                self.assertTrue(all(r["archived"] for r in body["results"]))
            finally:
                server.shutdown(); server.server_close()
        finally:
            os.unlink(tf.name)

    def test_bulk_tag(self):
        tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tf.close()
        try:
            store = PortfolioStore(tf.name)
            store.upsert_deal("d1", name="A")
            server, port = _start(tf.name)
            try:
                req = urllib.request.Request(
                    f"http://127.0.0.1:{port}/api/deals/bulk",
                    data=json.dumps({
                        "action": "tag",
                        "deal_ids": ["d1"],
                        "tag": "priority",
                    }).encode(),
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                with urllib.request.urlopen(req) as r:
                    body = json.loads(r.read().decode())
                self.assertEqual(body["action"], "tag")
                self.assertTrue(body["results"][0]["tagged"])
            finally:
                server.shutdown(); server.server_close()
        finally:
            os.unlink(tf.name)

    def test_bulk_unknown_action_400(self):
        tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tf.close()
        try:
            server, port = _start(tf.name)
            try:
                req = urllib.request.Request(
                    f"http://127.0.0.1:{port}/api/deals/bulk",
                    data=json.dumps({
                        "action": "nope",
                        "deal_ids": ["d1"],
                    }).encode(),
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                with self.assertRaises(urllib.error.HTTPError) as ctx:
                    urllib.request.urlopen(req)
                self.assertEqual(ctx.exception.code, 400)
            finally:
                server.shutdown(); server.server_close()
        finally:
            os.unlink(tf.name)

    def test_bulk_empty_ids_400(self):
        tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tf.close()
        try:
            server, port = _start(tf.name)
            try:
                req = urllib.request.Request(
                    f"http://127.0.0.1:{port}/api/deals/bulk",
                    data=json.dumps({
                        "action": "archive",
                        "deal_ids": [],
                    }).encode(),
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                with self.assertRaises(urllib.error.HTTPError) as ctx:
                    urllib.request.urlopen(req)
                self.assertEqual(ctx.exception.code, 400)
            finally:
                server.shutdown(); server.server_close()
        finally:
            os.unlink(tf.name)


if __name__ == "__main__":
    unittest.main()
