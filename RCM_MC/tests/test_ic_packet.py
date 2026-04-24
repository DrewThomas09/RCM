"""IC Packet Assembler regression tests.

- Renderer produces a valid HTML document with every expected
  section when given a full input bundle
- Missing inputs suppress the corresponding sections rather than
  rendering blank tables / fabricated numbers
- Partner synthesis branches match the input state (RED verdict
  → "CRITICAL screen-level finding" copy; GREEN → "clean screen")
- Walkaway conditions are auto-derived from LOW-feasibility
  counterfactuals
- Route renders landing page + live packet with full metadata
"""
from __future__ import annotations

import unittest
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from rcm_mc.exports.ic_packet import (
    ICPacketMetadata, render_ic_packet_html,
)


@dataclass
class _FakeScan:
    verdict_value: str = "CRITICAL"
    critical_hits: int = 3
    patterns_hit: int = 5
    named_comparisons: List[str] = field(default_factory=list)

    @property
    def verdict(self):
        class _V:
            def __init__(self, v):
                self.value = v
        return _V(self.verdict_value)


@dataclass
class _FakeWaterfall:
    total_divergence_status: str = "CRITICAL"
    total_accrual_revenue_usd: float = 10_000_000
    total_management_revenue_usd: float = 12_000_000
    total_qor_divergence_usd: float = -2_000_000
    total_qor_divergence_pct: float = -0.166


@dataclass
class _FakeCounterfactual:
    module: str = "STEWARD"
    original_band: str = "CRITICAL"
    target_band: str = "HIGH"
    change_description: str = "Cap escalator at 3.0%"
    narrative: str = "."
    deal_structure_implication: str = "x"
    estimated_dollar_impact_usd: float = 1_000_000
    feasibility: str = "HIGH"

    def to_dict(self):
        return {
            "module": self.module,
            "change_description": self.change_description,
            "estimated_dollar_impact_usd":
                self.estimated_dollar_impact_usd,
        }


@dataclass
class _FakeCfSet:
    items: List[_FakeCounterfactual] = field(default_factory=list)
    critical_findings_addressed: int = 0
    largest_lever: Optional[_FakeCounterfactual] = None


class ICPacketRenderTests(unittest.TestCase):

    def _full_bundle(self) -> Dict[str, Any]:
        largest = _FakeCounterfactual()
        low_feas_cf = _FakeCounterfactual(
            module="ANTITRUST",
            original_band="RED", target_band="YELLOW",
            change_description="Divest Houston holdings",
            feasibility="LOW",
        )
        return dict(
            metadata=ICPacketMetadata(
                deal_name="Project Aurora",
                partner_name="Partner A",
                preparer_name="Senior Associate B",
                recommendation="PROCEED_WITH_CONDITIONS",
            ),
            bankruptcy_scan=_FakeScan(
                verdict_value="CRITICAL",
                named_comparisons=[
                    "Steward Health Care — 2016 MPT",
                    "Prospect Medical — 2019 Leonard Green",
                ],
            ),
            cash_waterfall=_FakeWaterfall(),
            counterfactuals=_FakeCfSet(
                items=[largest, low_feas_cf],
                critical_findings_addressed=2,
                largest_lever=largest,
            ),
            enterprise_value_usd=350_000_000,
            revenue_usd=200_000_000,
            ebitda_usd=30_000_000,
            projected_moic=2.5,
            projected_irr=0.22,
            peer_median_ev_ebitda=9.0,
            public_comps=[
                {"ticker": "HCA", "name": "HCA Healthcare",
                 "revenue_ttm_usd_bn": 71.2,
                 "ev_ebitda_multiple": 8.9},
            ],
            sector_sentiment="negative",
            walkaway_conditions=[
                "Antitrust: Divest Houston holdings",
            ],
            hundred_day_summary=(
                "Replace Change Healthcare BA within 180 days; "
                "migrate billing to Availity."
            ),
        )

    def test_renders_valid_html(self):
        html = render_ic_packet_html(**self._full_bundle())
        self.assertTrue(html.startswith("<!DOCTYPE html>"))
        self.assertIn("</html>", html)

    def test_full_bundle_has_all_sections(self):
        html = render_ic_packet_html(**self._full_bundle())
        for section in (
            "Investment Committee Memorandum",
            "Project Aurora",
            "Partner Synthesis",
            "Headline Numbers",
            "Bankruptcy-Survivor Scan",
            "Quality of Revenue",
            "What Would Change Our Mind",
            "Market Context",
            "100-Day Plan",
            "Walkaway Conditions",
            "Partner Sign-Off",
        ):
            self.assertIn(section, html,
                          msg=f"missing section {section!r}")

    def test_critical_verdict_triggers_critical_synthesis(self):
        html = render_ic_packet_html(**self._full_bundle())
        self.assertIn("CRITICAL screen-level finding", html)

    def test_clean_verdict_triggers_clean_synthesis(self):
        bundle = self._full_bundle()
        bundle["bankruptcy_scan"] = _FakeScan(
            verdict_value="GREEN", critical_hits=0, patterns_hit=0,
        )
        bundle["counterfactuals"] = _FakeCfSet(
            items=[], critical_findings_addressed=0, largest_lever=None,
        )
        bundle["cash_waterfall"] = _FakeWaterfall(
            total_divergence_status="IMMATERIAL",
        )
        html = render_ic_packet_html(**bundle)
        self.assertIn("clean screen", html)
        self.assertIn("No counterfactual levers", html)

    def test_minimal_bundle_still_renders(self):
        """Just metadata — no analytical modules. Every analytical
        section is suppressed; cover + sign-off render."""
        html = render_ic_packet_html(
            metadata=ICPacketMetadata(deal_name="MinimalDeal"),
        )
        self.assertTrue(html.startswith("<!DOCTYPE html>"))
        self.assertIn("MinimalDeal", html)
        # Sections that depend on inputs are suppressed.
        self.assertNotIn("Market Context", html)
        self.assertNotIn("Bankruptcy-Survivor Scan", html)
        self.assertNotIn("Quality of Revenue", html)
        # Sign-off always renders.
        self.assertIn("Partner Sign-Off", html)

    def test_print_css_present(self):
        html = render_ic_packet_html(
            metadata=ICPacketMetadata(deal_name="X"),
        )
        self.assertIn("@media print", html)
        self.assertIn("@page", html)

    def test_recommendation_banner_reflects_input(self):
        for rec, expected_cls in [
            ("PROCEED", "recommend-proceed"),
            ("PROCEED_WITH_CONDITIONS", "recommend-conditions"),
            ("DECLINE", "recommend-decline"),
        ]:
            html = render_ic_packet_html(
                metadata=ICPacketMetadata(
                    deal_name="X", recommendation=rec,
                ),
            )
            self.assertIn(expected_cls, html)


class ICPacketPageRouteTests(unittest.TestCase):

    def test_landing_renders_form(self):
        from rcm_mc.ui.ic_packet_page import render_ic_packet_page
        h = render_ic_packet_page(qs={})
        self.assertIn("IC Packet Assembler", h)
        self.assertIn("Assemble IC Packet", h)

    def test_live_render_with_metadata_works_end_to_end(self):
        from rcm_mc.ui.ic_packet_page import render_ic_packet_page
        qs = {
            "dataset": ["hospital_08_waterfall_critical"],
            "deal_name": ["Project Aurora"],
            "partner_name": ["Partner A"],
            "specialty": ["EMERGENCY_MEDICINE"],
            "states": ["OR, WA"],
            "legal_structure": ["FRIENDLY_PC_PASS_THROUGH"],
            "landlord": ["Medical Properties Trust"],
            "lease_term_years": ["20"],
            "lease_escalator_pct": ["0.035"],
            "ebitdar_coverage": ["1.2"],
            "annual_rent_usd": ["10000000"],
            "portfolio_ebitdar_usd": ["12000000"],
            "geography": ["RURAL"],
            "cbsa_codes": ["35620"],
            "market_category": ["MULTI_SITE_ACUTE_HOSPITAL"],
            "revenue_usd": ["200000000"],
            "enterprise_value_usd": ["300000000"],
            "ebitda_usd": ["30000000"],
            "projected_moic": ["2.5"],
        }
        h = render_ic_packet_page(qs=qs)
        # Cover
        self.assertIn("Project Aurora", h)
        # Partner synthesis reflects Steward-pattern input
        self.assertIn("Steward", h)
        # Market context pulled
        self.assertIn("HCA", h)
        # Counterfactual section included
        self.assertIn("What Would Change Our Mind", h)
        # Headline numbers rendered
        self.assertIn("EV / EBITDA", h)

    def test_unknown_fixture_falls_back_to_landing(self):
        from rcm_mc.ui.ic_packet_page import render_ic_packet_page
        h = render_ic_packet_page(qs={"dataset": ["not_a_fixture"]})
        self.assertIn("pick a CCD fixture", h)


class NavLinkTest(unittest.TestCase):

    def test_ic_packet_link_in_sidebar(self):
        from rcm_mc.ui._chartis_kit import chartis_shell
        rendered = chartis_shell("<p>x</p>", "Test")
        self.assertIn('href="/diligence/ic-packet"', rendered)


if __name__ == "__main__":
    unittest.main()
