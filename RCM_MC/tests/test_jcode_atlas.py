"""J-Code Atlas — infusion J-codes by site of care + the change, tied
to disease.

The catalog codes/descriptors are public CMS facts; the site-of-care mix
and its change come from labeled archetype anchors and patient pools are
real-geography × published epi anchors, so every derived figure
recomputes and audits cleanly.
"""
from __future__ import annotations

import unittest

from rcm_mc.data.infusion_jcodes import (
    SOC_NOW_YEAR, SOC_THEN_YEAR, disease_index, jcode_by_code, jcode_catalog,
    site_archetypes,
)
from rcm_mc.diligence.jcode_atlas import (
    SITES, jcode_atlas, jcode_disease_tie, jcode_scan_dataframe,
    jcode_site_of_care_scan,
)
from rcm_mc.ui.jcode_atlas_page import render_jcode_atlas_page


class CatalogTests(unittest.TestCase):
    def test_catalog_is_substantial_and_well_formed(self):
        cat = jcode_catalog()
        # The whole point was "use ALL the j codes" — far beyond the old 12.
        self.assertGreaterEqual(len(cat), 40)
        codes = [c["hcpcs"] for c in cat]
        self.assertEqual(len(codes), len(set(codes)), "duplicate J-codes")
        arch_keys = set(site_archetypes())
        for c in cat:
            for field in ("hcpcs", "drug", "unit", "drug_class", "soc",
                          "diseases", "icd10", "epi_per_100k", "epi_basis",
                          "denominator"):
                self.assertIn(field, c, f"{c.get('hcpcs')} missing {field}")
            self.assertIn(c["soc"], arch_keys,
                          f"{c['hcpcs']} references unknown archetype")
            self.assertTrue(c["diseases"], f"{c['hcpcs']} has no disease tie")
            self.assertIn(c["denominator"], ("population", "seniors"))
            self.assertGreater(float(c["epi_per_100k"]), 0)

    def test_archetype_shares_sum_to_one(self):
        for key, a in site_archetypes().items():
            for anchor in ("then", "now"):
                total = sum(a[anchor][s] for s in SITES)
                self.assertAlmostEqual(total, 1.0, places=2,
                                       msg=f"{key}.{anchor} != 1.0")

    def test_lookup_and_disease_index(self):
        self.assertIsNone(jcode_by_code("NOPE9999"))
        ivig = jcode_by_code("j1569")  # case-insensitive
        self.assertEqual(ivig["drug_class"], "Immune globulin (IVIG)")
        idx = disease_index()
        # A common autoimmune indication is treated by several codes.
        self.assertGreaterEqual(len(idx.get("Rheumatoid arthritis", [])), 3)


class ScanTests(unittest.TestCase):
    def setUp(self):
        self.scan = jcode_site_of_care_scan(population=31_000_000)

    def test_one_row_per_code_ranked_by_migration(self):
        self.assertEqual(len(self.scan), len(jcode_catalog()))
        ooh = [r["out_of_hospital_pts"] for r in self.scan]
        self.assertEqual(ooh, sorted(ooh, reverse=True))
        self.assertEqual([r["migration_rank"] for r in self.scan],
                         list(range(1, len(self.scan) + 1)))

    def test_change_is_now_minus_then(self):
        for r in self.scan:
            for s in SITES:
                expect = round((r["site_mix_now"][s]
                                - r["site_mix_then"][s]) * 100, 1)
                self.assertAlmostEqual(r["change"]["delta_pts"][s], expect,
                                       places=1)
            # Out-of-hospital = home+office+aic gain = -hopd delta (shares
            # sum to 1), within rounding.
            self.assertAlmostEqual(
                r["out_of_hospital_pts"],
                -r["change"]["delta_pts"]["hopd"], delta=0.2)

    def test_patient_pool_scales_with_geography(self):
        small = jcode_site_of_care_scan(population=1_000_000)
        big = jcode_site_of_care_scan(population=10_000_000)
        s0 = {r["hcpcs"]: r["estimated_patients"] for r in small}
        for r in big:
            # 10x population → ~10x pool (allow rounding on tiny pools).
            self.assertAlmostEqual(r["estimated_patients"],
                                   s0[r["hcpcs"]] * 10, delta=10)

    def test_offline_asp_is_none_not_fabricated(self):
        # No fetch_live → no fabricated dollar value.
        for r in self.scan:
            self.assertIsNone(r["asp_payment_limit_per_unit"])
            self.assertFalse(r["asp_live"])


class DiseaseTieTests(unittest.TestCase):
    def test_pool_is_max_not_sum(self):
        scan = jcode_site_of_care_scan(population=31_000_000)
        tie = jcode_disease_tie(scan=scan)
        by_code = {r["hcpcs"]: r for r in scan}
        for d in tie:
            pools = [by_code[c]["estimated_patients"] for c in d["codes"]]
            # Conservative: the disease pool is the largest single code,
            # never the (double-counting) sum of overlapping brands.
            self.assertEqual(d["estimated_pool"], max(pools))
            self.assertIn(d["dominant_site"], SITES)
        ranks = [d["rank"] for d in tie]
        self.assertEqual(ranks, list(range(1, len(tie) + 1)))


class AtlasTests(unittest.TestCase):
    def setUp(self):
        self.a = jcode_atlas(population=31_000_000)

    def test_summary_shape(self):
        s = self.a["summary"]
        self.assertEqual(s["n_codes"], len(jcode_catalog()))
        self.assertGreater(s["n_diseases"], s["n_codes"] // 2)
        self.assertGreaterEqual(s["n_migrating_home"], 1)
        self.assertEqual(self.a["then_year"], SOC_THEN_YEAR)
        self.assertEqual(self.a["now_year"], SOC_NOW_YEAR)

    def test_book_mix_is_a_distribution(self):
        s = self.a["summary"]
        self.assertAlmostEqual(sum(s["book_mix_now"].values()), 1.0, places=2)
        self.assertAlmostEqual(sum(s["book_mix_then"].values()), 1.0, places=2)
        # The whole book has migrated out of the hospital on net.
        self.assertGreater(s["out_of_hospital_gain_pts"], 0)
        self.assertGreater(s["home_office_now"], s["home_office_then"])

    def test_top_movers_present(self):
        self.assertTrue(self.a["summary"]["top_movers"])
        for m in self.a["summary"]["top_movers"]:
            self.assertIn("hcpcs", m)
            self.assertIn("out_of_hospital_pts", m)

    def test_default_us_geography(self):
        a = jcode_atlas()  # no population
        self.assertTrue(a["geography"]["is_default_us"])


class OpportunityTests(unittest.TestCase):
    def setUp(self):
        self.scan = jcode_site_of_care_scan(population=31_000_000)

    def test_every_code_scored_0_to_100(self):
        for r in self.scan:
            self.assertIn("home_shift_opportunity", r)
            self.assertGreaterEqual(r["home_shift_opportunity"], 0.0)
            self.assertLessEqual(r["home_shift_opportunity"], 100.0)
            self.assertEqual(set(r["opportunity_axes"]),
                             {"demand", "momentum", "runway"})

    def test_office_bound_code_scores_below_a_migrating_anchor(self):
        # An office-fixed intravitreal code (no migration, no HOPD runway)
        # must rank below a high-pool, fast-migrating immunology anchor.
        by_code = {r["hcpcs"]: r for r in self.scan}
        eylea = by_code["J0178"]            # office_injectable, ~no migration
        remicade = by_code["J1745"]         # immunology_steered, big pool
        self.assertLess(eylea["home_shift_opportunity"],
                        remicade["home_shift_opportunity"])

    def test_summary_top_opportunities_ranked(self):
        a = jcode_atlas(population=31_000_000)
        opps = a["summary"]["top_opportunities"]
        self.assertTrue(opps)
        scores = [o["score"] for o in opps]
        self.assertEqual(scores, sorted(scores, reverse=True))
        # The weights are exposed for auditability and sum to 1.
        self.assertAlmostEqual(sum(a["opportunity_weights"].values()), 1.0,
                               places=3)


class DataframeTests(unittest.TestCase):
    def test_one_row_per_code_with_flat_columns(self):
        df = jcode_scan_dataframe(population=31_000_000)
        self.assertEqual(len(df), len(jcode_catalog()))
        for col in ("hcpcs", "drug", "primary_disease", "home_pct_now",
                    "hopd_pct_now", "out_of_hospital_pts",
                    "estimated_patients", "home_shift_opportunity"):
            self.assertIn(col, df.columns)
        # No nested objects leaked into the flat export.
        for v in df["primary_disease"]:
            self.assertIsInstance(v, str)


class PageTests(unittest.TestCase):
    def test_page_renders(self):
        html = render_jcode_atlas_page({})
        self.assertIn("J-Code Atlas", html)
        self.assertIn("Site-of-care scan", html)
        self.assertIn("tied to disease", html)
        # A couple of real codes appear.
        self.assertIn("J1569", html)
        self.assertIn("J9271", html)

    def test_pop_scaling_in_meta(self):
        html = render_jcode_atlas_page({"pop": ["31000000"]})
        self.assertIn("31.0M population", html)

    def test_opportunity_scatter_and_export_present(self):
        html = render_jcode_atlas_page({"pop": ["31000000"]})
        self.assertIn("Home-shift roll-up targets", html)
        self.assertIn("Where is the volume", html)
        # CSV export + sibling cross-links, with the geography carried.
        self.assertIn("/api/diligence/jcode-atlas/export.csv?pop=31000000",
                      html)
        self.assertIn("/diligence/texas-infusion", html)
        self.assertIn("/diligence/infusion-markets", html)


if __name__ == "__main__":
    unittest.main()
