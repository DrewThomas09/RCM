"""Tests for the CY2026 fee-schedule backbone + site-of-service reference.

Locks in two contract layers:

1. *The hard-coded constants* — the finalized CY2026 dollar values and
   their year-over-year direction. These are the single source of truth
   other models cite; a silent edit should break a test.
2. *The site-of-service arbitrage math* — the facility-fee gap is the
   value driver, so the delta and the annualization must be exact, and
   the calculator must refuse to size off a missing rate.
"""
from __future__ import annotations

import unittest

from rcm_mc.data_public.fee_schedule_2026 import (
    COMMERCIAL_TO_MEDICARE,
    FEE_SCHEDULE_BACKBONE_2026,
    PROCEDURE_RATES_2026,
    gross_up_all_payer,
    pfs_payment,
    site_of_service_arbitrage,
)


# ── Backbone constants ──────────────────────────────────────────

class TestBackbone(unittest.TestCase):
    def test_conversion_factors_exact(self):
        b = FEE_SCHEDULE_BACKBONE_2026
        self.assertEqual(b["pfs_cf_nonqp"].value, 33.4009)
        self.assertEqual(b["pfs_cf_qp"].value, 33.5675)
        self.assertEqual(b["opps_cf"].value, 91.415)
        self.assertEqual(b["asc_cf"].value, 56.322)

    def test_qp_cf_above_nonqp(self):
        b = FEE_SCHEDULE_BACKBONE_2026
        self.assertGreater(b["pfs_cf_qp"].value, b["pfs_cf_nonqp"].value)

    def test_pfs_cf_rose_off_2025(self):
        # 2026 CFs both step up from the 2025 CF of 32.3465.
        nonqp = FEE_SCHEDULE_BACKBONE_2026["pfs_cf_nonqp"]
        self.assertEqual(nonqp.prior_value, 32.3465)
        self.assertGreater(nonqp.value, nonqp.prior_value)
        self.assertAlmostEqual(nonqp.update_pct, 3.26, places=2)

    def test_asc_cf_is_about_62pct_of_opps(self):
        b = FEE_SCHEDULE_BACKBONE_2026
        ratio = b["asc_cf"].value / b["opps_cf"].value
        self.assertTrue(0.60 <= ratio <= 0.64, ratio)

    def test_prospective_base_rates(self):
        b = FEE_SCHEDULE_BACKBONE_2026
        self.assertEqual(b["esrd_base"].value, 281.71)
        self.assertEqual(b["hh_30day_base"].value, 2038.22)
        self.assertEqual(b["hospice_cap"].value, 35361.44)

    def test_home_health_is_a_net_cut(self):
        # The poster child: market-basket positive but net negative after
        # behavioral clawbacks.
        hh = FEE_SCHEDULE_BACKBONE_2026["hh_30day_base"]
        self.assertLess(hh.value, hh.prior_value)
        self.assertLess(hh.update_pct, 0)

    def test_snf_has_update_but_no_single_base(self):
        snf = FEE_SCHEDULE_BACKBONE_2026["snf_update"]
        self.assertIsNone(snf.value)
        self.assertAlmostEqual(snf.update_pct, 3.2, places=1)

    def test_every_constant_cites_a_rule(self):
        for c in FEE_SCHEDULE_BACKBONE_2026.values():
            self.assertTrue(c.rule.startswith("CMS-"), c.key)


# ── PFS payment math ────────────────────────────────────────────

class TestPfsPayment(unittest.TestCase):
    def test_simple_triplet(self):
        # 1.0 total RVU at national GPCIs = the conversion factor
        # (rounded to the cent, as a paid amount).
        self.assertEqual(pfs_payment(0.5, 0.4, 0.1), 33.40)

    def test_qp_uses_higher_cf(self):
        self.assertGreater(
            pfs_payment(1.0, 0.0, 0.0, qp=True),
            pfs_payment(1.0, 0.0, 0.0, qp=False),
        )

    def test_gpci_scales(self):
        base = pfs_payment(1.0, 1.0, 1.0)
        localized = pfs_payment(1.0, 1.0, 1.0, gpci_work=1.1, gpci_pe=1.1, gpci_mp=1.1)
        self.assertAlmostEqual(localized, round(base * 1.1, 2), places=1)


# ── Procedure reference ─────────────────────────────────────────

class TestProcedureRates(unittest.TestCase):
    def test_colonoscopy_hopd_exceeds_asc(self):
        p = PROCEDURE_RATES_2026["45378"]
        self.assertGreater(p.hopd_facility, p.asc_facility)
        # HOPD is roughly 1.8-1.9x the ASC facility fee.
        self.assertTrue(1.7 <= p.hopd_facility / p.asc_facility <= 2.0)

    def test_physician_fee_setting_invariant_for_cath(self):
        # The cardiology cath professional fee sits well below either
        # facility fee — the facility component is the value driver.
        p = PROCEDURE_RATES_2026["93458"]
        self.assertLess(p.physician_fee, p.asc_facility)
        self.assertLess(p.asc_facility, p.hopd_facility)

    def test_every_rate_has_a_subsector(self):
        for code, p in PROCEDURE_RATES_2026.items():
            self.assertEqual(code, p.code)
            self.assertTrue(p.subsector)


# ── Site-of-service arbitrage ───────────────────────────────────

class TestArbitrage(unittest.TestCase):
    def test_hopd_to_asc_colonoscopy(self):
        r = site_of_service_arbitrage("45378", 1000, "hopd", "asc")
        # Moving 1,000 colonoscopies HOPD->ASC: facility fee falls
        # 710 -> 375 = -335/case = -$335,000 to the payer.
        self.assertEqual(r.per_case_delta, 375.0 - 710.0)
        self.assertEqual(r.annual_delta, (375.0 - 710.0) * 1000)

    def test_capture_is_positive_into_destination(self):
        # Framed as ASC capturing the facility fee it didn't have before.
        r = site_of_service_arbitrage("45378", 500, "physician", "asc")
        self.assertGreater(r.per_case_delta, 0)
        self.assertEqual(r.annual_delta, round((375.0 - 216.0) * 500, 2))

    def test_commercial_payer_grosses_rates(self):
        med = site_of_service_arbitrage("93458", 100, "physician", "hopd", payer="medicare")
        com = site_of_service_arbitrage("93458", 100, "physician", "hopd", payer="commercial")
        # Commercial HOPD multiple (2.60) exceeds professional (1.44),
        # so the commercial gap is wider than the Medicare gap.
        self.assertGreater(com.to_rate, med.to_rate)
        self.assertGreater(com.per_case_delta, med.per_case_delta)

    def test_unknown_code_raises(self):
        with self.assertRaises(ValueError):
            site_of_service_arbitrage("00000", 10, "hopd", "asc")

    def test_missing_rate_raises_not_silently_zero(self):
        # 66984 has no HOPD facility fee published — must raise, not size off None.
        with self.assertRaises(ValueError):
            site_of_service_arbitrage("66984", 10, "hopd", "asc")

    def test_bad_setting_raises(self):
        with self.assertRaises(ValueError):
            site_of_service_arbitrage("45378", 10, "hopd", "spaceship")


# ── Grossing-up engine ──────────────────────────────────────────

class TestGrossUp(unittest.TestCase):
    def test_default_is_identity(self):
        self.assertEqual(gross_up_all_payer(100.0, 0.0), 100.0)

    def test_ma_gross_up(self):
        # At 55% MA penetration, FFS is 45% of all-Medicare.
        self.assertAlmostEqual(gross_up_all_payer(45.0, 0.55), 100.0, places=2)

    def test_commercial_blend_raises_total(self):
        out = gross_up_all_payer(
            100.0, 0.0, commercial_share=0.5,
            commercial_multiplier=COMMERCIAL_TO_MEDICARE["professional"],
        )
        self.assertGreater(out, 100.0)

    def test_full_ma_penetration_raises(self):
        with self.assertRaises(ValueError):
            gross_up_all_payer(100.0, 1.0)

    def test_out_of_range_share_raises(self):
        with self.assertRaises(ValueError):
            gross_up_all_payer(100.0, 0.5, commercial_share=1.5)


if __name__ == "__main__":
    unittest.main()
