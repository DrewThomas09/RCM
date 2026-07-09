"""Tests for the IFT sourcing prompts — Part 1 (module + /ift-sourcing page).

Pins the scope boundary, the 10 prompts (verbatim + boundary-prefixed), the
priority set (2/4/6), the live-source/connector wiring, and the page render
(single title, copy affordances, leak-free, route + palette + cross-links).
"""
import pathlib
import unittest

from rcm_mc.market_reports import ift_sourcing as s


class TestSourcingModule(unittest.TestCase):
    def test_scope_boundary_present_and_excludes_the_adjacents(self):
        b = s.scope_boundary()
        self.assertTrue(b)
        for token in ("interfacility", "911", "NEMT", "air ambulance",
                      "both endpoints are facilities"):
            self.assertIn(token, b, f"boundary missing {token!r}")

    def test_ten_prompts_boundary_prefixed(self):
        ps = s.sourcing_prompts()
        self.assertEqual(len(ps), 10)
        nums = [p.num for p in ps]
        self.assertEqual(nums, list(range(1, 11)))
        self.assertEqual(len({p.slug for p in ps}), 10)      # unique anchors
        for p in ps:
            self.assertTrue(p.title and p.prompt and p.why and p.sources)
            # the copy-paste unit prefixes the boundary
            self.assertTrue(p.full_prompt.startswith(s.scope_boundary()))
            self.assertIn(p.prompt, p.full_prompt)

    def test_priority_set_is_two_four_six(self):
        self.assertEqual(s.priority_prompts(), (2, 4, 6))
        by_num = {p.num: p for p in s.sourcing_prompts()}
        for n in (2, 4, 6):
            self.assertTrue(by_num[n].priority)
        for n in (1, 3, 5, 7, 8, 9, 10):
            self.assertFalse(by_num[n].priority)

    def test_claims_method_prompt_carries_the_modifier_set(self):
        by_num = {p.num: p for p in s.sourcing_prompts()}
        p2 = by_num[2]
        for token in ("A0426", "A0434", "A0425",
                      "{H, N, E, G, J, D, I}", "Limited Data Set"):
            self.assertIn(token, p2.prompt, f"claims prompt missing {token!r}")

    def test_sources_carry_valid_bases(self):
        for p in s.sourcing_prompts():
            for name, basis in p.sources:
                self.assertTrue(name)
                self.assertIn(basis, ("GOV", "ACADEMIC", "INDUSTRY"),
                              f"prompt {p.num} bad source basis {basis!r}")

    def test_connector_keys_resolve_in_live_estate(self):
        ce = s.connector_evidence()
        self.assertTrue(ce.available)
        for p in s.sourcing_prompts():
            self.assertTrue(p.connector_keys, f"prompt {p.num} has no connectors")
            for k in p.connector_keys:
                self.assertIn(k, ce.probes_by_key,
                              f"prompt {p.num} references unknown connector {k!r}")

    def test_answer_links_point_at_real_surfaces(self):
        from rcm_mc.market_reports.ift_diligence import LINK
        known = {route for route, _lbl in LINK.values()}
        known.add("/ift-diligence")                          # slide anchors' base
        for p in s.sourcing_prompts():
            self.assertTrue(p.answered_by, f"prompt {p.num} has no answer link")
            for _txt, href in p.answered_by:
                base = href.split("#")[0]
                self.assertIn(base, known,
                              f"prompt {p.num} links to unknown route {href}")

    def test_summary_counts(self):
        summ = s.sourcing_summary()
        self.assertEqual(summ["n_prompts"], 10)
        self.assertEqual(summ["n_priority"], 3)
        self.assertEqual(summ["priority_set"], [2, 4, 6])
        self.assertGreater(summ["n_sources"], 15)
        self.assertGreater(summ["n_connectors_used"], 0)
        self.assertEqual(summ["part"], 1)


class TestSourcingPage(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from rcm_mc.ui.ift_sourcing_page import render_ift_sourcing
        cls._render = staticmethod(render_ift_sourcing)
        cls.html = render_ift_sourcing()

    def test_full_document_single_title(self):
        self.assertGreater(len(self.html), 40_000)
        self.assertEqual(self.html.count("<h1"), 1)
        self.assertIn("</html>", self.html.lower())

    def test_boundary_priority_and_all_prompts(self):
        self.assertIn("The scope boundary", self.html)
        self.assertIn("If you only run three", self.html)
        self.assertIn("both endpoints are facilities", self.html)
        self.assertEqual(self.html.count('class="ifs-num">PROMPT '), 10)  # 10 panels
        for n in (1, 6, 10):
            self.assertIn(f'id="ifs-p{n}"', self.html)       # panel anchors
        for token in ("PROMPT 1", "PROMPT 10", "{H, N, E, G, J, D, I}", "RSNAT"):
            self.assertIn(token, self.html)

    def test_current_research_read_rendered_inline(self):
        # the page is fleshed out with findings, not just prompts — real figures
        # pulled from the sized modules, one research block per prompt.
        self.assertGreaterEqual(self.html.count("Current research read"), 10)
        for needle in ("Medicare FFS GROUND",          # denominator (TAM)
                       "both endpoints in {H, N, E, G, J, D, I}",  # claims method
                       "blended escalation CAGR",       # demographic engine
                       "Post-acute setting",            # post-acute universe
                       "SCT (A0434)",                   # RVU over-index
                       "RSNAT prior authorization",     # policy discontinuity
                       "high-acuity incl. behavioral"): # mission mix
            self.assertIn(needle, self.html, f"missing research finding: {needle}")

    def test_degrades_when_a_findings_module_raises(self):
        import rcm_mc.market_reports.ift_analytics as an
        saved = (an.ground_tam, an.occupancy_trend)

        def boom(*a, **k):
            raise RuntimeError("simulated outage")
        try:
            an.ground_tam = an.occupancy_trend = boom
            html = self._render()
            self.assertEqual(html.count("<h1"), 1)
            self.assertIn("</html>", html.lower())
            self.assertEqual(html.count('class="ifs-num">PROMPT '), 10)
        finally:
            an.ground_tam, an.occupancy_trend = saved

    def test_copy_affordances_present(self):
        # a boundary copy button + one per prompt, each targeting a <pre> id
        self.assertIn('data-target="ifs-boundary-text"', self.html)
        self.assertIn('data-target="ifs-prompt-claims-method"', self.html)
        self.assertGreaterEqual(self.html.count("ifs-copy"), 11)

    def test_source_and_connector_crosslinks(self):
        for route in ("/ift-diligence", "/ift-markets", "/ift-clinical",
                      "/connector-estate"):
            self.assertIn(route, self.html, f"missing crosslink {route}")
        self.assertIn("/connector-estate?dataset=", self.html)
        self.assertIn("/ift-diligence#ifq-slide-", self.html)

    def test_content_is_leak_free(self):
        for bad in (">None<", "None</td>", ">nan<", "SourcingPrompt(", "()>",
                    "&lt;script"):
            self.assertNotIn(bad, self.html, f"leak: {bad!r}")

    def test_route_wired_and_registered(self):
        src = pathlib.Path("rcm_mc/server.py").read_text(encoding="utf-8")
        self.assertIn('path == "/ift-sourcing"', src)
        self.assertIn("render_ift_sourcing", src)
        from rcm_mc.ui._chartis_kit import _DEFAULT_PALETTE_MODULES
        self.assertIn("/ift-sourcing",
                      {m["route"] for m in _DEFAULT_PALETTE_MODULES})

    def test_linked_from_diligence_page(self):
        from rcm_mc.ui.ift_diligence_page import render_ift_diligence
        self.assertIn("/ift-sourcing", render_ift_diligence())


if __name__ == "__main__":
    unittest.main()
