"""CDC PLACES + NVSS county health statistics ingestion.

Two CDC sources cover what diligence needs at sub-state granularity:

  • **PLACES** (Local Data for Better Health) — model-based
    county/census-tract estimates of chronic disease prevalence
    (diabetes, COPD, CHD, stroke, obesity, depression) plus the
    behavioral risk factors that drive them (smoking, physical
    inactivity, binge drinking). Derived from BRFSS + ACS, published
    annually at chronicdata.cdc.gov/dataset/places.

  • **NVSS** (National Vital Statistics System) — county-level
    age-adjusted mortality rates by cause: all-cause, heart
    disease, cancer, accidents, drug overdose. Published via
    wonder.cdc.gov.

Why this matters for hospital diligence (separate from the existing
``disease_density.py`` which is *Medicare-beneficiary* prevalence):

  • PLACES covers the *full population* (not just Medicare) — the
    relevant denominator for an MSO/ASC's commercial-payer flow.
  • Risk-factor prevalence (smoking, obesity) leads disease
    prevalence by ~5-10 years — a forward indicator of demand mix.
  • Mortality rates flag underdiagnosed/undertreated populations
    (high CHD-mortality + low CHD-prevalence often = access gap).

Public API::

    from rcm_mc.data.cdc_places import (
        CountyHealthStatistics,
        load_cdc_places,
        get_health_stats_for_county,
        compute_health_burden_score,
        list_high_burden_counties,
    )
"""
from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional


# ── Schema ────────────────────────────────────────────────────

def _ensure_table(con: Any) -> None:
    con.execute(
        """
        CREATE TABLE IF NOT EXISTS cdc_county_health (
            county_fips TEXT NOT NULL,
            year INTEGER NOT NULL,
            county_name TEXT,
            state TEXT,
            population INTEGER,
            -- Chronic disease prevalence (% adult population)
            diabetes_pct REAL,
            copd_pct REAL,
            chd_pct REAL,
            stroke_pct REAL,
            obesity_pct REAL,
            depression_pct REAL,
            high_bp_pct REAL,
            -- Risk factors
            smoking_pct REAL,
            physical_inactivity_pct REAL,
            binge_drinking_pct REAL,
            no_health_insurance_pct REAL,
            -- Mortality (per 100K, age-adjusted)
            all_cause_mortality REAL,
            heart_disease_mortality REAL,
            cancer_mortality REAL,
            drug_overdose_mortality REAL,
            -- Composite
            health_burden_score REAL,
            loaded_at TEXT NOT NULL,
            PRIMARY KEY (county_fips, year)
        )
        """
    )
    con.execute(
        "CREATE INDEX IF NOT EXISTS "
        "idx_cdc_state ON cdc_county_health(state)"
    )
    con.execute(
        "CREATE INDEX IF NOT EXISTS "
        "idx_cdc_burden "
        "ON cdc_county_health(health_burden_score DESC)"
    )


@dataclass
class CountyHealthStatistics:
    """One county × year CDC health snapshot."""
    county_fips: str
    year: int
    county_name: str = ""
    state: str = ""
    population: Optional[int] = None
    # Chronic disease prevalence
    diabetes_pct: Optional[float] = None
    copd_pct: Optional[float] = None
    chd_pct: Optional[float] = None
    stroke_pct: Optional[float] = None
    obesity_pct: Optional[float] = None
    depression_pct: Optional[float] = None
    high_bp_pct: Optional[float] = None
    # Risk factors
    smoking_pct: Optional[float] = None
    physical_inactivity_pct: Optional[float] = None
    binge_drinking_pct: Optional[float] = None
    no_health_insurance_pct: Optional[float] = None
    # Mortality (per 100K, age-adjusted)
    all_cause_mortality: Optional[float] = None
    heart_disease_mortality: Optional[float] = None
    cancer_mortality: Optional[float] = None
    drug_overdose_mortality: Optional[float] = None
    # Composite
    health_burden_score: Optional[float] = None


def _safe_float(v: Any) -> Optional[float]:
    if v is None or v == "":
        return None
    s = str(v).strip().replace(",", "").replace("%", "")
    if s.lower() in ("not available", "n/a", "na",
                     "(x)", "suppressed", "*"):
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
    """County FIPS is 5 digits (state-2 + county-3); zero-pad."""
    s = str(s).strip()
    if not s:
        return s
    return s.zfill(5)


def parse_places_csv(
    path: Any, *, year: int = 0,
) -> Iterable[CountyHealthStatistics]:
    """Parse a CDC PLACES county CSV into CountyHealthStatistics.

    PLACES uses the long ``MeasureId`` shape (one row per county ×
    measure) in its raw API export but also publishes a wide
    county-level table where each measure is a separate column.
    We accept both — the wide form via column aliases, the long
    form by aggregating MeasureId values for the same FIPS.
    """
    p = Path(str(path))
    if not p.is_file():
        raise FileNotFoundError(
            f"CDC PLACES CSV not found at {p}")
    with p.open("r", encoding="utf-8", errors="replace",
                newline="") as fh:
        reader = csv.DictReader(fh)
        rows = list(reader)
    if not rows:
        return

    # Long form has MeasureId + Data_Value per row
    if any("MeasureId" in r or "measure_id" in r for r in rows):
        yield from _parse_places_long(rows, year)
    else:
        yield from _parse_places_wide(rows, year)


# Long-form MeasureId → CountyHealthStatistics field mapping.
# Source: CDC PLACES data dictionary (2024 release).
_PLACES_MEASURE_MAP: Dict[str, str] = {
    "DIABETES": "diabetes_pct",
    "COPD": "copd_pct",
    "CHD": "chd_pct",
    "STROKE": "stroke_pct",
    "OBESITY": "obesity_pct",
    "DEPRESSION": "depression_pct",
    "BPHIGH": "high_bp_pct",
    "CSMOKING": "smoking_pct",
    "LPA": "physical_inactivity_pct",
    "BINGE": "binge_drinking_pct",
    "ACCESS2": "no_health_insurance_pct",
}


def _parse_places_long(
    rows: List[Dict[str, Any]], year: int,
) -> Iterable[CountyHealthStatistics]:
    by_fips: Dict[str, CountyHealthStatistics] = {}
    for r in rows:
        fips = _pad_fips(str(_pick(
            r, "LocationID", "CountyFIPS",
            "county_fips", "FIPS") or ""))
        if not fips:
            continue
        rec = by_fips.get(fips)
        if rec is None:
            rec = CountyHealthStatistics(
                county_fips=fips,
                year=year or _safe_int(
                    _pick(r, "Year", "year")) or 0,
                county_name=str(_pick(
                    r, "LocationName", "CountyName",
                    "county_name") or "").strip(),
                state=str(_pick(
                    r, "StateAbbr", "state",
                    "State") or "").strip().upper(),
                population=_safe_int(_pick(
                    r, "TotalPopulation", "Population")),
            )
            by_fips[fips] = rec
        measure = str(_pick(
            r, "MeasureId", "measure_id") or "").strip().upper()
        field = _PLACES_MEASURE_MAP.get(measure)
        if not field:
            continue
        value = _safe_float(_pick(
            r, "Data_Value", "value", "Value"))
        if value is not None:
            setattr(rec, field, value)
    yield from by_fips.values()


def _parse_places_wide(
    rows: List[Dict[str, Any]], year: int,
) -> Iterable[CountyHealthStatistics]:
    for r in rows:
        fips = _pad_fips(str(_pick(
            r, "county_fips", "FIPS", "LocationID",
            "GEOID") or ""))
        if not fips:
            continue
        yield CountyHealthStatistics(
            county_fips=fips,
            year=year or _safe_int(
                _pick(r, "year", "Year")) or 0,
            county_name=str(_pick(
                r, "county_name", "CountyName",
                "LocationName") or "").strip(),
            state=str(_pick(
                r, "state", "State",
                "StateAbbr") or "").strip().upper(),
            population=_safe_int(_pick(
                r, "population", "Population")),
            diabetes_pct=_safe_float(_pick(
                r, "diabetes_pct", "DIABETES")),
            copd_pct=_safe_float(_pick(
                r, "copd_pct", "COPD")),
            chd_pct=_safe_float(_pick(
                r, "chd_pct", "CHD")),
            stroke_pct=_safe_float(_pick(
                r, "stroke_pct", "STROKE")),
            obesity_pct=_safe_float(_pick(
                r, "obesity_pct", "OBESITY")),
            depression_pct=_safe_float(_pick(
                r, "depression_pct", "DEPRESSION")),
            high_bp_pct=_safe_float(_pick(
                r, "high_bp_pct", "BPHIGH",
                "hypertension_pct")),
            smoking_pct=_safe_float(_pick(
                r, "smoking_pct", "CSMOKING")),
            physical_inactivity_pct=_safe_float(_pick(
                r, "physical_inactivity_pct", "LPA")),
            binge_drinking_pct=_safe_float(_pick(
                r, "binge_drinking_pct", "BINGE")),
            no_health_insurance_pct=_safe_float(_pick(
                r, "no_health_insurance_pct", "ACCESS2",
                "uninsured_pct")),
            all_cause_mortality=_safe_float(_pick(
                r, "all_cause_mortality", "AllCauseMort")),
            heart_disease_mortality=_safe_float(_pick(
                r, "heart_disease_mortality", "HDMort")),
            cancer_mortality=_safe_float(_pick(
                r, "cancer_mortality", "CancerMort")),
            drug_overdose_mortality=_safe_float(_pick(
                r, "drug_overdose_mortality",
                "OverdoseMort")),
        )


def parse_nvss_mortality_csv(
    path: Any, *, year: int = 0,
) -> Iterable[CountyHealthStatistics]:
    """Parse a CDC WONDER county-level mortality CSV.

    NVSS publishes one row per (county, cause) with age-adjusted
    rates per 100K. We aggregate the canonical causes a partner
    asks about (all-cause, heart, cancer, overdose) into one
    record per county.
    """
    p = Path(str(path))
    if not p.is_file():
        raise FileNotFoundError(
            f"NVSS mortality CSV not found at {p}")
    by_fips: Dict[str, CountyHealthStatistics] = {}
    with p.open("r", encoding="utf-8", errors="replace",
                newline="") as fh:
        reader = csv.DictReader(fh)
        for r in reader:
            fips = _pad_fips(str(_pick(
                r, "County Code", "county_fips",
                "FIPS") or ""))
            if not fips:
                continue
            rec = by_fips.get(fips)
            if rec is None:
                rec = CountyHealthStatistics(
                    county_fips=fips,
                    year=year or _safe_int(
                        _pick(r, "Year")) or 0,
                    county_name=str(_pick(
                        r, "County", "county_name") or "")
                    .strip(),
                    state=str(_pick(
                        r, "State", "state") or "")
                    .strip().upper(),
                )
                by_fips[fips] = rec
            cause = str(_pick(
                r, "Cause", "cause") or "").strip().lower()
            rate = _safe_float(_pick(
                r, "Age Adjusted Rate", "Rate",
                "rate_per_100k"))
            if rate is None:
                continue
            if "all" in cause:
                rec.all_cause_mortality = rate
            elif "heart" in cause:
                rec.heart_disease_mortality = rate
            elif "cancer" in cause or "neoplasm" in cause:
                rec.cancer_mortality = rate
            elif "overdose" in cause or "drug" in cause:
                rec.drug_overdose_mortality = rate
    yield from by_fips.values()


def compute_health_burden_score(
    s: CountyHealthStatistics,
) -> float:
    """Composite 0-1 score: how heavy is the chronic disease
    burden in this county?

    Higher = more burden = more demand for chronic-care services
    (great for an Oncology platform, mixed for an ASC).

    Weights:
      • Chronic disease prevalence (40%): diabetes + COPD + CHD
      • Risk factors (25%): smoking + inactivity + obesity
      • Mortality (25%): heart + cancer + overdose
      • Access gaps (10%): uninsured rate

    Returns 0-1; renormalized to weights actually used so partial
    data still produces a defensible score.
    """
    score = 0.0
    weights = 0.0

    # Chronic disease prevalence — national avg ~10-30% for these
    chronic_vals = [
        (s.diabetes_pct, 0.15),    # ~12% national
        (s.copd_pct, 0.10),        # ~6% national
        (s.chd_pct, 0.10),         # ~7% national
        (s.stroke_pct, 0.05),      # ~3% national
    ]
    chronic_score = 0.0
    chronic_w = 0.0
    for val, w in chronic_vals:
        if val is not None:
            # Cap at 30% — anything above is fully maxed
            chronic_score += w * min(1.0, val / 30.0)
            chronic_w += w
    if chronic_w > 0:
        score += chronic_score
        weights += chronic_w

    # Risk factors
    risk_vals = [
        (s.smoking_pct, 0.10),     # ~14% national
        (s.physical_inactivity_pct, 0.08),  # ~25% national
        (s.obesity_pct, 0.07),     # ~33% national
    ]
    risk_score = 0.0
    risk_w = 0.0
    for val, w in risk_vals:
        if val is not None:
            risk_score += w * min(1.0, val / 50.0)
            risk_w += w
    if risk_w > 0:
        score += risk_score
        weights += risk_w

    # Mortality — per 100K, age-adjusted
    if s.heart_disease_mortality is not None:
        # National ~165, range ~80-400
        score += 0.10 * min(1.0,
                            max(0.0,
                                (s.heart_disease_mortality - 80)
                                / 320.0))
        weights += 0.10
    if s.cancer_mortality is not None:
        # National ~145, range ~100-300
        score += 0.10 * min(1.0,
                            max(0.0,
                                (s.cancer_mortality - 100)
                                / 200.0))
        weights += 0.10
    if s.drug_overdose_mortality is not None:
        # National ~32, range ~5-100
        score += 0.05 * min(1.0,
                            max(0.0,
                                (s.drug_overdose_mortality - 5)
                                / 95.0))
        weights += 0.05

    # Access — uninsured
    if s.no_health_insurance_pct is not None:
        score += 0.10 * min(1.0,
                            s.no_health_insurance_pct / 25.0)
        weights += 0.10

    if weights <= 0:
        return 0.0
    return round(score / weights, 4)


# ── Loader ────────────────────────────────────────────────────

def load_cdc_places(
    store: Any,
    records: Iterable[CountyHealthStatistics],
) -> int:
    """Persist CDC county health records, computing the burden
    score on insert when not already supplied."""
    store.init_db()
    now = datetime.now(timezone.utc).isoformat()
    n = 0
    with store.connect() as con:
        _ensure_table(con)
        con.execute("BEGIN IMMEDIATE")
        try:
            for s in records:
                if s.health_burden_score is None:
                    s.health_burden_score = (
                        compute_health_burden_score(s))
                con.execute(
                    "INSERT OR REPLACE INTO cdc_county_health "
                    "(county_fips, year, county_name, state, "
                    " population, diabetes_pct, copd_pct, "
                    " chd_pct, stroke_pct, obesity_pct, "
                    " depression_pct, high_bp_pct, "
                    " smoking_pct, physical_inactivity_pct, "
                    " binge_drinking_pct, "
                    " no_health_insurance_pct, "
                    " all_cause_mortality, "
                    " heart_disease_mortality, "
                    " cancer_mortality, "
                    " drug_overdose_mortality, "
                    " health_burden_score, loaded_at) "
                    "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,"
                    "?,?,?,?,?,?)",
                    (s.county_fips, s.year, s.county_name,
                     s.state, s.population,
                     s.diabetes_pct, s.copd_pct, s.chd_pct,
                     s.stroke_pct, s.obesity_pct,
                     s.depression_pct, s.high_bp_pct,
                     s.smoking_pct,
                     s.physical_inactivity_pct,
                     s.binge_drinking_pct,
                     s.no_health_insurance_pct,
                     s.all_cause_mortality,
                     s.heart_disease_mortality,
                     s.cancer_mortality,
                     s.drug_overdose_mortality,
                     s.health_burden_score, now),
                )
                n += 1
            con.commit()
        except Exception:
            con.rollback()
            raise
    return n


# ── Read helpers ─────────────────────────────────────────────

def get_health_stats_for_county(
    store: Any,
    county_fips: str,
    *,
    year: Optional[int] = None,
) -> Optional[Dict[str, Any]]:
    """Lookup the most-recent (or specified-year) snapshot."""
    if not county_fips:
        return None
    sql = ("SELECT * FROM cdc_county_health "
           "WHERE county_fips = ?")
    params: List[Any] = [_pad_fips(county_fips)]
    if year:
        sql += " AND year = ?"
        params.append(int(year))
    sql += " ORDER BY year DESC LIMIT 1"
    with store.connect() as con:
        _ensure_table(con)
        row = con.execute(sql, params).fetchone()
    return dict(row) if row else None


def list_high_burden_counties(
    store: Any,
    *,
    state: Optional[str] = None,
    limit: int = 25,
) -> List[Dict[str, Any]]:
    """Top counties by composite health burden score — partner's
    first look at where chronic-care demand is heaviest."""
    sql = ("SELECT * FROM cdc_county_health "
           "WHERE health_burden_score IS NOT NULL")
    params: List[Any] = []
    if state:
        sql += " AND state = ?"
        params.append(state.upper())
    sql += " ORDER BY health_burden_score DESC LIMIT ?"
    params.append(int(limit))
    with store.connect() as con:
        _ensure_table(con)
        rows = con.execute(sql, params).fetchall()
    return [dict(r) for r in rows]


def list_counties_by_condition(
    store: Any,
    condition_field: str,
    *,
    state: Optional[str] = None,
    limit: int = 25,
    descending: bool = True,
) -> List[Dict[str, Any]]:
    """Rank counties by a single condition prevalence column —
    e.g. diabetes_pct, smoking_pct, drug_overdose_mortality.

    Used by the disease-density UI to drive condition-specific
    catchment rankings (an Oncology platform cares about
    cancer_mortality, an SUD platform cares about
    drug_overdose_mortality)."""
    allowed = {
        "diabetes_pct", "copd_pct", "chd_pct", "stroke_pct",
        "obesity_pct", "depression_pct", "high_bp_pct",
        "smoking_pct", "physical_inactivity_pct",
        "binge_drinking_pct", "no_health_insurance_pct",
        "all_cause_mortality", "heart_disease_mortality",
        "cancer_mortality", "drug_overdose_mortality",
    }
    if condition_field not in allowed:
        raise ValueError(
            f"Unknown condition field: {condition_field}")
    direction = "DESC" if descending else "ASC"
    sql = (f"SELECT * FROM cdc_county_health "
           f"WHERE {condition_field} IS NOT NULL")
    params: List[Any] = []
    if state:
        sql += " AND state = ?"
        params.append(state.upper())
    sql += f" ORDER BY {condition_field} {direction} LIMIT ?"
    params.append(int(limit))
    with store.connect() as con:
        _ensure_table(con)
        rows = con.execute(sql, params).fetchall()
    return [dict(r) for r in rows]
