"""Regression: screeners label each value's basis — Actual vs Predicted.

A partner must never mistake a model estimate for a real filing. The
target screener shows only measured CMS data (HCRIS margin, CMS star
ratings) and marks its metric column ACTUAL; the predictive screener
mixes measured columns (Beds/Revenue/Margin) with ML point estimates
(Est. Denial/Est. Uplift) and badges each accordingly. See
_chartis_kit.ck_basis_badge.
"""
import unittest

from rcm_mc.ui._chartis_kit import ck_basis_badge


class BasisBadgeTests(unittest.TestCase):
    def test_actual_badge(self):
        b = ck_basis_badge("actual")
        self.assertIn("ACTUAL", b)
        self.assertIn("not a model estimate", b)

    def test_predicted_badge(self):
        b = ck_basis_badge("predicted")
        self.assertIn("PREDICTED", b)
        self.assertIn("not a filed figure", b)

    def test_unknown_kind_is_empty(self):
        self.assertEqual(ck_basis_badge("x"), "")
        self.assertEqual(ck_basis_badge(""), "")
        self.assertEqual(ck_basis_badge(None), "")


class TargetScreenerBasisTests(unittest.TestCase):
    def test_metric_column_marked_actual_not_predicted(self):
        from rcm_mc.ui.target_screener_page import render_target_screener
        html = render_target_screener({"vertical": ["hospitals"]})
        # The measured-data screen never labels a value PREDICTED, and marks
        # its metric column ACTUAL so it's not confused with the model screen.
        self.assertIn("ACTUAL</span>", html)
        self.assertNotIn("PREDICTED</span>", html)


class PredictiveScreenerBasisTests(unittest.TestCase):
    def test_actual_and_predicted_columns_both_badged(self):
        from rcm_mc.data.hcris import _get_latest_per_ccn
        from rcm_mc.ui.predictive_screener import render_predictive_screener
        html = render_predictive_screener(_get_latest_per_ccn(), "")
        # Beds / Revenue / Margin = ACTUAL (3); Est. Denial / Est. Uplift =
        # PREDICTED (2). The mixed table must distinguish them per-column.
        self.assertEqual(html.count(">ACTUAL</span>"), 3)
        self.assertEqual(html.count(">PREDICTED</span>"), 2)


if __name__ == "__main__":
    unittest.main()
