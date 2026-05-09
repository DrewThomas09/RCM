"""tests for the canary KPI-strip migration.

PROMPTS.md Phase 3 / Prompt 26: 25+ pages stack KPIs vertically. The
fix is to migrate them all to the ``kpi_strip()`` primitive built in
P11. Portfolio overview is the canary — these tests pin that the
migration landed and that the page no longer emits the bespoke
``cad-kpi-grid`` markup for its top-level stat row.

Subsequent pages migrate one at a time; each gets its own pin in
this file or a follow-up.
"""
from __future__ import annotations

import unittest


class PortfolioOverviewMigrated(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        # Render with a synthetic deal frame so the populated path
        # runs (not the empty-state branch). Use pandas DataFrame
        # with the columns the renderer expects.
        import pandas as pd

        df = pd.DataFrame([
            {"deal_id": "alpha", "denial_rate": 0.085, "days_in_ar": 42,
             "net_revenue": 100_000_000, "net_collection_rate": 0.94,
             "health_score": 78},
            {"deal_id": "bravo", "denial_rate": 0.118, "days_in_ar": 55,
             "net_revenue": 240_000_000, "net_collection_rate": 0.89,
             "health_score": 65},
        ])

        from rcm_mc.ui.portfolio_overview import render_portfolio_overview
        cls.html = render_portfolio_overview(df)

    def test_kpi_strip_present(self) -> None:
        self.assertIn("kpi-strip", self.html)
        # Five KPIs in the migrated strip.
        self.assertIn("repeat(5,1fr)", self.html)

    def test_legacy_cad_kpi_grid_no_longer_used_for_strip(self) -> None:
        # The bespoke vertical-stack markup should be gone from the
        # top-level stat row. Other parts of the page may still use
        # cad-kpi for now (will be migrated in follow-up sweeps), so
        # we can't simply count zero — instead we verify the new
        # primitive is the dominant container around the five KPIs.
        # Specifically: kpi-strip appears before the first cad-card.
        kpi_strip_idx = self.html.find('class="kpi-strip')
        first_cad_card_idx = self.html.find('class="cad-card')
        self.assertGreater(kpi_strip_idx, 0)
        # Either no cad-card on the page, or kpi-strip appears earlier.
        if first_cad_card_idx > 0:
            self.assertLess(kpi_strip_idx, first_cad_card_idx)

    def test_format_value_still_in_play(self) -> None:
        # Migration must not regress the missing-aware value rendering
        # we wired in P9 — values still flow through format_value.
        self.assertIn("$340.00M", self.html)  # 100M + 240M total
        self.assertIn("10.2%", self.html)  # avg of 8.5 and 11.8


class PortfolioOverviewProvenanceMarkers(unittest.TestCase):
    """P32 canary: every KPI in the migrated strip carries a
    provenance_marker so the source family is visible at a glance."""

    @classmethod
    def setUpClass(cls) -> None:
        import pandas as pd
        from rcm_mc.ui.portfolio_overview import render_portfolio_overview

        df = pd.DataFrame([
            {"deal_id": "alpha", "denial_rate": 0.085, "days_in_ar": 42,
             "net_revenue": 100_000_000, "net_collection_rate": 0.94,
             "health_score": 78},
        ])
        cls.html = render_portfolio_overview(df)

    def test_calculated_marker_present(self) -> None:
        # Total revenue, avg denial, avg AR, avg net collection are
        # derived aggregates → CALCULATED source family → triangle.
        self.assertIn('data-source="CALCULATED"', self.html)
        self.assertIn("prov-derived", self.html)

    def test_user_input_marker_present_on_count(self) -> None:
        # The deal count is observed (the row count of the input
        # frame, not derived) → USER_INPUT family → filled circle.
        self.assertIn('data-source="USER_INPUT"', self.html)
        self.assertIn("prov-observed", self.html)


class PortfolioOverviewEmptyMigrated(unittest.TestCase):
    """P27 canary: empty portfolio renders via the kit's empty_state
    primitive, not a bespoke cad-card with inline styles."""

    @classmethod
    def setUpClass(cls) -> None:
        import pandas as pd
        from rcm_mc.ui.portfolio_overview import render_portfolio_overview

        cls.html = render_portfolio_overview(pd.DataFrame())

    def test_empty_state_card_present(self) -> None:
        # The kit's empty_state emits a div with class "es-card".
        self.assertIn('class="es-card"', self.html)

    def test_primary_cta_routes_to_import(self) -> None:
        self.assertIn('href="/import"', self.html)
        self.assertIn("Add a deal", self.html)

    def test_no_legacy_inline_text_align_block(self) -> None:
        # The previous bespoke card carried a "No Deals in Portfolio"
        # H2 followed by a centred flex CTA row. The migration must
        # have removed that exact wording.
        self.assertNotIn("No Deals in Portfolio", self.html)


if __name__ == "__main__":
    unittest.main()
