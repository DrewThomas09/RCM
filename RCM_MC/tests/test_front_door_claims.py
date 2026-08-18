"""The front door may only advertise a product that exists.

The public landing page (``/``) and the signed-in home page (``/home``)
are the two surfaces a reader meets before they can browse anything, so
they are the two most expensive places to be out of date — and in
2026-08 they were the most out of date in the codebase.

The landing page's capability grid named eight things the product does.
FIVE of them (Monte Carlo, EBITDA bridge, comparables, covenant stress,
management read) had been hidden by the visibility sweeps as
deal-execution machinery. The home page's entire first-run experience
was a "Run Pipeline" button chaining seven surfaces, every one of them
hidden — so a first-time visitor's only call to action led into the
retired product. Neither was caught, because the sweeps' own tests all
asked "does a LISTING surface offer a hidden route?" and these two pages
are marketing copy, not listings.

So this file asks the question the other way round: of everything the
front door PROMISES, does it still exist? Both halves are pinned —
routes must resolve AND be visible — because a promise pointing at a
still-serving but unlisted page is the same broken promise to a reader
who cannot find it anywhere else.

The second guard is on audience. The product reads what a
Medicare-certified provider filed, which is the same work whether you
are underwriting an acquisition, advising a system, lending against one,
or checking a claim about one. The front door used to sell it to
"healthcare deal teams" alone; these tests keep the vocabulary of a
single reader out of the two pages that set the frame.
"""
from __future__ import annotations

import re
import unittest

from rcm_mc.ui._surface_visibility import is_visible


class LandingPageClaims(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        from rcm_mc.ui.chartis.marketing_page import render_marketing_page
        cls.html = render_marketing_page()

    def test_every_advertised_capability_is_a_live_surface(self):
        # The regression that started this: five of eight capabilities
        # were hidden. Asserted against the module constant rather than
        # scraped from HTML so the grid cannot advertise one route while
        # the constant lists another.
        from rcm_mc.ui.chartis.marketing_page import CAPABILITY_ROUTES
        self.assertGreaterEqual(len(CAPABILITY_ROUTES), 6)
        dead = [r for r in CAPABILITY_ROUTES if not is_visible(r)]
        self.assertEqual(dead, [], f"landing page advertises hidden: {dead}")

    def test_capability_routes_actually_serve(self):
        # Visible is not the same as reachable. A capability the front
        # door names must answer a GET.
        from rcm_mc.server import RCMHandler
        from rcm_mc.ui.chartis.marketing_page import CAPABILITY_ROUTES
        served = set(RCMHandler._discover_all_routes(include_hidden=True))
        missing = [r for r in CAPABILITY_ROUTES if r not in served]
        self.assertEqual(missing, [], f"advertised but unrouted: {missing}")

    def test_no_link_on_the_landing_page_is_hidden(self):
        from rcm_mc.ui._surface_visibility import is_hidden
        hrefs = {h for h in re.findall(r'href="(/[^"#?]*)', self.html)}
        leaked = sorted(h for h in hrefs if is_hidden(h))
        self.assertEqual(leaked, [], f"landing page links to hidden: {leaked}")

    def test_the_retired_product_is_not_advertised(self):
        # Named because each of these was on the page while hidden.
        for claim in ("Monte Carlo", "EBITDA bridge", "Covenant stress",
                      "Management read", "Comparables"):
            self.assertNotIn(claim, self.html, f"retired claim: {claim}")

    def test_no_fabricated_figures(self):
        # The page's whole promise is that every figure traces to a
        # source, so an invented one is the worst possible copy on it.
        # These are the specific invented values it used to carry: a
        # deal funnel, a made-up target, and a made-up source inventory.
        for made_up in ("Project Meridian", "$3.2B", "$418M", "1,936",
                        "2,847", "108%", "11.4x"):
            self.assertNotIn(made_up, self.html, f"fabricated: {made_up}")

    def test_audience_is_not_narrowed_to_one_reader(self):
        low = self.html.lower()
        for narrow in ("deal team", "for partners", "your fund",
                       "portfolio company"):
            self.assertNotIn(narrow, low, f"single-audience copy: {narrow}")

    def test_it_still_says_what_it_does(self):
        # Guard against fixing the framing by emptying it: the page must
        # still name the subject, the data and the traceability claim.
        for kept in ("Medicare-certified", "cost report", "CMS"):
            self.assertIn(kept, self.html, kept)


class HomePageFirstRun(unittest.TestCase):
    """The empty-state path a first-time visitor is handed."""

    @classmethod
    def setUpClass(cls) -> None:
        from rcm_mc.ui.chartis.home_page import _try_the_tool_quickstart
        cls.html = _try_the_tool_quickstart()

    def test_first_run_ctas_point_at_live_surfaces(self):
        from rcm_mc.ui._surface_visibility import is_hidden
        hrefs = {h.split("?", 1)[0]
                 for h in re.findall(r'href="(/[^"]*)', self.html)}
        self.assertTrue(hrefs, "first-run block offered nothing at all")
        leaked = sorted(h for h in hrefs if is_hidden(h))
        self.assertEqual(leaked, [], f"first-run CTA is hidden: {leaked}")

    def test_first_run_uses_real_providers_not_fixtures(self):
        # The four fixture dataset ids are gone; real CCNs replace them.
        for fixture in ("hospital_01_clean_acute", "hospital_02_denial_heavy",
                        "hospital_07_waterfall_concordant",
                        "hospital_08_waterfall_critical"):
            self.assertNotIn(fixture, self.html, fixture)
        self.assertNotIn("Run Pipeline", self.html)

    def test_first_run_ccns_are_in_the_shipped_universe(self):
        # A deep link to a CCN that is not loaded would land on an empty
        # search form, which is exactly the dead end this replaced.
        ccns = set(re.findall(r'\?q=(\d{6})', self.html))
        self.assertGreaterEqual(len(ccns), 3)
        from rcm_mc.data.hcris import _get_latest_per_ccn
        known = set(_get_latest_per_ccn()["ccn"].astype(str))
        missing = sorted(c for c in ccns if c not in known)
        self.assertEqual(missing, [], f"CCNs not in HCRIS: {missing}")


if __name__ == "__main__":
    unittest.main()
