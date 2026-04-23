"""Target leakage audit — must catch a deliberate leak and refuse.

The fix function pattern from the spec:

    A feature whose source provider_ids include the target — whether
    because a pipeline step forgot to hold the target out or because
    a CCD-derived metric slipped into the peer pool — must raise
    LeakageError with a chain that names the specific feature(s).

This test constructs the failure case by hand, confirms the audit
catches it, and confirms a clean peer pool passes silently.
"""
from __future__ import annotations

import unittest

from rcm_mc.diligence.integrity import (
    FeatureSource, LeakageError, LeakageFinding, audit_features,
)
from rcm_mc.diligence.integrity.leakage_audit import (
    feature_from_target, features_from_peer_pool,
)


class LeakageAuditTests(unittest.TestCase):

    # ── Clean path ──────────────────────────────────────────────────

    def test_clean_peer_pool_passes_silently(self):
        features = features_from_peer_pool(
            peer_records=[
                {"provider_id": "P-001", "denial_rate": 0.08},
                {"provider_id": "P-002", "denial_rate": 0.11},
                {"provider_id": "P-003", "denial_rate": 0.09},
            ],
            feature_names=("denial_rate",),
            dataset="CCD",
        )
        # Should not raise — target isn't in the peer pool.
        audit_features(target_provider_id="TARGET-X", features=features)

    # ── Deliberate leak ─────────────────────────────────────────────

    def test_target_in_peer_pool_raises(self):
        features = features_from_peer_pool(
            peer_records=[
                {"provider_id": "P-001", "denial_rate": 0.08},
                # Target's own data mistakenly in the peer pool:
                {"provider_id": "TARGET-X", "denial_rate": 0.12},
                {"provider_id": "P-003", "denial_rate": 0.09},
            ],
            feature_names=("denial_rate",),
            dataset="CCD",
        )
        with self.assertRaises(LeakageError) as ctx:
            audit_features(target_provider_id="TARGET-X", features=features)
        findings = ctx.exception.findings
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].feature_name, "denial_rate")
        self.assertEqual(findings[0].leaked_provider_id, "TARGET-X")
        self.assertIn("target provider 'TARGET-X'", findings[0].chain())

    def test_target_derived_feature_raises_directly(self):
        leaked = feature_from_target("ccd_days_in_ar",
                                     target_provider_id="T-999")
        with self.assertRaises(LeakageError):
            audit_features(target_provider_id="T-999", features=[leaked])

    # ── Benchmark features are exempt ───────────────────────────────

    def test_benchmark_dataset_does_not_leak(self):
        """A BENCHMARK median across thousands of hospitals that
        happens to include the target is not leakage — it's a
        population fact."""
        features = [
            FeatureSource(
                feature_name="national_p50_dar",
                dataset="BENCHMARK",
                provider_ids=("TARGET-X",) + tuple(f"P-{i:04d}" for i in range(4000)),
                description="national P50 across CMS public data",
            ),
        ]
        # Should not raise — BENCHMARK dataset is exempt.
        audit_features(target_provider_id="TARGET-X", features=features)

    # ── Normalisation ──────────────────────────────────────────────

    def test_normalises_provider_id_formatting(self):
        features = features_from_peer_pool(
            peer_records=[{"provider_id": "target-x"}],  # lower-case
            feature_names=("dar",),
        )
        with self.assertRaises(LeakageError):
            audit_features(target_provider_id="TARGET-X", features=features)

    # ── Misuse ─────────────────────────────────────────────────────

    def test_empty_target_id_rejected(self):
        with self.assertRaises(ValueError):
            audit_features(target_provider_id="", features=[])


if __name__ == "__main__":
    unittest.main()
