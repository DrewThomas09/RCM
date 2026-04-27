"""Test for the 4A metric→glossary link wrapping in
ui/value_tracking_page.py (campaign target 4A, loop 109).

Phase 4A wraps every metric mention on every page in an anchor
to /metric-glossary#<key>. The Value Creation Tracker page
displays lever names in two display surfaces:
  - lever-by-lever realization comparison (line 117 area)
  - frozen bridge plan section (line 149 area)
Both used to render `_html.escape(lev["lever"|"name"][:25])`;
both now route through the shared metric_label_link helper.

The lever NAME (not metric key) is what's stored, because
``pe.value_tracker`` lives in the restricted ml/pe/etc package
list and the campaign brief forbids touching it without user
approval. So we build a name→glossary-key reverse lookup table
at module-import time by reading _LEVER_CONFIG +
_LEVER_METRIC_TO_GLOSSARY from the bridge module.

The form dropdown at line 170 (_route_value_tracker_record's
<option> elements) is intentionally NOT wrapped — <option>
content is plain text, and HTML inside breaks the form.

Asserts:
  - _LEVER_NAME_TO_GLOSSARY_KEY has every lever name from
    _LEVER_CONFIG and resolves each to a real glossary key.
  - The two display sites that used to call
    `_html.escape(lev["lever"|"name"][:25])` are gone.
  - The shared helper is referenced ≥2 times in the module.
  - The form-dropdown option content is unchanged (still
    plain `_html.escape(lev["name"])` — wrapping in HTML
    would break the <select>).
"""
from __future__ import annotations

import re
import unittest
from pathlib import Path

from rcm_mc.ui.value_tracking_page import _LEVER_NAME_TO_GLOSSARY_KEY
from rcm_mc.ui.metric_glossary import get_metric_definition


_MODULE_PATH = (
    Path(__file__).resolve().parents[1]
    / "rcm_mc" / "ui" / "value_tracking_page.py"
)


class ValueTrackingGlossaryLinksTests(unittest.TestCase):
    def test_reverse_table_covers_every_lever(self) -> None:
        """Every entry in the bridge's _LEVER_CONFIG must
        appear as a key in the reverse lookup; every value
        must be a real glossary key."""
        from rcm_mc.ui.ebitda_bridge_page import _LEVER_CONFIG
        names_in_config = {cfg["name"] for cfg in _LEVER_CONFIG}
        names_in_lookup = set(_LEVER_NAME_TO_GLOSSARY_KEY.keys())
        self.assertEqual(
            names_in_config, names_in_lookup,
            f"reverse-table coverage mismatch: "
            f"missing={names_in_config - names_in_lookup}, "
            f"extra={names_in_lookup - names_in_config}",
        )
        for name, key in _LEVER_NAME_TO_GLOSSARY_KEY.items():
            with self.subTest(name=name, key=key):
                self.assertIsNotNone(
                    get_metric_definition(key),
                    f"reverse-table maps {name!r} → {key!r} "
                    f"but {key!r} is not in the glossary",
                )

    def test_cmi_alias_resolved_in_lookup(self) -> None:
        """The bridge's "CDI / Case Mix Index" lever stores
        metric_key="cmi"; the reverse-table entry must resolve
        to the glossary key "case_mix_index", not "cmi"."""
        self.assertEqual(
            _LEVER_NAME_TO_GLOSSARY_KEY.get("CDI / Case Mix Index"),
            "case_mix_index",
        )

    def test_display_render_sites_use_helper(self) -> None:
        """The two display render sites (lever realization
        comparison + bridge plan section) should no longer
        contain the bare _html.escape(lev[...]) pattern with
        the metric label."""
        text = _MODULE_PATH.read_text(encoding="utf-8")
        # Realization-table site (was: _html.escape(lev["lever"][:25]))
        self.assertNotIn(
            '_html.escape(lev["lever"][:25])', text,
            "value_tracking_page realization table still has "
            'un-linked _html.escape(lev["lever"][:25])',
        )
        # Bridge-plan site (was: _html.escape(lev["name"][:25]))
        self.assertNotIn(
            '_html.escape(lev["name"][:25])', text,
            "value_tracking_page bridge plan section still has "
            'un-linked _html.escape(lev["name"][:25])',
        )

    def test_helper_referenced_in_module(self) -> None:
        """Module imports metric_label_link and uses it ≥2x."""
        text = _MODULE_PATH.read_text(encoding="utf-8")
        self.assertIn(
            "from ._glossary_link import metric_label_link",
            text,
        )
        ref_count = len(re.findall(r"metric_label_link\(", text))
        self.assertGreaterEqual(
            ref_count, 2,
            f"metric_label_link should be called ≥2x; "
            f"found {ref_count}",
        )

    def test_form_dropdown_option_not_wrapped(self) -> None:
        """The form <option> at line ~170 must NOT be wrapped
        in metric_label_link — <option> content is plain text
        and HTML inside breaks the <select> form control. The
        bare _html.escape pattern for the dropdown should
        survive the migration."""
        text = _MODULE_PATH.read_text(encoding="utf-8")
        # The dropdown line uses lev["name"] (no [:25] truncation)
        # for both the value and the display, both wrapped in
        # _html.escape. Confirm the unique full-length form
        # still uses bare escape.
        self.assertIn(
            'f\'<option value="{_html.escape(lev["name"])}">'
            '{_html.escape(lev["name"])}</option>\'',
            text,
            "form dropdown <option> should still use bare "
            "_html.escape — wrapping HTML inside <option> "
            "breaks the form control",
        )


if __name__ == "__main__":
    unittest.main()
