"""Tests for the public-data API client scaffolds.

Pure URL builders are asserted directly; the shared transport's retry,
rate-limit floor, JSON parse and fail-closed behaviour are exercised with a
fake opener and a fake clock — no socket, deterministic.
"""
from __future__ import annotations

import json
import unittest
from urllib.error import HTTPError, URLError

from rcm_mc.data_public import public_api_clients as c


def _json_opener(payload):
    def _open(url, headers, timeout):
        # Every request must carry a contact User-Agent.
        assert "User-Agent" in headers
        return json.dumps(payload).encode()
    return _open


class RequestBuilderTests(unittest.TestCase):
    def test_openfda_builds_search_and_caps_limit(self):
        r = c.openfda_request("device", "510k", search="applicant:x", limit=99999)
        self.assertTrue(r.url.endswith("/device/510k.json"))
        self.assertEqual(r.params["search"], "applicant:x")
        self.assertEqual(r.params["limit"], "1000")  # capped

    def test_clinicaltrials_v2_phase_filter_and_format(self):
        r = c.clinicaltrials_request(condition="psoriasis", phase="Phase 3")
        self.assertIn("/api/v2/studies", r.url)
        self.assertEqual(r.params["format"], "json")
        self.assertEqual(r.params["query.cond"], "psoriasis")
        self.assertIn("Phase 3", r.params["filter.advanced"])

    def test_rxnorm_rxcui_request(self):
        r = c.rxnorm_rxcui_request("atorvastatin")
        self.assertTrue(r.url.endswith("/rxcui.json"))
        self.assertEqual(r.params["name"], "atorvastatin")

    def test_census_request_threads_key_and_geo(self):
        r = c.census_request(2022, "acs/acs5", get=["B01001_001E"],
                             for_geo="county:*", in_geo="state:48", api_key="K")
        self.assertIn("/2022/acs/acs5", r.url)
        self.assertEqual(r.params["get"], "B01001_001E")
        self.assertEqual(r.params["for"], "county:*")
        self.assertEqual(r.params["in"], "state:48")
        self.assertEqual(r.params["key"], "K")

    def test_propublica_org_strips_ein_dashes(self):
        r = c.propublica_organization_request("13-1837418")
        self.assertTrue(r.url.endswith("/organizations/131837418.json"))

    def test_full_url_encodes_params(self):
        req = c.ApiRequest(url="https://x/api", params={"q": "a b", "n": "1"})
        self.assertIn("q=a+b", req.full_url)
        self.assertIn("?", req.full_url)


class TransportTests(unittest.TestCase):
    def test_api_key_merged_when_configured(self):
        client = c.HttpJsonClient(base_url="https://api.x", api_key="SECRET",
                                  api_key_param="api_key")
        req = client.request("/path", {"q": "1"})
        self.assertEqual(req.params["api_key"], "SECRET")
        self.assertEqual(req.params["q"], "1")

    def test_get_json_parses(self):
        client = c.HttpJsonClient(base_url="https://api.x")
        out = client.get_json(opener=_json_opener({"ok": True}))
        self.assertEqual(out, {"ok": True})

    def test_non_json_raises_public_api_error(self):
        client = c.HttpJsonClient(base_url="https://api.x")
        with self.assertRaises(c.PublicApiError):
            client.get_json(opener=lambda u, h, t: b"<html>not json</html>")

    def test_4xx_fails_immediately_without_retry(self):
        calls = {"n": 0}

        def opener(url, headers, timeout):
            calls["n"] += 1
            raise HTTPError(url, 404, "Not Found", {}, None)

        client = c.HttpJsonClient(base_url="https://api.x", retry_count=3)
        with self.assertRaises(c.PublicApiError):
            client.get_json(opener=opener, sleep=lambda s: None)
        self.assertEqual(calls["n"], 1)  # no retry on 4xx

    def test_5xx_retries_then_fails_closed(self):
        calls = {"n": 0}

        def opener(url, headers, timeout):
            calls["n"] += 1
            raise HTTPError(url, 503, "Busy", {}, None)

        client = c.HttpJsonClient(base_url="https://api.x", retry_count=2)
        with self.assertRaises(c.PublicApiError):
            client.get_json(opener=opener, sleep=lambda s: None)
        self.assertEqual(calls["n"], 3)  # initial + 2 retries

    def test_url_error_fails_closed(self):
        def opener(url, headers, timeout):
            raise URLError("no network")

        client = c.HttpJsonClient(base_url="https://api.x", retry_count=1)
        with self.assertRaises(c.PublicApiError):
            client.get_json(opener=opener, sleep=lambda s: None)

    def test_rate_limit_floor_sleeps_between_calls(self):
        clock = {"t": 100.0}
        slept = {"total": 0.0}

        def now():
            return clock["t"]

        def sleep(s):
            slept["total"] += s
            clock["t"] += s  # honor the sleep on the fake clock

        client = c.HttpJsonClient(base_url="https://api.x", min_interval_s=1.0)
        opener = _json_opener({"ok": 1})
        client.get_json(opener=opener, sleep=sleep, now=now)   # first: no wait
        clock["t"] += 0.2                                      # only 0.2s passes
        client.get_json(opener=opener, sleep=sleep, now=now)   # must wait ~0.8s
        self.assertAlmostEqual(slept["total"], 0.8, places=5)


class FetcherTests(unittest.TestCase):
    def test_openfda_search_unwraps_results(self):
        out = c.openfda_search("drug", "event", search="x",
                               opener=_json_opener({"results": [{"a": 1}, {"a": 2}]}))
        self.assertEqual(len(out), 2)

    def test_clinicaltrials_search_unwraps_studies(self):
        out = c.clinicaltrials_search(condition="x",
                                      opener=_json_opener({"studies": [{"s": 1}]}))
        self.assertEqual(len(out), 1)

    def test_census_get_zips_header_and_rows(self):
        payload = [["NAME", "B01001_001E", "state"],
                   ["Texas", "29000000", "48"]]
        out = c.census_get(2022, "acs/acs5", get=["NAME", "B01001_001E"],
                           for_geo="state:48", opener=_json_opener(payload))
        self.assertEqual(out[0]["NAME"], "Texas")
        self.assertEqual(out[0]["B01001_001E"], "29000000")

    def test_rxnorm_rxcui_unwraps_id_group(self):
        out = c.rxnorm_rxcui("atorvastatin",
                             opener=_json_opener({"idGroup": {"rxnormId": ["83367"]}}))
        self.assertEqual(out, ["83367"])

    def test_available_clients_lists_the_top_apis(self):
        avail = set(c.available_clients())
        for k in ("nppes", "openfda", "clinicaltrials", "rxnorm", "census_acs",
                  "propublica_990", "who_gho"):
            self.assertIn(k, avail)

    def test_nppes_request_caps_limit_and_threads_filters(self):
        r = c.nppes_request(organization_name="Acme Health", state="TX",
                            enumeration_type="NPI-2", limit=9999)
        self.assertTrue(r.url.startswith("https://npiregistry.cms.hhs.gov"))
        self.assertEqual(r.params["limit"], "200")     # NPPES hard cap
        self.assertEqual(r.params["state"], "TX")
        self.assertEqual(r.params["enumeration_type"], "NPI-2")

    def test_who_gho_builds_odata_filter(self):
        r = c.who_gho_request("WHOSIS_000001", country="USA", year="2019")
        self.assertTrue(r.url.endswith("/WHOSIS_000001"))
        self.assertIn("SpatialDim eq 'USA'", r.params["$filter"])
        self.assertIn("TimeDim eq 2019", r.params["$filter"])

    def test_who_gho_indicator_unwraps_value(self):
        out = c.who_gho_indicator(
            "WHOSIS_000001",
            opener=_json_opener({"value": [{"NumericValue": 78.5}]}))
        self.assertEqual(out[0]["NumericValue"], 78.5)


if __name__ == "__main__":
    unittest.main()
