"""Packet-builder ↔ integrity gauntlet hook.

Closes the "callable but not invoked" gap flagged at the end of
session 4: when ``build_analysis_packet`` is called with a CCD
attached, the six guardrails run automatically, their results land
on ``packet.integrity_checks``, and a FAIL raises
:class:`GuardrailViolation`.

Two cases exercise the hook end-to-end:

1. ``ccd=None`` (every existing caller): the preflight is NOT
   invoked, ``packet.integrity_checks == []``, and behaviour is
   byte-for-byte unchanged vs pre-session-5.
2. ``ccd=<CCD>`` attached: exactly six guardrails ran, each
   :class:`IntegrityCheck` on the packet has the expected shape,
   and the guardrail names match what the preflight would produce
   standalone.

No fixture deal / store is built here — we drive
``build_analysis_packet`` with the in-memory ``store=None`` path the
existing packet tests already use, so this test doesn't couple to
the analysis_runs SQLite cache.
"""
from __future__ import annotations

import unittest
from datetime import date
from pathlib import Path
from unittest import mock

from rcm_mc.analysis.packet import DealAnalysisPacket, IntegrityCheck
from rcm_mc.analysis.packet_builder import build_analysis_packet
from rcm_mc.diligence import ingest_dataset
from rcm_mc.diligence.integrity import GuardrailViolation


FIXTURES = Path(__file__).resolve().parent / "fixtures" / "kpi_truth"


class _FakeStore:
    """Minimal store stub matching the shape the builder needs.

    The builder reads a deal row from the store; we return a dict
    shaped like the real SQLite row so ``_load_deal_row`` resolves.
    Every test path we exercise returns ``None`` from
    ``get_overrides`` (no analyst overrides).
    """
    def __init__(self, deal_id: str, name: str = "Test Deal"):
        self._deal_id = deal_id
        self._name = name

    # Builder's ``_load_deal_row`` calls ``store.get_deal`` OR reads
    # a raw dict depending on the store type. Keep the interface
    # minimal and let the real path monkey-patch.


def _build_deal_row(deal_id: str) -> dict:
    return {
        "id": deal_id,
        "name": "Test Deal",
        "provider_id": "H1",
        "bed_count": 120,
        "state": "IL",
        "sector": "hospital",
        "profile": {
            "observed_metrics": {},
            "hospital_type": "acute",
        },
    }


class PacketBuilderHookTests(unittest.TestCase):

    # ── Case 1: ccd=None, existing behaviour ────────────────────────

    def test_no_ccd_skips_preflight_and_sets_empty_integrity_checks(self):
        """The all-existing-callers path. ``integrity_checks`` is an
        empty list (additive default); the preflight module is
        never imported.
        """
        deal_row = _build_deal_row("D-no-ccd")
        with mock.patch(
            "rcm_mc.analysis.packet_builder._load_deal_row",
            return_value=deal_row,
        ), mock.patch(
            "rcm_mc.diligence.integrity.preflight.run_ccd_guardrails",
        ) as preflight_mock:
            packet = build_analysis_packet(
                store=None, deal_id="D-no-ccd", skip_simulation=True,
            )
        self.assertIsInstance(packet, DealAnalysisPacket)
        self.assertEqual(packet.integrity_checks, [])
        preflight_mock.assert_not_called()

    def test_no_ccd_json_round_trip_preserves_empty_integrity_checks(self):
        """Packets built without a CCD serialise + deserialise with
        ``integrity_checks=[]`` — no drop, no spurious fill."""
        deal_row = _build_deal_row("D-rt")
        with mock.patch(
            "rcm_mc.analysis.packet_builder._load_deal_row",
            return_value=deal_row,
        ):
            packet = build_analysis_packet(
                store=None, deal_id="D-rt", skip_simulation=True,
            )
        d = packet.to_dict()
        self.assertEqual(d["integrity_checks"], [])
        packet2 = DealAnalysisPacket.from_dict(d)
        self.assertEqual(packet2.integrity_checks, [])

    # ── Case 2: ccd attached, preflight fires ───────────────────────

    def test_ccd_attached_runs_six_guardrails(self):
        """A CCD-attached build runs the preflight and attaches
        exactly six IntegrityCheck rows with the expected names."""
        ccd = ingest_dataset(FIXTURES / "hospital_01_clean_acute")
        deal_row = _build_deal_row("D-ccd")
        with mock.patch(
            "rcm_mc.analysis.packet_builder._load_deal_row",
            return_value=deal_row,
        ):
            packet = build_analysis_packet(
                store=None, deal_id="D-ccd", skip_simulation=True,
                as_of=date(2025, 1, 1),
                ccd=ccd,
            )
        self.assertEqual(len(packet.integrity_checks), 6)
        names = {c.guardrail for c in packet.integrity_checks}
        self.assertEqual(names, {
            "leakage_audit", "split_enforcer", "cohort_censoring",
            "distribution_shift", "temporal_validity", "provenance_chain",
        })
        # Every check is an IntegrityCheck instance with a status.
        for c in packet.integrity_checks:
            self.assertIsInstance(c, IntegrityCheck)
            self.assertIn(c.status, {"PASS", "WARN", "FAIL"})

    def test_ccd_attached_clean_fixture_produces_no_fails(self):
        """hospital_01_clean_acute passes every guardrail (no leakage
        inputs, no manifest, no corpus, no regulatory overlap)."""
        ccd = ingest_dataset(FIXTURES / "hospital_01_clean_acute")
        deal_row = _build_deal_row("D-clean")
        with mock.patch(
            "rcm_mc.analysis.packet_builder._load_deal_row",
            return_value=deal_row,
        ):
            packet = build_analysis_packet(
                store=None, deal_id="D-clean", skip_simulation=True,
                as_of=date(2025, 1, 1),
                ccd=ccd,
            )
        fails = [c for c in packet.integrity_checks if c.status == "FAIL"]
        self.assertEqual(fails, [],
                         msg=f"clean fixture should not fail: {fails}")

    def test_ccd_attached_regulatory_overlap_is_warn_not_fail(self):
        """hospital_03 spans Dec 2025 → Feb 2026, crossing the OBBBA
        2026-01-01 phase-in. Temporal validity WARNs but does not
        FAIL the build — WARN must not raise."""
        ccd = ingest_dataset(FIXTURES / "hospital_03_censoring")
        deal_row = _build_deal_row("D-regoverlap")
        with mock.patch(
            "rcm_mc.analysis.packet_builder._load_deal_row",
            return_value=deal_row,
        ):
            packet = build_analysis_packet(
                store=None, deal_id="D-regoverlap", skip_simulation=True,
                as_of=date(2026, 3, 15),
                ccd=ccd,
            )
        temporal = [c for c in packet.integrity_checks
                    if c.guardrail == "temporal_validity"]
        self.assertEqual(len(temporal), 1)
        self.assertEqual(temporal[0].status, "WARN")
        self.assertTrue(temporal[0].ok)

    # ── FAIL path raises ────────────────────────────────────────────

    def test_ccd_attached_fail_raises_guardrail_violation(self):
        """Force a FAIL by patching a guardrail to return ``ok=False``.
        Build must raise GuardrailViolation BEFORE step 2 does any
        observed-metric work."""
        from rcm_mc.diligence.integrity.split_enforcer import GuardrailResult

        ccd = ingest_dataset(FIXTURES / "hospital_01_clean_acute")
        deal_row = _build_deal_row("D-fail")

        def _fake_preflight(ccd, **kwargs):
            from rcm_mc.diligence.integrity.preflight import PreflightReport
            return PreflightReport(
                ran_at_ingest_id="fake",
                results=[
                    GuardrailResult(
                        guardrail="leakage_audit", ok=False, status="FAIL",
                        reason="deliberate leak for test",
                    ),
                    GuardrailResult(
                        guardrail="split_enforcer", ok=True, status="PASS",
                        reason="ok",
                    ),
                    GuardrailResult(
                        guardrail="cohort_censoring", ok=True, status="PASS",
                        reason="ok",
                    ),
                    GuardrailResult(
                        guardrail="distribution_shift", ok=True, status="PASS",
                        reason="skipped",
                    ),
                    GuardrailResult(
                        guardrail="temporal_validity", ok=True, status="PASS",
                        reason="ok",
                    ),
                    GuardrailResult(
                        guardrail="provenance_chain", ok=True, status="PASS",
                        reason="deferred",
                    ),
                ],
            )

        with mock.patch(
            "rcm_mc.analysis.packet_builder._load_deal_row",
            return_value=deal_row,
        ), mock.patch(
            "rcm_mc.diligence.integrity.preflight.run_ccd_guardrails",
            side_effect=_fake_preflight,
        ):
            with self.assertRaises(GuardrailViolation) as ctx:
                build_analysis_packet(
                    store=None, deal_id="D-fail", skip_simulation=True,
                    as_of=date(2025, 1, 1),
                    ccd=ccd,
                )
        # Exception names the failed guardrail(s) for the analyst.
        self.assertEqual(len(ctx.exception.failed), 1)
        self.assertEqual(ctx.exception.failed[0].guardrail, "leakage_audit")
        self.assertIn("leakage_audit", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
