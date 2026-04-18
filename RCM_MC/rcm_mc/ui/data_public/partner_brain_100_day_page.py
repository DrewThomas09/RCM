"""Partner Brain · 100-Day & Operational Readiness — /partner-brain/100-day.

Post-close, the partner cares about four things: day-one readiness,
90-day reality check, EHR transition risk (the one that sinks
post-close EBITDA), and integration readiness (management
retention, system plan, comp alignment).

Modules surfaced:

- ``day_one_action_plan.assess_day_one_readiness`` — status across
  the day-1 standard action set with unowned + escalation counts.
- ``post_close_90_day_reality_check.run_90_day_reality_check`` —
  category-by-category underwritten vs actual Q1 delta.
- ``ehr_transition_risk_assessor.assess_ehr_transition`` — transition
  cost, productivity dip, revenue hit, payback years.
- ``integration_readiness.assess_integration_readiness`` — gap
  findings with 0-100 scoring.
"""
from __future__ import annotations

import html as _html
from typing import Any, Dict, List, Optional

from rcm_mc.ui._chartis_kit import P, chartis_shell, ck_section_header


_STATUS_COLORS = {
    "ON_TRACK": P["positive"],
    "AT_RISK": P["warning"],
    "OFF_TRACK": P["critical"],
    "DONE": P["positive"],
    "NOT_STARTED": P["text_dim"],
    "IN_PROGRESS": P["warning"],
    "BLOCKED": P["negative"],
    "STRONG": P["positive"],
    "WEAK": P["warning"],
    "CRITICAL_GAP": P["critical"],
    "GAP": P["warning"],
    "READY": P["positive"],
    "NOT_READY": P["critical"],
    "UNOWNED": P["negative"],
    "OWNED_PENDING": P["warning"],
}


def _status_badge(status: str) -> str:
    color = _STATUS_COLORS.get(status.upper(), P["text_dim"])
    return (
        f'<span style="font-size:9px;font-family:JetBrains Mono,monospace;'
        f"color:{color};border:1px solid {color};padding:2px 6px;"
        f'letter-spacing:0.08em;border-radius:2px">{_html.escape(status)}</span>'
    )


def _kpi_tile(label: str, value: str, color: Optional[str] = None) -> str:
    val_color = color or P["text"]
    return (
        f'<div style="background:{P["panel"]};border:1px solid {P["border"]};'
        f'padding:12px 14px;min-width:140px">'
        f'<div style="font-size:9px;color:{P["text_dim"]};letter-spacing:0.08em;'
        f'text-transform:uppercase;margin-bottom:4px">{_html.escape(label)}</div>'
        f'<div style="font-size:18px;font-weight:700;color:{val_color};'
        f'font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace">'
        f"{_html.escape(value)}</div></div>"
    )


def _panel(label: str, body: str) -> str:
    return (
        f'<div style="background:{P["panel"]};border:1px solid {P["border"]};'
        f'padding:14px 16px;margin-bottom:12px">'
        f'<div style="font-size:10px;color:{P["text_dim"]};letter-spacing:0.08em;'
        f'text-transform:uppercase;margin-bottom:10px;font-weight:600">{_html.escape(label)}</div>'
        f"{body}</div>"
    )


# ── Demo builders ──────────────────────────────────────────────────


def _build_day_one_inputs():
    from rcm_mc.pe_intelligence.day_one_action_plan import DayOneInputs, list_day_one_actions
    all_actions = list_day_one_actions()
    # Seeded state: first half done, next quarter owned-but-pending, rest unowned.
    half = len(all_actions) // 2
    quarter = len(all_actions) // 4
    return DayOneInputs(
        actions_done=list(all_actions[:half]),
        actions_owned=list(all_actions[:half + quarter]),
    )


def _build_90_day_inputs():
    from rcm_mc.pe_intelligence.post_close_90_day_reality_check import NinetyDayInputs
    return NinetyDayInputs(
        deal_name="Acme Regional Health (demo)",
        underwritten_annual_growth_pct=0.06,
        actual_q1_annualized_growth_pct=0.038,
        underwritten_ebitda_margin_pct=0.115,
        actual_q1_ebitda_margin_pct=0.104,
        underwritten_q1_denial_drop_bps=60.0,
        actual_q1_denial_drop_bps=20.0,
        top_5_physicians_at_close=5,
        top_5_physicians_active_q1=4,
        expected_c_suite_count=5,
        actual_c_suite_count_at_q1=4,
        day1_actions_committed=18,
        day1_actions_delivered=13,
        material_surprises_count=2,
    )


def _build_ehr_inputs():
    from rcm_mc.pe_intelligence.ehr_transition_risk_assessor import EHRTransitionInputs
    return EHRTransitionInputs(
        transition_type="meditech_to_epic",
        beds_or_providers=420,
        annual_revenue_m=410.0,
        post_transition_annual_savings_m=2.5,
    )


def _build_integration_inputs():
    from rcm_mc.pe_intelligence.integration_readiness import IntegrationInputs
    return IntegrationInputs(
        integration_officer_named=True,
        day_one_system_plan_ready=True,
        management_retention_signed=True,
        management_comp_aligned=False,  # gap
        communications_plan_ready=True,
        customer_retention_plan_ready=False,  # gap
        financial_reporting_harmonized=False,  # gap
        synergy_tracking_cadence_set=True,
        culture_assessment_complete=False,  # gap
        it_systems_map_complete=True,
        regulatory_change_of_ownership_filed=True,
        payer_notification_complete=True,
    )


# ── Rendering ─────────────────────────────────────────────────────


def _day_one_statuses(report: Any) -> str:
    statuses = list(getattr(report, "statuses", []) or [])
    if not statuses:
        return "<div>—</div>"
    bg = P["panel"]
    panel_alt = P["panel_alt"]
    text = P["text"]
    text_dim = P["text_dim"]

    rows = []
    for i, s in enumerate(statuses):
        rb = panel_alt if i % 2 == 0 else bg
        action = getattr(s, "action", None)
        name = getattr(action, "name", "") if action else ""
        owner = getattr(action, "owner", "") if action else ""
        timing = getattr(action, "timing", "") if action else ""
        risk = getattr(action, "risk_if_delayed", "") if action else ""
        desc = getattr(action, "description", "") if action else ""

        is_done = bool(getattr(s, "is_done", False))
        is_owned = bool(getattr(s, "is_owned", False))
        escalation = bool(getattr(s, "escalation_needed", False))
        if is_done:
            status = "DONE"
        elif escalation:
            status = "BLOCKED"
        elif is_owned:
            status = "OWNED_PENDING"
        else:
            status = "UNOWNED"

        rows.append(
            f'<tr style="background:{rb};vertical-align:top">'
            f'<td style="padding:6px 12px;width:120px;text-align:center">{_status_badge(status)}</td>'
            f'<td style="padding:6px 12px">'
            f'<div style="font-size:11px;font-weight:700;color:{text}">{_html.escape(name)}</div>'
            + (
                f'<div style="font-size:10px;color:{text_dim};margin-top:3px;line-height:1.4">{_html.escape(desc)}</div>'
                if desc else ""
            )
            + f'<div style="font-size:9px;color:{text_dim};margin-top:4px;font-family:JetBrains Mono,monospace">'
            f"owner: {_html.escape(owner)} · timing: {_html.escape(timing)} · risk: {_html.escape(risk)}"
            f"</div></td></tr>"
        )
    return (
        f'<table style="width:100%;border-collapse:collapse;font-size:11px">'
        f'<tbody>{"".join(rows)}</tbody></table>'
    )


def _90_day_table(categories: List[Any]) -> str:
    if not categories:
        return "<div>—</div>"
    bg = P["panel"]
    panel_alt = P["panel_alt"]
    text = P["text"]
    text_dim = P["text_dim"]
    acc = P["accent"]

    cols = [
        ("Status", "center", 100),
        ("Category", "left", 160),
        ("Underwritten", "right", 120),
        ("Actual Q1", "right", 120),
        ("Delta", "left", 0),
    ]
    ths = "".join(
        f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {P["border"]};'
        f'font-size:10px;color:{text_dim};letter-spacing:0.05em'
        f'{";width:" + str(w) + "px" if w else ""}">{c}</th>'
        for c, a, w in cols
    )

    rows = []
    for i, c in enumerate(categories):
        rb = panel_alt if i % 2 == 0 else bg
        status = getattr(c, "status", "") or ""
        name = getattr(c, "name", "") or ""
        actual = getattr(c, "actual", "") or ""
        underwritten = getattr(c, "underwritten", "") or ""
        delta = getattr(c, "delta_summary", "") or ""
        partner_read = getattr(c, "partner_read", "") or ""

        rows.append(
            f'<tr style="background:{rb};vertical-align:top">'
            f'<td style="text-align:center;padding:8px 10px">{_status_badge(status)}</td>'
            f'<td style="padding:8px 10px;font-size:11px;font-weight:600;color:{text}">{_html.escape(name)}</td>'
            f'<td style="text-align:right;padding:8px 10px;font-variant-numeric:tabular-nums;'
            f'font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{_html.escape(underwritten)}</td>'
            f'<td style="text-align:right;padding:8px 10px;font-variant-numeric:tabular-nums;'
            f'font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{_html.escape(actual)}</td>'
            f'<td style="padding:8px 10px">'
            f'<div style="font-size:11px;color:{text}">{_html.escape(delta)}</div>'
            + (
                f'<div style="font-size:10px;color:{acc};font-style:italic;margin-top:3px;line-height:1.5">'
                f'"{_html.escape(partner_read)}"</div>' if partner_read else ""
            )
            + "</td></tr>"
        )
    return (
        f'<table style="width:100%;border-collapse:collapse;font-size:11px">'
        f'<thead><tr style="background:{bg}">{ths}</tr></thead>'
        f'<tbody>{"".join(rows)}</tbody></table>'
    )


def _ehr_block(report: Any) -> str:
    text = P["text"]
    text_dim = P["text_dim"]
    panel = P["panel"]
    border = P["border"]

    transition = getattr(report, "transition_type", "") or ""
    in_cat = getattr(report, "in_catalog", False)
    if not in_cat:
        return (
            f'<div style="font-size:11px;color:{P["text_dim"]};padding:12px">'
            f"EHR transition type <code>{_html.escape(transition)}</code> "
            f"not in catalog.</div>"
        )
    months = getattr(report, "migration_months", 0)
    capex = getattr(report, "capex_m", 0.0) or 0.0
    dip_pct = getattr(report, "productivity_dip_pct", 0.0) or 0.0
    dip_months = getattr(report, "productivity_dip_months", 0)
    rev_dip = getattr(report, "revenue_dip_during_transition_m", 0.0) or 0.0
    total_cost = getattr(report, "total_all_in_cost_m", 0.0) or 0.0
    payback = getattr(report, "payback_years", None)
    note = getattr(report, "partner_note", "") or ""

    payback_str = f"{payback:.1f} yrs" if payback is not None else "never"
    payback_color = (
        P["positive"] if payback is not None and payback <= 3 else
        (P["warning"] if payback is not None and payback <= 6 else P["critical"])
    )

    tiles = (
        f'<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:10px">'
        f"{_kpi_tile('Migration months', str(months))}"
        f"{_kpi_tile('Capex', f'${capex:.1f}M')}"
        f"{_kpi_tile('Productivity dip', f'{dip_pct*100:.1f}%', P['critical'] if dip_pct > 0.10 else P['warning'])}"
        f"{_kpi_tile('Dip duration', f'{dip_months} mo')}"
        f"{_kpi_tile('Revenue dip', f'${rev_dip:.1f}M', P['negative'])}"
        f"{_kpi_tile('Total all-in', f'${total_cost:.1f}M')}"
        f"{_kpi_tile('Payback', payback_str, payback_color)}"
        f"</div>"
    )
    return (
        f'<div style="margin-bottom:12px">'
        f'<div style="font-size:11px;color:{text_dim};font-family:JetBrains Mono,monospace;'
        f'margin-bottom:10px">transition_type: {_html.escape(transition)}</div>'
        f"{tiles}"
        + (
            f'<div style="margin-top:12px;padding:10px 12px;background:{panel};'
            f"border-left:3px solid {P['warning']};font-size:12px;color:{text};"
            f'line-height:1.6">{_html.escape(note)}</div>' if note else ""
        )
        + "</div>"
    )


def _integration_findings(report: Any) -> str:
    findings = list(getattr(report, "findings", []) or [])
    if not findings:
        return "<div>—</div>"

    bg = P["panel"]
    panel_alt = P["panel_alt"]
    text = P["text"]
    text_dim = P["text_dim"]

    rows = []
    for i, f in enumerate(findings):
        rb = panel_alt if i % 2 == 0 else bg
        area = getattr(f, "area", "") or ""
        score = getattr(f, "score", 0) or 0
        status = getattr(f, "status", "") or ""
        comment = getattr(f, "commentary", "") or ""

        score_color = (
            P["positive"] if score >= 75 else (P["warning"] if score >= 50 else P["critical"])
        )
        rows.append(
            f'<tr style="background:{rb};vertical-align:top">'
            f'<td style="padding:6px 12px;width:60px;text-align:center">'
            f'<div style="font-size:14px;font-weight:700;color:{score_color};'
            f'font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace">{score}</div>'
            f"</td>"
            f'<td style="padding:6px 12px;width:130px;text-align:center">{_status_badge(status)}</td>'
            f'<td style="padding:6px 12px">'
            f'<div style="font-size:11px;font-weight:600;color:{text}">{_html.escape(area.replace("_", " ").title())}</div>'
            f'<div style="font-size:10px;color:{text_dim};margin-top:3px;line-height:1.5">'
            f"{_html.escape(comment)}</div></td></tr>"
        )
    return (
        f'<table style="width:100%;border-collapse:collapse;font-size:11px">'
        f'<tbody>{"".join(rows)}</tbody></table>'
    )


# ── Main entry ───────────────────────────────────────────────────


def render_partner_brain_100_day(qp: Dict[str, str] | None = None) -> str:
    _ = qp or {}

    from rcm_mc.pe_intelligence.day_one_action_plan import assess_day_one_readiness
    from rcm_mc.pe_intelligence.post_close_90_day_reality_check import run_90_day_reality_check
    from rcm_mc.pe_intelligence.ehr_transition_risk_assessor import assess_ehr_transition
    from rcm_mc.pe_intelligence.integration_readiness import assess_integration_readiness

    try:
        day_one = assess_day_one_readiness(_build_day_one_inputs())
    except Exception:  # noqa: BLE001
        day_one = None
    try:
        ninety = run_90_day_reality_check(_build_90_day_inputs())
    except Exception:  # noqa: BLE001
        ninety = None
    try:
        ehr = assess_ehr_transition(_build_ehr_inputs())
    except Exception:  # noqa: BLE001
        ehr = None
    try:
        integration = assess_integration_readiness(_build_integration_inputs())
    except Exception:  # noqa: BLE001
        integration = None

    text = P["text"]
    text_dim = P["text_dim"]
    acc = P["accent"]

    day_one_done = getattr(day_one, "done_count", 0) if day_one else 0
    day_one_total = getattr(day_one, "total_actions", 0) if day_one else 0
    day_one_unowned = getattr(day_one, "unowned_count", 0) if day_one else 0
    ninety_verdict = (getattr(ninety, "aggregate_verdict", "") if ninety else "") or "—"
    ninety_off_track = getattr(ninety, "off_track_count", 0) if ninety else 0
    integ_score = getattr(integration, "score", 0) if integration else 0
    integ_gaps = getattr(integration, "gap_count", 0) if integration else 0

    verdict_color = (
        P["critical"] if ninety_verdict.upper() in ("OFF_TRACK", "FAILING") else
        (P["warning"] if ninety_verdict.upper() in ("AT_RISK", "MIXED") else P["positive"])
    )
    integ_color = (
        P["positive"] if integ_score >= 75 else (P["warning"] if integ_score >= 50 else P["critical"])
    )

    kpi_strip = (
        f'<div style="display:flex;gap:12px;flex-wrap:wrap;margin-bottom:20px">'
        f"{_kpi_tile('Day-1 actions done', f'{day_one_done}/{day_one_total}')}"
        f"{_kpi_tile('Day-1 unowned', str(day_one_unowned), P['critical'] if day_one_unowned else P['text'])}"
        f"{_kpi_tile('90-day verdict', ninety_verdict, verdict_color)}"
        f"{_kpi_tile('Off-track categories', str(ninety_off_track), P['critical'] if ninety_off_track else P['text'])}"
        f"{_kpi_tile('Integration score', str(integ_score), integ_color)}"
        f"{_kpi_tile('Integration gaps', str(integ_gaps), P['warning'] if integ_gaps else P['text'])}"
        f"</div>"
    )

    demo_banner = (
        f'<div style="padding:10px 14px;margin-bottom:16px;background:{P["panel"]};'
        f'border:1px solid {P["warning"]};border-left:3px solid {P["warning"]};'
        f'font-size:11px;color:{text_dim};line-height:1.5">'
        f'<span style="color:{P["warning"]};font-weight:700;letter-spacing:0.05em">'
        f"DEMO DATA:</span> "
        f"Post-close state seeded with partial completion: day-1 half done, "
        f"90-day slightly off-track, Meditech→Epic transition, 3 integration gaps."
        f"</div>"
    )

    day_one_note = getattr(day_one, "partner_note", "") if day_one else ""
    ninety_note = getattr(ninety, "partner_note", "") if ninety else ""
    integ_note = getattr(integration, "partner_note", "") if integration else ""
    integ_verdict = getattr(integration, "verdict", "") if integration else ""

    day_one_body = (
        (
            f'<div style="padding:10px 12px;background:{P["panel"]};border-left:3px solid {P["accent"]};'
            f'font-size:12px;color:{text};line-height:1.6;margin-bottom:12px">{_html.escape(day_one_note)}</div>'
            if day_one_note else ""
        )
        + _day_one_statuses(day_one)
    ) if day_one else "<div>—</div>"

    ninety_body = (
        (
            f'<div style="padding:10px 12px;background:{P["panel"]};border-left:3px solid {P["accent"]};'
            f'font-size:12px;color:{text};line-height:1.6;margin-bottom:12px">{_html.escape(ninety_note)}</div>'
            if ninety_note else ""
        )
        + _90_day_table(list(getattr(ninety, "categories", []) or []))
    ) if ninety else "<div>—</div>"

    integ_body = (
        f'<div style="display:flex;align-items:center;gap:18px;margin-bottom:12px">'
        f'<div style="font-size:20px;font-weight:700;color:{integ_color};'
        f'font-family:JetBrains Mono,monospace">{integ_verdict.upper()}</div>'
        f'</div>'
        + (
            f'<div style="padding:10px 12px;background:{P["panel"]};border-left:3px solid {P["accent"]};'
            f'font-size:12px;color:{text};line-height:1.6;margin-bottom:12px">{_html.escape(integ_note)}</div>'
            if integ_note else ""
        )
        + _integration_findings(integration)
    ) if integration else "<div>—</div>"

    body = (
        f'<div style="padding:20px;max-width:1400px;margin:0 auto">'
        f'<div style="margin-bottom:16px">'
        f'<a href="/partner-brain" style="color:{acc};font-size:11px;text-decoration:none">'
        f"← Partner Brain hub</a></div>"
        f'<h1 style="font-size:18px;font-weight:700;color:{text};letter-spacing:0.02em">'
        f"Partner Brain · 100-Day & Operational Readiness</h1>"
        f'<p style="font-size:12px;color:{text_dim};margin-top:4px;line-height:1.5">'
        f"Post-close reality. Day-1 readiness, 90-day underwritten-vs-"
        f"actual reality check, EHR transition risk, and integration "
        f"readiness gaps.</p>"
        f"{demo_banner}"
        f"{kpi_strip}"
        f'{ck_section_header("Day-1 action plan", "status across the standard close-day action set", day_one_total)}'
        f'<div style="margin-top:8px">{day_one_body}</div>'
        f'<div style="margin-top:24px"></div>'
        f'{ck_section_header("90-day reality check", "underwritten vs actual Q1 — where the plan slipped", ninety_off_track)}'
        f'<div style="margin-top:8px">{ninety_body}</div>'
        f'<div style="margin-top:24px"></div>'
        f'{ck_section_header("EHR transition risk", "the one that sinks post-close EBITDA if mis-sized", None)}'
        f"<div style=\"margin-top:8px\">{_ehr_block(ehr) if ehr else '—'}</div>"
        f'<div style="margin-top:24px"></div>'
        f'{ck_section_header("Integration readiness", "12-dimension score with gap call-outs", integ_gaps)}'
        f'<div style="margin-top:8px">{integ_body}</div>'
        f"</div>"
    )

    return chartis_shell(
        body=body, title="Partner Brain · 100-Day Plan", active_nav="/partner-brain"
    )
