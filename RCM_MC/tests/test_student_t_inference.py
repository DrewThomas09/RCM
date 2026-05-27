"""Exact Student-t inference for regression coefficients.

The regression page previously took coefficient p-values from a normal-tail
approximation (erfc) and built CIs with a flat 1.96 multiplier. Both ignore
the degrees of freedom, so a tight universe filter (n=15 → df≈12) got
p-values that were too small and CIs that were too narrow — overstated
precision. These tests pin the EXACT Student-t behaviour against textbook
critical values (no scipy available) and confirm it converges to the normal
as df→∞.
"""
from __future__ import annotations

import unittest

import numpy as np
import pandas as pd

from rcm_mc.finance.regression import (
    t_critical_value,
    t_two_tailed_pvalue,
)
from rcm_mc.ui.regression_page import _run_ols


class TwoTailedPValue(unittest.TestCase):
    def test_matches_textbook_critical_t(self):
        # At the textbook two-sided 0.05 critical t, the p-value must be ~0.05.
        for t, df in [(2.228, 10), (2.086, 20), (2.042, 30), (1.984, 100)]:
            p = t_two_tailed_pvalue(t, df)
            self.assertAlmostEqual(p, 0.05, places=3, msg=f"t={t} df={df} p={p}")

    def test_matches_textbook_001_level(self):
        self.assertAlmostEqual(t_two_tailed_pvalue(3.169, 10), 0.01, places=3)

    def test_more_conservative_than_normal_for_small_df(self):
        # For the SAME t, the t-distribution has heavier tails → a LARGER
        # (more conservative, honest) p-value than the normal approximation.
        from math import erfc, sqrt
        t = 2.2
        normal_p = erfc(abs(t) / sqrt(2))
        self.assertGreater(t_two_tailed_pvalue(t, 8), normal_p)

    def test_converges_to_normal_for_large_df(self):
        from math import erfc, sqrt
        t = 2.0
        normal_p = erfc(abs(t) / sqrt(2))
        self.assertAlmostEqual(t_two_tailed_pvalue(t, 5_000_000), normal_p, places=4)

    def test_degenerate_safe(self):
        self.assertEqual(t_two_tailed_pvalue(2.0, 0), 1.0)
        self.assertEqual(t_two_tailed_pvalue(0.0, 10), 1.0)


class CriticalValue(unittest.TestCase):
    def test_matches_t_table(self):
        table = {5: 2.571, 10: 2.228, 20: 2.086, 30: 2.042, 60: 2.000, 120: 1.980}
        for df, want in table.items():
            self.assertAlmostEqual(t_critical_value(df), want, places=2,
                                   msg=f"df={df}")

    def test_exceeds_196_for_small_df_and_converges(self):
        self.assertGreater(t_critical_value(5), 1.96)
        self.assertGreater(t_critical_value(30), 1.96)
        self.assertAlmostEqual(t_critical_value(10_000_000), 1.96, places=3)

    def test_degenerate_safe(self):
        self.assertAlmostEqual(t_critical_value(0), 1.96, places=2)


class RunOLSUsesStudentT(unittest.TestCase):
    def _small_df(self, n=15):
        rng = np.random.default_rng(7)
        x = rng.normal(100, 20, n)
        return pd.DataFrame({
            "beds": x,
            "operating_expenses": x * 1000 + rng.normal(0, 4000, n),
            "net_patient_revenue": x * 900 + rng.normal(0, 8000, n),
        })

    def test_result_exposes_t_inference_fields(self):
        res = _run_ols(self._small_df(), "net_patient_revenue",
                       ["beds", "operating_expenses"])
        self.assertIsNotNone(res)
        self.assertIn("resid_df", res)
        self.assertIn("t_critical", res)
        # small sample → critical t must exceed the normal 1.96
        self.assertGreater(res["t_critical"], 1.96)
        # df = n - p - 1 = 15 - 2 - 1 = 12
        self.assertEqual(res["resid_df"], 12)

    def test_ci_wider_than_normal_at_small_n(self):
        # The half-width of every coefficient CI must equal t_crit * SE,
        # i.e. STRICTLY wider than the old 1.96*SE — the honest correction.
        res = _run_ols(self._small_df(), "net_patient_revenue",
                       ["beds", "operating_expenses"])
        tc = res["t_critical"]
        for c in res["coefficients"]:
            half = (c["ci_high"] - c["ci_low"]) / 2.0
            se = c["std_error"]
            self.assertAlmostEqual(half, tc * se, places=6)
            if se > 0:
                self.assertGreater(half, 1.96 * se)


if __name__ == "__main__":
    unittest.main()
