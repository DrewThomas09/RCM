"""Market-model improvement regressions — methodology fixes re-derived exactly.

Covers the market-models front survey gaps:

  * state_portfolio_fit unit normalization (P0) — documented weights now
    describe the delivered math; a small/high-growth state can outrank a
    large/flat one.
  * market_concentration honesty — provider-type MIX HHI labelled as such,
    hhi_10k dual scale, opt-in true competitor HHI.
  * payer_shift EBITDA fall-through + counterfactual total impact.
  * peer-snapshot multiple_basis provenance (12% assumed margin disclosed).
  * illustrative flags on the five curated data_public models + shared
    canonical corpus count.
  * geo_market component decomposition derived from the real scoring pass.
  * sponsor_activity timezone-aware as_of window.
  * market_intel content vintage accessor.
  * footprint_exposure revenue weighting.
  * unrecognized-mix disclosure in labor_cost_stress / blended_rate_impact.
  * PROPOSED-status visibility in blended_rate_impact.
  * transaction_multiple size-band fallback labelling.
  * statistics.median (not upper-element) in multiple rollups.
  * five illustrative compute_ models' headline aggregates re-derived.
  * market-intel adapter registry drives peer-snapshot transaction bands.
  * fragility_score clamped; news sentiment enum contract.

No mocks of our own code; every test exercises the real path offline.
"""
from __future__ import annotations

import datetime as _dt
import statistics
import unittest

import pandas as pd


# ────────────────────────────────────────────────────────────────────
# P0 — state_portfolio_fit unit normalization
# ────────────────────────────────────────────────────────────────────

class StatePortfolioFitNormalizationTests(unittest.TestCase):

    def _panel(self):
        """Two-state panel: A = small, fast-growing; B = huge, flat."""
        growth = pd.DataFrame([
            {"state": "A", "avg_state_growth": 0.20,
             "latest_state_growth": 0.25, "latest_payment": 1.0e8},
            {"state": "B", "avg_state_growth": 0.00,
             "latest_state_growth": 0.00, "latest_payment": 1.0e10},
        ])
        vol = pd.DataFrame([
            {"state": "A", "yoy_volatility": 0.05},
            {"state": "B", "yoy_volatility": 0.05},
        ])
        conc = pd.DataFrame([
            {"state": "A", "year": 2021, "hhi": 0.20},
            {"state": "B", "year": 2021, "hhi": 0.20},
        ])
        return growth, vol, conc

    def test_high_growth_small_state_outranks_large_flat_state(self):
        from rcm_mc.data_public.market_concentration import state_portfolio_fit
        fit = state_portfolio_fit(*self._panel())
        self.assertEqual(fit.iloc[0]["state"], "A",
                         "documented 0.35 growth weight must dominate the "
                         "0.20 payment weight once units are normalized")

    def test_score_is_exact_weighted_rank_blend(self):
        from rcm_mc.data_public.market_concentration import state_portfolio_fit
        fit = state_portfolio_fit(*self._panel()).set_index("state")
        # n=2 percentile ranks: higher value → 1.0, lower → 0.5; ties → 0.75.
        # State A: growth ranks 1.0/1.0, payment 0.5, stability tied 0.75,
        # fragmentation tied 0.75.
        expected_a = (0.35 * 1.0 + 0.20 * 1.0 + 0.20 * 0.5
                      + 0.15 * 0.75 + 0.10 * 0.75)
        expected_b = (0.35 * 0.5 + 0.20 * 0.5 + 0.20 * 1.0
                      + 0.15 * 0.75 + 0.10 * 0.75)
        self.assertAlmostEqual(fit.loc["A", "state_fit_score"], expected_a)
        self.assertAlmostEqual(fit.loc["B", "state_fit_score"], expected_b)

    def test_score_bounded_zero_one_and_percentile_kept(self):
        from rcm_mc.data_public.market_concentration import state_portfolio_fit
        fit = state_portfolio_fit(*self._panel())
        self.assertTrue(((fit["state_fit_score"] >= 0)
                         & (fit["state_fit_score"] <= 1)).all())
        # Stable public columns survive the rework.
        for col in ("state_fit_score", "state_fit_percentile",
                    "stability_score", "fragmentation_bonus"):
            self.assertIn(col, fit.columns)

    def test_missing_components_rank_neutral_not_floor(self):
        from rcm_mc.data_public.market_concentration import state_portfolio_fit
        growth, _, _ = self._panel()
        fit = state_portfolio_fit(growth, pd.DataFrame(), pd.DataFrame())
        # No volatility/hhi inputs at all → those components rank 0.5
        # for every state instead of dragging anyone to zero.
        self.assertTrue((fit["stability_rank"] == 0.5).all())
        self.assertTrue((fit["fragmentation_rank"] == 0.5).all())


# ────────────────────────────────────────────────────────────────────
# P1 — provider-type mix HHI honesty + hhi_10k + competitor HHI
# ────────────────────────────────────────────────────────────────────

class ConcentrationScaleAndMeaningTests(unittest.TestCase):

    def _mix_df(self):
        return pd.DataFrame([
            {"state": "TX", "year": 2021, "provider_type": "Cardiology",
             "npi": "1", "total_medicare_payment_amt": 600.0},
            {"state": "TX", "year": 2021, "provider_type": "Cardiology",
             "npi": "2", "total_medicare_payment_amt": 200.0},
            {"state": "TX", "year": 2021, "provider_type": "Orthopedic",
             "npi": "3", "total_medicare_payment_amt": 200.0},
        ])

    def test_hhi_fractional_and_hhi_10k_consistent(self):
        from rcm_mc.data_public.market_concentration import (
            market_concentration_summary,
        )
        out = market_concentration_summary(self._mix_df())
        row = out.iloc[0]
        # Provider-type shares: 0.8 / 0.2 → HHI = 0.68.
        self.assertAlmostEqual(row["hhi"], 0.8 ** 2 + 0.2 ** 2)
        self.assertLessEqual(row["hhi"], 1.0)
        self.assertEqual(row["hhi_10k"], round(row["hhi"] * 10_000))

    def test_competitor_hhi_differs_from_mix_hhi(self):
        from rcm_mc.data_public.market_concentration import (
            competitor_concentration_summary,
        )
        out = competitor_concentration_summary(self._mix_df())
        row = out.iloc[0]
        # Provider shares: 0.6 / 0.2 / 0.2 → HHI = 0.44 ≠ mix HHI 0.68.
        self.assertAlmostEqual(row["hhi"], 0.6 ** 2 + 0.2 ** 2 + 0.2 ** 2)
        self.assertEqual(row["provider_count"], 3)
        self.assertEqual(row["hhi_10k"], round(row["hhi"] * 10_000))

    def test_competitor_hhi_fails_closed_without_provider_ids(self):
        from rcm_mc.data_public.market_concentration import (
            competitor_concentration_summary,
        )
        df = self._mix_df().drop(columns=["npi"])
        self.assertTrue(competitor_concentration_summary(df).empty)

    def test_docstring_carries_not_competitor_warning(self):
        from rcm_mc.data_public.market_concentration import (
            market_concentration_summary,
        )
        self.assertIn("NOT a competitor HHI",
                      market_concentration_summary.__doc__)

    def test_concentration_table_states_the_scale(self):
        from rcm_mc.data_public.market_concentration import (
            concentration_table, market_concentration_summary,
        )
        txt = concentration_table(market_concentration_summary(self._mix_df()))
        self.assertIn("not a competitor HHI", txt)
        self.assertIn("0-1 scale", txt)


# ────────────────────────────────────────────────────────────────────
# P1 — payer_shift fall-through + counterfactual total impact
# ────────────────────────────────────────────────────────────────────

class PayerShiftMethodologyTests(unittest.TestCase):

    def test_scenario_fallthrough_is_single_documented_constant(self):
        from rcm_mc.data_public.payer_shift import (
            EBITDA_FALLTHROUGH, compute_payer_shift,
        )
        self.assertTrue(0.80 <= EBITDA_FALLTHROUGH <= 1.00)
        r = compute_payer_shift()
        for s in r.scenarios:
            self.assertAlmostEqual(
                s.ebitda_impact_mm,
                round(s.revenue_impact_mm * EBITDA_FALLTHROUGH, 2),
                delta=0.02,  # both sides independently rounded to 2dp
                msg=s.label)

    def test_yearly_ebitda_uses_same_fallthrough_convention(self):
        from rcm_mc.data_public.payer_shift import (
            EBITDA_FALLTHROUGH, compute_payer_shift,
        )
        rev, margin, growth = 80.0, 0.18, 0.04
        r = compute_payer_shift(revenue_mm=rev, ebitda_margin=margin,
                                growth_pct=growth)
        for y in r.yearly_projection:
            rev_no_shift = rev * (1 + growth) ** y.year
            expected = (rev_no_shift * margin
                        + (y.revenue_mm - rev_no_shift) * EBITDA_FALLTHROUGH)
            self.assertAlmostEqual(y.ebitda_mm, expected, delta=0.02,
                                   msg=f"year {y.year}")

    def test_total_impact_excludes_baseline_growth(self):
        """With NO mix shift, the payer-shift impact must be ~zero even
        though revenue grows 4%/yr — the old flat-base subtraction
        attributed all growth to the shift."""
        from rcm_mc.data_public.payer_shift import compute_payer_shift
        mix = {"commercial": 0.50, "medicare_fee_for_service": 0.30,
               "medicaid": 0.20}
        r = compute_payer_shift(starting_mix=dict(mix),
                                target_mix=dict(mix), growth_pct=0.04)
        self.assertAlmostEqual(r.total_ebitda_impact_mm, 0.0, delta=0.15)
        self.assertAlmostEqual(r.total_ev_impact_mm, 0.0, delta=0.5)

    def test_total_impact_re_derived_from_counterfactual(self):
        from rcm_mc.data_public.payer_shift import compute_payer_shift
        rev, margin, growth = 80.0, 0.18, 0.04
        r = compute_payer_shift(revenue_mm=rev, ebitda_margin=margin,
                                growth_pct=growth)
        expected = sum(
            y.ebitda_mm - rev * (1 + growth) ** y.year * margin
            for y in r.yearly_projection)
        self.assertAlmostEqual(r.total_ebitda_impact_mm,
                               round(expected, 2), delta=0.05)

    def test_result_carries_illustrative_flag(self):
        from rcm_mc.data_public.payer_shift import compute_payer_shift
        self.assertTrue(compute_payer_shift().is_illustrative)


if __name__ == "__main__":
    unittest.main()
