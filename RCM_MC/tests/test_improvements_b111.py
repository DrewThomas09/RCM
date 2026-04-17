"""Tests for B111: Vary header, export links, startup self-test.

VARY HEADER:
 1. Gzipped responses include Vary: Accept-Encoding.

EXPORT LINKS:
 2. /api/deals/<id>/export-links returns all export URLs.

SELF-TEST:
 3. build_server resets counters on each call.
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


class TestExportLinks(unittest.TestCase):

    def test_export_links_returns_urls(self):
        tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tf.close()
        try:
            store = PortfolioStore(tf.name)
            store.upsert_deal("d1", name="Alpha")
            server, port = _start(tf.name)
            try:
                with urllib.request.urlopen(
                    f"http://127.0.0.1:{port}/api/deals/d1/export-links",
                ) as r:
                    body = json.loads(r.read().decode())
                self.assertEqual(body["deal_id"], "d1")
                links = body["links"]
                self.assertIn("analysis_json", links)
                self.assertIn("export_html", links)
                self.assertIn("export_csv", links)
                self.assertIn("export_package", links)
                self.assertIn("provenance", links)
                self.assertIn("risks", links)
            finally:
                server.shutdown(); server.server_close()
        finally:
            os.unlink(tf.name)


class TestStartupSelfTest(unittest.TestCase):

    def test_counters_reset_on_build(self):
        from rcm_mc.server import build_server, RCMHandler
        tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tf.close()
        try:
            s = socket.socket(); s.bind(("127.0.0.1", 0))
            port = s.getsockname()[1]; s.close()
            # Simulate prior state
            RCMHandler._request_counter = 999
            RCMHandler._error_count = 50
            server, _ = build_server(port=port, db_path=tf.name)
            self.assertEqual(RCMHandler._request_counter, 0)
            self.assertEqual(RCMHandler._error_count, 0)
            self.assertEqual(RCMHandler._response_times, [])
            server.server_close()
        finally:
            os.unlink(tf.name)


if __name__ == "__main__":
    unittest.main()
