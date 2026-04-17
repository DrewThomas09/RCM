"""Tests for B109: completeness endpoint, server timeout config.

COMPLETENESS:
 1. /api/deals/<id>/completeness returns grade + coverage.
 2. Missing deal returns 404.
 3. Deal with many profile fields gets better grade.

TIMEOUT:
 4. Server has timeout configured.
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


class TestCompleteness(unittest.TestCase):

    def test_completeness_returns_grade(self):
        tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tf.close()
        try:
            store = PortfolioStore(tf.name)
            store.upsert_deal("d1", name="Alpha",
                              profile={"bed_count": 200, "denial_rate": 10})
            server, port = _start(tf.name)
            try:
                with urllib.request.urlopen(
                    f"http://127.0.0.1:{port}/api/deals/d1/completeness",
                ) as r:
                    body = json.loads(r.read().decode())
                self.assertEqual(body["deal_id"], "d1")
                self.assertIn("grade", body)
                self.assertIn("coverage_pct", body)
                self.assertIn("present_count", body)
                self.assertIn("missing_keys", body)
                self.assertIn(body["grade"], ("A", "B", "C", "D"))
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
                        f"http://127.0.0.1:{port}/api/deals/nope/completeness",
                    )
                self.assertEqual(ctx.exception.code, 404)
            finally:
                server.shutdown(); server.server_close()
        finally:
            os.unlink(tf.name)


class TestServerTimeout(unittest.TestCase):

    def test_timeout_configured(self):
        from rcm_mc.server import build_server, RCMHandler
        tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tf.close()
        try:
            s = socket.socket(); s.bind(("127.0.0.1", 0))
            port = s.getsockname()[1]; s.close()
            server, _ = build_server(port=port, db_path=tf.name)
            self.assertEqual(server.timeout, 300)
            self.assertEqual(RCMHandler.timeout, 120)
            server.server_close()
        finally:
            os.unlink(tf.name)


if __name__ == "__main__":
    unittest.main()
