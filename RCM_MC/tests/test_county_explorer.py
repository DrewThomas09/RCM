"""County Explorer (/county-explorer): real county-level demographics drill-down
for a state. Guards the new loader function, state/sort validation, real-value
rows, sort behavior, the weighted footer, CSV export, and GREEN classification.
"""
import unittest

from rcm_mc.data import county_demographics as _d
from rcm_mc.diligence.surface_status import classify_surface
from rcm_mc.ui.data_public.county_explorer_page import (
    _DEFAULT,
    _DEFAULT_SORT,
    _parse_sort,
    _parse_state,
    county_dataframe,
    explorer_rows,
    render_county_explorer,
)


class CountyExplorerTests(unittest.TestCase):
    def test_loader_lists_state_counties(self):
        oh = _d.counties_for_state("OH")
        self.assertGreater(len(oh), 80)  # Ohio has 88 counties
        self.assertEqual(_d.counties_for_state("ZZ"), [])

    def test_parse_validates(self):
        self.assertEqual(_parse_state({"state": ["tx"]}), "TX")
        self.assertEqual(_parse_state({"state": ["ZZ"]}), _DEFAULT)
        self.assertEqual(_parse_sort({"sort": ["bogus"]}), _DEFAULT_SORT)
        self.assertEqual(_parse_sort({"sort": ["uninsured_rate"]}), "uninsured_rate")

    def test_rows_sorted_and_real(self):
        rows, footer = explorer_rows("OH", "population")
        self.assertGreater(len(rows), 80)
        pops = [r["population"] for r in rows if r["population"] is not None]
        self.assertEqual(pops, sorted(pops, reverse=True))  # high→low
        # footer total population is the sum of county populations
        self.assertAlmostEqual(footer["population"], sum(pops), delta=1)
        # weighted uninsured rate sits within the per-county min/max
        urs = [r["uninsured_rate"] for r in rows if r["uninsured_rate"] is not None]
        self.assertTrue(min(urs) <= footer["uninsured_rate"] <= max(urs))

    def test_csv_export(self):
        df = county_dataframe("OH", "population")
        self.assertEqual(df.columns[0], "County")
        self.assertIn("Median HH income", df.columns)
        self.assertGreater(len(df), 80)

    def test_page_renders(self):
        h = render_county_explorer({"state": ["OH"]})
        self.assertIn("County Explorer", h)
        self.assertIn("Ohio", h)
        self.assertIn("<table", h)
        self.assertIn("fabricated", h)

    def test_surface_is_green(self):
        self.assertEqual(classify_surface("/county-explorer")["tier"], "green")


if __name__ == "__main__":
    unittest.main()
