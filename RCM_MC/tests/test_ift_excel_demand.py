"""Real-path tests for the SEPARATE IFT DEMAND workbook (/api/ift/demand.xlsx).

Pins that the demand-only workbook always builds a real, openable .xlsx carrying
the volume centerpiece and every demand-side layer, that the transports/year
funnel is GOV-anchored and sourced, that NO trade / market-research-firm figure
(IBISWorld / Grand View) leaks in, and that it degrades — never raises — when a
source analytic is dark, because the download must always succeed.
"""
from __future__ import annotations

import io
import re
import unittest
import zipfile
from xml.sax.saxutils import unescape

from rcm_mc.market_reports import ift_demand as d
from rcm_mc.market_reports.ift_excel_demand import demand_workbook_xlsx


def _content_text(data: bytes) -> str:
    """All human-visible text in the workbook (sheet XML + sharedStrings)."""
    z = zipfile.ZipFile(io.BytesIO(data))
    blob = []
    for n in z.namelist():
        if n.endswith(".xml") and ("worksheets" in n or "sharedStrings" in n):
            blob.append(z.read(n).decode("utf-8", "replace"))
    return "".join(blob)


class NationalVolumeModuleTests(unittest.TestCase):
    """The transports/year function — the demand centerpiece."""

    def setUp(self):
        self.vol = d.national_transport_volume()

    def test_gov_anchor_is_the_medpac_figure(self):
        self.assertTrue(self.vol.available)
        # The hard GOV anchor: MedPAC 2024 — 11.3M FFS ground transports, $5.3B.
        self.assertAlmostEqual(self.vol.ffs_transports_m, 11.3, places=1)
        self.assertAlmostEqual(self.vol.ffs_spend_bn, 5.3, places=1)
        self.assertEqual(self.vol.ffs_orgs, 10_600)
        self.assertEqual(self.vol.ffs_year, 2024)

    def test_allpayer_is_derived_from_the_gov_anchor(self):
        # all-payer = FFS ÷ FFS share; the band must bracket the anchor upward.
        self.assertGreater(self.vol.allpayer_low_m, self.vol.ffs_transports_m)
        self.assertGreater(self.vol.allpayer_high_m, self.vol.allpayer_low_m)
        # the derived low = ffs / high_share (within rounding)
        self.assertAlmostEqual(
            self.vol.allpayer_low_m,
            round(self.vol.ffs_transports_m / self.vol.ffs_share_high, 1), places=1)

    def test_tiers_carry_basis_and_the_derived_line_is_labelled(self):
        bases = {t.basis for t in self.vol.tiers}
        self.assertIn("GOV", bases)
        self.assertIn("DERIVED", bases)
        self.assertIn("ACADEMIC", bases)          # the NHAMCS floor
        derived = [t for t in self.vol.tiers if t.basis == "DERIVED"]
        self.assertTrue(derived)
        self.assertNotIn("ibis", derived[0].source.lower())

    def test_acuity_split_is_the_three_types(self):
        labels = " ".join(a.label for a in self.vol.acuity_split).upper()
        for tok in ("BLS", "ALS", "SCT"):
            self.assertIn(tok, labels)
        # shares are on the FFS base and roughly sum to 100
        self.assertAlmostEqual(sum(a.share_pct for a in self.vol.acuity_split),
                               100.0, delta=1.0)

    def test_emergency_split_present_and_sums(self):
        self.assertEqual(len(self.vol.emergency_split), 2)
        self.assertAlmostEqual(sum(e.share_pct for e in self.vol.emergency_split),
                               100.0, delta=1.0)

    def test_interfacility_tier_uses_the_current_neds_read(self):
        # NEDS supersedes the older NHAMCS floor as the interfacility anchor.
        self.assertAlmostEqual(self.vol.neds_ed_transfers_m, 2.0, places=1)
        ift = [t for t in self.vol.tiers if "NEDS" in t.tier]
        self.assertTrue(ift, "no HCUP NEDS interfacility tier")
        self.assertEqual(ift[0].basis, "SOURCED")
        self.assertIn("NEDS", ift[0].source)

    def test_no_trade_firm_figure_anywhere_in_the_build(self):
        blob = (self.vol.source_label + self.vol.note
                + " ".join(t.source for t in self.vol.tiers)).lower()
        self.assertNotIn("ibis", blob)
        self.assertNotIn("grand view", blob)


class DemandSourceMatrixTests(unittest.TestCase):
    """The multi-database triangulation — the answer to 'are we using NEDS?'."""

    def setUp(self):
        self.m = d.demand_source_matrix()

    def test_triangulates_across_the_key_databases(self):
        self.assertTrue(self.m.available)
        self.assertGreaterEqual(len(self.m.sources), 8)
        names = " ".join(s.name for s in self.m.sources)
        for db in ("NEDS", "NIS", "NEMSIS", "MedPAC", "HCRIS", "NHAMCS"):
            self.assertIn(db, names, f"missing database {db}")

    def test_every_source_has_a_figure_year_basis_and_url(self):
        for s in self.m.sources:
            self.assertTrue(s.current_read, f"{s.name}: no figure")
            self.assertTrue(s.data_year, f"{s.name}: no data year")
            self.assertIn(s.basis, ("GOV", "SOURCED", "ACADEMIC"))
            self.assertTrue(s.url.startswith("http"), f"{s.name}: no url")

    def test_neds_is_the_current_ed_transfer_read(self):
        neds = [s for s in self.m.sources if "NEDS" in s.name][0]
        self.assertIn("2.0", neds.current_read)     # ~2.0M/yr
        self.assertIn("ahrq", neds.url.lower())

    def test_nemsis_activation_denominator_present(self):
        nemsis = [s for s in self.m.sources if "NEMSIS" in s.name][0]
        self.assertIn("54.2M", nemsis.current_read)

    def test_no_trade_firm_source(self):
        blob = " ".join(s.name + s.steward + s.note for s in self.m.sources).lower()
        self.assertNotIn("ibis", blob)
        self.assertNotIn("grand view", blob)


class DemandDriversTests(unittest.TestCase):
    """The sourced demand-driver table — every user-named lever, no illustrative."""

    def setUp(self):
        self.dd = d.demand_drivers()

    def test_available_and_all_sourced(self):
        self.assertTrue(self.dd.available)
        self.assertGreaterEqual(len(self.dd.drivers), 8)
        # the load-bearing guarantee the user asked for: NOTHING illustrative.
        self.assertTrue(self.dd.all_sourced)
        for x in self.dd.drivers:
            self.assertIn(x.basis, ("GOV", "SOURCED", "ACADEMIC"),
                          f"{x.driver}: basis {x.basis} is not fully sourced")

    def test_every_driver_has_source_url_proxy_and_tracking(self):
        for x in self.dd.drivers:
            self.assertTrue(x.value, f"{x.driver}: no value")
            self.assertTrue(x.source, f"{x.driver}: no source")
            self.assertTrue(x.url.startswith("http"), f"{x.driver}: no url")
            self.assertTrue(x.proxy, f"{x.driver}: no proxy")
            self.assertTrue(x.track, f"{x.driver}: no tracking path")
            self.assertTrue(x.ift_link, f"{x.driver}: no IFT linkage")

    def test_covers_every_driver_the_user_named(self):
        drivers = " ".join(x.driver.lower() for x in self.dd.drivers)
        for needed in ("admission", "ift mission", "hospital-to-hospital",
                       "als / bls", "facilities increasing", "specializing",
                       "boarding", "impact on hospital"):
            self.assertIn(needed, drivers, f"missing driver: {needed}")

    def test_key_anchors_are_the_current_sourced_figures(self):
        by = {x.driver: x for x in self.dd.drivers}
        consol = [x for x in self.dd.drivers if "consolidation" in x.driver][0]
        self.assertIn("640", consol.value)            # AHRQ Compendium 2022
        self.assertEqual(consol.basis, "GOV")
        h2h = [x for x in self.dd.drivers if "hospital-to-hospital" in x.driver][0]
        self.assertIn("1.5M", h2h.value)              # nationwide outcomes study

    def test_nothing_illustrative_or_trade_firm(self):
        blob = " ".join(x.driver + x.source + x.proxy + x.track + x.ift_link
                        for x in self.dd.drivers).lower()
        self.assertNotIn("illustrative", blob)
        self.assertNotIn("ibis", blob)
        self.assertNotIn("grand view", blob)


class DemandWorkbookTests(unittest.TestCase):
    def setUp(self):
        self.data = demand_workbook_xlsx()

    def test_returns_a_real_xlsx_zip(self):
        self.assertIsInstance(self.data, bytes)
        self.assertGreater(len(self.data), 5000)
        self.assertEqual(self.data[:2], b"PK")            # zip magic
        z = zipfile.ZipFile(io.BytesIO(self.data))
        self.assertIn("xl/workbook.xml", z.namelist())
        self.assertIn("[Content_Types].xml", z.namelist())
        self.assertIsNone(z.testzip())                     # not corrupt

    def _sheet_names(self):
        z = zipfile.ZipFile(io.BytesIO(self.data))
        wb = z.read("xl/workbook.xml").decode()
        return [unescape(n) for n in re.findall(r'name="([^"]+)"', wb)]

    def test_carries_the_demand_spine(self):
        names = self._sheet_names()
        for expected in ("Contents", "National volume", "Volume sources",
                         "Demand databases", "Demand drivers", "CMS code analysis",
                         "Emergency mix", "Demand by condition YoY",
                         "Aggregate demand YoY", "Clinical demand engine",
                         "Regional demand", "Demographic engine", "Provenance"):
            self.assertIn(expected, names, f"missing sheet: {expected}")

    def test_demand_drivers_sheet_is_sourced_with_proxy_and_tracking(self):
        text = _content_text(self.data).lower()
        self.assertIn("best proxy to get it", text)
        self.assertIn("how to track it", text)
        for anchor in ("640 health systems", "emtala", "boarding"):
            self.assertIn(anchor, text)
        z = zipfile.ZipFile(io.BytesIO(self.data))
        rels = "".join(z.read(n).decode("utf-8", "replace")
                       for n in z.namelist() if n.endswith(".rels"))
        self.assertIn("ahrq.gov/chsp", rels)          # the consolidation source
        self.assertIn("acep.org", rels)               # the ED-boarding source

    def test_demand_databases_sheet_names_the_databases(self):
        text = _content_text(self.data).lower()
        for db in ("neds", "nemsis", "national inpatient sample"):
            self.assertIn(db, text, f"database {db} not in workbook")
        # the database URLs travel in the relationship parts
        z = zipfile.ZipFile(io.BytesIO(self.data))
        rels = "".join(z.read(n).decode("utf-8", "replace")
                       for n in z.namelist() if n.endswith(".rels"))
        self.assertIn("hcup-us.ahrq.gov", rels)
        self.assertIn("nemsis.org", rels)

    def test_volume_sheet_leads_the_pack(self):
        # the centerpiece sits first after Contents (volume-first by design)
        names = self._sheet_names()
        self.assertEqual(names[0], "Contents")
        self.assertEqual(names[1], "National volume")

    def test_provenance_always_present(self):
        self.assertIn("Provenance", self._sheet_names())

    def test_volume_anchor_and_sources_travel_into_the_workbook(self):
        text = _content_text(self.data)
        low = text.lower()
        self.assertIn("medpac", low)               # the GOV source
        self.assertIn("11.3", text)                # the anchor figure
        self.assertIn("nhamcs", low)               # the ACADEMIC IFT floor
        self.assertIn("derived", low)              # the all-payer label

    def test_no_ibis_or_trade_firm_anywhere(self):
        low = _content_text(self.data).lower()
        self.assertNotIn("ibis", low)
        self.assertNotIn("grand view", low)

    def test_degrades_when_a_source_analytic_raises(self):
        # kill the volume source; the workbook must still build (sheet drops).
        import rcm_mc.market_reports.ift_excel_demand as m

        orig = m._dd.national_transport_volume
        try:
            m._dd.national_transport_volume = lambda: (_ for _ in ()).throw(
                RuntimeError("boom"))
            data = demand_workbook_xlsx()
        finally:
            m._dd.national_transport_volume = orig
        self.assertEqual(data[:2], b"PK")
        z = zipfile.ZipFile(io.BytesIO(data))
        self.assertIsNone(z.testzip())
        # provenance still there even with the centerpiece dropped
        wb = z.read("xl/workbook.xml").decode()
        self.assertIn("Provenance", wb)


class DemandWorkbookWiringTests(unittest.TestCase):
    def test_route_wired_in_server(self):
        import pathlib
        src = pathlib.Path("rcm_mc/server.py").read_text()
        self.assertIn("/api/ift/demand.xlsx", src)
        self.assertIn("demand_workbook_xlsx", src)

    def test_download_link_on_demand_pages(self):
        from rcm_mc.ui.ift_demand_page import render_ift_demand
        from rcm_mc.ui.ift_hs_demand_page import render_ift_hs_demand
        self.assertIn("/api/ift/demand.xlsx", render_ift_demand())
        self.assertIn("/api/ift/demand.xlsx", render_ift_hs_demand())

    def test_volume_section_rendered_on_demand_page(self):
        from rcm_mc.ui.ift_demand_page import render_ift_demand
        html = render_ift_demand()
        self.assertIn("National transport volume", html)
        self.assertIn("11.3M", html)               # the GOV anchor on the page
        self.assertNotIn("ibis", html.lower())

    def test_demand_databases_section_on_page(self):
        from rcm_mc.ui.ift_demand_page import render_ift_demand
        html = render_ift_demand()
        self.assertIn("Demand databases", html)
        for db in ("NEMSIS", "HCUP NEDS", "HCUP NIS"):
            self.assertIn(db, html)
        self.assertIn("hcup-us.ahrq.gov", html)    # the clickable source URL

    def test_demand_drivers_section_on_page(self):
        from rcm_mc.ui.ift_demand_page import render_ift_demand
        html = render_ift_demand()
        self.assertIn("Demand drivers", html)
        self.assertIn("Best proxy to get it", html)
        self.assertIn("How to track it", html)
        for anchor in ("Annual hospital admissions", "640 health systems",
                       "ED boarding", "EMTALA"):
            self.assertIn(anchor, html)


if __name__ == "__main__":
    unittest.main()
