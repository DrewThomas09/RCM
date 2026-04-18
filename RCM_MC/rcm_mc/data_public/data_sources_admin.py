"""Data Sources Admin — inventory of corpus data sources, scraper status, and coverage.

Shows: scraper last-run timestamps, record counts by source, data freshness,
CMS dataset inventory, corpus coverage by sector/year/source.
"""
from __future__ import annotations

import importlib
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional


@dataclass
class DataSource:
    name: str
    source_type: str        # "corpus_seed", "cms_public", "scraper", "manual"
    description: str
    record_count: int
    last_updated: str       # ISO date or "static"
    status: str             # "active", "stale", "error", "disabled"
    coverage_notes: str
    url: str


@dataclass
class ScraperStatus:
    name: str
    module: str
    record_count: int
    status: str
    last_run: str
    error_msg: str


@dataclass
class CorpusCoverage:
    total_deals: int
    by_sector: Dict[str, int]
    by_year: Dict[int, int]
    by_source: Dict[str, int]
    year_range: tuple
    sector_count: int
    avg_ev_mm: float
    median_moic: float


@dataclass
class DataSourcesResult:
    corpus_coverage: CorpusCoverage
    data_sources: List[DataSource]
    scraper_statuses: List[ScraperStatus]
    seed_file_count: int
    total_seed_deals: int


def _load_corpus() -> List[dict]:
    deals: List[dict] = []
    for i in range(2, 60):
        try:
            mod = importlib.import_module(f"rcm_mc.data_public.extended_seed_{i}")
            deals.extend(getattr(mod, f"EXTENDED_SEED_DEALS_{i}", []))
        except ImportError:
            pass
    try:
        from rcm_mc.data_public.deals_corpus import _SEED_DEALS, EXTENDED_SEED_DEALS
        deals = _SEED_DEALS + EXTENDED_SEED_DEALS + deals
    except Exception:
        pass
    return deals


def _count_seed_files() -> int:
    count = 0
    for i in range(2, 100):
        try:
            importlib.import_module(f"rcm_mc.data_public.extended_seed_{i}")
            count += 1
        except ImportError:
            if i > 10:
                break
    return count


def _scraper_status() -> List[ScraperStatus]:
    scrapers = [
        ("CMS Public Deals", "rcm_mc.data_public.scrapers.cms_data", "CMS public deal data"),
        ("News/Deals Scraper", "rcm_mc.data_public.scrapers.news_deals", "Healthcare PE news deals"),
        ("PE Portfolios", "rcm_mc.data_public.scrapers.pe_portfolios", "PE firm portfolio data"),
        ("SEC Filings", "rcm_mc.data_public.scrapers.sec_filings", "SEC EDGAR healthcare M&A"),
    ]
    results = []
    for name, module_path, _ in scrapers:
        try:
            mod = importlib.import_module(module_path)
            results.append(ScraperStatus(
                name=name,
                module=module_path,
                record_count=0,
                status="available",
                last_run="n/a",
                error_msg="",
            ))
        except ImportError as e:
            results.append(ScraperStatus(
                name=name,
                module=module_path,
                record_count=0,
                status="import_error",
                last_run="n/a",
                error_msg=str(e)[:80],
            ))
    return results


def _build_coverage(deals: List[dict]) -> CorpusCoverage:
    by_sector: Dict[str, int] = {}
    by_year: Dict[int, int] = {}
    by_source: Dict[str, int] = {"corpus_seed": len(deals)}

    evs, moics = [], []
    for d in deals:
        s = d.get("sector") or "Unknown"
        by_sector[s] = by_sector.get(s, 0) + 1
        y = d.get("year") or 2020
        by_year[y] = by_year.get(y, 0) + 1
        if d.get("ev_mm"):
            evs.append(d["ev_mm"])
        if d.get("moic"):
            moics.append(d["moic"])

    years = sorted(by_year.keys())
    year_range = (years[0], years[-1]) if years else (2015, 2024)
    avg_ev = sum(evs) / len(evs) if evs else 0.0
    moics_s = sorted(moics)
    mid = len(moics_s) // 2
    median_moic = moics_s[mid] if moics_s else 0.0

    return CorpusCoverage(
        total_deals=len(deals),
        by_sector=dict(sorted(by_sector.items(), key=lambda x: -x[1])[:20]),
        by_year=dict(sorted(by_year.items())),
        by_source=by_source,
        year_range=year_range,
        sector_count=len(by_sector),
        avg_ev_mm=round(avg_ev, 1),
        median_moic=round(median_moic, 2),
    )


def _data_sources() -> List[DataSource]:
    return [
        DataSource(
            name="Corpus Seed Files",
            source_type="corpus_seed",
            description="Synthetic healthcare PE deals, 57 seed batches. "
                        "Covers physician groups, hospitals, behavioral health, "
                        "HCIT, revenue cycle, home health, diagnostics.",
            record_count=0,
            last_updated="static",
            status="active",
            coverage_notes="1,050+ deals, 2012–2024, 40+ sectors",
            url="",
        ),
        DataSource(
            name="CMS Hospital Compare",
            source_type="cms_public",
            description="CMS Hospital Compare quality metrics: HCAHPS, VBP, "
                        "readmission rates, safety scores.",
            record_count=5_000,
            last_updated="2024-Q4",
            status="active",
            coverage_notes="All Medicare-certified hospitals (~5,000 facilities)",
            url="https://data.cms.gov/provider-data",
        ),
        DataSource(
            name="CMS HCRIS Cost Reports",
            source_type="cms_public",
            description="Healthcare Cost Report Information System. "
                        "Annual hospital financial statements.",
            record_count=7_000,
            last_updated="2024-Q3",
            status="active",
            coverage_notes="Hospitals, SNFs, HHAs. 40+ financial fields.",
            url="https://www.cms.gov/Research-Statistics-Data-and-Systems/Downloadable-Public-Use-Files/Cost-Reports",
        ),
        DataSource(
            name="CMS Physician Fee Schedule",
            source_type="cms_public",
            description="Medicare physician fee schedule with RVU weights. "
                        "Used for reimbursement rate benchmarking.",
            record_count=12_000,
            last_updated="2025-Q1",
            status="active",
            coverage_notes="10,000+ CPT codes, all specialties",
            url="https://www.cms.gov/Medicare/Medicare-Fee-for-Service-Payment/PhysicianFeeSched",
        ),
        DataSource(
            name="CMS Utilization (PUF)",
            source_type="cms_public",
            description="Medicare Part B utilization and payment data by provider. "
                        "Used for market share and concentration analysis.",
            record_count=1_000_000,
            last_updated="2024-Q2",
            status="active",
            coverage_notes="900K+ providers, procedure-level detail",
            url="https://data.cms.gov/provider-summary-by-type-of-service",
        ),
        DataSource(
            name="IRS Form 990",
            source_type="cms_public",
            description="Non-profit hospital financial disclosures via IRS 990. "
                        "Revenue, compensation, and program expenses.",
            record_count=30_000,
            last_updated="2024-Q1",
            status="active",
            coverage_notes="All 501(c)(3) hospitals, 5-year history",
            url="https://www.irs.gov/charities-non-profits/form-990-resources-and-tools",
        ),
        DataSource(
            name="Healthcare M&A News Scraper",
            source_type="scraper",
            description="Automated scraper for healthcare PE deal announcements "
                        "from trade press (Becker's, ModernHealthcare, PRNewswire).",
            record_count=0,
            last_updated="pending",
            status="disabled",
            coverage_notes="Not yet enabled",
            url="",
        ),
        DataSource(
            name="SEC EDGAR 8-K Filings",
            source_type="scraper",
            description="SEC EDGAR 8-K and S-1 filings for healthcare company M&A "
                        "and going-public transactions.",
            record_count=0,
            last_updated="pending",
            status="disabled",
            coverage_notes="Covers public company acquisitions only",
            url="https://efts.sec.gov/LATEST/search-index",
        ),
        DataSource(
            name="PE Firm Portfolio Pages",
            source_type="scraper",
            description="Portfolio company listings from major healthcare PE firm websites. "
                        "Provides active portfolio and realized deal tracking.",
            record_count=0,
            last_updated="pending",
            status="disabled",
            coverage_notes="50+ PE firms tracked; requires JS rendering",
            url="",
        ),
    ]


def compute_data_sources_admin() -> DataSourcesResult:
    all_deals = _load_corpus()
    seed_count = _count_seed_files()
    coverage = _build_coverage(all_deals)
    sources = _data_sources()
    # Patch corpus seed record count
    for s in sources:
        if s.source_type == "corpus_seed":
            s.record_count = len(all_deals)
    scraper_statuses = _scraper_status()

    return DataSourcesResult(
        corpus_coverage=coverage,
        data_sources=sources,
        scraper_statuses=scraper_statuses,
        seed_file_count=seed_count,
        total_seed_deals=len(all_deals),
    )
