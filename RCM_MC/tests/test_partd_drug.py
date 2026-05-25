"""CMS Part D Spending by Drug aggregate loader — committed data + shape."""
import unittest

from rcm_mc.data import partd_drug as d


class PartDDrugTests(unittest.TestCase):
    def test_summary_plausible(self):
        s = d.partd_drug_summary()
        self.assertTrue(s, "summary missing — run scripts/ingest_partd_drug_spending.py")
        self.assertGreater(s["drugs"], 2000)
        # 2023 Part D drug spend is a few hundred $B
        self.assertTrue(1e11 < s["total_spending_2023"] < 5e11, s["total_spending_2023"])
        self.assertIsNotNone(s["median_price_cagr_19_23"])

    def test_top_spend(self):
        top = d.top_drugs_by_spend(10)
        self.assertEqual(len(top), 10)
        # descending by spend
        sp = [r["spend_2023"] for r in top]
        self.assertEqual(sp, sorted(sp, reverse=True))
        self.assertTrue(all(r.get("brand") for r in top))

    def test_top_inflation_descending(self):
        infl = d.top_drugs_by_price_inflation(10)
        self.assertEqual(len(infl), 10)
        cg = [r["price_cagr_19_23"] for r in infl if r["price_cagr_19_23"] is not None]
        self.assertEqual(cg, sorted(cg, reverse=True))

    def test_registry(self):
        rows = d.partd_drug_sources()
        self.assertTrue(rows)
        self.assertEqual(rows[0]["source_id"], "cms_partd_drug_spending")


if __name__ == "__main__":
    unittest.main()
