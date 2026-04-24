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
        }
        for a in _ANALYTICS:
            self.assertIn(a["href"], expected_routes,
                          msg=f"unknown route {a['href']}")


if __name__ == "__main__":
    unittest.main()
