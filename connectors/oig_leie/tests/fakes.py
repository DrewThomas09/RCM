"""In-memory fake OIG download server for tests — no socket, deterministic.

A :class:`FakeOig` is an :data:`Opener` (``(url, headers, timeout) ->
RawResponse``) that serves canned CSV text per download path. It also
models 429 + ``Retry-After`` and 5xx via a scripted ``transients`` map so
the transport's retry path is exercised without a network.

Fixture fidelity: :data:`LEIE_HEADERS` is the **real, complete header
row** of the live files (sampled 2026-07-06 — UPDATED.csv and the
monthly ``{yy}{mm}excl.csv`` / ``{yy}{mm}rein.csv`` supplements all
publish the identical 18 columns), and the fixture rows mirror the live
sentinel quirks: ``NPI = 0000000000`` when unknown, dates as
``yyyymmdd`` with ``00000000`` for null, uppercase values, business
names containing commas (quoted in the CSV), and an optional
byte-identical duplicate line (the live full file contains a couple
dozen). Row values are hand-written but shaped from real records so
normalize/table tests assert against realistic data.
"""
from __future__ import annotations

import csv
import io
from typing import Dict, List, Optional, Tuple

from ..transport import RawResponse

# ── the real live header row (all LEIE files share it) ────────────────
LEIE_HEADERS: Tuple[str, ...] = (
    "LASTNAME", "FIRSTNAME", "MIDNAME", "BUSNAME", "GENERAL", "SPECIALTY",
    "UPIN", "NPI", "DOB", "ADDRESS", "CITY", "STATE", "ZIP", "EXCLTYPE",
    "EXCLDATE", "REINDATE", "WAIVERDATE", "WVRSTATE",
)

UPDATED_PATH = "/exclusions/downloadables/UPDATED.csv"
SUPPL_2605_EXCL = "/exclusions/downloadables/2026/2605excl.csv"
SUPPL_2605_REIN = "/exclusions/downloadables/2026/2605rein.csv"


def _to_csv(rows: List[Dict[str, str]]) -> str:
    """Emit CSV the way OIG publishes it: plain 18-column rows, no
    dangling trailing comma (unlike HRSA's files — verified live)."""
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(list(LEIE_HEADERS))
    for row in rows:
        writer.writerow([row.get(h, "") for h in LEIE_HEADERS])
    return buf.getvalue()


# ── ready-made fixture rows (realistic values, small counts) ──────────
def updated_rows() -> List[Dict[str, str]]:
    """Four rows spanning the shapes a screen must handle: a business
    with the zero-NPI sentinel, a business with a real NPI (embedded
    comma in the name), an individual with a real NPI, and an individual
    with no NPI but a waiver."""
    r1 = {
        "BUSNAME": "#1 MARKETING SERVICE, INC", "GENERAL": "OTHER BUSINESS",
        "SPECIALTY": "SOBER HOME", "NPI": "0000000000",
        "ADDRESS": "239 BRIGHTON BEACH AVENUE", "CITY": "BROOKLYN",
        "STATE": "NY", "ZIP": "11235", "EXCLTYPE": "1128a1",
        "EXCLDATE": "20200319", "REINDATE": "00000000",
        "WAIVERDATE": "00000000",
    }
    r2 = {
        "BUSNAME": "101 FIRST CARE PHARMACY INC", "GENERAL": "OTHER BUSINESS",
        "SPECIALTY": "PHARMACY", "NPI": "1972902351",
        "ADDRESS": "C/O 609 W 191ST STREET, APT D", "CITY": "NEW YORK",
        "STATE": "NY", "ZIP": "10040", "EXCLTYPE": "1128b8",
        "EXCLDATE": "20220320", "REINDATE": "00000000",
        "WAIVERDATE": "00000000",
    }
    r3 = {
        "LASTNAME": "SMITH", "FIRSTNAME": "JOHN", "MIDNAME": "A",
        "GENERAL": "IND- LIC HC SERV PRO", "SPECIALTY": "NURSE/NURSES AIDE",
        "NPI": "1234567893", "DOB": "19701205",
        "ADDRESS": "12824 CANOVA DRIVE", "CITY": "MANASSAS", "STATE": "VA",
        "ZIP": "20112", "EXCLTYPE": "1128b4", "EXCLDATE": "20230115",
        "REINDATE": "00000000", "WAIVERDATE": "00000000",
    }
    r4 = {
        "LASTNAME": "GARZA", "FIRSTNAME": "MARIA", "MIDNAME": "",
        "GENERAL": "IND- LIC HC SERV PRO", "SPECIALTY": "PHYSICIAN",
        "NPI": "0000000000", "DOB": "19650409",
        "ADDRESS": "701 NW 36 AVENUE", "CITY": "MIAMI", "STATE": "FL",
        "ZIP": "33125", "EXCLTYPE": "1128b7", "EXCLDATE": "19970620",
        "REINDATE": "00000000", "WAIVERDATE": "20240101", "WVRSTATE": "FL",
    }
    return [r1, r2, r3, r4]


def updated_csv(duplicate_last_row: bool = False) -> str:
    rows = updated_rows()
    if duplicate_last_row:
        rows = rows + [dict(rows[-1])]  # byte-identical duplicate line
    return _to_csv(rows)


def supplement_excl_rows() -> List[Dict[str, str]]:
    """One month's new exclusions: one row already in the full file
    (upsert must merge, not duplicate) and one genuinely new row."""
    known = updated_rows()[2]  # SMITH, JOHN — also in UPDATED.csv
    new = {
        "LASTNAME": "OKAFOR", "FIRSTNAME": "CHIKE", "MIDNAME": "",
        "GENERAL": "IND- LIC HC SERV PRO", "SPECIALTY": "PHARMACIST",
        "NPI": "1558362563", "DOB": "19810423",
        "ADDRESS": "44 ELM STREET", "CITY": "AKRON", "STATE": "OH",
        "ZIP": "44301", "EXCLTYPE": "1128a2", "EXCLDATE": "20260501",
        "REINDATE": "00000000", "WAIVERDATE": "00000000",
    }
    return [known, new]


def supplement_excl_csv() -> str:
    return _to_csv(supplement_excl_rows())


def supplement_rein_rows() -> List[Dict[str, str]]:
    """One month's reinstatements (REINDATE populated), shaped from the
    live 2605rein.csv: a business and an individual."""
    r1 = {
        "BUSNAME": "MEHRAN ZAMANI, DDS, PC", "GENERAL": "OTHER BUSINESS",
        "SPECIALTY": "DENTAL PRACTICE", "NPI": "0000000000",
        "ADDRESS": "143 HOYT ST, APT 1-0", "CITY": "STAMFORD", "STATE": "CT",
        "ZIP": "06905", "EXCLTYPE": "1128b7", "EXCLDATE": "20150306",
        "REINDATE": "20260519", "WAIVERDATE": "00000000",
    }
    r2 = {
        "LASTNAME": "ACHU", "FIRSTNAME": "RUTH", "MIDNAME": "FRI",
        "GENERAL": "IND- LIC HC SERV PRO", "SPECIALTY": "NURSE/NURSES AIDE",
        "NPI": "1234567893", "DOB": "19960906",
        "ADDRESS": "12824 CANOVA DRIVE", "CITY": "MANASSAS", "STATE": "VA",
        "ZIP": "20112", "EXCLTYPE": "1128b4", "EXCLDATE": "20260120",
        "REINDATE": "20260519", "WAIVERDATE": "00000000",
    }
    return [r1, r2]


def supplement_rein_csv() -> str:
    return _to_csv(supplement_rein_rows())


class FakeOig:
    """Serve canned CSV bodies per path; script transient failures."""

    def __init__(self) -> None:
        self.files: Dict[str, str] = {}
        self.calls: List[str] = []
        # Scripted transient responses keyed by call index:
        # {idx: (status, headers)}.
        self.transients: Dict[int, Tuple[int, Optional[Dict[str, str]]]] = {}

    def add(self, path: str, csv_text: str) -> "FakeOig":
        self.files[path] = csv_text
        return self

    def __call__(self, url: str, headers: Dict[str, str], timeout: float
                 ) -> RawResponse:
        idx = len(self.calls)
        self.calls.append(url)
        if idx in self.transients:
            status, hdrs = self.transients[idx]
            return RawResponse(status=status, headers=hdrs or {}, body=b"err")
        path = url.split("oig.hhs.gov", 1)[-1].split("?", 1)[0]
        if path not in self.files:
            return RawResponse(status=404, body=b"Not Found")
        body = self.files[path].encode("utf-8")
        # The live server declares Content-Length; mirroring it makes
        # every test exercise the transport's byte-count integrity check.
        return RawResponse(status=200,
                           headers={"content-length": str(len(body))},
                           body=body)
