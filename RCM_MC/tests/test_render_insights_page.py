"""Test the render_insights_page helper.

Cycle 18 lifts the chartis Insights triplet wiring (search hero +
filter sidebar + results header + chip URLs + extra_hidden round-
trip + Clear all + intro) into one call. This decorator-shaped
helper composes ~5 ck_* primitives plus chartis_shell behind a
single signature so future content-listing ports drop from ~200
LOC to ~20 LOC. These tests pin the API contract.
"""
from __future__ import annotations

import unittest

from rcm_mc.ui._chartis_kit import render_insights_page


def _facet(
    name="topic",
    title="By topic",
    input_type="radio",
    options=None,
):
    return {
        "name": name,
        "title": title,
        "input_type": input_type,
        "options": options or [
            {"label": "All", "value": "", "checked": True},
            {"label": "AI", "value": "ai", "checked": False},
        ],
    }


class RenderInsightsPageContractTests(unittest.TestCase):
    def test_minimal_render_emits_full_chrome(self):
        html = render_insights_page(
            action="/library",
            state={},
            facets=[_facet()],
            count=0,
            body_html="<p>no results</p>",
            title="Library",
        )
        # Triplet wrappers all present
        self.assertIn('class="ck-search-hero"', html)
        self.assertIn('class="ck-filter-rail"', html)
        self.assertIn('class="ck-rail-layout"', html)
        self.assertIn('class="ck-results-header"', html)
        # Body slots in the right place
        self.assertIn("<p>no results</p>", html)
        # No chips when state is empty
        self.assertNotIn('class="ck-results-chips"', html)

    def test_active_state_emits_chips_and_clear_all(self):
        html = render_insights_page(
            action="/library",
            state={"q": "Apollo", "topic": "ai"},
            facets=[_facet()],
            count=12,
            body_html="<p>x</p>",
            title="Library",
        )
        self.assertIn('class="ck-results-chips"', html)
        # Keyword chip wraps in &quot;...&quot;
        self.assertIn("&quot;Apollo&quot;", html)
        # Topic chip carries the value as label by default
        self.assertIn(">ai <span", html)
        # Clear all link present
        self.assertIn(
            '<a class="ck-arrow" href="/library">Clear all</a>', html,
        )

    def test_chip_remove_href_drops_only_target_facet(self):
        html = render_insights_page(
            action="/library",
            state={"q": "Apollo", "topic": "ai", "kind": "ref"},
            facets=[_facet(), _facet(name="kind", title="By kind")],
            count=5,
            body_html="<p>x</p>",
            title="Library",
        )
        # The topic chip's remove_href must keep q + kind, drop topic
        chip_block = html.split('class="ck-results-chips"')[1]
        topic_chip_start = chip_block.index(">ai <span")
        chip_html = chip_block[max(0, topic_chip_start - 200):topic_chip_start + 50]
        self.assertIn("q=Apollo", chip_html)
        self.assertIn("kind=ref", chip_html)
        # topic= must NOT appear in this chip's href (it's the one
        # being removed)
        href_start = chip_html.rindex('href="')
        href_end = chip_html.index('"', href_start + 6)
        self.assertNotIn("topic=", chip_html[href_start:href_end])

    def test_search_hero_round_trips_non_keyword_state(self):
        html = render_insights_page(
            action="/library",
            state={"q": "Apollo", "topic": "ai", "sort_by": "moic"},
            facets=[_facet()],
            count=0,
            body_html="<p>x</p>",
            title="Library",
        )
        # Hero form contains hidden inputs for topic + sort_by but
        # NOT for q (the keyword is the visible input).
        self.assertIn(
            '<input type="hidden" name="topic" value="ai">', html,
        )
        self.assertIn(
            '<input type="hidden" name="sort_by" value="moic">', html,
        )
        # Keyword input itself carries the q value
        self.assertIn(' value="Apollo"', html)

    def test_filter_sidebar_round_trips_keyword(self):
        html = render_insights_page(
            action="/library",
            state={"q": "Apollo", "topic": "ai"},
            facets=[_facet()],
            count=0,
            body_html="<p>x</p>",
            title="Library",
        )
        # Filter form should carry q as a hidden input so toggling
        # a facet doesn't drop the keyword.
        rail_block = html.split('class="ck-filter-rail"')[1]
        rail_form_block = rail_block[:rail_block.index('</form>')]
        self.assertIn(
            '<input type="hidden" name="q" value="Apollo">',
            rail_form_block,
        )

    def test_intro_kwargs_render_strict_5_block_head(self):
        # 2026-05-28 style-sweep · intro kwargs now compose the strict
        # Tier-1 5-block head (eyebrow with dash → serif h1 → italic
        # deck → lede → status-dot legend) instead of the legacy
        # ck_section_intro h2 deck. The italicized word AND the
        # eyebrow text still appear in the rendered output; the
        # wrapper class changed from ck-section-intro to ip-head.
        html = render_insights_page(
            action="/library",
            state={},
            facets=[_facet()],
            count=0,
            body_html="<p>x</p>",
            title="Library",
            intro={
                "eyebrow": "EYEBROW",
                "headline": "Where the platform finds its voice.",
                "italic_word": "finds",
            },
        )
        # The new wrapper carries class="ip-head ck-page-title" so
        # the shell auto-inject is skipped (one h1, not two).
        self.assertIn('class="ip-head ck-page-title"', html)
        # Eyebrow + dash glyph (Tier-2 §2.1).
        self.assertIn('class="eyebrow"', html)
        self.assertIn('class="dash"', html)
        self.assertIn("EYEBROW", html)
        # Italic word still wraps the deck phrase.
        self.assertIn("<em>finds</em>", html)
        # H1 uses the page title.
        self.assertIn("<h1>Library</h1>", html)
        # Status-dot legend lives inside the head (Tier-2 §2.4).
        self.assertIn('<span class="dot live"></span>', html)

    def test_section_title_renders_when_provided(self):
        html = render_insights_page(
            action="/library",
            state={},
            facets=[_facet()],
            count=0,
            body_html="<p>x</p>",
            title="Library",
            section_title="All deals",
            section_eyebrow="DEAL CORPUS",
        )
        self.assertIn('class="ck-section-header"', html)
        self.assertIn(">All deals</h2>", html)
        self.assertIn(">DEAL CORPUS</div>", html)

    def test_section_omitted_when_no_title(self):
        html = render_insights_page(
            action="/library",
            state={},
            facets=[_facet()],
            count=0,
            body_html="<p>x</p>",
            title="Library",
        )
        self.assertNotIn('class="ck-section-header"', html)

    def test_chip_label_overrides_static(self):
        # Static override — every active value gets the same label.
        html = render_insights_page(
            action="/notes",
            state={"deal_id": "hca-001"},
            facets=[_facet(name="deal_id", title="By deal")],
            count=0,
            body_html="<p>x</p>",
            title="Notes",
            chip_label_overrides={"deal_id": "deal: hca-001"},
        )
        self.assertIn(">deal: hca-001 <span", html)

    def test_chip_label_overrides_callable(self):
        # Callable override — caller computes label from value.
        html = render_insights_page(
            action="/notes",
            state={"deal_id": "hca-001"},
            facets=[_facet(name="deal_id", title="By deal")],
            count=0,
            body_html="<p>x</p>",
            title="Notes",
            chip_label_overrides={
                "deal_id": lambda v: f"deal: {v}",
            },
        )
        self.assertIn(">deal: hca-001 <span", html)

    def test_non_facet_state_does_not_emit_chip(self):
        # sort_by is in state but not in facets — should round-trip
        # via hidden inputs and remove_hrefs but NOT surface as its
        # own chip (partner controls sort via column headers, not
        # the chip row).
        html = render_insights_page(
            action="/library",
            state={"sort_by": "moic", "topic": "ai"},
            facets=[_facet()],
            count=0,
            body_html="<p>x</p>",
            title="Library",
        )
        # Topic chip yes
        self.assertIn(">ai <span", html)
        # Chip count: exactly 1 (topic), not 2 (would mean sort_by
        # got its own chip).
        chip_block = html.split('class="ck-results-chips"')[1].split('</div>')[0]
        chip_count = chip_block.count('class="ck-chip"')
        self.assertEqual(chip_count, 1)
        # No `>moic <span` would mean sort_by isn't the chip label
        self.assertNotIn(">moic <span", chip_block)

    def test_count_label_and_count_render(self):
        html = render_insights_page(
            action="/library",
            state={},
            facets=[_facet()],
            count="1,234",
            count_label="Deals",
            body_html="<p>x</p>",
            title="Library",
        )
        self.assertIn(">1,234<", html)
        self.assertIn(">Deals</span>", html)

    def test_breadcrumbs_pass_through_to_shell(self):
        html = render_insights_page(
            action="/library",
            state={},
            facets=[_facet()],
            count=0,
            body_html="<p>x</p>",
            title="Library",
            breadcrumbs=[("Home", "/"), ("Library", None)],
        )
        self.assertIn('class="ck-breadcrumbs"', html)
        self.assertIn('href="/"', html)


if __name__ == "__main__":
    unittest.main()
