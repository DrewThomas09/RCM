"""Tests for the IFT demand deep-dive (module + /ift-demand page).

Pins the CMS HCPCS acuity/emergency analysis, the emergency-vs-non-emergency
prevalence, the regional roll-up, the national frame, the time series, and the
page render (national -> regional -> subcounty, charts, leak-free, route +
palette + cross-links).
"""
import pathlib
import unittest

from rcm_mc.market_reports import ift_demand as d


class TestDemandModule(unittest.TestCase):
    def test_hcpcs_analysis_three_types_and_emergency_split(self):
        hc = d.hcpcs_acuity_analysis()
        self.assertTrue(hc.available)
        self.assertGreaterEqual(len(hc.rows), 6)
        groups = {r.acuity_group for r in hc.rows}
        for g in ("BLS", "ALS", "SCT"):
            self.assertIn(g, groups, f"missing acuity group {g}")
        self.assertEqual(tuple(t.acuity_type for t in hc.types),
                         ("BLS", "ALS", "SCT"))
        by = {r.hcpcs: r for r in hc.rows}
        # the emergency flag is right where the descriptor fixes it
        self.assertEqual(by["A0429"].emergency, "Emergency")
        self.assertEqual(by["A0428"].emergency, "Non-emergency")
        # SCT is the premium interfacility tier
        self.assertEqual(by["A0434"].acuity_group, "SCT")
        self.assertGreater(by["A0434"].rvu, by["A0428"].rvu)

    def test_emergency_prevalence_reads_registry(self):
        ep = d.emergency_prevalence()
        self.assertTrue(ep.available)
        self.assertIn("Escalation", ep.by_family)
        self.assertGreater(ep.n_emergent_scenarios, 0)
        self.assertGreater(ep.n_nonemergent_scenarios, 0)
        self.assertTrue(ep.by_transfer_type)
        self.assertIsNotNone(ep.cct_sct_share)

    def test_regional_rollup_is_sourced_and_ordered(self):
        regions = d.regional_demand()
        self.assertGreaterEqual(len(regions), 4)
        for r in regions:
            self.assertTrue(r.region_label)
            self.assertGreater(r.n_metros, 0)
            self.assertGreaterEqual(r.n_hospitals, 0)
        # sorted by demand $ descending
        vals = [r.sam_dollars for r in regions]
        self.assertEqual(vals, sorted(vals, reverse=True))

    def test_national_frame(self):
        nf = d.national_frame()
        self.assertTrue(nf.available)
        self.assertGreater(nf.n_hospitals_national, 0)
        self.assertGreater(nf.postacute_destinations, 0)
        self.assertGreater(nf.tam_central_bn, 0)
        self.assertEqual(len(nf.age_bands), 3)

    def test_time_series_assembled_with_bases(self):
        ts = d.demand_time_series()
        self.assertTrue(ts.available)
        keys = {s.key for s in ts.series}
        # the AIF + MMT projection series always assemble offline
        self.assertIn("aif", keys)
        self.assertIn("mmt_projection", keys)
        for s in ts.series:
            self.assertTrue(s.points)
            self.assertIn(s.basis, ("GOV", "ILLUSTRATIVE", "SOURCED"))

    def test_summary_counts(self):
        summ = d.demand_summary()
        self.assertGreaterEqual(summ["n_regions"], 4)
        self.assertGreater(summ["n_metros"], 0)
        self.assertGreater(summ["n_hospitals_national"], 0)
        self.assertGreaterEqual(summ["n_hcpcs"], 6)
        self.assertEqual(summ["n_counties"], 22)
        self.assertEqual(summ["n_cbsa"], 7)


class TestDemandPage(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from rcm_mc.ui.ift_demand_page import render_ift_demand
        cls._render = staticmethod(render_ift_demand)
        cls.html = render_ift_demand()

    def test_full_document_single_title(self):
        self.assertGreater(len(self.html), 40_000)
        self.assertEqual(self.html.count("<h1"), 1)
        self.assertIn("</html>", self.html.lower())

    def test_all_levels_present(self):
        for marker in ("National frame",
                       "CMS code analysis — BLS / ALS / SCT",
                       "Emergency vs non-emergency",
                       "Trailed over time",
                       "Regional breakdown",
                       "MMT granular",
                       "Demand by subcounty"):
            self.assertIn(marker, self.html, f"missing section: {marker}")

    def test_cms_codes_and_subcounty_detail(self):
        for token in ("A0434", "A0428", "SCT", "Emergency?"):
            self.assertIn(token, self.html)
        # subcounty granularity — a real MMT county appears
        self.assertIn("Douglas, NE", self.html)
        # customer concentration
        self.assertIn("Where customers concentrate", self.html)

    def test_condition_yoy_trend_rendered(self):
        # demand by condition, trended year over year
        self.assertIn("Demand by condition — year over year", self.html)
        self.assertIn("Aggregate trajectory", self.html)
        self.assertIn("YoY growth", self.html)
        self.assertIn("Blended demand CAGR", self.html)
        self.assertIn("Fastest-growing conditions", self.html)   # chart
        self.assertIn("Hip fracture", self.html)

    def test_has_charts(self):
        self.assertIn("ck-chart-card", self.html)
        self.assertGreaterEqual(self.html.count("<svg"), 2)

    def test_content_is_leak_free(self):
        for bad in (">None<", "None</td>", ">nan<", "RegionDemand(", "HcpcsRow(",
                    "TimeSeries(", "()>"):
            self.assertNotIn(bad, self.html, f"leak: {bad!r}")

    def test_degrades_when_a_module_raises(self):
        import rcm_mc.market_reports.ift_geo as geo
        saved = geo.all_metros
        try:
            geo.all_metros = lambda: (_ for _ in ()).throw(RuntimeError("x"))
            html = self._render()
            self.assertEqual(html.count("<h1"), 1)
            self.assertIn("</html>", html.lower())
        finally:
            geo.all_metros = saved

    def test_route_and_palette_wired(self):
        src = pathlib.Path("rcm_mc/server.py").read_text(encoding="utf-8")
        self.assertIn('path == "/ift-demand"', src)
        self.assertIn("render_ift_demand", src)
        from rcm_mc.ui._chartis_kit import _DEFAULT_PALETTE_MODULES
        self.assertIn("/ift-demand",
                      {m["route"] for m in _DEFAULT_PALETTE_MODULES})

    def test_crosslinked_from_family(self):
        from rcm_mc.ui.ift_sourcing_page import render_ift_sourcing
        from rcm_mc.ui.ift_diligence_page import render_ift_diligence
        self.assertIn("/ift-demand", render_ift_sourcing())
        self.assertIn("/ift-demand", render_ift_diligence())


if __name__ == "__main__":
    unittest.main()


class DoubleEscapeRegressionTests(unittest.TestCase):
    """2026-07-10 user-reported: the growth-evidence tables passed BUILT
    markup through the escaping _table() helper, and the YoY table
    pre-escaped cells before _table() escaped them again — both rendered
    literal HTML/entities on /ift-demand. Guard both directions."""

    def test_no_escaped_tags_or_double_entities_render(self):
        import re
        from rcm_mc.ui.ift_demand_page import render_ift_demand
        h = render_ift_demand({})
        self.assertEqual(
            re.findall(r"&lt;(strong|span|a href|br|em|td|tr)", h), [],
            "built markup was escaped — raw table cells routed through "
            "_table()?")
        self.assertEqual(
            re.findall(r"&amp;(amp|lt|gt|ldquo|rdquo|quot);", h), [],
            "double-escaped entity — cell pre-escaped before _table()?")
        # the growth-evidence links + chips must render as real markup
        self.assertIn('href="https://doi.org/10.1016/j.ajem.2026.04.025"', h)
        self.assertIn('ifd-chip ifd-chip-academic', h)
