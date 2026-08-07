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
    _DEFAULT_USER_AGENT,
    _parse_record,
    _parse_results,
    fetch_by_npi,
    paginate,
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

class HeaderEncodingTests(unittest.TestCase):
    """HTTP header values are latin-1, and the failure is invisible.

    ``http.client.putheader`` encodes every header value latin-1 and
    raises ``UnicodeEncodeError`` before a socket is opened. The default
    User-Agent here once carried an em dash, so every live NPPES call
    raised — and ``capiq._default_npi_fetch`` swallows the exception
    under a bare ``except Exception: return []`` and reports UNMATCHED.
    A transport bug that presents as "no such provider" is the worst
    kind, because the answer looks like data.

    Every other test in this file patches ``urlopen``, which is exactly
    why this survived: the header never reached the encoder.
    """

    def test_the_default_user_agent_survives_the_header_encoder(self):
        _DEFAULT_USER_AGENT.encode("latin-1")   # raises if it regresses

    def test_a_real_putheader_accepts_the_default_user_agent(self):
        """Exercise the actual encoder rather than asserting about it."""
        import http.client
        from io import BytesIO

        conn = http.client.HTTPConnection("example.invalid")
        conn.sock = BytesIO()   # buffered, never sent
        conn.putrequest("GET", "/", skip_host=True, skip_accept_encoding=True)
        conn.putheader("User-Agent", _DEFAULT_USER_AGENT)

    def test_the_encoder_really_does_reject_non_latin1(self):
        """Pin the mechanism, so the test above cannot pass vacuously."""
        import http.client
        from io import BytesIO

        conn = http.client.HTTPConnection("example.invalid")
        conn.sock = BytesIO()
        conn.putrequest("GET", "/", skip_host=True, skip_accept_encoding=True)
        with self.assertRaises(UnicodeEncodeError):
            conn.putheader("User-Agent", "research — contact")


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


class PaginationTests(unittest.TestCase):
    """The 200-per-page walk, and the 1,200 ceiling it cannot pass.

    Both numbers are the server's, not ours: NPPES returns at most 200
    records per call and refuses to skip past 1,000. A query with more
    matches than that cannot be enumerated at all, which is exactly why
    this client cannot harvest the register and the dissemination file
    exists.
    """

    def _pages(self, total: int):
        """A fake NPPES that holds ``total`` records and honours skip."""
        captured = []

        def _fake(request, timeout=None):  # noqa: ARG001
            url = request.full_url
            query = dict(
                part.split("=", 1) for part in url.split("?", 1)[1].split("&")
            )
            skip = int(query.get("skip", 0))
            limit = int(query.get("limit", 200))
            captured.append((skip, limit))
            window = range(skip, min(skip + limit, total))
            return _FakeResponse({"results": [
                dict(_ORG_RESULT, number=f"{1000000000 + i}") for i in window
            ]})

        return _fake, captured

    def test_a_result_set_larger_than_one_page_is_walked(self):
        fake, captured = self._pages(450)
        with patch("rcm_mc.data_public.nppes_api_client.urlopen", fake):
            results = paginate({"version": "2.1"}, limit=450,
                               sleep=lambda _s: None)
        self.assertEqual(len(results), 450)
        self.assertEqual(captured, [(0, 200), (200, 200), (400, 50)])

    def test_skip_is_the_count_already_returned(self):
        fake, captured = self._pages(1000)
        with patch("rcm_mc.data_public.nppes_api_client.urlopen", fake):
            paginate({"version": "2.1"}, limit=600, sleep=lambda _s: None)
        self.assertEqual([skip for skip, _ in captured], [0, 200, 400])

    def test_a_short_page_ends_the_walk(self):
        """Without this the client re-requests an exhausted result set
        until it hits the ceiling, getting the same short page each time."""
        fake, captured = self._pages(250)
        with patch("rcm_mc.data_public.nppes_api_client.urlopen", fake):
            results = paginate({"version": "2.1"}, limit=1200,
                               sleep=lambda _s: None)
        self.assertEqual(len(results), 250)
        self.assertEqual(len(captured), 2)

    def test_an_empty_first_page_stops_immediately(self):
        fake, captured = self._pages(0)
        with patch("rcm_mc.data_public.nppes_api_client.urlopen", fake):
            self.assertEqual(paginate({"version": "2.1"}, limit=1200,
                                      sleep=lambda _s: None), [])
        self.assertEqual(len(captured), 1)

    def test_the_ceiling_is_the_servers_not_a_suggestion(self):
        fake, _ = self._pages(50_000)
        with patch("rcm_mc.data_public.nppes_api_client.urlopen", fake):
            results = paginate({"version": "2.1"}, limit=99_999,
                               sleep=lambda _s: None)
        self.assertEqual(len(results), 1200)

    def test_the_walk_paces_itself_between_pages(self):
        """NPPES returns 503 under load. A harvest that trips that is
        slower than one that waits."""
        slept = []
        fake, _ = self._pages(600)
        with patch("rcm_mc.data_public.nppes_api_client.urlopen", fake):
            paginate({"version": "2.1"}, limit=600, sleep=slept.append)
        self.assertEqual(len(slept), 2)      # between pages, not after the last
        self.assertTrue(all(s > 0 for s in slept))

    def test_a_single_page_request_does_not_sleep(self):
        slept = []
        fake, _ = self._pages(10)
        with patch("rcm_mc.data_public.nppes_api_client.urlopen", fake):
            paginate({"version": "2.1"}, limit=200, sleep=slept.append)
        self.assertEqual(slept, [])

    def test_search_helpers_go_through_the_walk(self):
        fake, captured = self._pages(300)
        with patch("rcm_mc.data_public.nppes_api_client.urlopen", fake):
            results = search_by_organization("Demo", state="GA", limit=300)
        self.assertEqual(len(results), 300)
        self.assertEqual(len(captured), 2)
