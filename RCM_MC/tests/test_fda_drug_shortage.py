"""openFDA drug-shortage snapshot — loader + LIVE page section.

Build-time public-domain snapshot (no runtime API). The Drug Shortage page now
leads with the real FDA shortage landscape; the supplier/GPO model is scoped
illustrative below.
"""
import unittest

from rcm_mc.data import drug_shortage_data as ds
from rcm_mc.ui.data_public.drug_shortage_page import render_drug_shortage


class TestFdaDrugShortageLoader(unittest.TestCase):
    def test_snapshot_loads(self):
        df = ds.load_drug_shortages()
        self.assertGreater(len(df), 1000)
        for c in ("generic_name", "therapeutic_category", "status"):
            self.assertIn(c, df.columns)

    def test_summary_counts(self):
        s = ds.drug_shortage_summary()
        self.assertGreater(s["current"], 100)
        self.assertGreater(s["categories"], 10)
        self.assertTrue(s["snapshot_date"])

    def test_categories_and_search(self):
        cats = ds.shortages_by_category(current_only=True)
        self.assertTrue(cats and cats[0]["n"] >= cats[-1]["n"])   # ranked desc
        hit = ds.current_shortages(search="morphine")
        self.assertTrue((hit["generic_name"].str.lower().str.contains("morphine")).any())

    def test_registry_entry(self):
        self.assertTrue(ds.drug_shortage_sources())

    def test_no_runtime_network_constant(self):
        # Loader path reads a local CSV; the module must not import urllib/requests.
        import inspect
        src = inspect.getsource(ds)
        self.assertNotIn("urllib", src)
        self.assertNotIn("requests", src)


class TestDrugShortagePageLive(unittest.TestCase):
    def test_live_section_present(self):
        h = render_drug_shortage({})
        self.assertIn("FDA Drug Shortages · LIVE (openFDA)", h)
        self.assertIn("current shortages across", h)
        self.assertIn("product-level, not provider-specific", h)

    def test_illustrative_model_scoped(self):
        h = render_drug_shortage({})
        self.assertIn("Illustrative supply-chain planning model", h)
        self.assertIn("ck-illus-note", h)

    def test_drug_search(self):
        h = render_drug_shortage({"drug": "cisplatin"})
        self.assertIn("isplatin", h)


if __name__ == "__main__":
    unittest.main()
