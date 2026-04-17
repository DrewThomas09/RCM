"""Sponsor League Table page — /sponsor-league.

Ranks all healthcare PE sponsors by realized returns across 635+ corpus
deals. Shows P50 MOIC, loss rate, homerun rate, consistency score, sector
concentration, and active deal count.
"""
from __future__ import annotations

import html as _html
import importlib
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


def _moic_color(v: Optional[float]) -> str:
    if v is None:
        return "var(--ck-text-faint)"
    if v < 1.0:
        return "#ef4444"
    if v >= 2.5:
        return "#22c55e"
    if v >= 1.5:
        return "#e2e8f0"
    return "#f59e0b"


def _loss_color(v: float) -> str:
    if v >= 0.30:
        return "#ef4444"
    if v >= 0.15:
        return "#f59e0b"
    return "#22c55e"


def _consistency_bar(score: float, width: int = 60) -> str:
    """Inline SVG consistency score bar."""
    filled = int(score / 100 * width)
    bar_color = "#22c55e" if score >= 70 else ("#f59e0b" if score >= 45 else "#ef4444")
    return (
        f'<svg width="{width}" height="8" xmlns="http://www.w3.org/2000/svg" style="display:inline-block;vertical-align:middle;">'
        f'<rect x="0" y="1" width="{width}" height="6" rx="1" fill="#1e293b"/>'
        f'<rect x="0" y="1" width="{filled}" height="6" rx="1" fill="{bar_color}"/>'
        f'</svg>'
        f'<span style="font-family:var(--ck-mono);font-variant-numeric:tabular-nums;'
        f'font-size:9.5px;color:{bar_color};margin-left:4px;">{score:.0f}</span>'
    )


def _fmt_moic(v: Optional[float]) -> str:
    if v is None:
        return '<span style="color:var(--ck-text-faint)">—</span>'
    color = _moic_color(v)
    return (
        f'<span style="font-family:var(--ck-mono);font-variant-numeric:tabular-nums;'
        f'color:{color};font-weight:{"600" if v >= 2.5 or v < 1.0 else "400"}">'
        f'{v:.2f}×</span>'
    )


def _fmt_pct(v: float, color: Optional[str] = None) -> str:
    c = color or "var(--ck-text-dim)"
    return (
        f'<span style="font-family:var(--ck-mono);font-variant-numeric:tabular-nums;color:{c}">'
        f'{v*100:.1f}%</span>'
    )


def _fmt_ev(v: Optional[float]) -> str:
    if v is None:
        return '<span style="color:var(--ck-text-faint)">—</span>'
    if v >= 1000:
        return f'<span style="font-family:var(--ck-mono);font-variant-numeric:tabular-nums">${v/1000:.1f}B</span>'
    return f'<span style="font-family:var(--ck-mono);font-variant-numeric:tabular-nums">${v:.0f}M</span>'


def _sector_pills(sectors: List[str]) -> str:
    pills = []
    for s in sectors[:3]:
        pills.append(
            f'<span style="display:inline-block;background:#0f172a;border:1px solid #1e293b;'
            f'border-radius:2px;padding:1px 5px;font-size:8.5px;color:#64748b;margin:1px;">'
            f'{_html.escape(s[:20])}</span>'
        )
    if len(sectors) > 3:
        pills.append(
            f'<span style="font-size:8.5px;color:#475569">+{len(sectors)-3}</span>'
        )
    return "".join(pills)


def _sparkline_moics(moics: List[float], width: int = 60, height: int = 14) -> str:
    """Mini inline SVG sparkline of sorted MOIC distribution."""
    if not moics:
        return ""
    s = sorted(moics)
    lo, hi = 0.0, max(5.0, max(s))
    pts = []
    for i, m in enumerate(s):
        x = int(i / max(len(s) - 1, 1) * width)
        y = height - int((m - lo) / (hi - lo) * height)
        pts.append(f"{x},{max(0,y)}")
    polyline = " ".join(pts)
    breakeven_y = height - int((1.0 - lo) / (hi - lo) * height)
    return (
        f'<svg width="{width}" height="{height}" xmlns="http://www.w3.org/2000/svg" '
        f'style="display:inline-block;vertical-align:middle;">'
        f'<line x1="0" y1="{breakeven_y}" x2="{width}" y2="{breakeven_y}" '
        f'stroke="#ef4444" stroke-width="0.8" stroke-dasharray="2,2" opacity="0.5"/>'
        f'<polyline points="{polyline}" fill="none" stroke="#3b82f6" stroke-width="1.2" opacity="0.8"/>'
        f'</svg>'
    )


def _build_table(records: List[Any]) -> str:
    """Build the sponsor league table HTML."""
    from rcm_mc.data_public.sponsor_track_record import build_sponsor_records
    import importlib

    corps = _load_corpus()
    # Map sponsor → list of realized moics for sparkline
    records_dict = {r.sponsor: r for r in records}

    headers = [
        ("Sponsor", "left", "220px"),
        ("Deals", "right", "52px"),
        ("Realized", "right", "62px"),
        ("P25 MOIC", "right", "76px"),
        ("P50 MOIC", "right", "76px"),
        ("P75 MOIC", "right", "76px"),
        ("Distribution", "center", "68px"),
        ("Loss%", "right", "60px"),
        ("3×+%", "right", "60px"),
        ("Consistency", "center", "90px"),
        ("Avg EV", "right", "72px"),
        ("Sectors", "left", ""),
    ]

    thead_cells = "".join(
        f'<th style="text-align:{align};{"width:"+w+";" if w else ""}">{h}</th>'
        for h, align, w in headers
    )

    rows_html = []
    for i, rec in enumerate(records):
        stripe = ' style="background:#0f172a"' if i % 2 == 1 else ""

        # Get realized moics for sparkline
        moics = sorted([
            float(d["realized_moic"]) for d in corps
            if d.get("realized_moic") is not None
            and any(
                s.lower() in (d.get("buyer") or "").lower()
                for s in [rec.sponsor.split()[0].lower()]
            )
        ])
        spark = _sparkline_moics(moics) if moics else ""

        rows_html.append(f"""
<tr{stripe}>
  <td style="padding:7px 8px;font-size:11px;color:var(--ck-text);">{_html.escape(rec.sponsor)}</td>
  <td class="mono" style="text-align:right;padding:7px 6px;">{rec.deal_count}</td>
  <td class="mono dim" style="text-align:right;padding:7px 6px;">{rec.realized_count}</td>
  <td style="text-align:right;padding:7px 6px;">{_fmt_moic(rec.moic_p25)}</td>
  <td style="text-align:right;padding:7px 6px;">{_fmt_moic(rec.median_moic)}</td>
  <td style="text-align:right;padding:7px 6px;">{_fmt_moic(rec.moic_p75)}</td>
  <td style="text-align:center;padding:7px 6px;">{spark}</td>
  <td style="text-align:right;padding:7px 6px;">{_fmt_pct(rec.loss_rate, _loss_color(rec.loss_rate))}</td>
  <td style="text-align:right;padding:7px 6px;">{_fmt_pct(rec.home_run_rate, "#22c55e" if rec.home_run_rate >= 0.30 else None)}</td>
  <td style="text-align:center;padding:7px 6px;">{_consistency_bar(rec.consistency_score)}</td>
  <td style="text-align:right;padding:7px 6px;">{_fmt_ev(rec.avg_ev_mm)}</td>
  <td style="padding:7px 6px;">{_sector_pills(rec.sectors)}</td>
</tr>""")

    return f"""
<div class="ck-panel">
  <div class="ck-panel-title">Sponsor League Table — Healthcare PE (≥3 corpus deals)</div>
  <div class="ck-table-wrap">
    <table class="ck-table" style="table-layout:fixed;">
      <colgroup>
        <col style="width:220px"><col style="width:52px"><col style="width:62px">
        <col style="width:76px"><col style="width:76px"><col style="width:76px">
        <col style="width:68px"><col style="width:60px"><col style="width:60px">
        <col style="width:90px"><col style="width:72px"><col>
      </colgroup>
      <thead><tr>{thead_cells}</tr></thead>
      <tbody>{''.join(rows_html)}</tbody>
    </table>
  </div>
</div>"""


def _kpi_bar(records: List[Any]) -> str:
    from rcm_mc.ui._chartis_kit import ck_kpi_block
    corpus = _load_corpus()
    total_sponsors = len(records)
    top_moic = records[0].median_moic if records else None
    loss_free = sum(1 for r in records if r.loss_rate == 0.0)
    avg_consistency = sum(r.consistency_score for r in records) / len(records) if records else 0

    best_html = (
        f'<span class="mn" style="color:#22c55e">{top_moic:.2f}×</span>'
        if top_moic else '<span class="faint">—</span>'
    )
    return (
        '<div class="ck-kpi-grid">'
        + ck_kpi_block("Sponsors Ranked", f'<span class="mn">{total_sponsors}</span>', "≥3 deals in corpus")
        + ck_kpi_block("Best P50 MOIC", best_html, records[0].sponsor[:20] if records else "")
        + ck_kpi_block("Zero-Loss Sponsors", f'<span class="mn pos">{loss_free}</span>', "no impairments in corpus")
        + ck_kpi_block("Avg Consistency", f'<span class="mn">{avg_consistency:.0f}</span>', "score out of 100")
        + ck_kpi_block("Corpus Deals", f'<span class="mn">{len(corpus)}</span>', "total across all sponsors")
        + '</div>'
    )


def _methodology_panel() -> str:
    return """
<div class="ck-panel">
  <div class="ck-panel-title">Methodology</div>
  <div style="padding:12px 16px;color:var(--ck-text-dim);font-size:10.5px;line-height:1.7;">
    <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:12px;">
      <div>
        <div style="font-family:var(--ck-mono);font-size:9px;letter-spacing:0.12em;
                    text-transform:uppercase;color:var(--ck-text-faint);margin-bottom:5px;">Consistency Score</div>
        <div>Composite 0-100. Rewards: high deal count, low loss rate, tight IQR (low variance),
        sector specialization, and median MOIC ≥ 2.0×. Penalizes: high standard deviation,
        SPAC/distressed exits, short tenures.</div>
      </div>
      <div>
        <div style="font-family:var(--ck-mono);font-size:9px;letter-spacing:0.12em;
                    text-transform:uppercase;color:var(--ck-text-faint);margin-bottom:5px;">Deal Attribution</div>
        <div>Sponsor assigned from buyer field. Multi-sponsor deals (JV, co-invest) count for each
        named firm. Name normalization maps ~80 alias forms to canonical names. Deals with
        &lt;3 sponsor-attributed outcomes excluded from ranking.</div>
      </div>
      <div>
        <div style="font-family:var(--ck-mono);font-size:9px;letter-spacing:0.12em;
                    text-transform:uppercase;color:var(--ck-text-faint);margin-bottom:5px;">Caveats</div>
        <div>Corpus covers announced healthcare PE transactions — survivorship bias exists.
        Unrealized deals excluded from MOIC statistics. IRR distorted by partial-period holds.
        Large sponsors may show lower P50 because they absorb more difficult sectors.</div>
      </div>
    </div>
  </div>
</div>"""


def render_sponsor_league(
    min_deals: int = 3,
    sort_by: str = "median_moic",
    sector_filter: str = "",
) -> str:
    from rcm_mc.ui._chartis_kit import chartis_shell, ck_section_header
    from rcm_mc.data_public.sponsor_track_record import sponsor_league_table

    corpus = _load_corpus()
    records = sponsor_league_table(corpus, min_deals=min_deals)

    # Sort options
    sort_map = {
        "median_moic": lambda r: (r.median_moic is None, -(r.median_moic or 0)),
        "deal_count": lambda r: -r.deal_count,
        "consistency": lambda r: -r.consistency_score,
        "loss_rate": lambda r: r.loss_rate,
        "home_run": lambda r: -r.home_run_rate,
    }
    sk = sort_map.get(sort_by, sort_map["median_moic"])
    records.sort(key=sk)

    # Sort control form
    sort_opts = "".join(
        f'<option value="{v}" {"selected" if v==sort_by else ""}>{lbl}</option>'
        for v, lbl in [
            ("median_moic", "Sort: P50 MOIC ↓"),
            ("deal_count", "Sort: Deal Count ↓"),
            ("consistency", "Sort: Consistency ↓"),
            ("loss_rate", "Sort: Loss Rate ↑"),
            ("home_run", "Sort: Homerun Rate ↓"),
        ]
    )
    min_opts = "".join(
        f'<option value="{v}" {"selected" if v==min_deals else ""}>{v}+ deals</option>'
        for v in [2, 3, 5, 8, 10]
    )

    controls = f"""
<form method="get" action="/sponsor-league" class="ck-filters" style="margin-bottom:10px;">
  <select name="sort_by" class="ck-sel" onchange="this.form.submit()">{sort_opts}</select>
  <span class="ck-filter-label">Min Deals</span>
  <select name="min_deals" class="ck-sel" onchange="this.form.submit()">{min_opts}</select>
  <span class="ck-filter-label">Search</span>
  <input type="text" name="q" placeholder="sponsor name..." class="ck-input" data-search-target="#sponsor-tbl">
</form>"""

    kpis = _kpi_bar(records)
    section = ck_section_header("SPONSOR LEAGUE TABLE", "healthcare PE returns by firm", len(records))
    table = _build_table(records)
    meth = _methodology_panel()

    body = kpis + controls + section + table + meth

    return chartis_shell(
        body,
        title="Sponsor League Table",
        active_nav="/sponsor-league",
        subtitle=f"{len(records)} sponsors ranked · ≥{min_deals} corpus deals · sorted by {sort_by}",
    )
