"""CMS Provider X-Ray — multi-peer-set benchmarks + risk indicators (PR E).

Pins: per-metric percentiles across national / state / locality / ownership
peer sets (bounded, with peer_n, suppressed when n<5); guarded state z-score;
and transparent rule-based risk indicators that are explicitly NOT forecasts
(the disclaimer states so) and only carry enforcement signals where the data
exists (SNF).
"""
from __future__ import annotations

import unittest

from rcm_mc.data.cross_sector import SECTOR_BY_ID
from rcm_mc.data.provider_xray_benchmark import (
    ELEVATED, INSUFFICIENT, LOW, MODERATE,
    metric_benchmarks,
    provider_benchmark_bundle,
    risk_indicators,
)
from rcm_mc.data.snf import load_snf_providers

_LEVELS = {ELEVATED, MODERATE, LOW, INSUFFICIENT}


def _tx_snf() -> str:
    for c, p in load_snf_providers().items():
        if p.state == "TX":
            return c
    return next(iter(load_snf_providers()))


class BenchmarkTests(unittest.TestCase):
    def setUp(self):
        self.ccn = _tx_snf()
        self.bm = metric_benchmarks("nursing-homes", self.ccn)

    def test_metrics_have_multiple_peer_sets(self):
        self.assertTrue(self.bm)
        head = self.bm[0]
        peer_sets = {p.peer_set for p in head.percentiles}
        # National + state always; locality/ownership when peers exist.
        self.assertIn("national", peer_sets)
        self.assertIn("state", peer_sets)
        self.assertTrue({"locality", "ownership"} & peer_sets)

    def test_percentiles_bounded_and_counted(self):
        for m in self.bm:
            for p in m.percentiles:
                self.assertGreaterEqual(p.peer_n, 0)
                if p.percentile is not None:
                    self.assertTrue(0 <= p.percentile <= 100)
                    self.assertFalse(p.suppressed)
                else:
                    self.assertTrue(p.suppressed or p.peer_n < 5)

    def test_national_peer_set_is_largest(self):
        head = self.bm[0]
        nat = next(p for p in head.percentiles if p.peer_set == "national")
        st = next(p for p in head.percentiles if p.peer_set == "state")
        self.assertGreaterEqual(nat.peer_n, st.peer_n)

    def test_unknown_sector_or_ccn_empty(self):
        self.assertEqual(metric_benchmarks("dental", "x"), [])
        self.assertEqual(metric_benchmarks("nursing-homes", "000000"), [])


class RiskIndicatorTests(unittest.TestCase):
    def setUp(self):
        self.ccn = _tx_snf()
        self.bundle = provider_benchmark_bundle("nursing-homes", self.ccn)

    def test_levels_valid_and_named(self):
        self.assertTrue(self.bundle.risk_indicators)
        for r in self.bundle.risk_indicators:
            self.assertIn(r.level, _LEVELS)
            self.assertTrue(r.name and r.basis)
        names = {r.name for r in self.bundle.risk_indicators}
        self.assertIn("Quality position", names)
        self.assertIn("Evidence confidence", names)

    def test_disclaimer_says_not_a_forecast(self):
        d = self.bundle.disclaimer.lower()
        self.assertIn("not trained predictive models", d)
        self.assertIn("forecast", d)
        self.assertIn("single-snapshot", d)

    def test_enforcement_indicator_only_for_snf(self):
        snf = {r.name for r in self.bundle.risk_indicators}
        self.assertIn("Enforcement / staffing", snf)
        for vid in ("home-health", "hospice", "dialysis", "inpatient-rehab",
                    "long-term-care-hospital"):
            ccn = next(iter(SECTOR_BY_ID[vid].providers_loader()))
            names = {r.name for r in
                     provider_benchmark_bundle(vid, ccn).risk_indicators}
            self.assertNotIn("Enforcement / staffing", names)

    def test_quality_indicator_tracks_national_percentile(self):
        head = metric_benchmarks("nursing-homes", self.ccn)[0]
        nat = next(p for p in head.percentiles if p.peer_set == "national")
        q = next(r for r in self.bundle.risk_indicators
                 if r.name == "Quality position")
        if nat.percentile is None:
            self.assertEqual(q.level, INSUFFICIENT)
        elif nat.percentile < 25:
            self.assertEqual(q.level, ELEVATED)
        elif nat.percentile < 50:
            self.assertEqual(q.level, MODERATE)
        else:
            self.assertEqual(q.level, LOW)


if __name__ == "__main__":
    unittest.main()
