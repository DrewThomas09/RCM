"""Referring Radiology & Diagnostic Imaging atlas — /radiology-imaging.

Covers the data layer (CMS claims atlas, the coverage-connection loop, MAC
payers, state + county data, players, AI, factors), the rendered page, and the
route wiring (module index, palette, sub-nav, section map).
"""
from __future__ import annotations

import html as _html
import unittest

from rcm_mc.data_public.radiology_imaging import (
    build_cms_connections,
    compute_radiology_imaging,
)
from rcm_mc.ui.data_public.radiology_imaging_page import render_radiology_imaging


class RadiologyImagingDataTests(unittest.TestCase):
    def setUp(self):
        self.r = compute_radiology_imaging()

    def test_headline_kpis_present(self):
        self.assertGreater(self.r.market_size_bn, 0)
        self.assertGreater(self.r.freestanding_centers, 0)
        self.assertGreater(self.r.mqsa_facilities, 0)
        # CY2025 FINAL conversion factor (not the superseded proposed $32.3465).
        self.assertAlmostEqual(self.r.pfs_conversion_factor_2025, 32.2465, places=4)

    def test_cpt_global_equals_prof_plus_tech(self):
        # The page asserts "global ≈ prof + tech" — keep it internally honest.
        for c in self.r.cpt_codes:
            self.assertAlmostEqual(
                c.global_rate, c.prof_26 + c.tech_tc, delta=0.5,
                msg=f"{c.code}: global {c.global_rate} != {c.prof_26}+{c.tech_tc}",
            )

    def test_mammography_codes_present(self):
        codes = {c.code for c in self.r.cpt_codes}
        # 2D screening, diagnostic, and the 3D/DBT add-on the request called out.
        for needed in ("77067", "77066", "77065", "77063", "G0279"):
            self.assertIn(needed, codes)

    def test_ldct_rate_is_corrected(self):
        # LDCT lung screening is ~$271 global, not the ~$110 first-pass figure.
        ldct = next(c for c in self.r.cpt_codes if c.code == "71271")
        self.assertGreater(ldct.global_rate, 200.0)

    def test_screening_mammography_is_preventive(self):
        m77067 = next(c for c in self.r.cpt_codes if c.code == "77067")
        self.assertEqual(m77067.category, "screening")

    def test_cms_connection_loop(self):
        conns = build_cms_connections()
        # The loop must materialise both national NCDs and local LCDs.
        ncds = [c for c in conns if c.doc_type == "NCD"]
        lcds = [c for c in conns if c.doc_type == "LCD"]
        self.assertGreaterEqual(len(ncds), 5)
        self.assertGreaterEqual(len(lcds), 5)
        # NCDs sort first (national policies bind every MAC).
        types = [c.doc_type for c in conns]
        self.assertEqual(types, sorted(types, key=lambda t: t != "NCD"))

    def test_real_cms_documents_wired(self):
        conns = build_cms_connections()
        display_ids = {c.display_id for c in conns}
        # Real document IDs pulled from the CMS Coverage API.
        self.assertIn("210.14", display_ids)   # LDCT lung screening NCD 364
        self.assertIn("220.1", display_ids)    # Computed Tomography NCD 176
        self.assertIn("L33950", display_ids)   # CGS breast-imaging mammography LCD
        # Every connection links to the Medicare Coverage Database.
        for c in conns:
            self.assertTrue(c.url.startswith("https://www.cms.gov/medicare-coverage-database"))

    def test_seven_mac_payers(self):
        names = {m.mac_name for m in self.r.mac_jurisdictions}
        self.assertEqual(len(self.r.mac_jurisdictions), 7)
        for mac in ("CGS Administrators, LLC", "Noridian Healthcare Solutions, LLC",
                    "Novitas Solutions, Inc.", "Palmetto GBA",
                    "National Government Services, Inc.", "WPS Insurance Corporation",
                    "First Coast Service Options, Inc."):
            self.assertIn(mac, names)

    def test_state_and_county_data(self):
        self.assertGreaterEqual(len(self.r.state_profiles), 10)
        self.assertGreaterEqual(len(self.r.county_payer_mix), 10)
        # County payer-mix shares are a coverage split — each row sums ~100%.
        for c in self.r.county_payer_mix:
            total = c.medicare_pct + c.medicaid_pct + c.commercial_pct + c.uninsured_pct
            self.assertAlmostEqual(total, 100.0, delta=0.5,
                                   msg=f"{c.county} payer mix sums to {total}")

    def test_big_players_include_majors(self):
        names = {p.name for p in self.r.big_players}
        self.assertIn("RadNet", names)
        self.assertIn("Radiology Partners", names)

    def test_payer_shares_sum_to_100(self):
        total = sum(p.imaging_revenue_share_pct for p in self.r.payer_shares)
        self.assertAlmostEqual(total, 100.0, delta=0.5)

    def test_ai_and_recent_factors_present(self):
        self.assertGreaterEqual(len(self.r.ai_implementations), 5)
        self.assertGreaterEqual(len(self.r.recent_factors), 8)


class RadiologyImagingRenderTests(unittest.TestCase):
    def setUp(self):
        self.html = render_radiology_imaging({})

    def test_renders_full_page(self):
        self.assertGreater(len(self.html), 5000)
        self.assertIn("ck-page-wrap", self.html)
        self.assertIn("Referring Radiology", self.html)

    def test_key_sections_present(self):
        for marker in (
            "CMS Claims Atlas",
            "Mammography &amp; Breast Imaging",
            "CMS Coverage Connections",
            "MAC Payer Jurisdictions",
            "State-Level Data",
            "County-Level Payer Mix",
            "Big Players",
            "AI Implementation",
        ):
            self.assertIn(marker, self.html, msg=f"missing section: {marker}")

    def test_coverage_links_render(self):
        # The loop's connections render as clickable CMS source links.
        self.assertIn("ncdid=364", self.html)
        self.assertIn("lcdid=33950", self.html)

    def test_no_double_escape(self):
        # Ampersands escape once, never twice.
        self.assertNotIn("&amp;amp;", self.html)

    def test_no_literal_none(self):
        self.assertNotIn(">None<", self.html)


class RadiologyImagingWiringTests(unittest.TestCase):
    def test_in_module_index(self):
        from rcm_mc.data_public.module_index import compute_module_index
        routes = {m.route for m in compute_module_index().modules}
        self.assertIn("/radiology-imaging", routes)

    def test_module_index_renders_module(self):
        from rcm_mc.ui.data_public.module_index_page import render_module_index, _source_badge
        html = render_module_index({})
        self.assertIn("/radiology-imaging", html)
        # Tagged CMS (grounded in live CMS coverage data).
        self.assertIn("CMS", _source_badge("/radiology-imaging"))

    def test_in_command_palette(self):
        from rcm_mc.ui._chartis_kit import _DEFAULT_PALETTE_MODULES
        routes = {m["route"] for m in _DEFAULT_PALETTE_MODULES}
        self.assertIn("/radiology-imaging", routes)

    def test_in_research_subnav(self):
        from rcm_mc.ui._chartis_kit import _SUB_NAV
        hrefs = {item["href"] for item in _SUB_NAV["research"]}
        self.assertIn("/radiology-imaging", hrefs)

    def test_section_map_resolves(self):
        from rcm_mc.ui._chartis_kit import _SUB_SECTION_MAP
        self.assertEqual(_SUB_SECTION_MAP.get("/radiology-imaging"), "research")


if __name__ == "__main__":
    unittest.main()
