"""Regression: gross-derived revenue ratios are None when the filing is
inconsistent — never an impossible >100% net-to-gross or negative allowance.

net = gross − contractual allowances, so net-to-gross ∈ (0, 1] and the
allowance rate ∈ [0, 1]. When a filing reports gross < net (gross understated),
both come out impossible. The X-Ray used to show "230% net-to-gross" / a
negative allowance rate as real KPIs. Now those land None → "—", and the peer
benchmark carries the None target through without a bogus verdict. See
metrics._bounded_ratio and xray.compute_benchmarks.
"""
from __future__ import annotations

import unittest

from rcm_mc.diligence.hcris_xray import load_all_metrics
from rcm_mc.diligence.hcris_xray.metrics import _bounded_ratio, compute_metrics


class BoundedRatioTests(unittest.TestCase):
    def test_valid_in_band(self):
        self.assertAlmostEqual(_bounded_ratio(90.0, 100.0), 0.90)

    def test_missing_denominator_is_none(self):
        self.assertIsNone(_bounded_ratio(50.0, 0))
        self.assertIsNone(_bounded_ratio(50.0, None))  # type: ignore[arg-type]

    def test_impossible_high_is_none(self):
        # net > gross → >100% → artifact
        self.assertIsNone(_bounded_ratio(120.0, 100.0))

    def test_negative_is_none(self):
        self.assertIsNone(_bounded_ratio(-5.0, 100.0))

    def test_rounding_tolerance_allows_just_over_one(self):
        # 100.4% is a rounding-level overage, not an artifact — kept.
        self.assertIsNotNone(_bounded_ratio(100.4, 100.0))


class ComputeMetricsConsistencyTests(unittest.TestCase):
    def test_gross_below_net_yields_none(self):
        m = compute_metrics({
            "ccn": "999999", "net_patient_revenue": 12e6,
            "gross_patient_revenue": 5e6,  # gross < net → impossible
            "contractual_allowances": 6e6,  # > gross → impossible rate
            "operating_expenses": 11e6,
            "beds": 25,
        })
        self.assertIsNone(m.net_to_gross_ratio)
        self.assertIsNone(m.contractual_allowance_rate)

    def test_consistent_filing_yields_real_ratio(self):
        m = compute_metrics({
            "ccn": "999998", "net_patient_revenue": 8e6,
            "gross_patient_revenue": 20e6, "contractual_allowances": 12e6,
            "operating_expenses": 7e6, "beds": 50,
        })
        self.assertAlmostEqual(m.net_to_gross_ratio, 0.40, places=3)
        self.assertAlmostEqual(m.contractual_allowance_rate, 0.60, places=3)


class LiveDataHasNoImpossibleRatiosTests(unittest.TestCase):
    def test_no_impossible_net_to_gross_or_allowance(self):
        ms = load_all_metrics()
        bad_n2g = [m for m in ms if (m.net_to_gross_ratio or 0) > 1.05]
        bad_alw = [m for m in ms if (m.contractual_allowance_rate or 0) < -0.01]
        self.assertEqual(bad_n2g, [], "net-to-gross >105% leaked through")
        self.assertEqual(bad_alw, [], "negative allowance rate leaked through")


class BenchmarkHandlesNoneTargetTests(unittest.TestCase):
    def test_none_target_gets_na_verdict_no_crash(self):
        from rcm_mc.diligence.hcris_xray.xray import compute_benchmarks
        ms = load_all_metrics()
        target = next(m for m in ms if m.net_to_gross_ratio is None)
        # A few same-state peers as a stand-in cohort.
        from rcm_mc.diligence.hcris_xray.xray import PeerMatch
        peers = [PeerMatch(hospital=p, distance=0.1, same_state=True,
                           same_region=True, same_size_cohort=True)
                 for p in ms[:40]]
        bms = compute_benchmarks(target, peers)
        n2g = [b for b in bms if b.spec.attr == "net_to_gross_ratio"]
        if n2g:  # only asserts if peers produced a benchmark row
            self.assertIsNone(n2g[0].target_value)
            self.assertTrue(n2g[0].verdict.startswith("n/a"))


if __name__ == "__main__":
    unittest.main()
