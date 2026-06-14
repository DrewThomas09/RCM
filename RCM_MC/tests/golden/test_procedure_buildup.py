"""Golden test for NEW-23 Procedure / claims bottom-up TAM.

Hand-computed single segment:
    population 100,000; utilization 12.2 / 1,000; 1.0 procedure/patient
    volume = 100,000 * 12.2/1000 * 1.0 = 1,220

    site mix  : HOPD 0.50, ASC 0.50
    payer mix : Medicare 0.60, Commercial 0.40
    Medicare allowed: HOPD 1,000; ASC 600
    commercial multipliers: HOPD 2.79, ASC 1.71

    HOPD payer-weighted = 0.6*1000 + 0.4*(1000*2.79) = 600 + 1116 = 1,716
    ASC  payer-weighted = 0.6*600  + 0.4*(600*1.71)  = 360 + 410.4 = 770.4
    per-procedure allowed = 0.5*1716 + 0.5*770.4 = 858 + 385.2 = 1,243.2
    revenue = 1,220 * 1,243.2 = 1,516,704
"""
import unittest

from rcm_mc.cdd.procedure_buildup import procedure_buildup

TOL = 1e-3

SEGMENT = {
    "label": "TKA metro",
    "population": 100_000,
    "utilization_per_1000": 12.2,
    "procedures_per_patient": 1.0,
    "site_mix": {"hopd": 0.50, "asc": 0.50},
    "payer_mix": {"medicare": 0.60, "commercial": 0.40},
    "allowed": {"hopd": 1000.0, "asc": 600.0},
}


class TestProcedureBuildup(unittest.TestCase):
    def test_hand_computed_tam(self):
        ex = procedure_buildup(
            [SEGMENT],
            commercial_multipliers={"hopd": 2.79, "asc": 1.71},
            source="Golden fixture",
            vintage="2026",
        )
        m = ex.meta
        self.assertAlmostEqual(m["tam"], 1_516_704.0, delta=TOL)
        self.assertAlmostEqual(m["segments"][0]["volume"], 1220.0, delta=TOL)
        self.assertAlmostEqual(
            m["segments"][0]["per_procedure_allowed"], 1243.2, delta=TOL
        )
        self.assertTrue(ex.reconciled)

    def test_component_allowed_sums(self):
        # An allowed dict (professional + facility) sums to the scalar base.
        seg = dict(SEGMENT)
        seg["allowed"] = {
            "hopd": {"professional": 400.0, "facility": 600.0},  # sums to 1000
            "asc": 600.0,
        }
        ex = procedure_buildup(
            [seg], commercial_multipliers={"hopd": 2.79, "asc": 1.71}
        )
        self.assertAlmostEqual(ex.meta["tam"], 1_516_704.0, delta=TOL)

    def test_default_multipliers_from_backbone(self):
        # Without overrides the build uses the fee-schedule backbone multipliers.
        ex = procedure_buildup([SEGMENT])
        self.assertTrue(ex.reconciled)
        self.assertGreater(ex.meta["tam"], 0.0)

    def test_unnormalized_mix_flags(self):
        seg = dict(SEGMENT)
        seg["site_mix"] = {"hopd": 0.5, "asc": 0.3}  # sums to 0.8
        ex = procedure_buildup(
            [seg], commercial_multipliers={"hopd": 2.79, "asc": 1.71}
        )
        self.assertFalse(ex.reconciled)
        self.assertTrue(any(c.startswith("mix_not_normalized") for c in ex.flag_codes()))

    def test_unknown_payer_raises(self):
        seg = dict(SEGMENT)
        seg["payer_mix"] = {"medicaid": 1.0}
        with self.assertRaises(ValueError):
            procedure_buildup([seg], commercial_multipliers={"hopd": 2.79, "asc": 1.71})

    def test_empty_segments_raises(self):
        with self.assertRaises(ValueError):
            procedure_buildup([])


if __name__ == "__main__":
    unittest.main()
