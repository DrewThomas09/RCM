"""Tests for the Bloomberg-style analyst workbench page.

Three rendering regimes must all produce a valid HTML page:
1. Fully populated packet — everything renders.
2. Minimal packet — most sections INCOMPLETE / SKIPPED; page must
   still serve without raising.
3. Empty deal — builder falls back on defaults; we still produce a
   readable page.

Plus: the slider JS must reference the real bridge POST endpoint and
use fetch() with Content-Type JSON.
"""
from __future__ import annotations

import os
import re
import tempfile
import unittest

from rcm_mc.analysis.packet import (
    ComparableHospital,
    ComparableSet,
    CompletenessAssessment,
    DealAnalysisPacket,
    DiligencePriority,
    DiligenceQuestion,
    EBITDABridgeResult,
    HospitalProfile,
    MetricImpact,
    MetricSource,
    MissingField,
    ObservedMetric,
    PercentileSet,
    PredictedMetric,
    ProfileMetric,
    ProvenanceGraph,
    DataNode,
    RiskFlag,
    RiskSeverity,
    SectionStatus,
    SimulationSummary,
)
from rcm_mc.analysis.packet_builder import build_analysis_packet
from rcm_mc.portfolio.store import PortfolioStore
from rcm_mc.ui.analysis_workbench import PALETTE, render_workbench


# ── Fixtures ─────────────────────────────────────────────────────────

def _temp_store():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    s = PortfolioStore(path)
    s.init_db()
    return s, path


def _full_packet() -> DealAnalysisPacket:
    """A packet with every section populated — exercises the full
    render path."""
    p = DealAnalysisPacket(deal_id="acme", deal_name="Acme Health")
    p.profile = HospitalProfile(
        bed_count=420, region="midwest", state="IL",
        payer_mix={"medicare": 0.40, "commercial": 0.45, "medicaid": 0.15},
    )
    p.observed_metrics = {
        "denial_rate": ObservedMetric(value=12.0, source="USER_INPUT"),
        "days_in_ar": ObservedMetric(value=55.0, source="USER_INPUT"),
    }
    p.completeness = CompletenessAssessment(
        coverage_pct=0.78, total_metrics=30, observed_count=23, grade="B",
        missing_fields=[
            MissingField(metric_key="cost_to_collect",
                          display_name="Cost to Collect",
                          category="collections",
                          ebitda_sensitivity_rank=5),
        ],
        missing_ranked_by_sensitivity=["cost_to_collect"],
    )
    p.comparables = ComparableSet(
        peers=[ComparableHospital(id=f"peer{i}", similarity_score=0.85 - 0.01 * i)
                for i in range(8)],
        features_used=["bed_count", "payer_mix"],
        weights={"bed_count": 0.25, "payer_mix": 0.25},
    )
    p.predicted_metrics = {
        "net_collection_rate": PredictedMetric(
            value=94.2, ci_low=91.8, ci_high=96.6, method="ridge_regression",
            r_squared=0.81, n_comparables_used=47, coverage_target=0.90,
        ),
    }
    p.rcm_profile = {
        "denial_rate": ProfileMetric(value=12.0, source=MetricSource.OBSERVED,
                                      quality="high"),
        "days_in_ar": ProfileMetric(value=55.0, source=MetricSource.OBSERVED,
                                     quality="high"),
        "net_collection_rate": ProfileMetric(value=94.2, source=MetricSource.PREDICTED,
                                              quality="medium"),
        "denial_rate_medicare_advantage": ProfileMetric(value=17.5,
                                                         source=MetricSource.OBSERVED),
    }
    p.ebitda_bridge = EBITDABridgeResult(
        current_ebitda=32_000_000, target_ebitda=45_000_000,
        total_ebitda_impact=13_000_000, new_ebitda_margin=0.112,
        margin_improvement_bps=320,
        per_metric_impacts=[
            MetricImpact(metric_key="denial_rate",
                          current_value=12.0, target_value=7.0,
                          ebitda_impact=9_800_000, revenue_impact=9_100_000,
                          cost_impact=-700_000, margin_impact_bps=245,
                          upstream_metrics=["denial_rate", "net_revenue"]),
            MetricImpact(metric_key="days_in_ar",
                          current_value=55.0, target_value=45.0,
                          ebitda_impact=3_200_000, revenue_impact=0,
                          cost_impact=-3_200_000,
                          working_capital_impact=11_000_000,
                          upstream_metrics=["days_in_ar", "net_revenue"]),
        ],
        waterfall_data=[("Current EBITDA", 32e6),
                        ("denial_rate", 9.8e6),
                        ("days_in_ar", 3.2e6),
                        ("Target EBITDA", 45e6)],
        ev_impact_at_multiple={"10x": 130_000_000, "12x": 156_000_000},
        status=SectionStatus.OK,
    )
    p.simulation = SimulationSummary(
        n_sims=2000, seed=42,
        ebitda_uplift=PercentileSet(p10=8e6, p25=10e6, p50=13e6, p75=16e6, p90=19e6),
        moic=PercentileSet(p10=1.4, p25=1.6, p50=1.9, p75=2.2, p90=2.5),
        irr=PercentileSet(p10=0.08, p50=0.14, p90=0.18),
        variance_contribution_by_metric={"denial_rate": 0.6, "days_in_ar": 0.4},
        convergence_check={"converged": True, "n_sims": 2000},
        status=SectionStatus.OK,
    )
    p.risk_flags = [
        RiskFlag(category="OPERATIONAL", severity=RiskSeverity.CRITICAL,
                  title="Systemic denial problem",
                  detail="Denial rate 12% is above the 10% threshold.",
                  trigger_metrics=["denial_rate"], trigger_metric="denial_rate",
                  trigger_value=12.0, ebitda_at_risk=9.8e6),
        RiskFlag(category="PAYER", severity=RiskSeverity.HIGH,
                  title="MA denial rate elevated",
                  detail="Medicare Advantage denial rate 17.5% vs industry 15.7%",
                  trigger_metric="denial_rate_medicare_advantage",
                  trigger_value=17.5),
    ]
    p.diligence_questions = [
        DiligenceQuestion(
            question="Provide the denial root-cause breakdown for the last 12 months.",
            category="OPERATIONAL", priority=DiligencePriority.P0,
            trigger="denial_rate=12.0%",
            trigger_metric="denial_rate",
            context="Denial rate is 12%; partner needs to know the mix.",
        ),
        DiligenceQuestion(
            question="Is there an EHR transition planned?",
            category="OPERATIONAL", priority=DiligencePriority.P1,
            trigger="standard",
        ),
    ]
    g = ProvenanceGraph()
    g.add(DataNode(metric="observed:denial_rate", value=12.0,
                    source="USER_INPUT", upstream=[]))
    g.add(DataNode(metric="bridge:denial_rate", value=9.8e6,
                    source="rcm_ebitda_bridge", confidence=0.8,
                    upstream=["observed:denial_rate"]))
    g.add(DataNode(metric="bridge:total", value=13e6,
                    source="rcm_ebitda_bridge", confidence=0.8,
                    upstream=["bridge:denial_rate"]))
    p.provenance = g
    return p


def _minimal_packet() -> DealAnalysisPacket:
    """A packet where most sections are INCOMPLETE or SKIPPED."""
    p = DealAnalysisPacket(deal_id="minimal", deal_name="Minimal Deal")
    p.profile = HospitalProfile(bed_count=100, region="west", state="CA")
    p.completeness = CompletenessAssessment(
        coverage_pct=0.15, total_metrics=30, observed_count=4, grade="D",
        status=SectionStatus.INCOMPLETE, reason="only 4/30 metrics observed",
    )
    p.comparables = ComparableSet(status=SectionStatus.INCOMPLETE,
                                   reason="no pool provided")
    p.ebitda_bridge = EBITDABridgeResult(
        status=SectionStatus.INCOMPLETE, reason="no revenue baseline",
    )
    p.simulation = SimulationSummary(status=SectionStatus.SKIPPED,
                                      reason="skip_simulation=True")
    return p


# ── Rendering tests ─────────────────────────────────────────────────

class TestRenderRegimes(unittest.TestCase):
    def test_full_packet_renders(self):
        html = render_workbench(_full_packet())
        self.assertIn("<!DOCTYPE html>", html)
        # Deal name in header.
        self.assertIn("Acme Health", html)
        # All six tab labels present.
        for tab in ("Overview", "RCM Profile", "EBITDA Bridge",
                     "Monte Carlo", "Risk & Diligence", "Provenance"):
            self.assertIn(tab, html)

    def test_full_packet_includes_bloomberg_palette(self):
        html = render_workbench(_full_packet())
        self.assertIn(PALETTE["bg"], html)
        self.assertIn(PALETTE["panel"], html)
        self.assertIn(PALETTE["border"], html)
        # Monospace font reference
        self.assertIn("JetBrains Mono", html)

    def test_full_packet_quotes_specific_numbers(self):
        """Bloomberg's rule: zero wasted whitespace, every number
        visible. We assert a few figures from the fixture show up."""
        html = render_workbench(_full_packet())
        # EBITDA impact hero number $13.0M
        self.assertIn("$13.0M", html)
        # A risk flag title
        self.assertIn("Systemic denial problem", html)
        # A diligence question
        self.assertIn("denial root-cause breakdown", html)

    def test_full_packet_severity_badges_present(self):
        html = render_workbench(_full_packet())
        self.assertIn("CRITICAL", html)
        self.assertIn("HIGH", html)
        self.assertIn("wb-badge-critical", html)

    def test_full_packet_emits_slider_bootstrap(self):
        html = render_workbench(_full_packet())
        # The bridge tab should emit a bootstrap JSON script tag.
        self.assertIn('id="wb-bridge-bootstrap"', html)
        # And two slider inputs (one per lever).
        sliders = re.findall(r'class="wb-slider"', html)
        self.assertEqual(len(sliders), 2)

    def test_full_packet_emits_waterfall_rows(self):
        html = render_workbench(_full_packet())
        # One row per waterfall step (4 steps → 4 wf-row divs).
        rows = re.findall(r'class="wf-row"', html)
        self.assertGreaterEqual(len(rows), 4)
        self.assertIn("Current EBITDA", html)
        self.assertIn("Target EBITDA", html)

    def test_minimal_packet_renders_without_error(self):
        html = render_workbench(_minimal_packet())
        self.assertIn("<!DOCTYPE html>", html)
        # Bridge tab should surface a "not available" empty state
        # rather than crash.
        self.assertIn("no revenue baseline", html)
        self.assertIn("skip_simulation=True", html)

    def test_empty_packet_renders(self):
        packet = DealAnalysisPacket(deal_id="empty", deal_name="")
        html = render_workbench(packet)
        self.assertIn("<!DOCTYPE html>", html)
        # Falls back to deal_id when name is blank.
        self.assertIn("empty", html)

    def test_html_is_well_formed_enough(self):
        """Sanity: matching braces on doctype / html / body / style."""
        html = render_workbench(_full_packet())
        for token, at_least in (("<html", 1), ("</html>", 1),
                                  ("<body", 1), ("</body>", 1),
                                  ("<style>", 1), ("</style>", 1),
                                  ("<script>", 1), ("</script>", 1)):
            self.assertGreaterEqual(html.count(token), at_least,
                                    f"missing {token!r}")


# ── Slider JS behavior ──────────────────────────────────────────────

class TestSliderJS(unittest.TestCase):
    def test_slider_js_posts_to_bridge_endpoint(self):
        html = render_workbench(_full_packet())
        # The JS must reference the bridge POST URL.
        self.assertIn("/api/analysis/", html)
        self.assertIn("/bridge", html)
        self.assertIn("method: 'POST'", html)
        self.assertIn("'Content-Type': 'application/json'", html)

    def test_slider_js_debounces(self):
        html = render_workbench(_full_packet())
        # setTimeout with 300ms is the debounce hook.
        self.assertIn("setTimeout", html)
        self.assertIn("300", html)

    def test_slider_js_handles_tab_switching(self):
        html = render_workbench(_full_packet())
        # Tab click listeners toggle .active on panels.
        self.assertIn("classList.toggle('active'", html)

    def test_bridge_bootstrap_payload_is_valid_json(self):
        import html as _html
        import json as _json
        page = render_workbench(_full_packet())
        # Extract the script block's inner text.
        m = re.search(
            r'<script id="wb-bridge-bootstrap"[^>]*>(.*?)</script>',
            page, re.DOTALL,
        )
        self.assertIsNotNone(m)
        raw = _html.unescape(m.group(1))
        payload = _json.loads(raw)
        self.assertEqual(payload["deal_id"], "acme")
        self.assertEqual(len(payload["assumptions"]), 2)
        # First assumption has the expected shape.
        first = payload["assumptions"][0]
        self.assertIn("metric", first)
        self.assertIn("current", first)
        self.assertIn("target", first)


# ── End-to-end via the builder ──────────────────────────────────────

class TestEndToEndBuilderRender(unittest.TestCase):
    def test_render_after_real_build(self):
        store, path = _temp_store()
        try:
            store.upsert_deal("e2e", name="E2E Health", profile={
                "bed_count": 420, "region": "midwest", "state": "IL",
                "payer_mix": {"medicare": 0.40, "commercial": 0.45, "medicaid": 0.15},
            })
            packet = build_analysis_packet(
                store, "e2e", skip_simulation=True,
                observed_override={
                    "denial_rate": ObservedMetric(value=11.0),
                    "days_in_ar": ObservedMetric(value=55.0),
                },
                target_metrics={"denial_rate": 7.0, "days_in_ar": 45.0},
                financials={
                    "gross_revenue": 1_000_000_000,
                    "net_revenue": 400_000_000,
                    "current_ebitda": 32_000_000,
                    "claims_volume": 300_000,
                },
            )
            html = render_workbench(packet)
            self.assertIn("E2E Health", html)
            self.assertIn("wb-slider", html)
            self.assertIn("EBITDA", html)
        finally:
            try:
                os.unlink(path)
            except OSError:
                pass


if __name__ == "__main__":
    unittest.main()
