"""Deep cross-module integration tests + new page route tests + response cache.

DEEP INTEGRATION:
 1. Full pipeline: auto-populate → packet → plan → stage tracking →
    timeline → diligence package — all on a single deal in one test.

NEW ROUTES:
 2. GET /source renders the deal sourcing page.
 3. GET /source?thesis=denial_turnaround returns results.
 4. GET /settings/custom-kpis renders.
 5. GET /settings/automations renders.
 6. GET /settings/integrations renders.

RESPONSE CACHE:
 7. Cache set/get round-trips.
 8. TTL expiry works.
 9. Cache max_entries eviction.
10. Thread safety (concurrent access doesn't crash).
"""
from __future__ import annotations

import json
import os
import socket
import tempfile
import threading
import time
import unittest
import urllib.request
from pathlib import Path

from rcm_mc.infra.response_cache import ResponseCache
from rcm_mc.portfolio.store import PortfolioStore


def _tmp_store():
    tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tf.close()
    return PortfolioStore(tf.name), tf.name


def _start(db_path):
    from rcm_mc.server import build_server
    s = socket.socket(); s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]; s.close()
    server, _ = build_server(port=port, db_path=db_path)
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start(); time.sleep(0.05)
    return server, port


# ── Deep integration ──────────────────────────────────────────────

class TestDeepIntegration(unittest.TestCase):

    def test_full_pipeline_single_deal(self):
        """auto-populate → packet → plan → stage → timeline → package."""
        store, path = _tmp_store()
        try:
            from rcm_mc.data.auto_populate import auto_populate
            from rcm_mc.data.hcris import _get_hcris_cached

            # Step 1: Find a hospital.
            df = _get_hcris_cached()
            ccn = str(df.iloc[0]["ccn"])
            result = auto_populate(store, ccn)
            self.assertIsNotNone(result.selected)
            deal_id = result.selected.ccn
            store.upsert_deal(deal_id, name=result.selected.name,
                              profile=result.profile)

            # Step 2: Build packet.
            from rcm_mc.analysis.analysis_store import get_or_build_packet
            packet = get_or_build_packet(
                store, deal_id, skip_simulation=True,
                observed_override={"denial_rate": 11.0},
                financials={"net_revenue": 400e6, "current_ebitda": 50e6,
                             "claims_volume": 150_000},
                auto_populated=result.benchmark_metrics,
            )
            self.assertEqual(packet.deal_id, deal_id)

            # Step 3: Create value creation plan.
            from rcm_mc.pe.value_creation_plan import (
                create_plan_from_packet, save_plan, load_latest_plan,
            )
            plan = create_plan_from_packet(packet)
            if plan.initiatives:
                save_plan(store, plan)
                loaded = load_latest_plan(store, deal_id)
                self.assertIsNotNone(loaded)

            # Step 4: Set deal stage.
            from rcm_mc.deals.deal_stages import set_stage, current_stage
            set_stage(store, deal_id, "diligence")
            self.assertEqual(current_stage(store, deal_id), "diligence")

            # Step 5: Timeline should have events.
            from rcm_mc.ui.deal_timeline import collect_timeline
            events = collect_timeline(store, deal_id, days=1)
            self.assertGreater(len(events), 0)

            # Step 6: Generate diligence package.
            from rcm_mc.exports.diligence_package import generate_package
            import zipfile
            out = Path(tempfile.mkdtemp())
            pkg = generate_package(packet, out)
            self.assertTrue(zipfile.is_zipfile(pkg))

            # Step 7: Cross-deal search finds our deal.
            from rcm_mc.analysis.deal_overrides import set_override
            set_override(store, deal_id, "bridge.exit_multiple", 11.0,
                         set_by="test", reason="deep integration test")
            from rcm_mc.analysis.cross_deal_search import search_across_deals
            results = search_across_deals(store, "integration test")
            self.assertTrue(
                any(r.deal_id == deal_id for r in results),
            )

        finally:
            os.unlink(path)


# ── New route tests ───────────────────────────────────────────────

class TestNewRoutes(unittest.TestCase):

    def test_source_page(self):
        tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tf.close()
        try:
            server, port = _start(tf.name)
            try:
                with urllib.request.urlopen(
                    f"http://127.0.0.1:{port}/source",
                ) as r:
                    body = r.read().decode()
                self.assertIn("Deal Sourcing", body)
                self.assertIn("thesis", body)
            finally:
                server.shutdown(); server.server_close()
        finally:
            os.unlink(tf.name)

    def test_source_with_thesis(self):
        tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tf.close()
        try:
            server, port = _start(tf.name)
            try:
                with urllib.request.urlopen(
                    f"http://127.0.0.1:{port}/source?thesis=denial_turnaround",
                ) as r:
                    body = r.read().decode()
                self.assertIn("Deal Sourcing", body)
                # The thesis is selected in the dropdown.
                self.assertIn("selected", body)
            finally:
                server.shutdown(); server.server_close()
        finally:
            os.unlink(tf.name)

    def test_settings_custom_kpis(self):
        tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tf.close()
        try:
            server, port = _start(tf.name)
            try:
                with urllib.request.urlopen(
                    f"http://127.0.0.1:{port}/settings/custom-kpis",
                ) as r:
                    self.assertIn("Custom KPIs", r.read().decode())
            finally:
                server.shutdown(); server.server_close()
        finally:
            os.unlink(tf.name)

    def test_settings_automations(self):
        # Uses its own server instance; add a pause so the prior
        # test's port is fully released.
        time.sleep(0.2)
        tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tf.close()
        try:
            server, port = _start(tf.name)
            try:
                with urllib.request.urlopen(
                    f"http://127.0.0.1:{port}/settings/automations",
                ) as r:
                    self.assertIn("Automation Rules", r.read().decode())
            finally:
                server.shutdown(); server.server_close()
        finally:
            os.unlink(tf.name)

    def test_settings_integrations(self):
        tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tf.close()
        try:
            server, port = _start(tf.name)
            try:
                with urllib.request.urlopen(
                    f"http://127.0.0.1:{port}/settings/integrations",
                ) as r:
                    self.assertIn("Integrations", r.read().decode())
            finally:
                server.shutdown(); server.server_close()
        finally:
            os.unlink(tf.name)


# ── Response cache ────────────────────────────────────────────────

class TestResponseCache(unittest.TestCase):

    def test_set_get_roundtrip(self):
        c = ResponseCache()
        c.set("k1", {"data": 42})
        self.assertEqual(c.get("k1"), {"data": 42})

    def test_ttl_expiry(self):
        c = ResponseCache(default_ttl=0.05)
        c.set("k1", "value")
        time.sleep(0.1)
        self.assertIsNone(c.get("k1"))

    def test_max_entries_eviction(self):
        c = ResponseCache(max_entries=3)
        for i in range(5):
            c.set(f"k{i}", i)
        self.assertLessEqual(c.size, 3)

    def test_thread_safety(self):
        c = ResponseCache()
        errors = []

        def _writer(idx):
            try:
                for i in range(50):
                    c.set(f"w{idx}_{i}", i)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=_writer, args=(i,))
                   for i in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        self.assertEqual(errors, [])

    def test_invalidate(self):
        c = ResponseCache()
        c.set("k1", "v")
        c.invalidate("k1")
        self.assertIsNone(c.get("k1"))

    def test_clear(self):
        c = ResponseCache()
        c.set("a", 1)
        c.set("b", 2)
        c.clear()
        self.assertEqual(c.size, 0)


if __name__ == "__main__":
    unittest.main()
