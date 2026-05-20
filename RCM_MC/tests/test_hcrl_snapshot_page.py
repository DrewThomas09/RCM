"""Healthcare Revenue Leakage V2 — snapshot UI render tests."""
from __future__ import annotations

import unittest
from pathlib import Path

from rcm_mc.diligence.snapshot import run_snapshot
from rcm_mc.diligence.snapshot_page import (
    render_snapshot_result,
    render_snapshot_upload,
)

_FIX = Path(__file__).parent / "fixtures" / "edi"


class TestUploadPage(unittest.TestCase):
    def test_form_and_phi_warning(self):
        html = render_snapshot_upload()
        self.assertIn('action="/diligence/snapshot"', html)
        self.assertIn('enctype="multipart/form-data"', html)
        self.assertIn("PHI", html)
        self.assertIn('type="file"', html)

    def test_error_surfaced(self):
        html = render_snapshot_upload(error="Analysis failed: boom")
        self.assertIn("Analysis failed: boom", html)


class TestResultPage(unittest.TestCase):
    def setUp(self):
        self.res = run_snapshot(
            [_FIX / "clean_837p.edi", _FIX / "clean_835.edi"],
            deal_name="Project Atlas", salt="s")
        self.html = render_snapshot_result(self.res, deal_name="Project Atlas")

    def test_contains_score_findings_memo(self):
        self.assertIn("Data Confidence", self.html)
        self.assertIn(f"{self.res.confidence.score}/100", self.html)
        self.assertIn("Diligence memo", self.html)
        self.assertIn("## 1. Executive summary", self.html)  # memo embedded

    def test_phi_safe(self):
        import re
        self.assertIsNone(re.search(r"\bPT-\w", self.html))
        self.assertNotIn("MRN", self.html)

    def test_deal_name_shown(self):
        self.assertIn("Project Atlas", self.html)


if __name__ == "__main__":
    unittest.main()
