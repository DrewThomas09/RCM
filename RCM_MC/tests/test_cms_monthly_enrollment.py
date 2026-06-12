"""CMS Medicare Monthly Enrollment client — state/county bene splits.

The live client must fail closed (no fabricated enrollment) when egress
is blocked, parse a mocked data-api payload (aliases, comma counts,
suppressed cells), and walk the publication year back. No network.
"""
from __future__ import annotations

import json
import unittest
from unittest import mock

from rcm_mc.data import cms_monthly_enrollment as me


class _Resp:
    def __init__(self, d):
        self._b = json.dumps(d).encode()

    def read(self):
        return self._b

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


class ParseTests(unittest.TestCase):
    def test_to_int_commas_and_suppression(self):
        self.assertEqual(me._to_int("4,712,345"), 4_712_345)
        self.assertEqual(me._to_int("12"), 12)
        # Suppressed cells must be None — distinguishable from zero.
        self.assertIsNone(me._to_int("*"))
        self.assertIsNone(me._to_int(""))
        self.assertIsNone(me._to_int(None))
        self.assertIsNone(me._to_int("N/A"))

    def test_parse_row_aliases(self):
        row = me._parse_row({
            "BENE_GEO_LVL": "County", "BENE_STATE_ABRVTN": "tx",
            "BENE_COUNTY_DESC": "Harris", "BENE_FIPS_CD": "48201",
            "YEAR": "2024", "MONTH": "Year",
            "TOT_BENES": "520,000", "ORGNL_MDCR_BENES": "230,000",
            "MA_AND_OTH_BENES": "290,000", "AGED_TOT_BENES": "450,000",
            "DSBLD_TOT_BENES": "70,000",
        })
        self.assertEqual(row["geo_level"], "County")
        self.assertEqual(row["state"], "TX")
        self.assertEqual(row["fips"], "48201")
        self.assertEqual(row["year"], 2024)
        self.assertEqual(row["total_benes"], 520_000)
        self.assertEqual(row["ffs_benes"], 230_000)
        self.assertEqual(row["ma_benes"], 290_000)


class FetchTests(unittest.TestCase):
    def test_no_dataset_fails_closed(self):
        with mock.patch.object(me, "resolve_monthly_enrollment_dataset",
                               lambda timeout=0: ""):
            self.assertEqual(
                me.fetch_enrollment_rows("TX", "County", 2024), [])
            self.assertEqual(me.fetch_state_medicare_base("TX"), {})

    def test_network_error_fails_closed(self):
        def _boom(req, timeout=0, context=None):
            raise OSError("egress blocked")
        with mock.patch.object(me, "resolve_monthly_enrollment_dataset",
                               lambda timeout=0: "ds-1"), \
             mock.patch.object(me.urllib.request, "urlopen", _boom):
            self.assertEqual(
                me.fetch_enrollment_rows("TX", "State", 2024), [])

    def test_parses_mocked_payload(self):
        payload = [
            {"BENE_GEO_LVL": "County", "BENE_STATE_ABRVTN": "TX",
             "BENE_COUNTY_DESC": "Harris", "BENE_FIPS_CD": "48201",
             "YEAR": "2024", "MONTH": "Year", "TOT_BENES": "520,000",
             "ORGNL_MDCR_BENES": "230,000", "MA_AND_OTH_BENES": "290,000"},
            {"BENE_GEO_LVL": "County", "BENE_STATE_ABRVTN": "TX",
             "BENE_COUNTY_DESC": "Loving", "BENE_FIPS_CD": "48301",
             "YEAR": "2024", "MONTH": "Year", "TOT_BENES": "*",
             "ORGNL_MDCR_BENES": "*", "MA_AND_OTH_BENES": "*"},
        ]
        with mock.patch.object(me, "resolve_monthly_enrollment_dataset",
                               lambda timeout=0: "ds-1"), \
             mock.patch.object(
                 me.urllib.request, "urlopen",
                 lambda req, timeout=0, context=None: _Resp(payload)):
            rows = me.fetch_enrollment_rows("TX", "County", 2024)
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["total_benes"], 520_000)
        self.assertIsNone(rows[1]["total_benes"])   # suppressed, not 0


class StateBaseTests(unittest.TestCase):
    def test_year_walkback_to_latest_published(self):
        published = {
            2024: {
                "State": [{"geo_level": "State", "state": "TX",
                           "county": "", "fips": "", "year": 2024,
                           "month": "Year", "total_benes": 4_700_000,
                           "ffs_benes": 2_300_000, "ma_benes": 2_400_000,
                           "aged_benes": 4_000_000,
                           "disabled_benes": 700_000, "dual_benes": None}],
                "County": [{"geo_level": "County", "state": "TX",
                            "county": "Harris", "fips": "48201",
                            "year": 2024, "month": "Year",
                            "total_benes": 520_000, "ffs_benes": 230_000,
                            "ma_benes": 290_000, "aged_benes": None,
                            "disabled_benes": None, "dual_benes": None}],
            },
        }

        def _fetch(state, geo, year, dataset="", timeout=0):
            return published.get(year, {}).get(geo, [])

        with mock.patch.object(me, "resolve_monthly_enrollment_dataset",
                               lambda timeout=0: "ds-1"), \
             mock.patch.object(me, "fetch_enrollment_rows", _fetch):
            base = me.fetch_state_medicare_base("TX")
        # Walked back from the current year to the published 2024 rows.
        self.assertEqual(base["year"], 2024)
        self.assertEqual(base["state"]["total_benes"], 4_700_000)
        self.assertEqual(len(base["counties"]), 1)
        self.assertEqual(base["counties"][0]["fips"], "48201")
        self.assertIn("2024", base["period"])

    def test_nothing_published_fails_closed(self):
        with mock.patch.object(me, "resolve_monthly_enrollment_dataset",
                               lambda timeout=0: "ds-1"), \
             mock.patch.object(
                 me, "fetch_enrollment_rows",
                 lambda *a, **k: []):
            self.assertEqual(me.fetch_state_medicare_base("TX"), {})


if __name__ == "__main__":
    unittest.main()
