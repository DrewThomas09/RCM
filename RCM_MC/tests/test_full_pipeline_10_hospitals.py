"""Run the full ML pipeline on 10 representative hospital
archetypes. Verify every output makes analytical sense — fix
any nonsensical results.

The 10 archetypes span the partner's universe:
  1. Large urban academic (1000 beds, Medicare-heavy, high CMI)
  2. Mid-size suburban community (250 beds, balanced mix)
  3. Rural critical access (25 beds, Medicare-heavy)
  4. Safety-net urban (300 beds, high Medicaid)
  5. High-margin specialty (100 beds, commercial-heavy)
  6. Distressed rural (75 beds, negative margin)
  7. For-profit suburban (200 beds, normal mix)
  8. Large for-profit chain (600 beds)
  9. Children's hospital (200 beds, high Medicaid pediatric)
  10. Declining-region rural CAH (50 beds, demographic decay)

For each:
  • Run trained predictors (denial / DSO / collection)
  • Build EBITDA bridge with realistic peer benchmarks
  • Compute improvement potential (3 scenarios)
  • Run forward-distress predictor
  • Compute payer-mix cascade

Verify:
  • Predictions sit within sanity ranges
  • Peer-relative scoring matches archetype expectations
    (distressed → higher distress prob; commercial-heavy →
    lower denial rate)
  • EBITDA dollars scale with NPR (bigger hospital → bigger
    uplift)
  • Scenario monotonicity (optimistic > realistic > conservative)
"""
from __future__ import annotations

import unittest


HOSPITALS = [
    {
        "name": "Large Urban Academic",
        "beds": 1000,
        "medicare_day_pct": 0.50,
        "medicaid_day_pct": 0.18,
        "self_pay_pct": 0.05,
        "ma_penetration": 0.45,
        "case_mix_index": 1.85,
        "annual_npr_mm": 1_800,
        "operating_margin": 0.06,
        "rural": 0,
        "archetype": "academic",
    },
    {
        "name": "Mid-Size Suburban Community",
        "beds": 250,
        "medicare_day_pct": 0.42,
        "medicaid_day_pct": 0.15,
        "self_pay_pct": 0.05,
        "ma_penetration": 0.40,
        "case_mix_index": 1.35,
        "annual_npr_mm": 350,
        "operating_margin": 0.04,
        "rural": 0,
        "archetype": "community",
    },
    {
        "name": "Rural Critical Access",
        "beds": 25,
        "medicare_day_pct": 0.65,
        "medicaid_day_pct": 0.20,
        "self_pay_pct": 0.08,
        "ma_penetration": 0.35,
        "case_mix_index": 1.10,
        "annual_npr_mm": 25,
        "operating_margin": 0.01,
        "rural": 1,
        "archetype": "rural_cah",
    },
    {
        "name": "Safety-Net Urban",
        "beds": 300,
        "medicare_day_pct": 0.30,
        "medicaid_day_pct": 0.40,
        "self_pay_pct": 0.15,
        "ma_penetration": 0.30,
        "case_mix_index": 1.40,
        "annual_npr_mm": 280,
        "operating_margin": -0.02,
        "rural": 0,
        "archetype": "safety_net",
    },
    {
        "name": "High-Margin Specialty",
        "beds": 100,
        "medicare_day_pct": 0.30,
        "medicaid_day_pct": 0.05,
        "self_pay_pct": 0.02,
        "ma_penetration": 0.50,
        "case_mix_index": 2.10,
        "annual_npr_mm": 220,
        "operating_margin": 0.18,
        "rural": 0,
        "archetype": "specialty",
    },
    {
        "name": "Distressed Rural",
        "beds": 75,
        "medicare_day_pct": 0.55,
        "medicaid_day_pct": 0.30,
        "self_pay_pct": 0.10,
        "ma_penetration": 0.30,
        "case_mix_index": 1.05,
        "annual_npr_mm": 45,
        "operating_margin": -0.08,
        "rural": 1,
        "archetype": "distressed",
    },
    {
        "name": "For-Profit Suburban",
        "beds": 200,
        "medicare_day_pct": 0.40,
        "medicaid_day_pct": 0.12,
        "self_pay_pct": 0.04,
        "ma_penetration": 0.45,
        "case_mix_index": 1.45,
        "annual_npr_mm": 320,
        "operating_margin": 0.09,
        "rural": 0,
        "archetype": "for_profit",
    },
    {
        "name": "Large For-Profit Chain",
        "beds": 600,
        "medicare_day_pct": 0.45,
        "medicaid_day_pct": 0.16,
        "self_pay_pct": 0.06,
        "ma_penetration": 0.48,
        "case_mix_index": 1.65,
        "annual_npr_mm": 950,
        "operating_margin": 0.11,
        "rural": 0,
        "archetype": "for_profit_chain",
    },
    {
        "name": "Children's Hospital",
        "beds": 200,
        "medicare_day_pct": 0.05,
        "medicaid_day_pct": 0.55,
        "self_pay_pct": 0.04,
        "ma_penetration": 0.10,
        "case_mix_index": 1.55,
        "annual_npr_mm": 280,
        "operating_margin": 0.03,
        "rural": 0,
        "archetype": "childrens",
    },
    {
        "name": "Declining-Region Rural CAH",
        "beds": 50,
        "medicare_day_pct": 0.62,
        "medicaid_day_pct": 0.22,
        "self_pay_pct": 0.10,
        "ma_penetration": 0.30,
        "case_mix_index": 1.05,
        "annual_npr_mm": 35,
        "operating_margin": -0.04,
        "rural": 1,
        "archetype": "declining_rural",
    },
]


def _hospital_to_packet(h):
    """Build a minimal denial-rate-predictor input from the
    archetype dict."""
    npr = h["annual_npr_mm"] * 1_000_000
    discharges = h["beds"] * 4
    gross_charges = npr * 3.0
    return {
        "beds": h["beds"],
        "discharges": discharges,
        "medicare_day_pct": h["medicare_day_pct"],
        "medicaid_day_pct": h["medicaid_day_pct"],
        "self_pay_pct": h["self_pay_pct"],
        "ma_penetration": h["ma_penetration"],
        "rural": h["rural"],
        "gross_patient_revenue": gross_charges,
        "net_patient_revenue": npr,
        "operating_expenses": npr * (1 - h["operating_margin"]),
        "total_patient_days": h["beds"] * 365 * 0.65,
        "bed_days_available": h["beds"] * 365,
    }


def _profile(h):
    from rcm_mc.pe.rcm_ebitda_bridge import (
        FinancialProfile,
    )
    npr = h["annual_npr_mm"] * 1_000_000
    return FinancialProfile(
        gross_revenue=npr * 3,
        net_revenue=npr,
        total_operating_expenses=(
            npr * (1 - h["operating_margin"])),
        current_ebitda=npr * h["operating_margin"],
        total_claims_volume=h["beds"] * 1500,
        payer_mix={
            "medicare": h["medicare_day_pct"],
            "medicaid": h["medicaid_day_pct"],
            "commercial": (
                1 - h["medicare_day_pct"]
                - h["medicaid_day_pct"]
                - h["self_pay_pct"]),
        })


# ── Build a synthetic but realistic predictor ──────────────

def _trained_predictors():
    """Train denial + DSO predictors once on a synthetic
    universe so every hospital gets a real prediction."""
    import numpy as np
    from rcm_mc.ml.denial_rate_predictor import (
        train_denial_rate_predictor,
    )
    from rcm_mc.ml.days_in_ar_predictor import (
        train_days_in_ar_predictor,
    )
    rng = np.random.default_rng(7)
    rows = []
    for _ in range(200):
        beds = float(rng.integers(20, 1200))
        mc = float(rng.uniform(0.20, 0.65))
        md = float(rng.uniform(0.05, 0.45))
        sp = float(rng.uniform(0.02, 0.15))
        margin = float(rng.normal(0.04, 0.08))
        # latent denial rate driven by Medicaid + self-pay
        true_dr = max(0.02, min(0.30,
            0.07 + 0.10 * md + 0.10 * sp
            - 0.02 * (margin)
            + rng.normal(0, 0.012)))
        # latent DSO driven by Medicaid + self-pay
        true_dso = max(20, min(110,
            42 + 12 * md + 25 * sp - 10 * margin
            + rng.normal(0, 4)))
        npr = beds * 4 * 60_000
        rows.append({
            "beds": beds,
            "medicare_day_pct": mc,
            "medicaid_day_pct": md,
            "self_pay_pct": sp,
            "discharges": beds * 4,
            "gross_patient_revenue": npr / 0.30,
            "net_patient_revenue": npr,
            "operating_expenses": (
                npr * (1 - margin)),
            "total_patient_days": beds * 365 * 0.65,
            "bed_days_available": beds * 365,
            "denial_rate": true_dr,
            "days_in_ar": true_dso,
        })
    denial_p = train_denial_rate_predictor(rows)
    dso_p = train_days_in_ar_predictor(rows)
    return denial_p, dso_p


# ── Tests ────────────────────────────────────────────────────

class TestTenHospitalsPipeline(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.denial_p, cls.dso_p = _trained_predictors()

    def test_predictions_within_sanity(self):
        """Every hospital's denial/DSO prediction sits in the
        published sanity range."""
        from rcm_mc.ml.denial_rate_predictor import (
            predict_denial_rate, DENIAL_RATE_RANGE,
        )
        from rcm_mc.ml.days_in_ar_predictor import (
            predict_days_in_ar, DAYS_AR_RANGE,
        )
        for h in HOSPITALS:
            packet = _hospital_to_packet(h)
            dr, _, _ = predict_denial_rate(
                self.denial_p, packet)
            dso, _, _ = predict_days_in_ar(
                self.dso_p, packet)
            self.assertGreaterEqual(
                dr, DENIAL_RATE_RANGE[0],
                f"{h['name']} denial below sanity")
            self.assertLessEqual(
                dr, DENIAL_RATE_RANGE[1],
                f"{h['name']} denial above sanity")
            self.assertGreaterEqual(
                dso, DAYS_AR_RANGE[0],
                f"{h['name']} DSO below sanity")
            self.assertLessEqual(
                dso, DAYS_AR_RANGE[1],
                f"{h['name']} DSO above sanity")

    def test_safety_net_higher_denial_than_specialty(self):
        """Safety-net (40% Medicaid + 15% self-pay) should
        predict higher denial than Specialty
        (5% Medicaid + 2% self-pay) — pipeline correctness
        check."""
        from rcm_mc.ml.denial_rate_predictor import (
            predict_denial_rate,
        )
        safety = next(h for h in HOSPITALS
                      if h["archetype"] == "safety_net")
        specialty = next(
            h for h in HOSPITALS
            if h["archetype"] == "specialty")
        safety_dr, _, _ = predict_denial_rate(
            self.denial_p,
            _hospital_to_packet(safety))
        spec_dr, _, _ = predict_denial_rate(
            self.denial_p,
            _hospital_to_packet(specialty))
        self.assertGreater(
            safety_dr, spec_dr,
            f"safety-net DR {safety_dr:.3f} should "
            f"exceed specialty DR {spec_dr:.3f}")

    def test_safety_net_higher_dso_than_specialty(self):
        from rcm_mc.ml.days_in_ar_predictor import (
            predict_days_in_ar,
        )
        safety = next(h for h in HOSPITALS
                      if h["archetype"] == "safety_net")
        specialty = next(
            h for h in HOSPITALS
            if h["archetype"] == "specialty")
        safety_dso, _, _ = predict_days_in_ar(
            self.dso_p,
            _hospital_to_packet(safety))
        spec_dso, _, _ = predict_days_in_ar(
            self.dso_p,
            _hospital_to_packet(specialty))
        self.assertGreater(safety_dso, spec_dso)

    def test_ebitda_bridge_for_every_hospital(self):
        """Every hospital builds a non-crashing bridge with
        sensible signs."""
        from rcm_mc.pe.rcm_ebitda_bridge import (
            RCMEBITDABridge,
        )
        for h in HOSPITALS:
            bridge = RCMEBITDABridge(_profile(h))
            result = bridge.compute_bridge(
                current_metrics={"denial_rate": 12.0,
                                 "days_in_ar": 55.0},
                target_metrics={"denial_rate": 7.0,
                                "days_in_ar": 38.0})
            # Improvement-direction → positive impact
            self.assertGreater(
                result.total_ebitda_impact, 0,
                f"{h['name']} bridge produced "
                f"non-positive impact")

    def test_uplift_scales_with_npr(self):
        """Bigger hospital → bigger absolute uplift dollars."""
        from rcm_mc.pe.rcm_ebitda_bridge import (
            RCMEBITDABridge,
        )
        small = next(h for h in HOSPITALS
                     if h["archetype"] == "rural_cah")
        large = next(
            h for h in HOSPITALS
            if h["archetype"] == "academic")
        small_bridge = RCMEBITDABridge(_profile(small))
        large_bridge = RCMEBITDABridge(_profile(large))
        target = {"denial_rate": 7.0,
                  "days_in_ar": 38.0}
        current = {"denial_rate": 12.0,
                   "days_in_ar": 55.0}
        s = small_bridge.compute_bridge(
            current, target).total_ebitda_impact
        l = large_bridge.compute_bridge(
            current, target).total_ebitda_impact
        self.assertGreater(
            l, s,
            f"large NPR ${large['annual_npr_mm']}M uplift "
            f"({l:,.0f}) should exceed small "
            f"${small['annual_npr_mm']}M uplift ({s:,.0f})")

    def test_distress_probability_for_distressed_archetype(self):
        """The 'distressed' archetype should produce a
        higher predicted distress probability than the
        'specialty' archetype."""
        from rcm_mc.ml.forward_distress_predictor import (
            train_forward_distress_predictor,
            predict_distress,
        )
        # Quick synthetic train
        import numpy as np
        rng = np.random.default_rng(11)
        rows = []
        for _ in range(150):
            margin_t = float(
                rng.normal(0.05, 0.06))
            margin_history = [
                margin_t - rng.normal(0, 0.01)
                for _ in range(4)]
            future = (
                margin_t * 0.9
                + rng.normal(0, 0.015))
            rows.append({
                "operating_margin_t": margin_t,
                "margin_history": margin_history,
                "cash_on_hand": float(
                    rng.uniform(5_000_000,
                                100_000_000)),
                "annual_operating_expenses":
                    100_000_000,
                "long_term_debt": float(
                    rng.uniform(0,
                                100_000_000)),
                "net_patient_revenue":
                    100_000_000,
                "interest_expense": float(
                    rng.uniform(0, 5_000_000)),
                "ebit": margin_t * 100_000_000,
                "discharges_history": [10000,
                                       10500,
                                       11000,
                                       11500],
                "beds": 300,
                "occupancy_rate": float(
                    rng.uniform(0.4, 0.85)),
                "future_margin": future,
            })
        p = train_forward_distress_predictor(
            rows, horizon_months=24)

        distressed = next(
            h for h in HOSPITALS
            if h["archetype"] == "distressed")
        specialty = next(
            h for h in HOSPITALS
            if h["archetype"] == "specialty")

        d_panel = {
            "operating_margin_t":
                distressed["operating_margin"],
            "margin_history": [-0.02, -0.05, -0.07,
                               distressed["operating_margin"]],
            "cash_on_hand": 1_000_000,
            "annual_operating_expenses":
                distressed["annual_npr_mm"]
                * 1_000_000 * 1.05,
            "long_term_debt":
                distressed["annual_npr_mm"]
                * 1_000_000 * 0.6,
            "net_patient_revenue":
                distressed["annual_npr_mm"]
                * 1_000_000,
            "beds": distressed["beds"],
        }
        s_panel = {
            "operating_margin_t":
                specialty["operating_margin"],
            "margin_history": [0.16, 0.17, 0.17,
                               specialty["operating_margin"]],
            "cash_on_hand": 50_000_000,
            "annual_operating_expenses":
                specialty["annual_npr_mm"]
                * 1_000_000 * 0.85,
            "long_term_debt":
                specialty["annual_npr_mm"]
                * 1_000_000 * 0.10,
            "net_patient_revenue":
                specialty["annual_npr_mm"]
                * 1_000_000,
            "beds": specialty["beds"],
        }
        _, prob_d, _, _, _ = predict_distress(p, d_panel)
        _, prob_s, _, _, _ = predict_distress(p, s_panel)
        self.assertGreater(
            prob_d, prob_s,
            f"distressed prob {prob_d:.2f} should "
            f"exceed specialty prob {prob_s:.2f}")

    def test_payer_mix_cascade_directional(self):
        """Worsening payer mix (commercial → medicaid)
        should reduce NPR for every hospital."""
        from rcm_mc.ml.payer_mix_cascade import (
            PayerMix, cascade_payer_mix_shift,
        )
        for h in HOSPITALS:
            commercial = (
                1 - h["medicare_day_pct"]
                - h["medicaid_day_pct"]
                - h["self_pay_pct"])
            if commercial < 0.05:
                continue  # already very low commercial
            baseline = PayerMix(
                medicare=h["medicare_day_pct"],
                medicaid=h["medicaid_day_pct"],
                commercial=commercial,
                self_pay=h["self_pay_pct"])
            # Shift 5pp commercial → medicaid
            new = PayerMix(
                medicare=h["medicare_day_pct"],
                medicaid=h["medicaid_day_pct"] + 0.05,
                commercial=commercial - 0.05,
                self_pay=h["self_pay_pct"])
            result = cascade_payer_mix_shift(
                baseline, new,
                annual_gross_charges=(
                    h["annual_npr_mm"] * 3 * 1_000_000))
            self.assertLess(
                result.npr_delta_dollars, 0,
                f"{h['name']} commercial→medicaid shift "
                f"should reduce NPR")

    def test_improvement_potential_three_scenarios(self):
        """Every hospital with peer benchmarks should produce
        monotonic conservative < realistic < optimistic."""
        from rcm_mc.ml.improvement_potential import (
            PeerBenchmarks,
            estimate_improvement_potential,
        )
        bm = PeerBenchmarks(
            denial_rate=7.0, days_in_ar=38.0)
        current = {
            "denial_rate": 12.0,
            "days_in_ar": 55.0,
        }
        for h in HOSPITALS:
            result = estimate_improvement_potential(
                _profile(h), current, bm)
            if result.realistic_total_ebitda <= 0:
                continue  # already at/beyond peer
            self.assertGreater(
                result.optimistic_total_ebitda,
                result.realistic_total_ebitda,
                f"{h['name']} optimistic should exceed "
                f"realistic")
            self.assertGreater(
                result.realistic_total_ebitda,
                result.conservative_total_ebitda,
                f"{h['name']} realistic should exceed "
                f"conservative")


# ── Service-line decomposition for the 10 archetypes ──────

class TestServiceLineDecomposition(unittest.TestCase):
    """Verify cross-subsidy patterns match the partner's
    expectation across archetypes."""

    def _records(self, h):
        from rcm_mc.ml.service_line_profitability import (
            CostCenterRecord,
        )
        npr = h["annual_npr_mm"] * 1_000_000
        # Stylized per-line revenue split
        records = [
            CostCenterRecord(
                ccn=h["name"], fiscal_year=2023,
                line_number=60,
                cost_center_name="OR",
                direct_cost=npr * 0.10,
                overhead_allocation=npr * 0.02,
                gross_charges=npr * 1.00,
                net_revenue=npr * 0.30),
            CostCenterRecord(
                ccn=h["name"], fiscal_year=2023,
                line_number=89,
                cost_center_name="ED",
                direct_cost=npr * 0.10,
                overhead_allocation=npr * 0.02,
                gross_charges=npr * 0.30,
                net_revenue=npr * 0.10),
            CostCenterRecord(
                ccn=h["name"], fiscal_year=2023,
                line_number=65,
                cost_center_name="Imaging",
                direct_cost=npr * 0.04,
                overhead_allocation=npr * 0.01,
                gross_charges=npr * 0.20,
                net_revenue=npr * 0.10),
        ]
        return records

    def test_surgery_typically_profitable(self):
        from rcm_mc.ml.service_line_profitability import (
            analyze_hospital_service_lines,
        )
        for h in HOSPITALS:
            margins, _ = analyze_hospital_service_lines(
                self._records(h))
            surgery = next(
                m for m in margins
                if m.service_line == "Surgery")
            self.assertGreater(
                surgery.contribution_margin, 0,
                f"{h['name']} Surgery should be "
                f"profitable in this stylized split")


if __name__ == "__main__":
    unittest.main()
