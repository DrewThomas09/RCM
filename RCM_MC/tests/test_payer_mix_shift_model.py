"""Tests for payer_mix_shift_model.py — payer mix evolution over hold period."""
from __future__ import annotations

import unittest
from typing import Any, Dict, List


def _commercial_heavy() -> Dict[str, float]:
    return {"commercial": 0.70, "medicare": 0.20, "medicaid": 0.08, "self_pay": 0.02}


def _medicaid_heavy() -> Dict[str, float]:
    return {"commercial": 0.20, "medicare": 0.15, "medicaid": 0.55, "self_pay": 0.10}


def _all_commercial() -> Dict[str, float]:
    return {"commercial": 1.0}


class TestProjectPayerMixBasic(unittest.TestCase):
    def setUp(self):
        from rcm_mc.data_public.payer_mix_shift_model import project_payer_mix
        self.project = project_payer_mix

    def test_returns_result_object(self):
        from rcm_mc.data_public.payer_mix_shift_model import PayerMixShiftResult
        result = self.project(_commercial_heavy(), hold_years=5)
        self.assertIsInstance(result, PayerMixShiftResult)

    def test_projections_length(self):
        result = self.project(_commercial_heavy(), hold_years=5)
        self.assertEqual(len(result.projections), 6)  # year 0..5

    def test_year_zero_revenue_index_one(self):
        result = self.project(_commercial_heavy(), hold_years=5)
        self.assertAlmostEqual(result.projections[0].revenue_index, 1.0)

    def test_year_zero_ebitda_delta_zero(self):
        result = self.project(_commercial_heavy(), hold_years=5)
        self.assertAlmostEqual(result.projections[0].ebitda_margin_delta_pct, 0.0)

    def test_commercial_erodes_over_time(self):
        result = self.project(_commercial_heavy(), hold_years=5, sector="Physician Practices")
        entry_comm = result.projections[0].mix["commercial"]
        exit_comm = result.projections[-1].mix["commercial"]
        self.assertLess(exit_comm, entry_comm)

    def test_revenue_index_declines_when_commercial_erodes(self):
        result = self.project(_commercial_heavy(), hold_years=5)
        self.assertLessEqual(result.projections[-1].revenue_index, 1.0)

    def test_ebitda_at_risk_non_negative(self):
        result = self.project(_commercial_heavy(), hold_years=5)
        self.assertGreaterEqual(result.ebitda_at_risk_pct, 0.0)

    def test_signal_valid(self):
        result = self.project(_commercial_heavy(), hold_years=5)
        self.assertIn(result.signal, ("green", "yellow", "red"))

    def test_base_mix_stored(self):
        pm = _commercial_heavy()
        result = self.project(pm, hold_years=5)
        self.assertAlmostEqual(result.base_mix["commercial"], 0.70)

    def test_exit_mix_populated(self):
        result = self.project(_commercial_heavy(), hold_years=5)
        self.assertIsNotNone(result.exit_mix)
        total = sum(result.exit_mix.values())
        self.assertAlmostEqual(total, 1.0, places=2)

    def test_mix_sums_to_one_each_year(self):
        result = self.project(_commercial_heavy(), hold_years=5)
        for p in result.projections:
            total = sum(p.mix.values())
            self.assertAlmostEqual(total, 1.0, places=2, msg=f"Year {p.year} mix total {total:.4f}")

    def test_hold_years_3(self):
        result = self.project(_commercial_heavy(), hold_years=3)
        self.assertEqual(len(result.projections), 4)

    def test_hold_years_7(self):
        result = self.project(_commercial_heavy(), hold_years=7)
        self.assertEqual(len(result.projections), 8)

    def test_notes_is_list(self):
        result = self.project(_commercial_heavy(), hold_years=5)
        self.assertIsInstance(result.notes, list)


class TestSectorRates(unittest.TestCase):
    def setUp(self):
        from rcm_mc.data_public.payer_mix_shift_model import project_payer_mix
        self.project = project_payer_mix

    def test_behavioral_health_more_at_risk_than_digital(self):
        pm = {"commercial": 0.50, "medicare": 0.20, "medicaid": 0.25, "self_pay": 0.05}
        r_beh = self.project(pm, 5, "Behavioral Health")
        r_dig = self.project(pm, 5, "Digital Health")
        self.assertGreaterEqual(r_beh.ebitda_at_risk_pct, r_dig.ebitda_at_risk_pct)

    def test_skilled_nursing_high_medicare_drift(self):
        pm = {"commercial": 0.30, "medicare": 0.50, "medicaid": 0.18, "self_pay": 0.02}
        result = self.project(pm, 5, "Skilled Nursing")
        # Medicare → Medicaid drift is elevated in SNF
        entry_mcaid = result.projections[0].mix.get("medicaid", 0.0)
        exit_mcaid = result.projections[-1].mix.get("medicaid", 0.0)
        self.assertGreater(exit_mcaid, entry_mcaid)

    def test_behavioral_note_generated(self):
        pm = _medicaid_heavy()
        result = self.project(pm, 5, "Behavioral Health")
        self.assertTrue(
            any("Behavioral Health" in n or "Medicaid" in n for n in result.notes)
        )

    def test_unknown_sector_no_crash(self):
        result = self.project(_commercial_heavy(), 5, "Niche Robotics Surgery")
        self.assertIsNotNone(result)

    def test_high_medicaid_note_triggered(self):
        pm = {"commercial": 0.10, "medicare": 0.10, "medicaid": 0.70, "self_pay": 0.10}
        result = self.project(pm, 5, "Behavioral Health")
        self.assertTrue(any("Medicaid" in n for n in result.notes))


class TestSignalThresholds(unittest.TestCase):
    def setUp(self):
        from rcm_mc.data_public.payer_mix_shift_model import project_payer_mix
        self.project = project_payer_mix

    def test_all_commercial_lowest_risk(self):
        # All commercial has lowest ebitda_at_risk vs any mixed payer scenario
        r_comm = self.project(_all_commercial(), 5, "Digital Health")
        r_mixed = self.project(_commercial_heavy(), 5, "Behavioral Health")
        self.assertLessEqual(r_comm.ebitda_at_risk_pct, r_mixed.ebitda_at_risk_pct)

    def test_medicaid_heavy_high_risk(self):
        result = self.project(_medicaid_heavy(), 5, "Behavioral Health")
        self.assertIn(result.signal, ("yellow", "red"))

    def test_bear_scenario_more_risk(self):
        from rcm_mc.data_public.payer_mix_shift_model import stress_payer_shift
        scenarios = stress_payer_shift(_commercial_heavy(), 5, "Physician Practices")
        self.assertGreaterEqual(
            scenarios["bear"].ebitda_at_risk_pct,
            scenarios["base"].ebitda_at_risk_pct,
        )

    def test_bull_scenario_less_risk(self):
        from rcm_mc.data_public.payer_mix_shift_model import stress_payer_shift
        scenarios = stress_payer_shift(_commercial_heavy(), 5, "Physician Practices")
        self.assertLessEqual(
            scenarios["bull"].ebitda_at_risk_pct,
            scenarios["base"].ebitda_at_risk_pct,
        )


class TestRevenueIndex(unittest.TestCase):
    def setUp(self):
        from rcm_mc.data_public.payer_mix_shift_model import _revenue_index
        self.fn = _revenue_index

    def test_all_commercial_index_1(self):
        self.assertAlmostEqual(self.fn({"commercial": 1.0}), 1.0)

    def test_all_medicare_below_1(self):
        idx = self.fn({"medicare": 1.0})
        self.assertLess(idx, 1.0)
        self.assertGreater(idx, 0.7)

    def test_all_medicaid_below_medicare(self):
        idx_mcare = self.fn({"medicare": 1.0})
        idx_mcaid = self.fn({"medicaid": 1.0})
        self.assertLess(idx_mcaid, idx_mcare)

    def test_all_selfpay_lowest(self):
        idx_sp = self.fn({"self_pay": 1.0})
        idx_mcaid = self.fn({"medicaid": 1.0})
        self.assertLess(idx_sp, idx_mcaid)

    def test_mixed_between_extremes(self):
        idx = self.fn({"commercial": 0.5, "medicaid": 0.5})
        self.assertGreater(idx, 0.5)
        self.assertLess(idx, 1.0)


class TestAssumptionsOverride(unittest.TestCase):
    def setUp(self):
        from rcm_mc.data_public.payer_mix_shift_model import project_payer_mix
        self.project = project_payer_mix

    def test_higher_fixed_cost_more_at_risk(self):
        r_low = self.project(_commercial_heavy(), 5, assumptions={"fixed_cost_fraction": 0.4})
        r_high = self.project(_commercial_heavy(), 5, assumptions={"fixed_cost_fraction": 0.9})
        self.assertGreaterEqual(r_high.ebitda_at_risk_pct, r_low.ebitda_at_risk_pct)

    def test_rate_multiplier_2x_accelerates_drift(self):
        r_base = self.project(_commercial_heavy(), 5)
        r_stress = self.project(_commercial_heavy(), 5, assumptions={"rate_multiplier": 2.0})
        entry_c_base = r_base.projections[-1].mix.get("commercial", 0.0)
        entry_c_stress = r_stress.projections[-1].mix.get("commercial", 0.0)
        self.assertLess(entry_c_stress, entry_c_base)

    def test_empty_assumptions_no_crash(self):
        result = self.project(_commercial_heavy(), 5, assumptions={})
        self.assertIsNotNone(result)


class TestEdgeCases(unittest.TestCase):
    def setUp(self):
        from rcm_mc.data_public.payer_mix_shift_model import project_payer_mix
        self.project = project_payer_mix

    def test_empty_payer_mix_no_crash(self):
        result = self.project({}, 5)
        self.assertIsNotNone(result)

    def test_unnormalized_mix_normalizes(self):
        # Should sum to ~1 after normalization
        result = self.project({"commercial": 2.0, "medicare": 1.0}, 5)
        total = sum(result.base_mix.values())
        self.assertAlmostEqual(total, 1.0, places=2)

    def test_hold_years_1(self):
        result = self.project(_commercial_heavy(), 1)
        self.assertEqual(len(result.projections), 2)

    def test_deal_name_stored(self):
        result = self.project(_commercial_heavy(), 5, deal_name="Acme Health")
        self.assertEqual(result.deal_name, "Acme Health")

    def test_sector_stored(self):
        result = self.project(_commercial_heavy(), 5, sector="Dental")
        self.assertEqual(result.sector, "Dental")


class TestStressScenarios(unittest.TestCase):
    def setUp(self):
        from rcm_mc.data_public.payer_mix_shift_model import stress_payer_shift
        self.stress = stress_payer_shift

    def test_returns_three_scenarios(self):
        result = self.stress(_commercial_heavy(), 5)
        self.assertIn("base", result)
        self.assertIn("bear", result)
        self.assertIn("bull", result)

    def test_bear_worse_than_base(self):
        result = self.stress(_commercial_heavy(), 5, "Behavioral Health")
        self.assertGreaterEqual(
            result["bear"].ebitda_at_risk_pct,
            result["base"].ebitda_at_risk_pct,
        )

    def test_bull_better_than_base(self):
        result = self.stress(_commercial_heavy(), 5)
        self.assertLessEqual(
            result["bull"].ebitda_at_risk_pct,
            result["base"].ebitda_at_risk_pct,
        )


class TestCorpusPayerShiftRisk(unittest.TestCase):
    def setUp(self):
        from rcm_mc.data_public.payer_mix_shift_model import corpus_payer_shift_risk
        self.fn = corpus_payer_shift_risk

    def _make_corpus(self) -> list:
        return [
            {
                "source_id": f"deal_{i}",
                "deal_name": f"Deal {i}",
                "sector": ["Behavioral Health", "Digital Health", "Dental"][i % 3],
                "payer_mix": [_commercial_heavy(), _medicaid_heavy(), _all_commercial()][i % 3],
                "hold_years": 5,
            }
            for i in range(9)
        ]

    def test_returns_list(self):
        result = self.fn(self._make_corpus())
        self.assertIsInstance(result, list)

    def test_sorted_descending_by_risk(self):
        result = self.fn(self._make_corpus())
        risks = [r[1].ebitda_at_risk_pct for r in result]
        for i in range(len(risks) - 1):
            self.assertGreaterEqual(risks[i], risks[i + 1])

    def test_deals_without_payer_mix_excluded(self):
        corpus = [{"source_id": "no_pm", "deal_name": "No PM deal"}]
        result = self.fn(corpus)
        self.assertEqual(len(result), 0)

    def test_all_deals_with_payer_mix_included(self):
        corpus = self._make_corpus()
        result = self.fn(corpus)
        self.assertEqual(len(result), 9)


class TestFormatters(unittest.TestCase):
    def setUp(self):
        from rcm_mc.data_public.payer_mix_shift_model import (
            project_payer_mix, payer_shift_report, payer_shift_table,
        )
        self.result = project_payer_mix(_commercial_heavy(), 5, "Physician Practices", "Test Deal")
        self.report = payer_shift_report(self.result)
        self.payer_shift_table = payer_shift_table

    def test_report_returns_string(self):
        self.assertIsInstance(self.report, str)

    def test_report_contains_deal_name(self):
        self.assertIn("Test Deal", self.report)

    def test_report_contains_signal(self):
        self.assertIn(self.result.signal.upper(), self.report)

    def test_report_contains_all_years(self):
        for yr in range(6):
            self.assertIn(str(yr), self.report)

    def test_table_returns_string(self):
        results = [self.result]
        table = self.payer_shift_table(results)
        self.assertIsInstance(table, str)

    def test_table_sorted_descending(self):
        from rcm_mc.data_public.payer_mix_shift_model import project_payer_mix
        results = [
            project_payer_mix(_all_commercial(), 5, "Digital Health", "Safe"),
            project_payer_mix(_medicaid_heavy(), 5, "Behavioral Health", "Risky"),
        ]
        table = self.payer_shift_table(results)
        risky_pos = table.index("Risky")
        safe_pos = table.index("Safe")
        self.assertLess(risky_pos, safe_pos)  # Risky appears first (higher risk)


if __name__ == "__main__":
    unittest.main()
