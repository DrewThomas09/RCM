"""Unit tests for the NPPES NPI Registry API client + cache.

Mocks the HTTP layer so tests run offline. Per CLAUDE.md guidance:
unittest.mock is acceptable for external stubs only; everything
internal exercises the real code path.
"""
from __future__ import annotations

import json
import sqlite3
import unittest
from io import BytesIO
from unittest.mock import patch
from urllib.error import HTTPError, URLError

from rcm_mc.data_public.nppes_api_client import (
    NppesApiError,
    NppesProvider,
    _parse_record,
    _parse_results,
    fetch_by_npi,
    search_by_address,
    search_by_organization,
)
from rcm_mc.data_public.nppes_cache import (
    cache_age_days,
    ensure_table,
    get_cached_org_roster,
    is_stale,
    list_providers,
    refresh_org_roster,
)


# ── Fixture payloads ──────────────────────────────────────────────

_ORG_RESULT = {
    "number": "1234567890",
    "enumeration_type": "NPI-2",
    "basic": {
        "organization_name": "Demo Health System",
        "enumeration_date": "2020-01-15",
        "last_updated": "2024-03-20",
    },
    "addresses": [
        {
            "address_purpose": "LOCATION",
            "address_1": "100 Main St",
            "city": "Atlanta",
            "state": "GA",
            "postal_code": "30303",
            "telephone_number": "404-555-0100",
        },
    ],
    "taxonomies": [
        {
            "primary": True,
            "code": "282N00000X",
            "desc": "General Acute Care Hospital",
        },
    ],
}

_INDIVIDUAL_RESULT = {
    "number": "2222222222",
    "enumeration_type": "NPI-1",
    "basic": {
        "first_name": "Jane",
        "last_name": "Smith",
        "enumeration_date": "2015-07-01",
        "last_updated": "2024-08-12",
    },
    "addresses": [
        {
            "address_purpose": "LOCATION",
            "address_1": "100 Main St Suite 200",
            "city": "Atlanta",
            "state": "GA",
            "postal_code": "30303",
        },
    ],
    "taxonomies": [
        {
            "primary": True,
            "code": "207R00000X",
            "desc": "Internal Medicine",
        },
    ],
}


class _FakeResponse:
    """Minimal urllib response stub."""
    def __init__(self, payload: dict, status: int = 200):
        self._body = json.dumps(payload).encode("utf-8")
        self.status = status
    def read(self) -> bytes:
        return self._body
    def __enter__(self):
        return self
    def __exit__(self, *a):
        return False


# ── Parser tests ──────────────────────────────────────────────────

class ParserTests(unittest.TestCase):
    def test_parses_organization(self):
        rec = _parse_record(_ORG_RESULT)
        self.assertEqual(rec.npi, "1234567890")
        self.assertTrue(rec.is_organization)
        self.assertFalse(rec.is_individual)
        self.assertEqual(rec.organization_name, "Demo Health System")
        self.assertEqual(rec.name, "Demo Health System")
        self.assertEqual(rec.taxonomy_code, "282N00000X")
        self.assertEqual(rec.primary_specialty, "General Acute Care Hospital")
        self.assertEqual(rec.state, "GA")
        self.assertEqual(rec.address_line, "100 Main St")
        self.assertEqual(rec.phone, "404-555-0100")

    def test_parses_individual(self):
        rec = _parse_record(_INDIVIDUAL_RESULT)
        self.assertEqual(rec.npi, "2222222222")
        self.assertTrue(rec.is_individual)
        self.assertFalse(rec.is_organization)
        self.assertEqual(rec.first_name, "Jane")
        self.assertEqual(rec.last_name, "Smith")
        self.assertEqual(rec.name, "Jane Smith")
        self.assertEqual(rec.primary_specialty, "Internal Medicine")

    def test_parses_missing_taxonomies(self):
        rec = _parse_record({
            "number": "9999",
            "enumeration_type": "NPI-1",
            "basic": {"first_name": "A", "last_name": "B"},
            "addresses": [],
            "taxonomies": [],
        })
        self.assertEqual(rec.taxonomy_code, "")
        self.assertEqual(rec.primary_specialty, "")
        self.assertEqual(rec.state, "")

    def test_results_raises_on_error_payload(self):
        with self.assertRaises(NppesApiError):
            _parse_results({"Errors": [{"description": "Bad query"}]})

    def test_results_empty_returns_empty_list(self):
        self.assertEqual(_parse_results({"results": []}), [])
        self.assertEqual(_parse_results({}), [])


# ── HTTP transport tests ──────────────────────────────────────────

class TransportTests(unittest.TestCase):
    def test_search_by_organization_happy_path(self):
        payload = {"results": [_ORG_RESULT]}
        with patch(
            "rcm_mc.data_public.nppes_api_client.urlopen",
            return_value=_FakeResponse(payload),
        ):
            results = search_by_organization(
                "Demo Health System", state="GA",
            )
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].npi, "1234567890")

    def test_search_by_address_happy_path(self):
        payload = {"results": [_INDIVIDUAL_RESULT]}
        with patch(
            "rcm_mc.data_public.nppes_api_client.urlopen",
            return_value=_FakeResponse(payload),
        ):
            results = search_by_address(city="Atlanta", state="GA")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].last_name, "Smith")

    def test_fetch_by_npi_returns_none_when_not_found(self):
        with patch(
            "rcm_mc.data_public.nppes_api_client.urlopen",
            return_value=_FakeResponse({"results": []}),
        ):
            self.assertIsNone(fetch_by_npi("0000000000"))

    def test_http_4xx_raises_immediately(self):
        err = HTTPError(
            url="x", code=400, msg="Bad Request",
            hdrs={}, fp=BytesIO(b"bad"),
        )
        with patch(
            "rcm_mc.data_public.nppes_api_client.urlopen",
            side_effect=err,
        ):
            with self.assertRaises(NppesApiError) as ctx:
                search_by_organization("Demo")
            self.assertIn("HTTP 400", str(ctx.exception))

    def test_url_error_retries_then_fails(self):
        # All attempts fail → NppesApiError raised
        with patch(
            "rcm_mc.data_public.nppes_api_client.urlopen",
            side_effect=URLError("timeout"),
        ), patch(
            "rcm_mc.data_public.nppes_api_client.time.sleep",
            return_value=None,
        ):
            with self.assertRaises(NppesApiError):
                search_by_organization("Demo")


# ── Cache tests ───────────────────────────────────────────────────

class CacheTests(unittest.TestCase):
    def setUp(self):
        self.con = sqlite3.connect(":memory:")
        ensure_table(self.con)

    def tearDown(self):
        self.con.close()

    def test_ensure_table_idempotent(self):
        # Calling twice must not raise
        ensure_table(self.con)
        ensure_table(self.con)

    def test_empty_cache_returns_none(self):
        self.assertIsNone(get_cached_org_roster(self.con, "123456"))
        self.assertIsNone(cache_age_days(self.con, "123456"))
        self.assertTrue(is_stale(self.con, "123456"))

    def test_refresh_writes_to_cache(self):
        payload = {"results": [_ORG_RESULT]}
        with patch(
            "rcm_mc.data_public.nppes_api_client.urlopen",
            return_value=_FakeResponse(payload),
        ):
            n = refresh_org_roster(
                self.con, ccn="123456",
                hospital_name="Demo Health System",
                state="GA",
            )
        # _ORG_RESULT contributes 1 NPI via the org search;
        # we also hit search_by_address but the patched urlopen
        # returns the same payload (still _ORG_RESULT, deduped by NPI)
        self.assertGreaterEqual(n, 1)
        summary = get_cached_org_roster(self.con, "123456")
        self.assertIsNotNone(summary)
        self.assertGreaterEqual(summary["n_providers"], 1)
        self.assertGreater(summary["n_organizations"], 0)

    def test_refresh_replaces_existing(self):
        # First refresh
        with patch(
            "rcm_mc.data_public.nppes_api_client.urlopen",
            return_value=_FakeResponse({"results": [_ORG_RESULT]}),
        ):
            refresh_org_roster(
                self.con, ccn="123456",
                hospital_name="Demo Health System",
                state="GA",
            )
        first_count = len(list_providers(self.con, "123456"))
        # Second refresh — same payload → DELETE+INSERT keeps count
        with patch(
            "rcm_mc.data_public.nppes_api_client.urlopen",
            return_value=_FakeResponse({"results": [_ORG_RESULT]}),
        ):
            refresh_org_roster(
                self.con, ccn="123456",
                hospital_name="Demo Health System",
                state="GA",
            )
        second_count = len(list_providers(self.con, "123456"))
        self.assertEqual(first_count, second_count)
        self.assertGreater(first_count, 0)


if __name__ == "__main__":
    unittest.main()
