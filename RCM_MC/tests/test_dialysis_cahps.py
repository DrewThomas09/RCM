"""Dialysis patient-experience (ICH CAHPS) enrichment.

Adds the real CMS ICH-CAHPS in-center-hemodialysis patient survey to the
Dialysis vertical, keyed by CCN, merged into the quality dict so it flows
through screener / cross-sector benchmark / X-Ray. Real vendored data with
provenance + labels from the file; facilities without a survey carry None.
"""
from __future__ import annotations

import pathlib
import unittest

from rcm_mc.data.dialysis import (
    load_dialysis_cahps,
    load_dialysis_providers,
    load_dialysis_quality,
)

_CSV = (pathlib.Path(__file__).resolve().parents[1]
        / "rcm_mc" / "data" / "dialysis_cahps.csv")
_KEYS = ("cahps_facility_star", "cahps_nephrologist_comm_star",
         "cahps_center_care_star", "cahps_information_star",
         "cahps_nephrologist_star", "cahps_staff_star")


class DialysisCahpsTests(unittest.TestCase):
    def test_vendored_with_provenance(self):
        self.assertTrue(_CSV.is_file())
        head = _CSV.read_text(encoding="utf-8").splitlines()[0]
        self.assertIn("ccn", head)
        self.assertIn("source", head)
        self.assertIn("cahps_facility_star", head)

    def test_loader_real_subset(self):
        c = load_dialysis_cahps()
        self.assertGreater(len(c), 1500)
        self.assertLess(len(c), len(load_dialysis_providers()))
        self.assertEqual(set(_KEYS), set(c[next(iter(c))]))

    def test_merged_into_quality(self):
        row = next(iter(load_dialysis_quality().values()))
        for k in _KEYS:
            self.assertIn(k, row)
        self.assertEqual(len(row), 11)          # 5 clinical + 6 CAHPS

    def test_stars_real_or_none(self):
        any_star = False
        for row in load_dialysis_quality().values():
            s = row.get("cahps_facility_star")
            if s is not None:
                any_star = True
                self.assertTrue(1.0 <= s <= 5.0)
        self.assertTrue(any_star)

    def test_xray_surfaces_patient_survey(self):
        from rcm_mc.data.provider_xray_benchmark import metric_benchmarks
        q = load_dialysis_quality()
        ccn = next(c for c, r in q.items()
                   if r.get("cahps_facility_star") is not None)
        labels = [b.label for b in metric_benchmarks("dialysis", ccn)]
        self.assertIn("Patient-survey facility star", labels)


if __name__ == "__main__":
    unittest.main()
