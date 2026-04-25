"""Tests for the Site-Neutral Module."""
from __future__ import annotations

import unittest


# ── Code list ───────────────────────────────────────────────────

class TestCodeList(unittest.TestCase):
    def test_drug_admin_codes_recognized(self):
        from rcm_mc.site_neutral import is_site_neutral_code
        self.assertTrue(is_site_neutral_code("96365"))
        self.assertTrue(is_site_neutral_code("96409"))

    def test_imaging_codes_recognized(self):
        from rcm_mc.site_neutral import is_site_neutral_code
        self.assertTrue(is_site_neutral_code("70551"))
        self.assertTrue(is_site_neutral_code("74176"))

    def test_unrelated_code_not_recognized(self):
        from rcm_mc.site_neutral import is_site_neutral_code
        self.assertFalse(is_site_neutral_code("99999"))
        self.assertFalse(is_site_neutral_code(""))


# ── Hospital revenue-at-risk ──────────────────────────────────

class TestHospitalRevenueAtRisk(unittest.TestCase):
    def test_basic_exposure(self):
        from rcm_mc.site_neutral import (
            compute_hospital_revenue_at_risk,
            SiteNeutralCategory,
        )
        result = compute_hospital_revenue_at_risk(
            "TestHospital",
            offcampus_pbd_revenue_mm=100.0,
            category_revenue_share={
                SiteNeutralCategory.DRUG_ADMINISTRATION: 0.30,
                SiteNeutralCategory.DIAGNOSTIC_IMAGING: 0.25,
                SiteNeutralCategory.EM_CODES: 0.20,
                SiteNeutralCategory.DIALYSIS_RELATED: 0.05,
            },
            medicare_share=0.50,
            ebitda_margin=0.20,
        )
        # Expected drug admin contribution:
        # 100 × 0.30 × 0.50 × 0.40 = 6.0M revenue at risk
        # × 0.20 ebitda margin = 1.2M ebitda at risk
        drug = next(c for c in result.per_category
                    if c.category
                    == SiteNeutralCategory.DRUG_ADMINISTRATION)
        self.assertAlmostEqual(
            drug.revenue_at_risk_mm, 6.0, places=1)
        self.assertAlmostEqual(
            drug.ebitda_at_risk_mm, 1.2, places=1)

    def test_zero_medicare_share_zero_exposure(self):
        """Site-neutral only affects Medicare bills — zero share
        → zero exposure."""
        from rcm_mc.site_neutral import (
            compute_hospital_revenue_at_risk,
            SiteNeutralCategory,
        )
        result = compute_hospital_revenue_at_risk(
            "Test",
            offcampus_pbd_revenue_mm=100.0,
            category_revenue_share={
                SiteNeutralCategory.DRUG_ADMINISTRATION: 1.0,
            },
            medicare_share=0.0,
            ebitda_margin=0.20,
        )
        self.assertEqual(result.total_revenue_at_risk_mm, 0.0)
        self.assertEqual(result.total_ebitda_at_risk_mm, 0.0)


# ── ASC opportunity ─────────────────────────────────────────────

class TestASCOpportunity(unittest.TestCase):
    def test_capture_with_local_competitors(self):
        from rcm_mc.site_neutral import (
            compute_asc_opportunity,
        )
        from rcm_mc.site_neutral.asc_opportunity import (
            HospitalCompetitor,
        )
        comps = [
            HospitalCompetitor(
                company_name="Hosp A", cbsa="26420",
                affected_revenue_mm=10.0,
                asc_relevant_share=0.7),
            HospitalCompetitor(
                company_name="Hosp B", cbsa="26420",
                affected_revenue_mm=15.0,
                asc_relevant_share=0.6),
            # Different CBSA — should be filtered out
            HospitalCompetitor(
                company_name="Hosp C", cbsa="19100",
                affected_revenue_mm=20.0),
        ]
        opp = compute_asc_opportunity(
            "TestASC", "26420",
            capacity_share=0.20,
            competitors=comps,
            asc_ebitda_margin=0.30,
            volume_elasticity=0.30,
        )
        # 2 competitors in CBSA 26420
        self.assertEqual(opp.n_competitors, 2)
        # Total shiftable: (10×0.7 + 15×0.6) × 0.30 = (7 + 9) × 0.30 = 4.8
        # ASC captures 0.20 → 0.96M volume
        # × 0.30 margin → 0.288M ebitda
        self.assertAlmostEqual(
            opp.expected_volume_pickup_mm, 0.96, places=2)
        self.assertAlmostEqual(
            opp.expected_ebitda_pickup_mm, 0.29, places=2)

    def test_no_local_competitors_zero_pickup(self):
        from rcm_mc.site_neutral import compute_asc_opportunity
        opp = compute_asc_opportunity(
            "ASC", "99999",  # CBSA with no competitors
            capacity_share=0.5, competitors=[])
        self.assertEqual(opp.expected_ebitda_pickup_mm, 0.0)


# ── Net impact wrapper ─────────────────────────────────────────

class TestSiteNeutralImpact(unittest.TestCase):
    def test_hospital_only_negative_impact(self):
        from rcm_mc.site_neutral import (
            compute_site_neutral_impact, SiteNeutralCategory,
        )
        impact = compute_site_neutral_impact(
            "TestHospital", target_type="hospital",
            offcampus_pbd_revenue_mm=200.0,
            category_revenue_share={
                SiteNeutralCategory.DRUG_ADMINISTRATION: 0.40,
                SiteNeutralCategory.DIAGNOSTIC_IMAGING: 0.30,
            },
            medicare_share=0.45,
            hospital_ebitda_margin=0.18,
        )
        self.assertIsNotNone(impact.hospital_risk)
        self.assertIsNone(impact.asc_opportunity)
        # Net impact is negative for hospitals
        self.assertLess(impact.net_ebitda_impact_mm, 0)

    def test_asc_only_positive_impact(self):
        from rcm_mc.site_neutral import compute_site_neutral_impact
        from rcm_mc.site_neutral.asc_opportunity import (
            HospitalCompetitor,
        )
        impact = compute_site_neutral_impact(
            "TestASC", target_type="asc",
            asc_cbsa="26420",
            asc_capacity_share=0.30,
            asc_competitors=[
                HospitalCompetitor(
                    company_name="Hosp",
                    cbsa="26420",
                    affected_revenue_mm=20.0)],
            asc_ebitda_margin=0.30,
        )
        self.assertIsNone(impact.hospital_risk)
        self.assertIsNotNone(impact.asc_opportunity)
        self.assertGreater(impact.net_ebitda_impact_mm, 0)

    def test_mixed_target_combines_both(self):
        from rcm_mc.site_neutral import (
            compute_site_neutral_impact, SiteNeutralCategory,
        )
        from rcm_mc.site_neutral.asc_opportunity import (
            HospitalCompetitor,
        )
        # A health-system that owns both a hospital + ASCs in
        # the same CBSA — the textbook hedge.
        impact = compute_site_neutral_impact(
            "MixedSystem", target_type="mixed",
            offcampus_pbd_revenue_mm=100.0,
            category_revenue_share={
                SiteNeutralCategory.DRUG_ADMINISTRATION: 0.20,
            },
            medicare_share=0.40,
            hospital_ebitda_margin=0.18,
            asc_cbsa="26420",
            asc_capacity_share=0.40,
            asc_competitors=[
                HospitalCompetitor(
                    company_name="Other", cbsa="26420",
                    affected_revenue_mm=5.0)],
        )
        self.assertIsNotNone(impact.hospital_risk)
        self.assertIsNotNone(impact.asc_opportunity)
        # Notes string populated for mixed targets
        self.assertGreater(len(impact.notes), 0)


if __name__ == "__main__":
    unittest.main()
