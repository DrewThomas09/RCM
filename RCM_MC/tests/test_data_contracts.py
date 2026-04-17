"""Step 73: Data contract tests -- verify output schemas match expectations."""
import os
import tempfile
import unittest

import pandas as pd

from rcm_mc.cli import main


class TestOutputSchemas(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.tmpdir = tempfile.mkdtemp()
        main([
            "--actual", "configs/actual.yaml",
            "--benchmark", "configs/benchmark.yaml",
            "--n-sims", "200",
            "--seed", "42",
            "--outdir", cls.tmpdir,
            "--no-report",
        ])

    def test_simulations_csv_columns(self):
        df = pd.read_csv(os.path.join(self.tmpdir, "simulations.csv"))
        # data_scrub renames engine column sim -> iteration for board-ready CSV
        required = {"iteration", "ebitda_drag", "economic_drag"}
        self.assertTrue(required.issubset(set(df.columns)),
                        f"Missing columns: {required - set(df.columns)}")

    def test_summary_csv_has_metrics(self):
        df = pd.read_csv(os.path.join(self.tmpdir, "summary.csv"), index_col=0)
        self.assertIn("mean", df.columns)
        self.assertIn("p10", df.columns)
        self.assertIn("p90", df.columns)

    def test_provenance_json_valid(self):
        import json
        path = os.path.join(self.tmpdir, "provenance.json")
        with open(path) as f:
            doc = json.load(f)
        self.assertIn("schema", doc)
        self.assertIn("run", doc)
        self.assertIn("metrics", doc)


if __name__ == "__main__":
    unittest.main()
