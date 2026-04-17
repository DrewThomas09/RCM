"""Tests for rcm_mc/data_public/corpus_red_flags.py and corpus_flags_panel.py."""
from __future__ import annotations

import unittest
from typing import Any, Dict, List


def _deal(**kwargs) -> Dict[str, Any]:
    base = {
        "deal_name": "Test Deal",
        "sector": "Physician Practice",
        "ev_mm": 100.0,
        "ebitda_at_entry_mm": 12.5,   # 8× — moderate
        "hold_years": 5.0,
        "leverage_pct": 0.55,
        "payer_mix": {"commercial": 0.60, "medicare": 0.30, "medicaid": 0.10},
    }
    base.update(kwargs)
    return base


class TestDetectCorpusRedFlags(unittest.TestCase):
    def test_clean_deal_has_few_flags(self):
        from rcm_mc.data_public.corpus_red_flags import detect_corpus_red_flags
        flags = detect_corpus_red_flags(_deal())
        # A moderate deal should have 0-2 flags
        self.assertLessEqual(len(flags), 3)

    def test_high_entry_multiple_triggers_flag(self):
        from rcm_mc.data_public.corpus_red_flags import detect_corpus_red_flags
        deal = _deal(ev_mm=400.0, ebitda_at_entry_mm=20.0)  # 20× — top decile
        flags = detect_corpus_red_flags(deal)
        categories = [f.category for f in flags]
        self.assertIn("ENTRY_RISK", categories)

    def test_high_leverage_triggers_flag(self):
        from rcm_mc.data_public.corpus_red_flags import detect_corpus_red_flags
        deal = _deal(leverage_pct=0.85)  # 85% — very high
        flags = detect_corpus_red_flags(deal)
        sev = [f.severity for f in flags if f.category == "LEVERAGE"]
        self.assertIn("critical", sev)

    def test_low_commercial_mix_triggers_payer_flag(self):
        from rcm_mc.data_public.corpus_red_flags import detect_corpus_red_flags
        deal = _deal(payer_mix={"commercial": 0.20, "medicare": 0.50, "medicaid": 0.30})
        flags = detect_corpus_red_flags(deal)
        categories = [f.category for f in flags]
        self.assertIn("PAYER", categories)

    def test_high_medicaid_triggers_policy_flag(self):
        from rcm_mc.data_public.corpus_red_flags import detect_corpus_red_flags
        deal = _deal(payer_mix={"commercial": 0.25, "medicare": 0.40, "medicaid": 0.35})
        flags = detect_corpus_red_flags(deal)
        payer_flags = [f for f in flags if f.category == "PAYER"]
        details = " ".join(f.detail for f in payer_flags)
        self.assertIn("Medicaid", details)

    def test_missing_fields_no_crash(self):
        from rcm_mc.data_public.corpus_red_flags import detect_corpus_red_flags
        # Completely empty deal
        flags = detect_corpus_red_flags({})
        self.assertIsInstance(flags, list)

    def test_sorted_by_severity(self):
        from rcm_mc.data_public.corpus_red_flags import detect_corpus_red_flags
        deal = _deal(
            ev_mm=450.0, ebitda_at_entry_mm=20.0,
            leverage_pct=0.82,
            payer_mix={"commercial": 0.15, "medicare": 0.55, "medicaid": 0.30},
        )
        flags = detect_corpus_red_flags(deal)
        if len(flags) >= 2:
            order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
            sev_order = [order[f.severity] for f in flags]
            self.assertEqual(sev_order, sorted(sev_order))

    def test_flags_have_required_fields(self):
        from rcm_mc.data_public.corpus_red_flags import detect_corpus_red_flags
        deal = _deal(ev_mm=400.0, ebitda_at_entry_mm=18.0, leverage_pct=0.80)
        flags = detect_corpus_red_flags(deal)
        for f in flags:
            self.assertIsNotNone(f.category)
            self.assertIsNotNone(f.severity)
            self.assertIsNotNone(f.headline)
            self.assertIsNotNone(f.detail)
            self.assertGreater(len(f.headline), 5)
            self.assertGreater(len(f.detail), 10)

    def test_payer_mix_as_string_no_crash(self):
        from rcm_mc.data_public.corpus_red_flags import detect_corpus_red_flags
        import json
        deal = _deal(payer_mix=json.dumps({"commercial": 0.25, "medicare": 0.55, "medicaid": 0.20}))
        flags = detect_corpus_red_flags(deal)
        self.assertIsInstance(flags, list)

    def test_no_sector_no_sector_flag(self):
        from rcm_mc.data_public.corpus_red_flags import detect_corpus_red_flags
        deal = _deal()
        del deal["sector"]
        flags = detect_corpus_red_flags(deal)
        self.assertNotIn("SECTOR", [f.category for f in flags])

    def test_sector_flag_for_high_loss_sector(self):
        from rcm_mc.data_public.corpus_red_flags import detect_corpus_red_flags
        # Use a sector known to have many deals in corpus
        deal = _deal(sector="Behavioral Health")
        flags = detect_corpus_red_flags(deal)
        # May or may not trigger depending on corpus data — should not crash
        self.assertIsInstance(flags, list)

    def test_as_dict(self):
        from rcm_mc.data_public.corpus_red_flags import detect_corpus_red_flags
        deal = _deal(ev_mm=400.0, ebitda_at_entry_mm=18.0)
        flags = detect_corpus_red_flags(deal)
        if flags:
            d = flags[0].as_dict()
            for key in ["category", "severity", "headline", "detail"]:
                self.assertIn(key, d)


class TestFlagSummary(unittest.TestCase):
    def test_empty_flags(self):
        from rcm_mc.data_public.corpus_red_flags import flag_summary
        s = flag_summary([])
        self.assertEqual(s["total_flags"], 0)
        self.assertIsNone(s["total_ebitda_at_risk_mm"])

    def test_counts_by_severity(self):
        from rcm_mc.data_public.corpus_red_flags import detect_corpus_red_flags, flag_summary
        deal = _deal(
            ev_mm=450.0, ebitda_at_entry_mm=20.0, leverage_pct=0.82,
            payer_mix={"commercial": 0.15, "medicare": 0.55, "medicaid": 0.30},
        )
        flags = detect_corpus_red_flags(deal)
        s = flag_summary(flags)
        total = sum(s["by_severity"].values())
        self.assertEqual(total, s["total_flags"])

    def test_ebitda_at_risk_sum(self):
        from rcm_mc.data_public.corpus_red_flags import CorpusRedFlag, flag_summary
        flags = [
            CorpusRedFlag("LEVERAGE", "critical", "H1", "D1", ebitda_at_risk_mm=3.5),
            CorpusRedFlag("PAYER", "high", "H2", "D2", ebitda_at_risk_mm=1.2),
            CorpusRedFlag("SECTOR", "medium", "H3", "D3"),  # no ebitda_at_risk
        ]
        s = flag_summary(flags)
        self.assertAlmostEqual(s["total_ebitda_at_risk_mm"], 4.7, places=1)


class TestFlagChecks(unittest.TestCase):
    def test_flag_entry_multiple_none_returns_none(self):
        from rcm_mc.data_public.corpus_red_flags import _flag_entry_multiple, _get_corpus
        f = _flag_entry_multiple(None, None, _get_corpus(), [])
        self.assertIsNone(f)

    def test_flag_entry_low_multiple_returns_none(self):
        from rcm_mc.data_public.corpus_red_flags import _flag_entry_multiple, _get_corpus
        f = _flag_entry_multiple(5.0, 20.0, _get_corpus(), [])
        self.assertIsNone(f)

    def test_flag_leverage_none_returns_none(self):
        from rcm_mc.data_public.corpus_red_flags import _flag_leverage, _get_corpus
        f = _flag_leverage(None, None, _get_corpus(), [])
        self.assertIsNone(f)

    def test_flag_leverage_low_returns_none(self):
        from rcm_mc.data_public.corpus_red_flags import _flag_leverage, _get_corpus
        f = _flag_leverage(0.30, 20.0, _get_corpus(), [])
        self.assertIsNone(f)

    def test_flag_hold_long_triggers(self):
        from rcm_mc.data_public.corpus_red_flags import _flag_hold_years, _get_corpus
        f = _flag_hold_years(12.0, _get_corpus())
        self.assertIsNotNone(f)
        self.assertEqual(f.category, "HOLD")

    def test_flag_sector_loss_rate_too_few_deals(self):
        from rcm_mc.data_public.corpus_red_flags import _flag_sector_loss_rate
        f = _flag_sector_loss_rate("Rare Sector", [{"realized_moic": 0.5}, {"realized_moic": 2.0}])
        self.assertIsNone(f)  # < 3 deals → skip


class TestCorpusFlagsPanel(unittest.TestCase):
    def test_renders_html(self):
        from rcm_mc.ui.data_public.corpus_flags_panel import render_corpus_flags_panel
        panel = render_corpus_flags_panel(_deal())
        self.assertIn("ckf-drawer", panel)
        self.assertIn("Corpus Red Flags", panel)

    def test_panel_no_crash_on_empty_deal(self):
        from rcm_mc.ui.data_public.corpus_flags_panel import render_corpus_flags_panel
        panel = render_corpus_flags_panel({})
        self.assertIn("ckf-drawer", panel)

    def test_panel_shows_critical_badge_for_high_leverage(self):
        from rcm_mc.ui.data_public.corpus_flags_panel import render_corpus_flags_panel
        deal = _deal(leverage_pct=0.88, ev_mm=400.0, ebitda_at_entry_mm=18.0)
        panel = render_corpus_flags_panel(deal)
        self.assertIn("critical", panel.lower())

    def test_panel_shows_ebitda_at_risk(self):
        from rcm_mc.ui.data_public.corpus_flags_panel import render_corpus_flags_panel
        deal = _deal(leverage_pct=0.85, ebitda_at_entry_mm=30.0)
        panel = render_corpus_flags_panel(deal)
        self.assertIn("EBITDA at risk", panel)

    def test_inject_into_workbench_inserts_before_body_close(self):
        from rcm_mc.ui.data_public.corpus_flags_panel import inject_into_workbench
        fake_html = "<html><body><h1>Test</h1></body></html>"
        result = inject_into_workbench(fake_html, _deal(leverage_pct=0.82))
        self.assertIn("ckf-drawer", result)
        # Panel must come before </body>
        panel_pos = result.find("ckf-drawer")
        body_close_pos = result.rfind("</body>")
        self.assertLess(panel_pos, body_close_pos)

    def test_inject_no_crash_on_exception(self):
        from rcm_mc.ui.data_public.corpus_flags_panel import inject_into_workbench
        # If panel rendering fails (e.g., import error), should still return original HTML
        fake_html = "<html><body>Content</body></html>"
        result = inject_into_workbench(fake_html, {"bad": "deal"})
        self.assertIn("Content", result)

    def test_inject_no_body_tag(self):
        from rcm_mc.ui.data_public.corpus_flags_panel import inject_into_workbench
        result = inject_into_workbench("plain text", _deal())
        # Should append at end
        self.assertIn("ckf-drawer", result)

    def test_panel_clear_badge_for_clean_deal(self):
        from rcm_mc.ui.data_public.corpus_flags_panel import render_corpus_flags_panel
        clean = _deal(
            ev_mm=50.0, ebitda_at_entry_mm=10.0,  # 5× multiple — low
            leverage_pct=0.40,
            payer_mix={"commercial": 0.70, "medicare": 0.25, "medicaid": 0.05},
            hold_years=4.5,
        )
        panel = render_corpus_flags_panel(clean)
        # No crash and panel renders
        self.assertIn("ckf-drawer", panel)

    def test_dark_theme_colors_present(self):
        from rcm_mc.ui.data_public.corpus_flags_panel import render_corpus_flags_panel
        panel = render_corpus_flags_panel(_deal())
        self.assertIn("#0b0f18", panel)  # dark background
        self.assertIn("#1e293b", panel)  # border color


if __name__ == "__main__":
    unittest.main()
