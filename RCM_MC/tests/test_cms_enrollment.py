"""CMS Medicare Monthly Enrollment client.

Provides the total-Medicare denominator for a true MA-penetration rate.
The live fetch must fail closed (fall back to the published total, never
fabricate) when egress is blocked, and parse a mocked payload otherwise.
"""
from __future__ import annotations

import unittest
from unittest import mock

from rcm_mc.data import cms_enrollment as ce


class FallbackTests(unittest.TestCase):
    def test_offline_uses_published_total(self):
        out = ce.total_medicare_for("TX")          # fetch_live default False
        self.assertFalse(out["live"])
        self.assertEqual(out["total"], ce.STATE_TOTAL_MEDICARE["TX"])

    def test_unknown_state_uses_us_fallback(self):
        out = ce.total_medicare_for("ZZ")
        self.assertEqual(out["total"], ce.STATE_TOTAL_MEDICARE["US"])

    def test_fetch_fails_closed_when_unresolved(self):
        with mock.patch.object(ce, "_resolve_dataset",
                               lambda timeout=0: ""):
            self.assertEqual(ce.fetch_total_medicare("TX"), {"live": False})


class ParseTests(unittest.TestCase):
    def test_picks_latest_month_total(self):
        payload = [
            {"BENE_GEO_LVL": "State", "BENE_STATE_ABRVTN": "TX",
             "MONTH": "2024-01", "TOT_BENES": "4500000",
             "MA_AND_OTH_BENES": "2100000", "ORGNL_MDCR_BENES": "2400000"},
            {"BENE_GEO_LVL": "State", "BENE_STATE_ABRVTN": "TX",
             "MONTH": "2024-06", "TOT_BENES": "4650000",
             "MA_AND_OTH_BENES": "2200000", "ORGNL_MDCR_BENES": "2450000"},
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

        with mock.patch.object(ce, "_resolve_dataset",
                               lambda timeout=0: "ds-1"), \
             mock.patch.object(
                 ce.urllib.request, "urlopen",
                 lambda req, timeout=0, context=None: _Resp(payload)):
            out = ce.fetch_total_medicare("TX")
        self.assertTrue(out["live"])
        self.assertEqual(out["total"], 4_650_000)   # latest month
        self.assertEqual(out["ma_and_other"], 2_200_000)


if __name__ == "__main__":
    unittest.main()
