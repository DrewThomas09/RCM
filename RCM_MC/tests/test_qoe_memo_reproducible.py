"""End-to-end QoE memo reproducibility — verify.py round-trip.

PROMPTS.md Phase 5 / Prompt 67 (third memo type). Mirrors the LP
Update + IC Memo wiring: the QoE memo HTML now embeds the
canonical reproducibility block; the embedded ``verify.py``
script round-trips against the generated artifact.

Reuses the existing ``hospital_08_waterfall_critical`` KPI fixture
to avoid synthesizing a KPIBundle by hand.
"""
from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path

from rcm_mc.diligence import ingest_dataset
from rcm_mc.diligence.benchmarks import compute_cash_waterfall, compute_kpis
from rcm_mc.exports.qoe_memo import QoEMemoMetadata, render_qoe_memo_html
from rcm_mc.exports.reproducibility import VERIFY_SCRIPT


FIXTURE_ROOT = Path(__file__).resolve().parent / "fixtures" / "kpi_truth"


def _build_qoe_html() -> str:
    fixture = "hospital_08_waterfall_critical"
    ccd = ingest_dataset(FIXTURE_ROOT / fixture)
    as_of = date(2025, 1, 1)
    bundle = compute_kpis(ccd, as_of_date=as_of, provider_id=fixture)
    waterfall = compute_cash_waterfall(
        ccd.claims, as_of_date=as_of,
        management_reported_revenue_by_cohort_month={"2024-03": 6850.0},
    )
    meta = QoEMemoMetadata(
        deal_name="Project Aurora",
        target_entity="Aurora Specialty Hospital LLC",
        engagement_id="RCM-2025-042",
        partner_name="Partner A",
        preparer_name="Senior Associate B",
    )
    return render_qoe_memo_html(
        bundle=bundle,
        cash_waterfall=waterfall,
        metadata=meta,
    )


class QoEMemoRoundTrip(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        cls.html = _build_qoe_html()

    def test_artifact_contains_reproducibility_block(self) -> None:
        self.assertIn(
            'id="rcm-reproducibility-payload"',
            self.html,
        )
        self.assertIn("verify.py", self.html)

    def test_run_id_namespaced_to_qoe_memo(self) -> None:
        self.assertIn("qoe-memo-RCM-2025-042-", self.html)

    def test_artifact_kind_marker(self) -> None:
        self.assertIn('"artifact_kind": "qoe_memo"', self.html)

    def test_verify_py_round_trip_passes(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            artifact_path = Path(d) / "qoe_memo.html"
            verify_path = Path(d) / "verify.py"
            artifact_path.write_text(self.html, encoding="utf-8")
            verify_path.write_text(VERIFY_SCRIPT, encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(verify_path), str(artifact_path)],
                capture_output=True, text=True, timeout=10,
            )
        self.assertEqual(
            result.returncode, 0,
            f"stderr={result.stderr}\nstdout={result.stdout}",
        )
        self.assertIn("VERIFIED", result.stdout)

    def test_tampered_artifact_reports_mismatch(self) -> None:
        # Mutate the engagement id in the embedded JSON; verify.py
        # must report MISMATCH.
        tampered = self.html.replace(
            '"engagement_id": "RCM-2025-042"',
            '"engagement_id": "RCM-2025-999"',
        )
        self.assertNotEqual(tampered, self.html)
        with tempfile.TemporaryDirectory() as d:
            artifact_path = Path(d) / "tampered.html"
            verify_path = Path(d) / "verify.py"
            artifact_path.write_text(tampered, encoding="utf-8")
            verify_path.write_text(VERIFY_SCRIPT, encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(verify_path), str(artifact_path)],
                capture_output=True, text=True, timeout=10,
            )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("MISMATCH", result.stdout)


if __name__ == "__main__":
    unittest.main()
