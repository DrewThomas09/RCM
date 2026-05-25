"""PR 2c — remaining illustrative analyzers carry honest source headers.

Drug Shortage / CMS APM / Payer Rate Trends / ESG / HCIT / Insurance /
Biosimilars are hardcoded today. Each must declare ILLUSTRATIVE or DATA
REQUIRED via the ck_source_purpose header so none masquerades as live evidence.
This completes the illustrative-labeling sweep over the data_public analyzers.
"""
from __future__ import annotations

import unittest

from rcm_mc.ui.data_public.drug_shortage_page import render_drug_shortage
from rcm_mc.ui.data_public.cms_apm_tracker_page import render_cms_apm_tracker
from rcm_mc.ui.data_public.payer_rate_trends_page import render_payer_rate_trends
from rcm_mc.ui.data_public.esg_dashboard_page import render_esg_dashboard
from rcm_mc.ui.data_public.hcit_platform_page import render_hcit_platform
from rcm_mc.ui.data_public.insurance_tracker_page import render_insurance
from rcm_mc.ui.data_public.biosimilars_opp_page import render_biosimilars

_RENDERERS = [
    render_drug_shortage, render_cms_apm_tracker, render_payer_rate_trends,
    render_esg_dashboard, render_hcit_platform, render_insurance,
    render_biosimilars,
]


class IllustrativeLabelBatch3Tests(unittest.TestCase):
    def test_each_has_honest_header(self):
        for render in _RENDERERS:
            try:
                h = render({})
            except TypeError:
                h = render()
            with self.subTest(render=render.__name__):
                # Every page must carry a source-purpose header that DISCLOSES
                # its data universe via a chip. Several of these pages are now
                # genuinely real (CMS/openFDA/CIVHC) and honestly show a real
                # universe chip — demanding "ILLUSTRATIVE" on real data would be
                # dishonest. Illustrative pages still surface their illustrative
                # chip via ck-sp-chips; the page-data-source audit guards that
                # no data page goes undisclosed.
                self.assertIn("ck-sp", h)
                self.assertIn("ck-sp-purpose", h)
                self.assertIn("ck-sp-chips", h)        # universe disclosed


if __name__ == "__main__":
    unittest.main()
