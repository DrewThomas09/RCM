"""End-to-end LP Update reproducibility — verify.py round-trip.

PROMPTS.md Phase 5 / Prompt 66 acceptance: download the LP Update
HTML, run the embedded ``verify.py`` script in a stdlib-only
environment, and see ``VERIFIED`` output.

This test exercises the full path:
  1. Build a synthetic ``DealAnalysisPacket``
  2. Render the LP Update via ``PacketRenderer.render_lp_update_html``
  3. Save the HTML + ``verify.py`` to a temp dir
  4. Subprocess-invoke ``verify.py <artifact.html>``
  5. Assert exit 0 + "VERIFIED" in stdout

A tampered artifact must report MISMATCH.
"""
from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path


def _build_synthetic_packet():
    """Build a minimal packet stub the LP renderer can consume.

    The renderer reads only ``.deal_id``, ``.deal_name``,
    ``.ebitda_bridge.total_ebitda_impact``, ``.risk_flags``,
    ``.diligence_questions``, ``.run_id``, ``.generated_at``. A
    ``SimpleNamespace`` is enough — no need for the full
    ``DealAnalysisPacket`` dataclass.
    """
    from types import SimpleNamespace
    bridge = SimpleNamespace(total_ebitda_impact=4_500_000.0)
    return SimpleNamespace(
        deal_id="aurora",
        deal_name="Project Aurora",
        ebitda_bridge=bridge,
        risk_flags=[],
        diligence_questions=[],
        run_id="run-aurora-001",
        generated_at=datetime(2026, 5, 9, tzinfo=timezone.utc),
    )


class LPUpdateRoundTrip(unittest.TestCase):

    def setUp(self) -> None:
        from rcm_mc.exports.packet_renderer import PacketRenderer
        from rcm_mc.exports.reproducibility import VERIFY_SCRIPT

        renderer = PacketRenderer(out_dir=Path(tempfile.mkdtemp()))
        self.html = renderer.render_lp_update_html(
            [_build_synthetic_packet()]
        )
        self.verify_script = VERIFY_SCRIPT

    def test_artifact_contains_reproducibility_block(self) -> None:
        self.assertIn(
            'id="rcm-reproducibility-payload"',
            self.html,
        )
        self.assertIn("verify.py", self.html)

    def test_verify_py_round_trip_passes(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            artifact_path = Path(d) / "lp_update.html"
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
        self.assertIn("run-aurora-001", result.stdout)

    def test_tampered_artifact_reports_mismatch(self) -> None:
        # Mutate the embedded total_opportunity_usd; verify.py
        # should detect the tampering.
        tampered = self.html.replace(
            '"total_opportunity_usd": 4500000.0',
            '"total_opportunity_usd": 9999999.0',
        )
        # Pin that the substring replacement actually fired (else
        # the test passes vacuously).
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
