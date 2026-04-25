"""Tests for service line profitability + cross-subsidy analysis."""
from __future__ import annotations

import unittest


def _record(line, name, direct, overhead, charges, revenue):
    from rcm_mc.ml.service_line_profitability import (
        CostCenterRecord,
    )
    return CostCenterRecord(
        ccn="450001", fiscal_year=2023,
        line_number=line, cost_center_name=name,
        direct_cost=direct, overhead_allocation=overhead,
        gross_charges=charges, net_revenue=revenue,
    )


class TestServiceLineMapping(unittest.TestCase):
    def test_canonical_mapping(self):
        from rcm_mc.ml.service_line_profitability import (
            LINE_TO_SERVICE_LINE,
            SERVICE_LINE_GROUPS,
        )
        # ICU (line 31) → Inpatient Routine
        self.assertEqual(
            LINE_TO_SERVICE_LINE[31], "Inpatient Routine")
        # OR (line 60) → Surgery
        self.assertEqual(LINE_TO_SERVICE_LINE[60], "Surgery")
        # ED (line 89) → ED
        self.assertEqual(LINE_TO_SERVICE_LINE[89], "ED")
        # Behavioral (line 40) → Behavioral Health
        self.assertEqual(
            LINE_TO_SERVICE_LINE[40], "Behavioral Health")

    def test_no_overlap_in_groups(self):
        from rcm_mc.ml.service_line_profitability import (
            SERVICE_LINE_GROUPS,
        )
        all_lines = []
        for lines in SERVICE_LINE_GROUPS.values():
            all_lines.extend(lines)
        # No line number maps to two groups
        self.assertEqual(
            len(all_lines), len(set(all_lines)))


class TestProfitability(unittest.TestCase):
    def test_basic_aggregation(self):
        from rcm_mc.ml.service_line_profitability import (
            compute_service_line_profitability,
        )
        # Surgery: OR + Recovery + Anesthesia (lines 60, 61, 64)
        records = [
            _record(60, "OR", 2_000_000, 500_000,
                    20_000_000, 8_000_000),
            _record(61, "Recovery", 200_000, 80_000,
                    1_200_000, 480_000),
            _record(64, "Anesthesia", 800_000, 200_000,
                    8_000_000, 3_200_000),
        ]
        out = compute_service_line_profitability(records)
        self.assertEqual(len(out), 1)
        m = out[0]
        self.assertEqual(m.service_line, "Surgery")
        self.assertEqual(m.n_cost_centers, 3)
        self.assertAlmostEqual(m.direct_cost, 3_000_000)
        self.assertAlmostEqual(m.overhead_allocation, 780_000)
        self.assertAlmostEqual(m.total_cost, 3_780_000)
        self.assertAlmostEqual(m.net_revenue, 11_680_000)
        self.assertAlmostEqual(
            m.contribution_margin, 7_900_000)
        # 7.9M / 11.68M ≈ 67.6%
        self.assertGreater(m.contribution_margin_pct, 0.65)
        # All 3 lines surfaced
        self.assertEqual(
            m.cost_center_lines, [60, 61, 64])

    def test_unknown_line_skipped(self):
        from rcm_mc.ml.service_line_profitability import (
            compute_service_line_profitability,
        )
        records = [
            _record(60, "OR", 100, 0, 1000, 400),
            _record(999, "Mystery", 50, 0, 500, 200),
        ]
        out = compute_service_line_profitability(records)
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0].service_line, "Surgery")

    def test_results_sorted_by_margin_desc(self):
        from rcm_mc.ml.service_line_profitability import (
            compute_service_line_profitability,
        )
        # ED running at loss, Surgery profitable
        records = [
            _record(89, "ED", 5_000_000, 1_000_000,
                    8_000_000, 4_500_000),  # loss
            _record(60, "OR", 1_000_000, 200_000,
                    8_000_000, 5_000_000),  # profit
        ]
        out = compute_service_line_profitability(records)
        self.assertEqual(out[0].service_line, "Surgery")
        self.assertEqual(out[-1].service_line, "ED")

    def test_revenue_share_sums_to_one(self):
        from rcm_mc.ml.service_line_profitability import (
            compute_service_line_profitability,
        )
        records = [
            _record(60, "OR", 100, 50, 1000, 400),
            _record(89, "ED", 50, 25, 500, 200),
            _record(65, "Imaging", 75, 25, 800, 350),
        ]
        out = compute_service_line_profitability(records)
        self.assertAlmostEqual(
            sum(m.revenue_share for m in out), 1.0,
            places=3)


class TestCrossSubsidy(unittest.TestCase):
    def test_classic_subsidy_pattern(self):
        """ED + Behavioral subsidized by Surgery + Cardiology."""
        from rcm_mc.ml.service_line_profitability import (
            analyze_hospital_service_lines,
        )
        records = [
            # Profit drivers
            _record(60, "OR", 5_000_000, 1_000_000,
                    50_000_000, 20_000_000),
            _record(75, "ECG", 200_000, 50_000,
                    3_000_000, 1_500_000),
            # Loss leaders
            _record(89, "ED", 8_000_000, 1_500_000,
                    12_000_000, 6_000_000),
            _record(40, "Psych", 2_500_000, 500_000,
                    3_500_000, 2_000_000),
        ]
        margins, analysis = analyze_hospital_service_lines(
            records)
        self.assertGreater(
            len(analysis.profitable_lines), 0)
        self.assertGreater(
            len(analysis.subsidized_lines), 0)
        # Surgery + Cardiology profitable
        prof_names = {m.service_line
                      for m in analysis.profitable_lines}
        self.assertIn("Surgery", prof_names)
        self.assertIn("Cardiology", prof_names)
        # ED + Behavioral subsidized
        sub_names = {m.service_line
                     for m in analysis.subsidized_lines}
        self.assertIn("ED", sub_names)
        self.assertIn("Behavioral Health", sub_names)
        # Subsidy + profit dollars positive
        self.assertGreater(analysis.total_subsidy_dollars, 0)
        self.assertGreater(analysis.total_profit_dollars, 0)
        # Net margin = profit - subsidy
        self.assertAlmostEqual(
            analysis.net_hospital_margin,
            (analysis.total_profit_dollars
             - analysis.total_subsidy_dollars))

    def test_atypical_flag_when_ed_profitable(self):
        from rcm_mc.ml.service_line_profitability import (
            analyze_hospital_service_lines,
        )
        # ED running profitably — atypical for community hospital
        records = [
            _record(89, "ED", 1_000_000, 200_000,
                    8_000_000, 3_000_000),
            _record(60, "OR", 1_000_000, 200_000,
                    8_000_000, 3_000_000),
        ]
        margins, analysis = analyze_hospital_service_lines(
            records)
        # ED is in profitable_lines and flagged
        prof_names = {m.service_line
                      for m in analysis.profitable_lines}
        self.assertIn("ED", prof_names)
        self.assertTrue(any(
            "ED is profitable" in f
            for f in analysis.flagged_atypical))

    def test_atypical_flag_when_surgery_loses(self):
        from rcm_mc.ml.service_line_profitability import (
            analyze_hospital_service_lines,
        )
        # Surgery losing money — investigate
        records = [
            _record(60, "OR", 10_000_000, 2_000_000,
                    12_000_000, 8_000_000),
            _record(75, "ECG", 200_000, 50_000,
                    3_000_000, 1_500_000),
        ]
        margins, analysis = analyze_hospital_service_lines(
            records)
        sub_names = {m.service_line
                     for m in analysis.subsidized_lines}
        self.assertIn("Surgery", sub_names)
        self.assertTrue(any(
            "Surgery is losing money" in f
            for f in analysis.flagged_atypical))

    def test_high_subsidy_intensity_note(self):
        from rcm_mc.ml.service_line_profitability import (
            analyze_hospital_service_lines,
        )
        # Subsidy ($) > Profit ($) → intensity > 1.0
        records = [
            _record(60, "OR", 3_000_000, 500_000,
                    8_000_000, 3_700_000),
            _record(89, "ED", 8_000_000, 1_500_000,
                    12_000_000, 4_000_000),
        ]
        _, analysis = analyze_hospital_service_lines(records)
        self.assertGreater(analysis.subsidy_intensity, 1.0)
        self.assertTrue(any(
            "Subsidy intensity" in n
            for n in analysis.notes))

    def test_breakeven_band(self):
        """Lines within ±2% of breakeven go into breakeven_lines,
        not profitable or subsidized."""
        from rcm_mc.ml.service_line_profitability import (
            analyze_hospital_service_lines,
        )
        # Surgery at exactly +1% margin (within band)
        records = [
            _record(60, "OR", 990_000, 0,
                    2_500_000, 1_000_000),
        ]
        _, analysis = analyze_hospital_service_lines(
            records, breakeven_band=0.02)
        self.assertEqual(len(analysis.breakeven_lines), 1)
        self.assertEqual(len(analysis.profitable_lines), 0)
        self.assertEqual(len(analysis.subsidized_lines), 0)

    def test_all_profitable_note(self):
        from rcm_mc.ml.service_line_profitability import (
            analyze_hospital_service_lines,
        )
        records = [
            _record(60, "OR", 1_000_000, 200_000,
                    5_000_000, 2_000_000),
            _record(75, "ECG", 200_000, 50_000,
                    1_500_000, 700_000),
        ]
        _, analysis = analyze_hospital_service_lines(records)
        self.assertEqual(len(analysis.subsidized_lines), 0)
        self.assertTrue(any(
            "All service lines profitable" in n
            for n in analysis.notes))

    def test_distressed_asset_note(self):
        from rcm_mc.ml.service_line_profitability import (
            analyze_hospital_service_lines,
        )
        # Every line losing money
        records = [
            _record(60, "OR", 5_000_000, 1_000_000,
                    8_000_000, 3_000_000),
            _record(89, "ED", 5_000_000, 1_000_000,
                    8_000_000, 3_000_000),
        ]
        _, analysis = analyze_hospital_service_lines(records)
        self.assertEqual(len(analysis.profitable_lines), 0)
        self.assertGreater(
            len(analysis.subsidized_lines), 0)
        self.assertTrue(any(
            "Every service line is losing money" in n
            for n in analysis.notes))


class TestComposer(unittest.TestCase):
    def test_empty_records_rejected(self):
        from rcm_mc.ml.service_line_profitability import (
            analyze_hospital_service_lines,
        )
        with self.assertRaises(ValueError):
            analyze_hospital_service_lines([])

    def test_ccn_inferred_from_records(self):
        from rcm_mc.ml.service_line_profitability import (
            analyze_hospital_service_lines,
        )
        records = [
            _record(60, "OR", 100, 50, 1000, 400),
        ]
        _, analysis = analyze_hospital_service_lines(records)
        self.assertEqual(analysis.ccn, "450001")
        self.assertEqual(analysis.fiscal_year, 2023)

    def test_explicit_ccn_overrides(self):
        from rcm_mc.ml.service_line_profitability import (
            analyze_hospital_service_lines,
        )
        records = [
            _record(60, "OR", 100, 50, 1000, 400),
        ]
        _, analysis = analyze_hospital_service_lines(
            records, ccn="999999", fiscal_year=2024)
        self.assertEqual(analysis.ccn, "999999")
        self.assertEqual(analysis.fiscal_year, 2024)


if __name__ == "__main__":
    unittest.main()
