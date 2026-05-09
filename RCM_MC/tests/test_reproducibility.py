"""tests for reproducible-artifact embedding (P66 + P67)."""
from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
import unittest

from rcm_mc.exports.reproducibility import (
    VERIFY_SCRIPT, canonical_hash, reproducibility_block,
)


SAMPLE_INPUTS = {
    "deal_id": "aurora",
    "ebitda_year0": 67_500_000,
    "revenue_year0": 450_000_000,
    "denial_rate": 0.092,
    "n_runs": 250,
}


class CanonicalHashStability(unittest.TestCase):

    def test_same_payload_same_hash(self) -> None:
        h1 = canonical_hash(SAMPLE_INPUTS)
        h2 = canonical_hash(SAMPLE_INPUTS)
        self.assertEqual(h1, h2)

    def test_key_order_insensitive(self) -> None:
        # Reorder keys → canonical_hash should produce the same digest.
        reordered = dict(reversed(list(SAMPLE_INPUTS.items())))
        self.assertEqual(
            canonical_hash(SAMPLE_INPUTS),
            canonical_hash(reordered),
        )

    def test_value_change_changes_hash(self) -> None:
        modified = dict(SAMPLE_INPUTS)
        modified["denial_rate"] = 0.118
        self.assertNotEqual(
            canonical_hash(SAMPLE_INPUTS),
            canonical_hash(modified),
        )


class ReproducibilityBlockRendering(unittest.TestCase):

    def test_payload_json_embedded(self) -> None:
        html = reproducibility_block(
            SAMPLE_INPUTS,
            run_id="run-2026-05-09-aurora",
            artifact_kind="lp_update",
        )
        # Extract the payload via the same regex verify.py uses.
        m = re.search(
            r'<script type="application/json" '
            r'id="rcm-reproducibility-payload">(.*?)</script>',
            html,
            flags=re.DOTALL,
        )
        self.assertIsNotNone(m)
        # Need to undo the </ → <\/ escape for parsing.
        raw = m.group(1).replace(r"<\/", "</")
        parsed = json.loads(raw)
        self.assertEqual(parsed["run_id"], "run-2026-05-09-aurora")
        self.assertEqual(parsed["artifact_kind"], "lp_update")
        self.assertEqual(parsed["inputs"], SAMPLE_INPUTS)
        self.assertEqual(
            parsed["inputs_hash"],
            canonical_hash(SAMPLE_INPUTS),
        )

    def test_visible_footer_includes_run_id_and_hash(self) -> None:
        html = reproducibility_block(
            SAMPLE_INPUTS,
            run_id="run-2026-05-09-aurora",
            artifact_kind="lp_update",
        )
        self.assertIn("run-2026-05-09-aurora", html)
        # First 16 chars of hash visible.
        self.assertIn(canonical_hash(SAMPLE_INPUTS)[:16], html)

    def test_download_link_to_verify_script(self) -> None:
        html = reproducibility_block(
            SAMPLE_INPUTS,
            run_id="run-1",
            artifact_kind="ic_memo",
        )
        # data: URL ships the script so an LP analyst can save it
        # without a separate download endpoint.
        self.assertIn("data:text/x-python", html)
        self.assertIn('download="verify.py"', html)


class VerifyScriptEndToEnd(unittest.TestCase):
    """Save the rendered artifact to disk, save verify.py to disk,
    invoke verify.py on the artifact, confirm VERIFIED."""

    def test_verify_round_trip(self) -> None:
        # Build an artifact-shaped HTML containing the reproducibility
        # block. verify.py only cares about the embedded JSON; the
        # rest of the HTML is decorative.
        block = reproducibility_block(
            SAMPLE_INPUTS,
            run_id="rt-1",
            artifact_kind="lp_update",
        )
        artifact_html = (
            "<!doctype html><html><body><h1>LP Update</h1>"
            f"{block}"
            "</body></html>"
        )
        with tempfile.TemporaryDirectory() as d:
            artifact_path = f"{d}/artifact.html"
            verify_path = f"{d}/verify.py"
            with open(artifact_path, "w", encoding="utf-8") as f:
                f.write(artifact_html)
            with open(verify_path, "w", encoding="utf-8") as f:
                f.write(VERIFY_SCRIPT)

            result = subprocess.run(
                [sys.executable, verify_path, artifact_path],
                capture_output=True, text=True, timeout=10,
            )
        self.assertEqual(result.returncode, 0,
                         f"stderr={result.stderr}\nstdout={result.stdout}")
        self.assertIn("VERIFIED", result.stdout)
        self.assertIn("rt-1", result.stdout)

    def test_tampered_artifact_reports_mismatch(self) -> None:
        # Mutate one byte of the embedded inputs and confirm
        # verify.py reports MISMATCH.
        block = reproducibility_block(
            SAMPLE_INPUTS,
            run_id="rt-2",
            artifact_kind="lp_update",
        )
        # Swap denial_rate for 0.999 in the embedded JSON. The JSON
        # encoder may or may not insert a space after the colon, so
        # try both forms.
        tampered = block.replace('"denial_rate": 0.092',
                                 '"denial_rate": 0.999')
        if tampered == block:
            tampered = block.replace('"denial_rate":0.092',
                                     '"denial_rate":0.999')
        self.assertNotEqual(tampered, block)  # tampering happened
        artifact_html = (
            "<!doctype html><html><body>"
            f"{tampered}"
            "</body></html>"
        )
        with tempfile.TemporaryDirectory() as d:
            artifact_path = f"{d}/tampered.html"
            verify_path = f"{d}/verify.py"
            with open(artifact_path, "w", encoding="utf-8") as f:
                f.write(artifact_html)
            with open(verify_path, "w", encoding="utf-8") as f:
                f.write(VERIFY_SCRIPT)
            result = subprocess.run(
                [sys.executable, verify_path, artifact_path],
                capture_output=True, text=True, timeout=10,
            )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("MISMATCH", result.stdout)


if __name__ == "__main__":
    unittest.main()
