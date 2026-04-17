"""Public deals corpus and calibration data for SeekingChartis.

Submodules:
    deals_corpus  – SQLite schema + CRUD for public_deals table
    normalizer    – normalize raw deal dicts to canonical schema
    base_rates    – P25/P50/P75 MOIC benchmarks by hospital size + payer mix
    backtester    – backtest platform predictions vs realized outcomes
    scrapers      – data ingestion from SEC EDGAR and PE portfolio pages
"""
from __future__ import annotations

from .deals_corpus import DealsCorpus

__all__ = ["DealsCorpus"]
