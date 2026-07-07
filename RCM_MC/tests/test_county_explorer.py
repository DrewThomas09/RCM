"""County Explorer (/county-explorer): real county-level demographics drill-down
for a state. Guards the new loader function, state/sort validation, real-value
rows, sort behavior, the weighted footer, CSV export, GREEN classification,
and the P13 insight bullets (figures re-derived exactly; trivia suppressed).
"""
import unittest

from rcm_mc.data import county_demographics as _d
from rcm_mc.diligence.surface_status import classify_surface
from rcm_mc.ui.data_public.county_explorer_page import (
    _DEFAULT,
    _DEFAULT_SORT,
    _county_insights,
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

    def test_page_leads_with_real_kpi_strip(self):
        # X-Ray pattern: leading KPI strip from the real county data
        # (counties / total population / largest county).
        h = render_county_explorer({"state": ["OH"]})
        self.assertIn("ck-kpi-strip", h)
        self.assertIn("Counties", h)
        self.assertIn("Total population", h)
        self.assertIn("Largest county", h)

    def test_surface_is_green(self):
        self.assertEqual(classify_surface("/county-explorer")["tier"], "green")


class CountyInsightTests(unittest.TestCase):
    """P13 bullets (backlog #34): every figure in a bullet is re-derived
    here from the SAME rows/footer the table renders — never a second
    data path — and the significance guards suppress trivia."""

    @staticmethod
    def _wtd_mean(rows, key):
        # Independent recomputation of the page's footer stat: the
        # population-weighted mean over counties carrying both values.
        num = sum(r[key] * r["population"] for r in rows
                  if r.get(key) is not None and r.get("population"))
        den = sum(r["population"] for r in rows
                  if r.get(key) is not None and r.get("population"))
        return num / den

    def test_aged_and_uninsured_bullets_rederive_exactly(self):
        rows, _footer = explorer_rows("OH", "population")
        h = render_county_explorer({"state": ["OH"]})
        self.assertIn("Ohio counties — the read", h)
        top_aged = max(((r["name"], r["pct_age_65_plus"]) for r in rows
                        if r["pct_age_65_plus"] is not None),
                       key=lambda x: x[1])
        self.assertIn(top_aged[0], h)
        self.assertIn(f"{top_aged[1]*100:.1f}% 65+", h)
        self.assertIn(
            f"{self._wtd_mean(rows, 'pct_age_65_plus')*100:.1f}% state "
            f"weighted mean", h)
        hi_un = max(((r["name"], r["uninsured_rate"]) for r in rows
                     if r["uninsured_rate"] is not None),
                    key=lambda x: x[1])
        self.assertIn(hi_un[0], h)
        self.assertIn(f"at {hi_un[1]*100:.1f}% vs the "
                      f"{self._wtd_mean(rows, 'uninsured_rate')*100:.1f}% "
                      f"state weighted mean", h)

    def test_concentration_bullet_rederives_exactly(self):
        # Maricopa holds well over the 20%-share guard in AZ.
        rows, _footer = explorer_rows("AZ", "population")
        total = sum(r["population"] for r in rows if r["population"])
        top = max((r for r in rows if r["population"]),
                  key=lambda r: r["population"])
        h = render_county_explorer({"state": ["AZ"]})
        share = top["population"] / total
        self.assertGreaterEqual(share, 0.20)   # the guard this bullet passed
        self.assertIn(f"{share*100:.1f}% of Arizona", h)
        self.assertIn(top["name"], h)

    def test_concentration_guard_suppresses_ohio(self):
        # Franklin County is ~11% of Ohio — below the 20% share guard, so
        # the bullet must NOT render even though the aged/uninsured ones do.
        rows, _footer = explorer_rows("OH", "population")
        total = sum(r["population"] for r in rows if r["population"])
        top = max((r for r in rows if r["population"]),
                  key=lambda r: r["population"])
        self.assertLess(top["population"] / total, 0.20)
        self.assertNotIn("metro-first entry math", render_county_explorer(
            {"state": ["OH"]}))

    def test_tiny_deltas_suppressed(self):
        # 0.4pp tails over the state mean: every guard fails → no bullets.
        rows = [{"name": f"C{i}", "population": 100_000.0,
                 "pct_age_65_plus": 0.180, "uninsured_rate": 0.080,
                 "median_household_income": 60_000.0,
                 "child_poverty_rate": 0.15, "pct_rural": 0.4}
                for i in range(10)]
        rows[0]["pct_age_65_plus"] = 0.184
        rows[0]["uninsured_rate"] = 0.084
        footer = {"population": 1_000_000.0,
                  "pct_age_65_plus": self._wtd_mean(rows, "pct_age_65_plus"),
                  "uninsured_rate": self._wtd_mean(rows, "uninsured_rate")}
        self.assertEqual(_county_insights(rows, footer, "Testland"), "")

    def test_empty_and_thin_data_render_nothing(self):
        # No rows → no bullets, no crash, no empty section shell.
        self.assertEqual(_county_insights([], {}, "Testland"), "")
        # Real thin-data path: Delaware has 3 counties (< the n≥8 floor),
        # so the page carries no insights block at all.
        h = render_county_explorer({"state": ["DE"]})
        self.assertNotIn("ck-insights", h)
        self.assertNotIn("counties — the read", h)


if __name__ == "__main__":
    unittest.main()
