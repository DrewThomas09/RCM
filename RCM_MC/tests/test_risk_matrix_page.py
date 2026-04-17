"""Tests for rcm_mc/ui/data_public/risk_matrix_page.py."""
from __future__ import annotations

import unittest


class TestRenderRiskMatrix(unittest.TestCase):
    def test_renders_html(self):
        from rcm_mc.ui.data_public.risk_matrix_page import render_risk_matrix
        html = render_risk_matrix()
        self.assertIn("<!DOCTYPE html>", html)
        self.assertGreater(len(html), 50_000)

    def test_contains_svg_scatter(self):
        import re
        from rcm_mc.ui.data_public.risk_matrix_page import render_risk_matrix
        html = render_risk_matrix()
        self.assertGreaterEqual(len(re.findall(r"<svg", html)), 1)

    def test_contains_kpi_bar(self):
        from rcm_mc.ui.data_public.risk_matrix_page import render_risk_matrix
        html = render_risk_matrix()
        self.assertIn("Scored Deals", html)
        self.assertIn("Danger Zone", html)

    def test_contains_sector_heatmap(self):
        from rcm_mc.ui.data_public.risk_matrix_page import render_risk_matrix
        html = render_risk_matrix()
        self.assertIn("Sector Risk-Return Summary", html)

    def test_nav_link(self):
        from rcm_mc.ui.data_public.risk_matrix_page import render_risk_matrix
        html = render_risk_matrix()
        self.assertIn("/risk-matrix", html)

    def test_sector_filter_works(self):
        from rcm_mc.ui.data_public.risk_matrix_page import render_risk_matrix
        html = render_risk_matrix(sector_filter="Physician Practice")
        self.assertIn("<!DOCTYPE html>", html)

    def test_no_light_theme(self):
        from rcm_mc.ui.data_public.risk_matrix_page import render_risk_matrix
        html = render_risk_matrix()
        self.assertNotIn("background:#ffffff", html.lower())


class TestScatterData(unittest.TestCase):
    def test_build_scatter_returns_data(self):
        from rcm_mc.ui.data_public.risk_matrix_page import _load_corpus, _build_scatter_data
        corpus = _load_corpus()
        pts, sector_rows = _build_scatter_data(corpus)
        self.assertGreater(len(pts), 100)
        self.assertGreater(len(sector_rows), 5)

    def test_scatter_points_in_range(self):
        from rcm_mc.ui.data_public.risk_matrix_page import _load_corpus, _build_scatter_data
        corpus = _load_corpus()
        pts, _ = _build_scatter_data(corpus)
        for risk, moic, sector, name in pts[:20]:
            self.assertGreaterEqual(risk, 0)
            self.assertLessEqual(risk, 100)
            self.assertGreaterEqual(moic, 0)

    def test_sector_rows_have_fields(self):
        from rcm_mc.ui.data_public.risk_matrix_page import _load_corpus, _build_scatter_data
        corpus = _load_corpus()
        _, rows = _build_scatter_data(corpus)
        if rows:
            r = rows[0]
            for key in ["sector", "n", "avg_risk", "p50_moic", "loss_rate"]:
                self.assertIn(key, r)

    def test_sector_rows_sorted_by_risk(self):
        from rcm_mc.ui.data_public.risk_matrix_page import _load_corpus, _build_scatter_data
        corpus = _load_corpus()
        _, rows = _build_scatter_data(corpus)
        risks = [r["avg_risk"] for r in rows]
        self.assertEqual(risks, sorted(risks))


class TestSvgHelpers(unittest.TestCase):
    def test_scatter_svg_produces_svg(self):
        from rcm_mc.ui.data_public.risk_matrix_page import _risk_return_scatter
        pts = [(30.0, 2.5, "Cardiology", "Deal A"), (70.0, 0.8, "Emergency Medicine", "Deal B")]
        svg = _risk_return_scatter(pts)
        self.assertIn("<svg", svg)
        self.assertIn("<circle", svg)

    def test_scatter_empty_no_crash(self):
        from rcm_mc.ui.data_public.risk_matrix_page import _risk_return_scatter
        svg = _risk_return_scatter([])
        self.assertIn("<svg", svg)

    def test_quadrant_lines_present(self):
        from rcm_mc.ui.data_public.risk_matrix_page import _risk_return_scatter
        pts = [(40.0, 3.0, "Sector", "Deal")]
        svg = _risk_return_scatter(pts)
        self.assertIn("stroke-dasharray", svg)

    def test_entry_risk_score_returns_float(self):
        from rcm_mc.ui.data_public.risk_matrix_page import _entry_risk_score, _load_corpus
        corpus = _load_corpus()
        deal = corpus[0]
        score = _entry_risk_score(deal, corpus)
        if score is not None:
            self.assertGreaterEqual(score, 0)
            self.assertLessEqual(score, 100)


if __name__ == "__main__":
    unittest.main()
