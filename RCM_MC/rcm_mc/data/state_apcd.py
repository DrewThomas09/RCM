"""State All-Payer Claims Database (APCD) public-use ingestion.

About 30 states operate APCDs, but public-use availability varies
wildly. The states that publish aggregated public-use files
(CO, ME, MA, NH, OR, RI, UT, VT, WA) ship per-region per-procedure
allowed-amount percentiles by payer type — the only practical way
to see commercial-payer pricing alongside the Medicare-only CMS
sources we already ingest (HCRIS, OPPS, Hospital MRF).

Why this matters:

  • Hospital MRF + payer TiC publish *contracted* rates. APCDs
    publish *paid* allowed amounts, which include the discount
    actually realized after secondary adjudication, eligibility
    issues, and downcoding. Different number, both useful.
  • APCDs include Medicare Advantage and Medicaid Managed Care
    payments — neither show up in HCRIS or OPPS.
  • Per Gobeille v. Liberty Mutual (2016), self-funded ERISA plans
    are *not* required to report. Most public APCDs note ~30-40%
    coverage gap on commercial — useful caveat for the
    coverage_pct field.

Schema is one row per (state × region × cpt_code × payer_type ×
year) — the canonical public-use granularity. Member-level data
is restricted to qualified researchers and is out of scope here.

Public API::

    from rcm_mc.data.state_apcd import (
        APCDPriceRecord,
        load_apcd_prices,
        get_apcd_prices_for_cpt,
        compute_commercial_medicare_ratio,
        list_high_dispersion_procedures,
    )
"""
from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional


# Canonical payer-type buckets — every state APCD uses one of
# these or a near-equivalent. Normalization happens in
# _normalize_payer_type below.
PAYER_TYPES = {
    "commercial",       # fully-insured + self-funded ERISA reporting
    "medicare_advantage",
    "medicaid_managed_care",
    "medicaid_ffs",
    "medicare_ffs",
}


def _ensure_table(con: Any) -> None:
    con.execute(
        """
        CREATE TABLE IF NOT EXISTS state_apcd_prices (
            state TEXT NOT NULL,
            region TEXT NOT NULL,
            cpt_code TEXT NOT NULL,
            payer_type TEXT NOT NULL,
            year INTEGER NOT NULL,
            cpt_description TEXT,
            n_claims INTEGER,
            allowed_p25 REAL,
            allowed_p50 REAL,
            allowed_p75 REAL,
            allowed_p95 REAL,
            allowed_mean REAL,
            avg_member_oop REAL,
            coverage_pct REAL,
            loaded_at TEXT NOT NULL,
            PRIMARY KEY (state, region, cpt_code,
                         payer_type, year)
        )
        """
    )
    con.execute(
        "CREATE INDEX IF NOT EXISTS "
        "idx_apcd_cpt ON state_apcd_prices(cpt_code, year)"
    )
    con.execute(
        "CREATE INDEX IF NOT EXISTS "
        "idx_apcd_state_region "
        "ON state_apcd_prices(state, region)"
    )


@dataclass
class APCDPriceRecord:
    """One state × region × CPT × payer-type × year row."""
    state: str
    region: str
    cpt_code: str
    payer_type: str
    year: int
    cpt_description: str = ""
    n_claims: Optional[int] = None
    allowed_p25: Optional[float] = None
    allowed_p50: Optional[float] = None
    allowed_p75: Optional[float] = None
    allowed_p95: Optional[float] = None
    allowed_mean: Optional[float] = None
    avg_member_oop: Optional[float] = None
    coverage_pct: Optional[float] = None  # share of state pop


# ── Parsing ───────────────────────────────────────────────────

def _safe_float(v: Any) -> Optional[float]:
    if v is None or v == "":
        return None
    s = str(v).strip().replace(",", "").replace("$", "")
    if s.lower() in ("not available", "n/a", "na",
                     "(x)", "suppressed", "*", "<11"):
        return None
    try:
        return float(s)
    except (TypeError, ValueError):
        return None


def _safe_int(v: Any) -> Optional[int]:
    f = _safe_float(v)
    return int(f) if f is not None else None


def _pick(row: Dict[str, Any], *names: str) -> Any:
    for n in names:
        if n in row and row[n] not in (None, ""):
            return row[n]
    return None


def _normalize_payer_type(raw: str) -> str:
    """Each state names payer types differently. Normalize to
    PAYER_TYPES values; fall back to 'commercial' for ambiguous
    insurer-name fields."""
    if not raw:
        return "commercial"
    s = raw.strip().lower()
    if "medicare advantage" in s or "ma plan" in s or s == "ma":
        return "medicare_advantage"
    if "medicaid" in s and ("managed" in s or "mco" in s
                            or "mc" in s.split()):
        return "medicaid_managed_care"
    if "medicaid" in s:
        return "medicaid_ffs"
    if "medicare" in s:
        return "medicare_ffs"
    if ("commercial" in s or "private" in s
            or "self-insured" in s or "fully insured" in s
            or "ppo" in s or "hmo" in s or "epo" in s):
        return "commercial"
    return "commercial"


def parse_apcd_csv(
    path: Any,
    *,
    state: str = "",
    year: int = 0,
) -> Iterable[APCDPriceRecord]:
    """Parse a state APCD public-use CSV.

    Column conventions vary per state — we accept the common
    aliases. CO uses ``Procedure Code`` + ``Median Allowed``,
    MA uses ``cpt`` + ``allowed_p50``, OR/WA use ``hcpcs`` +
    ``median_allowed_amount``. The state and year arguments
    let callers supply context the CSV may not include.
    """
    p = Path(str(path))
    if not p.is_file():
        raise FileNotFoundError(
            f"APCD CSV not found at {p}")
    with p.open("r", encoding="utf-8", errors="replace",
                newline="") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            cpt = str(_pick(
                row, "cpt_code", "cpt", "hcpcs",
                "Procedure Code", "ProcedureCode",
                "ServiceCode") or "").strip()
            if not cpt:
                continue
            payer_raw = str(_pick(
                row, "payer_type", "PayerType",
                "payer_category", "Payer Type",
                "Insurance Type", "Coverage Type") or "")
            yield APCDPriceRecord(
                state=str(_pick(
                    row, "state", "State") or state
                ).strip().upper(),
                region=str(_pick(
                    row, "region", "Region",
                    "hsa", "HSA",
                    "county", "County",
                    "msa", "MSA") or "ALL").strip(),
                cpt_code=cpt,
                payer_type=_normalize_payer_type(payer_raw),
                year=year or _safe_int(
                    _pick(row, "year", "Year")) or 0,
                cpt_description=str(_pick(
                    row, "cpt_description", "Description",
                    "ProcedureDescription") or "").strip(),
                n_claims=_safe_int(_pick(
                    row, "n_claims", "claim_count",
                    "ClaimCount", "Claims",
                    "Number of Claims")),
                allowed_p25=_safe_float(_pick(
                    row, "allowed_p25", "P25 Allowed",
                    "p25_allowed_amount",
                    "AllowedP25")),
                allowed_p50=_safe_float(_pick(
                    row, "allowed_p50", "Median Allowed",
                    "median_allowed_amount",
                    "AllowedMedian", "MedianAllowed")),
                allowed_p75=_safe_float(_pick(
                    row, "allowed_p75", "P75 Allowed",
                    "p75_allowed_amount",
                    "AllowedP75")),
                allowed_p95=_safe_float(_pick(
                    row, "allowed_p95", "P95 Allowed",
                    "p95_allowed_amount",
                    "AllowedP95")),
                allowed_mean=_safe_float(_pick(
                    row, "allowed_mean", "Mean Allowed",
                    "mean_allowed_amount",
                    "AverageAllowed")),
                avg_member_oop=_safe_float(_pick(
                    row, "avg_member_oop",
                    "average_oop", "Avg Member OOP",
                    "MemberCostShare",
                    "patient_responsibility")),
                coverage_pct=_safe_float(_pick(
                    row, "coverage_pct", "CoverageShare",
                    "covered_lives_pct")),
            )


# ── Loader ────────────────────────────────────────────────────

def load_apcd_prices(
    store: Any,
    records: Iterable[APCDPriceRecord],
) -> int:
    """Persist APCD price records (idempotent upsert)."""
    store.init_db()
    now = datetime.now(timezone.utc).isoformat()
    n = 0
    with store.connect() as con:
        _ensure_table(con)
        con.execute("BEGIN IMMEDIATE")
        try:
            for r in records:
                con.execute(
                    "INSERT OR REPLACE INTO state_apcd_prices "
                    "(state, region, cpt_code, payer_type, "
                    " year, cpt_description, n_claims, "
                    " allowed_p25, allowed_p50, allowed_p75, "
                    " allowed_p95, allowed_mean, "
                    " avg_member_oop, coverage_pct, "
                    " loaded_at) "
                    "VALUES "
                    "(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (r.state, r.region, r.cpt_code,
                     r.payer_type, r.year,
                     r.cpt_description, r.n_claims,
                     r.allowed_p25, r.allowed_p50,
                     r.allowed_p75, r.allowed_p95,
                     r.allowed_mean, r.avg_member_oop,
                     r.coverage_pct, now),
                )
                n += 1
            con.commit()
        except Exception:
            con.rollback()
            raise
    return n


# ── Read helpers ─────────────────────────────────────────────

def get_apcd_prices_for_cpt(
    store: Any,
    cpt_code: str,
    *,
    state: Optional[str] = None,
    payer_type: Optional[str] = None,
    year: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """Lookup all matching APCD price rows for a CPT."""
    if not cpt_code:
        return []
    sql = ("SELECT * FROM state_apcd_prices "
           "WHERE cpt_code = ?")
    params: List[Any] = [str(cpt_code).strip()]
    if state:
        sql += " AND state = ?"
        params.append(state.upper())
    if payer_type:
        sql += " AND payer_type = ?"
        params.append(payer_type.lower())
    if year:
        sql += " AND year = ?"
        params.append(int(year))
    sql += " ORDER BY year DESC, state, region"
    with store.connect() as con:
        _ensure_table(con)
        rows = con.execute(sql, params).fetchall()
    return [dict(r) for r in rows]


def compute_commercial_medicare_ratio(
    store: Any,
    cpt_code: str,
    *,
    state: Optional[str] = None,
    year: Optional[int] = None,
) -> Optional[float]:
    """The single most-asked APCD question on a deal:
    *what's the commercial-to-Medicare price ratio for this CPT
    in this market?* National averages are ~2-3x for hospital
    outpatient, ~1.5-2x for physician services. A ratio above
    ~3.5x is a re-pricing risk; below ~1.4x is an opportunity.

    Returns commercial median / Medicare median, or None if
    either side is missing.
    """
    com = get_apcd_prices_for_cpt(
        store, cpt_code,
        state=state, payer_type="commercial", year=year)
    med = get_apcd_prices_for_cpt(
        store, cpt_code,
        state=state, payer_type="medicare_ffs", year=year)
    if not com or not med:
        # Try Medicare Advantage as fallback
        med = med or get_apcd_prices_for_cpt(
            store, cpt_code,
            state=state, payer_type="medicare_advantage",
            year=year)
    if not com or not med:
        return None

    def _weighted_p50(rows: List[Dict[str, Any]],
                      ) -> Optional[float]:
        total_n = 0
        total_v = 0.0
        for r in rows:
            v = r.get("allowed_p50")
            n = r.get("n_claims") or 1
            if v is None:
                continue
            total_v += float(v) * int(n)
            total_n += int(n)
        return total_v / total_n if total_n > 0 else None

    com_p50 = _weighted_p50(com)
    med_p50 = _weighted_p50(med)
    if com_p50 is None or med_p50 is None or med_p50 <= 0:
        return None
    return round(com_p50 / med_p50, 4)


def list_high_dispersion_procedures(
    store: Any,
    *,
    state: Optional[str] = None,
    payer_type: str = "commercial",
    year: Optional[int] = None,
    min_claims: int = 30,
    limit: int = 25,
) -> List[Dict[str, Any]]:
    """Procedures with the widest price spread (p95/p25 ratio)
    in a market — partner's first look at where rate-negotiation
    upside lives. A 5x p95/p25 ratio on a high-volume CPT is the
    classic add-on roll-up signal."""
    sql = (
        "SELECT cpt_code, cpt_description, state, region, "
        "       year, payer_type, n_claims, "
        "       allowed_p25, allowed_p50, "
        "       allowed_p75, allowed_p95, "
        "       (allowed_p95 / allowed_p25) AS dispersion "
        "FROM state_apcd_prices "
        "WHERE allowed_p25 > 0 AND allowed_p95 IS NOT NULL "
        "  AND n_claims >= ? "
        "  AND payer_type = ?"
    )
    params: List[Any] = [int(min_claims), payer_type.lower()]
    if state:
        sql += " AND state = ?"
        params.append(state.upper())
    if year:
        sql += " AND year = ?"
        params.append(int(year))
    sql += " ORDER BY dispersion DESC LIMIT ?"
    params.append(int(limit))
    with store.connect() as con:
        _ensure_table(con)
        rows = con.execute(sql, params).fetchall()
    return [dict(r) for r in rows]
