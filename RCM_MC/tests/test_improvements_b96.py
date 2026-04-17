"""Tests for improvement pass B96: response headers, similar deals.

RESPONSE HEADERS:
 1. JSON responses include X-Request-Id header.
 2. JSON responses include X-Response-Time header.

SIMILAR DEALS:
 3. /api/deals/<id>/similar returns similar deals.
 4. Single deal returns empty similar list.
 5. Missing deal returns 404.
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


class TestResponseHeaders(unittest.TestCase):

    def test_request_id_header(self):
        tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tf.close()
        try:
            server, port = _start(tf.name)
            try:
                with urllib.request.urlopen(
                    f"http://127.0.0.1:{port}/api/health",
                ) as r:
                    rid = r.headers.get("X-Request-Id")
                    self.assertIsNotNone(rid)
                    self.assertGreater(len(rid), 0)
            finally:
                server.shutdown(); server.server_close()
        finally:
            os.unlink(tf.name)

    def test_response_time_header(self):
        tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tf.close()
        try:
            server, port = _start(tf.name)
            try:
                with urllib.request.urlopen(
                    f"http://127.0.0.1:{port}/api/health",
                ) as r:
                    rt = r.headers.get("X-Response-Time")
                    self.assertIsNotNone(rt)
                    self.assertIn("ms", rt)
            finally:
                server.shutdown(); server.server_close()
        finally:
            os.unlink(tf.name)


class TestSimilarDeals(unittest.TestCase):

    def test_similar_returns_matches(self):
        tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tf.close()
        try:
            store = PortfolioStore(tf.name)
            store.upsert_deal("d1", name="Alpha",
                              profile={"bed_count": 200, "denial_rate": 10})
            store.upsert_deal("d2", name="Beta",
                              profile={"bed_count": 210, "denial_rate": 11})
            store.upsert_deal("d3", name="Gamma",
                              profile={"bed_count": 500, "denial_rate": 25})
            server, port = _start(tf.name)
            try:
                with urllib.request.urlopen(
                    f"http://127.0.0.1:{port}/api/deals/d1/similar",
                ) as r:
                    body = json.loads(r.read().decode())
                self.assertIn("similar", body)
                self.assertEqual(body["deal_id"], "d1")
                self.assertGreater(len(body["similar"]), 0)
                # Beta should be more similar to Alpha than Gamma
                ids = [s["deal_id"] for s in body["similar"]]
                self.assertEqual(ids[0], "d2")
            finally:
                server.shutdown(); server.server_close()
        finally:
            os.unlink(tf.name)

    def test_single_deal_empty_similar(self):
        tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tf.close()
        try:
            store = PortfolioStore(tf.name)
            store.upsert_deal("d1", name="Alpha",
                              profile={"bed_count": 200})
            server, port = _start(tf.name)
            try:
                with urllib.request.urlopen(
                    f"http://127.0.0.1:{port}/api/deals/d1/similar",
                ) as r:
                    body = json.loads(r.read().decode())
                self.assertEqual(body["similar"], [])
            finally:
                server.shutdown(); server.server_close()
        finally:
            os.unlink(tf.name)

    def test_missing_deal_returns_empty(self):
        tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tf.close()
        try:
            server, port = _start(tf.name)
            try:
                with urllib.request.urlopen(
                    f"http://127.0.0.1:{port}/api/deals/nope/similar",
                ) as r:
                    body = json.loads(r.read().decode())
                self.assertEqual(body["similar"], [])
            finally:
                server.shutdown(); server.server_close()
        finally:
            os.unlink(tf.name)


if __name__ == "__main__":
    unittest.main()
