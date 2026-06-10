"""CIM Cross-Check / Variance Engine (P2) — unit + page tests.

Verification per the session plan: flags fire at exactly the spec
thresholds; estimators reproduce hand-computed scope numbers from the real
HCRIS frame; UNVERIFIABLE is its own state (never a silent pass); the memo
and CSV exports carry claim/estimate/variance/source/expert question.
"""
from __future__ import annotations

import unittest

import pandas as pd

from rcm_mc.diligence.cim_crosscheck import (
    classify_variance, run_crosscheck, variance_memo,
)

_DF = pd.DataFrame([
    # 4 TX hospitals + 1 OK control. Margins: 0.05, 0.10, (junk 0.90 — must
    # be excluded from the median by the plausible band), 0.0/NaN-mix.
    {"ccn": "450001", "state": "TX", "beds": 100, "net_patient_revenue": 1.0e8,
     "operating_expenses": 0.95e8, "total_patient_days": 20000,
     "medicare_day_pct": 0.30, "medicaid_day_pct": 0.10},
    {"ccn": "450002", "state": "TX", "beds": 200, "net_patient_revenue": 2.0e8,
     "operating_expenses": 1.8e8, "total_patient_days": 40000,
     "medicare_day_pct": 0.40, "medicaid_day_pct": 0.20},
    {"ccn": "450003", "state": "TX", "beds": 50, "net_patient_revenue": 1.0e8,
     "operating_expenses": 0.1e8,  # 90% margin — junk-opex artifact
     "total_patient_days": 10000,
     "medicare_day_pct": 0.20, "medicaid_day_pct": float("nan")},
    {"ccn": "450004", "state": "TX", "beds": 25, "net_patient_revenue": 0.5e8,
     "operating_expenses": 0.5e8, "total_patient_days": 5000,
     "medicare_day_pct": float("nan"), "medicaid_day_pct": 0.15},
    {"ccn": "370001", "state": "OK", "beds": 80, "net_patient_revenue": 9.9e8,
     "operating_expenses": 9.0e8, "total_patient_days": 90000,
     "medicare_day_pct": 0.50, "medicaid_day_pct": 0.05},
])


class ClassifyVarianceTests(unittest.TestCase):
    def test_thresholds_exact(self):
        self.assertEqual(classify_variance(0.10), "green")     # boundary in
        self.assertEqual(classify_variance(-0.10), "green")
        self.assertEqual(classify_variance(0.1001), "yellow")
        self.assertEqual(classify_variance(0.25), "yellow")    # boundary in
        self.assertEqual(classify_variance(-0.2501), "red")
        self.assertEqual(classify_variance(1.5), "red")

    def test_unverifiable_is_its_own_state(self):
        self.assertEqual(classify_variance(None), "unverifiable")
        self.assertEqual(classify_variance(float("nan")), "unverifiable")


class EstimatorScopingTests(unittest.TestCase):
    """Hand-computed TX scope: NPR Σ=4.5e8, days Σ=75,000, count=4,
    medicare median over {0.30,0.40,0.20}=0.30, margin median over the
    PLAUSIBLE values {5%,10%,0%}=5% (the 90% junk filing excluded)."""

    def _run(self, claims, **kw):
        return run_crosscheck(_DF, state="TX", claims=claims, **kw)

    def test_market_size_estimate(self):
        r = self._run({"market_size_dollars": 4.5e8}).rows[0]
        self.assertAlmostEqual(r.estimate.value, 4.5e8)
        self.assertEqual(r.estimate.n, 4)
        self.assertEqual(r.flag, "green")          # exact match

    def test_provider_count_and_days(self):
        res = self._run({"provider_count": 5, "inpatient_days": 75000})
        by = {r.claim_key: r for r in res.rows}
        self.assertEqual(by["provider_count"].estimate.value, 4)
        self.assertEqual(by["provider_count"].flag, "yellow")  # 5 vs 4 = +25%
        self.assertAlmostEqual(by["inpatient_days"].estimate.value, 75000)
        self.assertEqual(by["inpatient_days"].flag, "green")

    def test_margin_median_excludes_junk_filing(self):
        r = self._run({"median_operating_margin_pct": 5.0}).rows[0]
        # plausible margins: 5%, 10%, 0% → median 5.0 (90% artifact excluded)
        self.assertAlmostEqual(r.estimate.value, 5.0)
        self.assertEqual(r.flag, "green")

    def test_medicare_share_nan_excluded_not_zero_filled(self):
        r = self._run({"medicare_share_pct": 30.0}).rows[0]
        self.assertAlmostEqual(r.estimate.value, 30.0)   # median of 3 values
        self.assertEqual(r.estimate.n, 3)                # NaN row not counted

    def test_target_npr_check(self):
        res = self._run({"target_net_revenue_dollars": 1.0e8}, ccn="450001")
        r = res.rows[0]
        self.assertAlmostEqual(r.estimate.value, 1.0e8)
        self.assertEqual(r.flag, "green")
        # wrong-by-2x claim → red
        res2 = self._run({"target_net_revenue_dollars": 2.0e8}, ccn="450001")
        self.assertEqual(res2.rows[0].flag, "red")

    def test_unknown_ccn_is_unverifiable(self):
        res = self._run({"target_net_revenue_dollars": 1e8}, ccn="999999")
        self.assertEqual(res.rows[0].flag, "unverifiable")
        self.assertIsNone(res.rows[0].variance)

    def test_empty_scope_is_unverifiable_never_fabricated(self):
        res = run_crosscheck(_DF, state="WY", claims={"market_size_dollars": 1e8})
        self.assertEqual(res.rows[0].flag, "unverifiable")

    def test_beds_band_scoping(self):
        res = run_crosscheck(_DF, state="TX",
                             claims={"provider_count": 2}, min_beds=60)
        self.assertEqual(res.rows[0].estimate.value, 2)   # 100- and 200-bed


class MemoTests(unittest.TestCase):
    def test_memo_carries_all_fields(self):
        res = run_crosscheck(
            _DF, state="TX",
            claims={"market_size_dollars": 4.6e8, "provider_count": 9})
        memo = variance_memo(res)
        for needle in ("CIM CROSS-CHECK", "TX hospitals (n=4)",
                       "CMS HCRIS", "Expert-call question",
                       "UNVERIFIABLE = no public estimate"):
            self.assertIn(needle, memo)
        # 4.6e8 vs 4.5e8 = +2.2% → green; 9 vs 4 → red. Both flags named.
        self.assertIn("GREEN]", memo)
        self.assertIn("RED]", memo)
        self.assertIn("Summary: 1 green", memo)


class PageTests(unittest.TestCase):
    def test_page_renders_and_flags(self):
        from rcm_mc.ui.cim_crosscheck_page import render_cim_crosscheck
        h = render_cim_crosscheck({
            "state": ["TX"],
            "c_market_size_dollars": ["104200000000"],
            "c_provider_count": ["688"],
        })
        self.assertIn("Variance vs public data", h)
        self.assertIn("ENTERED", h)
        self.assertIn("ACTUAL", h)
        self.assertIn("cost-reports", h)   # CMS HCRIS source link

    def test_csv_export_shape(self):
        from rcm_mc.ui.cim_crosscheck_page import render_cim_crosscheck
        out = render_cim_crosscheck({
            "state": ["TX"], "format": ["csv"],
            "c_provider_count": ["600"]})
        lines = out.splitlines()
        self.assertTrue(lines[0].startswith("claim,label,"))
        self.assertEqual(len(lines), 2)

    def test_hostile_qs_no_crash_and_escaped(self):
        from rcm_mc.ui.cim_crosscheck_page import render_cim_crosscheck
        h = render_cim_crosscheck({
            "state": ["<script>alert(1)</script>"],
            "ccn": ['"><script>alert(2)</script>'],
            "c_provider_count": ["not-a-number"]})
        self.assertIn("CIM Cross-Check", h)            # renders, no crash
        # hostile state fails the whitelist; hostile ccn must be escaped —
        # the raw payloads never appear executable in the output.
        self.assertNotIn("<script>alert(1)", h)
        self.assertNotIn("<script>alert(2)", h)


if __name__ == "__main__":
    unittest.main()


class NonFiniteInputTests(unittest.TestCase):
    """float() accepts 'nan'/'inf'/'1e309'; these 500'd the page (int(inf)
    in the form echo) and would poison variance math. A non-finite claim is
    no claim — page renders, value dropped."""

    def test_nonfinite_params_render_without_500(self):
        from rcm_mc.ui.cim_crosscheck_page import render_cim_crosscheck
        for v in ("nan", "NaN", "Infinity", "1e309", "-inf"):
            h = render_cim_crosscheck({
                "state": ["TX"], "min_beds": [v], "max_beds": [v],
                "c_market_size_dollars": [v], "ccn": [v]})
            self.assertIn("CIM Cross-Check", h)   # page rendered

    def test_nonfinite_claim_is_skipped_not_flagged(self):
        from rcm_mc.ui.cim_crosscheck_page import _claims_from_qs
        claims = _claims_from_qs({"c_market_size_dollars": ["inf"],
                                  "c_provider_count": ["400"]})
        self.assertNotIn("market_size_dollars", claims)
        self.assertEqual(claims["provider_count"], 400.0)


class ClaimPercentileTests(unittest.TestCase):
    """P4b — where the CLAIM sits in the in-scope distribution. Aggregates
    and tiny scopes (<8) get None, never a fabricated rank; the percentile
    population is the SAME plausible-band one the estimator describes."""

    def _scope(self):
        import pandas as pd
        rows = []
        # 10 facilities, margins 1%..10% (plausible), medicare 10%..55%
        for i in range(10):
            rows.append({"ccn": f"45{i:04d}", "state": "TX",
                         "name": f"H{i}", "beds": 100 + i,
                         "net_patient_revenue": 1e8 * (i + 1),
                         "operating_expenses": 1e8 * (i + 1) * (1 - (i + 1) / 100),
                         "operating_margin": (i + 1) / 100,
                         "medicare_day_pct": 0.10 + i * 0.05,
                         "total_patient_days": 1e4})
        return pd.DataFrame(rows)

    def test_median_claim_ranks_p50(self):
        from rcm_mc.diligence.cim_crosscheck import run_crosscheck
        r = run_crosscheck(self._scope(), state="TX",
                           claims={"median_operating_margin_pct": 5.5})
        row = r.rows[0]
        self.assertEqual(row.claim_percentile, 50)   # 5 below, 0 ties, n=10
        self.assertEqual(row.percentile_n, 10)

    def test_tail_claim_ranks_high(self):
        from rcm_mc.diligence.cim_crosscheck import run_crosscheck
        r = run_crosscheck(self._scope(), state="TX",
                           claims={"median_operating_margin_pct": 50.0})
        self.assertGreaterEqual(r.rows[0].claim_percentile, 90)

    def test_aggregate_claim_has_no_percentile(self):
        from rcm_mc.diligence.cim_crosscheck import run_crosscheck
        r = run_crosscheck(self._scope(), state="TX",
                           claims={"provider_count": 10})
        self.assertIsNone(r.rows[0].claim_percentile)

    def test_tiny_scope_gets_none(self):
        from rcm_mc.diligence.cim_crosscheck import run_crosscheck
        small = self._scope().head(5)   # n=5 < 8 floor
        r = run_crosscheck(small, state="TX",
                           claims={"median_operating_margin_pct": 3.0})
        self.assertIsNone(r.rows[0].claim_percentile)

    def test_chip_renders_tail_amber_and_aggregate_none(self):
        from rcm_mc.ui.cim_crosscheck_page import _pctile_chip

        class _R:
            claim_percentile = 97
            percentile_n = 457
        c = _pctile_chip(_R())
        self.assertIn("p97", c)
        self.assertIn("tail claim", c)
        self.assertIn("b8732a", c)         # amber

        class _Agg:
            claim_percentile = None
            percentile_n = 0
        self.assertEqual(_pctile_chip(_Agg()), "")


class MemoPercentileTests(unittest.TestCase):
    """The variance memo (the consultant's deliverable) carries the claim
    percentile, and flags a tail claim (≥p90/≤p10) for scrutiny even when
    the variance flag is green."""

    def _scope(self):
        import pandas as pd
        rows = []
        for i in range(12):
            rows.append({"ccn": f"45{i:04d}", "state": "TX", "name": f"H{i}",
                         "beds": 100 + i, "net_patient_revenue": 1e8 * (i + 1),
                         "operating_expenses": 1e8 * (i + 1) * 0.97,
                         "operating_margin": (i + 1) / 100,
                         "total_patient_days": 1e4})
        return pd.DataFrame(rows)

    def test_memo_includes_percentile_and_tail_flag(self):
        from rcm_mc.diligence.cim_crosscheck import run_crosscheck, variance_memo
        # claim at the very top of the margin distribution → tail
        res = run_crosscheck(self._scope(), state="TX",
                             claims={"median_operating_margin_pct": 50.0})
        memo = variance_memo(res)
        self.assertIn("Claim percentile:", memo)
        self.assertIn("tail — scrutinize", memo)

    def test_aggregate_claim_has_no_percentile_line(self):
        from rcm_mc.diligence.cim_crosscheck import run_crosscheck, variance_memo
        res = run_crosscheck(self._scope(), state="TX",
                             claims={"provider_count": 12})
        # aggregate claim → no per-facility percentile
        memo = variance_memo(res)
        self.assertNotIn("Claim percentile:", memo)


class MarketBackdropTests(unittest.TestCase):
    """The CIM results carry a state payer-demand backdrop (Census/ACS) so
    claims are read against real demographics; absent when no ACS row."""

    def test_backdrop_renders_on_results(self):
        from rcm_mc.ui.cim_crosscheck_page import render_cim_crosscheck
        h = render_cim_crosscheck({"state": ["TX"], "c_provider_count": ["400"]})
        self.assertIn("Market demand backdrop", h)
        self.assertIn("uninsured", h)
        self.assertIn("Census/ACS", h)

    def test_no_backdrop_without_results(self):
        from rcm_mc.ui.cim_crosscheck_page import render_cim_crosscheck
        self.assertNotIn("Market demand backdrop", render_cim_crosscheck({}))

    def test_backdrop_helper_empty_for_unknown_state(self):
        from rcm_mc.ui.cim_crosscheck_page import _market_backdrop
        self.assertEqual(_market_backdrop("ZZ"), "")
