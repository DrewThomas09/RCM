"""Tests for rcm_mc/ui/data_public/underwriting_page.py."""
from __future__ import annotations

import unittest


class TestRenderUnderwriting(unittest.TestCase):
    def test_renders_default(self):
        from rcm_mc.ui.data_public.underwriting_page import render_underwriting
        html = render_underwriting()
        self.assertIn("<!doctype html>", html.lower())
        self.assertGreater(len(html), 15_000)

    def test_renders_with_params(self):
        from rcm_mc.ui.data_public.underwriting_page import render_underwriting
        html = render_underwriting(entry_ev=200.0, entry_ebitda=20.0, equity_pct=40.0,
                                    ebitda_cagr=12.0, hold_years=5.0, exit_multiple=11.0)
        self.assertIn("Gross MOIC", html)
        self.assertIn("Underwriting Results", html)

    def test_sensitivity_table_present(self):
        from rcm_mc.ui.data_public.underwriting_page import render_underwriting
        html = render_underwriting(entry_ev=200.0, entry_ebitda=20.0, equity_pct=40.0,
                                    ebitda_cagr=10.0, hold_years=5.0, exit_multiple=10.0)
        self.assertIn("Sensitivity", html)

    def test_sensitivity_grid_pivots_not_raw_keys(self):
        # Regression: sensitivity_table() returns flat
        # {exit_multiple, hold_years, metric} rows, but the renderer
        # assumed a pivoted grid — so headers showed the raw keys
        # ("Exit exit_multiple×", "Exit net_irr×") and the body rows had
        # no value cells (3-col header over 1-col body). The grid must
        # now pivot to Hold × Exit-Multiple with MOIC value cells.
        import re
        from rcm_mc.ui.data_public.underwriting_page import render_underwriting
        html = render_underwriting(entry_ev=200.0, entry_ebitda=20.0,
                                   equity_pct=40.0, ebitda_cagr=10.0,
                                   hold_years=5.0, exit_multiple=10.0)
        # No raw field-name headers.
        self.assertNotIn("Exit exit_multiple", html)
        self.assertNotIn("net_irr×", html)
        # Header carries formatted exit multiples; body carries MOIC cells.
        self.assertRegex(html, r"Exit \d+\.\d×")
        body = re.sub(r"<(script|style)\b.*?</\1>", " ", html,
                      flags=re.S | re.I)
        tbl = re.search(
            r"MOIC Sensitivity.*?<table\b[^>]*>(.*?)</table>", body, re.S)
        self.assertIsNotNone(tbl)
        t = tbl.group(1)
        ncol = len(re.findall(r"<th\b", t))
        self.assertGreaterEqual(ncol, 3)
        # every body row has a hold cell + one MOIC cell per multiple
        for rowm in re.finditer(r"<tr\b[^>]*>(.*?)</tr>", t, re.S):
            row = rowm.group(1)
            if "<th" in row:
                continue
            self.assertEqual(len(re.findall(r"<td\b", row)), ncol)

    def test_corpus_benchmark_present(self):
        from rcm_mc.ui.data_public.underwriting_page import render_underwriting
        html = render_underwriting(entry_ev=200.0, entry_ebitda=20.0, equity_pct=40.0,
                                    ebitda_cagr=10.0, hold_years=5.0, exit_multiple=10.0)
        self.assertIn("Corpus Benchmark", html)

    def test_nav_link(self):
        from rcm_mc.ui.data_public.underwriting_page import render_underwriting
        html = render_underwriting()
        self.assertIn("/underwriting", html)

    def test_form_inputs_present(self):
        from rcm_mc.ui.data_public.underwriting_page import render_underwriting
        html = render_underwriting()
        self.assertIn("entry_ev", html)
        self.assertIn("entry_ebitda", html)
        self.assertIn("Run Underwriting", html)

    def test_no_light_theme(self):
        from rcm_mc.ui.data_public.underwriting_page import render_underwriting
        html = render_underwriting()
        self.assertNotIn("background:#ffffff", html.lower())

    def test_high_ev_low_ebitda_red_moic(self):
        from rcm_mc.ui.data_public.underwriting_page import render_underwriting
        # 25× entry multiple — should produce low MOIC
        html = render_underwriting(entry_ev=500.0, entry_ebitda=20.0, equity_pct=40.0,
                                    ebitda_cagr=5.0, hold_years=5.0, exit_multiple=8.0)
        self.assertIn("<!doctype html>", html.lower())

    def test_corpus_benchmark_panel(self):
        from rcm_mc.ui.data_public.underwriting_page import _corpus_benchmark_panel, _load_corpus
        from rcm_mc.data_public.deal_underwriting_model import underwrite_deal, UnderwritingAssumptions
        corpus = _load_corpus()
        a = UnderwritingAssumptions(entry_ev_mm=200, entry_ebitda_mm=20,
                                     equity_contribution_pct=0.4, ebitda_cagr=0.10,
                                     hold_years=5, exit_multiple=10)
        result = underwrite_deal(a)
        panel = _corpus_benchmark_panel(result, corpus)
        self.assertIn("Corpus Benchmark", panel)
        self.assertIn("Peer P50 MOIC", panel)

    def test_pct_rank_bar_svg(self):
        from rcm_mc.ui.data_public.underwriting_page import _pct_rank_bar
        bar = _pct_rank_bar(65.0)
        self.assertIn("<svg", bar)
        self.assertIn("65th pctile", bar)


if __name__ == "__main__":
    unittest.main()
