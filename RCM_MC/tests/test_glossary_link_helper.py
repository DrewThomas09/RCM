"""Test for the shared /metric-glossary anchor-link helper
(campaign target 4A, loop 107).

Phase 4A wraps every metric mention on every page in an
anchor link to /metric-glossary#<key>. Loop 106 introduced
the wrapping pattern in ebitda_bridge_page.py with a
bridge-local helper. This loop lifts that helper to a
shared module (rcm_mc/ui/_glossary_link.py) so multiple
pages can use it without duplicating the alias-table /
fallthrough logic.

Asserts:
  - metric_label_link wraps a known glossary key in an
    `<a href="/metric-glossary#<key>">` anchor with a
    dotted underline.
  - The optional alias table resolves divergent caller-
    local keys (e.g., "cmi" -> "case_mix_index").
  - Unknown / empty keys fall through to plain escaped
    text (no dead links).
  - The label argument is HTML-escaped.

Plus regression pins for the 2 callers that adopted the
shared helper this loop:
  - ebitda_bridge_page._lever_label_link still wraps known
    bridge metrics correctly (now delegates to the shared
    helper).
  - data_room_page now imports metric_label_link and uses it
    at the calibration-table and entry-history render sites.
"""
from __future__ import annotations

import re
import unittest
from pathlib import Path

from rcm_mc.ui._glossary_link import metric_label_link
from rcm_mc.ui.ebitda_bridge_page import _lever_label_link


_DATA_ROOM_PATH = (
    Path(__file__).resolve().parents[1]
    / "rcm_mc" / "ui" / "data_room_page.py"
)


class GlossaryLinkHelperTests(unittest.TestCase):
    def test_known_key_produces_anchor(self) -> None:
        html = metric_label_link("Denial Rate", "denial_rate")
        self.assertIn('href="/metric-glossary#denial_rate"', html)
        self.assertIn("Denial Rate", html)
        self.assertIn("border-bottom:1px dotted", html)

    def test_alias_table_resolves(self) -> None:
        html = metric_label_link(
            "CMI", "cmi", alias={"cmi": "case_mix_index"},
        )
        self.assertIn('href="/metric-glossary#case_mix_index"', html)
        self.assertNotIn("#cmi", html)

    def test_unknown_key_falls_through(self) -> None:
        html = metric_label_link("Mystery", "no_such_metric")
        self.assertNotIn("<a", html)
        self.assertNotIn("href", html)
        self.assertIn("Mystery", html)

    def test_empty_key_falls_through(self) -> None:
        """An empty metric_key (caller passing default "") must
        also fall through to plain text — not produce a link to
        /metric-glossary# (just '#' as a fragment)."""
        html = metric_label_link("Untyped", "")
        self.assertNotIn("<a", html)
        self.assertIn("Untyped", html)

    def test_label_is_html_escaped(self) -> None:
        """A label containing < and > should be escaped to
        prevent HTML injection from data-driven label sources."""
        html = metric_label_link(
            "<script>", "denial_rate",
        )
        self.assertNotIn("<script>", html)
        self.assertIn("&lt;script&gt;", html)


class EbitdaBridgeDelegatesToSharedHelperTests(unittest.TestCase):
    """The bridge's _lever_label_link is now a thin wrapper
    around metric_label_link — confirm it still produces the
    same output as before."""

    def test_bridge_known_metric(self) -> None:
        html = _lever_label_link("Denial Rate Reduction", "denial_rate")
        self.assertIn('href="/metric-glossary#denial_rate"', html)

    def test_bridge_cmi_alias(self) -> None:
        html = _lever_label_link("CDI / Case Mix Index", "cmi")
        self.assertIn('href="/metric-glossary#case_mix_index"', html)

    def test_bridge_unknown_falls_through(self) -> None:
        html = _lever_label_link("Mystery", "no_such_metric")
        self.assertNotIn("<a", html)


class DataRoomAdoptsSharedHelperTests(unittest.TestCase):
    """data_room_page should now import the shared helper at
    module top and use it at both metric-label render sites
    (calibration table + entry history)."""

    def setUp(self) -> None:
        self.text = _DATA_ROOM_PATH.read_text(encoding="utf-8")

    def test_imports_shared_helper(self) -> None:
        self.assertIn(
            "from ._glossary_link import metric_label_link",
            self.text,
            "data_room_page should import metric_label_link",
        )

    def test_calibration_table_uses_helper(self) -> None:
        """The calibration-table per-row label render should
        call metric_label_link(cal.label, ...) instead of
        bare _html.escape(cal.label)."""
        self.assertNotIn(
            '_html.escape(cal.label)', self.text,
            "data_room_page calibration table still has "
            "un-linked _html.escape(cal.label)",
        )

    def test_entry_history_uses_helper(self) -> None:
        """The entry-history table per-row label render should
        call metric_label_link(...) instead of bare
        _html.escape(defn.get("label", e.metric))."""
        self.assertNotIn(
            '_html.escape(defn.get("label", e.metric))',
            self.text,
            "data_room_page entry history still has un-linked "
            'bare _html.escape on the metric label',
        )

    def test_helper_referenced_at_least_twice(self) -> None:
        """Two render sites = two calls to metric_label_link."""
        ref_count = len(re.findall(r"metric_label_link\(", self.text))
        self.assertGreaterEqual(
            ref_count, 2,
            f"data_room_page should call metric_label_link "
            f"≥2 times (calibration table + entry history); "
            f"found {ref_count}",
        )


if __name__ == "__main__":
    unittest.main()
