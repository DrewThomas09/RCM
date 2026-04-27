"""Test for the first 4C adoption — hospital_profile.py wraps
the Operating Margin KPI value in provenance_tooltip
(campaign target 4C, loop 131).

Loop 118 shipped the provenance_tooltip helper and loop 124
shipped build_provenance_graph. This loop is the first
production adoption: render_hospital_profile constructs a
ProvenanceGraph from the hospital dict (plus the locally-
computed operating_margin) and wraps the Operating Margin
KPI value in a hover-tooltip showing the explanation.

Asserts:
  - render_hospital_profile produces HTML containing a
    `class="prov-tt"` wrapper (tooltip is wired).
  - The tooltip's hover-card body (`class="prov-tt-card"`)
    is present, with the SOURCE node type (HCRIS-derived
    operating_margin → SOURCE per build_provenance_graph's
    classification).
  - The Operating Margin label still appears as plain text
    in the KPI label below the value (the v3 layout is
    preserved).
  - The page is robust to a hospital dict missing the
    revenue / expenses fields — should not raise; graph
    just won't include an operating_margin node, and the
    helper falls through to plain text.
"""
from __future__ import annotations

import unittest

from rcm_mc.ui.hospital_profile import render_hospital_profile


class _FakeScore:
    """Minimal score stand-in matching the hasattr(...) checks
    in render_hospital_profile."""
    grade = "B+"
    score = 75
    components = {}


_HOSPITAL_FULL = {
    "ccn": "010001",
    "name": "Test General Hospital",
    "city": "Atlanta",
    "state": "GA",
    "beds": 200,
    "net_patient_revenue": 1.5e8,
    "operating_expenses": 1.4e8,
    "net_income": 1.0e7,
    "medicare_day_pct": 0.45,
    "medicaid_day_pct": 0.20,
}


class HospitalProfileProvenanceTooltipTests(unittest.TestCase):
    def test_render_includes_prov_tt_wrapper(self) -> None:
        out = render_hospital_profile(
            _HOSPITAL_FULL, _FakeScore(),
        )
        self.assertIn(
            'class="prov-tt"', out,
            "render_hospital_profile should wrap the Operating "
            "Margin value in a provenance tooltip wrapper",
        )

    def test_render_includes_tooltip_card(self) -> None:
        out = render_hospital_profile(
            _HOSPITAL_FULL, _FakeScore(),
        )
        self.assertIn('class="prov-tt-card"', out)
        # operating_margin is computed from npr/opex (HCRIS data) +
        # spliced into the prov_profile, so the canonical node is
        # SOURCE (HCRIS). Card should include node-type tag.
        self.assertIn("SOURCE", out)

    def test_label_still_renders_below_value(self) -> None:
        """v3 layout pin: the cad-kpi-label "Operating Margin"
        text should still appear unchanged below the wrapped
        value cell — only the value itself gets the tooltip."""
        out = render_hospital_profile(
            _HOSPITAL_FULL, _FakeScore(),
        )
        self.assertIn(
            '<div class="cad-kpi-label">Operating Margin</div>',
            out,
        )

    def test_render_robust_to_missing_financials(self) -> None:
        """Defensive contract: a hospital with no NPR / opex
        produces margin=0 (per the page's existing fallback);
        build_provenance_graph then produces no
        operating_margin node; provenance_tooltip falls
        through to plain text. No raise, page still renders."""
        thin_hospital = {
            "ccn": "010002", "name": "Sparse",
            "city": "Boston", "state": "MA", "beds": 100,
        }
        out = render_hospital_profile(thin_hospital, _FakeScore())
        # Page renders without raising
        self.assertGreater(len(out), 1000)
        # Operating Margin label still appears (KPI card present)
        self.assertIn(
            '<div class="cad-kpi-label">Operating Margin</div>',
            out,
        )

    def test_render_robust_to_no_db_path(self) -> None:
        """build_provenance_graph supports db_path=None
        (skips the seller-data + calibrations read). The page
        is the same."""
        out = render_hospital_profile(
            _HOSPITAL_FULL, _FakeScore(),
            db_path=None,
        )
        self.assertIn('class="prov-tt"', out)

    def test_all_six_fundamentals_kpis_have_tooltips(self) -> None:
        """Loop 138: extend the loop-131 single-cell adoption to
        every cell in the Fundamentals KPI grid. NPR, Operating
        Margin, Net Income, Licensed Beds, Revenue per Bed, and
        Operating Expenses all get tooltips. Count the
        prov-tt wrappers; should be ≥6 (one per KPI)."""
        import re
        out = render_hospital_profile(
            _HOSPITAL_FULL, _FakeScore(),
        )
        wrapper_count = len(re.findall(r'class="prov-tt"', out))
        self.assertGreaterEqual(
            wrapper_count, 6,
            f"expected ≥6 prov-tt wrappers (one per KPI in the "
            f"Fundamentals grid); found {wrapper_count}",
        )

    def test_npr_value_is_wrapped(self) -> None:
        """Loop 138 wrap pin: the NPR value cell ($1.5M-style)
        renders inside a prov-tt wrapper, not bare."""
        out = render_hospital_profile(
            _HOSPITAL_FULL, _FakeScore(),
        )
        # The NPR cell formats as $150.0M for npr=1.5e8
        self.assertIn('$150.0M', out)
        # And the cell that shows that string is followed by the
        # NPR label (with provenance wrapper between)
        self.assertIn(
            'Net Patient Revenue', out,
        )
        # Sanity: at least one wrapper sits before the NPR label
        # (not just the loop-131 Operating Margin wrapper)
        npr_label_idx = out.index(
            '<div class="cad-kpi-label">Net Patient Revenue</div>')
        op_margin_idx = out.index(
            '<div class="cad-kpi-label">Operating Margin</div>')
        # NPR card comes before Operating Margin in the grid
        self.assertLess(npr_label_idx, op_margin_idx)
        # And there's a prov-tt wrapper sitting in between
        # the start-of-html and the NPR label
        self.assertIn('class="prov-tt"', out[:npr_label_idx])


if __name__ == "__main__":
    unittest.main()
