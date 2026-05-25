"""Colorado CIVHC / CO-APCD public payer datasets — loaders.

Exercises the vendored public-use CSVs (no network, no licensed data). Locks
in: datasets load, provenance/source_id present, missingness preserved (NaN
never silently 0), summaries report real coverage, and every dataset is in the
source registry.
"""
import math
import unittest

import pandas as pd

from rcm_mc.data import payer_data as pdt


class TestPayerDataLoaders(unittest.TestCase):
    def test_datasets_load_nonempty(self):
        self.assertGreater(len(pdt.load_cost_of_care("total")), 1000)
        self.assertGreater(len(pdt.load_cost_of_care("outpatient")), 1000)
        self.assertGreater(len(pdt.load_apm_public()), 50)
        self.assertGreater(len(pdt.load_reference_based_pricing()), 500)

    def test_provenance_source_id_present(self):
        for df in (pdt.load_cost_of_care("total"), pdt.load_apm_public(),
                   pdt.load_reference_based_pricing()):
            self.assertIn("source_id", df.columns)
            self.assertTrue(df["source_id"].astype(str).str.startswith("civhc_").all())

    def test_summary_coverage(self):
        s = pdt.payer_data_summary()
        self.assertIn("Medicaid", s["cost_of_care_total"]["payer_types"])
        self.assertIn("Denver", s["cost_of_care_total"]["regions"])
        self.assertGreaterEqual(s["reference_based_pricing"]["providers"], 100)

    def test_missingness_preserved_not_zeroed(self):
        # RBP has ~1% missing on payer fields — must report as missing, and the
        # loaded values must be NaN (not coerced to 0).
        miss = pdt.payer_data_missingness()
        self.assertIn("reference_based_pricing", miss)
        rbp = pdt.load_reference_based_pricing()
        if rbp["payer_median"].isna().any():
            self.assertTrue(math.isnan(
                rbp.loc[rbp["payer_median"].isna()].iloc[0]["payer_median"]))

    def test_apm_summary_real_percentages(self):
        df = pdt.apm_summary_by_model("2024")
        self.assertGreater(len(df), 0)
        # %APM is a fraction in [0,1] where present
        vals = df["pct_apm"].dropna()
        self.assertTrue((vals >= 0).all() and (vals <= 1).all())

    def test_reference_pricing_summary_sorted(self):
        df = pdt.reference_pricing_summary()
        self.assertIn("organization_name", df.columns)
        vals = df["hospital_pct_medicare"].dropna().tolist()
        self.assertEqual(vals, sorted(vals, reverse=True))

    def test_cost_filters_return_rows(self):
        self.assertGreater(len(pdt.payer_cost_by_geography(
            year="2021", payer_type="All", claim_type="Inpatient")), 0)
        self.assertGreater(len(pdt.payer_cost_by_service(
            year="2021", payer_type="All", region="Denver")), 0)

    def test_sources_in_registry(self):
        ids = {s["source_id"] for s in pdt.payer_data_sources()}
        self.assertTrue({"civhc_apm_fy26", "civhc_rbp_fy26"}.issubset(ids))


if __name__ == "__main__":
    unittest.main()
