"""Backlog #35 — glossary long-tail: predictive-screener + X-Ray
metric headers via the shared metric_label_link helper.

Part 1 (W2-218) linked the predictive screener's metric column
headers (Revenue / Margin / Est. Denial / Est. AR Days). Part 2
(W4-009, this change) links the HCRIS X-Ray benchmark grid's metric
labels through a spec.attr → glossary-key alias table
(_XRAY_ATTR_TO_GLOSSARY_KEY in ui/hcris_xray_page.py).

The helper's guard is the no-dead-anchor invariant: any key that
does not resolve in the metric_glossary registry renders as plain
escaped text, never an <a>. These tests pin that from both sides:

  - every alias-table value resolves in the glossary registry, and
    every alias-table key is a real X-Ray METRIC_CATALOG attr;
  - the linkable catalog attrs resolve to exactly the expected 10
    glossary keys; the 5 attrs without a glossary card are pinned
    so a new catalog metric forces a deliberate choice here;
  - a rendered X-Ray report page carries all 10 anchors, carries NO
    anchor for the unlinked/raw attr names, and EVERY
    /metric-glossary#<key> anchor on the page resolves;
  - the predictive screener's four header anchors survive and every
    anchor on that page resolves too;
  - regression: a bogus key (direct or via alias) renders plain
    escaped text — no link, no glossary href.
"""
from __future__ import annotations

import re
import unittest

from rcm_mc.diligence.hcris_xray import METRIC_CATALOG
from rcm_mc.ui._glossary_link import metric_label_link
from rcm_mc.ui.hcris_xray_page import _XRAY_ATTR_TO_GLOSSARY_KEY
from rcm_mc.ui.metric_glossary import get_metric_definition

_ANCHOR_RE = re.compile(r"/metric-glossary#([A-Za-z0-9_.\-]+)")

# The 10 glossary keys the X-Ray benchmark grid links to: 5 attrs
# whose names already match the glossary key, 5 bridged by the alias
# table.
_XRAY_LINKED_KEYS = {
    # attr == glossary key
    "total_patient_days", "occupancy_rate", "medicare_day_pct",
    "medicaid_day_pct", "net_to_gross_ratio",
    # via _XRAY_ATTR_TO_GLOSSARY_KEY
    "commercial_pct", "payer_diversity", "revenue_per_bed",
    "expense_per_bed", "operating_margin",
}

# Catalog attrs with no glossary card — the guard must render these
# as plain text. Pinned exactly: adding a metric to METRIC_CATALOG
# (or a card to the glossary) should force a deliberate revisit.
_XRAY_UNLINKED_ATTRS = {
    "beds", "net_revenue_per_patient_day",
    "contractual_allowance_rate", "opex_per_patient_day",
    "net_income_margin_on_npr",
}


class XrayAliasTableTests(unittest.TestCase):
    def test_alias_values_all_resolve_in_glossary(self) -> None:
        for attr, key in _XRAY_ATTR_TO_GLOSSARY_KEY.items():
            with self.subTest(attr=attr, key=key):
                self.assertIsNotNone(
                    get_metric_definition(key),
                    f"alias maps {attr!r} → {key!r} but {key!r} "
                    "is not in the glossary registry",
                )

    def test_alias_keys_are_real_catalog_attrs(self) -> None:
        catalog_attrs = {spec.attr for spec in METRIC_CATALOG}
        stale = set(_XRAY_ATTR_TO_GLOSSARY_KEY) - catalog_attrs
        self.assertFalse(
            stale,
            f"alias table has entries for non-catalog attrs: {stale}",
        )

    def test_catalog_partition_linked_vs_unlinked(self) -> None:
        """Re-derive, per catalog attr, what the helper will do:
        resolve through the alias table, then look up the glossary.
        The linkable set must be exactly the 10 expected keys and
        the fall-through set exactly the 5 pinned attrs."""
        linked, unlinked = set(), set()
        for spec in METRIC_CATALOG:
            resolved = _XRAY_ATTR_TO_GLOSSARY_KEY.get(
                spec.attr, spec.attr)
            if get_metric_definition(resolved) is not None:
                linked.add(resolved)
            else:
                unlinked.add(spec.attr)
        self.assertEqual(linked, _XRAY_LINKED_KEYS)
        self.assertEqual(unlinked, _XRAY_UNLINKED_ATTRS)


class XrayPageAnchorTests(unittest.TestCase):
    """Anchors on a real rendered X-Ray report (first CCN in the
    vendored HCRIS universe — same fixture as the headline tests)."""

    @classmethod
    def setUpClass(cls) -> None:
        from rcm_mc.data.hcris import _get_latest_per_ccn
        from rcm_mc.ui.hcris_xray_page import render_hcris_xray_page
        ccn = str(_get_latest_per_ccn().iloc[0]["ccn"])
        cls.html = render_hcris_xray_page(qs={"ccn": [ccn]})

    def test_linked_metric_anchors_present(self) -> None:
        for key in sorted(_XRAY_LINKED_KEYS):
            with self.subTest(key=key):
                self.assertIn(f"/metric-glossary#{key}", self.html)

    def test_every_anchor_on_page_resolves(self) -> None:
        """The load-bearing no-dead-anchor check: every glossary
        anchor the page ships must exist in the registry."""
        anchors = set(_ANCHOR_RE.findall(self.html))
        self.assertTrue(anchors, "expected glossary anchors on the page")
        for key in sorted(anchors):
            with self.subTest(key=key):
                self.assertIsNotNone(
                    get_metric_definition(key),
                    f"page ships dead anchor /metric-glossary#{key}",
                )

    def test_unlinked_and_raw_attrs_produce_no_anchor(self) -> None:
        """Guarded fall-through attrs must not become anchors, and
        aliased attrs must never leak their RAW attr name as an
        anchor (the alias, not the attr, is the glossary key)."""
        never_anchored = _XRAY_UNLINKED_ATTRS | set(
            _XRAY_ATTR_TO_GLOSSARY_KEY)
        for attr in sorted(never_anchored):
            with self.subTest(attr=attr):
                self.assertNotIn(
                    f"/metric-glossary#{attr}", self.html)


class PredictiveScreenerAnchorTests(unittest.TestCase):
    """Part-1 anchors (W2-218) stay resolvable — same no-dead-anchor
    sweep applied to the screener's rendered HTML."""

    @classmethod
    def setUpClass(cls) -> None:
        from rcm_mc.data.hcris import _get_latest_per_ccn
        from rcm_mc.ui.predictive_screener import (
            render_predictive_screener)
        cls.html = render_predictive_screener(
            _get_latest_per_ccn(), "state=TX")

    def test_header_anchors_present(self) -> None:
        for key in ("net_patient_revenue", "operating_margin",
                    "denial_rate", "days_in_ar"):
            with self.subTest(key=key):
                self.assertIn(f"/metric-glossary#{key}", self.html)

    def test_every_anchor_on_page_resolves(self) -> None:
        anchors = set(_ANCHOR_RE.findall(self.html))
        self.assertTrue(anchors, "expected glossary anchors on the page")
        for key in sorted(anchors):
            with self.subTest(key=key):
                self.assertIsNotNone(
                    get_metric_definition(key),
                    f"page ships dead anchor /metric-glossary#{key}",
                )


class HelperGuardRegressionTests(unittest.TestCase):
    """A bogus term must NOT produce a link — the guard returns the
    escaped label, with no <a> and no glossary href."""

    def test_bogus_key_renders_plain_text(self) -> None:
        out = metric_label_link(
            "Days in A/R & Aging", "totally_bogus_metric_key")
        self.assertNotIn("<a ", out)
        self.assertNotIn("metric-glossary", out)
        self.assertEqual(out, "Days in A/R &amp; Aging")

    def test_bogus_alias_target_renders_plain_text(self) -> None:
        out = metric_label_link(
            "Beds", "beds", alias={"beds": "not_a_glossary_key"})
        self.assertNotIn("<a ", out)
        self.assertNotIn("metric-glossary", out)
        self.assertEqual(out, "Beds")


if __name__ == "__main__":
    unittest.main()
