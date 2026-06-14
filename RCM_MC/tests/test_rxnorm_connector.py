"""Tests for the RxNorm connector: discover(), fetch() parsing/pagination, and
the internal rate-limit / retry / fail-closed transport behaviour.

All network behaviour is exercised with a fake opener + fake clock — no socket,
deterministic — exactly as the repo's other public-API client tests do.
"""
from __future__ import annotations

import json
import unittest
from urllib.error import HTTPError, URLError

from rcm_mc.data_public.rxnorm import seed as seedmod
from rcm_mc.data_public.rxnorm.connector import RxNormApiError, RxNormConnector


def _json_opener(payload):
    def _open(url, headers, timeout):
        assert "User-Agent" in headers  # every request carries a contact UA
        return json.dumps(payload).encode()
    return _open


class DiscoverTests(unittest.TestCase):
    def test_discover_returns_registry_rows(self):
        rows = RxNormConnector().discover()
        ids = {r["dataset_id"] for r in rows}
        self.assertIn("rxnorm_concepts", ids)
        self.assertIn("rxnorm_ndc_crosswalk", ids)
        for r in rows:
            self.assertEqual(r["source"], "rxnorm")
            # every row carries the declarative contract fields
            for key in ("connector", "base_url", "endpoint", "default_params",
                        "refresh_cadence", "join_keys", "target_table"):
                self.assertIn(key, r)


class FetchParsingTests(unittest.TestCase):
    def setUp(self):
        self.c = RxNormConnector()
        self.kw = {"sleep": lambda s: None, "now": lambda: 0.0}

    def test_fetch_properties(self):
        rows, cur = self.c.fetch(
            "properties", {"rxcui": "83367"},
            opener=seedmod.seed_opener, **self.kw)
        self.assertEqual(cur, "")
        self.assertEqual(rows[0]["rxcui"], "83367")
        self.assertEqual(rows[0]["tty"], "IN")

    def test_fetch_historystatus_remap(self):
        rows, _ = self.c.fetch("historystatus", {"rxcui": "9999999"},
                               opener=seedmod.seed_opener, **self.kw)
        self.assertEqual(rows[0]["status"], "remapped")
        self.assertEqual(rows[0]["remapped_to_rxcui"], "83367")

    def test_fetch_ndcs(self):
        rows, _ = self.c.fetch("ndcs", {"rxcui": "7052"},
                               opener=seedmod.seed_opener, **self.kw)
        self.assertEqual([r["ndc_raw"] for r in rows], ["0409-1896-20"])

    def test_fetch_rxcui_by_ndc(self):
        rows, _ = self.c.fetch("rxcui_by_ndc", {"id": "0409-1896-20"},
                               opener=seedmod.seed_opener, **self.kw)
        self.assertEqual(rows[0]["rxcui"], "7052")

    def test_fetch_rxclass_spans_types(self):
        rows, _ = self.c.fetch("rxclass", {"rxcui": "83367"},
                               opener=seedmod.seed_opener, **self.kw)
        types = {r["class_type"] for r in rows}
        self.assertEqual(types, {"ATC", "mechanism_of_action", "therapeutic"})

    def test_fetch_allconcepts_paginates(self):
        # batch_size=3 forces multiple pages over the seed concept universe.
        c = RxNormConnector(batch_size=3)
        seen = []
        cursor = ""
        pages = 0
        while True:
            rows, cursor = c.fetch("allconcepts", {}, cursor,
                                   opener=seedmod.seed_opener, **self.kw)
            seen.extend(r["rxcui"] for r in rows)
            pages += 1
            if not cursor:
                break
        self.assertGreater(pages, 1)
        self.assertEqual(len(seen), len(set(seen)))  # no dupes across pages
        self.assertIn("83367", seen)

    def test_unknown_endpoint_raises(self):
        with self.assertRaises(RxNormApiError):
            self.c.fetch("nope", {}, opener=seedmod.seed_opener, **self.kw)


class TransportTests(unittest.TestCase):
    def setUp(self):
        self.kw = {"sleep": lambda s: None, "now": lambda: 0.0}

    def test_non_json_fails_closed(self):
        c = RxNormConnector()
        with self.assertRaises(RxNormApiError):
            c.fetch("properties", {"rxcui": "1"},
                    opener=lambda u, h, t: b"<html/>", **self.kw)

    def test_429_is_retried_then_succeeds(self):
        calls = {"n": 0}

        def opener(url, headers, timeout):
            calls["n"] += 1
            if calls["n"] == 1:
                raise HTTPError(url, 429, "Too Many Requests", {}, None)
            return json.dumps(
                {"properties": {"rxcui": "1", "name": "x", "tty": "IN"}}).encode()

        c = RxNormConnector(retry_count=3)
        rows, _ = c.fetch("properties", {"rxcui": "1"}, opener=opener, **self.kw)
        self.assertEqual(calls["n"], 2)  # retried once past the 429
        self.assertEqual(rows[0]["rxcui"], "1")

    def test_503_retried_then_exhausts(self):
        calls = {"n": 0}

        def opener(url, headers, timeout):
            calls["n"] += 1
            raise HTTPError(url, 503, "Service Unavailable", {}, None)

        c = RxNormConnector(retry_count=2)
        with self.assertRaises(RxNormApiError):
            c.fetch("properties", {"rxcui": "1"}, opener=opener, **self.kw)
        self.assertEqual(calls["n"], 3)  # initial + 2 retries

    def test_404_fails_immediately_without_retry(self):
        calls = {"n": 0}

        def opener(url, headers, timeout):
            calls["n"] += 1
            raise HTTPError(url, 404, "Not Found", {}, None)

        c = RxNormConnector(retry_count=3)
        with self.assertRaises(RxNormApiError):
            c.fetch("properties", {"rxcui": "1"}, opener=opener, **self.kw)
        self.assertEqual(calls["n"], 1)  # no retry on a non-429 4xx

    def test_urlerror_retried_then_exhausts(self):
        calls = {"n": 0}

        def opener(url, headers, timeout):
            calls["n"] += 1
            raise URLError("connection refused")

        c = RxNormConnector(retry_count=1)
        with self.assertRaises(RxNormApiError):
            c.fetch("properties", {"rxcui": "1"}, opener=opener, **self.kw)
        self.assertEqual(calls["n"], 2)

    def test_rate_limit_floor_waits_between_calls(self):
        waits = []
        clock = {"t": 0.0}

        def opener(url, headers, timeout):
            return json.dumps(
                {"properties": {"rxcui": "1", "name": "x", "tty": "IN"}}).encode()

        def sleep(s):
            waits.append(s)
            clock["t"] += s

        c = RxNormConnector(min_interval_s=0.05)
        c._last_call_s = 0.0
        clock["t"] = 0.01  # only 0.01s since last call → must wait ~0.04s
        c.fetch("properties", {"rxcui": "1"}, opener=opener,
                sleep=sleep, now=lambda: clock["t"])
        self.assertTrue(any(w > 0 for w in waits))


if __name__ == "__main__":
    unittest.main()
