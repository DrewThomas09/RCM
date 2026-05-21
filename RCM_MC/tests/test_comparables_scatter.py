"""Pin for the Entry-Multiple vs Realized-Outcome scatter on /comparables.

The comps table lists EV/EBITDA and realized MOIC in adjacent columns;
the scatter pairs them so a partner reads the IC question directly — did
peers who paid this entry multiple still return well? Dots are realized
peers (clickable through to the deal); y=1.0× is break-even and the
target's own multiple drops a dashed vertical reference.
"""
from __future__ import annotations

import unittest


def _comp(name, ev, eb, moic, sid):
    return {
        "deal_name": name, "ev_mm": ev, "ebitda_mm": eb,
        "realized_moic": moic, "source_id": sid,
    }


class ComparablesScatterTests(unittest.TestCase):
    def _scatter(self, comps, target=None):
        from rcm_mc.ui.data_public.comparables_page import _comps_scatter
        return _comps_scatter(comps, target)

    def test_renders_dots_with_axis_labels(self):
        html = self._scatter([
            _comp("Alpha", 500, 50, 3.4, "s1"),
            _comp("Beta", 300, 40, 0.8, "s2"),
        ])
        self.assertIn("Entry Multiple vs Realized Outcome", html)
        self.assertIn("Entry multiple (EV/EBITDA)", html)
        self.assertIn("Realized MOIC", html)
        self.assertEqual(html.count("<circle"), 2)

    def test_dots_link_to_library_detail(self):
        html = self._scatter([
            _comp("Alpha", 500, 50, 3.4, "s1"),
            _comp("Gamma", 200, 25, 2.1, "s3"),
        ])
        self.assertEqual(html.count("<a href"), 2)
        self.assertIn("/library/s1", html)

    def test_target_multiple_draws_reference_line(self):
        # With a query deal, the target's entry multiple drops a dashed
        # vertical so the partner sees where their price sits.
        html = self._scatter(
            [_comp("Alpha", 500, 50, 3.4, "s1"), _comp("Beta", 300, 40, 0.8, "s2")],
            target={"ev_mm": 400, "ebitda_mm": 40},
        )
        self.assertIn("stroke-dasharray", html)
        # caption text is HTML-escaped by ck_scatter (apostrophe -> &#x27;)
        self.assertIn("your target", html)
        self.assertIn("entry multiple", html)

    def test_tone_marks_homerun_and_loss(self):
        html = self._scatter([
            _comp("Home", 500, 50, 3.5, "s1"),   # >=3.0 positive
            _comp("Loss", 300, 40, 0.7, "s2"),   # <1.0 negative
        ])
        self.assertIn("--sc-positive", html)
        self.assertIn("--sc-negative", html)

    def test_skips_comps_without_multiple_or_moic(self):
        html = self._scatter([
            _comp("Has", 500, 50, 2.0, "s1"),
            _comp("NoMoic", 300, 40, None, "s2"),
            _comp("NoEbitda", 300, 0, 2.0, "s3"),
            _comp("Also", 200, 25, 1.5, "s4"),
        ])
        self.assertEqual(html.count("<circle"), 2)


if __name__ == "__main__":
    unittest.main()
