"""Deal-driven PE Intelligence tool runner (/diligence/pe-tool).

These tools were dark; this guards that they now run against a REAL deal's
analysis packet (no fabricated inputs), render to HTML, and degrade honestly
when a deal/packet is missing.
"""
from __future__ import annotations

import pathlib
import tempfile
import unittest

from rcm_mc.ui.pe_tool_page import (
    PE_TOOL_REGISTRY,
    _md_to_html,
    render_pe_tool_page,
    run_review_tool,
)

_SERVER = pathlib.Path(__file__).resolve().parents[1] / "rcm_mc" / "server.py"


def _real_review():
    from tests.test_alerts import _seed_with_pe_math
    from rcm_mc.analysis.analysis_store import get_or_build_packet
    from rcm_mc import pe_intelligence as pei
    tmp = tempfile.mkdtemp()
    store = _seed_with_pe_math(tmp, "ccf", headroom=-0.5)
    packet = get_or_build_packet(store, "ccf", skip_simulation=True)
    return pei.partner_review(packet)


class RunReviewToolTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.review = _real_review()

    def test_every_registered_tool_runs_on_real_deal(self):
        # No-fake-data: each tool must produce output from the real PartnerReview.
        for slug in PE_TOOL_REGISTRY:
            md, err = run_review_tool(slug, self.review)
            self.assertIsNone(err, f"{slug} failed: {err}")
            self.assertGreater(len(md), 20, slug)

    def test_unknown_tool_errors_cleanly(self):
        md, err = run_review_tool("not_a_tool", self.review)
        self.assertEqual(md, "")
        self.assertIsNotNone(err)

    def test_registry_excludes_deal_independent_tools(self):
        # Honesty guard: tools that ignore the review (constant output) must NOT
        # be wired as deal-driven — they'd falsely imply "computed from your
        # deal". Audited and excluded; keep them out.
        for slug in ("named_failure_library_v2", "historical_failure_library",
                     "partner_traps_library", "quality_of_diligence_scorer",
                     "data_room_gap_signal_reader"):
            self.assertNotIn(slug, PE_TOOL_REGISTRY)

    def test_diligence_board_is_deal_driven(self):
        # The newly-added tool must genuinely vary with the deal.
        self.assertIn("diligence_tracker", PE_TOOL_REGISTRY)
        md, err = run_review_tool("diligence_tracker", self.review)
        self.assertIsNone(err)
        self.assertIn("Diligence Board", md)


class DefaultDealTests(unittest.TestCase):
    def test_deals_with_packets_prefers_built(self):
        # The runner defaults to a deal that already has a packet so the page
        # looks filled out rather than hollow. Helper must surface built deals.
        from tests.test_alerts import _seed_with_pe_math
        from rcm_mc.analysis.analysis_store import (
            deals_with_packets, get_or_build_packet)
        store = _seed_with_pe_math(tempfile.mkdtemp(), "ccf", headroom=-0.5)
        self.assertEqual(deals_with_packets(store), [])
        get_or_build_packet(store, "ccf", skip_simulation=True)
        self.assertIn("ccf", deals_with_packets(store))


class MarkdownTests(unittest.TestCase):
    def test_renders_headings_tables_bold(self):
        md = "# Title\n\nLead **bold**.\n\n| A | B |\n|---|---|\n| 1 | 2 |\n\n- item"
        h = _md_to_html(md)
        self.assertIn("<h2", h)
        self.assertIn("<table", h)
        self.assertIn("<strong>bold</strong>", h)
        self.assertIn("<li", h)

    def test_escapes_html(self):
        self.assertIn("&lt;script&gt;", _md_to_html("<script>"))

    def test_blockquote_hr_ordered_not_literal(self):
        # Regression: these constructs used to leak through as literal
        # &gt; / --- / "1." (old-looking output). They must render as elements.
        h = _md_to_html("> a quote\n\n1. first\n2. second\n\n---\n\ntail")
        self.assertIn("<blockquote", h)
        self.assertIn("<ol ", h)
        self.assertIn("<hr ", h)
        # no literal markdown left in paragraphs
        self.assertNotRegex(h, r"<p[^>]*>\s*&gt;")
        self.assertNotRegex(h, r"<p[^>]*>\d+\.\s")

    def test_real_tool_output_has_no_literal_markdown(self):
        # The two tools that emit blockquotes / hr / numbered lists must render
        # clean (no &gt;/---/"1." leaking) on a real deal.
        review = _real_review()
        for slug in ("analyst_cheatsheet", "partner_discussion"):
            md, _ = run_review_tool(slug, review)
            html = _md_to_html(md)
            self.assertNotRegex(html, r"<p[^>]*>\s*&gt;", slug)
            self.assertNotRegex(html, r"<p[^>]*>-{3,}</p>", slug)


class ToolPageTests(unittest.TestCase):
    def test_no_deals_empty_state(self):
        h = render_pe_tool_page("hundred_day_plan", None, "", "", [])
        self.assertIn("No deal loaded", h)

    def test_unknown_tool_prompts_pick(self):
        h = render_pe_tool_page("", None, "ccf", "CCF", [("ccf", "CCF")])
        self.assertIn("Pick a tool", h)

    def test_renders_tool_on_real_deal(self):
        review = _real_review()
        h = render_pe_tool_page("hundred_day_plan", review, "ccf", "CCF",
                                [("ccf", "CCF")])
        self.assertIn("100-Day Plan", h)
        self.assertIn("Run</button>", h)   # deal picker present
        self.assertIn("ck-panel", h)

    def test_packet_error_shows_guidance_not_crash(self):
        h = render_pe_tool_page("hundred_day_plan", None, "ccf", "CCF",
                                [("ccf", "CCF")], error="packet build failed")
        self.assertIn("Could not run on this deal", h)

    def test_route_wired(self):
        src = _SERVER.read_text()
        self.assertIn('path == "/diligence/pe-tool"', src)
        self.assertIn("render_pe_tool_page", src)

    def test_classified_navy_and_ranked(self):
        from rcm_mc.diligence.surface_status import classify_surface
        from rcm_mc.ui._surface_rankings import RANKINGS
        self.assertEqual(classify_surface("/diligence/pe-tool")["tier"], "navy")
        self.assertIn("/diligence/pe-tool",
                      {r["route"] for r in RANKINGS.get("diligence", [])})

    def test_library_marks_runnable(self):
        from rcm_mc.ui.pe_library_page import render_pe_library_page
        h = render_pe_library_page()
        self.assertIn("RUN ON DEAL", h)
        self.assertIn("/diligence/pe-tool?tool=", h)


if __name__ == "__main__":
    unittest.main()
