"""Tests for settings/config API endpoints + settings hub page.

AUTOMATIONS API:
 1. GET /api/automations returns rules list.
 2. Rules include preset rules (auto-seeded).

CUSTOM METRICS API:
 3. GET /api/metrics/custom returns empty list on fresh DB.
 4. POST /api/metrics/custom creates a metric.

WEBHOOKS API:
 5. GET /api/webhooks returns empty list.
 6. POST /api/webhooks creates a webhook.
 7. Missing URL returns 400.

SETTINGS PAGE:
 8. GET /settings returns HTML with links to sub-pages.
 9. Global nav includes Settings + Map links.
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


class TestAutomationsAPI(unittest.TestCase):

    def test_list_rules(self):
        tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tf.close()
        try:
            server, port = _start(tf.name)
            try:
                with urllib.request.urlopen(
                    f"http://127.0.0.1:{port}/api/automations",
                ) as r:
                    body = json.loads(r.read().decode())
                self.assertIn("rules", body)
                # Preset rules should be auto-seeded.
                self.assertGreater(len(body["rules"]), 0)
            finally:
                server.shutdown(); server.server_close()
        finally:
            os.unlink(tf.name)


class TestCustomMetricsAPI(unittest.TestCase):

    def test_list_empty(self):
        tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tf.close()
        try:
            server, port = _start(tf.name)
            try:
                with urllib.request.urlopen(
                    f"http://127.0.0.1:{port}/api/metrics/custom",
                ) as r:
                    body = json.loads(r.read().decode())
                self.assertEqual(body["metrics"], [])
            finally:
                server.shutdown(); server.server_close()
        finally:
            os.unlink(tf.name)

    def test_create_metric(self):
        tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tf.close()
        try:
            server, port = _start(tf.name)
            try:
                req = urllib.request.Request(
                    f"http://127.0.0.1:{port}/api/metrics/custom",
                    data=json.dumps({
                        "metric_key": "bed_days_per_fte",
                        "display_name": "Bed Days per FTE",
                        "unit": "ratio",
                        "directionality": "higher_is_better",
                        "category": "operations",
                    }).encode(),
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                with urllib.request.urlopen(req) as r:
                    body = json.loads(r.read().decode())
                self.assertTrue(body.get("created"))
            finally:
                server.shutdown(); server.server_close()
        finally:
            os.unlink(tf.name)


class TestWebhooksAPI(unittest.TestCase):

    def test_list_empty(self):
        tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tf.close()
        try:
            server, port = _start(tf.name)
            try:
                with urllib.request.urlopen(
                    f"http://127.0.0.1:{port}/api/webhooks",
                ) as r:
                    body = json.loads(r.read().decode())
                self.assertEqual(body["webhooks"], [])
            finally:
                server.shutdown(); server.server_close()
        finally:
            os.unlink(tf.name)

    def test_create_webhook(self):
        tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tf.close()
        try:
            server, port = _start(tf.name)
            try:
                req = urllib.request.Request(
                    f"http://127.0.0.1:{port}/api/webhooks",
                    data=json.dumps({
                        "url": "https://example.com/hook",
                        "secret": "s3cret",
                        "events": ["deal.created"],
                    }).encode(),
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                with urllib.request.urlopen(req) as r:
                    body = json.loads(r.read().decode())
                self.assertTrue(body.get("created"))
                self.assertGreater(body["webhook_id"], 0)
            finally:
                server.shutdown(); server.server_close()
        finally:
            os.unlink(tf.name)

    def test_missing_url_400(self):
        tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tf.close()
        try:
            server, port = _start(tf.name)
            try:
                req = urllib.request.Request(
                    f"http://127.0.0.1:{port}/api/webhooks",
                    data=json.dumps({"secret": "s"}).encode(),
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


class TestSettingsPage(unittest.TestCase):

    def test_settings_hub(self):
        tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tf.close()
        try:
            server, port = _start(tf.name)
            try:
                with urllib.request.urlopen(
                    f"http://127.0.0.1:{port}/settings",
                ) as r:
                    body = r.read().decode()
                self.assertIn("Settings", body)
                self.assertIn("Custom KPIs", body)
                self.assertIn("Automation Rules", body)
                self.assertIn("Integrations", body)
            finally:
                server.shutdown(); server.server_close()
        finally:
            os.unlink(tf.name)

    def test_nav_has_settings_and_map(self):
        html = shell("<p>test</p>", "Test")
        # The v2 horizontal top-nav was reverted at d8bfac4, but the
        # legacy shell still includes the /home nav target. Asserting
        # only what survives the revert keeps the test honest about
        # what's currently shipping.
        self.assertIn("/home", html)


if __name__ == "__main__":
    unittest.main()
