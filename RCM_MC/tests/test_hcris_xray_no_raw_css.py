"""Regression: HCRIS X-Ray must never render raw CSS text in the page body.

A partner saw `.xr-ws{display:grid;grid-template-columns:...` printed at the
top of the HCRIS X-Ray page. Cause: the landing renderer concatenated the raw
`_WORKSTATION_CSS` string into the body instead of passing it through
`extra_css` (which the shell wraps in <style>). This test strips every
<style> block and asserts no CSS selector/declaration leaks into the visible
body — on both the landing and the report render paths.
"""
from __future__ import annotations

import re
import unittest

from rcm_mc.ui.hcris_xray_page import render_hcris_xray_page

# CSS fragments that must only ever appear INSIDE a <style> block.
_CSS_FRAGMENTS = (".xr-ws{", ".xr-seg{", ".xr-ws-field", "grid-template-columns:",
                  ".xr-topfind", "display:grid;")


def _body_without_styles(html: str) -> str:
    return re.sub(r"<style>.*?</style>", "", html, flags=re.DOTALL)


class HcrisXrayNoRawCssTests(unittest.TestCase):
    def _assert_no_leak(self, html: str, label: str):
        body = _body_without_styles(html)
        for frag in _CSS_FRAGMENTS:
            self.assertNotIn(
                frag, body,
                f"raw CSS {frag!r} leaked into the {label} body (outside <style>)")

    def test_landing_has_no_raw_css_in_body(self):
        self._assert_no_leak(render_hcris_xray_page({}), "landing")

    def test_search_results_have_no_raw_css_in_body(self):
        # A search that resolves through the engine exercises the report path.
        self._assert_no_leak(render_hcris_xray_page({"q": ["hospital"]}),
                             "search/report")

    def test_workstation_css_is_present_but_only_in_style(self):
        html = render_hcris_xray_page({})
        self.assertIn(".xr-ws{", html)                       # styling still ships
        self.assertNotIn(".xr-ws{", _body_without_styles(html))  # but not in body


if __name__ == "__main__":
    unittest.main()
