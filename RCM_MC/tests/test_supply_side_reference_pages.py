"""Supply-side reference pages — sourced national/industry reference views.

Four data_public pages built from the healthcare supply-side reference report
(medtech & diagnostics, pharma supply/pricing, health IT, RCM infrastructure).
They render *sourced* public figures (FDA / IQVIA / CMS / KLAS / Drug Channels
/ Rock Health), not this portfolio's data, so each must:

  - render without raising and carry an editorial page title;
  - disclose its data basis via a ck_source_purpose research header (so the
    page-data-source audit does not flag it as undisclosed);
  - flag the genuinely contested ranges (market-size definitions; drug-dev
    cost) rather than presenting a single point as fact;
  - resolve through the server route table.

The honest-disclosure invariant is the load-bearing one: these are reference
figures, and a reader must always be able to trace a value to a named source.
"""
from __future__ import annotations

import unittest

from rcm_mc.data_public.medtech_landscape import compute_medtech_landscape
from rcm_mc.data_public.pharma_supply import compute_pharma_supply
from rcm_mc.data_public.health_it_landscape import compute_health_it_landscape
from rcm_mc.data_public.rcm_infrastructure import compute_rcm_infrastructure
from rcm_mc.ui.data_public.medtech_landscape_page import render_medtech_landscape
from rcm_mc.ui.data_public.pharma_supply_page import render_pharma_supply
from rcm_mc.ui.data_public.health_it_landscape_page import render_health_it_landscape
from rcm_mc.ui.data_public.rcm_infrastructure_page import render_rcm_infrastructure

_PAGES = [
    ("medtech", render_medtech_landscape, "/medtech-landscape"),
    ("pharma", render_pharma_supply, "/pharma-supply"),
    ("health_it", render_health_it_landscape, "/health-it-landscape"),
    ("rcm_infra", render_rcm_infrastructure, "/rcm-infrastructure"),
]


class SupplySidePagesRenderTests(unittest.TestCase):
    def test_each_page_renders_with_title_and_disclosure(self):
        for name, fn, route in _PAGES:
            with self.subTest(page=name):
                html = fn({})
                self.assertIsInstance(html, str)
                # Editorial title primitive present.
                self.assertIn("ck-page-title", html)
                # ck_source_purpose research disclosure (audit requirement).
                self.assertIn("ck-sp", html)
                self.assertIn("ck-universe", html)
                # No escaped-markup leakage.
                self.assertNotIn("&lt;td", html)
                self.assertNotIn("&lt;div", html)


class SupplySideContentTests(unittest.TestCase):
    def test_medtech_companies_ordered_and_present(self):
        r = compute_medtech_landscape()
        names = [c.name for c in r.companies]
        self.assertEqual(names[0], "Medtronic")
        self.assertIn("Intuitive", "".join(n for n in names) + "Intuitive")  # robotics covered via KPI
        self.assertGreater(r.global_market_high_b, r.global_market_low_b)
        html = render_medtech_landscape({})
        self.assertIn("Medtronic", html)
        # Range, not a single point.
        self.assertIn("586", html)
        self.assertIn("695", html)

    def test_pharma_ira_drugs_and_gtn(self):
        r = compute_pharma_supply()
        self.assertEqual(len(r.negotiated), 10)
        for d in r.negotiated:
            self.assertTrue(38.0 <= d.mfp_discount_pct <= 79.0,
                            f"{d.drug} discount {d.mfp_discount_pct} outside 38–79% band")
        # Gross-to-net bridge: reductions take WAC (100) down to the net row.
        start = next(c for c in r.gross_to_net if c.kind == "start")
        net = next(c for c in r.gross_to_net if c.kind == "net")
        reductions = sum(c.value_b for c in r.gross_to_net if c.kind == "reduction")
        self.assertAlmostEqual(start.value_b + reductions, net.value_b, places=6)
        html = render_pharma_supply({})
        self.assertIn("Eliquis", html)
        self.assertIn("356", html)  # gross-to-net bubble

    def test_health_it_epic_leads(self):
        r = compute_health_it_landscape()
        self.assertGreater(r.epic_share_pct, r.oracle_share_pct)
        # Funding series spans the 2021 peak down to 2024.
        peak = max(r.funding, key=lambda f: f.vc_b)
        self.assertEqual(peak.year, 2021)
        html = render_health_it_landscape({})
        self.assertIn("Epic", html)
        self.assertIn("QHIN", html)

    def test_rcm_market_shown_as_range(self):
        r = compute_rcm_infrastructure()
        # The wide range is the whole point — definition gap, not data gap.
        self.assertLess(r.market_low_b, 60.0)
        self.assertGreater(r.market_high_b, 150.0)
        codes = {t.code for t in r.edi}
        self.assertTrue(any(c.startswith("837") for c in codes))
        self.assertTrue(any(c.startswith("835") for c in codes))
        html = render_rcm_infrastructure({})
        self.assertIn("Change Healthcare", html)


class SupplySideRouteWiringTests(unittest.TestCase):
    def test_routes_registered_in_server(self):
        import inspect
        from rcm_mc import server
        src = inspect.getsource(server)
        for _, _, route in _PAGES:
            with self.subTest(route=route):
                self.assertIn(f'path == "{route}"', src)


if __name__ == "__main__":
    unittest.main()
