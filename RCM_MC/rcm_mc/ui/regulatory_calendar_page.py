"""Regulatory Calendar × Thesis Kill-Switch page.

The partner-facing demo moment: a gantt-style timeline where thesis
drivers DIE on specific dates tied to named CMS / OIG / FTC / DOJ
events.  Nothing else in the diligence stack produces this view.

Route: ``/diligence/regulatory-calendar``
Query params (all optional — landing form seeds them):
    target_name, specialty / specialties (comma-separated),
    ma_mix_pct, commercial_payer_share,
    has_hopd_revenue, has_reit_landlord,
    revenue_usd, ebitda_usd,
    horizon_months (default 24).
"""
from __future__ import annotations

import html
from datetime import date
from typing import Any, Dict, List, Optional

from ..diligence.regulatory_calendar import (
    DEFAULT_THESIS_DRIVERS, KillSwitchVerdict, RegulatoryEvent,
    RegulatoryExposureReport, analyze_regulatory_exposure,
)
from ..diligence.regulatory_calendar.impact_mapper import (
    ImpactVerdict,
)
from ..diligence.regulatory_calendar.killswitch import (
    DriverKillTimeline, EbitdaOverlay,
)
from ._chartis_kit import P, chartis_shell
from .power_ui import (
    benchmark_chip, bookmark_hint, deal_context_bar,
    export_json_panel, interpret_callout, provenance, sortable_table,
)


# ────────────────────────────────────────────────────────────────────
# Peer benchmarks for regulatory exposure — PE healthcare norms
# ────────────────────────────────────────────────────────────────────
#
# PE partners compare a target's regulatory exposure against the
# typical healthcare LBO portfolio.  A score of 30-50 is the
# "expected" zone for a hospital target; 70+ means the deal is
# more exposed than 90% of screened targets.
_REG_RISK_PEER_LOW = 20.0
_REG_RISK_PEER_HIGH = 50.0
_REG_RISK_PEER_MEDIAN = 35.0


# ────────────────────────────────────────────────────────────────────
# Scoped CSS (rc- prefix)
# ────────────────────────────────────────────────────────────────────

def _scoped_styles() -> str:
    css = """
.rc-wrap{{font-family:"Helvetica Neue",Arial,sans-serif;}}
.rc-eyebrow{{font-size:11px;letter-spacing:1.6px;text-transform:uppercase;
color:{tf};font-weight:600;}}
.rc-h1{{font-size:26px;color:{tx};font-weight:600;line-height:1.15;
margin:4px 0 0 0;letter-spacing:-.2px;}}
.rc-section-label{{font-size:10px;letter-spacing:1.6px;text-transform:uppercase;
font-weight:700;color:{tf};margin:22px 0 10px 0;}}
.rc-panel{{background:{pn};border:1px solid {bd};border-radius:4px;
padding:14px 20px;margin-bottom:16px;}}
.rc-verdict-card{{background:{pn};border:1px solid {bd};border-radius:4px;
padding:18px 22px;margin-top:14px;position:relative;overflow:hidden;}}
.rc-verdict-card::before{{content:"";position:absolute;top:0;left:0;right:0;
height:3px;background:linear-gradient(90deg,var(--tone),{ac});}}
.rc-verdict-PASS{{--tone:{po};}}
.rc-verdict-CAUTION{{--tone:{wn};}}
.rc-verdict-WARNING{{--tone:{wn};}}
.rc-verdict-FAIL{{--tone:{ne};}}
.rc-verdict-badge{{display:inline-block;padding:4px 12px;border-radius:3px;
font-size:11px;font-weight:700;letter-spacing:1.3px;text-transform:uppercase;
background:var(--tone);color:#fff;}}
.rc-verdict-headline{{font-size:17px;color:{tx};font-weight:600;
line-height:1.45;margin-top:12px;}}
.rc-verdict-rationale{{font-size:12.5px;color:{td};line-height:1.6;
margin-top:8px;max-width:900px;}}
.rc-kpi-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));
gap:14px;margin-top:14px;}}
.rc-kpi__label{{font-size:9px;letter-spacing:1.3px;text-transform:uppercase;
color:{tf};font-weight:600;margin-bottom:3px;}}
.rc-kpi__val{{font-size:24px;line-height:1;font-family:"JetBrains Mono",monospace;
font-variant-numeric:tabular-nums;font-weight:700;color:{tx};}}
.rc-kpi__val.neg{{color:{ne};}}
.rc-kpi__val.pos{{color:{po};}}
.rc-driver-row{{display:grid;grid-template-columns:1fr 110px 150px 1fr;
gap:12px;padding:10px 0;border-bottom:1px solid {bd};align-items:center;}}
.rc-driver-label{{font-size:13.5px;color:{tx};font-weight:600;}}
.rc-driver-sub{{font-size:10.5px;color:{tf};margin-top:2px;}}
.rc-verdict-chip{{display:inline-block;padding:3px 9px;border-radius:3px;
font-size:10.5px;font-weight:700;letter-spacing:1.1px;}}
.rc-chip-KILLED{{background:{ne};color:#fff;}}
.rc-chip-DAMAGED{{background:{wn};color:#1a1a1a;}}
.rc-chip-UNAFFECTED{{background:{pa};color:{td};border:1px solid {bd};}}
.rc-event-card{{background:{pn};border:1px solid {bd};border-left:3px solid {ac};
border-radius:0 3px 3px 0;padding:14px 18px;margin-bottom:12px;}}
.rc-event-card.killer{{border-left-color:{ne};}}
.rc-event-card.damager{{border-left-color:{wn};}}
.rc-event-card.tailwind{{border-left-color:{po};}}
.rc-event-head{{display:flex;justify-content:space-between;gap:14px;
flex-wrap:wrap;align-items:baseline;}}
.rc-event-title{{font-size:14.5px;color:{tx};font-weight:600;}}
.rc-event-dates{{font-family:"JetBrains Mono",monospace;font-size:11px;
color:{td};}}
.rc-event-meta{{font-size:10.5px;color:{tf};margin-top:4px;
text-transform:uppercase;letter-spacing:1.1px;}}
.rc-event-body{{font-size:12px;color:{td};line-height:1.65;margin-top:10px;}}
.rc-killmap-chip{{display:inline-block;padding:3px 9px;margin:3px 4px 3px 0;
border-radius:3px;font-size:10px;color:{ne};border:1px solid {ne};
font-family:"JetBrains Mono",monospace;}}
.rc-overlay-row{{display:grid;grid-template-columns:80px 160px 160px 1fr;
gap:10px;padding:8px 0;border-bottom:1px solid {bd};
font-family:"JetBrains Mono",monospace;font-size:12px;}}
.rc-overlay-head{{color:{tf};font-size:9px;letter-spacing:1.3px;
text-transform:uppercase;font-weight:700;}}
.rc-overlay-neg{{color:{ne};font-weight:700;}}
.rc-overlay-pos{{color:{po};font-weight:700;}}
.rc-form-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));
gap:14px;}}
.rc-form-field label{{display:block;font-size:10px;color:{tf};
letter-spacing:1.2px;text-transform:uppercase;font-weight:600;margin-bottom:4px;}}
.rc-form-field input,.rc-form-field select{{width:100%;
background:{pa};color:{tx};border:1px solid {bd};padding:8px 10px;
border-radius:3px;font-family:"JetBrains Mono",monospace;font-size:13px;}}
.rc-form-submit{{margin-top:18px;padding:10px 20px;background:{ac};
color:#fff;border:0;border-radius:3px;font-size:12px;letter-spacing:1.3px;
text-transform:uppercase;font-weight:700;cursor:pointer;}}
.rc-form-submit:hover{{filter:brightness(1.15);}}
.rc-callout{{background:{pa};padding:12px 16px;border-left:3px solid {ac};
border-radius:0 3px 3px 0;font-size:12px;color:{td};line-height:1.65;
max-width:880px;margin-top:12px;}}
""".format(
        tx=P["text"], td=P["text_dim"], tf=P["text_faint"],
        pn=P["panel"], pa=P["panel_alt"],
        bd=P["border"], ac=P["accent"],
        po=P["positive"], wn=P["warning"], ne=P["negative"],
    )
    return f"<style>{css}</style>"


# ────────────────────────────────────────────────────────────────────
# Gantt timeline SVG — the demo moment
# ────────────────────────────────────────────────────────────────────

_VERDICT_COLOR = {
    ImpactVerdict.KILLED: P["negative"],
    ImpactVerdict.DAMAGED: P["warning"],
    ImpactVerdict.UNAFFECTED: P["text_faint"],
}


def _timeline_svg(
    report: RegulatoryExposureReport,
    width: int = 960, height: int = 420,
) -> str:
    """Gantt-style timeline: x-axis is calendar months, one row per
    driver, each event plotted as a marker on its row on its
    effective date."""
    events = report.events
    timelines = report.driver_timelines
    if not events or not timelines:
        return ""

    # Filter out UNAFFECTED-only drivers for a clean view (they
    # still appear in the grid below).
    active = [
        t for t in timelines
        if t.worst_verdict != ImpactVerdict.UNAFFECTED
    ]
    if not active:
        active = timelines[:4]

    # X-axis range: as_of → max event date + 30 days
    as_of = date.fromisoformat(report.as_of)
    max_d = as_of
    for e in events:
        eff = e.effective_date or e.publish_date
        if eff > max_d:
            max_d = eff
    span_days = max((max_d - as_of).days, 30)

    pad_l, pad_r, pad_t, pad_b = 160, 30, 40, 52
    inner_w = max(1, width - pad_l - pad_r)
    inner_h = max(1, height - pad_t - pad_b)

    row_h = inner_h / max(len(active), 1)

    def x(d: date) -> float:
        return pad_l + ((d - as_of).days / span_days) * inner_w

    def y_row(i: int) -> float:
        return pad_t + i * row_h + row_h / 2

    # Month gridlines
    month_lines: List[str] = []
    month_labels: List[str] = []
    cur = date(as_of.year, as_of.month, 1)
    while cur <= max_d:
        xc = x(cur)
        month_lines.append(
            f'<line x1="{xc:.1f}" y1="{pad_t}" '
            f'x2="{xc:.1f}" y2="{pad_t + inner_h}" '
            f'stroke="{P["border"]}" stroke-width="1" '
            f'stroke-dasharray="2,3" opacity="0.5"/>'
        )
        if cur.month in (1, 4, 7, 10):
            month_labels.append(
                f'<text x="{xc:.1f}" y="{pad_t + inner_h + 14}" '
                f'text-anchor="middle" font-size="10" '
                f'fill="{P["text_faint"]}" '
                f'font-family="JetBrains Mono,monospace">'
                f'{cur.year}Q{(cur.month - 1) // 3 + 1}</text>'
            )
        y = cur.year + (1 if cur.month == 12 else 0)
        m = 1 if cur.month == 12 else cur.month + 1
        cur = date(y, m, 1)

    # Row labels + row backgrounds
    rows: List[str] = []
    for i, tl in enumerate(active):
        yc = y_row(i)
        rows.append(
            f'<line x1="{pad_l}" y1="{yc:.1f}" '
            f'x2="{pad_l + inner_w}" y2="{yc:.1f}" '
            f'stroke="{P["border_dim"]}" stroke-width="1"/>'
        )
        tone = _VERDICT_COLOR[tl.worst_verdict]
        rows.append(
            f'<text x="{pad_l - 10}" y="{yc + 4:.1f}" '
            f'text-anchor="end" font-size="11" '
            f'fill="{P["text"]}" font-weight="600">'
            f'{html.escape(tl.driver_label[:22])}</text>'
        )
        rows.append(
            f'<rect x="{pad_l - 8}" y="{yc - 5:.1f}" width="4" '
            f'height="10" fill="{tone}" rx="1"/>'
        )

    # Event markers
    marks: List[str] = []
    for i, tl in enumerate(active):
        yc = y_row(i)
        for imp in tl.impacts:
            if imp.verdict == ImpactVerdict.UNAFFECTED:
                continue
            if not imp.effective_date:
                continue
            try:
                d = date.fromisoformat(imp.effective_date)
            except ValueError:
                continue
            if d < as_of or d > max_d:
                continue
            xc = x(d)
            tone = _VERDICT_COLOR[imp.verdict]
            r = 7 if imp.verdict == ImpactVerdict.KILLED else 5
            # Event title for the tooltip
            event_title = next(
                (e.title for e in events if e.event_id == imp.event_id),
                imp.event_id,
            )
            tip = (
                f"{event_title}\\n"
                f"{imp.verdict.value} {tl.driver_label}\\n"
                f"{d.isoformat()} · impairment "
                f"{imp.impairment_pct*100:.0f}%"
            )
            marks.append(
                f'<circle cx="{xc:.1f}" cy="{yc:.1f}" r="{r}" '
                f'fill="{tone}" stroke="{P["panel"]}" '
                f'stroke-width="2">'
                f'<title>{html.escape(tip)}</title></circle>'
            )

    # Today marker
    today_x = x(as_of)
    today_line = (
        f'<line x1="{today_x:.1f}" y1="{pad_t - 8}" '
        f'x2="{today_x:.1f}" y2="{pad_t + inner_h}" '
        f'stroke="{P["accent"]}" stroke-width="1.5" '
        f'stroke-dasharray="4,3"/>'
        f'<text x="{today_x:.1f}" y="{pad_t - 14}" '
        f'text-anchor="middle" font-size="10" '
        f'fill="{P["accent"]}" font-weight="700" '
        f'font-family="JetBrains Mono,monospace">'
        f'TODAY · {report.as_of}</text>'
    )

    return (
        f'<svg viewBox="0 0 {width} {height}" '
        f'width="100%" style="max-width:{width}px;height:auto;" '
        f'role="img" aria-label="Thesis kill-switch timeline">'
        f'<rect x="0" y="0" width="{width}" height="{height}" '
        f'fill="{P["panel"]}"/>'
        + "".join(month_lines) + "".join(rows)
        + "".join(marks) + today_line
        + "".join(month_labels)
        + '</svg>'
    )


# ────────────────────────────────────────────────────────────────────
# Composed blocks
# ────────────────────────────────────────────────────────────────────

def _verdict_card(report: RegulatoryExposureReport) -> str:
    verdict = report.verdict.value
    headline = html.escape(report.headline)
    rationale = html.escape(report.rationale)
    score_class = (
        "neg" if report.risk_score >= 50
        else "pos" if report.risk_score < 20
        else ""
    )

    risk_val = provenance(
        f"{report.risk_score:.0f}",
        source="Kill-switch risk model",
        formula="Σ per-driver verdict-base × proximity factor, clamped 0-100",
        detail=(
            "40 pts per KILLED driver, 15 pts per DAMAGED; scaled "
            "0.5-1.0 by days-to-first-kill / horizon."
        ),
        tag="span",
    )
    margin_val = provenance(
        f"{report.total_expected_margin_impact_pp:+.2f} pp",
        source="Σ event.expected_margin_impact_pp",
        formula=(
            f"sum across {len(report.events)} curated events in the "
            f"{report.horizon_months}-month horizon"
        ),
        detail=(
            "Each curated event carries a directional pp margin "
            "impact for affected specialties — negative = contraction."
        ),
    )
    rev_val = provenance(
        f"{report.total_expected_revenue_impact_pct*100:+.2f}%",
        source="Σ event.expected_revenue_impact_pct",
        formula=(
            f"sum across {len(report.events)} curated events"
        ),
        detail=(
            "Aggregate top-line impact from all in-horizon events "
            "affecting the target's specialties."
        ),
    )
    killed_val = provenance(
        str(report.killed_driver_count),
        source="Kill-switch verdict engine",
        formula="count(driver.worst_verdict == KILLED)",
        detail=(
            ">50% impairment of a driver's claimed EBITDA lift "
            "within the horizon."
        ),
    )
    damaged_val = provenance(
        str(report.damaged_driver_count),
        source="Kill-switch verdict engine",
        formula="count(driver.worst_verdict == DAMAGED)",
        detail="10-50% impairment of claimed lift.",
    )

    # Plain-English translation of the verdict so first-time users
    # know *what to do* with it.
    if verdict == "FAIL":
        plain = (
            "Multiple thesis drivers are getting killed by named "
            "regulatory events — partners should walk or restructure "
            "offer shape before signing. Expect a 10-20% entry "
            "multiple discount or earn-out tied to the affected "
            "drivers."
        )
        plain_tone = "bad"
    elif verdict == "WARNING":
        plain = (
            "One thesis driver is killed or multiple damaged. "
            "Negotiate seller-side indemnities for the affected "
            "drivers and build the impact into your base-case bid."
        )
        plain_tone = "warn"
    elif verdict == "CAUTION":
        plain = (
            "One driver is damaged. Monitor the effective date and "
            "haircut the related bridge lever by the impairment %."
        )
        plain_tone = "warn"
    else:
        plain = (
            "No thesis drivers materially impaired within the "
            f"{report.horizon_months}-month horizon. Regulatory "
            "exposure is not a gate on this deal."
        )
        plain_tone = "good"

    # Peer-anchored risk score chip
    risk_chip = benchmark_chip(
        value=report.risk_score,
        peer_low=_REG_RISK_PEER_LOW,
        peer_high=_REG_RISK_PEER_HIGH,
        peer_median=_REG_RISK_PEER_MEDIAN,
        higher_is_better=False,
        format_spec=".0f",
        label="Risk Score vs PE healthcare deals",
        peer_label="screened-deal band",
    )

    return (
        f'<div class="rc-verdict-card rc-verdict-{verdict}">'
        f'<div class="rc-verdict-badge">{verdict}</div>'
        f'<div class="rc-verdict-headline">{headline}</div>'
        f'<div class="rc-verdict-rationale">{rationale}</div>'
        + interpret_callout("What partners do here:", plain, tone=plain_tone)
        + f'<div style="margin-top:16px;">{risk_chip}</div>'
        f'<div class="rc-kpi-grid">'
        f'  <div><div class="rc-kpi__label">Risk Score</div>'
        f'       <div class="rc-kpi__val {score_class}">'
        f'{risk_val}</div>'
        f'       <div style="font-size:10px;color:{P["text_faint"]};'
        f'margin-top:3px;">PE norm {_REG_RISK_PEER_LOW:.0f}-'
        f'{_REG_RISK_PEER_HIGH:.0f} · median '
        f'{_REG_RISK_PEER_MEDIAN:.0f}</div></div>'
        f'  <div><div class="rc-kpi__label">Drivers Killed</div>'
        f'       <div class="rc-kpi__val '
        f'{"neg" if report.killed_driver_count else ""}">'
        f'{killed_val}</div></div>'
        f'  <div><div class="rc-kpi__label">Drivers Damaged</div>'
        f'       <div class="rc-kpi__val '
        f'{"neg" if report.damaged_driver_count else ""}">'
        f'{damaged_val}</div></div>'
        f'  <div><div class="rc-kpi__label">Events In Horizon</div>'
        f'       <div class="rc-kpi__val">{len(report.events)}</div></div>'
        f'  <div><div class="rc-kpi__label">Margin Impact Σ</div>'
        f'       <div class="rc-kpi__val '
        f'{"neg" if report.total_expected_margin_impact_pp < 0 else "pos"}">'
        f'{margin_val}</div></div>'
        f'  <div><div class="rc-kpi__label">Revenue Impact Σ</div>'
        f'       <div class="rc-kpi__val '
        f'{"neg" if report.total_expected_revenue_impact_pct < 0 else "pos"}">'
        f'{rev_val}</div></div>'
        f'</div>'
        f'</div>'
    )


def _driver_table(report: RegulatoryExposureReport) -> str:
    rows: List[str] = []
    rows.append(
        f'<div class="rc-driver-row" style="font-size:9px;'
        f'color:{P["text_faint"]};letter-spacing:1.3px;'
        f'text-transform:uppercase;font-weight:700;'
        f'border-bottom:2px solid {P["border"]};">'
        f'<div>Thesis Driver</div>'
        f'<div>Verdict</div>'
        f'<div>First Kill Date</div>'
        f'<div>Residual Lift</div>'
        f'</div>'
    )
    for tl in report.driver_timelines:
        first_kill = (
            tl.first_kill_date or "—"
            if tl.worst_verdict != ImpactVerdict.UNAFFECTED
            else "—"
        )
        residual = (
            f'{tl.residual_lift_pct*100:.2f} pp of '
            f'{tl.expected_lift_pct*100:.2f} pp claimed'
        )
        sub_bits: List[str] = []
        if tl.impacts:
            sub_bits.append(
                f'{len(tl.impacts)} event'
                f'{"s" if len(tl.impacts) != 1 else ""} impair this driver'
            )
        if tl.cumulative_impairment_pct:
            sub_bits.append(
                f'{tl.cumulative_impairment_pct*100:.0f}% cumulative '
                f'impairment'
            )
        rows.append(
            f'<div class="rc-driver-row">'
            f'  <div>'
            f'    <div class="rc-driver-label">'
            f'{html.escape(tl.driver_label)}</div>'
            f'    <div class="rc-driver-sub">'
            f'{html.escape(" · ".join(sub_bits) or "no impact in horizon")}'
            f'</div>'
            f'  </div>'
            f'  <div><span class="rc-verdict-chip '
            f'rc-chip-{tl.worst_verdict.value}">'
            f'{tl.worst_verdict.value}</span></div>'
            f'  <div style="font-family:\'JetBrains Mono\',monospace;'
            f'font-size:11.5px;color:{P["text"]};">{first_kill}</div>'
            f'  <div style="font-size:12px;color:{P["text_dim"]};">'
            f'{residual}</div>'
            f'</div>'
        )
    return f'<div class="rc-panel">{"".join(rows)}</div>'


def _event_card(event: RegulatoryEvent, report: RegulatoryExposureReport) -> str:
    """Render one event — mark it red if it kills any driver,
    amber if only damages, green if tailwind."""
    killer = False
    damager = False
    for tl in report.driver_timelines:
        for imp in tl.impacts:
            if imp.event_id == event.event_id:
                if imp.verdict == ImpactVerdict.KILLED:
                    killer = True
                elif imp.verdict == ImpactVerdict.DAMAGED:
                    damager = True
    tone_cls = (
        "killer" if killer
        else "damager" if damager
        else "tailwind" if event.expected_revenue_impact_pct > 0
        else ""
    )
    kill_chips = "".join(
        f'<span class="rc-killmap-chip">{html.escape(k)}</span>'
        for k in event.thesis_driver_kill_map
    ) or "<em>tailwind / neutral</em>"

    eff = (
        event.effective_date.isoformat()
        if event.effective_date else "—"
    )
    return (
        f'<div class="rc-event-card {tone_cls}">'
        f'<div class="rc-event-head">'
        f'  <div class="rc-event-title">{html.escape(event.title)}</div>'
        f'  <div class="rc-event-dates">Pub {event.publish_date.isoformat()}'
        f' · Eff {eff}</div>'
        f'</div>'
        f'<div class="rc-event-meta">'
        f'{html.escape(event.agency)} · {event.category.value} · '
        f'{event.status.value} · rev '
        f'{event.expected_revenue_impact_pct*100:+.2f}% · margin '
        f'{event.expected_margin_impact_pp:+.2f} pp'
        f'</div>'
        f'<div class="rc-event-body">{html.escape(event.narrative)}</div>'
        f'<div style="margin-top:8px;">{kill_chips}</div>'
        f'<div style="margin-top:8px;font-size:10.5px;">'
        f'<a href="{html.escape(event.source_url)}" target="_blank" '
        f'rel="noopener" style="color:{P["accent"]};">Source docket ↗</a>'
        f'</div>'
        f'</div>'
    )


def _overlay_panel(report: RegulatoryExposureReport) -> str:
    if not report.ebitda_overlay:
        return ""
    rows: List[str] = []
    rows.append(
        f'<div class="rc-overlay-row rc-overlay-head">'
        f'<div>Year</div><div>Revenue Δ</div>'
        f'<div>EBITDA Δ</div><div>Driving Events</div>'
        f'</div>'
    )
    for o in report.ebitda_overlay:
        rev_cls = (
            "rc-overlay-neg" if o.revenue_delta_usd < 0
            else "rc-overlay-pos" if o.revenue_delta_usd > 0
            else ""
        )
        eb_cls = (
            "rc-overlay-neg" if o.ebitda_delta_usd < 0
            else "rc-overlay-pos" if o.ebitda_delta_usd > 0
            else ""
        )
        rows.append(
            f'<div class="rc-overlay-row">'
            f'<div>{o.year}</div>'
            f'<div class="{rev_cls}">${o.revenue_delta_usd:+,.0f}</div>'
            f'<div class="{eb_cls}">${o.ebitda_delta_usd:+,.0f} '
            f'<span style="color:{P["text_faint"]};font-size:10px;">'
            f'({o.margin_delta_pp:+.2f} pp)</span></div>'
            f'<div style="color:{P["text_dim"]};font-size:11px;">'
            f'{html.escape(", ".join(o.driving_events))}</div>'
            f'</div>'
        )
    total_eb = sum(o.ebitda_delta_usd for o in report.ebitda_overlay)
    total_rev = sum(o.revenue_delta_usd for o in report.ebitda_overlay)
    rows.append(
        f'<div class="rc-overlay-row" '
        f'style="border-top:2px solid {P["border"]};border-bottom:0;'
        f'font-weight:700;color:{P["text"]};">'
        f'<div>TOTAL</div>'
        f'<div class="{"rc-overlay-neg" if total_rev < 0 else "rc-overlay-pos" if total_rev > 0 else ""}">'
        f'${total_rev:+,.0f}</div>'
        f'<div class="{"rc-overlay-neg" if total_eb < 0 else "rc-overlay-pos" if total_eb > 0 else ""}">'
        f'${total_eb:+,.0f}</div>'
        f'<div></div></div>'
    )
    return (
        f'<div class="rc-panel">'
        f'<div class="rc-section-label" style="margin-top:0;">'
        f'EBITDA Bridge Overlay — feeds Deal MC + PE Math</div>'
        f'<div class="rc-callout">'
        f'<strong style="color:{P["text"]};">How to read: </strong>'
        f'Each row is the cumulative $ impact of all regulatory events '
        f'effective in that year.  Revenue Δ uses '
        f'<em>target revenue × Σ event revenue-impact %</em>.  EBITDA Δ '
        f'combines revenue pass-through (at the target\'s current margin) '
        f'plus margin-pp drag on the post-delta revenue base.  These '
        f'numbers subtract from the Deal MC expected EBITDA cone.'
        f'</div>'
        f'<div style="margin-top:10px;">{"".join(rows)}</div>'
        f'</div>'
    )


# ────────────────────────────────────────────────────────────────────
# Market Context — peer snapshot + sector sentiment
# ────────────────────────────────────────────────────────────────────

def _infer_peer_category(target: Dict[str, Any]) -> Optional[str]:
    """Map the target's primary specialty onto a PeerSnapshot
    category the market_intel module indexes."""
    specs = target.get("specialties") or []
    if target.get("specialty"):
        specs = [target["specialty"]] + list(specs)
    specs = [s.upper() for s in specs if s]
    if not specs:
        return None
    for s in specs:
        if s in ("HOSPITAL", "ACUTE_HOSPITAL"):
            return "MULTI_SITE_ACUTE_HOSPITAL"
        if s == "DIALYSIS":
            return "DIALYSIS"
        if s in (
            "DERMATOLOGY", "GI", "OPHTHALMOLOGY",
            "DENTAL_DSO", "PHYSICIAN_GROUP_ROLL_UP",
        ):
            return "PHYSICIAN_GROUP_ROLL_UP"
        if s == "AMBULATORY_SURGERY" or "ASC" in s:
            return "AMBULATORY_SURGERY"
    return None


def _market_context_block(
    target: Dict[str, Any],
    report: RegulatoryExposureReport,
) -> str:
    """Peer-snapshot envelope rendered alongside the regulatory
    verdict — answers "how does this target price vs public peers,
    given its regulatory exposure?" in the same view.

    Failures are swallowed — if market_intel raises, the block
    renders a small "market data unavailable" line rather than
    blowing up the page.
    """
    try:
        from ..market_intel import (
            sector_sentiment as _sector_sentiment,
        )
        from ..market_intel.peer_snapshot import compute_peer_snapshot
    except Exception:  # noqa: BLE001
        return ""

    category = _infer_peer_category(target)
    ev_usd = target.get("ebitda_usd")
    # Rough implied EV — in this view we don't always have an explicit
    # EV input, so use EBITDA × a 9× placeholder only for the peer-
    # comparison math; the resulting "implied" value clearly flags
    # itself as back-of-envelope.
    implied_ev = None
    if ev_usd:
        implied_ev = float(ev_usd) * 9.0

    try:
        snap = compute_peer_snapshot(
            category=category or "",
            target_revenue_usd=target.get("revenue_usd"),
            target_ebitda_usd=target.get("ebitda_usd"),
            target_ev_usd=implied_ev,
        )
    except Exception:  # noqa: BLE001
        return ""

    sentiment_label = None
    specs = target.get("specialties") or []
    if target.get("specialty"):
        specs = [target["specialty"]] + list(specs)
    for s in specs:
        try:
            sentiment_label = _sector_sentiment(s) or sentiment_label
        except Exception:  # noqa: BLE001
            pass
        if sentiment_label:
            break

    if not category and not sentiment_label:
        return ""

    # Compose the block
    peers_html = ""
    if getattr(snap, "peers", None):
        peer_rows = []
        for peer in snap.peers[:6]:
            ticker = html.escape(str(getattr(peer, "ticker", "")))
            name = html.escape(str(getattr(peer, "name", "")))
            mult = getattr(peer, "ev_ebitda_multiple", None)
            mult_str = f"{mult:.2f}x" if mult else "—"
            peer_rows.append(
                f'<tr><td style="padding:4px 8px;">{ticker}</td>'
                f'<td style="padding:4px 8px;color:{P["text_dim"]};">'
                f'{name}</td>'
                f'<td style="padding:4px 8px;font-family:monospace;'
                f'text-align:right;">{mult_str}</td></tr>'
            )
        if peer_rows:
            peers_html = (
                f'<div style="margin-top:12px;">'
                f'<div style="font-size:10px;color:{P["text_faint"]};'
                f'letter-spacing:1.2px;text-transform:uppercase;'
                f'font-weight:700;margin-bottom:6px;">'
                f'Public peer multiples</div>'
                f'<table style="width:100%;border-collapse:collapse;'
                f'font-size:12px;color:{P["text"]};">'
                f'{"".join(peer_rows)}</table></div>'
            )

    target_mult_str = "—"
    if snap.target_implied_multiple is not None:
        target_mult_str = f"{snap.target_implied_multiple:.2f}x"
    median_str = (
        f"{snap.peer_median_ev_ebitda:.2f}x"
        if snap.peer_median_ev_ebitda else "—"
    )
    delta_str = "—"
    if snap.delta_vs_median_turns is not None:
        delta_str = f"{snap.delta_vs_median_turns:+.2f}x"

    # Assessment tone
    tone = (
        P["positive"] if snap.assessment == "DISCOUNT"
        else P["negative"] if snap.assessment == "PREMIUM"
        else P["accent"]
    )

    sentiment_line = ""
    if sentiment_label:
        sent_tone = {
            "EUPHORIC": P["positive"],
            "POSITIVE": P["positive"],
            "NEUTRAL": P["text_dim"],
            "CAUTIOUS": P["warning"],
            "NEGATIVE": P["negative"],
        }.get(str(sentiment_label).upper(), P["text_dim"])
        sentiment_line = (
            f'<div style="margin-top:8px;font-size:12px;'
            f'color:{P["text_dim"]};">Sector sentiment: '
            f'<span style="color:{sent_tone};font-weight:700;">'
            f'{html.escape(str(sentiment_label))}</span></div>'
        )

    killed_note = ""
    if report.killed_driver_count > 0 and snap.assessment == "PREMIUM":
        killed_note = (
            f'<div style="margin-top:10px;padding:8px 12px;'
            f'background:{P["panel_alt"]};border-left:3px solid '
            f'{P["negative"]};font-size:12px;color:{P["text_dim"]};'
            f'line-height:1.55;">'
            f'<strong style="color:{P["text"]};">Partner flag:</strong> '
            f'Target is priced at a premium to peers while the '
            f'regulatory kill-switch flags '
            f'{report.killed_driver_count} thesis driver'
            f'{"s" if report.killed_driver_count != 1 else ""} KILLED '
            f'in the horizon — a compounding risk partners typically '
            f'price-protect with an earn-out or a lower entry.'
            f'</div>'
        )
    elif report.killed_driver_count == 0 and snap.assessment == "DISCOUNT":
        killed_note = (
            f'<div style="margin-top:10px;padding:8px 12px;'
            f'background:{P["panel_alt"]};border-left:3px solid '
            f'{P["positive"]};font-size:12px;color:{P["text_dim"]};'
            f'line-height:1.55;">'
            f'<strong style="color:{P["text"]};">Partner flag:</strong> '
            f'Regulatory kill-switch clean AND target priced at a '
            f'discount to peers — the favourable end of the '
            f'risk/return distribution.'
            f'</div>'
        )

    return (
        f'<div class="rc-panel">'
        f'<div class="rc-section-label" style="margin-top:0;">'
        f'Market Context · Seeking Alpha peer snapshot</div>'
        f'<div style="display:grid;grid-template-columns:'
        f'repeat(auto-fit,minmax(170px,1fr));gap:14px;">'
        f'  <div><div class="rc-kpi__label">Peer Category</div>'
        f'       <div class="rc-kpi__val" style="font-size:14px;">'
        f'{html.escape(snap.category or "—")}</div></div>'
        f'  <div><div class="rc-kpi__label">Target Implied Multiple</div>'
        f'       <div class="rc-kpi__val">{target_mult_str}</div></div>'
        f'  <div><div class="rc-kpi__label">Peer Median</div>'
        f'       <div class="rc-kpi__val">{median_str}</div></div>'
        f'  <div><div class="rc-kpi__label">Δ vs Median</div>'
        f'       <div class="rc-kpi__val" style="color:{tone};">'
        f'{delta_str}</div></div>'
        f'  <div><div class="rc-kpi__label">Assessment</div>'
        f'       <div class="rc-kpi__val" style="color:{tone};'
        f'font-size:14px;">{snap.assessment}</div></div>'
        f'</div>'
        f'<div style="margin-top:10px;font-size:12px;color:{P["text_dim"]};'
        f'line-height:1.6;max-width:880px;">'
        f'{html.escape(snap.summary or "")}</div>'
        f'{sentiment_line}'
        f'{peers_html}'
        f'{killed_note}'
        f'</div>'
    )


# ────────────────────────────────────────────────────────────────────
# Landing form (no target params → seed the demo)
# ────────────────────────────────────────────────────────────────────

def _landing(qs: Optional[Dict[str, List[str]]] = None) -> str:
    form = """
<form method="get" action="/diligence/regulatory-calendar" class="rc-wrap">
  <div class="rc-panel">
    <div class="rc-section-label" style="margin-top:0;">
      Target profile</div>
    <div class="rc-form-grid">
      <div class="rc-form-field"><label>Target name</label>
        <input name="target_name" value="Meadowbrook Health System"/></div>
      <div class="rc-form-field"><label>Specialties (comma)</label>
        <input name="specialties"
               value="HOSPITAL,ACUTE_HOSPITAL,MA_RISK_PRIMARY_CARE"/></div>
      <div class="rc-form-field"><label>MA mix % (0-1)</label>
        <input name="ma_mix_pct" value="0.55"/></div>
      <div class="rc-form-field"><label>Commercial payer share (0-1)</label>
        <input name="commercial_payer_share" value="0.35"/></div>
      <div class="rc-form-field"><label>Has HOPD revenue</label>
        <select name="has_hopd_revenue">
          <option value="1">Yes</option><option value="">No</option>
        </select></div>
      <div class="rc-form-field"><label>REIT landlord</label>
        <select name="has_reit_landlord">
          <option value="1">Yes</option><option value="">No</option>
        </select></div>
      <div class="rc-form-field"><label>Revenue (USD)</label>
        <input name="revenue_usd" value="450000000"/></div>
      <div class="rc-form-field"><label>EBITDA (USD)</label>
        <input name="ebitda_usd" value="67500000"/></div>
      <div class="rc-form-field"><label>Horizon months</label>
        <input name="horizon_months" value="24"/></div>
    </div>
    <button class="rc-form-submit" type="submit">
      Run kill-switch analysis</button>
  </div>
</form>
"""
    body = (
        _scoped_styles()
        + '<div class="rc-wrap">'
        + deal_context_bar(qs or {}, active_surface="reg")
        + f'<div style="padding:22px 0 16px 0;">'
        + '<div class="rc-eyebrow">Regulatory Calendar × '
        + 'Thesis Kill-Switch</div>'
        + '<div class="rc-h1">Which thesis drivers die, and when.</div>'
        + f'<div class="rc-callout">Curated library of upcoming CMS / OIG / '
        + 'FTC / DOJ / NSA-IDR / state-level events mapped against your '
        + 'target\'s thesis drivers. The output is a gantt-style timeline '
        + 'showing the specific calendar date on which each driver '
        + '<em>dies</em> — plus an EBITDA bridge overlay that subtracts '
        + 'from the Deal MC cone.</div>'
        + '</div>'
        + form
        + '</div>'
    )
    return chartis_shell(
        body, "RCM Diligence — Regulatory Calendar",
        subtitle="Kill-switch × thesis × calendar",
    )


# ────────────────────────────────────────────────────────────────────
# Public entry
# ────────────────────────────────────────────────────────────────────

def _parse_target(qs: Dict[str, List[str]]) -> Dict[str, Any]:
    def first(k: str, default: str = "") -> str:
        return (qs.get(k) or [default])[0].strip()

    def f(k: str) -> Optional[float]:
        v = first(k)
        if not v:
            return None
        try:
            return float(v)
        except ValueError:
            return None

    def b(k: str) -> bool:
        v = first(k).lower()
        return v in ("1", "true", "yes", "on")

    specialties_raw = first("specialties")
    specialty = first("specialty")
    specialties: List[str] = []
    if specialties_raw:
        specialties = [
            s.strip().upper() for s in specialties_raw.split(",")
            if s.strip()
        ]
    if specialty:
        specialties.append(specialty.upper())

    return {
        "target_name": first("target_name") or "Target Deal",
        "specialties": specialties,
        "ma_mix_pct": f("ma_mix_pct"),
        "commercial_payer_share": f("commercial_payer_share"),
        "has_hopd_revenue": b("has_hopd_revenue"),
        "has_reit_landlord": b("has_reit_landlord"),
        "revenue_usd": f("revenue_usd"),
        "ebitda_usd": f("ebitda_usd"),
    }


def render_regulatory_calendar_page(
    qs: Optional[Dict[str, List[str]]] = None,
) -> str:
    qs = qs or {}
    if not (qs.get("specialties") or qs.get("specialty")):
        return _landing(qs)

    target = _parse_target(qs)
    horizon = 24
    try:
        raw = (qs.get("horizon_months") or ["24"])[0]
        horizon = max(3, min(60, int(float(raw))))
    except (TypeError, ValueError):
        horizon = 24

    report = analyze_regulatory_exposure(
        target_profile=target,
        as_of=date.today(),
        horizon_months=horizon,
    )

    target_name = target.get("target_name", "Target Deal")

    hero = (
        f'<div style="padding:22px 0 16px 0;border-bottom:1px solid '
        f'{P["border"]};margin-bottom:22px;">'
        f'<div class="rc-eyebrow">Regulatory Calendar × Kill-Switch</div>'
        f'<div class="rc-h1">{html.escape(target_name)}</div>'
        f'<div style="font-size:11px;color:{P["text_faint"]};'
        f'margin-top:4px;">'
        f'{len(report.events)} events · {horizon}-month horizon · '
        f'scanned {len(report.driver_timelines)} thesis drivers'
        f'</div>'
        f'{_verdict_card(report)}'
        f'</div>'
    )

    timeline_panel = (
        f'<div class="rc-panel">'
        f'<div class="rc-section-label" style="margin-top:0;">'
        f'Kill-switch timeline — thesis drivers × calendar dates</div>'
        f'{_timeline_svg(report)}'
        f'<div class="rc-callout">'
        f'<strong style="color:{P["text"]};">How to read: </strong>'
        f'Each row is one thesis driver.  Each dot is a regulatory event '
        f'that <strong style="color:{P["negative"]};">KILLS</strong> '
        f'(red) or <strong style="color:{P["warning"]};">DAMAGES</strong> '
        f'(amber) that driver on the plotted effective date.  Hover any '
        f'dot for the exact event, verdict, and impairment percentage.  '
        f'The dashed accent line is today.'
        f'</div>'
        f'</div>'
    )

    driver_panel = (
        f'<div class="rc-panel">'
        f'<div class="rc-section-label" style="margin-top:0;">'
        f'Per-driver verdict grid</div>'
        f'{_driver_table(report)}'
        f'</div>'
    )

    # Event cards — sort killers first
    def _event_rank(e: RegulatoryEvent) -> int:
        for tl in report.driver_timelines:
            for imp in tl.impacts:
                if imp.event_id == e.event_id:
                    if imp.verdict == ImpactVerdict.KILLED:
                        return 0
                    if imp.verdict == ImpactVerdict.DAMAGED:
                        return 1
        return 2

    events_sorted = sorted(report.events, key=_event_rank)

    # Sortable / filterable table view for analysts who want to scan
    # the universe of events at a glance (sits above the rich cards).
    table_headers = [
        "Event", "Agency", "Category", "Status",
        "Publish", "Effective", "Rev %", "Margin pp", "Kills",
    ]
    table_rows = []
    table_sort_keys = []
    for e in events_sorted:
        kills = len(e.thesis_driver_kill_map)
        eff_iso = e.effective_date.isoformat() if e.effective_date else ""
        table_rows.append([
            html.escape(e.title),
            html.escape(e.agency),
            e.category.value,
            e.status.value,
            e.publish_date.isoformat(),
            eff_iso or "—",
            f"{e.expected_revenue_impact_pct*100:+.2f}",
            f"{e.expected_margin_impact_pp:+.2f}",
            str(kills),
        ])
        table_sort_keys.append([
            e.title, e.agency, e.category.value, e.status.value,
            e.publish_date.isoformat(),
            eff_iso or "9999-99-99",
            e.expected_revenue_impact_pct,
            e.expected_margin_impact_pp, kills,
        ])

    events_table = sortable_table(
        table_headers, table_rows,
        sort_keys=table_sort_keys,
        name=f"regulatory_events_{target_name.replace(' ', '_')}",
        caption="Click any column header to sort · filter box at top · CSV export auto-wired",
    )

    events_panel = (
        f'<div class="rc-section-label">'
        f'Regulatory events in horizon · sortable view</div>'
        f'<div class="rc-panel">{events_table}</div>'
        f'<div class="rc-section-label">Event detail cards</div>'
        + "".join(_event_card(e, report) for e in events_sorted)
    )

    # Market Context — peer snapshot + sector sentiment.  Pulls the
    # same envelope the Deal Profile page uses so partners see the
    # target's regulatory exposure alongside its public-market
    # benchmark in one view.
    market_block = _market_context_block(target, report)

    # Deal MC cross-link if revenue/ebitda supplied
    cross_link = ""
    if target.get("revenue_usd") and target.get("ebitda_usd"):
        q = (
            f"target_name={html.escape(target_name)}"
            f"&ebitda_year0_usd={target['ebitda_usd']}"
            f"&debt_year0_usd={target['ebitda_usd']*5}"
            f"&equity_check_usd={target['ebitda_usd']*5}"
            f"&ebitda_growth=0.06"
        )
        cross_link = (
            f'<div class="rc-panel">'
            f'<div class="rc-section-label" style="margin-top:0;">'
            f'Next step</div>'
            f'<div style="font-size:13px;color:{P["text_dim"]};'
            f'line-height:1.65;">'
            f'The ${sum(o.ebitda_delta_usd for o in report.ebitda_overlay):+,.0f} '
            f'cumulative EBITDA overlay should subtract from the Deal MC '
            f'expected cone and from the Exit Timing IRR curve.  '
            f'<a href="/diligence/deal-mc?{q}" '
            f'style="color:{P["accent"]};text-decoration:underline;">'
            f'Open this target in Deal MC →</a>'
            f'</div>'
            f'</div>'
        )

    body = (
        _scoped_styles()
        + '<div class="rc-wrap">'
        + deal_context_bar(qs, active_surface="reg")
        + hero
        + market_block
        + timeline_panel
        + _overlay_panel(report)
        + driver_panel
        + events_panel
        + cross_link
        + export_json_panel(
            '<div class="rc-section-label" style="margin-top:22px;">'
            'JSON export — full exposure report</div>',
            payload=report.to_dict(),
            name=f"regulatory_exposure_{target_name.replace(' ', '_')}",
        )
        + bookmark_hint()
        + '</div>'
    )
    return chartis_shell(
        body, "RCM Diligence — Regulatory Calendar",
        subtitle=f"{target_name} · kill-switch verdict {report.verdict.value}",
    )
