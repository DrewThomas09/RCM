"""CCDDerivedMetric node + chain completeness + explainer walkback.

Covers:
- Construction of a ``CCDDerivedMetric`` and round-trip to a
  ``ProvenanceNode``.
- ``attach_ccd_source`` + ``attach_ccd_derived`` extend a
  ``ProvenanceGraph`` without breaking existing node types.
- ``chain_is_complete`` catches a broken chain (missing ingest_id,
  missing upstream source, zero claim ids).
- ``explain_metric`` + ``explain_for_ui`` produce a narrative that
  names the KPI rule, the ingest_id, and the source-row chain.
- Integration with ``conformal.split_train_calibration`` via a
  :class:`SplitManifest`: provider-disjoint rows end up in train
  or calibration but never both.
"""
from __future__ import annotations

import unittest
import warnings

import numpy as np

from rcm_mc.diligence.integrity import SplitManifest, build_split_manifest
from rcm_mc.ml.conformal import split_train_calibration
from rcm_mc.provenance.ccd_nodes import (
    CCDDerivedMetric,
    attach_ccd_derived,
    attach_ccd_source,
    chain_is_complete,
    explain_ccd_derived,
)
from rcm_mc.provenance.explain import explain_for_ui, explain_metric
from rcm_mc.provenance.graph import NodeType, ProvenanceGraph


def _build_ccd_metric(**overrides) -> CCDDerivedMetric:
    defaults = dict(
        metric_key="days_in_ar",
        label="Days in A/R",
        value=30.0,
        unit="days",
        ingest_id="ccd-deadbeef",
        kpi_aggregation_rule="weighted_mean(paid_date - service_date_from)",
        citation="HFMA MAP Key — Days in A/R",
        qualifying_claim_ids=("H1-001", "H1-002", "H1-003"),
        transformation_refs=(
            {"source_file": "claims.csv", "source_row": 2, "rule": "date_parse:iso"},
            {"source_file": "claims.csv", "source_row": 3, "rule": "date_parse:iso"},
        ),
        kpi_source_detail="CCD:ccd-deadbeef · HFMA MAP Key · n=3",
        sample_size=3,
        confidence=1.0,
    )
    defaults.update(overrides)
    return CCDDerivedMetric(**defaults)


class CCDDerivedMetricTests(unittest.TestCase):

    def test_to_node_preserves_metadata(self):
        m = _build_ccd_metric()
        node = m.to_node()
        self.assertEqual(node.node_type, NodeType.CCD_DERIVED)
        self.assertEqual(node.id, "ccd::days_in_ar")
        self.assertAlmostEqual(node.value, 30.0)
        self.assertEqual(node.confidence, 1.0)
        self.assertEqual(node.metadata["ingest_id"], "ccd-deadbeef")
        self.assertEqual(node.metadata["sample_size"], 3)
        self.assertEqual(len(node.metadata["qualifying_claim_ids"]), 3)
        self.assertEqual(len(node.metadata["transformation_refs"]), 2)

    def test_attach_ccd_source_is_idempotent(self):
        g = ProvenanceGraph()
        id1 = attach_ccd_source(
            g, ingest_id="ccd-xyz",
            source_files=["a.csv", "b.parquet"],
            content_hash="abcd1234",
        )
        id2 = attach_ccd_source(
            g, ingest_id="ccd-xyz",
            source_files=["a.csv", "b.parquet"],
        )
        self.assertEqual(id1, id2)
        self.assertEqual(len([n for n in g.nodes.values()
                              if n.node_type == NodeType.SOURCE]), 1)

    def test_attach_ccd_derived_wires_edge_to_source(self):
        g = ProvenanceGraph()
        m = _build_ccd_metric()
        node_id = attach_ccd_derived(g, m)
        self.assertIn(node_id, g.nodes)
        self.assertIn("ccd_source::ccd-deadbeef", g.nodes)
        edges = [e for e in g.edges
                 if e.to_node == node_id
                 and e.from_node == "ccd_source::ccd-deadbeef"]
        self.assertEqual(len(edges), 1)


class ChainCompletenessTests(unittest.TestCase):

    def test_complete_chain_returns_ok(self):
        g = ProvenanceGraph()
        attach_ccd_derived(g, _build_ccd_metric())
        ok, missing = chain_is_complete(g, "ccd::days_in_ar")
        self.assertTrue(ok)
        self.assertIsNone(missing)

    def test_unknown_node_flagged(self):
        g = ProvenanceGraph()
        ok, missing = chain_is_complete(g, "ccd::does_not_exist")
        self.assertFalse(ok)
        self.assertIn("unknown node", missing or "")

    def test_missing_ingest_id_breaks_chain(self):
        g = ProvenanceGraph()
        m = _build_ccd_metric(ingest_id="")
        node = m.to_node()
        g.nodes[node.id] = node
        ok, missing = chain_is_complete(g, node.id)
        self.assertFalse(ok)
        self.assertIn("ingest_id", missing or "")

    def test_missing_source_node_breaks_chain(self):
        g = ProvenanceGraph()
        m = _build_ccd_metric()
        node = m.to_node()
        g.nodes[node.id] = node       # derived node only, no source
        ok, missing = chain_is_complete(g, node.id)
        self.assertFalse(ok)
        self.assertIn("CCD source", missing or "")

    def test_zero_claims_breaks_chain(self):
        g = ProvenanceGraph()
        m = _build_ccd_metric(qualifying_claim_ids=())
        attach_ccd_derived(g, m)
        ok, missing = chain_is_complete(g, m.node_id())
        self.assertFalse(ok)
        self.assertIn("qualifying_claim_ids", missing or "")


class ExplainerTests(unittest.TestCase):

    def test_explain_mentions_kpi_rule_and_ingest_id(self):
        g = ProvenanceGraph()
        attach_ccd_derived(g, _build_ccd_metric())
        text = explain_metric(g, "days_in_ar")
        self.assertIn("ccd-deadbeef", text)
        self.assertIn("weighted_mean", text)
        self.assertIn("HFMA", text)

    def test_explain_lists_source_row_chain(self):
        g = ProvenanceGraph()
        attach_ccd_derived(g, _build_ccd_metric())
        text = explain_metric(g, "days_in_ar")
        self.assertIn("claims.csv", text)
        self.assertIn("row 2", text)
        self.assertIn("date_parse:iso", text)

    def test_explain_for_ui_returns_chain_break_when_incomplete(self):
        g = ProvenanceGraph()
        m = _build_ccd_metric()
        node = m.to_node()
        g.nodes[node.id] = node       # derived only, no source
        out = explain_for_ui(g, "days_in_ar")
        self.assertIn("error", out)
        self.assertIn("chain_break", out)
        self.assertIn("CCD source", out["chain_break"] or "")

    def test_explain_ccd_derived_handles_missing_fields_gracefully(self):
        g = ProvenanceGraph()
        m = _build_ccd_metric(
            qualifying_claim_ids=(),
            transformation_refs=(),
            temporal_validity={},
        )
        # attach_ccd_derived still writes the node + edge; the
        # explainer shouldn't crash on empty metadata.
        attach_ccd_derived(g, m)
        text = explain_ccd_derived(g, g.nodes[m.node_id()])
        self.assertIn("ccd-deadbeef", text)
        self.assertIn("weighted_mean", text)


class ConformalSplitManifestTests(unittest.TestCase):

    def test_provider_disjoint_mode_routes_by_bucket(self):
        # Build a 6-provider pool plus target H1. Manifest partitions
        # them into train (~3), calibration (~2), test (~1 + target).
        pool = [f"P-{i:02d}" for i in range(6)]
        manifest = build_split_manifest(
            target_provider_id="H1", provider_pool=pool, random_seed=7,
        )
        # Synthesise one row per provider (not the target — target
        # is in TEST, not in train/cal).
        X = np.arange(6).reshape(-1, 1).astype(float)
        y = np.arange(6).astype(float)
        provider_ids = pool
        Xt, yt, Xc, yc = split_train_calibration(
            X, y, provider_ids=provider_ids, manifest=manifest,
        )
        # No overlap between train and cal.
        train_pids = {provider_ids[i] for i in range(6)
                      if provider_ids[i] in manifest.split.train}
        cal_pids = {provider_ids[i] for i in range(6)
                    if provider_ids[i] in manifest.split.calibration}
        self.assertEqual(train_pids & cal_pids, set())
        # Row counts match bucket sizes.
        self.assertEqual(len(Xt), len(train_pids))
        self.assertEqual(len(Xc), len(cal_pids))

    def test_manifest_without_provider_ids_raises(self):
        manifest = build_split_manifest(
            target_provider_id="H1",
            provider_pool=[f"P-{i:02d}" for i in range(6)],
        )
        X = np.arange(6).reshape(-1, 1).astype(float)
        y = np.arange(6).astype(float)
        with self.assertRaises(ValueError):
            split_train_calibration(X, y, manifest=manifest)

    def test_provider_ids_without_manifest_emits_deprecation(self):
        X = np.arange(6).reshape(-1, 1).astype(float)
        y = np.arange(6).astype(float)
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            split_train_calibration(
                X, y, provider_ids=[f"P-{i}" for i in range(6)],
            )
        dep = [msg for msg in w
               if issubclass(msg.category, DeprecationWarning)]
        self.assertGreaterEqual(len(dep), 1)

    def test_legacy_mode_unchanged(self):
        # No provider_ids, no manifest → legacy row-wise split, no
        # warning, same shape contract as pre-session-4.
        X = np.arange(20).reshape(-1, 1).astype(float)
        y = np.arange(20).astype(float)
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            Xt, yt, Xc, yc = split_train_calibration(
                X, y, cal_fraction=0.3, random_state=0,
            )
        self.assertEqual(
            len([msg for msg in w
                 if issubclass(msg.category, DeprecationWarning)]), 0,
            msg="legacy mode should not emit deprecation warnings",
        )
        self.assertEqual(len(Xt) + len(Xc), 20)


class SplitManifestHashTests(unittest.TestCase):

    def test_same_inputs_produce_same_hash(self):
        kwargs = dict(
            target_provider_id="H1",
            provider_pool=[f"P-{i:02d}" for i in range(10)],
            random_seed=42,
        )
        a = build_split_manifest(**kwargs)
        b = build_split_manifest(**kwargs)
        self.assertEqual(a.manifest_hash, b.manifest_hash)

    def test_different_seed_changes_hash(self):
        pool = [f"P-{i:02d}" for i in range(10)]
        a = build_split_manifest(target_provider_id="H1",
                                 provider_pool=pool, random_seed=1)
        b = build_split_manifest(target_provider_id="H1",
                                 provider_pool=pool, random_seed=2)
        self.assertNotEqual(a.manifest_hash, b.manifest_hash)

    def test_hash_round_trip_through_to_dict(self):
        a = build_split_manifest(
            target_provider_id="H1",
            provider_pool=[f"P-{i:02d}" for i in range(10)],
        )
        d = a.to_dict()
        self.assertIn("manifest_hash", d)
        self.assertEqual(d["manifest_hash"], a.manifest_hash)


if __name__ == "__main__":
    unittest.main()
