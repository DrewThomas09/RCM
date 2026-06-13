"""NPPES connector slice: NPI validation, streaming parse, connector
discover()/fetch() with pagination, rate-limit, retry, and cap behavior."""
from __future__ import annotations

import io
import json
from pathlib import Path

import pytest

from connectors.nppes import synth
from connectors.nppes.connector import (
    NppesConnector, API_DEPTH_CAP, API_PAGE_CAP)
from connectors.nppes.luhn import is_valid_npi, make_valid_npi, luhn_check_digit
from connectors.nppes import parse


# ── Luhn / NPI validation ───────────────────────────────────────────
def test_known_valid_npis():
    # make_valid_npi produces Luhn-valid NPIs over the 80840 prefix.
    for base in ("100000042", "123456789", "000000001"):
        npi = make_valid_npi(base)
        assert is_valid_npi(npi), npi
        assert len(npi) == 10


def test_invalid_npis_rejected():
    assert not is_valid_npi("1234567890")   # bad check digit
    assert not is_valid_npi("999")          # too short
    assert not is_valid_npi("12345678901")  # too long
    assert not is_valid_npi("12345abcd0")   # non-digit
    assert not is_valid_npi(None)
    assert not is_valid_npi("")


def test_luhn_check_digit_known():
    # 80840 + base, the check digit makes the whole string Luhn-valid.
    npi = make_valid_npi("123456789")
    base = npi[:9]
    chk = int(npi[9])
    assert luhn_check_digit("80840" + base) == chk


# ── streaming parse ─────────────────────────────────────────────────
@pytest.fixture(scope="module")
def fixtures(tmp_path_factory):
    d = tmp_path_factory.mktemp("nppes_fx")
    return synth.generate(str(d), n_orgs=20, n_individuals=60, seed=3)


def test_parse_main_file_both_entity_types(fixtures):
    rows = list(parse.parse_main_file(fixtures["monthly_path"]))
    et = {r.entity_type for r in rows}
    assert 1 in et and 2 in et
    # taxonomy slots parsed with exactly one primary for multi-taxonomy rows
    multi = [r for r in rows if len(r.taxonomies) > 1]
    for r in multi:
        assert sum(1 for t in r.taxonomies if t.primary) == 1
    # organizations carry legal business name + authorized official
    orgs = [r for r in rows if r.entity_type == 2 and r.organization_name]
    assert any(o.authorized_official_last_name for o in orgs)
    # addresses present
    assert any(r.addresses for r in rows)


def test_parse_nucc(fixtures):
    defs = list(parse.parse_nucc_csv(fixtures["nucc_path"]))
    codes = {d.code for d in defs}
    assert "207Q00000X" in codes
    fam = next(d for d in defs if d.code == "207Q00000X")
    assert fam.classification == "Family Medicine"


# ── connector discover ──────────────────────────────────────────────
def test_discover_enumerates_registry():
    rows = NppesConnector().discover()
    ids = {r["dataset_id"] for r in rows}
    assert "nppes_monthly_full" in ids
    assert "nucc_taxonomy" in ids
    assert "npi_registry_api" in ids
    assert all(r["source"] == "nppes" for r in rows)
    modes = {r["ingest_mode"] for r in rows}
    assert {"bulk_file", "api", "derived"} <= modes


# ── connector fetch: API pagination / cap / retry ───────────────────
class _FakeResp:
    def __init__(self, payload):
        self._b = json.dumps(payload).encode()
    def read(self):
        return self._b
    def __enter__(self):
        return self
    def __exit__(self, *a):
        return False


def _api_result(npi):
    return {
        "number": npi, "enumeration_type": "NPI-1",
        "basic": {"first_name": "A", "last_name": "B", "status": "A"},
        "addresses": [{"address_purpose": "LOCATION", "state": "TX",
                       "city": "DALLAS", "address_1": "1 MAIN"}],
        "taxonomies": [{"code": "207Q00000X", "primary": True}],
    }


def test_fetch_api_paginates_and_stops_at_depth_cap(monkeypatch):
    conn = NppesConnector(sleeper=lambda s: None)
    # Always returns a full page of 200 → connector should keep a cursor
    # until the depth cap, then stop.
    def fake_urlopen(req, timeout=0):
        payload = {"results": [_api_result(make_valid_npi(str(100000000 + i)))
                               for i in range(API_PAGE_CAP)]}
        return _FakeResp(payload)
    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)

    cursor = 0
    pages = 0
    seen = 0
    while True:
        rows, cursor = conn.fetch("?version=2.1",
                                  {"kind": "api_lookup", "limit": API_PAGE_CAP,
                                   "taxonomy_description": "family"}, cursor)
        pages += 1
        seen += len(rows)
        if cursor is None:
            break
        assert pages < 20  # safety
    # Must not page beyond the documented depth cap.
    assert seen <= API_DEPTH_CAP
    assert any(r["npi"] for r in rows) or seen >= API_PAGE_CAP


def test_fetch_api_flattens_to_canonical_shape(monkeypatch):
    conn = NppesConnector(sleeper=lambda s: None)
    npi = make_valid_npi("200000001")
    monkeypatch.setattr("urllib.request.urlopen",
                        lambda req, timeout=0: _FakeResp({"results": [_api_result(npi)]}))
    rows, nxt = conn.fetch("?version=2.1", {"kind": "api_lookup"}, 0)
    assert nxt is None  # short page → exhausted
    assert rows[0]["npi"] == npi
    assert rows[0]["taxonomies"][0]["code"] == "207Q00000X"
    assert rows[0]["addresses"][0]["state"] == "TX"


def test_fetch_api_retries_on_500_then_gives_up(monkeypatch):
    import urllib.error
    calls = {"n": 0}
    def boom(req, timeout=0):
        calls["n"] += 1
        raise urllib.error.HTTPError(req.full_url, 500, "err", {}, None)
    monkeypatch.setattr("urllib.request.urlopen", boom)
    conn = NppesConnector(max_retries=3, sleeper=lambda s: None)
    rows, nxt = conn.fetch("?version=2.1", {"kind": "api_lookup"}, 0)
    assert rows == [] and nxt is None
    assert calls["n"] == 3  # retried up to max_retries
    assert conn.events[-1].ok is False


def test_fetch_bulk_uses_local_path_when_offline():
    conn = NppesConnector(sleeper=lambda s: None)
    rows, nxt = conn.fetch("NPPES.zip",
                           {"kind": "monthly_full", "local_path": "/data/x.csv"}, None)
    assert rows == [{"local_path": "/data/x.csv", "kind": "monthly_full"}]
    assert nxt is None
