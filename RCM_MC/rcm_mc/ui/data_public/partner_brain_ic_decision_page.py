"""Partner Brain · IC Decision — /partner-brain/ic-decision.

One-page IC read: recommend / pass / price X, plus the three numbers
behind the call. Surfaces:

- ``ic_decision_synthesizer.synthesize_ic_decision`` — the partner's
  one-paragraph call + chair opening line + must-close-before-IC list.
- ``thesis_validator.validate_thesis`` — consistency findings on the
  thesis statement (e.g., denial improvement inconsistent with
  revenue growth assumptions).
- ``red_team_review.build_red_team_report`` — adversarial review of
  the partner_review output.
- ``bear_book.scan_bear_book`` — bear-pattern library scan.

Phase 1 runs on seeded mid-market acute-care inputs. Later phase
wires real-deal loading.
"""
from __future__ import annotations

import html as _html
from typing import Any, Dict, List, Optional

from rcm_mc.ui._chartis_kit import P, chartis_shell, ck_section_header


_REC_COLORS = {
    "STRONG_PROCEED": P["positive"],
    "PROCEED": P["positive"],
    "PROCEED_WITH_CAVEATS": P["warning"],
    "PROCEED_AT_REPRICE": P["warning"],
    "PASS": P["critical"],
    "REWORK": P["negative"],
}

_SEVERITY_COLORS = {
    "CRITICAL": P["critical"],
    "HIGH": P["negative"],
    "MEDIUM": P["warning"],
    "LOW": P["text_dim"],
    "INFO": P["text_dim"],
}


def _sev_badge(sev: str) -> str:
    color = _SEVERITY_COLORS.get(sev.upper(), P["text_dim"])
    return (
        f'<span style="font-size:9px;font-family:JetBrains Mono,monospace;'
        f"color:{color};border:1px solid {color};padding:2px 6px;"
        f'letter-spacing:0.08em;border-radius:2px">{_html.escape(sev)}</span>'
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


def _build_ic_bundle():
    from rcm_mc.pe_intelligence.ic_decision_synthesizer import ICSignalBundle
    return ICSignalBundle(
        deal_name="Acme Regional Health (demo)",
        scorecard_all_pass=False,
        scorecard_failed_dimensions=["payer_concentration", "clinician_flight"],
        qod_ic_ready=True,
        qod_weakest_dimension="denial_coverage_evidence",
        qod_overall_pct=0.78,
        bear_moic=1.40,
        bear_probability_weighted_moic=2.1,
        bear_top_driver="MA_bridge_shortfall",
        safety_thin_levers=["cmi_uplift", "payer_renegotiation"],
        safety_combined_shock_moic=1.25,
        face_high_implausibilities=1,
        historical_pattern_matches=["ma_startup_unwind_2023"],
        partner_trap_names=["denial_fix_in_12_months", "ma_will_make_it_up"],
        coherence_score_0_100=74,
        connective_high_insight_count=3,
        cycle_double_peak=False,
        has_defensible_organic_growth=True,
        has_clear_exit_story=True,
        management_score_0_100=72,
        pricing_power_score_0_100=58,
    )


def _build_thesis():
    from rcm_mc.pe_intelligence.thesis_validator import ThesisStatement
    return ThesisStatement(
        entry_multiple=10.0,
        exit_multiple=12.0,
        hold_years=5.0,
        revenue_cagr=0.06,
        margin_expansion_bps_per_yr=120.0,
        denial_improvement_bps_per_yr=180.0,
        ar_reduction_days_per_yr=3.5,
        leverage_multiple=5.5,
        deal_structure="FFS",
        payer_mix={"medicare": 0.40, "medicaid": 0.18, "commercial": 0.35, "self_pay": 0.07},
        target_irr=0.22,
        target_moic=2.6,
        has_rollup_thesis=False,
        has_rcm_thesis=True,
        has_turnaround_thesis=False,
    )


def _build_heuristic_ctx():
    from rcm_mc.pe_intelligence.heuristics import HeuristicContext
    return HeuristicContext(
        payer_mix={"medicare": 0.40, "medicaid": 0.18, "commercial": 0.35, "self_pay": 0.07},
        ebitda_m=42.0, revenue_m=410.0, bed_count=420, hospital_type="acute_care",
        state="IL", denial_rate=0.11, days_in_ar=55.0, clean_claim_rate=0.88,
        case_mix_index=1.62, ebitda_margin=0.102, exit_multiple=12.0, entry_multiple=10.0,
        hold_years=5.0, projected_irr=0.22, projected_moic=2.6,
        denial_improvement_bps_per_yr=180.0, ar_reduction_days_per_yr=3.5,
        revenue_growth_pct_per_yr=0.06, margin_expansion_bps_per_yr=120.0,
        deal_structure="FFS", leverage_multiple=5.5, covenant_headroom_pct=0.18,
    )


# ── Rendering ─────────────────────────────────────────────────────


def _decision_banner(d: Any) -> str:
    rec = getattr(d, "recommendation", "") or "UNKNOWN"
    score = getattr(d, "score_0_100", 0) or 0
    chair = getattr(d, "chair_opening_line", "") or ""
    note = getattr(d, "partner_note", "") or ""

    rec_color = _REC_COLORS.get(rec, P["text_dim"])
    score_color = (
        P["positive"] if score >= 75 else (P["warning"] if score >= 50 else P["critical"])
    )
    return (
        f'<div style="background:{P["panel"]};border:1px solid {P["border"]};'
        f'padding:18px 22px;margin-bottom:16px;border-left:4px solid {rec_color}">'
        f'<div style="display:flex;align-items:center;gap:20px;flex-wrap:wrap">'
        f'<div>'
        f'<div style="font-size:9px;color:{P["text_dim"]};letter-spacing:0.08em;'
        f'text-transform:uppercase;margin-bottom:4px">Recommendation</div>'
        f'<div style="font-size:20px;font-weight:700;color:{rec_color};'
        f'font-family:JetBrains Mono,monospace;letter-spacing:0.04em">'
        f'{_html.escape(rec.replace("_", " "))}</div>'
        f'</div>'
        f'<div>'
        f'<div style="font-size:9px;color:{P["text_dim"]};letter-spacing:0.08em;'
        f'text-transform:uppercase;margin-bottom:4px">Score 0-100</div>'
        f'<div style="font-size:26px;font-weight:700;color:{score_color};'
        f'font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace">'
        f"{score}</div></div>"
        f'</div>'
        f'<div style="margin-top:14px;padding-top:12px;border-top:1px solid {P["border"]}">'
        f'<div style="font-size:10px;color:{P["text_dim"]};letter-spacing:0.08em;'
        f'text-transform:uppercase;margin-bottom:6px">Chair opening line</div>'
        f'<div style="font-size:13px;color:{P["text"]};font-style:italic;line-height:1.6">'
        f'"{_html.escape(chair)}"</div>'
        f'</div>'
        f'<div style="margin-top:12px;font-size:12px;color:{P["text"]};line-height:1.6">'
        f"{_html.escape(note)}</div>"
        f"</div>"
    )


def _reasons_list(d: Any) -> str:
    reasons = list(getattr(d, "reasons_for", []) or [])
    flips = list(getattr(d, "flip_the_call_signals", []) or [])
    musts = list(getattr(d, "must_close_before_ic", []) or [])

    def _ul(items: List[str], color: str) -> str:
        if not items:
            return f'<div style="font-size:11px;color:{P["text_dim"]};padding:4px 0">—</div>'
        return (
            '<ul style="margin:4px 0;padding-left:20px">'
            + "".join(
                f'<li style="font-size:11px;color:{color};line-height:1.6;margin:3px 0">'
                f"{_html.escape(str(r))}</li>"
                for r in items
            )
            + "</ul>"
        )

    return (
        f'<div style="display:grid;grid-template-columns:repeat(3,1fr);gap:12px">'
        f'{_panel("Reasons for", _ul(reasons, P["text"]))}'
        f'{_panel("Flip-the-call signals", _ul(flips, P["warning"]))}'
        f'{_panel("Must close before IC", _ul(musts, P["critical"]))}'
        f"</div>"
    )


def _findings_table(findings: List[Any]) -> str:
    if not findings:
        return (
            f'<div style="font-size:11px;color:{P["text_dim"]};padding:12px">'
            f"No inconsistencies detected in the thesis.</div>"
        )
    bg = P["panel"]
    panel_alt = P["panel_alt"]
    text = P["text"]
    text_dim = P["text_dim"]
    acc = P["accent"]

    rows = []
    for i, f in enumerate(findings):
        rb = panel_alt if i % 2 == 0 else bg
        rule = getattr(f, "rule", "") or ""
        sev = getattr(f, "severity", "") or ""
        summary = getattr(f, "summary", "") or ""
        note = getattr(f, "partner_note", "") or ""
        impl = getattr(f, "fields_implicated", []) or []

        fields_html = ", ".join(
            f'<code style="color:{acc}">{_html.escape(str(x))}</code>' for x in impl[:6]
        ) or "—"

        rows.append(
            f'<tr style="background:{rb};vertical-align:top">'
            f'<td style="padding:8px 12px;width:80px;text-align:center">{_sev_badge(sev)}</td>'
            f'<td style="padding:8px 12px">'
            f'<div style="font-size:10px;font-family:JetBrains Mono,monospace;color:{text_dim};'
            f'margin-bottom:2px">{_html.escape(rule)}</div>'
            f'<div style="font-size:11px;color:{text};line-height:1.5">{_html.escape(summary)}</div>'
            f'<div style="font-size:11px;color:{acc};font-style:italic;margin-top:4px;line-height:1.5">'
            f'"{_html.escape(note)}"</div>'
            f'<div style="font-size:10px;color:{text_dim};margin-top:4px">'
            f'<span style="color:{text_dim}">Fields:</span> {fields_html}</div>'
            f"</td></tr>"
        )
    return (
        f'<table style="width:100%;border-collapse:collapse;font-size:11px">'
        f'<tbody>{"".join(rows)}</tbody></table>'
    )


def _bear_hits_table(hits: List[Any]) -> str:
    if not hits:
        return (
            f'<div style="font-size:11px;color:{P["text_dim"]};padding:12px">'
            f"No bear-book patterns matched above the 30% confidence floor.</div>"
        )
    bg = P["panel"]
    panel_alt = P["panel_alt"]
    text = P["text"]
    text_dim = P["text_dim"]
    acc = P["accent"]

    rows = []
    for i, h in enumerate(hits):
        rb = panel_alt if i % 2 == 0 else bg
        name = getattr(h, "name", "") or ""
        pattern_id = getattr(h, "pattern_id", "") or ""
        confidence = getattr(h, "confidence", 0.0) or 0.0
        summary = getattr(h, "summary", "") or ""
        failure = getattr(h, "failure_mode", "") or ""
        voice = getattr(h, "partner_voice", "") or ""
        conf_pct = int(confidence * 100)
        conf_color = (
            P["critical"] if conf_pct >= 70 else (P["warning"] if conf_pct >= 50 else P["text_dim"])
        )

        rows.append(
            f'<tr style="background:{rb};vertical-align:top">'
            f'<td style="padding:10px 12px;width:80px;text-align:center">'
            f'<div style="font-size:16px;font-weight:700;color:{conf_color};'
            f'font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace">{conf_pct}%</div>'
            f'<div style="font-size:9px;color:{text_dim};letter-spacing:0.08em">CONFIDENCE</div>'
            f"</td>"
            f'<td style="padding:10px 12px">'
            f'<div style="font-size:12px;font-weight:700;color:{text}">{_html.escape(name)}</div>'
            f'<div style="font-size:10px;color:{text_dim};font-family:JetBrains Mono,monospace;'
            f'margin-top:2px">{_html.escape(pattern_id)}</div>'
            f'<div style="font-size:11px;color:{text};margin-top:6px;line-height:1.5">'
            f"{_html.escape(summary)}</div>"
            f'<div style="font-size:10px;color:{P["negative"]};margin-top:4px;line-height:1.5">'
            f'<span style="color:{text_dim}">Failure mode:</span> {_html.escape(failure)}</div>'
            f'<div style="font-size:11px;color:{acc};font-style:italic;margin-top:4px;line-height:1.5">'
            f'"{_html.escape(voice)}"</div>'
            f"</td></tr>"
        )
    return (
        f'<table style="width:100%;border-collapse:collapse;font-size:11px">'
        f'<tbody>{"".join(rows)}</tbody></table>'
    )


def _red_team_block(report: Any) -> str:
    attacks = list(getattr(report, "attacks", []) or [])
    if not attacks:
        return (
            f'<div style="font-size:11px;color:{P["text_dim"]};padding:12px">'
            f"Red team found no open angles to attack on this review.</div>"
        )
    text = P["text"]
    text_dim = P["text_dim"]
    panel_alt = P["panel_alt"]
    border = P["border"]
    crit = P["critical"]

    items = []
    for a in attacks:
        angle = getattr(a, "angle", "") or ""
        attack_text = getattr(a, "attack", "") or getattr(a, "attack_line", "") or ""
        counter = getattr(a, "counter_burden", "") or getattr(a, "defense_burden", "") or ""
        items.append(
            f'<div style="padding:10px 12px;border-bottom:1px dashed {border}">'
            f'<div style="font-size:11px;color:{crit};font-weight:700">{_html.escape(angle)}</div>'
            f'<div style="font-size:11px;color:{text};margin-top:4px;line-height:1.5">'
            f"{_html.escape(attack_text)}</div>"
            + (
                f'<div style="font-size:10px;color:{text_dim};margin-top:4px;line-height:1.5">'
                f'<span style="color:{text_dim}">Defense burden:</span> {_html.escape(counter)}</div>'
                if counter else ""
            )
            + "</div>"
        )
    return f'<div style="background:{panel_alt}">{"".join(items)}</div>'


# ── Main entry ───────────────────────────────────────────────────


def render_partner_brain_ic_decision(qp: Dict[str, str] | None = None) -> str:
    _ = qp or {}

    # Run modules on demo inputs.
    from rcm_mc.pe_intelligence.ic_decision_synthesizer import synthesize_ic_decision
    from rcm_mc.pe_intelligence.thesis_validator import validate_thesis
    from rcm_mc.pe_intelligence.red_team_review import build_red_team_report
    from rcm_mc.pe_intelligence.bear_book import scan_bear_book
    from rcm_mc.pe_intelligence import partner_review as _pr
    from rcm_mc.pe_intelligence.partner_review import partner_review_from_context

    try:
        decision = synthesize_ic_decision(_build_ic_bundle())
    except Exception:  # noqa: BLE001
        decision = None

    try:
        findings = validate_thesis(_build_thesis())
    except Exception:  # noqa: BLE001
        findings = []

    try:
        bear_hits = scan_bear_book(_build_heuristic_ctx())
    except Exception:  # noqa: BLE001
        bear_hits = []

    try:
        review = partner_review_from_context(
            _build_heuristic_ctx(),
            deal_id="demo_acme_regional",
            deal_name="Acme Regional Health (demo)",
        )
        red_team = build_red_team_report(review)
    except Exception:  # noqa: BLE001
        red_team = None

    text = P["text"]
    text_dim = P["text_dim"]
    acc = P["accent"]

    score = getattr(decision, "score_0_100", 0) if decision else 0
    sev_counts = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
    for f in findings:
        sev = (getattr(f, "severity", "") or "").upper()
        if sev in sev_counts:
            sev_counts[sev] += 1

    score_color = (
        P["positive"] if score >= 75 else (P["warning"] if score >= 50 else P["critical"])
    )

    kpi_strip = (
        f'<div style="display:flex;gap:12px;flex-wrap:wrap;margin-bottom:20px">'
        f"{_kpi_tile('IC score', str(score), score_color)}"
        f"{_kpi_tile('Thesis findings', str(len(findings)))}"
        f"{_kpi_tile('Critical inconsistencies', str(sev_counts['CRITICAL']), P['critical'] if sev_counts['CRITICAL'] else P['text'])}"
        f"{_kpi_tile('Bear patterns', str(len(bear_hits)), P['warning'] if bear_hits else P['text'])}"
        f"{_kpi_tile('Red-team attacks', str(len(getattr(red_team, 'attacks', []) or [])))}"
        f"</div>"
    )

    demo_banner = (
        f'<div style="padding:10px 14px;margin-bottom:16px;background:{P["panel"]};'
        f'border:1px solid {P["warning"]};border-left:3px solid {P["warning"]};'
        f'font-size:11px;color:{text_dim};line-height:1.5">'
        f'<span style="color:{P["warning"]};font-weight:700;letter-spacing:0.05em">'
        f"DEMO DATA:</span> "
        f"All 4 IC modules running on a seeded mid-market acute-care signal bundle."
        f"</div>"
    )

    decision_html = _decision_banner(decision) if decision else ""
    reasons_html = _reasons_list(decision) if decision else ""
    findings_html = _findings_table(findings)
    bear_html = _bear_hits_table(bear_hits)
    red_team_html = _red_team_block(red_team) if red_team else ""

    body = (
        f'<div style="padding:20px;max-width:1400px;margin:0 auto">'
        f'<div style="margin-bottom:16px">'
        f'<a href="/partner-brain" style="color:{acc};font-size:11px;text-decoration:none">'
        f"← Partner Brain hub</a></div>"
        f'<h1 style="font-size:18px;font-weight:700;color:{text};letter-spacing:0.02em">'
        f"Partner Brain · IC Decision</h1>"
        f'<p style="font-size:12px;color:{text_dim};margin-top:4px;line-height:1.5">'
        f"One-page IC read: the recommendation, the score behind it, the "
        f"bear-book scan, the thesis-consistency check, and what red team "
        f"would attack before the chair walks in.</p>"
        f"{demo_banner}"
        f"{kpi_strip}"
        f"{decision_html}"
        f"{reasons_html}"
        f'<div style="margin-top:24px"></div>'
        f'{ck_section_header("Thesis consistency", "internal contradictions in the model inputs", len(findings))}'
        f'<div style="margin-top:8px">{findings_html}</div>'
        f'<div style="margin-top:24px"></div>'
        f'{ck_section_header("Bear book", "dated bear patterns matched to the current context", len(bear_hits))}'
        f'<div style="margin-top:8px">{bear_html}</div>'
        f'<div style="margin-top:24px"></div>'
        f'{ck_section_header("Red team", "adversarial angles on the partner review", len(getattr(red_team, "attacks", []) or []) if red_team else 0)}'
        f'<div style="margin-top:8px">{red_team_html or "<div>—</div>"}</div>'
        f"</div>"
    )

    return chartis_shell(
        body=body, title="Partner Brain · IC Decision", active_nav="/partner-brain"
    )
