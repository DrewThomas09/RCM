"""Regression: NaN metrics render as a gap ("—" + red dot), never "nan%".

The HCRIS loader reads Medicaid days from a single Worksheet S-3 column, so
~2,637 hospital-years have NaN medicaid_day_pct (genuinely missing, not 0).
MetricSpec.fmt used to print literal "nan%", and the benchmark counted NaN as
a real value (skewing peer percentiles and missing the gap dot). NaN is now
treated identically to None — a gap. See metrics.MetricSpec.fmt and
xray.compute_benchmarks.
"""
from __future__ import annotations

import math
import unittest

from rcm_mc.diligence.hcris_xray.metrics import METRIC_CATALOG


class MetricFmtNaNTests(unittest.TestCase):
    def setUp(self):
        self.spec = next(s for s in METRIC_CATALOG if s.attr == "medicaid_day_pct")

    def test_nan_renders_dash(self):
        self.assertEqual(self.spec.fmt(float("nan")), "—")

    def test_none_renders_dash(self):
        self.assertEqual(self.spec.fmt(None), "—")

    def test_real_value_renders_normally(self):
        self.assertEqual(self.spec.fmt(0.12), "12.0%")


class XrayNoNanPercentTests(unittest.TestCase):
    def test_nan_medicaid_hospital_shows_gap_not_nan(self):
        from rcm_mc.diligence.hcris_xray import find_hospital
        from rcm_mc.data.hcris import load_hcris
        from rcm_mc.ui.hcris_xray_page import render_hcris_xray_page
        ccn = None
        for c in load_hcris()["ccn"].astype(str).unique().tolist()[:3000]:
            h = find_hospital(c)
            v = getattr(h, "medicaid_day_pct", None) if h else None
            if isinstance(v, float) and math.isnan(v):
                ccn = c
                break
        self.assertIsNotNone(ccn, "expected a NaN-medicaid hospital in HCRIS")
        html = render_hcris_xray_page({"ccn": [ccn]})
        self.assertNotIn("nan%", html.lower())   # no literal nan%
        self.assertIn("ck-gap-dot", html)        # the gap is marked


class BenchmarkNaNExcludedTests(unittest.TestCase):
    def test_nan_excluded_from_peer_percentiles(self):
        from rcm_mc.diligence.hcris_xray.xray import compute_benchmarks, PeerMatch
        from rcm_mc.diligence.hcris_xray import load_all_metrics
        ms = load_all_metrics()
        target = next(m for m in ms
                      if isinstance(m.medicaid_day_pct, float)
                      and math.isnan(m.medicaid_day_pct))
        peers = [PeerMatch(hospital=p, distance=0.1, same_state=True,
                           same_region=True, same_size_cohort=True)
                 for p in ms[:60]]
        bms = compute_benchmarks(target, peers)
        med = [b for b in bms if b.spec.attr == "medicaid_day_pct"]
        if med:
            b = med[0]
            self.assertIsNone(b.target_value)               # NaN target → gap
            self.assertFalse(math.isnan(b.peer_median))     # peers exclude NaN


if __name__ == "__main__":
    unittest.main()
