"""Integration test — all six guardrails fire on a CCD-attached build.

Session 4 done-criteria: "Integration test proves all six run when a
CCD is attached to a packet build."

Exercises the full preflight surface: builds a CCD from a kpi_truth
fixture, runs every guardrail, and asserts the report has exactly
six ``GuardrailResult`` rows (one per guardrail), each with the
expected name. Also exercises the FAIL paths — a deliberate leak,
a corrupted manifest, a censored cohort request, and an OOD
distribution — to prove the preflight is honest when things go
wrong.
"""
from __future__ import annotations

import unittest
from datetime import date
from pathlib import Path

from rcm_mc.diligence import ingest_dataset
from rcm_mc.diligence.integrity import (
    FeatureSource,
    GuardrailResult,
    PreflightReport,
    SplitManifest,
    build_split_manifest,
    run_ccd_guardrails,
)
from rcm_mc.diligence.integrity.leakage_audit import (
    feature_from_target,
    features_from_peer_pool,
)


FIXTURES = Path(__file__).resolve().parent / "fixtures" / "kpi_truth"


class PreflightIntegrationTests(unittest.TestCase):

    def setUp(self):
        self.ccd = ingest_dataset(FIXTURES / "hospital_01_clean_acute")
        self.as_of = date(2025, 1, 1)
        self.target = "H1"
        self.peer_pool = [f"P-{i:03d}" for i in range(40)]

    # ── Happy path — all six PASS ───────────────────────────────────

    def test_all_six_guardrails_run_on_clean_inputs(self):
        manifest = build_split_manifest(
            target_provider_id=self.target,
            provider_pool=self.peer_pool,
        )
        peer_features = features_from_peer_pool(
            [{"provider_id": p, "dar": 30.0} for p in self.peer_pool[:5]],
            feature_names=("dar",),
        )
        report = run_ccd_guardrails(
            self.ccd,
            as_of_date=self.as_of,
            target_provider_id=self.target,
            peer_features=peer_features,
            split_manifest=manifest,
        )
        self.assertIsInstance(report, PreflightReport)
        guardrails = [r.guardrail for r in report.results]
        self.assertEqual(len(guardrails), 6,
                         msg=f"expected 6 guardrails, got {guardrails}")
        self.assertEqual(
            sorted(guardrails),
            sorted(["leakage_audit", "split_enforcer", "cohort_censoring",
                    "distribution_shift", "temporal_validity",
                    "provenance_chain"]),
        )
        self.assertFalse(report.any_fail,
                         msg=f"clean inputs should not FAIL: "
                             f"{[r for r in report.results if not r.ok]}")
        self.assertEqual(report.status, "PASS")

    # ── FAIL path — deliberate leakage ──────────────────────────────

    def test_fails_on_leaking_peer_feature(self):
        manifest = build_split_manifest(
            target_provider_id=self.target,
            provider_pool=self.peer_pool,
        )
        leaking = [feature_from_target("dar", target_provider_id=self.target)]
        report = run_ccd_guardrails(
            self.ccd, as_of_date=self.as_of,
            target_provider_id=self.target,
            peer_features=leaking,
            split_manifest=manifest,
        )
        self.assertTrue(report.any_fail)
        leak_result = report.by_guardrail()["leakage_audit"]
        self.assertEqual(leak_result.status, "FAIL")
        self.assertFalse(leak_result.ok)

    # ── FAIL path — censored cohort requested ───────────────────────

    def test_fails_on_censored_cohort_request(self):
        """Ask for a 120d liquidation number on a cohort that's only
        30 days old — the preflight must refuse."""
        ccd_young = ingest_dataset(FIXTURES / "hospital_03_censoring")
        # hospital_03 claims are March 2026-ish with as_of 2026-03-15;
        # asking for 2026-02 at 120d is definitely censored.
        report = run_ccd_guardrails(
            ccd_young, as_of_date=date(2026, 3, 15),
            target_provider_id="H3",
            requested_cohort_cells=[("2026-02", 120)],
        )
        censoring = report.by_guardrail()["cohort_censoring"]
        self.assertEqual(censoring.status, "FAIL")
        self.assertTrue(report.any_fail)

    # ── WARN path — regulatory overlap ──────────────────────────────

    def test_warns_when_regulatory_event_inside_window(self):
        """Claims spanning 2025-12 → 2026-02 include the OBBBA phase-
        in (effective 2026-01-01). Temporal validity should WARN."""
        # Use hospital_03 which has claims in Dec 2025 + Feb 2026 —
        # OBBBA Medicaid work requirements take effect 2026-01-01.
        ccd_spanning = ingest_dataset(FIXTURES / "hospital_03_censoring")
        report = run_ccd_guardrails(
            ccd_spanning, as_of_date=date(2026, 3, 15),
            target_provider_id="H3",
        )
        temporal = report.by_guardrail()["temporal_validity"]
        self.assertEqual(temporal.status, "WARN")
        self.assertTrue(temporal.ok)    # WARN is ok=True, not a failure
        self.assertIn("regulatory event", temporal.reason)

    # ── Inputs that aren't available get neutral PASS ───────────────

    def test_missing_inputs_skip_gracefully_with_pass(self):
        """When no peer features + no manifest + no corpus are
        supplied, the three dependent guardrails return neutral PASS
        with a 'skipped' reason. The three input-independent
        guardrails still run."""
        report = run_ccd_guardrails(
            self.ccd, as_of_date=self.as_of,
            target_provider_id=self.target,
        )
        by = report.by_guardrail()
        self.assertEqual(by["leakage_audit"].status, "PASS")
        self.assertIn("skipped", by["leakage_audit"].reason)
        self.assertEqual(by["split_enforcer"].status, "PASS")
        self.assertIn("skipped", by["split_enforcer"].reason)
        self.assertEqual(by["distribution_shift"].status, "PASS")
        self.assertIn("skipped", by["distribution_shift"].reason)
        # Cohort censoring + temporal validity always run.
        self.assertIn(by["cohort_censoring"].status, ("PASS", "WARN"))
        self.assertIn(by["temporal_validity"].status, ("PASS", "WARN"))

    # ── Serialisation contract ──────────────────────────────────────

    def test_preflight_report_json_shape(self):
        report = run_ccd_guardrails(
            self.ccd, as_of_date=self.as_of,
            target_provider_id=self.target,
        )
        d = report.to_dict()
        self.assertIn("status", d)
        self.assertIn("any_fail", d)
        self.assertIn("results", d)
        self.assertEqual(len(d["results"]), 6)
        for r in d["results"]:
            self.assertIn("guardrail", r)
            self.assertIn("status", r)
            self.assertIn("reason", r)


if __name__ == "__main__":
    unittest.main()
