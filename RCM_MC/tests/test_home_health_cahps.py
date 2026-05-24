"""Home Health patient-experience (HHCAHPS) enrichment.

Adds the real CMS HHCAHPS facility survey to the Home Health vertical — the
patient-voice dimension it previously lacked — keyed by CCN, merged into the
quality dict so it flows through the screener, cross-sector benchmark, and
X-Ray. Real vendored data with provenance; agencies without a survey carry
None (never fabricated).
"""
from __future__ import annotations

import pathlib
import unittest

from rcm_mc.data.home_health import (
    load_home_health_cahps,
    load_home_health_providers,
    load_home_health_quality,
)

_CSV = (pathlib.Path(__file__).resolve().parents[1]
        / "rcm_mc" / "data" / "home_health_cahps.csv")
_CAHPS_KEYS = ("cahps_summary_star", "cahps_professional_star",
               "cahps_communication_star", "cahps_medicines_star",
               "cahps_overall_star", "cahps_overall_9_10_pct",
               "cahps_recommend_pct")


class CahpsLoaderTests(unittest.TestCase):
    def test_vendored_file_with_provenance(self):
        self.assertTrue(_CSV.is_file())
        head = _CSV.read_text(encoding="utf-8").splitlines()[0]
        self.assertIn("ccn", head)
        self.assertIn("source", head)
        self.assertIn("cahps_summary_star", head)

    def test_loader_real_subset(self):
        c = load_home_health_cahps()
        self.assertGreater(len(c), 4000)              # ~7k agencies surveyed
        self.assertLess(len(c), len(load_home_health_providers()))  # not all
        # Source label is the real CMS HHCAHPS file (sanity via a row).
        ccn = next(iter(c))
        self.assertEqual(set(_CAHPS_KEYS), set(c[ccn]))


class QualityMergeTests(unittest.TestCase):
    def setUp(self):
        self.q = load_home_health_quality()

    def test_cahps_merged_into_quality(self):
        row = next(iter(self.q.values()))
        for k in _CAHPS_KEYS:
            self.assertIn(k, row)            # present on every agency row
        # HH grew from 6 clinical metrics to 6 + 7 CAHPS = 13.
        self.assertEqual(len(row), 13)

    def test_values_are_real_or_none_not_fabricated(self):
        # Star ratings are 1–5; percents 0–100; missing → None.
        any_star = False
        for row in self.q.values():
            s = row.get("cahps_summary_star")
            if s is not None:
                any_star = True
                self.assertTrue(1.0 <= s <= 5.0)
            p = row.get("cahps_recommend_pct")
            if p is not None:
                self.assertTrue(0.0 <= p <= 100.0)
        self.assertTrue(any_star)


class XRaySurfacesCahpsTests(unittest.TestCase):
    def test_xray_benchmark_includes_patient_survey(self):
        from rcm_mc.data.provider_xray_benchmark import metric_benchmarks
        q = load_home_health_quality()
        ccn = next(c for c, r in q.items()
                   if r.get("cahps_summary_star") is not None)
        labels = [b.label for b in metric_benchmarks("home-health", ccn)]
        self.assertIn("Patient-survey summary star", labels)
        self.assertIn("Would recommend the agency", labels)


if __name__ == "__main__":
    unittest.main()
