"""State-detail county drilldown (PAGE_INVENTORY top fix, ungated).

/market-data/state/<ST> links into the scoped county explorer and the
state dossier — the county-level layers existed; the state detail just
never linked to them.
"""
from __future__ import annotations

import unittest


class StateDetailDrilldownTests(unittest.TestCase):
    def test_state_detail_links_counties_and_dossier(self):
        from rcm_mc.ui.market_data_page import render_state_detail
        h = render_state_detail("TX")
        self.assertIn('href="/county-explorer?state=TX"', h)
        self.assertIn('href="/state-profile?state=TX"', h)

    def test_state_table_headers_link_glossary(self):
        # PAGE_INVENTORY "link from every KPI label" — the hospital
        # table's metric headers route to the canonical glossary cards.
        from rcm_mc.ui.market_data_page import render_state_detail
        h = render_state_detail("TX")
        self.assertIn('href="/metric-glossary#net_patient_revenue"', h)
        self.assertIn('href="/metric-glossary#operating_margin"', h)

    def test_county_explorer_accepts_state_scope(self):
        from rcm_mc.ui.data_public.county_explorer_page import (
            render_county_explorer)
        h = render_county_explorer({"state": ["TX"]})
        self.assertIn("TX", h)


if __name__ == "__main__":
    unittest.main()
