"""HCRIS X-Ray render hygiene: a single <h1> and no literal 'nan' cells.

The page stacks a "HCRIS X-Ray" masthead, a target-overview card, and a
peer-benchmark block — the latter two were each emitting their own <h1>
(three total). And a dataless peer leaked a literal 'nan' into the peer
roster's Distance / NPR columns. Both are partner-facing on a core
diligence surface.
"""

import math
import re
import unittest

from rcm_mc.diligence.hcris_xray import PeerMatch, compute_metrics
from rcm_mc.ui.hcris_xray_page import _peer_table, render_hcris_xray_page

# A cell whose entire content is "nan" / "nan%" (not the substring inside
# "financial", "covenant", "maintenance", …).
_BAD_NAN = re.compile(r">\s*nan\b|nan%|\bnan\s*<", re.IGNORECASE)


class TestHcrisXrayRenderHygiene(unittest.TestCase):
    def test_single_h1(self):
        page = render_hcris_xray_page({"ccn": ["010001"]})
        self.assertEqual(
            len(re.findall(r"<h1[ >]", page)), 1,
            "HCRIS X-Ray must render exactly one <h1>",
        )

    def test_no_literal_nan_cell_on_real_render(self):
        page = render_hcris_xray_page({"ccn": ["010001"]})
        self.assertIsNone(
            _BAD_NAN.search(page),
            "a 'nan' cell leaked into the rendered page",
        )

    def test_peer_table_dataless_peer_shows_dash_not_nan(self):
        """Deterministic guard: a peer with NaN metrics renders em-dashes,
        never 'nan', in the Distance / NPR / Beds / margin columns."""
        h = compute_metrics({})
        for attr in ("beds", "net_patient_revenue", "medicare_day_pct",
                     "operating_margin_on_npr"):
            setattr(h, attr, math.nan)
        peer = PeerMatch(hospital=h, distance=math.nan, same_state=True,
                         same_region=False, same_size_cohort=True)
        html = _peer_table([peer])
        self.assertIsNone(_BAD_NAN.search(html))
        self.assertIn("—", html)


if __name__ == "__main__":
    unittest.main()
