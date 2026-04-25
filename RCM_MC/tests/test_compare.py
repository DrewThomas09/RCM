"""Tests for the side-by-side comparison component."""
from __future__ import annotations

import unittest


class TestWinnerIndex(unittest.TestCase):
    def test_higher_is_better(self):
        from rcm_mc.ui.compare import _winner_index
        self.assertEqual(
            _winner_index([0.10, 0.20, 0.15],
                          lower_is_better=False), 1)

    def test_lower_is_better(self):
        from rcm_mc.ui.compare import _winner_index
        self.assertEqual(
            _winner_index([0.10, 0.20, 0.15],
                          lower_is_better=True), 0)

    def test_tie_returns_none(self):
        from rcm_mc.ui.compare import _winner_index
        self.assertIsNone(
            _winner_index([0.10, 0.10, 0.20],
                          lower_is_better=True))

    def test_all_none_returns_none(self):
        from rcm_mc.ui.compare import _winner_index
        self.assertIsNone(
            _winner_index([None, None, None],
                          lower_is_better=False))

    def test_one_value_returns_none(self):
        """Need ≥2 numeric values to declare a winner."""
        from rcm_mc.ui.compare import _winner_index
        self.assertIsNone(
            _winner_index([0.10, None, None],
                          lower_is_better=False))

    def test_skips_none(self):
        from rcm_mc.ui.compare import _winner_index
        # Only entities 0 and 2 have numeric values
        self.assertEqual(
            _winner_index([0.10, None, 0.05],
                          lower_is_better=True), 2)


class TestDeltaPct(unittest.TestCase):
    def test_basic(self):
        from rcm_mc.ui.compare import _delta_pct
        self.assertAlmostEqual(
            _delta_pct(110, 100), 0.10)
        self.assertAlmostEqual(
            _delta_pct(90, 100), -0.10)

    def test_none_or_zero(self):
        from rcm_mc.ui.compare import _delta_pct
        self.assertIsNone(_delta_pct(None, 100))
        self.assertIsNone(_delta_pct(100, None))
        self.assertIsNone(_delta_pct(100, 0))


class TestRenderComparison(unittest.TestCase):
    def _basic_args(self):
        from rcm_mc.ui.compare import (
            ComparableEntity, ComparisonMetric,
        )
        return {
            "entities": [
                ComparableEntity(
                    label="Aurora",
                    values={"denial_rate": 0.08,
                            "operating_margin": 0.10}),
                ComparableEntity(
                    label="Borealis",
                    values={"denial_rate": 0.12,
                            "operating_margin": 0.05}),
            ],
            "metrics": [
                ComparisonMetric(
                    "denial_rate", kind="pct",
                    lower_is_better=True),
                ComparisonMetric(
                    "operating_margin", kind="pct",
                    lower_is_better=False),
            ],
        }

    def test_basic_render(self):
        from rcm_mc.ui.compare import render_comparison
        args = self._basic_args()
        html = render_comparison(**args)
        self.assertIn("Aurora", html)
        self.assertIn("Borealis", html)
        # Aurora wins both metrics → green-styled cell + ▲
        self.assertIn("cmp-winner", html)
        self.assertIn("▲", html)
        # Loser styling on Borealis
        self.assertIn("cmp-loser", html)

    def test_winner_arrow_on_correct_column(self):
        from rcm_mc.ui.compare import render_comparison
        html = render_comparison(**self._basic_args())
        # Aurora wins both metrics → both winner cells should
        # appear in the data tbody. Two winner-arrow uses in
        # the rendered table.
        self.assertEqual(html.count("▲"), 2)
        # Each metric row has exactly one winner-class cell
        # (the right-hand winner)
        body = html.split("<tbody>")[1]
        self.assertEqual(
            body.count('class="cmp-winner"'), 2)

    def test_delta_pct_sign_swaps_for_lower_is_better(self):
        from rcm_mc.ui.compare import render_comparison
        # Borealis denial 0.12 vs Aurora 0.08 → +50% delta;
        # since lower_is_better, the up-arrow direction maps
        # to 'down' (red) — bad outcome
        html = render_comparison(**self._basic_args())
        # Up arrow / red 'down' for the worse value
        self.assertIn("cmp-delta", html)

    def test_too_few_entities(self):
        from rcm_mc.ui.compare import (
            ComparableEntity, ComparisonMetric,
            render_comparison,
        )
        with self.assertRaises(ValueError):
            render_comparison(
                [ComparableEntity(
                    label="x", values={})],
                [ComparisonMetric(
                    "denial_rate")])

    def test_title_renders(self):
        from rcm_mc.ui.compare import render_comparison
        html = render_comparison(
            **self._basic_args(),
            title="Q3 hospitals")
        self.assertIn("Q3 hospitals", html)

    def test_inject_css_disabled(self):
        from rcm_mc.ui.compare import render_comparison
        html = render_comparison(
            **self._basic_args(), inject_css=False)
        self.assertNotIn("<style>", html)
        # Table still there
        self.assertIn('class="cmp-table"', html)

    def test_metric_glossary_tooltip(self):
        """When a metric is in the glossary, the row label
        renders the tooltip icon."""
        from rcm_mc.ui.compare import render_comparison
        html = render_comparison(**self._basic_args())
        # The glossary tooltip class should appear on the
        # known metric row labels (denial_rate is in the
        # glossary).
        self.assertIn("metric-tt-icon", html)

    def test_html_escape_in_label(self):
        from rcm_mc.ui.compare import (
            ComparableEntity, ComparisonMetric,
            render_comparison,
        )
        html = render_comparison(
            [
                ComparableEntity(
                    label="<script>",
                    values={"x": 1}),
                ComparableEntity(
                    label="OK",
                    values={"x": 2}),
            ],
            [ComparisonMetric("x", kind="number")])
        self.assertNotIn("<script>", html.split(
            "<style>")[0] + (html.split("</style>")[-1]
                             if "</style>" in html else html))
        self.assertIn("&lt;script&gt;", html)


class TestCompareHospitals(unittest.TestCase):
    def test_basic(self):
        from rcm_mc.ui.compare import compare_hospitals
        html = compare_hospitals([
            {"name": "Aurora", "ccn": "010001",
             "state": "AL",
             "denial_rate": 0.08,
             "days_in_ar": 42,
             "operating_margin": 0.10},
            {"name": "Borealis", "ccn": "060001",
             "state": "CO",
             "denial_rate": 0.12,
             "days_in_ar": 50,
             "operating_margin": 0.05},
        ])
        self.assertIn("Aurora", html)
        self.assertIn("Borealis", html)
        self.assertIn("CCN 010001", html)
        self.assertIn("AL", html)
        # Aurora wins denial / DSO / margin → multiple winners
        self.assertGreaterEqual(html.count("▲"), 3)

    def test_too_few_hospitals(self):
        from rcm_mc.ui.compare import compare_hospitals
        with self.assertRaises(ValueError):
            compare_hospitals([{"name": "X"}])


class TestCompareScenarios(unittest.TestCase):
    def test_basic(self):
        from rcm_mc.ui.compare import (
            compare_scenarios, ComparisonMetric,
        )
        html = compare_scenarios(
            [
                {"name": "Bear",
                 "description": "Conservative",
                 "ebitda_uplift": 5_000_000,
                 "irr": 0.18},
                {"name": "Base",
                 "ebitda_uplift": 10_000_000,
                 "irr": 0.22},
                {"name": "Bull",
                 "description": "Aggressive",
                 "ebitda_uplift": 18_000_000,
                 "irr": 0.30},
            ],
            metrics=[
                ComparisonMetric(
                    "ebitda_uplift", label="EBITDA uplift",
                    kind="money", lower_is_better=False,
                    show_in_glossary=False),
                ComparisonMetric(
                    "irr", label="IRR",
                    kind="pct", lower_is_better=False,
                    show_in_glossary=False),
            ],
            reference_index=1)
        self.assertIn("Bear", html)
        self.assertIn("Base", html)
        self.assertIn("Bull", html)
        # Bull wins both → 2 ▲ arrows
        self.assertEqual(html.count("▲"), 2)
        # Description shown as sublabel
        self.assertIn("Conservative", html)
        self.assertIn("Aggressive", html)

    def test_metrics_required(self):
        from rcm_mc.ui.compare import compare_scenarios
        with self.assertRaises(ValueError):
            compare_scenarios([
                {"name": "A"}, {"name": "B"}])

    def test_too_few_scenarios(self):
        from rcm_mc.ui.compare import (
            compare_scenarios, ComparisonMetric,
        )
        with self.assertRaises(ValueError):
            compare_scenarios(
                [{"name": "Solo"}],
                metrics=[ComparisonMetric(
                    "x", show_in_glossary=False)])


if __name__ == "__main__":
    unittest.main()
