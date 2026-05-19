"""Tests for the corpus intelligence dashboard page."""
from __future__ import annotations

import unittest


class TestRenderCorpusDashboard(unittest.TestCase):
    def test_renders_default(self):
        from rcm_mc.ui.data_public.corpus_dashboard_page import render_corpus_dashboard
        html = render_corpus_dashboard()
        self.assertIn("<!doctype html>", html.lower())
        self.assertGreater(len(html), 20_000)

    def test_kpi_bar_present(self):
        from rcm_mc.ui.data_public.corpus_dashboard_page import render_corpus_dashboard
        html = render_corpus_dashboard()
        self.assertIn("Corpus Deals", html)
        self.assertIn("P50 MOIC", html)
        self.assertIn("Loss Rate", html)

    def test_moic_histogram_present(self):
        from rcm_mc.ui.data_public.corpus_dashboard_page import render_corpus_dashboard
        html = render_corpus_dashboard()
        self.assertIn("MOIC Distribution", html)
        self.assertIn("<svg", html)

    def test_nav_tiles_present(self):
        from rcm_mc.ui.data_public.corpus_dashboard_page import render_corpus_dashboard
        html = render_corpus_dashboard()
        self.assertIn("/sector-intel", html)
        self.assertIn("/vintage-perf", html)
        self.assertIn("/deal-quality", html)

    def test_sector_table_present(self):
        from rcm_mc.ui.data_public.corpus_dashboard_page import render_corpus_dashboard
        html = render_corpus_dashboard()
        self.assertIn("Top Sectors", html)

    def test_vintage_table_present(self):
        from rcm_mc.ui.data_public.corpus_dashboard_page import render_corpus_dashboard
        html = render_corpus_dashboard()
        self.assertIn("Recent Vintages", html)

    def test_nav_link(self):
        # The legacy assertion checked that /corpus-dashboard appeared
        # as a self-href in the rendered page (legacy sidebar). The
        # editorial shell's nav doesn't include it; the page still
        # renders standalone. Assert the page's canonical title text
        # so the test guards "page renders" rather than the gone-nav.
        from rcm_mc.ui.data_public.corpus_dashboard_page import render_corpus_dashboard
        html = render_corpus_dashboard()
        self.assertIn("Corpus Dashboard", html)

    def test_editorial_theme(self):
        # The dark-terminal `power_ui.css` shell (restored briefly by
        # `fix/revert-ui-reskin`) was permanently retired. The canonical
        # chrome is the chartis editorial shell: `chartis_tokens.css`
        # + parchment background tokens.
        from rcm_mc.ui.data_public.corpus_dashboard_page import render_corpus_dashboard
        html = render_corpus_dashboard()
        self.assertIn("chartis_tokens.css", html)
        self.assertIn("/static/v3/chartis.css", html)

    def test_quality_summary(self):
        from rcm_mc.ui.data_public.corpus_dashboard_page import render_corpus_dashboard
        html = render_corpus_dashboard()
        self.assertIn("Avg Quality", html)


if __name__ == "__main__":
    unittest.main()
