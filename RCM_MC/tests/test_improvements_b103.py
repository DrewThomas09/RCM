"""Tests for improvement pass B103: diligence package, deal search.

DILIGENCE PACKAGE:
 1. /api/deals/<id>/package returns a zip file.

DEAL SEARCH:
 2. /api/deals/search?q=alpha finds matching deals.
 3. Empty query returns empty results.
 4. Search is case-insensitive.
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

from rcm_mc.portfolio.store import PortfolioStore


def _start(db_path):
    from rcm_mc.server import build_server
    s = socket.socket(); s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]; s.close()
    server, _ = build_server(port=port, db_path=db_path)
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start(); time.sleep(0.05)
    return server, port


class TestDealSearch(unittest.TestCase):

    def test_search_finds_deal(self):
        tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tf.close()
        try:
            store = PortfolioStore(tf.name)
            store.upsert_deal("d1", name="Alpha Hospital")
            store.upsert_deal("d2", name="Beta Medical")
            server, port = _start(tf.name)
            try:
                with urllib.request.urlopen(
                    f"http://127.0.0.1:{port}/api/deals/search?q=alpha",
                ) as r:
                    body = json.loads(r.read().decode())
                self.assertEqual(body["count"], 1)
                self.assertEqual(body["results"][0]["deal_id"], "d1")
            finally:
                server.shutdown(); server.server_close()
        finally:
            os.unlink(tf.name)

    def test_empty_query(self):
        tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tf.close()
        try:
            server, port = _start(tf.name)
            try:
                with urllib.request.urlopen(
                    f"http://127.0.0.1:{port}/api/deals/search?q=",
                ) as r:
                    body = json.loads(r.read().decode())
                self.assertEqual(body["results"], [])
            finally:
                server.shutdown(); server.server_close()
        finally:
            os.unlink(tf.name)

    def test_case_insensitive(self):
        tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tf.close()
        try:
            store = PortfolioStore(tf.name)
            store.upsert_deal("d1", name="ALPHA HOSPITAL")
            server, port = _start(tf.name)
            try:
                with urllib.request.urlopen(
                    f"http://127.0.0.1:{port}/api/deals/search?q=alpha",
                ) as r:
                    body = json.loads(r.read().decode())
                self.assertEqual(body["count"], 1)
            finally:
                server.shutdown(); server.server_close()
        finally:
            os.unlink(tf.name)


class TestDiligencePackage(unittest.TestCase):

    def test_package_returns_zip(self):
        tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tf.close()
        try:
            store = PortfolioStore(tf.name)
            store.upsert_deal("d1", name="Alpha Hospital",
                              profile={"bed_count": 200})
            server, port = _start(tf.name)
            try:
                with urllib.request.urlopen(
                    f"http://127.0.0.1:{port}/api/deals/d1/package",
                ) as r:
                    self.assertEqual(r.status, 200)
                    ct = r.headers.get("Content-Type")
                    self.assertIn("zip", ct)
                    cd = r.headers.get("Content-Disposition")
                    self.assertIn("package.zip", cd)
                    data = r.read()
                    # ZIP files start with PK magic bytes
                    self.assertTrue(data[:2] == b"PK")
            finally:
                server.shutdown(); server.server_close()
        finally:
            os.unlink(tf.name)


if __name__ == "__main__":
    unittest.main()
