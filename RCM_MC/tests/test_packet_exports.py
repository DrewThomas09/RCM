"""Tests for the packet-driven export renderer.

Every export format must:
- Render from the packet alone (no hidden store reads).
- Include the audit footer (run_id, input hash, observed/predicted counts).
- Not crash on minimal packets.

Also: the ``generated_exports`` audit table records every export call.
"""
from __future__ import annotations

import csv
import json
import os
import re
import tempfile
import unittest
from pathlib import Path

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
    PACKET_SCHEMA_VERSION,
    PercentileSet,
    PredictedMetric,
    ProfileMetric,
    RiskFlag,
    RiskSeverity,
    SectionStatus,
    SimulationSummary,
)
from rcm_mc.exports import PacketRenderer, list_exports, record_export
from rcm_mc.exports.export_store import _ensure_table
from rcm_mc.portfolio.store import PortfolioStore


# ── Fixtures ─────────────────────────────────────────────────────────

def _full_packet(run_id: str = "r-full") -> DealAnalysisPacket:
    p = DealAnalysisPacket(deal_id="acme", deal_name="Acme Health", run_id=run_id)
    p.profile = HospitalProfile(
        bed_count=420, region="midwest", state="IL",
        payer_mix={"medicare": 0.4, "commercial": 0.45, "medicaid": 0.15},
    )
    p.observed_metrics = {
        "denial_rate": ObservedMetric(value=12.0, source="USER_INPUT"),
        "days_in_ar": ObservedMetric(value=55.0, source="USER_INPUT"),
    }
    p.completeness = CompletenessAssessment(
        coverage_pct=0.78, total_metrics=30, observed_count=23, grade="B",
        missing_fields=[
            MissingField(metric_key="cost_to_collect",
                          display_name="Cost to Collect", category="collections",
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
            value=94.2, ci_low=91.8, ci_high=96.6,
            method="ridge_regression", r_squared=0.81,
            n_comparables_used=47, coverage_target=0.90,
        ),
    }
    p.rcm_profile = {
        "denial_rate": ProfileMetric(value=12.0, source=MetricSource.OBSERVED, quality="high"),
        "days_in_ar": ProfileMetric(value=55.0, source=MetricSource.OBSERVED, quality="high"),
        "net_collection_rate": ProfileMetric(value=94.2, source=MetricSource.PREDICTED),
    }
    p.ebitda_bridge = EBITDABridgeResult(
        current_ebitda=32_000_000, target_ebitda=45_000_000,
        total_ebitda_impact=13_000_000, new_ebitda_margin=0.112,
        margin_improvement_bps=320,
        per_metric_impacts=[
            MetricImpact(
                metric_key="denial_rate", current_value=12.0, target_value=7.0,
                revenue_impact=9_100_000, cost_impact=-700_000,
                ebitda_impact=9_800_000, margin_impact_bps=245,
                upstream_metrics=["denial_rate"],
            ),
            MetricImpact(
                metric_key="days_in_ar", current_value=55.0, target_value=45.0,
                revenue_impact=0, cost_impact=-3_200_000,
                ebitda_impact=3_200_000, working_capital_impact=11_000_000,
                upstream_metrics=["days_in_ar"],
            ),
        ],
        ev_impact_at_multiple={"10x": 130_000_000, "12x": 156_000_000},
        status=SectionStatus.OK,
    )
    p.simulation = SimulationSummary(
        n_sims=2000, seed=42,
        ebitda_uplift=PercentileSet(p10=8e6, p25=10e6, p50=13e6, p75=16e6, p90=19e6),
        moic=PercentileSet(p10=1.4, p50=1.9, p90=2.5),
        irr=PercentileSet(p10=0.08, p50=0.14, p90=0.18),
        variance_contribution_by_metric={"denial_rate": 0.6, "days_in_ar": 0.4},
        status=SectionStatus.OK,
    )
    p.risk_flags = [
        RiskFlag(category="OPERATIONAL", severity=RiskSeverity.CRITICAL,
                  title="Systemic denial problem",
                  detail="Denial rate 12% above threshold.",
                  trigger_metrics=["denial_rate"], trigger_metric="denial_rate",
                  trigger_value=12.0, ebitda_at_risk=9_800_000.0),
        RiskFlag(category="PAYER", severity=RiskSeverity.HIGH,
                  title="MA denial rate elevated",
                  detail="MA denial rate 17.5%",
                  trigger_metric="denial_rate_medicare_advantage",
                  trigger_value=17.5),
    ]
    p.diligence_questions = [
        DiligenceQuestion(
            question="Provide denial root-cause breakdown for 12 months.",
            category="OPERATIONAL", priority=DiligencePriority.P0,
            trigger="denial_rate=12.0%",
            trigger_metric="denial_rate",
            context="Denial rate 12% is material.",
        ),
        DiligenceQuestion(
            question="Are any payer contract renegotiations pending?",
            category="PAYER", priority=DiligencePriority.P1,
            trigger="standard",
        ),
    ]
    return p


def _minimal_packet() -> DealAnalysisPacket:
    p = DealAnalysisPacket(deal_id="min", deal_name="Minimal", run_id="r-min")
    p.completeness = CompletenessAssessment(
        coverage_pct=0.15, total_metrics=30, observed_count=4, grade="D",
        status=SectionStatus.INCOMPLETE,
    )
    p.ebitda_bridge = EBITDABridgeResult(
        status=SectionStatus.INCOMPLETE, reason="no revenue baseline",
    )
    p.simulation = SimulationSummary(status=SectionStatus.SKIPPED)
    return p


def _temp_store():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    s = PortfolioStore(path)
    s.init_db()
    return s, path


# ── HTML diligence memo ─────────────────────────────────────────────

class TestHTMLMemo(unittest.TestCase):
    def test_memo_contains_all_eight_sections(self):
        r = PacketRenderer()
        html = r.render_diligence_memo_html(_full_packet(), inputs_hash="abc")
        for n in ("1. Executive Summary",
                   "2. Data Completeness",
                   "3. RCM Performance",
                   "4. EBITDA Value Creation",
                   "5. Risk Assessment",
                   "6. Monte Carlo Returns",
                   "7. Key Diligence Questions",
                   "8. Comparable Set"):
            self.assertIn(n, html, f"missing section: {n}")

    def test_memo_audit_footer_has_packet_hash_and_run_id(self):
        r = PacketRenderer()
        html = r.render_diligence_memo_html(_full_packet("run-123"), inputs_hash="deadbeef")
        self.assertIn("run-123", html)
        self.assertIn("deadbeef", html)
        self.assertIn("2 observed", html)    # 2 observed metrics
        self.assertIn("1 predicted", html)   # 1 predicted metric
        self.assertIn(f"v1.0", html)          # product version

    def test_memo_quotes_specific_dollar_numbers(self):
        r = PacketRenderer()
        html = r.render_diligence_memo_html(_full_packet())
        self.assertIn("$13.0M", html)         # total_ebitda_impact
        self.assertIn("Systemic denial problem", html)

    def test_memo_on_minimal_packet_does_not_crash(self):
        r = PacketRenderer()
        html = r.render_diligence_memo_html(_minimal_packet())
        self.assertIn("Bridge unavailable", html)
        self.assertIn("Simulation not run", html)


# ── PPTX ────────────────────────────────────────────────────────────

class TestPPTX(unittest.TestCase):
    def test_pptx_fallback_has_eight_slides(self):
        """Prompt 22 replaced the ``.pptx.txt`` sibling with a real
        hand-built OOXML .pptx. Assert against the zip structure now:
        8 slide parts + embedded footer text inside slide8.xml."""
        import zipfile as _zip
        r = PacketRenderer()
        path = r.render_diligence_memo_pptx(_full_packet(), inputs_hash="xx")
        self.assertTrue(path.exists())
        self.assertEqual(path.suffix, ".pptx")
        with _zip.ZipFile(path) as z:
            names = z.namelist()
            slide_parts = [
                n for n in names
                if n.startswith("ppt/slides/slide") and n.endswith(".xml")
            ]
            self.assertEqual(len(slide_parts), 8)
            final_slide = z.read("ppt/slides/slide8.xml").decode("utf-8")
        # Footer text lives on the final slide.
        self.assertIn("RCM-MC v", final_slide)
        self.assertIn("Analysis Packet ID:", final_slide)

    def test_pptx_bridge_slide_quotes_lever_impacts(self):
        """Slide 4 (EBITDA Value Creation) should carry the bridge
        narrative text — denial_rate name + dollar impact."""
        import zipfile as _zip
        r = PacketRenderer()
        path = r.render_diligence_memo_pptx(_full_packet())
        with _zip.ZipFile(path) as z:
            bridge_slide = z.read("ppt/slides/slide4.xml").decode("utf-8")
        self.assertIn("denial_rate", bridge_slide)
        self.assertIn("$9.8M", bridge_slide)


# ── JSON ────────────────────────────────────────────────────────────

class TestJSON(unittest.TestCase):
    def test_json_is_valid_and_roundtrips(self):
        r = PacketRenderer()
        p = _full_packet()
        out = r.render_packet_json(p)
        parsed = json.loads(out)
        self.assertEqual(parsed["deal_id"], "acme")
        # Round-trip through from_dict returns an equivalent packet.
        from_dict = DealAnalysisPacket.from_dict(parsed)
        self.assertEqual(from_dict.deal_id, p.deal_id)
        self.assertEqual(len(from_dict.risk_flags), len(p.risk_flags))


# ── Raw CSV ─────────────────────────────────────────────────────────

class TestRawCSV(unittest.TestCase):
    def test_csv_columns_match_spec(self):
        r = PacketRenderer()
        path = r.render_raw_data_csv(_full_packet(), inputs_hash="h")
        with open(path, newline="", encoding="utf-8") as fh:
            rows = list(csv.reader(fh))
        header = rows[0]
        for col in ("metric_key", "display_name", "current_value", "source",
                     "benchmark_p50", "predicted_value", "ci_low", "ci_high",
                     "ebitda_impact", "risk_flags"):
            self.assertIn(col, header)

    def test_csv_includes_denial_rate_row_with_ebitda_impact(self):
        r = PacketRenderer()
        path = r.render_raw_data_csv(_full_packet())
        with open(path, newline="", encoding="utf-8") as fh:
            rows = list(csv.DictReader(fh))
        denial = next((r for r in rows if r.get("metric_key") == "denial_rate"), None)
        self.assertIsNotNone(denial)
        self.assertTrue(denial["ebitda_impact"])  # non-empty
        self.assertIn("CRITICAL", denial["risk_flags"])

    def test_csv_footer_comment_contains_audit(self):
        r = PacketRenderer()
        path = r.render_raw_data_csv(_full_packet("run-abc"), inputs_hash="hash-xyz")
        text = Path(path).read_text()
        self.assertIn("run-abc", text)
        self.assertIn("hash-xyz", text)


# ── DOCX / markdown fallback ────────────────────────────────────────

class TestQuestionsDocx(unittest.TestCase):
    def test_questions_fallback_markdown(self):
        """Without python-docx the export emits a .md file partners
        paste into Word/Docs. Sections must be organized by priority."""
        r = PacketRenderer()
        path = r.render_diligence_questions_docx(_full_packet(), inputs_hash="h")
        text = path.read_text()
        # Markdown fallback — confirm structure.
        self.assertIn("P0 Questions", text)
        self.assertIn("P1 Questions", text)
        self.assertIn("denial root-cause breakdown", text)
        self.assertIn("Audit Trail", text)

    def test_questions_empty_packet_returns_file(self):
        r = PacketRenderer()
        p = DealAnalysisPacket(deal_id="e", deal_name="E")
        path = r.render_diligence_questions_docx(p)
        self.assertTrue(path.exists())


# ── LP update portfolio roll-up ─────────────────────────────────────

class TestLPUpdate(unittest.TestCase):
    def test_lp_update_aggregates_multiple_deals(self):
        r = PacketRenderer()
        p1 = _full_packet("r-1")
        p2 = _full_packet("r-2")
        p2.deal_id = "bravo"
        p2.deal_name = "Bravo Health"
        p2.ebitda_bridge.total_ebitda_impact = 4_000_000
        html = r.render_lp_update_html([p1, p2])
        self.assertIn("Acme Health", html)
        self.assertIn("Bravo Health", html)
        self.assertIn("2</span>", html)           # deal_count = 2
        # Sum = $17.0M
        self.assertIn("$17.0M", html)

    def test_lp_update_empty_list_renders(self):
        r = PacketRenderer()
        html = r.render_lp_update_html([])
        self.assertIn("0</span>", html)
        self.assertIn("<!doctype html>", html.lower())

    def test_lp_update_flags_critical_risks_count(self):
        r = PacketRenderer()
        html = r.render_lp_update_html([_full_packet(), _full_packet("r-2")])
        # Each packet has one CRITICAL flag → 2 critical total.
        self.assertIn("2</span>", html)


# ── generated_exports audit log ─────────────────────────────────────

class TestExportAudit(unittest.TestCase):
    def setUp(self):
        self.store, self.path = _temp_store()

    def tearDown(self):
        try:
            os.unlink(self.path)
        except OSError:
            pass

    def test_record_export_writes_row(self):
        _ensure_table(self.store)
        # Prompt 21 flipped on FK enforcement — the parent deal row
        # must exist before the export references it.
        self.store.upsert_deal("d", name="d")
        row_id = record_export(
            self.store, deal_id="d", analysis_run_id="r-1",
            format="html", filepath=None, file_size_bytes=1234,
            packet_hash="h",
        )
        self.assertGreater(row_id, 0)
        rows = list_exports(self.store, "d")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["format"], "html")
        self.assertEqual(rows[0]["packet_hash"], "h")

    def test_list_exports_orders_latest_first(self):
        _ensure_table(self.store)
        self.store.upsert_deal("d", name="d")
        record_export(self.store, deal_id="d", analysis_run_id="r-1",
                       format="html", filepath=None, file_size_bytes=1,
                       packet_hash="h1")
        record_export(self.store, deal_id="d", analysis_run_id="r-2",
                       format="pptx", filepath="/tmp/x.pptx",
                       file_size_bytes=2, packet_hash="h2")
        rows = list_exports(self.store, "d")
        self.assertEqual(rows[0]["packet_hash"], "h2")
        self.assertEqual(rows[1]["packet_hash"], "h1")


# ── Audit footer appears across format pairings ─────────────────────

class TestFooterConsistency(unittest.TestCase):
    """The packet hash + run_id must appear in html, pptx (or fallback),
    csv, and docx (or fallback). Sharing the footer generator means
    changes to the footer format propagate everywhere in one edit.
    """
    def test_footer_hash_in_html_pptx_csv_docx(self):
        import zipfile as _zip
        r = PacketRenderer()
        packet = _full_packet("run-fp")
        ihash = "sha-test-aa11"
        html = r.render_diligence_memo_html(packet, inputs_hash=ihash)
        pptx = r.render_diligence_memo_pptx(packet, inputs_hash=ihash)
        csvp = r.render_raw_data_csv(packet, inputs_hash=ihash)
        mdp = r.render_diligence_questions_docx(packet, inputs_hash=ihash)
        # Prompt 22: PPTX is now a real .pptx zip — pull the final
        # slide's XML out of the archive instead of reading it as text.
        with _zip.ZipFile(pptx) as z:
            pptx_text = z.read("ppt/slides/slide8.xml").decode("utf-8")
        for rendered in (html, pptx_text, csvp.read_text(), mdp.read_text()):
            self.assertIn("run-fp", rendered,
                          f"run_id missing from {rendered[:80]!r}...")
            self.assertIn(ihash, rendered,
                          f"input hash missing from {rendered[:80]!r}...")


if __name__ == "__main__":
    unittest.main()
