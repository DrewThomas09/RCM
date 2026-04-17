"""Tests for final gap-fill prompts: 32, 54, 56, 58.

LP QUARTERLY REPORT (54):
 1. generate_lp_quarterly_html returns valid HTML.
 2. HTML contains portfolio summary cards.
 3. Empty portfolio → "No deals" text.
 4. Quarter label rendered.

MOBILE CSS (56):
 5. Workbench CSS contains @media max-width 768px.
 6. _ui_kit CSS contains @media max-width 768px.
 7. Viewport meta tag in workbench HTML.

INTEGRATION HUB (58):
 8. save_integration + list_integrations round-trip.
 9. export_portfolio_csv returns CSV with header row.
10. Empty portfolio → just header row.
11. sync_deal_to_crm returns 0 when no webhooks configured.

INLINE EXPLAIN (32 — minimal):
12. Workbench metrics have the explain link pattern.
"""
from __future__ import annotations

import os
import tempfile
import unittest

from rcm_mc.analysis.packet import DealAnalysisPacket, EBITDABridgeResult
from rcm_mc.exports.lp_quarterly_report import generate_lp_quarterly_html
from rcm_mc.integrations.integration_hub import (
    export_portfolio_csv,
    list_integrations,
    save_integration,
    sync_deal_to_crm,
)
from rcm_mc.portfolio.store import PortfolioStore


def _tmp_store():
    tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tf.close()
    return PortfolioStore(tf.name), tf.name


# ── LP Quarterly Report ───────────────────────────────────────────

class TestLPQuarterlyReport(unittest.TestCase):

    def test_returns_html(self):
        store, path = _tmp_store()
        try:
            html = generate_lp_quarterly_html(store, quarter="2026-Q1")
            self.assertIn("<!DOCTYPE html>", html)
            self.assertIn("LP Quarterly Report", html)
        finally:
            os.unlink(path)

    def test_contains_summary_cards(self):
        store, path = _tmp_store()
        try:
            html = generate_lp_quarterly_html(store)
            self.assertIn("Active Deals", html)
            self.assertIn("Total Opportunity", html)
        finally:
            os.unlink(path)

    def test_empty_portfolio(self):
        store, path = _tmp_store()
        try:
            html = generate_lp_quarterly_html(store)
            self.assertIn("No deals", html)
        finally:
            os.unlink(path)

    def test_quarter_label(self):
        store, path = _tmp_store()
        try:
            html = generate_lp_quarterly_html(store, quarter="2026-Q2")
            self.assertIn("2026-Q2", html)
        finally:
            os.unlink(path)


# ── Mobile CSS ────────────────────────────────────────────────────

class TestMobileCSS(unittest.TestCase):

    def test_workbench_has_mobile_breakpoint(self):
        from rcm_mc.ui.analysis_workbench import _WORKBENCH_CSS
        self.assertIn("max-width: 768px", _WORKBENCH_CSS)

    def test_ui_kit_has_mobile_breakpoint(self):
        from rcm_mc.ui._ui_kit import BASE_CSS
        self.assertIn("max-width: 768px", BASE_CSS)

    def test_viewport_meta_in_workbench(self):
        from rcm_mc.ui.analysis_workbench import render_workbench
        p = DealAnalysisPacket(deal_id="d1")
        html = render_workbench(p)
        self.assertIn('name="viewport"', html)
        self.assertIn("width=device-width", html)


# ── Integration Hub ───────────────────────────────────────────────

class TestIntegrationHub(unittest.TestCase):

    def test_save_and_list(self):
        store, path = _tmp_store()
        try:
            iid = save_integration(store, "dealcloud",
                                   {"api_key": "xxx"})
            self.assertGreater(iid, 0)
            configs = list_integrations(store)
            self.assertEqual(len(configs), 1)
            self.assertEqual(configs[0]["provider"], "dealcloud")
        finally:
            os.unlink(path)

    def test_portfolio_csv_header(self):
        store, path = _tmp_store()
        try:
            csv_str = export_portfolio_csv(store)
            self.assertIn("deal_id", csv_str)
            self.assertIn("ebitda_opportunity", csv_str)
        finally:
            os.unlink(path)

    def test_empty_portfolio_csv(self):
        store, path = _tmp_store()
        try:
            csv_str = export_portfolio_csv(store)
            lines = [l for l in csv_str.strip().splitlines() if l]
            # Just the header row.
            self.assertEqual(len(lines), 1)
        finally:
            os.unlink(path)

    def test_sync_no_webhooks(self):
        store, path = _tmp_store()
        try:
            matched = sync_deal_to_crm(store, "d1")
            self.assertEqual(matched, 0)
        finally:
            os.unlink(path)


# ── Inline Explain (minimal — Prompt 32) ──────────────────────────

class TestInlineExplain(unittest.TestCase):

    def test_metric_link_pattern_in_workbench(self):
        """Workbench metric names link to the provenance anchor so
        partners can navigate to the source. This is the minimal
        explain surface — a full slide-in panel is Prompt 32's
        advanced scope."""
        from rcm_mc.ui.analysis_workbench import render_workbench
        from rcm_mc.analysis.packet import ProfileMetric, MetricSource
        p = DealAnalysisPacket(
            deal_id="d1",
            rcm_profile={
                "denial_rate": ProfileMetric(
                    value=12.0, source=MetricSource.OBSERVED,
                ),
            },
        )
        html = render_workbench(p)
        self.assertIn('href="#prov-denial_rate"', html)


if __name__ == "__main__":
    unittest.main()
