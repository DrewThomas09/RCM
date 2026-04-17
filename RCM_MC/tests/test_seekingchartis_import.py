"""Tests for SeekingChartis quick import and final shell_v2 migration.

QUICK IMPORT:
 1. GET /import renders form with shell_v2.
 2. POST /quick-import creates a deal and redirects.
 3. POST /quick-import-json imports from JSON.

ALL SHELL_V2:
 4. Every page returns 200 with cad-topbar.
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
import urllib.parse

from rcm_mc.portfolio.store import PortfolioStore


def _start(db_path):
    from rcm_mc.server import build_server
    s = socket.socket(); s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]; s.close()
    server, _ = build_server(port=port, db_path=db_path)
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start(); time.sleep(0.05)
    return server, port


class TestQuickImport(unittest.TestCase):

    def test_import_page_renders(self):
        tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tf.close()
        try:
            server, port = _start(tf.name)
            try:
                with urllib.request.urlopen(
                    f"http://127.0.0.1:{port}/import",
                ) as r:
                    body = r.read().decode()
                self.assertIn("Import Deals", body)
                self.assertIn("SeekingChartis", body)
                self.assertIn("cad-topbar", body)
                self.assertIn("deal_id", body)
                self.assertIn("denial_rate", body)
                self.assertIn("Bulk Import", body)
            finally:
                server.shutdown(); server.server_close()
        finally:
            os.unlink(tf.name)

    def test_quick_import_creates_deal(self):
        tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tf.close()
        try:
            server, port = _start(tf.name)
            try:
                data = urllib.parse.urlencode({
                    "deal_id": "test_import",
                    "name": "Test Import Hospital",
                    "denial_rate": "15.5",
                    "days_in_ar": "48",
                    "net_revenue": "200000000",
                    "bed_count": "250",
                }).encode()
                req = urllib.request.Request(
                    f"http://127.0.0.1:{port}/quick-import",
                    data=data, method="POST",
                )
                with urllib.request.urlopen(req) as r:
                    self.assertEqual(r.status, 200)

                store = PortfolioStore(tf.name)
                deals = store.list_deals()
                self.assertFalse(deals.empty)
                self.assertIn("test_import", deals["deal_id"].values)
            finally:
                server.shutdown(); server.server_close()
        finally:
            os.unlink(tf.name)

    def test_quick_import_json(self):
        tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tf.close()
        try:
            server, port = _start(tf.name)
            try:
                json_data = json.dumps([
                    {"deal_id": "j1", "name": "JSON Hospital 1",
                     "profile": {"denial_rate": 12}},
                    {"deal_id": "j2", "name": "JSON Hospital 2",
                     "profile": {"denial_rate": 18}},
                ])
                data = urllib.parse.urlencode({
                    "json_data": json_data,
                }).encode()
                req = urllib.request.Request(
                    f"http://127.0.0.1:{port}/quick-import-json",
                    data=data, method="POST",
                )
                with urllib.request.urlopen(req) as r:
                    body = r.read().decode()
                self.assertIn("Successfully imported 2", body)

                store = PortfolioStore(tf.name)
                deals = store.list_deals()
                self.assertEqual(len(deals), 2)
            finally:
                server.shutdown(); server.server_close()
        finally:
            os.unlink(tf.name)


class TestAllPagesShellV2(unittest.TestCase):

    def test_every_page_has_cad_topbar(self):
        tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tf.close()
        try:
            server, port = _start(tf.name)
            try:
                pages = [
                    "/home", "/analysis", "/news", "/market-data/map",
                    "/screen", "/portfolio", "/library", "/settings",
                    "/runs", "/scenarios", "/calibration", "/source",
                    "/portfolio/regression", "/import",
                    "/settings/custom-kpis", "/settings/automations",
                    "/settings/integrations", "/surrogate", "/pressure",
                ]
                for path in pages:
                    with self.subTest(path=path):
                        with urllib.request.urlopen(
                            f"http://127.0.0.1:{port}{path}",
                        ) as r:
                            self.assertEqual(r.status, 200)
                            body = r.read().decode()
                            self.assertIn("cad-topbar", body,
                                          f"{path} missing cad-topbar")
                            self.assertIn("SeekingChartis", body,
                                          f"{path} missing SeekingChartis")
            finally:
                server.shutdown(); server.server_close()
        finally:
            os.unlink(tf.name)


if __name__ == "__main__":
    unittest.main()
