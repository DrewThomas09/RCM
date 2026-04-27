"""End-to-end test for /models/importance (campaign target 2 — bespoke -> v3).

Boots a real ThreadingHTTPServer and hits /models/importance via
urllib.request. The empty-state branch is enough to verify the
migration: page goes through chartis_shell, no bespoke wrapper, no
bare hardcoded dark palette outside of var() fallbacks.

What this guards (per Phase 2 per-page checklist):
  - shell() with no bespoke wrapper: chartis_shell <title> present.
  - v3 chartis.css tokens: at least one .micro utility class on
    the eyebrow link.
  - Empty-state path renders without crashing.
  - No bare-literal #1f2937 / #374151 / #f3f4f6 in body content
    (they are allowed only inside var(--name,#fallback)).
  - The SVG bar chart fill/stroke literals are explicitly NOT
    checked — those are semantic STATUS colors and stay inline.
"""
from __future__ import annotations

import os
import re
import socket as _socket
import tempfile
import threading
import time as _time
import unittest
import urllib.request as _u

from rcm_mc.server import build_server


def _free_port() -> int:
    s = _socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


class FeatureImportancePageTests(unittest.TestCase):
    def _start(self, tmp: str):
        port = _free_port()
        server, _ = build_server(port=port, db_path=os.path.join(tmp, "p.db"))
        t = threading.Thread(target=server.serve_forever, daemon=True)
        t.start()
        _time.sleep(0.05)
        return server, port

    def test_page_returns_200_and_routes_through_shell(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            server, port = self._start(tmp)
            try:
                with _u.urlopen(f"http://127.0.0.1:{port}/models/importance") as r:
                    self.assertEqual(r.status, 200)
                    body = r.read().decode("utf-8")
                self.assertIn("<title>Feature Importance", body)
                self.assertIn("<h1", body)
                self.assertIn("Feature Importance", body)
            finally:
                server.shutdown()
                server.server_close()

    def test_page_carries_v3_micro_utility_class(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            server, port = self._start(tmp)
            try:
                with _u.urlopen(f"http://127.0.0.1:{port}/models/importance") as r:
                    body = r.read().decode("utf-8")
                self.assertIn('class="micro"', body)
            finally:
                server.shutdown()
                server.server_close()

    def test_page_renders_either_models_or_empty_state(self) -> None:
        """Default install runs the synthetic-data panel builder
        which produces three models (denial / days-in-AR / collection
        rate). If training fails for any reason, the empty-state
        branch fires with the importance_from_trained_ridge hint.
        Both renders are valid; this just asserts neither path
        crashes the page."""
        with tempfile.TemporaryDirectory() as tmp:
            server, port = self._start(tmp)
            try:
                with _u.urlopen(f"http://127.0.0.1:{port}/models/importance") as r:
                    body = r.read().decode("utf-8")
                rendered_models = any(
                    name in body for name in (
                        "Denial Rate Predictor",
                        "Days in AR Predictor",
                        "Collection Rate Predictor",
                    )
                )
                rendered_empty = "importance_from_trained_ridge" in body
                self.assertTrue(
                    rendered_models or rendered_empty,
                    "page rendered neither a model panel nor the empty state",
                )
            finally:
                server.shutdown()
                server.server_close()

    def test_page_emits_no_bare_legacy_palette_in_body_chrome(self) -> None:
        """The body/chrome (non-SVG) markup must not contain bare
        legacy hex literals. SVG fill/stroke literals from the bar
        chart are allowed because they're semantic status colors
        (colors.STATUS) tied to feature-importance direction."""
        with tempfile.TemporaryDirectory() as tmp:
            server, port = self._start(tmp)
            try:
                with _u.urlopen(f"http://127.0.0.1:{port}/models/importance") as r:
                    body = r.read().decode("utf-8")
                # Strip well-formed var(--name,#fallback) before checking.
                stripped = re.sub(r"var\(--[a-z-]+,\s*#[0-9a-fA-F]{3,8}\)", "", body)
                # Strip SVG element opening tags + their attributes (semantic
                # status colors stay there) so we only check the chrome.
                stripped = re.sub(r"<svg[^>]*>.*?</svg>", "", stripped, flags=re.S)
                for legacy in ("#1f2937", "#374151", "#f3f4f6"):
                    self.assertNotIn(
                        legacy, stripped,
                        f"bare legacy palette literal {legacy} still in chrome",
                    )
            finally:
                server.shutdown()
                server.server_close()


if __name__ == "__main__":
    unittest.main()
