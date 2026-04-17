"""Tests for auto-generated output folder index (UI-4)."""
from __future__ import annotations

import os
import tempfile
import unittest

from rcm_mc.infra.output_index import (
    _describe,
    _fmt_size,
    _kind,
    build_indices_recursive,
    build_output_index,
)


def _touch(path: str, content: str = "") -> None:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w") as f:
        f.write(content)


def _read_text(path: str) -> str:
    with open(path) as f:
        return f.read()


class TestKindAndDescribe(unittest.TestCase):
    def test_known_file_descriptions(self):
        self.assertIn("audit-grade", _describe("report.html"))
        self.assertIn("workbook", _describe("diligence_workbook.xlsx"))
        self.assertIn("bridge", _describe("pe_bridge.json"))

    def test_unknown_file_gets_extension_fallback(self):
        self.assertIn("CSV", _describe("weird_file.csv"))
        self.assertIn("JSON", _describe("random.json"))

    def test_kind_by_extension(self):
        self.assertEqual(_kind("foo.html"), "HTML")
        self.assertEqual(_kind("foo.xlsx"), "Excel")
        self.assertEqual(_kind("foo.csv"), "CSV")
        self.assertEqual(_kind("foo"), "File")

    def test_size_formatter(self):
        self.assertEqual(_fmt_size(500), "500 B")
        self.assertEqual(_fmt_size(5_000), "5 KB")
        self.assertEqual(_fmt_size(5_000_000), "5.0 MB")


class TestBuildOutputIndex(unittest.TestCase):
    def test_empty_folder_still_writes_index(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = build_output_index(tmp)
            self.assertTrue(os.path.isfile(path))
            html = _read_text(path)
            self.assertIn("<html", html)
            self.assertIn("0 files", html)

    def test_classifies_into_three_groups(self):
        with tempfile.TemporaryDirectory() as tmp:
            _touch(os.path.join(tmp, "report.html"))
            _touch(os.path.join(tmp, "diligence_workbook.xlsx"))
            _touch(os.path.join(tmp, "summary.csv"))
            _touch(os.path.join(tmp, "pe_bridge.json"))
            _touch(os.path.join(tmp, "runs.sqlite"))
            build_output_index(tmp)
            html = _read_text(os.path.join(tmp, "index.html"))
            # Three sections all present
            self.assertIn("Deliverables", html)
            self.assertIn("Data tables", html)
            self.assertIn("Everything else", html)
            # Each file surfaces by name
            for name in ("report.html", "diligence_workbook.xlsx",
                         "summary.csv", "pe_bridge.json", "runs.sqlite"):
                self.assertIn(name, html)

    def test_known_descriptions_rendered(self):
        with tempfile.TemporaryDirectory() as tmp:
            _touch(os.path.join(tmp, "partner_brief.html"))
            build_output_index(tmp)
            html = _read_text(os.path.join(tmp, "index.html"))
            self.assertIn("IC-ready executive brief", html)

    def test_hidden_files_skipped(self):
        with tempfile.TemporaryDirectory() as tmp:
            _touch(os.path.join(tmp, ".DS_Store"))
            _touch(os.path.join(tmp, "__pycache__"))
            _touch(os.path.join(tmp, "_internal.txt"))
            _touch(os.path.join(tmp, "visible.csv"))
            build_output_index(tmp)
            html = _read_text(os.path.join(tmp, "index.html"))
            self.assertNotIn(".DS_Store", html)
            self.assertNotIn("_internal.txt", html)
            self.assertIn("visible.csv", html)

    def test_subfolders_get_folder_cards(self):
        with tempfile.TemporaryDirectory() as tmp:
            sub = os.path.join(tmp, "lookup_data")
            os.makedirs(sub)
            _touch(os.path.join(sub, "peers.csv"))
            _touch(os.path.join(tmp, "report.html"))
            build_output_index(tmp)
            html = _read_text(os.path.join(tmp, "index.html"))
            self.assertIn("Sub-folders", html)
            self.assertIn("lookup_data", html)

    def test_index_links_use_relative_paths(self):
        with tempfile.TemporaryDirectory() as tmp:
            _touch(os.path.join(tmp, "report.html"))
            build_output_index(tmp)
            html = _read_text(os.path.join(tmp, "index.html"))
            # Link is just the filename — no absolute paths leaked
            self.assertIn('href="report.html"', html)
            self.assertNotIn(tmp, html)

    def test_idempotent_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            _touch(os.path.join(tmp, "a.csv"))
            build_output_index(tmp)
            _touch(os.path.join(tmp, "b.csv"))
            build_output_index(tmp)  # re-run
            html = _read_text(os.path.join(tmp, "index.html"))
            self.assertIn("a.csv", html)
            self.assertIn("b.csv", html)

    def test_custom_title(self):
        with tempfile.TemporaryDirectory() as tmp:
            build_output_index(tmp, title="My Deal — Q2 Review")
            html = _read_text(os.path.join(tmp, "index.html"))
            self.assertIn("My Deal — Q2 Review", html)

    def test_txt_hidden_when_html_sibling_exists(self):
        """UI-3 + UI-4 interplay: .txt with matching .html is de-duped out."""
        with tempfile.TemporaryDirectory() as tmp:
            _touch(os.path.join(tmp, "37_remark.txt"), "raw")
            _touch(os.path.join(tmp, "37_remark.html"), "<html></html>")
            _touch(os.path.join(tmp, "lone_txt.txt"), "no companion")
            build_output_index(tmp)
            html = _read_text(os.path.join(tmp, "index.html"))
            self.assertIn("37_remark.html", html)
            self.assertNotIn("37_remark.txt", html)
            # Lone .txt still appears
            self.assertIn("lone_txt.txt", html)

    def test_md_hidden_when_html_sibling_exists(self):
        with tempfile.TemporaryDirectory() as tmp:
            _touch(os.path.join(tmp, "memo.md"))
            _touch(os.path.join(tmp, "memo.html"))
            build_output_index(tmp)
            html = _read_text(os.path.join(tmp, "index.html"))
            self.assertNotIn("memo.md", html)

    def test_index_itself_not_listed(self):
        with tempfile.TemporaryDirectory() as tmp:
            build_output_index(tmp)  # creates index.html
            # Re-run — the prior index.html must not appear as a card
            build_output_index(tmp)
            html = _read_text(os.path.join(tmp, "index.html"))
            # Only reference to index.html should be the <title> / empty
            self.assertEqual(html.count("index.html"), 0)


class TestBuildIndicesRecursive(unittest.TestCase):
    def test_builds_index_in_each_subfolder(self):
        with tempfile.TemporaryDirectory() as tmp:
            _touch(os.path.join(tmp, "report.html"))
            sub = os.path.join(tmp, "_detail")
            os.makedirs(sub)
            _touch(os.path.join(sub, "chart.png"))
            sub2 = os.path.join(tmp, "lookup")
            os.makedirs(sub2)
            _touch(os.path.join(sub2, "peers.csv"))
            paths = build_indices_recursive(tmp)
            # Top + only non-hidden subfolder (_detail is hidden by prefix)
            self.assertIn(os.path.join(tmp, "index.html"), paths)
            self.assertIn(os.path.join(sub2, "index.html"), paths)
            # _detail/ starts with underscore → hidden, no index built
            self.assertNotIn(os.path.join(sub, "index.html"), paths)
