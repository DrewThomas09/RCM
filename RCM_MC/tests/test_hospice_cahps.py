"""Hospice family-caregiver experience (CAHPS Hospice Survey) enrichment.

Adds the real CMS CAHPS Hospice Survey to the Hospice vertical — the
family-voice dimension it lacked — keyed by CCN, merged into the quality dict
so it flows through the screener, cross-sector benchmark, and X-Ray. Real
vendored data with provenance and labels taken from the file's measure names;
hospices without a survey carry None (never fabricated).
"""
from __future__ import annotations

import pathlib
import unittest

from rcm_mc.data.hospice import (
    load_hospice_cahps,
    load_hospice_providers,
    load_hospice_quality,
)

_CSV = (pathlib.Path(__file__).resolve().parents[1]
        / "rcm_mc" / "data" / "hospice_cahps.csv")
_KEYS = ("cahps_summary_star", "cahps_recommend_pct", "cahps_rating_9_10_pct",
         "cahps_communication_pct", "cahps_symptoms_pct", "cahps_respect_pct",
         "cahps_timely_pct", "cahps_emotional_pct")


class HospiceCahpsTests(unittest.TestCase):
    def test_vendored_with_provenance(self):
        self.assertTrue(_CSV.is_file())
        head = _CSV.read_text(encoding="utf-8").splitlines()[0]
        self.assertIn("ccn", head)
        self.assertIn("source", head)
        self.assertIn("cahps_recommend_pct", head)

    def test_loader_real_subset(self):
        c = load_hospice_cahps()
        self.assertGreater(len(c), 2000)
        self.assertLess(len(c), len(load_hospice_providers()))
        self.assertEqual(set(_KEYS), set(c[next(iter(c))]))

    def test_merged_into_quality(self):
        q = load_hospice_quality()
        row = next(iter(q.values()))
        for k in _KEYS:
            self.assertIn(k, row)
        self.assertEqual(len(row), 14)          # 6 HIS + 8 CAHPS

    def test_values_real_or_none(self):
        any_star = False
        for row in load_hospice_quality().values():
            s = row.get("cahps_summary_star")
            if s is not None:
                any_star = True
                self.assertTrue(1.0 <= s <= 5.0)
            r = row.get("cahps_recommend_pct")
            if r is not None:
                self.assertTrue(0.0 <= r <= 100.0)
        self.assertTrue(any_star)

    def test_xray_surfaces_family_survey(self):
        from rcm_mc.data.provider_xray_benchmark import metric_benchmarks
        q = load_hospice_quality()
        ccn = next(c for c, r in q.items()
                   if r.get("cahps_summary_star") is not None)
        labels = [b.label for b in metric_benchmarks("hospice", ccn)]
        self.assertIn("Family-survey summary star", labels)
        self.assertIn("Would definitely recommend", labels)


if __name__ == "__main__":
    unittest.main()
