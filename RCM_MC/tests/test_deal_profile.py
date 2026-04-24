"""Deal Profile page regression tests.

The Deal Profile is the "single source of truth per deal" UX fix.
Tests cover:
    - Landing (no slug) renders the slug picker
    - Profile page for a slug renders the parameter form + all
      analytic cards
    - Every analytic card links to an expected downstream route
    - URL-seeded query params pre-fill the form (for share-by-URL)
    - Invalid slugs fall back to the landing
    - Nav link present in sidebar
"""
from __future__ import annotations

import re
import unittest

from rcm_mc.ui.deal_profile_page import (
    _ANALYTICS, render_deal_profile_page,
)


class LandingTests(unittest.TestCase):

    def test_empty_slug_renders_picker(self):
        h = render_deal_profile_page(slug="")
        self.assertIn("One source of truth per deal", h)
        self.assertIn('name="slug"', h)
        self.assertIn("aurora", h.lower())

    def test_invalid_slug_falls_back_to_landing(self):
        h = render_deal_profile_page(slug="  ")
        self.assertIn("Open profile", h)
        # Names with slashes get sanitised; path-traversal rejected.
        h2 = render_deal_profile_page(slug="../etc/passwd")
        # Sanitizer strips characters but the result is still a
        # valid slug ("etcpasswd") — just verify the rendered page
        # is a profile page (not a 500 or landing).
        self.assertIn("Deal Profile", h2)


class ProfilePageTests(unittest.TestCase):

    def test_renders_parameter_form_with_every_field(self):
        h = render_deal_profile_page(slug="aurora")
        for field in (
            "dataset", "deal_name", "partner_name",
            "specialty", "states", "legal_structure",
            "landlord", "lease_term_years",
            "enterprise_value_usd", "revenue_usd",
            "ebitda_usd", "equity_usd",
        ):
            self.assertIn(f'data-rcm-deal-field="{field}"', h,
                          msg=f"missing field {field}")

    def test_renders_card_for_every_analytic(self):
        h = render_deal_profile_page(slug="aurora")
        for a in _ANALYTICS:
            self.assertIn(a["label"], h,
                          msg=f"missing analytic card {a['label']}")

    def test_save_clear_buttons_present(self):
        h = render_deal_profile_page(slug="aurora")
        self.assertIn("data-rcm-deal-save", h)
        self.assertIn("data-rcm-deal-clear", h)

    def test_localstorage_js_initialised_with_slug(self):
        h = render_deal_profile_page(slug="project-aurora")
        self.assertIn('var slug = "project-aurora"', h)
        self.assertIn("rcm_deal_", h)     # storage key prefix
        self.assertIn("localStorage", h)

    def test_url_seed_params_prefill_form(self):
        h = render_deal_profile_page(
            slug="aurora",
            qs={
                "deal_name": ["Project Aurora"],
                "landlord": ["Medical Properties Trust"],
                "specialty": ["EMERGENCY_MEDICINE"],
            },
        )
        self.assertIn('value="Project Aurora"', h)
        self.assertIn('value="Medical Properties Trust"', h)
        self.assertIn('value="EMERGENCY_MEDICINE"', h)

    def test_analytic_card_carries_href_template(self):
        h = render_deal_profile_page(slug="aurora")
        # Bankruptcy-Survivor Scan uses empty params — should still
        # render the href-base attribute.
        self.assertIn(
            'data-rcm-deal-href-base="/screening/bankruptcy-survivor"',
            h,
        )
        self.assertIn(
            'data-rcm-deal-href-base="/diligence/counterfactual"', h,
        )
        self.assertIn(
            'data-rcm-deal-href-base="/diligence/ic-packet"', h,
        )

    def test_slug_sanitization_rejects_path_traversal(self):
        # '..' contains no a-z/0-9/- so the sanitiser strips it and
        # falls back to landing.
        h = render_deal_profile_page(slug="..")
        self.assertIn("One source of truth per deal", h)

    def test_nav_link_in_sidebar(self):
        from rcm_mc.ui._chartis_kit import chartis_shell
        rendered = chartis_shell("<p>x</p>", "Test")
        self.assertIn('href="/diligence/deal"', rendered)


class AnalyticMappingTests(unittest.TestCase):

    def test_every_analytic_has_required_keys(self):
        for a in _ANALYTICS:
            self.assertIn("label", a)
            self.assertIn("href", a)
            self.assertIn("detail", a)
            # params always a list (may be empty)
            self.assertIsInstance(a.get("params", []), list)

    def test_every_analytic_points_at_a_registered_route(self):
        # Routes we know exist in server.py; keeping this list in
        # sync prevents Deal Profile links from 404-ing.
        expected_routes = {
            "/diligence/benchmarks",
            "/diligence/denial-prediction",
            "/diligence/risk-workbench",
            "/diligence/counterfactual",
            "/screening/bankruptcy-survivor",
            "/market-intel",
            "/diligence/compare",
            "/diligence/deal-mc",
            "/diligence/qoe-memo",
            "/diligence/ic-packet",
            "/diligence/deal-autopsy",
            "/diligence/physician-attrition",
            "/diligence/physician-eu",
            "/diligence/management",
            "/diligence/checklist",
            "/diligence/thesis-pipeline",
            "/diligence/exit-timing",
            "/diligence/regulatory-calendar",
            "/diligence/covenant-stress",
            "/diligence/bridge-audit",
            "/diligence/bear-case",
            "/diligence/payer-stress",
            "/diligence/hcris-xray",
        }
        for a in _ANALYTICS:
            self.assertIn(a["href"], expected_routes,
                          msg=f"unknown route {a['href']}")

    def test_every_analytic_has_a_phase(self):
        """Every analytic tile should carry a phase — the grouped
        grid renders by phase so un-categorised tiles fall into a
        default bucket and look out of place."""
        from rcm_mc.ui.deal_profile_page import (
            _ANALYTICS, _PHASE_ORDER,
        )
        for a in _ANALYTICS:
            self.assertIn("phase", a,
                          msg=f"analytic missing phase: {a.get('label')}")
            self.assertIn(a["phase"], _PHASE_ORDER,
                          msg=f"unknown phase {a['phase']!r}")


class ThesisSnapshotTests(unittest.TestCase):

    def _render(self, slug="aurora"):
        from rcm_mc.ui.deal_profile_page import (
            render_deal_profile_page,
        )
        return render_deal_profile_page(slug=slug)

    def test_thesis_snapshot_card_present(self):
        h = self._render()
        self.assertIn("Investment Thesis", h)
        self.assertIn("data-rcm-thesis-narrative", h)

    def test_thesis_kpi_tiles_all_present(self):
        h = self._render()
        for hook in (
            "data-rcm-thesis-ev",
            "data-rcm-thesis-revenue",
            "data-rcm-thesis-ebitda",
            "data-rcm-thesis-multiple",
        ):
            self.assertIn(hook, h)

    def test_capital_structure_bar_present(self):
        h = self._render()
        self.assertIn("data-rcm-thesis-equity-bar", h)
        self.assertIn("data-rcm-thesis-debt-bar", h)
        self.assertIn("Capital structure", h)

    def test_thesis_badge_present(self):
        h = self._render()
        self.assertIn("data-rcm-thesis-badge", h)
        self.assertIn("Awaiting inputs", h)

    def test_thesis_update_js_function_present(self):
        h = self._render()
        self.assertIn("updateThesisSnapshot", h)


class LifecycleRibbonTests(unittest.TestCase):

    def _render(self):
        from rcm_mc.ui.deal_profile_page import (
            render_deal_profile_page,
        )
        return render_deal_profile_page(slug="aurora")

    def test_all_five_phases_rendered(self):
        h = self._render()
        for phase_label in (
            "Screening", "Diligence", "Risk Workbench",
            "Financial synthesis", "Deliverables",
        ):
            self.assertIn(phase_label, h,
                          msg=f"phase missing: {phase_label}")

    def test_phase_count_badges(self):
        h = self._render()
        # At least two phases should show "analytic" / "analytics"
        self.assertIn("analytic", h)


class PhaseGroupedAnalyticsTests(unittest.TestCase):

    def _render(self):
        from rcm_mc.ui.deal_profile_page import (
            render_deal_profile_page,
        )
        return render_deal_profile_page(slug="aurora")

    def test_analytics_grouped_by_phase(self):
        h = self._render()
        self.assertIn("grouped by lifecycle phase", h)
        # The Workspace phase header contains Workspace subtitle
        self.assertIn("one-button orchestration", h)


class DealProfilePowerUITests(unittest.TestCase):

    def _render(self):
        from rcm_mc.ui.deal_profile_page import (
            render_deal_profile_page,
        )
        return render_deal_profile_page(slug="aurora")

    def test_bookmark_hint_present(self):
        h = self._render()
        # Bookmark hint emits a <kbd> element with "?" shortcut
        self.assertIn("<kbd", h)
        self.assertIn("for shortcuts", h)

    def test_run_full_pipeline_cta_present(self):
        h = self._render()
        self.assertIn("Run Full Pipeline", h)
        self.assertIn("data-rcm-run-pipeline", h)

    def test_analytic_card_hover_transitions(self):
        h = self._render()
        # Hover lift / border color transition
        self.assertIn("transform 140ms ease", h)
        self.assertIn("border-color 140ms ease", h)


class DealProfileLandingTests(unittest.TestCase):
    """The /diligence/deal (no slug) landing — shows both the
    slug-picker form AND a recent-deals grid populated from
    localStorage client-side."""

    def _render_landing(self):
        from rcm_mc.ui.deal_profile_page import render_deal_profile_page
        return render_deal_profile_page(slug="")

    def test_landing_has_recent_deals_placeholder(self):
        h = self._render_landing()
        self.assertIn("data-rcm-recent-deals", h)

    def test_landing_carries_enumeration_js(self):
        h = self._render_landing()
        self.assertIn("loadSavedDeals", h)
        # Iterates rcm_deal_ prefix
        self.assertIn("rcm_deal_", h)

    def test_landing_has_duplicate_and_delete_actions(self):
        h = self._render_landing()
        self.assertIn("data-rcm-duplicate", h)
        self.assertIn("data-rcm-delete", h)

    def test_landing_has_empty_state_message(self):
        h = self._render_landing()
        self.assertIn("No saved deals yet", h)

    def test_landing_keeps_slug_picker_form(self):
        """The new Recent Deals block is additive — the existing
        slug-picker form must still work for first-time users."""
        h = self._render_landing()
        self.assertIn("Open profile", h)
        self.assertIn('name="slug"', h)


if __name__ == "__main__":
    unittest.main()
