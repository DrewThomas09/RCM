"""Tests for the data-package loaders + YAML writer in core/calibration.

`rcm_mc/core/calibration.py` exposes 3 public-facing entry points
that load diligence data packages from filesystem directories or
write calibration config back to YAML:

  - load_data_package(data_dir) — auto-detect + load 3 CSV/Excel
    files (claims_summary, denials, ar_aging) by filename pattern
  - load_multiple_data_dirs(dirs) — load + concatenate from N dirs
  - write_yaml(cfg, path) — yaml.safe_dump with mkdir-as-needed

All 3 had no direct test coverage. These tests use tempdirs +
synthetic CSV fixtures to lock the filename-pattern discovery,
the multi-dir concatenation, and the YAML writer's path-creating
behavior.
"""
from __future__ import annotations

import os
import tempfile
import unittest

import pandas as pd
import yaml

from rcm_mc.core.calibration import (
    CalibrationError,
    DataPackage,
    DataQualityReport,
    load_data_package,
    load_multiple_data_dirs,
    write_yaml,
)


def _write_csv(path: str, data) -> None:
    pd.DataFrame(data).to_csv(path, index=False)


class LoadDataPackageTests(unittest.TestCase):
    """Contract for ``load_data_package``."""

    def test_empty_data_dir_arg_raises(self):
        with self.assertRaises(CalibrationError):
            load_data_package("")

    def test_nonexistent_dir_raises(self):
        with self.assertRaises(CalibrationError):
            load_data_package("/path/that/does/not/exist/here")

    def test_empty_dir_returns_none_dataframes(self):
        with tempfile.TemporaryDirectory() as tmp:
            pkg = load_data_package(tmp)
            self.assertIsInstance(pkg, DataPackage)
            self.assertIsNone(pkg.claims_summary)
            self.assertIsNone(pkg.denials)
            self.assertIsNone(pkg.ar_aging)
            self.assertIsInstance(pkg.quality, DataQualityReport)

    def test_loads_claims_summary_by_filename_pattern(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write_csv(os.path.join(tmp, "claims_summary.csv"), [
                {"month": "2024-01", "revenue": 1_000_000,
                 "claims": 5000},
                {"month": "2024-02", "revenue": 1_100_000,
                 "claims": 5500},
            ])
            pkg = load_data_package(tmp)
            self.assertIsNotNone(pkg.claims_summary)
            self.assertEqual(len(pkg.claims_summary), 2)

    def test_loads_all_three_files_when_present(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write_csv(os.path.join(tmp, "claims_summary.csv"),
                       [{"x": 1}, {"x": 2}])
            _write_csv(os.path.join(tmp, "denials.csv"),
                       [{"y": 3}, {"y": 4}, {"y": 5}])
            _write_csv(os.path.join(tmp, "ar_aging.csv"),
                       [{"z": 6}])
            pkg = load_data_package(tmp)
            self.assertEqual(len(pkg.claims_summary), 2)
            self.assertEqual(len(pkg.denials), 3)
            self.assertEqual(len(pkg.ar_aging), 1)

    def test_finds_files_by_alternate_base_names(self):
        # 'claims' (without _summary) is an accepted alias.
        with tempfile.TemporaryDirectory() as tmp:
            _write_csv(os.path.join(tmp, "claims.csv"),
                       [{"x": 1}])
            pkg = load_data_package(tmp)
            self.assertIsNotNone(pkg.claims_summary)

    def test_populates_quality_row_and_null_counts(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write_csv(os.path.join(tmp, "claims_summary.csv"), [
                {"month": "Jan", "revenue": 100, "claims": 5},
                {"month": "Feb", "revenue": None, "claims": 7},
                {"month": "Mar", "revenue": 200, "claims": None},
            ])
            pkg = load_data_package(tmp)
            self.assertEqual(pkg.quality.row_counts["claims_summary"],
                              3)
            null_counts = pkg.quality.null_counts["claims_summary"]
            self.assertEqual(null_counts["revenue"], 1)
            self.assertEqual(null_counts["claims"], 1)
            self.assertEqual(null_counts["month"], 0)

    def test_shared_quality_report_accumulates_across_calls(self):
        # When the caller passes an explicit DataQualityReport,
        # both calls write into the same dict.
        quality = DataQualityReport()
        with tempfile.TemporaryDirectory() as tmp:
            _write_csv(os.path.join(tmp, "claims_summary.csv"),
                       [{"x": 1}])
            load_data_package(tmp, quality=quality)
        with tempfile.TemporaryDirectory() as tmp:
            _write_csv(os.path.join(tmp, "denials.csv"),
                       [{"y": 1}, {"y": 2}])
            load_data_package(tmp, quality=quality)
        self.assertEqual(quality.row_counts["claims_summary"], 1)
        self.assertEqual(quality.row_counts["denials"], 2)


class LoadMultipleDataDirsTests(unittest.TestCase):
    """Contract for ``load_multiple_data_dirs``."""

    def test_concatenates_claims_across_dirs(self):
        # Two dirs, each with a claims file → merged result has
        # the sum of rows.
        with tempfile.TemporaryDirectory() as t1, \
                tempfile.TemporaryDirectory() as t2:
            _write_csv(os.path.join(t1, "claims_summary.csv"),
                       [{"x": 1}, {"x": 2}])
            _write_csv(os.path.join(t2, "claims_summary.csv"),
                       [{"x": 3}, {"x": 4}, {"x": 5}])
            pkg = load_multiple_data_dirs([t1, t2])
            self.assertEqual(len(pkg.claims_summary), 5)

    def test_handles_missing_files_in_one_dir(self):
        # One dir has claims only, another has denials only →
        # merged package has both.
        with tempfile.TemporaryDirectory() as t1, \
                tempfile.TemporaryDirectory() as t2:
            _write_csv(os.path.join(t1, "claims_summary.csv"),
                       [{"x": 1}])
            _write_csv(os.path.join(t2, "denials.csv"),
                       [{"y": 2}])
            pkg = load_multiple_data_dirs([t1, t2])
            self.assertIsNotNone(pkg.claims_summary)
            self.assertIsNotNone(pkg.denials)
            self.assertIsNone(pkg.ar_aging)

    def test_strips_whitespace_from_dir_strings(self):
        # The function strips each dir string (defensive against
        # CSV-of-paths config inputs with leading whitespace).
        with tempfile.TemporaryDirectory() as t1:
            _write_csv(os.path.join(t1, "claims_summary.csv"),
                       [{"x": 1}])
            pkg = load_multiple_data_dirs(["  " + t1 + "  "])
            self.assertIsNotNone(pkg.claims_summary)

    def test_empty_list_returns_all_none(self):
        pkg = load_multiple_data_dirs([])
        self.assertIsInstance(pkg, DataPackage)
        self.assertIsNone(pkg.claims_summary)
        self.assertIsNone(pkg.denials)
        self.assertIsNone(pkg.ar_aging)

    def test_quality_report_accumulates(self):
        with tempfile.TemporaryDirectory() as t1, \
                tempfile.TemporaryDirectory() as t2:
            _write_csv(os.path.join(t1, "claims_summary.csv"),
                       [{"x": 1}])
            _write_csv(os.path.join(t2, "claims_summary.csv"),
                       [{"x": 2}, {"x": 3}])
            pkg = load_multiple_data_dirs([t1, t2])
            # Quality dict was overwritten with the LAST load's
            # row counts (this is the documented behavior — both
            # writes use the same key "claims_summary"). Verify
            # the final value matches the second dir.
            self.assertEqual(
                pkg.quality.row_counts["claims_summary"], 2)


class WriteYamlTests(unittest.TestCase):
    """Contract for ``write_yaml``."""

    def test_writes_round_trip(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "out.yaml")
            cfg = {"a": 1, "b": [2, 3], "c": {"nested": "x"}}
            write_yaml(cfg, path)
            self.assertTrue(os.path.isfile(path))
            with open(path) as f:
                loaded = yaml.safe_load(f)
            self.assertEqual(loaded, cfg)

    def test_creates_missing_parent_dirs(self):
        with tempfile.TemporaryDirectory() as tmp:
            # Nested dir that doesn't exist yet.
            path = os.path.join(tmp, "a", "b", "c", "out.yaml")
            cfg = {"k": "v"}
            # Must not raise — mkdir is part of the function's
            # contract.
            write_yaml(cfg, path)
            self.assertTrue(os.path.isfile(path))

    def test_preserves_key_order_not_sorted(self):
        # sort_keys=False so insertion order is preserved.
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "out.yaml")
            # Use an ordered key sequence the alphabetic sort
            # would change.
            cfg = {"z_first": 1, "a_second": 2, "m_third": 3}
            write_yaml(cfg, path)
            with open(path) as f:
                lines = f.read().splitlines()
            # First non-blank line starts with 'z_first'.
            self.assertTrue(lines[0].startswith("z_first"))

    def test_empty_dir_in_path_safe(self):
        # Path with no directory component (just filename) → the
        # os.makedirs(... or '.') guard kicks in.
        with tempfile.TemporaryDirectory() as tmp:
            old_cwd = os.getcwd()
            try:
                os.chdir(tmp)
                write_yaml({"k": "v"}, "out.yaml")
                self.assertTrue(os.path.isfile("out.yaml"))
            finally:
                os.chdir(old_cwd)


if __name__ == "__main__":
    unittest.main()
