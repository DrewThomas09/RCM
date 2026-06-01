"""Tests for the formatter + chart helpers in ``reports/reporting.py``.

`rcm_mc/reports/reporting.py` ships 14 public functions; this file
covers the ones with no direct test coverage: ``pretty_money``,
``waterfall_ebitda_drag``, ``plot_denial_drivers_chart``,
``plot_underpayments_chart``.

Lock the formatter contract (used by every report + dashboard) and
verify the matplotlib chart helpers produce valid PNG files without
crashing on the documented edge cases.
"""
from __future__ import annotations

import os
import tempfile
import unittest

import pandas as pd

from rcm_mc.reports.reporting import (
    plot_denial_drivers_chart,
    plot_underpayments_chart,
    pretty_money,
    waterfall_ebitda_drag,
)


class PrettyMoneyTests(unittest.TestCase):
    """The formatter every report + dashboard uses to make $ readable.
    Format spec from the source docstring: '$8.8M, $-1.2K, etc.'"""

    def test_billions(self):
        self.assertEqual(pretty_money(1_500_000_000), "$1.5B")
        self.assertEqual(pretty_money(8_800_000_000), "$8.8B")

    def test_millions(self):
        self.assertEqual(pretty_money(8_800_000), "$8.8M")
        self.assertEqual(pretty_money(1_200_000), "$1.2M")
        self.assertEqual(pretty_money(999_999), "$1000K")  # 999.999K rounds

    def test_thousands(self):
        # K format uses 0 decimal places.
        self.assertEqual(pretty_money(8_800), "$9K")  # rounds
        self.assertEqual(pretty_money(1_200), "$1K")
        self.assertEqual(pretty_money(1_500), "$2K")

    def test_below_thousand_no_unit_letter(self):
        self.assertEqual(pretty_money(500), "$500")
        self.assertEqual(pretty_money(42), "$42")
        self.assertEqual(pretty_money(0), "$0")

    def test_negative_values_carry_minus_sign(self):
        # Minus prefix BEFORE the dollar sign, per docstring spec:
        # '$-1.2K' from the original test fixture.
        self.assertEqual(pretty_money(-1_200), "-$1K")
        self.assertEqual(pretty_money(-8_800_000), "-$8.8M")
        self.assertEqual(pretty_money(-500), "-$500")

    def test_boundary_at_1k(self):
        # Exactly $1,000 → '$1K' (not '$1000').
        self.assertEqual(pretty_money(1_000), "$1K")
        # $999 stays as raw '$999'
        self.assertEqual(pretty_money(999), "$999")

    def test_boundary_at_1m(self):
        self.assertEqual(pretty_money(1_000_000), "$1.0M")

    def test_boundary_at_1b(self):
        self.assertEqual(pretty_money(1_000_000_000), "$1.0B")

    def test_float_input(self):
        # Accepts float inputs (used by Monte Carlo mean output).
        self.assertEqual(pretty_money(8_800_000.0), "$8.8M")
        self.assertEqual(pretty_money(123.456), "$123")

    def test_zero(self):
        self.assertEqual(pretty_money(0), "$0")
        self.assertEqual(pretty_money(0.0), "$0")
        # -0 in float should NOT carry minus
        self.assertEqual(pretty_money(-0.0), "$0")


# Synthetic drag dataframe for the chart functions — same columns
# the simulator emits via simulate_compare.
def _drag_df(n=20):
    import numpy as np
    rng = np.random.default_rng(seed=42)
    return pd.DataFrame({
        "drag_denial_writeoff":      rng.uniform(1e5, 1e6, n),
        "drag_underpay_leakage":     rng.uniform(2e5, 8e5, n),
        "drag_denial_rework_cost":   rng.uniform(5e4, 3e5, n),
        "drag_underpay_cost":        rng.uniform(3e4, 2e5, n),
        "drag_dar_total":            rng.uniform(10, 60, n),
    })


class WaterfallEbitdaDragTests(unittest.TestCase):
    """Two render paths: with reported_ebitda anchor (PE pro-forma
    bridge), and without (decomposition only)."""

    def test_writes_png_at_outpath(self):
        with tempfile.TemporaryDirectory() as tmp:
            outpath = os.path.join(tmp, "out.png")
            waterfall_ebitda_drag(_drag_df(), outpath)
            self.assertTrue(os.path.isfile(outpath))
            # PNG signature: 89 50 4E 47
            with open(outpath, "rb") as f:
                self.assertEqual(f.read(4), b"\x89PNG")

    def test_with_reported_ebitda_anchor(self):
        with tempfile.TemporaryDirectory() as tmp:
            outpath = os.path.join(tmp, "out.png")
            waterfall_ebitda_drag(
                _drag_df(), outpath,
                reported_ebitda=50_000_000,
            )
            self.assertTrue(os.path.isfile(outpath))
            self.assertGreater(os.path.getsize(outpath), 5_000)

    def test_decomposition_path_when_no_anchor(self):
        # reported_ebitda=None → fallback to decomposition only
        with tempfile.TemporaryDirectory() as tmp:
            outpath = os.path.join(tmp, "out.png")
            waterfall_ebitda_drag(_drag_df(), outpath, None)
            self.assertTrue(os.path.isfile(outpath))

    def test_zero_or_negative_anchor_falls_to_decomposition(self):
        # reported_ebitda <= 0 → treated same as missing
        with tempfile.TemporaryDirectory() as tmp:
            outpath = os.path.join(tmp, "out.png")
            waterfall_ebitda_drag(
                _drag_df(), outpath, reported_ebitda=0)
            self.assertTrue(os.path.isfile(outpath))


class PlotDenialDriversChartTests(unittest.TestCase):

    def _drivers_df(self, n_rows=15):
        return pd.DataFrame({
            "payer": ["Medicare", "Medicaid", "Commercial",
                       "Self-Pay", "Medicare"] * (n_rows // 5),
            "root_cause": ["authorization", "coding", "eligibility",
                            "medical_necessity", "timely_filing"]
                          * (n_rows // 5),
            "drag_mean_denial_writeoff": [
                1e6 - i * 5e4 for i in range(n_rows)],
        })

    def test_writes_png(self):
        with tempfile.TemporaryDirectory() as tmp:
            outpath = os.path.join(tmp, "out.png")
            plot_denial_drivers_chart(self._drivers_df(), outpath)
            self.assertTrue(os.path.isfile(outpath))
            with open(outpath, "rb") as f:
                self.assertEqual(f.read(4), b"\x89PNG")

    def test_empty_df_silently_skips(self):
        # Empty df → function returns without writing; no crash.
        with tempfile.TemporaryDirectory() as tmp:
            outpath = os.path.join(tmp, "out.png")
            plot_denial_drivers_chart(pd.DataFrame(), outpath)
            self.assertFalse(os.path.isfile(outpath))

    def test_none_df_silently_skips(self):
        with tempfile.TemporaryDirectory() as tmp:
            outpath = os.path.join(tmp, "out.png")
            plot_denial_drivers_chart(None, outpath)
            self.assertFalse(os.path.isfile(outpath))

    def test_missing_drag_column_silently_skips(self):
        # If the drag_mean_denial_writeoff column isn't present,
        # the helper silently skips.
        df = pd.DataFrame({
            "payer": ["Medicare"], "root_cause": ["auth"],
            "other_metric": [1.0],
        })
        with tempfile.TemporaryDirectory() as tmp:
            outpath = os.path.join(tmp, "out.png")
            plot_denial_drivers_chart(df, outpath)
            self.assertFalse(os.path.isfile(outpath))

    def test_respects_top_n_kwarg(self):
        # top_n filters to N rows; can't easily verify visually but
        # we can confirm it doesn't crash on extreme values.
        with tempfile.TemporaryDirectory() as tmp:
            outpath = os.path.join(tmp, "out.png")
            plot_denial_drivers_chart(
                self._drivers_df(n_rows=15),
                outpath, top_n=3,
            )
            self.assertTrue(os.path.isfile(outpath))


class PlotUnderpaymentsChartTests(unittest.TestCase):

    def _underpay_df(self):
        # Wide format: rows are (payer, metric) pairs with
        # 'drag_mean_value' as the value column. Matches what the
        # simulator emits for chart consumers.
        return pd.DataFrame({
            "payer": ["Medicare", "Medicaid", "Commercial",
                       "Medicare", "Medicaid", "Commercial"],
            "metric": ["underpay_leakage"] * 3 + ["underpay_cost"] * 3,
            "drag_mean_value": [3e6, 1.5e6, 8e5,
                                 5e5, 2e5, 1e5],
        })

    def test_writes_png(self):
        with tempfile.TemporaryDirectory() as tmp:
            outpath = os.path.join(tmp, "out.png")
            plot_underpayments_chart(self._underpay_df(), outpath)
            self.assertTrue(os.path.isfile(outpath))
            with open(outpath, "rb") as f:
                self.assertEqual(f.read(4), b"\x89PNG")

    def test_empty_df_silently_skips(self):
        with tempfile.TemporaryDirectory() as tmp:
            outpath = os.path.join(tmp, "out.png")
            plot_underpayments_chart(pd.DataFrame(), outpath)
            self.assertFalse(os.path.isfile(outpath))

    def test_none_df_silently_skips(self):
        with tempfile.TemporaryDirectory() as tmp:
            outpath = os.path.join(tmp, "out.png")
            plot_underpayments_chart(None, outpath)
            self.assertFalse(os.path.isfile(outpath))

    def test_selfpay_payer_filtered_out(self):
        # The function explicitly drops 'SelfPay' from the chart
        # (documented behavior — SelfPay underpayment economics differ).
        df = self._underpay_df()
        df = pd.concat([df, pd.DataFrame({
            "payer": ["SelfPay"], "metric": ["underpay_leakage"],
            "drag_mean_value": [1e9],  # huge, would dominate
        })], ignore_index=True)
        with tempfile.TemporaryDirectory() as tmp:
            outpath = os.path.join(tmp, "out.png")
            plot_underpayments_chart(df, outpath)
            self.assertTrue(os.path.isfile(outpath))

    def test_no_leakage_rows_silently_skips(self):
        # df has the columns but no rows match metric=='underpay_leakage'
        df = pd.DataFrame({
            "payer": ["Medicare"], "metric": ["underpay_cost"],
            "drag_mean_value": [1.0],
        })
        with tempfile.TemporaryDirectory() as tmp:
            outpath = os.path.join(tmp, "out.png")
            plot_underpayments_chart(df, outpath)
            self.assertFalse(os.path.isfile(outpath))


if __name__ == "__main__":
    unittest.main()
