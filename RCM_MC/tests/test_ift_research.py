"""Tests for the IFT market-level research brief (module + /ift-research page)."""
import pathlib
import unittest

from rcm_mc.market_reports import ift_research as r


class TestResearchModule(unittest.TestCase):
    def test_industry_context_available(self):
        ic = r.industry_context()
        self.assertTrue(ic.available)
        self.assertTrue(ic.items)
        self.assertIn("IBISWorld", ic.source_label)

    def test_authored_sections_present_and_labelled(self):
        secs = r.research_sections()
        self.assertGreaterEqual(len(secs), 8)
        ids = {s["id"] for s in secs}
        for want in ("reimbursement", "unit-economics", "kpis", "technology",
                     "regulatory", "segmentation", "sizing", "growth", "evidence"):
            self.assertIn(want, ids, f"missing research section {want}")
        # every subsection carries a valid honesty basis
        for s in secs:
            self.assertTrue(s.get("title") and s.get("intro"))
            for ss in s["subsections"]:
                self.assertIn(ss.get("basis"),
                              ("GOV", "ACADEMIC", "ILLUSTRATIVE", "FRAMEWORK"),
                              f"{s['id']}::{ss.get('heading')} bad basis")
                # a subsection is either a table (columns) or bullets
                self.assertTrue(ss.get("columns") or ss.get("bullets"))

    def test_brief_rollup(self):
        b = r.research_brief()
        self.assertTrue(b.available)
        self.assertGreaterEqual(b.n_sections, 8)
        self.assertTrue(b.source_label and b.note)


class TestResearchPage(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from rcm_mc.ui.ift_research_page import render_ift_research
        cls.html = render_ift_research()

    def test_full_single_title(self):
        self.assertGreater(len(self.html), 60_000)
        self.assertEqual(self.html.count("<h1"), 1)
        self.assertIn("</html>", self.html.lower())

    def test_market_level_sections_present(self):
        # ampersands render as &amp;, so match on ampersand-free substrings.
        for marker in ("Market definition", "Industry structure",
                       "Patient journey", "Operating models, procurement",
                       "Competitive landscape by provider type",
                       "Performance metrics", "Reimbursement",
                       "Unit economics", "Market sizing methodology",
                       "Segmentation framework", "Regulatory",
                       "Evidence quality"):
            self.assertIn(marker, self.html, f"missing: {marker}")

    def test_real_gov_anchors_named(self):
        for anchor in ("No Surprises Act", "Physician Certification",
                       "Ambulance Fee Schedule", "42 CFR 431.53"):
            self.assertIn(anchor, self.html, f"missing GOV anchor {anchor}")

    def test_honesty_chips_and_toc(self):
        self.assertIn("irs-chip-gov", self.html)
        self.assertIn("irs-chip-framework", self.html)
        self.assertIn("irs-toc", self.html)          # table of contents

    def test_crosslinks_and_market_level_discipline(self):
        self.assertIn("/ift-study", self.html)
        self.assertIn("/ift-markets", self.html)
        self.assertIn("/api/ift/markets.xlsx", self.html)
        self.assertIn("no company-specific", self.html.lower())

    def test_leak_free(self):
        for bad in (">None<", "None</td>", "CompanyProfile(", "{'id'"):
            self.assertNotIn(bad, self.html, f"leak: {bad!r}")

    def test_route_wired(self):
        src = pathlib.Path("rcm_mc/server.py").read_text(encoding="utf-8")
        self.assertIn('path == "/ift-research"', src)
        self.assertIn("render_ift_research", src)


if __name__ == "__main__":
    unittest.main()
