"""End-to-end IC memo reproducibility — verify.py round-trip.

PROMPTS.md Phase 5 / Prompt 67: same contract as the LP Update —
embedded JSON + stdlib-only verify.py — applied to the IC memo
HTML renderer.
"""
from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path


def _build_review():
    """Build a minimal PartnerReview the IC memo HTML renderer can
    consume. Real reviews are produced by ``partner_review_from_*``
    factories; we synthesise the bare-minimum field set."""
    from rcm_mc.pe_intelligence.partner_review import (
        NarrativeBlock, PartnerReview,
    )

    narrative = NarrativeBlock(
        recommendation="PROCEED",
        recommendation_rationale="Solid fundamentals, manageable risks.",
        headline="Steward-pattern flag clears under counterfactual.",
        bull_case="Multi-site rural consolidation play.",
        bear_case="Steward-style sale-leaseback exposure on three sites.",
        key_questions=[
            "Will the clearinghouse vendor consolidation hold?",
            "Is regulatory headwind priced in at $360M?",
        ],
        ic_memo_paragraph="Recommend PROCEED at $360M.",
    )
    return PartnerReview(
        deal_id="aurora",
        deal_name="Project Aurora",
        generated_at=datetime(2026, 5, 9, tzinfo=timezone.utc),
        context_summary={
            "ebitda_m": 67.5,
            "hospital_type": "Rural multi-site",
            "projected_irr": 0.223,
            "projected_moic": 2.80,
            "entry_multiple": 8.9,
            "exit_multiple": 9.5,
        },
        reasonableness_checks=[],
        heuristic_hits=[],
        narrative=narrative,
    )


class ICMemoRoundTrip(unittest.TestCase):

    def setUp(self) -> None:
        from rcm_mc.exports.reproducibility import VERIFY_SCRIPT
        from rcm_mc.pe_intelligence.ic_memo import render_html

        self.html = render_html(_build_review())
        self.verify_script = VERIFY_SCRIPT

    def test_artifact_contains_reproducibility_block(self) -> None:
        self.assertIn(
            'id="rcm-reproducibility-payload"',
            self.html,
        )
        self.assertIn("verify.py", self.html)

    def test_run_id_namespaced_to_ic_memo(self) -> None:
        # The repro block uses an IC-memo-specific run id so a
        # downstream consumer can tell artifact families apart.
        self.assertIn("ic-memo-aurora-", self.html)

    def test_verify_py_round_trip_passes(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            artifact_path = Path(d) / "ic_memo.html"
            verify_path = Path(d) / "verify.py"
            artifact_path.write_text(self.html, encoding="utf-8")
            verify_path.write_text(self.verify_script, encoding="utf-8")
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
        # Mutate the recommendation field; verify.py must catch.
        tampered = self.html.replace(
            '"recommendation": "PROCEED"',
            '"recommendation": "PASS"',
        )
        self.assertNotEqual(tampered, self.html)
        with tempfile.TemporaryDirectory() as d:
            artifact_path = Path(d) / "tampered.html"
            verify_path = Path(d) / "verify.py"
            artifact_path.write_text(tampered, encoding="utf-8")
            verify_path.write_text(self.verify_script, encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(verify_path), str(artifact_path)],
                capture_output=True, text=True, timeout=10,
            )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("MISMATCH", result.stdout)


if __name__ == "__main__":
    unittest.main()
