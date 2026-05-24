"""Portfolio Analytics — /portfolio-analytics.

Combines ``data_public/portfolio_analytics.py`` (corpus scorecard,
vintage cohorts, deals-by-sponsor / type, return distribution,
outlier detection, payer-mix sensitivity) with
``data_public/market_concentration.py`` (concentration table, state
growth / volatility summaries, provider geo dependency).

Portfolio-scope views rather than per-deal: concentration risk
across the corpus, vintage mix, pacing, cross-holding synergy hints.
"""
from __future__ import annotations

import html as _html
from typing import Any, Dict, List, Optional

from .._chartis_kit import (
    P,
    chartis_shell,
    ck_bar_row,
    ck_data_universe,
    ck_kpi_block,
    ck_page_title,
    ck_section_header,
)
from ._helpers import (
    empty_note,
    fmt_multiple,
    fmt_pct,
    load_corpus_deals,
    small_panel,
    verdict_badge,
)
from ._sanity import render_number


def _fmt_ev_mm(v: Any) -> str:
    try:
        f = float(v)
        if abs(f) >= 1000:
            return f"${f/1000:.2f}B"
        return f"${f:,.0f}M"
    except (TypeError, ValueError):
        return "—"


def _scorecard_panel(sc: Dict[str, Any]) -> str:
    rows = [
        ("Total Deals", str(sc.get("total_deals", 0))),
        ("Realized", str(sc.get("realized_deals", 0))),
        ("Total EV", _fmt_ev_mm(sc.get("total_ev_mm"))),
        ("Median EV", _fmt_ev_mm(sc.get("median_ev_mm"))),
        ("MOIC P25 / P50 / P75",
         f"{render_number(sc.get('moic_p25'), 'moic')} · "
         f"{render_number(sc.get('moic_p50'), 'moic')} · "
         f"{render_number(sc.get('moic_p75'), 'moic')}"),
        ("MOIC Mean", render_number(sc.get("moic_mean"), "moic")),
        ("IRR P25 / P50 / P75",
         f"{render_number(sc.get('irr_p25'), 'irr')} · "
         f"{render_number(sc.get('irr_p50'), 'irr')} · "
         f"{render_number(sc.get('irr_p75'), 'irr')}"),
        ("Loss Rate", render_number(sc.get("loss_rate"), "loss_rate")),
        ("Home-Run Rate", render_number(sc.get("home_run_rate"), "home_run_rate")),
        ("Outliers (z≥2)", str(sc.get("outlier_count", 0))),
        ("Vintage Years", str(sc.get("vintage_years", 0))),
    ]
    items = []
    for k, v in rows:
        items.append(
            f'<div style="display:flex;gap:14px;padding:5px 0;'
            f'border-bottom:1px solid {P["border_dim"]};font-size:11.5px;">'
            f'<span style="color:{P["text_faint"]};font-family:var(--ck-mono);'
            f'font-size:10px;letter-spacing:0.08em;width:200px;flex-shrink:0;">'
            f'{_html.escape(k)}</span>'
            f'<span style="color:{P["text"]};font-family:var(--ck-mono);'
            f'font-variant-numeric:tabular-nums;">{v}</span>'
            f'</div>'
        )
    return "".join(items) or empty_note("No scorecard fields.")


_VINTAGE_METRICS = {
    # key: (field, axis label, value formatter, single-bar color or None=band)
    "moic": ("median_moic", "Median MOIC", lambda v: f"{v:.1f}x", None),
    "count": ("count", "Deal count", lambda v: f"{int(v)}", "#155752"),
    "ev": ("total_ev_mm", "Total EV ($M)", lambda v: f"${v:,.0f}M", "#0b2341"),
}


def _vintage_chart(cohorts: List[Dict[str, Any]], metric: str = "moic") -> str:
    """SVG bar chart of a vintage-cohort metric by year.

    ``metric`` ∈ {moic, count, ev} — drives the field, axis label, value
    format, and color (MOIC keeps the green/amber/red performance bands; the
    others use a single editorial fill). Skips entries with no value for the
    chosen metric (e.g. still-unrealized cohorts have no median MOIC).
    """
    field, axis_label_txt, fmt, fixed_color = _VINTAGE_METRICS.get(
        metric, _VINTAGE_METRICS["moic"])
    plotted = [
        c for c in cohorts
        if c.get(field) is not None and isinstance(c.get("year"), (int, str))
    ]
    if not plotted:
        return f'<p class="ck-pa-explainer" style="margin:8px 0;">No vintage data for {_html.escape(axis_label_txt.lower())}.</p>'
    plotted = sorted(plotted, key=lambda c: str(c.get("year", "")))
    width, height = 720, 220
    pad_l, pad_r, pad_t, pad_b = 56, 16, 28, 32
    inner_w = width - pad_l - pad_r
    inner_h = height - pad_t - pad_b
    n = len(plotted)
    bar_w = max(8.0, inner_w / max(n, 1) * 0.7)
    gap = inner_w / max(n, 1) - bar_w
    obs_max = max((float(c.get(field) or 0) for c in plotted), default=1.0)
    y_max = max(3.0, obs_max + 0.5) if metric == "moic" else max(obs_max * 1.15, 1.0)

    def sy(v: float) -> float:
        return pad_t + inner_h - (v / y_max) * inner_h

    grid_vals = ([0.0, 1.0, 2.0, 3.0] if metric == "moic"
                 else [y_max * f for f in (0, 0.25, 0.5, 0.75, 1.0)])
    grid_lines = []
    for v in grid_vals:
        if v > y_max:
            continue
        y = sy(v)
        glabel = f"{v:.1f}x" if metric == "moic" else fmt(v)
        grid_lines.append(
            f'<line x1="{pad_l}" x2="{pad_l + inner_w}" y1="{y:.1f}" y2="{y:.1f}" '
            f'stroke="#d6cfc0" stroke-dasharray="2,4" />'
            f'<text x="{pad_l - 6}" y="{y + 3:.1f}" fill="#7a8699" '
            f'text-anchor="end" font-size="10" '
            f'font-family="JetBrains Mono, monospace">{glabel}</text>'
        )
    bars, labels = [], []
    for i, c in enumerate(plotted):
        val = float(c.get(field) or 0)
        if fixed_color:
            color = fixed_color
        else:
            color = ("#0a8a5f" if val >= 2.5 else "#b8732a" if val >= 1.5 else "#b5321e")
        x = pad_l + i * (bar_w + gap) + gap / 2
        y_top = sy(val)
        bar_h = pad_t + inner_h - y_top
        bars.append(
            f'<rect x="{x:.1f}" y="{y_top:.1f}" width="{bar_w:.1f}" '
            f'height="{max(bar_h,0):.1f}" fill="{color}" fill-opacity="0.85" '
            f'stroke="{color}" stroke-width="0.5">'
            f'<title>Vintage {c.get("year")}: {axis_label_txt} {fmt(val)} · '
            f'{c.get("count", 0)} deals · {c.get("realized_count", 0)} realized</title>'
            f'</rect>'
        )
        labels.append(
            f'<text x="{x + bar_w/2:.1f}" y="{height - pad_b + 14}" '
            f'fill="#1a2332" text-anchor="middle" font-size="10" '
            f'font-family="JetBrains Mono, monospace">{c.get("year")}</text>'
        )
        labels.append(
            f'<text x="{x + bar_w/2:.1f}" y="{y_top - 4:.1f}" fill="{color}" '
            f'text-anchor="middle" font-size="10" '
            f'font-family="JetBrains Mono, monospace" font-weight="600">{fmt(val)}</text>'
        )
    axis_label = (
        f'<text x="14" y="{pad_t + inner_h/2:.1f}" fill="#1a2332" '
        f'text-anchor="middle" font-size="11" font-family="Inter, sans-serif" '
        f'font-weight="600" transform="rotate(-90 14 {pad_t + inner_h/2:.1f})">'
        f'{_html.escape(axis_label_txt)}</text>'
    )
    return (
        f'<svg viewBox="0 0 {width} {height}" width="100%" '
        f'style="max-width:{width}px;background:transparent;margin:8px 0 16px;">'
        f'{"".join(grid_lines)}{"".join(bars)}{"".join(labels)}{axis_label}</svg>'
    )


def _vintage_chart_toggle(cohorts: List[Dict[str, Any]]) -> str:
    """MOIC / Count / EV toggle over the vintage chart (vanilla JS — renders
    all three SVGs, shows one). No external chart library."""
    views = ""
    btns = ""
    for i, (key, label) in enumerate((("moic", "MOIC"), ("count", "Count"),
                                      ("ev", "EV"))):
        on = " on" if i == 0 else ""
        btns += (f'<button type="button" class="pa-vint-btn{on}" '
                 f'data-pa-vint="{key}">{label}</button>')
        views += (f'<div class="pa-vint-view{on}" data-pa-vint-view="{key}">'
                  f'{_vintage_chart(cohorts, key)}</div>')
    js = (
        "<script>(function(){var w=document.currentScript.closest('.pa-vint-wrap');"
        "if(!w)return;w.querySelectorAll('[data-pa-vint]').forEach(function(b){"
        "b.addEventListener('click',function(){var k=b.getAttribute('data-pa-vint');"
        "w.querySelectorAll('[data-pa-vint]').forEach(function(o){o.classList.toggle('on',o===b);});"
        "w.querySelectorAll('[data-pa-vint-view]').forEach(function(v){"
        "v.classList.toggle('on',v.getAttribute('data-pa-vint-view')===k);});});});})();</script>"
    )
    return (
        '<div class="pa-vint-wrap">'
        f'<div class="pa-vint-toggle" role="group" aria-label="Vintage metric">{btns}</div>'
        f'{views}{js}</div>'
    )


def _vintage_table(cohorts: List[Dict[str, Any]]) -> str:
    if not cohorts:
        return empty_note("No vintage data.")
    rows = []
    for c in cohorts:
        year = c.get("year", "—")
        count = c.get("count", 0)
        realized = c.get("realized_count", 0)
        median = c.get("median_moic")
        ev = c.get("total_ev_mm")
        loss = c.get("loss_rate")
        hr = c.get("home_run_rate")
        median_col = (
            P["positive"] if (median or 0) >= 2.5
            else P["warning"] if (median or 0) >= 1.5
            else P["negative"]
        )
        rows.append(
            f'<tr>'
            f'<td style="font-family:var(--ck-mono);color:{P["text"]};'
            f'font-weight:600;" data-val="{year}">{year}</td>'
            f'<td style="text-align:right;font-family:var(--ck-mono);'
            f'font-variant-numeric:tabular-nums;color:{P["text"]};" data-val="{count}">'
            f'{count}</td>'
            f'<td style="text-align:right;font-family:var(--ck-mono);'
            f'font-variant-numeric:tabular-nums;color:{P["text_dim"]};" data-val="{realized}">'
            f'{realized}</td>'
            f'<td style="text-align:right;font-family:var(--ck-mono);'
            f'font-variant-numeric:tabular-nums;color:{median_col};font-weight:600;" '
            f'data-val="{median or 0}">{render_number(median, "moic")}</td>'
            f'<td style="text-align:right;font-family:var(--ck-mono);'
            f'font-variant-numeric:tabular-nums;color:{P["text_dim"]};" data-val="{ev or 0}">'
            f'{_fmt_ev_mm(ev)}</td>'
            f'<td style="text-align:right;font-family:var(--ck-mono);'
            f'font-variant-numeric:tabular-nums;color:{P["negative"] if (loss or 0) > 0.3 else P["text"]};" '
            f'data-val="{loss or 0}">{render_number(loss, "loss_rate")}</td>'
            f'<td style="text-align:right;font-family:var(--ck-mono);'
            f'font-variant-numeric:tabular-nums;color:{P["positive"] if (hr or 0) > 0.25 else P["text"]};" '
            f'data-val="{hr or 0}">{render_number(hr, "home_run_rate")}</td>'
            f'</tr>'
        )
    return (
        f'<div class="ck-table-wrap"><table class="ck-table sortable">'
        f'<thead><tr>'
        f'<th>Vintage</th>'
        f'<th class="num">Count</th>'
        f'<th class="num">Realized</th>'
        f'<th class="num">Med MOIC</th>'
        f'<th class="num">Total EV</th>'
        f'<th class="num">Loss %</th>'
        f'<th class="num">HR %</th>'
        f'</tr></thead>'
        f'<tbody>{"".join(rows)}</tbody></table></div>'
    )


def _deal_type_moic_bars(by_type: Dict[str, Dict[str, Any]]) -> str:
    """Median MOIC by deal type — which archetypes actually returned.
    The table carries MOIC alongside count/loss/HR; this lead bar ranks
    types by realized median MOIC so the best-performing archetype reads
    first. Tone matches the table's MOIC coloring (≥2.5x positive,
    ≥1.5x warning, else negative)."""
    rows = [
        (t, float(s.get("median_moic") or 0.0))
        for t, s in by_type.items()
        if s.get("median_moic") is not None
    ]
    rows = [(t, m) for t, m in rows if m > 0]
    if len(rows) < 2:
        return ""
    rows.sort(key=lambda r: -r[1])
    mx = max(m for _, m in rows)
    out = ""
    for t, m in rows:
        tone = "positive" if m >= 2.5 else "warning" if m >= 1.5 else "negative"
        out += ck_bar_row(t, f"{m:.2f}x", m / mx * 100.0, tone=tone)
    return '<div style="margin-bottom:12px;">' + out + '</div>'


def _deal_type_table(by_type: Dict[str, Dict[str, Any]]) -> str:
    if not by_type:
        return empty_note("No deal-type breakdown.")
    items = sorted(
        by_type.items(),
        key=lambda kv: kv[1].get("count", 0),
        reverse=True,
    )
    rows = []
    total = sum(v.get("count", 0) for v in by_type.values()) or 1
    for deal_type, stats in items:
        n = stats.get("count", 0)
        pct = n / total * 100.0
        median = stats.get("median_moic")
        loss = stats.get("loss_rate")
        hr = stats.get("home_run_rate")
        median_col = (
            P["positive"] if (median or 0) >= 2.5
            else P["warning"] if (median or 0) >= 1.5
            else P["negative"]
        )
        rows.append(
            f'<tr>'
            f'<td style="color:{P["text"]};font-family:var(--ck-mono);'
            f'font-size:11px;">{_html.escape(deal_type)}</td>'
            f'<td style="text-align:right;font-family:var(--ck-mono);'
            f'font-variant-numeric:tabular-nums;color:{P["text"]};" data-val="{n}">'
            f'{n}</td>'
            f'<td style="text-align:right;font-family:var(--ck-mono);'
            f'font-variant-numeric:tabular-nums;color:{P["text_dim"]};" data-val="{pct}">'
            f'{pct:.1f}%</td>'
            f'<td style="text-align:right;font-family:var(--ck-mono);'
            f'font-variant-numeric:tabular-nums;color:{median_col};font-weight:600;" '
            f'data-val="{median or 0}">{render_number(median, "moic")}</td>'
            f'<td style="text-align:right;font-family:var(--ck-mono);'
            f'font-variant-numeric:tabular-nums;color:{P["negative"] if (loss or 0) > 0.3 else P["text_dim"]};" '
            f'data-val="{loss or 0}">{render_number(loss, "loss_rate")}</td>'
            f'<td style="text-align:right;font-family:var(--ck-mono);'
            f'font-variant-numeric:tabular-nums;color:{P["positive"] if (hr or 0) > 0.25 else P["text_dim"]};" '
            f'data-val="{hr or 0}">{render_number(hr, "home_run_rate")}</td>'
            f'</tr>'
        )
    return (
        f'<div class="ck-table-wrap"><table class="ck-table sortable">'
        f'<thead><tr>'
        f'<th>Deal Type</th>'
        f'<th class="num">Count</th>'
        f'<th class="num">Share %</th>'
        f'<th class="num">Med MOIC</th>'
        f'<th class="num">Loss %</th>'
        f'<th class="num">HR %</th>'
        f'</tr></thead>'
        f'<tbody>{"".join(rows)}</tbody></table></div>'
    )


def _concentration_panel(deals: List[Dict[str, Any]]) -> str:
    """Renders concentration across payer, subsector, and geography.

    Uses portfolio_analytics.deals_by_type for deal-type concentration
    (already covered by the deal-type table) — here we hand-roll payer +
    subsector + state concentration via simple counts because the
    market_concentration module expects a pandas DataFrame with a
    different shape than the corpus dicts.
    """
    from collections import Counter, defaultdict
    import statistics as _stats

    sector_counts: Counter = Counter()
    state_counts: Counter = Counter()
    sponsor_ev: defaultdict = defaultdict(float)
    sponsor_count: Counter = Counter()
    for d in deals:
        sec = d.get("subsector") or d.get("sector")
        if sec:
            sector_counts[str(sec)] += 1
        st = d.get("state") or d.get("headquarters_state")
        if st:
            state_counts[str(st)] += 1
        sp = d.get("buyer") or d.get("sponsor")
        ev = d.get("ev_mm")
        if sp and ev is not None:
            try:
                sponsor_ev[str(sp)] += float(ev)
                sponsor_count[str(sp)] += 1
            except (TypeError, ValueError):
                pass

    def _top_table(counter: Dict[str, Any], *, col1: str, top_n: int = 10) -> str:
        items = sorted(counter.items(), key=lambda kv: kv[1], reverse=True)[:top_n]
        total = sum(counter.values()) or 1
        rows = []
        for name, n in items:
            pct = n / total * 100.0
            rows.append(
                f'<tr>'
                f'<td style="color:{P["text"]};font-family:var(--ck-mono);'
                f'font-size:11px;">{_html.escape(str(name))}</td>'
                f'<td style="text-align:right;font-family:var(--ck-mono);'
                f'font-variant-numeric:tabular-nums;color:{P["text"]};" data-val="{n}">'
                f'{n}</td>'
                f'<td style="text-align:right;font-family:var(--ck-mono);'
                f'font-variant-numeric:tabular-nums;color:{P["text_dim"]};" data-val="{pct}">'
                f'{pct:.1f}%</td>'
                f'<td style="width:160px;"><span style="display:block;height:6px;'
                f'background:{P["border_dim"]};border-radius:1px;overflow:hidden;">'
                f'<span style="display:block;height:100%;width:{min(100,pct*2):.1f}%;'
                f'background:{P["accent"]};"></span></span></td>'
                f'</tr>'
            )
        return (
            f'<div class="ck-table-wrap"><table class="ck-table sortable">'
            f'<thead><tr><th>{_html.escape(col1)}</th><th class="num">Count</th>'
            f'<th class="num">Share</th><th></th></tr></thead>'
            f'<tbody>{"".join(rows)}</tbody></table></div>'
        )

    def _sponsor_ev_table(top_n: int = 10) -> str:
        items = sorted(
            sponsor_ev.items(), key=lambda kv: kv[1], reverse=True
        )[:top_n]
        total_ev = sum(sponsor_ev.values()) or 1.0
        rows = []
        for sp, ev in items:
            pct = ev / total_ev * 100.0
            n = sponsor_count[sp]
            rows.append(
                f'<tr>'
                f'<td style="color:{P["text"]};font-family:var(--ck-mono);'
                f'font-size:11px;">{_html.escape(sp)}</td>'
                f'<td style="text-align:right;font-family:var(--ck-mono);'
                f'font-variant-numeric:tabular-nums;color:{P["text_dim"]};" data-val="{n}">'
                f'{n}</td>'
                f'<td style="text-align:right;font-family:var(--ck-mono);'
                f'font-variant-numeric:tabular-nums;color:{P["text"]};" data-val="{ev}">'
                f'{_fmt_ev_mm(ev)}</td>'
                f'<td style="text-align:right;font-family:var(--ck-mono);'
                f'font-variant-numeric:tabular-nums;color:{P["text_dim"]};" data-val="{pct}">'
                f'{pct:.1f}%</td>'
                f'</tr>'
            )
        return (
            f'<div class="ck-table-wrap"><table class="ck-table sortable">'
            f'<thead><tr><th>Sponsor</th><th class="num">Deals</th>'
            f'<th class="num">Total EV</th><th class="num">Share</th></tr></thead>'
            f'<tbody>{"".join(rows)}</tbody></table></div>'
        )

    sector_table = _top_table(dict(sector_counts), col1="Subsector")
    state_table = _top_table(dict(state_counts), col1="State / Region")
    sponsor_table = _sponsor_ev_table()

    # HHI over composition shares — labeled as PORTFOLIO COMPOSITION
    # concentration, NOT market share (the denominator is the corpus, not a
    # real addressable market). 0 = perfectly diffuse, 1 = single category.
    def _hhi_note(counter: Counter, noun: str) -> str:
        hhi = _hhi([float(v) for v in counter.values()])
        if hhi is None:
            return ""
        if hhi < 0.15:
            band = "diffuse"
        elif hhi < 0.25:
            band = "moderately concentrated"
        else:
            band = "concentrated"
        return (f'<p class="pa-hhi">HHI {hhi:.3f} · {band} — portfolio '
                f'<strong>composition</strong> across {len(counter)} {noun}, '
                f'not market share.</p>')

    return (
        f'<div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;">'
        + small_panel(
            f"Subsector concentration (top 10 of {len(sector_counts)})",
            sector_table + _hhi_note(sector_counts, "subsectors"), code="SEC",
        )
        + small_panel(
            f"Geographic concentration (top 10 of {len(state_counts)})",
            state_table + _hhi_note(state_counts, "states/regions"), code="GEO",
        )
        + f'</div>'
        + small_panel(
            f"Sponsor $EV concentration (top 10 of {len(sponsor_count)})",
            sponsor_table, code="SPN",
        )
    )


def _outlier_panel(corpus: List[Dict[str, Any]]) -> str:
    # Statistical guardrail: a z-score needs a real peer sample. With fewer
    # than 3 realized deals, or zero variance (all the same MOIC), the z-score
    # is undefined / meaningless — show an honest "insufficient sample" note
    # rather than implying an investable outlier signal.
    import statistics as _stats
    realized = [float(d["realized_moic"]) for d in corpus
                if isinstance(d.get("realized_moic"), (int, float))]
    if len(realized) < 3:
        return empty_note(
            f"Insufficient peer sample — z-scores need at least 3 realized "
            f"deals (this universe has {len(realized)}). No outlier call made.")
    try:
        if _stats.pstdev(realized) == 0:
            return empty_note(
                "Insufficient variance — every realized deal in this universe "
                "has the same MOIC, so a z-score is undefined. No outlier "
                "call made.")
    except Exception:  # noqa: BLE001
        pass
    try:
        from ...data_public.portfolio_analytics import outlier_deals
        outliers = outlier_deals(corpus, z=2.0)
    except Exception:
        return empty_note("outlier_deals failed.")
    if not outliers:
        return empty_note("No MOIC outliers (|z| ≥ 2) in this universe.")
    rows = []
    for d in outliers[:30]:
        name = _html.escape(str(d.get("deal_name", "—")))
        year = d.get("year", "—")
        moic = d.get("realized_moic")
        z = d.get("z_score")
        col = P["positive"] if (moic or 0) >= 3 else (
            P["negative"] if (moic or 0) < 1 else P["warning"]
        )
        rows.append(
            f'<tr>'
            f'<td style="color:{P["text"]};font-size:11.5px;">{name}</td>'
            f'<td style="text-align:right;font-family:var(--ck-mono);'
            f'font-variant-numeric:tabular-nums;color:{P["text_dim"]};">{year}</td>'
            f'<td style="text-align:right;font-family:var(--ck-mono);'
            f'font-variant-numeric:tabular-nums;color:{col};font-weight:600;">'
            f'{fmt_multiple(moic)}</td>'
            f'<td style="text-align:right;font-family:var(--ck-mono);'
            f'font-variant-numeric:tabular-nums;color:{P["text_dim"]};">'
            + (f"{float(z):+.2f}" if isinstance(z, (int, float)) else "—")
            + f'</td>'
            f'</tr>'
        )
    return (
        f'<div class="ck-table-wrap"><table class="ck-table sortable">'
        f'<thead><tr><th>Deal</th><th class="num">Year</th>'
        f'<th class="num">Realized MOIC</th><th class="num">Z-score</th>'
        f'</tr></thead><tbody>{"".join(rows)}</tbody></table></div>'
    )


_EXPLAINER_CSS = """
.ck-pa-explainer{font-family:var(--sc-serif);font-size:15px;line-height:1.6;
color:var(--sc-text-dim);max-width:68ch;
margin:var(--sc-s-4) 0 var(--sc-s-6);}
.ck-pa-explainer em{color:var(--sc-teal-ink);font-style:italic;}
"""


def _hhi(shares: List[float]) -> Optional[float]:
    """Herfindahl-Hirschman Index over category SHARES (decimals summing to
    ~1). Returns sum(s_i^2) in [0,1]; None if no observations. Labeled in the
    UI as portfolio COMPOSITION concentration — not market share (the
    denominator is the corpus, not a real market)."""
    tot = sum(shares)
    if tot <= 0:
        return None
    return round(sum((s / tot) ** 2 for s in shares), 3)


def _filter_bar(corpus: List[Dict[str, Any]], *, sel_sub: Optional[str],
                sel_vint: Optional[str]) -> str:
    """Universe filter bar — subsector + vintage. Server-side, query-param
    backed (?subsector=&vintage=); selecting an option re-renders every panel
    on the filtered universe so the scorecard never desyncs from the rows."""
    subs = sorted({str(d.get("subsector") or d.get("sector") or "").strip()
                   for d in corpus if (d.get("subsector") or d.get("sector"))})
    years = sorted({str(d.get("year")) for d in corpus if d.get("year")},
                   reverse=True)

    def _seg(label_all: str, options: List[str], key: str,
             sel: Optional[str]) -> str:
        def _href(val: Optional[str]) -> str:
            parts = []
            other = ("vintage" if key == "subsector" else "subsector")
            other_val = sel_vint if key == "subsector" else sel_sub
            if val:
                parts.append(f"{key}={_html.escape(str(val), quote=True)}")
            if other_val:
                parts.append(f"{other}={_html.escape(str(other_val), quote=True)}")
            return "/portfolio-analytics" + ("?" + "&".join(parts) if parts else "")
        cells = (f'<a class="pa-seg-btn{"" if sel else " on"}" '
                 f'href="{_href(None)}">{_html.escape(label_all)}</a>')
        for opt in options:
            on = " on" if str(sel) == str(opt) else ""
            cells += (f'<a class="pa-seg-btn{on}" href="{_href(opt)}">'
                      f'{_html.escape(str(opt))}</a>')
        return f'<div class="pa-seg" role="group" aria-label="{_html.escape(key)}">{cells}</div>'

    return (
        '<div class="pa-filterbar">'
        '<span class="pa-filter-lab">Subsector</span>'
        + _seg("All", subs[:12], "subsector", sel_sub)
        + '<span class="pa-filter-lab">Vintage</span>'
        + _seg("All", years, "vintage", sel_vint)
        + ('<a class="pa-clear" href="/portfolio-analytics">clear filters</a>'
           if (sel_sub or sel_vint) else '')
        + '</div>'
    )


_PA_FILTER_CSS = """
.pa-filterbar{display:flex;align-items:center;gap:10px;flex-wrap:wrap;
background:var(--sc-panel,#faf6ec);border:1px solid var(--sc-rule,#c9c1ac);
padding:12px 16px;margin:0 0 16px;}
.pa-filter-lab{font-family:var(--sc-mono,monospace);font-size:10px;
letter-spacing:.12em;text-transform:uppercase;color:var(--sc-text-dim,#6a7480);}
.pa-seg{display:flex;flex-wrap:wrap;border:1px solid var(--sc-rule,#c9c1ac);}
.pa-seg-btn{font-family:var(--sc-mono,monospace);font-size:11px;
letter-spacing:.04em;padding:5px 11px;color:var(--sc-text-dim,#6a7480);
text-decoration:none;border-right:1px solid var(--sc-rule,#c9c1ac);}
.pa-seg-btn:last-child{border-right:0;}
.pa-seg-btn.on{background:var(--sc-navy,#15202b);color:#faf6ec;}
.pa-seg-btn:hover:not(.on){background:var(--sc-bone,#f3eddb);color:var(--sc-teal-ink,#1f7a5a);}
.pa-seg-btn:focus-visible{outline:2px solid var(--sc-teal,#1f7a5a);outline-offset:-2px;}
.pa-clear{font-family:var(--sc-sans);font-size:12px;color:var(--sc-teal-ink,#1f7a5a);
margin-left:auto;text-decoration:none;}
.pa-clear:hover{text-decoration:underline;}
.pa-hhi{font-family:var(--sc-mono,monospace);font-size:11px;
color:var(--sc-text-dim,#6a7480);margin:6px 0 0;letter-spacing:.02em;}
.pa-vint-toggle{display:inline-flex;border:1px solid var(--sc-rule,#c9c1ac);margin:0 0 8px;}
.pa-vint-toggle button{font-family:var(--sc-mono,monospace);font-size:10.5px;
letter-spacing:.08em;text-transform:uppercase;padding:5px 12px;cursor:pointer;
background:transparent;border:0;border-right:1px solid var(--sc-rule,#c9c1ac);
color:var(--sc-text-dim,#6a7480);}
.pa-vint-toggle button:last-child{border-right:0;}
.pa-vint-toggle button.on{background:var(--sc-navy,#15202b);color:#faf6ec;}
.pa-vint-view{display:none;}
.pa-vint-view.on{display:block;}
"""


def render_portfolio_analytics(
    store: Any = None,
    current_user: Optional[str] = None,
    subsector: Optional[str] = None,
    vintage: Optional[str] = None,
) -> str:
    # Pattern A — durable title + italic explainer (mirrors PR #68 deal-profile,
    # PR #73 portfolio-heatmap, PR #74 portfolio-risk-scan). Replaces three
    # stacked title elements that were on this page: dismissible
    # editorial_intro, render_page_explainer mega-block, and a bespoke grey
    # <p> intro. Copy is "corpus-wide" not "portfolio-wide" to label the
    # semantic-confusion bug honestly while the Pattern D rename is pending.
    def _title(meta: str) -> str:
        # Data-universe chip makes the semantic-confusion bug honest until the
        # rename to "Deal Corpus Analytics" lands: this is a benchmark CORPUS,
        # not the user's portfolio.
        return ck_page_title(
            "Portfolio Analytics",
            eyebrow="PORTFOLIO ANALYTICS",
            meta=meta,
        ) + '<div style="margin:8px 0 0;">' + ck_data_universe("corpus") + '</div>'
    explainer_html = (
        '<p class="ck-pa-explainer">'
        '<em>Where the corpus tells you what worked.</em> '
        "Corpus-wide views across the 655-deal universe: scorecard "
        "(MOIC/IRR quartiles, home-run rate, loss rate), vintage "
        "cohorts, deal-type mix, sector/geography/sponsor "
        "concentration, and realized-MOIC outliers. Read the cohort "
        "for pacing; read concentration to stress-test single-point "
        "risk before committing a new deal."
        '</p>'
    )

    try:
        from ...data_public.portfolio_analytics import (
            corpus_scorecard, vintage_cohort_summary, deals_by_type,
        )
    except Exception as exc:  # noqa: BLE001
        body = small_panel(
            "Portfolio analytics unavailable",
            empty_note(f"portfolio_analytics module failed: {exc!r}"),
            code="ERR",
        )
        return chartis_shell(
            _title("module unavailable") + explainer_html + body,
            title="Portfolio Analytics",
            active_nav="/portfolio-analytics",
            extra_css=_EXPLAINER_CSS,
        )

    full_corpus = load_corpus_deals()
    if not full_corpus:
        body = small_panel(
            "Portfolio analytics — no corpus",
            empty_note("No corpus available."),
            code="NIL",
        )
        return chartis_shell(
            _title("no corpus available") + explainer_html + body,
            title="Portfolio Analytics",
            active_nav="/portfolio-analytics",
            extra_css=_EXPLAINER_CSS,
        )

    # ── Universe filter (server-side; recomputes every panel honestly) ──
    # Validate the requested filters against the actual corpus so junk
    # query params are ignored rather than yielding an empty page.
    _all_subs = {str(d.get("subsector") or d.get("sector") or "").strip()
                 for d in full_corpus}
    _all_years = {str(d.get("year")) for d in full_corpus if d.get("year")}
    sel_sub = subsector if subsector in _all_subs and subsector else None
    sel_vint = vintage if vintage in _all_years and vintage else None
    corpus = [
        d for d in full_corpus
        if (sel_sub is None
            or str(d.get("subsector") or d.get("sector") or "").strip() == sel_sub)
        and (sel_vint is None or str(d.get("year")) == sel_vint)
    ]
    filter_bar = _filter_bar(full_corpus, sel_sub=sel_sub, sel_vint=sel_vint)
    if not corpus:
        # Filter matched nothing — honest, with a clear path back.
        body = (
            _title("no deals match the filter") + explainer_html + filter_bar
            + small_panel(
                "No deals in this universe",
                empty_note("No corpus deals match the selected subsector / "
                           "vintage. <a href='/portfolio-analytics'>Clear "
                           "filters</a> to see the full corpus."),
                code="NIL",
            )
        )
        return chartis_shell(
            body, title="Portfolio Analytics",
            active_nav="/portfolio-analytics",
            extra_css=_EXPLAINER_CSS + _PA_FILTER_CSS,
        )

    try:
        sc = corpus_scorecard(corpus)
        vc = vintage_cohort_summary(corpus)
        dt = deals_by_type(corpus)
    except Exception as exc:  # noqa: BLE001
        body = small_panel(
            "Portfolio analytics failed",
            empty_note(f"scorecard/vintage/type raised: {exc!r}"),
            code="ERR",
        )
        return chartis_shell(
            _title("analysis raised an error") + explainer_html + body,
            title="Portfolio Analytics",
            active_nav="/portfolio-analytics",
            extra_css=_EXPLAINER_CSS,
        )

    kpis = (
        ck_kpi_block("Total Deals", str(sc.get("total_deals", 0)), "corpus size")
        + ck_kpi_block("Realized",
                        str(sc.get("realized_deals", 0)),
                        f"{sc.get('realized_deals',0)/max(sc.get('total_deals',1),1)*100:.0f}% of corpus")
        + ck_kpi_block("Median MOIC",
                        render_number(sc.get("moic_p50"), "moic"), "realized deals")
        + ck_kpi_block("Home-Run Rate",
                        render_number(sc.get("home_run_rate"), "home_run_rate"), "≥ 3.0x MOIC")
        + ck_kpi_block("Loss Rate",
                        render_number(sc.get("loss_rate"), "loss_rate"), "< 1.0x MOIC")
        + ck_kpi_block("Outliers",
                        str(sc.get("outlier_count", 0)), "|z| ≥ 2")
    )
    kpi_strip = f'<div class="ck-kpi-grid">{kpis}</div>'

    scorecard = small_panel(
        "Corpus scorecard (corpus_scorecard output)",
        _scorecard_panel(sc), code="SCR",
    )

    # Visual + tabular: SVG bar chart of median MOIC by vintage
    # year above the underlying table. The chart turns the cohort
    # table into an at-a-glance shape view; partners see which
    # vintages were home-run years vs. underwater without
    # reading the numbers.
    vintage_body = _vintage_chart_toggle(vc) + _vintage_table(vc)
    vintage_panel = small_panel(
        f"Vintage cohort summary ({len(vc)} years)",
        vintage_body, code="VNT",
    )

    type_panel = small_panel(
        f"Deals by type ({len(dt)} categories)",
        _deal_type_moic_bars(dt) + _deal_type_table(dt), code="TYP",
    )

    outlier_panel = small_panel(
        "Outlier deals (|z| ≥ 2 realized MOIC)",
        _outlier_panel(corpus), code="OUT",
    )

    meta = (
        f"{sc.get('total_deals',0)} corpus deals · "
        f"median {fmt_multiple(sc.get('moic_p50'))} · "
        f"HR {fmt_pct(sc.get('home_run_rate'))} · "
        f"loss {fmt_pct(sc.get('loss_rate'))}"
    )

    scope_note = ""
    if sel_sub or sel_vint:
        bits = []
        if sel_sub:
            bits.append(_html.escape(sel_sub))
        if sel_vint:
            bits.append(f"vintage {_html.escape(sel_vint)}")
        scope_note = (
            f'<p class="ck-pa-explainer" style="margin-top:0;">Filtered to '
            f'<em>{" · ".join(bits)}</em> — {len(corpus)} of '
            f'{len(full_corpus)} corpus deals. Every panel below is '
            f'recomputed on this universe.</p>'
        )

    body = (
        _title(meta)
        + explainer_html
        + filter_bar
        + scope_note
        + kpi_strip
        + ck_section_header(
            "CORPUS SCORECARD",
            "realized-deal roll-up statistics",
        )
        + f'<div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;">'
        + scorecard + type_panel
        + f'</div>'
        + ck_section_header(
            "VINTAGE MIX & PACING",
            "annual cohort sizes + realized-MOIC distribution",
            count=len(vc),
        )
        + vintage_panel
        + ck_section_header(
            "CONCENTRATION RISK",
            "where the corpus is clustered — subsector, geography, sponsor",
        )
        + _concentration_panel(corpus)
        + ck_section_header(
            "OUTLIER DEALS", "tails of the realized-MOIC distribution",
        )
        + outlier_panel
    )

    return chartis_shell(
        body,
        title="Portfolio Analytics",
        active_nav="/portfolio-analytics",
        extra_css=_EXPLAINER_CSS + _PA_FILTER_CSS,
    )
