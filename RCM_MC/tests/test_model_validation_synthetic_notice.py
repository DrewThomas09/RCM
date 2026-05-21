"""Defensibility pin: /model-validation labels synthetic backtests.

When no live prediction ledger exists yet, the page seeds a synthetic
backtest on HCRIS data so the scorecard isn't empty. That's fine — but
the numbers must NOT be presented as validated live performance. This
test pins the honest banner that says so. (Mirrors the project rule:
never present synthetic/illustrative numbers as real validation.)
"""
from __future__ import annotations

import os
import tempfile
import unittest

from rcm_mc.data.hcris import _get_latest_per_ccn
from rcm_mc.ui.model_validation_page import render_model_validation


class SyntheticNoticeTests(unittest.TestCase):
    def test_fresh_db_shows_synthetic_backtest_banner(self) -> None:
        # A fresh DB has no recorded predictions, so the scorecard is a
        # synthetic backtest — the page must say so plainly.
        hcris = _get_latest_per_ccn()
        with tempfile.TemporaryDirectory() as tmp:
            html = render_model_validation(os.path.join(tmp, "p.db"), hcris)
        self.assertIn("Synthetic backtest", html)
        self.assertIn("not live validation", html)
        # The banner must disclaim that these are real validated numbers.
        self.assertIn("synthetic backtest on HCRIS data", html)


if __name__ == "__main__":
    unittest.main()
