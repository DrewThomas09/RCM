"""A feature that doesn't vary within the selected subset must drop out of the
regression entirely — not sit on the charts as a meaningless zero bar. This is
what keeps a universe filter (e.g. acquisition_targets) clean: "things left at
0 because it doesn't measure certain things" no longer appear.
"""
from __future__ import annotations

import unittest

import numpy as np
import pandas as pd

from rcm_mc.ui.regression_page import _run_ols


class ConstantFeatureDropped(unittest.TestCase):
    def _df(self, n=60):
        rng = np.random.default_rng(7)
        x = rng.normal(100, 20, n)
        return pd.DataFrame({
            "beds": x,
            "operating_expenses": x * 1000 + rng.normal(0, 500, n),
            "flatline": np.full(n, 42.0),          # zero variance — unmeasurable
            "net_patient_revenue": x * 900 + rng.normal(0, 1000, n),
        })

    def test_constant_feature_absent_from_all_chart_inputs(self):
        res = _run_ols(self._df(), "net_patient_revenue",
                       ["beds", "operating_expenses", "flatline"])
        self.assertIsNotNone(res)
        coef_feats = {c["feature"] for c in res.get("coefficients", [])}
        corr_feats = {c["feature"] for c in res.get("target_correlations", [])}
        vif_feats = {v["feature"] for v in res.get("vifs", [])}
        for label, feats in (("coefficients", coef_feats),
                             ("correlations", corr_feats), ("vifs", vif_feats)):
            self.assertNotIn("flatline", feats,
                             f"constant feature leaked into {label}")
        # the real varying features are still present
        self.assertIn("beds", coef_feats)

    def test_varying_features_are_kept(self):
        # A feature that genuinely varies (even if weakly related) is NOT
        # dropped — only constant ones are. (Don't hide real findings.)
        res = _run_ols(self._df(), "net_patient_revenue",
                       ["beds", "operating_expenses"])
        self.assertIsNotNone(res)
        self.assertEqual({c["feature"] for c in res["coefficients"]},
                         {"beds", "operating_expenses"})


if __name__ == "__main__":
    unittest.main()
