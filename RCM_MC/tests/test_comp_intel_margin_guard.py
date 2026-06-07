"""Regression: comp-intel surfaces band-gate implausible HCRIS margins.

The `_op_margin` accessor feeds three surfaces (hero strip, percentile
ranking, peer table). Gating once at the accessor keeps the "one margin"
rule: an artifact like 100% (incomplete/aggregated opex in the filing)
must read as "—" everywhere, never as a confident comp on one surface and
"—" on another. See _chartis_kit.margin_is_plausible.
"""
import unittest

from rcm_mc.ui.deal_surfaces.comp_intel import _op_margin


class CompIntelMarginGuardTests(unittest.TestCase):
    def test_plausible_margin_passes_through(self):
        # NPR 100M, opex 92M -> 8% operating margin, inside the band.
        m = _op_margin({"net_patient_revenue": 100e6, "operating_expenses": 92e6})
        self.assertAlmostEqual(m, 0.08, places=6)

    def test_plausible_negative_margin_passes_through(self):
        # Hospitals routinely file negative operating margins — those are real.
        m = _op_margin({"net_patient_revenue": 100e6, "operating_expenses": 120e6})
        self.assertAlmostEqual(m, -0.20, places=6)

    def test_artifact_margin_is_suppressed(self):
        # Near-zero opex -> ~100% margin, an incomplete-filing artifact.
        m = _op_margin({"net_patient_revenue": 100e6, "operating_expenses": 100.0})
        self.assertIsNone(m)

    def test_missing_inputs_return_none(self):
        self.assertIsNone(_op_margin({"net_patient_revenue": 100e6}))
        self.assertIsNone(_op_margin({}))


if __name__ == "__main__":
    unittest.main()
