"""Data catalog — what sources we have, how fresh, how complete.

Surfaces every public-data table the platform has ingested. The
purpose is twofold:

  • **Visibility for the partner** — *what edge does our data give
    us?* A catalog answers it directly. Each row shows record
    count, refresh date, geographic/temporal coverage, and a
    quality score derived from completeness + freshness +
    coverage breadth.

  • **Audit trail for diligence** — when LP asks *what's behind
    your screening universe?*, the catalog is the answer. Every
    source, every refresh date, every row count.

Each catalog entry is computed from a live SQLite query — no
hand-maintained registry to drift. Adding a new ingest module
means adding a row to ``_CATALOG_DEFINITIONS`` below and the
catalog picks it up.

Public API::

    from rcm_mc.data.catalog import (
        DataSourceEntry,
        inventory_data_sources,
        compute_data_estate_summary,
    )
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class DataSourceEntry:
    """One catalog row — derived from a live SQL scan."""
    source_id: str
    name: str
    category: str          # 'pricing'|'utilization'|'demographic'|...
    table: str
    description: str
    record_count: int = 0
    last_refreshed_at: Optional[str] = None
    coverage_summary: str = ""
    completeness_pct: Optional[float] = None
    quality_score: Optional[float] = None  # 0-1
    freshness_days: Optional[int] = None
    primary_grouper: str = ""              # e.g. 'CCN', 'CBSA'


# Catalog definitions. Each entry pairs a logical source with the
# SQL needed to compute its catalog metrics. The catalog renderer
# walks this list at request time and skips tables that don't
# exist (so it works against partial-load test DBs).
_CATALOG_DEFINITIONS: List[Dict[str, Any]] = [
    # ── Cost / financial ──
    {
        "source_id": "hcris",
        "name": "Medicare Hospital Cost Reports (HCRIS)",
        "category": "financial",
        "table": "cms_hcris" if False else "cms_hospital_general",
        "description":
            "Hospital-level financials: revenue, expenses, "
            "payer mix, beds, occupancy, case-mix index.",
        "primary_grouper": "CCN",
        "coverage_sql":
            "SELECT COUNT(DISTINCT ccn) AS unique_keys, "
            "       MIN(loaded_at) AS first_load, "
            "       MAX(loaded_at) AS last_load, "
            "       COUNT(*) AS n_rows "
            "FROM cms_hospital_general",
    },
    {
        "source_id": "hcris_load_log",
        "name": "HCRIS incremental load history",
        "category": "internal",
        "table": "hcris_load_log",
        "description":
            "Incremental ingestion log — submitted/settled/"
            "audited status progression.",
        "primary_grouper": "CCN",
        "coverage_sql":
            "SELECT COUNT(*) AS n_rows, "
            "       MAX(loaded_at) AS last_load, "
            "       COUNT(DISTINCT ccn) AS unique_keys "
            "FROM hcris_load_log",
    },
    {
        "source_id": "irs990",
        "name": "IRS 990 nonprofit hospital filings",
        "category": "financial",
        "table": "irs990_filings",
        "description":
            "Revenue, expenses, exec compensation, net assets "
            "for nonprofit hospitals — multi-year trends.",
        "primary_grouper": "EIN",
        "coverage_sql":
            "SELECT COUNT(DISTINCT ein) AS unique_keys, "
            "       COUNT(*) AS n_rows, "
            "       MAX(loaded_at) AS last_load, "
            "       MIN(tax_year) || '-' || "
            "         MAX(tax_year) AS year_range "
            "FROM irs990_filings",
    },
    # ── Provider / quality ──
    {
        "source_id": "nppes",
        "name": "NPPES provider registry",
        "category": "provider",
        "table": "pricing_nppes",
        "description":
            "National Provider Identifier registry — Type-1 "
            "individuals + Type-2 organizations, with "
            "deactivation tracking.",
        "primary_grouper": "NPI",
        "coverage_sql":
            "SELECT COUNT(*) AS n_rows, "
            "       COUNT(DISTINCT npi) AS unique_keys, "
            "       MAX(updated_at) AS last_load "
            "FROM pricing_nppes",
    },
    {
        "source_id": "cms_quality_metrics",
        "name": "Hospital Compare quality metrics",
        "category": "quality",
        "table": "cms_quality_metrics",
        "description":
            "Star ratings, readmission, mortality, HCAHPS, "
            "HAI rates per CCN — partner-relevant predictors.",
        "primary_grouper": "CCN",
        "coverage_sql":
            "SELECT COUNT(*) AS n_rows, "
            "       COUNT(DISTINCT ccn) AS unique_keys, "
            "       MAX(loaded_at) AS last_load "
            "FROM cms_quality_metrics",
    },
    # ── Pricing ──
    {
        "source_id": "hospital_mrf",
        "name": "Hospital Machine-Readable Files",
        "category": "pricing",
        "table": "pricing_hospital_charges",
        "description":
            "5 charge types per CPT — gross, discounted-cash, "
            "min/max negotiated, allowed amount percentiles "
            "(CY2026), Type-2 billing NPI.",
        "primary_grouper": "ccn × cpt",
        "coverage_sql":
            "SELECT COUNT(*) AS n_rows, "
            "       COUNT(DISTINCT ccn) AS unique_keys, "
            "       MAX(loaded_at) AS last_load "
            "FROM pricing_hospital_charges",
    },
    {
        "source_id": "payer_mrf",
        "name": "Transparency-in-Coverage payer MRFs",
        "category": "pricing",
        "table": "pricing_payer_rates",
        "description":
            "In-network negotiated rates by CPT × payer × "
            "provider group.",
        "primary_grouper": "payer × cpt × tin",
        "coverage_sql":
            "SELECT COUNT(*) AS n_rows, "
            "       COUNT(DISTINCT payer_id) AS unique_keys, "
            "       MAX(loaded_at) AS last_load "
            "FROM pricing_payer_rates",
    },
    {
        "source_id": "state_apcd",
        "name": "State All-Payer Claims Databases",
        "category": "pricing",
        "table": "state_apcd_prices",
        "description":
            "Commercial-payer paid allowed amounts by region × "
            "CPT × payer-type. Public-use aggregated files.",
        "primary_grouper": "state × region × cpt",
        "coverage_sql":
            "SELECT COUNT(*) AS n_rows, "
            "       COUNT(DISTINCT state) AS unique_keys, "
            "       MAX(loaded_at) AS last_load "
            "FROM state_apcd_prices",
    },
    # ── Utilization ──
    {
        "source_id": "cms_part_b",
        "name": "Medicare Part B procedure mix",
        "category": "utilization",
        "table": "cms_part_b_metrics",
        "description":
            "Per-NPI procedure mix + Herfindahl concentration "
            "from CMS Provider Utilization data.",
        "primary_grouper": "NPI",
        "coverage_sql":
            "SELECT COUNT(*) AS n_rows, "
            "       COUNT(DISTINCT npi) AS unique_keys, "
            "       MAX(loaded_at) AS last_load "
            "FROM cms_part_b_metrics",
    },
    {
        "source_id": "cms_part_d",
        "name": "Medicare Part D prescriber metrics",
        "category": "utilization",
        "table": "cms_part_d_metrics",
        "description":
            "Per-NPI prescriber mix, brand share, opioid flag "
            "(>=10% claim share).",
        "primary_grouper": "NPI",
        "coverage_sql":
            "SELECT COUNT(*) AS n_rows, "
            "       COUNT(DISTINCT npi) AS unique_keys, "
            "       MAX(loaded_at) AS last_load "
            "FROM cms_part_d_metrics",
    },
    {
        "source_id": "cms_opps",
        "name": "Medicare OPPS outpatient",
        "category": "utilization",
        "table": "cms_opps_outpatient",
        "description":
            "DRG-level outpatient HCPCS volumes + payments + "
            "off-campus share.",
        "primary_grouper": "CCN × HCPCS",
        "coverage_sql":
            "SELECT COUNT(*) AS n_rows, "
            "       COUNT(DISTINCT ccn) AS unique_keys, "
            "       MAX(loaded_at) AS last_load "
            "FROM cms_opps_outpatient",
    },
    {
        "source_id": "ahrq_hcup",
        "name": "AHRQ HCUP NIS/NEDS discharges",
        "category": "utilization",
        "table": "ahrq_hcup_discharges",
        "description":
            "All-payer discharge volume + LOS + charges + "
            "mortality by clinical-grouper × region × age × "
            "payer. Site-of-service-shift signal.",
        "primary_grouper": "clinical × region",
        "coverage_sql":
            "SELECT COUNT(*) AS n_rows, "
            "       COUNT(DISTINCT clinical_code) "
            "         AS unique_keys, "
            "       MAX(loaded_at) AS last_load "
            "FROM ahrq_hcup_discharges",
    },
    # ── Conflict / payments ──
    {
        "source_id": "cms_open_payments",
        "name": "CMS Open Payments (Sunshine Act)",
        "category": "compliance",
        "table": "cms_open_payments_npi",
        "description":
            "Industry payments to physicians — conflict + "
            "concentration flags ($50K consulting/speaker, "
            "$250K total, $100K ownership thresholds).",
        "primary_grouper": "NPI",
        "coverage_sql":
            "SELECT COUNT(*) AS n_rows, "
            "       COUNT(DISTINCT npi) AS unique_keys, "
            "       MAX(loaded_at) AS last_load "
            "FROM cms_open_payments_npi",
    },
    # ── Market / demographic ──
    {
        "source_id": "census_demographics",
        "name": "US Census ACS demographics",
        "category": "market",
        "table": "census_demographics",
        "description":
            "CBSA-level population, age, income, insurance "
            "coverage, growth — composite attractiveness "
            "score per market.",
        "primary_grouper": "CBSA",
        "coverage_sql":
            "SELECT COUNT(*) AS n_rows, "
            "       COUNT(DISTINCT cbsa) AS unique_keys, "
            "       MAX(loaded_at) AS last_load "
            "FROM census_demographics",
    },
    {
        "source_id": "cdc_places",
        "name": "CDC PLACES + NVSS county health",
        "category": "market",
        "table": "cdc_county_health",
        "description":
            "County-level chronic disease prevalence + risk "
            "factors + age-adjusted mortality. Composite "
            "burden score.",
        "primary_grouper": "county FIPS",
        "coverage_sql":
            "SELECT COUNT(*) AS n_rows, "
            "       COUNT(DISTINCT county_fips) "
            "         AS unique_keys, "
            "       MAX(loaded_at) AS last_load "
            "FROM cdc_county_health",
    },
    # ── Medicare Advantage ──
    {
        "source_id": "cms_ma_enrollment",
        "name": "CMS MA monthly enrollment",
        "category": "ma",
        "table": "cms_ma_enrollment",
        "description":
            "Monthly contract × plan × county enrollment. "
            "Aggregated for county MA penetration.",
        "primary_grouper": "contract × county × month",
        "coverage_sql":
            "SELECT COUNT(*) AS n_rows, "
            "       COUNT(DISTINCT county_fips) "
            "         AS unique_keys, "
            "       MAX(loaded_at) AS last_load "
            "FROM cms_ma_enrollment",
    },
    {
        "source_id": "cms_ma_star_ratings",
        "name": "CMS MA Star Ratings",
        "category": "ma",
        "table": "cms_ma_star_ratings",
        "description":
            "Annual contract Star scores. 4.0+ unlocks the "
            "Quality Bonus Payment.",
        "primary_grouper": "contract × year",
        "coverage_sql":
            "SELECT COUNT(*) AS n_rows, "
            "       COUNT(DISTINCT contract_id) "
            "         AS unique_keys, "
            "       MAX(loaded_at) AS last_load "
            "FROM cms_ma_star_ratings",
    },
    {
        "source_id": "cms_ma_benchmarks",
        "name": "CMS MA county benchmarks",
        "category": "ma",
        "table": "cms_ma_benchmarks",
        "description":
            "Annual county-level MA benchmark + FFS baseline "
            "+ quartile + YoY change.",
        "primary_grouper": "county × year",
        "coverage_sql":
            "SELECT COUNT(*) AS n_rows, "
            "       COUNT(DISTINCT county_fips) "
            "         AS unique_keys, "
            "       MAX(loaded_at) AS last_load "
            "FROM cms_ma_benchmarks",
    },
]


def _table_exists(con: Any, table: str) -> bool:
    row = con.execute(
        "SELECT 1 FROM sqlite_master "
        "WHERE type='table' AND name=?",
        (table,),
    ).fetchone()
    return row is not None


def _days_since(iso_str: Optional[str]) -> Optional[int]:
    if not iso_str:
        return None
    try:
        ts = datetime.fromisoformat(
            iso_str.replace("Z", "+00:00"))
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
    except ValueError:
        return None
    return (datetime.now(timezone.utc) - ts).days


def _compute_quality_score(
    record_count: int,
    unique_keys: int,
    freshness_days: Optional[int],
) -> Optional[float]:
    """0-1 composite. Three terms:
      - volume (0-0.4): log10-scaled record count (10K → 0.4)
      - coverage (0-0.3): >1000 unique keys → 0.3
      - freshness (0-0.3): <30 days → 0.3, decays linearly to 0
        at 365 days
    """
    if record_count <= 0:
        return None
    import math
    volume = min(0.4, math.log10(max(record_count, 1)) / 10)
    coverage = min(0.3, unique_keys / 1000 * 0.3)
    if freshness_days is None:
        freshness = 0.0
    elif freshness_days <= 30:
        freshness = 0.3
    elif freshness_days >= 365:
        freshness = 0.0
    else:
        freshness = 0.3 * (1.0 - (freshness_days - 30) / 335)
    return round(volume + coverage + freshness, 3)


def inventory_data_sources(
    store: Any,
) -> List[DataSourceEntry]:
    """Walk the catalog definitions, query each table that exists,
    return the populated entries. Tables that don't exist are
    skipped silently (catalog adapts to whatever has been loaded).
    """
    out: List[DataSourceEntry] = []
    with store.connect() as con:
        for d in _CATALOG_DEFINITIONS:
            if not _table_exists(con, d["table"]):
                continue
            try:
                row = con.execute(d["coverage_sql"]).fetchone()
            except Exception:
                continue
            if not row:
                continue
            r = dict(row)
            n_rows = int(r.get("n_rows") or 0)
            unique = int(r.get("unique_keys") or 0)
            last = r.get("last_load")
            freshness = _days_since(last)
            quality = _compute_quality_score(
                n_rows, unique, freshness)
            coverage_bits: List[str] = []
            if unique:
                coverage_bits.append(
                    f"{unique:,} unique {d['primary_grouper']}")
            if r.get("year_range"):
                coverage_bits.append(
                    f"years {r['year_range']}")
            out.append(DataSourceEntry(
                source_id=d["source_id"],
                name=d["name"],
                category=d["category"],
                table=d["table"],
                description=d["description"],
                record_count=n_rows,
                last_refreshed_at=last,
                coverage_summary=" · ".join(coverage_bits),
                quality_score=quality,
                freshness_days=freshness,
                primary_grouper=d["primary_grouper"],
            ))
    return out


def compute_data_estate_summary(
    entries: List[DataSourceEntry],
) -> Dict[str, Any]:
    """Top-of-page numbers a partner glances at first."""
    if not entries:
        return {
            "n_sources": 0, "total_records": 0,
            "avg_quality": None, "fresh_sources": 0,
            "stale_sources": 0,
        }
    total = sum(e.record_count for e in entries)
    qualities = [e.quality_score for e in entries
                 if e.quality_score is not None]
    avg_q = (round(sum(qualities) / len(qualities), 3)
             if qualities else None)
    fresh = sum(1 for e in entries
                if e.freshness_days is not None
                and e.freshness_days <= 30)
    stale = sum(1 for e in entries
                if e.freshness_days is not None
                and e.freshness_days > 90)
    by_category: Dict[str, int] = {}
    for e in entries:
        by_category[e.category] = (
            by_category.get(e.category, 0) + 1)
    return {
        "n_sources": len(entries),
        "total_records": total,
        "avg_quality": avg_q,
        "fresh_sources": fresh,
        "stale_sources": stale,
        "by_category": by_category,
    }
