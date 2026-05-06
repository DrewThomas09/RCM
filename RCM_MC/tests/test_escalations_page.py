"""Test the editorial /escalations renderer.

Cycle 14 ports `_route_escalations` from a legacy inline `shell()`
implementation to the chartis editorial chrome (search hero + day-
threshold filter rail + results header + ck_severity_panel +
ck_affirm_empty). These tests pin the chrome on each rendered
state — empty / no-match-at-tighter-threshold / populated.
"""
from __future__ import annotations

import os
import tempfile
import unittest

from rcm_mc.portfolio.store import PortfolioStore
from rcm_mc.ui.escalations_page import render_escalations


def _fresh_store() -> PortfolioStore:
    db = os.path.join(tempfile.mkdtemp(prefix="esc_test_"), "p.db")
    return PortfolioStore(db)


class EscalationsEditorialChromeTests(unittest.TestCase):
    def test_empty_state_renders_affirm_band(self) -> None:
        html = render_escalations(store=_fresh_store(), min_days=30)
        self.assertIn('class="ck-search-hero"', html)
        self.assertIn('class="ck-rail-layout"', html)
        self.assertIn('class="ck-results-header"', html)
        self.assertIn('class="ck-filter-rail"', html)
        self.assertIn("ck-affirm-empty", html)
        # Affirmative copy + a CTA back to /alerts so partner has a
        # next step from the empty state, not just a void.
        self.assertIn("No red alerts open", html)
        self.assertIn('href="/alerts"', html)

    def test_threshold_filter_renders_radios_for_canonical_options(self) -> None:
        html = render_escalations(store=_fresh_store(), min_days=30)
        # All canonical thresholds rendered as radio rows
        for t in (7, 14, 30, 60, 90):
            self.assertIn(f'value="{t}"', html)
            self.assertIn(f'≥ {t} days', html)
        # Default 30 is checked
        self.assertIn('value="30" checked', html)
        # Other thresholds are NOT checked
        self.assertNotIn('value="7" checked', html)
        self.assertNotIn('value="60" checked', html)

    def test_non_default_threshold_marked_checked(self) -> None:
        html = render_escalations(store=_fresh_store(), min_days=14)
        self.assertIn('value="14" checked', html)
        self.assertNotIn('value="30" checked', html)

    def test_non_default_threshold_emits_chip(self) -> None:
        html = render_escalations(store=_fresh_store(), min_days=14)
        # Active-filter chip + Clear all link to reset to default
        self.assertIn('class="ck-results-chips"', html)
        self.assertIn(
            '<a class="ck-arrow" href="/escalations">Clear all</a>', html,
        )

    def test_default_threshold_omits_chip(self) -> None:
        html = render_escalations(store=_fresh_store(), min_days=30)
        # No chips block when at the default threshold (the empty
        # state is informational, not a "remove this" filter).
        self.assertNotIn(
            '<div class="ck-results-chips">', html,
        )

    def test_csv_download_link_round_trips_min_days(self) -> None:
        html = render_escalations(store=_fresh_store(), min_days=60)
        # The CSV link should preserve the active threshold so the
        # partner downloads the same view they're looking at.
        self.assertIn(
            '/escalations?min_days=60&amp;format=csv', html,
        )

    def test_search_hero_round_trips_active_threshold(self) -> None:
        html = render_escalations(store=_fresh_store(), min_days=14)
        self.assertIn(
            '<input type="hidden" name="min_days" value="14">', html,
        )

    def test_section_eyebrow_and_title(self) -> None:
        html = render_escalations(store=_fresh_store(), min_days=30)
        self.assertIn(">ESCALATIONS</div>", html)
        self.assertIn("Red alerts open at least 30 days", html)

    def test_label_singular_when_count_is_one(self) -> None:
        # Use a high min_days against an empty DB so count is 0;
        # the label should say "Escalations" (plural) when count
        # is 0 too.
        html_zero = render_escalations(store=_fresh_store(), min_days=999)
        self.assertIn(">Escalations</span>", html_zero)


if __name__ == "__main__":
    unittest.main()
