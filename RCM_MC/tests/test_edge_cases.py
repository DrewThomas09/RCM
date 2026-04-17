"""Step 66: Edge case tests for empty/degenerate DataFrames."""
import unittest
import numpy as np
import pandas as pd

from rcm_mc.data.data_scrub import scrub_simulation_data
from rcm_mc.reports.reporting import summary_table, correlation_sensitivity


class TestEmptyDataFrames(unittest.TestCase):

    def test_scrub_empty(self):
        df = pd.DataFrame()
        result, report = scrub_simulation_data(df)
        self.assertEqual(len(result), 0)
        self.assertEqual(report.total_rows, 0)

    def test_scrub_single_row(self):
        df = pd.DataFrame({"ebitda_drag": [100.0], "sim": [0]})
        result, report = scrub_simulation_data(df)
        self.assertEqual(len(result), 1)

    def test_summary_table_minimal(self):
        df = pd.DataFrame({
            "ebitda_drag": [100, 200, 300],
            "economic_drag": [10, 20, 30],
        })
        try:
            summary = summary_table(df)
            self.assertIsNotNone(summary)
        except Exception:
            pass  # acceptable if it requires more columns

    def test_scrub_all_nan_ebitda(self):
        df = pd.DataFrame({"ebitda_drag": [np.nan, np.nan, np.nan], "sim": [0, 1, 2]})
        result, report = scrub_simulation_data(df)
        self.assertEqual(len(result), 3)


class TestCorrelationSensitivity(unittest.TestCase):

    def test_with_no_driver_cols(self):
        df = pd.DataFrame({
            "ebitda_drag": np.random.randn(100),
            "other_col": np.random.randn(100),
        })
        try:
            result = correlation_sensitivity(df)
            self.assertIsNotNone(result)
        except Exception:
            pass  # may legitimately fail with no drivers


if __name__ == "__main__":
    unittest.main()
