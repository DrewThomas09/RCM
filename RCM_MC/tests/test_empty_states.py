"""Tests for the empty-state component library."""
from __future__ import annotations

import unittest


class TestEmptyState(unittest.TestCase):
    def test_basic_render(self):
        from rcm_mc.ui.empty_states import empty_state
        html = empty_state(
            "No deals", "Add a deal to get started.")
        self.assertIn("No deals", html)
        self.assertIn("Add a deal to get started", html)
        # Has the icon (default ○)
        self.assertIn("○", html)
        # Has the role for accessibility
        self.assertIn('role="status"', html)
        # CSS injected
        self.assertIn("<style>", html)

    def test_with_primary_action(self):
        from rcm_mc.ui.empty_states import (
            empty_state, EmptyAction,
        )
        html = empty_state(
            "No data", "Load some.",
            actions=[
                EmptyAction("Refresh", "/data/refresh"),
            ])
        self.assertIn('href="/data/refresh"', html)
        self.assertIn("Refresh", html)
        self.assertIn("es-btn-primary", html)

    def test_with_multiple_actions(self):
        from rcm_mc.ui.empty_states import (
            empty_state, EmptyAction,
        )
        html = empty_state(
            "No data", "Load some.",
            actions=[
                EmptyAction("Primary", "/p", primary=True),
                EmptyAction("Secondary", "/s",
                            primary=False),
            ])
        self.assertIn("es-btn-primary", html)
        self.assertIn("es-btn-secondary", html)

    def test_html_escape(self):
        from rcm_mc.ui.empty_states import empty_state
        html = empty_state(
            "<script>x</script>",
            "Bad <input> in <description>.")
        self.assertNotIn("<script>x", html)
        self.assertIn("&lt;script&gt;", html)
        self.assertIn("&lt;input&gt;", html)

    def test_inject_css_disabled(self):
        from rcm_mc.ui.empty_states import empty_state
        html = empty_state("X", "Y", inject_css=False)
        self.assertNotIn("<style>", html)
        # But the structure is there
        self.assertIn("es-card", html)

    def test_custom_icon(self):
        from rcm_mc.ui.empty_states import empty_state
        html = empty_state("X", "Y", icon="⌕")
        self.assertIn("⌕", html)


class TestEmptyInline(unittest.TestCase):
    def test_basic(self):
        from rcm_mc.ui.empty_states import empty_inline
        html = empty_inline("No items.")
        self.assertIn("No items", html)
        self.assertIn("es-inline", html)

    def test_with_action(self):
        from rcm_mc.ui.empty_states import empty_inline
        html = empty_inline(
            "No data.",
            action_label="Load",
            action_url="/data/refresh")
        self.assertIn('href="/data/refresh"', html)
        self.assertIn("Load", html)

    def test_html_escape(self):
        from rcm_mc.ui.empty_states import empty_inline
        html = empty_inline("<script>")
        self.assertNotIn("<script>x", html)
        self.assertIn("&lt;script&gt;", html)


class TestEmptyTableRow(unittest.TestCase):
    def test_renders_colspan(self):
        from rcm_mc.ui.empty_states import (
            empty_table_row,
        )
        html = empty_table_row(
            n_columns=5, message="No rows.")
        self.assertIn('colspan="5"', html)
        self.assertIn("No rows", html)

    def test_with_action_link(self):
        from rcm_mc.ui.empty_states import (
            empty_table_row,
        )
        html = empty_table_row(
            n_columns=3,
            message="No rows.",
            action_label="Load",
            action_url="/data/refresh")
        self.assertIn('href="/data/refresh"', html)


class TestPreBuiltVariants(unittest.TestCase):
    def test_no_data_loaded(self):
        from rcm_mc.ui.empty_states import no_data_loaded
        html = no_data_loaded()
        self.assertIn("No data loaded", html)
        self.assertIn("/data/refresh", html)
        # Two actions: refresh + catalog
        self.assertIn("/data/catalog", html)

    def test_no_packets_built_generic(self):
        from rcm_mc.ui.empty_states import (
            no_packets_built,
        )
        html = no_packets_built()
        self.assertIn("No analysis packets", html)
        self.assertIn("Analysis packets bundle", html)

    def test_no_packets_built_for_deal(self):
        from rcm_mc.ui.empty_states import (
            no_packets_built,
        )
        html = no_packets_built(deal_id="aurora")
        self.assertIn("aurora", html)

    def test_no_models_trained(self):
        from rcm_mc.ui.empty_states import (
            no_models_trained,
        )
        html = no_models_trained()
        self.assertIn("No models trained", html)
        self.assertIn("/data/refresh", html)
        self.assertIn("/models/quality", html)

    def test_no_filter_results(self):
        from rcm_mc.ui.empty_states import (
            no_filter_results,
        )
        html = no_filter_results()
        self.assertIn("No matches", html)
        self.assertIn("broadening", html)

    def test_no_search_results_with_query(self):
        from rcm_mc.ui.empty_states import (
            no_search_results,
        )
        html = no_search_results(query="aurora")
        self.assertIn("aurora", html)
        self.assertIn("Try fewer words", html)

    def test_no_search_results_no_query(self):
        from rcm_mc.ui.empty_states import (
            no_search_results,
        )
        html = no_search_results()
        self.assertIn("No search results", html)

    def test_feature_disabled(self):
        from rcm_mc.ui.empty_states import (
            feature_disabled,
        )
        html = feature_disabled(
            "Live mode", env_var="RCM_MC_LIVE")
        self.assertIn("Live mode", html)
        self.assertIn("RCM_MC_LIVE", html)


if __name__ == "__main__":
    unittest.main()
