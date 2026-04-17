"""Tests for improvement pass B105: deal counts endpoint.

COUNTS:
 1. /api/deals/<id>/counts returns badge numbers.
 2. Includes notes, tags, overrides, stage, health.
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


class TestDealCounts(unittest.TestCase):

    def test_counts_returns_badges(self):
        tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tf.close()
        try:
            store = PortfolioStore(tf.name)
            store.upsert_deal("d1", name="Alpha",
                              profile={"bed_count": 200})
            from rcm_mc.deals.deal_notes import record_note
            record_note(store, deal_id="d1", body="Test note", author="t")
            from rcm_mc.deals.deal_tags import add_tag
            add_tag(store, "d1", "priority")
            server, port = _start(tf.name)
            try:
                with urllib.request.urlopen(
                    f"http://127.0.0.1:{port}/api/deals/d1/counts",
                ) as r:
                    body = json.loads(r.read().decode())
                self.assertEqual(body["deal_id"], "d1")
                self.assertEqual(body["notes"], 1)
                self.assertEqual(body["tags"], 1)
                self.assertIn("overrides", body)
                self.assertIn("stage", body)
                self.assertIn("health_score", body)
                self.assertIn("health_band", body)
            finally:
                server.shutdown(); server.server_close()
        finally:
            os.unlink(tf.name)

    def test_counts_empty_deal(self):
        tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tf.close()
        try:
            store = PortfolioStore(tf.name)
            store.upsert_deal("d1", name="Alpha")
            server, port = _start(tf.name)
            try:
                with urllib.request.urlopen(
                    f"http://127.0.0.1:{port}/api/deals/d1/counts",
                ) as r:
                    body = json.loads(r.read().decode())
                self.assertEqual(body["notes"], 0)
                self.assertEqual(body["tags"], 0)
            finally:
                server.shutdown(); server.server_close()
        finally:
            os.unlink(tf.name)


if __name__ == "__main__":
    unittest.main()
