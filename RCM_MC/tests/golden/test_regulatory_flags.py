"""Golden test for NEW-17 regulatory-flag module.

Golden fixture: a heavy-Medicaid (60%) home-health target in California (a
CPOM-active oversight state) must raise both the OBBBA Medicaid flag and the
state PE-oversight flag, and nothing else.
"""
import unittest

from rcm_mc.cdd.regulatory_flags import regulatory_flags

HEAVY_MEDICAID_HOMEHEALTH_CA = {
    "payer_mix": {"Medicaid": 0.60, "Medicare": 0.20, "Commercial": 0.20},
    "state": "CA",
    "subsector": "home-health",
    "ma_exposure": 0.05,
    "is_340b": False,
}


class TestRegulatoryFlags(unittest.TestCase):
    def test_heavy_medicaid_cpom_state_raises_both(self):
        ex = regulatory_flags(HEAVY_MEDICAID_HOMEHEALTH_CA, source="Golden", vintage="2026")
        codes = ex.flag_codes()
        self.assertIn("obbba_medicaid_exposure", codes)
        self.assertIn("state_pe_oversight", codes)
        # No other rule should fire for this target.
        self.assertNotIn("ma_raf_compression", codes)
        self.assertNotIn("site_of_care_shift_exposure", codes)
        self.assertNotIn("drug_340b_drag", codes)

    def test_every_flag_has_rationale_and_source(self):
        ex = regulatory_flags(HEAVY_MEDICAID_HOMEHEALTH_CA, source="Golden", vintage="2026")
        for f in ex.flags:
            self.assertTrue(f.message, f"{f.code} missing rationale")
            self.assertTrue(f.source, f"{f.code} missing source")

    def test_flags_surface_in_both_audiences(self):
        ex = regulatory_flags(HEAVY_MEDICAID_HOMEHEALTH_CA, source="Golden", vintage="2026")
        partner = ex.render(internal_mode=False)
        internal = ex.render(internal_mode=True)
        p_codes = {f["code"] for f in partner["flags"]}
        i_codes = {f["code"] for f in internal["flags"]}
        self.assertIn("obbba_medicaid_exposure", p_codes)
        self.assertIn("obbba_medicaid_exposure", i_codes)
        # Internal exposes the rule trace; partner does not.
        p_series = {s["name"] for s in partner["series"]}
        i_series = {s["name"] for s in internal["series"]}
        self.assertNotIn("Rule trace", p_series)
        self.assertIn("Rule trace", i_series)

    def test_full_exposure_target_raises_all(self):
        target = {
            "payer_mix": {"Medicaid": 0.50},
            "state": "MA",
            "subsector": "hospital",
            "ma_exposure": 0.40,
            "is_340b": True,
        }
        codes = set(regulatory_flags(target, source="Golden", vintage="2026").flag_codes())
        self.assertEqual(codes, {
            "obbba_medicaid_exposure", "ma_raf_compression",
            "site_of_care_shift_exposure", "drug_340b_drag", "state_pe_oversight",
        })

    def test_clean_target_no_flags(self):
        target = {
            "payer_mix": {"Commercial": 0.80, "Medicare": 0.20},
            "state": "TX",  # not in oversight list
            "subsector": "behavioral-health",
            "ma_exposure": 0.10,
            "is_340b": False,
        }
        ex = regulatory_flags(target, source="Golden", vintage="2026")
        self.assertEqual(ex.flag_codes(), [])

    def test_flag_count_reconciles(self):
        ex = regulatory_flags(HEAVY_MEDICAID_HOMEHEALTH_CA, source="Golden", vintage="2026")
        self.assertTrue(ex.reconciled)
        self.assertEqual(len(ex.flags), 2)

    def test_threshold_boundary(self):
        # Exactly 40% Medicaid fires (>=).
        target = {"payer_mix": {"Medicaid": 0.40}, "state": "TX", "subsector": "x"}
        self.assertIn("obbba_medicaid_exposure",
                      regulatory_flags(target, source="G", vintage="2026").flag_codes())
        # 39% does not.
        target2 = {"payer_mix": {"Medicaid": 0.39}, "state": "TX", "subsector": "x"}
        self.assertNotIn("obbba_medicaid_exposure",
                         regulatory_flags(target2, source="G", vintage="2026").flag_codes())


if __name__ == "__main__":
    unittest.main()
