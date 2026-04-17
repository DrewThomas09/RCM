"""Tests for the unit-economics value bridge (v2).

Spec §14 invariants this file locks in:

1. Denial reduction has *larger* revenue value under commercial-heavy
   vs Medicare-heavy mix (contract leverage differential).
2. ``days_in_ar`` loads primarily into working capital, not recurring
   EBITDA.
3. ``cost_to_collect`` lands almost entirely as cost savings.
4. ``net_collection_rate`` lands as pure revenue recovery.
5. Coding / CDI levers matter more under DRG-heavy profiles.
6. Self-pay heavy profile amplifies ``bad_debt`` sensitivity.
7. Same improvement → different value under different profiles.
8. Recurring EBITDA and one-time WC release are reported separately.
9. Enterprise value applied to recurring EBITDA only.
10. Provenance tags attached to every lever impact.
"""
from __future__ import annotations

import os
import tempfile
import unittest

from rcm_mc.analysis.packet import (
    DealAnalysisPacket,
    HospitalProfile,
    ObservedMetric,
)
from rcm_mc.analysis.packet_builder import build_analysis_packet
from rcm_mc.finance.reimbursement_engine import (
    PayerClass,
    ReimbursementMethod,
    build_reimbursement_profile,
    compute_revenue_realization_path,
)
from rcm_mc.pe.value_bridge_v2 import (
    BridgeAssumptions,
    LeverImpact,
    RevenueLeakageBreakdown,
    ValueBridgeResult,
    WorkingCapitalEffect,
    compute_value_bridge,
    explain_lever_value,
)
from rcm_mc.portfolio.store import PortfolioStore


# ── Fixtures ─────────────────────────────────────────────────────────

def _profile(mix, beds=400, state="IL"):
    return HospitalProfile(bed_count=beds, region="midwest",
                             state=state, payer_mix=mix)


def _rp(mix, beds=400, **override):
    hp = _profile(mix, beds=beds)
    return build_reimbursement_profile(
        hp, mix, optional_contract_inputs=override or None,
    )


def _default_assumptions(
    *, exit_multiple=10.0, net_revenue=400_000_000, claims=300_000,
) -> BridgeAssumptions:
    return BridgeAssumptions(
        exit_multiple=exit_multiple,
        net_revenue=float(net_revenue),
        claims_volume=int(claims),
    )


def _temp_store():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    s = PortfolioStore(path)
    s.init_db()
    return s, path


# ── Spec §14: profile-dependent value ──────────────────────────────

class TestProfileDependentValue(unittest.TestCase):
    def test_commercial_denial_reduction_exceeds_medicare(self):
        """Same 12→5 denial_rate delta produces larger revenue uplift
        under a commercial-heavy mix than a Medicare-heavy mix, because
        commercial contracts pay more per recovered claim."""
        rp_comm = _rp({"commercial": 0.70, "medicare": 0.20, "medicaid": 0.10})
        rp_med = _rp({"medicare": 0.70, "commercial": 0.20, "medicaid": 0.10})
        a = _default_assumptions()

        r_comm = compute_value_bridge(
            {"denial_rate": 12.0}, {"denial_rate": 5.0},
            rp_comm, a, current_ebitda=32e6,
        )
        r_med = compute_value_bridge(
            {"denial_rate": 12.0}, {"denial_rate": 5.0},
            rp_med, a, current_ebitda=32e6,
        )
        self.assertGreater(
            r_comm.total_recurring_revenue_uplift,
            r_med.total_recurring_revenue_uplift,
        )

    def test_drg_heavy_cmi_lift_exceeds_commercial_cmi_lift(self):
        """CMI is a DRG-mechanism lever — Medicare-heavy mix should
        show a bigger recurring revenue impact for the same CMI delta."""
        rp_drg = _rp({"medicare": 0.70, "commercial": 0.20, "medicaid": 0.10})
        rp_comm = _rp({"commercial": 0.70, "medicare": 0.20, "medicaid": 0.10})
        a = _default_assumptions()
        r_drg = compute_value_bridge(
            {"cmi": 1.50}, {"cmi": 1.60}, rp_drg, a, current_ebitda=32e6,
        )
        r_comm = compute_value_bridge(
            {"cmi": 1.50}, {"cmi": 1.60}, rp_comm, a, current_ebitda=32e6,
        )
        self.assertGreater(
            r_drg.total_recurring_revenue_uplift,
            r_comm.total_recurring_revenue_uplift,
        )

    def test_self_pay_heavy_amplifies_bad_debt_savings(self):
        rp_sp = _rp({"self_pay": 0.30, "commercial": 0.40, "medicaid": 0.30})
        rp_plain = _rp({"commercial": 0.70, "medicare": 0.30})
        a = _default_assumptions()
        r_sp = compute_value_bridge(
            {"bad_debt": 5.0}, {"bad_debt": 3.0},
            rp_sp, a, current_ebitda=20e6,
        )
        r_plain = compute_value_bridge(
            {"bad_debt": 5.0}, {"bad_debt": 3.0},
            rp_plain, a, current_ebitda=20e6,
        )
        self.assertGreater(
            r_sp.total_recurring_cost_savings,
            r_plain.total_recurring_cost_savings,
        )

    def test_capitation_heavy_dampens_denial_value(self):
        """When commercial is ~100% capitated, a denial-rate lever
        produces markedly smaller revenue uplift vs pure FFS commercial."""
        rp_ffs = _rp({"commercial": 1.0})
        rp_cap = _rp(
            {"commercial": 1.0},
            **{"method_distribution_by_payer": {
                PayerClass.COMMERCIAL: {ReimbursementMethod.CAPITATION: 1.0},
            }},
        )
        a = _default_assumptions()
        r_ffs = compute_value_bridge(
            {"denial_rate": 10.0}, {"denial_rate": 5.0},
            rp_ffs, a, current_ebitda=30e6,
        )
        r_cap = compute_value_bridge(
            {"denial_rate": 10.0}, {"denial_rate": 5.0},
            rp_cap, a, current_ebitda=30e6,
        )
        self.assertGreater(
            r_ffs.total_recurring_revenue_uplift,
            r_cap.total_recurring_revenue_uplift,
        )


# ── Spec §14: pathway dominance ────────────────────────────────────

class TestPathwayDominance(unittest.TestCase):
    def test_days_in_ar_dominated_by_working_capital(self):
        rp = _rp({"commercial": 0.5, "medicare": 0.5})
        a = _default_assumptions()
        r = compute_value_bridge(
            {"days_in_ar": 55.0}, {"days_in_ar": 40.0},
            rp, a, current_ebitda=30e6,
        )
        self.assertGreater(
            r.total_one_time_wc_release,
            r.total_recurring_ebitda_delta,
            "days_in_ar should release more one-time WC than recurring EBITDA",
        )
        # And the lever itself tags the pathway.
        lever = r.lever_impacts[0]
        self.assertIn("working_capital", lever.pathway_tags)
        self.assertIsNotNone(lever.working_capital)
        self.assertGreater(lever.working_capital.cash_release_one_time, 0)

    def test_cost_to_collect_is_pure_cost_save(self):
        rp = _rp({"commercial": 0.5, "medicare": 0.5})
        a = _default_assumptions()
        r = compute_value_bridge(
            {"cost_to_collect": 4.0}, {"cost_to_collect": 2.5},
            rp, a, current_ebitda=30e6,
        )
        lever = r.lever_impacts[0]
        self.assertEqual(lever.recurring_revenue_uplift, 0.0)
        self.assertGreater(lever.recurring_cost_savings, 0.0)
        self.assertEqual(lever.one_time_working_capital_release, 0.0)
        self.assertIn("cost", lever.pathway_tags)

    def test_net_collection_rate_is_revenue_dominated(self):
        rp = _rp({"commercial": 0.5, "medicare": 0.5})
        a = _default_assumptions()
        r = compute_value_bridge(
            {"net_collection_rate": 92.0}, {"net_collection_rate": 97.0},
            rp, a, current_ebitda=30e6,
        )
        lever = r.lever_impacts[0]
        self.assertGreater(lever.recurring_revenue_uplift, 0.0)
        self.assertEqual(lever.recurring_cost_savings, 0.0)
        self.assertEqual(lever.one_time_working_capital_release, 0.0)

    def test_dnfb_is_pure_timing(self):
        rp = _rp({"commercial": 0.5, "medicare": 0.5})
        a = _default_assumptions()
        r = compute_value_bridge(
            {"discharged_not_final_billed_days": 10.0},
            {"discharged_not_final_billed_days": 5.0},
            rp, a, current_ebitda=30e6,
        )
        lever = r.lever_impacts[0]
        self.assertGreater(lever.one_time_working_capital_release, 0.0)
        self.assertEqual(lever.recurring_revenue_uplift, 0.0)
        self.assertEqual(lever.recurring_cost_savings, 0.0)


# ── Spec §14: recurring vs one-time separation ─────────────────────

class TestRecurringVsOneTime(unittest.TestCase):
    def test_totals_do_not_mix_recurring_with_one_time(self):
        rp = _rp({"commercial": 0.5, "medicare": 0.5})
        a = _default_assumptions()
        r = compute_value_bridge(
            {"days_in_ar": 55.0, "cost_to_collect": 4.0,
             "net_collection_rate": 92.0},
            {"days_in_ar": 40.0, "cost_to_collect": 3.0,
             "net_collection_rate": 95.0},
            rp, a, current_ebitda=30e6,
        )
        # Recurring aggregate = revenue + cost + financing (not WC release).
        expected_recurring = (
            r.total_recurring_revenue_uplift
            + r.total_recurring_cost_savings
            + r.total_financing_benefit
        )
        self.assertAlmostEqual(
            r.total_recurring_ebitda_delta, expected_recurring, places=2,
        )
        # One-time WC release is reported separately.
        self.assertGreater(r.total_one_time_wc_release, 0)
        self.assertEqual(
            r.cash_release_excluded_from_ev,
            r.total_one_time_wc_release,
        )


# ── Spec §14: EV translation ───────────────────────────────────────

class TestEnterpriseValueTranslation(unittest.TestCase):
    def test_ev_equals_multiple_times_recurring(self):
        rp = _rp({"commercial": 0.5, "medicare": 0.5})
        a = _default_assumptions(exit_multiple=12.0)
        r = compute_value_bridge(
            {"denial_rate": 10.0}, {"denial_rate": 6.0},
            rp, a, current_ebitda=30e6,
        )
        self.assertAlmostEqual(
            r.enterprise_value_from_recurring,
            r.total_recurring_ebitda_delta * 12.0, places=2,
        )
        self.assertEqual(
            r.enterprise_value_delta,
            r.enterprise_value_from_recurring,
        )

    def test_ev_ignores_one_time_wc_release(self):
        """EV scales with recurring EBITDA only. One-time cash release
        lands on ``cash_release_excluded_from_ev`` and does NOT
        inflate EV. Critical IC invariant."""
        rp = _rp({"commercial": 0.5, "medicare": 0.5})
        a = _default_assumptions(exit_multiple=10.0)
        # Days-in-AR is heavy on WC release, light on recurring.
        r = compute_value_bridge(
            {"days_in_ar": 90.0}, {"days_in_ar": 40.0},
            rp, a, current_ebitda=30e6,
        )
        self.assertGreater(r.total_one_time_wc_release, 0)
        # Enterprise value should be much smaller than WC release,
        # because EV = 10 × (small recurring), not 10 × (huge WC).
        self.assertLess(
            r.enterprise_value_delta,
            r.total_one_time_wc_release,
            "EV must not capture one-time WC release",
        )

    def test_multiple_is_explicit_input(self):
        rp = _rp({"commercial": 0.5, "medicare": 0.5})
        a1 = _default_assumptions(exit_multiple=8.0)
        a2 = _default_assumptions(exit_multiple=15.0)
        r1 = compute_value_bridge(
            {"denial_rate": 10.0}, {"denial_rate": 5.0},
            rp, a1, current_ebitda=30e6,
        )
        r2 = compute_value_bridge(
            {"denial_rate": 10.0}, {"denial_rate": 5.0},
            rp, a2, current_ebitda=30e6,
        )
        self.assertAlmostEqual(
            r2.enterprise_value_delta / r1.enterprise_value_delta,
            15.0 / 8.0, places=2,
        )


# ── Spec §14: provenance on every lever ────────────────────────────

class TestProvenanceAttached(unittest.TestCase):
    def test_every_lever_has_provenance(self):
        rp = _rp({"commercial": 0.5, "medicare": 0.5})
        a = _default_assumptions()
        r = compute_value_bridge(
            {"denial_rate": 11.0, "days_in_ar": 55.0, "cost_to_collect": 4.0,
             "cmi": 1.50},
            {"denial_rate": 6.0, "days_in_ar": 40.0, "cost_to_collect": 3.0,
             "cmi": 1.60},
            rp, a, current_ebitda=30e6,
        )
        for lever in r.lever_impacts:
            self.assertTrue(
                lever.provenance,
                f"lever {lever.metric_key} missing provenance",
            )
            # revenue_base tag present on every non-trivial lever.
            self.assertIn("revenue_base", lever.provenance)

    def test_confidence_degraded_by_inferred_assumptions(self):
        """All method distributions default to inferred_from_profile,
        so confidence should come out somewhere under the fully-observed
        ceiling (~0.85)."""
        rp = _rp({"commercial": 0.5, "medicare": 0.5})
        a = _default_assumptions()
        r = compute_value_bridge(
            {"denial_rate": 10.0}, {"denial_rate": 5.0},
            rp, a, current_ebitda=30e6,
        )
        lever = r.lever_impacts[0]
        self.assertLess(lever.confidence, 0.85)

    def test_fallback_profile_marks_low_confidence(self):
        a = _default_assumptions()
        r = compute_value_bridge(
            {"denial_rate": 10.0}, {"denial_rate": 5.0},
            None, a, current_ebitda=30e6,
        )
        lever = r.lever_impacts[0]
        self.assertLess(lever.confidence, 0.85)


# ── Structural checks ──────────────────────────────────────────────

class TestStructure(unittest.TestCase):
    def test_empty_targets_produces_incomplete(self):
        rp = _rp({"commercial": 0.5, "medicare": 0.5})
        a = _default_assumptions()
        r = compute_value_bridge({}, {}, rp, a, current_ebitda=30e6)
        self.assertEqual(r.status, "INCOMPLETE")
        self.assertEqual(r.lever_impacts, [])

    def test_unknown_metric_is_skipped(self):
        rp = _rp({"commercial": 0.5, "medicare": 0.5})
        a = _default_assumptions()
        r = compute_value_bridge(
            {"foo": 1.0, "denial_rate": 10.0},
            {"foo": 2.0, "denial_rate": 5.0},
            rp, a, current_ebitda=30e6,
        )
        metrics = {li.metric_key for li in r.lever_impacts}
        self.assertIn("denial_rate", metrics)
        self.assertNotIn("foo", metrics)

    def test_zero_delta_lever_is_skipped(self):
        rp = _rp({"commercial": 0.5, "medicare": 0.5})
        a = _default_assumptions()
        r = compute_value_bridge(
            {"denial_rate": 10.0}, {"denial_rate": 10.0},
            rp, a, current_ebitda=30e6,
        )
        self.assertEqual(r.lever_impacts, [])

    def test_waterfall_has_anchor_components(self):
        rp = _rp({"commercial": 0.5, "medicare": 0.5})
        a = _default_assumptions()
        r = compute_value_bridge(
            {"denial_rate": 10.0}, {"denial_rate": 5.0},
            rp, a, current_ebitda=30e6,
        )
        kinds = [c.kind for c in r.bridge_components]
        self.assertEqual(kinds[0], "anchor")
        self.assertEqual(kinds[-1], "anchor")

    def test_implementation_ramp_scales_recurring(self):
        rp = _rp({"commercial": 0.5, "medicare": 0.5})
        a_full = _default_assumptions()
        a_half = _default_assumptions()
        a_half.implementation_ramp = 0.5
        r_full = compute_value_bridge(
            {"denial_rate": 10.0}, {"denial_rate": 5.0},
            rp, a_full, current_ebitda=30e6,
        )
        r_half = compute_value_bridge(
            {"denial_rate": 10.0}, {"denial_rate": 5.0},
            rp, a_half, current_ebitda=30e6,
        )
        self.assertAlmostEqual(
            r_half.total_recurring_ebitda_delta * 2.0,
            r_full.total_recurring_ebitda_delta, places=2,
        )


# ── Explanation ────────────────────────────────────────────────────

class TestExplainLeverValue(unittest.TestCase):
    def test_explanation_identifies_dominant_pathway(self):
        rp = _rp({"commercial": 0.5, "medicare": 0.5})
        text = explain_lever_value(
            "days_in_ar", 55.0, 40.0, rp, _default_assumptions(),
        )
        self.assertTrue(
            "cash timing" in text.lower() or "working capital" in text.lower()
        )

    def test_explanation_flags_commercial_tilt_for_denial(self):
        rp = _rp({"commercial": 0.80, "medicare": 0.20})
        text = explain_lever_value(
            "denial_rate", 10.0, 5.0, rp, _default_assumptions(),
        )
        self.assertIn("commercial", text.lower())

    def test_unknown_metric_explanation_is_safe(self):
        rp = _rp({"commercial": 0.5, "medicare": 0.5})
        text = explain_lever_value(
            "not_a_lever", 1.0, 2.0, rp, _default_assumptions(),
        )
        self.assertIn("not modeled", text.lower())


# ── Packet integration ─────────────────────────────────────────────

class TestPacketIntegration(unittest.TestCase):
    def test_builder_attaches_v2_sections(self):
        store, path = _temp_store()
        try:
            store.upsert_deal("vb2", name="V2 Deal", profile={
                "bed_count": 420,
                "payer_mix": {"medicare": 0.5, "commercial": 0.35,
                               "medicaid": 0.15},
            })
            packet = build_analysis_packet(
                store, "vb2", skip_simulation=True,
                observed_override={
                    "denial_rate": ObservedMetric(value=11.0),
                    "days_in_ar": ObservedMetric(value=55.0),
                    "cost_to_collect": ObservedMetric(value=4.0),
                },
                target_metrics={
                    "denial_rate": 6.0, "days_in_ar": 40.0,
                    "cost_to_collect": 2.5,
                },
                financials={
                    "gross_revenue": 1_000_000_000,
                    "net_revenue": 400_000_000,
                    "current_ebitda": 32_000_000,
                    "claims_volume": 300_000,
                    "exit_multiple": 12.0,
                },
            )
            self.assertIsNotNone(packet.value_bridge_result)
            self.assertIsNotNone(packet.leverage_table)
            self.assertIsNotNone(packet.recurring_vs_one_time_summary)
            self.assertIsNotNone(packet.enterprise_value_summary)
            # Leverage table has one row per lever.
            metrics = {row["metric_key"] for row in packet.leverage_table}
            self.assertEqual(
                metrics,
                {"denial_rate", "days_in_ar", "cost_to_collect"},
            )
            # Enterprise value uses the explicit multiple.
            self.assertAlmostEqual(
                packet.enterprise_value_summary["exit_multiple"], 12.0,
            )
        finally:
            try:
                os.unlink(path)
            except OSError:
                pass

    def test_packet_json_roundtrip_preserves_v2_sections(self):
        store, path = _temp_store()
        try:
            store.upsert_deal("vb3", name="V2 RT", profile={
                "bed_count": 400,
                "payer_mix": {"medicare": 0.5, "commercial": 0.5},
            })
            packet = build_analysis_packet(
                store, "vb3", skip_simulation=True,
                observed_override={"denial_rate": ObservedMetric(value=10.0)},
                target_metrics={"denial_rate": 5.0},
                financials={"gross_revenue": 500e6, "net_revenue": 200e6,
                             "current_ebitda": 18e6, "claims_volume": 150_000,
                             "exit_multiple": 10.0},
            )
            payload = packet.to_json()
            restored = DealAnalysisPacket.from_json(payload)
            self.assertIsNotNone(restored.value_bridge_result)
            self.assertAlmostEqual(
                restored.enterprise_value_summary["enterprise_value_delta"],
                packet.enterprise_value_summary["enterprise_value_delta"],
                places=2,
            )
        finally:
            try:
                os.unlink(path)
            except OSError:
                pass


if __name__ == "__main__":
    unittest.main()
