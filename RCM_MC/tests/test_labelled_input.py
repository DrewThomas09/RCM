"""tests for ``labelled_input`` (P97)."""
from __future__ import annotations

import unittest

from rcm_mc.ui._ui_kit import labelled_input


class StructureAndContent(unittest.TestCase):

    def test_emits_label_and_input(self) -> None:
        html = labelled_input("revenue", label="Revenue Y0 (USD)")
        self.assertIn("<label", html)
        self.assertIn("<input", html)
        self.assertIn("Revenue Y0 (USD)", html)
        self.assertIn('name="revenue"', html)

    def test_label_for_matches_input_id(self) -> None:
        html = labelled_input("revenue", label="Revenue")
        self.assertIn('for="li-revenue"', html)
        self.assertIn('id="li-revenue"', html)


class PlaceholderPrefixing(unittest.TestCase):

    def test_placeholder_prefixed_with_eg(self) -> None:
        html = labelled_input(
            "ccn", label="HCRIS CCN",
            placeholder="010001",
        )
        self.assertIn('placeholder="e.g., 010001"', html)

    def test_existing_eg_preserved(self) -> None:
        # Don't double-prefix if caller already provides the example
        # marker.
        html = labelled_input(
            "ccn", label="HCRIS CCN",
            placeholder="e.g., 010001",
        )
        self.assertNotIn("e.g., e.g.,", html)
        self.assertIn('placeholder="e.g., 010001"', html)

    def test_no_placeholder_omits_attribute(self) -> None:
        html = labelled_input("x", label="X")
        self.assertNotIn("placeholder=", html)


class TypeAndExtraAttrs(unittest.TestCase):

    def test_type_passes_through(self) -> None:
        html = labelled_input("rev", label="Revenue", type="number")
        self.assertIn('type="number"', html)

    def test_required(self) -> None:
        html = labelled_input("name", label="Name", required=True)
        self.assertIn(" required", html)

    def test_extra_attrs(self) -> None:
        html = labelled_input(
            "x", label="X",
            extra_attrs={"min": "0", "max": "100", "step": "0.5"},
        )
        self.assertIn('min="0"', html)
        self.assertIn('max="100"', html)
        self.assertIn('step="0.5"', html)


class HtmlEscaping(unittest.TestCase):

    def test_label_escaped(self) -> None:
        html = labelled_input("x", label="<script>")
        self.assertIn("&lt;script&gt;", html)

    def test_value_escaped(self) -> None:
        html = labelled_input("x", label="X", value='"&hack')
        self.assertNotIn('"&hack', html)


if __name__ == "__main__":
    unittest.main()
