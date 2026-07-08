"""Tests for the IFT Market Study synthesis (module + /ift-study page).

Pins the four SOW dimensions, the company registry (MMT is the deep-dive
subject), degradation, honesty labels, and the page render (single title, all
dimensions, the taxonomy matrix, the ?company= selector, and the Excel link).
"""
import pathlib
import unittest

from rcm_mc.market_reports import ift_study as s


class TestStudyModule(unittest.TestCase):
    def test_taxonomy_matrix_shape(self):
        tm = s.taxonomy_matrix()
        self.assertTrue(tm.available)
        # 5 modalities × 7 differentiating dimensions, IFT column present
        self.assertEqual(len(tm.columns), 5)
        self.assertIn("Interfacility (IFT)", tm.columns)
        self.assertEqual(tm.columns[tm.ift_col_index], "Interfacility (IFT)")
        self.assertGreaterEqual(len(tm.rows), 6)
        for label, cells in tm.rows:
            self.assertEqual(len(cells), len(tm.columns),
                             f"row {label!r} has wrong cell count")
        self.assertTrue(tm.why_dedicated_different)

    def test_ecosystem_reuses_real_clinical_spine(self):
        eco = s.ecosystem()
        self.assertTrue(eco.available)
        self.assertTrue(eco.journey)
        self.assertTrue(eco.participants)
        # SOURCED anchors flow through from ift_clinical_demand
        self.assertGreater(eco.n_acute_scenarios, 0)
        self.assertGreater(eco.postacute_destinations, 0)

    def test_operating_models_classify_by_volume(self):
        om = s.operating_models()
        self.assertTrue(om.available)
        self.assertTrue(om.bands)              # insource/outsource/hybrid bands
        self.assertTrue(om.procurement)
        self.assertTrue(om.pain_points)
        # the SOW nuance is explicit
        self.assertIn("VOLUME", om.classification_note.upper())

    def test_company_registry_mmt_is_subject(self):
        companies = s.all_companies()
        self.assertGreaterEqual(len(companies), 6)
        subjects = [c for c in companies if c.is_subject]
        self.assertEqual(len(subjects), 1)
        self.assertEqual(subjects[0].slug, "mmt")
        # MMT carries a real SOURCED footprint (its Nebraska metros)
        self.assertGreaterEqual(len(subjects[0].footprint_markets), 3)
        self.assertIn("Omaha", subjects[0].footprint_markets)

    def test_company_positioning_default_and_switch(self):
        default = s.company_positioning()
        self.assertTrue(default.available)
        self.assertTrue(default.is_subject_mmt)
        self.assertEqual(default.subject.slug, "mmt")
        # a competitor subject
        other = s.company_positioning("amr_gmr")
        self.assertFalse(other.is_subject_mmt)
        self.assertEqual(other.subject.slug, "amr_gmr")
        # unknown slug degrades to MMT, never raises / 404s
        bogus = s.company_positioning("does-not-exist")
        self.assertEqual(bogus.subject.slug, "mmt")

    def test_every_result_carries_a_source_label(self):
        for res in (s.taxonomy_matrix(), s.ecosystem(), s.operating_models(),
                    s.company_positioning()):
            self.assertTrue(res.source_label,
                            f"{type(res).__name__} missing source_label")


class TestStudyPage(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from rcm_mc.ui.ift_study_page import render_ift_study
        cls._render = staticmethod(render_ift_study)
        cls.html = render_ift_study()

    def test_full_document_single_title(self):
        self.assertGreater(len(self.html), 40_000)
        self.assertEqual(self.html.count("<h1"), 1)
        self.assertIn("</html>", self.html.lower())

    def test_all_four_dimensions_present(self):
        for marker in ("Dimension 1 — Market context",
                       "Dimension 2 — The IFT ecosystem",
                       "Dimension 3 — The health-system POV",
                       "Dimension 4 — Company positioning"):
            self.assertIn(marker, self.html, f"missing: {marker}")

    def test_taxonomy_matrix_and_market_education(self):
        # the matrix distinguishes IFT from the adjacent modalities
        for col in ("911 Emergency", "Interfacility (IFT)",
                    "Wheelchair / Van / NEMT", "Air Transport"):
            self.assertIn(col, self.html)
        self.assertIn("hospital-ordered B2B operating service", self.html)

    def test_company_selector_and_mmt_subject(self):
        self.assertIn("ist-companybar", self.html)
        self.assertIn("Midwest Medical Transport", self.html)
        self.assertIn("/ift-study?company=", self.html)
        # deep-dive subject marker
        self.assertIn("deep-dive subject", self.html)

    def test_switches_subject_via_query(self):
        html = self._render({"company": ["superior"]})
        self.assertIn("Superior Air-Ground", html)
        self.assertEqual(html.count("<h1"), 1)

    def test_shares_excel_and_crosslinks(self):
        self.assertIn("/api/ift/markets.xlsx", self.html)
        self.assertIn("/ift-markets", self.html)
        self.assertIn("/ift-clinical", self.html)
        self.assertIn("/market/interfacility_transport", self.html)

    def test_has_chart_visuals(self):
        self.assertIn("ck-chart-card", self.html)
        self.assertGreaterEqual(self.html.count("<svg"), 1)

    def test_content_is_leak_free(self):
        for bad in (">None<", "None</td>", ">nan<", "CompanyProfile(",
                    "TaxonomyMatrix(", "()>"):
            self.assertNotIn(bad, self.html, f"leak: {bad!r}")

    def test_route_wired_into_server(self):
        src = pathlib.Path("rcm_mc/server.py").read_text(encoding="utf-8")
        self.assertIn('path == "/ift-study"', src)
        self.assertIn("render_ift_study", src)


if __name__ == "__main__":
    unittest.main()
