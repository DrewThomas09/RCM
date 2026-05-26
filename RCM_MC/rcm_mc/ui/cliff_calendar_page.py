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
    scan_cliff_calendar_for_deal,
)
from ._chartis_kit import (
    P,
    chartis_shell,
    ck_illustrative_note,
    ck_kpi_block,
    ck_page_title,
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
    table = (
        f'<div class="ck-panel"><div class="ck-panel-title">'
        f'Full calendar — highlighted rows hit the {_label(subsector)} hold '
        f'({report.hold_start_year}–{report.hold_end_year})</div>'
        f'<div style="overflow-x:auto;padding:4px 6px;">'
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
        f'</tr></thead><tbody>{full_rows}</tbody></table></div></div>'
    )

    partner_note = (
        f'<div style="background:{P["panel"]};border:1px solid {P["border"]};'
        f'border-left:3px solid {P["accent"]};border-radius:3px;padding:12px 14px;'
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
        + ck_section_header("CALENDAR", "every modeled event; hold-window hits "
                            "highlighted", count=len(CLIFF_CALENDAR))
        + table
        + partner_note
    )

    return chartis_shell(
        body,
        title="Reimbursement Cliff Calendar",
        active_nav="/diligence",
    )
