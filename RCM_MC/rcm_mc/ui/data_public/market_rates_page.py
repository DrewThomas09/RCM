"""Market Rates page — /market-rates.

P25/P50/P75 MOIC and IRR by sector, payer mix bucket, and hold period.
Computed live from the corpus. Dense filterable table + summary stats.
"""
from __future__ import annotations

import html as _html
from typing import Any, Dict, List, Optional, Tuple


def _get_corpus() -> List[Dict[str, Any]]:
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


def _percentile(values: List[float], pct: float) -> Optional[float]:
    if not values:
        return None
    s = sorted(values)
    idx = pct * (len(s) - 1)
    lo, hi = int(idx), min(int(idx) + 1, len(s) - 1)
    return s[lo] + (idx - lo) * (s[hi] - s[lo])


def _payer_bucket(payer_mix: Any) -> str:
    """Classify payer mix into commercial-dominant / balanced / government-heavy."""
    if not payer_mix or not isinstance(payer_mix, dict):
        return "unknown"
    comm = float(payer_mix.get("commercial", 0.0))
    gov = float(payer_mix.get("medicare", 0.0)) + float(payer_mix.get("medicaid", 0.0))
    if comm >= 0.65:
        return "commercial-dominant"
    elif gov >= 0.65:
        return "government-heavy"
    else:
        return "balanced"


def _hold_bucket(hold: Any) -> str:
    if hold is None:
        return "unknown"
    try:
        h = float(hold)
        if h < 3.5:
            return "short (<3.5yr)"
        elif h < 6.0:
            return "mid (3.5-6yr)"
        else:
            return "long (>6yr)"
    except (TypeError, ValueError):
        return "unknown"


def _compute_rates(
    corpus: List[Dict[str, Any]],
    group_by: str = "sector",   # sector | payer_bucket | hold_bucket | region
    sector_filter: str = "",
    payer_filter: str = "",
    region_filter: str = "",
    min_n: int = 3,
) -> List[Dict[str, Any]]:
    """Compute P25/P50/P75 MOIC and IRR grouped by specified dimension."""
    groups: Dict[str, List[Dict[str, Any]]] = {}

    for deal in corpus:
        moic = deal.get("realized_moic")
        if moic is None:
            continue

        # Apply filters
        sector = deal.get("sector") or ""
        payer_b = _payer_bucket(deal.get("payer_mix"))
        region = deal.get("region") or ""

        if sector_filter and sector != sector_filter:
            continue
        if payer_filter and payer_b != payer_filter:
            continue
        if region_filter and region != region_filter:
            continue

        # Determine grouping key
        if group_by == "sector":
            key = sector or "Unknown"
        elif group_by == "payer_bucket":
            key = payer_b
        elif group_by == "hold_bucket":
            key = _hold_bucket(deal.get("hold_years"))
        elif group_by == "region":
            key = region or "Unknown"
        else:
            key = "All"

        groups.setdefault(key, []).append(deal)

    rows = []
    for group_name, deals in sorted(groups.items()):
        moics = sorted([float(d["realized_moic"]) for d in deals if d.get("realized_moic") is not None])
        irrs = sorted([float(d["realized_irr"]) for d in deals
                       if d.get("realized_irr") is not None])
        evs = [float(d.get("ev_mm") or d.get("entry_ev_mm") or 0) for d in deals]
        holds = [float(d["hold_years"]) for d in deals if d.get("hold_years")]

        loss_count = sum(1 for m in moics if m < 1.0)
        home_run = sum(1 for m in moics if m >= 3.0)

        if len(moics) < min_n:
            continue

        avg_ev = sum(evs) / len(evs) if evs else None
        avg_hold = sum(holds) / len(holds) if holds else None

        rows.append({
            "group":          group_name,
            "n":              len(moics),
            "moic_p25":       _percentile(moics, 0.25),
            "moic_p50":       _percentile(moics, 0.50),
            "moic_p75":       _percentile(moics, 0.75),
            "moic_min":       moics[0] if moics else None,
            "moic_max":       moics[-1] if moics else None,
            "irr_p50":        _percentile(irrs, 0.50),
            "loss_rate":      loss_count / len(moics),
            "homerun_rate":   home_run / len(moics),
            "avg_ev_mm":      avg_ev,
            "avg_hold_yr":    avg_hold,
        })

    # Sort by P50 MOIC descending
    rows.sort(key=lambda r: (r["moic_p50"] or 0), reverse=True)
    return rows


def _sparkline_svg(p25: Optional[float], p50: Optional[float], p75: Optional[float],
                   x_min: float = 0.0, x_max: float = 5.0, width: int = 90, height: int = 16) -> str:
    """Render a tiny inline SVG box plot (whisker chart)."""
    if p25 is None or p50 is None or p75 is None:
        return '<span class="faint dim">—</span>'

    def scale(v: float) -> int:
        rng = x_max - x_min
        if rng == 0:
            return width // 2
        return max(0, min(width, int((v - x_min) / rng * width)))

    x25 = scale(p25)
    x50 = scale(p50)
    x75 = scale(p75)
    mid_y = height // 2

    return (
        f'<svg width="{width}" height="{height}" style="vertical-align:middle;overflow:visible">'
        # Box (IQR)
        f'<rect x="{x25}" y="{mid_y-4}" width="{max(1,x75-x25)}" height="8" '
        f'fill="none" stroke="#2fb3ad" stroke-width="1"/>'
        # Median line
        f'<line x1="{x50}" y1="{mid_y-5}" x2="{x50}" y2="{mid_y+5}" '
        f'stroke="#0a8a5f" stroke-width="1.5"/>'
        # 1.0x breakeven marker
        f'<line x1="{scale(1.0)}" y1="{mid_y-7}" x2="{scale(1.0)}" y2="{mid_y+7}" '
        f'stroke="#b5321e" stroke-width="0.75" stroke-dasharray="2,2" opacity="0.6"/>'
        f'</svg>'
    )


def _rates_table(rows: List[Dict[str, Any]], group_label: str) -> str:
    if not rows:
        return '<div class="ck-panel" style="padding:20px;color:var(--ck-text-faint);text-align:center;">No data meets minimum sample size (n≥3).</div>'

    def fmtm(v: Optional[float]) -> str:
        if v is None:
            return '<span class="faint">—</span>'
        cls = " neg" if v < 1.0 else (" pos" if v >= 2.5 else "")
        return f'<span class="mn{cls}">{v:.2f}x</span>'

    def fmtp(v: Optional[float]) -> str:
        if v is None:
            return '<span class="faint">—</span>'
        cls = " neg" if v < 0.15 else (" pos" if v >= 0.25 else "")
        return f'<span class="mn{cls}">{v*100:.1f}%</span>'

    def fmtloss(v: Optional[float]) -> str:
        if v is None:
            return '<span class="faint">—</span>'
        cls = " neg" if v > 0.20 else (" pos" if v < 0.08 else " warn")
        return f'<span class="mn{cls}">{v*100:.1f}%</span>'

    def fmtcur(v: Optional[float]) -> str:
        if v is None:
            return '<span class="faint">—</span>'
        if v >= 1000:
            return f'<span class="mn">${v/1000:.1f}B</span>'
        return f'<span class="mn">${v:.0f}M</span>'

    header = f"""
<thead>
  <tr>
    <th style="width:200px">{_html.escape(group_label)}</th>
    <th class="num" style="width:40px">N</th>
    <th class="num" style="width:68px">P25 MOIC</th>
    <th class="num" style="width:68px">P50 MOIC</th>
    <th class="num" style="width:68px">P75 MOIC</th>
    <th style="width:100px;padding-left:8px">Distribution</th>
    <th class="num" style="width:64px">P50 IRR</th>
    <th class="num" style="width:64px">Loss Rate</th>
    <th class="num" style="width:64px">3x+ Rate</th>
    <th class="num" style="width:72px">Avg EV</th>
    <th class="num" style="width:64px">Avg Hold</th>
  </tr>
</thead>"""

    tbody_rows = []
    for i, r in enumerate(rows):
        stripe = ' style="background:#faf7f0"' if i % 2 == 0 else ""
        spark = _sparkline_svg(r["moic_p25"], r["moic_p50"], r["moic_p75"])
        tbody_rows.append(f"""
<tr{stripe}>
  <td class="dim">{_html.escape(str(r['group']))}</td>
  <td class="num mono">{r['n']}</td>
  <td class="num">{fmtm(r['moic_p25'])}</td>
  <td class="num">{fmtm(r['moic_p50'])}</td>
  <td class="num">{fmtm(r['moic_p75'])}</td>
  <td style="padding:4px 8px;">{spark}</td>
  <td class="num">{fmtp(r['irr_p50'])}</td>
  <td class="num">{fmtloss(r['loss_rate'])}</td>
  <td class="num"><span class="mn pos">{r['homerun_rate']*100:.1f}%</span></td>
  <td class="num">{fmtcur(r['avg_ev_mm'])}</td>
  <td class="num"><span class="mn">{f"{r['avg_hold_yr']:.1f}yr" if r['avg_hold_yr'] else "—"}</span></td>
</tr>""")

    return f"""
<div class="ck-panel">
  <div class="ck-panel-title">Base Rate Distribution — {_html.escape(group_label)} (P25 / P50 / P75 MOIC, min n=3)</div>
  <div class="ck-table-wrap">
    <table class="ck-table sortable">
      {header}
      <tbody>{''.join(tbody_rows)}</tbody>
    </table>
  </div>
  <div style="padding:6px 10px;font-size:9.5px;color:var(--ck-text-faint);font-family:var(--ck-mono);">
    Distribution bar: ▏P25 ◻ IQR | median ◻ P75 ▕ · red dashed line = 1.0× breakeven
  </div>
</div>"""


def render_market_rates(
    group_by: str = "sector",
    sector_filter: str = "",
    payer_filter: str = "",
    region_filter: str = "",
) -> str:
    from rcm_mc.ui._chartis_kit import (
        chartis_shell, ck_kpi_block, ck_section_header, ck_fmt_moic,
    )

    corpus = _get_corpus()
    realized = [d for d in corpus if d.get("realized_moic") is not None]
    all_moics = sorted([float(d["realized_moic"]) for d in realized])
    all_irrs = sorted([float(d["realized_irr"]) for d in realized if d.get("realized_irr")])

    corpus_p25 = _percentile(all_moics, 0.25)
    corpus_p50 = _percentile(all_moics, 0.50)
    corpus_p75 = _percentile(all_moics, 0.75)
    corpus_irr_p50 = _percentile(all_irrs, 0.50)
    loss_rate = sum(1 for m in all_moics if m < 1.0) / len(all_moics) if all_moics else 0

    kpis = (
        f'<div class="ck-kpi-grid">'
        + ck_kpi_block("Corpus N (Realized)", f'<span class="mn">{len(realized)}</span>', f"of {len(corpus)} total")
        + ck_kpi_block("P25 MOIC", ck_fmt_moic(corpus_p25), "lower quartile")
        + ck_kpi_block("P50 MOIC", ck_fmt_moic(corpus_p50), "corpus median")
        + ck_kpi_block("P75 MOIC", ck_fmt_moic(corpus_p75), "upper quartile")
        + ck_kpi_block("P50 IRR", f'<span class="mn">{corpus_irr_p50*100:.1f}%</span>' if corpus_irr_p50 else '<span class="faint">—</span>', "median realized IRR")
        + ck_kpi_block("Loss Rate", f'<span class="mn neg">{loss_rate*100:.1f}%</span>', "MOIC < 1.0×")
        + '</div>'
    )

    # Filter bar
    all_sectors = sorted({d.get("sector") for d in corpus if d.get("sector")})
    all_regions = sorted({(d.get("region") or "").split(",")[0].strip() for d in corpus if d.get("region")})
    payer_buckets = ["commercial-dominant", "balanced", "government-heavy"]
    group_options = [("sector", "Sector"), ("payer_bucket", "Payer Mix"), ("hold_bucket", "Hold Period"), ("region", "Region")]

    def _opt(val, label, selected):
        sel = ' selected' if val == selected else ''
        return f'<option value="{_html.escape(val)}"{sel}>{_html.escape(label)}</option>'

    grp_opts = "".join(_opt(v, l, group_by) for v, l in group_options)
    sec_opts = '<option value="">All Sectors</option>' + "".join(_opt(s, s, sector_filter) for s in all_sectors)
    pay_opts = '<option value="">All Payer Types</option>' + "".join(_opt(p, p.replace("-", " ").title(), payer_filter) for p in payer_buckets)
    reg_opts = '<option value="">All Regions</option>' + "".join(_opt(r, r, region_filter) for r in all_regions if r)

    filter_bar = f"""
<form method="get" action="/market-rates" class="ck-filters">
  <span class="ck-filter-label">Group By</span>
  <select name="group_by" class="ck-sel" onchange="this.form.submit()">{grp_opts}</select>
  <span class="ck-filter-label">Sector</span>
  <select name="sector" class="ck-sel" onchange="this.form.submit()">{sec_opts}</select>
  <span class="ck-filter-label">Payer</span>
  <select name="payer" class="ck-sel" onchange="this.form.submit()">{pay_opts}</select>
  <span class="ck-filter-label">Region</span>
  <select name="region" class="ck-sel" onchange="this.form.submit()">{reg_opts}</select>
</form>"""

    group_labels = {
        "sector": "Sector",
        "payer_bucket": "Payer Mix Profile",
        "hold_bucket": "Hold Period Bucket",
        "region": "Region",
    }
    group_label = group_labels.get(group_by, group_by.replace("_", " ").title())

    rates = _compute_rates(corpus, group_by, sector_filter, payer_filter, region_filter)

    active_filters = []
    if sector_filter:
        active_filters.append(f"sector={sector_filter}")
    if payer_filter:
        active_filters.append(f"payer={payer_filter}")
    if region_filter:
        active_filters.append(f"region={region_filter}")
    filter_desc = " · ".join(active_filters) if active_filters else "all corpus"

    body = (
        kpis
        + filter_bar
        + ck_section_header(f"BASE RATES BY {group_label.upper()}", filter_desc, len(rates))
        + _rates_table(rates, group_label)
    )

    return chartis_shell(
        body,
        title="Market Rates",
        active_nav="/market-rates",
        subtitle=f"P25/P50/P75 MOIC and IRR · {len(realized)} realized deals · grouped by {group_label.lower()}",
    )
