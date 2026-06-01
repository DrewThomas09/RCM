"""Extended coverage for ``rcm_mc/reports/reporting.py``.

Companion to ``test_reports_reporting_helpers.py``. Locks the contract
of four production functions that had no direct unit-test coverage:

  * ``strategic_priority_matrix``
  * ``actionable_insights``
  * ``assumption_summary``
  * ``plot_ebitda_drag_distribution``

These are PE-board-facing surfaces — the matrix, the bullets, and the
risk/reward chart that appear in every diligence deck. Regressions
here ship straight into the partner brief, so we lock the contracts
(tier labels, insight phrasing, dollar formatting, PNG render) before
they drift.
"""
from __future__ import annotations

import os
import tempfile
import unittest

import numpy as np
import pandas as pd

from rcm_mc.reports.reporting import (
    actionable_insights,
    assumption_summary,
    plot_ebitda_drag_distribution,
    strategic_priority_matrix,
)


# ---------------------------------------------------------------------------
# strategic_priority_matrix
# ---------------------------------------------------------------------------


class StrategicPriorityMatrixTests(unittest.TestCase):
    """Sensitivity → Impact/Ease/Tier table. Board-facing — labels
    are the contract."""

    def _sens(self, *rows):
        # Each row is (driver, corr).
        return pd.DataFrame(
            [{"driver": d, "corr": c} for d, c in rows]
        )

    def test_returns_dataframe_with_expected_columns(self):
        out = strategic_priority_matrix(self._sens(("dar_clean_days", 0.42)))
        self.assertIsInstance(out, pd.DataFrame)
        for col in (
            "Variable",
            "Impact (Correlation)",
            "Ease of Implementation",
            "Strategic Designation",
        ):
            self.assertIn(col, out.columns)

    def test_high_corr_is_tier1(self):
        # |corr| >= 0.35 → Tier 1
        out = strategic_priority_matrix(self._sens(("idr_medicare", 0.55)))
        self.assertEqual(out.iloc[0]["Strategic Designation"],
                         "Tier 1: Strategic Fix")
        self.assertIn("High", out.iloc[0]["Impact (Correlation)"])

    def test_mid_corr_is_tier2(self):
        # 0.2 <= |corr| < 0.35 → Tier 2
        out = strategic_priority_matrix(self._sens(("fwr_medicare", 0.25)))
        self.assertEqual(out.iloc[0]["Strategic Designation"],
                         "Tier 2: Efficiency Play")
        self.assertIn("Med", out.iloc[0]["Impact (Correlation)"])

    def test_low_corr_is_tier3(self):
        # |corr| < 0.2 → Tier 3
        out = strategic_priority_matrix(self._sens(("upr_other", 0.10)))
        self.assertEqual(out.iloc[0]["Strategic Designation"],
                         "Tier 3: Monitor Only")
        self.assertIn("Low", out.iloc[0]["Impact (Correlation)"])

    def test_negative_corr_uses_magnitude_for_tier(self):
        # Tier classification is by |corr|, not signed corr.
        out = strategic_priority_matrix(self._sens(("idr_x", -0.45)))
        self.assertEqual(out.iloc[0]["Strategic Designation"],
                         "Tier 1: Strategic Fix")
        # Signed correlation preserved in the display string.
        self.assertIn("-0.45", out.iloc[0]["Impact (Correlation)"])

    def test_ease_for_dar_is_high_automation(self):
        out = strategic_priority_matrix(self._sens(("dar_medicare", 0.30)))
        self.assertEqual(out.iloc[0]["Ease of Implementation"],
                         "High (Automation)")

    def test_ease_for_denial_drivers_is_moderate(self):
        # idr / fwr → Moderate ease
        for d in ("idr_commercial", "fwr_medicaid"):
            out = strategic_priority_matrix(self._sens((d, 0.30)))
            self.assertEqual(out.iloc[0]["Ease of Implementation"],
                             "Moderate")

    def test_ease_for_upr_is_low(self):
        # upr → Low (contract negotiation)
        out = strategic_priority_matrix(self._sens(("upr_commercial", 0.30)))
        self.assertEqual(out.iloc[0]["Ease of Implementation"], "Low")

    def test_ease_for_unknown_driver_is_moderate(self):
        # No keyword match → Moderate fallback.
        out = strategic_priority_matrix(self._sens(("mystery_var", 0.30)))
        self.assertEqual(out.iloc[0]["Ease of Implementation"], "Moderate")

    def test_empty_input_returns_empty_frame(self):
        out = strategic_priority_matrix(pd.DataFrame(columns=["driver", "corr"]))
        self.assertEqual(len(out), 0)

    def test_preserves_row_count(self):
        sens = self._sens(
            ("dar_x", 0.5), ("idr_y", 0.4), ("fwr_z", 0.3), ("upr_q", 0.1)
        )
        out = strategic_priority_matrix(sens)
        self.assertEqual(len(out), 4)


# ---------------------------------------------------------------------------
# actionable_insights
# ---------------------------------------------------------------------------


def _summary(**overrides) -> pd.DataFrame:
    """Build a summary frame with the index columns that
    ``actionable_insights`` reads — mean/p10/p90 per metric."""
    base = {
        "ebitda_drag":             dict(mean=5_000_000, p10=3_000_000, p90=7_500_000),
        "economic_drag":           dict(mean=400_000,   p10=200_000,   p90=600_000),
        "drag_denial_writeoff":    dict(mean=2_500_000, p10=1_500_000, p90=3_500_000),
        "drag_underpay_leakage":   dict(mean=1_000_000, p10=600_000,   p90=1_400_000),
        "drag_denial_rework_cost": dict(mean=300_000,   p10=200_000,   p90=400_000),
        "drag_underpay_cost":      dict(mean=200_000,   p10=150_000,   p90=300_000),
    }
    base.update(overrides)
    rows = [{"metric": k, **v} for k, v in base.items()]
    return pd.DataFrame(rows).set_index("metric")


class ActionableInsightsTests(unittest.TestCase):
    """The bullet generator that lands in the partner brief. Each
    insight is gated by a contract (mean > 0, leakage > $100K, etc.) —
    these tests lock those gates so future tweaks don't quietly drop
    callouts from the deck."""

    def test_returns_list_of_strings(self):
        out = actionable_insights(_summary(), sensitivity=None)
        self.assertIsInstance(out, list)
        self.assertTrue(all(isinstance(s, str) for s in out))
        # At minimum the recoverable-opportunity bullet fires for the
        # default fixture.
        self.assertTrue(any("recoverable opportunity" in s for s in out))

    def test_ev_multiple_default_is_8x(self):
        # Default ev_multiple=8 → mean=5M → EV=$40M in the headline bullet.
        # Multiple is rendered via Python's default float formatting → '8.0x'.
        out = actionable_insights(_summary(), sensitivity=None)
        headline = next(s for s in out if "recoverable opportunity" in s)
        self.assertIn("8.0x", headline)
        self.assertIn("$40.0M", headline)

    def test_ev_multiple_override_carries_through(self):
        out = actionable_insights(_summary(), sensitivity=None, ev_multiple=12)
        headline = next(s for s in out if "recoverable opportunity" in s)
        self.assertIn("12", headline)  # multiple appears (12 or 12.0)
        self.assertIn("$60.0M", headline)  # 5M × 12

    def test_no_headline_when_mean_zero_or_negative(self):
        # ebitda_mean <= 0 → no headline opportunity bullet
        s = _summary(ebitda_drag=dict(mean=0, p10=0, p90=0))
        out = actionable_insights(s, sensitivity=None)
        self.assertFalse(any("recoverable opportunity" in t for t in out))

    def test_denial_writeoff_bullet_fires(self):
        out = actionable_insights(_summary(), sensitivity=None)
        self.assertTrue(any("Denial write-offs" in s for s in out))

    def test_no_denial_bullet_when_writeoff_zero(self):
        s = _summary(drag_denial_writeoff=dict(mean=0, p10=0, p90=0))
        out = actionable_insights(s, sensitivity=None)
        self.assertFalse(any("Denial write-offs" in t for t in out))

    def test_underpay_leakage_bullet_gated_at_100k(self):
        # Just under threshold → no bullet
        s = _summary(drag_underpay_leakage=dict(
            mean=99_000, p10=50_000, p90=120_000))
        out = actionable_insights(s, sensitivity=None)
        self.assertFalse(any("Underpayment leakage" in t for t in out))
        # Above threshold → bullet present
        s2 = _summary(drag_underpay_leakage=dict(
            mean=500_000, p10=300_000, p90=700_000))
        out2 = actionable_insights(s2, sensitivity=None)
        self.assertTrue(any("Underpayment leakage" in t for t in out2))

    def test_working_capital_bullet_gated_at_200k(self):
        # Just under threshold → no working-cap bullet
        s = _summary(economic_drag=dict(mean=199_000, p10=100_000, p90=300_000))
        out = actionable_insights(s, sensitivity=None)
        self.assertFalse(any("working capital drag" in t for t in out))

    def test_tail_risk_bullet_when_p90_above_mean_1_3x(self):
        # default fixture: mean=5M, p90=7.5M → ratio 1.5 → bullet fires
        out = actionable_insights(_summary(), sensitivity=None)
        self.assertTrue(any("stress case (P90)" in s for s in out))

    def test_no_tail_risk_bullet_when_p90_close_to_mean(self):
        # p90=mean*1.10 → no tail-risk bullet, may add the
        # "narrow tail" bullet instead.
        s = _summary(ebitda_drag=dict(
            mean=5_000_000, p10=4_500_000, p90=5_400_000))
        out = actionable_insights(s, sensitivity=None)
        self.assertFalse(any("stress case (P90) exceeds" in t for t in out))
        # Stability bullet should appear (p90 < mean*1.15 → narrow tail)
        self.assertTrue(
            any("close to the mean" in t for t in out),
            "narrow-tail stability bullet should appear when p90 < 1.15x mean",
        )

    def test_sensitivity_top_driver_bullet(self):
        sens = pd.DataFrame([
            {"driver": "idr_medicare",
             "driver_label": "Medicare Initial Denial Rate",
             "corr": 0.55},
            {"driver": "dar_other", "driver_label": "Other DAR", "corr": 0.10},
        ])
        out = actionable_insights(_summary(), sensitivity=sens)
        bullet = next(
            (s for s in out if "Sensitivity analysis identifies" in s),
            None,
        )
        self.assertIsNotNone(bullet)
        # Driver label, not raw column name, must appear in the bullet.
        self.assertIn("Medicare Initial Denial Rate", bullet)

    def test_sensitivity_weak_top_driver_skips_bullet(self):
        # |corr| < 0.3 → no bullet (avoids partner reading noise as signal)
        sens = pd.DataFrame([{"driver": "x",
                              "driver_label": "Some Driver",
                              "corr": 0.15}])
        out = actionable_insights(_summary(), sensitivity=sens)
        self.assertFalse(any("Sensitivity analysis identifies" in t
                              for t in out))

    def test_sensitivity_none_safe(self):
        out = actionable_insights(_summary(), sensitivity=None)
        self.assertIsInstance(out, list)
        self.assertFalse(any("Sensitivity analysis identifies" in t
                              for t in out))

    def test_sensitivity_empty_safe(self):
        out = actionable_insights(_summary(), sensitivity=pd.DataFrame())
        self.assertFalse(any("Sensitivity analysis identifies" in t
                              for t in out))

    def test_rework_bullet_fires_when_rework_share_high(self):
        # rework total = 1.5M, ebitda = 5M → 30% → > 18% gate → bullet
        s = _summary(
            drag_denial_rework_cost=dict(
                mean=1_000_000, p10=600_000, p90=1_400_000),
            drag_underpay_cost=dict(
                mean=500_000, p10=300_000, p90=700_000),
        )
        out = actionable_insights(s, sensitivity=None)
        self.assertTrue(any("Rework-related costs" in t for t in out))

    def test_dollar_formatting_in_bullets(self):
        # Every $ figure in the output must go through pretty_money,
        # so we expect $X.XM / $XK style (no raw 5000000.0).
        out = actionable_insights(_summary(), sensitivity=None)
        joined = " ".join(out)
        self.assertNotIn("5000000.0", joined)
        # Headline ebitda mean 5M → '$5.0M' in joined output.
        self.assertIn("$5.0M", joined)


# ---------------------------------------------------------------------------
# assumption_summary
# ---------------------------------------------------------------------------


def _cfg(include_denials=True, include_underpayments=True):
    """Minimal config that exercises every assumption_summary branch."""
    cfg = {
        "payers": {
            "Medicare": {
                "dar_clean_days": {"dist": "fixed", "value": 32},
                "include_denials": include_denials,
                "include_underpayments": include_underpayments,
                "denials": {
                    "idr": {"dist": "beta", "mean": 0.10, "sd": 0.02},
                    "fwr": {"dist": "beta", "mean": 0.02, "sd": 0.005},
                },
                "underpayments": {
                    "upr":      {"dist": "beta", "mean": 0.05, "sd": 0.01},
                    "severity": {"dist": "beta", "mean": 0.10, "sd": 0.02},
                    "recovery": {"dist": "beta", "mean": 0.55, "sd": 0.05},
                },
            },
            "Commercial": {
                "dar_clean_days": {"dist": "triangular",
                                    "low": 30, "mode": 40, "high": 60},
                "include_denials": False,
                "include_underpayments": False,
            },
        },
        "underpayments": {"enabled": True},
        "appeals": {
            "stages": {
                "stage1": {
                    "cost": {"dist": "fixed", "value": 50},
                    "days": {"dist": "fixed", "value": 14},
                },
                "stage2": {
                    "cost": {"dist": "fixed", "value": 150},
                    "days": {"dist": "fixed", "value": 30},
                },
            }
        },
    }
    return cfg


class AssumptionSummaryTests(unittest.TestCase):
    """Diligence-time documentation of what we *assumed*. Output is
    consumed by ``html_report`` + appears in the partner workbook —
    column names + payer rows are the contract."""

    def test_returns_dataframe_with_expected_columns(self):
        df = assumption_summary(_cfg(), n_draws=500, seed=7)
        for col in ("payer", "variable", "mean", "p10", "p90"):
            self.assertIn(col, df.columns)

    def test_includes_dar_for_every_payer(self):
        df = assumption_summary(_cfg(), n_draws=500, seed=7)
        dar_rows = df[df["variable"] == "dar_clean_days"]
        self.assertEqual(set(dar_rows["payer"]), {"Medicare", "Commercial"})

    def test_denial_rows_only_for_opted_in_payers(self):
        df = assumption_summary(_cfg(), n_draws=500, seed=7)
        idr = df[df["variable"] == "initial_denial_rate"]
        self.assertEqual(set(idr["payer"]), {"Medicare"})
        # Commercial opts out of denials → no row.
        self.assertFalse(((df["payer"] == "Commercial") &
                          (df["variable"] == "initial_denial_rate")).any())

    def test_underpayment_rows_for_opted_in_payers(self):
        df = assumption_summary(_cfg(), n_draws=500, seed=7)
        upr = df[df["variable"] == "underpayment_rate"]
        self.assertEqual(set(upr["payer"]), {"Medicare"})

    def test_global_appeals_rows_present(self):
        df = assumption_summary(_cfg(), n_draws=500, seed=7)
        # Cost + days for each stage, payer='ALL'
        appeal_rows = df[df["payer"] == "ALL"]
        names = set(appeal_rows["variable"])
        self.assertIn("appeal_cost_stage1", names)
        self.assertIn("appeal_days_stage1", names)
        self.assertIn("appeal_cost_stage2", names)
        self.assertIn("appeal_days_stage2", names)

    def test_underpayments_disabled_globally_skips_rows(self):
        cfg = _cfg()
        cfg["underpayments"]["enabled"] = False
        df = assumption_summary(cfg, n_draws=500, seed=7)
        self.assertFalse((df["variable"] == "underpayment_rate").any())

    def test_seed_determines_output(self):
        # Same seed → bit-for-bit identical output (run-to-run audit).
        a = assumption_summary(_cfg(), n_draws=500, seed=42)
        b = assumption_summary(_cfg(), n_draws=500, seed=42)
        pd.testing.assert_frame_equal(
            a.reset_index(drop=True), b.reset_index(drop=True))

    def test_different_seed_changes_random_distributions(self):
        # beta-distributed Medicare IDR must vary with seed.
        a = assumption_summary(_cfg(), n_draws=500, seed=1)
        b = assumption_summary(_cfg(), n_draws=500, seed=99)
        a_idr = float(a[(a.payer == "Medicare") &
                        (a.variable == "initial_denial_rate")]["mean"].iloc[0])
        b_idr = float(b[(b.payer == "Medicare") &
                        (b.variable == "initial_denial_rate")]["mean"].iloc[0])
        self.assertNotEqual(a_idr, b_idr)

    def test_fixed_dist_returns_exact_value(self):
        # Medicare DAR is fixed at 32 → mean == 32, p10 == p90 == 32
        df = assumption_summary(_cfg(), n_draws=200, seed=0)
        row = df[(df.payer == "Medicare") &
                 (df.variable == "dar_clean_days")].iloc[0]
        self.assertEqual(row["mean"], 32.0)
        self.assertEqual(row["p10"], 32.0)
        self.assertEqual(row["p90"], 32.0)

    def test_sorted_by_payer_then_variable(self):
        df = assumption_summary(_cfg(), n_draws=200, seed=0)
        # Stable sort key — first column is payer.
        payers = df["payer"].tolist()
        self.assertEqual(payers, sorted(payers))


# ---------------------------------------------------------------------------
# plot_ebitda_drag_distribution
# ---------------------------------------------------------------------------


def _drag_df(n=300, seed=42):
    rng = np.random.default_rng(seed)
    # Skewed positive (matches real sim output for ebitda_drag)
    return pd.DataFrame({
        "ebitda_drag": rng.gamma(shape=2.0, scale=1_500_000, size=n),
    })


class PlotEbitdaDragDistributionTests(unittest.TestCase):
    """Risk/Reward density chart. Drops the KDE → falls back to
    histogram silently when scipy/data is missing."""

    def test_writes_png_at_outpath(self):
        with tempfile.TemporaryDirectory() as tmp:
            outpath = os.path.join(tmp, "out.png")
            plot_ebitda_drag_distribution(_drag_df(), outpath)
            self.assertTrue(os.path.isfile(outpath))
            with open(outpath, "rb") as f:
                self.assertEqual(f.read(4), b"\x89PNG")
            self.assertGreater(os.path.getsize(outpath), 5_000)

    def test_handles_small_n_with_histogram_fallback(self):
        # n < 20 → KDE skipped, histogram path. Still must render.
        with tempfile.TemporaryDirectory() as tmp:
            outpath = os.path.join(tmp, "out.png")
            plot_ebitda_drag_distribution(_drag_df(n=10), outpath)
            self.assertTrue(os.path.isfile(outpath))

    def test_empty_df_silently_returns(self):
        # All-NaN / empty → return without writing; no crash.
        with tempfile.TemporaryDirectory() as tmp:
            outpath = os.path.join(tmp, "out.png")
            plot_ebitda_drag_distribution(
                pd.DataFrame({"ebitda_drag": []}), outpath,
            )
            self.assertFalse(os.path.isfile(outpath))

    def test_all_nan_silently_returns(self):
        with tempfile.TemporaryDirectory() as tmp:
            outpath = os.path.join(tmp, "out.png")
            plot_ebitda_drag_distribution(
                pd.DataFrame({"ebitda_drag": [float("nan")] * 10}),
                outpath,
            )
            self.assertFalse(os.path.isfile(outpath))

    def test_with_covenant_trigger_overlay(self):
        with tempfile.TemporaryDirectory() as tmp:
            outpath = os.path.join(tmp, "out.png")
            plot_ebitda_drag_distribution(
                _drag_df(), outpath,
                covenant_trigger_drag=5_000_000,
            )
            self.assertTrue(os.path.isfile(outpath))

    def test_with_management_case_overlay(self):
        with tempfile.TemporaryDirectory() as tmp:
            outpath = os.path.join(tmp, "out.png")
            plot_ebitda_drag_distribution(
                _drag_df(), outpath,
                management_case_drag=2_500_000,
            )
            self.assertTrue(os.path.isfile(outpath))

    def test_with_both_overlays(self):
        with tempfile.TemporaryDirectory() as tmp:
            outpath = os.path.join(tmp, "out.png")
            plot_ebitda_drag_distribution(
                _drag_df(), outpath,
                covenant_trigger_drag=6_000_000,
                management_case_drag=2_500_000,
            )
            self.assertTrue(os.path.isfile(outpath))

    def test_covenant_trigger_out_of_visible_range_safe(self):
        # Trigger far outside the data range → must not crash; the
        # render is allowed to skip drawing the line, just not error.
        with tempfile.TemporaryDirectory() as tmp:
            outpath = os.path.join(tmp, "out.png")
            plot_ebitda_drag_distribution(
                _drag_df(), outpath,
                covenant_trigger_drag=1e15,
            )
            self.assertTrue(os.path.isfile(outpath))


if __name__ == "__main__":
    unittest.main()
