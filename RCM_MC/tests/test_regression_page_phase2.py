"""Tests for the Phase-2 regression page UI extensions.

Pins the partner-facing contracts the review called out:

  - Universe selector pill row + active highlight
  - "Fit ln(target)" toggle (renamed from "Predict log(target)"
    after Phase-2 review — softer language for a diagnostic surface)
  - "Segmented regression" toggle wires through to
    finance.regression.run_segmented_regression
  - Baseline row in the segmented table is labeled with the
    currently-selected universe (not implicitly "all hospitals")
  - Outlier table makes explicit, in log mode, that residual σ
    ranking comes from log space while Actual/Predicted are
    back-transformed to raw target units
  - Log mode handles zero / negative / all-NaN target rows
    gracefully (drops + falls back to empty state)
"""
import unittest

import numpy as np
import pandas as pd

from rcm_mc.ui.regression_page import _run_ols, render_regression_page


def _synthetic_hcris(n: int = 60) -> pd.DataFrame:
    """Minimal HCRIS-shaped frame so the page can render in tests
    without hitting the real cache."""
    rng = np.random.default_rng(42)
    return pd.DataFrame({
        "ccn": [f"{i:06d}" for i in range(n)],
        "name": [f"Test Hospital {i}" for i in range(n)],
        "state": ["MA"] * n,
        "beds": rng.integers(20, 500, n).astype(float),
        "bed_days_available": rng.integers(7000, 180000, n).astype(float),
        "total_patient_days": rng.integers(5000, 150000, n).astype(float),
        "medicare_days": rng.integers(1000, 60000, n).astype(float),
        "medicaid_days": rng.integers(500, 30000, n).astype(float),
        "medicare_day_pct": rng.uniform(20, 70, n),
        "medicaid_day_pct": rng.uniform(5, 35, n),
        "net_patient_revenue": rng.uniform(1e7, 1e9, n),
        "operating_expenses": rng.uniform(1e7, 9e8, n),
        "gross_patient_revenue": rng.uniform(2e7, 2e9, n),
        "contractual_allowances": rng.uniform(1e7, 9e8, n),
        "net_income": rng.uniform(-1e7, 1e8, n),
    })


class UniverseSelectorTests(unittest.TestCase):
    def setUp(self):
        self.df = _synthetic_hcris(80)

    def test_baseline_render_includes_universe_pills(self):
        html = render_regression_page(hcris_df=self.df)
        self.assertIn("rg-pill", html)
        self.assertIn("rg-pill-active", html)
        # "All hospitals" should be the active default
        self.assertIn('class="rg-pill rg-pill-active">All hospitals</a>',
                      html)

    def test_universe_pills_preserve_log_and_segmented_in_href(self):
        html = render_regression_page(
            hcris_df=self.df, log_target=True, segmented=True,
        )
        # Pills should carry log=1 and segmented=1 in their links so
        # switching universe doesn't drop the partner's toggles.
        self.assertIn("log=1", html)
        self.assertIn("segmented=1", html)


class LogModeWordingTests(unittest.TestCase):
    """Review point: 'Predict log(target)' was too production-sounding
    for a diagnostic-only surface. Renamed to 'Fit ln(target)'.
    """

    def test_checkbox_label_is_fit_not_predict(self):
        html = render_regression_page(hcris_df=_synthetic_hcris(60))
        self.assertIn("Fit ln(target)", html)
        # The old wording must NOT appear (avoids partner reading the
        # page as a predictive forecast)
        self.assertNotIn("Predict log(target)", html)


class DiagnosticBannerTests(unittest.TestCase):
    def test_diagnostic_banner_renders(self):
        html = render_regression_page(hcris_df=_synthetic_hcris(60))
        self.assertIn("rg-diagnostic-banner", html)
        self.assertIn("in-sample", html.lower())
        self.assertIn("not how it will predict an unseen", html)


class SegmentedPanelLabelingTests(unittest.TestCase):
    """Review point: baseline row must be labeled with the currently
    selected universe, not implicitly as 'all hospitals'.
    """

    def setUp(self):
        self.df = _synthetic_hcris(120)

    def test_baseline_row_uses_universe_label_when_all(self):
        html = render_regression_page(
            hcris_df=self.df, segmented=True, universe="all",
        )
        self.assertIn("baseline (pooled · all hospitals)", html)

    def test_baseline_row_uses_universe_label_when_filtered(self):
        # Re-tag the synthetic frame so it has at least one segment
        # the universe filter can pick up. We pick names that match
        # the curated academic list so derive_taxonomy assigns them
        # the Academic segment.
        df = self.df.copy()
        df.loc[:30, "name"] = "STANFORD HOSPITAL " + df.loc[:30, "ccn"]
        html = render_regression_page(
            hcris_df=df, segmented=True,
            universe="academic_teaching",
        )
        # The baseline row should reflect the current filter, not "all"
        self.assertIn("baseline (pooled · universe = academic_teaching)", html)


class OutlierLogSpaceNoteTests(unittest.TestCase):
    """Review point: when log mode is on, the outlier table must make
    clear that the σ ranking comes from log space while Actual /
    Predicted are back-transformed.
    """

    def test_log_mode_adds_explanation_in_outlier_panel(self):
        html = render_regression_page(
            hcris_df=_synthetic_hcris(80), log_target=True,
        )
        self.assertIn("Log mode:", html)
        self.assertIn("computed in <em>log space</em>", html)
        self.assertIn("back-transformed", html)

    def test_no_log_mode_note_when_log_off(self):
        html = render_regression_page(hcris_df=_synthetic_hcris(80))
        self.assertNotIn("computed in <em>log space</em>", html)


class LogModeEdgeCases(unittest.TestCase):
    """Review point: log mode must handle zero / negative / missing
    target rows gracefully — drop them, fall back to empty state if
    nothing is left.
    """

    def test_all_zero_target_returns_none(self):
        df = pd.DataFrame({
            "target": [0.0] * 50,
            "x1": list(range(50)),
            "x2": list(range(50)),
        })
        self.assertIsNone(
            _run_ols(df, "target", ["x1", "x2"], log_target=True)
        )

    def test_mixed_positive_zero_negative_drops_non_positive(self):
        df = pd.DataFrame({
            "target": [-5.0, 0.0] + list(range(1, 100)),
            "x1": list(range(101)),
            "x2": list(range(101)),
        })
        res = _run_ols(df, "target", ["x1", "x2"], log_target=True)
        self.assertIsNotNone(res)
        self.assertEqual(res["n"], 99)

    def test_all_nan_target_returns_none(self):
        df = pd.DataFrame({
            "target": [float("nan")] * 50,
            "x1": list(range(50)),
        })
        self.assertIsNone(
            _run_ols(df, "target", ["x1"], log_target=True)
        )

    def test_page_renders_empty_state_when_log_yields_no_rows(self):
        df = pd.DataFrame({
            "name": [f"H{i}" for i in range(50)],
            "ccn": [f"{i:06d}" for i in range(50)],
            "state": ["MA"] * 50,
            "beds": list(range(50)),
            "net_patient_revenue": [0.0] * 50,  # all zero — log drops everything
            "medicare_day_pct": [40.0] * 50,
            "medicaid_day_pct": [10.0] * 50,
            "total_patient_days": [100.0] * 50,
            "bed_days_available": [365.0] * 50,
        })
        html = render_regression_page(hcris_df=df, log_target=True)
        # Must NOT 500. Either "Insufficient data" or "No data" is
        # acceptable as the empty-state copy.
        self.assertTrue(
            "Insufficient data" in html or "No data" in html,
            "expected graceful empty-state copy",
        )


class SegmentChipInOutliersTests(unittest.TestCase):
    def test_outlier_table_renders_segment_chip(self):
        html = render_regression_page(hcris_df=_synthetic_hcris(80))
        self.assertIn("rg-segment-chip", html)


if __name__ == "__main__":
    unittest.main()
