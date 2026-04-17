"""Tests for ``rcm-mc ingest`` — messy-data → calibration-ready directory."""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

import pandas as pd

from rcm_mc.data.ingest import (
    IngestReport,
    classify_dataframe,
    ingest_path,
    load_source,
    main as ingest_main,
)


BASE_DIR = Path(__file__).resolve().parents[1]


# ── Fixtures ─────────────────────────────────────────────────────────────

def _claims_df() -> pd.DataFrame:
    return pd.DataFrame({
        "payer":        ["Medicare", "Medicaid", "Commercial", "SelfPay"],
        "net_revenue":  [1.5e8, 8e7, 2.2e8, 2e7],
        "claim_count":  [15000, 9000, 22000, 3000],
    })


def _denials_df() -> pd.DataFrame:
    return pd.DataFrame({
        "claim_id":       ["A1", "A2", "A3", "A4"],
        "payer":          ["Medicare", "Commercial", "Commercial", "Medicaid"],
        "denial_amount":  [1500, 3200, 2800, 900],
        "stage":          ["L1", "L2", "L1", "L1"],
        "denial_reason":  ["auth", "coding", "timely", "elig"],
        "writeoff_amount": [500, 0, 0, 900],
    })


def _ar_df() -> pd.DataFrame:
    return pd.DataFrame({
        "payer":     ["Medicare", "Medicaid", "Commercial"],
        "ar_amount": [1.2e7, 6e6, 1.8e7],
    })


# ── Classification ────────────────────────────────────────────────────────

class TestClassifyDataframe(unittest.TestCase):
    def test_claims_signature(self):
        kind, m = classify_dataframe(_claims_df())
        self.assertEqual(kind, "claims_summary")
        self.assertIn("payer", m)
        self.assertIn("net_revenue", m)

    def test_denials_signature(self):
        kind, m = classify_dataframe(_denials_df())
        self.assertEqual(kind, "denials")
        self.assertEqual(m["denial_amount"], "denial_amount")

    def test_ar_aging_signature(self):
        kind, _ = classify_dataframe(_ar_df())
        self.assertEqual(kind, "ar_aging")

    def test_unknown_returns_empty(self):
        kind, m = classify_dataframe(pd.DataFrame({"x": [1], "y": [2]}))
        self.assertEqual(kind, "unknown")
        self.assertEqual(m, {})

    def test_empty_dataframe_returns_unknown(self):
        self.assertEqual(classify_dataframe(pd.DataFrame())[0], "unknown")

    def test_aliased_column_names_match(self):
        """'payor_name' (seller variant) should resolve to 'payer'."""
        df = pd.DataFrame({"payor_name": ["Medicare"], "revenue": [1e6]})
        kind, m = classify_dataframe(df)
        self.assertEqual(kind, "claims_summary")
        self.assertEqual(m["payer"], "payor_name")


# ── Source loader ────────────────────────────────────────────────────────

class TestLoadSource(unittest.TestCase):
    def test_single_csv(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            _claims_df().to_csv(path, index=False)
            tables = list(load_source(path))
            self.assertEqual(len(tables), 1)
            self.assertEqual(tables[0][0], "claims.csv")

    def test_folder_recurses(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)
            _claims_df().to_csv(p / "claims.csv", index=False)
            _denials_df().to_csv(p / "denials.csv", index=False)
            tables = list(load_source(p))
            self.assertEqual(len(tables), 2)

    def test_multi_sheet_excel(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "pack.xlsx"
            with pd.ExcelWriter(path, engine="openpyxl") as xw:
                _claims_df().to_excel(xw, sheet_name="Claims", index=False)
                _denials_df().to_excel(xw, sheet_name="Denials", index=False)
                _ar_df().to_excel(xw, sheet_name="AR Aging", index=False)
            tables = list(load_source(path))
            self.assertEqual(len(tables), 3)
            labels = [t[0] for t in tables]
            self.assertTrue(all(":" in lbl for lbl in labels),
                            msg=f"Excel labels should include sheet name: {labels}")

    def test_zip_extracts_and_recurses(self):
        with tempfile.TemporaryDirectory() as tmp:
            # Build a zip with a claims CSV inside a subfolder
            p = Path(tmp)
            subdir = p / "data"
            subdir.mkdir()
            _claims_df().to_csv(subdir / "claims.csv", index=False)
            _denials_df().to_csv(subdir / "denials.csv", index=False)
            zip_path = p / "pack.zip"
            with zipfile.ZipFile(zip_path, "w") as zf:
                for f in subdir.iterdir():
                    zf.write(f, arcname=f"data/{f.name}")
            tables = list(load_source(zip_path))
            self.assertEqual(len(tables), 2)

    def test_nonexistent_path_yields_nothing(self):
        self.assertEqual(list(load_source(Path("/nonexistent/path.csv"))), [])


# ── End-to-end ingest_path ───────────────────────────────────────────────

class TestIngestPath(unittest.TestCase):
    def test_writes_canonical_csvs(self):
        with tempfile.TemporaryDirectory() as tmp_src, tempfile.TemporaryDirectory() as tmp_out:
            _claims_df().to_csv(Path(tmp_src) / "claims.csv", index=False)
            _denials_df().to_csv(Path(tmp_src) / "denials_q1.csv", index=False)
            _ar_df().to_csv(Path(tmp_src) / "aging.csv", index=False)
            report = ingest_path(tmp_src, tmp_out)
            self.assertTrue(os.path.exists(os.path.join(tmp_out, "claims_summary.csv")))
            self.assertTrue(os.path.exists(os.path.join(tmp_out, "denials.csv")))
            self.assertTrue(os.path.exists(os.path.join(tmp_out, "ar_aging.csv")))
            self.assertEqual(report.classified_count, 3)

    def test_concatenates_multiple_tables_of_same_kind(self):
        """Two denials CSVs should be row-concatenated into one canonical file."""
        with tempfile.TemporaryDirectory() as tmp_src, tempfile.TemporaryDirectory() as tmp_out:
            _denials_df().to_csv(Path(tmp_src) / "denials_q1.csv", index=False)
            _denials_df().to_csv(Path(tmp_src) / "denials_q2.csv", index=False)
            ingest_path(tmp_src, tmp_out)
            merged = pd.read_csv(os.path.join(tmp_out, "denials.csv"))
            self.assertEqual(len(merged), 2 * len(_denials_df()))

    def test_unknown_tables_recorded_not_written(self):
        with tempfile.TemporaryDirectory() as tmp_src, tempfile.TemporaryDirectory() as tmp_out:
            pd.DataFrame({"foo": [1], "bar": [2]}).to_csv(
                Path(tmp_src) / "mystery.csv", index=False,
            )
            report = ingest_path(tmp_src, tmp_out)
            # No canonical CSVs written
            self.assertEqual(report.output_files, {})
            # But the mystery table IS in the detected list (kind='unknown')
            unknowns = [t for t in report.detected if t.kind == "unknown"]
            self.assertEqual(len(unknowns), 1)

    def test_report_markdown_includes_sections(self):
        with tempfile.TemporaryDirectory() as tmp_src, tempfile.TemporaryDirectory() as tmp_out:
            _claims_df().to_csv(Path(tmp_src) / "claims.csv", index=False)
            ingest_path(tmp_src, tmp_out)
            md = (Path(tmp_out) / "data_intake_report.md").read_text()
            self.assertIn("# Data Intake Report", md)
            self.assertIn("Canonical files written", md)
            self.assertIn("Detected tables", md)
            self.assertIn("claims_summary", md)

    def test_excel_pack_round_trips(self):
        """Multi-sheet Excel → ingest → 3 canonical CSVs."""
        with tempfile.TemporaryDirectory() as tmp_src, tempfile.TemporaryDirectory() as tmp_out:
            path = Path(tmp_src) / "pack.xlsx"
            with pd.ExcelWriter(path, engine="openpyxl") as xw:
                _claims_df().to_excel(xw, sheet_name="Claims Summary", index=False)
                _denials_df().to_excel(xw, sheet_name="Denials Detail", index=False)
                _ar_df().to_excel(xw, sheet_name="AR Aging by Payer", index=False)
            ingest_path(str(path), tmp_out)
            for kind in ("claims_summary", "denials", "ar_aging"):
                self.assertTrue(
                    os.path.exists(os.path.join(tmp_out, f"{kind}.csv")),
                    msg=f"Missing {kind}.csv",
                )


class TestIngestCalibrateIntegration(unittest.TestCase):
    """Round-trip: ingest output is directly consumable by calibrate_config."""

    def test_ingested_dir_works_with_calibration(self):
        from rcm_mc.core.calibration import calibrate_config
        from rcm_mc.infra.config import load_and_validate

        with tempfile.TemporaryDirectory() as tmp_src, tempfile.TemporaryDirectory() as tmp_out:
            # Source: raw alias'd column names (what a seller hands over)
            pd.DataFrame({
                "payor_name":  ["Medicare", "Medicaid", "Commercial", "SelfPay"],
                "revenue":     [1.5e8, 8e7, 2.2e8, 2e7],
                "claim_count": [15000, 9000, 22000, 3000],
            }).to_csv(Path(tmp_src) / "claims.csv", index=False)
            _denials_df().to_csv(Path(tmp_src) / "denials.csv", index=False)
            _ar_df().to_csv(Path(tmp_src) / "aging.csv", index=False)

            ingest_path(tmp_src, tmp_out)
            # Now calibrate_config should consume the ingested dir
            cfg = load_and_validate(str(BASE_DIR / "configs" / "actual.yaml"))
            calibrated, report, quality = calibrate_config(cfg, tmp_out)
            # Report has per-payer rows (Medicare, Medicaid, Commercial, SelfPay)
            self.assertGreaterEqual(len(report), 3)


class TestIngestCLI(unittest.TestCase):
    def test_help_exits_zero(self):
        env = os.environ.copy()
        env.setdefault("MPLCONFIGDIR", "/tmp/mplcache")
        result = subprocess.run(
            [sys.executable, "-m", "rcm_mc", "ingest", "--help"],
            cwd=str(BASE_DIR), env=env,
            capture_output=True, text=True, timeout=30,
        )
        self.assertEqual(result.returncode, 0)
        # prog parameterization: subcommand help shows unified name
        self.assertIn("rcm-mc ingest", result.stdout)

    def test_missing_source_returns_2(self):
        rc = ingest_main(["/nonexistent", "--out", "/tmp/should-not-exist"])
        self.assertEqual(rc, 2)

    def test_end_to_end_via_cli(self):
        env = os.environ.copy()
        env.setdefault("MPLCONFIGDIR", "/tmp/mplcache")
        with tempfile.TemporaryDirectory() as tmp_src, tempfile.TemporaryDirectory() as tmp_out:
            _claims_df().to_csv(Path(tmp_src) / "claims.csv", index=False)
            _denials_df().to_csv(Path(tmp_src) / "denials.csv", index=False)
            _ar_df().to_csv(Path(tmp_src) / "aging.csv", index=False)
            result = subprocess.run(
                [sys.executable, "-m", "rcm_mc", "ingest", tmp_src, "--out", tmp_out, "-q"],
                cwd=str(BASE_DIR), env=env,
                capture_output=True, text=True, timeout=60,
            )
            self.assertEqual(
                result.returncode, 0,
                msg=f"STDOUT:{result.stdout}\nSTDERR:{result.stderr}",
            )
            for kind in ("claims_summary", "denials", "ar_aging"):
                self.assertTrue(os.path.exists(os.path.join(tmp_out, f"{kind}.csv")))
