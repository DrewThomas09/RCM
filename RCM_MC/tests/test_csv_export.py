"""Tests for the one-click CSV export of the portfolio risk scan.

The time-saver: partner sees 8 deals needing attention and wants
to drop the list into an email or PowerPoint without copy-paste-
and-reformat. One click → CSV download with the whole scan.
"""
from __future__ import annotations

import csv
import io
import json
import os
import socket
import tempfile
import threading
import unittest
import urllib.request
from contextlib import closing
from datetime import datetime, timezone


def _free_port() -> int:
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class TestCsvExport(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.db = os.path.join(cls.tmp.name, "t.db")
        cls.port = _free_port()
        # Seed two deals so the export has rows
        from rcm_mc.portfolio.store import PortfolioStore
        store = PortfolioStore(cls.db)
        store.init_db()
        with store.connect() as con:
            for did, name in [("EXP_1", "Hospital Alpha"),
                              ("EXP_2", "Hospital Beta")]:
                con.execute(
                    "INSERT INTO deals (deal_id, name, created_at, "
                    "profile_json) VALUES (?, ?, ?, ?)",
                    (did, name,
                     datetime.now(timezone.utc).isoformat(),
                     json.dumps({"sector": "hospital"})),
                )
            con.commit()

        from rcm_mc.server import build_server
        cls.server, _ = build_server(
            port=cls.port, host="127.0.0.1",
            db_path=cls.db, auth=None,
        )
        cls.thread = threading.Thread(
            target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=5)
        cls.tmp.cleanup()

    def test_csv_endpoint_returns_csv(self):
        with urllib.request.urlopen(
            f"http://127.0.0.1:{self.port}/api/portfolio/risk-scan.csv",
            timeout=10,
        ) as resp:
            self.assertEqual(resp.status, 200)
            self.assertIn("text/csv", resp.headers.get("Content-Type", ""))
            cd = resp.headers.get("Content-Disposition", "")
            self.assertIn("attachment", cd)
            self.assertIn("risk-scan-", cd)
            body = resp.read().decode()

        # Parse it as CSV — header + 2 deal rows
        reader = csv.reader(io.StringIO(body))
        rows = list(reader)
        self.assertGreaterEqual(len(rows), 3,
                                msg="expected header + 2 deal rows, "
                                    f"got {len(rows)}")
        # Header sanity
        header = rows[0]
        for col in ("deal_id", "name", "sector", "chain",
                    "quality_rating", "health_score", "covenant_status",
                    "open_alerts"):
            self.assertIn(col, header)
        # Both seeded deals appear
        deal_ids = {r[0] for r in rows[1:]}
        self.assertIn("EXP_1", deal_ids)
        self.assertIn("EXP_2", deal_ids)

    def test_risk_scan_page_links_to_csv(self):
        with urllib.request.urlopen(
            f"http://127.0.0.1:{self.port}/portfolio/risk-scan",
            timeout=10,
        ) as resp:
            html = resp.read().decode()
        self.assertIn("/api/portfolio/risk-scan.csv", html)
        self.assertIn("Export CSV", html)


if __name__ == "__main__":
    unittest.main()
