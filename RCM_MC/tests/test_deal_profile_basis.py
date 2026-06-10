"""Regression: deal-profile metrics disclose their ENTERED basis + sanity flags.

Deal RCM metrics (net collection rate, denial rate, days in A/R, …) come from
the partner-entered profile (via /import), stored in deals.profile_json — not
a public filing, not a model. The quick view must say so (ENTERED badge), and
implausible percent entries (e.g. the fraction 0.945 entered where percent
points 94.5 were expected) are flagged ⚠ for review rather than displayed as
confident KPIs. Portfolio-overview provenance names the same basis.
"""
from __future__ import annotations

import unittest

from rcm_mc.ui._chartis_kit import ck_basis_badge
from rcm_mc.ui.deal_quick_view import render_deal_quick_view

_GOOD = {"name": "Atlas", "denial_rate": 11.5, "days_in_ar": 48,
         "net_collection_rate": 94.5, "clean_claim_rate": 86.0,
         "cost_to_collect": 3.4, "net_revenue": 2.4e8,
         "bed_count": 220, "claims_volume": 410000}


class EnteredBadgeTests(unittest.TestCase):
    def test_entered_badge_renders(self):
        b = ck_basis_badge("entered")
        self.assertIn("ENTERED", b)
        self.assertIn("Partner-entered", b)

    def test_quick_view_discloses_basis(self):
        h = render_deal_quick_view("atlas", _GOOD)
        self.assertIn("ENTERED", h)
        self.assertIn("/import", h)   # the edit path is one click away


class UnitMistakeFlagTests(unittest.TestCase):
    def test_plausible_profile_has_no_flag(self):
        h = render_deal_quick_view("atlas", _GOOD)
        self.assertNotIn("Outside the typical", h)

    def test_fraction_entered_as_ncr_is_flagged(self):
        # 0.945 entered where 94.5 percent-points were expected.
        h = render_deal_quick_view("atlas", {**_GOOD, "net_collection_rate": 0.945})
        self.assertIn("⚠", h)
        self.assertIn("Outside the typical 80–100% range", h)

    def test_swapped_denial_rate_is_flagged(self):
        # A 94.5 denial rate is almost certainly NCR in the wrong field.
        h = render_deal_quick_view("atlas", {**_GOOD, "denial_rate": 94.5})
        self.assertIn("Outside the typical 0–40% range", h)


class PortfolioProvenanceTests(unittest.TestCase):
    def test_overview_provenance_names_entered_basis(self):
        import pandas as pd
        import json
        from rcm_mc.ui.portfolio_overview import render_portfolio_overview
        deals = pd.DataFrame([{
            "deal_id": "atlas", "name": "Atlas",
            "created_at": "2026-01-01", "archived_at": None,
            "profile_json": json.dumps(_GOOD),
            **_GOOD,
        }])
        h = render_portfolio_overview(deals, None)
        self.assertIn("partner-entered deal profiles", h)


class NestedObservedMetricsTests(unittest.TestCase):
    """Packet-seeded deals nest metrics under ONE observed_metrics dict
    column; the overview's KPIs read flat columns. Before _expand_profiles
    every headline KPI showed '—' while the data sat right there."""

    def _deals(self):
        import pandas as pd
        om = {m: {"value": v, "quality_flags": []}
              for m, v in [("denial_rate", 14.2), ("days_in_ar", 58.4),
                           ("net_collection_rate", 91.8),
                           ("clean_claim_rate", 84.2)]}
        return pd.DataFrame([{
            "deal_id": "ccf", "name": "CCF", "created_at": "2026-01-01",
            "observed_metrics": om,
        }])

    def test_expand_pulls_values_out_of_observed_metrics(self):
        from rcm_mc.ui.portfolio_overview import _expand_profiles
        out = _expand_profiles(self._deals())
        self.assertAlmostEqual(out["net_collection_rate"].iloc[0], 91.8)
        self.assertAlmostEqual(out["denial_rate"].iloc[0], 14.2)

    def test_overview_kpis_show_values_not_dashes(self):
        from rcm_mc.ui.portfolio_overview import render_portfolio_overview
        h = render_portfolio_overview(self._deals(), None)
        self.assertIn("91.8%", h)          # Avg Net Collection has a value
        self.assertIn("14.2%", h)          # Avg Denial Rate too


class RegressionOverfitGuardTests(unittest.TestCase):
    """A 5-deal × 4-feature OLS fits (near-)exactly by construction —
    'R-Squared 100%' is an artifact of n ≤ k+1, not a real relationship.
    The panel must say so; a portfolio with enough deals stays clean."""

    @staticmethod
    def _portfolio(n):
        import numpy as np
        import pandas as pd
        rng = np.random.default_rng(7)
        return pd.DataFrame([{
            "deal_id": f"d{i}", "name": f"D{i}", "created_at": "2026-01-01",
            "denial_rate": float(8 + rng.normal(0, 2)),
            "days_in_ar": float(45 + rng.normal(0, 6)),
            "net_collection_rate": float(94 + rng.normal(0, 2)),
            "clean_claim_rate": float(85 + rng.normal(0, 3)),
            "cost_to_collect": float(3.5 + rng.normal(0, 0.5)),
            "net_revenue": 2e8,
        } for i in range(n)])

    def test_small_portfolio_flags_degenerate_fit(self):
        from rcm_mc.ui.portfolio_overview import render_portfolio_overview
        h = render_portfolio_overview(self._portfolio(5), None)
        self.assertIn("degrees of freedom", h)

    def test_larger_portfolio_not_flagged(self):
        from rcm_mc.ui.portfolio_overview import render_portfolio_overview
        h = render_portfolio_overview(self._portfolio(12), None)
        self.assertNotIn("degrees of freedom", h)


if __name__ == "__main__":
    unittest.main()
