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

    def test_no_trade_firm_figure_anywhere_in_the_build(self):
        blob = (self.vol.source_label + self.vol.note
                + " ".join(t.source for t in self.vol.tiers)).lower()
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
                         "CMS code analysis", "Emergency mix",
                         "Demand by condition YoY", "Aggregate demand YoY",
                         "Clinical demand engine", "Regional demand",
                         "Demographic engine", "Provenance"):
            self.assertIn(expected, names, f"missing sheet: {expected}")

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


if __name__ == "__main__":
    unittest.main()
