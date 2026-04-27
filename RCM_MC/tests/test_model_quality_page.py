"""End-to-end test for /models/quality (campaign target 2 — bespoke -> v3).

Closes the bespoke -> v3 migration sub-batch. After this loop, the
inventory's bespoke count should be 0.

What this guards (per Phase 2 per-page checklist):
  - shell() with no bespoke wrapper: chartis_shell <title> present.
  - v3 chartis.css tokens: at least one .micro utility class.
  - Empty-state path renders without crashing and points at the
    run_model_quality_panel CLI hint.
  - No bare-literal #1f2937 / #374151 / #f3f4f6 in body chrome
    (allowed only inside var() fallbacks). Grade/calibration badge
    inline colors are explicitly NOT checked — those are semantic
    STATUS palette ties to the data and stay inline.
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


class ModelQualityPageTests(unittest.TestCase):
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
                with _u.urlopen(f"http://127.0.0.1:{port}/models/quality") as r:
                    self.assertEqual(r.status, 200)
                    body = r.read().decode("utf-8")
                self.assertIn("<title>Model Quality", body)
                self.assertIn("<h1", body)
                self.assertIn("Model Quality", body)
            finally:
                server.shutdown()
                server.server_close()

    def test_page_carries_v3_micro_utility_class(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            server, port = self._start(tmp)
            try:
                with _u.urlopen(f"http://127.0.0.1:{port}/models/quality") as r:
                    body = r.read().decode("utf-8")
                self.assertIn('class="micro"', body)
            finally:
                server.shutdown()
                server.server_close()

    def test_page_renders_either_models_or_empty_state(self) -> None:
        """Default install runs the synthetic-data backtest panel
        which produces three predictors (denial / days-in-AR /
        collection rate). If the panel is empty for any reason, the
        empty-state branch fires with the run_model_quality_panel
        hint. Both renders are valid."""
        with tempfile.TemporaryDirectory() as tmp:
            server, port = self._start(tmp)
            try:
                with _u.urlopen(f"http://127.0.0.1:{port}/models/quality") as r:
                    body = r.read().decode("utf-8")
                rendered_models = any(
                    keyword in body for keyword in (
                        "Avg CV R²",
                        "Models tracked",
                    )
                )
                rendered_empty = "run_model_quality_panel" in body
                self.assertTrue(
                    rendered_models or rendered_empty,
                    "page rendered neither a backtest panel nor the empty state",
                )
            finally:
                server.shutdown()
                server.server_close()

    def test_page_emits_no_bare_legacy_palette_in_chrome(self) -> None:
        """The body/chrome must not contain bare legacy hex literals.
        Grade/calibration badge inline colors come from
        rcm_mc/ui/colors.STATUS and are part of the data signal —
        those stay inline and are NOT checked here.

        Strategy: strip well-formed var(--name,#fallback), then strip
        attributes inside <span> tags carrying a class or backed by
        STATUS-colored grade/calibration badges. What remains is the
        chrome; assert no #1f2937 / #374151 / #f3f4f6 in it.
        """
        with tempfile.TemporaryDirectory() as tmp:
            server, port = self._start(tmp)
            try:
                with _u.urlopen(f"http://127.0.0.1:{port}/models/quality") as r:
                    body = r.read().decode("utf-8")
                stripped = re.sub(r"var\(--[a-z-]+,\s*#[0-9a-fA-F]{3,8}\)", "", body)
                # Strip the inline-styled badge spans (grade + calibration)
                # so semantic STATUS palette literals don't trigger the check.
                stripped = re.sub(
                    r'<span[^>]*style="display:inline-block;[^"]*background:#[0-9a-fA-F]{3,8};[^"]*"[^>]*>[^<]*</span>',
                    "", stripped,
                )
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
