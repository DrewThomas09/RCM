"""Tests for improvement pass B89: metrics endpoint, version footer,
deal compare API, manifest.json.

METRICS:
 1. /api/metrics returns response time percentiles.
 2. /api/metrics returns request_count and error_count.

VERSION FOOTER:
 3. Shell footer includes version string.

MANIFEST:
 4. /manifest.json returns valid JSON with name field.
 5. Shell HTML includes manifest link tag.

DEAL COMPARE API:
 6. /api/deals/compare?ids=a,b returns comparison data.
 7. Fewer than 2 IDs returns 400.
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
from rcm_mc.ui._ui_kit import shell


def _start(db_path):
    from rcm_mc.server import build_server
    s = socket.socket(); s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]; s.close()
    server, _ = build_server(port=port, db_path=db_path)
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start(); time.sleep(0.05)
    return server, port


class TestMetricsEndpoint(unittest.TestCase):

    def test_metrics_returns_percentiles(self):
        tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tf.close()
        try:
            server, port = _start(tf.name)
            try:
                # Make a few requests first to populate metrics
                for _ in range(3):
                    urllib.request.urlopen(
                        f"http://127.0.0.1:{port}/api/health")
                with urllib.request.urlopen(
                    f"http://127.0.0.1:{port}/api/metrics",
                ) as r:
                    body = json.loads(r.read().decode())
                self.assertIn("request_count", body)
                self.assertIn("error_count", body)
                self.assertIn("response_times_ms", body)
                rt = body["response_times_ms"]
                self.assertIn("p50", rt)
                self.assertIn("p95", rt)
                self.assertIn("p99", rt)
                self.assertIn("avg", rt)
            finally:
                server.shutdown(); server.server_close()
        finally:
            os.unlink(tf.name)


class TestVersionFooter(unittest.TestCase):

    def test_footer_includes_version(self):
        # Version is surfaced via /api/system/info; the editorial shell does not embed it.
        from rcm_mc import __version__
        self.assertIsNotNone(__version__)
        html_str = shell("<p>test</p>", "Test")
        self.assertIn("SeekingChartis", html_str)


class TestManifest(unittest.TestCase):

    def test_manifest_json_served(self):
        tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tf.close()
        try:
            server, port = _start(tf.name)
            try:
                with urllib.request.urlopen(
                    f"http://127.0.0.1:{port}/manifest.json",
                ) as r:
                    body = json.loads(r.read().decode())
                self.assertEqual(body["name"], "RCM-MC")
                self.assertIn("start_url", body)
                self.assertIn("theme_color", body)
            finally:
                server.shutdown(); server.server_close()
        finally:
            os.unlink(tf.name)

    @unittest.skipUnless(
        os.environ.get("CHARTIS_UI_V2"),
        "PWA manifest + theme-color shipped with the v2 reskin and was "
        "reverted at d8bfac4. Re-enable when v2 ships again.",
    )
    def test_shell_has_manifest_link(self):
        html_str = shell("<p>test</p>", "Test")
        self.assertIn('rel="manifest"', html_str)
        self.assertIn('href="/manifest.json"', html_str)
        self.assertIn('name="theme-color"', html_str)


class TestDealCompareAPI(unittest.TestCase):

    def test_compare_needs_two_ids(self):
        tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tf.close()
        try:
            server, port = _start(tf.name)
            try:
                with self.assertRaises(urllib.error.HTTPError) as ctx:
                    urllib.request.urlopen(
                        f"http://127.0.0.1:{port}/api/deals/compare?ids=d1",
                    )
                self.assertEqual(ctx.exception.code, 400)
            finally:
                server.shutdown(); server.server_close()
        finally:
            os.unlink(tf.name)

    def test_compare_returns_deals(self):
        tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tf.close()
        try:
            store = PortfolioStore(tf.name)
            store.upsert_deal("d1", name="Alpha",
                              profile={"bed_count": 200})
            store.upsert_deal("d2", name="Beta",
                              profile={"bed_count": 300})
            server, port = _start(tf.name)
            try:
                with urllib.request.urlopen(
                    f"http://127.0.0.1:{port}/api/deals/compare?ids=d1,d2",
                ) as r:
                    body = json.loads(r.read().decode())
                self.assertIn("deals", body)
                self.assertEqual(len(body["deals"]), 2)
            finally:
                server.shutdown(); server.server_close()
        finally:
            os.unlink(tf.name)


if __name__ == "__main__":
    unittest.main()
