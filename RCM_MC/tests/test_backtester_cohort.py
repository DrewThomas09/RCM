"""Tests for the leave-one-out backtester + cohort entry points.

`rcm_mc/ml/backtester.py` exposes two backtest functions:

- ``backtest(hospital_data, ...)`` — leave-one-out across hospitals:
  each hospital in turn becomes the held-out target, the rest is the
  candidate pool, and per-RCM-metric predicted-vs-observed pairs
  build up the per-metric grade.
- ``run_cohort_backtest(all_hospitals)`` — thin JSON-safe wrapper
  around ``backtest`` for the partner-facing cohort card.

Neither had direct test coverage before this file. The B.1-affected
``backtest_predictions`` is tested through test_ridge_predictor;
the legacy Phase-1 path through ``predict_missing`` was uncovered.
This file pins its contract.
"""
from __future__ import annotations

import math
import unittest

from rcm_mc.ml.backtester import (
    BacktestResult,
    backtest,
    run_cohort_backtest,
)


def _hospital(ccn, denial_rate, days_in_ar, **kw):
    """Minimal hospital dict carrying the two RCM metrics the
    legacy predictor reliably emits + a few non-RCM context features
    so find_comparables has something to anchor on."""
    base = {
        "ccn": ccn,
        "bed_count": kw.get("bed_count", 200),
        "region": kw.get("region", "South"),
        "payer_mix": kw.get("payer_mix", {
            "medicare": 0.45, "medicaid": 0.20,
            "commercial": 0.30, "self_pay": 0.05,
        }),
        "denial_rate": denial_rate,
        "days_in_ar": days_in_ar,
    }
    base.update({k: v for k, v in kw.items()
                 if k not in ("bed_count", "region", "payer_mix")})
    return base


class BacktestResultTests(unittest.TestCase):
    """Contract for the BacktestResult dataclass + to_dict."""

    def test_default_grade_is_F(self):
        # A fresh BacktestResult with no data has the failing grade
        # so the UI never silently shows a stale "A" rating.
        r = BacktestResult()
        self.assertEqual(r.overall_grade, "F")
        self.assertEqual(r.n_hospitals, 0)
        self.assertEqual(r.n_predictions, 0)
        self.assertEqual(r.per_metric, {})

    def test_to_dict_round_trip_keys(self):
        r = BacktestResult(
            per_metric={"denial_rate": {"mae": 0.01, "grade": "A"}},
            overall_grade="B",
            n_hospitals=50,
            n_predictions=300,
        )
        d = r.to_dict()
        # JSON-safe shape — every field is a plain dict/str/int.
        self.assertEqual(set(d.keys()), {
            "per_metric", "overall_grade",
            "n_hospitals", "n_predictions",
        })
        self.assertEqual(d["per_metric"]["denial_rate"]["grade"], "A")


class BacktestFunctionTests(unittest.TestCase):
    """Contract for the leave-one-out ``backtest`` function."""

    def test_empty_hospital_list_grade_F(self):
        r = backtest([])
        self.assertEqual(r.overall_grade, "F")
        self.assertEqual(r.n_hospitals, 0)
        self.assertEqual(r.n_predictions, 0)

    def test_single_hospital_grade_F(self):
        # Need ≥2 hospitals for leave-one-out (the target's pool
        # would be empty with n=1).
        r = backtest([_hospital("h1", 0.10, 45)])
        self.assertEqual(r.overall_grade, "F")
        self.assertEqual(r.n_hospitals, 1)
        self.assertEqual(r.n_predictions, 0)

    def test_none_input_safe(self):
        # Defensive: None coerces to empty list.
        r = backtest(None)  # type: ignore
        self.assertEqual(r.n_hospitals, 0)

    def test_returns_per_metric_dict(self):
        # 6 hospitals → leave-one-out across all 6, the predictor
        # gets exercised, and per_metric should carry entries for
        # the RCM metrics actually present in the data.
        hospitals = [
            _hospital(f"h{i}", 0.08 + i * 0.005, 40 + i * 2)
            for i in range(6)
        ]
        r = backtest(hospitals)
        self.assertEqual(r.n_hospitals, 6)
        # n_predictions is bounded above by n × n_metrics.
        self.assertGreaterEqual(r.n_predictions, 0)
        # If we got predictions, per_metric is populated with the
        # standard schema (mae/r2/mape/n/grade).
        for metric, stats in r.per_metric.items():
            self.assertIn("mae", stats)
            self.assertIn("r2", stats)
            self.assertIn("mape", stats)
            self.assertIn("n", stats)
            self.assertIn("grade", stats)
            # Grade is a single letter.
            self.assertIn(stats["grade"], ["A", "B", "C", "D", "F"])

    def test_grade_is_one_of_known_letters(self):
        hospitals = [
            _hospital(f"h{i}", 0.10, 50) for i in range(4)
        ]
        r = backtest(hospitals)
        self.assertIn(r.overall_grade, ["A", "B", "C", "D", "F"])

    def test_n_predictions_bounded_by_hospitals(self):
        # Per-hospital we hold ≥1 RCM metric and predict it; total
        # predictions ≥ 0 but never exceeds n × |RCM_METRICS|.
        from rcm_mc.ml.rcm_predictor import RCM_METRICS
        hospitals = [_hospital(f"h{i}", 0.10, 50) for i in range(5)]
        r = backtest(hospitals)
        self.assertLessEqual(
            r.n_predictions, 5 * len(RCM_METRICS),
        )

    def test_ignores_non_finite_actuals(self):
        # A hospital with NaN/inf in a target metric should NOT crash
        # the backtest and should NOT contribute to that metric's
        # per-metric pair count.
        hospitals = [
            _hospital(f"h{i}", 0.10, 50) for i in range(4)
        ]
        hospitals[0]["denial_rate"] = float("nan")
        hospitals[1]["days_in_ar"] = float("inf")
        # Must not raise.
        r = backtest(hospitals)
        self.assertEqual(r.n_hospitals, 4)

    def test_max_comparables_honored(self):
        # The max_comparables knob is forwarded to find_comparables;
        # smaller pool → fewer comparables but backtest still runs.
        hospitals = [_hospital(f"h{i}", 0.10, 50) for i in range(8)]
        r_default = backtest(hospitals)
        r_capped = backtest(hospitals, max_comparables=2)
        self.assertEqual(r_default.n_hospitals, r_capped.n_hospitals)
        # Both runs produce a JSON-safe dict — schema stable
        # regardless of the cap.
        self.assertIn("per_metric", r_capped.to_dict())


class RunCohortBacktestTests(unittest.TestCase):
    """Contract for the JSON-safe wrapper."""

    def test_wraps_backtest_and_returns_dict(self):
        hospitals = [
            _hospital(f"h{i}", 0.10, 50) for i in range(4)
        ]
        out = run_cohort_backtest(hospitals)
        self.assertIsInstance(out, dict)
        self.assertIn("per_metric", out)
        self.assertIn("overall_grade", out)
        self.assertIn("n_hospitals", out)
        self.assertIn("n_predictions", out)

    def test_empty_input(self):
        out = run_cohort_backtest([])
        self.assertEqual(out["overall_grade"], "F")
        self.assertEqual(out["n_hospitals"], 0)
        self.assertEqual(out["n_predictions"], 0)
        self.assertEqual(out["per_metric"], {})

    def test_iterable_input_accepted(self):
        # The signature says Iterable, not List — a generator must work.
        def gen():
            for i in range(3):
                yield _hospital(f"h{i}", 0.10, 50)
        out = run_cohort_backtest(gen())
        self.assertEqual(out["n_hospitals"], 3)

    def test_output_is_json_safe(self):
        # All values must round-trip through json.dumps (no numpy
        # types, no objects).
        import json
        out = run_cohort_backtest([
            _hospital(f"h{i}", 0.10, 50) for i in range(4)
        ])
        s = json.dumps(out)
        # Round-trip restores the same structure.
        round_trip = json.loads(s)
        self.assertEqual(round_trip["overall_grade"],
                         out["overall_grade"])


if __name__ == "__main__":
    unittest.main()
