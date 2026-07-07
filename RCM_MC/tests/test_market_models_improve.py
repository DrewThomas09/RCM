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

    def test_pipeline_consumer_still_works_end_to_end(self):
        """run_market_analysis (advisory memo / corpus CLI path) must
        keep producing a sorted portfolio_fit with the stable columns
        after the rank-normalization rework."""
        from rcm_mc.data_public.cms_market_analysis import (
            analysis_summary_text, run_market_analysis,
        )
        df = pd.DataFrame([
            {"state": st, "year": yr, "provider_type": pt, "npi": f"{st}{pt}{yr}",
             "total_medicare_payment_amt": amt}
            for st, base in (("TX", 1000.0), ("CA", 5000.0), ("OK", 200.0))
            for yr, mult in ((2020, 1.0), (2021, 1.2))
            for pt, amt in (("Cardiology", base * mult),
                            ("Orthopedic", base * 0.5 * mult))
        ])
        report = run_market_analysis(df=df)
        fit = report.portfolio_fit
        self.assertFalse(fit.empty)
        for col in ("state", "state_fit_score", "state_fit_percentile"):
            self.assertIn(col, fit.columns)
        scores = list(fit["state_fit_score"])
        self.assertEqual(scores, sorted(scores, reverse=True))
        # Text summary renders with the new score scale (0-1).
        txt = analysis_summary_text(report)
        self.assertIn("Top Portfolio Fit States", txt)

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


# ────────────────────────────────────────────────────────────────────
# P1 — peer snapshot discloses the multiple's basis
# ────────────────────────────────────────────────────────────────────

class PeerSnapshotBasisTests(unittest.TestCase):

    def test_actual_ebitda_basis(self):
        from rcm_mc.market_intel import compute_peer_snapshot
        s = compute_peer_snapshot(
            category="MULTI_SITE_ACUTE_HOSPITAL",
            target_ev_usd=350_000_000, target_ebitda_usd=35_000_000,
        )
        self.assertEqual(s.multiple_basis, "actual_ebitda")
        self.assertIsNone(s.assumed_margin)
        d = s.to_dict()
        self.assertEqual(d["multiple_basis"], "actual_ebitda")
        self.assertIsNone(d["assumed_margin"])

    def test_assumed_margin_basis_disclosed_in_payload_and_summary(self):
        from rcm_mc.market_intel import (
            ASSUMED_EBITDA_MARGIN, compute_peer_snapshot,
        )
        s = compute_peer_snapshot(
            category="MULTI_SITE_ACUTE_HOSPITAL",
            target_ev_usd=350_000_000, target_revenue_usd=250_000_000,
        )
        self.assertEqual(s.multiple_basis, "assumed_margin_12pct")
        self.assertEqual(s.assumed_margin, ASSUMED_EBITDA_MARGIN)
        # Exact re-derivation: EV / (revenue × 12%).
        self.assertAlmostEqual(
            s.target_implied_multiple,
            350_000_000 / (250_000_000 * ASSUMED_EBITDA_MARGIN), places=6)
        self.assertIn("assumed", s.summary.lower())
        self.assertIn("12%", s.summary)

    def test_no_multiple_no_basis(self):
        from rcm_mc.market_intel import compute_peer_snapshot
        s = compute_peer_snapshot(category="MULTI_SITE_ACUTE_HOSPITAL")
        self.assertIsNone(s.target_implied_multiple)
        self.assertIsNone(s.multiple_basis)

    def test_summary_multiples_render_2dp(self):
        from rcm_mc.market_intel import compute_peer_snapshot
        s = compute_peer_snapshot(
            category="MULTI_SITE_ACUTE_HOSPITAL",
            target_ev_usd=350_000_000, target_ebitda_usd=35_000_000,
        )
        self.assertIn("10.00x", s.summary)   # 2dp+x house convention


# ────────────────────────────────────────────────────────────────────
# P2 — adapter registry is real and drives peer-snapshot bands
# ────────────────────────────────────────────────────────────────────

class AdapterRegistryTests(unittest.TestCase):

    def test_default_is_manual_adapter(self):
        from rcm_mc.market_intel import ManualMarketIntelAdapter, get_adapter
        self.assertIsInstance(get_adapter(), ManualMarketIntelAdapter)

    def test_set_adapter_rejects_non_conforming_object(self):
        from rcm_mc.market_intel import set_adapter
        with self.assertRaises(TypeError):
            set_adapter(object())

    def test_swapped_adapter_reaches_peer_snapshot(self):
        from rcm_mc.market_intel import compute_peer_snapshot, set_adapter
        from rcm_mc.market_intel.transaction_multiples import MultipleBand

        class FakeVendorAdapter:
            def public_comps(self):
                return []

            def transaction_multiple(self, *, specialty, ev_usd=None):
                return MultipleBand(
                    specialty=specialty, deal_size_band="VENDOR_TEST",
                    p25_ev_ebitda=7.00, p50_ev_ebitda=9.00,
                    p75_ev_ebitda=11.00, sample_size=99,
                )

            def news_for_target(self, *, specialty=None, tickers=None,
                                limit=20):
                return []

        prev = set_adapter(FakeVendorAdapter())
        try:
            s = compute_peer_snapshot(
                category="MULTI_SITE_ACUTE_HOSPITAL",
                target_ev_usd=350_000_000,
                target_ebitda_usd=35_000_000,
                specialty="ANESTHESIOLOGY",
            )
            self.assertEqual(
                s.transaction_band["deal_size_band"], "VENDOR_TEST")
            self.assertEqual(s.transaction_band["sample_size"], 99)
        finally:
            set_adapter(prev)
        # Restored: manual adapter serves the curated band again.
        s2 = compute_peer_snapshot(
            category="MULTI_SITE_ACUTE_HOSPITAL",
            target_ev_usd=350_000_000, target_ebitda_usd=35_000_000,
            specialty="ANESTHESIOLOGY",
        )
        self.assertNotEqual(
            s2.transaction_band["deal_size_band"], "VENDOR_TEST")

    def test_stub_message_names_the_real_install_function(self):
        from rcm_mc.market_intel import StubVendorSeekingAlphaAdapter
        with self.assertRaises(NotImplementedError) as cm:
            StubVendorSeekingAlphaAdapter("key").public_comps()
        self.assertIn("set_adapter", str(cm.exception))


# ────────────────────────────────────────────────────────────────────
# P2 — transaction_multiple labels size-band fallbacks
# ────────────────────────────────────────────────────────────────────

class TransactionMultipleFallbackTests(unittest.TestCase):

    def test_matched_band_reports_size_band(self):
        from rcm_mc.market_intel import transaction_multiple
        m = transaction_multiple(
            specialty="MULTI_SITE_PHYSICIAN_GROUP", ev_usd=50_000_000)
        self.assertEqual(m.deal_size_band, "SUB_100M")
        self.assertEqual(m.match_basis, "size_band")
        self.assertEqual(m.to_dict()["match_basis"], "size_band")

    def test_no_size_requested_reports_default(self):
        from rcm_mc.market_intel import transaction_multiple
        m = transaction_multiple(specialty="MULTI_SITE_PHYSICIAN_GROUP")
        self.assertEqual(m.match_basis, "largest_sample_default")

    def test_unavailable_requested_band_reports_fallback(self):
        from rcm_mc.market_intel import transaction_multiple
        m = transaction_multiple(
            specialty="MULTI_SITE_PHYSICIAN_GROUP",
            deal_size_band="NO_SUCH_BAND",
        )
        self.assertIsNotNone(m)
        self.assertEqual(m.match_basis, "largest_sample_fallback")


# ────────────────────────────────────────────────────────────────────
# P2 — content vintage accessor + YAML contract
# ────────────────────────────────────────────────────────────────────

class ContentVintageTests(unittest.TestCase):

    def test_every_content_yaml_has_parseable_last_reviewed(self):
        from rcm_mc.market_intel import content_freshness_report
        from rcm_mc.market_intel.content_vintage import CONTENT_FILES
        report = content_freshness_report()
        self.assertEqual(set(report), set(CONTENT_FILES))
        for name, row in report.items():
            self.assertIsNone(row["error"], f"{name}: {row['error']}")
            self.assertIsNotNone(row["last_reviewed"], name)
            _dt.date.fromisoformat(row["last_reviewed"])  # parseable
            self.assertTrue(row["source_urls"] or name == "pe_transactions",
                            f"{name} missing source_urls")

    def test_staleness_clock_is_injectable_and_correct(self):
        from rcm_mc.market_intel import content_vintage
        v = content_vintage("ma_penetration")
        reviewed = _dt.date.fromisoformat(v["last_reviewed"])
        fresh_day = reviewed + _dt.timedelta(days=10)
        stale_day = reviewed + _dt.timedelta(days=121)
        self.assertFalse(
            content_vintage("ma_penetration", today=fresh_day)["stale"])
        self.assertTrue(
            content_vintage("ma_penetration", today=stale_day)["stale"])
        self.assertEqual(
            content_vintage("ma_penetration", today=fresh_day)["age_days"],
            10)

    def test_missing_file_fails_closed(self):
        from rcm_mc.market_intel import content_vintage
        v = content_vintage("no_such_content")
        self.assertTrue(v["stale"])
        self.assertEqual(v["error"], "missing")


# ────────────────────────────────────────────────────────────────────
# P1 — illustrative flags + one canonical corpus count for the five
# curated data_public market models
# ────────────────────────────────────────────────────────────────────

class IllustrativeModelContractTests(unittest.TestCase):

    def _results(self):
        from rcm_mc.data_public.geo_market import compute_geo_market
        from rcm_mc.data_public.msa_concentration import (
            compute_msa_concentration,
        )
        from rcm_mc.data_public.payer_shift import compute_payer_shift
        from rcm_mc.data_public.peer_transactions import (
            compute_peer_transactions,
        )
        from rcm_mc.data_public.physician_labor import (
            compute_physician_labor,
        )
        return {
            "geo_market": compute_geo_market(),
            "msa_concentration": compute_msa_concentration(),
            "payer_shift": compute_payer_shift(),
            "peer_transactions": compute_peer_transactions(),
            "physician_labor": compute_physician_labor(),
        }

    def test_all_five_results_carry_illustrative_flag(self):
        for name, r in self._results().items():
            self.assertTrue(getattr(r, "is_illustrative"), name)

    def test_all_five_module_docstrings_open_with_illustrative(self):
        import rcm_mc.data_public.geo_market as gm
        import rcm_mc.data_public.msa_concentration as mc
        import rcm_mc.data_public.payer_shift as ps
        import rcm_mc.data_public.peer_transactions as pt
        import rcm_mc.data_public.physician_labor as pl
        for mod in (gm, mc, ps, pt, pl):
            self.assertTrue(mod.__doc__.startswith("ILLUSTRATIVE"),
                            mod.__name__)
            self.assertIn("Do not quote", mod.__doc__, mod.__name__)

    def test_corpus_deal_count_agrees_across_all_five(self):
        from rcm_mc.data_public.corpus_loader import load_corpus_deals
        canonical = len(load_corpus_deals("all"))
        for name, r in self._results().items():
            self.assertEqual(r.corpus_deal_count, canonical, name)

    def test_pages_keep_their_illustrative_notes(self):
        from rcm_mc.ui.data_public.geo_market_page import render_geo_market
        from rcm_mc.ui.data_public.msa_concentration_page import (
            render_msa_concentration,
        )
        from rcm_mc.ui.data_public.payer_shift_page import render_payer_shift
        from rcm_mc.ui.data_public.peer_transactions_page import (
            render_peer_transactions,
        )
        from rcm_mc.ui.data_public.physician_labor_page import (
            render_physician_labor,
        )
        for fn in (render_geo_market, render_msa_concentration,
                   render_payer_shift, render_peer_transactions,
                   render_physician_labor):
            self.assertIn("ck-illus-note", fn({}), fn.__name__)


# ────────────────────────────────────────────────────────────────────
# P1 — geo_market components decompose the real score
# ────────────────────────────────────────────────────────────────────

class GeoMarketDecompositionTests(unittest.TestCase):

    def test_contributions_sum_to_panel_average_composite(self):
        from rcm_mc.data_public.geo_market import compute_geo_market
        r = compute_geo_market(sector="Physician Services")
        contrib = sum(c.contribution for c in r.components)
        panel_avg = (sum(m.white_space_score for m in r.markets)
                     / len(r.markets))
        self.assertAlmostEqual(contrib, panel_avg, delta=0.5)

    def test_components_re_derived_from_dimension_scores(self):
        from rcm_mc.data_public.geo_market import (
            _CBSAS, _dimension_scores, compute_geo_market,
        )
        sector = "Senior Primary Care"
        r = compute_geo_market(sector=sector)
        per_market = [_dimension_scores(m, sector) for m in _CBSAS]
        for c in r.components:
            expected = sum(s[c.dimension] for s in per_market) / len(_CBSAS)
            self.assertAlmostEqual(c.normalized_score, expected, delta=0.06,
                                   msg=c.dimension)
            self.assertAlmostEqual(c.contribution,
                                   round(expected * c.weight, 1),
                                   delta=0.06, msg=c.dimension)

    def test_components_respond_to_sector(self):
        """Senior sectors flip the demographic-fit dimension, so the
        panel is provably not a hardcoded constant table."""
        from rcm_mc.data_public.geo_market import compute_geo_market
        base = {c.dimension: c.normalized_score
                for c in compute_geo_market("Physician Services").components}
        senior = {c.dimension: c.normalized_score
                  for c in compute_geo_market("Dialysis").components}
        self.assertNotEqual(base["Demographic Fit"],
                            senior["Demographic Fit"])

    def test_weights_sum_to_one_and_tier_counts_match_thresholds(self):
        from rcm_mc.data_public.geo_market import compute_geo_market
        r = compute_geo_market()
        self.assertAlmostEqual(sum(c.weight for c in r.components), 1.0)
        for m in r.markets:
            s = m.white_space_score
            expected = ("Priority" if s >= 68 else "Watch" if s >= 55
                        else "Secondary" if s >= 40 else "Avoid")
            self.assertEqual(m.tier, expected, m.cbsa)
        self.assertEqual(r.priority_markets,
                         sum(1 for m in r.markets if m.tier == "Priority"))

    def test_payback_years_derived_not_constant(self):
        from rcm_mc.data_public.geo_market import (
            _ACQUISITION_EBITDA_MARGIN, _DE_NOVO_CONTRIBUTION_MARGIN,
            compute_geo_market,
        )
        r = compute_geo_market()
        for s in r.entry_scenarios:
            margin = (_DE_NOVO_CONTRIBUTION_MARGIN
                      if s.entry_strategy.startswith("De novo")
                      else _ACQUISITION_EBITDA_MARGIN)
            expected = round(s.capex_mm / (s.year3_revenue_mm * margin), 1)
            self.assertAlmostEqual(s.payback_years, expected, places=1,
                                   msg=s.entry_strategy)


# ────────────────────────────────────────────────────────────────────
# P2 — sponsor_activity deterministic window
# ────────────────────────────────────────────────────────────────────

class SponsorActivityWindowTests(unittest.TestCase):

    def test_as_of_pins_the_window(self):
        from rcm_mc.market_intel import list_transactions, sponsor_activity
        newest = max(t.date for t in list_transactions())
        y, m, d = (int(p) for p in newest.split("-"))
        inside = sponsor_activity(
            lookback_months=12, as_of=_dt.date(y, m, d))
        self.assertTrue(inside, "window anchored at newest fixture "
                                "date must see activity")
        # Anchor two years past the newest fixture: window empties —
        # the aging failure mode is now provable instead of latent.
        stale = sponsor_activity(
            lookback_months=12, as_of=_dt.date(y + 2, m, d))
        self.assertEqual(stale, {})

    def test_counts_re_derived_for_pinned_window(self):
        from rcm_mc.market_intel import list_transactions, sponsor_activity
        as_of = _dt.date(2026, 4, 30)
        act = sponsor_activity(lookback_months=12, as_of=as_of)
        expected: dict = {}
        for t in list_transactions():
            y, m, _ = (int(p) for p in t.date.split("-"))
            delta = (as_of.year - y) * 12 + (as_of.month - m)
            if 0 <= delta <= 12:
                expected[t.sponsor] = expected.get(t.sponsor, 0) + 1
        self.assertEqual(act, dict(sorted(expected.items(),
                                          key=lambda kv: -kv[1])))

    def test_default_clock_is_utc_today(self):
        from rcm_mc.market_intel import sponsor_activity
        today = _dt.datetime.now(_dt.timezone.utc).date()
        self.assertEqual(sponsor_activity(lookback_months=600),
                         sponsor_activity(lookback_months=600,
                                          as_of=today))


# ────────────────────────────────────────────────────────────────────
# P2 — footprint_exposure revenue weighting
# ────────────────────────────────────────────────────────────────────

class FootprintWeightingTests(unittest.TestCase):

    def test_equal_weight_default_unchanged_and_labelled(self):
        from rcm_mc.market_intel.ma_penetration import (
            footprint_exposure, get_state,
        )
        fl = get_state("FL").penetration_pct
        ak = get_state("AK").penetration_pct
        fp = footprint_exposure(["FL", "AK"])
        self.assertEqual(fp["weighting"], "equal")
        self.assertAlmostEqual(fp["avg_penetration_pct"],
                               round((fl + ak) / 2, 1))

    def test_revenue_weights_change_the_read(self):
        from rcm_mc.market_intel.ma_penetration import (
            footprint_exposure, get_state, national_penetration_pct,
        )
        fl = get_state("FL").penetration_pct
        ak = get_state("AK").penetration_pct
        fp = footprint_exposure(["FL", "AK"],
                                weights={"FL": 0.9, "AK": 0.1})
        self.assertEqual(fp["weighting"], "revenue")
        expected = 0.9 * fl + 0.1 * ak
        self.assertAlmostEqual(fp["avg_penetration_pct"],
                               round(expected, 1))
        self.assertAlmostEqual(
            fp["vs_national_pp"],
            round(expected - national_penetration_pct(), 1))
        # Per-state normalized weights disclosed.
        by_state = {s["state"]: s for s in fp["states"]}
        self.assertAlmostEqual(by_state["FL"]["weight_pct"], 90.0)
        self.assertAlmostEqual(by_state["AK"]["weight_pct"], 10.0)

    def test_weights_for_unknown_states_fall_back_to_equal(self):
        from rcm_mc.market_intel.ma_penetration import footprint_exposure
        fp = footprint_exposure(["FL", "AK"], weights={"ZZ": 1.0})
        self.assertEqual(fp["weighting"], "equal")


# ────────────────────────────────────────────────────────────────────
# P2 — unrecognized-mix mass disclosed; PROPOSED status surfaced
# ────────────────────────────────────────────────────────────────────

class UnrecognizedMixDisclosureTests(unittest.TestCase):

    def test_labor_stress_reports_unmatched_mass(self):
        from rcm_mc.market_intel.labor_market import labor_cost_stress
        s = labor_cost_stress(10_000_000, {"RN": 60.0, "ZZZ": 40.0})
        self.assertAlmostEqual(s.unrecognized_share_pct, 40.0)
        self.assertEqual(s.unrecognized_codes, ["ZZZ"])
        clean = labor_cost_stress(10_000_000, {"RN": 100.0})
        self.assertEqual(clean.unrecognized_share_pct, 0.0)
        self.assertEqual(clean.unrecognized_codes, [])

    def test_labor_stress_all_unknown_reports_full_mass(self):
        from rcm_mc.market_intel.labor_market import labor_cost_stress
        s = labor_cost_stress(10_000_000, {"AAA": 30.0, "BBB": 70.0})
        self.assertAlmostEqual(s.unrecognized_share_pct, 100.0)
        self.assertEqual(s.annual_cost_increase_usd, 0.0)

    def test_blended_rate_impact_reports_unmatched_mass(self):
        from rcm_mc.market_intel.rate_environment import blended_rate_impact
        i = blended_rate_impact(1_000_000, {"PFS": 50.0, "XX": 50.0})
        self.assertAlmostEqual(i.unrecognized_share_pct, 50.0)
        self.assertEqual(i.unrecognized_codes, ["XX"])

    def test_per_setting_rows_carry_status_all_final_today(self):
        from rcm_mc.market_intel.rate_environment import blended_rate_impact
        i = blended_rate_impact(60_000_000, {"PFS": 40.0, "OPPS": 60.0})
        self.assertFalse(i.has_proposed)
        for row in i.per_setting:
            self.assertEqual(row["status"], "FINAL")

    def test_proposed_status_flips_has_proposed(self):
        """Synthetic PROPOSED cycle through the real blend path (the
        injectable ``settings`` seam, same pattern as
        run_market_analysis(df=...))."""
        from rcm_mc.market_intel.rate_environment import (
            RateUpdate, SettingRates, blended_rate_impact, get_setting,
        )
        proposed_pfs = SettingRates(
            setting="PFS", label="Physician fee schedule", cycle="CY",
            updates=[
                RateUpdate("CY2026", -2.8, "FINAL"),
                RateUpdate("CY2027", 1.2, "PROPOSED"),
            ])
        i = blended_rate_impact(
            10_000_000, {"PFS": 70.0, "OPPS": 30.0},
            settings=[proposed_pfs, get_setting("OPPS")])
        self.assertTrue(i.has_proposed)
        by_setting = {r["setting"]: r for r in i.per_setting}
        self.assertEqual(by_setting["PFS"]["status"], "PROPOSED")
        self.assertEqual(by_setting["PFS"]["period"], "CY2027")
        self.assertEqual(by_setting["OPPS"]["status"], "FINAL")
        # Blend re-derived: 0.7×1.2 + 0.3×(OPPS latest).
        opps = get_setting("OPPS").latest().net_update_pct
        self.assertAlmostEqual(i.blended_update_pct,
                               round(0.7 * 1.2 + 0.3 * opps, 2))


# ────────────────────────────────────────────────────────────────────
# P2 — true medians on even n
# ────────────────────────────────────────────────────────────────────

class MedianCorrectnessTests(unittest.TestCase):

    def test_pe_transactions_specialty_median_is_true_median(self):
        from rcm_mc.market_intel.pe_transactions import (
            list_transactions, multiple_band_by_specialty,
        )
        by_sp: dict = {}
        for t in list_transactions():
            if t.ev_ebitda_multiple and t.specialty:
                by_sp.setdefault(t.specialty, []).append(
                    float(t.ev_ebitda_multiple))
        bands = multiple_band_by_specialty()
        for sp, mults in by_sp.items():
            self.assertAlmostEqual(bands[sp]["median"],
                                   statistics.median(mults), msg=sp)
        # At least one even-n specialty must exist for this test to
        # bite; if the library ever becomes all-odd, extend the YAML.
        self.assertTrue(any(len(v) % 2 == 0 for v in by_sp.values()),
                        "no even-n specialty left — test lost its bite")

    def test_peer_transactions_headline_medians_true(self):
        from rcm_mc.data_public.peer_transactions import (
            compute_peer_transactions,
        )
        r = compute_peer_transactions()
        self.assertAlmostEqual(
            r.median_ev_ebitda,
            round(statistics.median(d.ev_ebitda_x for d in r.deals), 2))
        self.assertAlmostEqual(
            r.median_ev_revenue,
            round(statistics.median(d.ev_revenue_x for d in r.deals), 2))
        # n=20 (even): the upper-element pick would differ from the
        # central-pair mean — assert we're on the true median.
        self.assertEqual(len(r.deals) % 2, 0)

    def test_no_string_values_in_numeric_dataclass_fields(self):
        from rcm_mc.data_public.peer_transactions import (
            compute_peer_transactions,
        )
        r = compute_peer_transactions()
        for t in r.deal_types:
            for fld in ("median_ev_ebitda_x", "typical_holding_period",
                        "typical_leverage", "median_size_m"):
                v = getattr(t, fld)
                self.assertNotIsInstance(v, str,
                                         f"{t.deal_type}.{fld}")
        # The two None-able rows exist and are None, not "n/a".
        by_type = {t.deal_type: t for t in r.deal_types}
        self.assertIsNone(by_type["Dividend Recap"].median_ev_ebitda_x)
        self.assertIsNone(by_type["Strategic M&A"].typical_holding_period)


# ────────────────────────────────────────────────────────────────────
# P2 — five illustrative models' headline aggregates re-derived
# ────────────────────────────────────────────────────────────────────

class IllustrativeAggregateRederivationTests(unittest.TestCase):

    def test_physician_labor_blended_wage_is_headcount_weighted(self):
        from rcm_mc.data_public.physician_labor import (
            compute_physician_labor,
        )
        r = compute_physician_labor()
        total = sum(s.active_physicians for s in r.specialties)
        expected_wage = sum(
            s.wage_inflation_ltm_pct * s.active_physicians
            for s in r.specialties) / total
        expected_age = sum(
            s.median_age * s.active_physicians
            for s in r.specialties) / total
        self.assertEqual(r.total_active_physicians, total)
        self.assertAlmostEqual(r.blended_wage_inflation_pct,
                               round(expected_wage, 4))
        self.assertAlmostEqual(r.avg_median_age, round(expected_age, 1))
        self.assertEqual(
            r.specialties_in_shortage,
            sum(1 for s in r.specialties
                if s.projected_2030_shortage > 5000))

    def test_msa_regime_counts_and_averages_re_derived(self):
        from rcm_mc.data_public.msa_concentration import (
            compute_msa_concentration,
        )
        r = compute_msa_concentration()
        self.assertEqual(r.total_msas_analyzed, len(r.msa_details))
        self.assertEqual(
            r.fragmented_count,
            sum(1 for m in r.msa_details
                if m.market_structure == "fragmented"))
        self.assertEqual(
            r.highly_concentrated_count,
            sum(1 for m in r.msa_details
                if m.market_structure == "highly concentrated"))
        self.assertEqual(
            r.avg_hhi,
            int(sum(m.hhi for m in r.msa_details) / len(r.msa_details)))
        self.assertAlmostEqual(
            r.avg_cr3_pct,
            round(sum(m.cr3_pct for m in r.msa_details)
                  / len(r.msa_details), 4))
        # This panel uses the 0-10,000 HHI convention (vs 0-1 in
        # data_public.market_concentration) — pin the scale.
        self.assertTrue(all(100 <= m.hhi <= 10_000 for m in r.msa_details))

    def test_geo_market_addressable_pop_re_derived(self):
        from rcm_mc.data_public.geo_market import compute_geo_market
        r = compute_geo_market()
        expected = round(sum(
            m.population_k for m in r.markets
            if m.tier in ("Priority", "Watch")) / 1000, 1)
        self.assertEqual(r.total_addressable_pop_mm, expected)

    def test_payer_shift_yield_math_hand_computed_two_payer_mix(self):
        from rcm_mc.data_public.payer_shift import (
            _PAYER_COLLECTION_RATE, _PAYER_RATE_INDEX, _weighted_yield,
        )
        mix = {"commercial": 0.6, "medicaid": 0.4}
        expected = (0.6 * _PAYER_RATE_INDEX["commercial"]
                    * _PAYER_COLLECTION_RATE["commercial"]
                    + 0.4 * _PAYER_RATE_INDEX["medicaid"]
                    * _PAYER_COLLECTION_RATE["medicaid"])
        self.assertAlmostEqual(_weighted_yield(mix), expected)
        # 0.6×1.00×0.96 + 0.4×0.48×0.92 = 0.576 + 0.176640
        self.assertAlmostEqual(expected, 0.75264)

    def test_peer_transactions_total_volume_re_derived(self):
        from rcm_mc.data_public.peer_transactions import (
            compute_peer_transactions,
        )
        r = compute_peer_transactions()
        self.assertAlmostEqual(
            r.total_volume_b,
            round(sum(d.deal_size_m for d in r.deals) / 1000.0, 2))

    def test_payload_key_sets_stable_for_back_compat(self):
        """The five results keep every pre-existing field (additive
        evolution only) — a rename here breaks five pages at once."""
        from dataclasses import fields
        from rcm_mc.data_public.geo_market import GeoMarketResult
        from rcm_mc.data_public.msa_concentration import MSAResult
        from rcm_mc.data_public.payer_shift import PayerShiftResult
        from rcm_mc.data_public.peer_transactions import PeerResult
        from rcm_mc.data_public.physician_labor import LaborResult
        expected = {
            GeoMarketResult: {
                "sector", "markets", "components", "entry_scenarios",
                "tiers", "priority_markets", "watch_markets",
                "secondary_markets", "avoid_markets",
                "total_addressable_pop_mm", "corpus_deal_count"},
            MSAResult: {
                "total_msas_analyzed", "fragmented_count",
                "moderately_concentrated_count",
                "highly_concentrated_count", "avg_hhi", "avg_cr3_pct",
                "msa_details", "regimes", "whitespace",
                "stress_scenarios", "top_operators", "corpus_deal_count"},
            PayerShiftResult: {
                "sector", "starting_mix", "target_mix", "scenarios",
                "yearly_projection", "base_revenue_mm",
                "terminal_revenue_mm", "total_ebitda_impact_mm",
                "total_ev_impact_mm", "corpus_deal_count"},
            PeerResult: {
                "total_transactions", "total_volume_b",
                "median_ev_ebitda", "median_ev_revenue", "ltm_trends",
                "deals", "sector_multiples", "deal_types", "buyers",
                "trends", "advisors", "corpus_deal_count"},
            LaborResult: {
                "total_active_physicians", "avg_median_age",
                "specialties_in_shortage", "blended_wage_inflation_pct",
                "specialties", "wages", "extenders", "burnout",
                "geography", "corpus_deal_count"},
        }
        for cls, keys in expected.items():
            have = {f.name for f in fields(cls)}
            self.assertTrue(keys.issubset(have),
                            f"{cls.__name__} lost {keys - have}")
            self.assertIn("is_illustrative", have, cls.__name__)


# ────────────────────────────────────────────────────────────────────
# P3 — fragility clamp + content sentiment/labor value contracts
# ────────────────────────────────────────────────────────────────────

class ContentContractTests(unittest.TestCase):

    def test_fragility_score_clamped_for_negative_wage_growth(self):
        from rcm_mc.market_intel.labor_market import RoleEconomics
        deflation = RoleEconomics(
            role="X", label="x", median_hourly_usd=30.0,
            wage_yoy_pct=-3.0, turnover_pct=0.0, vacancy_pct=0.0,
            replacement_weeks=4)
        self.assertEqual(deflation.fragility_score(), 0.0)
        maxed = RoleEconomics(
            role="Y", label="y", median_hourly_usd=30.0,
            wage_yoy_pct=99.0, turnover_pct=99.0, vacancy_pct=99.0,
            replacement_weeks=4)
        self.assertEqual(maxed.fragility_score(), 100.0)

    def test_news_item_sentiments_in_allowed_enum(self):
        from rcm_mc.market_intel.news_feed import _all_items, _load
        allowed = {"positive", "negative", "neutral", "mixed"}
        for item in _all_items():
            self.assertIn(item.sentiment, allowed, item.title)
        for sp, sent in (_load().get("sector_sentiment") or {}).items():
            self.assertIn(sent, allowed, sp)

    def test_labor_roles_have_non_negative_pressure_metrics(self):
        from rcm_mc.market_intel.labor_market import list_roles
        for r in list_roles():
            self.assertGreaterEqual(r.turnover_pct, 0.0, r.role)
            self.assertGreaterEqual(r.vacancy_pct, 0.0, r.role)
            self.assertGreaterEqual(r.replacement_weeks, 0, r.role)


if __name__ == "__main__":
    unittest.main()
