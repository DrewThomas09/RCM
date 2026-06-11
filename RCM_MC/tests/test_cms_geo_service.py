"""CMS 'by Geography and Service' client — J-code POS by state.

The live client must fail closed (no fabricated claims) when egress is
blocked, parse a mocked Socrata payload, and aggregate facility vs
non-facility services across states/years. No network required.
"""
from __future__ import annotations

import unittest
from unittest import mock

from rcm_mc.data import cms_geo_service as gs


class FetchTests(unittest.TestCase):
    def test_no_dataset_fails_closed(self):
        with mock.patch.object(gs, "resolve_geo_service_dataset",
                               lambda year, timeout=0: ""):
            self.assertEqual(gs.fetch_geo_service_hcpcs("J1745", 2022), [])

    def test_parses_state_pos_rows(self):
        payload = [
            {"Rndrng_Prvdr_Geo_Lvl": "State", "Rndrng_Prvdr_Geo_Desc": "Texas",
             "HCPCS_Cd": "J1745", "Place_Of_Srvc": "F", "Tot_Srvcs": "1000",
             "Tot_Benes": "200"},
            {"Rndrng_Prvdr_Geo_Lvl": "State", "Rndrng_Prvdr_Geo_Desc": "Texas",
             "HCPCS_Cd": "J1745", "Place_Of_Srvc": "O", "Tot_Srvcs": "3000",
             "Tot_Benes": "600"},
        ]

        class _Resp:
            def __init__(self, d):
                import json
                self._b = json.dumps(d).encode()
            def read(self):
                return self._b
            def __enter__(self):
                return self
            def __exit__(self, *a):
                return False

        with mock.patch.object(gs, "resolve_geo_service_dataset",
                               lambda year, timeout=0: "ds-1"), \
             mock.patch.object(
                 gs.urllib.request, "urlopen",
                 lambda req, timeout=0, context=None: _Resp(payload)):
            rows = gs.fetch_geo_service_hcpcs("J1745", 2022)
        self.assertEqual(len(rows), 2)
        self.assertEqual({r["pos"] for r in rows}, {"F", "O"})

    def test_aggregate_computes_nonfacility_pct(self):
        rows = [
            {"state": "Texas", "pos": "F", "services": 1000.0, "benes": 200.0},
            {"state": "Texas", "pos": "O", "services": 3000.0, "benes": 600.0},
        ]
        with mock.patch.object(gs, "resolve_geo_service_dataset",
                               lambda year, timeout=0: "ds-1"), \
             mock.patch.object(gs, "fetch_geo_service_hcpcs",
                               lambda code, yr, dataset="", timeout=0: rows):
            agg = gs.jcode_pos_by_state(["J1745"], [2022])
        slot = agg["Texas"][2022]
        self.assertEqual(slot["facility"], 1000.0)
        self.assertEqual(slot["nonfacility"], 3000.0)
        self.assertAlmostEqual(slot["nonfac_pct"], 0.75)

    def test_aggregate_empty_when_unresolved(self):
        with mock.patch.object(gs, "resolve_geo_service_dataset",
                               lambda year, timeout=0: ""):
            self.assertEqual(gs.jcode_pos_by_state(["J1745"], [2022]), {})


if __name__ == "__main__":
    unittest.main()
