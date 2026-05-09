"""tests for ``metric_with_dollars`` (P65)."""
from __future__ import annotations

import math
import unittest

from rcm_mc.ui._ui_kit import metric_with_dollars


class WithDollars(unittest.TestCase):

    def test_percent_with_ebitda_translation(self) -> None:
        out = metric_with_dollars(
            0.449, kind="percent",
            dollars_amount=156_000_000,
            dollars_label="EBITDA contribution",
        )
        self.assertIn("44.9%", out)
        self.assertIn("dollar-context", out)
        self.assertIn("$156.00M", out)
        self.assertIn("EBITDA contribution", out)

    def test_denial_rate_with_recoverable_revenue(self) -> None:
        out = metric_with_dollars(
            0.092, kind="percent",
            dollars_amount=14_200_000,
            dollars_label="recoverable at corpus P25",
        )
        self.assertIn("9.2%", out)
        self.assertIn("$14.20M", out)
        self.assertIn("recoverable", out)


class WithoutDollars(unittest.TestCase):

    def test_no_dollars_renders_point_only(self) -> None:
        out = metric_with_dollars(0.449, kind="percent")
        self.assertEqual(out, "44.9%")

    def test_nan_dollars_drops_span(self) -> None:
        out = metric_with_dollars(
            0.449, kind="percent",
            dollars_amount=math.nan,
            dollars_label="any",
        )
        self.assertNotIn("dollar-context", out)


class MissingPointDropsContext(unittest.TestCase):

    def test_missing_value_renders_unpopulated_span(self) -> None:
        out = metric_with_dollars(
            None, kind="percent",
            dollars_amount=1_000_000,
            dollars_label="any",
        )
        self.assertIn("muted unpopulated", out)
        # No dollar context when the point is missing — the
        # translation is meaningless without a base value.
        self.assertNotIn("dollar-context", out)


class HtmlEscaping(unittest.TestCase):

    def test_label_escaped(self) -> None:
        out = metric_with_dollars(
            0.5, kind="percent",
            dollars_amount=1_000_000,
            dollars_label="<script>",
        )
        self.assertNotIn("<script>", out)
        self.assertIn("&lt;script&gt;", out)


if __name__ == "__main__":
    unittest.main()
