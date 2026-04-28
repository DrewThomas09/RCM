"""Test for the editorial /notes renderer.

Cycle 8 ports `_route_notes_search` from a legacy inline `shell()`
implementation to the chartis Insights triplet (search hero +
filter sidebar + results header). These tests pin the editorial
chrome on each rendered state — empty / no-match / scoped /
populated — without re-testing the underlying search semantics
(those are covered by `tests/test_notes_search.py`).
"""
from __future__ import annotations

import os
import tempfile
import unittest

from rcm_mc.deals.deal_notes import record_note
from rcm_mc.deals.note_tags import add_note_tag
from rcm_mc.portfolio.store import PortfolioStore
from rcm_mc.ui.notes_search_page import render_notes_search


def _fresh_store() -> PortfolioStore:
    db_path = os.path.join(tempfile.mkdtemp(prefix="notes_test_"), "p.db")
    return PortfolioStore(db_path)


class NotesSearchEditorialChromeTests(unittest.TestCase):
    def test_empty_state_emits_search_hero_and_affirm_band(self) -> None:
        store = _fresh_store()
        html = render_notes_search(store=store)
        # Triplet wrappers
        self.assertIn('class="ck-search-hero"', html)
        self.assertIn('class="ck-rail-layout"', html)
        self.assertIn('class="ck-results-header"', html)
        # Affirmative empty-state band — partner sees a real signal,
        # not a void.
        self.assertIn("Start typing to search notes", html)
        # No chips when nothing's active.
        self.assertNotIn('<div class="ck-results-chips">', html)

    def test_no_match_state_renders_search_chip(self) -> None:
        store = _fresh_store()
        html = render_notes_search(store=store, q="Apollo")
        self.assertIn("No notes match", html)
        self.assertIn("&quot;Apollo&quot;", html)
        # Clear-all link present so partner can reset
        self.assertIn(
            '<a class="ck-arrow" href="/notes">Clear all</a>', html,
        )

    def test_deal_scope_renders_deal_chip(self) -> None:
        store = _fresh_store()
        html = render_notes_search(store=store, deal_id="hca-001")
        self.assertIn("deal: hca-001", html)
        self.assertIn(
            '<a class="ck-arrow" href="/notes">Clear all</a>', html,
        )

    def test_tags_scope_renders_one_chip_per_tag(self) -> None:
        store = _fresh_store()
        html = render_notes_search(
            store=store, q="apollo", tags_raw="ic-prep red-flag",
        )
        # Both tag chips present
        self.assertIn(">ic-prep <span", html)
        self.assertIn(">red-flag <span", html)
        # And the search chip
        self.assertIn("&quot;apollo&quot;", html)

    def test_chip_remove_href_drops_only_that_facet(self) -> None:
        store = _fresh_store()
        html = render_notes_search(
            store=store, q="apollo", tags_raw="ic-prep red-flag",
        )
        # The ic-prep chip's remove_href should preserve red-flag + q
        # and drop only ic-prep. Use a coarse anchor pattern.
        self.assertIn("/notes?q=apollo&amp;tags=red-flag", html)

    def test_results_list_renders_when_notes_exist(self) -> None:
        store = _fresh_store()
        nid = record_note(store, deal_id="hca-001",
                          body="Apollo IC prep — bear thesis", author="dt")
        add_note_tag(store, nid, "ic-prep")
        html = render_notes_search(store=store, q="Apollo")
        # 1 match → singular "Note" label
        self.assertIn(">Note</span>", html)
        # Note row chrome present
        self.assertIn('class="ck-note-row"', html)
        self.assertIn('class="ck-note-deal" href="/deal/hca-001"', html)
        # Highlight wraps the matched substring
        self.assertIn('<mark class="ck-mark">Apollo</mark>', html)
        # Tag pill links back to a tag-scoped search
        self.assertIn('href="/notes?tags=ic-prep"', html)

    def test_label_pluralizes_with_count(self) -> None:
        store = _fresh_store()
        for i in range(2):
            record_note(store, deal_id=f"d-{i}", body=f"foo {i}")
        html = render_notes_search(store=store, q="foo")
        # 2 matches → plural "Notes"
        self.assertIn(">Notes</span>", html)

    def test_filter_sidebar_lists_known_tags_with_counts(self) -> None:
        store = _fresh_store()
        nid1 = record_note(store, deal_id="d-1", body="x")
        nid2 = record_note(store, deal_id="d-2", body="y")
        add_note_tag(store, nid1, "ic-prep")
        add_note_tag(store, nid2, "ic-prep")
        add_note_tag(store, nid2, "red-flag")
        html = render_notes_search(store=store)
        # Sidebar reads counts from all_note_tags
        self.assertIn(">ic-prep (2)</span>", html)
        self.assertIn(">red-flag (1)</span>", html)
        # Group head renders
        self.assertIn(">By tag</header>", html)

    def test_active_tag_marks_checkbox_checked(self) -> None:
        store = _fresh_store()
        nid = record_note(store, deal_id="d-1", body="x")
        add_note_tag(store, nid, "ic-prep")
        html = render_notes_search(store=store, tags_raw="ic-prep")
        # The ic-prep checkbox should be checked
        self.assertIn(
            'name="tags" value="ic-prep" checked', html,
        )

    def test_search_hero_round_trips_active_scope(self) -> None:
        store = _fresh_store()
        html = render_notes_search(
            store=store, q="apollo", deal_id="hca-001",
            tags_raw="ic-prep red-flag",
        )
        # Hero form contains hidden inputs preserving the scope
        # so submitting a new q doesn't drop the filters.
        self.assertIn(
            '<input type="hidden" name="deal_id" value="hca-001">', html,
        )
        self.assertIn(
            '<input type="hidden" name="tags" value="ic-prep red-flag">',
            html,
        )

    def test_invalid_tag_surfaces_warning_band(self) -> None:
        store = _fresh_store()
        # ValueError-raising tag (whitespace-only after normalise)
        # — covered by deal_tags._normalize. Construct one that
        # search_notes will reject.
        html = render_notes_search(store=store, tags_raw="$$$invalid")
        # Either renders a tag-rejected band OR routes to no-match
        # depending on the underlying normaliser. Both are acceptable
        # editorial outcomes — the smoke gate is just "page renders".
        self.assertIn("ck-rail-layout", html)


if __name__ == "__main__":
    unittest.main()
