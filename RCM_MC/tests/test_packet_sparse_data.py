"""Sparse-data regime: packet must still build + degrade gracefully.

Partners routinely look at deals where only 3-5 metrics are observed.
The packet builder's contract is:
- Never crash on sparse input
- Produce grade D on completeness
- Still emit bridge impacts for the levers where data exists
- Still emit sensible diligence questions
- Mark missing / skipped sections with ``SectionStatus`` so the UI
  can render an empty state rather than a null pointer
"""
from __future__ import annotations

import os
import tempfile
import unittest

from rcm_mc.analysis.packet import (
    DiligencePriority,
    ObservedMetric,
    SectionStatus,
)
from rcm_mc.analysis.packet_builder import build_analysis_packet
from rcm_mc.portfolio.store import PortfolioStore


def _temp_store():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    s = PortfolioStore(path)
    s.init_db()
    s.upsert_deal("sparse", name="Sparse Deal", profile={
        "bed_count": 120, "region": "west", "state": "CA",
        "payer_mix": {"medicare": 0.40, "commercial": 0.45, "medicaid": 0.15},
    })
    return s, path


class TestSparseDataRegime(unittest.TestCase):
    def setUp(self):
        self.store, self.path = _temp_store()

    def tearDown(self):
        try:
            os.unlink(self.path)
        except OSError:
            pass

    def _build(self, observed, **kwargs):
        return build_analysis_packet(
            self.store, "sparse", skip_simulation=True,
            observed_override=observed,
            financials={
                "gross_revenue": 200_000_000,
                "net_revenue": 80_000_000,
                "current_ebitda": 6_000_000,
                "claims_volume": 50_000,
            },
            **kwargs,
        )

    def test_three_metrics_grade_d_packet_builds(self):
        observed = {
            "denial_rate": ObservedMetric(value=10.0),
            "days_in_ar": ObservedMetric(value=52.0),
            "cost_to_collect": ObservedMetric(value=3.5),
        }
        packet = self._build(observed)
        self.assertEqual(packet.completeness.grade, "D")
        self.assertLess(packet.completeness.coverage_pct, 0.5)
        self.assertEqual(packet.completeness.observed_count, 3)

    def test_bridge_still_computes_with_available_levers(self):
        observed = {
            "denial_rate": ObservedMetric(value=10.0),
            "days_in_ar": ObservedMetric(value=52.0),
        }
        packet = self._build(
            observed,
            target_metrics={"denial_rate": 6.0, "days_in_ar": 45.0},
        )
        # Bridge should have two lever impacts.
        self.assertEqual(packet.ebitda_bridge.status, SectionStatus.OK)
        keys = {i.metric_key for i in packet.ebitda_bridge.per_metric_impacts}
        self.assertEqual(keys, {"denial_rate", "days_in_ar"})
        self.assertGreater(packet.ebitda_bridge.total_ebitda_impact, 0)

    def test_missing_critical_data_surfaces_p0_diligence(self):
        """With only 1 metric observed, the completeness-driven P0
        request for missing metrics must fire."""
        observed = {"denial_rate": ObservedMetric(value=14.0)}
        packet = self._build(observed)
        p0 = [q for q in packet.diligence_questions
              if q.priority == DiligencePriority.P0]
        # At least a few P0 items from the missing-metrics rule.
        self.assertGreaterEqual(len(p0), 3)

    def test_zero_observed_metrics_still_builds(self):
        packet = self._build({})
        # No observed → bridge incomplete, but packet itself valid.
        self.assertEqual(packet.completeness.observed_count, 0)
        self.assertEqual(packet.ebitda_bridge.status, SectionStatus.INCOMPLETE)
        # Packet JSON roundtrip still works.
        from rcm_mc.analysis.packet import DealAnalysisPacket
        DealAnalysisPacket.from_json(packet.to_json())  # no exception


if __name__ == "__main__":
    unittest.main()
