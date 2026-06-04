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

    def test_verified_subset_moic_shown(self):
        """The credible verified-only MOIC must sit beside the illustrative
        aggregate, with its deal count + loss rate — so a partner doesn't
        anchor on the synthetic-skewed median."""
        from rcm_mc.ui.data_public.corpus_dashboard_page import render_corpus_dashboard
        html = render_corpus_dashboard()
        self.assertIn("Verified P50 MOIC", html)
        self.assertIn("verified-historical deals", html)
        self.assertIn("loss rate", html)
        # The illustrative aggregate is now labelled as such.
        self.assertIn("illustrative", html.lower())

    def test_universe_toggle_present(self):
        """The data-universe toggle lets a partner flip the whole dashboard
        between the illustrative aggregate and the verified-only read."""
        from rcm_mc.ui.data_public.corpus_dashboard_page import render_corpus_dashboard
        html = render_corpus_dashboard()
        self.assertIn("Data universe", html)
        self.assertIn("Illustrative corpus", html)
        self.assertIn("Verified only", html)
        # The verified pill links to the verified universe.
        self.assertIn("/corpus-dashboard?universe=verified", html)

    def test_verified_mode_recomputes_everything(self):
        """In verified mode every figure is recomputed from the real subset:
        the page foregrounds the credible (lower) median, flips the sidecar to
        show the illustrative aggregate as the contrast, and recomputes the
        sector table from sector-tagged real deals."""
        from rcm_mc.ui.data_public.corpus_dashboard_page import render_corpus_dashboard
        html = render_corpus_dashboard(universe="verified")
        # Verified is now the foreground; the illustrative aggregate is the
        # contrast sidecar (the inverse of default mode).
        self.assertIn("Illustrative P50 MOIC", html)
        self.assertIn("Verified historical", html)
        self.assertIn("verified-historical only", html)
        self.assertIn("synthetic-skewed", html)
        # Structural panels still render off the (smaller) real corpus.
        self.assertIn("Top Sectors", html)
        self.assertIn("MOIC Distribution", html)
        # The verified deal count is the real-tier size and far below the
        # full corpus — assert it dynamically so it tracks corpus growth.
        from rcm_mc.data_public.corpus_loader import load_corpus_deals
        n_real = len(load_corpus_deals("real"))
        n_all = len(load_corpus_deals("all"))
        self.assertIn(f"{n_real} deals", html)
        self.assertLess(n_real, n_all)

    def test_top_sectors_excludes_singledeal_noise(self):
        """Regression: the all-mode 'Top Sectors by P50 MOIC' table ranked
        flukey 1-deal micro-sectors (e.g. a lone 5.1x 'women's health') above
        well-populated sectors. The ranking must require >=5 realized deals and
        say so, so a partner doesn't read single-deal noise as a top sector."""
        from rcm_mc.ui.data_public.corpus_dashboard_page import render_corpus_dashboard
        import re
        html = render_corpus_dashboard()  # all mode
        self.assertIn("realized deals", html)
        self.assertIn("single-deal sectors excluded", html)
        # Every deal-count cell in the Top Sectors table must be >= 5.
        m = re.search(r"Top Sectors by P50 MOIC.*?<tbody>(.*?)</tbody>", html, re.S)
        self.assertIsNotNone(m)
        rows = re.findall(r"<tr.*?</tr>", m.group(1), re.S)
        self.assertTrue(rows)
        for row in rows:
            cells = re.findall(r"<td[^>]*>(.*?)</td>", row, re.S)
            # cells: [sector, n_deals, P50 MOIC, P50 IRR, loss%]
            n_deals = int(re.sub(r"[^0-9]", "", cells[1]))
            self.assertGreaterEqual(
                n_deals, 5,
                f"single-/low-deal sector leaked into Top Sectors: {cells}",
            )

    def test_verified_mode_sector_table_nonempty(self):
        """Regression: the real seed deals were unclassified (no `sector`),
        so verified-mode sector analysis was silently empty. The canonical
        backfill must surface real sectors (e.g. hospital)."""
        from rcm_mc.ui.data_public.corpus_dashboard_page import render_corpus_dashboard
        html = render_corpus_dashboard(universe="verified")
        # hospital is the largest verified sector; it must appear in the table.
        self.assertIn("hospital", html.lower())

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
