"""Wave-20 visual: IC memo integrity strip.

The memo page rendered sections as a vertical stack of panels with a
per-section Verified/Check Required badge — the memo's overall shape
(which sections dominate, which are unverified) required scrolling.
Pins the strip: width ∝ word share, fact-check tones, caption totals,
and the empty state.
"""
from __future__ import annotations

import unittest

from rcm_mc.ui.memo_page import _memo_integrity_svg, render_memo_page


def _sec(title, words, passed=True):
    return {
        "title": title,
        "content": " ".join(["word"] * words),
        "fact_checks_passed": passed,
    }


class MemoIntegrityStripTests(unittest.TestCase):
    def test_renders_blocks_with_factcheck_tones(self):
        svg = _memo_integrity_svg([
            _sec("Thesis", 400, passed=True),
            _sec("Market", 300, passed=False),
        ])
        self.assertIn("<svg", svg)
        self.assertIn("ck-memo-integrity", svg)
        self.assertIn("#0a8a5f", svg)   # verified green
        self.assertIn("#b5321e", svg)   # check-required red
        self.assertIn("2 SECTIONS · 1 VERIFIED · 1 CHECK REQUIRED", svg)
        self.assertIn("700 WORDS", svg)

    def test_section_order_preserved(self):
        svg = _memo_integrity_svg([
            _sec("Thesis", 200), _sec("Risks", 200),
        ])
        self.assertLess(svg.index("Thesis"), svg.index("Risks"))

    def test_empty_sections_render_nothing(self):
        self.assertEqual(_memo_integrity_svg([]), "")

    def test_strip_appears_in_page_before_panels(self):
        html_out = render_memo_page("d1", "Test Deal", {
            "sections": [_sec("Thesis", 100)],
            "fact_check_warnings": [],
            "llm_used": False,
        })
        self.assertIn("ck-memo-integrity", html_out)
        self.assertLess(html_out.index("ck-memo-integrity"),
                        html_out.index("memo-section-content"))


if __name__ == "__main__":
    unittest.main()
