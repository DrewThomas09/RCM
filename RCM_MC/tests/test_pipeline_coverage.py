"""Thesis-pipeline coverage read — how complete the synthesis is.

A pure function of the report's step_log + populated headline
numbers, so the 'how much of this thesis ran vs. short-circuited'
read is auditable. Steps that did not run surface as unassessed
risks, not cleared ones.
"""
from __future__ import annotations

import unittest

from rcm_mc.diligence.thesis_pipeline import (
    PipelineInput, ThesisPipelineReport, analyze_pipeline_coverage,
    run_thesis_pipeline,
)


def _report(log):
    r = ThesisPipelineReport()
    r.step_log = log
    return r


class PipelineCoverageTests(unittest.TestCase):
    def test_empty_pipeline_is_thin(self):
        cov = analyze_pipeline_coverage(_report([]))
        self.assertEqual(cov.confidence, "THIN")
        self.assertEqual(cov.steps_total, 0)

    def test_all_ok_is_full(self):
        cov = analyze_pipeline_coverage(_report([
            {"step": "a", "status": "ok"},
            {"step": "b", "status": "ok"},
        ]))
        self.assertEqual(cov.confidence, "FULL")
        self.assertEqual(cov.steps_ok, 2)
        self.assertEqual(cov.steps_failed, 0)
        self.assertEqual(cov.coverage_pct, 1.0)

    def test_partial_lists_failed_steps_as_unassessed(self):
        cov = analyze_pipeline_coverage(_report([
            {"step": "a", "status": "ok"},
            {"step": "b", "status": "ok"},
            {"step": "c", "status": "ok"},
            {"step": "payer_stress", "status": "fail",
             "error": "KeyError: payer_mix"},
        ]))
        self.assertEqual(cov.confidence, "PARTIAL")
        self.assertEqual(cov.steps_failed, 1)
        self.assertEqual(cov.failed_steps[0]["step"], "payer_stress")
        self.assertIn("unassessed", cov.note)

    def test_thin_below_60pct(self):
        cov = analyze_pipeline_coverage(_report([
            {"step": "a", "status": "ok"},
            {"step": "b", "status": "fail", "error": "x"},
            {"step": "c", "status": "fail", "error": "y"},
        ]))
        self.assertEqual(cov.confidence, "THIN")
        self.assertLess(cov.coverage_pct, 0.60)

    def test_coverage_matches_log_arithmetic(self):
        log = [{"step": f"s{i}", "status": "ok"} for i in range(8)]
        log += [{"step": "bad", "status": "fail", "error": "e"}]
        cov = analyze_pipeline_coverage(_report(log))
        self.assertEqual(cov.steps_ok, 8)
        self.assertEqual(cov.steps_total, 9)
        self.assertAlmostEqual(cov.coverage_pct, 8 / 9, places=4)

    def test_real_pipeline_run(self):
        r = run_thesis_pipeline(PipelineInput(
            dataset="hospital_02_denial_heavy", deal_name="T",
            enterprise_value_usd=500e6, ebitda_year0_usd=60e6,
            revenue_year0_usd=450e6))
        cov = analyze_pipeline_coverage(r)
        self.assertGreater(cov.steps_total, 0)
        self.assertEqual(cov.steps_ok + cov.steps_failed, cov.steps_total)
        # headline split is bounded by the to_dict headline block.
        self.assertLessEqual(cov.headline_populated, cov.headline_total)

    def test_to_dict_round_trips(self):
        cov = analyze_pipeline_coverage(_report([
            {"step": "a", "status": "ok"}]))
        d = cov.to_dict()
        self.assertIn("coverage_pct", d)
        self.assertIn("failed_steps", d)

    def test_renders_in_page(self):
        from rcm_mc.ui.thesis_pipeline_page import (
            render_thesis_pipeline_page,
        )
        h = render_thesis_pipeline_page({
            "dataset": ["hospital_02_denial_heavy"], "deal_name": ["T"],
            "ebitda_year0_usd": ["60000000"],
            "revenue_year0_usd": ["450000000"],
            "enterprise_value_usd": ["500000000"]})
        self.assertIn("COVERAGE", h)


if __name__ == "__main__":
    unittest.main()
