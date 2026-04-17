"""Step 69: Integration test for full CLI pipeline."""
import os
import tempfile
import unittest

from rcm_mc.cli import main


class TestCLIIntegration(unittest.TestCase):

    def test_full_pipeline(self):
        """Run CLI end-to-end and verify output files exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            main([
                "--actual", "configs/actual.yaml",
                "--benchmark", "configs/benchmark.yaml",
                "--n-sims", "200",
                "--seed", "42",
                "--outdir", tmpdir,
                "--no-report",
            ])

            expected_files = [
                "simulations.csv",
                "summary.csv",
                "provenance.json",
            ]
            for fname in expected_files:
                path = os.path.join(tmpdir, fname)
                self.assertTrue(os.path.exists(path), f"Missing: {fname}")
                self.assertGreater(os.path.getsize(path), 0, f"Empty: {fname}")


class TestRunCompletionBanner(unittest.TestCase):
    """Brick 38: completion box should carry an IC one-liner when CCN is known."""

    def test_banner_includes_one_liner_when_ccn_provided(self):
        import argparse
        import io
        import sys

        from rcm_mc.cli import _print_run_complete_banner

        args = argparse.Namespace(bundle=False, report=False, partner_brief=False)
        buf = io.StringIO()
        saved = sys.stdout
        sys.stdout = buf
        try:
            _print_run_complete_banner("/tmp/outdir", args, target_ccn="360180")
        finally:
            sys.stdout = saved
        out = buf.getvalue()
        self.assertIn("Summary:", out)
        self.assertIn("CLEVELAND CLINIC", out)

    def test_banner_omits_summary_when_no_ccn(self):
        import argparse
        import io
        import sys

        from rcm_mc.cli import _print_run_complete_banner

        args = argparse.Namespace(bundle=False, report=False, partner_brief=False)
        buf = io.StringIO()
        saved = sys.stdout
        sys.stdout = buf
        try:
            _print_run_complete_banner("/tmp/outdir", args, target_ccn=None)
        finally:
            sys.stdout = saved
        self.assertNotIn("Summary:", buf.getvalue())


class TestValidateOnly(unittest.TestCase):

    def test_validate_only(self):
        """--validate-only exits cleanly."""
        try:
            main([
                "--actual", "configs/actual.yaml",
                "--benchmark", "configs/benchmark.yaml",
                "--validate-only",
            ])
        except SystemExit as e:
            self.assertEqual(e.code, 0)


if __name__ == "__main__":
    unittest.main()
