"""Roll-Up Scenario Builder (P7) — combine math, HHI, honesty rules.

Verification per plan: aggregates hand-checked against per-facility rows;
HHI delta hand-recomputed; gaps reported as coverage (never silent zeros);
synergy refuses a partially-known cost base.
"""
from __future__ import annotations

import unittest

import pandas as pd

from rcm_mc.pe.rollup_scenario import antitrust_note, build_scenario

_DF = pd.DataFrame([
    {"ccn": "450001", "state": "TX", "name": "A", "beds": 100,
     "net_patient_revenue": 4.0e8, "operating_expenses": 3.6e8,
     "total_patient_days": 30000, "medicare_day_pct": 0.30,
     "medicaid_day_pct": 0.10},
    {"ccn": "450002", "state": "TX", "name": "B", "beds": 50,
     "net_patient_revenue": 1.0e8, "operating_expenses": 0.9e8,
     "total_patient_days": 10000, "medicare_day_pct": 0.50,
     "medicaid_day_pct": 0.20},
    {"ccn": "450003", "state": "TX", "name": "C", "beds": None,
     "net_patient_revenue": 5.0e8, "operating_expenses": None,
     "total_patient_days": 40000, "medicare_day_pct": float("nan"),
     "medicaid_day_pct": 0.15},
    # rest of the TX market
    {"ccn": "450010", "state": "TX", "name": "M1", "beds": 300,
     "net_patient_revenue": 6.0e8, "operating_expenses": 5.5e8,
     "total_patient_days": 60000, "medicare_day_pct": 0.4,
     "medicaid_day_pct": 0.1},
    {"ccn": "450011", "state": "TX", "name": "M2", "beds": 200,
     "net_patient_revenue": 4.0e8, "operating_expenses": 3.9e8,
     "total_patient_days": 35000, "medicare_day_pct": 0.35,
     "medicaid_day_pct": 0.12},
    {"ccn": "450012", "state": "TX", "name": "TINY", "beds": 20,
     "net_patient_revenue": 0.2e8, "operating_expenses": 0.19e8,
     "total_patient_days": 2000, "medicare_day_pct": 0.45,
     "medicaid_day_pct": 0.20},
])


class CombineMathTests(unittest.TestCase):
    def test_aggregates_hand_checked(self):
        s = build_scenario(_DF, ["450001", "450002"])
        self.assertEqual(s.beds.value, 150)
        self.assertEqual(s.inpatient_days.value, 40000)
        self.assertAlmostEqual(s.npr.value, 5.0e8)
        self.assertTrue(s.npr.complete)

    def test_gap_reported_as_coverage_not_zero(self):
        s = build_scenario(_DF, ["450001", "450003"])
        # C has no beds — combined beds covers 1/2, value is A's alone.
        self.assertEqual(s.beds.value, 100)
        self.assertEqual(s.beds.covered, 1)
        self.assertEqual(s.beds.n, 2)
        self.assertFalse(s.beds.complete)

    def test_day_weighted_payer_blend_excludes_nan_filings(self):
        s = build_scenario(_DF, ["450001", "450002", "450003"])
        # C reports NaN medicare → excluded from numerator AND denominator:
        # blend = (30000*.30 + 10000*.50) / 40000 = 0.35
        self.assertAlmostEqual(s.blended_medicare_pct, 0.35)
        self.assertEqual(s.payer_mix_covered, 2)

    def test_synergy_refuses_partial_cost_base(self):
        s = build_scenario(_DF, ["450001", "450003"])   # C has no opex
        self.assertIsNone(s.synergy_ebitda(0.10))
        s2 = build_scenario(_DF, ["450001", "450002"])
        self.assertAlmostEqual(s2.synergy_ebitda(0.10), 0.45e8)


class HhiTests(unittest.TestCase):
    def test_hhi_delta_hand_recomputed(self):
        s = build_scenario(_DF, ["450001", "450002"])
        m = s.markets[0]
        tot = 20.2e8
        sh = [4.0e8 / tot, 1.0e8 / tot]
        hand_delta = (100 * sum(sh)) ** 2 - sum((100 * x) ** 2 for x in sh)
        self.assertAlmostEqual(m.hhi_delta, hand_delta, places=6)
        self.assertAlmostEqual(m.share_after, 5.0e8 / tot)

    def test_screening_note_fires_in_presumption_zone(self):
        # Combine the two biggest (5e8 + 6e8 = 55% share) → post-HHI >1800,
        # Δ large → structural-presumption note.
        s = build_scenario(_DF, ["450003", "450010"])
        note = antitrust_note(s.markets[0])
        self.assertIn("Structural-presumption", note)
        # Tiny combo (5% + 1% shares → Δ ≈ +10) stays below thresholds.
        s2 = build_scenario(_DF, ["450002", "450012"])
        n2 = antitrust_note(s2.markets[0])
        self.assertIn("below the structural-presumption", n2)

    def test_overlap_note_when_same_state(self):
        s = build_scenario(_DF, ["450001", "450002"])
        self.assertTrue(any("overlap" in n for n in s.notes))


class PageTests(unittest.TestCase):
    def test_page_renders_and_labels_bases(self):
        from rcm_mc.ui.rollup_builder_page import render_rollup_builder
        h = render_rollup_builder({"ccns": ["450076,450068,450358"],
                                   "ga_pct": ["0.10"]})
        self.assertIn("Pro-forma platform", h)
        self.assertIn("ACTUAL", h)         # filed basis on combined figures
        self.assertIn("ENTERED", h)        # synergy is a user assumption
        self.assertIn("Merger Guidelines", h)

    def test_csv_export(self):
        from rcm_mc.ui.rollup_builder_page import render_rollup_builder
        out = render_rollup_builder({"ccns": ["450076,450068"],
                                     "format": ["csv"]})
        self.assertTrue(out.startswith("section,key,value"))

    def test_single_ccn_shows_help_not_crash(self):
        from rcm_mc.ui.rollup_builder_page import render_rollup_builder
        h = render_rollup_builder({"ccns": ["450076"]})
        self.assertIn("How this works", h)


if __name__ == "__main__":
    unittest.main()
