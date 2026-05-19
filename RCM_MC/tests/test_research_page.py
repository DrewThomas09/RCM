"""Test for the /research editorial renderer.

Cycle 9 builds /research as a curated content-listing surface that
sits visually alongside `/library` and `/notes` as the third sibling
on the chartis Insights triplet pattern. These tests pin the
editorial chrome, the catalog surfacing, and the facet semantics.

Doesn't test the catalog content itself — `RESEARCH_ENTRIES` is a
curated list that may evolve.
"""
from __future__ import annotations

import html as _html
import unittest

from rcm_mc.ui.research_page import RESEARCH_ENTRIES, render_research


def _extract_research_grid(html: str) -> str:
    """Return only the markup between the grid's opening + closing tags.

    The chartis_shell ships a Cmd+K palette as page chrome AFTER the
    grid; that palette lists `Bear Cases` as a navigable route. A
    naive `html.split('class="ck-research-grid"')[1]` captures the
    palette and produces false-positive matches. This helper scopes
    assertions to the actual grid contents by counting balanced
    <div> tags (the grid wrapper contains <article> cards which
    themselves contain inner <div class="ck-eyebrow"> blocks, so
    we can't stop at the first </div>).
    """
    start = html.find('class="ck-research-grid"')
    if start == -1:
        return ""
    open_div = html.rfind("<div", 0, start)
    if open_div == -1:
        return ""
    # Walk forward from the END of the grid's opening tag; depth
    # starts at 1 because the wrapper itself is already open. We
    # decrement on every </div> and increment on every nested <div>.
    grid_open_end = html.find(">", start) + 1
    depth = 1
    i = grid_open_end
    while i < len(html):
        next_open = html.find("<div", i)
        next_close = html.find("</div>", i)
        if next_close == -1:
            return html[open_div:]
        if next_open != -1 and next_open < next_close:
            depth += 1
            i = next_open + len("<div")
        else:
            depth -= 1
            if depth == 0:
                return html[open_div : next_close + len("</div>")]
            i = next_close + len("</div>")
    return html[open_div:]


class ResearchEditorialChromeTests(unittest.TestCase):
    def test_unfiltered_renders_all_entries(self) -> None:
        html = render_research()
        self.assertIn('class="ck-search-hero"', html)
        self.assertIn('class="ck-rail-layout"', html)
        self.assertIn('class="ck-results-header"', html)
        self.assertIn('class="ck-research-grid"', html)
        self.assertIn(
            f'>{len(RESEARCH_ENTRIES):,}<', html,
        )
        # Every catalog entry's title appears in the grid (HTML-
        # escaped — entries with `&` in the title render as `&amp;`).
        for entry in RESEARCH_ENTRIES:
            self.assertIn(_html.escape(entry["title"]), html)

    def test_topic_filter_narrows_results(self) -> None:
        html = render_research(topic="Methodology")
        # Methodology Hub is in the filtered set
        self.assertIn("Methodology Hub", html)
        # An entry from a different topic should NOT appear in the grid
        # (it may still appear in the filter sidebar option list).
        grid_section = _extract_research_grid(html)
        self.assertNotIn("Conference Roadmap", grid_section)

    def test_kind_filter_narrows_results(self) -> None:
        html = render_research(kind="Reference")
        # Limit the search window to the actual research grid, not
        # everything that follows it — the Cmd+K palette (injected by
        # chartis_shell at page end) lists "Bear Cases" as a palette
        # route, which used to leak into the post-grid split and
        # cause false-positive failures.
        grid_section = _extract_research_grid(html)
        # Reference items are present
        self.assertIn("Methodology Hub", grid_section)
        # Case Studies items are not
        self.assertNotIn("Bear Cases", grid_section)

    def test_keyword_search_matches_title_or_body(self) -> None:
        html = render_research(q="conference")
        # Conference Roadmap title contains "conference"
        self.assertIn("Conference Roadmap", html)
        # Empty hit on bear-cases (no "conference" substring there)
        grid_section = _extract_research_grid(html)
        self.assertNotIn("Bear Cases", grid_section)

    def test_zero_match_renders_affirm_band(self) -> None:
        html = render_research(q="thiswillneverbeintheresearchcatalog")
        self.assertIn("No research matches", html)
        # Grid is suppressed when zero matches
        self.assertNotIn('class="ck-research-grid"', html)

    def test_active_filters_emit_chips_and_clear_all(self) -> None:
        html = render_research(topic="Methodology", q="hub")
        self.assertIn('<div class="ck-results-chips">', html)
        # Topic chip
        self.assertIn(">Methodology <span class=\"ck-chip-x\"", html)
        # Search chip — q is wrapped in &quot;
        self.assertIn("&quot;hub&quot;", html)
        # Clear all anchor
        self.assertIn(
            '<a class="ck-arrow" href="/research">Clear all</a>', html,
        )

    def test_chip_remove_href_drops_only_that_facet(self) -> None:
        html = render_research(topic="Methodology", kind="Reference", q="hub")
        # The topic chip's remove_href preserves kind + q
        chip_block = html.split('<div class="ck-results-chips">')[1]
        self.assertIn(
            '/research?q=hub&amp;kind=Reference', chip_block,
        )

    def test_filter_sidebar_emits_topic_and_kind_groups(self) -> None:
        html = render_research()
        self.assertIn(">By topic</header>", html)
        self.assertIn(">By format</header>", html)

    def test_search_hero_round_trips_active_facets(self) -> None:
        html = render_research(topic="Methodology", kind="Reference")
        self.assertIn(
            '<input type="hidden" name="topic" value="Methodology">', html,
        )
        self.assertIn(
            '<input type="hidden" name="kind" value="Reference">', html,
        )

    def test_card_links_to_entry_href(self) -> None:
        html = render_research(q="methodology hub")
        # Card title contains an anchor to /methodology
        self.assertIn('href="/methodology"', html)

    def test_label_pluralizes_with_count(self) -> None:
        html_one = render_research(q="conference roadmap")  # likely 1 hit
        html_many = render_research()  # 8 entries
        self.assertIn(">Note</span>", html_one)
        self.assertIn(">Notes</span>", html_many)


if __name__ == "__main__":
    unittest.main()
