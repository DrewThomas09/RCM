"""In-memory fake QCEW slice server for tests — no socket, deterministic.

A :class:`FakeQcew` is an :data:`Opener` (``(url, headers, timeout) ->
RawResponse``) that serves canned CSV text per slice path. It also
models 429 + ``Retry-After`` and 5xx via a scripted ``transients`` map
so the transport's retry path is exercised without a network.

Fixture fidelity: :data:`QCEW_HEADERS` is the **real, complete header
row** of the live quarterly slices (sampled 2026-07-06 from
``/cew/data/api/2025/4/industry/622.csv`` and ``.../area/48453.csv`` —
identical for both slice kinds), and :func:`_to_csv` mirrors the live
quoting convention exactly: the eight leading code/dimension cells plus
the three ``*disclosure_code`` cells are double-quoted, every numeric
measure is bare. Row values are hand-written but shaped from real
records (the 48453 own_code=0 totals row carries the actual live
values) so normalize/table/lookup tests assert against realistic data.
The industry-622 and area-48453 fixtures deliberately overlap on two
Travis County observations — the live overlap that motivates the
slice-prefixed upsert key.
"""
from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from ..transport import RawResponse

# ── the real live header row (verbatim, 42 columns) ───────────────────
QCEW_HEADERS: Tuple[str, ...] = (
    "area_fips", "own_code", "industry_code", "agglvl_code", "size_code",
    "year", "qtr", "disclosure_code",
    "qtrly_estabs", "month1_emplvl", "month2_emplvl", "month3_emplvl",
    "total_qtrly_wages", "taxable_qtrly_wages", "qtrly_contributions",
    "avg_wkly_wage",
    "lq_disclosure_code", "lq_qtrly_estabs", "lq_month1_emplvl",
    "lq_month2_emplvl", "lq_month3_emplvl", "lq_total_qtrly_wages",
    "lq_taxable_qtrly_wages", "lq_qtrly_contributions", "lq_avg_wkly_wage",
    "oty_disclosure_code", "oty_qtrly_estabs_chg",
    "oty_qtrly_estabs_pct_chg", "oty_month1_emplvl_chg",
    "oty_month1_emplvl_pct_chg", "oty_month2_emplvl_chg",
    "oty_month2_emplvl_pct_chg", "oty_month3_emplvl_chg",
    "oty_month3_emplvl_pct_chg", "oty_total_qtrly_wages_chg",
    "oty_total_qtrly_wages_pct_chg", "oty_taxable_qtrly_wages_chg",
    "oty_taxable_qtrly_wages_pct_chg", "oty_qtrly_contributions_chg",
    "oty_qtrly_contributions_pct_chg", "oty_avg_wkly_wage_chg",
    "oty_avg_wkly_wage_pct_chg",
)

# Cells the live files double-quote (everything else is bare numeric).
_QUOTED = {
    "area_fips", "own_code", "industry_code", "agglvl_code", "size_code",
    "year", "qtr", "disclosure_code", "lq_disclosure_code",
    "oty_disclosure_code",
}

# Reasonable bare defaults so fixture rows only spell out what they
# assert on; every live cell is populated, so "" only appears in the
# disclosure-code cells (which the live files leave empty when the
# observation is not suppressed).
_ZERO_ROW: Dict[str, str] = {h: "0" for h in QCEW_HEADERS}
for _h in ("disclosure_code", "lq_disclosure_code", "oty_disclosure_code"):
    _ZERO_ROW[_h] = ""


def _row(**overrides: str) -> Dict[str, str]:
    row = dict(_ZERO_ROW)
    row.update(overrides)
    return row


def _to_csv(rows: List[Dict[str, str]]) -> str:
    """Emit CSV the way BLS publishes it: quoted dimension cells, bare
    numerics, LF line endings."""
    def cell(h: str, v: str) -> str:
        return f'"{v}"' if h in _QUOTED else v
    lines = [",".join(f'"{h}"' for h in QCEW_HEADERS)]
    for row in rows:
        lines.append(",".join(cell(h, row.get(h, "")) for h in QCEW_HEADERS))
    return "\n".join(lines) + "\n"


# ── ready-made fixture rows (realistic values, small counts) ──────────
def industry_622_rows() -> List[Dict[str, str]]:
    """The 2025 Q4 industry/622 (hospitals) slice: one row per area x
    ownership — national, state, and two Texas counties."""
    common = dict(industry_code="622", year="2025", qtr="4")
    return [
        _row(area_fips="US000", own_code="5", agglvl_code="15",
             qtrly_estabs="6531", month1_emplvl="5401200",
             month2_emplvl="5410100", month3_emplvl="5421400",
             total_qtrly_wages="123456789012", avg_wkly_wage="1750",
             lq_qtrly_estabs="1.00", oty_month3_emplvl_chg="98000",
             oty_month3_emplvl_pct_chg="1.8", **common),
        _row(area_fips="48000", own_code="5", agglvl_code="55",
             qtrly_estabs="720", month1_emplvl="418000",
             month2_emplvl="419500", month3_emplvl="421000",
             total_qtrly_wages="9876543210", avg_wkly_wage="1680",
             lq_qtrly_estabs="0.98", **common),
        # Travis County private hospitals — this observation also appears
        # in the area/48453 fixture (the live cross-slice overlap).
        # avg_wkly_wage carries synthetic padding to prove the normalizer
        # strips defensively (live QCEW cells are clean).
        _row(area_fips="48453", own_code="5", agglvl_code="75",
             qtrly_estabs="28", month1_emplvl="21300",
             month2_emplvl="21400", month3_emplvl="21500",
             total_qtrly_wages="482000000", avg_wkly_wage=" 1725",
             lq_qtrly_estabs="0.74", **common),
        # ... and its local-government twin (also overlapping).
        _row(area_fips="48453", own_code="2", agglvl_code="75",
             qtrly_estabs="3", month1_emplvl="5150",
             month2_emplvl="5180", month3_emplvl="5200",
             total_qtrly_wages="128000000", avg_wkly_wage="1900", **common),
        _row(area_fips="48303", own_code="5", agglvl_code="75",
             qtrly_estabs="12", month1_emplvl="9700",
             month2_emplvl="9750", month3_emplvl="9800",
             total_qtrly_wages="191000000", avg_wkly_wage="1500", **common),
        # A disclosure-suppressed county (live files publish N + zeros).
        _row(area_fips="48117", own_code="5", agglvl_code="75",
             disclosure_code="N", qtrly_estabs="0", month3_emplvl="0",
             avg_wkly_wage="0", **common),
    ]


def area_48453_rows() -> List[Dict[str, str]]:
    """The 2025 Q4 area/48453 (Travis County, TX) slice: one row per
    industry x ownership. The own_code=0 totals row carries the actual
    live values; the two 622 rows repeat the industry fixture's
    observations (cross-slice overlap)."""
    common = dict(area_fips="48453", year="2025", qtr="4")
    return [
        _row(own_code="0", industry_code="10", agglvl_code="70",
             qtrly_estabs="51464", month1_emplvl="936246",
             month2_emplvl="939042", month3_emplvl="939358",
             total_qtrly_wages="25138970001",
             taxable_qtrly_wages="806586545",
             qtrly_contributions="13819877", avg_wkly_wage="2061",
             lq_qtrly_estabs="1.00", oty_month3_emplvl_chg="24601",
             oty_month3_emplvl_pct_chg="2.7", **common),
        _row(own_code="5", industry_code="62", agglvl_code="74",
             qtrly_estabs="6200", month1_emplvl="97400",
             month2_emplvl="97800", month3_emplvl="98000",
             total_qtrly_wages="1790000000", avg_wkly_wage="1400", **common),
        _row(own_code="5", industry_code="622", agglvl_code="75",
             qtrly_estabs="28", month1_emplvl="21300",
             month2_emplvl="21400", month3_emplvl="21500",
             total_qtrly_wages="482000000", avg_wkly_wage="1725",
             lq_qtrly_estabs="0.74", **common),
        _row(own_code="2", industry_code="622", agglvl_code="75",
             qtrly_estabs="3", month1_emplvl="5150",
             month2_emplvl="5180", month3_emplvl="5200",
             total_qtrly_wages="128000000", avg_wkly_wage="1900", **common),
        _row(own_code="5", industry_code="6216", agglvl_code="76",
             qtrly_estabs="180", month1_emplvl="5500",
             month2_emplvl="5550", month3_emplvl="5600",
             total_qtrly_wages="76000000", avg_wkly_wage="1050", **common),
        # Non-healthcare row: the labor-market lookup must filter it out.
        _row(own_code="5", industry_code="23", agglvl_code="74",
             qtrly_estabs="2400", month1_emplvl="57200",
             month2_emplvl="57600", month3_emplvl="58000",
             total_qtrly_wages="1210000000", avg_wkly_wage="1600", **common),
    ]


def area_48453_2024q1_rows() -> List[Dict[str, str]]:
    """An older quarter for the same county — lets tests prove the
    lookups default to the newest ingested period and can be pinned
    back to an earlier one."""
    return [
        _row(area_fips="48453", own_code="5", industry_code="622",
             agglvl_code="75", year="2024", qtr="1",
             qtrly_estabs="26", month1_emplvl="19800",
             month2_emplvl="19900", month3_emplvl="20000",
             total_qtrly_wages="425000000", avg_wkly_wage="1640"),
    ]


def industry_622_csv(duplicate_last_row: bool = False) -> str:
    rows = industry_622_rows()
    if duplicate_last_row:
        rows = rows + [dict(rows[-1])]  # byte-identical duplicate line
    return _to_csv(rows)


def area_48453_csv() -> str:
    return _to_csv(area_48453_rows())


def area_48453_2024q1_csv() -> str:
    return _to_csv(area_48453_2024q1_rows())


class FakeQcew:
    """Serve canned CSV bodies per path; script transient failures."""

    def __init__(self) -> None:
        self.files: Dict[str, str] = {}
        self.calls: List[str] = []
        # Scripted transient responses keyed by call index:
        # {idx: (status, headers)}.
        self.transients: Dict[int, Tuple[int, Optional[Dict[str, str]]]] = {}

    def add(self, path: str, csv_text: str) -> "FakeQcew":
        self.files[path] = csv_text
        return self

    def __call__(self, url: str, headers: Dict[str, str], timeout: float
                 ) -> RawResponse:
        idx = len(self.calls)
        self.calls.append(url)
        if idx in self.transients:
            status, hdrs = self.transients[idx]
            return RawResponse(status=status, headers=hdrs or {}, body=b"err")
        path = url.split("data.bls.gov", 1)[-1].split("?", 1)[0]
        if path not in self.files:
            return RawResponse(status=404, body=b"Not Found")
        body = self.files[path].encode("utf-8")
        # The live server declares Content-Length; mirroring it makes
        # every test exercise the transport's byte-count integrity check.
        return RawResponse(status=200,
                           headers={"content-length": str(len(body))},
                           body=body)
