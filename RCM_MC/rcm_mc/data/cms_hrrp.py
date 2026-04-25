"""CMS Hospital Readmissions Reduction Program (HRRP) penalty file.

Public dataset:
    https://data.cms.gov/provider-data/dataset/9n3s-kdb3

What HRRP adds beyond General Info's "below national readmission"
flag: a DOLLAR-QUANTIFIED measure of CMS penalty exposure per CCN.

Mechanism: under HRRP, CMS reduces a hospital's Medicare IPPS
payments by up to 3% based on its 30-day readmission rates for
six conditions (AMI, COPD, HF, PNE, CABG, THA/TKA). The penalty
applies for the upcoming federal fiscal year and is published
annually as the FY{year}_HRRP_Hospital file.

For RCM diligence:

  - 1% HRRP penalty on a typical Medicare-heavy hospital ≈ 30-40bps
    of EBITDA exposure. A 3% penalty (the cap) ≈ 100bps. Direct
    bridge math.
  - Trend matters: penalty climbing year-over-year is a leading
    indicator that quality programs aren't working.
  - Threshold-aware: a hospital scraping under the 1% line in the
    current year may be 0.5% next year just from regression to
    the mean — discount the bid accordingly.

Schema in SQLite::

    CREATE TABLE IF NOT EXISTS cms_hrrp (
        ccn TEXT PRIMARY KEY,
        facility_name TEXT,
        state TEXT,
        fiscal_year INTEGER,
        excess_readmission_ratio REAL,
        payment_adjustment_pct REAL,
        loaded_at TEXT NOT NULL
    )

Public API::

    parse_hrrp_csv(path) -> List[HRRPRecord]
    load_hrrp_to_store(store, records) -> int
    refresh_hrrp_source(store) -> int
    get_penalty_by_ccn(store, ccn) -> Optional[dict]
    list_high_penalty(store, min_pct=2.0) -> List[dict]
"""
from __future__ import annotations

import csv
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

_COL_CCN          = ("PRVDR_NUM", "Facility ID", "ccn", "CCN")
_COL_NAME         = ("FAC_NAME", "Facility Name", "facility_name")
_COL_STATE        = ("State", "STATE_CD", "state")
_COL_FY           = ("FY", "Fiscal Year", "fiscal_year")
_COL_ERR          = ("Excess Readmission Ratio", "excess_readmission_ratio",
                     "ERR")
_COL_ADJUSTMENT   = ("Payment Adjustment Factor",
                     "payment_adjustment_factor",
                     "Payment Adjustment %",
                     "payment_adjustment_pct")


DEFAULT_HRRP_SAMPLE_PATH = Path(__file__).parent / "hrrp_sample.csv"


@dataclass
class HRRPRecord:
    ccn: str
    facility_name: str = ""
    state: str = ""
    fiscal_year: Optional[int] = None
    excess_readmission_ratio: Optional[float] = None
    payment_adjustment_pct: Optional[float] = None


def _first_present(row: Dict[str, str], candidates) -> str:
    for c in candidates:
        if c in row and row[c] is not None:
            v = str(row[c]).strip()
            if v:
                return v
    return ""


def _safe_float(v: Any) -> Optional[float]:
    if v is None or v == "" or str(v).strip() in (
        "Not Available", "N/A", "NA",
    ):
        return None
    try:
        return float(str(v).strip())
    except (TypeError, ValueError):
        return None


def _safe_int(v: Any) -> Optional[int]:
    if v is None or v == "":
        return None
    try:
        return int(str(v).strip())
    except (TypeError, ValueError):
        return None


def _normalize_payment_adjustment(raw: str) -> Optional[float]:
    """CMS publishes the adjustment as either a factor (0.99 = 1%
    penalty) or a percentage (1.0 = 1% penalty). We normalize to
    PERCENT — i.e. 1.0 = 1% reduction, 3.0 = the 3% cap. This is
    what partners say out loud.

    Heuristic: any value < 0.5 is treated as a factor (0.99 → 1.0),
    any value ≥ 0.5 is treated as a percentage already. CMS
    factors are always 0.97-1.00 (since cap is 3%) and percentages
    are 0-3, so the threshold is unambiguous.
    """
    f = _safe_float(raw)
    if f is None:
        return None
    if 0.95 <= f <= 1.0:
        # Factor form: 1.0 = no penalty, 0.99 = 1% penalty
        return round((1.0 - f) * 100.0, 3)
    if 0 <= f <= 5:
        # Already in percent
        return round(f, 3)
    return None  # bogus value


def parse_hrrp_csv(path: Path) -> List[HRRPRecord]:
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(f"HRRP CSV not found at {path}")

    out: List[HRRPRecord] = []
    with path.open("r", encoding="utf-8", errors="replace") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            ccn = _first_present(row, _COL_CCN)
            if not ccn:
                continue
            out.append(HRRPRecord(
                ccn=ccn,
                facility_name=_first_present(row, _COL_NAME),
                state=_first_present(row, _COL_STATE).upper(),
                fiscal_year=_safe_int(_first_present(row, _COL_FY)),
                excess_readmission_ratio=_safe_float(
                    _first_present(row, _COL_ERR)),
                payment_adjustment_pct=_normalize_payment_adjustment(
                    _first_present(row, _COL_ADJUSTMENT)),
            ))
    return out


def _ensure_table(store: Any) -> None:
    store.init_db()
    with store.connect() as con:
        con.execute(
            """CREATE TABLE IF NOT EXISTS cms_hrrp (
                ccn TEXT PRIMARY KEY,
                facility_name TEXT NOT NULL DEFAULT '',
                state TEXT NOT NULL DEFAULT '',
                fiscal_year INTEGER,
                excess_readmission_ratio REAL,
                payment_adjustment_pct REAL,
                loaded_at TEXT NOT NULL
            )"""
        )
        con.execute(
            "CREATE INDEX IF NOT EXISTS idx_cms_hrrp_penalty "
            "ON cms_hrrp(payment_adjustment_pct DESC) "
            "WHERE payment_adjustment_pct IS NOT NULL"
        )
        con.commit()


def load_hrrp_to_store(store: Any, records: List[HRRPRecord]) -> int:
    from datetime import datetime as _dt, timezone as _tz
    _ensure_table(store)
    now = _dt.now(_tz.utc).isoformat()
    with store.connect() as con:
        con.execute("BEGIN IMMEDIATE")
        try:
            for r in records:
                con.execute(
                    """INSERT OR REPLACE INTO cms_hrrp (
                        ccn, facility_name, state, fiscal_year,
                        excess_readmission_ratio,
                        payment_adjustment_pct, loaded_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (r.ccn, r.facility_name, r.state, r.fiscal_year,
                     r.excess_readmission_ratio,
                     r.payment_adjustment_pct, now),
                )
            con.commit()
        except Exception:
            con.rollback()
            raise
    return len(records)


def refresh_hrrp_source(store: Any) -> int:
    import os as _os
    path = Path(
        _os.environ.get("RCM_MC_HRRP_CSV", DEFAULT_HRRP_SAMPLE_PATH)
    )
    return load_hrrp_to_store(store, parse_hrrp_csv(path))


def get_penalty_by_ccn(
    store: Any, ccn: str,
) -> Optional[Dict[str, Any]]:
    if not ccn:
        return None
    _ensure_table(store)
    with store.connect() as con:
        row = con.execute(
            "SELECT * FROM cms_hrrp WHERE ccn = ?", (str(ccn),),
        ).fetchone()
    return dict(row) if row else None


def list_high_penalty(
    store: Any, *, min_pct: float = 2.0,
) -> List[Dict[str, Any]]:
    """Return CCNs at or above a penalty threshold — useful for
    surfacing 'your portfolio has 4 hospitals at >2% HRRP penalty'."""
    _ensure_table(store)
    with store.connect() as con:
        rows = con.execute(
            "SELECT * FROM cms_hrrp "
            "WHERE payment_adjustment_pct IS NOT NULL "
            "AND payment_adjustment_pct >= ? "
            "ORDER BY payment_adjustment_pct DESC",
            (float(min_pct),),
        ).fetchall()
    return [dict(r) for r in rows]
