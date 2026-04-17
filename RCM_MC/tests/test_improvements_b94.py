"""Tests for improvement pass B94: backup, system info, deal import.

BACKUP:
 1. GET /api/backup returns SQLite file.

SYSTEM INFO:
 2. GET /api/system/info returns version and stats.

DEAL IMPORT:
 3. POST /api/deals/import creates deals.
 4. Empty array returns 400.
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


class TestBackupEndpoint(unittest.TestCase):

    def test_backup_returns_sqlite(self):
        tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tf.close()
        try:
            store = PortfolioStore(tf.name)
            store.upsert_deal("d1", name="Test")
            server, port = _start(tf.name)
            try:
                with urllib.request.urlopen(
                    f"http://127.0.0.1:{port}/api/backup",
                ) as r:
                    self.assertEqual(r.status, 200)
                    ct = r.headers.get("Content-Type")
                    self.assertIn("sqlite", ct)
                    cd = r.headers.get("Content-Disposition")
                    self.assertIn("rcm_mc_backup.db", cd)
                    data = r.read()
                    # SQLite files start with "SQLite format 3"
                    self.assertTrue(data[:16].startswith(b"SQLite format 3"))
            finally:
                server.shutdown(); server.server_close()
        finally:
            os.unlink(tf.name)


class TestSystemInfo(unittest.TestCase):

    def test_system_info_returns_stats(self):
        tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tf.close()
        try:
            store = PortfolioStore(tf.name)
            store.upsert_deal("d1", name="Test")
            server, port = _start(tf.name)
            try:
                with urllib.request.urlopen(
                    f"http://127.0.0.1:{port}/api/system/info",
                ) as r:
                    body = json.loads(r.read().decode())
                self.assertIn("version", body)
                self.assertIn("python_version", body)
                self.assertIn("db_size_mb", body)
                self.assertIn("table_count", body)
                self.assertIn("deal_count", body)
                self.assertEqual(body["deal_count"], 1)
                self.assertGreater(body["table_count"], 0)
            finally:
                server.shutdown(); server.server_close()
        finally:
            os.unlink(tf.name)


class TestDealImport(unittest.TestCase):

    def test_import_creates_deals(self):
        tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tf.close()
        try:
            server, port = _start(tf.name)
            try:
                req = urllib.request.Request(
                    f"http://127.0.0.1:{port}/api/deals/import",
                    data=json.dumps([
                        {"deal_id": "d1", "name": "Alpha",
                         "profile": {"bed_count": 200}},
                        {"deal_id": "d2", "name": "Beta",
                         "profile": {"bed_count": 300}},
                    ]).encode(),
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                with urllib.request.urlopen(req) as r:
                    body = json.loads(r.read().decode())
                self.assertEqual(body["imported"], 2)
                self.assertEqual(set(body["deal_ids"]), {"d1", "d2"})
            finally:
                server.shutdown(); server.server_close()
            # Verify deals exist
            store = PortfolioStore(tf.name)
            deals = store.list_deals()
            self.assertEqual(len(deals), 2)
        finally:
            os.unlink(tf.name)

    def test_import_empty_400(self):
        tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tf.close()
        try:
            server, port = _start(tf.name)
            try:
                req = urllib.request.Request(
                    f"http://127.0.0.1:{port}/api/deals/import",
                    data=b"[]",
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
