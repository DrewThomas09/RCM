"""Full corpus ingest pipeline — seed + PE portfolios + news in one call.

Orchestrates all data sources in priority order:
    1. Core seed deals (35 deals, fully curated, always first)
    2. Extended seed deals (20 deals, curated second batch)
    3. News deals (15+ curated from Modern Healthcare / Becker's)
    4. PE portfolio deals (KKR/Apollo/Carlyle/Bain/TPG curated fallbacks)
    5. SEC EDGAR filings (live HTTP, optional — set sec_edgar=True)

Deduplication: source_id is the unique key; existing records are updated
(not duplicated) via the upsert semantics in DealsCorpus.

Public API:
    IngestReport dataclass
    run_full_ingest(db_path, *, sec_edgar, live_pe, verbose) -> IngestReport
    print_ingest_report(report)                              -> None
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .deals_corpus import DealsCorpus
from .normalizer import normalize_batch


@dataclass
class IngestReport:
    started_at: str
    finished_at: str
    sources_run: List[str]
    counts_by_source: Dict[str, int]
    total_upserted: int
    corpus_stats: Dict[str, Any]
    errors: List[str] = field(default_factory=list)

    def as_dict(self) -> Dict[str, Any]:
        return {
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "sources_run": self.sources_run,
            "counts_by_source": self.counts_by_source,
            "total_upserted": self.total_upserted,
            "corpus_stats": self.corpus_stats,
            "errors": self.errors,
        }


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def run_full_ingest(
    db_path: str,
    *,
    sec_edgar: bool = False,
    live_pe: bool = False,
    verbose: bool = False,
) -> IngestReport:
    """Run all corpus ingest sources and return a report.

    Args:
        db_path:   path to corpus SQLite file (created if absent)
        sec_edgar: whether to call SEC EDGAR live HTTP API (rate-limited)
        live_pe:   whether to attempt live scrape of PE firm pages
        verbose:   print progress to stdout
    """
    started = _utcnow()
    corpus = DealsCorpus(db_path)
    errors: List[str] = []
    counts: Dict[str, int] = {}
    sources_run: List[str] = []

    def _log(msg: str) -> None:
        if verbose:
            print(msg)

    # ------------------------------------------------------------------
    # 1. Core seed
    # ------------------------------------------------------------------
    _log("  [1/5] Loading core seed deals...")
    try:
        n = corpus.seed(skip_if_populated=False)
        counts["seed"] = n
        sources_run.append("seed")
        _log(f"       → {n} deals upserted")
    except Exception as e:
        errors.append(f"seed: {e}")
        _log(f"       ERROR: {e}")

    # ------------------------------------------------------------------
    # 2. News deals (curated)
    # ------------------------------------------------------------------
    _log("  [2/5] Loading curated news deals...")
    try:
        from .scrapers.news_deals import scrape_news_deals
        raw = scrape_news_deals(max_articles=30)
        normalized = normalize_batch(raw)
        n = 0
        for deal in normalized:
            corpus.upsert(deal)
            n += 1
        counts["news"] = n
        sources_run.append("news")
        _log(f"       → {n} deals upserted")
    except Exception as e:
        errors.append(f"news: {e}")
        _log(f"       ERROR: {e}")

    # ------------------------------------------------------------------
    # 3. PE portfolio curated fallbacks (always)
    # ------------------------------------------------------------------
    _log("  [3/5] Loading PE portfolio deals...")
    try:
        from .scrapers.pe_portfolios import (
            _KKR_HEALTHCARE, _APOLLO_HEALTHCARE, _CARLYLE_HEALTHCARE,
            _BAIN_HEALTHCARE, _TPG_HEALTHCARE,
        )
        all_pe = (_KKR_HEALTHCARE + _APOLLO_HEALTHCARE + _CARLYLE_HEALTHCARE
                  + _BAIN_HEALTHCARE + _TPG_HEALTHCARE)
        normalized = normalize_batch(all_pe)
        n = 0
        for deal in normalized:
            corpus.upsert(deal)
            n += 1
        counts["pe_portfolio"] = n
        sources_run.append("pe_portfolio")
        _log(f"       → {n} deals upserted")
    except Exception as e:
        errors.append(f"pe_portfolio: {e}")
        _log(f"       ERROR: {e}")

    # ------------------------------------------------------------------
    # 4. PE portfolio live scrape (optional)
    # ------------------------------------------------------------------
    if live_pe:
        _log("  [4/5] Live-scraping PE firm portfolio pages...")
        try:
            from .scrapers.pe_portfolios import scrape_all
            raw = scrape_all()
            normalized = normalize_batch(raw)
            n = 0
            for deal in normalized:
                corpus.upsert(deal)
                n += 1
            counts["pe_portfolio_live"] = n
            sources_run.append("pe_portfolio_live")
            _log(f"       → {n} deals upserted")
        except Exception as e:
            errors.append(f"pe_portfolio_live: {e}")
            _log(f"       ERROR: {e}")
    else:
        _log("  [4/5] Skipping live PE scrape (pass live_pe=True to enable)")

    # ------------------------------------------------------------------
    # 5. SEC EDGAR live scrape (optional)
    # ------------------------------------------------------------------
    if sec_edgar:
        _log("  [5/5] Querying SEC EDGAR EFTS API...")
        try:
            from .scrapers.sec_filings import scrape_recent_hospital_ma
            raw = scrape_recent_hospital_ma(max_hits=50)
            normalized = normalize_batch(raw)
            n = 0
            for deal in normalized:
                corpus.upsert(deal)
                n += 1
            counts["sec_edgar"] = n
            sources_run.append("sec_edgar")
            _log(f"       → {n} deals upserted")
        except Exception as e:
            errors.append(f"sec_edgar: {e}")
            _log(f"       ERROR: {e}")
    else:
        _log("  [5/5] Skipping SEC EDGAR scrape (pass sec_edgar=True to enable)")

    finished = _utcnow()
    total = sum(counts.values())
    stats = corpus.stats()

    return IngestReport(
        started_at=started,
        finished_at=finished,
        sources_run=sources_run,
        counts_by_source=counts,
        total_upserted=total,
        corpus_stats=stats,
        errors=errors,
    )


def print_ingest_report(report: IngestReport) -> None:
    print(f"\n=== Corpus Ingest Report ===")
    print(f"  Started : {report.started_at}")
    print(f"  Finished: {report.finished_at}")
    print(f"\n  Sources run:")
    for src in report.sources_run:
        n = report.counts_by_source.get(src, 0)
        print(f"    {src:<25} {n:>4} deals upserted")
    print(f"\n  Total upserted: {report.total_upserted}")
    s = report.corpus_stats
    print(f"\n  Corpus totals:")
    print(f"    Total deals   : {s['total']}")
    print(f"    With MOIC     : {s['with_moic']}")
    print(f"    With IRR      : {s['with_irr']}")
    print(f"    By source     : {s['by_source']}")
    if report.errors:
        print(f"\n  Errors ({len(report.errors)}):")
        for e in report.errors:
            print(f"    {e}")
