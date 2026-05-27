"""Metro Markets (/metro-markets): the real CBSA-level analyzer on the OMB
crosswalk × county ACS layer. Guards sort/type validation, real ranked rows,
CSV export, and GREEN classification.
"""
import unittest

from rcm_mc.diligence.surface_status import classify_surface
from rcm_mc.ui.data_public.metro_markets_page import (
    _DEFAULT_SORT,
    _parse_sort,
    _parse_type,
    metro_dataframe,
    metro_rows,
    render_metro_markets,
)


class MetroMarketsTests(unittest.TestCase):
    def test_parse_validates(self):
        self.assertEqual(_parse_sort({"sort": ["uninsured_rate"]}), "uninsured_rate")
        self.assertEqual(_parse_sort({"sort": ["bogus"]}), _DEFAULT_SORT)
        self.assertEqual(_parse_type({"type": ["micropolitan"]}), "Micropolitan")
        self.assertEqual(_parse_type({"type": ["bogus"]}), "Metropolitan")

    def test_rows_sorted_real_and_nyc_top(self):
        rows = metro_rows("Metropolitan", "population")
        self.assertGreater(len(rows), 50)
        pops = [r["population"] for r in rows]
        self.assertEqual(pops, sorted(pops, reverse=True))
        self.assertIn("New York", rows[0]["cbsa_title"])  # largest metro
        self.assertGreater(rows[0]["population"], 18_000_000)

    def test_csv_export(self):
        df = metro_dataframe("Metropolitan", "population")
        self.assertEqual(list(df.columns)[:3], ["CBSA", "Type", "Counties"])
        self.assertIn("Median HH income", df.columns)
        self.assertGreater(len(df), 100)

    def test_page_renders(self):
        h = render_metro_markets({"type": ["Metropolitan"]})
        self.assertIn("Metro Markets", h)
        self.assertIn("<table", h)
        self.assertIn("estimate", h)  # income-estimate honesty
        self.assertIn("fabricated", h)

    def test_page_leads_with_real_kpi_strip(self):
        # X-Ray pattern: leading KPI strip from the real CBSA rows
        # (area count / population covered / largest market).
        h = render_metro_markets({"type": ["Metropolitan"]})
        self.assertIn("ck-kpi-strip", h)
        self.assertIn("Population covered", h)
        self.assertIn("Largest market", h)

    def test_surface_is_green(self):
        self.assertEqual(classify_surface("/metro-markets")["tier"], "green")


if __name__ == "__main__":
    unittest.main()
