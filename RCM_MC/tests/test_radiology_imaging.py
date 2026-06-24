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


class RadiologyImagingExpansionTests(unittest.TestCase):
    """Sub-segments, supply shocks, unit economics, RP diligence, AI build."""

    def setUp(self):
        self.r = compute_radiology_imaging()

    def test_modality_segments(self):
        mods = {m.modality for m in self.r.modality_segments}
        self.assertGreaterEqual(len(self.r.modality_segments), 8)
        # The radiology breakdown must include the core modalities.
        self.assertTrue(any("MRI" in m for m in mods))
        self.assertTrue(any("CT" in m for m in mods))
        self.assertTrue(any("PET" in m for m in mods))
        self.assertTrue(any("Teleradiology" in m for m in mods))

    def test_supply_shocks_have_severity(self):
        self.assertGreaterEqual(len(self.r.supply_shocks), 6)
        cats = {s.category for s in self.r.supply_shocks}
        # The big shocks: contrast, cryogen (helium), isotope, equipment, labor.
        for cat in ("contrast", "cryogen", "isotope", "equipment", "labor"):
            self.assertIn(cat, cats)
        for s in self.r.supply_shocks:
            self.assertIn(s.severity, ("high", "medium", "low"))

    def test_unit_economics_nets_to_ebitda(self):
        lines = self.r.unit_economics
        cost_and_rev = sum(u.pct_of_revenue for u in lines if not u.is_total)
        # Net revenue (+100 total) + cost lines should reconcile to the EBITDA total.
        ebitda = next(u for u in lines if u.line_item == "Center EBITDA")
        # cost lines (the non-total entries) sum to -(100 - EBITDA)
        self.assertAlmostEqual(cost_and_rev, -(100.0 - ebitda.pct_of_revenue), delta=0.5)
        # per-scan EBITDA is positive and consistent with the margin.
        self.assertGreater(ebitda.per_scan, 0)

    def test_economic_drivers(self):
        self.assertGreaterEqual(len(self.r.economic_drivers), 8)
        drivers = " ".join(d.driver.lower() for d in self.r.economic_drivers)
        self.assertIn("utilization", drivers)
        self.assertIn("payer mix", drivers)

    def test_rp_diligence(self):
        self.assertGreaterEqual(len(self.r.rp_diligence), 8)
        flags = {d.flag for d in self.r.rp_diligence}
        # A real diligence read carries both strengths and risks.
        self.assertIn("positive", flags)
        self.assertIn("risk", flags)
        text = " ".join(d.metric + " " + d.value + " " + d.assessment for d in self.r.rp_diligence)
        self.assertIn("vRad", text)
        self.assertIn("Whistler", text)

    def test_ai_build_pipeline(self):
        self.assertGreaterEqual(len(self.r.ai_build_stages), 7)
        joined = " ".join(s.stage + s.description for s in self.r.ai_build_stages).lower()
        self.assertIn("fda", joined)
        self.assertIn("validation", joined)
        self.assertIn("reimbursement", joined)

    def test_ai_build_vs_buy(self):
        self.assertGreaterEqual(len(self.r.ai_build_vs_buy), 5)
        verdicts = " ".join(b.verdict.lower() for b in self.r.ai_build_vs_buy)
        self.assertIn("buy", verdicts)

    def test_expansion_renders(self):
        html = render_radiology_imaging({})
        for marker in (
            "Radiology Broken Into Sub-Segments",
            "Imaging-Center Unit Economics",
            "Economic Drivers",
            "Supply Shocks",
            "Radiology Partners",
            "How To Build a Model",
            "Build vs Buy",
        ):
            self.assertIn(marker, html, msg=f"missing expansion section: {marker}")
        # No render regressions.
        self.assertNotIn("&amp;amp;", html)
        self.assertNotIn(">None<", html)


class RadiologyImagingServiceModelTests(unittest.TestCase):
    """Outsourced radiology service-model competitive landscape (generic)."""

    def setUp(self):
        self.r = compute_radiology_imaging()

    def test_three_plus_models(self):
        models = " ".join(m.model.lower() for m in self.r.service_models)
        self.assertGreaterEqual(len(self.r.service_models), 3)
        # The three core archetypes + the emerging hybrid.
        self.assertIn("national", models)
        self.assertIn("teleradiology", models)
        self.assertIn("local", models)
        # Scores are bounded 1-5 on every axis.
        for m in self.r.service_models:
            for v in (m.on_site_presence, m.scale, m.subspecialty_depth, m.tech_ai,
                      m.coverage_reliability, m.physician_alignment):
                self.assertGreaterEqual(v, 1)
                self.assertLessEqual(v, 5)

    def test_sla_tiers_turnaround_priced(self):
        self.assertGreaterEqual(len(self.r.sla_tiers), 4)
        tiers = " ".join(s.tier.lower() for s in self.r.sla_tiers)
        self.assertIn("stroke", tiers)
        self.assertIn("critical", tiers)  # critical/actionable findings tier

    def test_staffing_models_fixed_and_variable(self):
        structures = " ".join(s.cost_structure.lower() for s in self.r.staffing_models)
        self.assertIn("fixed", structures)        # on-site
        self.assertIn("pay-per-read", structures)  # hawk models

    def test_switching_triggers(self):
        self.assertGreaterEqual(len(self.r.switching_triggers), 6)
        for s in self.r.switching_triggers:
            self.assertIn(s.urgency, ("high", "medium", "low"))

    def test_decision_hierarchy_proximity_last(self):
        ranked = sorted(self.r.decision_criteria, key=lambda d: d.rank)
        self.assertEqual(ranked[0].weight, "primary")   # cost is #1
        self.assertIn("cost", ranked[0].criterion.lower())
        self.assertIn("proximity", ranked[-1].criterion.lower())  # proximity is last
        self.assertEqual(ranked[-1].weight, "minimal")

    def test_outsourced_economics_has_subsidy(self):
        items = " ".join(e.line_item.lower() for e in self.r.outsourced_economics)
        self.assertIn("subsidy", items)
        self.assertIn("per read", items.replace("/", " "))
        dirs = {e.direction for e in self.r.outsourced_economics}
        self.assertEqual(dirs, {"revenue", "cost", "margin"})

    def test_ai_vendor_roles(self):
        roles = " ".join(a.role.lower() for a in self.r.ai_vendor_roles)
        for needed in ("enabler", "embedded", "competitor", "target"):
            self.assertIn(needed, roles)

    def test_service_model_renders(self):
        html = render_radiology_imaging({})
        for marker in (
            "Outsourced Service Model",
            "Turnaround SLA Tiers",
            "Reading-Labor Economics",
            "Switching Triggers",
            "Hospital Purchasing Hierarchy",
            "AI Vendor Role",
        ):
            self.assertIn(marker, html, msg=f"missing D3 section: {marker}")
        self.assertNotIn(">None<", html)


if __name__ == "__main__":
    unittest.main()
