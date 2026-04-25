"""Extreme-value resilience suite.

Every modeled function should handle edge inputs without
crashing — very large hospitals (5000 beds / $10B NPSR), very
small (5 beds / $1M NPSR), zero revenue, 100% denial rate,
100% single-payer mix, negative margins, negative growth.

Outcome on every test: no crash, sensible output. Assertions
verify outputs stay within sanity-range clamps, division-by-zero
paths return None or 0 instead of raising, and ratio-based math
doesn't blow up to infinity.
"""
from __future__ import annotations

import unittest

import numpy as np


# ── ML predictors at scale extremes ─────────────────────────

class TestDenialRatePredictorExtremes(unittest.TestCase):
    def _train(self):
        from rcm_mc.ml.denial_rate_predictor import (
            train_denial_rate_predictor,
        )
        rng = np.random.default_rng(7)
        rows = []
        for _ in range(120):
            beds = float(rng.integers(50, 500))
            rows.append({
                "beds": beds,
                "medicare_day_pct":
                    float(rng.uniform(0.2, 0.6)),
                "medicaid_day_pct":
                    float(rng.uniform(0.1, 0.3)),
                "denial_rate":
                    float(rng.uniform(0.05, 0.15)),
            })
        return train_denial_rate_predictor(rows)

    def test_giant_hospital(self):
        from rcm_mc.ml.denial_rate_predictor import (
            predict_denial_rate,
        )
        p = self._train()
        # 5000 beds, $10B NPSR, 90% Medicare
        yhat, (lo, hi), _ = predict_denial_rate(p, {
            "beds": 5_000,
            "medicare_day_pct": 0.90,
            "medicaid_day_pct": 0.05,
            "net_patient_revenue": 10_000_000_000,
            "gross_patient_revenue": 30_000_000_000,
            "operating_expenses": 9_500_000_000,
        })
        # Sanity range (0.0, 0.40)
        self.assertGreaterEqual(yhat, 0.0)
        self.assertLessEqual(yhat, 0.40)

    def test_tiny_hospital(self):
        from rcm_mc.ml.denial_rate_predictor import (
            predict_denial_rate,
        )
        p = self._train()
        yhat, _, _ = predict_denial_rate(p, {
            "beds": 5,
            "medicare_day_pct": 0.55,
            "medicaid_day_pct": 0.30,
            "net_patient_revenue": 1_000_000,
        })
        self.assertGreaterEqual(yhat, 0.0)
        self.assertLessEqual(yhat, 0.40)

    def test_zero_revenue(self):
        from rcm_mc.ml.denial_rate_predictor import (
            predict_denial_rate,
            build_denial_features,
        )
        # Zero revenue → division-by-zero risk
        f = build_denial_features({
            "beds": 100,
            "net_patient_revenue": 0,
            "gross_patient_revenue": 0,
            "operating_expenses": 0,
            "discharges": 0,
        })
        # All features are real numbers — no inf, no NaN
        for name, val in f.items():
            self.assertFalse(
                np.isnan(val),
                f"{name} is NaN")
            self.assertFalse(
                np.isinf(val),
                f"{name} is inf")

        p = self._train()
        yhat, _, _ = predict_denial_rate(p, {
            "beds": 100,
            "net_patient_revenue": 0,
            "gross_patient_revenue": 0,
        })
        self.assertGreaterEqual(yhat, 0.0)
        self.assertLessEqual(yhat, 0.40)

    def test_full_medicaid_mix(self):
        from rcm_mc.ml.denial_rate_predictor import (
            predict_denial_rate,
        )
        p = self._train()
        yhat, _, _ = predict_denial_rate(p, {
            "beds": 200,
            "medicare_day_pct": 0.0,
            "medicaid_day_pct": 1.0,
        })
        self.assertGreaterEqual(yhat, 0.0)
        self.assertLessEqual(yhat, 0.40)


class TestForwardDistressExtremes(unittest.TestCase):
    def test_zero_everything_features(self):
        from rcm_mc.ml.forward_distress_predictor import (
            build_forward_distress_features,
        )
        f = build_forward_distress_features({
            "operating_margin_t": 0,
            "margin_history": [],
            "cash_on_hand": 0,
            "annual_operating_expenses": 0,
            "current_assets": 0,
            "current_liabilities": 0,
            "long_term_debt": 0,
            "net_patient_revenue": 0,
            "interest_expense": 0,
            "ebit": 0,
            "discharges_history": [],
            "beds": 0,
            "occupancy_rate": 0,
            "medicare_day_pct": 0,
            "medicaid_day_pct": 0,
            "gross_patient_revenue": 0,
        })
        for name, v in f.items():
            self.assertFalse(np.isnan(v),
                             f"{name} NaN")
            self.assertFalse(np.isinf(v),
                             f"{name} inf")

    def test_pathological_margin_history(self):
        from rcm_mc.ml.forward_distress_predictor import (
            build_forward_distress_features,
        )
        # Extreme negative + positive margins
        f = build_forward_distress_features({
            "margin_history": [-0.50, 0.50, -0.30, 0.40],
        })
        self.assertFalse(
            np.isnan(f["margin_3yr_slope"]))
        self.assertFalse(
            np.isnan(f["margin_3yr_volatility"]))


# ── Service line profitability at extremes ──────────────────

class TestServiceLineExtremes(unittest.TestCase):
    def _record(self, line, **kwargs):
        from rcm_mc.ml.service_line_profitability import (
            CostCenterRecord,
        )
        return CostCenterRecord(
            ccn="X", fiscal_year=2023, line_number=line,
            cost_center_name=str(line), **kwargs)

    def test_zero_revenue(self):
        from rcm_mc.ml.service_line_profitability import (
            compute_service_line_profitability,
        )
        # All revenue = 0 — division should not crash
        out = compute_service_line_profitability([
            self._record(60,
                         direct_cost=1_000_000,
                         overhead_allocation=200_000,
                         gross_charges=0,
                         net_revenue=0),
        ])
        self.assertEqual(len(out), 1)
        # contribution_margin_pct = 0 when net_revenue is 0
        self.assertEqual(
            out[0].contribution_margin_pct, 0.0)

    def test_giant_hospital(self):
        from rcm_mc.ml.service_line_profitability import (
            compute_service_line_profitability,
        )
        out = compute_service_line_profitability([
            self._record(60,
                         direct_cost=500_000_000,
                         overhead_allocation=100_000_000,
                         gross_charges=4_000_000_000,
                         net_revenue=2_000_000_000),
        ])
        self.assertEqual(len(out), 1)
        self.assertAlmostEqual(
            out[0].contribution_margin,
            1_400_000_000)

    def test_negative_revenue(self):
        """Edge case: a refund-heavy quarter could leave net
        revenue negative. Should not crash."""
        from rcm_mc.ml.service_line_profitability import (
            compute_service_line_profitability,
        )
        out = compute_service_line_profitability([
            self._record(60,
                         direct_cost=1_000,
                         overhead_allocation=200,
                         gross_charges=5_000,
                         net_revenue=-500),
        ])
        self.assertEqual(len(out), 1)
        # Negative revenue → negative margin pct, no inf
        self.assertFalse(
            np.isinf(out[0].contribution_margin_pct))


# ── Payer mix cascade at extremes ───────────────────────────

class TestPayerMixCascadeExtremes(unittest.TestCase):
    def test_full_self_pay_baseline(self):
        from rcm_mc.ml.payer_mix_cascade import (
            PayerMix, compute_baseline_metrics,
        )
        # 100% self-pay — pathological but legal
        m = PayerMix(
            medicare=0, medicaid=0,
            commercial=0, self_pay=1.0)
        metrics = compute_baseline_metrics(m)
        # Self-pay reimbursement_index is 0.15
        self.assertAlmostEqual(
            metrics["revenue_index"], 0.15)
        # Realistic NPR scaled accordingly
        self.assertGreater(metrics["npr"], 0)

    def test_extreme_shift(self):
        """Shift from 100% commercial to 100% self-pay —
        cascade should compute without crashing."""
        from rcm_mc.ml.payer_mix_cascade import (
            PayerMix, cascade_payer_mix_shift,
        )
        baseline = PayerMix(
            medicare=0, medicaid=0,
            commercial=1.0, self_pay=0)
        new = PayerMix(
            medicare=0, medicaid=0,
            commercial=0, self_pay=1.0)
        result = cascade_payer_mix_shift(
            baseline, new,
            annual_gross_charges=1_000_000_000)
        # Massive negative NPR delta
        self.assertLess(
            result.npr_delta_dollars, -700_000_000)

    def test_zero_gross_charges(self):
        from rcm_mc.ml.payer_mix_cascade import (
            PayerMix, compute_baseline_metrics,
        )
        m = PayerMix(
            medicare=0.4, medicaid=0.1,
            commercial=0.4, self_pay=0.1)
        metrics = compute_baseline_metrics(
            m, annual_gross_charges=0)
        self.assertEqual(metrics["npr"], 0)
        self.assertEqual(metrics["bad_debt"], 0)
        self.assertEqual(metrics["ar_balance"], 0)


# ── Improvement potential at extremes ───────────────────────

class TestImprovementPotentialExtremes(unittest.TestCase):
    def _profile(self, **overrides):
        from rcm_mc.pe.rcm_ebitda_bridge import (
            FinancialProfile,
        )
        defaults = dict(
            gross_revenue=1_300_000_000,
            net_revenue=400_000_000,
            total_operating_expenses=370_000_000,
            current_ebitda=30_000_000,
            total_claims_volume=300_000,
            payer_mix={"medicare": 0.4,
                       "medicaid": 0.15,
                       "commercial": 0.45},
        )
        defaults.update(overrides)
        return FinancialProfile(**defaults)

    def test_zero_revenue_profile(self):
        from rcm_mc.ml.improvement_potential import (
            PeerBenchmarks,
            estimate_improvement_potential,
        )
        bm = PeerBenchmarks(
            denial_rate=7.0, days_in_ar=38.0)
        profile = self._profile(
            net_revenue=0,
            gross_revenue=0,
            current_ebitda=0,
            total_claims_volume=0)
        result = estimate_improvement_potential(
            profile,
            current_metrics={
                "denial_rate": 12.0,
                "days_in_ar": 55.0},
            benchmarks=bm)
        # No NaN / inf
        self.assertFalse(
            np.isinf(result.realistic_total_ebitda))

    def test_100_pct_denial_rate(self):
        """Extreme: 100% denial rate. Bridge should still
        compute without overflow."""
        from rcm_mc.ml.improvement_potential import (
            PeerBenchmarks,
            estimate_improvement_potential,
        )
        bm = PeerBenchmarks(denial_rate=7.0)
        result = estimate_improvement_potential(
            self._profile(),
            current_metrics={"denial_rate": 100.0},
            benchmarks=bm)
        # Lever fires (huge gap), no inf
        self.assertGreater(
            result.realistic_total_ebitda, 0)
        self.assertFalse(
            np.isinf(result.realistic_total_ebitda))


# ── Power chart edge inputs ─────────────────────────────────

class TestPowerChartExtremes(unittest.TestCase):
    def test_single_data_point(self):
        from rcm_mc.ui.power_chart import (
            ChartSeries, render_power_chart,
        )
        html = render_power_chart(
            chart_id="x",
            series=[ChartSeries(
                "A", points=[("Q1", 100)])])
        # Renders, has SVG, no inf
        self.assertIn("<svg", html)

    def test_all_same_value(self):
        """y_min == y_max edge — viewBox math could divide by 0."""
        from rcm_mc.ui.power_chart import (
            ChartSeries, render_power_chart,
        )
        html = render_power_chart(
            chart_id="x",
            series=[ChartSeries(
                "A",
                points=[("Q1", 100), ("Q2", 100),
                        ("Q3", 100)])])
        self.assertIn("<svg", html)

    def test_extreme_value_range(self):
        """Mix of $1 and $10B values."""
        from rcm_mc.ui.power_chart import (
            ChartSeries, render_power_chart,
        )
        html = render_power_chart(
            chart_id="x",
            series=[ChartSeries(
                "A",
                points=[("Q1", 1.0),
                        ("Q2", 10_000_000_000.0)])],
            y_kind="money")
        # Renders without crashing
        self.assertIn("<svg", html)
        # Money formatting handles billions
        self.assertIn("$10.00B", html)

    def test_negative_values(self):
        from rcm_mc.ui.power_chart import (
            ChartSeries, render_power_chart,
        )
        html = render_power_chart(
            chart_id="x",
            series=[ChartSeries(
                "A",
                points=[("Q1", -100), ("Q2", 100),
                        ("Q3", -50)])])
        self.assertIn("<svg", html)

    def test_all_none_in_series(self):
        from rcm_mc.ui.power_chart import (
            ChartSeries, render_power_chart,
        )
        # All-None y values: should reject with helpful error
        with self.assertRaises(ValueError):
            render_power_chart(
                chart_id="x",
                series=[ChartSeries(
                    "A",
                    points=[("Q1", None),
                            ("Q2", None)])])


# ── Power table extreme inputs ──────────────────────────────

class TestPowerTableExtremes(unittest.TestCase):
    def test_huge_row_count(self):
        from rcm_mc.ui.power_table import (
            Column, render_power_table,
        )
        rows = [
            {"a": i, "b": i * 100}
            for i in range(5000)
        ]
        html = render_power_table(
            table_id="big",
            columns=[
                Column("a", "A", kind="int"),
                Column("b", "B", kind="money"),
            ],
            rows=rows)
        # Counter shows the right count
        self.assertIn("5,000 of 5,000", html)

    def test_extreme_money_values(self):
        from rcm_mc.ui.power_table import (
            Column, render_power_table, _format_cell,
        )
        # Test the formatter directly first
        self.assertEqual(
            _format_cell(1e12, "money"), "$1,000.00B")
        # Render
        html = render_power_table(
            table_id="x",
            columns=[Column("v", "Val", kind="money")],
            rows=[
                {"v": 1e12},
                {"v": -1e9},
                {"v": 0.01},
            ])
        # No crash
        self.assertIn("<table", html)


# ── Compare module extreme inputs ───────────────────────────

class TestCompareExtremes(unittest.TestCase):
    def test_compare_with_extreme_values(self):
        from rcm_mc.ui.compare import (
            ComparableEntity, ComparisonMetric,
            render_comparison,
        )
        html = render_comparison(
            entities=[
                ComparableEntity(
                    label="Tiny",
                    values={"npr": 1.0,
                            "margin": -0.99}),
                ComparableEntity(
                    label="Huge",
                    values={"npr": 10_000_000_000,
                            "margin": 0.99}),
            ],
            metrics=[
                ComparisonMetric(
                    "npr", kind="money",
                    show_in_glossary=False),
                ComparisonMetric(
                    "margin", kind="pct",
                    show_in_glossary=False),
            ])
        # Both render
        self.assertIn("Tiny", html)
        self.assertIn("Huge", html)
        # Money formatter handles 10B
        self.assertIn("$10.00B", html)


# ── Geographic clustering extremes ──────────────────────────

class TestGeographicClusteringExtremes(unittest.TestCase):
    def test_one_hospital_per_state(self):
        from rcm_mc.ml.geographic_clustering import (
            find_hunting_grounds,
        )
        # Each state has exactly 1 hospital — below default
        # min_hospitals=3
        hospitals = [
            {"state": s, "denial_rate": 0.1,
             "days_in_ar": 45,
             "collection_rate": 0.95,
             "operating_margin": 0.05}
            for s in ["AL", "AK", "AZ", "AR", "CA"]
        ]
        report = find_hunting_grounds(hospitals)
        # No regions met the floor
        self.assertEqual(report.n_regions, 0)
        self.assertTrue(any(
            "min_hospitals_per_region" in n
            for n in report.notes))

    def test_identical_metrics_across_states(self):
        """Zero variance across regions — z-score uses
        std=1 fallback."""
        from rcm_mc.ml.geographic_clustering import (
            score_hotspots, aggregate_by_region,
        )
        hospitals = [
            {"state": s, "denial_rate": 0.10,
             "days_in_ar": 45,
             "collection_rate": 0.95,
             "operating_margin": 0.05}
            for s in ["AL", "AK", "AZ"] * 5
        ]
        aggs = aggregate_by_region(hospitals)
        hotspots = score_hotspots(aggs)
        self.assertGreater(len(hotspots), 0)
        # All composite_z near 0 (no variance to flag)
        for h in hotspots:
            self.assertAlmostEqual(
                h.composite_z, 0, places=2)


if __name__ == "__main__":
    unittest.main()
