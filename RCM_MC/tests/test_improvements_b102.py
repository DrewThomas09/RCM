"""Tests for improvement pass B102: migrations endpoint, auto-run on startup.

MIGRATIONS ENDPOINT:
 1. /api/migrations returns applied list.
 2. all_applied is True after startup.

AUTO-RUN:
 3. build_server triggers migrations automatically.
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


class TestMigrationsEndpoint(unittest.TestCase):

    def test_migrations_returns_status(self):
        tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tf.close()
        try:
            server, port = _start(tf.name)
            try:
                with urllib.request.urlopen(
                    f"http://127.0.0.1:{port}/api/migrations",
                ) as r:
                    body = json.loads(r.read().decode())
                self.assertIn("total_migrations", body)
                self.assertIn("applied", body)
                self.assertIn("pending", body)
                self.assertIn("all_applied", body)
                self.assertTrue(body["all_applied"])
            finally:
                server.shutdown(); server.server_close()
        finally:
            os.unlink(tf.name)

    def test_startup_runs_migrations(self):
        tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tf.close()
        try:
            from rcm_mc.server import build_server
            s = socket.socket(); s.bind(("127.0.0.1", 0))
            port = s.getsockname()[1]; s.close()
            server, _ = build_server(port=port, db_path=tf.name)
            # After build_server, migrations should have run
            from rcm_mc.infra.migrations import list_applied
            store = PortfolioStore(tf.name)
            applied = list_applied(store)
            self.assertGreater(len(applied), 0)
            server.server_close()
        finally:
            os.unlink(tf.name)


if __name__ == "__main__":
    unittest.main()
