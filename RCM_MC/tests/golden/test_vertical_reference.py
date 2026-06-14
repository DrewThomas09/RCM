"""Golden test for REF-01..04 healthcare vertical reference layer.

Hand-verified anchors:

    REF-01 price ladder (RAND PT5.1, 2022 data):
        HOPD 279, inpatient 254, blended 254, professional 184, ASC 170.
        Reconciliation: blended (254) == inpatient (254).

    REF-02 wRVU (MGMA): GI median 8700 wRVU; implied comp per wRVU
        512500 / 8700 = 58.908..., reported band midpoint 61, ties within 5.

    REF-03 RCM KPI (HFMA): optimal clean-claim 95 + optimal denial 5 == 100.

    REF-04 catalog: Fresenius implied margin (353 - 282) / 353 * 100 =
        20.113..., reported 19, ties within 1.5. Dermatology, urgent care,
        and imaging headline figures are tier 3 and must be flagged.
"""
import unittest

from rcm_mc.cdd import registry
from rcm_mc.cdd.vertical_reference import (
    FEATURE_PRICE_LADDER,
    FEATURE_RCM_KPI,
    FEATURE_VERTICAL_CATALOG,
    FEATURE_WRVU,
    TIER_REQUIRES_VERIFICATION,
    get_vertical,
    price_ladder,
    rcm_kpis,
    vertical_catalog,
    verticals,
    wrvu_percentiles,
)


class TestPriceLadder(unittest.TestCase):
    def test_ladder_values(self):
        ex = price_ladder()
        ladder = {p["label"]: p["value"] for p in ex.meta["ladder"]}
        self.assertEqual(ladder["Hospital outpatient facility"], 279.0)
        self.assertEqual(ladder["ASC common outpatient surgery"], 170.0)

    def test_blended_reconciles_to_inpatient(self):
        ex = price_ladder()
        self.assertTrue(ex.reconciled)
        recon = ex.reconciliations[0]
        self.assertEqual(recon.lhs, recon.rhs)

    def test_drug_basis_is_internal_only(self):
        ex = price_ladder()
        partner = {s["name"] for s in ex.render(internal_mode=False)["series"]}
        self.assertNotIn("Physician-administered drug basis (ASP)", partner)
        internal = {s["name"] for s in ex.render(internal_mode=True)["series"]}
        self.assertIn("Physician-administered drug basis (ASP)", internal)


class TestWrvu(unittest.TestCase):
    def test_gi_comp_per_wrvu_reconciles(self):
        ex = wrvu_percentiles()
        self.assertTrue(ex.reconciled)
        self.assertAlmostEqual(ex.meta["gi_implied_comp_per_wrvu"],
                               512_500.0 / 8700.0, delta=1e-9)

    def test_radiology_leads_productivity(self):
        rows = {r["specialty"]: r["median_wrvu"] for r in wrvu_percentiles().meta["rows"]}
        self.assertEqual(max(rows.values()), rows["Radiology"])
        self.assertGreater(rows["Gastroenterology"], rows["Family medicine"])


class TestRcmKpis(unittest.TestCase):
    def test_clean_claim_plus_denial_identity(self):
        ex = rcm_kpis()
        self.assertTrue(ex.reconciled)
        recon = ex.reconciliations[0]
        self.assertAlmostEqual(recon.lhs, 100.0, delta=1e-9)

    def test_denial_target_present(self):
        kpis = {k["kpi"]: k["target"] for k in rcm_kpis().meta["kpis"]}
        self.assertEqual(kpis["Initial denial rate"], 5.0)
        self.assertEqual(kpis["Clean claim first-pass rate"], 95.0)


class TestVerticalCatalog(unittest.TestCase):
    def test_fresenius_margin_reconciles(self):
        ex = vertical_catalog()
        self.assertTrue(ex.reconciled)
        self.assertAlmostEqual(ex.meta["fresenius_implied_margin"],
                               (353.0 - 282.0) / 353.0 * 100.0, delta=1e-9)

    def test_tier3_headlines_flagged(self):
        ex = vertical_catalog()
        self.assertIn("headline_requires_verification", ex.flag_codes())
        flagged = {v.name for v in verticals()
                   if v.headline.tier == TIER_REQUIRES_VERIFICATION}
        # Dermatology, urgent care, and imaging lead with a tier-3 figure.
        self.assertIn("Dermatology", flagged)
        self.assertIn("Imaging and Radiology Centers", flagged)

    def test_detail_is_internal_only(self):
        ex = vertical_catalog()
        partner = {s["name"] for s in ex.render(internal_mode=False)["series"]}
        self.assertNotIn("Full vertical metric detail", partner)

    def test_every_metric_carries_source_and_tier(self):
        for v in verticals():
            for m in [v.headline, *v.metrics]:
                self.assertTrue(m.source, f"{v.key} metric missing source")
                self.assertTrue(m.vintage, f"{v.key} metric missing vintage")
                self.assertIn(m.tier, (1, 2, 3))

    def test_get_vertical_lookup(self):
        self.assertEqual(get_vertical("dialysis").name, "Dialysis")
        with self.assertRaises(KeyError):
            get_vertical("does-not-exist")


class TestRegistryWiring(unittest.TestCase):
    def test_all_ref_features_registered(self):
        ids = set(registry.feature_ids())
        for fid in (FEATURE_PRICE_LADDER, FEATURE_WRVU, FEATURE_RCM_KPI,
                    FEATURE_VERTICAL_CATALOG):
            self.assertIn(fid, ids)

    def test_features_render_both_audiences(self):
        for fid in (FEATURE_PRICE_LADDER, FEATURE_WRVU, FEATURE_RCM_KPI,
                    FEATURE_VERTICAL_CATALOG):
            partner = registry.run(fid, internal_mode=False)
            internal = registry.run(fid, internal_mode=True)
            self.assertEqual(partner["feature_id"], fid)
            self.assertNotIn("assumptions", partner)
            self.assertIn("assumptions", internal)


if __name__ == "__main__":
    unittest.main()
