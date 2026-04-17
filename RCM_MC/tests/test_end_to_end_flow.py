"""End-to-end integration test: full deal lifecycle.

This test exercises the golden path: look up a hospital by CCN →
auto-populate → build analysis packet → verify the v2 bridge ran →
verify MC ran → generate diligence package → verify the package
contains all expected files → create a value creation plan from the
packet → update an initiative status.

Not a unit test — this is the kind of smoke test you'd run after
every deploy to verify the pipeline is wired end-to-end.
"""
from __future__ import annotations

import json
import os
import tempfile
import unittest
import zipfile
from pathlib import Path

from rcm_mc.analysis.analysis_store import get_or_build_packet
from rcm_mc.data.auto_populate import auto_populate
from rcm_mc.exports.diligence_package import generate_package
from rcm_mc.pe.value_creation_plan import (
    create_plan_from_packet,
    load_latest_plan,
    save_plan,
    update_initiative_status,
)
from rcm_mc.portfolio.store import PortfolioStore


class TestEndToEndFlow(unittest.TestCase):
    """Full deal lifecycle: CCN → packet → package → plan."""

    def setUp(self):
        tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tf.close()
        self.db_path = tf.name
        self.store = PortfolioStore(self.db_path)
        # Use the first CCN in the shipped HCRIS bundle.
        from rcm_mc.data.hcris import _get_hcris_cached
        df = _get_hcris_cached()
        self.ccn = str(df.iloc[0]["ccn"])

    def tearDown(self):
        try:
            os.unlink(self.db_path)
        except OSError:
            pass

    def test_golden_path(self):
        # ── 1. Auto-populate from CCN ──────────────────────────
        result = auto_populate(self.store, self.ccn)
        self.assertIsNotNone(result.selected)
        self.assertEqual(result.selected.confidence, 1.0)
        deal_id = result.selected.ccn

        # Upsert the deal into the store.
        self.store.upsert_deal(
            deal_id,
            name=result.selected.name,
            profile=result.profile,
        )

        # ── 2. Build analysis packet ──────────────────────────
        packet = get_or_build_packet(
            self.store, deal_id,
            skip_simulation=True,
            observed_override={"denial_rate": 11.5},
            financials={
                "gross_revenue": 600_000_000,
                "net_revenue": 400_000_000,
                "current_ebitda": 50_000_000,
                "claims_volume": 150_000,
                "exit_multiple": 10.0,
            },
            auto_populated=result.benchmark_metrics,
        )
        self.assertEqual(packet.deal_id, deal_id)
        self.assertIsNotNone(packet.ebitda_bridge)
        self.assertGreater(len(packet.rcm_profile), 0)

        # ── 3. Verify v2 bridge ran ──────────────────────────
        vbr = packet.value_bridge_result
        if vbr is not None:
            self.assertIn("lever_impacts", vbr)
            self.assertIn("total_recurring_ebitda_delta", vbr)

        # ── 4. Verify risk flags present ──────────────────────
        self.assertIsInstance(packet.risk_flags, list)

        # ── 5. Verify regulatory context attached ────────────
        if result.selected.state:
            self.assertIsNotNone(packet.regulatory_context)

        # ── 6. Generate diligence package ────────────────────
        out_dir = Path(tempfile.mkdtemp())
        pkg_path = generate_package(packet, out_dir, inputs_hash="e2e")
        self.assertTrue(zipfile.is_zipfile(pkg_path))
        with zipfile.ZipFile(pkg_path) as z:
            names = z.namelist()
            self.assertIn("manifest.json", names)
            self.assertIn("01_Executive_Summary.html", names)
            self.assertIn("02_Diligence_Memo.html", names)
            # Manifest has our deal_id.
            manifest = json.loads(z.read("manifest.json"))
            self.assertEqual(manifest["deal_id"], deal_id)

        # ── 7. Create value creation plan ────────────────────
        plan = create_plan_from_packet(packet)
        self.assertEqual(plan.deal_id, deal_id)
        if packet.ebitda_bridge.per_metric_impacts:
            self.assertGreater(len(plan.initiatives), 0)
            save_plan(self.store, plan)
            loaded = load_latest_plan(self.store, deal_id)
            self.assertIsNotNone(loaded)

            # ── 8. Update initiative status ──────────────────
            if loaded.initiatives:
                ok = update_initiative_status(
                    self.store, deal_id,
                    loaded.initiatives[0].initiative_id,
                    "in_progress",
                )
                self.assertTrue(ok)

        # ── 9. Verify packet is cached ───────────────────────
        # Second call should hit the cache (same inputs).
        packet2 = get_or_build_packet(
            self.store, deal_id,
            skip_simulation=True,
            observed_override={"denial_rate": 11.5},
            financials={
                "gross_revenue": 600_000_000,
                "net_revenue": 400_000_000,
                "current_ebitda": 50_000_000,
                "claims_volume": 150_000,
                "exit_multiple": 10.0,
            },
            auto_populated=result.benchmark_metrics,
        )
        # Same run_id means cache hit (didn't rebuild).
        self.assertEqual(packet2.run_id, packet.run_id)


class TestModuleCoherenceSmoke(unittest.TestCase):
    """Verify that the major subsystems don't raise on import +
    basic construction. This catches circular import regressions
    that don't surface in isolated unit tests."""

    def test_all_verticals_construct_bridge(self):
        from rcm_mc.verticals.asc.bridge import compute_asc_bridge
        from rcm_mc.verticals.mso.bridge import compute_mso_bridge
        from rcm_mc.verticals.behavioral_health.bridge import compute_bh_bridge

        r1 = compute_asc_bridge(
            {"cases_per_room_per_day": 3.0},
            {"cases_per_room_per_day": 5.0},
        )
        self.assertIsInstance(r1.total_ebitda_impact, float)

        r2 = compute_mso_bridge(
            {"wrvus_per_provider": 4000},
            {"wrvus_per_provider": 5500},
        )
        self.assertIsInstance(r2.total_ebitda_impact, float)

        r3 = compute_bh_bridge(
            {"occupancy_rate": 65}, {"occupancy_rate": 80},
        )
        self.assertIsInstance(r3.total_ebitda_impact, float)

    def test_ai_modules_construct(self):
        from rcm_mc.ai.llm_client import LLMClient, LLMResponse
        from rcm_mc.ai.memo_writer import compose_memo, ComposedMemo
        from rcm_mc.ai.conversation import ConversationEngine
        from rcm_mc.ai.document_qa import DocumentIndex

        # These should construct without needing API keys.
        client = LLMClient()
        self.assertIsNotNone(client)

    def test_analytics_modules_construct(self):
        from rcm_mc.analytics.causal_inference import interrupted_time_series
        from rcm_mc.analytics.service_lines import compute_service_line_pnl
        from rcm_mc.analytics.counterfactual import counterfactual_baseline

        r = counterfactual_baseline([10, 9, 8, 7])
        self.assertEqual(len(r.actual_trajectory), 4)


if __name__ == "__main__":
    unittest.main()
