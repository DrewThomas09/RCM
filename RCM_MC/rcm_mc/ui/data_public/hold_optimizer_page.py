"""Hold Period Optimizer page — /hold-optimizer.

Given entry profile (sector, EV, EV/EBITDA, commercial payer %),
recommends optimal hold period from corpus peer data with
P25/P50/P75 MOIC confidence intervals per hold bucket.
"""
from __future__ import annotations

import html as _html
from typing import Any, Dict, List, Optional

from rcm_mc.ui._chartis_kit import (
    P, chartis_shell, ck_section_header, ck_kpi_block,
    ck_fmt_moic, ck_fmt_num,
)


def _bucket_bar_svg(
    buckets: List[Any],
    width: int = 640,
    height: int = 220,
) -> str:
    """Horizontal grouped bar chart: P25–P75 band + P50 tick per hold bucket."""
    if not buckets:
        return ""
    ml, mr, mt, mb = 70, 20, 10, 30
    W = width - ml - mr
    H = height - mt - mb

    valid = [b for b in buckets if b.moic_p50 is not None]
    if not valid:
        return ""

    all_p75 = [b.moic_p75 or b.moic_p50 for b in valid]
    max_v = max(max(all_p75), 4.0) * 1.1
    bar_h = max(14, H // len(buckets) - 4)
    row_h = H // len(buckets)

    def px(v: float) -> int:
        return int(ml + v / max_v * W)

    def py(i: int) -> int:
        return mt + i * row_h + (row_h - bar_h) // 2

    lines = [
        f'<svg viewBox="0 0 {width} {height}" width="{width}" height="{height}" '
        f'xmlns="http://www.w3.org/2000/svg" style="display:block">'
    ]
    # Grid lines at 1, 2, 3, 4
    for gv in [1.0, 2.0, 3.0, 4.0]:
        x = px(gv)
        lines.append(
            f'<line x1="{x}" y1="{mt}" x2="{x}" y2="{mt + H}" '
            f'stroke="{P["border"]}" stroke-width="1"/>'
        )
        lines.append(
            f'<text x="{x}" y="{mt + H + 14}" text-anchor="middle" '
            f'font-size="9" fill="{P["text_faint"]}" '
            f'font-family=\'JetBrains Mono,monospace\'>{gv:.0f}×</text>'
        )

    for i, b in enumerate(buckets):
        y = py(i)
        cx = b.moic_p50 or 0
        is_opt = getattr(b, "is_optimal", False)
        bar_color = P["positive"] if is_opt else P["accent"]
        band_color = "#1e3a5f" if is_opt else "#1a2744"
        label_color = P["text"] if is_opt else P["text_dim"]

        # P25–P75 band
        if b.moic_p25 is not None and b.moic_p75 is not None:
            bx = px(b.moic_p25)
            bw = max(2, px(b.moic_p75) - bx)
            lines.append(
                f'<rect x="{bx}" y="{y}" width="{bw}" height="{bar_h}" '
                f'fill="{band_color}" rx="2"/>'
            )
        # P50 tick
        if b.moic_p50 is not None:
            tx = px(b.moic_p50)
            lines.append(
                f'<rect x="{tx - 1}" y="{y}" width="3" height="{bar_h}" '
                f'fill="{bar_color}"/>'
            )
            lines.append(
                f'<text x="{tx + 6}" y="{y + bar_h // 2 + 4}" '
                f'font-size="9" fill="{bar_color}" '
                f'font-family=\'JetBrains Mono,monospace\' font-variant-numeric="tabular-nums">'
                f'{b.moic_p50:.2f}×</text>'
            )

        # Row label
        opt_marker = " ✓" if is_opt else ""
        lines.append(
            f'<text x="{ml - 4}" y="{y + bar_h // 2 + 4}" '
            f'text-anchor="end" font-size="10" fill="{label_color}" '
            f'font-family=\'Inter,sans-serif\'>{_html.escape(b.label)}{opt_marker}</text>'
        )
        # n label
        lines.append(
            f'<text x="{width - mr}" y="{y + bar_h // 2 + 4}" '
            f'text-anchor="end" font-size="9" fill="{P["text_faint"]}" '
            f'font-family=\'JetBrains Mono,monospace\'>n={b.n}</text>'
        )

        # Stripe for optimal row
        if is_opt:
            lines.append(
                f'<rect x="0" y="{y - 2}" width="{width}" height="{bar_h + 4}" '
                f'fill="{P["positive"]}" opacity="0.04" rx="2"/>'
            )

    lines.append("</svg>")
    return "\n".join(lines)


def _loss_color(v: float) -> str:
    if v >= 0.25:
        return P["critical"]
    if v >= 0.10:
        return P["warning"]
    return P["positive"]


def _moic_color(v: Optional[float]) -> str:
    if v is None:
        return P["text_faint"]
    if v >= 3.0:
        return P["positive"]
    if v >= 2.0:
        return P["text"]
    if v >= 1.5:
        return P["warning"]
    return P["negative"]


def _bucket_table(buckets: List[Any]) -> str:
    rows = []
    for b in buckets:
        opt_cls = ' class="opt-row"' if b.is_optimal else ""
        p50_html = (
            f'<span class="mn" style="color:{_moic_color(b.moic_p50)}">'
            f'{b.moic_p50:.2f}×</span>'
            if b.moic_p50 else '<span class="faint">—</span>'
        )
        p25_html = (
            f'<span class="mn" style="color:{P["text_dim"]}">{b.moic_p25:.2f}×</span>'
            if b.moic_p25 else '<span class="faint">—</span>'
        )
        p75_html = (
            f'<span class="mn" style="color:{P["text_dim"]}">{b.moic_p75:.2f}×</span>'
            if b.moic_p75 else '<span class="faint">—</span>'
        )
        irr_html = (
            f'<span class="mn">{b.irr_p50 * 100:.1f}%</span>'
            if b.irr_p50 else '<span class="faint">—</span>'
        )
        loss_html = (
            f'<span class="mn" style="color:{_loss_color(b.loss_rate)}">'
            f'{b.loss_rate * 100:.1f}%</span>'
        )
        hr_html = (
            f'<span class="mn" style="color:{P["positive"]}">'
            f'{b.home_run_rate * 100:.1f}%</span>'
        )
        opt_badge = (
            '<span class="badge-opt">OPTIMAL</span>' if b.is_optimal else ""
        )
        rows.append(
            f"<tr{opt_cls}>"
            f"<td>{_html.escape(b.label)} {opt_badge}</td>"
            f"<td class='r mn'>{b.n}</td>"
            f"<td class='r'>{p25_html}</td>"
            f"<td class='r'>{p50_html}</td>"
            f"<td class='r'>{p75_html}</td>"
            f"<td class='r'>{irr_html}</td>"
            f"<td class='r'>{loss_html}</td>"
            f"<td class='r'>{hr_html}</td>"
            f"</tr>"
        )
    return (
        '<table class="ck-table">'
        "<thead><tr>"
        "<th>Hold Bucket</th><th class='r'>N</th>"
        "<th class='r'>P25 MOIC</th><th class='r'>P50 MOIC</th>"
        "<th class='r'>P75 MOIC</th><th class='r'>P50 IRR</th>"
        "<th class='r'>Loss Rate</th><th class='r'>Home Run</th>"
        "</tr></thead>"
        "<tbody>" + "".join(rows) + "</tbody>"
        "</table>"
    )


def _peer_table(peers: List[Dict[str, Any]], top: int = 15) -> str:
    rows = []
    for d in peers[:top]:
        m = None
        for k in ("moic", "realized_moic"):
            v = d.get(k)
            if v is not None:
                try:
                    m = float(v)
                    break
                except (TypeError, ValueError):
                    pass
        h = d.get("hold_years")
        ev = d.get("ev_mm")
        ee = None
        if ev and d.get("ebitda_at_entry_mm") and float(d.get("ebitda_at_entry_mm", 0)) > 0:
            ee = float(ev) / float(d["ebitda_at_entry_mm"])
        name = _html.escape(d.get("company_name") or d.get("deal_name") or "—")
        sector = _html.escape(d.get("sector") or "—")
        buyer = _html.escape((d.get("buyer") or "—")[:30])
        moic_html = (
            f'<span class="mn" style="color:{_moic_color(m)}">{m:.2f}×</span>'
            if m else '<span class="faint">—</span>'
        )
        rows.append(
            f"<tr>"
            f"<td>{name}</td>"
            f"<td>{sector}</td>"
            f"<td>{buyer}</td>"
            f"<td class='r mn'>{d.get('year', '—')}</td>"
            f"<td class='r mn'>{f'${float(ev):.0f}M' if ev else '—'}</td>"
            f"<td class='r mn'>{f'{ee:.1f}×' if ee else '—'}</td>"
            f"<td class='r mn'>{f'{float(h):.1f}yr' if h else '—'}</td>"
            f"<td class='r'>{moic_html}</td>"
            f"</tr>"
        )
    if not rows:
        return '<p class="ck-empty">No peer deals matched the input profile.</p>'
    return (
        '<table class="ck-table">'
        "<thead><tr>"
        "<th>Company</th><th>Sector</th><th>Sponsor</th>"
        "<th class='r'>Yr</th><th class='r'>EV</th>"
        "<th class='r'>EV/EBITDA</th><th class='r'>Hold</th>"
        "<th class='r'>MOIC</th>"
        "</tr></thead>"
        "<tbody>" + "".join(rows) + "</tbody>"
        "</table>"
    )


def _input_form(params: Dict[str, str]) -> str:
    sector = _html.escape(params.get("sector", ""))
    ev_mm = params.get("ev_mm", "")
    ev_ebitda = params.get("ev_ebitda", "")
    comm_pct = params.get("comm_pct", "")
    return f"""
<form method="get" action="/hold-optimizer" class="ck-form">
  <div class="ck-form-row">
    <div class="ck-form-group">
      <label class="ck-label">Sector</label>
      <input type="text" name="sector" class="ck-input" placeholder="e.g. Behavioral Health"
        value="{sector}">
    </div>
    <div class="ck-form-group">
      <label class="ck-label">Entry EV ($M)</label>
      <input type="number" name="ev_mm" class="ck-input" placeholder="e.g. 300"
        value="{_html.escape(ev_mm)}" step="10" min="10" max="10000">
    </div>
    <div class="ck-form-group">
      <label class="ck-label">Entry EV/EBITDA (×)</label>
      <input type="number" name="ev_ebitda" class="ck-input" placeholder="e.g. 12"
        value="{_html.escape(ev_ebitda)}" step="0.5" min="4" max="30">
    </div>
    <div class="ck-form-group">
      <label class="ck-label">Commercial Payer % (0–1)</label>
      <input type="number" name="comm_pct" class="ck-input" placeholder="e.g. 0.65"
        value="{_html.escape(comm_pct)}" step="0.05" min="0" max="1">
    </div>
    <div class="ck-form-group" style="align-self:flex-end">
      <button type="submit" class="ck-btn">Optimize</button>
    </div>
  </div>
</form>"""


def render_hold_optimizer(params: Dict[str, str]) -> str:
    from rcm_mc.data_public.hold_optimizer import compute_hold_optimizer

    sector = params.get("sector", "")
    ev_mm: Optional[float] = None
    ev_ebitda: Optional[float] = None
    comm_pct: Optional[float] = None

    try:
        if params.get("ev_mm"):
            ev_mm = float(params["ev_mm"])
    except (TypeError, ValueError):
        pass
    try:
        if params.get("ev_ebitda"):
            ev_ebitda = float(params["ev_ebitda"])
    except (TypeError, ValueError):
        pass
    try:
        if params.get("comm_pct"):
            comm_pct = float(params["comm_pct"])
    except (TypeError, ValueError):
        pass

    result = compute_hold_optimizer(
        sector=sector,
        ev_mm=ev_mm,
        ev_ebitda_entry=ev_ebitda,
        comm_pct=comm_pct,
    )

    # KPI strip
    kpi_grid = (
        '<div class="ck-kpi-grid">'
        + ck_kpi_block(
            "Peer Deals Found",
            f'<span class="mn">{result.n_peers}</span>',
            f"of {result.corpus_n} total",
        )
        + ck_kpi_block(
            "Corpus P50 MOIC",
            ck_fmt_moic(result.corpus_p50),
            "all realized deals",
        )
        + ck_kpi_block(
            "Optimal Hold",
            f'<span class="mn pos">{_html.escape(result.optimal_bucket or "—")}</span>',
            "highest P50 MOIC bucket (n≥5)",
        )
        + ck_kpi_block(
            "Optimal P50 MOIC",
            ck_fmt_moic(result.optimal_moic_p50),
            "peer-calibrated",
        )
        + "</div>"
    )

    # No-results message
    if result.n_peers == 0:
        body = (
            _input_form(params)
            + kpi_grid
            + '<p class="ck-empty" style="margin-top:32px">No peer deals matched — try broadening the filters.</p>'
        )
    else:
        chart = _bucket_bar_svg(result.buckets)
        table = _bucket_table(result.buckets)
        peers = _peer_table(result.peer_deals)

        body = f"""
{_input_form(params)}
{kpi_grid}
{ck_section_header("Hold Period vs. MOIC", f"P25/P50/P75 across {result.n_peers} peer deals")}
<div style="overflow-x:auto;margin-bottom:24px">{chart}</div>
{ck_section_header("Bucket Statistics")}
<div style="overflow-x:auto;margin-bottom:24px">{table}</div>
{ck_section_header("Top Peer Deals", "Similarity-ranked, top 15 shown")}
<div style="overflow-x:auto">{peers}</div>
"""

    extra_css = """
.ck-form { margin-bottom: 24px; }
.ck-form-row { display:flex; flex-wrap:wrap; gap:12px; align-items:flex-start; }
.ck-form-group { display:flex; flex-direction:column; gap:4px; }
.ck-label { font-size:11px; color:var(--ck-text-dim); text-transform:uppercase; letter-spacing:.06em; }
.ck-input {
  background:var(--ck-panel-alt); border:1px solid var(--ck-border);
  color:var(--ck-text); padding:6px 10px; font-size:12px;
  font-family:'JetBrains Mono',monospace; border-radius:3px; width:180px;
}
.ck-input:focus { outline:1px solid var(--ck-accent); }
.ck-btn {
  background:var(--ck-accent); color:#fff; border:none; padding:7px 18px;
  font-size:12px; border-radius:3px; cursor:pointer; letter-spacing:.04em;
}
.ck-btn:hover { filter:brightness(1.15); }
.opt-row { background:rgba(16,185,129,.06); }
.badge-opt {
  display:inline-block; background:var(--ck-positive); color:#000;
  font-size:9px; padding:1px 5px; border-radius:2px; letter-spacing:.06em;
  vertical-align:middle; margin-left:6px; font-weight:700;
}
"""

    return chartis_shell(
        body=body,
        title="Hold Period Optimizer",
        active_nav="/hold-optimizer",
        subtitle="Corpus-calibrated optimal hold period from peer deal distribution",
        extra_css=extra_css,
    )
