"""Tests for the temporal forecasting module (Prompt 27).

Invariants locked here:

 1. ``detect_trend`` recovers slope 0.5 on y = 2 + 0.5·t.
 2. ``detect_trend`` on a short (n<3) series returns stable.
 3. Rising denial_rate → direction "deteriorating".
 4. Rising net_collection_rate → direction "improving".
 5. ``detect_seasonality`` fires on sin-overlay data.
 6. ``detect_seasonality`` false on pure linear data.
 7. ≥6 periods → linear method.
 8. ≥8 periods + seasonality → holt_winters.
 9. <6 periods → weighted_recent.
10. Linear forecast CI widens each forward step.
11. Holt-Winters CI widens each forward step.
12. Period labels: "2024-Q3" → "2024-Q4" / "2025-Q1" / ...
13. Period labels: "2024-01" → "2024-02" / ...
14. Unknown period label falls back to "+1" / "+2".
15. Non-finite values dropped silently.
16. ``forecast_all`` returns empty dict for empty input.
17. ``TemporalForecast.to_dict`` / ``from_dict`` round-trips.
18. Builder attaches forecasts when historical_values supplied.
19. Risk flag fires on deteriorating trend.
20. Sparkline SVG rendered in workbench when forecast is present.
21. Old packets without metric_forecasts still deserialize.
22. Packet JSON round-trip preserves forecasts.
"""
from __future__ import annotations

import math
import unittest
from typing import List, Tuple

from rcm_mc.analysis.packet import DealAnalysisPacket, ProfileMetric, MetricSource
from rcm_mc.ml.temporal_forecaster import (
    TemporalForecast,
    TrendResult,
    detect_seasonality,
    detect_trend,
    forecast_all,
    forecast_metric,
)
from rcm_mc.ui.analysis_workbench import render_workbench


def _linear_series(slope: float, n: int) -> List[Tuple[str, float]]:
    return [(f"2024-Q{i+1}" if i < 4 else
             f"{2025 + (i-4)//4}-Q{((i-4) % 4) + 1}",
             2.0 + slope * i) for i in range(n)]


# ── Trend detection ───────────────────────────────────────────────

class TestDetectTrend(unittest.TestCase):

    def test_slope_half_recovered(self):
        xs = [2.0 + 0.5 * i for i in range(10)]
        t = detect_trend(xs)
        self.assertAlmostEqual(t.slope_per_period, 0.5, delta=0.05)
        self.assertEqual(t.n_periods, 10)

    def test_short_series_stable(self):
        t = detect_trend([1.0, 2.0])
        self.assertEqual(t.direction, "stable")
        self.assertEqual(t.n_periods, 2)

    def test_rising_denial_rate_is_deteriorating(self):
        xs = [8.0, 9.0, 10.0, 11.0, 12.0, 13.0]
        t = detect_trend(xs, metric_key="denial_rate")
        self.assertEqual(t.direction, "deteriorating")

    def test_rising_ncr_is_improving(self):
        xs = [94.0, 95.0, 96.0, 97.0, 98.0, 99.0]
        t = detect_trend(xs, metric_key="net_collection_rate")
        self.assertEqual(t.direction, "improving")

    def test_flat_series_stable(self):
        xs = [10.0, 10.1, 9.9, 10.0, 10.0, 10.1]
        t = detect_trend(xs, metric_key="denial_rate")
        # Low slope → stable label.
        self.assertEqual(t.direction, "stable")


# ── Seasonality ───────────────────────────────────────────────────

class TestSeasonality(unittest.TestCase):

    def test_sin_overlay_detected(self):
        xs = [2 + 0.1 * i + math.sin(2 * math.pi * i / 4) for i in range(12)]
        self.assertTrue(detect_seasonality(xs, period=4))

    def test_linear_not_seasonal(self):
        xs = [2.0 + 0.5 * i for i in range(12)]
        self.assertFalse(detect_seasonality(xs, period=4))

    def test_short_series_not_seasonal(self):
        self.assertFalse(detect_seasonality([1, 2, 3], period=4))


# ── forecast_metric dispatch ──────────────────────────────────────

class TestForecastDispatch(unittest.TestCase):

    def test_linear_at_six_periods(self):
        f = forecast_metric("denial_rate", _linear_series(0.5, 6))
        self.assertEqual(f.method, "linear")

    def test_holt_winters_with_seasonality(self):
        xs = [(f"2024-Q{(i % 4) + 1}",
               2 + 0.1 * i + math.sin(2 * math.pi * i / 4))
              for i in range(12)]
        f = forecast_metric("denial_rate", xs, period=4)
        self.assertEqual(f.method, "holt_winters")
        self.assertTrue(f.seasonality_detected)

    def test_weighted_recent_at_three_periods(self):
        f = forecast_metric("denial_rate", _linear_series(0.5, 3))
        self.assertEqual(f.method, "weighted_recent")

    def test_ci_widens_over_horizon_linear(self):
        f = forecast_metric("denial_rate", _linear_series(0.5, 8))
        spans = [hi - lo for _, _, lo, hi in f.forecasted]
        for a, b in zip(spans, spans[1:]):
            self.assertGreaterEqual(b, a - 1e-9)

    def test_ci_widens_over_horizon_holt_winters(self):
        xs = [(f"p{i}", 2 + 0.1 * i + math.sin(2 * math.pi * i / 4))
              for i in range(16)]
        f = forecast_metric("denial_rate", xs, period=4)
        spans = [hi - lo for _, _, lo, hi in f.forecasted]
        for a, b in zip(spans, spans[1:]):
            self.assertGreaterEqual(b, a - 1e-9)


# ── Period-label rollover ─────────────────────────────────────────

class TestPeriodLabels(unittest.TestCase):

    def test_quarterly_rollover(self):
        xs = [("2024-Q1", 1.0), ("2024-Q2", 2.0), ("2024-Q3", 3.0),
              ("2024-Q4", 4.0), ("2025-Q1", 5.0), ("2025-Q2", 6.0)]
        f = forecast_metric("denial_rate", xs, n_forward=3)
        labels = [row[0] for row in f.forecasted]
        self.assertEqual(labels, ["2025-Q3", "2025-Q4", "2026-Q1"])

    def test_monthly_rollover(self):
        xs = [("2024-11", 10.0), ("2024-12", 11.0), ("2025-01", 12.0),
              ("2025-02", 13.0), ("2025-03", 14.0), ("2025-04", 15.0)]
        f = forecast_metric("denial_rate", xs, n_forward=2)
        labels = [row[0] for row in f.forecasted]
        self.assertEqual(labels, ["2025-05", "2025-06"])

    def test_unknown_format_falls_back(self):
        xs = [(f"WeekOf{i}", float(i)) for i in range(6)]
        f = forecast_metric("denial_rate", xs, n_forward=2)
        self.assertEqual([r[0] for r in f.forecasted], ["+1", "+2"])


# ── Edge cases ────────────────────────────────────────────────────

class TestEdgeCases(unittest.TestCase):

    def test_empty_history_empty_forecast(self):
        f = forecast_metric("denial_rate", [])
        self.assertEqual(f.historical, [])
        self.assertEqual(f.forecasted, [])

    def test_non_finite_values_dropped(self):
        xs = [("p0", 1.0), ("p1", float("nan")), ("p2", 2.0),
              ("p3", 3.0), ("p4", 4.0), ("p5", 5.0), ("p6", 6.0)]
        f = forecast_metric("denial_rate", xs)
        self.assertEqual(len(f.historical), 6)

    def test_forecast_all_empty(self):
        self.assertEqual(forecast_all({}), {})


# ── Serialization ─────────────────────────────────────────────────

class TestSerialization(unittest.TestCase):

    def test_roundtrip(self):
        f = forecast_metric(
            "denial_rate", _linear_series(0.5, 8),
        )
        restored = TemporalForecast.from_dict(f.to_dict())
        self.assertEqual(restored.method, f.method)
        self.assertEqual(len(restored.forecasted), len(f.forecasted))


# ── Builder + risk-flag integration ───────────────────────────────

class TestBuilderIntegration(unittest.TestCase):

    def _build(self, historical_values):
        import tempfile, os
        from rcm_mc.portfolio.store import PortfolioStore
        from rcm_mc.analysis.packet_builder import build_analysis_packet
        tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tf.close()
        try:
            store = PortfolioStore(tf.name)
            store.upsert_deal(
                "d1", name="Test",
                profile={"payer_mix": {"commercial": 1.0}, "bed_count": 200},
            )
            return build_analysis_packet(
                store, "d1", skip_simulation=True,
                observed_override={"denial_rate": 12.0},
                historical_values=historical_values,
            )
        finally:
            os.unlink(tf.name)

    def test_builder_attaches_forecasts(self):
        hist = {
            "denial_rate": _linear_series(0.5, 8),
        }
        packet = self._build(hist)
        self.assertIn("denial_rate", packet.metric_forecasts)
        self.assertEqual(
            packet.metric_forecasts["denial_rate"]["method"], "linear",
        )

    def test_trending_deterioration_flag_fires(self):
        """Rising denial rate over 8 periods → HIGH operational flag."""
        hist = {
            "denial_rate": [(f"2024-Q{i+1}" if i < 4 else
                              f"2025-Q{i-3}",
                              8.0 + 0.8 * i) for i in range(8)],
        }
        packet = self._build(hist)
        titles = [f.title for f in packet.risk_flags]
        self.assertTrue(
            any("trending deterioration" in t.lower() for t in titles),
        )

    def test_no_flag_when_improving(self):
        """Rising NCR (higher-is-better) → direction "improving" → no flag."""
        hist = {
            "net_collection_rate": _linear_series(0.4, 8),
        }
        packet = self._build(hist)
        trending_titles = [
            f.title for f in packet.risk_flags
            if "trending" in f.title.lower()
        ]
        self.assertEqual(trending_titles, [])


# ── Packet serialization ──────────────────────────────────────────

class TestPacketSerialization(unittest.TestCase):

    def test_roundtrip_preserves_forecasts(self):
        f = forecast_metric("denial_rate", _linear_series(0.5, 8))
        p = DealAnalysisPacket(
            deal_id="d1",
            metric_forecasts={"denial_rate": f.to_dict()},
        )
        restored = DealAnalysisPacket.from_dict(p.to_dict())
        self.assertIn("denial_rate", restored.metric_forecasts)

    def test_old_packet_without_field_deserializes(self):
        p = DealAnalysisPacket.from_dict({"deal_id": "d1"})
        self.assertEqual(p.metric_forecasts, {})


# ── Workbench sparkline ───────────────────────────────────────────

class TestWorkbenchSparkline(unittest.TestCase):

    def test_trend_arrow_rendered(self):
        f = forecast_metric(
            "denial_rate",
            [(f"2024-Q{i+1}" if i < 4 else f"2025-Q{i-3}",
              8.0 + 0.5 * i) for i in range(8)],
        )
        p = DealAnalysisPacket(
            deal_id="d1",
            rcm_profile={
                "denial_rate": ProfileMetric(
                    value=12.0, source=MetricSource.OBSERVED,
                ),
            },
            metric_forecasts={"denial_rate": f.to_dict()},
        )
        html = render_workbench(p)
        # Deteriorating → down arrow.
        self.assertIn("↓", html)
        # Sparkline SVG with polyline.
        self.assertIn("<polyline", html)


if __name__ == "__main__":
    unittest.main()
