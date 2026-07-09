"""Tests for the IFT health-system demand model (module + /ift-hs-demand page).

Pins the hospital-discharge driver (SNF dropped), the health-system roll-up, the
county allocation, the demand-data inventory, and the page render.
"""
import pathlib
import unittest

from rcm_mc.market_reports import ift_hs_demand as h


class TestHsDemandModule(unittest.TestCase):
    def test_hospital_demand_is_discharge_driven_and_nonzero(self):
        hd = h.hospital_demand()
        self.assertGreaterEqual(len(hd), 10)
        for m in hd:
            self.assertGreater(m.discharges, 0)         # non-zero in any env
            self.assertIn(m.discharge_basis, ("SOURCED", "ILLUSTRATIVE"))
            # legs are a fraction of discharges (SNF term dropped, not added)
            self.assertLess(m.ift_legs, m.discharges)
            self.assertLessEqual(m.serviceable_legs, m.ift_legs)
        # sorted by demand descending
        vals = [m.demand_dollars for m in hd]
        self.assertEqual(vals, sorted(vals, reverse=True))

    def test_discharge_fallback_when_hcris_absent(self):
        # offline (no HCRIS/pandas) the driver must fall back to hospital-count,
        # never zero — the whole point of the robust build
        hd = h.hospital_demand()
        self.assertTrue(hd)
        m = hd[0]
        if m.discharge_basis == "ILLUSTRATIVE":
            # fallback = n_hospitals * ~7300
            self.assertAlmostEqual(m.discharges,
                                   round(m.n_hospitals * 7300.0), delta=1)

    def test_health_system_rollup_is_the_buyer(self):
        sr = h.health_system_rollup()
        self.assertGreaterEqual(len(sr), 3)
        names = {s.system for s in sr}
        self.assertTrue(any("CHI" in n or "CommonSpirit" in n for n in names))
        for s in sr:
            self.assertTrue(s.system and s.tier)
            self.assertGreaterEqual(s.n_metros, 0)
        vals = [s.demand_dollars for s in sr]
        self.assertEqual(vals, sorted(vals, reverse=True))

    def test_county_breakdown_allocates_by_population(self):
        cd = h.county_demand()
        self.assertEqual(len(cd), 22)
        # allocation weights within a metro sum to ~1
        by_metro = {}
        for c in cd:
            by_metro.setdefault(c.metro, 0.0)
            by_metro[c.metro] += c.pop_share_of_metro
        for metro, tot in by_metro.items():
            self.assertAlmostEqual(tot, 1.0, places=2,
                                   msg=f"{metro} pop shares do not sum to 1")
        # a real county is present with its serving systems tagged
        douglas = [c for c in cd if c.county == "Douglas"]
        self.assertTrue(douglas)
        self.assertGreater(douglas[0].ift_legs, 0)

    def test_demand_inventory_lists_drivers_with_status(self):
        inv = h.demand_data_inventory()
        self.assertTrue(inv.available)
        self.assertGreaterEqual(len(inv.signals), 10)
        statuses = {s.status for s in inv.signals}
        self.assertEqual(statuses, {"live", "ingest-ready", "to-source"})
        # HCRIS discharges is the load-bearing live signal
        drivers = {s.driver for s in inv.signals}
        self.assertTrue(any("discharge" in d.lower() for d in drivers))
        self.assertEqual(inv.n_live + inv.n_ingest_ready + inv.n_to_source,
                         len(inv.signals))

    def test_summary(self):
        summ = h.hs_demand_summary()
        self.assertGreater(summ["n_metros"], 0)
        self.assertGreater(summ["n_systems"], 0)
        self.assertEqual(summ["n_counties"], 22)
        self.assertGreater(summ["total_discharges"], 0)
        self.assertGreater(summ["total_ift_legs"], 0)


class TestHsDemandPage(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from rcm_mc.ui.ift_hs_demand_page import render_ift_hs_demand
        cls._render = staticmethod(render_ift_hs_demand)
        cls.html = render_ift_hs_demand()

    def test_full_document_single_title(self):
        self.assertGreater(len(self.html), 40_000)
        self.assertEqual(self.html.count("<h1"), 1)
        self.assertIn("</html>", self.html.lower())

    def test_sections_and_snf_dropped_framing(self):
        for marker in ("How we size it", "SNF is not the buyer",
                       "Demand-data inventory", "Hospital-discharge demand",
                       "The buyers — demand by health system", "County breakdown"):
            self.assertIn(marker, self.html, f"missing: {marker}")
        # the HCRIS driver is explained
        self.assertIn("patient_days", self.html)
        self.assertIn("CHI Health", self.html)
        self.assertIn("Douglas, NE", self.html)

    def test_inventory_links_connectors(self):
        self.assertIn("/connector-estate?dataset=", self.html)
        for status in ("LIVE", "INGEST-READY", "TO SOURCE"):
            self.assertIn(status, self.html)

    def test_has_charts(self):
        self.assertIn("ck-chart-card", self.html)
        self.assertGreaterEqual(self.html.count("<svg"), 2)

    def test_leak_free(self):
        for bad in (">None<", "None</td>", ">nan<", "MetroHsDemand(",
                    "SystemDemand(", "CountyHsDemand(", "()>"):
            self.assertNotIn(bad, self.html, f"leak: {bad!r}")

    def test_route_palette_and_crosslinks(self):
        src = pathlib.Path("rcm_mc/server.py").read_text(encoding="utf-8")
        self.assertIn('path == "/ift-hs-demand"', src)
        self.assertIn("render_ift_hs_demand", src)
        from rcm_mc.ui._chartis_kit import _DEFAULT_PALETTE_MODULES
        self.assertIn("/ift-hs-demand",
                      {m["route"] for m in _DEFAULT_PALETTE_MODULES})
        from rcm_mc.ui.ift_demand_page import render_ift_demand
        self.assertIn("/ift-hs-demand", render_ift_demand())

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


if __name__ == "__main__":
    unittest.main()
