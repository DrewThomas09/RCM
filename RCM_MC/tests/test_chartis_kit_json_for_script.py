"""ck_json_for_script -- safe JSON embedding inside a <script> element.

A <script> is an HTML raw-text element: the parser does NOT decode
character references in its content. So html.escape()-ing a JSON blob
leaves literal &quot; in the text and the browser's
JSON.parse(el.textContent) throws -- which had silently aborted the
analysis-workbench bridge IIFE (dead sliders + presets) and the explain
panel. This helper escapes only what can break out of / split the script
element; JSON.parse decodes the \\uXXXX back.
"""

import json
import unittest

from rcm_mc.ui._chartis_kit import ck_json_for_script


class TestCkJsonForScript(unittest.TestCase):
    def test_roundtrips_a_dict(self):
        data = {"deal_id": "acme", "assumptions": [{"metric": "denial_rate",
                                                    "current": 12.0,
                                                    "target": 7.0}]}
        out = ck_json_for_script(data)
        # The output is what the browser feeds to JSON.parse verbatim.
        self.assertEqual(json.loads(out), data)

    def test_not_html_escaped(self):
        """The classic regression: structural quotes must stay as " (not
        &quot;) so JSON.parse of the raw <script> text works."""
        out = ck_json_for_script({"k": "v"})
        self.assertNotIn("&quot;", out)
        self.assertIn('"k"', out)

    def test_cannot_break_out_of_script(self):
        """A value containing </script> must not appear literally -- it would
        otherwise terminate the embedding element."""
        data = {"name": "Evil</script><script>alert(1)</script>"}
        out = ck_json_for_script(data)
        self.assertNotIn("</script>", out)
        self.assertNotIn("<script>", out)
        # ...yet the value survives a real parse intact.
        self.assertEqual(json.loads(out)["name"], data["name"])

    def test_escapes_angle_brackets_and_amp(self):
        out = ck_json_for_script({"x": "<a> & </b>"})
        # Each only survives as its \\uXXXX escape, never bare.
        self.assertNotIn("<", out)
        self.assertNotIn(">", out)
        self.assertNotIn("&", out)
        self.assertEqual(json.loads(out)["x"], "<a> & </b>")

    def test_escapes_line_and_paragraph_separators(self):
        # U+2028 / U+2029 are valid in JSON but historically break JS source.
        value = "a\u2028b\u2029c"
        out = ck_json_for_script({"x": value})
        self.assertNotIn("\u2028", out)
        self.assertNotIn("\u2029", out)
        self.assertEqual(json.loads(out)["x"], value)

    def test_accepts_pre_serialised_string(self):
        """Callers that already json.dumps()-ed pass the string straight in;
        it must not be double-encoded into a JSON string literal."""
        pre = json.dumps({"a": 1})
        out = ck_json_for_script(pre)
        self.assertEqual(json.loads(out), {"a": 1})


if __name__ == "__main__":
    unittest.main()
