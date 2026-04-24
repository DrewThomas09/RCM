"""Integration sockets regression tests.

Two vendor capabilities, one adapter pattern per capability:

- ChartAuditAdapter + ManualChartAuditAdapter + StubVendorChartAuditAdapter
- ContractDigitizationAdapter + ManualContractDigitizationAdapter +
  StubVendorContractDigitizationAdapter

Invariants under test:

- Data classes serialise → JSON → deserialise cleanly (round trip)
- Manual adapters submit → poll cycle writes a readable file, returns
  a valid report, and handles unknown job_ids with a clear error
- Stub vendor adapters REFUSE to fake output — calls raise
  NotImplementedError with the exact HTTP endpoint documented
- Chart audit rollups compute signed net delta, under/over rates
  from per-finding direction
- Contract extraction maps to the real re-pricer ContractSchedule
  and silently drops unparseable rows rather than raising
- Adapters satisfy the runtime-checkable Protocol (ABC conformance)
"""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from rcm_mc.diligence.benchmarks.contract_repricer import (
    ContractRate, ContractSchedule,
)
from rcm_mc.integrations import (
    ChartAuditAdapter,
    ChartAuditFinding,
    ChartAuditJob,
    ChartAuditReport,
    ContractDigitizationAdapter,
    ContractDigitizationJob,
    ContractDigitizationReport,
    ContractExtraction,
    ManualChartAuditAdapter,
    ManualContractDigitizationAdapter,
    StubVendorChartAuditAdapter,
    StubVendorContractDigitizationAdapter,
)


# ── Chart audit ────────────────────────────────────────────────────

class ChartAuditFindingTests(unittest.TestCase):

    def test_delta_positive_on_undercoding(self):
        f = ChartAuditFinding(
            claim_id="c1", billed_code="99213", audited_code="99214",
            billed_amount_usd=100.0, audited_amount_usd=150.0,
            direction="UNDERCODED",
        )
        self.assertEqual(f.delta_usd, 50.0)

    def test_delta_negative_on_overcoding(self):
        f = ChartAuditFinding(
            claim_id="c2", billed_code="99215", audited_code="99213",
            billed_amount_usd=200.0, audited_amount_usd=100.0,
            direction="OVERCODED",
        )
        self.assertEqual(f.delta_usd, -100.0)

    def test_delta_zero_on_no_change(self):
        f = ChartAuditFinding(
            claim_id="c3", billed_code="99213", audited_code="99213",
            billed_amount_usd=100.0, audited_amount_usd=100.0,
            direction="NO_CHANGE",
        )
        self.assertEqual(f.delta_usd, 0.0)


class ChartAuditReportRollupTests(unittest.TestCase):

    def setUp(self):
        self.report = ChartAuditReport(
            job=ChartAuditJob(job_id="J-1", sample_size=4),
            findings=[
                ChartAuditFinding(
                    claim_id="c1", billed_amount_usd=100,
                    audited_amount_usd=150, direction="UNDERCODED",
                ),
                ChartAuditFinding(
                    claim_id="c2", billed_amount_usd=100,
                    audited_amount_usd=100, direction="NO_CHANGE",
                ),
                ChartAuditFinding(
                    claim_id="c3", billed_amount_usd=200,
                    audited_amount_usd=80, direction="OVERCODED",
                ),
                ChartAuditFinding(
                    claim_id="c4", billed_amount_usd=50,
                    audited_amount_usd=80, direction="UNDERCODED",
                ),
            ],
        )

    def test_net_reimbursement_delta_is_signed_sum(self):
        # +50 + 0 + (-120) + 30 = -40
        self.assertAlmostEqual(
            self.report.net_reimbursement_delta_usd, -40.0, places=2,
        )

    def test_under_rate_and_over_rate(self):
        self.assertAlmostEqual(self.report.under_rate, 0.5)
        self.assertAlmostEqual(self.report.over_rate, 0.25)

    def test_rates_on_empty_report_are_zero(self):
        empty = ChartAuditReport(job=ChartAuditJob(job_id="J-2"))
        self.assertEqual(empty.under_rate, 0.0)
        self.assertEqual(empty.over_rate, 0.0)
        self.assertEqual(empty.net_reimbursement_delta_usd, 0.0)


class ChartAuditJsonRoundTripTests(unittest.TestCase):

    def test_report_survives_json_round_trip(self):
        from rcm_mc.integrations.chart_audit import _report_from_dict
        original = ChartAuditReport(
            job=ChartAuditJob(job_id="J-rt", sample_size=2,
                              vendor="example_vendor"),
            findings=[
                ChartAuditFinding(
                    claim_id="c1", billed_amount_usd=100,
                    audited_amount_usd=150, direction="UNDERCODED",
                    reason="documented 99214, billed 99213",
                ),
            ],
        )
        rebuilt = _report_from_dict(original.to_dict())
        self.assertEqual(rebuilt.job.job_id, "J-rt")
        self.assertEqual(rebuilt.job.vendor, "example_vendor")
        self.assertEqual(len(rebuilt.findings), 1)
        self.assertEqual(rebuilt.findings[0].reason,
                         "documented 99214, billed 99213")


class ChartAuditManualAdapterTests(unittest.TestCase):

    def test_submit_writes_placeholder_readable_as_in_progress(self):
        with tempfile.TemporaryDirectory() as tmp:
            adapter = ManualChartAuditAdapter(tmp)
            job = ChartAuditJob(job_id="J-abc", sample_size=10,
                                deal_id="D-1")
            job_id = adapter.submit(job)
            self.assertEqual(job_id, "J-abc")
            # File exists, is JSON, parses to IN_PROGRESS
            path = Path(tmp) / "J-abc.json"
            self.assertTrue(path.exists())
            d = json.loads(path.read_text("utf-8"))
            self.assertEqual(d["status"], "IN_PROGRESS")
            # poll() returns the placeholder
            rep = adapter.poll("J-abc")
            self.assertEqual(rep.status, "IN_PROGRESS")
            self.assertEqual(rep.findings, [])

    def test_poll_reads_analyst_filled_in_report(self):
        """After submit(), the analyst edits the JSON file with real
        findings and calls poll() — that's the manual workflow."""
        with tempfile.TemporaryDirectory() as tmp:
            adapter = ManualChartAuditAdapter(tmp)
            adapter.submit(ChartAuditJob(job_id="J-def", sample_size=2))
            # Simulate the analyst editing the file.
            completed = ChartAuditReport(
                job=ChartAuditJob(job_id="J-def", sample_size=2),
                findings=[
                    ChartAuditFinding(
                        claim_id="c1", billed_amount_usd=100,
                        audited_amount_usd=150, direction="UNDERCODED",
                    ),
                ],
                completed_at="2026-01-01T00:00:00+00:00",
                status="COMPLETED",
            )
            (Path(tmp) / "J-def.json").write_text(
                json.dumps(completed.to_dict()), encoding="utf-8",
            )
            rep = adapter.poll("J-def")
            self.assertEqual(rep.status, "COMPLETED")
            self.assertEqual(len(rep.findings), 1)
            self.assertAlmostEqual(
                rep.net_reimbursement_delta_usd, 50.0,
            )

    def test_poll_unknown_job_raises_file_not_found(self):
        with tempfile.TemporaryDirectory() as tmp:
            adapter = ManualChartAuditAdapter(tmp)
            with self.assertRaises(FileNotFoundError):
                adapter.poll("no-such-job")

    def test_invalid_job_id_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            adapter = ManualChartAuditAdapter(tmp)
            with self.assertRaises(ValueError):
                adapter.submit(ChartAuditJob(job_id="../../etc/passwd"))

    def test_protocol_conformance(self):
        with tempfile.TemporaryDirectory() as tmp:
            adapter = ManualChartAuditAdapter(tmp)
            self.assertIsInstance(adapter, ChartAuditAdapter)


class ChartAuditStubVendorTests(unittest.TestCase):

    def test_requires_api_key(self):
        with self.assertRaises(ValueError):
            StubVendorChartAuditAdapter(api_key="")

    def test_submit_refuses_to_fake(self):
        adapter = StubVendorChartAuditAdapter(api_key="fake-key")
        with self.assertRaises(NotImplementedError) as cm:
            adapter.submit(ChartAuditJob(job_id="X"))
        self.assertIn("POST", str(cm.exception))
        self.assertIn("audits", str(cm.exception))

    def test_poll_refuses_to_fake(self):
        adapter = StubVendorChartAuditAdapter(api_key="fake-key")
        with self.assertRaises(NotImplementedError) as cm:
            adapter.poll("X")
        self.assertIn("GET", str(cm.exception))

    def test_protocol_conformance(self):
        adapter = StubVendorChartAuditAdapter(api_key="fake-key")
        self.assertIsInstance(adapter, ChartAuditAdapter)


# ── Contract digitization ─────────────────────────────────────────

class ContractExtractionToScheduleTests(unittest.TestCase):

    def test_maps_to_schedule_with_all_rate_types(self):
        ext = ContractExtraction(
            payer_name="Blue Shield of CA",
            rate_rows=[
                {"payer_class": "COMMERCIAL", "cpt_code": "99213",
                 "allowed_amount_usd": 120.0, "withhold_pct": 0.02},
                {"payer_class": "COMMERCIAL", "cpt_code": "99214",
                 "allowed_pct_of_charge": 0.65},
                {"payer_class": "COMMERCIAL", "cpt_code": "99215",
                 "is_carve_out": True},
            ],
        )
        sched = ext.to_schedule()
        self.assertIsInstance(sched, ContractSchedule)
        self.assertEqual(len(sched.rates), 3)
        self.assertEqual(sched.name, "Blue Shield of CA")
        # Spot-check a row.
        r = next(r for r in sched.rates if r.cpt_code == "99213")
        self.assertEqual(r.allowed_amount_usd, 120.0)
        self.assertEqual(r.withhold_pct, 0.02)
        r2 = next(r for r in sched.rates if r.cpt_code == "99215")
        self.assertTrue(r2.is_carve_out)

    def test_unparseable_rows_are_silently_dropped(self):
        """Rows with no rate info and no carve_out flag are dropped
        rather than raising — the extraction's quality issue surfaces
        at the report level, not as an exception."""
        ext = ContractExtraction(
            payer_name="Medicaid",
            rate_rows=[
                {"payer_class": "MEDICAID", "cpt_code": "99213",
                 "allowed_amount_usd": 50.0},
                # Missing rate info entirely.
                {"payer_class": "MEDICAID", "cpt_code": "99999"},
                # Missing payer_class (can't uniquely identify).
                {"cpt_code": "99214", "allowed_amount_usd": 70},
                # Missing cpt_code.
                {"payer_class": "MEDICAID", "allowed_amount_usd": 80},
                # Bad numeric; caught and dropped.
                {"payer_class": "MEDICAID", "cpt_code": "99216",
                 "allowed_amount_usd": "not-a-number"},
            ],
        )
        sched = ext.to_schedule()
        self.assertEqual(len(sched.rates), 1)
        self.assertEqual(sched.rates[0].cpt_code, "99213")


class ContractDigitizationJsonRoundTripTests(unittest.TestCase):

    def test_report_survives_json_round_trip(self):
        from rcm_mc.integrations.contract_digitization import (
            _report_from_dict,
        )
        original = ContractDigitizationReport(
            job=ContractDigitizationJob(
                job_id="C-rt",
                source_filename="medicare_2024.pdf",
                payer_name="Medicare",
            ),
            extraction=ContractExtraction(
                payer_name="Medicare",
                rate_rows=[
                    {"payer_class": "MEDICARE", "cpt_code": "99213",
                     "allowed_amount_usd": 80.0},
                ],
            ),
            status="COMPLETED",
            confidence_score=0.92,
            unparseable_sections=["amendment-3"],
        )
        rebuilt = _report_from_dict(original.to_dict())
        self.assertEqual(rebuilt.job.job_id, "C-rt")
        self.assertEqual(rebuilt.confidence_score, 0.92)
        self.assertEqual(rebuilt.unparseable_sections, ["amendment-3"])
        self.assertIsNotNone(rebuilt.extraction)
        self.assertEqual(rebuilt.extraction.payer_name, "Medicare")


class ContractDigitizationManualAdapterTests(unittest.TestCase):

    def test_submit_poll_cycle(self):
        with tempfile.TemporaryDirectory() as tmp:
            adapter = ManualContractDigitizationAdapter(tmp)
            job = ContractDigitizationJob(
                job_id="C-1", source_filename="medicare.pdf",
                payer_name="Medicare",
            )
            jid = adapter.submit(job)
            self.assertEqual(jid, "C-1")
            rep = adapter.poll("C-1")
            self.assertEqual(rep.status, "IN_PROGRESS")
            self.assertIsNone(rep.extraction)

    def test_poll_unknown_raises_file_not_found(self):
        with tempfile.TemporaryDirectory() as tmp:
            adapter = ManualContractDigitizationAdapter(tmp)
            with self.assertRaises(FileNotFoundError):
                adapter.poll("missing")

    def test_protocol_conformance(self):
        with tempfile.TemporaryDirectory() as tmp:
            adapter = ManualContractDigitizationAdapter(tmp)
            self.assertIsInstance(adapter, ContractDigitizationAdapter)


class ContractDigitizationStubVendorTests(unittest.TestCase):

    def test_stub_refuses_to_fake(self):
        adapter = StubVendorContractDigitizationAdapter(api_key="k")
        with self.assertRaises(NotImplementedError):
            adapter.submit(ContractDigitizationJob(
                job_id="X", source_filename="foo.pdf",
            ))
        with self.assertRaises(NotImplementedError):
            adapter.poll("X")

    def test_stub_requires_api_key(self):
        with self.assertRaises(ValueError):
            StubVendorContractDigitizationAdapter(api_key="")

    def test_protocol_conformance(self):
        adapter = StubVendorContractDigitizationAdapter(api_key="k")
        self.assertIsInstance(adapter, ContractDigitizationAdapter)


if __name__ == "__main__":
    unittest.main()
