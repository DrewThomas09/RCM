"""Corpus Comparables page — /comparables.

Given a query deal (specified via URL params), finds the most similar
realized deals in the 635-deal corpus and shows IC-grade peer benchmarks.

URL params:
  sector     : filter/anchor to a specific sector
  ev_mm      : target EV in $M
  ebitda_mm  : target EBITDA in $M (used to compute entry multiple)
  hold_years : expected hold
  commercial : commercial payer fraction 0-1
  search     : text search in deal name

If no params given, shows the full corpus with a search form.
"""
from __future__ import annotations

import html as _html
import importlib
from typing import Any, Dict, List, Optional, Tuple


def _load_corpus() -> List[Dict[str, Any]]:
    from rcm_mc.data_public.deals_corpus import _SEED_DEALS
    from rcm_mc.data_public.extended_seed import EXTENDED_SEED_DEALS
    result = list(_SEED_DEALS) + list(EXTENDED_SEED_DEALS)
    for i in range(2, 32):
        try:
            mod = importlib.import_module(f"rcm_mc.data_public.extended_seed_{i}")
            result += list(getattr(mod, f"EXTENDED_SEED_DEALS_{i}"))
        except (ImportError, AttributeError):
            pass
    return result


def _percentile(vals: List[float], p: float) -> float:
    if not vals:
        return 0.0
    s = sorted(vals)
    idx = p / 100 * (len(s) - 1)
    lo, hi = int(idx), min(int(idx) + 1, len(s) - 1)
    return s[lo] + (s[hi] - s[lo]) * (idx - lo)


# ---------------------------------------------------------------------------
# HTML helpers
# ---------------------------------------------------------------------------

def _moic_html(v: Optional[float]) -> str:
    if v is None:
        return '<span style="color:var(--ck-text-faint)">—</span>'
    color = "#ef4444" if v < 1.0 else ("#22c55e" if v >= 2.5 else "#e2e8f0")
    weight = "600" if v < 1.0 or v >= 2.5 else "400"
    return (
        f'<span style="font-family:var(--ck-mono);font-variant-numeric:tabular-nums;'
        f'color:{color};font-weight:{weight}">{v:.2f}×</span>'
    )


def _num_html(v: Optional[float], decimals: int = 1, suffix: str = "") -> str:
    if v is None:
        return '<span style="color:var(--ck-text-faint)">—</span>'
    return (
        f'<span style="font-family:var(--ck-mono);font-variant-numeric:tabular-nums">'
        f'{v:.{decimals}f}{suffix}</span>'
    )


def _ev_html(v: Optional[float]) -> str:
    if v is None:
        return '<span style="color:var(--ck-text-faint)">—</span>'
    if v >= 1000:
        return _num_html(v / 1000, 1, "B")
    return _num_html(v, 0, "M")


def _sim_badge(score: float) -> str:
    pct = int(score * 100)
    color = "#22c55e" if pct >= 70 else ("#f59e0b" if pct >= 40 else "#64748b")
    return (
        f'<span style="font-family:var(--ck-mono);font-size:9.5px;'
        f'color:{color};font-variant-numeric:tabular-nums">{pct}%</span>'
    )


def _payer_bars(pm: Optional[Dict[str, float]]) -> str:
    """Tiny inline payer mix bar (80px wide SVG)."""
    if not pm or not isinstance(pm, dict):
        return '<span style="color:var(--ck-text-faint);font-size:9px">—</span>'
    comm = pm.get("commercial", 0) or 0
    med = pm.get("medicare", 0) or 0
    mcd = pm.get("medicaid", 0) or 0
    sp = pm.get("self_pay", 0) or 0
    total = comm + med + mcd + sp
    if total <= 0:
        return ""
    w = 80
    cx = comm / total * w
    mx = med / total * w
    ax = mcd / total * w
    sx = sp / total * w
    return (
        f'<svg width="{w}" height="8" xmlns="http://www.w3.org/2000/svg" style="display:inline-block;vertical-align:middle;">'
        f'<rect x="0" y="1" width="{cx:.1f}" height="6" fill="#3b82f6"/>'
        f'<rect x="{cx:.1f}" y="1" width="{mx:.1f}" height="6" fill="#22c55e"/>'
        f'<rect x="{cx+mx:.1f}" y="1" width="{ax:.1f}" height="6" fill="#f59e0b"/>'
        f'<rect x="{cx+mx+ax:.1f}" y="1" width="{sx:.1f}" height="6" fill="#475569"/>'
        f'</svg>'
        f'<span style="font-family:var(--ck-mono);font-size:8.5px;color:#64748b;margin-left:3px;">'
        f'{comm*100:.0f}%C</span>'
    )


# ---------------------------------------------------------------------------
# Peer stats panel
# ---------------------------------------------------------------------------

def _peer_stats_panel(comps: List[Dict[str, Any]], target: Optional[Dict[str, Any]]) -> str:
    """Percentile context for the target vs peer group."""
    realized = [c for c in comps if c.get("realized_moic") is not None]
    if not realized:
        return ""

    moics = sorted([float(c["realized_moic"]) for c in realized])
    p25 = _percentile(moics, 25)
    p50 = _percentile(moics, 50)
    p75 = _percentile(moics, 75)
    loss = sum(1 for m in moics if m < 1.0) / len(moics)
    homerun = sum(1 for m in moics if m >= 3.0) / len(moics)

    # Multiple stats
    multiples = []
    for c in comps:
        ev = c.get("ev_mm")
        eb = c.get("ebitda_at_entry_mm") or c.get("ebitda_mm")
        if ev and eb and float(eb) > 0:
            multiples.append(float(ev) / float(eb))
    mult_p50 = _percentile(sorted(multiples), 50) if multiples else None

    target_moic = target.get("realized_moic") if target else None

    cells = [
        ("Peer P25 MOIC", _moic_html(p25)),
        ("Peer P50 MOIC", _moic_html(p50)),
        ("Peer P75 MOIC", _moic_html(p75)),
        ("Peer Loss Rate", f'<span style="font-family:var(--ck-mono);color:#ef4444">{loss*100:.1f}%</span>'),
        ("Peer 3×+ Rate", f'<span style="font-family:var(--ck-mono);color:#22c55e">{homerun*100:.1f}%</span>'),
        ("Peer Avg Multiple", _num_html(mult_p50, 1, "×") if mult_p50 else "—"),
    ]
    if target_moic is not None:
        percentile_rank = sum(1 for m in moics if m <= float(target_moic)) / len(moics) * 100
        cells.append(("Target MOIC Percentile", f'<span style="font-family:var(--ck-mono)">{percentile_rank:.0f}th</span>'))

    cells_html = "".join(
        f'<div style="padding:8px 12px;border-right:1px solid #1e293b;">'
        f'<div style="font-size:8.5px;color:#475569;letter-spacing:0.1em;text-transform:uppercase;margin-bottom:3px;">{_html.escape(k)}</div>'
        f'<div style="font-size:13px;">{v}</div>'
        f'</div>'
        for k, v in cells
    )
    return f"""
<div class="ck-panel">
  <div class="ck-panel-title">Peer Group Statistics ({len(comps)} comparable deals · {len(realized)} realized)</div>
  <div style="display:flex;flex-wrap:wrap;padding:8px 4px;">
    {cells_html}
  </div>
</div>"""


# ---------------------------------------------------------------------------
# Main comparables table
# ---------------------------------------------------------------------------

def _comps_table(comps: List[Dict[str, Any]], show_similarity: bool = True) -> str:
    headers = [
        ("Deal", "left", "240px"),
        ("Sector", "left", "160px"),
        ("Year", "right", "48px"),
        ("EV", "right", "72px"),
        ("EV/EBITDA", "right", "78px"),
        ("MOIC", "right", "64px"),
        ("IRR", "right", "60px"),
        ("Hold", "right", "60px"),
        ("Payer Mix", "center", "110px"),
    ]
    if show_similarity:
        headers.append(("Match", "center", "60px"))

    thead = "".join(
        f'<th style="text-align:{align};{"width:"+w+";" if w else ""}">{h}</th>'
        for h, align, w in headers
    )

    rows_html = []
    for i, c in enumerate(comps):
        stripe = ' style="background:#0f172a"' if i % 2 == 1 else ""
        ev = c.get("ev_mm")
        eb = c.get("ebitda_at_entry_mm") or c.get("ebitda_mm")
        multiple = float(ev) / float(eb) if ev and eb and float(eb) > 0 else None
        irr = c.get("realized_irr")
        hold = c.get("hold_years")
        sim = c.get("similarity_score", c.get("_similarity_score"))

        # Detail link
        sid = _html.escape(str(c.get("source_id", "")))
        deal_html = (
            f'<a href="/deals-library/{sid}" style="color:var(--ck-accent);text-decoration:none;font-size:11px;">'
            f'{_html.escape(c.get("deal_name") or "—")[:38]}</a>'
        )

        row = f"""
<tr{stripe}>
  <td style="padding:7px 8px;">{deal_html}</td>
  <td class="dim" style="font-size:10.5px;padding:7px 6px;">{_html.escape(str(c.get('sector') or '—')[:22])}</td>
  <td class="mono dim" style="text-align:right;padding:7px 6px;">{c.get('year') or '—'}</td>
  <td style="text-align:right;padding:7px 6px;">{_ev_html(float(ev) if ev else None)}</td>
  <td style="text-align:right;padding:7px 6px;">{_num_html(multiple, 1, '×')}</td>
  <td style="text-align:right;padding:7px 6px;">{_moic_html(float(c['realized_moic']) if c.get('realized_moic') is not None else None)}</td>
  <td class="mono dim" style="text-align:right;padding:7px 6px;">{_num_html(float(irr)*100 if irr else None, 1, '%')}</td>
  <td class="mono dim" style="text-align:right;padding:7px 6px;">{_num_html(float(hold) if hold else None, 1, 'yr')}</td>
  <td style="text-align:center;padding:7px 6px;">{_payer_bars(c.get('payer_mix'))}</td>"""
        if show_similarity and sim is not None:
            row += f'\n  <td style="text-align:center;padding:7px 6px;">{_sim_badge(float(sim))}</td>'
        row += "\n</tr>"
        rows_html.append(row)

    colgroup = "".join(f'<col style="width:{w}">' for _, _, w in headers)
    return f"""
<div class="ck-panel">
  <div class="ck-panel-title">Comparable Transactions</div>
  <div class="ck-table-wrap">
    <table class="ck-table" style="table-layout:fixed;" id="comps-tbl">
      <colgroup>{colgroup}</colgroup>
      <thead><tr>{thead}</tr></thead>
      <tbody>{''.join(rows_html)}</tbody>
    </table>
  </div>
</div>"""


# ---------------------------------------------------------------------------
# Query form
# ---------------------------------------------------------------------------

def _all_sectors(corpus: List[Dict[str, Any]]) -> List[str]:
    return sorted({d.get("sector") for d in corpus if d.get("sector")})


def _query_form(corpus: List[Dict[str, Any]], params: Dict[str, str]) -> str:
    sector = params.get("sector", "")
    ev_mm = params.get("ev_mm", "")
    ebitda_mm = params.get("ebitda_mm", "")
    hold_years = params.get("hold_years", "")
    commercial = params.get("commercial", "")
    search = params.get("search", "")

    sec_opts = '<option value="">All Sectors</option>' + "".join(
        f'<option value="{_html.escape(s)}" {"selected" if s==sector else ""}>{_html.escape(s)}</option>'
        for s in _all_sectors(corpus)
    )

    return f"""
<form method="get" action="/comparables" class="ck-filters" style="margin-bottom:12px;flex-wrap:wrap;gap:8px;">
  <span class="ck-filter-label">Sector</span>
  <select name="sector" class="ck-sel" style="width:180px;">{sec_opts}</select>
  <span class="ck-filter-label">EV ($M)</span>
  <input type="number" name="ev_mm" value="{_html.escape(ev_mm)}" placeholder="e.g. 250" class="ck-input" style="width:80px;">
  <span class="ck-filter-label">EBITDA ($M)</span>
  <input type="number" name="ebitda_mm" value="{_html.escape(ebitda_mm)}" placeholder="e.g. 25" class="ck-input" style="width:80px;">
  <span class="ck-filter-label">Hold (yr)</span>
  <input type="number" name="hold_years" value="{_html.escape(hold_years)}" placeholder="5" class="ck-input" style="width:60px;" step="0.5">
  <span class="ck-filter-label">Comm%</span>
  <input type="number" name="commercial" value="{_html.escape(commercial)}" placeholder="0.6" class="ck-input" style="width:60px;" step="0.05">
  <span class="ck-filter-label">Search</span>
  <input type="text" name="search" value="{_html.escape(search)}" placeholder="deal name..." class="ck-input" data-search-target="#comps-tbl">
  <button type="submit" class="ck-btn">Find Comparables</button>
</form>"""


# ---------------------------------------------------------------------------
# Main render
# ---------------------------------------------------------------------------

def render_comparables(
    sector: str = "",
    ev_mm: Optional[float] = None,
    ebitda_mm: Optional[float] = None,
    hold_years: Optional[float] = None,
    commercial: Optional[float] = None,
    search: str = "",
    n: int = 20,
) -> str:
    from rcm_mc.ui._chartis_kit import chartis_shell, ck_section_header, ck_kpi_block
    from rcm_mc.data_public.deal_comparables_enhanced import find_enhanced_comps

    corpus = _load_corpus()

    # Build query deal dict
    has_query = any(v is not None for v in [ev_mm, ebitda_mm, hold_years, commercial]) or bool(sector)
    query_deal: Dict[str, Any] = {}
    if sector:
        query_deal["sector"] = sector
    if ev_mm is not None:
        query_deal["ev_mm"] = ev_mm
    if ebitda_mm is not None:
        query_deal["ebitda_at_entry_mm"] = ebitda_mm
    if hold_years is not None:
        query_deal["hold_years"] = hold_years
    if commercial is not None:
        query_deal["payer_mix"] = {"commercial": commercial, "medicare": (1 - commercial) * 0.5,
                                    "medicaid": (1 - commercial) * 0.4, "self_pay": (1 - commercial) * 0.1}

    # Get comparables
    if has_query:
        comps = find_enhanced_comps(query_deal, corpus, n=n, min_similarity=0.0)
        show_sim = True
        subtitle_mode = "similarity-ranked comparables"
    else:
        # Show all realized corpus deals, most recent first
        comps = sorted(
            [d for d in corpus if d.get("realized_moic") is not None],
            key=lambda d: (d.get("year") or 0),
            reverse=True
        )[:n]
        show_sim = False
        subtitle_mode = "most recent realized deals"

    # Apply search filter
    if search:
        q = search.lower()
        comps = [c for c in comps if q in (c.get("deal_name") or "").lower()
                  or q in (c.get("buyer") or "").lower()
                  or q in (c.get("sector") or "").lower()]

    # KPI bar
    total_corpus = len(corpus)
    realized_n = sum(1 for d in corpus if d.get("realized_moic") is not None)
    kpis = (
        '<div class="ck-kpi-grid">'
        + ck_kpi_block("Corpus Size", f'<span class="mn">{total_corpus}</span>', "total deals")
        + ck_kpi_block("Realized Deals", f'<span class="mn">{realized_n}</span>', "with MOIC data")
        + ck_kpi_block("Comparables Found", f'<span class="mn">{len(comps)}</span>', subtitle_mode)
        + ck_kpi_block("Sectors Covered", f'<span class="mn">{len(_all_sectors(corpus))}</span>', "in corpus")
        + '</div>'
    )

    params = {
        "sector": sector, "ev_mm": str(ev_mm) if ev_mm else "",
        "ebitda_mm": str(ebitda_mm) if ebitda_mm else "",
        "hold_years": str(hold_years) if hold_years else "",
        "commercial": str(commercial) if commercial else "",
        "search": search,
    }
    form = _query_form(corpus, params)
    section = ck_section_header(
        "COMPARABLES" if has_query else "REALIZED CORPUS DEALS",
        f"{'similarity-ranked against query deal' if has_query else 'most recent realized exits'} · {len(comps)} shown"
    )
    comps_table = _comps_table(comps, show_similarity=show_sim)

    peer_panel = ""
    if has_query and comps:
        peer_panel = _peer_stats_panel(comps, query_deal)

    body = kpis + form + (peer_panel + section + comps_table if peer_panel else section + comps_table)

    entry_multiple_str = ""
    if ev_mm and ebitda_mm and ebitda_mm > 0:
        mult = ev_mm / ebitda_mm
        entry_multiple_str = f" · {mult:.1f}× entry multiple"

    return chartis_shell(
        body,
        title="Corpus Comparables",
        active_nav="/comparables",
        subtitle=(
            f"{len(comps)} comparables" +
            (f" · {sector}" if sector else "") +
            (f" · EV ${ev_mm:,.0f}M" if ev_mm else "") +
            entry_multiple_str
        ) if has_query else f"{total_corpus} deals · {realized_n} realized",
    )
