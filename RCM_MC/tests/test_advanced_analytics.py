"""Tests for the advanced-analytics composition facade."""
from __future__ import annotations

import unittest

import numpy as np

from rcm_mc.diligence.advanced_analytics import (
    AdvancedAnalyticsInputs,
    run_advanced_analytics,
)
from rcm_mc.diligence.episodes import ClaimLine, EpisodeDefinition
from rcm_mc.diligence.pmpm import PMPMPeriod
from rcm_mc.diligence.policy_shock import PanelData
from rcm_mc.diligence.quality_measures import evaluate_measure, get_measure
from rcm_mc.diligence.risk_adjustment import Demographics


def _policy_panel(effect=-0.04, n_units=40, seed=0):
    rng = np.random.default_rng(seed)
    u, p, o, t = [], [], [], []
    for unit in range(n_units):
        tr = unit < n_units // 2
        fe = rng.normal(100, 8)
        for period in range(6):
            y = fe + 2 * period
            if tr and period >= 3:
                y += effect * fe
            y += rng.normal(0, 0.4)
            u.append(f"u{unit}")
            p.append(period)
            o.append(y)
            t.append(tr)
    return PanelData(u, p, o, t, 3)


class FacadeTests(unittest.TestCase):

    def test_empty_inputs_runs_nothing(self):
        res = run_advanced_analytics(AdvancedAnalyticsInputs())
        self.assertEqual(res.findings, [])
        self.assertIn("no inputs", res.headline.lower())
        self.assertEqual(res.total_ebitda_at_risk_usd, 0.0)

    def test_single_section_risk(self):
        res = run_advanced_analytics(AdvancedAnalyticsInputs(
            panel=[(Demographics(72, "M"), ["CHF"]),
                   (Demographics(80, "F"), ["E11.42", "I50.9"])],
        ))
        self.assertIsNotNone(res.risk)
        self.assertIsNone(res.pmpm)
        self.assertEqual(len(res.findings), 1)

    def test_pmpm_ebitda_rolls_up(self):
        periods = [PMPMPeriod("2023", 1000, 1.0),
                   PMPMPeriod("2024", 1100, 1.0)]   # 10%/yr real inflation
        res = run_advanced_analytics(AdvancedAnalyticsInputs(
            pmpm_periods=periods, pmpm_periods_per_year=1.0,
            pmpm_annual_member_months=120_000,
        ))
        self.assertIsNotNone(res.pmpm)
        self.assertGreater(res.total_ebitda_at_risk_usd, 0)

    def test_policy_overlay_rolls_up_adverse(self):
        res = run_advanced_analytics(AdvancedAnalyticsInputs(
            policy_panel=_policy_panel(effect=-0.04),
            policy_exposed_revenue_usd=50_000_000,
            policy_att_is_pct=True,
        ))
        self.assertIsNotNone(res.policy)
        self.assertIsNotNone(res.policy_overlay)
        self.assertGreater(res.total_ebitda_at_risk_usd, 0)

    def test_full_stack_composes(self):
        inputs = AdvancedAnalyticsInputs(
            panel=[(Demographics(72, "M"), ["CHF"])],
            unit_ids=["a", "b", "c"], unit_estimates=[1.0, 1.5, 0.9],
            unit_ses=[0.1, 0.4, 0.1],
            pmpm_periods=[PMPMPeriod("2023", 1000, 1.0),
                          PMPMPeriod("2024", 1050, 1.0)],
            pmpm_periods_per_year=1.0,
            policy_panel=_policy_panel(),
            policy_exposed_revenue_usd=50_000_000,
            survival_durations=[1, 2, 3, 4, 5], survival_events=[1, 1, 0, 1, 1],
            episode_claims=[ClaimLine("p1", 100, 10000.0, "inpatient")],
            episode_definition=EpisodeDefinition(
                frozenset({"inpatient"}), post_window_days=90),
            quality_results=[evaluate_measure(get_measure("HBA1C_CONTROL"),
                                              700, 1000)],
            billed_amounts=(10 ** np.random.default_rng(0).uniform(0, 5, 2000)).tolist(),
        )
        res = run_advanced_analytics(inputs)
        for section in (res.risk, res.hierarchical, res.pmpm, res.policy,
                        res.survival, res.episodes, res.quality, res.integrity):
            self.assertIsNotNone(section)
        self.assertEqual(len(res.findings), 8)
        self.assertTrue(res.headline.startswith("Advanced analytics ran 8"))

    def test_to_dict_round_trips(self):
        res = run_advanced_analytics(AdvancedAnalyticsInputs(
            panel=[(Demographics(72, "M"), ["CHF"])],
        ))
        d = res.to_dict()
        self.assertEqual(d["citation_key"], "AA1")
        self.assertIsNotNone(d["risk"])
        self.assertIsNone(d["pmpm"])


if __name__ == "__main__":
    unittest.main()
