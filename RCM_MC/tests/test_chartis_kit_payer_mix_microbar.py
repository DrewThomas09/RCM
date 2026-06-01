"""Tests for ``ck_payer_mix_microbar`` — compact stacked-segment
payer-mix bar.

Iter-7 FQHC-spec foundation; reused everywhere payer concentration
matters (FQHCs, ASCs, physician groups, dialysis, SNFs). Renders an
inline horizontal stacked SVG bar at 100×12px default — width per
segment = share; color from the semantic palette (Medicare gray,
Commercial blue, Medicaid muted, Self-pay beige).

Not yet wired to any partner-facing page. Tests lock the visual +
behavior contract before integration.
"""
from __future__ import annotations

import unittest

from rcm_mc.ui._chartis_kit import (
    _PAYER_MIX_COLORS,
    ck_payer_mix_microbar,
)


class EmptyCasesTests(unittest.TestCase):

    def test_empty_dict_returns_empty(self):
        self.assertEqual(ck_payer_mix_microbar({}), "")

    def test_none_returns_empty(self):
        self.assertEqual(ck_payer_mix_microbar(None), "")  # type: ignore

    def test_all_zero_shares_returns_empty(self):
        self.assertEqual(
            ck_payer_mix_microbar({"a": 0, "b": 0}), "")

    def test_all_negative_shares_returns_empty(self):
        # Negative shares filtered before normalization → empty
        self.assertEqual(
            ck_payer_mix_microbar({"a": -0.4, "b": -0.6}), "")

    def test_all_non_numeric_returns_empty(self):
        self.assertEqual(
            ck_payer_mix_microbar({"a": "junk", "b": None}), "")

    def test_nan_inf_filtered(self):
        # NaN/inf filtered; if everything filters out → empty
        self.assertEqual(
            ck_payer_mix_microbar({
                "a": float("nan"),
                "b": float("inf"),
            }),
            "",
        )


class BasicRenderTests(unittest.TestCase):

    _MIX = {
        "Medicare": 0.40, "Medicaid": 0.30,
        "Commercial": 0.25, "Self-Pay": 0.05,
    }

    def test_returns_svg(self):
        out = ck_payer_mix_microbar(self._MIX)
        self.assertTrue(out.startswith("<svg"))
        self.assertTrue(out.endswith("</svg>"))

    def test_default_dimensions(self):
        out = ck_payer_mix_microbar(self._MIX)
        self.assertIn('width="100"', out)
        self.assertIn('height="12"', out)

    def test_custom_dimensions(self):
        out = ck_payer_mix_microbar(
            self._MIX, width=200, height=20)
        self.assertIn('width="200"', out)
        self.assertIn('height="20"', out)

    def test_class_and_accessibility(self):
        out = ck_payer_mix_microbar(self._MIX)
        self.assertIn('class="ck-payer-mix"', out)
        self.assertIn('role="img"', out)
        self.assertIn('aria-label="payer mix microbar"', out)

    def test_renders_one_g_per_segment(self):
        out = ck_payer_mix_microbar(self._MIX)
        self.assertEqual(out.count('<g>'), 4)

    def test_white_separators_between_segments(self):
        # Each segment carries stroke="#ffffff" so adjacent
        # segments visually separate without a divider element.
        out = ck_payer_mix_microbar(self._MIX)
        self.assertIn('stroke="#ffffff"', out)


class WidthAllocationTests(unittest.TestCase):

    # Tight regex: `\swidth="..."` requires whitespace before `width=`
    # so it doesn't also match `stroke-width="0.5"` on the same rect.
    _WIDTH_RX = r'<rect [^>]*\swidth="([\d.]+)"'

    def test_widths_proportional_to_shares(self):
        out = ck_payer_mix_microbar(
            {"Medicare": 0.50, "Commercial": 0.50},
            width=200,
        )
        import re
        widths = re.findall(self._WIDTH_RX, out)
        self.assertEqual(len(widths), 2)
        self.assertAlmostEqual(float(widths[0]), 100.0, places=0)
        self.assertAlmostEqual(float(widths[1]), 100.0, places=0)

    def test_normalizes_to_unit_sum(self):
        # Pass percent-points (sums to 100, not 1) → still renders
        # proportionally to 100% canvas width.
        out = ck_payer_mix_microbar(
            {"Medicare": 40, "Medicaid": 40, "Commercial": 20},
            width=100,
        )
        import re
        widths = sorted(
            float(w) for w in re.findall(self._WIDTH_RX, out))
        self.assertAlmostEqual(sum(widths), 100.0, places=0)
        self.assertEqual(widths, [20.0, 40.0, 40.0])

    def test_widths_sum_to_canvas_width(self):
        out = ck_payer_mix_microbar(
            {"Medicare": 0.3, "Medicaid": 0.3,
             "Commercial": 0.3, "Self-Pay": 0.1},
            width=400,
        )
        import re
        widths = [
            float(w) for w in re.findall(self._WIDTH_RX, out)]
        self.assertAlmostEqual(sum(widths), 400.0, places=0)

    def test_sub_pixel_segment_dropped(self):
        # 0.001 share at 100px width = 0.1px → below sub-pixel floor
        # → segment dropped (no invisible <rect>)
        out = ck_payer_mix_microbar(
            {"Medicare": 0.999, "Other": 0.001},
            width=100,
        )
        # Only 1 segment renders.
        self.assertEqual(out.count('<g>'), 1)


class ColorPaletteTests(unittest.TestCase):

    def test_medicare_uses_gray(self):
        out = ck_payer_mix_microbar({"Medicare": 1.0})
        self.assertIn(_PAYER_MIX_COLORS["medicare"], out)

    def test_commercial_uses_premium_blue(self):
        out = ck_payer_mix_microbar({"Commercial": 1.0})
        self.assertIn(_PAYER_MIX_COLORS["commercial"], out)

    def test_medicaid_uses_muted_blue(self):
        out = ck_payer_mix_microbar({"Medicaid": 1.0})
        self.assertIn(_PAYER_MIX_COLORS["medicaid"], out)

    def test_self_pay_uses_beige(self):
        out = ck_payer_mix_microbar({"Self-Pay": 1.0})
        self.assertIn(_PAYER_MIX_COLORS["self-pay"], out)

    def test_lookup_is_case_insensitive(self):
        out1 = ck_payer_mix_microbar({"MEDICARE": 1.0})
        out2 = ck_payer_mix_microbar({"medicare": 1.0})
        out3 = ck_payer_mix_microbar({"MeDiCaRe": 1.0})
        # All three resolve to the same palette color.
        for out in (out1, out2, out3):
            self.assertIn(_PAYER_MIX_COLORS["medicare"], out)

    def test_unknown_payer_falls_back_to_neutral_gray(self):
        out = ck_payer_mix_microbar({"WeirdPayerName": 1.0})
        self.assertIn("#a8a8a8", out)

    def test_aco_value_based_uses_teal(self):
        # VBC/ACO arrangements share the editorial teal anchor.
        out = ck_payer_mix_microbar({"ACO": 1.0})
        self.assertIn(_PAYER_MIX_COLORS["aco"], out)


class SortOrderTests(unittest.TestCase):
    """Sort order matters for partner readability — the canonical
    'preferred' order mirrors how payer tables are usually printed."""

    def test_preferred_anchors_known_payers_first(self):
        # Pass in messy order; rendered order should be Medicare,
        # Medicaid, Commercial.
        out = ck_payer_mix_microbar(
            {"Commercial": 0.3, "Medicare": 0.4, "Medicaid": 0.3},
            sort="preferred",
        )
        # Pull x positions to verify order.
        import re
        order = re.findall(r'<title>([^<:]+):', out)
        # First three should match the preferred anchor order.
        self.assertEqual(order[:3],
                          ["Medicare", "Medicaid", "Commercial"])

    def test_desc_sorts_largest_first(self):
        out = ck_payer_mix_microbar(
            {"Small": 0.1, "Large": 0.6, "Medium": 0.3},
            sort="desc",
        )
        import re
        names = re.findall(r'<title>([^<:]+):', out)
        self.assertEqual(names[:3], ["Large", "Medium", "Small"])

    def test_asc_sorts_smallest_first(self):
        out = ck_payer_mix_microbar(
            {"Small": 0.1, "Large": 0.6, "Medium": 0.3},
            sort="asc",
        )
        import re
        names = re.findall(r'<title>([^<:]+):', out)
        self.assertEqual(names[:3], ["Small", "Medium", "Large"])

    def test_as_given_preserves_insertion_order(self):
        from collections import OrderedDict
        mix = OrderedDict([
            ("Zebra", 0.3),
            ("Alpha", 0.3),
            ("Lima", 0.4),
        ])
        out = ck_payer_mix_microbar(mix, sort="as_given")
        import re
        names = re.findall(r'<title>([^<:]+):', out)
        self.assertEqual(names[:3], ["Zebra", "Alpha", "Lima"])

    def test_unknown_sort_defaults_to_preferred(self):
        out = ck_payer_mix_microbar(
            {"Commercial": 0.3, "Medicare": 0.4, "Medicaid": 0.3},
            sort="weird_mode",
        )
        import re
        names = re.findall(r'<title>([^<:]+):', out)
        # Falls back to 'preferred'
        self.assertEqual(names[:3],
                          ["Medicare", "Medicaid", "Commercial"])


class LabelTests(unittest.TestCase):

    def test_no_labels_by_default(self):
        out = ck_payer_mix_microbar(
            {"Medicare": 0.40, "Commercial": 0.60})
        self.assertNotIn('<text', out)

    def test_show_labels_renders_text_per_segment(self):
        out = ck_payer_mix_microbar(
            {"Medicare": 0.40, "Commercial": 0.60},
            show_labels=True,
        )
        # 2 segments, both above default 10% threshold → 2 labels
        self.assertEqual(out.count('<text'), 2)
        # Percent values present
        self.assertIn(">40%<", out)
        self.assertIn(">60%<", out)

    def test_label_threshold_filters_tiny_slices(self):
        # 5% slice falls below default 10% threshold → no label.
        out = ck_payer_mix_microbar(
            {"Big": 0.95, "Small": 0.05},
            show_labels=True,
        )
        # Only big slice gets a label.
        self.assertEqual(out.count('<text'), 1)
        self.assertIn(">95%<", out)
        self.assertNotIn(">5%<", out)

    def test_custom_label_threshold(self):
        # Lower threshold → small slices now labeled.
        out = ck_payer_mix_microbar(
            {"Big": 0.95, "Small": 0.05},
            show_labels=True,
            label_threshold=0.03,
        )
        self.assertEqual(out.count('<text'), 2)
        self.assertIn(">5%<", out)

    def test_dark_text_on_light_segments(self):
        # Beige + muted backgrounds use dark ink for legibility.
        out = ck_payer_mix_microbar(
            {"Self-Pay": 1.0}, show_labels=True)
        # Dark ink color appears in fill attribute
        self.assertIn('fill="#1a2332"', out)

    def test_white_text_on_dark_segments(self):
        # Commercial blue is dark enough for white text.
        out = ck_payer_mix_microbar(
            {"Commercial": 1.0}, show_labels=True)
        self.assertIn('fill="#ffffff"', out)


class TooltipTests(unittest.TestCase):

    def test_per_segment_tooltip(self):
        out = ck_payer_mix_microbar(
            {"Medicare": 0.40, "Commercial": 0.60})
        self.assertIn("Medicare: 40%", out)
        self.assertIn("Commercial: 60%", out)

    def test_composite_svg_tooltip_carries_full_mix(self):
        out = ck_payer_mix_microbar(
            {"Medicare": 0.40, "Commercial": 0.40, "Medicaid": 0.20})
        # The top-level <title> shows the full mix in canonical order.
        self.assertIn("Medicare 40%", out)
        self.assertIn("Medicaid 20%", out)
        self.assertIn("Commercial 40%", out)
        # The full string is dot-separated.
        self.assertIn(" · ", out)

    def test_payer_name_html_escaped(self):
        # Defensive against bad payer names from upstream data.
        out = ck_payer_mix_microbar(
            {"<script>": 1.0})
        self.assertNotIn("<script>", out.split("<svg")[1].split(">",
                                                                  1)[1])
        self.assertIn("&lt;script&gt;", out)


class HygieneTests(unittest.TestCase):

    def test_negative_share_filtered_others_renormalize(self):
        # 0.4 + (-0.1) + 0.6 → valid mass is 1.0, but negatives
        # are dropped pre-normalization → renormalized to 0.4/1.0
        # and 0.6/1.0 → 40% / 60% split.
        out = ck_payer_mix_microbar(
            {"A": 0.4, "B": -0.1, "C": 0.6},
        )
        self.assertIn("A: 40%", out)
        self.assertIn("C: 60%", out)
        self.assertNotIn("B:", out)

    def test_non_numeric_share_filtered(self):
        out = ck_payer_mix_microbar(
            {"A": 0.5, "B": "junk", "C": 0.5},
        )
        # Only A and C survive → 50/50
        self.assertIn("A: 50%", out)
        self.assertIn("C: 50%", out)
        self.assertNotIn("B:", out)


if __name__ == "__main__":
    unittest.main()
