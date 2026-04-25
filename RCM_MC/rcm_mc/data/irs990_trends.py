"""IRS 990 multi-year financial trend store + analytics.

The existing ``irs990.py`` fetches a single EIN's filings and
cross-checks against HCRIS. ``irs990_loader.py`` ingests one
parsed 990 into the benchmarks store. Neither persists the full
multi-year history a partner needs for trend analysis: how is
revenue trending? Is executive compensation growing faster than
revenue? Are net assets eroding?

This module fills that gap.

  • Schema: irs990_filings — one row per (EIN, tax_year) with
    revenue / expenses / net_assets / top5_exec_comp + the
    operator name + state for cohort grouping.
  • Storage: store_filing / store_filings_bulk for ingestion.
  • Analytics:
      compute_financial_trends(ein) — 3-year CAGRs + flags
      cohort_trend_summary(state=, sector=) — across-EIN
        median trends for benchmarking
      flag_concerning_trends(ein) — auto-flag list (declining
        net assets, exec-comp-vs-revenue gap, etc.)

Joins back to HCRIS via the analyst-supplied CCN↔EIN mapping
(or downstream consumers can join via the EIN column).
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional

logger = logging.getLogger(__name__)


# ── Schema ────────────────────────────────────────────────────

def _ensure_table(con: Any) -> None:
    con.execute(
        """
        CREATE TABLE IF NOT EXISTS irs990_filings (
            ein TEXT NOT NULL,
            tax_year INTEGER NOT NULL,
            organization_name TEXT,
            state TEXT,
            ccn TEXT,
            total_revenue REAL,
            total_expenses REAL,
            net_assets_end_of_year REAL,
            net_assets_beginning REAL,
            top5_exec_comp_total REAL,
            program_service_revenue REAL,
            contributions_revenue REAL,
            investment_income REAL,
            employee_count INTEGER,
            volunteer_count INTEGER,
            loaded_at TEXT NOT NULL,
            PRIMARY KEY (ein, tax_year)
        )
        """
    )
    con.execute(
        "CREATE INDEX IF NOT EXISTS idx_irs990_state "
        "ON irs990_filings(state)"
    )
    con.execute(
        "CREATE INDEX IF NOT EXISTS idx_irs990_ccn "
        "ON irs990_filings(ccn)"
    )


@dataclass
class FilingRecord:
    """One year's 990 row."""
    ein: str
    tax_year: int
    organization_name: str = ""
    state: str = ""
    ccn: str = ""
    total_revenue: Optional[float] = None
    total_expenses: Optional[float] = None
    net_assets_end_of_year: Optional[float] = None
    net_assets_beginning: Optional[float] = None
    top5_exec_comp_total: Optional[float] = None
    program_service_revenue: Optional[float] = None
    contributions_revenue: Optional[float] = None
    investment_income: Optional[float] = None
    employee_count: Optional[int] = None
    volunteer_count: Optional[int] = None


@dataclass
class TrendResult:
    """Multi-year trend summary for one EIN."""
    ein: str
    organization_name: str = ""
    n_years: int = 0
    years: List[int] = field(default_factory=list)
    revenue_cagr_3y: Optional[float] = None
    expense_cagr_3y: Optional[float] = None
    net_assets_cagr_3y: Optional[float] = None
    exec_comp_cagr_3y: Optional[float] = None
    latest_revenue: Optional[float] = None
    latest_net_assets: Optional[float] = None
    margin_pct_latest: Optional[float] = None
    concerning_flags: List[str] = field(default_factory=list)


def _cagr(start: float, end: float, years: int) -> Optional[float]:
    """Compound annual growth rate. Returns None for invalid
    inputs."""
    if not start or start <= 0 or years <= 0:
        return None
    if end <= 0:
        return -1.0  # full erosion
    return (end / start) ** (1.0 / years) - 1.0


# ── Ingestion ─────────────────────────────────────────────────

def store_filing(
    store: Any,
    filing: FilingRecord,
) -> bool:
    """Upsert one filing. Returns True if written."""
    if not filing.ein or not filing.tax_year:
        return False
    store.init_db()
    now = datetime.now(timezone.utc).isoformat()
    with store.connect() as con:
        _ensure_table(con)
        con.execute(
            "INSERT OR REPLACE INTO irs990_filings (ein, "
            "tax_year, organization_name, state, ccn, "
            "total_revenue, total_expenses, "
            "net_assets_end_of_year, net_assets_beginning, "
            "top5_exec_comp_total, program_service_revenue, "
            "contributions_revenue, investment_income, "
            "employee_count, volunteer_count, loaded_at) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (filing.ein, filing.tax_year,
             filing.organization_name, filing.state,
             filing.ccn, filing.total_revenue,
             filing.total_expenses,
             filing.net_assets_end_of_year,
             filing.net_assets_beginning,
             filing.top5_exec_comp_total,
             filing.program_service_revenue,
             filing.contributions_revenue,
             filing.investment_income,
             filing.employee_count, filing.volunteer_count,
             now),
        )
        con.commit()
    return True


def store_filings_bulk(
    store: Any,
    filings: Iterable[FilingRecord],
) -> int:
    """Bulk upsert. Returns count written."""
    n = 0
    for f in filings:
        if store_filing(store, f):
            n += 1
    return n


# ── Trend analytics ──────────────────────────────────────────

def compute_financial_trends(
    store: Any,
    ein: str,
) -> Optional[TrendResult]:
    """Multi-year trend analysis for one EIN.

    Returns None if the EIN has fewer than 2 filings.
    Computes 3-year CAGRs + flags concerning patterns.
    """
    if not ein:
        return None
    with store.connect() as con:
        _ensure_table(con)
        rows = con.execute(
            "SELECT * FROM irs990_filings WHERE ein = ? "
            "ORDER BY tax_year ASC",
            (str(ein).strip(),),
        ).fetchall()
    if len(rows) < 2:
        return None

    years = [int(r["tax_year"]) for r in rows]
    n_years = len(rows)
    span = years[-1] - years[0]

    # Earliest + latest values for CAGR. Use a 3-year window
    # when available; fall back to the full span.
    target_window = min(3, span) if span > 0 else 1
    # Find the row that's `target_window` years before the latest.
    target_year = years[-1] - target_window
    earlier = next((r for r in rows
                    if int(r["tax_year"]) <= target_year),
                   rows[0])
    latest = rows[-1]
    actual_span = max(1, int(latest["tax_year"])
                       - int(earlier["tax_year"]))

    def _val(row, col):
        v = row[col]
        return float(v) if v is not None else None

    rev_start = _val(earlier, "total_revenue")
    rev_end = _val(latest, "total_revenue")
    exp_start = _val(earlier, "total_expenses")
    exp_end = _val(latest, "total_expenses")
    na_start = _val(earlier, "net_assets_end_of_year")
    na_end = _val(latest, "net_assets_end_of_year")
    ec_start = _val(earlier, "top5_exec_comp_total")
    ec_end = _val(latest, "top5_exec_comp_total")

    rev_cagr = (_cagr(rev_start, rev_end, actual_span)
                if rev_start and rev_end else None)
    exp_cagr = (_cagr(exp_start, exp_end, actual_span)
                if exp_start and exp_end else None)
    na_cagr = (_cagr(na_start, na_end, actual_span)
               if na_start and na_end else None)
    ec_cagr = (_cagr(ec_start, ec_end, actual_span)
               if ec_start and ec_end else None)

    margin_pct: Optional[float] = None
    if rev_end and exp_end and rev_end > 0:
        margin_pct = (rev_end - exp_end) / rev_end

    flags: List[str] = []
    if na_cagr is not None and na_cagr < -0.05:
        flags.append(
            f"Net assets eroding "
            f"{na_cagr*100:+.1f}% CAGR — material balance-sheet "
            f"weakness over {actual_span} years.")
    if (ec_cagr is not None and rev_cagr is not None
            and (ec_cagr - rev_cagr) > 0.05):
        flags.append(
            f"Executive comp growing {ec_cagr*100:+.1f}% CAGR "
            f"vs revenue {rev_cagr*100:+.1f}% — comp outpacing "
            f"top line by "
            f"{(ec_cagr - rev_cagr)*100:.1f}pp.")
    if (rev_cagr is not None and exp_cagr is not None
            and (exp_cagr - rev_cagr) > 0.03):
        flags.append(
            f"Expenses growing faster than revenue "
            f"({exp_cagr*100:+.1f}% vs {rev_cagr*100:+.1f}%) — "
            f"operating-leverage compression.")
    if margin_pct is not None and margin_pct < 0:
        flags.append(
            f"Latest filing margin "
            f"{margin_pct*100:.1f}% — operating losses.")

    return TrendResult(
        ein=str(ein).strip(),
        organization_name=(latest["organization_name"]
                           or "").strip(),
        n_years=n_years, years=years,
        revenue_cagr_3y=(round(rev_cagr, 4)
                         if rev_cagr is not None else None),
        expense_cagr_3y=(round(exp_cagr, 4)
                         if exp_cagr is not None else None),
        net_assets_cagr_3y=(round(na_cagr, 4)
                            if na_cagr is not None else None),
        exec_comp_cagr_3y=(round(ec_cagr, 4)
                           if ec_cagr is not None else None),
        latest_revenue=rev_end,
        latest_net_assets=na_end,
        margin_pct_latest=(round(margin_pct, 4)
                           if margin_pct is not None else None),
        concerning_flags=flags,
    )


def flag_concerning_trends(
    store: Any,
    ein: str,
) -> List[str]:
    """Convenience wrapper — just the flags."""
    result = compute_financial_trends(store, ein)
    return result.concerning_flags if result else []


def cohort_trend_summary(
    store: Any,
    *,
    state: Optional[str] = None,
) -> Dict[str, Any]:
    """Across-EIN median trends for the cohort. Used for
    benchmarking a target's trend rates against peer non-profits."""
    sql = ("SELECT DISTINCT ein FROM irs990_filings")
    params: List[Any] = []
    if state:
        sql += " WHERE state = ?"
        params.append(state.upper())
    with store.connect() as con:
        _ensure_table(con)
        eins = [r["ein"]
                for r in con.execute(sql, params).fetchall()]

    rev_cagrs: List[float] = []
    na_cagrs: List[float] = []
    margins: List[float] = []
    for ein in eins:
        t = compute_financial_trends(store, ein)
        if not t:
            continue
        if t.revenue_cagr_3y is not None:
            rev_cagrs.append(t.revenue_cagr_3y)
        if t.net_assets_cagr_3y is not None:
            na_cagrs.append(t.net_assets_cagr_3y)
        if t.margin_pct_latest is not None:
            margins.append(t.margin_pct_latest)

    def _median(values: List[float]) -> Optional[float]:
        if not values:
            return None
        s = sorted(values)
        return s[len(s) // 2]

    return {
        "n_eins": len(eins),
        "state_filter": state,
        "median_revenue_cagr": _median(rev_cagrs),
        "median_net_assets_cagr": _median(na_cagrs),
        "median_margin_pct": _median(margins),
    }
