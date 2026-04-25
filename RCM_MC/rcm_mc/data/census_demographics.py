"""US Census demographic data for hospital catchment markets.

The American Community Survey (ACS) 5-year estimates publish
population + age + income + insurance-coverage + growth data at
multiple geographies. For PE diligence on hospitals / MSOs / ASCs,
the CBSA (metropolitan statistical area) is the right granularity
— it matches how partners think about market overlap.

Why this matters:
  • Population growth → forward demand
  • Age distribution → 65+ share drives Medicare volume; 0-17
    share drives pediatric / OB volume
  • Income → payer-mix proxy (high commercial mix in higher-
    income markets)
  • Uninsured rate → bad-debt risk
  • Coverage source mix → policy-exposure (Medicaid expansion
    states have different ACA dynamics)

Public API::

    from rcm_mc.data.census_demographics import (
        MarketDemographics,
        load_acs_demographics,
        get_demographics_for_cbsa,
        compute_market_attractiveness_score,
        list_top_growth_markets,
    )
"""
from __future__ import annotations

import csv
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional


# ── Schema ────────────────────────────────────────────────────

def _ensure_table(con: Any) -> None:
    con.execute(
        """
        CREATE TABLE IF NOT EXISTS census_demographics (
            cbsa TEXT NOT NULL,
            year INTEGER NOT NULL,
            geography_name TEXT,
            state TEXT,
            population INTEGER,
            population_growth_5yr REAL,
            pct_under_18 REAL,
            pct_18_64 REAL,
            pct_65_plus REAL,
            median_household_income REAL,
            poverty_rate REAL,
            pct_uninsured REAL,
            pct_employer_insurance REAL,
            pct_medicaid REAL,
            pct_medicare REAL,
            attractiveness_score REAL,
            loaded_at TEXT NOT NULL,
            PRIMARY KEY (cbsa, year)
        )
        """
    )
    con.execute(
        "CREATE INDEX IF NOT EXISTS "
        "idx_census_state ON census_demographics(state)"
    )
    con.execute(
        "CREATE INDEX IF NOT EXISTS "
        "idx_census_growth "
        "ON census_demographics(population_growth_5yr DESC)"
    )


@dataclass
class MarketDemographics:
    """One CBSA × year demographic snapshot."""
    cbsa: str
    year: int
    geography_name: str = ""
    state: str = ""
    population: Optional[int] = None
    population_growth_5yr: Optional[float] = None    # 5y CAGR
    pct_under_18: Optional[float] = None
    pct_18_64: Optional[float] = None
    pct_65_plus: Optional[float] = None
    median_household_income: Optional[float] = None
    poverty_rate: Optional[float] = None
    pct_uninsured: Optional[float] = None
    pct_employer_insurance: Optional[float] = None
    pct_medicaid: Optional[float] = None
    pct_medicare: Optional[float] = None
    attractiveness_score: Optional[float] = None


def _safe_float(v: Any) -> Optional[float]:
    if v is None or v == "":
        return None
    s = str(v).strip().replace(",", "").replace("%", "")
    if s.lower() in ("not available", "n/a", "na", "(x)"):
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


def parse_acs_csv(
    path: Any, *, year: int = 0,
) -> Iterable[MarketDemographics]:
    """Parse an ACS 5-year CSV into MarketDemographics records.

    The ACS column-name convention varies across vintages; we
    accept the common B-table aliases: B01003 (population),
    B19013 (median income), B27001 (insurance status), etc.
    """
    p = Path(str(path))
    if not p.is_file():
        raise FileNotFoundError(
            f"ACS CSV not found at {p}")
    with p.open("r", encoding="utf-8", errors="replace",
                newline="") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            cbsa = str(_pick(
                row, "cbsa", "CBSA", "GEOID",
                "Geography_Code") or "").strip()
            if not cbsa:
                continue
            yield MarketDemographics(
                cbsa=cbsa,
                year=year or _safe_int(
                    _pick(row, "year", "Year")) or 0,
                geography_name=str(_pick(
                    row, "geography_name", "NAME",
                    "Geography") or "").strip(),
                state=str(_pick(
                    row, "state", "State") or "").strip().upper(),
                population=_safe_int(_pick(
                    row, "population",
                    "B01003_001E", "Total_Population")),
                population_growth_5yr=_safe_float(_pick(
                    row, "population_growth_5yr",
                    "Pop_Growth_5yr")),
                pct_under_18=_safe_float(_pick(
                    row, "pct_under_18", "Pct_Under_18")),
                pct_18_64=_safe_float(_pick(
                    row, "pct_18_64", "Pct_18_64")),
                pct_65_plus=_safe_float(_pick(
                    row, "pct_65_plus", "Pct_65_Plus")),
                median_household_income=_safe_float(_pick(
                    row, "median_household_income",
                    "B19013_001E", "Median_Income")),
                poverty_rate=_safe_float(_pick(
                    row, "poverty_rate", "Poverty_Rate")),
                pct_uninsured=_safe_float(_pick(
                    row, "pct_uninsured",
                    "Uninsured_Rate")),
                pct_employer_insurance=_safe_float(_pick(
                    row, "pct_employer_insurance",
                    "Employer_Insurance_Rate")),
                pct_medicaid=_safe_float(_pick(
                    row, "pct_medicaid", "Medicaid_Rate")),
                pct_medicare=_safe_float(_pick(
                    row, "pct_medicare", "Medicare_Rate")),
            )


def compute_market_attractiveness_score(
    d: MarketDemographics,
) -> float:
    """Composite 0-1 score: how attractive is this market for a
    healthcare-PE asset?

    Inputs weighted toward partner-relevant signals:
      • Population growth (+30%) — forward demand
      • % 65+ (+20%) — Medicare volume driver
      • Median income (+15%) — commercial revenue / payer mix
      • (1 - Uninsured rate) (+15%) — collections quality
      • Population scale (+10%, log-scaled)
      • (1 - Poverty rate) (+10%) — bad-debt risk

    Returns 0-1 score; higher = more attractive.
    """
    score = 0.0
    weights = 0.0

    if d.population_growth_5yr is not None:
        # Cap growth contribution at +5% / -2% per year for sanity
        normalized = min(1.0, max(0.0,
                                  (d.population_growth_5yr
                                   + 0.02) / 0.07))
        score += 0.30 * normalized
        weights += 0.30
    if d.pct_65_plus is not None:
        # 18% national avg → score linearly above that
        normalized = min(1.0, max(0.0,
                                  (d.pct_65_plus - 0.10)
                                  / 0.20))
        score += 0.20 * normalized
        weights += 0.20
    if d.median_household_income is not None:
        # National median ~$75K — score 0-1 over $30K-$120K
        normalized = min(1.0, max(0.0,
                                  (d.median_household_income
                                   - 30_000) / 90_000))
        score += 0.15 * normalized
        weights += 0.15
    if d.pct_uninsured is not None:
        # Inverse — lower uninsured = better. National ~9%
        normalized = min(1.0, max(0.0,
                                  1.0 - d.pct_uninsured / 0.20))
        score += 0.15 * normalized
        weights += 0.15
    if d.population is not None and d.population > 0:
        # Log-scaled: 50K → 0.0, 5M → 1.0
        from math import log10
        normalized = min(1.0, max(0.0,
                                  (log10(d.population) - 4.7)
                                  / 2.0))
        score += 0.10 * normalized
        weights += 0.10
    if d.poverty_rate is not None:
        # Inverse — lower poverty = better. National ~12%
        normalized = min(1.0, max(0.0,
                                  1.0 - d.poverty_rate / 0.30))
        score += 0.10 * normalized
        weights += 0.10

    if weights <= 0:
        return 0.0
    # Renormalize to the weights we actually used (so
    # incomplete data still produces a defensible 0-1)
    return round(score / weights, 4)


# ── Loader ────────────────────────────────────────────────────

def load_acs_demographics(
    store: Any,
    records: Iterable[MarketDemographics],
) -> int:
    """Persist demographic records, computing the attractiveness
    score on insert when not already supplied."""
    store.init_db()
    now = datetime.now(timezone.utc).isoformat()
    n = 0
    with store.connect() as con:
        _ensure_table(con)
        con.execute("BEGIN IMMEDIATE")
        try:
            for d in records:
                if d.attractiveness_score is None:
                    d.attractiveness_score = (
                        compute_market_attractiveness_score(d))
                con.execute(
                    "INSERT OR REPLACE INTO census_demographics "
                    "(cbsa, year, geography_name, state, "
                    " population, population_growth_5yr, "
                    " pct_under_18, pct_18_64, pct_65_plus, "
                    " median_household_income, poverty_rate, "
                    " pct_uninsured, pct_employer_insurance, "
                    " pct_medicaid, pct_medicare, "
                    " attractiveness_score, loaded_at) "
                    "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (d.cbsa, d.year, d.geography_name, d.state,
                     d.population, d.population_growth_5yr,
                     d.pct_under_18, d.pct_18_64,
                     d.pct_65_plus, d.median_household_income,
                     d.poverty_rate, d.pct_uninsured,
                     d.pct_employer_insurance, d.pct_medicaid,
                     d.pct_medicare,
                     d.attractiveness_score, now),
                )
                n += 1
            con.commit()
        except Exception:
            con.rollback()
            raise
    return n


# ── Read helpers ─────────────────────────────────────────────

def get_demographics_for_cbsa(
    store: Any,
    cbsa: str,
    *,
    year: Optional[int] = None,
) -> Optional[Dict[str, Any]]:
    """Lookup the most-recent (or specified-year) snapshot."""
    if not cbsa:
        return None
    sql = ("SELECT * FROM census_demographics "
           "WHERE cbsa = ?")
    params: List[Any] = [str(cbsa).strip()]
    if year:
        sql += " AND year = ?"
        params.append(int(year))
    sql += " ORDER BY year DESC LIMIT 1"
    with store.connect() as con:
        _ensure_table(con)
        row = con.execute(sql, params).fetchone()
    return dict(row) if row else None


def list_top_growth_markets(
    store: Any,
    *,
    state: Optional[str] = None,
    limit: int = 25,
    min_population: int = 100_000,
) -> List[Dict[str, Any]]:
    """Top CBSAs by 5-year population CAGR — partner's first
    look at where demand is growing fastest."""
    sql = ("SELECT * FROM census_demographics "
           "WHERE population_growth_5yr IS NOT NULL "
           "  AND population >= ?")
    params: List[Any] = [int(min_population)]
    if state:
        sql += " AND state = ?"
        params.append(state.upper())
    sql += " ORDER BY population_growth_5yr DESC LIMIT ?"
    params.append(int(limit))
    with store.connect() as con:
        _ensure_table(con)
        rows = con.execute(sql, params).fetchall()
    return [dict(r) for r in rows]


def list_top_attractive_markets(
    store: Any,
    *,
    state: Optional[str] = None,
    limit: int = 25,
) -> List[Dict[str, Any]]:
    """Top CBSAs by composite attractiveness score."""
    sql = ("SELECT * FROM census_demographics "
           "WHERE attractiveness_score IS NOT NULL")
    params: List[Any] = []
    if state:
        sql += " AND state = ?"
        params.append(state.upper())
    sql += " ORDER BY attractiveness_score DESC LIMIT ?"
    params.append(int(limit))
    with store.connect() as con:
        _ensure_table(con)
        rows = con.execute(sql, params).fetchall()
    return [dict(r) for r in rows]
