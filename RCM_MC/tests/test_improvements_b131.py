"""Tests for B131: memo generation API.

 1. /api/deals/<id>/memo returns template-based sections.
 2. Response includes fact_check_warnings and cost.
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


class TestMemoAPI(unittest.TestCase):

    def test_memo_returns_sections(self):
        tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tf.close()
        try:
            store = PortfolioStore(tf.name)
            store.upsert_deal("d1", name="Alpha Hospital",
                              profile={"bed_count": 200, "denial_rate": 12})
            server, port = _start(tf.name)
            try:
                with urllib.request.urlopen(
                    f"http://127.0.0.1:{port}/api/deals/d1/memo",
                ) as r:
                    body = json.loads(r.read().decode())
                self.assertEqual(body["deal_id"], "d1")
                self.assertIn("sections", body)
                self.assertIn("fact_check_warnings", body)
                self.assertIn("cost_usd", body)
                self.assertFalse(body["llm_used"])
                self.assertGreater(len(body["sections"]), 0)
            finally:
                server.shutdown(); server.server_close()
        finally:
            os.unlink(tf.name)


if __name__ == "__main__":
    unittest.main()
