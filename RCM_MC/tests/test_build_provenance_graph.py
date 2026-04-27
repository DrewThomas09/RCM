"""Test for the build_provenance_graph constructor in
ui/provenance.py (campaign target 4C, loop 124).

Loop 118 shipped the rcm_mc/ui/_provenance_tooltip.py helper
that renders a hover-card from a (graph, metric_key) pair.
But no page in the codebase actually constructed a
ProvenanceGraph — there was nothing for the helper to
consume in production.

This loop adds build_provenance_graph(ccn, hcris_profile,
ml_predictions, db_path=None) — a sibling of
build_provenance_profile that emits a graph keyed by
``observed:<metric>`` (the form recognized by
provenance.explain._resolve_metric_id). For each metric, the
node_type reflects the chosen source (HCRIS → SOURCE, ML →
PREDICTED, SELLER → OBSERVED, CALIBRATED → CALCULATED), and
losing source signals appear as parent nodes so the
explainer's upstream walk can show the full picture.

Asserts:
  - HCRIS-only input produces a SOURCE-typed node per metric
    where hcris_profile has a valid float, and explain_for_ui
    resolves them to a usable explanation dict.
  - ML-only input produces a PREDICTED-typed node.
  - Mixed HCRIS + ML inputs produce a canonical node at the
    higher-priority source plus a parent node for the loser.
  - Metrics with no signal (no HCRIS, no ML, no seller) are
    omitted entirely — explain_for_ui returns the "metric not
    found" error path for those.
  - The graph integrates with the loop-118 provenance_tooltip
    helper end-to-end: passing the built graph + a metric_key
    produces a real hover card (not the plain-text fallthrough).
"""
from __future__ import annotations

import unittest

from rcm_mc.provenance.explain import explain_for_ui
from rcm_mc.provenance.graph import NodeType
from rcm_mc.ui._provenance_tooltip import provenance_tooltip
from rcm_mc.ui.provenance import build_provenance_graph


class BuildProvenanceGraphHcrisOnlyTests(unittest.TestCase):
    def test_hcris_only_produces_source_nodes(self) -> None:
        g = build_provenance_graph(
            ccn="010001",
            hcris_profile={
                "operating_margin": 0.04,
                "beds": 200,
                "net_patient_revenue": 1.5e8,
            },
            ml_predictions={},
        )
        # 3 canonical metric nodes
        self.assertIn("observed:operating_margin", g.nodes)
        self.assertIn("observed:beds", g.nodes)
        self.assertIn("observed:net_patient_revenue", g.nodes)
        # All HCRIS-sourced → NodeType.SOURCE
        self.assertEqual(
            g.nodes["observed:operating_margin"].node_type,
            NodeType.SOURCE,
        )
        # Values round-trip
        self.assertAlmostEqual(
            g.nodes["observed:operating_margin"].value, 0.04,
        )
        self.assertEqual(
            g.nodes["observed:operating_margin"].unit, "pct",
        )

    def test_explain_resolves_built_node(self) -> None:
        g = build_provenance_graph(
            ccn="010001",
            hcris_profile={"operating_margin": 0.04},
            ml_predictions={},
        )
        ui = explain_for_ui(g, "operating_margin")
        self.assertNotIn("error", ui)
        self.assertEqual(ui["node_type"], "SOURCE")
        self.assertEqual(ui["unit"], "pct")


class BuildProvenanceGraphMlPathTests(unittest.TestCase):
    def test_ml_only_produces_predicted_node(self) -> None:
        g = build_provenance_graph(
            ccn="010001",
            hcris_profile={},
            ml_predictions={"denial_rate": 0.10},
        )
        node = g.nodes.get("observed:denial_rate")
        self.assertIsNotNone(node)
        self.assertEqual(node.node_type, NodeType.PREDICTED)


class BuildProvenanceGraphMixedSourceTests(unittest.TestCase):
    def test_hcris_plus_ml_produces_parent_edge(self) -> None:
        """When HCRIS and ML both have a value for a metric,
        HCRIS wins (per classify_metric_source priority) and
        the ML signal becomes a parent of the canonical node."""
        g = build_provenance_graph(
            ccn="010001",
            hcris_profile={"operating_margin": 0.04},
            ml_predictions={"operating_margin": 0.05},
        )
        canonical = g.nodes["observed:operating_margin"]
        self.assertEqual(canonical.node_type, NodeType.SOURCE)
        # Parent ML node should exist
        self.assertIn("ml:operating_margin", g.nodes)
        # Edge from ml node → canonical
        self.assertTrue(any(
            e.from_node == "ml:operating_margin"
            and e.to_node == "observed:operating_margin"
            for e in g.edges
        ))


class BuildProvenanceGraphAbsentSignalTests(unittest.TestCase):
    def test_metric_with_no_signal_is_omitted(self) -> None:
        """A metric with no HCRIS / ML / seller / calib value
        should NOT appear as an empty node — the explainer
        should fail to resolve it cleanly."""
        g = build_provenance_graph(
            ccn="010001",
            hcris_profile={},
            ml_predictions={},
        )
        self.assertNotIn("observed:operating_margin", g.nodes)
        ui = explain_for_ui(g, "operating_margin")
        self.assertIn("error", ui)


class GraphIntegratesWithTooltipHelperTests(unittest.TestCase):
    def test_tooltip_renders_card_with_built_graph(self) -> None:
        """End-to-end: the graph from build_provenance_graph
        plugs into the loop-118 provenance_tooltip helper and
        produces a real hover card (not the plain-text
        fallthrough)."""
        g = build_provenance_graph(
            ccn="010001",
            hcris_profile={"operating_margin": 0.04},
            ml_predictions={},
        )
        out = provenance_tooltip(
            "Operating Margin", "4.0%",
            graph=g, metric_key="operating_margin",
        )
        self.assertIn('class="prov-tt"', out)
        self.assertIn("4.0%", out)
        self.assertIn("Operating Margin", out)
        self.assertIn("SOURCE", out)


if __name__ == "__main__":
    unittest.main()
