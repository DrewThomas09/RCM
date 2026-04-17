"""Packet reproducibility contract.

Same inputs → same packet. This isn't a "nice to have"; partners who
cite a $X.XM number in IC must be able to rebuild the packet next
quarter and get the same number, or the audit trail is meaningless.

Reproducibility invariants:
- ``hash_inputs(same inputs)`` returns the same SHA256 across calls.
- ``build_analysis_packet`` twice with identical inputs gives
  identical section contents (run_id and generated_at differ — those
  are per-execution metadata, not content).
- Re-serializing through ``to_json`` → ``from_json`` round-trips.
- Cache hit via ``get_or_build_packet`` returns the exact packet.
"""
from __future__ import annotations

import json
import os
import tempfile
import unittest

from rcm_mc.analysis.analysis_store import get_or_build_packet
from rcm_mc.analysis.packet import (
    DealAnalysisPacket,
    ObservedMetric,
    hash_inputs,
)
from rcm_mc.analysis.packet_builder import build_analysis_packet
from rcm_mc.portfolio.store import PortfolioStore


def _temp_store():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    s = PortfolioStore(path)
    s.init_db()
    s.upsert_deal("repro", name="Repro Deal", profile={
        "bed_count": 400, "region": "midwest",
        "payer_mix": {"medicare": 0.4, "commercial": 0.45, "medicaid": 0.15},
    })
    return s, path


class TestHashDeterminism(unittest.TestCase):
    def test_same_inputs_hash_identical(self):
        inputs = {
            "denial_rate": 11.0,
            "days_in_ar": 55.0,
            "cost_to_collect": 4.0,
        }
        h1 = hash_inputs(deal_id="d1", observed_metrics=inputs)
        h2 = hash_inputs(deal_id="d1", observed_metrics=inputs)
        self.assertEqual(h1, h2)

    def test_key_ordering_does_not_change_hash(self):
        a = {"alpha": 1, "beta": 2, "gamma": 3}
        b = {"gamma": 3, "alpha": 1, "beta": 2}
        self.assertEqual(
            hash_inputs(deal_id="x", observed_metrics=a),
            hash_inputs(deal_id="x", observed_metrics=b),
        )

    def test_scenario_id_changes_hash(self):
        h1 = hash_inputs(deal_id="x", observed_metrics={"a": 1.0})
        h2 = hash_inputs(deal_id="x", observed_metrics={"a": 1.0},
                          scenario_id="stress")
        self.assertNotEqual(h1, h2)

    def test_float_precision_preserved(self):
        h1 = hash_inputs(deal_id="x", observed_metrics={"a": 0.1 + 0.2})
        h2 = hash_inputs(deal_id="x", observed_metrics={"a": 0.1 + 0.2})
        self.assertEqual(h1, h2)


class TestBuildIdempotence(unittest.TestCase):
    def setUp(self):
        self.store, self.path = _temp_store()

    def tearDown(self):
        try:
            os.unlink(self.path)
        except OSError:
            pass

    def _build(self) -> DealAnalysisPacket:
        return build_analysis_packet(
            self.store, "repro", skip_simulation=True,
            observed_override={
                "denial_rate": ObservedMetric(value=11.0),
                "days_in_ar": ObservedMetric(value=55.0),
            },
            target_metrics={"denial_rate": 7.0, "days_in_ar": 45.0},
            financials={
                "gross_revenue": 1_000_000_000,
                "net_revenue": 400_000_000,
                "current_ebitda": 32_000_000,
                "claims_volume": 300_000,
            },
        )

    def test_two_builds_same_bridge_numbers(self):
        p1 = self._build()
        p2 = self._build()
        self.assertAlmostEqual(
            p1.ebitda_bridge.total_ebitda_impact,
            p2.ebitda_bridge.total_ebitda_impact, places=3,
        )
        self.assertEqual(
            len(p1.ebitda_bridge.per_metric_impacts),
            len(p2.ebitda_bridge.per_metric_impacts),
        )
        # Per-lever impacts match exactly.
        a = {i.metric_key: i.ebitda_impact for i in p1.ebitda_bridge.per_metric_impacts}
        b = {i.metric_key: i.ebitda_impact for i in p2.ebitda_bridge.per_metric_impacts}
        self.assertEqual(a, b)

    def test_run_ids_differ_between_builds(self):
        """run_id is per-execution metadata — same content, different
        id so the audit log can tell the two calls apart."""
        p1 = self._build()
        p2 = self._build()
        self.assertNotEqual(p1.run_id, p2.run_id)

    def test_json_roundtrip_preserves_content(self):
        p = self._build()
        payload = p.to_json()
        restored = DealAnalysisPacket.from_json(payload)
        self.assertEqual(restored.deal_id, p.deal_id)
        self.assertAlmostEqual(
            restored.ebitda_bridge.total_ebitda_impact,
            p.ebitda_bridge.total_ebitda_impact, places=3,
        )
        self.assertEqual(
            len(restored.risk_flags), len(p.risk_flags),
        )


class TestCacheReturnsIdenticalPacket(unittest.TestCase):
    def setUp(self):
        self.store, self.path = _temp_store()

    def tearDown(self):
        try:
            os.unlink(self.path)
        except OSError:
            pass

    def test_cache_hit_returns_same_run_id(self):
        """With identical inputs the cache returns the exact stored
        packet — same run_id, same content."""
        p1 = get_or_build_packet(self.store, "repro", skip_simulation=True)
        p2 = get_or_build_packet(self.store, "repro", skip_simulation=True)
        self.assertEqual(p1.run_id, p2.run_id)

    def test_force_rebuild_produces_new_run_id_but_equivalent_packet(self):
        p1 = get_or_build_packet(self.store, "repro", skip_simulation=True)
        p2 = get_or_build_packet(self.store, "repro",
                                  skip_simulation=True, force_rebuild=True)
        self.assertNotEqual(p1.run_id, p2.run_id)
        # But bridge output is the same by construction.
        self.assertAlmostEqual(
            p1.ebitda_bridge.total_ebitda_impact,
            p2.ebitda_bridge.total_ebitda_impact, places=3,
        )


if __name__ == "__main__":
    unittest.main()
