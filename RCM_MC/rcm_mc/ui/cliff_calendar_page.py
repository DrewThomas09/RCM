"""Reimbursement cliff calendar — /diligence/cliff-calendar.

Brings the long-dark ``pe_intelligence.reimbursement_cliff_calendar_2026_2029``
module to life as an editorial Chartis page. That module is a pre-seeded
catalog of specific 2026-2029 Medicare / 340B rate events keyed to subsector
(OBBBA phase 1/2, sequestration, site-neutral HOPD, PAMA, PDGM, 340B, DME
competitive bid, wage-index floor, …) plus a per-deal scan that filters the
calendar to a hold window and sums the rate exposure.

Honesty: the events are real, named regulatory items, but the magnitudes are
**partner-judgment approximations** (per the module's own docstring) — not a
live CMS feed. The page is classified NAVY (a calculator whose output is
computed from the subsector + hold-window you provide, over curated defaults)
and carries an explicit illustrative-template note so a deal team never
mistakes it for sourced live data.
"""
from __future__ import annotations

import html as _html
from typing import List, Optional

from ..pe_intelligence.reimbursement_cliff_calendar_2026_2029 import (
    CLIFF_CALENDAR,
    CliffEvent,
    analyze_cliff_exposure,
    scan_cliff_calendar_for_deal,
)
from ._chartis_kit import (
    P,
    chartis_shell,
    ck_illustrative_note,
    ck_kpi_block,
    ck_page_title,
    ck_panel,
    ck_section_header,
    ck_source_purpose,
)

# Distinct subsectors present in the curated calendar (sorted, display-cased).
_SUBSECTORS: List[str] = sorted({s for ev in CLIFF_CALENDAR for s in ev.subsectors})
_DEFAULT_SUBSECTOR = "hospital_general"
_MIN_YEAR = min(ev.effective_year for ev in CLIFF_CALENDAR)
_MAX_YEAR = max(ev.effective_year for ev in CLIFF_CALENDAR)


def _label(subsector: str) -> str:
    return subsector.replace("_", " ").title()


def _bps(v: float) -> str:
    """Rate change in basis points, signed, no decimals (bps are integers)."""
    return f"{v:+.0f} bps"


def _pct(bps: float) -> str:
    """Same exposure expressed as a percentage, 1 decimal (house rule)."""
    return f"{bps / 100.0:+.1f}%"


def _subsector_chips(active: str, hold_start: int, hold_years: int) -> str:
    chips = []
    for s in _SUBSECTORS:
        on = s == active
        chips.append(
            f'<a href="/diligence/cliff-calendar?subsector={_html.escape(s)}'
            f'&hold_start={hold_start}&hold_years={hold_years}" '
            f'style="display:inline-block;font-family:var(--ck-mono);font-size:11px;'
            f'padding:5px 10px;margin:0 6px 6px 0;border-radius:3px;'
            f'text-decoration:none;border:1px solid '
            f'{P["accent"] if on else P["border"]};'
            f'background:{P["accent"] if on else P["panel"]};'
            f'color:{"#fff" if on else P["text_dim"]};">'
            f'{_html.escape(_label(s))}</a>'
        )
    return f'<div style="margin:10px 0 14px;">{"".join(chips)}</div>'


def _year_chips(active_subsector: str, hold_start: int, hold_years: int) -> str:
    chips = []
    for y in range(_MIN_YEAR, _MAX_YEAR + 1):
        on = y == hold_start
        chips.append(
            f'<a href="/diligence/cliff-calendar?subsector={_html.escape(active_subsector)}'
            f'&hold_start={y}&hold_years={hold_years}" '
            f'style="display:inline-block;font-family:var(--ck-mono);font-size:11px;'
            f'padding:4px 9px;margin:0 5px 5px 0;border-radius:3px;text-decoration:none;'
            f'border:1px solid {P["accent"] if on else P["border"]};'
            f'background:{P["accent"] if on else P["panel"]};'
            f'color:{"#fff" if on else P["text_dim"]};">{y}</a>'
        )
    return (
        f'<div style="margin:2px 0 14px;"><span style="font-family:var(--ck-mono);'
        f'font-size:10px;letter-spacing:0.1em;color:{P["text_faint"]};'
        f'text-transform:uppercase;margin-right:8px;">Hold start</span>'
        f'{"".join(chips)}</div>'
    )


def _calendar_row(ev: CliffEvent, in_hold: bool) -> str:
    flag = (
        f'<span style="font-family:var(--ck-mono);font-size:9.5px;font-weight:700;'
        f'color:{P["accent"]};">IN HOLD</span>'
        if in_hold else
        f'<span style="font-family:var(--ck-mono);font-size:9.5px;'
        f'color:{P["text_faint"]};">—</span>'
    )
    return (
        f'<tr style="border-bottom:1px solid {P["border_dim"]};'
        f'{"background:"+P["panel"]+";" if in_hold else ""}">'
        f'<td style="padding:7px 10px;font-family:var(--ck-mono);font-size:11px;'
        f'color:{P["text"]};">{ev.effective_year}</td>'
        f'<td style="padding:7px 10px;font-size:12px;color:{P["text"]};">'
        f'{_html.escape(ev.name)}</td>'
        f'<td style="padding:7px 10px;font-family:var(--ck-mono);font-size:10.5px;'
        f'color:{P["text_dim"]};text-transform:uppercase;">'
        f'{_html.escape(ev.affected_payer)}</td>'
        f'<td style="padding:7px 10px;font-family:var(--ck-mono);font-size:11px;'
        f'text-align:right;color:{P["negative"] if ev.rate_change_bps < 0 else P["text"]};'
        f'font-variant-numeric:tabular-nums;">{_bps(ev.rate_change_bps)}</td>'
        f'<td style="padding:7px 10px;font-size:11px;color:{P["text_dim"]};'
        f'line-height:1.5;">{_html.escape(ev.partner_note)}</td>'
        f'<td style="padding:7px 10px;text-align:center;">{flag}</td>'
        f'</tr>'
    )


def _cliff_timeline_svg(report, width: int = 680) -> str:
    """The hold period as a picture: one lollipop per cliff event on
    the hold-year axis — drop length ∝ the bps cut, color by payer,
    cumulative bps annotated at the end. Empty hold → empty string."""
    hits = report.hits
    if not hits:
        return ""
    payer_tone = {"medicare": "#0b2341", "medicaid": "#1F7A75",
                  "commercial": "#b8732a", "340b": "#a98545"}
    years = list(range(report.hold_start_year, report.hold_end_year + 1))
    n_years = max(len(years) - 1, 1)
    pad_l, pad_r, base_y = 50, 120, 36
    pw = width - pad_l - pad_r
    max_bps = max(abs(h.event.rate_change_bps) for h in hits) or 1
    drop_max = 86
    h_total = base_y + drop_max + 44
    parts = [f'<svg width="{width}" height="{h_total}" '
             'xmlns="http://www.w3.org/2000/svg" role="img" '
             'aria-label="Reimbursement cliffs across the hold">']
    # axis
    parts.append(
        f'<line x1="{pad_l}" y1="{base_y}" x2="{pad_l+pw}" '
        f'y2="{base_y}" stroke="#7a8699" stroke-width="1"/>')
    for i, yr in enumerate(years):
        x = pad_l + (i / n_years) * pw
        parts.append(
            f'<line x1="{x:.1f}" y1="{base_y-3}" x2="{x:.1f}" '
            f'y2="{base_y+3}" stroke="#7a8699"/>'
            f'<text x="{x:.1f}" y="{base_y-8}" text-anchor="middle" '
            'font-family="monospace" font-size="10" fill="#465366">'
            f'{yr}</text>')
    # lollipops — jitter same-year events horizontally so they don't
    # overprint
    seen_years: dict = {}
    for hit in sorted(hits, key=lambda h: h.event.effective_year):
        ev = hit.event
        k = seen_years.get(ev.effective_year, 0)
        seen_years[ev.effective_year] = k + 1
        frac = (ev.effective_year - report.hold_start_year) / n_years
        x = pad_l + frac * pw + k * 9
        drop = abs(ev.rate_change_bps) / max_bps * drop_max
        color = payer_tone.get(ev.affected_payer, "#7a8699")
        parts.append(
            f'<line x1="{x:.1f}" y1="{base_y}" x2="{x:.1f}" '
            f'y2="{base_y+drop:.1f}" stroke="{color}" '
            'stroke-width="2"/>'
            f'<circle cx="{x:.1f}" cy="{base_y+drop:.1f}" r="4" '
            f'fill="{color}"><title>'
            f'{_html.escape(ev.name)} · {ev.effective_year} · '
            f'{ev.rate_change_bps:+,.0f} bps ({ev.affected_payer})'
            '</title></circle>')
    parts.append(
        f'<text x="{pad_l+pw+8}" y="{base_y+14}" '
        'font-family="monospace" font-size="11" fill="#b5321e">'
        f'{report.total_bps_in_hold:+,.0f} bps</text>'
        f'<text x="{pad_l+pw+8}" y="{base_y+27}" '
        'font-family="monospace" font-size="9" fill="#7a8699">'
        'cumulative in hold</text>')
    parts.append('</svg>')
    legend = "".join(
        f'<span style="display:inline-flex;align-items:center;gap:4px;'
        f'margin-right:12px;font-size:10.5px;color:#465366;">'
        f'<span style="width:9px;height:9px;background:{c};'
        f'display:inline-block;"></span>{p_}</span>'
        for p_, c in payer_tone.items())
    return ("".join(parts)
            + f'<div style="margin:2px 0 12px;">{legend}'
            '<span style="font-size:10px;color:#7a8699;">drop length '
            '∝ bps cut · hover a dot for the event</span></div>')


_PAYER_TONE = {"medicare": "#0b2341", "medicaid": "#1F7A75",
               "commercial": "#b8732a", "340b": "#a98545"}


def _exposure_section(report) -> str:
    """Payer-channel decomposition of the in-hold rate cut + the
    cumulative erosion curve. Both recompute from the timeline's
    events, so the concentration read is auditable.

    Stays in basis points (no revenue base assumed) so nothing is
    fabricated — the partner reads which channel carries the cut and
    how it accumulates across the hold."""
    exp = analyze_cliff_exposure(report)
    if not exp.by_payer:
        return ""
    # Payer bars — each channel's total in-hold bps, most-cut first.
    max_bps = max((abs(p.total_bps) for p in exp.by_payer), default=1) or 1
    bar_rows = []
    for p in exp.by_payer:
        tone = _PAYER_TONE.get(p.payer, "#7a8699")
        w = abs(p.total_bps) / max_bps * 100.0
        worst = (f' · worst: {_html.escape(p.worst_event)} '
                 f'({p.worst_bps:+.0f})' if p.worst_event else "")
        bar_rows.append(
            f'<div style="display:grid;grid-template-columns:110px 1fr 92px;'
            f'align-items:center;gap:9px;margin:4px 0;">'
            f'<div style="font-size:11px;color:#1a2332;text-align:right;'
            f'text-transform:capitalize;">{_html.escape(p.payer)}</div>'
            f'<div style="height:13px;background:#ece5d6;border-radius:2px;'
            f'overflow:hidden;"><div style="height:100%;width:{w:.0f}%;'
            f'background:{tone};"></div></div>'
            f'<div style="font-family:var(--sc-mono,monospace);font-size:11px;'
            f'color:{tone};text-align:right;font-variant-numeric:tabular-nums;">'
            f'{p.total_bps:+.0f} bps</div>'
            f'<div style="grid-column:2/4;font-size:9.5px;color:#7a8699;'
            f'margin:-2px 0 2px;">{p.event_count} event'
            f'{"s" if p.event_count != 1 else ""}{worst}</div>'
            f'</div>')
    # Cumulative erosion curve — relative-year running total.
    curve = ""
    if exp.cumulative_by_relative_year:
        pts = exp.cumulative_by_relative_year
        chips = " → ".join(
            f'<span style="font-family:var(--sc-mono,monospace);">Y{y}: '
            f'{b:+.0f}</span>' for y, b in pts)
        curve = (
            f'<p style="font-size:11px;color:#465366;margin:8px 0 0;">'
            f'<span style="color:#7a8699;">Cumulative erosion (bps, '
            f'running): </span>{chips}</p>')
    dom = ""
    if exp.dominant_payer:
        dom = (
            f'<span style="font-family:var(--sc-mono,monospace);font-size:10px;'
            f'letter-spacing:0.08em;color:{_PAYER_TONE.get(exp.dominant_payer, "#7a8699")};'
            f'margin-left:8px;">{exp.dominant_payer.upper()} '
            f'{exp.dominant_share*100:.0f}% OF CUT</span>')
    return ck_panel(
        f'<p class="ck-section-body" style="font-size:12px;margin:0 0 8px;'
        f'line-height:1.6;">{_html.escape(exp.note)}</p>'
        + "".join(bar_rows) + curve
        + '<p style="font-size:9.5px;color:#7a8699;margin:8px 0 0;">'
        'Per-payer totals and the cumulative curve sum the timeline events '
        'above — basis points only, no revenue base assumed.</p>',
        title=f'Payer-channel exposure{dom}',
    )


def render_cliff_calendar_page(
    subsector: str = "",
    hold_start: int = _MIN_YEAR,
    hold_years: int = 5,
) -> str:
    """Render the reimbursement cliff calendar for a chosen subsector + hold."""
    subsector = subsector if subsector in _SUBSECTORS else _DEFAULT_SUBSECTOR
    if hold_start < _MIN_YEAR or hold_start > _MAX_YEAR + 5:
        hold_start = _MIN_YEAR
    hold_years = hold_years if 1 <= hold_years <= 10 else 5

    report = scan_cliff_calendar_for_deal(subsector, hold_start, hold_years)
    in_hold_ids = {h.event.id for h in report.hits}

    # Value-anchor: lead with the computed in-hold rate exposure for the
    # selected subsector (the real metric this tool produces).
    worst = min((h.event.rate_change_bps for h in report.hits), default=0.0)
    worst_ev = next((h.event for h in report.hits
                     if h.event.rate_change_bps == worst), None)
    kpis = (
        ck_kpi_block(
            "In-hold rate exposure",
            _pct(report.total_bps_in_hold),
            f"{_bps(report.total_bps_in_hold)} · {_label(subsector)}",
        )
        + ck_kpi_block(
            "Cliff events in hold",
            str(len(report.hits)),
            f"hold {report.hold_start_year}–{report.hold_end_year}",
        )
        + ck_kpi_block(
            "Largest single cut",
            _pct(worst) if worst_ev else "0.0%",
            _html.escape(worst_ev.name) if worst_ev else "no events",
        )
        + ck_kpi_block(
            "Calendar coverage",
            f"{_MIN_YEAR}–{_MAX_YEAR}",
            f"{len(CLIFF_CALENDAR)} events · {len(_SUBSECTORS)} subsectors",
        )
    )

    source_purpose = ck_source_purpose(
        purpose=(
            "Scan which known 2026-2029 Medicare / 340B rate events land inside "
            "a deal's hold window for a given subsector, so the base case prices "
            "post-cut rates rather than today's."
        ),
        universe="derived",
        confidence="illustrative",
        source="Curated regulatory calendar (OBBBA, sequestration, site-neutral "
               "HOPD, PAMA, PDGM, PDPM, 340B, DME competitive bid, wage index) — "
               "partner-judgment magnitudes, refresh as rules finalize",
        next_action="Compare subsectors",
        next_href="/diligence/cliff-calendar?subsector=ambulatory_surgery_center",
    )

    full_rows = "".join(
        _calendar_row(ev, ev.id in in_hold_ids)
        for ev in sorted(CLIFF_CALENDAR, key=lambda e: (e.effective_year, e.name))
    )
    _table_inner = (
        f'<div style="overflow-x:auto;">'
        f'<table style="width:100%;border-collapse:collapse;">'
        f'<thead><tr style="border-bottom:2px solid {P["border"]};text-align:left;">'
        f'<th style="padding:7px 10px;font-family:var(--ck-mono);font-size:9.5px;'
        f'letter-spacing:0.08em;color:{P["text_faint"]};text-transform:uppercase;">Year</th>'
        f'<th style="padding:7px 10px;font-family:var(--ck-mono);font-size:9.5px;'
        f'letter-spacing:0.08em;color:{P["text_faint"]};text-transform:uppercase;">Event</th>'
        f'<th style="padding:7px 10px;font-family:var(--ck-mono);font-size:9.5px;'
        f'letter-spacing:0.08em;color:{P["text_faint"]};text-transform:uppercase;">Payer</th>'
        f'<th style="padding:7px 10px;font-family:var(--ck-mono);font-size:9.5px;'
        f'letter-spacing:0.08em;color:{P["text_faint"]};text-transform:uppercase;'
        f'text-align:right;">Rate</th>'
        f'<th style="padding:7px 10px;font-family:var(--ck-mono);font-size:9.5px;'
        f'letter-spacing:0.08em;color:{P["text_faint"]};text-transform:uppercase;">Partner note</th>'
        f'<th style="padding:7px 10px;font-family:var(--ck-mono);font-size:9.5px;'
        f'letter-spacing:0.08em;color:{P["text_faint"]};text-transform:uppercase;'
        f'text-align:center;">In hold</th>'
        f'</tr></thead><tbody>{full_rows}</tbody></table></div>'
    )
    table = ck_panel(
        _table_inner,
        title=(f"Full calendar — highlighted rows hit the {_label(subsector)} "
               f"hold ({report.hold_start_year}–{report.hold_end_year})"),
    )

    # 2026-05-28 batch 31 · Tier-4 trope removal — drops decorative
    # 3px accent stripe; caps radius at 2px.
    partner_note = (
        f'<div style="background:{P["panel"]};border:1px solid {P["border"]};'
        f'border-radius:2px;padding:12px 14px;'
        f'margin-top:14px;"><div style="font-family:var(--ck-mono);font-size:9.5px;'
        f'letter-spacing:0.12em;color:{P["text_faint"]};text-transform:uppercase;'
        f'margin-bottom:5px;">Partner read</div>'
        f'<div style="color:{P["text"]};font-size:12.5px;line-height:1.55;">'
        f'{_html.escape(report.partner_note)}</div></div>'
    )

    body = (
        ck_page_title(
            "Reimbursement Cliff Calendar",
            eyebrow="DILIGENCE · REGULATORY",
            meta=f"{len(CLIFF_CALENDAR)} events · {_MIN_YEAR}–{_MAX_YEAR} "
                 f"· {_label(subsector)} · hold {report.hold_start_year}"
                 f"–{report.hold_end_year}",
        )
        + ck_illustrative_note("rate-change magnitudes (real named events, "
                               "partner-judgment bps)")
        + source_purpose
        + _subsector_chips(subsector, hold_start, hold_years)
        + _year_chips(subsector, hold_start, hold_years)
        + f'<div class="ck-kpi-grid">{kpis}</div>'
        + _cliff_timeline_svg(report)
        + _exposure_section(report)
        + ck_section_header("CALENDAR", "every modeled event; hold-window hits "
                            "highlighted", count=len(CLIFF_CALENDAR))
        + table
        + partner_note
    )

    # 2026-05-28 wave-B: ck_page_actions adds Copy share link
    # + Back-to-top affordances. Idempotent JS guards.
    from ._chartis_kit import ck_page_actions
    body = body + ck_page_actions()
    return chartis_shell(
        body,
        title="Reimbursement Cliff Calendar",
        active_nav="/diligence",
    )
