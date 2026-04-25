"""CMS Medicare Advantage enrollment + Star ratings + benchmarks.

Three distinct CMS public-data files cover MA market dynamics:

  • **Monthly Enrollment by CPSC** (Contract/Plan/State/County)
    — county-level enrollment per plan. Aggregating across plans
    yields MA penetration by county.
  • **Star Ratings** — annual quality scores (1-5) per contract.
    4.0+ unlocks the Quality Bonus Payment (5% of benchmark). The
    rating drives plan economics more than premium does.
  • **MA Ratebook** — annual county-level benchmark rates (the
    CMS payment ceiling). Benchmark = local FFS spending × growth
    factor × QBP adjustment. High-benchmark counties carry richer
    plans; the benchmark/FFS gap is the rebate dollars available.

Why this matters:

  • MA penetration tells you what fraction of Medicare lives are
    risk-contracted. A hospital in a 65% MA county gets paid
    differently than one in a 20% MA county — rate, prior-auth
    burden, and bad-debt all shift.
  • Star Ratings predict next-year reimbursement. A 4-star
    contract dropping to 3.5 loses ~5% revenue. We track the
    YoY change separately so partner can flag downgrade risk
    on MA-exposed assets.
  • Benchmark trends signal MA economics. CMS announced
    -1.12% net change for CY2025 (the first negative since 2008)
    — counties with low absolute benchmarks get squeezed first.

Schema covers all three datasets in one denormalized table, keyed
on (contract_id, plan_id, county_fips, year) with NULL fields for
metrics absent from a given source. Three loaders populate them
independently — partner can refresh enrollment monthly without
touching star data.

Public API::

    from rcm_mc.data.cms_ma_enrollment import (
        MAEnrollmentRecord,
        StarRatingRecord,
        BenchmarkRecord,
        load_ma_enrollment,
        load_star_ratings,
        load_ma_benchmarks,
        compute_county_ma_penetration,
        list_top_ma_penetration_counties,
        get_contract_quality,
        list_qbp_eligible_contracts,
    )
"""
from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional


# ── Schema ────────────────────────────────────────────────────

def _ensure_tables(con: Any) -> None:
    # Enrollment is per (contract × plan × county × month)
    con.execute(
        """
        CREATE TABLE IF NOT EXISTS cms_ma_enrollment (
            contract_id TEXT NOT NULL,
            plan_id TEXT NOT NULL,
            county_fips TEXT NOT NULL,
            year_month TEXT NOT NULL,
            organization_name TEXT,
            plan_type TEXT,
            state TEXT,
            county_name TEXT,
            enrollment INTEGER,
            loaded_at TEXT NOT NULL,
            PRIMARY KEY (contract_id, plan_id, county_fips,
                         year_month)
        )
        """
    )
    con.execute(
        "CREATE INDEX IF NOT EXISTS "
        "idx_ma_enroll_county "
        "ON cms_ma_enrollment(county_fips, year_month)"
    )
    con.execute(
        "CREATE INDEX IF NOT EXISTS "
        "idx_ma_enroll_contract "
        "ON cms_ma_enrollment(contract_id, year_month)"
    )

    # Star Ratings are per (contract × year)
    con.execute(
        """
        CREATE TABLE IF NOT EXISTS cms_ma_star_ratings (
            contract_id TEXT NOT NULL,
            year INTEGER NOT NULL,
            organization_name TEXT,
            contract_type TEXT,
            overall_star_rating REAL,
            part_c_star_rating REAL,
            part_d_star_rating REAL,
            measure_count INTEGER,
            qbp_eligible INTEGER,
            prior_year_overall REAL,
            star_change REAL,
            loaded_at TEXT NOT NULL,
            PRIMARY KEY (contract_id, year)
        )
        """
    )
    con.execute(
        "CREATE INDEX IF NOT EXISTS "
        "idx_ma_star_qbp "
        "ON cms_ma_star_ratings(qbp_eligible, year)"
    )

    # Benchmarks are per (county × year)
    con.execute(
        """
        CREATE TABLE IF NOT EXISTS cms_ma_benchmarks (
            county_fips TEXT NOT NULL,
            year INTEGER NOT NULL,
            state TEXT,
            county_name TEXT,
            ffs_baseline REAL,
            benchmark_aged REAL,
            benchmark_disabled REAL,
            benchmark_aged_qbp REAL,
            quartile INTEGER,
            yoy_change_pct REAL,
            loaded_at TEXT NOT NULL,
            PRIMARY KEY (county_fips, year)
        )
        """
    )
    con.execute(
        "CREATE INDEX IF NOT EXISTS "
        "idx_ma_benchmark_state "
        "ON cms_ma_benchmarks(state, year)"
    )


# ── Records ──────────────────────────────────────────────────

@dataclass
class MAEnrollmentRecord:
    """One contract × plan × county × month enrollment cell."""
    contract_id: str
    plan_id: str
    county_fips: str
    year_month: str   # 'YYYY-MM'
    organization_name: str = ""
    plan_type: str = ""    # HMO / PPO / D-SNP / C-SNP / I-SNP
    state: str = ""
    county_name: str = ""
    enrollment: Optional[int] = None


@dataclass
class StarRatingRecord:
    """One contract × year Star Rating snapshot."""
    contract_id: str
    year: int
    organization_name: str = ""
    contract_type: str = ""   # MAPD / MA-only / PDP / Cost
    overall_star_rating: Optional[float] = None
    part_c_star_rating: Optional[float] = None
    part_d_star_rating: Optional[float] = None
    measure_count: Optional[int] = None
    prior_year_overall: Optional[float] = None


@dataclass
class BenchmarkRecord:
    """One county × year MA Ratebook benchmark."""
    county_fips: str
    year: int
    state: str = ""
    county_name: str = ""
    ffs_baseline: Optional[float] = None       # PMPM
    benchmark_aged: Optional[float] = None     # PMPM, before QBP
    benchmark_disabled: Optional[float] = None
    benchmark_aged_qbp: Optional[float] = None  # post-QBP for 4+ stars
    quartile: Optional[int] = None  # 1=lowest FFS, 4=highest
    yoy_change_pct: Optional[float] = None


# ── Helpers ──────────────────────────────────────────────────

def _safe_float(v: Any) -> Optional[float]:
    if v is None or v == "":
        return None
    s = str(v).strip().replace(",", "").replace("$", "")
    s = s.replace("%", "")
    if s.lower() in ("not available", "n/a", "na",
                     "(x)", "suppressed", "*", "."):
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


def _pad_fips(s: str) -> str:
    s = str(s).strip()
    if not s:
        return s
    return s.zfill(5)


def _parse_year_month(raw: str, default_year: int = 0) -> str:
    """Normalize CMS month/year cells to 'YYYY-MM'.

    Inputs we accept: '2024-01', '202401', 'Jan 2024',
    'January 2024'. Returns '' on parse failure.
    """
    s = str(raw or "").strip()
    if not s:
        if default_year:
            return f"{default_year:04d}-01"
        return ""
    if len(s) >= 7 and s[4] == "-":
        try:
            int(s[:4])
            int(s[5:7])
            return s[:7]
        except ValueError:
            pass
    if len(s) == 6 and s.isdigit():
        return f"{s[:4]}-{s[4:6]}"
    months = {
        "jan": "01", "feb": "02", "mar": "03",
        "apr": "04", "may": "05", "jun": "06",
        "jul": "07", "aug": "08", "sep": "09",
        "oct": "10", "nov": "11", "dec": "12",
    }
    parts = s.split()
    if len(parts) == 2:
        m = months.get(parts[0][:3].lower())
        y = parts[1]
        if m and y.isdigit() and len(y) == 4:
            return f"{y}-{m}"
    return ""


# ── Parsers ──────────────────────────────────────────────────

def parse_ma_enrollment_csv(
    path: Any, *, year_month: str = "",
) -> Iterable[MAEnrollmentRecord]:
    """Parse a CMS MA Monthly Enrollment by CPSC CSV.

    The CMS public file uses ``Contract Number`` + ``Plan ID`` +
    ``State`` + ``County`` + ``SSA State County Code`` + ``Enrollment``.
    Some legacy exports use lowercase snake_case.
    """
    p = Path(str(path))
    if not p.is_file():
        raise FileNotFoundError(
            f"MA enrollment CSV not found at {p}")
    with p.open("r", encoding="utf-8", errors="replace",
                newline="") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            contract = str(_pick(
                row, "Contract Number", "contract_id",
                "ContractID", "Contract") or "").strip()
            plan = str(_pick(
                row, "Plan ID", "plan_id",
                "PlanID") or "").strip()
            fips = _pad_fips(str(_pick(
                row, "FIPS State and County Code",
                "county_fips", "County FIPS Code",
                "FIPS") or ""))
            if not (contract and fips):
                continue
            ym = _parse_year_month(str(_pick(
                row, "Year Month", "year_month",
                "Report Month") or ""), 0) or year_month
            if not ym:
                continue
            yield MAEnrollmentRecord(
                contract_id=contract,
                plan_id=plan or "000",
                county_fips=fips,
                year_month=ym,
                organization_name=str(_pick(
                    row, "Organization Marketing Name",
                    "organization_name",
                    "Organization Name") or "").strip(),
                plan_type=str(_pick(
                    row, "Plan Type", "plan_type") or "")
                .strip(),
                state=str(_pick(
                    row, "State", "state") or "")
                .strip().upper(),
                county_name=str(_pick(
                    row, "County", "county_name") or "")
                .strip(),
                enrollment=_safe_int(_pick(
                    row, "Enrollment", "enrollment",
                    "Total Enrollment")),
            )


def parse_star_ratings_csv(
    path: Any, *, year: int = 0,
) -> Iterable[StarRatingRecord]:
    """Parse a CMS Part C + D Star Ratings CSV.

    Two common shapes: the per-contract summary table
    (``Contract ID``, ``Overall MA-PD Rating``) and the long
    per-measure file. We parse the summary; the per-measure file
    requires aggregation outside the partner's diligence flow.
    """
    p = Path(str(path))
    if not p.is_file():
        raise FileNotFoundError(
            f"Star Ratings CSV not found at {p}")
    with p.open("r", encoding="utf-8", errors="replace",
                newline="") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            cid = str(_pick(
                row, "Contract ID", "contract_id",
                "ContractID") or "").strip()
            if not cid:
                continue
            yield StarRatingRecord(
                contract_id=cid,
                year=year or _safe_int(
                    _pick(row, "Year", "year",
                          "Rating Year")) or 0,
                organization_name=str(_pick(
                    row, "Organization Marketing Name",
                    "Contract Name",
                    "organization_name") or "").strip(),
                contract_type=str(_pick(
                    row, "Contract Type", "Type",
                    "contract_type") or "").strip(),
                overall_star_rating=_safe_float(_pick(
                    row, "Overall MA-PD Rating",
                    "Overall Rating",
                    "overall_star_rating",
                    "Summary Rating")),
                part_c_star_rating=_safe_float(_pick(
                    row, "Part C Summary Rating",
                    "Part C Rating",
                    "part_c_star_rating")),
                part_d_star_rating=_safe_float(_pick(
                    row, "Part D Summary Rating",
                    "Part D Rating",
                    "part_d_star_rating")),
                measure_count=_safe_int(_pick(
                    row, "Number of Measures",
                    "measure_count")),
                prior_year_overall=_safe_float(_pick(
                    row, "Prior Year Rating",
                    "Previous Year Rating",
                    "prior_year_overall")),
            )


def parse_ma_benchmarks_csv(
    path: Any, *, year: int = 0,
) -> Iterable[BenchmarkRecord]:
    """Parse a CMS MA Ratebook county benchmarks CSV.

    The Ratebook publishes one row per county with columns for
    FFS baseline, aged + disabled benchmarks, post-QBP rates, and
    benchmark quartile (1-4 = lowest-FFS to highest-FFS county
    grouping that determines benchmark cap multiplier: 95%, 100%,
    107.5%, 115%).
    """
    p = Path(str(path))
    if not p.is_file():
        raise FileNotFoundError(
            f"MA benchmarks CSV not found at {p}")
    with p.open("r", encoding="utf-8", errors="replace",
                newline="") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            fips = _pad_fips(str(_pick(
                row, "FIPS", "county_fips",
                "County FIPS",
                "SSA State and County Code") or ""))
            if not fips:
                continue
            yield BenchmarkRecord(
                county_fips=fips,
                year=year or _safe_int(
                    _pick(row, "Year", "year")) or 0,
                state=str(_pick(
                    row, "State", "state") or "")
                .strip().upper(),
                county_name=str(_pick(
                    row, "County", "county_name") or "")
                .strip(),
                ffs_baseline=_safe_float(_pick(
                    row, "FFS Baseline", "FFS PMPM",
                    "ffs_baseline")),
                benchmark_aged=_safe_float(_pick(
                    row, "Aged Benchmark",
                    "Benchmark Aged",
                    "benchmark_aged")),
                benchmark_disabled=_safe_float(_pick(
                    row, "Disabled Benchmark",
                    "Benchmark Disabled",
                    "benchmark_disabled")),
                benchmark_aged_qbp=_safe_float(_pick(
                    row, "Aged Benchmark with QBP",
                    "QBP Benchmark Aged",
                    "benchmark_aged_qbp")),
                quartile=_safe_int(_pick(
                    row, "Quartile", "Benchmark Quartile",
                    "quartile")),
                yoy_change_pct=_safe_float(_pick(
                    row, "YoY Change", "Annual Change",
                    "yoy_change_pct")),
            )


# ── Loaders ──────────────────────────────────────────────────

def load_ma_enrollment(
    store: Any,
    records: Iterable[MAEnrollmentRecord],
) -> int:
    store.init_db()
    now = datetime.now(timezone.utc).isoformat()
    n = 0
    with store.connect() as con:
        _ensure_tables(con)
        con.execute("BEGIN IMMEDIATE")
        try:
            for r in records:
                con.execute(
                    "INSERT OR REPLACE INTO "
                    "cms_ma_enrollment "
                    "(contract_id, plan_id, county_fips, "
                    " year_month, organization_name, "
                    " plan_type, state, county_name, "
                    " enrollment, loaded_at) "
                    "VALUES (?,?,?,?,?,?,?,?,?,?)",
                    (r.contract_id, r.plan_id,
                     r.county_fips, r.year_month,
                     r.organization_name, r.plan_type,
                     r.state, r.county_name,
                     r.enrollment, now),
                )
                n += 1
            con.commit()
        except Exception:
            con.rollback()
            raise
    return n


def load_star_ratings(
    store: Any,
    records: Iterable[StarRatingRecord],
) -> int:
    """Persist Star Ratings, computing star_change YoY from
    prior_year_overall when present.

    qbp_eligible flag: 4.0+ overall = QBP-eligible (5% bonus on
    benchmark, 65% rebate share). The flag is stored as 0/1 for
    SQL-friendly indexing on the QBP-eligible-contracts query."""
    store.init_db()
    now = datetime.now(timezone.utc).isoformat()
    n = 0
    with store.connect() as con:
        _ensure_tables(con)
        con.execute("BEGIN IMMEDIATE")
        try:
            for r in records:
                qbp = (1 if r.overall_star_rating is not None
                       and r.overall_star_rating >= 4.0
                       else 0)
                star_change = None
                if (r.overall_star_rating is not None
                        and r.prior_year_overall is not None):
                    star_change = round(
                        r.overall_star_rating
                        - r.prior_year_overall, 2)
                con.execute(
                    "INSERT OR REPLACE INTO "
                    "cms_ma_star_ratings "
                    "(contract_id, year, "
                    " organization_name, contract_type, "
                    " overall_star_rating, "
                    " part_c_star_rating, "
                    " part_d_star_rating, measure_count, "
                    " qbp_eligible, prior_year_overall, "
                    " star_change, loaded_at) "
                    "VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                    (r.contract_id, r.year,
                     r.organization_name, r.contract_type,
                     r.overall_star_rating,
                     r.part_c_star_rating,
                     r.part_d_star_rating,
                     r.measure_count, qbp,
                     r.prior_year_overall, star_change,
                     now),
                )
                n += 1
            con.commit()
        except Exception:
            con.rollback()
            raise
    return n


def load_ma_benchmarks(
    store: Any,
    records: Iterable[BenchmarkRecord],
) -> int:
    store.init_db()
    now = datetime.now(timezone.utc).isoformat()
    n = 0
    with store.connect() as con:
        _ensure_tables(con)
        con.execute("BEGIN IMMEDIATE")
        try:
            for r in records:
                con.execute(
                    "INSERT OR REPLACE INTO "
                    "cms_ma_benchmarks "
                    "(county_fips, year, state, "
                    " county_name, ffs_baseline, "
                    " benchmark_aged, "
                    " benchmark_disabled, "
                    " benchmark_aged_qbp, quartile, "
                    " yoy_change_pct, loaded_at) "
                    "VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                    (r.county_fips, r.year, r.state,
                     r.county_name, r.ffs_baseline,
                     r.benchmark_aged,
                     r.benchmark_disabled,
                     r.benchmark_aged_qbp,
                     r.quartile, r.yoy_change_pct, now),
                )
                n += 1
            con.commit()
        except Exception:
            con.rollback()
            raise
    return n


# ── Read helpers ─────────────────────────────────────────────

def compute_county_ma_penetration(
    store: Any,
    county_fips: str,
    *,
    year_month: Optional[str] = None,
    medicare_eligible_pop: Optional[int] = None,
) -> Optional[Dict[str, Any]]:
    """MA enrollment + penetration % for a county-month.

    Without medicare_eligible_pop the function returns just the
    raw enrollment sum. With it, returns the penetration ratio —
    the partner-relevant number for a deal in the catchment.
    """
    if not county_fips:
        return None
    fips = _pad_fips(county_fips)
    sql = ("SELECT year_month, "
           "       SUM(enrollment) AS total_enrollment, "
           "       COUNT(DISTINCT contract_id) "
           "         AS n_contracts "
           "FROM cms_ma_enrollment "
           "WHERE county_fips = ?")
    params: List[Any] = [fips]
    if year_month:
        sql += " AND year_month = ?"
        params.append(year_month)
    sql += " GROUP BY year_month ORDER BY year_month DESC LIMIT 1"
    with store.connect() as con:
        _ensure_tables(con)
        row = con.execute(sql, params).fetchone()
    if not row:
        return None
    out = dict(row)
    if (medicare_eligible_pop and medicare_eligible_pop > 0
            and out["total_enrollment"]):
        out["ma_penetration_pct"] = round(
            out["total_enrollment"]
            / medicare_eligible_pop, 4)
    return out


def list_top_ma_penetration_counties(
    store: Any,
    *,
    state: Optional[str] = None,
    year_month: Optional[str] = None,
    limit: int = 25,
) -> List[Dict[str, Any]]:
    """Counties ranked by raw MA enrollment volume — caller
    layers Medicare-eligible population on top to compute
    penetration %. (Eligible-pop comes from census_demographics
    or the Medicare Geographic Variation public-use file.)"""
    sql = ("SELECT county_fips, state, county_name, "
           "       year_month, "
           "       SUM(enrollment) AS total_enrollment, "
           "       COUNT(DISTINCT contract_id) "
           "         AS n_contracts "
           "FROM cms_ma_enrollment "
           "WHERE enrollment IS NOT NULL")
    params: List[Any] = []
    if state:
        sql += " AND state = ?"
        params.append(state.upper())
    if year_month:
        sql += " AND year_month = ?"
        params.append(year_month)
    sql += (" GROUP BY county_fips, year_month "
            "ORDER BY total_enrollment DESC LIMIT ?")
    params.append(int(limit))
    with store.connect() as con:
        _ensure_tables(con)
        rows = con.execute(sql, params).fetchall()
    return [dict(r) for r in rows]


def get_contract_quality(
    store: Any,
    contract_id: str,
    *,
    year: Optional[int] = None,
) -> Optional[Dict[str, Any]]:
    """Most-recent (or specified-year) Star Ratings for a contract."""
    if not contract_id:
        return None
    sql = ("SELECT * FROM cms_ma_star_ratings "
           "WHERE contract_id = ?")
    params: List[Any] = [contract_id.strip()]
    if year:
        sql += " AND year = ?"
        params.append(int(year))
    sql += " ORDER BY year DESC LIMIT 1"
    with store.connect() as con:
        _ensure_tables(con)
        row = con.execute(sql, params).fetchone()
    if not row:
        return None
    out = dict(row)
    out["qbp_eligible"] = bool(out.get("qbp_eligible", 0))
    return out


def list_qbp_eligible_contracts(
    store: Any,
    *,
    year: Optional[int] = None,
    min_rating: float = 4.0,
    limit: int = 100,
) -> List[Dict[str, Any]]:
    """Contracts at or above min_rating in a year. The 4.0
    threshold is hard-coded in CMS rules — anything else is
    research/sensitivity territory but we let callers override
    so they can model the proposed 4.5 cliff."""
    sql = ("SELECT * FROM cms_ma_star_ratings "
           "WHERE overall_star_rating >= ?")
    params: List[Any] = [float(min_rating)]
    if year:
        sql += " AND year = ?"
        params.append(int(year))
    sql += " ORDER BY overall_star_rating DESC LIMIT ?"
    params.append(int(limit))
    with store.connect() as con:
        _ensure_tables(con)
        rows = con.execute(sql, params).fetchall()
    return [dict(r) for r in rows]


def get_county_benchmark(
    store: Any,
    county_fips: str,
    *,
    year: Optional[int] = None,
) -> Optional[Dict[str, Any]]:
    """Most-recent (or specified-year) MA benchmark for a county."""
    if not county_fips:
        return None
    sql = ("SELECT * FROM cms_ma_benchmarks "
           "WHERE county_fips = ?")
    params: List[Any] = [_pad_fips(county_fips)]
    if year:
        sql += " AND year = ?"
        params.append(int(year))
    sql += " ORDER BY year DESC LIMIT 1"
    with store.connect() as con:
        _ensure_tables(con)
        row = con.execute(sql, params).fetchone()
    return dict(row) if row else None
