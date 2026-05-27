"""Shared scaffold for sector provider screeners (Home Health, Hospice, …).

Renders, from the vendored sector loaders, a consistent surface:
KPI cards · real US state map (drilldown via ?state=) · per-state summary
table (national view) OR provider/quality table (state view) · a provenance
+ limitations card. No external calls; honest empty state.
"""
from __future__ import annotations

import html as _html
from typing import Any, Callable, Dict, List, Optional, Tuple

from ._chartis_kit import chartis_shell, ck_kpi_block, ck_page_title, ck_panel
from .sector_market_intel import filter_by_locality, render_state_market_panels
from .us_geo_map import render_us_geo_map
from .xray_kit import XRAY_CSS, xr_eyebrow


def _esc(s: Any) -> str:
    return _html.escape("" if s is None else str(s))


# Skin that brings the shared sector screener into the handoff X-Ray look —
# the same editorial system used by the hospital HCRIS X-Ray. Scoped to `.xr`
# so it only retints THIS page: the green accent (links / KPI emphasis / map
# legend), navy ribbon panel headers, sharp corners. No markup changes — the
# map, market-intelligence panels, KPIs, and tables keep their structure.
_SCREENER_SKIN = """
.xr .ck-link{color:var(--xr-green);}
.xr .ck-link:hover{color:var(--xr-green-deep);}
.xr .ck-panel{border-radius:0;border-color:var(--xr-rule);}
.xr .ck-panel-head{background:var(--xr-navy);border-radius:0;}
.xr .ck-kpi-block,.xr .ck-kpi{border-radius:0;}
.xr .ck-kpi-value em,.xr .ck-kpi-value .num{color:var(--xr-green);}
.xr .ck-table th{font-family:var(--xr-mono);letter-spacing:.06em;text-transform:uppercase;}
.xr .ck-table td a.ck-link{color:var(--xr-green);}
.xr-screener-eyebrow{margin-bottom:6px;}
"""


def _fmt(v: Optional[float], suffix: str = "") -> str:
    return f"{v:g}{suffix}" if v is not None else "—"


def render_sector_screener(
    *,
    qs: Optional[Dict[str, List[str]]],
    route: str,
    title: str,
    eyebrow: str,
    description: str,
    provenance: str,
    limitations: List[str],
    providers: Dict[str, Any],
    quality: Dict[str, Dict[str, Optional[float]]],
    summary: Dict[str, Dict[str, object]],
    count_key: str,
    count_label: str,
    avg_key: str,
    avg_label: str,
    name_attr: str,
    providers_for_state: Callable[[str], List[Any]],
    table_cols: List[Tuple[str, Callable[[Any, Dict[str, Optional[float]]], str]]],
    locality_attr: str = "",
    locality_label: str = "",
    headline_metric_key: str = "",
    headline_suffix: str = "",
) -> str:
    qs = qs or {}
    sel_state = (qs.get("state") or [""])[0].strip().upper()
    sel_loc = (qs.get("locality") or [""])[0].strip()

    # ── Honest empty state (data file missing) ──
    if not providers:
        body = (
            '<div class="xr">'
            + ck_page_title(title, eyebrow=eyebrow, meta="data not loaded")
            + ck_panel(
                '<p class="ck-section-body">No sector data is loaded yet. '
                'This page reads vendored CMS Provider Data Catalog files; '
                'when they are present it shows providers, quality, and a '
                'state map.</p>',
                title=title,
            )
            + '</div>'
        )
        return chartis_shell(body, title, active_nav=route,
                             extra_css=XRAY_CSS + _SCREENER_SKIN)

    n_total = len(providers)
    n_states = len(summary)
    n_rated = sum(int(s.get("rated", 0)) for s in summary.values())

    # ── Real US state map: shaded by provider count, drilldown by state ──
    state_values = {st: int(s.get(count_key, 0)) for st, s in summary.items()}
    state_notes = {
        st: f"avg {avg_label}: {_fmt(s.get(avg_key))}"
        for st, s in summary.items() if s.get(avg_key) is not None
    }
    map_panel = ck_panel(
        render_us_geo_map(
            state_values, metric_label=count_label.lower(),
            value_format=lambda v: f"{int(v):,}",
            state_notes=state_notes,
            selected_state=sel_state or None,
            state_link_template=f"{route}?state={{state}}",
        )
        + '<p style="font-size:11px;color:var(--sc-text-dim);margin:8px 0 0;">'
        f'Geographic US map — shaded by {count_label.lower()}. '
        f'Click a state to list its {count_label.lower()}.</p>',
        title=f"{count_label} by state",
    )

    # ── KPI cards (national or selected-state) ──
    if sel_state and sel_state in summary:
        s = summary[sel_state]
        kpis = (
            '<div class="ck-kpi-grid" style="grid-template-columns:repeat(3,1fr);gap:8px;margin-bottom:14px;">'
            + ck_kpi_block(f"{count_label} in {sel_state}", f"{int(s.get(count_key,0)):,}", "Medicare-certified")
            + ck_kpi_block(f"With {avg_label}", f"{int(s.get('rated',0)):,}", "publicly reported")
            + ck_kpi_block(f"Avg {avg_label}", _fmt(s.get(avg_key)), f"{sel_state} mean")
            + '</div>'
        )
    else:
        kpis = (
            '<div class="ck-kpi-grid" style="grid-template-columns:repeat(3,1fr);gap:8px;margin-bottom:14px;">'
            + ck_kpi_block(f"Total {count_label}", f"{n_total:,}", "Medicare-certified")
            + ck_kpi_block("States covered", f"{n_states}", "incl. territories")
            + ck_kpi_block(f"With {avg_label}", f"{n_rated:,}", "publicly reported")
            + '</div>'
        )

    # ── Table: per-state summary (national) OR providers (state view) ──
    if sel_state:
        # State competitive-market intelligence (summary cards, ownership mix,
        # quality distribution, locality competition). Only when the caller
        # wired locality + headline-metric params.
        market = ""
        if locality_attr and headline_metric_key:
            market = render_state_market_panels(
                providers=providers, quality=quality, state=sel_state,
                route=route, kind_singular=count_label.rstrip("s").lower(),
                locality_attr=locality_attr, locality_label=locality_label,
                headline_label=avg_label, headline_suffix=headline_suffix,
                headline_key=headline_metric_key, selected_locality=sel_loc,
            )

        state_rows = providers_for_state(sel_state)
        if sel_loc and locality_attr:
            state_rows = filter_by_locality(state_rows, locality_attr, sel_loc)
        total_in_scope = len(state_rows)
        rows = state_rows[:200]
        head = "".join(f"<th>{_esc(h)}</th>" for h, _ in table_cols)
        body_rows = ""
        for p in rows:
            q = quality.get(getattr(p, "ccn", ""), {})
            cells = "".join(f"<td>{fn(p, q)}</td>" for _, fn in table_cols)
            body_rows += f"<tr>{cells}</tr>"
        scope = f"in {_esc(sel_state)}"
        clear = ""
        if sel_loc:
            scope = f"in {_esc(sel_loc)}, {_esc(sel_state)}"
            clear = (f' · <a href="{route}?state={_esc(sel_state)}" class="ck-link">'
                     f'clear {_esc(locality_label.lower() or "locality")} filter</a>')
        table = market + ck_panel(
            f'<p class="ck-section-body"><a href="{route}" class="ck-link">'
            f'&larr; All states</a>{clear} · showing up to 200 of '
            f'{total_in_scope:,} {scope}.</p>'
            f'<table class="ck-table"><thead><tr>{head}</tr></thead>'
            f'<tbody>{body_rows}</tbody></table>',
            title=f"{count_label} {scope}",
        )
    else:
        srows = sorted(summary.items(), key=lambda kv: -int(kv[1].get(count_key, 0)))
        body_rows = "".join(
            f'<tr><td><a href="{route}?state={_esc(st)}" class="ck-link">{_esc(st)}</a></td>'
            f'<td class="num">{int(s.get(count_key,0)):,}</td>'
            f'<td class="num">{int(s.get("rated",0)):,}</td>'
            f'<td class="num">{_fmt(s.get(avg_key))}</td></tr>'
            for st, s in srows
        )
        table = ck_panel(
            '<p class="ck-section-body">Click a state for its provider list.</p>'
            f'<table class="ck-table"><thead><tr><th>State</th>'
            f'<th class="num">{_esc(count_label)}</th><th class="num">Rated</th>'
            f'<th class="num">Avg {_esc(avg_label)}</th></tr></thead>'
            f'<tbody>{body_rows}</tbody></table>',
            title=f"{count_label} by state",
        )

    # ── Provenance + limitations (trust) ──
    lim = "".join(f"<li>{_esc(x)}</li>" for x in limitations)
    prov_card = ck_panel(
        f'<p class="ck-section-body"><strong>Source:</strong> {_esc(provenance)}</p>'
        f'<ul style="font-size:12px;color:var(--sc-text-dim);line-height:1.6;'
        f'margin:6px 0 0;padding-left:18px;">{lim}</ul>',
        title="Data source & limitations",
    )

    body = (
        '<div class="xr">'
        + f'<div class="xr-screener-eyebrow">{xr_eyebrow(eyebrow)}</div>'
        + ck_page_title(title, eyebrow=eyebrow,
                      meta=f"{n_total:,} providers · {n_states} states · CMS public data")
        + f'<p class="ck-section-body" style="max-width:70ch;margin:0 0 14px;">{_esc(description)}</p>'
        + kpis + map_panel + table + prov_card
        + '</div>'
    )
    return chartis_shell(body, title, active_nav=route,
                         extra_css=XRAY_CSS + _SCREENER_SKIN)
