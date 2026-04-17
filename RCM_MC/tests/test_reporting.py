"""Tests for reporting plots and layout behavior."""
from __future__ import annotations

import os
import tempfile
import unittest
import warnings

import pandas as pd

from rcm_mc.reports.reporting import plot_deal_summary


class TestReportingPlots(unittest.TestCase):
    def test_plot_deal_summary_avoids_tight_layout_warning(self):
        summary = pd.DataFrame(
            {
                "mean": [18_500_000.0],
                "p10": [11_200_000.0],
                "p90": [27_800_000.0],
            },
            index=["ebitda_drag"],
        )
        tf = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
        tf.close()
        try:
            with warnings.catch_warnings(record=True) as caught:
                warnings.simplefilter("always")
                plot_deal_summary(summary, 12.5, tf.name)
            messages = [str(w.message) for w in caught]
            self.assertFalse(
                any("Tight layout not applied" in msg for msg in messages),
                msg=messages,
            )
            self.assertTrue(os.path.exists(tf.name))
            self.assertGreater(os.path.getsize(tf.name), 0)
        finally:
            os.unlink(tf.name)


if __name__ == "__main__":
    unittest.main()
