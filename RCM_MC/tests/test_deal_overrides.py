"""Tests for per-deal analyst overrides (Prompt 18).

Invariants locked here:

1. Round-trip: set → get → clear.
2. Validation rejects unknown prefixes, fields, payers, methods.
3. Upsert overwrites by (deal_id, override_key).
4. Value coercion: numbers / strings / bools / lists all survive JSON.
5. `group_overrides` splits flat keys into the five namespaces.
6. ``hash_inputs`` differs when overrides differ.
7. ``get_or_build_packet`` cache misses when an override is added.
8. ``bridge.exit_multiple`` override changes the EV delta.
9. ``payer_mix`` override shifts the v2 bridge output.
10. ``metric_target`` override replaces the target on the fly.
11. ``ramp.<family>.months_to_full`` override shrinks ramp at an
    early evaluation month.
12. ``method_distribution`` override flips the reimbursement profile
    provenance tag to ``ANALYST_OVERRIDE``.
13. CLI: ``rcm-mc pe override {set,list,clear}`` happy path.
14. CLI: invalid key exits non-zero.
15. API: GET + PUT + DELETE cycle over the HTTP server.
16. Persistence survives a store reopen (same file).
17. Overrides land on the packet's ``analyst_overrides`` field.
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

from rcm_mc.analysis.deal_overrides import (
    clear_override,
    get_overrides,
    group_overrides,
    list_overrides,
    set_override,
    validate_override_key,
)
from rcm_mc.analysis.packet import hash_inputs
from rcm_mc.portfolio.store import PortfolioStore


def _tmp_store(seed_deals: tuple = ("d1", "d2")) -> tuple:
    """Fresh SQLite DB + a couple of stub deals.

    Prompt 21 flipped on FK enforcement; ``deal_overrides.deal_id`` now
    references ``deals.deal_id`` so the test fixture seeds the parent
    rows. Any ``deal_id`` a test wants to hit must either be seeded
    here or via the store's ``upsert_deal`` before writing an override.
    """
    tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tf.close()
    store = PortfolioStore(tf.name)
    for deal_id in seed_deals:
        store.upsert_deal(deal_id, name=deal_id)
    return store, tf.name


# ── Validation ─────────────────────────────────────────────────────

class TestValidation(unittest.TestCase):

    def test_reject_unknown_prefix(self):
        with self.assertRaises(ValueError):
            validate_override_key("foo.bar")

    def test_reject_empty_key(self):
        with self.assertRaises(ValueError):
            validate_override_key("")

    def test_reject_bridge_unknown_field(self):
        with self.assertRaises(ValueError):
            validate_override_key("bridge.nonexistent_field")

    def test_accept_bridge_exit_multiple(self):
        validate_override_key("bridge.exit_multiple")  # does not raise

    def test_payer_mix_requires_share_suffix(self):
        with self.assertRaises(ValueError):
            validate_override_key("payer_mix.commercial")

    def test_payer_mix_rejects_unknown_payer(self):
        with self.assertRaises(ValueError):
            validate_override_key("payer_mix.humana_share")

    def test_method_distribution_requires_two_segments(self):
        with self.assertRaises(ValueError):
            validate_override_key("method_distribution.commercial")

    def test_method_distribution_rejects_unknown_method(self):
        with self.assertRaises(ValueError):
            validate_override_key("method_distribution.commercial.unknown")

    def test_ramp_rejects_unknown_family(self):
        with self.assertRaises(ValueError):
            validate_override_key("ramp.bogus_family.months_to_full")

    def test_ramp_rejects_unknown_field(self):
        with self.assertRaises(ValueError):
            validate_override_key("ramp.denial_management.months_to_finish")


# ── CRUD round-trip ────────────────────────────────────────────────

class TestRoundTrip(unittest.TestCase):

    def test_set_and_get(self):
        store, path = _tmp_store()
        try:
            set_override(store, "d1", "bridge.exit_multiple", 11.0, set_by="u")
            self.assertEqual(
                get_overrides(store, "d1"),
                {"bridge.exit_multiple": 11.0},
            )
        finally:
            os.unlink(path)

    def test_upsert_overwrites(self):
        store, path = _tmp_store()
        try:
            set_override(store, "d1", "bridge.exit_multiple", 10.0, set_by="u")
            set_override(store, "d1", "bridge.exit_multiple", 11.5, set_by="u",
                         reason="higher comps")
            overrides = get_overrides(store, "d1")
            self.assertEqual(overrides["bridge.exit_multiple"], 11.5)
            audit = list_overrides(store, "d1")
            self.assertEqual(len(audit), 1)
            self.assertEqual(audit[0]["reason"], "higher comps")
        finally:
            os.unlink(path)

    def test_clear_removes(self):
        store, path = _tmp_store()
        try:
            set_override(store, "d1", "bridge.exit_multiple", 11.0, set_by="u")
            self.assertTrue(clear_override(store, "d1", "bridge.exit_multiple"))
            self.assertEqual(get_overrides(store, "d1"), {})
        finally:
            os.unlink(path)

    def test_clear_missing_returns_false(self):
        store, path = _tmp_store()
        try:
            self.assertFalse(clear_override(store, "d1", "bridge.exit_multiple"))
        finally:
            os.unlink(path)

    def test_list_across_deals(self):
        store, path = _tmp_store()
        try:
            set_override(store, "d1", "bridge.exit_multiple", 11.0, set_by="u")
            set_override(store, "d2", "bridge.exit_multiple", 9.0, set_by="u")
            all_rows = list_overrides(store, None)
            self.assertEqual({r["deal_id"] for r in all_rows}, {"d1", "d2"})
        finally:
            os.unlink(path)

    def test_value_types_survive_json(self):
        store, path = _tmp_store()
        try:
            set_override(store, "d1", "bridge.exit_multiple", 11.0, set_by="u")
            set_override(store, "d1", "metric_target.denial_rate", 6, set_by="u")
            set_override(store, "d1", "payer_mix.commercial_share", 0.55,
                         set_by="u")
            out = get_overrides(store, "d1")
            self.assertIsInstance(out["bridge.exit_multiple"], float)
            self.assertIsInstance(out["metric_target.denial_rate"], int)
            self.assertAlmostEqual(out["payer_mix.commercial_share"], 0.55)
        finally:
            os.unlink(path)

    def test_persistence_survives_reopen(self):
        """Write via one PortfolioStore instance, read via a second —
        simulating a server restart."""
        tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tf.close()
        path = tf.name
        try:
            first_store = PortfolioStore(path)
            first_store.upsert_deal("d1", name="d1")
            set_override(first_store, "d1",
                         "bridge.exit_multiple", 11.0, set_by="u",
                         reason="persistence")
            second_store = PortfolioStore(path)
            self.assertEqual(
                get_overrides(second_store, "d1"),
                {"bridge.exit_multiple": 11.0},
            )
            # Audit row also survives.
            audit = list_overrides(second_store, "d1")
            self.assertEqual(audit[0]["reason"], "persistence")
        finally:
            os.unlink(path)


# ── group_overrides ───────────────────────────────────────────────

class TestGrouping(unittest.TestCase):

    def test_groups_five_namespaces(self):
        flat = {
            "payer_mix.commercial_share": 0.55,
            "method_distribution.commercial.fee_for_service": 0.8,
            "bridge.exit_multiple": 11.0,
            "ramp.denial_management.months_to_full": 9,
            "metric_target.denial_rate": 6.0,
        }
        # (method uses the enum value string — see _VALID_METHODS)
        g = group_overrides(flat)
        self.assertEqual(g["payer_mix"], {"commercial": 0.55})
        self.assertEqual(
            g["method_distribution"],
            {"commercial": {"fee_for_service": 0.8}},
        )
        self.assertEqual(g["bridge"], {"exit_multiple": 11.0})
        self.assertEqual(
            g["ramp"],
            {"denial_management": {"months_to_full": 9}},
        )
        self.assertEqual(g["metric_target"], {"denial_rate": 6.0})

    def test_unknown_prefix_silently_dropped(self):
        g = group_overrides({"foo.bar": 1, "bridge.exit_multiple": 9.0})
        self.assertNotIn("foo", g)
        self.assertEqual(g["bridge"], {"exit_multiple": 9.0})


# ── hash_inputs ───────────────────────────────────────────────────

class TestHashInputs(unittest.TestCase):

    def test_hash_differs_when_overrides_differ(self):
        h1 = hash_inputs(deal_id="d1", observed_metrics={},
                         analyst_overrides={})
        h2 = hash_inputs(deal_id="d1", observed_metrics={},
                         analyst_overrides={"bridge.exit_multiple": 11.0})
        self.assertNotEqual(h1, h2)

    def test_hash_stable_for_same_overrides(self):
        ov = {"bridge.exit_multiple": 10.0,
              "payer_mix.commercial_share": 0.5}
        h1 = hash_inputs(deal_id="d1", observed_metrics={},
                         analyst_overrides=ov)
        h2 = hash_inputs(deal_id="d1", observed_metrics={},
                         analyst_overrides=dict(ov))
        self.assertEqual(h1, h2)


# ── Packet-build integration ──────────────────────────────────────

class TestPacketBuildIntegration(unittest.TestCase):
    """Seed a minimal deal, apply overrides, rebuild the packet, and
    verify the overrides took effect end-to-end."""

    def _seed(self, store: PortfolioStore, deal_id: str) -> None:
        """Register a deal with a payer mix + bed count so the
        reimbursement engine fires."""
        store.upsert_deal(
            deal_id, name="Test Hospital",
            profile={
                "payer_mix": {
                    "commercial": 0.5,
                    "medicare_ffs": 0.3,
                    "medicaid": 0.2,
                },
                "bed_count": 200,
                "state": "TX",
            },
        )

    def _financials(self) -> dict:
        return {
            "gross_revenue": 500_000_000,
            "net_revenue": 400_000_000,
            "current_ebitda": 60_000_000,
            "claims_volume": 150_000,
            "cost_of_capital_pct": 0.08,
            "exit_multiple": 10.0,
        }

    def _build(self, store: PortfolioStore, deal_id: str):
        from rcm_mc.analysis.packet_builder import build_analysis_packet
        return build_analysis_packet(
            store, deal_id,
            skip_simulation=True,
            observed_override={
                "denial_rate": 12.0,
                "days_in_ar": 55.0,
                "net_collection_rate": 94.0,
            },
            financials=self._financials(),
            target_metrics={"denial_rate": 7.0, "days_in_ar": 45.0,
                            "net_collection_rate": 97.0},
        )

    def test_no_overrides_empty_analyst_overrides(self):
        store, path = _tmp_store()
        try:
            self._seed(store, "d1")
            packet = self._build(store, "d1")
            self.assertIsNone(packet.analyst_overrides)
        finally:
            os.unlink(path)

    def test_overrides_land_on_packet(self):
        store, path = _tmp_store()
        try:
            self._seed(store, "d1")
            set_override(store, "d1", "bridge.exit_multiple", 11.5,
                         set_by="u", reason="raised multiple")
            packet = self._build(store, "d1")
            self.assertIsNotNone(packet.analyst_overrides)
            self.assertEqual(
                packet.analyst_overrides["bridge.exit_multiple"], 11.5,
            )
        finally:
            os.unlink(path)

    def test_bridge_exit_multiple_override_changes_ev(self):
        store, path = _tmp_store()
        try:
            self._seed(store, "d1")
            baseline = self._build(store, "d1")
            ev_baseline = (baseline.enterprise_value_summary or {}).get(
                "enterprise_value_from_recurring", 0.0,
            )
            set_override(store, "d1", "bridge.exit_multiple", 13.0,
                         set_by="u")
            overridden = self._build(store, "d1")
            ev_overridden = (overridden.enterprise_value_summary or {}).get(
                "enterprise_value_from_recurring", 0.0,
            )
            self.assertGreater(ev_overridden, ev_baseline)
        finally:
            os.unlink(path)

    def test_payer_mix_override_shifts_v2_bridge(self):
        """Flipping the mix to 100% Medicaid should shrink recurring
        EBITDA because Medicaid leverage is half commercial."""
        store, path = _tmp_store()
        try:
            self._seed(store, "d1")
            baseline = self._build(store, "d1")
            baseline_recurring = (baseline.recurring_vs_one_time_summary or {}).get(
                "total_recurring_ebitda_delta", 0.0,
            )
            set_override(store, "d1", "payer_mix.commercial_share", 0.0,
                         set_by="u")
            set_override(store, "d1", "payer_mix.medicaid_share", 1.0,
                         set_by="u")
            set_override(store, "d1", "payer_mix.medicare_ffs_share", 0.0,
                         set_by="u")
            shifted = self._build(store, "d1")
            shifted_recurring = (shifted.recurring_vs_one_time_summary or {}).get(
                "total_recurring_ebitda_delta", 0.0,
            )
            self.assertLess(shifted_recurring, baseline_recurring)
        finally:
            os.unlink(path)

    def test_metric_target_override_replaces_target(self):
        """A target override should flow into the bridge's lever targets
        and change the recurring EBITDA delta."""
        store, path = _tmp_store()
        try:
            self._seed(store, "d1")
            baseline = self._build(store, "d1")
            baseline_recurring = (baseline.recurring_vs_one_time_summary or {}).get(
                "total_recurring_ebitda_delta", 0.0,
            )
            # Weaker target (denial only drops to 10 instead of 7).
            set_override(store, "d1", "metric_target.denial_rate", 10.0,
                         set_by="u")
            # The builder's explicit target_metrics wins over the
            # stored override by design; clear the conflict by calling
            # the builder without target_metrics for this assertion.
            from rcm_mc.analysis.packet_builder import build_analysis_packet
            weakened = build_analysis_packet(
                store, "d1",
                skip_simulation=True,
                observed_override={"denial_rate": 12.0},
                financials=self._financials(),
            )
            weakened_recurring = (weakened.recurring_vs_one_time_summary or {}).get(
                "total_recurring_ebitda_delta", 0.0,
            )
            # Weaker target → smaller recurring EBITDA delta.
            self.assertGreater(baseline_recurring, weakened_recurring)
        finally:
            os.unlink(path)

    def test_ramp_override_shrinks_early_month(self):
        """Lowering denial_management months_to_full below the default
        (12) should raise the ramp factor at month 6. Going the other
        way (up to 24) should lower it."""
        from rcm_mc.analysis.packet_builder import build_analysis_packet
        store, path = _tmp_store()
        try:
            self._seed(store, "d1")
            fin = dict(self._financials(), evaluation_month=6)

            set_override(store, "d1", "ramp.denial_management.months_to_25_pct",
                         12, set_by="u")
            set_override(store, "d1", "ramp.denial_management.months_to_75_pct",
                         18, set_by="u")
            set_override(store, "d1", "ramp.denial_management.months_to_full",
                         24, set_by="u")
            slow = build_analysis_packet(
                store, "d1", skip_simulation=True,
                observed_override={"denial_rate": 12.0},
                financials=fin,
                target_metrics={"denial_rate": 7.0},
            )
            slow_recurring = (slow.recurring_vs_one_time_summary or {}).get(
                "total_recurring_ebitda_delta", 0.0,
            )

            # Clear the ramp overrides → default 3/6/12 curve.
            for fld in ("months_to_25_pct", "months_to_75_pct",
                        "months_to_full"):
                clear_override(store, "d1", f"ramp.denial_management.{fld}")
            fast = build_analysis_packet(
                store, "d1", skip_simulation=True,
                observed_override={"denial_rate": 12.0},
                financials=fin,
                target_metrics={"denial_rate": 7.0},
            )
            fast_recurring = (fast.recurring_vs_one_time_summary or {}).get(
                "total_recurring_ebitda_delta", 0.0,
            )
            self.assertGreater(fast_recurring, slow_recurring)
        finally:
            os.unlink(path)

    def test_method_distribution_override_flips_provenance(self):
        """A method_distribution override should surface
        ``ANALYST_OVERRIDE`` in the reimbursement profile's provenance."""
        store, path = _tmp_store()
        try:
            self._seed(store, "d1")
            set_override(
                store, "d1",
                "method_distribution.commercial.fee_for_service",
                0.9, set_by="u",
            )
            set_override(
                store, "d1",
                "method_distribution.commercial.drg_prospective_payment",
                0.1, set_by="u",
            )
            packet = self._build(store, "d1")
            rp = packet.reimbursement_profile or {}
            payer_classes = rp.get("payer_classes") or {}
            commercial = payer_classes.get("commercial") or {}
            prov = commercial.get("provenance") or {}
            self.assertEqual(
                prov.get("method_distribution"), "analyst_override",
            )
        finally:
            os.unlink(path)


# ── Cache-miss behavior ───────────────────────────────────────────

class TestCacheInvalidation(unittest.TestCase):
    """Adding an override must force ``get_or_build_packet`` to rebuild
    rather than serve the old cached row."""

    def test_new_override_forces_rebuild(self):
        from rcm_mc.analysis.analysis_store import get_or_build_packet
        store, path = _tmp_store()
        try:
            store.upsert_deal("d1", name="Test",
                              profile={"payer_mix": {"commercial": 1.0},
                                        "bed_count": 200})
            first = get_or_build_packet(
                store, "d1", skip_simulation=True,
                observed_override={"denial_rate": 12.0},
                financials={"net_revenue": 400_000_000,
                             "claims_volume": 150_000,
                             "current_ebitda": 60_000_000,
                             "exit_multiple": 10.0},
                target_metrics={"denial_rate": 7.0},
            )
            set_override(store, "d1", "bridge.exit_multiple", 13.0,
                         set_by="u")
            second = get_or_build_packet(
                store, "d1", skip_simulation=True,
                observed_override={"denial_rate": 12.0},
                financials={"net_revenue": 400_000_000,
                             "claims_volume": 150_000,
                             "current_ebitda": 60_000_000,
                             "exit_multiple": 10.0},
                target_metrics={"denial_rate": 7.0},
            )
            # Different run_ids means we actually rebuilt rather than
            # pulling the cached row.
            self.assertNotEqual(first.run_id, second.run_id)
            self.assertIsNone(first.analyst_overrides)
            self.assertIsNotNone(second.analyst_overrides)
        finally:
            os.unlink(path)


# ── CLI ───────────────────────────────────────────────────────────

class TestCLI(unittest.TestCase):

    def test_set_list_clear_happy_path(self):
        from rcm_mc.pe_cli import main
        tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tf.close()
        db = tf.name
        try:
            PortfolioStore(db).upsert_deal("d1", name="d1")
            rc = main(["override", "--db", db, "set", "d1",
                        "bridge.exit_multiple", "11.0",
                        "--reason", "test"])
            self.assertEqual(rc, 0)
            rc = main(["override", "--db", db, "list", "d1", "--json"])
            self.assertEqual(rc, 0)
            rc = main(["override", "--db", db, "clear", "d1",
                        "bridge.exit_multiple"])
            self.assertEqual(rc, 0)
        finally:
            os.unlink(db)

    def test_invalid_key_exits_non_zero(self):
        from rcm_mc.pe_cli import main
        tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tf.close()
        db = tf.name
        try:
            rc = main(["override", "--db", db, "set", "d1",
                        "not.a.real.prefix", "1"])
            self.assertNotEqual(rc, 0)
        finally:
            os.unlink(db)

    def test_clear_missing_exits_nonzero(self):
        from rcm_mc.pe_cli import main
        tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tf.close()
        db = tf.name
        try:
            rc = main(["override", "--db", db, "clear", "d1",
                        "bridge.exit_multiple"])
            self.assertNotEqual(rc, 0)
        finally:
            os.unlink(db)


# ── HTTP API ──────────────────────────────────────────────────────

class TestAPI(unittest.TestCase):
    """End-to-end on a real HTTP server — PUT upserts, GET reads,
    DELETE removes."""

    def _start(self, db_path: str) -> tuple:
        from rcm_mc.server import build_server
        s = socket.socket(); s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]; s.close()
        server, _ = build_server(port=port, db_path=db_path)
        t = threading.Thread(target=server.serve_forever, daemon=True)
        t.start()
        time.sleep(0.05)
        return server, port

    def test_full_put_get_delete_cycle(self):
        tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tf.close()
        db = tf.name
        try:
            PortfolioStore(db).upsert_deal("d1", name="d1")
            server, port = self._start(db)
            try:
                base = f"http://127.0.0.1:{port}"

                # PUT
                req = urllib.request.Request(
                    f"{base}/api/deals/d1/overrides/bridge.exit_multiple",
                    data=json.dumps(
                        {"value": 11.5, "reason": "API test"}
                    ).encode("utf-8"),
                    headers={"Content-Type": "application/json"},
                    method="PUT",
                )
                with urllib.request.urlopen(req) as r:
                    body = json.loads(r.read().decode())
                    self.assertEqual(body["override_value"], 11.5)
                    self.assertEqual(body["override_key"], "bridge.exit_multiple")

                # GET list
                with urllib.request.urlopen(
                    f"{base}/api/deals/d1/overrides"
                ) as r:
                    body = json.loads(r.read().decode())
                    self.assertEqual(
                        body["overrides"]["bridge.exit_multiple"], 11.5,
                    )

                # GET single key
                with urllib.request.urlopen(
                    f"{base}/api/deals/d1/overrides/bridge.exit_multiple"
                ) as r:
                    body = json.loads(r.read().decode())
                    self.assertEqual(body["override_value"], 11.5)

                # DELETE
                req = urllib.request.Request(
                    f"{base}/api/deals/d1/overrides/bridge.exit_multiple",
                    method="DELETE",
                )
                with urllib.request.urlopen(req) as r:
                    body = json.loads(r.read().decode())
                    self.assertTrue(body["deleted"])

                # GET after DELETE → 404
                with self.assertRaises(urllib.error.HTTPError) as ctx:
                    urllib.request.urlopen(
                        f"{base}/api/deals/d1/overrides/bridge.exit_multiple"
                    )
                self.assertEqual(ctx.exception.code, 404)
            finally:
                server.shutdown()
                server.server_close()
        finally:
            os.unlink(db)

    def test_put_invalid_key_returns_400(self):
        tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tf.close()
        db = tf.name
        try:
            PortfolioStore(db).upsert_deal("d1", name="d1")
            server, port = self._start(db)
            try:
                req = urllib.request.Request(
                    f"http://127.0.0.1:{port}/api/deals/d1/overrides/not.valid",
                    data=json.dumps({"value": 1}).encode("utf-8"),
                    headers={"Content-Type": "application/json"},
                    method="PUT",
                )
                with self.assertRaises(urllib.error.HTTPError) as ctx:
                    urllib.request.urlopen(req)
                self.assertEqual(ctx.exception.code, 400)
            finally:
                server.shutdown()
                server.server_close()
        finally:
            os.unlink(db)


if __name__ == "__main__":
    unittest.main()
