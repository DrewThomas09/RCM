"""Test for the 4A metric→glossary link wrapping in
ui/portfolio_overview.py (campaign target 4A, loop 110).

The Portfolio Overview page is the default partner landing for
the cross-deal view. It surfaces 5 metric labels that match
canonical glossary entries:
  - 3 KPI cards (Avg Denial Rate, Avg Days in AR, Avg Net
    Collection)
  - 2 deal-table column headers (Denial, AR)

This loop wraps each in metric_label_link() pointing at the
canonical /metric-glossary card via _LABEL_TO_GLOSSARY_KEY.

Asserts:
  - _LABEL_TO_GLOSSARY_KEY has all 5 expected entries and each
    resolves to a real glossary key.
  - Each of the 5 wrap sites no longer renders the bare label
    text inside `<div class="cad-kpi-label">...</div>` or
    `<th>...</th>` — they now contain a metric_label_link
    call.
  - The shared helper is imported at module top.
  - The helper is referenced ≥5 times.
"""
from __future__ import annotations

import re
import unittest
from pathlib import Path

from rcm_mc.ui.portfolio_overview import _LABEL_TO_GLOSSARY_KEY
from rcm_mc.ui.metric_glossary import get_metric_definition


_MODULE_PATH = (
    Path(__file__).resolve().parents[1]
    / "rcm_mc" / "ui" / "portfolio_overview.py"
)


_EXPECTED_KEYS = {
    "Avg Denial Rate":   "denial_rate",
    "Avg Days in AR":    "days_in_ar",
    "Avg Net Collection": "net_collection_rate",
    "Total Net Revenue": "net_patient_revenue",  # added loop 116
    "Denial":            "denial_rate",
    "AR":                "days_in_ar",
    "NPR":               "net_patient_revenue",  # added loop 116
}


class PortfolioOverviewGlossaryLinksTests(unittest.TestCase):
    def test_label_to_key_map_is_complete(self) -> None:
        """Every expected label-to-key mapping is present and
        each resolves to a real glossary entry."""
        self.assertEqual(
            _LABEL_TO_GLOSSARY_KEY, _EXPECTED_KEYS,
            "portfolio_overview label-to-key map mismatch",
        )
        for label, key in _LABEL_TO_GLOSSARY_KEY.items():
            with self.subTest(label=label, key=key):
                self.assertIsNotNone(
                    get_metric_definition(key),
                    f"label {label!r} → key {key!r} is not in "
                    f"the glossary — link will be a 404",
                )

    def test_imports_shared_helper(self) -> None:
        text = _MODULE_PATH.read_text(encoding="utf-8")
        self.assertIn(
            "from ._glossary_link import metric_label_link",
            text,
        )

    def test_kpi_labels_no_longer_bare(self) -> None:
        """The 4 KPI cards used to render the label as plain
        text inside `<div class="cad-kpi-label">...</div>`.
        After loops 110 + 116 those exact bare substrings
        should be gone (the 4th — Total Net Revenue — was
        added in loop 116 once the new net_patient_revenue
        glossary entry shipped in loop 114)."""
        text = _MODULE_PATH.read_text(encoding="utf-8")
        bare_patterns = (
            '<div class="cad-kpi-label">Avg Denial Rate</div>',
            '<div class="cad-kpi-label">Avg Days in AR</div>',
            '<div class="cad-kpi-label">Avg Net Collection</div>',
            '<div class="cad-kpi-label">Total Net Revenue</div>',
        )
        for pat in bare_patterns:
            with self.subTest(pat=pat):
                self.assertNotIn(
                    pat, text,
                    f"portfolio_overview still has un-linked "
                    f"KPI label: {pat!r}",
                )

    def test_table_column_headers_no_longer_bare(self) -> None:
        """The deal-table used to render `<th>Denial</th>
        <th>AR</th>` and `<th>NPR</th>` as plain headers.
        After loops 110 + 116, none of those exact bare
        substrings should remain (NPR was wrapped in loop
        116 once net_patient_revenue was added to the
        glossary in loop 114)."""
        text = _MODULE_PATH.read_text(encoding="utf-8")
        self.assertNotIn(
            "<th>Denial</th><th>AR</th>", text,
            "portfolio_overview deal table still has un-linked "
            "<th>Denial</th><th>AR</th> column headers",
        )
        # NPR header should now also be wrapped (loop 116)
        self.assertNotIn(
            "<th>NPR</th>", text,
            "portfolio_overview deal table still has un-linked "
            "<th>NPR</th> column header — should now wrap to "
            "/metric-glossary#net_patient_revenue",
        )

    def test_helper_referenced_at_least_7_times(self) -> None:
        """After loops 110 + 116, 7 wrap sites total: 4 KPI
        cards (Avg Denial, Avg AR, Avg Net Collection, Total
        Net Revenue) + 3 deal-table headers (Denial, AR,
        NPR)."""
        text = _MODULE_PATH.read_text(encoding="utf-8")
        ref_count = len(re.findall(r"metric_label_link\(", text))
        self.assertGreaterEqual(
            ref_count, 7,
            f"metric_label_link should be called ≥7 times "
            f"(4 KPI cards + 3 table headers); found {ref_count}",
        )


if __name__ == "__main__":
    unittest.main()
