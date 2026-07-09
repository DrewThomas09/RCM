"""Tests for the IFT diligence question architecture (module + /ift-diligence page).

Pins the master question tree, the per-slide architecture (main question +
sub-questions + evidence + visuals + live answer links), the connector-evidence
resolution against the real estate, degradation / honesty labels, and the page
render (single title, all 15 slides, cross-links, leak-free, route wired, palette
+ IFT_Market link present).
"""
import pathlib
import unittest

from rcm_mc.market_reports import ift_diligence as d


class TestDiligenceModule(unittest.TestCase):
    def test_master_tree_three_branches(self):
        mt = d.master_tree()
        self.assertTrue(mt.available)
        self.assertEqual(len(mt.branches), 3)
        keys = {b.key for b in mt.branches}
        self.assertEqual(keys, {"what", "why", "advantage"})
        for b in mt.branches:
            self.assertTrue(b.title and b.main_question and b.intro)
            self.assertTrue(b.groups)
            for g in b.groups:
                self.assertTrue(g.heading and g.questions)
        self.assertTrue(mt.source_label and mt.note)

    def test_slide_architecture_covers_all_15_slides(self):
        sa = d.slide_architecture()
        self.assertTrue(sa.available)
        self.assertEqual(len(sa.slides), 15)
        nums = [s.num for s in sa.slides]
        self.assertEqual(nums, list(range(1, 16)))
        slugs = {s.slug for s in sa.slides}
        self.assertEqual(len(slugs), 15)          # unique slugs (anchors)
        for s in sa.slides:
            self.assertTrue(s.title and s.prompt and s.main_question)
            self.assertIn(s.kind, ("cover", "divider", "content"))
        # every content slide has a question tree and at least one live answer link
        for s in sa.slides:
            if s.kind == "content":
                self.assertTrue(s.groups, f"slide {s.num} has no question groups")
                self.assertTrue(s.answered_by, f"slide {s.num} has no answer link")

    def test_slide_answer_links_resolve_to_real_routes(self):
        sa = d.slide_architecture()
        known = {route for route, _lbl in d.LINK.values()}
        for s in sa.slides:
            for _txt, href in s.answered_by:
                self.assertIn(href, known,
                              f"slide {s.num} links to unknown route {href}")

    def test_slide_connector_keys_resolve_in_live_estate(self):
        sa = d.slide_architecture()
        ce = d.connector_evidence()
        self.assertTrue(ce.available)
        self.assertGreater(len(ce.probes_by_key), 0)
        for s in sa.slides:
            for k in s.connector_keys:
                self.assertIn(k, ce.probes_by_key,
                              f"slide {s.num} references unknown connector {k!r}")

    def test_evidence_plan_five_sources_mapped(self):
        ep = d.evidence_plan()
        ce = d.connector_evidence()
        self.assertTrue(ep.available)
        self.assertEqual(len(ep.sources), 5)
        for src in ep.sources:
            self.assertTrue(src.name and src.intro and src.items)
            # each evidence source maps to at least one live surface
            self.assertTrue(src.our_surface, f"{src.name} has no surface link")
            for k in src.connector_keys:
                self.assertIn(k, ce.probes_by_key,
                              f"{src.name} references unknown connector {k!r}")

    def test_visual_package_and_nuances(self):
        vp = d.visual_package()
        self.assertTrue(vp.available)
        self.assertEqual(len(vp.visuals), 15)
        for v in vp.visuals:
            self.assertTrue(v.name and v.purpose)
        ns = d.nuances()
        self.assertEqual(len(ns), 10)
        for n in ns:
            self.assertTrue(n.title and n.body)

    def test_summary_counts(self):
        summ = d.diligence_summary()
        self.assertEqual(summ["n_branches"], 3)
        self.assertEqual(summ["n_slides"], 15)
        self.assertGreater(summ["n_questions"], 100)
        self.assertEqual(summ["n_evidence_sources"], 5)
        self.assertEqual(summ["n_visuals"], 15)
        self.assertEqual(summ["n_nuances"], 10)
        self.assertGreater(summ["n_connectors"], 0)
        self.assertGreater(summ["n_connector_hooks"], 0)

    def test_connector_evidence_degrades(self):
        # connector_evidence must never raise, even if it returned empty
        ce = d.connector_evidence()
        self.assertIn(ce.available, (True, False))
        if not ce.available:
            self.assertEqual(ce.probes_by_key, {})


class TestDiligencePage(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from rcm_mc.ui.ift_diligence_page import render_ift_diligence
        cls._render = staticmethod(render_ift_diligence)
        cls.html = render_ift_diligence()

    def test_full_document_single_title(self):
        self.assertGreater(len(self.html), 40_000)
        self.assertEqual(self.html.count("<h1"), 1)
        self.assertIn("</html>", self.html.lower())

    def test_master_tree_and_all_slides_present(self):
        self.assertIn("master question tree", self.html)
        for marker in ("A. What exactly is the IFT market?",
                       "B. Why does the market matter to health systems?",
                       "C. Why might dedicated IFT providers be advantaged?"):
            self.assertIn(marker, self.html, f"missing branch: {marker}")
        # all 15 slide panels rendered with anchors
        self.assertEqual(self.html.count('id="ifq-slide-'), 15)
        self.assertIn("SLIDE 1", self.html)
        self.assertIn("SLIDE 15", self.html)

    def test_answer_and_connector_crosslinks(self):
        # answers wired to the sized pages
        for route in ("/ift-study", "/ift-markets", "/ift-research",
                      "/ift-clinical", "/ift-mmt", "/connector-estate",
                      "/api/ift/markets.xlsx"):
            self.assertIn(route, self.html, f"missing crosslink {route}")
        # per-slide connector chips point back into the estate by dataset id
        self.assertIn("/connector-estate?dataset=", self.html)
        self.assertGreater(self.html.count("/connector-estate?dataset="), 20)

    def test_answers_rendered_inline_from_sized_modules(self):
        # each slide carries its ANSWER inline (not just a link) — real content
        # pulled from the same modules the sized pages render.
        self.assertIn("ifq-ans-lab", self.html)          # answer block chrome
        self.assertIn("Go deeper on the sized pages", self.html)
        self.assertIn("The sub-questions behind it", self.html)
        # headline sized answer up top
        self.assertIn("TAM · all US ground IFT", self.html)
        # taxonomy matrix answer (IFT column highlighted)
        self.assertIn("911 Emergency", self.html)
        self.assertIn('class="ifq-ift"', self.html)
        # patient-journey, operating-model, MMT, competitive, moat answers present
        for needle in ("Community / referring hospital",
                       "Hybrid — mostly outsourced",
                       "Omaha, Nebraska",
                       "First-call relationship",
                       "Infrastructure for care transitions"):
            self.assertIn(needle, self.html, f"missing inline answer: {needle}")

    def test_degrades_when_answer_sources_unavailable(self):
        # answer builders must never break the page if a source module raises
        import rcm_mc.market_reports.ift_study as st
        saved = (st.taxonomy_matrix, st.ecosystem, st.operating_models,
                 st.company_positioning)

        def boom(*a, **k):
            raise RuntimeError("simulated outage")
        try:
            st.taxonomy_matrix = st.ecosystem = boom
            st.operating_models = st.company_positioning = boom
            html = self._render()
            self.assertEqual(html.count("<h1"), 1)
            self.assertIn("</html>", html.lower())
            self.assertEqual(html.count('id="ifq-slide-'), 15)
            self.assertIn("The sub-questions behind it", html)  # tree intact
        finally:
            (st.taxonomy_matrix, st.ecosystem, st.operating_models,
             st.company_positioning) = saved

    def test_evidence_visuals_nuances_sections(self):
        for section in ("Cross-slide data &amp; evidence plan",
                        "Best-overall visual package",
                        "The nuances not to miss",
                        "The connectors behind the evidence"):
            self.assertIn(section, self.html, f"missing section: {section}")

    def test_content_is_leak_free(self):
        for bad in (">None<", "None</td>", ">nan<", "Slide(", "QGroup(",
                    "TreeBranch(", "ConnectorEvidence(", "VisualRec(", "()>"):
            self.assertNotIn(bad, self.html, f"leak: {bad!r}")

    def test_route_wired_into_server(self):
        src = pathlib.Path("rcm_mc/server.py").read_text(encoding="utf-8")
        self.assertIn('path == "/ift-diligence"', src)
        self.assertIn("render_ift_diligence", src)

    def test_registered_in_palette(self):
        from rcm_mc.ui._chartis_kit import _DEFAULT_PALETTE_MODULES
        routes = {m["route"] for m in _DEFAULT_PALETTE_MODULES}
        self.assertIn("/ift-diligence", routes)

    def test_linked_from_ift_markets_page(self):
        from rcm_mc.ui.ift_markets_page import render_ift_markets
        markets = render_ift_markets()
        self.assertIn("/ift-diligence", markets)


if __name__ == "__main__":
    unittest.main()
