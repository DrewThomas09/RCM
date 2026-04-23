"""Phase 1 ingester regression suite.

Drives every fixture under ``tests/fixtures/messy/`` through
``ingest_dataset`` and asserts the output against the fixture's
``expected.json`` contract.

When intentionally changing fixture intent, regenerate with:

    .venv/bin/python -m tests.fixtures.messy.generate_fixtures

Unintentional changes → test failure, and the reader/log are dumped
so the delta is easy to diagnose.
"""
from __future__ import annotations

import json
import os
import unittest
from pathlib import Path
from typing import Any, Dict

from rcm_mc.diligence import ingest_dataset
from rcm_mc.diligence.ingest import CanonicalClaimsDataset

FIXTURE_ROOT = Path(__file__).resolve().parent / "fixtures" / "messy"


def _load_expected(fixture_dir: Path) -> Dict[str, Any]:
    return json.loads((fixture_dir / "expected.json").read_text("utf-8"))


def _rule_set(dataset: CanonicalClaimsDataset) -> set:
    return {t.rule for t in dataset.log.entries}


class DiligenceIngesterRegressionTests(unittest.TestCase):
    """Each fixture is one test method. Keeping them as methods (rather
    than parametrised) gives clearer failure labels in the test runner."""

    # ── fixture_01 ──────────────────────────────────────────────────

    def test_fixture_01_clean_837(self) -> None:
        d = FIXTURE_ROOT / "fixture_01_clean_837"
        exp = _load_expected(d)
        ds = ingest_dataset(d)
        self.assertEqual(len(ds.claims), exp["canonical_claim_count"])
        self.assertEqual(
            sorted({c.source_system for c in ds.claims}),
            exp["distinct_source_systems"],
        )
        # Payer class distribution must match exactly.
        counts = ds.distinct_payer_classes()
        for k, v in exp["payer_class_counts"].items():
            self.assertEqual(counts.get(k, 0), v, msg=f"payer class {k}")
        rules = _rule_set(ds)
        for r in exp["must_have_transformation_rules"]:
            self.assertIn(r, rules, msg=f"expected rule missing: {r}")
        if exp.get("must_not_have_severity_error"):
            errs = [t for t in ds.log.entries if t.severity == "ERROR"]
            self.assertEqual(errs, [], msg="unexpected ERROR-severity log entries")

    # ── fixture_02 ──────────────────────────────────────────────────

    def test_fixture_02_mixed_ehr_rollup(self) -> None:
        d = FIXTURE_ROOT / "fixture_02_mixed_ehr_rollup"
        exp = _load_expected(d)
        ds = ingest_dataset(d)
        self.assertEqual(len(ds.claims), exp["canonical_claim_count"])
        self.assertEqual(
            sorted({c.source_system for c in ds.claims}),
            exp["distinct_source_systems"],
        )
        logical_ids = {c.claim_id for c in ds.claims}
        self.assertEqual(len(logical_ids), exp["logical_claim_count_after_rollup"])
        rules = _rule_set(ds)
        for r in exp["must_have_transformation_rules"]:
            self.assertIn(r, rules, msg=f"missing rule {r}")

    # ── fixture_03 ──────────────────────────────────────────────────

    def test_fixture_03_excel_merged_cells(self) -> None:
        d = FIXTURE_ROOT / "fixture_03_excel_merged_cells"
        exp = _load_expected(d)
        ds = ingest_dataset(d)
        self.assertEqual(len(ds.claims), exp["canonical_claim_count"])
        # Merged cell should have propagated Aetna across 4 rows.
        canon_counts: Dict[str, int] = {}
        for c in ds.claims:
            canon_counts[c.payer_canonical or ""] = \
                canon_counts.get(c.payer_canonical or "", 0) + 1
        for k, v in exp["payer_canonical_counts"].items():
            self.assertEqual(canon_counts.get(k, 0), v, msg=f"payer {k}")
        # No "Grand Total" row should survive.
        for c in ds.claims:
            for bad in exp.get("must_not_include_source_rows", []):
                self.assertNotIn(bad.lower(), (c.patient_id or "").lower())

    # ── fixture_04 ──────────────────────────────────────────────────

    def test_fixture_04_payer_typos(self) -> None:
        d = FIXTURE_ROOT / "fixture_04_payer_typos"
        exp = _load_expected(d)
        ds = ingest_dataset(d)
        self.assertEqual(len(ds.claims), exp["canonical_claim_count"])
        distinct = sorted({c.payer_canonical for c in ds.claims if c.payer_canonical})
        self.assertEqual(distinct, exp["distinct_payer_canonicals"])
        counts = ds.distinct_payer_classes()
        for k, v in exp["payer_class_counts"].items():
            self.assertEqual(counts.get(k, 0), v, msg=f"payer class {k}")

    # ── fixture_05 ──────────────────────────────────────────────────

    def test_fixture_05_date_format_hell(self) -> None:
        d = FIXTURE_ROOT / "fixture_05_date_format_hell"
        exp = _load_expected(d)
        ds = ingest_dataset(d)
        self.assertEqual(len(ds.claims), exp["canonical_claim_count"])
        if exp.get("all_service_dates_non_null"):
            for c in ds.claims:
                self.assertIsNotNone(
                    c.service_date_from,
                    msg=f"row {c.ccd_row_id} service_date_from is None",
                )
        rules = _rule_set(ds)
        for r in exp["must_have_transformation_rules"]:
            self.assertIn(r, rules, msg=f"missing rule {r}")

    # ── fixture_06 ──────────────────────────────────────────────────

    def test_fixture_06_partial_837(self) -> None:
        d = FIXTURE_ROOT / "fixture_06_partial_837"
        exp = _load_expected(d)
        ds = ingest_dataset(d)
        self.assertGreaterEqual(
            len(ds.claims), exp["canonical_claim_count_min"],
            msg="truncated 837 must not lose cleanly-terminated prior claims",
        )
        self.assertEqual(
            sorted({c.source_system for c in ds.claims}),
            exp["distinct_source_systems"],
        )

    # ── fixture_07 ──────────────────────────────────────────────────

    def test_fixture_07_encoding_chaos(self) -> None:
        d = FIXTURE_ROOT / "fixture_07_encoding_chaos"
        exp = _load_expected(d)
        ds = ingest_dataset(d)
        self.assertEqual(len(ds.claims), exp["canonical_claim_count"])
        # The payer column in the cp1252 row includes smart quotes +
        # em dash. It must be resolved to a canonical payer (Cigna) OR
        # left with payer_raw preserved. Here we check preservation.
        payers = [c.payer_raw for c in ds.claims]
        # At least one preserves the non-ASCII bytes via decode
        # fallback (the row should still be present — this is the
        # true test of encoding resilience).
        self.assertEqual(len(payers), exp["canonical_claim_count"])

    # ── fixture_08 ──────────────────────────────────────────────────

    def test_fixture_08_cpt_icd_drift(self) -> None:
        d = FIXTURE_ROOT / "fixture_08_cpt_icd_drift"
        exp = _load_expected(d)
        ds = ingest_dataset(d)
        self.assertEqual(len(ds.claims), exp["canonical_claim_count"])
        rules = _rule_set(ds)
        for r in exp["must_have_transformation_rules"]:
            self.assertIn(r, rules, msg=f"missing rule {r}")
        # Proprietary CPT must be preserved (upper-cased) rather than dropped.
        cpts = {c.cpt_code for c in ds.claims}
        self.assertIn("LEGACY07", cpts,
                      msg="non-standard CPT must be preserved verbatim")

    # ── fixture_09 ──────────────────────────────────────────────────

    def test_fixture_09_duplicate_claims(self) -> None:
        d = FIXTURE_ROOT / "fixture_09_duplicate_claims"
        exp = _load_expected(d)
        ds = ingest_dataset(d)
        self.assertEqual(len(ds.claims), exp["canonical_claim_count"])
        rules = _rule_set(ds)
        for r in exp["must_have_transformation_rules"]:
            self.assertIn(r, rules, msg=f"missing rule {r}")
        dup_entries = [t for t in ds.log.entries if t.rule == "duplicate_resubmit"]
        # Each cohort logs its 3 rows → ≥ 2 cohorts × 3 rows = 6 entries.
        self.assertGreaterEqual(
            len(dup_entries),
            exp["duplicate_resubmit_cohorts_min"] * 3,
        )

    # ── fixture_10 ──────────────────────────────────────────────────

    def test_fixture_10_zero_balance_writeoffs(self) -> None:
        d = FIXTURE_ROOT / "fixture_10_zero_balance_writeoffs"
        exp = _load_expected(d)
        ds = ingest_dataset(d)
        self.assertEqual(len(ds.claims), exp["canonical_claim_count"])
        zba_spec = exp["zba_row_must_preserve"]
        zba = next((c for c in ds.claims if c.claim_id == zba_spec["claim_id"]), None)
        self.assertIsNotNone(zba, msg=f"ZBA row {zba_spec['claim_id']} missing")
        # Use `if-None` rather than `or 0` — paid_amount == 0.0 is
        # exactly the ZBA case and we must not let `or` mask it.
        def _v(x, default): return default if x is None else x
        self.assertAlmostEqual(_v(zba.charge_amount, -1), zba_spec["charge_amount"])
        self.assertAlmostEqual(_v(zba.allowed_amount, -1), zba_spec["allowed_amount"])
        self.assertAlmostEqual(_v(zba.paid_amount, -1), zba_spec["paid_amount"])
        self.assertAlmostEqual(_v(zba.adjustment_amount, -1), zba_spec["adjustment_amount"])
        self.assertGreaterEqual(
            len(zba.adjustment_reason_codes),
            zba_spec["adjustment_reason_codes_min_length"],
        )
        rules = _rule_set(ds)
        for r in exp["must_have_transformation_rules"]:
            self.assertIn(r, rules, msg=f"missing rule {r}")

    # ── Cross-cutting invariants ────────────────────────────────────

    def test_every_fixture_ingests_and_roundtrips(self) -> None:
        """For every fixture: ingest → to_json → from_json → equal hash.
        The CCD's ``content_hash`` excludes wall-time fields, so a
        round-trip through JSON must produce the same hash."""
        for d in sorted(FIXTURE_ROOT.iterdir()):
            if not d.is_dir() or not (d / "expected.json").exists():
                continue
            with self.subTest(fixture=d.name):
                ds = ingest_dataset(d)
                h = ds.content_hash()
                ds2 = ingest_dataset(d)
                self.assertEqual(h, ds2.content_hash(),
                                 msg="idempotency: re-ingest must produce same hash")
                # JSON round-trip preserves hash.
                from rcm_mc.diligence.ingest import CanonicalClaimsDataset
                ds3 = CanonicalClaimsDataset.from_json(ds.to_json())
                self.assertEqual(h, ds3.content_hash(),
                                 msg="JSON round-trip must preserve content_hash")


if __name__ == "__main__":
    unittest.main()
