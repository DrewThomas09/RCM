"""Tests for per-lever implementation ramp curves (Prompt 17).

Invariants locked here:

1. Zero-month → 0.0 ramp for every family.
2. Month >= months_to_full → 1.0 ramp.
3. Monotonically increasing.
4. Annual averages Y1 < Y2 < Y3.
5. Payer-renegotiation Y1 < denial-management Y1 (slower initiatives
   lag at Year-1).
6. At month 36 (the default) the bridge output matches pre-ramp
   behavior — confirmed by identity against an explicit ``ramp=1.0``
   apply.
7. ``apply_ramp_to_lever`` leaves ``one_time_working_capital_release``
   untouched and scales recurring flows in lock-step.
8. ``BridgeAssumptions`` round-trips through ``to_dict`` → ``from_dict``
   even when ``ramp_curves`` is absent (backward compat) or present.
9. ``compute_value_bridge`` populates ``per_lever_ramp_factors`` on
   every run and sets ``ramp_applied`` only when at least one lever
   got scaled.
10. v2 Monte Carlo ``hold_months`` threading: lowering hold_months
    lowers the recurring EBITDA distribution.
11. Custom RampCurve overrides override the default family.
12. Invalid RampCurve (months_to_25 >= months_to_75) raises.
"""
from __future__ import annotations

import json
import math
import unittest

from rcm_mc.finance.reimbursement_engine import (
    PayerClass,
    PayerClassProfile,
    ReimbursementMethod,
    ReimbursementProfile,
)
from rcm_mc.pe.ramp_curves import (
    DEFAULT_RAMP_CURVES,
    METRIC_TO_FAMILY,
    RampCurve,
    annual_ramp_factors,
    apply_ramp_to_lever,
    curve_for_metric,
    family_for_metric,
    ramp_factor,
    resolve_ramp_curves,
)
from rcm_mc.pe.value_bridge_v2 import (
    BridgeAssumptions,
    LeverImpact,
    compute_value_bridge,
)


# ── Fixtures ───────────────────────────────────────────────────────

def _profile() -> ReimbursementProfile:
    return ReimbursementProfile(
        payer_classes={
            PayerClass.COMMERCIAL: PayerClassProfile(
                payer_class=PayerClass.COMMERCIAL, revenue_share=1.0,
                method_distribution={ReimbursementMethod.FEE_FOR_SERVICE: 1.0},
            ),
        },
        method_weights={ReimbursementMethod.FEE_FOR_SERVICE: 1.0},
    )


# ── Endpoint math ──────────────────────────────────────────────────

class TestRampFactorEndpoints(unittest.TestCase):

    def test_month_zero_is_zero_for_every_family(self):
        for curve in DEFAULT_RAMP_CURVES.values():
            self.assertEqual(ramp_factor(curve, 0), 0.0)

    def test_negative_month_clamps_to_zero(self):
        for curve in DEFAULT_RAMP_CURVES.values():
            self.assertEqual(ramp_factor(curve, -5), 0.0)

    def test_months_to_full_is_one(self):
        for curve in DEFAULT_RAMP_CURVES.values():
            self.assertEqual(ramp_factor(curve, curve.months_to_full), 1.0)

    def test_beyond_full_is_still_one(self):
        for curve in DEFAULT_RAMP_CURVES.values():
            self.assertEqual(
                ramp_factor(curve, curve.months_to_full + 60), 1.0,
            )


class TestRampFactorShape(unittest.TestCase):

    def test_monotonically_increasing(self):
        for curve in DEFAULT_RAMP_CURVES.values():
            prev = -1e-9
            for m in range(0, curve.months_to_full + 1):
                v = ramp_factor(curve, m)
                self.assertGreaterEqual(v, prev)
                prev = v

    def test_hits_roughly_25_pct_at_m25(self):
        for curve in DEFAULT_RAMP_CURVES.values():
            v = ramp_factor(curve, curve.months_to_25_pct)
            # Logistic-with-renormalization won't be exactly 0.25 at
            # m25 — the renormalization shifts it slightly. Check a
            # reasonable band.
            self.assertGreater(v, 0.10)
            self.assertLess(v, 0.40)

    def test_hits_roughly_75_pct_at_m75(self):
        for curve in DEFAULT_RAMP_CURVES.values():
            v = ramp_factor(curve, curve.months_to_75_pct)
            self.assertGreater(v, 0.55)
            self.assertLess(v, 0.90)


# ── Annual averages ────────────────────────────────────────────────

class TestAnnualRampFactors(unittest.TestCase):

    def test_year_over_year_monotone(self):
        for curve in DEFAULT_RAMP_CURVES.values():
            annual = annual_ramp_factors(curve, 3)
            for prev, nxt in zip(annual, annual[1:]):
                self.assertLessEqual(prev, nxt)

    def test_payer_renego_y1_slower_than_denial_mgmt_y1(self):
        denial_y1 = annual_ramp_factors(
            DEFAULT_RAMP_CURVES["denial_management"], 3,
        )[0]
        payer_y1 = annual_ramp_factors(
            DEFAULT_RAMP_CURVES["payer_renegotiation"], 3,
        )[0]
        self.assertGreater(denial_y1, payer_y1)

    def test_ar_collections_fastest_y1(self):
        ar_y1 = annual_ramp_factors(
            DEFAULT_RAMP_CURVES["ar_collections"], 3,
        )[0]
        cdi_y1 = annual_ramp_factors(
            DEFAULT_RAMP_CURVES["cdi_coding"], 3,
        )[0]
        self.assertGreater(ar_y1, cdi_y1)

    def test_year_3_near_full_for_all_default_families(self):
        for curve in DEFAULT_RAMP_CURVES.values():
            y3 = annual_ramp_factors(curve, 3)[-1]
            # All default curves finish inside 24 months, so Y3 (mo
            # 25-36) sits at 1.0.
            self.assertAlmostEqual(y3, 1.0, places=3)


# ── apply_ramp_to_lever ────────────────────────────────────────────

class TestApplyRampToLever(unittest.TestCase):

    def _sample_impact(self) -> LeverImpact:
        return LeverImpact(
            metric_key="denial_rate",
            current_value=11.0, target_value=7.0,
            recurring_revenue_uplift=1_000_000,
            recurring_cost_savings=250_000,
            one_time_working_capital_release=800_000,
            ongoing_financing_benefit=60_000,
            recurring_ebitda_delta=1_310_000,
        )

    def test_factor_one_is_identity(self):
        imp = self._sample_impact()
        out = apply_ramp_to_lever(imp, 1.0)
        self.assertEqual(out.recurring_revenue_uplift, imp.recurring_revenue_uplift)
        self.assertEqual(out.recurring_cost_savings, imp.recurring_cost_savings)
        self.assertEqual(out.ongoing_financing_benefit, imp.ongoing_financing_benefit)
        self.assertEqual(out.recurring_ebitda_delta, imp.recurring_ebitda_delta)

    def test_factor_half_scales_recurring_only(self):
        imp = self._sample_impact()
        out = apply_ramp_to_lever(imp, 0.5)
        self.assertEqual(out.recurring_revenue_uplift, 500_000)
        self.assertEqual(out.recurring_cost_savings, 125_000)
        self.assertEqual(out.ongoing_financing_benefit, 30_000)
        self.assertAlmostEqual(out.recurring_ebitda_delta, 655_000, places=3)

    def test_wc_release_untouched(self):
        imp = self._sample_impact()
        for f in (0.0, 0.25, 0.5, 0.75, 1.0):
            out = apply_ramp_to_lever(imp, f)
            self.assertEqual(
                out.one_time_working_capital_release,
                imp.one_time_working_capital_release,
            )

    def test_factor_clamped_to_unit_interval(self):
        imp = self._sample_impact()
        hi = apply_ramp_to_lever(imp, 5.0)
        lo = apply_ramp_to_lever(imp, -3.0)
        self.assertEqual(hi.recurring_ebitda_delta, imp.recurring_ebitda_delta)
        self.assertEqual(lo.recurring_revenue_uplift, 0.0)
        self.assertEqual(lo.recurring_cost_savings, 0.0)
        self.assertEqual(lo.ongoing_financing_benefit, 0.0)

    def test_provenance_records_ramp(self):
        imp = self._sample_impact()
        out = apply_ramp_to_lever(imp, 0.5)
        self.assertEqual(out.provenance.get("ramp_applied"), "0.500")


# ── RampCurve validation ───────────────────────────────────────────

class TestRampCurveValidation(unittest.TestCase):

    def test_rejects_inverted_quartiles(self):
        with self.assertRaises(ValueError):
            RampCurve("bad", months_to_25_pct=6, months_to_75_pct=3,
                      months_to_full=12)

    def test_rejects_full_before_75(self):
        with self.assertRaises(ValueError):
            RampCurve("bad", months_to_25_pct=3, months_to_75_pct=12,
                      months_to_full=6)

    def test_roundtrip_to_dict(self):
        c = DEFAULT_RAMP_CURVES["denial_management"]
        c2 = RampCurve.from_dict(c.to_dict())
        self.assertEqual(c, c2)


# ── METRIC_TO_FAMILY ───────────────────────────────────────────────

class TestMetricFamilyMapping(unittest.TestCase):

    def test_denial_variants_all_map_to_denial_management(self):
        for k in ("denial_rate", "initial_denial_rate", "auth_denial_rate",
                  "eligibility_denial_rate", "final_denial_rate"):
            self.assertEqual(family_for_metric(k), "denial_management")

    def test_cdi_family_holds_coding(self):
        self.assertEqual(family_for_metric("coding_denial_rate"), "cdi_coding")
        self.assertEqual(family_for_metric("case_mix_index"), "cdi_coding")

    def test_unknown_metric_falls_back_to_default(self):
        self.assertEqual(family_for_metric("totally_made_up_metric"), "default")

    def test_curve_for_metric_uses_registry_override(self):
        """A caller-supplied registry missing a resolved family falls
        back to the 'default' curve in that registry."""
        alt = {
            "default": RampCurve("default", 1, 2, 6),
        }
        c = curve_for_metric("denial_rate", alt)
        self.assertEqual(c.lever_family, "default")
        self.assertEqual(c.months_to_full, 6)


# ── Bridge integration ─────────────────────────────────────────────

class TestBridgeIntegration(unittest.TestCase):

    def test_default_month_36_reproduces_old_output(self):
        """With evaluation_month=36 (default) every default curve
        returns 1.0. Bridge output should be identical to the pre-
        Prompt-17 behavior."""
        base = BridgeAssumptions(
            net_revenue=400_000_000, claims_volume=120_000,
        )
        res = compute_value_bridge(
            {"denial_rate": 11.0}, {"denial_rate": 7.0},
            _profile(), base, current_ebitda=60_000_000,
        )
        # No lever was dampened.
        self.assertFalse(res.ramp_applied)
        self.assertEqual(res.per_lever_ramp_factors["denial_rate"], 1.0)

    def test_month_6_scales_denial_rate(self):
        base = BridgeAssumptions(
            net_revenue=400_000_000, claims_volume=120_000,
            evaluation_month=6,
        )
        res_late = compute_value_bridge(
            {"denial_rate": 11.0}, {"denial_rate": 7.0},
            _profile(),
            BridgeAssumptions(
                net_revenue=400_000_000, claims_volume=120_000,
            ),
            current_ebitda=60_000_000,
        )
        res_early = compute_value_bridge(
            {"denial_rate": 11.0}, {"denial_rate": 7.0},
            _profile(), base, current_ebitda=60_000_000,
        )
        self.assertTrue(res_early.ramp_applied)
        # Denial-management 3/6/12 ramp at month 6 ≈ 0.75.
        self.assertAlmostEqual(
            res_early.per_lever_ramp_factors["denial_rate"],
            0.75, places=1,
        )
        self.assertLess(
            res_early.total_recurring_ebitda_delta,
            res_late.total_recurring_ebitda_delta,
        )

    def test_month_0_zeros_recurring_but_not_ev_denom(self):
        """At month 0 every recurring flow is zeroed. WC release, if
        any, persists — but the denial_rate lever carries no WC
        release, so total cash = 0 here."""
        base = BridgeAssumptions(
            net_revenue=400_000_000, claims_volume=120_000,
            evaluation_month=0,
        )
        res = compute_value_bridge(
            {"denial_rate": 11.0}, {"denial_rate": 7.0},
            _profile(), base, current_ebitda=60_000_000,
        )
        self.assertEqual(res.total_recurring_ebitda_delta, 0.0)
        self.assertEqual(res.enterprise_value_from_recurring, 0.0)

    def test_ar_days_wc_release_not_scaled_by_ramp(self):
        """Days-in-AR carries a one-time WC release; early months
        must still book the full WC even though recurring flows are
        scaled."""
        late = compute_value_bridge(
            {"days_in_ar": 55.0}, {"days_in_ar": 45.0},
            _profile(),
            BridgeAssumptions(
                net_revenue=400_000_000, claims_volume=120_000,
            ),
            current_ebitda=60_000_000,
        )
        early = compute_value_bridge(
            {"days_in_ar": 55.0}, {"days_in_ar": 45.0},
            _profile(),
            BridgeAssumptions(
                net_revenue=400_000_000, claims_volume=120_000,
                evaluation_month=3,
            ),
            current_ebitda=60_000_000,
        )
        self.assertEqual(
            early.total_one_time_wc_release,
            late.total_one_time_wc_release,
        )
        # Financing benefit, which is recurring, should shrink though.
        self.assertLess(
            early.total_financing_benefit,
            late.total_financing_benefit,
        )

    def test_custom_ramp_curve_override(self):
        """Overriding denial_management with a slower curve lowers
        the ramp factor at month 6."""
        slow = RampCurve("denial_management", 12, 18, 24)
        fast_res = compute_value_bridge(
            {"denial_rate": 11.0}, {"denial_rate": 7.0},
            _profile(),
            BridgeAssumptions(
                net_revenue=400_000_000, claims_volume=120_000,
                evaluation_month=6,
            ),
            current_ebitda=60_000_000,
        )
        slow_res = compute_value_bridge(
            {"denial_rate": 11.0}, {"denial_rate": 7.0},
            _profile(),
            BridgeAssumptions(
                net_revenue=400_000_000, claims_volume=120_000,
                evaluation_month=6,
                ramp_curves={"denial_management": slow},
            ),
            current_ebitda=60_000_000,
        )
        self.assertLess(
            slow_res.per_lever_ramp_factors["denial_rate"],
            fast_res.per_lever_ramp_factors["denial_rate"],
        )


# ── BridgeAssumptions serialization ────────────────────────────────

class TestBridgeAssumptionsSerialization(unittest.TestCase):

    def test_default_to_dict_is_json_safe(self):
        d = BridgeAssumptions().to_dict()
        json.dumps(d)  # must not raise
        self.assertEqual(d["evaluation_month"], 36)
        self.assertIsNone(d["ramp_curves"])

    def test_to_dict_with_ramp_curves(self):
        ba = BridgeAssumptions(
            ramp_curves={
                "denial_management": RampCurve("denial_management", 1, 2, 5),
            },
        )
        d = ba.to_dict()
        json.dumps(d)
        self.assertEqual(
            d["ramp_curves"]["denial_management"]["months_to_full"], 5,
        )

    def test_old_payload_without_ramp_fields_still_deserializes(self):
        """``BridgeAssumptions`` is a dataclass — constructing it from
        a dict that predates the ``ramp_curves`` / ``evaluation_month``
        fields must still work via the defaults."""
        # Simulate what a naive caller would pass — only the old fields.
        ba = BridgeAssumptions(
            exit_multiple=10.0,
            cost_of_capital=0.08,
            collection_realization=0.65,
        )
        self.assertEqual(ba.evaluation_month, 36)
        self.assertIsNone(ba.ramp_curves)


# ── resolve_ramp_curves ────────────────────────────────────────────

class TestResolveRampCurves(unittest.TestCase):

    def test_none_returns_defaults(self):
        reg = resolve_ramp_curves(None)
        self.assertEqual(reg, DEFAULT_RAMP_CURVES)

    def test_partial_override_preserves_other_families(self):
        reg = resolve_ramp_curves({
            "denial_management": RampCurve("denial_management", 1, 2, 5),
        })
        self.assertEqual(reg["denial_management"].months_to_full, 5)
        # Other families still carry the default values.
        self.assertEqual(
            reg["cdi_coding"],
            DEFAULT_RAMP_CURVES["cdi_coding"],
        )

    def test_dict_form_parses(self):
        reg = resolve_ramp_curves({
            "denial_management": {
                "lever_family": "denial_management",
                "months_to_25_pct": 1,
                "months_to_75_pct": 2,
                "months_to_full": 5,
            },
        })
        self.assertEqual(reg["denial_management"].months_to_full, 5)


# ── v2 MC integration ──────────────────────────────────────────────

class TestV2MonteCarloHoldMonths(unittest.TestCase):
    """Lowering hold_months should lower the recurring EBITDA
    distribution — partners need Year-1 grid cells to show partial
    credit."""

    def test_year_1_lower_than_year_3(self):
        from rcm_mc.mc import V2MonteCarloSimulator
        from rcm_mc.mc.ebitda_mc import default_execution_assumption

        def _run(hold_months):
            s = V2MonteCarloSimulator(n_simulations=200, seed=11)
            s.configure(
                current_metrics={"denial_rate": 11.0},
                metric_assumptions={
                    "denial_rate": default_execution_assumption(
                        "denial_rate", current_value=11.0, target_value=7.0,
                    ),
                },
                reimbursement_profile=_profile(),
                base_assumptions=BridgeAssumptions(
                    net_revenue=400_000_000, claims_volume=120_000,
                ),
                current_ebitda=60_000_000,
                hold_months=hold_months,
            )
            return s.run()

        y1 = _run(6).recurring_ebitda_distribution.p50
        y3 = _run(36).recurring_ebitda_distribution.p50
        self.assertLess(y1, y3)

    def test_default_hold_months_preserves_old_behavior(self):
        """Configuring without hold_months should evaluate at
        base.evaluation_month (36 → full run-rate)."""
        from rcm_mc.mc import V2MonteCarloSimulator
        from rcm_mc.mc.ebitda_mc import MetricAssumption

        pm = MetricAssumption(
            metric_key="denial_rate", current_value=11.0, target_value=7.0,
            uncertainty_source="none",
            execution_probability=1.0, execution_distribution="none",
            execution_params={},
        )
        sim = V2MonteCarloSimulator(n_simulations=20, seed=5)
        sim.configure(
            current_metrics={"denial_rate": 11.0},
            metric_assumptions={"denial_rate": pm},
            reimbursement_profile=_profile(),
            base_assumptions=BridgeAssumptions(
                net_revenue=400_000_000, claims_volume=120_000,
            ),
            current_ebitda=60_000_000,
            zero_variance=True,
        )
        r = sim.run()

        det = compute_value_bridge(
            {"denial_rate": 11.0}, {"denial_rate": 7.0},
            _profile(),
            BridgeAssumptions(
                net_revenue=400_000_000, claims_volume=120_000,
            ),
            current_ebitda=60_000_000,
        )
        self.assertAlmostEqual(
            r.recurring_ebitda_distribution.p50,
            det.total_recurring_ebitda_delta,
            places=2,
        )


if __name__ == "__main__":
    unittest.main()
