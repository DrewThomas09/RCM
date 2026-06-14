"""Golden test for NEW-07 provider density.

Hand-counted fixture across 3 counties:
    06037 -> 5 providers, 36061 -> 3 providers, 48201 -> 2 providers (total 10)
    With population, density per 100k = count / pop * 100000.
Renders on two geographies (FIPS and CBSA). Suppression hides small cells.
"""
import unittest

from rcm_mc.cdd.provider_density import provider_density


def _fips_set():
    return (
        [{"npi": f"L{i}", "fips": "06037"} for i in range(5)]
        + [{"npi": f"N{i}", "fips": "36061"} for i in range(3)]
        + [{"npi": f"H{i}", "fips": "48201"} for i in range(2)]
    )


class TestProviderDensity(unittest.TestCase):
    def test_per_fips_counts(self):
        ex = provider_density(_fips_set(), by="fips", suppress=False,
                              source="Golden", vintage="2026")
        c = ex.meta["counts"]
        self.assertEqual(c["06037"], 5)
        self.assertEqual(c["36061"], 3)
        self.assertEqual(c["48201"], 2)
        self.assertEqual(ex.meta["total"], 10)
        self.assertTrue(ex.reconciled)

    def test_density_per_100k(self):
        pop = {"06037": 1_000_000, "36061": 600_000, "48201": 200_000}
        ex = provider_density(_fips_set(), by="fips", population=pop, suppress=False,
                              source="Golden", vintage="2026")
        layer = {g["geo"]: g for g in ex.meta["geo_layer"]}
        self.assertAlmostEqual(layer["06037"]["density_per_100k"], 0.5, delta=1e-9)
        self.assertAlmostEqual(layer["48201"]["density_per_100k"], 1.0, delta=1e-9)

    def test_renders_on_cbsa_geography(self):
        rows = (
            [{"npi": f"a{i}", "cbsa": "31080"} for i in range(4)]
            + [{"npi": f"b{i}", "cbsa": "35620"} for i in range(6)]
        )
        ex = provider_density(rows, by="cbsa", suppress=False, source="Golden", vintage="2026")
        self.assertEqual(ex.meta["counts"]["31080"], 4)
        self.assertEqual(ex.meta["counts"]["35620"], 6)
        self.assertIn("cbsa", ex.render()["title"])

    def test_suppression_respected(self):
        ex = provider_density(_fips_set(), by="fips", suppress=True,
                              suppression_threshold=11, source="Golden", vintage="2026")
        # All cells <= 11, so all suppressed.
        self.assertIn("cells_suppressed", ex.flag_codes())
        for g in ex.meta["geo_layer"]:
            self.assertTrue(g["suppressed"])
            self.assertIsNone(g["count"])
        # Reconciliation still ties out on raw counts.
        self.assertTrue(ex.reconciled)

    def test_partner_hides_raw_geo_layer(self):
        ex = provider_density(_fips_set(), by="fips", suppress=False,
                              source="Golden", vintage="2026")
        partner = {s["name"] for s in ex.render(internal_mode=False)["series"]}
        self.assertNotIn("Raw geo layer", partner)

    def test_dedupe_same_npi(self):
        rows = [{"npi": "X", "fips": "06037"}, {"npi": "X", "fips": "06037"},
                {"npi": "Y", "fips": "06037"}]
        ex = provider_density(rows, by="fips", suppress=False, source="Golden", vintage="2026")
        self.assertEqual(ex.meta["counts"]["06037"], 2)

    def test_invalid_by_raises(self):
        with self.assertRaises(ValueError):
            provider_density(_fips_set(), by="zip")


if __name__ == "__main__":
    unittest.main()
