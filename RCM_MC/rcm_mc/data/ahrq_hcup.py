"""AHRQ HCUP (Healthcare Cost and Utilization Project) ingestion.

HCUP is AHRQ's family of all-payer hospital databases. The two
public-use sources we ingest:

  • **NIS** (Nationwide Inpatient Sample) — 20% stratified sample
    of US community hospital discharges; ~7M discharges/year.
    All-payer (Medicare + Medicaid + Private + Self-pay + Other).
  • **NEDS** (Nationwide Emergency Department Sample) — ~30M ED
    visits/year, all-payer.

Public-use deliverables come pre-aggregated as one row per
(year × clinical-grouper × region × age-group × payer) with
discharges, mean LOS, mean charges, in-hospital mortality.

Why this matters separately from existing CMS ingest:

  • HCRIS = hospital-level financials. Doesn't tell you that
    knee replacement volume in the South grew 8%/yr while
    Northeast shrank.
  • CMS OPPS = outpatient HCPCS at facility level. HCUP is
    inpatient and ED, with full clinical groupers (CCS, DRG).
  • HCUP is *all-payer* — the only public source that lets you
    benchmark commercial-payer volume of a given procedure.
  • Regional variation index (West/South/Midwest/Northeast)
    is the canonical site-of-service-shift signal — a procedure
    with high regional CoV is one where the market hasn't
    settled on the optimal care setting.

Schema is one row per (clinical_code × clinical_system × region ×
age_group × payer × year). The clinical_system field disambiguates
DRG / CCS-DX / CCS-PR / ICD10 coding so a single table can hold
inpatient discharge groupers and procedure groupers.

Public API::

    from rcm_mc.data.ahrq_hcup import (
        HCUPDischargeRecord,
        load_hcup_discharges,
        get_hcup_metrics,
        compute_regional_variation_index,
        list_top_volume_procedures,
    )
"""
from __future__ import annotations

import csv
import math
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional


# Canonical clinical-system identifiers for the
# clinical_system column. Order: most-specific to least.
CLINICAL_SYSTEMS = {
    "drg",          # MS-DRG codes
    "ccs_dx",       # CCS for ICD diagnoses
    "ccs_pr",       # CCS for ICD procedures
    "icd10cm",      # raw ICD-10-CM diagnosis
    "icd10pcs",     # raw ICD-10-PCS procedure
}

# Census regions HCUP uses
HCUP_REGIONS = {
    "northeast", "midwest", "south", "west", "national",
}

# Payer buckets HCUP publishes
HCUP_PAYERS = {
    "medicare", "medicaid", "private",
    "self_pay", "other", "all",
}

# Age-group buckets HCUP publishes
HCUP_AGE_GROUPS = {
    "0-17", "18-44", "45-64", "65-84", "85+", "all",
}


def _ensure_table(con: Any) -> None:
    con.execute(
        """
        CREATE TABLE IF NOT EXISTS ahrq_hcup_discharges (
            clinical_code TEXT NOT NULL,
            clinical_system TEXT NOT NULL,
            region TEXT NOT NULL,
            age_group TEXT NOT NULL,
            payer TEXT NOT NULL,
            year INTEGER NOT NULL,
            clinical_description TEXT,
            source_db TEXT,
            n_discharges INTEGER,
            mean_los REAL,
            mean_charges REAL,
            mean_costs REAL,
            mortality_pct REAL,
            readmission_30d_pct REAL,
            loaded_at TEXT NOT NULL,
            PRIMARY KEY (clinical_code, clinical_system,
                         region, age_group, payer, year)
        )
        """
    )
    con.execute(
        "CREATE INDEX IF NOT EXISTS "
        "idx_hcup_clinical "
        "ON ahrq_hcup_discharges(clinical_system, "
        "                        clinical_code, year)"
    )
    con.execute(
        "CREATE INDEX IF NOT EXISTS "
        "idx_hcup_volume "
        "ON ahrq_hcup_discharges(n_discharges DESC)"
    )


@dataclass
class HCUPDischargeRecord:
    """One HCUP aggregated discharge cell."""
    clinical_code: str
    clinical_system: str   # 'drg' | 'ccs_dx' | 'ccs_pr' | 'icd10*'
    region: str            # 'northeast'|'midwest'|'south'|'west'|'national'
    age_group: str         # '0-17'|'18-44'|'45-64'|'65-84'|'85+'|'all'
    payer: str             # 'medicare'|'medicaid'|'private'|'self_pay'|'other'|'all'
    year: int
    clinical_description: str = ""
    source_db: str = ""    # 'NIS' | 'NEDS' | 'KID' | 'SID'
    n_discharges: Optional[int] = None
    mean_los: Optional[float] = None      # days
    mean_charges: Optional[float] = None  # dollars (charges, not paid)
    mean_costs: Optional[float] = None    # cost-to-charge-ratio adjusted
    mortality_pct: Optional[float] = None
    readmission_30d_pct: Optional[float] = None


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


def _normalize_region(raw: str) -> str:
    s = (raw or "").strip().lower()
    if not s or s == "us" or "national" in s or "all" in s:
        return "national"
    if "north" in s and "east" in s:
        return "northeast"
    if "midwest" in s or "north central" in s:
        return "midwest"
    if "south" in s:
        return "south"
    if "west" in s:
        return "west"
    return s


def _normalize_payer(raw: str) -> str:
    s = (raw or "").strip().lower()
    if not s or "all" in s:
        return "all"
    if "medicare" in s:
        return "medicare"
    if "medicaid" in s:
        return "medicaid"
    if "private" in s or "commercial" in s:
        return "private"
    if "self" in s or "uninsured" in s or "no charge" in s:
        return "self_pay"
    return "other"


def _normalize_age_group(raw: str) -> str:
    s = (raw or "").strip().lower()
    if not s or "all" in s:
        return "all"
    if "0" in s and ("17" in s or "18" in s):
        return "0-17"
    if "18" in s and "44" in s:
        return "18-44"
    if "45" in s and ("64" in s or "65" in s):
        return "45-64"
    if "65" in s and ("84" in s or "85" in s):
        return "65-84"
    if "85" in s or "+" in s:
        return "85+"
    return s


def _normalize_clinical_system(raw: str) -> str:
    s = (raw or "").strip().lower()
    if not s:
        return "drg"
    if "drg" in s:
        return "drg"
    if "ccs" in s and ("dx" in s or "diag" in s):
        return "ccs_dx"
    if "ccs" in s and ("pr" in s or "proc" in s):
        return "ccs_pr"
    if "icd" in s and ("pcs" in s or "proc" in s):
        return "icd10pcs"
    if "icd" in s:
        return "icd10cm"
    return s


def parse_hcup_csv(
    path: Any,
    *,
    year: int = 0,
    source_db: str = "",
) -> Iterable[HCUPDischargeRecord]:
    """Parse an HCUP NIS/NEDS public-use aggregated CSV.

    HCUPnet exports use friendly column names; the underlying NIS
    public-use files use ``DRG`` / ``CCSDX`` / ``HOSPREGION`` /
    ``ZIPINC`` / ``PAY1`` / ``AGE_GROUP``. We accept both.
    """
    p = Path(str(path))
    if not p.is_file():
        raise FileNotFoundError(
            f"HCUP CSV not found at {p}")
    with p.open("r", encoding="utf-8", errors="replace",
                newline="") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            code = str(_pick(
                row, "clinical_code", "drg_code", "DRG",
                "ccs_code", "CCSDX", "CCSPR",
                "icd_code", "code") or "").strip()
            if not code:
                continue
            yield HCUPDischargeRecord(
                clinical_code=code,
                clinical_system=_normalize_clinical_system(
                    str(_pick(
                        row, "clinical_system",
                        "code_system", "Code Type",
                        "grouper") or "drg")),
                region=_normalize_region(str(_pick(
                    row, "region", "Region",
                    "HOSPREGION", "Census Region") or "")),
                age_group=_normalize_age_group(str(_pick(
                    row, "age_group", "Age Group",
                    "AGE_GROUP", "AgeGroup") or "all")),
                payer=_normalize_payer(str(_pick(
                    row, "payer", "Payer", "PAY1",
                    "Primary Payer",
                    "Expected Payer") or "all")),
                year=year or _safe_int(
                    _pick(row, "year", "Year")) or 0,
                clinical_description=str(_pick(
                    row, "clinical_description",
                    "Description", "DRG Description",
                    "Procedure", "Diagnosis") or "").strip(),
                source_db=source_db or str(_pick(
                    row, "source_db", "Source",
                    "Database") or ""),
                n_discharges=_safe_int(_pick(
                    row, "n_discharges", "Discharges",
                    "DISCWT", "Total Discharges",
                    "Number of Discharges")),
                mean_los=_safe_float(_pick(
                    row, "mean_los", "Mean LOS",
                    "LOS", "Average LOS",
                    "AvgLOS")),
                mean_charges=_safe_float(_pick(
                    row, "mean_charges", "Mean Charges",
                    "TOTCHG", "Average Charges",
                    "Total Charges")),
                mean_costs=_safe_float(_pick(
                    row, "mean_costs", "Mean Costs",
                    "Average Costs")),
                mortality_pct=_safe_float(_pick(
                    row, "mortality_pct",
                    "In-Hospital Mortality",
                    "Mortality Rate", "Died")),
                readmission_30d_pct=_safe_float(_pick(
                    row, "readmission_30d_pct",
                    "30-Day Readmission",
                    "Readmission Rate")),
            )


# ── Loader ────────────────────────────────────────────────────

def load_hcup_discharges(
    store: Any,
    records: Iterable[HCUPDischargeRecord],
) -> int:
    """Persist HCUP discharge records (idempotent upsert)."""
    store.init_db()
    now = datetime.now(timezone.utc).isoformat()
    n = 0
    with store.connect() as con:
        _ensure_table(con)
        con.execute("BEGIN IMMEDIATE")
        try:
            for r in records:
                con.execute(
                    "INSERT OR REPLACE INTO "
                    "ahrq_hcup_discharges "
                    "(clinical_code, clinical_system, region, "
                    " age_group, payer, year, "
                    " clinical_description, source_db, "
                    " n_discharges, mean_los, mean_charges, "
                    " mean_costs, mortality_pct, "
                    " readmission_30d_pct, loaded_at) "
                    "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (r.clinical_code, r.clinical_system,
                     r.region, r.age_group, r.payer, r.year,
                     r.clinical_description, r.source_db,
                     r.n_discharges, r.mean_los,
                     r.mean_charges, r.mean_costs,
                     r.mortality_pct,
                     r.readmission_30d_pct, now),
                )
                n += 1
            con.commit()
        except Exception:
            con.rollback()
            raise
    return n


# ── Read helpers ─────────────────────────────────────────────

def get_hcup_metrics(
    store: Any,
    clinical_code: str,
    *,
    clinical_system: str = "drg",
    region: Optional[str] = None,
    payer: Optional[str] = None,
    age_group: Optional[str] = None,
    year: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """Lookup HCUP metrics for a clinical code."""
    if not clinical_code:
        return []
    sql = ("SELECT * FROM ahrq_hcup_discharges "
           "WHERE clinical_code = ? AND clinical_system = ?")
    params: List[Any] = [
        str(clinical_code).strip(), clinical_system.lower()]
    if region:
        sql += " AND region = ?"
        params.append(region.lower())
    if payer:
        sql += " AND payer = ?"
        params.append(payer.lower())
    if age_group:
        sql += " AND age_group = ?"
        params.append(age_group)
    if year:
        sql += " AND year = ?"
        params.append(int(year))
    sql += " ORDER BY year DESC, region"
    with store.connect() as con:
        _ensure_table(con)
        rows = con.execute(sql, params).fetchall()
    return [dict(r) for r in rows]


def compute_regional_variation_index(
    store: Any,
    clinical_code: str,
    *,
    clinical_system: str = "drg",
    year: Optional[int] = None,
    metric: str = "n_discharges",
) -> Optional[float]:
    """Coefficient of variation across the four census regions.

    A high CoV (>0.4) on a procedure means the market hasn't
    settled on the optimal care setting — the canonical
    site-of-service-shift signal. Returns None when fewer than
    two regions have data.

    metric: 'n_discharges' | 'mean_los' | 'mean_charges' |
            'mortality_pct'
    """
    allowed = {"n_discharges", "mean_los", "mean_charges",
               "mortality_pct", "readmission_30d_pct"}
    if metric not in allowed:
        raise ValueError(f"Unknown metric: {metric}")
    sql = (f"SELECT region, AVG({metric}) as v "
           f"FROM ahrq_hcup_discharges "
           f"WHERE clinical_code = ? AND clinical_system = ? "
           f"  AND region != 'national' "
           f"  AND payer = 'all' AND age_group = 'all' "
           f"  AND {metric} IS NOT NULL")
    params: List[Any] = [
        str(clinical_code).strip(), clinical_system.lower()]
    if year:
        sql += " AND year = ?"
        params.append(int(year))
    sql += " GROUP BY region"
    with store.connect() as con:
        _ensure_table(con)
        rows = con.execute(sql, params).fetchall()
    values = [r["v"] for r in rows
              if r["v"] is not None]
    if len(values) < 2:
        return None
    mean = sum(values) / len(values)
    if mean <= 0:
        return None
    var = sum((v - mean) ** 2 for v in values) / len(values)
    return round(math.sqrt(var) / mean, 4)


def list_top_volume_procedures(
    store: Any,
    *,
    clinical_system: str = "drg",
    region: str = "national",
    year: Optional[int] = None,
    limit: int = 25,
) -> List[Dict[str, Any]]:
    """Top clinical groupers by discharge volume in a region —
    the universe a partner is screening for roll-up plays."""
    sql = (
        "SELECT clinical_code, clinical_description, "
        "       region, year, n_discharges, mean_los, "
        "       mean_charges, mortality_pct "
        "FROM ahrq_hcup_discharges "
        "WHERE clinical_system = ? AND region = ? "
        "  AND payer = 'all' AND age_group = 'all' "
        "  AND n_discharges IS NOT NULL"
    )
    params: List[Any] = [
        clinical_system.lower(), region.lower()]
    if year:
        sql += " AND year = ?"
        params.append(int(year))
    sql += " ORDER BY n_discharges DESC LIMIT ?"
    params.append(int(limit))
    with store.connect() as con:
        _ensure_table(con)
        rows = con.execute(sql, params).fetchall()
    return [dict(r) for r in rows]


def compute_volume_trend(
    store: Any,
    clinical_code: str,
    *,
    clinical_system: str = "drg",
    region: str = "national",
    year_from: Optional[int] = None,
    year_to: Optional[int] = None,
) -> Optional[float]:
    """Compound annual growth rate of discharge volume between
    year_from and year_to. Without args, uses the earliest and
    latest years on file.

    A procedure with -3% CAGR over 5 years is in decline (likely
    moving to outpatient or being substituted). +5% is genuine
    demand growth. The combination of national-flat + regional
    variation tells you where the shift is happening."""
    sql = (
        "SELECT year, n_discharges "
        "FROM ahrq_hcup_discharges "
        "WHERE clinical_code = ? AND clinical_system = ? "
        "  AND region = ? AND payer = 'all' "
        "  AND age_group = 'all' "
        "  AND n_discharges IS NOT NULL "
        "ORDER BY year"
    )
    params = [str(clinical_code).strip(),
              clinical_system.lower(), region.lower()]
    with store.connect() as con:
        _ensure_table(con)
        rows = con.execute(sql, params).fetchall()
    pts = [(r["year"], r["n_discharges"]) for r in rows]
    if year_from:
        pts = [p for p in pts if p[0] >= year_from]
    if year_to:
        pts = [p for p in pts if p[0] <= year_to]
    if len(pts) < 2:
        return None
    y0, v0 = pts[0]
    y1, v1 = pts[-1]
    if v0 <= 0 or y1 == y0:
        return None
    years = y1 - y0
    return round((v1 / v0) ** (1.0 / years) - 1.0, 4)
