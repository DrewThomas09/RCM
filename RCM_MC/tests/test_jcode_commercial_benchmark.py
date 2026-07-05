"""Tests for the J-code commercial benchmark (2022-2026) surface.

The benchmark is built from PUBLIC anchors only — Merative MarketScan is
licensed and not vendored. These tests assert no commercial-claims
dollars are invented, that the multiples are the published values, and
that the biosimilar-driven year index behaves correctly.
"""
import unittest

from rcm_mc.diligence.jcode_commercial_benchmark import (
    YEARS,
    jcode_commercial_benchmark,
    marketscan_ingest_schema,
)


class BenchmarkDataTests(unittest.TestCase):
    def setUp(self):
        self.b = jcode_commercial_benchmark()

    def test_years_span_2022_to_2026(self):
        self.assertEqual(self.b["years"], [2022, 2023, 2024, 2025, 2026])
        self.assertEqual(YEARS, [2022, 2023, 2024, 2025, 2026])

    def test_each_jcode_has_an_index_for_every_year(self):
        for r in self.b["jcodes"]:
            self.assertEqual(set(r["index_by_year"]), set(YEARS))
            for y in YEARS:
                self.assertGreater(r["index_by_year"][y], 0)

    def test_published_multiples_are_real_values(self):
        by = {m["source"]: m["multiple"] for m in self.b["multiples"]}
        self.assertEqual(by["HCCI"], 1.22)
        self.assertEqual(by["Milliman"], 1.48)
        band = self.b["multiple_band"]
        self.assertEqual(band["lo"], 1.22)
        self.assertEqual(band["hi"], 1.48)

    def test_biosimilar_molecules_erode_after_entry(self):
        # A molecule with a biosimilar entry inside the window must show a
        # lower index at 2026 than before entry.
        nat = next(r for r in self.b["jcodes"] if r["hcpcs"] == "J2323")
        self.assertEqual(nat["biosimilar_entry"], 2024)
        self.assertEqual(nat["index_by_year"][2023], 100.0)  # pre-entry
        self.assertLess(nat["index_by_year"][2026], 100.0)   # eroded
        self.assertLess(nat["change_22_26"], 0)

    def test_sole_source_holds_and_ivig_rises(self):
        entv = next(r for r in self.b["jcodes"] if r["hcpcs"] == "J3380")
        self.assertEqual(entv["trend"], "stable")
        self.assertEqual(entv["change_22_26"], 0.0)
        ivig = next(r for r in self.b["jcodes"] if r["hcpcs"] == "J1569")
        self.assertEqual(ivig["trend"], "rising")
        self.assertGreater(ivig["change_22_26"], 0)

    def test_marketscan_schema_documents_the_load_slot(self):
        sch = marketscan_ingest_schema()
        self.assertIn("marketscan", sch["filename"])
        self.assertIn("mean_allowed_per_unit", sch["columns"])


class BenchmarkPageTests(unittest.TestCase):
    def test_page_renders_heatmap_and_marketscan_note(self):
        from rcm_mc.ui.texas_infusion_jcode_benchmark_page import (
            render_texas_infusion_jcode_benchmark_page)
        h = render_texas_infusion_jcode_benchmark_page()
        for needle in (
                "J-code commercial benchmark", "Merative MarketScan",
                "Commercial-as-%-of-Medicare", "benchmark heatmap",
                "Rituximab", "jcode-benchmark.csv"):
            self.assertIn(needle, h, needle)
        self.assertGreaterEqual(h.count("<svg"), 1)

    def test_no_fabricated_dollar_claims_in_year_cells(self):
        # The page expresses the year trajectory as an index, not as
        # invented commercial-claims dollars. The methodology must say so.
        from rcm_mc.ui.texas_infusion_jcode_benchmark_page import (
            render_texas_infusion_jcode_benchmark_page)
        h = render_texas_infusion_jcode_benchmark_page()
        self.assertIn("not commercial-claims", h)

    def test_heat_legend_div_is_balanced(self):
        # Regression: _heat_legend() opened a <div> it never closed, so the
        # browser's recovery nested the "J-code reference" and "Methodology"
        # panels inside the heatmap panel body.
        from rcm_mc.ui.texas_infusion_jcode_benchmark_page import _heat_legend
        legend = _heat_legend()
        self.assertEqual(legend.count("<div"), legend.count("</div>"),
                         "unbalanced <div> in heat legend")
        from rcm_mc.ui.texas_infusion_jcode_benchmark_page import (
            render_texas_infusion_jcode_benchmark_page)
        body = render_texas_infusion_jcode_benchmark_page()
        # strip script/style blocks (they legitimately contain markup-ish text)
        import re as _re
        stripped = _re.sub(r"(?s)<(script|style)\b.*?</\1>", "", body)
        self.assertEqual(stripped.count("<div"), stripped.count("</div>"),
                         "unbalanced <div> on the rendered page")

    def test_route_registered_in_palette(self):
        from rcm_mc.ui._chartis_kit import _DEFAULT_PALETTE_MODULES
        routes = {m["route"] for m in _DEFAULT_PALETTE_MODULES}
        self.assertIn("/diligence/texas-infusion/jcode-benchmark", routes)

    def test_csv_has_year_columns(self):
        from rcm_mc.ui.texas_infusion_jcode_benchmark_page import (
            texas_jcode_benchmark_csv)
        csv = texas_jcode_benchmark_csv()
        self.assertIn("index_2022", csv)
        self.assertIn("index_2026", csv)
        self.assertIn("J2323", csv)


if __name__ == "__main__":
    unittest.main()
