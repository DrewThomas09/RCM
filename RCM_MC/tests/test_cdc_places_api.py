"""CDC PLACES county API + ACS sex client.

These hit live public APIs (CDC Socrata, Census ACS) when egress is
available, and must fail *closed* — never fabricating data — when it is
not. Tests exercise the parsing logic with synthetic API payloads and
the offline fallbacks; no network is required.
"""
from __future__ import annotations

import unittest
from unittest import mock

from rcm_mc.data import cdc_places_api as places
from rcm_mc.data import acs_sex


class PlacesMeasureMapTests(unittest.TestCase):
    def test_named_proxy_measures_present(self):
        # The clinical proxies the analysis depends on must map to real
        # PLACES crude-prevalence columns.
        for friendly, col in (
            ("arthritis", "arthritis_crudeprev"),
            ("kidney_disease", "kidney_crudeprev"),
            ("cancer", "cancer_crudeprev"),
            ("diabetes", "diabetes_crudeprev"),
            ("obesity", "obesity_crudeprev"),
            ("poor_physical_health", "phlth_crudeprev"),
            ("uninsured_18_64", "access2_crudeprev"),
        ):
            self.assertEqual(places.MEASURES[friendly], col)


class PlacesParseTests(unittest.TestCase):
    def _payload(self):
        return [
            {"countyfips": "48201", "countyname": "Harris",
             "stateabbr": "TX", "totalpopulation": "4731145",
             "arthritis_crudeprev": "20.1", "kidney_crudeprev": "3.2",
             "cancer_crudeprev": "5.9", "diabetes_crudeprev": "11.8"},
        ]

    def test_fetch_parses_rows_and_floats(self):
        # Patch urlopen to return our payload once, then an empty page.
        pages = [self._payload(), []]

        class _Resp:
            def __init__(self, data):
                import json
                self._b = json.dumps(data).encode()
            def read(self):
                return self._b
            def __enter__(self):
                return self
            def __exit__(self, *a):
                return False

        def _open(req, timeout=0, context=None):
            return _Resp(pages.pop(0))

        with mock.patch.object(places.urllib.request, "urlopen", _open):
            rows = places.fetch_places_counties(
                "TX", measures=["arthritis", "kidney_disease",
                                "cancer", "diabetes"])
        self.assertEqual(len(rows), 1)
        r = rows[0]
        self.assertEqual(r["county_fips"], "48201")
        self.assertEqual(r["state"], "TX")
        self.assertAlmostEqual(r["arthritis"], 20.1)
        self.assertAlmostEqual(r["kidney_disease"], 3.2)
        self.assertEqual(r["population"], 4731145.0)

    def test_fetch_fails_closed_on_error(self):
        def _boom(req, timeout=0, context=None):
            raise OSError("blocked")
        with mock.patch.object(places.urllib.request, "urlopen", _boom):
            self.assertEqual(places.fetch_places_counties("TX"), [])

    def test_empty_state_returns_empty(self):
        self.assertEqual(places.fetch_places_counties(""), [])


class AcsSexTests(unittest.TestCase):
    def test_female_share_parses(self):
        payload = [
            ["B01001_001E", "B01001_026E", "state", "county"],
            ["1000000", "510000", "48", "201"],
            ["0", "0", "48", "203"],          # zero total → skipped
        ]

        class _Resp:
            def __init__(self, data):
                import json
                self._b = json.dumps(data).encode()
            def read(self):
                return self._b
            def __enter__(self):
                return self
            def __exit__(self, *a):
                return False

        with mock.patch.object(
                acs_sex.urllib.request, "urlopen",
                lambda req, timeout=0, context=None: _Resp(payload)):
            out = acs_sex.fetch_acs_county_female("48")
        self.assertEqual(out["48201"], 0.51)
        self.assertNotIn("48203", out)

    def test_fallback_to_state_constant(self):
        # No live data → published statewide share, labeled real value.
        self.assertAlmostEqual(
            acs_sex.female_share_for("48201", "TX", {}), 0.497)
        # A present live value wins.
        self.assertAlmostEqual(
            acs_sex.female_share_for("48201", "TX", {"48201": 0.512}),
            0.512)

    def test_unknown_state_uses_us_fallback(self):
        self.assertAlmostEqual(
            acs_sex.female_share_for("99999", "ZZ", {}),
            acs_sex.STATE_FEMALE_SHARE["US"])


if __name__ == "__main__":
    unittest.main()
