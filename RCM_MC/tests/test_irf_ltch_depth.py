"""IRF + LTCH measure deepening (real CMS Provider Data, verified names).

The two thinnest verticals were pivoted from 3 measures to the fuller set in
their Provider Data files — names verified against the official CMS IRF / LTCH
Data Dictionaries (not guessed). Higher-is-better function/process/vaccination
measures surface in the X-Ray index; lower-is-better readmission/spend/safety/
infection rates stay out of the higher=better index. Every provider keeps a
quality row (blank where unrated — never fabricated).
"""
from __future__ import annotations

import unittest

from rcm_mc.data.irf import load_irf_providers, load_irf_quality
from rcm_mc.data.ltch import load_ltch_providers, load_ltch_quality
from rcm_mc.data.provider_xray_benchmark import metric_benchmarks


class IrfDepthTests(unittest.TestCase):
    def test_irf_metric_count_and_alignment(self):
        P, Q = load_irf_providers(), load_irf_quality()
        self.assertEqual(set(P) - set(Q), set())          # every provider rated-row
        row = next(iter(Q.values()))
        self.assertEqual(len(row), 13)                     # 3 -> 13
        for k in ("dtc_rs_rate", "selfcare_fn_pct", "mobility_fn_pct",
                  "hcp_flu_pct", "within_stay_readmit_rsrr", "pressure_ulcer_rate",
                  "cauti_sir", "cdi_sir"):
            self.assertIn(k, row)

    def test_irf_xray_surfaces_higher_is_better_only(self):
        ccn = next(iter(load_irf_quality()))
        labels = [b.label for b in metric_benchmarks("inpatient-rehab", ccn)]
        self.assertIn("Self-care function at/above expected", labels)
        self.assertIn("Healthcare-personnel flu vaccination", labels)
        # Lower-is-better rates are NOT in the higher=better X-Ray index.
        self.assertNotIn("pressure_ulcer_rate", labels)


class LtchDepthTests(unittest.TestCase):
    def test_ltch_metric_count_and_alignment(self):
        P, Q = load_ltch_providers(), load_ltch_quality()
        self.assertEqual(set(P) - set(Q), set())
        row = next(iter(Q.values()))
        self.assertEqual(len(row), 12)                     # 3 -> 12
        # LTCH-specific ventilator-weaning measure is present.
        self.assertIn("vent_weaning_pct", row)
        for k in ("dtc_rs_rate", "selfcare_fn_pct", "clabsi_sir", "cdi_sir"):
            self.assertIn(k, row)

    def test_ltch_xray_includes_ventilator_weaning(self):
        ccn = next(iter(load_ltch_quality()))
        labels = [b.label for b in metric_benchmarks("long-term-care-hospital", ccn)]
        self.assertIn("Successfully weaned from ventilator", labels)


if __name__ == "__main__":
    unittest.main()
