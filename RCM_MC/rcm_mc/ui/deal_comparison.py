"""Side-by-side deal comparison + screening page (Prompt 33-A/C).

Two pages:

1. ``/compare?deals=acme,beta`` — column-per-deal comparison table
   with an SVG radar chart overlay.
2. ``/screen`` — paste hospital names, get a ranked table with
   verdict badges.

Both are server-rendered HTML using the shared ``_ui_kit.shell()``.
"""
from __future__ import annotations

import html
import math
from typing import Any, Dict, List, Optional

from ..analysis.packet import DealAnalysisPacket


# ── Comparison ────────────────────────────────────────────────────

_COMPARE_DIMENSIONS = [
    ("Completeness", lambda p: p.completeness.grade if p.completeness else "—"),
    ("EBITDA impact", lambda p: p.ebitda_bridge.total_ebitda_impact if p.ebitda_bridge else 0),
    ("denial_rate", lambda p: _pm_val(p, "denial_rate")),
    ("days_in_ar", lambda p: _pm_val(p, "days_in_ar")),
    ("net_collection_rate", lambda p: _pm_val(p, "net_collection_rate")),
    ("cost_to_collect", lambda p: _pm_val(p, "cost_to_collect")),
    ("clean_claim_rate", lambda p: _pm_val(p, "clean_claim_rate")),
    ("case_mix_index", lambda p: _pm_val(p, "case_mix_index")),
    ("Risk count", lambda p: len(p.risk_flags or [])),
]

_RADAR_METRICS = [
    "denial_rate", "days_in_ar", "net_collection_rate",
    "cost_to_collect", "clean_claim_rate", "case_mix_index",
]

# Editorial categorical series colors (one per compared deal) —
# navy / teal / amber / red, distinct but on-palette.
_PALETTE = ["#0b2341", "#1F7A75", "#b8732a", "#b5321e"]


def _pm_val(p: DealAnalysisPacket, metric: str) -> Optional[float]:
    pm = (p.rcm_profile or {}).get(metric)
    return float(pm.value) if pm is not None else None


def _esc(s: Any) -> str:
    return html.escape("" if s is None else str(s))


def _fmt(v: Any) -> str:
    if v is None:
        return "—"
    if isinstance(v, float):
        if abs(v) >= 1e6:
            return f"${v / 1e6:,.1f}M"
        return f"{v:,.2f}"
    return str(v)


def _render_radar(packets: List[DealAnalysisPacket]) -> str:
    """Overlapping radar polygons — one per deal, 6 axes."""
    if not packets:
        return ""
    n_axes = len(_RADAR_METRICS)
    cx, cy, radius = 150, 150, 120
    angle_step = 2 * math.pi / n_axes

    # Collect values per metric across all deals to normalize 0–1.
    all_vals: Dict[str, List[float]] = {m: [] for m in _RADAR_METRICS}
    for p in packets:
        for m in _RADAR_METRICS:
            v = _pm_val(p, m)
            if v is not None:
                all_vals[m].append(v)
    mins = {m: min(vs) if vs else 0 for m, vs in all_vals.items()}
    maxs = {m: max(vs) if vs else 1 for m, vs in all_vals.items()}

    # Axis labels.
    labels = ""
    for i, m in enumerate(_RADAR_METRICS):
        angle = -math.pi / 2 + i * angle_step
        lx = cx + (radius + 18) * math.cos(angle)
        ly = cy + (radius + 18) * math.sin(angle)
        anchor = "middle"
        if lx < cx - 10:
            anchor = "end"
        elif lx > cx + 10:
            anchor = "start"
        labels += (
            f'<text x="{lx:.0f}" y="{ly:.0f}" '
            f'text-anchor="{anchor}" fill="#7a8699" '
            f'font-size="10">{m.replace("_", " ")}</text>'
        )

    # Polygons.
    polygons = ""
    for idx, p in enumerate(packets):
        color = _PALETTE[idx % len(_PALETTE)]
        pts: List[str] = []
        for i, m in enumerate(_RADAR_METRICS):
            v = _pm_val(p, m)
            lo, hi = mins[m], maxs[m]
            frac = ((v - lo) / (hi - lo)) if v is not None and hi > lo else 0.5
            angle = -math.pi / 2 + i * angle_step
            r = frac * radius
            px = cx + r * math.cos(angle)
            py = cy + r * math.sin(angle)
            pts.append(f"{px:.1f},{py:.1f}")
        polygons += (
            f'<polygon points="{" ".join(pts)}" '
            f'fill="{color}" fill-opacity="0.15" '
            f'stroke="{color}" stroke-width="1.5"/>'
        )

    return (
        f'<svg viewBox="0 0 300 300" width="300" height="300" '
        f'style="display:block;margin:0 auto;">'
        f'{labels}{polygons}</svg>'
    )


def render_comparison(packets: List[DealAnalysisPacket]) -> str:
    """Column-per-deal table + radar chart. Used by ``GET /compare``."""
    from ._chartis_kit import (
        chartis_shell, ck_kpi_block, ck_next_section, ck_panel,
    )

    if not packets:
        body = (
            '<div class="cad-card">'
            '<p style="color:var(--cad-text3);margin-bottom:12px;">No deals selected for comparison.</p>'
            '<a href="/portfolio" class="cad-btn cad-btn-primary" '
            'style="text-decoration:none;">Go to Portfolio to select deals</a>'
            '</div>'
        )
        return chartis_shell(body, "Deal Comparison",
                        subtitle="Side-by-side deal analysis",
            editorial_intro={
                "eyebrow": "DEAL COMPARISON",
                "headline": "Where these deals diverge.",
                "italic_word": "diverge",
                "body": "Pick deals from the portfolio to compare side-by-side.",
            })

    header_cells = "".join(
        f'<th>{_esc(p.deal_name or p.deal_id)}</th>'
        for p in packets
    )
    rows_html: List[str] = []
    for dim_name, fn in _COMPARE_DIMENSIONS:
        cells: List[str] = []
        for p in packets:
            v = fn(p)
            cells.append(f'<td class="num">{_fmt(v)}</td>')
        rows_html.append(
            f"<tr><td><strong>{_esc(dim_name)}</strong></td>"
            + "".join(cells) + "</tr>"
        )
    table_html = (
        '<table class="cad-table">'
        f'<thead><tr><th>Dimension</th>{header_cells}</tr></thead>'
        f'<tbody>{"".join(rows_html)}</tbody>'
        '</table>'
    )

    radar = _render_radar(packets)

    legend = " ".join(
        f'<span style="color:{_PALETTE[i % len(_PALETTE)]};margin-right:12px;">'
        f'&#9632; {_esc(p.deal_name or p.deal_id)}</span>'
        for i, p in enumerate(packets)
    )

    # KPI summary for each deal — render each as a ck_panel with a
    # ck_kpi_strip of four metrics + nav badges.
    kpi_cards = []
    for i, p in enumerate(packets):
        dr = _pm_val(p, "denial_rate")
        ar = _pm_val(p, "days_in_ar")
        risk_count = len(p.risk_flags or [])
        grade = p.completeness.grade if p.completeness else "—"
        did = _esc(p.deal_id)
        metrics = (
            '<div class="ck-kpi-strip">'
            + ck_kpi_block(
                "Denial Rate", _fmt(dr),
                help={
                    "definition": (
                        "Initial-denial rate as a share of total "
                        "claims. PE healthcare median ~10-12%; above "
                        "15% signals a structural denial issue (often "
                        "payer-mix or charge-capture). Below 7% on a "
                        "claims volume large enough to matter is "
                        "best-in-class."
                    ),
                },
            )
            + ck_kpi_block(
                "AR Days", _fmt(ar),
                help={
                    "definition": (
                        "Days in accounts receivable. PE healthcare "
                        "median is 45-55 days; above 75 days means "
                        "cash is sitting on the books instead of in "
                        "the bank. Below 35 is unusual (either "
                        "best-in-class or a posting policy that "
                        "front-loads adjustments)."
                    ),
                },
            )
            + ck_kpi_block(
                "Risks", str(risk_count),
                help={
                    "definition": (
                        "Count of risk flags fired by the diligence "
                        "engines on this packet. Zero is unusual "
                        "(every deal has something); 3-5 is typical "
                        "before mitigants; 10+ is a structurally "
                        "broken deal that should not have made it to "
                        "this stage."
                    ),
                },
            )
            + ck_kpi_block(
                "Grade", grade,
                help={
                    "definition": (
                        "Completeness grade A-F for this deal's "
                        "underlying data. A = full HCRIS + claims + "
                        "operating data; D-F = heavy imputation, so "
                        "downstream numbers carry wider conformal "
                        "bands. Compare grades when reading two "
                        "deals — same KPI, different confidence."
                    ),
                },
            )
            + "</div>"
        )
        nav_links = (
            f'<p class="ck-section-body">'
            f'<a href="/deal/{did}" class="cad-badge cad-badge-blue">Dashboard</a> '
            f'<a href="/models/dcf/{did}" class="cad-badge cad-badge-muted">DCF</a> '
            f'<a href="/models/lbo/{did}" class="cad-badge cad-badge-muted">LBO</a> '
            f'<a href="/models/bridge/{did}" class="cad-badge cad-badge-muted">Bridge</a> '
            f'<a href="/models/denial/{did}" class="cad-badge cad-badge-muted">Denial</a>'
            f'</p>'
        )
        kpi_cards.append(ck_panel(
            metrics + nav_links,
            title=_esc(p.deal_name or p.deal_id),
        ))

    actions = ck_panel(
        '<p class="ck-section-body">'
        '<a href="/portfolio" class="cad-btn">Portfolio</a> '
        '<a href="/portfolio/regression" class="cad-btn">Regression</a> '
        '<a href="/analysis" class="cad-btn cad-btn-primary">Analysis Hub</a>'
        '</p>',
        title="Next steps",
    )

    body = (
        '<div class="ck-card-grid">'
        + "".join(kpi_cards)
        + '</div>'
        + ck_panel(
            f'<p class="ck-section-body">{legend}</p>{radar}',
            title="Comparative radar",
        )
        + ck_panel(table_html, title="Dimension table")
        + actions
        + ck_next_section(
            "Open the IC packet",
            "/diligence/ic-packet",
            eyebrow="Continue —",
            italic_word="IC",
        )
    )
    return chartis_shell(
        body, "Deal Comparison",
        subtitle=f"Comparing {len(packets)} deals",
        editorial_intro={
            "eyebrow": "DEAL COMPARISON",
            "headline": "Where these deals diverge.",
            "italic_word": "diverge",
            "body": (
                "Side-by-side metrics across the selected deals "
                "with a radar chart for visual divergence. Use "
                "this when picking which of two competing deals "
                "to advance, or to see how a deal compares to a "
                "recently closed peer."
            ),
        },
    )


# ── Screening page ────────────────────────────────────────────────

_EXPLAINER_CSS = """
.ck-hs-explainer{font-family:var(--sc-serif);font-size:15px;line-height:1.6;
color:var(--sc-text-dim);max-width:68ch;
margin:var(--sc-s-4) 0 var(--sc-s-6);}
.ck-hs-explainer em{color:var(--sc-teal-ink);font-style:italic;}
/* Preset screens as labelled cards (not bare chips) so intent is explicit:
   which buy in-range vs which is the large-cap/diligence screen. */
.hs-presets{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));
gap:8px;margin-bottom:16px;}
.hs-preset{display:flex;flex-direction:column;gap:3px;text-decoration:none;
padding:9px 12px;border:1px solid var(--cad-border,#d6cfc0);border-radius:5px;
background:var(--cad-bg3,#faf7f0);transition:border-color 90ms,background 90ms;}
.hs-preset:hover{border-color:var(--sc-teal,#155752);}
.hs-preset-active{border-color:var(--sc-teal,#155752);
background:var(--sc-teal-soft,#d4e4e2);}
.hs-preset-label{font-family:var(--sc-sans,Inter Tight),sans-serif;font-weight:600;
font-size:12.5px;color:var(--cad-text,#1a2332);}
.hs-preset-desc{font-size:10.5px;line-height:1.4;color:var(--cad-text2,#5b6b7a);}
/* Active-criteria chips — what "in range" actually means for this screen. */
.hs-chips{display:flex;gap:6px;flex-wrap:wrap;margin:2px 0 14px;}
.hs-chip{font-family:var(--sc-mono,JetBrains Mono),monospace;font-size:10px;
letter-spacing:.02em;color:var(--sc-teal-ink,#0f3d39);background:var(--sc-teal-soft,#d4e4e2);
border-radius:3px;padding:3px 8px;}
.hs-dq{opacity:.5;cursor:help;}
.hs-field-help{font-size:9.5px;color:var(--cad-text3,#7a8699);}
"""


def render_screen_page(
    results: Optional[List[Dict[str, Any]]] = None,
    filters: Optional[Dict[str, str]] = None,
    predefined: Optional[str] = None,
    total_scanned: int = 0,
) -> str:
    """GET /screen — metric-based hospital screener."""
    from ._chartis_kit import chartis_shell, ck_page_title, margin_is_plausible
    from .brand import PALETTE

    filters = filters or {}

    # Predefined screens — each labelled card states its SIZE range so the
    # intent is explicit: which presets find acquirable in-range targets vs
    # the one large-cap/diligence screen. (Old "Turnaround" had no size bound
    # and surfaced 1,000-bed systems.) Keys mirror the filter map in
    # server.py:_route_screener_page.
    presets = [
        ("turnaround", "Turnaround — acquirable",
         "50–400 beds · margin ≤3% · most-distressed first. Buyable fix-it targets, not giant systems."),
        ("large_cap", "Large platforms",
         "300+ beds · $300M+ NPR. Platform-scale & large-cap diligence — where big turnarounds live."),
        ("margin_expansion", "Margin expansion",
         "100–500 beds · margin 0–10%. Profitable already, clear room to grow."),
        ("undervalued", "Undervalued",
         "150+ beds · lowest revenue-per-bed first. Priced below its capacity."),
        ("small_efficient", "Efficient bolt-ons",
         "<200 beds · margin ≥0%. Small, clean add-ons."),
    ]
    preset_html = '<div class="hs-presets">'
    for key, label, desc in presets:
        active = " hs-preset-active" if predefined == key else ""
        preset_html += (
            f'<a href="/screen?preset={key}" class="hs-preset{active}">'
            f'<span class="hs-preset-label">{_esc(label)}</span>'
            f'<span class="hs-preset-desc">{_esc(desc)}</span></a>'
        )
    preset_html += '</div>'

    # Filter form — explicit min/max RANGES so "in range" is unambiguous, each
    # with a one-line gloss. (NPR = net patient revenue; margin = operating
    # margin.) The max-beds / max-revenue ceilings are what keep a screen from
    # returning giant systems.
    filter_fields = [
        ("min_beds", "Beds — min", filters.get("min_beds", ""), "e.g. 50", "smallest bed count"),
        ("max_beds", "Beds — max", filters.get("max_beds", ""), "e.g. 400", "ceiling — caps giant systems"),
        ("min_revenue", "NPR $M — min", filters.get("min_revenue", ""), "e.g. 25", "revenue floor"),
        ("max_revenue", "NPR $M — max", filters.get("max_revenue", ""), "e.g. 500", "revenue ceiling"),
        ("min_margin", "Margin % — min", filters.get("min_margin", ""), "e.g. 0", "operating-margin floor"),
        ("max_margin", "Margin % — max", filters.get("max_margin", ""), "e.g. 3", "ceiling — low = struggling"),
        ("state", "State", filters.get("state", ""), "e.g. TX", "2-letter code"),
    ]
    filter_inputs = ""
    for name, label, val, placeholder, helptext in filter_fields:
        filter_inputs += (
            f'<div>'
            f'<label style="font-size:11px;color:{PALETTE["text_muted"]};display:block;margin-bottom:2px;">'
            f'{_esc(label)}</label>'
            f'<input name="{name}" value="{_esc(val)}" placeholder="{_esc(placeholder)}" '
            f'style="width:100%;padding:7px 10px;border:1px solid var(--cad-border);'
            f'border-radius:6px;background:var(--cad-bg3);color:var(--cad-text);font-size:13px;">'
            f'<div class="hs-field-help">{_esc(helptext)}</div></div>'
        )

    # Sort control — "Margin (most distressed first)" is what turns a screen
    # into a list of fix-it candidates rather than the biggest hospitals.
    sort_val = filters.get("sort", "") or "revenue"
    sort_opts = [
        ("revenue", "Revenue (largest first)"),
        ("margin", "Margin (most distressed first)"),
        ("beds", "Beds (most first)"),
        ("rev_per_bed", "Revenue per bed (lowest first)"),
    ]
    sort_select = (
        f'<div><label style="font-size:11px;color:{PALETTE["text_muted"]};display:block;margin-bottom:2px;">'
        f'Sort by</label>'
        f'<select name="sort" style="width:100%;padding:7px 10px;border:1px solid var(--cad-border);'
        f'border-radius:6px;background:var(--cad-bg3);color:var(--cad-text);font-size:13px;">'
        + "".join(
            f'<option value="{v}"{" selected" if v == sort_val else ""}>{_esc(lbl)}</option>'
            for v, lbl in sort_opts)
        + '</select><div class="hs-field-help">order of matches</div></div>'
    )

    form = (
        f'<div class="cad-card">'
        f'<h2>Filter by Metrics</h2>'
        f'<p style="color:{PALETTE["text_secondary"]};font-size:12.5px;margin-bottom:12px;">'
        f'Find hospitals from {total_scanned:,} HCRIS records by financial size and margin. '
        f'Pick a preset, or set your own ranges — the <b>max</b> fields are what keep results '
        f'in an acquirable range instead of returning the biggest systems.</p>'
        f'{preset_html}'
        f'<form method="GET" action="/screen">'
        f'<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:10px;">'
        f'{filter_inputs}{sort_select}</div>'
        f'<div style="margin-top:12px;">'
        f'<button type="submit" class="cad-btn cad-btn-primary">Run Screen</button></div>'
        f'</form></div>'
    )

    # Active-criteria chips — make "in range" concrete: exactly what's being
    # screened, so a result set is never a mystery.
    def _chip(t: str) -> str:
        return f'<span class="hs-chip">{_esc(t)}</span>'
    _range_keys = ("min_beds", "max_beds", "min_revenue", "max_revenue",
                   "min_margin", "max_margin", "state")
    chips = []
    if filters.get("min_beds") or filters.get("max_beds"):
        chips.append(_chip(f"Beds {filters.get('min_beds') or '0'}–{filters.get('max_beds') or '∞'}"))
    if filters.get("min_revenue") or filters.get("max_revenue"):
        chips.append(_chip(f"NPR ${filters.get('min_revenue') or '0'}M–${filters.get('max_revenue') or '∞'}M"))
    if filters.get("min_margin") or filters.get("max_margin"):
        chips.append(_chip(f"Margin {filters.get('min_margin') or '−∞'}%–{filters.get('max_margin') or '∞'}%"))
    if filters.get("state"):
        chips.append(_chip(f"State {filters['state']}"))
    chips.append(_chip(f"Sorted: {dict(sort_opts).get(sort_val, sort_val)}"))
    chips_html = (
        f'<div class="hs-chips"><span style="font-size:10px;color:{PALETTE["text_muted"]};'
        f'align-self:center;">IN RANGE →</span>{"".join(chips)}</div>'
        if any(filters.get(k) for k in _range_keys) else ""
    )

    # Results
    results_block = ""
    if results:
        rows_html = ""
        for r in results:
            ccn = _esc(str(r.get("ccn", "")))
            name = _esc(str(r.get("name", ""))[:45])
            state = _esc(str(r.get("state", "")))
            beds = r.get("beds", r.get("bed_count", 0))
            rev = r.get("net_patient_revenue", r.get("revenue", r.get("net_revenue", 0)))
            rpb = r.get("rev_per_bed", 0) or 0
            margin = r.get("operating_margin", 0)
            margin = float(margin) if margin else 0
            if margin_is_plausible(margin):
                margin_color = PALETTE["positive"] if margin > 0.05 else (
                    PALETTE["warning"] if margin > 0 else PALETTE["negative"])
                margin_cell = f'<td class="num" style="color:{margin_color};">{margin:.1%}</td>'
            else:
                # Junk-opex artifact: show it, but mute + flag rather than let
                # it read as a real result (see margin_is_plausible).
                margin_cell = (
                    f'<td class="num hs-dq" title="Margin {margin:.1%} is outside the '
                    f'realistic -40% to +30% band — this HCRIS filing likely has '
                    f'incomplete or aggregated opex; review before relying on it.">'
                    f'{margin:.1%} &#9888;</td>'
                )
            rpb_str = f'${rpb/1e3:,.0f}K' if rpb else '&mdash;'
            rows_html += (
                f'<tr>'
                f'<td><a href="/hospital/{ccn}" style="font-weight:500;">{name}</a></td>'
                f'<td>{state}</td>'
                f'<td class="num">{int(beds):,}</td>'
                f'<td class="num">${float(rev)/1e6:,.0f}M</td>'
                f'<td class="num">{rpb_str}</td>'
                f'{margin_cell}'
                f'<td style="white-space:nowrap;">'
                f'<a href="/hospital/{ccn}" class="cad-badge cad-badge-blue" '
                f'style="text-decoration:none;">Profile</a> '
                f'<a href="/new-deal?q={ccn}" class="cad-badge cad-badge-green" '
                f'style="text-decoration:none;">Diligence</a></td>'
                f'</tr>'
            )
        results_block = (
            f'<div class="cad-card">'
            f'<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;">'
            f'<h2>{len(results)} Matches</h2>'
            f'<span style="font-size:12px;color:{PALETTE["text_muted"]};">from {total_scanned:,} hospitals</span>'
            f'</div>'
            f'<table class="cad-table"><thead><tr>'
            f'<th>Hospital</th><th>State</th><th>Beds</th><th>NPR</th>'
            f'<th>NPR/Bed</th><th>Margin</th><th>Actions</th></tr></thead>'
            f'<tbody>{rows_html}</tbody></table></div>'
        )

    n = len(results) if results else 0
    meta = (
        f"{n} matches · {total_scanned:,} hospitals scanned"
        if results else f"{total_scanned:,} HCRIS hospitals"
    )
    title_block = ck_page_title(
        "Hospital Screener", eyebrow="HOSPITAL SCREENER", meta=meta,
    )
    explainer_html = (
        '<p class="ck-hs-explainer">'
        '<em>Where the universe filters down to candidates.</em> '
        "Screen the HCRIS universe by size (beds, revenue) and operating "
        "margin. To <b>find targets to buy</b>, keep a bed/revenue "
        "<b>max</b> so results stay in an acquirable range and sort by "
        "<em>margin (most distressed first)</em>; to <b>run diligence on a "
        "large turnaround</b>, use the <em>Large platforms</em> preset. Each "
        "match links to its profile and the diligence flow."
        '</p>'
    )
    body = title_block + explainer_html + form + chips_html + results_block
    return chartis_shell(
        body, "Hospital Screener", active_nav="/screen",
        extra_css=_EXPLAINER_CSS,
    )
