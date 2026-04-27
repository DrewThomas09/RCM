"""Test for the 4A metric→glossary link wrapping in
ui/competitive_intel_page.py (campaign target 4A, loop 112).

The Competitive Intelligence page (/competitive-intel/{ccn})
shows percentile rankings across peer groups for every metric
in _METRIC_DEFS, plus a Gap-to-Best-in-Class table of P75 gap
opportunities. Both tables render the metric label per row.

This loop wraps both render sites with metric_label_link.
4 of 12 _METRIC_DEFS columns are direct glossary matches
(operating_margin, occupancy_rate, medicare_day_pct,
medicaid_day_pct); the other 8 fall through to plain text via
the helper's "unknown key" fallback.

Asserts:
  - The percentile-table render site no longer renders the
    label as bare _html.escape(label).
  - The gap-table render site no longer renders the label as
    bare _html.escape(g["metric"]).
  - The shared helper is imported.
  - The gap_opportunities dict carries the canonical column
    key (not just the label) so the gap-table row can resolve
    its glossary anchor.
  - At least 4 of the 12 _METRIC_DEFS columns resolve to a
    real glossary entry — these are the partner-visible
    glossary links the change ships.
  - The other 8 fall through to plain escaped text via the
    helper (no dead anchors).
"""
from __future__ import annotations

import re
import unittest
from pathlib import Path

from rcm_mc.ui.competitive_intel_page import _METRIC_DEFS
from rcm_mc.ui._glossary_link import metric_label_link
from rcm_mc.ui.metric_glossary import get_metric_definition


_MODULE_PATH = (
    Path(__file__).resolve().parents[1]
    / "rcm_mc" / "ui" / "competitive_intel_page.py"
)


_EXPECTED_LINKED = {
    "operating_margin", "occupancy_rate",
    "medicare_day_pct", "medicaid_day_pct",
}


class CompetitiveIntelGlossaryLinksTests(unittest.TestCase):
    def test_imports_shared_helper(self) -> None:
        text = _MODULE_PATH.read_text(encoding="utf-8")
        self.assertIn(
            "from ._glossary_link import metric_label_link",
            text,
        )

    def test_percentile_table_no_longer_renders_bare_label(self) -> None:
        """Line ~216 used to be `cells = f'<td ...>{_html.escape
        (label)}</td>'`. After the migration that exact bare
        substring should be gone."""
        text = _MODULE_PATH.read_text(encoding="utf-8")
        # Helper is now used: search for `metric_label_link(label, col)`
        self.assertIn(
            "metric_label_link(label, col)", text,
            "competitive_intel percentile table should call "
            "metric_label_link(label, col)",
        )

    def test_gap_table_no_longer_renders_bare_metric_label(self) -> None:
        text = _MODULE_PATH.read_text(encoding="utf-8")
        self.assertNotIn(
            '_html.escape(g["metric"])', text,
            "competitive_intel gap table still has un-linked "
            'bare _html.escape(g["metric"])',
        )

    def test_gap_dict_carries_column_key(self) -> None:
        """gap_opportunities entries must include a "col" key so
        the per-row render can pass the canonical column to
        metric_label_link. Without this, the gap-table label
        would always fall through to plain text even for
        columns that have a glossary entry."""
        text = _MODULE_PATH.read_text(encoding="utf-8")
        # Look for the dict construction including "col": col
        self.assertIn(
            '"col": col,', text,
            "gap_opportunities dict should include the canonical "
            'column key as `"col": col,` so the helper can resolve',
        )

    def test_at_least_4_metric_defs_have_glossary_entries(self) -> None:
        """Today, 4 of the 12 _METRIC_DEFS columns are direct
        glossary matches. If the glossary expands or shrinks,
        update this floor — but it should never go below 4."""
        linked = set()
        for col, label, fmt, direction in _METRIC_DEFS:
            if get_metric_definition(col) is not None:
                linked.add(col)
        self.assertGreaterEqual(
            linked, _EXPECTED_LINKED,
            f"expected at least {_EXPECTED_LINKED} to resolve "
            f"to glossary; resolved={linked}",
        )

    def test_unknown_metric_columns_fall_through(self) -> None:
        """The 8 _METRIC_DEFS columns NOT in the glossary
        (net_patient_revenue, beds, etc.) should produce plain
        escaped text via the helper rather than dead anchors."""
        for col, label, fmt, direction in _METRIC_DEFS:
            if get_metric_definition(col) is not None:
                continue
            with self.subTest(col=col):
                html = metric_label_link(label, col)
                self.assertNotIn(
                    "<a", html,
                    f"label {label!r} (col={col!r}) is not in the "
                    f"glossary but the helper produced an anchor — "
                    f"would ship a dead link",
                )

    def test_helper_referenced_at_least_twice(self) -> None:
        """2 render sites = 2 calls to metric_label_link."""
        text = _MODULE_PATH.read_text(encoding="utf-8")
        ref_count = len(re.findall(r"metric_label_link\(", text))
        self.assertGreaterEqual(
            ref_count, 2,
            f"metric_label_link should be called ≥2x; "
            f"found {ref_count}",
        )


if __name__ == "__main__":
    unittest.main()
