"""Deal Search page — /deal-search.

Full-text search across 655 corpus deals.
Filters: sector, year range, EV range, MOIC range, payer regime, deal type.
Dense results table with all key metrics.
"""
from __future__ import annotations

import html as _html
import importlib
import math
from typing import Any, Dict, List, Optional


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


def _moic_color(m: float) -> str:
    if m >= 3.0: return "#22c55e"
    if m >= 2.0: return "#2fb3ad"
    if m >= 1.5: return "#b8732a"
    return "#b5321e"


def _match_deal(deal: Dict[str, Any], query: str, sector: str, yr_lo: Optional[int],
                yr_hi: Optional[int], ev_lo: Optional[float], ev_hi: Optional[float],
                moic_lo: Optional[float], moic_hi: Optional[float],
                deal_type: str) -> bool:
    """Return True if deal matches all active filters."""
    # Full-text search on deal_name, buyer, seller, notes, sector
    if query:
        q = query.lower()
        haystack = " ".join(str(deal.get(f, "") or "") for f in
                            ("deal_name", "buyer", "seller", "notes", "sector")).lower()
        if q not in haystack:
            return False

    if sector and deal.get("sector", "") != sector:
        return False

    if deal_type and deal.get("deal_type", "") != deal_type:
        return False

    yr = deal.get("year") or deal.get("entry_year")
    if yr is not None:
        try:
            yr_int = int(yr)
            if yr_lo is not None and yr_int < yr_lo:
                return False
            if yr_hi is not None and yr_int > yr_hi:
                return False
        except (TypeError, ValueError):
            pass

    ev = deal.get("ev_mm")
    if ev is not None:
        try:
            ev_f = float(ev)
            if ev_lo is not None and ev_f < ev_lo:
                return False
            if ev_hi is not None and ev_f > ev_hi:
                return False
        except (TypeError, ValueError):
            pass

    moic = deal.get("realized_moic")
    if moic is not None:
        try:
            moic_f = float(moic)
            if moic_lo is not None and moic_f < moic_lo:
                return False
            if moic_hi is not None and moic_f > moic_hi:
                return False
        except (TypeError, ValueError):
            pass

    return True


def _payer_mini(pm: Any) -> str:
    """Tiny inline payer mix bar."""
    if not isinstance(pm, dict):
        return '<span style="color:#475569;font-size:9px;">—</span>'
    comm = float(pm.get("commercial", 0) or 0)
    med  = float(pm.get("medicare", 0) or 0)
    maid = float(pm.get("medicaid", 0) or 0)
    total = max(0.01, comm + med + maid)
    W = 60
    w_c = int(comm / total * W)
    w_m = int(med / total * W)
    w_d = max(0, W - w_c - w_m)
    return (
        f'<svg width="{W}" height="6" xmlns="http://www.w3.org/2000/svg">'
        f'<rect x="0" y="0" width="{w_c}" height="6" fill="#2fb3ad"/>'
        f'<rect x="{w_c}" y="0" width="{w_m}" height="6" fill="#22c55e"/>'
        f'<rect x="{w_c+w_m}" y="0" width="{w_d}" height="6" fill="#b8732a"/>'
        f'</svg>'
    )


def render_deal_search(
    query: str = "",
    sector: str = "",
    yr_lo: Optional[int] = None,
    yr_hi: Optional[int] = None,
    ev_lo: Optional[float] = None,
    ev_hi: Optional[float] = None,
    moic_lo: Optional[float] = None,
    moic_hi: Optional[float] = None,
    deal_type: str = "",
    sort_by: str = "realized_moic",
    page: int = 1,
) -> str:
    from rcm_mc.ui._chartis_kit import chartis_shell, ck_section_header, ck_kpi_block
    from rcm_mc.ui.chartis._helpers import render_page_explainer

    corpus = _load_corpus()

    # Apply filters
    matches = [
        d for d in corpus
        if _match_deal(d, query, sector, yr_lo, yr_hi, ev_lo, ev_hi, moic_lo, moic_hi, deal_type)
    ]

    # Sort
    def _sort_key(d: Dict[str, Any]):
        v = d.get(sort_by)
        if v is None:
            return (1, 0)
        try:
            return (0, -float(v))
        except (TypeError, ValueError):
            return (0, 0)

    if sort_by == "deal_name":
        matches.sort(key=lambda d: d.get("deal_name", "") or "")
    elif sort_by == "year":
        matches.sort(key=lambda d: -(int(d.get("year") or d.get("entry_year") or 0) or 0))
    elif sort_by == "ev_mm":
        matches.sort(key=lambda d: -(float(d.get("ev_mm") or 0)))
    elif sort_by == "hold_years":
        matches.sort(key=lambda d: float(d.get("hold_years") or 0))
    else:
        matches.sort(key=_sort_key)

    # Paginate
    PAGE_SIZE = 40
    total = len(matches)
    total_pages = max(1, math.ceil(total / PAGE_SIZE))
    page = max(1, min(page, total_pages))
    page_deals = matches[(page - 1) * PAGE_SIZE: page * PAGE_SIZE]

    # KPIs on filtered set
    moics  = [float(d["realized_moic"]) for d in matches if d.get("realized_moic") is not None]
    evs    = [float(d["ev_mm"]) for d in matches if d.get("ev_mm") is not None]
    p50_m  = sorted(moics)[len(moics) // 2] if moics else 0
    avg_ev = sum(evs) / len(evs) if evs else 0

    kpis = (
        '<div class="ck-kpi-grid">'
        + ck_kpi_block("Results", f'<span class="mn">{total:,}</span>', f"of {len(corpus):,} corpus deals")
        + ck_kpi_block("P50 MOIC", f'<span class="mn" style="color:{_moic_color(p50_m)}">{p50_m:.2f}x</span>', "filtered set")
        + ck_kpi_block("Avg EV", f'<span class="mn">${avg_ev:.0f}M</span>', "filtered set")
        + ck_kpi_block("Page", f'<span class="mn">{page}/{total_pages}</span>', f"{PAGE_SIZE} per page")
        + '</div>'
    )

    # Filter form
    # Collect unique sectors and deal types from corpus
    all_sectors   = sorted({d.get("sector") for d in corpus if d.get("sector")})
    all_deal_types = sorted({d.get("deal_type") for d in corpus if d.get("deal_type")})

    def _esc(v: Any) -> str:
        return _html.escape(str(v) if v is not None else "")

    def _opt(val: Any, label: str, selected: str) -> str:
        sel = ' selected' if str(val) == selected else ""
        return f'<option value="{_esc(val)}"{sel}>{_esc(label)}</option>'

    sector_opts = '<option value="">All Sectors</option>' + "".join(
        _opt(s, s[:35], sector) for s in all_sectors
    )
    type_opts = '<option value="">All Types</option>' + "".join(
        _opt(t, t, deal_type) for t in all_deal_types
    )

    def _vi(name: str, val: Any, placeholder: str = "") -> str:
        v_str = str(val) if val is not None else ""
        return (f'<input name="{name}" value="{_esc(v_str)}" placeholder="{_esc(placeholder)}" '
                f'style="background:#f5f1ea;border:1px solid #d6cfc3;color:#1a2332;'
                f'font-family:var(--ck-mono);font-size:10px;padding:3px 6px;width:80px;">')

    form_html = f"""
<div class="ck-panel">
  <div class="ck-panel-title">Search &amp; Filter</div>
  <form method="get" action="/deal-search" style="padding:10px 16px;">
    <div style="display:flex;flex-wrap:wrap;gap:12px;align-items:flex-end;">
      <div>
        <div style="font-size:9px;color:#475569;margin-bottom:3px;">Search</div>
        <input name="q" value="{_esc(query)}" placeholder="deal name, buyer, sector..."
          style="background:#f5f1ea;border:1px solid #d6cfc3;color:#1a2332;
          font-size:10px;padding:3px 8px;width:200px;">
      </div>
      <div>
        <div style="font-size:9px;color:#475569;margin-bottom:3px;">Sector</div>
        <select name="sector" style="background:#f5f1ea;border:1px solid #d6cfc3;color:#1a2332;font-size:10px;padding:3px 6px;">
          {sector_opts}
        </select>
      </div>
      <div>
        <div style="font-size:9px;color:#475569;margin-bottom:3px;">Deal Type</div>
        <select name="deal_type" style="background:#f5f1ea;border:1px solid #d6cfc3;color:#1a2332;font-size:10px;padding:3px 6px;">
          {type_opts}
        </select>
      </div>
      <div>
        <div style="font-size:9px;color:#475569;margin-bottom:3px;">Year</div>
        <div style="display:flex;gap:4px;">
          {_vi("yr_lo", yr_lo, "from")}
          {_vi("yr_hi", yr_hi, "to")}
        </div>
      </div>
      <div>
        <div style="font-size:9px;color:#475569;margin-bottom:3px;">EV ($M)</div>
        <div style="display:flex;gap:4px;">
          {_vi("ev_lo", ev_lo, "min")}
          {_vi("ev_hi", ev_hi, "max")}
        </div>
      </div>
      <div>
        <div style="font-size:9px;color:#475569;margin-bottom:3px;">MOIC</div>
        <div style="display:flex;gap:4px;">
          {_vi("moic_lo", moic_lo, "min")}
          {_vi("moic_hi", moic_hi, "max")}
        </div>
      </div>
      <div>
        <div style="font-size:9px;color:#475569;margin-bottom:3px;">Sort by</div>
        <select name="sort_by" style="background:#f5f1ea;border:1px solid #d6cfc3;color:#1a2332;font-size:10px;padding:3px 6px;">
          {"".join(_opt(k, k.replace('_',' '), sort_by) for k in ('realized_moic','ev_mm','year','hold_years','deal_name'))}
        </select>
      </div>
      <div>
        <button type="submit" class="ck-btn">Search</button>
        <a href="/deal-search" style="margin-left:8px;font-size:9.5px;color:#7a8699;">Clear</a>
      </div>
    </div>
  </form>
</div>"""

    # Results table
    rows = []
    for i, d in enumerate(page_deals):
        stripe = ' style="background:#faf7f0"' if i % 2 == 1 else ""
        moic = d.get("realized_moic")
        irr  = d.get("realized_irr")
        ev   = d.get("ev_mm")
        yr   = d.get("year") or d.get("entry_year")
        hold = d.get("hold_years")
        ebitda = d.get("ebitda_at_entry_mm") or d.get("ebitda_mm")
        ev_ebitda = d.get("ev_ebitda") or (float(ev)/float(ebitda) if ev and ebitda else None)
        try:
            moic_f = float(moic)
            mc = _moic_color(moic_f)
            moic_str = f'<span style="color:{mc};font-weight:500;">{moic_f:.2f}x</span>'
        except (TypeError, ValueError):
            moic_str = '<span style="color:#475569;">—</span>'

        def _fmt(v: Any, fmt: str) -> str:
            try:
                return fmt.format(float(v))
            except (TypeError, ValueError):
                return '<span style="color:#475569;">—</span>'

        rows.append(f"""<tr{stripe}>
  <td style="padding:4px 6px;font-size:9px;color:#7a8699;font-family:var(--ck-mono);">{_esc(d.get('source_id',''))}</td>
  <td style="padding:4px 8px;font-size:10px;max-width:240px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">
    <span title="{_esc(d.get('deal_name',''))}">{_esc((d.get('deal_name') or '')[:45])}</span>
  </td>
  <td style="padding:4px 8px;font-size:9.5px;color:#465366;max-width:140px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">{_esc((d.get('buyer') or '')[:22])}</td>
  <td style="padding:4px 8px;font-size:9.5px;color:#7a8699;">{_esc((d.get('sector') or '—')[:20])}</td>
  <td style="padding:4px 8px;font-family:var(--ck-mono);font-variant-numeric:tabular-nums;text-align:right;">{_esc(str(yr) if yr else '—')}</td>
  <td style="padding:4px 8px;font-family:var(--ck-mono);font-variant-numeric:tabular-nums;text-align:right;">{_fmt(ev, '${:.0f}M')}</td>
  <td style="padding:4px 8px;font-family:var(--ck-mono);font-variant-numeric:tabular-nums;text-align:right;">{_fmt(ev_ebitda, '{:.1f}x')}</td>
  <td style="padding:4px 8px;font-family:var(--ck-mono);font-variant-numeric:tabular-nums;text-align:right;">{_fmt(hold, '{:.1f}y')}</td>
  <td style="padding:4px 8px;font-family:var(--ck-mono);font-variant-numeric:tabular-nums;text-align:right;">{moic_str}</td>
  <td style="padding:4px 8px;font-family:var(--ck-mono);font-variant-numeric:tabular-nums;text-align:right;">{_fmt(irr, '{:.1f}%' if irr is None else '{:.1%}')}</td>
  <td style="padding:4px 8px;">{_payer_mini(d.get('payer_mix'))}</td>
  <td style="padding:4px 8px;font-size:9px;color:#7a8699;">{_esc((d.get('deal_type') or '—')[:10])}</td>
</tr>""")

    def _col_href(label: str, key: str) -> str:
        color = "#1a2332" if sort_by == key else "#7a8699"
        q_str = f"&q={_html.escape(query)}" if query else ""
        sec_str = f"&sector={_html.escape(sector)}" if sector else ""
        return (
            f'<th style="padding:5px 8px;white-space:nowrap;">'
            f'<a href="/deal-search?sort_by={key}{q_str}{sec_str}" style="color:{color};text-decoration:none;">{label}</a></th>'
        )

    table = f"""
<div class="ck-panel">
  <div class="ck-panel-title">{total:,} Results{' — ' + _esc(query) if query else ''}</div>
  <div class="ck-table-wrap" style="max-height:600px;overflow-y:auto;">
    <table class="ck-table" style="width:100%;table-layout:fixed;">
      <thead style="position:sticky;top:0;background:#ece6db;z-index:2;">
        <tr>
          <th style="padding:5px 6px;color:#7a8699;width:70px;">ID</th>
          {_col_href("Deal", "deal_name")}
          <th style="padding:5px 8px;color:#7a8699;">Buyer</th>
          <th style="padding:5px 8px;color:#7a8699;">Sector</th>
          {_col_href("Year", "year")}
          {_col_href("EV", "ev_mm")}
          <th style="padding:5px 8px;color:#7a8699;text-align:right;">EV/EBITDA</th>
          {_col_href("Hold", "hold_years")}
          {_col_href("MOIC", "realized_moic")}
          <th style="padding:5px 8px;color:#7a8699;text-align:right;">IRR</th>
          <th style="padding:5px 8px;color:#7a8699;">Payer</th>
          <th style="padding:5px 8px;color:#7a8699;">Type</th>
        </tr>
      </thead>
      <tbody>{''.join(rows) if rows else '<tr><td colspan="12" style="padding:16px;text-align:center;color:#475569;">No deals match current filters.</td></tr>'}</tbody>
    </table>
  </div>
</div>"""

    # Pagination
    page_links = ""
    if total_pages > 1:
        def _page_url(p: int) -> str:
            parts = [f"/deal-search?page={p}&sort_by={sort_by}"]
            if query: parts.append(f"q={_html.escape(query)}")
            if sector: parts.append(f"sector={_html.escape(sector)}")
            return "&".join(parts)
        link_parts = []
        for p in range(1, min(total_pages + 1, 20)):
            color = "#2fb3ad" if p == page else "#7a8699"
            link_parts.append(f'<a href="{_page_url(p)}" style="margin:0 3px;font-family:var(--ck-mono);font-size:10px;color:{color};text-decoration:none;">{p}</a>')
        if total_pages > 20:
            link_parts.append(f'<span style="color:#475569;font-size:10px;">… {total_pages}</span>')
        page_links = f'<div style="padding:8px 16px;text-align:center;">{"".join(link_parts)}</div>'

    explainer = render_page_explainer(
        what=(
            "Full-text search across the 655-deal corpus with filters "
            "on sector, vintage year range, EV range, MOIC range, "
            "payer regime, and deal type, sortable by any column."
        ),
        source="data_public/deal_search.py (corpus query engine).",
        page_key="deal-search",
    )
    body = explainer + kpis + form_html + table + page_links

    return chartis_shell(
        body,
        title="Deal Search",
        active_nav="/deal-search",
        subtitle=(
            f"{total:,} of {len(corpus):,} deals"
            + (f' matching "{query}"' if query else "")
            + (f" · sector: {sector}" if sector else "")
            + f" · sorted by {sort_by.replace('_', ' ')}"
        ),
    )
