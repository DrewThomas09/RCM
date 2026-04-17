"""Tests for cross-lever dependency adjustment in the v2 bridge.

Spec §Prompt 15 invariants locked here:

1. Topological order respects `eligibility_denial_rate →
   denial_rate → net_collection_rate` (parents before children).
2. Adjusting denial_rate *after* eligibility_denial_rate reduces
   denial_rate's revenue-recovery component.
3. Independent levers (cost_to_collect, case_mix_index) produce zero
   adjustment.
4. Total adjusted bridge ≤ total unadjusted bridge (no inflation).
5. Old packets without `dependency_audit` still deserialize.
6. Audit rows explain the full delta between raw and adjusted totals.
7. Magnitude-hint mapping: strong → 0.60, moderate → 0.35, weak → 0.15.
8. Only `recurring_revenue_uplift` is adjusted; cost savings and WC
   release are untouched.
9. `_MAX_TOTAL_OVERLAP = 0.75` caps heavily-linked children.
10. v1 bridge output is not adjusted by the dependency walker.
"""
from __future__ import annotations

import copy
import os
import tempfile
import unittest

from rcm_mc.analysis.packet import (
    DealAnalysisPacket,
    HospitalProfile,
    ObservedMetric,
)
from rcm_mc.analysis.packet_builder import build_analysis_packet
from rcm_mc.domain.econ_ontology import (
    CausalGraph,
    MechanismEdge,
    MetricDefinition,
    causal_graph,
)
from rcm_mc.finance.reimbursement_engine import build_reimbursement_profile
from rcm_mc.pe.lever_dependency import (
    DependencyAuditRow,
    _MAGNITUDE_OVERLAP,
    _MAX_TOTAL_OVERLAP,
    _topological_order,
    apply_dependency_adjustment,
    topological_lever_order,
    walk_dependency,
)
from rcm_mc.pe.value_bridge_v2 import (
    BridgeAssumptions,
    LeverImpact,
    compute_value_bridge,
)
from rcm_mc.portfolio.store import PortfolioStore


# ── Fixtures ─────────────────────────────────────────────────────────

def _rp(mix, beds=400):
    hp = HospitalProfile(bed_count=beds, payer_mix=mix)
    return build_reimbursement_profile(hp, mix)


def _assumptions(**overrides):
    base = {"net_revenue": 400_000_000, "claims_volume": 300_000}
    base.update(overrides)
    return BridgeAssumptions(**base)


def _fake_lever(key: str, *, revenue=1_000_000, cost=100_000,
                wc=0, fin=0) -> LeverImpact:
    return LeverImpact(
        metric_key=key,
        current_value=10.0, target_value=5.0,
        recurring_revenue_uplift=float(revenue),
        recurring_cost_savings=float(cost),
        one_time_working_capital_release=float(wc),
        ongoing_financing_benefit=float(fin),
        recurring_ebitda_delta=float(revenue + cost + fin),
        provenance={"revenue_base": "observed"},
    )


def _temp_store():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    s = PortfolioStore(path)
    s.init_db()
    return s, path


# ── Topological order ─────────────────────────────────────────────

class TestTopologicalOrder(unittest.TestCase):
    def test_order_respects_denial_chain(self):
        keys = ["net_collection_rate", "denial_rate",
                "eligibility_denial_rate"]
        order = topological_lever_order(keys)
        # eligibility_denial_rate is a parent of denial_rate; must come first.
        self.assertLess(
            order.index("eligibility_denial_rate"),
            order.index("denial_rate"),
        )
        # denial_rate is a parent of net_collection_rate; must come first.
        self.assertLess(
            order.index("denial_rate"),
            order.index("net_collection_rate"),
        )

    def test_order_preserves_unrelated_levers(self):
        keys = ["cost_to_collect", "case_mix_index", "days_in_ar"]
        order = topological_lever_order(keys)
        # All three present; relative order doesn't matter (no edges among them).
        self.assertEqual(set(order), set(keys))

    def test_unknown_keys_placed_at_end(self):
        keys = ["denial_rate", "not_a_real_metric", "eligibility_denial_rate"]
        order = topological_lever_order(keys)
        # Ontology metrics first; unknown last.
        self.assertEqual(
            order.index("not_a_real_metric"),
            len(order) - 1,
        )

    def test_empty_input(self):
        self.assertEqual(topological_lever_order([]), [])

    def test_cycle_fallback_does_not_lose_levers(self):
        """If a synthetic graph has a cycle, _topological_order returns
        [] and the lever order helper falls back to placing every
        lever in the input-preserving tail — nothing is silently lost."""
        fake_graph = CausalGraph(
            nodes={
                "a": MetricDefinition(
                    metric_key="a", display_name="a",
                    domain=None, subdomain="", economic_mechanism="",
                    directionality=None, financial_pathway=None,
                    confidence_class=None, reimbursement_sensitivity=None,
                ),
                "b": MetricDefinition(
                    metric_key="b", display_name="b",
                    domain=None, subdomain="", economic_mechanism="",
                    directionality=None, financial_pathway=None,
                    confidence_class=None, reimbursement_sensitivity=None,
                ),
            },
            edges=[
                MechanismEdge(parent="a", child="b"),
                MechanismEdge(parent="b", child="a"),   # cycle
            ],
        )
        order = topological_lever_order(["a", "b"], graph=fake_graph)
        self.assertEqual(set(order), {"a", "b"})


# ── Magnitude hint mapping ────────────────────────────────────────

class TestMagnitudeMapping(unittest.TestCase):
    def test_strong_moderate_weak_values(self):
        self.assertAlmostEqual(_MAGNITUDE_OVERLAP["strong"], 0.60)
        self.assertAlmostEqual(_MAGNITUDE_OVERLAP["moderate"], 0.35)
        self.assertAlmostEqual(_MAGNITUDE_OVERLAP["weak"], 0.15)


# ── apply_dependency_adjustment unit-level ────────────────────────

class TestApplyAdjustment(unittest.TestCase):
    def test_no_upstream_is_zero_adjustment(self):
        lever = _fake_lever("days_in_ar", revenue=0, cost=0, fin=500_000)
        already = {}
        adjusted, audit = apply_dependency_adjustment(
            "days_in_ar", lever, already,
        )
        self.assertEqual(adjusted.recurring_ebitda_delta,
                          lever.recurring_ebitda_delta)
        self.assertEqual(audit.adjustment_pct, 0.0)
        self.assertEqual(audit.upstream_levers, [])

    def test_parent_in_already_captured_reduces_revenue(self):
        # denial_rate has eligibility_denial_rate as a parent.
        parent = _fake_lever("eligibility_denial_rate", revenue=200_000)
        child = _fake_lever("denial_rate", revenue=5_000_000)
        already = {"eligibility_denial_rate": parent}
        adjusted, audit = apply_dependency_adjustment(
            "denial_rate", child, already,
        )
        self.assertLess(
            adjusted.recurring_revenue_uplift,
            child.recurring_revenue_uplift,
        )
        self.assertIn("eligibility_denial_rate", audit.upstream_levers)
        self.assertGreater(audit.adjustment_pct, 0)

    def test_adjustment_only_touches_revenue_component(self):
        parent = _fake_lever("eligibility_denial_rate", revenue=100_000)
        child = _fake_lever(
            "denial_rate", revenue=1_000_000, cost=300_000, fin=50_000, wc=800_000,
        )
        adjusted, _audit = apply_dependency_adjustment(
            "denial_rate", child, {"eligibility_denial_rate": parent},
        )
        # Cost, WC release, financing untouched.
        self.assertEqual(
            adjusted.recurring_cost_savings, child.recurring_cost_savings,
        )
        self.assertEqual(
            adjusted.one_time_working_capital_release,
            child.one_time_working_capital_release,
        )
        self.assertEqual(
            adjusted.ongoing_financing_benefit,
            child.ongoing_financing_benefit,
        )

    def test_ebitda_delta_recomputed_consistently(self):
        parent = _fake_lever("eligibility_denial_rate", revenue=100_000)
        child = _fake_lever(
            "denial_rate", revenue=1_000_000, cost=300_000, fin=50_000,
        )
        adjusted, _audit = apply_dependency_adjustment(
            "denial_rate", child, {"eligibility_denial_rate": parent},
        )
        expected = (
            adjusted.recurring_revenue_uplift
            + adjusted.recurring_cost_savings
            + adjusted.ongoing_financing_benefit
        )
        self.assertAlmostEqual(adjusted.recurring_ebitda_delta, expected)

    def test_multiple_upstream_sum_capped_at_max(self):
        """denial_rate has several parents. If all fire, total overlap
        must respect _MAX_TOTAL_OVERLAP = 0.75."""
        upstream_keys = [
            "eligibility_denial_rate", "auth_denial_rate",
            "coding_denial_rate", "medical_necessity_denial_rate",
            "timely_filing_denial_rate", "clean_claim_rate",
        ]
        already = {
            k: _fake_lever(k, revenue=100_000) for k in upstream_keys
        }
        child = _fake_lever("denial_rate", revenue=1_000_000)
        adjusted, audit = apply_dependency_adjustment(
            "denial_rate", child, already,
        )
        self.assertLessEqual(audit.adjustment_pct / 100.0,
                              _MAX_TOTAL_OVERLAP + 1e-9)
        # Revenue still positive (not zeroed).
        self.assertGreater(adjusted.recurring_revenue_uplift, 0)

    def test_adjusted_lever_records_provenance_flag(self):
        parent = _fake_lever("eligibility_denial_rate", revenue=100_000)
        child = _fake_lever("denial_rate", revenue=1_000_000)
        adjusted, _audit = apply_dependency_adjustment(
            "denial_rate", child, {"eligibility_denial_rate": parent},
        )
        self.assertIn("dependency_adjusted", adjusted.provenance)
        self.assertIn("eligibility_denial_rate",
                       adjusted.provenance["dependency_adjusted"])


# ── walk_dependency end-to-end ─────────────────────────────────────

class TestWalkDependency(unittest.TestCase):
    def test_independent_levers_are_untouched(self):
        levers = [
            _fake_lever("cost_to_collect", revenue=0, cost=2_000_000),
            _fake_lever("case_mix_index", revenue=3_000_000, cost=0),
        ]
        adjusted, audit = walk_dependency(levers)
        for i, li in enumerate(adjusted):
            self.assertAlmostEqual(
                li.recurring_ebitda_delta,
                levers[i].recurring_ebitda_delta,
            )
        for row in audit:
            self.assertEqual(row.adjustment_pct, 0.0)

    def test_parent_child_pair_shrinks_child(self):
        levers = [
            _fake_lever("eligibility_denial_rate", revenue=500_000),
            _fake_lever("denial_rate", revenue=5_000_000),
        ]
        adjusted, audit = walk_dependency(levers)
        # Child adjusted down.
        child_adj = next(
            li for li in adjusted if li.metric_key == "denial_rate"
        )
        child_raw = levers[1]
        self.assertLess(
            child_adj.recurring_ebitda_delta,
            child_raw.recurring_ebitda_delta,
        )
        # Parent untouched.
        parent_adj = next(
            li for li in adjusted if li.metric_key == "eligibility_denial_rate"
        )
        self.assertAlmostEqual(
            parent_adj.recurring_ebitda_delta,
            levers[0].recurring_ebitda_delta,
        )

    def test_total_adjusted_never_exceeds_raw(self):
        """Monotonicity — adjustments only shrink, never inflate."""
        levers = [
            _fake_lever("eligibility_denial_rate", revenue=500_000),
            _fake_lever("coding_denial_rate", revenue=300_000),
            _fake_lever("denial_rate", revenue=5_000_000),
            _fake_lever("net_collection_rate", revenue=3_000_000),
        ]
        adjusted, _audit = walk_dependency(levers)
        raw_total = sum(li.recurring_ebitda_delta for li in levers)
        adj_total = sum(li.recurring_ebitda_delta for li in adjusted)
        self.assertLessEqual(adj_total, raw_total + 1e-6)

    def test_audit_rows_preserve_order_of_input(self):
        levers = [
            _fake_lever("denial_rate", revenue=5_000_000),
            _fake_lever("eligibility_denial_rate", revenue=500_000),
        ]
        adjusted, audit = walk_dependency(levers)
        self.assertEqual(
            [li.metric_key for li in adjusted],
            ["denial_rate", "eligibility_denial_rate"],
        )
        self.assertEqual(
            [row.lever for row in audit],
            ["denial_rate", "eligibility_denial_rate"],
        )

    def test_audit_rows_explain_delta(self):
        """Sum of (raw − adjusted) across audit rows equals the total
        reduction in recurring_ebitda_delta. Partners can reconcile
        the audit trail by arithmetic."""
        levers = [
            _fake_lever("eligibility_denial_rate", revenue=500_000),
            _fake_lever("denial_rate", revenue=5_000_000),
        ]
        adjusted, audit = walk_dependency(levers)
        raw_total = sum(li.recurring_ebitda_delta for li in levers)
        adj_total = sum(li.recurring_ebitda_delta for li in adjusted)
        delta_from_audit = sum(row.raw_impact - row.adjusted_impact
                                for row in audit)
        self.assertAlmostEqual(delta_from_audit, raw_total - adj_total, places=2)

    def test_empty_input_returns_empty_outputs(self):
        adjusted, audit = walk_dependency([])
        self.assertEqual(adjusted, [])
        self.assertEqual(audit, [])

    def test_single_lever_no_adjustment(self):
        lever = _fake_lever("denial_rate", revenue=1_000_000)
        adjusted, audit = walk_dependency([lever])
        self.assertAlmostEqual(
            adjusted[0].recurring_ebitda_delta,
            lever.recurring_ebitda_delta,
        )
        self.assertEqual(audit[0].adjustment_pct, 0.0)


# ── Integration with compute_value_bridge ─────────────────────────

class TestComputeValueBridgeDependency(unittest.TestCase):
    def _rp_and_a(self):
        return (
            _rp({"medicare": 0.6, "commercial": 0.3, "medicaid": 0.1}),
            _assumptions(),
        )

    def test_bridge_result_carries_dependency_audit(self):
        rp, a = self._rp_and_a()
        r = compute_value_bridge(
            {"denial_rate": 12.0, "cost_to_collect": 4.0},
            {"denial_rate": 6.0, "cost_to_collect": 3.0},
            rp, a, current_ebitda=30e6,
        )
        self.assertEqual(len(r.dependency_audit), len(r.lever_impacts))
        # Every lever has an audit row.
        lever_keys = {li.metric_key for li in r.lever_impacts}
        audit_keys = {row.lever for row in r.dependency_audit}
        self.assertEqual(lever_keys, audit_keys)

    def test_overlapping_levers_produce_meaningful_shrinkage(self):
        """With both eligibility_denial_rate AND denial_rate fired,
        the adjusted total must be materially below the raw total."""
        rp, a = self._rp_and_a()
        r = compute_value_bridge(
            {"eligibility_denial_rate": 1.5, "denial_rate": 12.0},
            {"eligibility_denial_rate": 0.8, "denial_rate": 5.0},
            rp, a, current_ebitda=32e6,
        )
        self.assertGreater(
            r.raw_total_recurring_ebitda_delta,
            r.total_recurring_ebitda_delta,
        )
        shrinkage = (
            1 - r.total_recurring_ebitda_delta
            / r.raw_total_recurring_ebitda_delta
        )
        # Shrinkage should be at least several percent but not total.
        self.assertGreater(shrinkage, 0.05)
        self.assertLess(shrinkage, 0.75)

    def test_independent_levers_no_shrinkage(self):
        """cost_to_collect and case_mix_index aren't causally linked in
        the ontology; both raw and adjusted totals should match."""
        rp, a = self._rp_and_a()
        r = compute_value_bridge(
            {"cost_to_collect": 4.0, "cmi": 1.50},
            {"cost_to_collect": 3.0, "cmi": 1.60},
            rp, a, current_ebitda=30e6,
        )
        self.assertAlmostEqual(
            r.raw_total_recurring_ebitda_delta,
            r.total_recurring_ebitda_delta, places=3,
        )
        for row in r.dependency_audit:
            self.assertEqual(row.adjustment_pct, 0.0)

    def test_enterprise_value_uses_adjusted_recurring_total(self):
        rp, a = self._rp_and_a()
        r = compute_value_bridge(
            {"eligibility_denial_rate": 1.5, "denial_rate": 12.0},
            {"eligibility_denial_rate": 0.8, "denial_rate": 5.0},
            rp, a, current_ebitda=32e6,
        )
        self.assertAlmostEqual(
            r.enterprise_value_from_recurring,
            r.total_recurring_ebitda_delta * a.exit_multiple,
            places=2,
        )
        # EV must reflect the ADJUSTED total, not the raw one.
        self.assertNotAlmostEqual(
            r.enterprise_value_from_recurring,
            r.raw_total_recurring_ebitda_delta * a.exit_multiple,
            places=2,
        )


# ── JSON roundtrip ────────────────────────────────────────────────

class TestRoundtripBackCompat(unittest.TestCase):
    def test_packet_roundtrip_preserves_audit(self):
        rp = _rp({"medicare": 0.5, "commercial": 0.5})
        a = _assumptions()
        r = compute_value_bridge(
            {"eligibility_denial_rate": 1.5, "denial_rate": 12.0},
            {"eligibility_denial_rate": 0.8, "denial_rate": 5.0},
            rp, a, current_ebitda=30e6,
        )
        d = r.to_dict()
        self.assertIn("dependency_audit", d)
        self.assertIn("raw_total_recurring_ebitda_delta", d)
        self.assertGreater(len(d["dependency_audit"]), 0)

    def test_old_packet_without_audit_still_loads(self):
        """Packets serialized before Prompt 15 don't have
        dependency_audit. The field defaults to an empty list so
        from_json on an old payload still succeeds."""
        store, path = _temp_store()
        try:
            store.upsert_deal("t", name="T", profile={
                "bed_count": 400,
                "payer_mix": {"medicare": 0.5, "commercial": 0.5},
            })
            packet = build_analysis_packet(
                store, "t", skip_simulation=True,
                observed_override={"denial_rate": ObservedMetric(value=11.0)},
                target_metrics={"denial_rate": 6.0},
                financials={
                    "gross_revenue": 1_000_000_000,
                    "net_revenue": 400_000_000,
                    "current_ebitda": 32_000_000,
                    "claims_volume": 300_000,
                },
            )
            # Strip the new fields to simulate an old payload.
            payload = packet.to_dict()
            vb = payload.get("value_bridge_result") or {}
            vb.pop("dependency_audit", None)
            vb.pop("raw_total_recurring_ebitda_delta", None)
            vb.pop("raw_total_recurring_revenue_uplift", None)
            payload["value_bridge_result"] = vb
            restored = DealAnalysisPacket.from_dict(payload)
            # No exception; packet loads with empty audit.
            self.assertIsNotNone(restored.value_bridge_result)
        finally:
            try:
                os.unlink(path)
            except OSError:
                pass


# ── Packet-builder surface ─────────────────────────────────────────

class TestPacketSurface(unittest.TestCase):
    def test_recurring_vs_one_time_exposes_audit(self):
        store, path = _temp_store()
        try:
            store.upsert_deal("t2", name="T2", profile={
                "bed_count": 400,
                "payer_mix": {"medicare": 0.5, "commercial": 0.5},
            })
            packet = build_analysis_packet(
                store, "t2", skip_simulation=True,
                observed_override={
                    "eligibility_denial_rate": ObservedMetric(value=1.5),
                    "denial_rate": ObservedMetric(value=12.0),
                },
                target_metrics={
                    "eligibility_denial_rate": 0.8,
                    "denial_rate": 5.0,
                },
                financials={
                    "gross_revenue": 1_000_000_000,
                    "net_revenue": 400_000_000,
                    "current_ebitda": 32_000_000,
                    "claims_volume": 300_000,
                },
            )
            self.assertIsNotNone(packet.recurring_vs_one_time_summary)
            summary = packet.recurring_vs_one_time_summary
            self.assertIn("raw_total_recurring_ebitda_delta", summary)
            self.assertIn("dependency_audit", summary)
        finally:
            try:
                os.unlink(path)
            except OSError:
                pass


# ── v1 bridge untouched ───────────────────────────────────────────

class TestV1BridgeUntouched(unittest.TestCase):
    def test_v1_bridge_still_matches_research_band(self):
        """Dependency walk is v2-only. The v1 bridge's 29 research-band
        calibration tests should still pass — no cross-lever shrinkage
        applied there. Quick spot-check here (full suite runs the 29)."""
        from rcm_mc.pe.rcm_ebitda_bridge import (
            FinancialProfile, RCMEBITDABridge,
        )
        fp = FinancialProfile(
            gross_revenue=1_000_000_000, net_revenue=400_000_000,
            current_ebitda=32_000_000, total_claims_volume=300_000,
            cost_per_reworked_claim=30.0,
            payer_mix={"medicare": 0.4, "commercial": 0.45, "medicaid": 0.15},
        )
        b = RCMEBITDABridge(fp)
        r = b.compute_bridge({"denial_rate": 12.0}, {"denial_rate": 5.0})
        imp = next(m for m in r.per_metric_impacts
                   if m.metric_key == "denial_rate")
        # Research band $8-15M on $400M NPR.
        self.assertGreaterEqual(imp.ebitda_impact, 8_000_000)
        self.assertLessEqual(imp.ebitda_impact, 15_000_000)


if __name__ == "__main__":
    unittest.main()
