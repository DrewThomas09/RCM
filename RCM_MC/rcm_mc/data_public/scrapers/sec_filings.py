"""SEC EDGAR scraper for hospital and health-system M&A disclosures.

Uses the EDGAR EFTS full-text search API (no API key required, 10 req/s limit).
Targets 8-K (material event), SC TO-T (tender offer), and DEFM14A (merger proxy)
filings that mention hospital acquisitions.

The EDGAR EFTS base URL is documented at:
    https://efts.sec.gov/LATEST/search-index?q=...

Results are returned as raw dicts matching the normalizer's expected keys.
All HTTP is stdlib-only (urllib.request).

Public API:
    scrape(keyword, start_year, end_year, max_hits) -> List[dict]
    scrape_recent_hospital_ma(max_hits)             -> List[dict]
"""
from __future__ import annotations

import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


_EDGAR_EFTS = "https://efts.sec.gov/LATEST/search-index"
_USER_AGENT = "SeekingChartis/1.0 data@seekingchartis.com"  # EDGAR requires contact info
_RATE_LIMIT_S = 0.15  # 10 req/s safe margin

_HEALTH_KEYWORDS = [
    '"hospital acquisition"',
    '"health system acquisition"',
    '"hospital merger"',
    '"health system merger"',
    '"hospital purchase price"',
    '"hospital enterprise value"',
]

_TARGET_FORMS = "8-K,SC+TO-T,DEFM14A"


def _get_json(url: str) -> Optional[Dict[str, Any]]:
    req = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, json.JSONDecodeError, OSError):
        return None


def _build_search_url(
    query: str,
    forms: str,
    start_date: str,
    end_date: str,
    from_offset: int = 0,
    size: int = 20,
) -> str:
    params = {
        "q": query,
        "forms": forms,
        "dateRange": "custom",
        "startdt": start_date,
        "enddt": end_date,
        "from": str(from_offset),
        "hits.hits._source": "entity_name,file_date,form_type,period_of_report,display_names",
    }
    return f"{_EDGAR_EFTS}?{urllib.parse.urlencode(params)}"


def _parse_ev_from_text(text: str) -> Optional[float]:
    """Extract the first enterprise value mention in $M from filing text."""
    patterns = [
        r"\$\s*([\d,]+(?:\.\d+)?)\s*billion",
        r"\$\s*([\d,]+(?:\.\d+)?)\s*million",
        r"enterprise\s+value\s+of\s+approximately\s+\$\s*([\d,.]+)\s*(billion|million)?",
        r"total\s+consideration\s+of\s+\$\s*([\d,.]+)\s*(billion|million)?",
    ]
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            raw = float(m.group(1).replace(",", ""))
            unit_group = m.lastgroup
            if unit_group and "billion" in m.group(m.lastindex or 0).lower():
                return raw * 1_000
            if "billion" in pat:
                return raw * 1_000
            return raw
    return None


def _parse_year_from_date(date_str: str) -> Optional[int]:
    if not date_str:
        return None
    try:
        return int(date_str[:4])
    except (ValueError, TypeError):
        return None


def _hit_to_raw(hit: Dict[str, Any]) -> Dict[str, Any]:
    src = hit.get("_source", {})
    names = src.get("display_names") or []
    entity = src.get("entity_name", "")
    company = names[0] if names else entity

    file_date = src.get("file_date", "")
    year = _parse_year_from_date(file_date)
    form = src.get("form_type", "")

    return {
        "source_id": f"edgar_{hit.get('_id', '')}",
        "source": "sec_edgar",
        "deal_name": f"{company} – {form} ({file_date})",
        "year": year,
        "buyer": None,
        "seller": company,
        "ev_mm": None,
        "ebitda_at_entry_mm": None,
        "hold_years": None,
        "realized_moic": None,
        "realized_irr": None,
        "payer_mix": None,
        "notes": f"SEC EDGAR {form} filing; entity: {entity}; date: {file_date}",
    }


def scrape(
    keyword: str = '"hospital acquisition"',
    start_year: int = 2015,
    end_year: int = 2024,
    max_hits: int = 50,
    forms: str = _TARGET_FORMS,
) -> List[Dict[str, Any]]:
    """Query EDGAR EFTS and return raw deal dicts for hospital M&A filings.

    Each dict matches the normalizer's input schema with None for unknown fields.
    Callers should pass results through normalizer.normalize_raw() before upserting.
    """
    start_date = f"{start_year}-01-01"
    end_date = f"{end_year}-12-31"
    results: List[Dict[str, Any]] = []
    seen: set = set()

    page_size = min(20, max_hits)
    url = _build_search_url(keyword, forms, start_date, end_date, 0, page_size)
    data = _get_json(url)
    if not data:
        return results

    hits = data.get("hits", {}).get("hits", [])
    for hit in hits:
        hit_id = hit.get("_id", "")
        if hit_id in seen:
            continue
        seen.add(hit_id)
        raw = _hit_to_raw(hit)
        results.append(raw)
        if len(results) >= max_hits:
            break
        time.sleep(_RATE_LIMIT_S)

    return results


def scrape_recent_hospital_ma(max_hits: int = 100) -> List[Dict[str, Any]]:
    """Scrape multiple EDGAR keyword queries and deduplicate.

    Targets the last decade of hospital M&A disclosures across multiple
    search terms to maximize recall.
    """
    all_raw: List[Dict[str, Any]] = []
    seen_ids: set = set()

    for kw in _HEALTH_KEYWORDS:
        batch = scrape(keyword=kw, start_year=2012, end_year=2024, max_hits=20)
        for raw in batch:
            sid = raw.get("source_id", "")
            if sid not in seen_ids:
                seen_ids.add(sid)
                all_raw.append(raw)
        time.sleep(_RATE_LIMIT_S * 3)
        if len(all_raw) >= max_hits:
            break

    return all_raw[:max_hits]
