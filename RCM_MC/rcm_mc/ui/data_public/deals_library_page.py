"""Deals Library page — /deals-library.

Dense sortable table of all 615+ corpus deals with payer mix, MOIC,
entry multiple, vintage regime, and data quality grade.
"""
from __future__ import annotations

import html as _html
import os
import tempfile
from typing import Any, Dict, List, Optional


def _get_all_seed_deals() -> List[Dict[str, Any]]:
    from rcm_mc.data_public.deals_corpus import _SEED_DEALS
    from rcm_mc.data_public.extended_seed import EXTENDED_SEED_DEALS
    result = list(_SEED_DEALS) + list(EXTENDED_SEED_DEALS)
    for i in range(2, 32):
        try:
            mod = __import__(
                f"rcm_mc.data_public.extended_seed_{i}",
                fromlist=[f"EXTENDED_SEED_DEALS_{i}"],
            )
            result += list(getattr(mod, f"EXTENDED_SEED_DEALS_{i}"))
        except (ImportError, AttributeError):
            pass
    return result


def _entry_multiple(deal: Dict[str, Any]) -> Optional[float]:
    ev = deal.get("ev_mm") or deal.get("entry_ev_mm")
    ebitda = deal.get("ebitda_at_entry_mm") or deal.get("ebitda_mm")
    if ev and ebitda and float(ebitda) > 0:
        return round(float(ev) / float(ebitda), 1)
    return None


def _commercial_pct(deal: Dict[str, Any]) -> Optional[float]:
    pm = deal.get("payer_mix")
    if not pm or not isinstance(pm, dict):
        return None
    return pm.get("commercial")


def _vintage_regime(year: Optional[int]) -> str:
    if year is None:
        return "unknown"
    _MAP = {
        2000: "peak", 2001: "contraction", 2002: "recovery", 2003: "recovery",
        2004: "expansion", 2005: "expansion", 2006: "expansion", 2007: "peak",
        2008: "contraction", 2009: "contraction", 2010: "recovery", 2011: "recovery",
        2012: "expansion", 2013: "expansion", 2014: "expansion", 2015: "peak",
        2016: "correction", 2017: "expansion", 2018: "expansion", 2019: "expansion",
        2020: "contraction", 2021: "peak", 2022: "peak", 2023: "normalization",
        2024: "normalization",
    }
    return _MAP.get(int(year), "unknown")


def _data_grade(deal: Dict[str, Any]) -> str:
    try:
        from rcm_mc.data_public.deal_quality_scorer import score_deal_quality
        return score_deal_quality(deal).grade
    except Exception:
        return "?"


def _build_rows(deals: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    rows = []
    for deal in deals:
        entry_year = deal.get("entry_year") or deal.get("year")
        moic = deal.get("realized_moic")
        ev = deal.get("ev_mm") or deal.get("entry_ev_mm")
        sector = deal.get("sector") or "—"
        buyer = deal.get("buyer") or "—"
        region = deal.get("region") or "—"
        lev = deal.get("leverage_pct")

        rows.append({
            "source_id":  deal.get("source_id", ""),
            "deal_name":  deal.get("deal_name", "—"),
            "sector":     sector,
            "entry_year": entry_year,
            "regime":     _vintage_regime(entry_year),
            "ev_mm":      float(ev) if ev else None,
            "multiple":   _entry_multiple(deal),
            "moic":       float(moic) if moic is not None else None,
            "irr":        deal.get("realized_irr"),
            "hold":       deal.get("hold_years"),
            "leverage":   float(lev) if lev else None,
            "commercial": _commercial_pct(deal),
            "buyer":      buyer[:30],
            "region":     region[:18],
            "grade":      _data_grade(deal),
            "detail_href": f"/library/{_html.escape(str(deal.get('source_id', '')))}",
        })
    return rows


_COLUMNS = [
    {"key": "deal_name",  "label": "Deal",        "type": "str",      "width": "260px"},
    {"key": "sector",     "label": "Sector",       "type": "str",      "width": "160px"},
    {"key": "entry_year", "label": "Year",         "type": "num",      "decimals": 0, "width": "52px"},
    {"key": "regime",     "label": "Regime",       "type": "regime",   "width": "96px"},
    {"key": "ev_mm",      "label": "EV ($M)",      "type": "currency", "width": "76px"},
    {"key": "multiple",   "label": "EV/EBITDA",    "type": "num",      "decimals": 1, "suffix": "x", "width": "78px"},
    {"key": "moic",       "label": "MOIC",         "type": "moic",     "width": "64px"},
    {"key": "irr",        "label": "IRR",          "type": "irr",      "width": "60px"},
    {"key": "hold",       "label": "Hold (yr)",    "type": "num",      "decimals": 1, "width": "68px"},
    {"key": "leverage",   "label": "Lev%",         "type": "pct",      "decimals": 0, "width": "54px"},
    {"key": "commercial", "label": "Comm%",        "type": "pct",      "decimals": 0, "width": "58px"},
    {"key": "buyer",      "label": "Sponsor",      "type": "str",      "width": "150px"},
    {"key": "region",     "label": "Region",       "type": "str",      "width": "110px", "dim": True},
    {"key": "grade",      "label": "Grade",        "type": "grade",    "width": "50px"},
]


def _kpi_bar(deals: List[Dict[str, Any]], rows: List[Dict[str, Any]]) -> str:
    from rcm_mc.ui._chartis_kit import ck_kpi_block, ck_fmt_num

    total = len(deals)
    realized = [r for r in rows if r["moic"] is not None]
    moics = sorted([r["moic"] for r in realized])
    p50 = moics[len(moics) // 2] if moics else None
    loss_count = sum(1 for m in moics if m < 1.0)
    sectors = len({d.get("sector") for d in deals if d.get("sector")})

    p50_html = ck_fmt_num(p50, 2, "x") if p50 else '<span class="faint">—</span>'
    loss_pct = f"{loss_count/len(moics)*100:.1f}%" if moics else "—"

    return (
        f'<div class="ck-kpi-grid">'
        + ck_kpi_block("Total Deals", f'<span class="mn">{total}</span>', "in corpus")
        + ck_kpi_block("Realized", f'<span class="mn">{len(realized)}</span>', f"{len(realized)/total*100:.0f}% of corpus")
        + ck_kpi_block("Corpus P50 MOIC", p50_html, "realized deals")
        + ck_kpi_block("Loss Rate", f'<span class="mn neg">{loss_pct}</span>', "MOIC < 1.0×")
        + ck_kpi_block("Sectors", f'<span class="mn">{sectors}</span>', "covered")
        + '</div>'
    )


def render_deals_library(
    sector_filter: str = "",
    regime_filter: str = "",
    search: str = "",
    sort_by: str = "entry_year",
    sort_dir: str = "desc",
) -> str:
    from rcm_mc.ui._chartis_kit import (
        chartis_shell, ck_table, ck_section_header,
    )
    from rcm_mc.ui.chartis._helpers import render_page_explainer

    deals = _get_all_seed_deals()
    rows = _build_rows(deals)
    n_deals = len(deals)
    explainer = render_page_explainer(
        what=(
            f"Browsable {n_deals:,}-deal healthcare-PE corpus — name, "
            "sponsor, entry year, sector, EV / EBITDA multiple, "
            "realized MOIC and IRR, hold period, commercial-payer %, "
            "vintage regime, and data grade per row. See the provenance "
            "footer for which rows are real vs. synthetic."
        ),
        scale=(
            "Data grade A–D reflects row completeness: A = all core "
            "fields populated (entry + exit + payer mix + returns); "
            "D = thin, sponsor or returns missing. Sort by any column."
        ),
        use=(
            "Filter by sector + regime to assemble comparables for a "
            "target; click a deal row to open its detail view."
        ),
        source=(
            "data_public/deal_quality_score.py (grading) + "
            "data_public/deals_corpus._SEED_DEALS + extended_seed_*.py."
        ),
        page_key="library",
    )

    # Build filter options
    all_sectors = sorted({d.get("sector") for d in deals if d.get("sector")})
    all_regimes = ["expansion", "peak", "contraction", "recovery", "correction", "normalization"]

    # Apply server-side filters (client-side search handles the rest)
    if sector_filter:
        rows = [r for r in rows if r["sector"] == sector_filter]
    if regime_filter:
        rows = [r for r in rows if r["regime"] == regime_filter]

    # Sort
    _SORT_KEY = {
        "entry_year": "entry_year", "moic": "moic", "ev_mm": "ev_mm",
        "multiple": "multiple", "deal_name": "deal_name",
    }
    sk = _SORT_KEY.get(sort_by, "entry_year")
    rev = sort_dir == "desc"
    rows.sort(key=lambda r: (r[sk] is None, r[sk] or 0 if isinstance(r[sk], (int, float)) else str(r[sk] or "")), reverse=rev)

    # Sector <select> options
    sec_opts = '<option value="">All Sectors</option>' + "".join(
        f'<option value="{_html.escape(s)}" {"selected" if s==sector_filter else ""}>{_html.escape(s)}</option>'
        for s in all_sectors
    )
    reg_opts = '<option value="">All Regimes</option>' + "".join(
        f'<option value="{r}" {"selected" if r==regime_filter else ""}>{r.title()}</option>'
        for r in all_regimes
    )

    filter_bar = f"""
<form method="get" action="/library" class="ck-filters" style="margin-bottom:10px;">
  <span class="ck-filter-label">Sector</span>
  <select name="sector" class="ck-sel" onchange="this.form.submit()">{sec_opts}</select>
  <span class="ck-filter-label">Regime</span>
  <select name="regime" class="ck-sel" onchange="this.form.submit()">{reg_opts}</select>
  <span class="ck-filter-label">Search</span>
  <input type="text" name="q" value="{_html.escape(search)}" placeholder="deal name, sponsor..." class="ck-input" data-search-target="#deals-tbl">
</form>"""

    from rcm_mc.ui._chartis_kit import ck_related_views

    kpis = _kpi_bar(deals, rows)
    section = ck_section_header("DEAL CORPUS", "all healthcare PE transactions", len(rows))
    table = ck_table(rows, _COLUMNS, caption="", sortable=True, id="deals-tbl")
    related = ck_related_views([
        ("Sponsor Track Record",  "/sponsor-track-record"),
        ("Sector Intel",          "/sector-intel"),
        ("Base Rates",            "/base-rates"),
        ("Payer Intelligence",    "/payer-intelligence"),
        ("Vintage Cohorts",       "/vintage-cohorts"),
        ("Deal Screening",        "/deal-screening"),
    ])

    body = explainer + kpis + filter_bar + section + table + related

    return chartis_shell(
        body,
        title="Deals Library",
        active_nav="/library",
        subtitle=f"{len(rows):,} deals · {len({r['sector'] for r in rows})} sectors · sorted by {sort_by} {sort_dir}",
    )
