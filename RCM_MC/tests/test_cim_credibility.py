"""CIM credibility index — the auditable trust read on a CIM.

The score must be a deterministic, pure function of the variance
rows (so it can never disagree with the table), penalize red
variances and unverifiable claims, and surface the overstatement-
direction signal a CDD lead is hunting for.
"""
from __future__ import annotations

import unittest

from rcm_mc.diligence.cim_crosscheck import (
    CrossCheckResult, Estimate, VarianceRow, compute_cim_credibility,
)


def _row(flag, var):
    return VarianceRow(
        claim_key="k", label="L", claim_value=1.0,
        estimate=Estimate(claim_key="k", label="L", value=1.0, n=10,
                          unit="$", method="m"),
        variance=var, flag=flag,
    )


def _result(rows):
    r = CrossCheckResult(scope_label="x", state="TX", ccn="")
    r.rows = rows
    return r


class CIMCredibilityTests(unittest.TestCase):
    def test_all_green_is_corroborated_100(self):
        c = compute_cim_credibility(_result([
            _row("green", 0.02), _row("green", -0.03), _row("green", 0.01),
        ]))
        self.assertEqual(c.score, 100)
        self.assertEqual(c.band, "Corroborated")
        self.assertEqual(c.bias_direction, "balanced")
        self.assertEqual(c.verified_share, 1.0)

    def test_score_is_deterministic_deduction(self):
        # 1 red (-28) + 1 yellow (-10) + 1 unverifiable (-6) = 56.
        c = compute_cim_credibility(_result([
            _row("green", 0.0), _row("red", 0.4),
            _row("yellow", 0.18), _row("unverifiable", None),
        ]))
        self.assertEqual(c.score, 100 - 28 - 10 - 6)

    def test_overstatement_pattern_detected(self):
        c = compute_cim_credibility(_result([
            _row("red", 0.40), _row("red", 0.32), _row("yellow", 0.18),
        ]))
        self.assertEqual(c.band, "Overstated")
        self.assertEqual(c.bias_direction, "overstates")
        self.assertGreater(c.overstatement_bias, 0.05)
        self.assertIn("overstatement pattern", c.rationale)

    def test_understatement_is_conservative_not_overstated(self):
        c = compute_cim_credibility(_result([
            _row("red", -0.40), _row("yellow", -0.18),
        ]))
        self.assertEqual(c.bias_direction, "understates")
        # One red, understating → not the "Overstated" band.
        self.assertNotEqual(c.band, "Overstated")

    def test_all_unverifiable_is_unsubstantiated(self):
        c = compute_cim_credibility(_result([
            _row("unverifiable", None), _row("unverifiable", None),
        ]))
        self.assertEqual(c.band, "Unsubstantiated")
        self.assertEqual(c.bias_direction, "n/a")
        self.assertIsNone(c.overstatement_bias)

    def test_empty_result(self):
        c = compute_cim_credibility(_result([]))
        self.assertEqual(c.band, "Unsubstantiated")
        self.assertEqual(c.n_verifiable, 0)

    def test_score_floored_at_zero(self):
        c = compute_cim_credibility(_result([_row("red", 0.9)] * 5))
        self.assertEqual(c.score, 0)

    def test_to_dict_round_trips(self):
        c = compute_cim_credibility(_result([_row("green", 0.0)]))
        d = c.to_dict()
        self.assertEqual(d["band"], "Corroborated")
        self.assertIn("overstatement_bias", d)

    def test_renders_in_page(self):
        from rcm_mc.ui.cim_crosscheck_page import render_cim_crosscheck
        html_out = render_cim_crosscheck({
            "state": ["TX"],
            "c_market_size_dollars": ["5000000000"],
            "c_target_ebitda_margin": ["18"],
        })
        self.assertIn("CIM credibility index", html_out)
        self.assertIn("/100", html_out)


if __name__ == "__main__":
    unittest.main()
