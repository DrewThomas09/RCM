"""ck_scatter per-point links (connectivity) + backward compatibility.

A 5th tuple element (href) wraps a dot in an SVG <a> so a partner can
click a point through to that row's drill-down. 4-tuples (and shorter)
must keep working unchanged — no <a>, no behavior change.
"""
from __future__ import annotations

import unittest

from rcm_mc.ui._chartis_kit import ck_scatter


class CkScatterLinkTests(unittest.TestCase):
    def test_four_tuples_have_no_anchor(self):
        html = ck_scatter([(1, 2, "A", "teal"), (3, 4, "B", "positive")])
        self.assertNotIn("<a href", html)
        self.assertEqual(html.count("<circle"), 2)

    def test_five_tuple_href_wraps_dot_in_anchor(self):
        html = ck_scatter([
            (1, 2, "A", "teal", "/detail?id=A"),
            (3, 4, "B", "positive", "/detail?id=B"),
        ])
        self.assertEqual(html.count("<a href"), 2)
        self.assertIn("/detail?id=A", html)
        self.assertIn("cursor:pointer", html)
        self.assertEqual(html.count("<circle"), 2)  # circles still present

    def test_href_is_escaped(self):
        html = ck_scatter([
            (1, 2, "A", "teal", '/d?q=<x>&y="z"'),
            (3, 4, "B", "teal", "/d?q=2"),
        ])
        self.assertNotIn("<x>", html)
        self.assertIn("&lt;x&gt;", html)
        self.assertIn("&amp;", html)

    def test_mixed_href_and_none(self):
        html = ck_scatter([
            (1, 2, "A", "teal", None),
            (3, 4, "B", "teal", "/y"),
        ])
        self.assertEqual(html.count("<a href"), 1)


if __name__ == "__main__":
    unittest.main()
