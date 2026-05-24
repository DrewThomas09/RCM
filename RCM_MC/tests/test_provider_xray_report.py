"""CMS Provider X-Ray — benchmarked diligence report (PR B).

The report COMPOSES the existing layers (cross_sector #619 + investable_evidence
#620) — it must add no new benchmarking math and no fabricated values. Pins:
every live vertical builds a report with transparent green/amber/red/gray
signals traceable to a shown component; small samples degrade to gray; SNF
enforcement flags surface separately; hospital points to HCRIS instead of
faking peer benchmarks; caveats disclaim recommendation + market-share.
"""
from __future__ import annotations

import unittest

from rcm_mc.data.cross_sector import SECTOR_BY_ID
from rcm_mc.data.hcris import _get_latest_per_ccn
from rcm_mc.data.provider_xray import provider_match_by_ccn
from rcm_mc.data.provider_xray_report import (
    AMBER, GRAY, GREEN, RED,
    DiligenceSignal,
    build_provider_xray_report,
)
from rcm_mc.data.snf import load_snf_providers


def _tx_or_any(loader, state="TX"):
    for c, p in loader().items():
        if (getattr(p, "state", "") or "").upper() == state:
            return c
    return next(iter(loader()))


class ReportShapeTests(unittest.TestCase):
    def test_every_live_vertical_builds_a_report(self):
        for vid, spec in SECTOR_BY_ID.items():
            ccn = next(iter(spec.providers_loader()))
            m = provider_match_by_ccn(ccn, vid)
            r = build_provider_xray_report(m)
            self.assertTrue(r.has_benchmarks, f"{vid} has no benchmarks")
            self.assertTrue(r.signals, f"{vid} has no signals")
            self.assertGreaterEqual(len(r.suggested_questions), 8)
            sevs = {s.severity for s in r.signals}
            self.assertTrue(sevs <= {GREEN, AMBER, RED, GRAY})

    def test_signals_are_traceable_and_typed(self):
        ccn = _tx_or_any(load_snf_providers)
        r = build_provider_xray_report(provider_match_by_ccn(ccn, "nursing-homes"))
        names = {s.name for s in r.signals}
        self.assertIn("Quality position", names)
        self.assertIn("Peer sample", names)
        for s in r.signals:
            self.assertIsInstance(s, DiligenceSignal)
            self.assertTrue(s.detail)

    def test_quality_signal_follows_evidence_index(self):
        ccn = _tx_or_any(load_snf_providers)
        r = build_provider_xray_report(provider_match_by_ccn(ccn, "nursing-homes"))
        q = next(s for s in r.signals if s.name == "Quality position")
        idx = r.evidence.evidence_index
        if idx is None:
            self.assertEqual(q.severity, GRAY)
        elif idx >= 66:
            self.assertEqual(q.severity, GREEN)
        elif idx >= 34:
            self.assertEqual(q.severity, AMBER)
        else:
            self.assertEqual(q.severity, RED)


class HonestyTests(unittest.TestCase):
    def test_enforcement_signal_only_for_snf(self):
        snf_ccn = _tx_or_any(load_snf_providers)
        snf_r = build_provider_xray_report(provider_match_by_ccn(snf_ccn, "nursing-homes"))
        self.assertTrue(any(s.name == "Enforcement / staffing" for s in snf_r.signals))
        for vid in ("home-health", "hospice", "dialysis", "inpatient-rehab",
                    "long-term-care-hospital"):
            ccn = next(iter(SECTOR_BY_ID[vid].providers_loader()))
            r = build_provider_xray_report(provider_match_by_ccn(ccn, vid))
            self.assertFalse(any(s.name == "Enforcement / staffing" for s in r.signals),
                             f"{vid} should have no enforcement signal")

    def test_no_market_share_language(self):
        ccn = _tx_or_any(load_snf_providers)
        r = build_provider_xray_report(provider_match_by_ccn(ccn, "nursing-homes"))
        blob = " ".join(s.detail for s in r.signals) + " ".join(r.caveats)
        self.assertIn("not market share", blob.lower())
        self.assertIn("not an investment recommendation", " ".join(r.caveats).lower())

    def test_small_sample_degrades_to_gray(self):
        from rcm_mc.data import ltch
        for st in ("VT", "WY", "AK", "MT", "ND", "SD", "DE", "RI", "NH"):
            ccns = [c for c, p in ltch.load_ltch_providers().items() if p.state == st]
            if 0 < len(ccns) < 5:
                r = build_provider_xray_report(
                    provider_match_by_ccn(ccns[0], "long-term-care-hospital"))
                samp = next(s for s in r.signals if s.name == "Peer sample")
                self.assertEqual(samp.severity, GRAY)
                self.assertIn("insufficient", samp.detail.lower())
                return
        self.skipTest("no tiny-sample LTCH state available")


class HospitalReportTests(unittest.TestCase):
    def test_hospital_points_to_hcris_not_fake_benchmarks(self):
        hccn = str(_get_latest_per_ccn().iloc[0]["ccn"])
        r = build_provider_xray_report(provider_match_by_ccn(hccn, "hospital"))
        self.assertFalse(r.has_benchmarks)
        self.assertIsNone(r.evidence)
        self.assertIn("HCRIS", " ".join(s.detail for s in r.signals))
        self.assertTrue(r.note)
        self.assertGreaterEqual(len(r.suggested_questions), 8)


if __name__ == "__main__":
    unittest.main()
