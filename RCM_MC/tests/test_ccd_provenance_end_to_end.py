"""CCD → KPI → ObservedMetric → provenance chain resolves end-to-end.

The spec calls this "how the analyst defends a number in IC". We
exercise the full round-trip:

    CSV file
      → ingest_dataset(...)
      → ingest transformation log entry per row
      → compute_kpis(...)
      → kpis_to_observed(bundle, ccd)
        → ObservedMetric with source="CCD" + confidence=1.0
        → ProvenanceNode(type=CCD_DERIVED) with metadata pointing at
          the CCD ingest_id + qualifying_claim_ids

If any link in the chain drops provenance, this test fails. Adds the
merge_observed_sources priority check as a second assertion: OVERRIDE
> CCD > PARTNER > PREDICTED.
"""
from __future__ import annotations

import unittest
from datetime import date
from pathlib import Path

from rcm_mc.analysis.packet import MetricSource, ObservedMetric
from rcm_mc.diligence import (
    compute_cohort_liquidation, compute_kpis, ingest_dataset,
    kpis_to_observed, merge_observed_sources,
)
from rcm_mc.provenance.graph import NodeType


FIXTURE = (
    Path(__file__).resolve().parent
    / "fixtures" / "kpi_truth" / "hospital_01_clean_acute"
)


class CCDProvenanceEndToEndTests(unittest.TestCase):

    def setUp(self):
        self.ccd = ingest_dataset(FIXTURE)
        self.bundle = compute_kpis(
            self.ccd, as_of_date=date(2025, 1, 1), provider_id="H1",
        )
        self.out = kpis_to_observed(self.bundle, self.ccd)

    # ── The chain ───────────────────────────────────────────────────

    def test_observed_metrics_carry_ccd_source(self):
        metrics = self.out.observed_metrics
        self.assertIn("days_in_ar", metrics)
        self.assertEqual(
            metrics["days_in_ar"].source, MetricSource.CCD.value,
        )
        self.assertEqual(metrics["days_in_ar"].confidence, 1.0)
        self.assertIn("HFMA", metrics["days_in_ar"].source_detail)

    def test_provenance_nodes_point_to_ccd_source(self):
        ccd_derived = [
            n for n in self.out.provenance_nodes
            if n.node_type == NodeType.CCD_DERIVED
        ]
        self.assertGreaterEqual(len(ccd_derived), 1)
        dar_node = next((n for n in ccd_derived if n.id == "ccd::days_in_ar"), None)
        self.assertIsNotNone(dar_node)
        md = dar_node.metadata
        self.assertEqual(md["ingest_id"], self.ccd.ingest_id)
        self.assertEqual(md["sample_size"], 10)
        self.assertEqual(len(md["qualifying_claim_ids"]), 10)

    def test_source_node_is_present_exactly_once(self):
        source_nodes = [
            n for n in self.out.provenance_nodes
            if n.node_type == NodeType.SOURCE
            and n.id.startswith("ccd_source::")
        ]
        self.assertEqual(len(source_nodes), 1)
        self.assertEqual(source_nodes[0].metadata["ingest_id"],
                         self.ccd.ingest_id)

    def test_edges_wire_source_to_derived(self):
        edges = self.out.provenance_edges
        self.assertGreater(len(edges), 0)
        for e in edges:
            self.assertTrue(e.from_node.startswith("ccd_source::"))
            self.assertTrue(e.to_node.startswith("ccd::"))

    # ── Transformation log reachable via provenance ────────────────

    def test_log_is_recoverable_from_ingest_id(self):
        """Given only the ingest_id stored in the provenance node
        metadata, we should be able to find the original
        transformation log — in production this is an index lookup;
        here we verify that the link exists in the dataset object."""
        md = next(
            n for n in self.out.provenance_nodes
            if n.node_type == NodeType.CCD_DERIVED
        ).metadata
        self.assertEqual(md["ingest_id"], self.ccd.ingest_id)
        # The actual log:
        log_summary = self.ccd.log.summary()
        self.assertGreater(sum(log_summary.values()), 0,
                           "transformation log must have entries")

    # ── None-KPIs are skipped, not fabricated ──────────────────────

    def test_none_kpis_do_not_produce_observed_metrics(self):
        """Cost to Collect returns None (no inputs); it must not
        appear in observed_metrics."""
        self.assertNotIn("cost_to_collect", self.out.observed_metrics)
        self.assertTrue(
            any(kpi == "Cost to Collect" for kpi, _ in self.out.skipped_kpis),
        )

    # ── Priority order: OVERRIDE > CCD > PARTNER > PREDICTED ───────

    def test_merge_priority_order(self):
        override = {"days_in_ar": 99.9}
        ccd = {"days_in_ar": ObservedMetric(
            value=30.0, source=MetricSource.CCD.value, confidence=1.0,
        )}
        partner = {"days_in_ar": ObservedMetric(
            value=50.0, source=MetricSource.EXTRACTED.value,
        )}
        predicted = {"days_in_ar": ObservedMetric(
            value=40.0, source=MetricSource.PREDICTED.value,
        )}
        merged = merge_observed_sources(
            override=override, ccd=ccd,
            partner_yaml=partner, predicted=predicted,
        )
        self.assertAlmostEqual(merged["days_in_ar"].value, 99.9)
        self.assertEqual(merged["days_in_ar"].source, MetricSource.OBSERVED.value)

    def test_ccd_beats_partner_yaml(self):
        ccd = {"days_in_ar": ObservedMetric(
            value=30.0, source=MetricSource.CCD.value, confidence=1.0,
        )}
        partner = {"days_in_ar": ObservedMetric(
            value=50.0, source=MetricSource.EXTRACTED.value,
        )}
        merged = merge_observed_sources(ccd=ccd, partner_yaml=partner)
        self.assertAlmostEqual(merged["days_in_ar"].value, 30.0)
        self.assertEqual(merged["days_in_ar"].source, MetricSource.CCD.value)

    def test_partner_beats_predicted(self):
        partner = {"days_in_ar": ObservedMetric(
            value=50.0, source=MetricSource.EXTRACTED.value,
        )}
        predicted = {"days_in_ar": ObservedMetric(
            value=40.0, source=MetricSource.PREDICTED.value,
        )}
        merged = merge_observed_sources(
            partner_yaml=partner, predicted=predicted,
        )
        self.assertAlmostEqual(merged["days_in_ar"].value, 50.0)

    # ── ObservedMetric confidence in JSON round-trip ───────────────

    def test_observed_metric_confidence_roundtrips(self):
        om = ObservedMetric(value=30.0, source="CCD", confidence=1.0)
        d = om.to_dict()
        self.assertIn("confidence", d)
        om2 = ObservedMetric.from_dict(d)
        self.assertEqual(om2.confidence, 1.0)
        # Missing confidence in dict defaults to 1.0 (backwards compat).
        d_no_conf = {k: v for k, v in d.items() if k != "confidence"}
        om3 = ObservedMetric.from_dict(d_no_conf)
        self.assertEqual(om3.confidence, 1.0)


if __name__ == "__main__":
    unittest.main()
