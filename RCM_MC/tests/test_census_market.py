"""Census CBP + SAHIE market-context clients.

Pure request builders are asserted directly; normalization (header-row zip,
suppression handling, fail-closed) is exercised with a fake opener — no socket.
The Census key is read from the environment and is optional; both paths covered.
"""
from __future__ import annotations

import json
import os
import unittest

from rcm_mc.data_public import census_market as cm
from rcm_mc.data_public.public_api_clients import PublicApiError


def _opener(payload):
    def _open(url, headers, timeout):
        assert "User-Agent" in headers
        return json.dumps(payload).encode()
    return _open


class RequestBuilderTests(unittest.TestCase):
    def test_cbp_request_threads_naics_geo_and_key(self):
        r = cm.cbp_request("621111", state_fips="08", year=2022, api_key="K")
        self.assertIn("/2022/cbp", r.url)
        self.assertEqual(r.params["NAICS2017"], "621111")
        self.assertEqual(r.params["for"], "county:*")
        self.assertEqual(r.params["in"], "state:08")
        self.assertEqual(r.params["key"], "K")

    def test_cbp_request_omits_key_and_scope_when_absent(self):
        r = cm.cbp_request("621610")
        self.assertNotIn("key", r.params)
        self.assertNotIn("in", r.params)

    def test_sahie_request_uses_time_param_not_path_year(self):
        r = cm.sahie_request(state_fips="08", year=2021, api_key="K")
        self.assertTrue(r.url.endswith("/timeseries/healthins/sahie"))
        self.assertEqual(r.params["time"], "2021")
        self.assertEqual(r.params["in"], "state:08")


class NormalizationTests(unittest.TestCase):
    def test_fetch_cbp_zips_header_and_builds_fips(self):
        payload = [
            ["NAME", "ESTAB", "EMP", "state", "county"],
            ["Denver County, Colorado", "412", "5183", "08", "031"],
        ]
        out = cm.fetch_cbp("621111", state_fips="08", api_key="",
                           opener=_opener(payload))
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]["fips"], "08031")
        self.assertEqual(out[0]["establishments"], 412)
        self.assertEqual(out[0]["employment"], 5183)
        self.assertEqual(out[0]["naics"], "621111")

    def test_fetch_cbp_preserves_suppression_as_none(self):
        payload = [
            ["NAME", "ESTAB", "EMP", "state", "county"],
            ["Tiny County", "-666666666", "", "08", "111"],
        ]
        out = cm.fetch_cbp("621111", api_key="", opener=_opener(payload))
        self.assertIsNone(out[0]["establishments"])  # negative sentinel → None
        self.assertIsNone(out[0]["employment"])      # blank → None

    def test_fetch_sahie_normalizes_uninsured(self):
        payload = [
            ["NAME", "NUI_PT", "PCTUI_PT", "time", "state", "county"],
            ["Denver County", "62000", "8.7", "2021", "08", "031"],
        ]
        out = cm.fetch_sahie(state_fips="08", api_key="",
                             opener=_opener(payload))
        self.assertEqual(out[0]["uninsured"], 62000)
        self.assertAlmostEqual(out[0]["uninsured_pct"], 8.7)
        self.assertEqual(out[0]["fips"], "08031")

    def test_empty_payload_is_empty_list_not_error(self):
        out = cm.fetch_cbp("621111", api_key="", opener=_opener([["NAME"]]))
        self.assertEqual(out, [])

    def test_fetch_fails_closed_on_non_json(self):
        with self.assertRaises(PublicApiError):
            cm.fetch_cbp("621111", api_key="",
                         opener=lambda u, h, t: b"<html>down</html>")


class KeyAndMetricTests(unittest.TestCase):
    def test_api_key_read_from_env_and_optional(self):
        orig = os.environ.get("CENSUS_API_KEY")
        try:
            os.environ.pop("CENSUS_API_KEY", None)
            self.assertEqual(cm.census_api_key(), "")
            os.environ["CENSUS_API_KEY"] = "  abc123  "
            self.assertEqual(cm.census_api_key(), "abc123")  # trimmed
        finally:
            if orig is None:
                os.environ.pop("CENSUS_API_KEY", None)
            else:
                os.environ["CENSUS_API_KEY"] = orig

    def test_establishments_per_100k_is_none_safe(self):
        self.assertIsNone(cm.establishments_per_100k(None, 100_000))
        self.assertIsNone(cm.establishments_per_100k(10, 0))
        self.assertEqual(cm.establishments_per_100k(50, 100_000), 50.0)

    def test_provider_naics_table_is_public_codes(self):
        self.assertIn("621111", cm.PROVIDER_NAICS)
        self.assertIn("621610", cm.PROVIDER_NAICS)


if __name__ == "__main__":
    unittest.main()
