"""Tests for the difference-in-differences policy-shock evaluator."""
from __future__ import annotations

import unittest

import numpy as np

from rcm_mc.diligence.policy_shock import (
    POLICY_SHOCKS,
    DiDResult,
    ExpectedSign,
    PanelData,
    PolicyVerdict,
    did_2x2,
    estimate_did,
    event_study,
    get_policy,
    placebo_test,
    policy_ebitda_overlay,
    synthetic_control,
)


def _make_panel(
    n_units=40, n_periods=6, treat_period=3, effect=-5.0,
    pretrend_gap=0.0, noise=0.5, seed=0,
):
    """Build a balanced panel with a known ATT and (optionally) a
    differential pre-trend, so tests can assert recovery + diagnostics.

    outcome = unit_fe + time_trend + pretrend_gap*treated*t
              + effect*(treated & post) + noise
    """
    rng = np.random.default_rng(seed)
    unit, period, outcome, treated_unit = [], [], [], []
    for u in range(n_units):
        is_treated = u < n_units // 2
        unit_fe = rng.normal(100, 10)
        for t in range(n_periods):
            y = unit_fe + 2.0 * t
            if is_treated:
                y += pretrend_gap * t
                if t >= treat_period:
                    y += effect
            y += rng.normal(0, noise)
            unit.append(f"u{u}")
            period.append(t)
            outcome.append(float(y))
            treated_unit.append(is_treated)
    return PanelData(unit, period, outcome, treated_unit, treat_period)


class TwoByTwoTests(unittest.TestCase):

    def test_did_2x2_arithmetic(self):
        # treated: 100 -> 90 (-10); control: 100 -> 105 (+5) → ATT = -15
        self.assertAlmostEqual(did_2x2(100, 90, 100, 105), -15.0)


class PanelDataTests(unittest.TestCase):

    def test_validation_unequal_lengths(self):
        with self.assertRaises(ValueError):
            PanelData(["a"], [0, 1], [1.0], [True], 1)

    def test_validation_empty(self):
        with self.assertRaises(ValueError):
            PanelData([], [], [], [], 1)

    def test_post_mask(self):
        p = _make_panel(n_units=4, n_periods=4, treat_period=2)
        mask = p.post_mask()
        self.assertEqual(mask.sum(), sum(1 for x in p.period if x >= 2))


class EstimateDiDTests(unittest.TestCase):

    def test_recovers_known_att(self):
        panel = _make_panel(effect=-5.0, noise=0.5, n_units=40)
        res = estimate_did(panel)
        self.assertAlmostEqual(res.att, -5.0, delta=0.6)
        self.assertLess(res.p_value, 0.05)
        self.assertFalse(res.small_cluster_warning)
        self.assertEqual(res.n_treated_units, 20)
        self.assertEqual(res.n_control_units, 20)

    def test_clean_data_is_strong(self):
        panel = _make_panel(effect=-6.0, noise=0.4, n_units=40)
        res = estimate_did(panel)
        self.assertEqual(res.verdict, PolicyVerdict.STRONG)
        self.assertGreaterEqual(res.pretrend_pvalue, 0.10)
        self.assertGreaterEqual(res.placebo_pvalue, 0.10)

    def test_null_effect(self):
        panel = _make_panel(effect=0.0, noise=1.0, n_units=40)
        res = estimate_did(panel)
        self.assertEqual(res.verdict, PolicyVerdict.NULL)

    def test_small_cluster_warning_caps_verdict(self):
        panel = _make_panel(effect=-6.0, noise=0.3, n_units=8)
        res = estimate_did(panel)
        self.assertTrue(res.small_cluster_warning)
        self.assertIn(res.verdict, (PolicyVerdict.SUGGESTIVE,
                                    PolicyVerdict.NULL))

    def test_ci_brackets_point_estimate(self):
        panel = _make_panel(effect=-5.0, n_units=40)
        res = estimate_did(panel)
        self.assertLess(res.ci_low, res.att)
        self.assertGreater(res.ci_high, res.att)

    def test_to_dict(self):
        panel = _make_panel(n_units=40)
        d = estimate_did(panel).to_dict()
        self.assertEqual(d["citation_key"], "PS1")
        self.assertIn("att", d)


class EventStudyTests(unittest.TestCase):

    def test_parallel_trends_pass(self):
        panel = _make_panel(effect=-5.0, pretrend_gap=0.0, noise=0.4,
                            n_units=40)
        es = event_study(panel)
        self.assertGreaterEqual(es.pretrend_pvalue, 0.10)

    def test_pretrend_violation_detected(self):
        # Inject a strong differential pre-trend; the joint test should
        # flag it (low p-value).
        panel = _make_panel(effect=-5.0, pretrend_gap=4.0, noise=0.4,
                            n_units=40)
        es = event_study(panel)
        self.assertLess(es.pretrend_pvalue, 0.10)

    def test_pretrend_violation_downgrades_verdict(self):
        panel = _make_panel(effect=-5.0, pretrend_gap=4.0, noise=0.4,
                            n_units=40)
        res = estimate_did(panel)
        self.assertNotEqual(res.verdict, PolicyVerdict.STRONG)


class PlaceboTests(unittest.TestCase):

    def test_placebo_is_null_on_clean_data(self):
        panel = _make_panel(effect=-6.0, noise=0.4, n_units=40)
        _att, p = placebo_test(panel)
        self.assertIsNotNone(p)
        self.assertGreaterEqual(p, 0.10)


class SyntheticControlTests(unittest.TestCase):

    def test_recovers_effect_single_treated(self):
        # One treated unit that tracks a donor exactly pre-period, then
        # drops by a known amount post-period.
        unit, period, outcome, treated = [], [], [], []
        n_periods, treat = 8, 5
        for t in range(n_periods):
            base = 100 + 3 * t
            # treated unit
            y_t = base + (-7.0 if t >= treat else 0.0)
            unit.append("T")
            period.append(t)
            outcome.append(float(y_t))
            treated.append(True)
            # donors that span the treated pre-trend
            for j, off in enumerate((0.0, 5.0, -5.0)):
                unit.append(f"D{j}")
                period.append(t)
                outcome.append(float(base + off))
                treated.append(False)
        panel = PanelData(unit, period, outcome, treated, treat)
        sc = synthetic_control(panel, "T", max_iter=8000, lr=0.02)
        self.assertLess(sc.pre_rmse, 1.0)
        self.assertAlmostEqual(sc.post_gap_mean, -7.0, delta=1.0)
        self.assertAlmostEqual(sum(sc.weights), 1.0, places=4)
        self.assertTrue(all(w >= -1e-9 for w in sc.weights))


class EbitdaOverlayTests(unittest.TestCase):

    def test_pct_overlay_arithmetic(self):
        res = DiDResult(
            att=-0.04, se=0.01, z_stat=-4.0, p_value=0.0001,
            ci_low=-0.06, ci_high=-0.02, n_obs=100, n_clusters=40,
            n_treated_units=20, n_control_units=20,
        )
        ov = policy_ebitda_overlay(res, exposed_revenue_usd=50_000_000,
                                   att_is_pct=True)
        self.assertAlmostEqual(ov.ebitda_impact_usd, -2_000_000, places=0)
        self.assertLess(ov.ci_low_usd, ov.ci_high_usd)

    def test_flow_through(self):
        res = DiDResult(
            att=-0.04, se=0.01, z_stat=-4.0, p_value=0.0001,
            ci_low=-0.06, ci_high=-0.02, n_obs=100, n_clusters=40,
            n_treated_units=20, n_control_units=20,
        )
        ov = policy_ebitda_overlay(res, 50_000_000, att_is_pct=True,
                                   flow_through=0.5)
        self.assertAlmostEqual(ov.ebitda_impact_usd, -1_000_000, places=0)


class PolicyLibraryTests(unittest.TestCase):

    def test_catalog_has_core_shocks(self):
        ids = {s.shock_id for s in POLICY_SHOCKS}
        for s in ("OBBBA_MEDICAID", "MA_RATE_CY2027", "PFS_CY2027"):
            self.assertIn(s, ids)

    def test_get_policy_and_fields(self):
        p = get_policy("OBBBA_MEDICAID")
        self.assertIsNotNone(p)
        self.assertEqual(p.expected_sign, ExpectedSign.NEGATIVE)
        self.assertIn("Medicaid", p.exposed_revenue_basis)
        self.assertEqual(p.to_dict()["citation_key"], "PS2")

    def test_unknown_policy(self):
        self.assertIsNone(get_policy("NOPE"))


if __name__ == "__main__":
    unittest.main()
