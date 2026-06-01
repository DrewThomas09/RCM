"""Tests for the pure helpers in ``rcm_mc/reports/_report_helpers.py``.

Module supplies the HTML formatting helpers used by ``html_report.py``
to assemble the partner-facing diligence packet. Heavier builders
(``_build_benchmark_gap_table``, ``_build_provenance_methodology_section``)
go through file-system + module-level reference dicts and are
covered indirectly by the html_report integration suite; this file
covers the **pure helpers** that had no direct unit-test coverage:

  * ``_extract_payer_params`` — cfg dict → flat payer/metric mapping
  * ``_read_csv_if_exists`` — silent-None on missing path
  * ``_img_tag`` — file-or-fallback base64 image embedding
  * ``_fmt_metric_row`` — summary-row HTML formatter
  * ``_format_money_cols`` — selective $-formatting for display tables
  * ``_BENCHMARK_REFERENCES`` — the partner-visible benchmark dict

Each helper is partner-visible (lands in the packet) so locking the
contract before any tweak is worth doing.
"""
from __future__ import annotations

import base64
import os
import tempfile
import unittest

import numpy as np
import pandas as pd

from rcm_mc.reports._report_helpers import (
    _BENCHMARK_REFERENCES,
    _extract_payer_params,
    _fmt_metric_row,
    _format_money_cols,
    _img_tag,
    _read_csv_if_exists,
)


# ---------------------------------------------------------------------------
# _extract_payer_params
# ---------------------------------------------------------------------------


class ExtractPayerParamsTests(unittest.TestCase):

    def test_empty_cfg_returns_empty_dict(self):
        self.assertEqual(_extract_payer_params({}), {})

    def test_missing_payers_key_returns_empty(self):
        self.assertEqual(_extract_payer_params({"appeals": {}}), {})

    def test_null_payers_returns_empty(self):
        # 'or {}' guard means None payers → empty.
        self.assertEqual(_extract_payer_params({"payers": None}), {})

    def test_extracts_idr_fwr_when_denials_present(self):
        cfg = {"payers": {"Medicare": {
            "denials": {
                "idr": {"mean": 0.12},
                "fwr": {"mean": 0.03},
            },
            "dar_clean_days": {"mean": 32},
        }}}
        out = _extract_payer_params(cfg)
        self.assertIn("Medicare", out)
        self.assertEqual(out["Medicare"]["idr"], 0.12)
        self.assertEqual(out["Medicare"]["fwr"], 0.03)
        self.assertEqual(out["Medicare"]["dar"], 32.0)

    def test_skips_payer_with_no_extractable_params(self):
        # Payer with no recognizable dict-with-mean inputs → omitted
        # (so report rows don't appear for payers with no data).
        cfg = {"payers": {
            "Mystery": {"denials": None},  # no extractable mean
        }}
        out = _extract_payer_params(cfg)
        self.assertNotIn("Mystery", out)

    def test_falsy_denials_dict_skipped(self):
        # denials={} (empty dict, falsy) → skipped
        cfg = {"payers": {"X": {"denials": {}}}}
        out = _extract_payer_params(cfg)
        self.assertNotIn("X", out)

    def test_missing_idr_or_fwr_just_drops_that_key(self):
        cfg = {"payers": {"X": {
            "denials": {"idr": {"mean": 0.10}},  # no fwr
        }}}
        out = _extract_payer_params(cfg)
        # X is included because idr was extracted.
        self.assertIn("X", out)
        self.assertIn("idr", out["X"])
        self.assertNotIn("fwr", out["X"])

    def test_dar_not_dict_skipped(self):
        # dar_clean_days could be a flat float — must be dict-with-mean.
        cfg = {"payers": {"X": {
            "denials": {"idr": {"mean": 0.10}},
            "dar_clean_days": 32,  # raw int — not a dist spec
        }}}
        out = _extract_payer_params(cfg)
        self.assertIn("idr", out["X"])
        self.assertNotIn("dar", out["X"])

    def test_dar_dict_without_mean_skipped(self):
        cfg = {"payers": {"X": {
            "denials": {"idr": {"mean": 0.10}},
            "dar_clean_days": {"dist": "triangular", "low": 30},
        }}}
        out = _extract_payer_params(cfg)
        self.assertNotIn("dar", out["X"])

    def test_idr_value_coerced_to_float(self):
        # If idr.mean is an int, coerced to float
        cfg = {"payers": {"X": {
            "denials": {"idr": {"mean": 1}},
        }}}
        out = _extract_payer_params(cfg)
        self.assertIsInstance(out["X"]["idr"], float)


# ---------------------------------------------------------------------------
# _read_csv_if_exists
# ---------------------------------------------------------------------------


class ReadCsvIfExistsTests(unittest.TestCase):

    def test_missing_path_returns_none(self):
        self.assertIsNone(_read_csv_if_exists("/nope/does-not-exist.csv"))

    def test_existing_path_returns_dataframe(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = os.path.join(tmp, "x.csv")
            pd.DataFrame({"a": [1, 2], "b": [3, 4]}).to_csv(p, index=False)
            df = _read_csv_if_exists(p)
            self.assertIsNotNone(df)
            self.assertEqual(len(df), 2)
            self.assertListEqual(list(df.columns), ["a", "b"])

    def test_kwargs_passed_through(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = os.path.join(tmp, "x.csv")
            with open(p, "w") as f:
                f.write("a|b\n1|2\n3|4\n")
            df = _read_csv_if_exists(p, sep="|")
            self.assertIsNotNone(df)
            self.assertListEqual(list(df.columns), ["a", "b"])


# ---------------------------------------------------------------------------
# _img_tag
# ---------------------------------------------------------------------------


class ImgTagTests(unittest.TestCase):

    def test_missing_path_returns_fallback_paragraph(self):
        out = _img_tag("/nope/missing.png", alt="missing chart")
        self.assertIn("Image not available", out)
        self.assertIn("missing chart", out)
        self.assertTrue(out.startswith("<p>"))

    def test_existing_png_returns_base64_data_uri(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = os.path.join(tmp, "x.png")
            with open(p, "wb") as f:
                f.write(b"\x89PNG\r\n\x1a\nfake-png-body")
            out = _img_tag(p, alt="chart")
            self.assertIn("data:image/png;base64,", out)
            # Decoded payload matches what we wrote.
            payload = out.split("base64,")[1].split("'")[0]
            decoded = base64.b64decode(payload)
            self.assertEqual(decoded, b"\x89PNG\r\n\x1a\nfake-png-body")

    def test_jpg_uses_image_jpeg_mime(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = os.path.join(tmp, "x.jpg")
            with open(p, "wb") as f:
                f.write(b"\xff\xd8\xff\xe0fake-jpeg")
            out = _img_tag(p, alt="chart")
            self.assertIn("data:image/jpeg;base64,", out)

    def test_alt_text_appears(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = os.path.join(tmp, "x.png")
            with open(p, "wb") as f:
                f.write(b"\x89PNG")
            out = _img_tag(p, alt="Risk/Reward chart")
            self.assertIn("alt='Risk/Reward chart'", out)


# ---------------------------------------------------------------------------
# _fmt_metric_row
# ---------------------------------------------------------------------------


class FmtMetricRowTests(unittest.TestCase):

    def _row(self, mean: float, p10: float, p90: float) -> pd.Series:
        return pd.Series({"mean": mean, "p10": p10, "p90": p90})

    def test_dar_metric_formats_as_days(self):
        # Any metric name containing 'dar' uses days suffix (not $).
        out = _fmt_metric_row("drag_dar_total", self._row(45.5, 30.5, 60.5))
        self.assertIn("45.5 days", out)
        self.assertIn("30.5 days", out)
        self.assertIn("60.5 days", out)
        # No $ formatting on DAR metrics.
        self.assertNotIn("$", out)

    def test_non_dar_metric_formats_as_money(self):
        out = _fmt_metric_row("ebitda_drag", self._row(5_000_000, 3_000_000, 7_500_000))
        # Goes through reporting.pretty_money
        self.assertIn("$5.0M", out)
        self.assertIn("$3.0M", out)
        self.assertIn("$7.5M", out)

    def test_renders_table_row(self):
        out = _fmt_metric_row("ebitda_drag", self._row(1, 1, 1))
        self.assertTrue(out.startswith("<tr>"))
        self.assertTrue(out.endswith("</tr>"))
        # 4 cells: label + mean + p10 + p90
        self.assertEqual(out.count("<td"), 4)

    def test_uses_metric_label_when_known(self):
        # METRIC_LABELS has 'ebitda_drag' → 'Total EBITDA Drag'
        out = _fmt_metric_row("ebitda_drag", self._row(1, 1, 1))
        self.assertIn("Total EBITDA Drag", out)

    def test_falls_back_to_title_case_for_unknown_metric(self):
        # Unknown metric → underscore replace + title case
        out = _fmt_metric_row("some_new_metric", self._row(1, 1, 1))
        self.assertIn("Some New Metric", out)


# ---------------------------------------------------------------------------
# _format_money_cols
# ---------------------------------------------------------------------------


class FormatMoneyColsTests(unittest.TestCase):

    def test_formats_listed_columns_only(self):
        df = pd.DataFrame({"amount": [1_500_000, 2_000_000],
                            "count": [5, 10]})
        out = _format_money_cols(df, ["amount"])
        # amount formatted as money strings.
        self.assertEqual(out["amount"].iloc[0], "$1.5M")
        # count untouched.
        self.assertEqual(out["count"].iloc[0], 5)

    def test_returns_copy_not_mutated_original(self):
        df = pd.DataFrame({"amount": [1_000_000]})
        out = _format_money_cols(df, ["amount"])
        # Original df still holds raw numeric.
        self.assertEqual(df["amount"].iloc[0], 1_000_000)
        # Returned df holds formatted string.
        self.assertEqual(out["amount"].iloc[0], "$1.0M")

    def test_missing_column_silently_skipped(self):
        # Asking to format a column that isn't present → no crash.
        df = pd.DataFrame({"amount": [1_000_000]})
        out = _format_money_cols(df, ["amount", "missing"])
        self.assertEqual(out["amount"].iloc[0], "$1.0M")
        self.assertNotIn("missing", out.columns)

    def test_nan_becomes_empty_string(self):
        df = pd.DataFrame({"amount": [1_000_000, float("nan")]})
        out = _format_money_cols(df, ["amount"])
        self.assertEqual(out["amount"].iloc[1], "")

    def test_small_values_use_two_decimal_fallback(self):
        # |x| < 1 → 2-decimal format (multipliers, ratios live in
        # money cols sometimes).
        df = pd.DataFrame({"amount": [0.12, 0.99]})
        out = _format_money_cols(df, ["amount"])
        self.assertEqual(out["amount"].iloc[0], "0.12")
        self.assertEqual(out["amount"].iloc[1], "0.99")


# ---------------------------------------------------------------------------
# _BENCHMARK_REFERENCES
# ---------------------------------------------------------------------------


class BenchmarkReferencesTests(unittest.TestCase):
    """Partner-visible HFMA/AHA/Kodiak/Fierce reference values.
    Changes here ship straight into the benchmark gap table — lock
    the keys + structure so a future refactor can't silently drop
    a row from the partner brief."""

    REQUIRED_KEYS = (
        "idr_commercial", "idr_ma", "idr_medicaid", "idr_medicare_ffs",
        "fwr_npsr", "dar_days", "ctc_pct", "ar_over_90",
    )

    def test_all_required_keys_present(self):
        for k in self.REQUIRED_KEYS:
            self.assertIn(k, _BENCHMARK_REFERENCES, f"missing key {k}")

    def test_each_reference_has_source(self):
        # Every benchmark must cite a source — the partner brief
        # always shows the citation column.
        for k, ref in _BENCHMARK_REFERENCES.items():
            self.assertIn("source", ref, f"{k} missing source")
            self.assertTrue(ref["source"], f"{k} source is empty")

    def test_each_reference_has_industry_avg(self):
        for k, ref in _BENCHMARK_REFERENCES.items():
            self.assertIn("industry_avg", ref, f"{k} missing industry_avg")


if __name__ == "__main__":
    unittest.main()
