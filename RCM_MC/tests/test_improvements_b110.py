"""Tests for B110: CSP headers, accessibility, flaky sleep fixes.

SECURITY HEADERS:
 1. HTML responses include Content-Security-Policy.
 2. HTML responses include X-Content-Type-Options: nosniff.
 3. HTML responses include X-Frame-Options: DENY.

ACCESSIBILITY:
 4. Workbench metric icons have aria-label.
 5. Workbench action buttons have aria-label.

FLAKY SLEEPS:
 6. No test uses sleep < 0.01s.
"""
from __future__ import annotations

import glob
import os
import re
import socket
import tempfile
import threading
import time
import unittest
import urllib.request

from rcm_mc.analysis.packet import (
    DealAnalysisPacket, MetricSource, ProfileMetric,
)
from rcm_mc.ui.analysis_workbench import render_workbench


def _start(db_path):
    from rcm_mc.server import build_server
    s = socket.socket(); s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]; s.close()
    server, _ = build_server(port=port, db_path=db_path)
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start(); time.sleep(0.05)
    return server, port


class TestSecurityHeaders(unittest.TestCase):

    def test_csp_header(self):
        tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tf.close()
        try:
            server, port = _start(tf.name)
            try:
                with urllib.request.urlopen(
                    f"http://127.0.0.1:{port}/settings",
                ) as r:
                    csp = r.headers.get("Content-Security-Policy")
                    self.assertIsNotNone(csp)
                    self.assertIn("default-src", csp)
                    self.assertIn("frame-ancestors 'none'", csp)
            finally:
                server.shutdown(); server.server_close()
        finally:
            os.unlink(tf.name)

    def test_nosniff_header(self):
        tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tf.close()
        try:
            server, port = _start(tf.name)
            try:
                with urllib.request.urlopen(
                    f"http://127.0.0.1:{port}/settings",
                ) as r:
                    self.assertEqual(
                        r.headers.get("X-Content-Type-Options"), "nosniff",
                    )
            finally:
                server.shutdown(); server.server_close()
        finally:
            os.unlink(tf.name)

    def test_frame_options_header(self):
        tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tf.close()
        try:
            server, port = _start(tf.name)
            try:
                with urllib.request.urlopen(
                    f"http://127.0.0.1:{port}/settings",
                ) as r:
                    self.assertEqual(
                        r.headers.get("X-Frame-Options"), "DENY",
                    )
            finally:
                server.shutdown(); server.server_close()
        finally:
            os.unlink(tf.name)


class TestAccessibility(unittest.TestCase):

    def _packet(self):
        return DealAnalysisPacket(
            deal_id="d1", deal_name="Test",
            rcm_profile={
                "denial_rate": ProfileMetric(
                    value=12.0, source=MetricSource.OBSERVED,
                    benchmark_percentile=0.85,
                ),
            },
        )

    def test_metric_icons_have_aria_label(self):
        html = render_workbench(self._packet())
        self.assertIn('role="img"', html)
        self.assertIn('aria-label="OBSERVED"', html)

    def test_action_buttons_have_aria_label(self):
        html = render_workbench(self._packet())
        self.assertIn('aria-label="Archive this deal"', html)
        self.assertIn('aria-label="Permanently delete this deal"', html)


class TestNoFlakySleeps(unittest.TestCase):

    def test_no_sub_10ms_sleeps(self):
        pattern = re.compile(r'sleep\(0\.00[0-9]')
        test_dir = os.path.join(os.path.dirname(__file__))
        violations = []
        for path in glob.glob(os.path.join(test_dir, "test_*.py")):
            with open(path) as f:
                for i, line in enumerate(f, 1):
                    if pattern.search(line):
                        violations.append(f"{os.path.basename(path)}:{i}")
        self.assertEqual(violations, [],
                         f"Tests with sub-10ms sleeps: {violations}")


if __name__ == "__main__":
    unittest.main()
