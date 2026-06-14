"""`rcm-mc data payer-mix` — Census SAHIE county uninsured rates.

SAHIE is patched via census_market.fetch_sahie's injected opener so the CLI
sorting/formatting is exercised offline. Covers ranking, suppression sinking
to the end, JSON, and the state guard.
"""
from __future__ import annotations

import contextlib
import io
import json
import unittest

from rcm_mc.cli import data_main
from rcm_mc.data_public import census_market as cm


def _run(argv):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = data_main(argv)
    return rc, buf.getvalue()


_PAYLOAD = [
    ["NAME", "NUI_PT", "PCTUI_PT", "time", "state", "county"],
    ["Low County", "1000", "5.0", "2021", "08", "001"],
    ["High County", "9000", "14.0", "2021", "08", "003"],
    ["Hidden County", "", "-1", "2021", "08", "005"],   # suppressed
]


class PayerMixCliTests(unittest.TestCase):
    def setUp(self):
        self._orig = cm.fetch_sahie
        cm.fetch_sahie = (lambda **kw:  # type: ignore[assignment]
                          self._orig(api_key="",
                                     opener=lambda u, h, t: json.dumps(_PAYLOAD).encode(),
                                     **{k: v for k, v in kw.items() if k != "api_key"}))

    def tearDown(self):
        cm.fetch_sahie = self._orig  # type: ignore[assignment]

    def test_sorted_by_rate_desc(self):
        rc, out = _run(["payer-mix", "--state", "CO"])
        self.assertEqual(rc, 0)
        self.assertLess(out.index("High County"), out.index("Low County"))

    def test_json_all_counties_suppression_last(self):
        rc, out = _run(["payer-mix", "--state", "CO", "--json"])
        self.assertEqual(rc, 0)
        rows = json.loads(out)
        self.assertEqual(rows[0]["county"], "High County")     # 14.0%
        self.assertIsNone(rows[-1]["uninsured_pct"])           # suppressed last

    def test_unknown_state_rejected(self):
        rc, _ = _run(["payer-mix", "--state", "ZZ"])
        self.assertEqual(rc, 2)


if __name__ == "__main__":
    unittest.main()
