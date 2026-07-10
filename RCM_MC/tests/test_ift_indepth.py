"""Tests for the IFT In-Depth surface (/ift-indepth).

Pins the writing contract the page promises: ten questions, every block
conclusion-led (conclusion → why-true → why-matters → evidence), every
subquestion answered or explicitly skipped as a diligence request, no banned
filler phrases, no ILLUSTRATIVE basis anywhere, and a page render that is
leak-free and — after the /ift-demand incident — free of double-escaped
markup.
"""
import pathlib
import unittest

from rcm_mc.market_reports import ift_indepth as idp

_VALID_BASES = {"GOV", "SOURCED", "ACADEMIC", "DERIVED", "FRAMEWORK"}


def _all_text(q) -> str:
    """Every human-readable string in one question, lowercased, for
    banned-phrase scanning."""
    parts = [q.title, q.storyline]
    for b in q.blocks:
        parts += [b.title, b.conclusion, b.why_matters]
        parts += list(b.why_true)
        for e in b.evidence:
            parts += [e.text, e.source]
        for s in b.subqs:
            parts += [s.q, s.a, s.skip]
    return " ".join(parts).lower()


class TestInDepthModule(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.qs = idp.questions()

    def test_all_ten_questions_present(self):
        self.assertEqual([q.num for q in self.qs], list(range(1, 11)))
        slugs = {q.slug for q in self.qs}
        self.assertEqual(len(slugs), 10)          # unique anchors

    def test_every_visual_key_resolves(self):
        from rcm_mc.ui.ift_indepth_page import _VISUALS
        for q in self.qs:
            self.assertIn(q.visual_key, _VISUALS,
                          f"Q{q.num} visual_key {q.visual_key!r} unknown")
        # all ten visuals are used exactly once (one bespoke visual each)
        self.assertEqual(len({q.visual_key for q in self.qs}), 10)

    def test_blocks_follow_writing_contract(self):
        for q in self.qs:
            self.assertTrue(q.blocks, f"Q{q.num} has no blocks")
            self.assertTrue(q.storyline, f"Q{q.num} has no storyline")
            for b in q.blocks:
                ctx = f"Q{q.num}/{b.key}"
                self.assertTrue(b.conclusion, f"{ctx}: no conclusion")
                self.assertGreaterEqual(
                    len(b.why_true), 2, f"{ctx}: needs >=2 findings")
                self.assertTrue(b.why_matters, f"{ctx}: no implication")
                for s in b.subqs:
                    self.assertTrue(
                        s.a or s.skip,
                        f"{ctx}: subquestion neither answered nor "
                        f"skipped: {s.q!r}")

    def test_block_keys_unique_across_page(self):
        # block keys become DOM ids — a collision breaks anchors
        keys = [b.key for q in self.qs for b in q.blocks]
        self.assertEqual(len(keys), len(set(keys)))

    def test_coverage_complete_and_substantial(self):
        cov = idp.coverage()
        self.assertEqual(cov["questions"], 10)
        self.assertEqual(cov["unaccounted"], 0)
        self.assertGreaterEqual(cov["subquestions"], 300)
        # answered dominates; skips are the honest company-data minority
        self.assertGreaterEqual(cov["answered"], cov["subquestions"] * 0.7)

    def test_no_banned_phrases_or_illustrative(self):
        for q in self.qs:
            text = _all_text(q)
            for phrase in idp.BANNED_PHRASES:
                self.assertNotIn(phrase.lower(), text,
                                 f"Q{q.num} contains banned phrase "
                                 f"{phrase!r}")
            self.assertNotIn("illustrative", text,
                             f"Q{q.num} uses 'illustrative'")

    def test_evidence_bases_valid(self):
        for q in self.qs:
            for b in q.blocks:
                for e in b.evidence:
                    self.assertIn(e.basis, _VALID_BASES,
                                  f"Q{q.num}/{b.key}: bad basis "
                                  f"{e.basis!r}")
                    self.assertTrue(e.text and e.source,
                                    f"Q{q.num}/{b.key}: empty evidence")

    def test_question_lookup(self):
        self.assertEqual(idp.question(1).slug, "markets")
        self.assertIsNone(idp.question(99))


class TestInDepthPage(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from rcm_mc.ui.ift_indepth_page import render_ift_indepth
        cls._render = staticmethod(render_ift_indepth)
        cls.html = render_ift_indepth()

    def test_full_document_single_title(self):
        self.assertGreater(len(self.html), 100_000)
        self.assertEqual(self.html.count("<h1"), 1)
        self.assertIn("</html>", self.html.lower())

    def test_all_ten_questions_rendered_with_toc(self):
        for n in range(1, 11):
            self.assertIn(f'id="idp-q{n}"', self.html, f"Q{n} anchor missing")
            self.assertIn(f'href="#idp-q{n}"', self.html,
                          f"Q{n} TOC link missing")
        self.assertIn("THE ANSWER IN ONE LINE", self.html)

    def test_storyline_arc_present(self):
        import html as _html
        self.assertIn('class="idp-arc"', self.html)
        for step in idp.STORYLINE:
            # the renderer escapes each step (apostrophes -> &#x27;)
            self.assertIn(_html.escape(step), self.html,
                          f"arc step missing: {step!r}")

    def test_writing_contract_chrome(self):
        # the conclusion-led structure is visible page chrome, not prose
        self.assertGreaterEqual(self.html.count("Conclusion"), 40)
        self.assertGreaterEqual(self.html.count("Why it is true"), 40)
        self.assertGreaterEqual(self.html.count("Why it matters"), 40)
        self.assertIn("subquestions —", self.html)  # coverage <details>

    def test_all_ten_visuals_render_nonempty(self):
        from rcm_mc.ui import ift_indepth_page as pg
        for key, builder in pg._VISUALS.items():
            out = builder()
            self.assertGreater(len(out), 200, f"visual {key!r} is empty")
            self.assertNotIn("&lt;", out, f"visual {key!r} double-escaped")

    def test_no_double_escaped_markup(self):
        # regression guard from the /ift-demand incident: pre-built markup
        # must never pass through an escaping helper again.
        for bad in ("&lt;strong&gt;", "&lt;span", "&lt;a href", "&amp;lt;",
                    "-&amp;gt;", "&lt;div", "&lt;td"):
            self.assertNotIn(bad, self.html, f"double-escape leak: {bad!r}")

    def test_content_is_leak_free(self):
        for bad in (">None<", "None</td>", ">nan<", "SubQ(", "Block(",
                    "Evidence(", "QuestionDef(", "()>"):
            self.assertNotIn(bad, self.html, f"leak: {bad!r}")

    def test_coverage_footer_reports_zero_unaccounted(self):
        self.assertIn("Coverage check:", self.html)
        self.assertIn("0 unaccounted", self.html)

    def test_degrades_when_content_unavailable(self):
        import rcm_mc.ui.ift_indepth_page as pg
        saved = (pg._idp.questions, pg._idp.coverage)

        def boom(*a, **k):
            raise RuntimeError("simulated outage")
        try:
            pg._idp.questions = boom
            pg._idp.coverage = boom
            html = self._render()
            self.assertEqual(html.count("<h1"), 1)
            self.assertIn("</html>", html.lower())
            self.assertIn("honest empty state", html)
        finally:
            pg._idp.questions, pg._idp.coverage = saved

    def test_route_wired_into_server(self):
        src = pathlib.Path("rcm_mc/server.py").read_text(encoding="utf-8")
        self.assertIn('path == "/ift-indepth"', src)
        self.assertIn("render_ift_indepth", src)

    def test_registered_in_palette(self):
        from rcm_mc.ui._chartis_kit import _DEFAULT_PALETTE_MODULES
        routes = {m["route"] for m in _DEFAULT_PALETTE_MODULES}
        self.assertIn("/ift-indepth", routes)

    def test_hub_card_present(self):
        from rcm_mc.ui.ift_hub_page import _SURFACES
        self.assertIn("/ift-indepth", {r for r, *_ in _SURFACES})


if __name__ == "__main__":
    unittest.main()
