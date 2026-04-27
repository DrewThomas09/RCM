"""Test for the glossary-expansion change in
ui/metric_glossary.py (campaign target 4A, loop 114).

Loop 112 wrapped the competitive_intel metric labels in
metric_label_link with the helper's "unknown key falls
through to plain text" semantics. Only 4 of 12 _METRIC_DEFS
columns had glossary entries — the other 8 rendered as plain
labels.

This loop adds 7 new MetricDefinition entries to the glossary
(net_patient_revenue, revenue_per_bed, expense_per_bed,
commercial_pct, payer_diversity, total_patient_days,
net_to_gross_ratio). Side effect: every existing 4A wrap that
previously fell through for these keys now lights up
automatically — no UI code changes.

Asserts:
  - All 7 new keys are registered with non-empty definition,
    why_it_matters, and how_calculated fields.
  - The metric_glossary_page renders an anchor card for each
    new key (id="<key>") and a TOC link to it (href="#<key>").
  - competitive_intel's _METRIC_DEFS now resolves at least 11
    of 12 columns (was 4 before the expansion). The single
    remaining unlinked column ("beds") is intentional — bed
    count is just a count, not really a "metric" in the
    diligence sense.
  - portfolio_overview's "Total Net Revenue" KPI now has a
    glossary key it can resolve to (net_patient_revenue) —
    confirms the expansion supports a follow-up wrap.
"""
from __future__ import annotations

import unittest

from rcm_mc.ui.competitive_intel_page import _METRIC_DEFS
from rcm_mc.ui.metric_glossary import (
    get_metric_definition,
    list_metrics,
)
from rcm_mc.ui.metric_glossary_page import render_metric_glossary


_NEW_KEYS_THIS_LOOP = (
    "net_patient_revenue",
    "revenue_per_bed",
    "expense_per_bed",
    "commercial_pct",
    "payer_diversity",
    "total_patient_days",
    "net_to_gross_ratio",
)


class GlossaryExpansionTests(unittest.TestCase):
    def test_each_new_key_has_full_definition(self) -> None:
        for k in _NEW_KEYS_THIS_LOOP:
            with self.subTest(key=k):
                d = get_metric_definition(k)
                self.assertIsNotNone(
                    d, f"metric {k!r} not registered",
                )
                self.assertTrue(
                    d.label, f"metric {k!r} missing label",
                )
                self.assertGreater(
                    len(d.definition), 30,
                    f"metric {k!r} definition is too short — "
                    f"the partner-language explanation should be "
                    f"a full sentence",
                )
                self.assertGreater(
                    len(d.why_it_matters), 30,
                    f"metric {k!r} why_it_matters is too short",
                )
                self.assertGreater(
                    len(d.how_calculated), 20,
                    f"metric {k!r} how_calculated is too short",
                )

    def test_glossary_total_count_increased(self) -> None:
        """Sanity floor: glossary should have at least 24
        entries after this loop (17 pre-loop + 7 added)."""
        self.assertGreaterEqual(
            len(list_metrics()), 24,
            "glossary expansion did not increase the total count",
        )

    def test_metric_glossary_page_renders_each_new_key(self) -> None:
        """The /metric-glossary page should render an anchor
        card and a TOC link for every new key."""
        html = render_metric_glossary()
        for k in _NEW_KEYS_THIS_LOOP:
            with self.subTest(key=k):
                self.assertIn(
                    f'id="{k}"', html,
                    f"new metric {k!r} missing card anchor on "
                    f"/metric-glossary",
                )
                self.assertIn(
                    f'href="#{k}"', html,
                    f"new metric {k!r} missing TOC link on "
                    f"/metric-glossary",
                )

    def test_competitive_intel_lights_up_to_11_of_12(self) -> None:
        """Auto-light-up: competitive_intel._METRIC_DEFS
        previously resolved 4 of 12 columns. After this loop,
        11 of 12 should resolve. The remaining column "beds"
        is intentionally not added (it's a count, not a
        metric)."""
        linked = 0
        unlinked = []
        for col, label, fmt, direction in _METRIC_DEFS:
            if get_metric_definition(col) is not None:
                linked += 1
            else:
                unlinked.append(col)
        self.assertGreaterEqual(
            linked, 11,
            f"expected ≥11 of 12 _METRIC_DEFS to resolve to "
            f"glossary; got {linked}. unlinked={unlinked}",
        )

    def test_portfolio_overview_npr_now_has_glossary_target(self) -> None:
        """portfolio_overview's "Total Net Revenue" KPI label
        is currently un-wrapped because there was no glossary
        target. After this loop, net_patient_revenue exists
        as a target so a follow-up wrap is possible."""
        d = get_metric_definition("net_patient_revenue")
        self.assertIsNotNone(d)
        self.assertEqual(d.label, "Net Patient Revenue")


if __name__ == "__main__":
    unittest.main()
