"""PR 2b — next batch of illustrative analyzers carry honest source headers.

Physician Productivity / Provider Retention / Partner Economics / Mgmt Comp are
hardcoded models today; each must declare its status (ILLUSTRATIVE or DATA
REQUIRED) + purpose + next action via the ck_source_purpose header so none
masquerades as live evidence.
"""
from __future__ import annotations

import unittest

from rcm_mc.ui.data_public.physician_productivity_page import render_physician_productivity
from rcm_mc.ui.data_public.provider_retention_page import render_provider_retention
from rcm_mc.ui.data_public.partner_economics_page import render_partner_economics
from rcm_mc.ui.data_public.mgmt_comp_page import render_mgmt_comp

_CASES = [
    (render_physician_productivity, "ILLUSTRATIVE"),
    (render_provider_retention, "DATA REQUIRED"),
    (render_partner_economics, "DATA REQUIRED"),
    (render_mgmt_comp, "ILLUSTRATIVE"),
]


class IllustrativeLabelBatch2Tests(unittest.TestCase):
    def test_each_has_honest_header(self):
        for render, label in _CASES:
            h = render({})
            with self.subTest(render=render.__name__):
                self.assertIn("ck-sp", h)            # source-purpose header
                self.assertIn(label, h)              # honest status chip
                self.assertIn("ck-sp-purpose", h)    # purpose stated


if __name__ == "__main__":
    unittest.main()
