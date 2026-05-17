"""A.10 PR B — chip propagation surface CONTRACT tests.

PR A (#141) shipped the foundation: ProfileMetric.failure_reason
field + propagation in _merge_rcm_profile + AggregatedFailure
dataclass + ck_aggregate. PR B is the surface rollout — these
tests verify the CONTRACT each consumer surface honors:

  - CSV export header includes failure_reason column
  - XLSX export header includes failure_reason column
  - Provenance graph node carries failure_reason in metadata
  - Workbench, heatmap, and other UI files import ck_prediction_chip
    (proves wire-up is present)

Why contract-tests rather than full-render integration tests for
PR B: constructing a full DealAnalysisPacket fixture across all
section dataclasses (HospitalProfile, EBITDABridgeResult,
DiligenceQuestion, RiskFlag, ComparableSet, CompletenessAssessment,
ObservedMetric, PredictedMetric, ProfileMetric, MetricSource, ...)
is a significant test scaffolding investment. The render functions
themselves are exercised by the broader regression suite
(test_analysis_workbench, test_packet_exports, test_provenance_graph)
which catches any wiring breakage at the render layer. These
contract tests pin the per-surface change shape without re-building
that fixture stack.

ck_prediction_chip's correctness vs ProfileMetric inputs is already
proven by tests/test_chip_propagation_foundation.py (29 tests in
PR A). What's new here: the SURFACE FILES correctly reach for it.
"""
from __future__ import annotations

import csv
import inspect
import io
import unittest

from rcm_mc.analysis.packet import ProfileMetric
from rcm_mc.ui._chartis_kit import ck_prediction_chip


# ────────────────────────────────────────────────────────────────────
# 1. Foundation chain re-confirmed (ProfileMetric → chip)
# ────────────────────────────────────────────────────────────────────


class TestProfileMetricToChip(unittest.TestCase):
    """Re-prove the foundation chain works against the actual
    ProfileMetric dataclass (not the PredictedMetric path that
    PR A's foundation tests already covered)."""

    def test_profile_metric_with_failure_reason_renders_chip(self):
        pm = ProfileMetric(value=12.0, failure_reason="ci_unstable")
        chip = ck_prediction_chip(pm)
        self.assertIn("ck-pred-chip-warn", chip)
        self.assertIn("fit unstable", chip)

    def test_profile_metric_without_failure_reason_renders_empty(self):
        pm = ProfileMetric(value=12.0)
        self.assertEqual(ck_prediction_chip(pm), "")

    def test_profile_metric_tier1_chip(self):
        pm = ProfileMetric(value=12.0, failure_reason="insufficient_comparables")
        chip = ck_prediction_chip(pm)
        self.assertIn("ck-pred-chip-na", chip)
        self.assertIn("insufficient comparables", chip)


# ────────────────────────────────────────────────────────────────────
# 2. CSV export — failure_reason column
# ────────────────────────────────────────────────────────────────────


class TestCsvExportColumn(unittest.TestCase):
    """The CSV writer must emit failure_reason as a column header
    AND populate it for predicted rows. Tests at the source-code
    level (inspect.getsource) so we don't need to construct a
    full packet fixture for an export round-trip."""

    def test_csv_writer_header_lists_failure_reason(self):
        from rcm_mc.exports import packet_renderer
        src = inspect.getsource(packet_renderer)
        # Find the CSV header row line. The exact line includes
        # all the column names emitted to the CSV.
        self.assertIn(
            '"failure_reason"', src,
            "packet_renderer.py CSV header doesn't include "
            "failure_reason column",
        )

    def test_csv_writer_populates_failure_reason_from_pm_or_pred(self):
        from rcm_mc.exports import packet_renderer
        src = inspect.getsource(packet_renderer)
        # The row-writer must read failure_reason from BOTH layers
        # (ProfileMetric carries it post-PR-A; PredictedMetric is
        # the source-of-truth when there's no profile row yet).
        self.assertIn("pm.failure_reason", src)
        self.assertIn("pred.failure_reason", src)


# ────────────────────────────────────────────────────────────────────
# 3. XLSX export — failure_reason column (lockstep with CSV)
# ────────────────────────────────────────────────────────────────────


class TestXlsxExportColumn(unittest.TestCase):
    def test_xlsx_writer_header_lists_failure_reason(self):
        from rcm_mc.exports import xlsx_renderer
        src = inspect.getsource(xlsx_renderer)
        self.assertIn(
            '"failure_reason"', src,
            "xlsx_renderer.py header doesn't include failure_reason",
        )

    def test_xlsx_writer_populates_failure_reason_from_pm_or_pred(self):
        from rcm_mc.exports import xlsx_renderer
        src = inspect.getsource(xlsx_renderer)
        self.assertIn("pm.failure_reason", src)
        self.assertIn("pred.failure_reason", src)


# ────────────────────────────────────────────────────────────────────
# 4. Provenance graph — failure_reason in node metadata
# ────────────────────────────────────────────────────────────────────


class TestProvenanceGraphMetadata(unittest.TestCase):
    def test_predicted_node_metadata_includes_failure_reason(self):
        from rcm_mc.provenance import graph
        src = inspect.getsource(graph)
        # The metadata dict construction in _add_predicted_nodes
        # must include failure_reason.
        self.assertIn(
            '"failure_reason": pm.failure_reason', src,
            "provenance/graph.py _add_predicted_nodes metadata "
            "dict missing failure_reason key",
        )


# ────────────────────────────────────────────────────────────────────
# 5. UI surface wire-up — chip helper is imported on each surface
# ────────────────────────────────────────────────────────────────────


class TestUISurfaceWireUp(unittest.TestCase):
    """Each surface file that renders ProfileMetric must import
    ck_prediction_chip — otherwise the chip never appears in the
    rendered HTML. Source-level check (no render needed)."""

    def test_analysis_workbench_imports_chip(self):
        from rcm_mc.ui import analysis_workbench
        src = inspect.getsource(analysis_workbench)
        self.assertIn("ck_prediction_chip", src)
        # And the metric cell concatenates it inline with the value
        self.assertIn("{value_fmt}{chip_html}", src)

    def test_analysis_workbench_risk_flag_chips_source(self):
        # Per user spec: chip belongs to the SOURCE (the
        # ProfileMetric the flag triggers on), not the flag.
        # Looking for the pattern that does `rcm_profile.get(...)`
        # then renders chip on the source.
        from rcm_mc.ui import analysis_workbench
        src = inspect.getsource(analysis_workbench)
        # rf.trigger_metric is looked up against rcm_profile
        self.assertIn("packet.rcm_profile.get(rf.trigger_metric)", src)

    def test_analysis_workbench_diligence_question_chips_source(self):
        from rcm_mc.ui import analysis_workbench
        src = inspect.getsource(analysis_workbench)
        # q.trigger_metric looked up against rcm_profile
        self.assertIn("packet.rcm_profile.get(q.trigger_metric)", src)

    def test_risk_flag_chip_tooltip_names_source_metric(self):
        # Amendment 2: tooltip must name the source metric, not just
        # the failure mode. Verifies the risk-flag chip path wraps
        # the source PM through ck_aggregate with the trigger-metric
        # name as label (so the tooltip says "Sources: denial_rate
        # (pinv_fallback)" rather than the ambiguous default
        # "Fit unstable" alone).
        from rcm_mc.ui import analysis_workbench
        src = inspect.getsource(analysis_workbench)
        # The risk-flag block routes the source through ck_aggregate
        # with the trigger-metric name as a label.
        self.assertIn(
            "ck_aggregate(source_pm, labels=[rf.trigger_metric])", src,
            "risk-flag chip doesn't route source through ck_aggregate "
            "with trigger_metric label — tooltip will lack source "
            "attribution (Amendment 2)",
        )

    def test_diligence_question_chip_tooltip_names_source_metric(self):
        # Amendment 2 — same shape for diligence questions.
        from rcm_mc.ui import analysis_workbench
        src = inspect.getsource(analysis_workbench)
        self.assertIn(
            "ck_aggregate(source_pm, labels=[q.trigger_metric])", src,
            "diligence-question chip doesn't route source through "
            "ck_aggregate with trigger_metric label — tooltip will "
            "lack source attribution (Amendment 2)",
        )

    def test_aggregated_failure_tooltip_names_source(self):
        # Behavioral check: when ck_prediction_chip is called on an
        # AggregatedFailure carrying contributing_sources, the
        # rendered chip HTML's title attribute names the source
        # metric. This is the actual partner-facing tooltip content
        # the Amendment-2 wire-up produces.
        from rcm_mc.analysis.packet import ProfileMetric
        from rcm_mc.ui._chartis_kit import ck_aggregate, ck_prediction_chip
        pm = ProfileMetric(value=12.0, failure_reason="pinv_fallback")
        chip = ck_prediction_chip(
            ck_aggregate(pm, labels=["denial_rate"])
        )
        # Source metric named in the chip's title
        self.assertIn("denial_rate", chip)
        self.assertIn("pinv_fallback", chip)
        # Tooltip prefix indicates source attribution
        self.assertIn("Sources:", chip)

    def test_analysis_workbench_json_export_carries_failure_reason(self):
        from rcm_mc.ui import analysis_workbench
        src = inspect.getsource(analysis_workbench)
        # The dict comprehension building the JSON payload includes
        # the failure_reason key
        self.assertIn('"failure_reason": pm.failure_reason', src)

    def test_portfolio_heatmap_renders_chip_inline_with_value(self):
        from rcm_mc.ui import portfolio_heatmap
        src = inspect.getsource(portfolio_heatmap)
        self.assertIn("ck_prediction_chip", src)
        # Chip concatenated to cell content (value + arrow + chip)
        self.assertIn("{val}{arrow}{chip_html}", src)


if __name__ == "__main__":
    unittest.main()
