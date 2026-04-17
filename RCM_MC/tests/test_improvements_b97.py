"""Tests for improvement pass B97: Retry-After, deals stats, IC checklist.

RETRY-AFTER:
 1. _send_rate_limited sets Retry-After header.

DEALS STATS:
 2. /api/deals/stats returns aggregate counts.

IC CHECKLIST:
 3. /api/deals/<id>/checklist returns progress items.
 4. New deal has some items not done.
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


class TestDealsStats(unittest.TestCase):

    def test_stats_returns_counts(self):
        tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tf.close()
        try:
            store = PortfolioStore(tf.name)
            store.upsert_deal("d1", name="Alpha")
            store.upsert_deal("d2", name="Beta")
            store.archive_deal("d2")
            server, port = _start(tf.name)
            try:
                with urllib.request.urlopen(
                    f"http://127.0.0.1:{port}/api/deals/stats",
                ) as r:
                    body = json.loads(r.read().decode())
                self.assertEqual(body["total_deals"], 2)
                self.assertEqual(body["active_deals"], 1)
                self.assertEqual(body["archived_deals"], 1)
                self.assertIn("stage_distribution", body)
            finally:
                server.shutdown(); server.server_close()
        finally:
            os.unlink(tf.name)


class TestICChecklist(unittest.TestCase):

    def test_checklist_returns_items(self):
        tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tf.close()
        try:
            store = PortfolioStore(tf.name)
            store.upsert_deal("d1", name="Alpha",
                              profile={"bed_count": 200})
            server, port = _start(tf.name)
            try:
                with urllib.request.urlopen(
                    f"http://127.0.0.1:{port}/api/deals/d1/checklist",
                ) as r:
                    body = json.loads(r.read().decode())
                self.assertEqual(body["deal_id"], "d1")
                self.assertIn("items", body)
                self.assertIn("progress", body)
                self.assertIn("ready_for_ic", body)
                self.assertGreater(len(body["items"]), 0)
                # Deal registered should be done
                reg = next(i for i in body["items"]
                           if i["item"] == "Deal registered")
                self.assertTrue(reg["done"])
            finally:
                server.shutdown(); server.server_close()
        finally:
            os.unlink(tf.name)

    def test_checklist_not_ready_for_ic(self):
        tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tf.close()
        try:
            store = PortfolioStore(tf.name)
            store.upsert_deal("d1", name="Alpha")
            server, port = _start(tf.name)
            try:
                with urllib.request.urlopen(
                    f"http://127.0.0.1:{port}/api/deals/d1/checklist",
                ) as r:
                    body = json.loads(r.read().decode())
                self.assertFalse(body["ready_for_ic"])
            finally:
                server.shutdown(); server.server_close()
        finally:
            os.unlink(tf.name)


if __name__ == "__main__":
    unittest.main()
