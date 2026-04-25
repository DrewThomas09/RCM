"""Tests for the new client-side table filter on sortable_table().

The filter is opt-in via ``filterable=True``. Each test asserts a
specific contract — what the rendered HTML looks like and what the
inline JS exposes — without booting a browser.
"""
from __future__ import annotations

import unittest

from rcm_mc.ui._web_components import (
    sortable_table,
    sortable_table_js,
    web_styles,
)


class TestFilterableSortableTable(unittest.TestCase):
    def test_filter_input_emitted_when_filterable(self):
        html = sortable_table(
            ["A", "B"], [["x", "y"]],
            id="t1", filterable=True,
        )
        self.assertIn('class="wc-filter"', html)
        self.assertIn('type="search"', html)
        self.assertIn('data-filter-for="t1"', html)
        self.assertIn('placeholder="Filter…"', html)

    def test_custom_placeholder_threads_through(self):
        html = sortable_table(
            ["A"], [["x"]], id="t2",
            filterable=True, filter_placeholder="Find a deal",
        )
        self.assertIn('placeholder="Find a deal"', html)

    def test_filterable_off_by_default(self):
        html = sortable_table(["A"], [["x"]], id="t3")
        self.assertNotIn('wc-filter', html)
        self.assertNotIn('type="search"', html)

    def test_filterable_without_id_generates_one(self):
        # When filterable=True and no id provided, the helper still has
        # to bind the input to a table — it generates a stable id and
        # uses it on both the input and the table.
        html = sortable_table(["A"], [["x"]], filterable=True)
        self.assertIn('class="wc-filter"', html)
        # Same identifier on both sides
        import re
        target = re.search(r'data-filter-for="([^"]+)"', html).group(1)
        self.assertIn(f'id="{target}"', html)

    def test_filter_css_classes_in_styles(self):
        styles = web_styles()
        self.assertIn(".wc-filter", styles)
        self.assertIn(".wc-filter-hide", styles)

    def test_filter_js_wires_inputs(self):
        js = sortable_table_js()
        # Wires the input → table binding via data-filter-for
        self.assertIn("input.wc-filter", js)
        self.assertIn("data-filter-for", js)
        # Toggles the row-hide class
        self.assertIn("wc-filter-hide", js)
        # Case-insensitive substring match
        self.assertIn("toLowerCase", js)

    def test_html_escape_on_user_supplied_placeholder(self):
        # XSS prevention — the placeholder is caller-controlled in
        # principle, so the value gets html.escape()'d.
        html = sortable_table(
            ["A"], [["x"]], id="t4",
            filterable=True,
            filter_placeholder='" onfocus="alert(1)',
        )
        self.assertNotIn('" onfocus="alert(1)"', html)
        self.assertIn("&quot;", html)


class TestDashboardWiresFilter(unittest.TestCase):
    """The two dashboard tables that opt into filterable=True must
    actually emit the filter input — guards against future refactors
    silently dropping the wiring."""

    def setUp(self):
        import os, tempfile
        self.tmp = tempfile.TemporaryDirectory()
        self.db = os.path.join(self.tmp.name, "t.db")
        from rcm_mc.portfolio.store import PortfolioStore
        PortfolioStore(self.db)

    def tearDown(self):
        self.tmp.cleanup()

    def test_what_you_can_run_has_filter_input(self):
        from rcm_mc.ui.dashboard_page import render_dashboard
        html = render_dashboard(self.db)
        self.assertIn('data-filter-for="dashboard-analyses"', html)
        self.assertIn("Filter analyses", html)

    def test_daily_workflow_has_filter_input(self):
        from rcm_mc.ui.dashboard_page import render_dashboard
        html = render_dashboard(self.db)
        self.assertIn('data-filter-for="dashboard-workflow"', html)
        self.assertIn("Filter workflow", html)

    def test_data_refresh_has_filter_input(self):
        from rcm_mc.ui.data_refresh_page import render_data_refresh_page
        html = render_data_refresh_page(self.db)
        self.assertIn('data-filter-for="data-sources"', html)
        self.assertIn("Filter sources", html)

    def test_exports_page_tables_have_filters(self):
        from rcm_mc.ui.exports_index_page import render_exports_index
        html = render_exports_index(self.db)
        # All three tables on /exports — per-deal format guide,
        # portfolio-scope, corpus browsers — should now be filterable
        for tbl_id in (
            "exports-format-guide",
            "exports-portfolio",
            "exports-corpus",
        ):
            self.assertIn(f'data-filter-for="{tbl_id}"', html)


class TestRowCounter(unittest.TestCase):
    """Every sortable_table now ships a row counter footer.

    Non-filterable tables show a static "N rows". Filterable
    tables get the same starting text but the JS swaps it for
    "showing K of N rows" when the user types in the filter."""

    def test_static_counter_present_on_simple_table(self):
        html = sortable_table(["A", "B"],
                              [["x", "y"], ["p", "q"]],
                              id="static-tbl")
        self.assertIn('wc-table-counter', html)
        self.assertIn('data-total="2"', html)
        self.assertIn("2 rows", html)

    def test_singular_row(self):
        html = sortable_table(["A"], [["x"]], id="single-tbl")
        self.assertIn("1 row", html)
        self.assertNotIn("1 rows", html)

    def test_filterable_table_includes_counter(self):
        html = sortable_table(
            ["A"], [["x"], ["y"], ["z"]],
            id="ft", filterable=True,
        )
        self.assertIn('wc-table-counter', html)
        self.assertIn('data-counter-for="ft"', html)
        self.assertIn("3 rows", html)

    def test_js_updates_counter_on_filter(self):
        """The shared sortable_table_js wires `data-counter-for`
        bindings to update the counter as the filter narrows the
        visible set. Verify the JS code path exists."""
        js = sortable_table_js()
        self.assertIn("wc-table-counter", js)
        self.assertIn("showing", js.lower())
        self.assertIn("data-total", js)
        self.assertIn("no matches", js)


class TestSectionCardSemantic(unittest.TestCase):
    """section_card titles must render as <h2> — partner-facing
    accessibility (screen readers, document-outline tools, PDF
    print) was broken when the title was a styled <span>."""

    def test_title_is_h2_element(self):
        from rcm_mc.ui._web_components import section_card
        html = section_card("Risk overview", "<p>body</p>")
        self.assertIn("<h2", html)
        self.assertIn("Risk overview</h2>", html)

    def test_title_html_escaped(self):
        from rcm_mc.ui._web_components import section_card
        html = section_card("<script>x</script>", "body")
        self.assertNotIn("<script>x</script>", html)
        self.assertIn("&lt;script&gt;", html)

    def test_actions_still_render_alongside(self):
        from rcm_mc.ui._web_components import section_card
        html = section_card("X", "body", actions_html="<button>Y</button>")
        self.assertIn("<button>Y</button>", html)


class TestKeyboardShortcuts(unittest.TestCase):
    def test_slash_key_shortcut_wired(self):
        # The SaaS-standard "/" key focuses the first filter input
        # on the page. Verify the JS listens for it and skips the
        # event when the user is already typing.
        js = sortable_table_js()
        # The JS does an early-return on `e.key !== '/'` rather than
        # the positive form, so check for the actual literal that ships.
        self.assertIn("e.key !== '/'", js)
        self.assertIn("first.focus()", js)
        # Modifier keys must NOT trigger (Ctrl-/, Cmd-/ should pass through)
        self.assertIn("metaKey", js)
        self.assertIn("ctrlKey", js)
        # Skip if already in an input/textarea/contenteditable
        self.assertIn("input", js.lower())
        self.assertIn("textarea", js.lower())
        self.assertIn("isContentEditable", js)

    def test_escape_clears_and_blurs(self):
        js = sortable_table_js()
        self.assertIn("Escape", js)
        self.assertIn("input.blur()", js)


if __name__ == "__main__":
    unittest.main()
