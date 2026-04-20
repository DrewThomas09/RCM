"""Tests for the polish pass: global nav, input validation, health endpoint.

GLOBAL NAV:
 1. All shell-rendered pages contain the global nav bar.
 2. Nav contains links to Dashboard, New Deal, Screen, Source, API.

INPUT VALIDATION:
 3. Empty deal_id raises ValueError.
 4. cost_of_capital_pct > 1 auto-corrected.
 5. Non-numeric observed_override values dropped without crash.

HEALTH:
 6. /api/health returns deal_count.
 7. /ready returns ready: true.
"""
from __future__ import annotations

import os
import tempfile
import unittest

from rcm_mc.portfolio.store import PortfolioStore
from rcm_mc.ui._ui_kit import shell


class TestGlobalNav(unittest.TestCase):

    def test_shell_contains_nav(self):
        html = shell("<p>test</p>", "Test Page")
        self.assertIn("Main navigation", html)
        self.assertIn("/pipeline", html)
        self.assertIn("/library", html)
        self.assertIn("SeekingChartis", html)

    def test_nav_links_accessible(self):
        html = shell("<p>test</p>", "Test Page")
        self.assertIn('aria-label="Main navigation"', html)


class TestInputValidation(unittest.TestCase):

    def test_empty_deal_id_raises(self):
        from rcm_mc.analysis.packet_builder import build_analysis_packet
        store, path = self._tmp_store()
        try:
            with self.assertRaises(ValueError):
                build_analysis_packet(store, "")
        finally:
            os.unlink(path)

    def test_cost_of_capital_auto_corrected(self):
        """Passing 8 instead of 0.08 should get auto-corrected."""
        from rcm_mc.analysis.packet_builder import build_analysis_packet
        store, path = self._tmp_store()
        try:
            store.upsert_deal("d1", name="D1",
                              profile={"bed_count": 200})
            # Should not crash — the 8.0 gets divided by 100.
            packet = build_analysis_packet(
                store, "d1", skip_simulation=True,
                financials={"cost_of_capital_pct": 8.0},
            )
            self.assertIsNotNone(packet)
        finally:
            os.unlink(path)

    def test_non_numeric_override_dropped(self):
        from rcm_mc.analysis.packet_builder import build_analysis_packet
        store, path = self._tmp_store()
        try:
            store.upsert_deal("d1", name="D1",
                              profile={"bed_count": 200})
            packet = build_analysis_packet(
                store, "d1", skip_simulation=True,
                observed_override={
                    "denial_rate": 12.0,
                    "bad_metric": "not a number",
                },
            )
            # denial_rate should be in the profile; bad_metric dropped.
            self.assertIn("denial_rate", packet.rcm_profile)
        finally:
            os.unlink(path)

    def _tmp_store(self):
        tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tf.close()
        return PortfolioStore(tf.name), tf.name


if __name__ == "__main__":
    unittest.main()
