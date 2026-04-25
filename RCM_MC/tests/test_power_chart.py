"""Tests for the interactive power chart component."""
from __future__ import annotations

import unittest


class TestChartSeries(unittest.TestCase):
    def test_basic_construction(self):
        from rcm_mc.ui.power_chart import ChartSeries
        s = ChartSeries(name="A",
                        points=[("Q1", 1.0), ("Q2", 2.0)])
        self.assertEqual(s.kind, "line")
        self.assertIsNone(s.color)

    def test_invalid_kind_rejected(self):
        from rcm_mc.ui.power_chart import ChartSeries
        with self.assertRaises(ValueError):
            ChartSeries(name="A", points=[("Q1", 1.0)],
                        kind="purple")


class TestRender(unittest.TestCase):
    def test_basic_line_chart(self):
        from rcm_mc.ui.power_chart import (
            ChartSeries, render_power_chart,
        )
        html = render_power_chart(
            chart_id="trend",
            title="EBITDA Trend",
            series=[
                ChartSeries("Aurora", points=[
                    ("Q1", 30), ("Q2", 32),
                    ("Q3", 35), ("Q4", 38)],
                    color="#60a5fa"),
            ],
            y_kind="money")
        # Required infrastructure
        self.assertIn('id="trend-root"', html)
        self.assertIn('id="trend-tooltip"', html)
        self.assertIn('id="trend-legend"', html)
        self.assertIn('id="trend-overlay"', html)
        self.assertIn('id="trend-export-svg"', html)
        self.assertIn('id="trend-export-png"', html)
        self.assertIn('id="trend-reset"', html)
        # SVG with polyline (line series)
        self.assertIn("<svg", html)
        self.assertIn("<polyline", html)
        # Title rendered
        self.assertIn("EBITDA Trend", html)
        # Legend item
        self.assertIn("Aurora", html)
        # Reset / drag instruction
        self.assertIn("Drag x-axis", html)
        # JS block
        self.assertIn("<script>", html)

    def test_invalid_chart_id_rejected(self):
        from rcm_mc.ui.power_chart import (
            ChartSeries, render_power_chart,
        )
        with self.assertRaises(ValueError):
            render_power_chart(
                chart_id="bad/id",
                series=[ChartSeries(
                    "A", [("Q1", 1.0)])])

    def test_empty_series_rejected(self):
        from rcm_mc.ui.power_chart import (
            render_power_chart,
        )
        with self.assertRaises(ValueError):
            render_power_chart(
                chart_id="x", series=[])

    def test_all_empty_points_rejected(self):
        from rcm_mc.ui.power_chart import (
            ChartSeries, render_power_chart,
        )
        with self.assertRaises(ValueError):
            render_power_chart(
                chart_id="x",
                series=[ChartSeries("A", points=[])])

    def test_palette_auto_assigns(self):
        from rcm_mc.ui.power_chart import (
            ChartSeries, render_power_chart,
        )
        s1 = ChartSeries("A", [("Q1", 1.0)])
        s2 = ChartSeries("B", [("Q1", 2.0)])
        render_power_chart(
            chart_id="x", series=[s1, s2])
        self.assertIsNotNone(s1.color)
        self.assertIsNotNone(s2.color)
        # Different colors from palette
        self.assertNotEqual(s1.color, s2.color)

    def test_bar_chart_renders_rects(self):
        from rcm_mc.ui.power_chart import (
            ChartSeries, render_power_chart,
        )
        html = render_power_chart(
            chart_id="bar",
            series=[ChartSeries(
                "A",
                points=[("Q1", 10), ("Q2", 20),
                        ("Q3", 15)],
                kind="bar")])
        # No polyline for bar series
        self.assertNotIn("<polyline", html)
        # Rects present
        self.assertIn('class="point"', html)
        self.assertIn("<rect", html)

    def test_drilldown_url_embedded(self):
        from rcm_mc.ui.power_chart import (
            ChartSeries, render_power_chart,
        )
        html = render_power_chart(
            chart_id="x",
            series=[ChartSeries(
                "A", [("Q1", 1), ("Q2", 2)])],
            drilldown_url="/deal/{series}?ts={x}")
        self.assertIn("/deal/{series}", html)

    def test_y_axis_ticks_formatted(self):
        from rcm_mc.ui.power_chart import (
            ChartSeries, render_power_chart,
        )
        html = render_power_chart(
            chart_id="x",
            series=[ChartSeries("A", points=[
                ("Q1", 1_000_000), ("Q2", 5_000_000)])],
            y_kind="money")
        # Y-axis ticks should be money-formatted
        self.assertTrue(
            "$1.0M" in html or "$2.5M" in html
            or "$3.0M" in html or "$4.0M" in html
            or "$5.0M" in html or "$0M" in html)

    def test_pct_y_kind(self):
        from rcm_mc.ui.power_chart import (
            ChartSeries, render_power_chart,
        )
        html = render_power_chart(
            chart_id="x",
            series=[ChartSeries("A", points=[
                ("Q1", 0.10), ("Q2", 0.15)])],
            y_kind="pct")
        # Pct ticks have % suffix
        self.assertIn("%", html)

    def test_data_attributes_on_points(self):
        """Each data point has data-x + data-series + data-i for
        click-drilldown + zoom hide/show."""
        from rcm_mc.ui.power_chart import (
            ChartSeries, render_power_chart,
        )
        html = render_power_chart(
            chart_id="x",
            series=[ChartSeries("A", points=[
                ("Q1", 1), ("Q2", 2)])])
        self.assertIn('data-i="0"', html)
        self.assertIn('data-i="1"', html)
        self.assertIn('data-x="Q1"', html)
        self.assertIn('data-x="Q2"', html)

    def test_native_svg_title_for_hover(self):
        """SVG <title> elements give native browser tooltips
        even before JS loads."""
        from rcm_mc.ui.power_chart import (
            ChartSeries, render_power_chart,
        )
        html = render_power_chart(
            chart_id="x",
            series=[ChartSeries("MyData", points=[
                ("Q1", 100)])],
            y_kind="int")
        self.assertIn("<title>MyData: 100</title>", html)

    def test_multiple_series_each_in_group(self):
        """Series wrapped in <g data-series="..."> for legend
        toggle."""
        from rcm_mc.ui.power_chart import (
            ChartSeries, render_power_chart,
        )
        html = render_power_chart(
            chart_id="x",
            series=[
                ChartSeries("Apple", points=[
                    ("Q1", 1), ("Q2", 2)]),
                ChartSeries("Banana", points=[
                    ("Q1", 3), ("Q2", 4)]),
            ])
        self.assertIn('data-series="Apple"', html)
        self.assertIn('data-series="Banana"', html)


class TestFormatY(unittest.TestCase):
    def test_money_scales(self):
        from rcm_mc.ui.power_chart import _format_y
        self.assertEqual(_format_y(1500, "money"), "$2K")
        self.assertEqual(_format_y(2_500_000, "money"),
                         "$2.5M")

    def test_pct_signed(self):
        from rcm_mc.ui.power_chart import _format_y
        self.assertEqual(_format_y(0.05, "pct"), "+5.0%")
        self.assertEqual(_format_y(-0.10, "pct"), "-10.0%")


if __name__ == "__main__":
    unittest.main()
