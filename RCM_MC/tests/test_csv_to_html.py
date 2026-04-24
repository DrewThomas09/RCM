"""Tests for CSV → HTML table renderer (UI-7)."""
from __future__ import annotations

import csv
import os
import tempfile
import unittest

from rcm_mc.ui.csv_to_html import (
    _pick_formatter,
    render_csv,
    wrap_csvs_in_folder,
)


def _write_csv(path: str, headers, rows):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(headers)
        for r in rows:
            w.writerow(r)


class TestFormatterPicker(unittest.TestCase):
    def test_pct_suffix_triggers_pct_formatter(self):
        fn = _pick_formatter("medicare_day_pct")
        self.assertIsNotNone(fn)
        self.assertEqual(fn("0.225"), "22.5%")

    def test_moic_col_triggers_multi(self):
        fn = _pick_formatter("moic")
        self.assertEqual(fn("2.55"), "2.55x")

    def test_revenue_col_triggers_money(self):
        fn = _pick_formatter("net_patient_revenue")
        self.assertEqual(fn("5000000"), "$5.0M")

    def test_beds_triggers_int(self):
        fn = _pick_formatter("beds")
        self.assertEqual(fn("1326"), "1,326")

    def test_unknown_column_no_formatter(self):
        self.assertIsNone(_pick_formatter("random_col"))


class TestRenderCsv(unittest.TestCase):
    def test_renders_complete_html_document(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "peers.csv")
            _write_csv(
                path,
                ["ccn", "name", "beds", "net_patient_revenue"],
                [
                    ["360180", "Cleveland Clinic", "1326", "6378833101"],
                    ["220071", "MGH", "997", "3500000000"],
                ],
            )
            doc = render_csv(path, title="Peers")
            self.assertIn("<!doctype html>", doc.lower())
            self.assertIn("Peers", doc)
            # Money column formatted
            self.assertIn("$6.38B", doc)
            # Int column formatted with thousands
            self.assertIn("1,326", doc)

    def test_numeric_polish_applied(self):
        """UI-1 post-polish must mark numeric cells with class=num."""
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "x.csv")
            _write_csv(path, ["label", "revenue"], [["A", "1000000"]])
            doc = render_csv(path)
            self.assertIn('class="num"', doc)

    def test_max_rows_returns_none_above_threshold(self):
        """Simulation dumps (5k+ rows) must not render — we'd OOM the browser."""
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "big.csv")
            _write_csv(path, ["x"], [[str(i)] for i in range(600)])
            doc = render_csv(path, max_rows=500)
            self.assertIsNone(doc)

    def test_empty_csv_returns_none(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "empty.csv")
            open(path, "w").close()
            self.assertIsNone(render_csv(path))

    def test_sortable_header_markup(self):
        """Each header carries the sort arrow + click handler hook."""
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "x.csv")
            _write_csv(path, ["a", "b"], [["1", "2"]])
            doc = render_csv(path)
            self.assertIn("arrow", doc)
            # Vanilla JS sort handler present
            self.assertIn("addEventListener", doc)

    def test_headers_are_keyboard_sortable_and_semantic(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "x.csv")
            _write_csv(path, ["revenue"], [["1000000"]])
            doc = render_csv(path, title="Revenue Table")
            self.assertIn('<caption class="sr-only">Revenue Table.', doc)
            self.assertIn('scope="col"', doc)
            self.assertIn('class="sort-btn"', doc)
            self.assertIn('aria-sort="none"', doc)
            self.assertIn('data-col-idx="0"', doc)

    def test_back_breadcrumb_present(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "x.csv")
            _write_csv(path, ["a"], [["1"]])
            doc = render_csv(path, back_href="../index.html")
            self.assertIn("../index.html", doc)
            self.assertIn("Back to index", doc)

    def test_html_escapes_cell_content(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "x.csv")
            _write_csv(path, ["a"], [["<script>alert(1)</script>"]])
            doc = render_csv(path)
            self.assertNotIn("<script>alert", doc)
            self.assertIn("&lt;script&gt;", doc)


class TestWrapCsvsInFolder(unittest.TestCase):
    def test_wraps_short_csvs(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write_csv(os.path.join(tmp, "a.csv"), ["x"], [["1"], ["2"]])
            _write_csv(os.path.join(tmp, "b.csv"), ["y"], [["3"]])
            written = wrap_csvs_in_folder(tmp)
            names = sorted(os.path.basename(p) for p in written)
            self.assertEqual(names, ["a.html", "b.html"])

    def test_skips_csvs_above_threshold(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write_csv(os.path.join(tmp, "big.csv"),
                       ["x"], [[str(i)] for i in range(600)])
            self.assertEqual(wrap_csvs_in_folder(tmp, max_rows=500), [])

    def test_preserves_existing_html(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write_csv(os.path.join(tmp, "a.csv"), ["x"], [["1"]])
            with open(os.path.join(tmp, "a.html"), "w") as f:
                f.write("<!-- hand -->")
            wrap_csvs_in_folder(tmp)
            with open(os.path.join(tmp, "a.html")) as f:
                self.assertIn("hand", f.read())

    def test_nonexistent_folder_returns_empty(self):
        self.assertEqual(wrap_csvs_in_folder("/nonexistent"), [])
