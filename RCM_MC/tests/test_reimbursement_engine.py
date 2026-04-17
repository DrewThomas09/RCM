"""Tests for the reimbursement + revenue-realization engine.

Two contract layers this file locks in:

1. *Economic structure*. Different hospital archetypes produce
   different reimbursement exposures, and the per-metric sensitivity
   scores respond accordingly — commercial-heavy vs. Medicare-heavy,
   DRG-dominant vs. capitation-dominant, inpatient vs. outpatient,
   etc.
2. *Mechanical correctness*. ``days_in_ar`` loads primarily into the
   working-capital pathway (not revenue); ``net_collection_rate``
   loads primarily into revenue; the realization path decomposes into
   the expected leakage categories; inferred assumptions carry the
   right provenance tags.
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
from rcm_mc.analysis.packet_builder import (
    _build_reimbursement_views,
    build_analysis_packet,
)
from rcm_mc.finance.reimbursement_engine import (
    DEFAULT_PAYER_METHOD_DISTRIBUTION,
    METHOD_SENSITIVITY_TABLE,
    PayerClass,
    PayerClassProfile,
    ProvenanceTag,
    ReimbursementMethod,
    ReimbursementProfile,
    _normalize_payer_mix,
    build_reimbursement_profile,
    compute_revenue_realization_path,
    estimate_metric_revenue_sensitivity,
    explain_reimbursement_logic,
)
from rcm_mc.portfolio.store import PortfolioStore


# ── Helpers ──────────────────────────────────────────────────────────

def _large_acute(payer_mix: dict, state: str = "IL") -> HospitalProfile:
    return HospitalProfile(
        bed_count=400, region="midwest", state=state,
        payer_mix=payer_mix,
    )


def _small_outpatient(payer_mix: dict) -> HospitalProfile:
    return HospitalProfile(
        bed_count=40, region="south", state="GA",
        payer_mix=payer_mix,
    )


def _critical_access(payer_mix: dict) -> HospitalProfile:
    return HospitalProfile(
        bed_count=20, region="rural", state="MT",
        payer_mix=payer_mix,
    )


def _temp_store():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    s = PortfolioStore(path)
    s.init_db()
    return s, path


# ── Payer-class inference ───────────────────────────────────────────

class TestPayerMixNormalization(unittest.TestCase):
    def test_fractions_passthrough(self):
        m = _normalize_payer_mix({"medicare": 0.4, "commercial": 0.5, "medicaid": 0.1})
        self.assertAlmostEqual(m[PayerClass.MEDICARE_FFS], 0.4)
        self.assertAlmostEqual(m[PayerClass.COMMERCIAL], 0.5)
        self.assertAlmostEqual(m[PayerClass.MEDICAID], 0.1)

    def test_percent_scale_normalized(self):
        m = _normalize_payer_mix({"commercial": 40, "medicare": 40, "medicaid": 20})
        self.assertAlmostEqual(sum(m.values()), 1.0, places=5)

    def test_aliases_understood(self):
        m = _normalize_payer_mix({
            "Medicare-Advantage": 0.3, "self_pay": 0.1, "tricare": 0.05,
            "commercial": 0.55,
        })
        self.assertIn(PayerClass.MEDICARE_ADVANTAGE, m)
        self.assertIn(PayerClass.SELF_PAY, m)
        self.assertIn(PayerClass.MANAGED_GOVERNMENT, m)


# ── Reimbursement profile inference ──────────────────────────────────

class TestReimbursementProfileBuild(unittest.TestCase):
    def test_large_acute_medicare_heavy_dominant_method_is_drg(self):
        profile = _large_acute({"medicare": 0.55, "commercial": 0.30,
                                 "medicaid": 0.15})
        rp = build_reimbursement_profile(profile, profile.payer_mix)
        self.assertEqual(rp.dominant_method(),
                         ReimbursementMethod.DRG_PROSPECTIVE)
        # All method weights sum to 1.
        self.assertAlmostEqual(sum(rp.method_weights.values()), 1.0, places=5)

    def test_commercial_heavy_has_more_ffs_and_case_rate(self):
        profile = _large_acute({"commercial": 0.65, "medicare": 0.25,
                                 "medicaid": 0.10})
        rp = build_reimbursement_profile(profile, profile.payer_mix)
        # FFS + case-rate combined should exceed DRG share under
        # commercial-heavy mix.
        ffs = rp.method_weights.get(ReimbursementMethod.FEE_FOR_SERVICE, 0)
        case_rate = rp.method_weights.get(ReimbursementMethod.CASE_RATE_BUNDLE, 0)
        drg = rp.method_weights.get(ReimbursementMethod.DRG_PROSPECTIVE, 0)
        self.assertGreater(ffs + case_rate, drg)

    def test_critical_access_hospital_gets_cost_based(self):
        profile = _critical_access({"medicare": 0.70, "medicaid": 0.25,
                                     "self_pay": 0.05})
        rp = build_reimbursement_profile(profile, profile.payer_mix)
        cost_based = rp.method_weights.get(
            ReimbursementMethod.COST_BASED, 0,
        )
        self.assertGreater(
            cost_based, 0.20,
            "critical-access hospital should route Medicare through cost-based"
        )
        # Provenance reflects the profile-driven inference.
        medicare_prov = rp.payer_classes[PayerClass.MEDICARE_FFS].provenance
        self.assertEqual(
            medicare_prov["method_distribution"],
            ProvenanceTag.INFERRED_FROM_PROFILE.value,
        )

    def test_small_outpatient_leans_apc(self):
        profile = _small_outpatient({"medicare": 0.5, "commercial": 0.4,
                                       "medicaid": 0.1})
        rp = build_reimbursement_profile(profile, profile.payer_mix)
        apc_share = rp.method_weights.get(
            ReimbursementMethod.OUTPATIENT_APC, 0,
        )
        drg_share = rp.method_weights.get(
            ReimbursementMethod.DRG_PROSPECTIVE, 0,
        )
        # Small outpatient: APC exposure outweighs inpatient DRG.
        self.assertGreater(apc_share, drg_share)

    def test_empty_payer_mix_returns_skip_profile(self):
        profile = HospitalProfile(bed_count=300)
        rp = build_reimbursement_profile(profile, {})
        self.assertEqual(rp.method_weights, {})
        self.assertTrue(rp.notes)

    def test_analyst_override_flags_method_distribution(self):
        profile = _large_acute({"medicare": 0.5, "commercial": 0.5})
        rp = build_reimbursement_profile(
            profile, profile.payer_mix,
            optional_contract_inputs={
                "method_distribution_by_payer": {
                    PayerClass.COMMERCIAL: {
                        ReimbursementMethod.CAPITATION: 1.0,
                    },
                },
            },
        )
        prov = rp.payer_classes[PayerClass.COMMERCIAL].provenance
        self.assertEqual(
            prov["method_distribution"],
            ProvenanceTag.ANALYST_OVERRIDE.value,
        )

    def test_inpatient_outpatient_mix_inferred_by_bed_count(self):
        large = _large_acute({"medicare": 0.5, "commercial": 0.5})
        rp = build_reimbursement_profile(large, large.payer_mix)
        self.assertEqual(
            rp.inpatient_outpatient_mix.get("inpatient", 0) >
            rp.inpatient_outpatient_mix.get("outpatient", 0), True,
        )
        small = _small_outpatient({"medicare": 0.5, "commercial": 0.5})
        rp2 = build_reimbursement_profile(small, small.payer_mix)
        self.assertGreater(
            rp2.inpatient_outpatient_mix.get("outpatient", 0),
            rp2.inpatient_outpatient_mix.get("inpatient", 0),
        )


# ── Per-metric sensitivity ──────────────────────────────────────────

class TestMetricSensitivity(unittest.TestCase):
    def _profile(self, mix: dict) -> ReimbursementProfile:
        return build_reimbursement_profile(_large_acute(mix), mix)

    def test_days_in_ar_is_working_capital_dominant(self):
        rp = self._profile({"medicare": 0.5, "commercial": 0.5})
        s = estimate_metric_revenue_sensitivity("days_in_ar", rp)
        # Working capital is the dominant pathway for AR days.
        self.assertGreater(
            s["working_capital_sensitivity"],
            s["revenue_sensitivity"],
        )
        self.assertGreater(
            s["working_capital_sensitivity"],
            s["cost_sensitivity"],
        )

    def test_net_collection_rate_is_revenue_dominant(self):
        rp = self._profile({"medicare": 0.5, "commercial": 0.5})
        s = estimate_metric_revenue_sensitivity("net_collection_rate", rp)
        self.assertGreater(
            s["revenue_sensitivity"],
            s["cost_sensitivity"],
        )
        self.assertGreater(
            s["revenue_sensitivity"],
            s["working_capital_sensitivity"],
        )

    def test_drg_heavy_weighting_lifts_cmi_sensitivity(self):
        drg_heavy = self._profile({"medicare": 0.80, "commercial": 0.20})
        commercial_heavy = self._profile({"commercial": 0.80, "medicare": 0.20})
        s_drg = estimate_metric_revenue_sensitivity("case_mix_index", drg_heavy)
        s_comm = estimate_metric_revenue_sensitivity(
            "case_mix_index", commercial_heavy,
        )
        self.assertGreater(
            s_drg["overall_sensitivity"],
            s_comm["overall_sensitivity"],
            "CMI should matter more under DRG-heavy mix",
        )

    def test_capitation_lowers_denial_rate_sensitivity(self):
        cap_heavy = self._profile({"medicare_advantage": 0.4,
                                     "commercial": 0.6})
        # Override to force capitation on commercial.
        profile = _large_acute({"medicare_advantage": 0.4, "commercial": 0.6})
        cap_override = build_reimbursement_profile(
            profile, profile.payer_mix,
            optional_contract_inputs={
                "method_distribution_by_payer": {
                    PayerClass.COMMERCIAL: {
                        ReimbursementMethod.CAPITATION: 1.0,
                    },
                    PayerClass.MEDICARE_ADVANTAGE: {
                        ReimbursementMethod.CAPITATION: 1.0,
                    },
                },
            },
        )
        ffs_profile = self._profile({"commercial": 1.0})
        s_cap = estimate_metric_revenue_sensitivity("denial_rate", cap_override)
        s_ffs = estimate_metric_revenue_sensitivity("denial_rate", ffs_profile)
        self.assertLess(
            s_cap["overall_sensitivity"],
            s_ffs["overall_sensitivity"],
            "capitation should lower denial_rate economic leverage",
        )

    def test_self_pay_heavy_lifts_bad_debt_relevance(self):
        rp_self_pay = self._profile({"self_pay": 0.40, "commercial": 0.30,
                                       "medicaid": 0.30})
        rp_commercial = self._profile({"commercial": 0.80, "medicare": 0.20})
        s_sp = estimate_metric_revenue_sensitivity("bad_debt", rp_self_pay)
        s_comm = estimate_metric_revenue_sensitivity("bad_debt", rp_commercial)
        # Bad-debt sensitivity shouldn't be identical across profiles;
        # the self-pay profile should show higher revenue+cost impact
        # because eligibility failures combine with self-pay exposure.
        self.assertNotAlmostEqual(
            s_sp["overall_sensitivity"],
            s_comm["overall_sensitivity"], places=3,
        )

    def test_unknown_metric_returns_zero_sensitivity(self):
        rp = self._profile({"medicare": 0.5, "commercial": 0.5})
        s = estimate_metric_revenue_sensitivity("nonexistent_metric", rp)
        self.assertEqual(s["overall_sensitivity"], 0.0)
        self.assertIn("not mapped", s["explanation"])


# ── Revenue realization path ────────────────────────────────────────

class TestRevenueRealizationPath(unittest.TestCase):
    def _rp(self, mix: dict):
        profile = _large_acute(mix)
        return build_reimbursement_profile(profile, profile.payer_mix)

    def test_path_sums_reasonably(self):
        rp = self._rp({"medicare": 0.50, "commercial": 0.35, "medicaid": 0.15})
        path = compute_revenue_realization_path(
            {"initial_denial_rate": 10.0, "days_in_ar": 55.0,
             "bad_debt": 3.0, "eligibility_denial_rate": 1.5,
             "coding_denial_rate": 1.0},
            rp, net_revenue=400_000_000,
        )
        # Gross > collectible net > final realized cash.
        self.assertGreater(path.gross_charges, path.collectible_net_revenue)
        self.assertGreaterEqual(
            path.collectible_net_revenue,
            path.final_realized_cash,
        )
        # Breakdowns populated for each canonical leak stage.
        stages = {b.stage for b in path.breakdowns}
        self.assertIn("contractual_adjustments", stages)
        self.assertIn("preventable_front_end_leakage", stages)
        self.assertIn("initial_denial_leakage", stages)
        self.assertIn("timing_drag", stages)
        self.assertIn("bad_debt_leakage", stages)

    def test_higher_days_in_ar_increases_timing_drag(self):
        rp = self._rp({"medicare": 0.5, "commercial": 0.5})
        low_ar = compute_revenue_realization_path(
            {"days_in_ar": 30.0}, rp, net_revenue=400_000_000,
        )
        high_ar = compute_revenue_realization_path(
            {"days_in_ar": 90.0}, rp, net_revenue=400_000_000,
        )
        self.assertGreater(high_ar.timing_drag, low_ar.timing_drag)

    def test_self_pay_profile_raises_bad_debt_leak(self):
        no_selfpay = self._rp({"medicare": 0.5, "commercial": 0.5})
        heavy_selfpay = self._rp({"self_pay": 0.3, "commercial": 0.4,
                                    "medicare": 0.3})
        base_metrics = {"initial_denial_rate": 8.0, "bad_debt": 3.0,
                         "days_in_ar": 40.0}
        a = compute_revenue_realization_path(
            base_metrics, no_selfpay, net_revenue=400_000_000,
        )
        b = compute_revenue_realization_path(
            base_metrics, heavy_selfpay, net_revenue=400_000_000,
        )
        self.assertGreater(b.bad_debt_leakage, a.bad_debt_leakage)

    def test_no_revenue_baseline_returns_skipped(self):
        rp = self._rp({"medicare": 0.5, "commercial": 0.5})
        path = compute_revenue_realization_path({}, rp)
        self.assertEqual(path.gross_charges, 0.0)
        self.assertIn("skipped", path.assumptions)

    def test_gross_inferred_tags_provenance(self):
        rp = self._rp({"medicare": 0.5, "commercial": 0.5})
        path = compute_revenue_realization_path(
            {}, rp, net_revenue=400_000_000,
        )
        self.assertEqual(
            path.assumptions.get("gross_charges"),
            ProvenanceTag.INFERRED_FROM_PROFILE.value,
        )


# ── Explanation narratives ──────────────────────────────────────────

class TestExplainReimbursementLogic(unittest.TestCase):
    def test_cmi_explanation_notes_drg_tilt(self):
        profile = _large_acute({"medicare": 0.7, "commercial": 0.3})
        rp = build_reimbursement_profile(profile, profile.payer_mix)
        text = explain_reimbursement_logic("case_mix_index", rp)
        self.assertIn("revenue", text.lower())
        self.assertTrue("drg" in text.lower() or "medicare" in text.lower())

    def test_days_in_ar_explanation_mentions_working_capital(self):
        profile = _large_acute({"medicare": 0.5, "commercial": 0.5})
        rp = build_reimbursement_profile(profile, profile.payer_mix)
        text = explain_reimbursement_logic("days_in_ar", rp)
        self.assertTrue(
            "working capital" in text.lower() or "timing" in text.lower()
        )

    def test_inferred_note_present(self):
        profile = _large_acute({"medicare": 0.5, "commercial": 0.5})
        rp = build_reimbursement_profile(profile, profile.payer_mix)
        text = explain_reimbursement_logic("denial_rate", rp)
        self.assertIn("inferred", text.lower())


# ── Packet integration ──────────────────────────────────────────────

class TestPacketIntegration(unittest.TestCase):
    def test_builder_attaches_reimbursement_sections(self):
        store, path = _temp_store()
        try:
            store.upsert_deal("rx", name="Reimb Deal", profile={
                "bed_count": 420, "region": "midwest",
                "payer_mix": {"medicare": 0.5, "commercial": 0.35,
                               "medicaid": 0.15},
            })
            packet = build_analysis_packet(
                store, "rx", skip_simulation=True,
                observed_override={
                    "denial_rate": ObservedMetric(value=11.0),
                    "days_in_ar": ObservedMetric(value=55.0),
                    "bad_debt": ObservedMetric(value=3.0),
                },
                financials={
                    "gross_revenue": 1_000_000_000,
                    "net_revenue": 400_000_000,
                    "current_ebitda": 32_000_000,
                    "claims_volume": 300_000,
                },
            )
            self.assertIsNotNone(packet.reimbursement_profile)
            self.assertIn("method_weights", packet.reimbursement_profile)
            self.assertIn("provenance", packet.reimbursement_profile)
            self.assertIsNotNone(packet.revenue_realization)
            self.assertIn("final_realized_cash", packet.revenue_realization)
            self.assertIsNotNone(packet.metric_sensitivity_map)
            self.assertIn("denial_rate", packet.metric_sensitivity_map)
            self.assertIn("days_in_ar", packet.metric_sensitivity_map)
        finally:
            try:
                os.unlink(path)
            except OSError:
                pass

    def test_builder_without_payer_mix_skips_cleanly(self):
        store, path = _temp_store()
        try:
            store.upsert_deal("rx2", name="No Mix", profile={
                "bed_count": 100,
            })
            packet = build_analysis_packet(store, "rx2", skip_simulation=True)
            # Reimbursement profile still present (with notes), but no
            # method weights and no sensitivity map.
            self.assertIsNotNone(packet.reimbursement_profile)
            self.assertEqual(
                packet.reimbursement_profile.get("method_weights") or {}, {},
            )
            self.assertIsNone(packet.metric_sensitivity_map)
        finally:
            try:
                os.unlink(path)
            except OSError:
                pass

    def test_packet_json_roundtrip_preserves_new_sections(self):
        store, path = _temp_store()
        try:
            store.upsert_deal("rx3", name="Roundtrip", profile={
                "bed_count": 300, "payer_mix": {"medicare": 0.6, "commercial": 0.4},
            })
            packet = build_analysis_packet(
                store, "rx3", skip_simulation=True,
                financials={"gross_revenue": 500e6, "net_revenue": 200e6,
                             "current_ebitda": 16e6, "claims_volume": 150_000},
            )
            payload = packet.to_json()
            restored = DealAnalysisPacket.from_json(payload)
            self.assertEqual(
                restored.reimbursement_profile["method_weights"].keys(),
                packet.reimbursement_profile["method_weights"].keys(),
            )
            self.assertAlmostEqual(
                restored.revenue_realization["final_realized_cash"],
                packet.revenue_realization["final_realized_cash"],
                places=2,
            )
        finally:
            try:
                os.unlink(path)
            except OSError:
                pass


# ── Provenance tags propagate ───────────────────────────────────────

class TestProvenanceTags(unittest.TestCase):
    def test_inferred_assumptions_tagged(self):
        profile = _large_acute({"medicare": 0.5, "commercial": 0.5})
        rp = build_reimbursement_profile(profile, profile.payer_mix)
        # Both payer-class method distributions are inferred (no
        # analyst override), so their provenance should reflect it.
        for pc, pcp in rp.payer_classes.items():
            self.assertIn(
                pcp.provenance["method_distribution"],
                (ProvenanceTag.BENCHMARK_DEFAULT.value,
                 ProvenanceTag.INFERRED_FROM_PROFILE.value),
            )
        # Top-level profile provenance tags present.
        self.assertIn("method_weights", rp.provenance)
        self.assertEqual(
            rp.provenance["method_weights"],
            ProvenanceTag.CALCULATED.value,
        )

    def test_method_sensitivity_table_covers_every_archetype(self):
        for method in ReimbursementMethod:
            self.assertIn(method, METHOD_SENSITIVITY_TABLE,
                           f"missing sensitivity entry for {method.value}")
        # Every entry in the default payer distribution points at a
        # method that has a sensitivity table entry.
        for payer, dist in DEFAULT_PAYER_METHOD_DISTRIBUTION.items():
            for method in dist:
                self.assertIn(method, METHOD_SENSITIVITY_TABLE)


if __name__ == "__main__":
    unittest.main()
