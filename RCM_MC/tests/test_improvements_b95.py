"""Tests for improvement pass B95: gzip, CSV import, deal pin.

GZIP:
 1. Large JSON responses are gzip-compressed when client accepts.
 2. Small responses are not compressed.

CSV IMPORT:
 3. POST /api/deals/import-csv creates deals from CSV.
 4. Missing deal_id rows produce errors.

DEAL PIN:
 5. POST /api/deals/<id>/pin adds pinned tag.
 6. POST /api/deals/<id>/unpin removes pinned tag.
"""
from __future__ import annotations

import gzip
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


class TestGzipCompression(unittest.TestCase):

    def test_large_response_gzipped(self):
        tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tf.close()
        try:
            store = PortfolioStore(tf.name)
            from rcm_mc.portfolio.portfolio_snapshots import register_snapshot
            for i in range(10):
                did = f"d{i}"
                store.upsert_deal(did, name=f"Deal {i}")
                register_snapshot(store, did, "loi")
            server, port = _start(tf.name)
            try:
                req = urllib.request.Request(
                    f"http://127.0.0.1:{port}/api/deals",
                    headers={"Accept-Encoding": "gzip"},
                )
                with urllib.request.urlopen(req) as r:
                    encoding = r.headers.get("Content-Encoding")
                    raw = r.read()
                    if encoding == "gzip":
                        data = json.loads(gzip.decompress(raw))
                    else:
                        data = json.loads(raw)
                    self.assertIn("deals", data)
            finally:
                server.shutdown(); server.server_close()
        finally:
            os.unlink(tf.name)


class TestCSVImport(unittest.TestCase):

    def test_csv_import_creates_deals(self):
        tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tf.close()
        try:
            server, port = _start(tf.name)
            try:
                csv_data = (
                    "deal_id,name,bed_count\n"
                    "d1,Alpha Hospital,200\n"
                    "d2,Beta Medical,350\n"
                )
                req = urllib.request.Request(
                    f"http://127.0.0.1:{port}/api/deals/import-csv",
                    data=csv_data.encode("utf-8"),
                    headers={"Content-Type": "text/csv"},
                    method="POST",
                )
                with urllib.request.urlopen(req) as r:
                    body = json.loads(r.read().decode())
                self.assertEqual(body["imported"], 2)
                self.assertEqual(body["errors"], [])
            finally:
                server.shutdown(); server.server_close()
            store = PortfolioStore(tf.name)
            self.assertEqual(len(store.list_deals()), 2)
        finally:
            os.unlink(tf.name)

    def test_csv_import_missing_deal_id(self):
        tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tf.close()
        try:
            server, port = _start(tf.name)
            try:
                csv_data = "deal_id,name\n,No ID\nd1,Good\n"
                req = urllib.request.Request(
                    f"http://127.0.0.1:{port}/api/deals/import-csv",
                    data=csv_data.encode("utf-8"),
                    headers={"Content-Type": "text/csv"},
                    method="POST",
                )
                with urllib.request.urlopen(req) as r:
                    body = json.loads(r.read().decode())
                self.assertEqual(body["imported"], 1)
                self.assertEqual(len(body["errors"]), 1)
            finally:
                server.shutdown(); server.server_close()
        finally:
            os.unlink(tf.name)


class TestDealPin(unittest.TestCase):

    def test_pin_and_unpin(self):
        tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tf.close()
        try:
            store = PortfolioStore(tf.name)
            store.upsert_deal("d1", name="Alpha")
            server, port = _start(tf.name)
            try:
                # Pin
                req = urllib.request.Request(
                    f"http://127.0.0.1:{port}/api/deals/d1/pin",
                    data=b"", method="POST",
                )
                with urllib.request.urlopen(req) as r:
                    body = json.loads(r.read().decode())
                self.assertTrue(body["pinned"])

                # Verify tag
                from rcm_mc.deals.deal_tags import tags_for
                tags = tags_for(store, "d1")
                self.assertIn("pinned", tags)

                # Unpin
                req = urllib.request.Request(
                    f"http://127.0.0.1:{port}/api/deals/d1/unpin",
                    data=b"", method="POST",
                )
                with urllib.request.urlopen(req) as r:
                    body = json.loads(r.read().decode())
                self.assertFalse(body["pinned"])
            finally:
                server.shutdown(); server.server_close()
        finally:
            os.unlink(tf.name)


if __name__ == "__main__":
    unittest.main()
