"""Tests for text → HTML wrapper (UI-3)."""
from __future__ import annotations

import os
import tempfile
import unittest

from rcm_mc.ui.text_to_html import (
    _colorize_line,
    _strip_ansi,
    text_to_html,
    wrap_text_file,
    wrap_text_files_in_folder,
)


class TestAnsiStrip(unittest.TestCase):
    def test_strips_color_codes(self):
        colored = "\x1b[32mgreen text\x1b[0m"
        self.assertEqual(_strip_ansi(colored), "green text")

    def test_plain_text_untouched(self):
        self.assertEqual(_strip_ansi("hello world"), "hello world")


class TestColorize(unittest.TestCase):
    def test_wraps_severity_glyphs_in_spans(self):
        out = _colorize_line("  ✓ on track")
        self.assertIn('<span class="ok">✓</span>', out)

    def test_wraps_status_words(self):
        out = _colorize_line("Covenant SAFE")
        self.assertIn('<span class="ok">SAFE</span>', out)

        out2 = _colorize_line("Covenant TRIPPED at 6.2x")
        self.assertIn('<span class="err">TRIPPED</span>', out2)

    def test_warn_amber_for_tight(self):
        out = _colorize_line("Covenant TIGHT")
        self.assertIn('<span class="warn">TIGHT</span>', out)

    def test_html_escapes_special_chars(self):
        """Raw <script> must never survive into the HTML output."""
        out = _colorize_line("<script>alert('xss')</script>")
        self.assertNotIn("<script>", out)
        self.assertIn("&lt;script&gt;", out)

    def test_preserves_spacing(self):
        """Monospace alignment depends on whitespace surviving."""
        out = _colorize_line("  ✓   Status line")
        # Count spaces — severity wrapping shouldn't eat them
        self.assertTrue(out.startswith("  "))
        self.assertIn("   Status line", out)


class TestTextToHtml(unittest.TestCase):
    def test_full_document_structure(self):
        doc = text_to_html("hello", title="Test")
        self.assertIn("<!DOCTYPE html>", doc)
        self.assertIn("Test", doc)
        self.assertIn("<pre>", doc)
        self.assertIn("hello", doc)

    def test_subtitle_optional(self):
        doc = text_to_html("x", title="T", subtitle="subtitle text")
        self.assertIn("subtitle text", doc)

    def test_back_href_creates_breadcrumb(self):
        doc = text_to_html("x", title="T", back_href="index.html")
        self.assertIn("index.html", doc)
        self.assertIn("Back to index", doc)

    def test_strips_ansi(self):
        doc = text_to_html("\x1b[31mred\x1b[0m", title="T")
        # No escape sequences survive
        self.assertNotIn("\x1b", doc)
        self.assertIn("red", doc)


class TestWrapTextFile(unittest.TestCase):
    def test_writes_html_sibling(self):
        with tempfile.TemporaryDirectory() as tmp:
            in_path = os.path.join(tmp, "37_remark_ccf.txt")
            with open(in_path, "w") as f:
                f.write("Underwrite re-mark — ccf_2026\n  ✓ SAFE")
            out = wrap_text_file(in_path)
            self.assertEqual(out, os.path.join(tmp, "37_remark_ccf.html"))
            with open(out) as f:
                html = f.read()
            self.assertIn("Underwrite re-mark", html)
            self.assertIn('<span class="ok">✓</span>', html)
            self.assertIn('<span class="ok">SAFE</span>', html)

    def test_auto_title_from_filename(self):
        with tempfile.TemporaryDirectory() as tmp:
            in_path = os.path.join(tmp, "37_remark_ccf.txt")
            with open(in_path, "w") as f:
                f.write("content")
            wrap_text_file(in_path)
            with open(os.path.join(tmp, "37_remark_ccf.html")) as f:
                html = f.read()
            # Leading "37_" numeric prefix stripped; rest title-cased
            self.assertIn("Remark Ccf", html)

    def test_missing_file_raises(self):
        with self.assertRaises(FileNotFoundError):
            wrap_text_file("/nonexistent/file.txt")


class TestWrapFolder(unittest.TestCase):
    def test_wraps_all_txt_and_md(self):
        with tempfile.TemporaryDirectory() as tmp:
            for name in ("a.txt", "b.md", "c.json"):
                with open(os.path.join(tmp, name), "w") as f:
                    f.write("content")
            written = wrap_text_files_in_folder(tmp)
            names = [os.path.basename(p) for p in written]
            self.assertIn("a.html", names)
            self.assertIn("b.html", names)
            # JSON not wrapped
            self.assertNotIn("c.html", names)

    def test_skip_when_html_already_exists(self):
        with tempfile.TemporaryDirectory() as tmp:
            with open(os.path.join(tmp, "a.txt"), "w") as f:
                f.write("new text content")
            # Existing custom HTML must not be clobbered
            with open(os.path.join(tmp, "a.html"), "w") as f:
                f.write("<!-- hand-written -->")
            wrap_text_files_in_folder(tmp)
            with open(os.path.join(tmp, "a.html")) as f:
                self.assertIn("hand-written", f.read())

    def test_nonexistent_folder_returns_empty(self):
        self.assertEqual(wrap_text_files_in_folder("/nonexistent"), [])
