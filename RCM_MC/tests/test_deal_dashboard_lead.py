"""The per-deal dashboard hub leads with a deal snapshot.

The hub opened with a 4-up KPI grid; the deal's scale (EV) and the
recoverable-EBITDA opportunity were KPIs #3-4, and EV otherwise only
appeared inline on a model tile. This pins that a ck_value_anchor band
now orients the partner with EV + recoverable EBITDA at the very top.
"""
from __future__ import annotations

import unittest

from rcm_mc.ui.deal_dashboard import render_deal_dashboard


class DealDashboardLeadAnchorTests(unittest.TestCase):
    def _html(self) -> str:
        profile = {
            "name": "Test Deal", "state": "TX", "net_revenue": 4.0e8,
            "ebitda_margin": 0.12, "bed_count": 300, "denial_rate": 14.0,
        }
        return render_deal_dashboard("d1", profile)

    def test_lead_value_anchor_present(self):
        html = self._html()
        self.assertIn("ck-value-anchor", html)
        self.assertIn("DEAL SNAPSHOT", html)
        self.assertIn("recoverable EBITDA", html)

    def test_anchor_leads_before_explainer(self):
        html = self._html()
        self.assertLess(
            html.index("ck-value-anchor"),
            html.index("Every analysis on this deal"),
        )


class DealDashboardOrganizationTests(unittest.TestCase):
    """The dashboard used to stack the same financials three deep — title
    meta, the DEAL SNAPSHOT anchor, AND the KPI strip all showed NPR/EV — and
    the bottom "next step" self-linked to the page it was on. One home per
    metric; the forward link goes somewhere new."""

    def _html(self) -> str:
        profile = {
            "name": "Cypress Crossing Health", "state": "TX",
            "net_revenue": 8.2e8, "ebitda_margin": 0.12,
            "bed_count": 240, "denial_rate": 13.0,
        }
        return render_deal_dashboard("ccf", profile)

    def test_title_meta_is_identity_not_financials(self):
        html = self._html()
        # The title/eyebrow identity line no longer repeats the valuation.
        self.assertNotIn("M NPR", html)
        self.assertNotIn("EV @ 11", html)

    def test_kpi_strip_is_operating_profile_not_valuation_dup(self):
        html = self._html()
        # Operating facts the anchor can't carry …
        self.assertIn("Denial Rate", html)
        self.assertIn("EBITDA Margin", html)
        self.assertIn("Bed Count", html)
        # … and no second copy of the anchor's EV card.
        self.assertNotIn("Rough EV", html)

    def test_forward_link_is_not_self_referential(self):
        html = self._html()
        # "Up next" points at the workbench, not back at /deal/ccf.
        self.assertIn('href="/analysis/ccf"', html)
        self.assertIn("Open the analysis", html)
        # The forward-link href is never the page's own /deal/<id> route.
        self.assertNotIn('class="ck-next-link" href="/deal/ccf"', html)



class EnteredBasisTests(unittest.TestCase):
    """PAGE_INVENTORY top fix: the operating-profile strip badges the
    partner's ENTERED values and never renders the model's fallback
    constants (12% denial / 10% margin) as if they were the deal's."""

    def test_entered_values_badged(self):
        from rcm_mc.ui.deal_dashboard import render_deal_dashboard
        h = render_deal_dashboard(
            "d1", {"name": "X", "denial_rate": 14.2, "bed_count": 250,
                   "ebitda_margin": 0.12})
        self.assertIn(">ENTERED<", h)
        self.assertIn("14.2%", h)

    def test_missing_metrics_show_dash_not_model_default(self):
        from rcm_mc.ui.deal_dashboard import render_deal_dashboard
        h = render_deal_dashboard("d2", {"name": "Y"})
        self.assertNotIn("12.0%", h)        # the model default, anywhere
        self.assertIn("not entered", h)     # honest sub-line



class ExportsRegistryTests(unittest.TestCase):
    """P5 exhibit registry: the deal page lists previously generated
    artifacts from the generated_exports audit table; empty → no panel."""

    def test_registry_panel_lists_real_export_rows(self):
        import tempfile, os
        from rcm_mc.portfolio.store import PortfolioStore
        from rcm_mc.exports.export_store import record_export, list_exports
        from rcm_mc.ui.deal_dashboard import render_deal_dashboard
        with tempfile.TemporaryDirectory() as tmp:
            s = PortfolioStore(os.path.join(tmp, "p.db"))
            s.upsert_deal("d1", name="X")
            record_export(s, deal_id="d1", analysis_run_id=None,
                          format="pdf", filepath="/tmp/x.pdf",
                          file_size_bytes=20480, generated_by="boss")
            h = render_deal_dashboard(
                "d1", {"name": "X"}, exports=list_exports(s, "d1"))
            self.assertIn("Previously generated · registry (1)", h)
            self.assertIn("pdf", h)
            self.assertIn("boss", h)
            self.assertIn("20 KB", h)

    def test_no_exports_no_panel(self):
        from rcm_mc.ui.deal_dashboard import render_deal_dashboard
        h = render_deal_dashboard("d1", {"name": "X"})
        self.assertNotIn("Previously generated", h)


if __name__ == "__main__":
    unittest.main()
