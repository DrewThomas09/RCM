"""Partner Brain · Sniff Test & Archetype — /partner-brain/sniff.

Before the math. Runs the on-face sniff test (400-bed rural CAH
projecting 28% IRR, dental DSO at 4× revenue, MA-will-cover-FFS
without a named contract) and the archetype recognizer so the
partner sees what kind of deal they're looking at and what
named risks the archetype carries.

Modules surfaced:

- ``unrealistic_on_face_check.run_sniff_test`` — on-face scorecard
  covering IRR, EV/revenue, projected margin, MA bridges, CPOM
  state compliance, PAMA exposure.
- ``healthcare_thesis_archetype_recognizer.recognize_healthcare_thesis_archetypes``
  — maps teaser signals to 7 archetypes (payer-mix shift,
  back-office consolidation, outpatient migration, CMI uplift,
  roll-up platform, cost-basis compression, capacity expansion).
"""
from __future__ import annotations

import html as _html
from typing import Any, Dict, List, Optional

from rcm_mc.ui._chartis_kit import P, chartis_shell, ck_section_header


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


# ── Demo builders ──────────────────────────────────────────────────


def _build_sniff_inputs():
    """A teaser deliberately crafted to trigger multiple sniff hits so
    the demo surfaces the real value of the check."""
    from rcm_mc.pe_intelligence.unrealistic_on_face_check import SniffTestInputs
    return SniffTestInputs(
        subsector="acute_care",
        is_rural_critical_access=False,
        is_standalone_snf=False,
        is_dental_dso=False,
        is_standalone_diagnostics=False,
        is_home_health=False,
        is_rollup_platform=False,
        is_cpom_strict_state=True,          # IL — mild
        recently_converted_nonprofit=False,
        is_critical_access_hospital=False,
        single_site_single_specialty=False,
        npr_m=410.0,
        projected_sponsor_irr=0.28,         # aggressive
        medicare_mix_pct=0.40,
        commercial_mix_pct=0.35,
        ev_to_ebitda_multiple=13.5,         # stretch
        ev_to_revenue_multiple=1.4,
        leverage_turns=6.2,
        margin_expansion_1yr_bps=400.0,     # 400 bps in 1 year — suspicious
        ebitda_margin_pct=0.102,
        ma_narrative_present=True,
        ma_contract_named=False,            # classic trap
        exit_multiple_assumption=13.0,
        pama_in_hold=False,
        revenue_m=410.0,
        has_named_cio=True,
        mso_pc_model_verified=True,
        pre_conversion_ebitda_margin_pct=0.102,
    )


def _build_archetype_signals():
    from rcm_mc.pe_intelligence.healthcare_thesis_archetype_recognizer import (
        HealthcareArchetypeSignals,
    )
    return HealthcareArchetypeSignals(
        commercial_mix_change_planned_pct=0.08,
        network_expansion_planned=True,
        multi_site_count=3,
        centralized_rcm_investment_m=8.0,
        it_platform_investment_planned_m=6.0,
        inpatient_to_outpatient_shift_planned=True,
        owns_asc_or_hopd=True,
        cdi_program_planned=True,
        coding_gap_vs_peers_bps=35.0,
        bolt_on_pipeline_count=4,
        platform_services_named=True,
        labor_cost_reduction_planned_bps=80.0,
        supply_cost_reduction_planned_bps=50.0,
        productivity_improvement_planned_pct=0.06,
        de_novo_count_planned=2,
        bed_expansion_planned_count=25,
        service_line_addition_count=2,
    )


# ── Rendering ─────────────────────────────────────────────────────


def _sniff_hits_table(hits: List[Any]) -> str:
    if not hits:
        return (
            f'<div style="font-size:11px;color:{P["positive"]};padding:12px">'
            f"✓ No on-face concerns. Deal shape is plausible before the math.</div>"
        )
    bg = P["panel"]
    panel_alt = P["panel_alt"]
    text = P["text"]
    text_dim = P["text_dim"]

    rows = []
    for i, h in enumerate(hits):
        rb = panel_alt if i % 2 == 0 else bg
        name = getattr(h, "name", "") or ""
        kill_level = getattr(h, "kill_level", "") or ""
        message = getattr(h, "message", "") or ""

        rows.append(
            f'<tr style="background:{rb};vertical-align:top">'
            f'<td style="padding:8px 12px;width:110px;text-align:center">{_sev_badge(kill_level)}</td>'
            f'<td style="padding:8px 12px">'
            f'<div style="font-size:11px;font-weight:700;color:{text}">{_html.escape(name)}</div>'
            f'<div style="font-size:11px;color:{text};margin-top:4px;line-height:1.5">'
            f"{_html.escape(message)}</div>"
            f"</td></tr>"
        )
    return (
        f'<table style="width:100%;border-collapse:collapse;font-size:11px">'
        f'<tbody>{"".join(rows)}</tbody></table>'
    )


def _archetype_banner(report: Any) -> str:
    dominant = getattr(report, "dominant_archetype", "") or "unknown"
    confidence = getattr(report, "dominant_confidence_0_100", 0) or 0
    note = getattr(report, "partner_note", "") or ""

    conf_color = (
        P["positive"] if confidence >= 70 else (P["warning"] if confidence >= 40 else P["text_dim"])
    )
    return (
        f'<div style="background:{P["panel"]};border:1px solid {P["border"]};'
        f'padding:18px 22px;margin-bottom:16px;border-left:4px solid {P["accent"]}">'
        f'<div style="display:flex;align-items:center;gap:24px;flex-wrap:wrap">'
        f'<div>'
        f'<div style="font-size:9px;color:{P["text_dim"]};letter-spacing:0.08em;'
        f'text-transform:uppercase;margin-bottom:4px">Dominant archetype</div>'
        f'<div style="font-size:20px;font-weight:700;color:{P["accent"]};'
        f'font-family:JetBrains Mono,monospace;letter-spacing:0.02em">'
        f'{_html.escape(dominant.replace("_", " "))}</div>'
        f'</div>'
        f'<div>'
        f'<div style="font-size:9px;color:{P["text_dim"]};letter-spacing:0.08em;'
        f'text-transform:uppercase;margin-bottom:4px">Confidence</div>'
        f'<div style="font-size:26px;font-weight:700;color:{conf_color};'
        f'font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace">'
        f"{confidence}</div></div>"
        f'</div>'
        + (
            f'<div style="margin-top:14px;padding-top:12px;border-top:1px solid {P["border"]};'
            f'font-size:12px;color:{P["text"]};line-height:1.6">{_html.escape(note)}</div>'
            if note else ""
        )
        + "</div>"
    )


def _archetype_matches_table(matches: List[Any]) -> str:
    if not matches:
        return (
            f'<div style="font-size:11px;color:{P["text_dim"]};padding:12px">'
            f"No archetype signals matched above the threshold.</div>"
        )
    bg = P["panel"]
    panel_alt = P["panel_alt"]
    text = P["text"]
    text_dim = P["text_dim"]
    acc = P["accent"]

    rows = []
    for i, m in enumerate(matches):
        rb = panel_alt if i % 2 == 0 else bg
        archetype = getattr(m, "archetype", "") or ""
        conf = getattr(m, "confidence_0_100", 0) or 0
        levers = getattr(m, "typical_levers", []) or []
        risks = getattr(m, "typical_risks", []) or []
        partner_note = getattr(m, "partner_note", "") or ""

        lever_html = ", ".join(_html.escape(str(x)) for x in levers[:5])
        risk_html = ", ".join(_html.escape(str(x)) for x in risks[:5])

        conf_color = (
            P["positive"] if conf >= 70 else (P["warning"] if conf >= 40 else P["text_dim"])
        )
        rows.append(
            f'<tr style="background:{rb};vertical-align:top">'
            f'<td style="padding:10px 12px;width:80px;text-align:center">'
            f'<div style="font-size:16px;font-weight:700;color:{conf_color};'
            f'font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace">{conf}</div>'
            f"</td>"
            f'<td style="padding:10px 12px">'
            f'<div style="font-size:12px;font-weight:700;color:{text};'
            f'font-family:JetBrains Mono,monospace">{_html.escape(archetype)}</div>'
            + (
                f'<div style="font-size:11px;color:{acc};font-style:italic;margin-top:4px;'
                f'line-height:1.5">"{_html.escape(partner_note)}"</div>' if partner_note else ""
            )
            + (
                f'<div style="font-size:10px;color:{text_dim};margin-top:6px">'
                f'<span style="color:{text_dim}">Typical levers:</span> {lever_html}</div>'
                if lever_html else ""
            )
            + (
                f'<div style="font-size:10px;color:{text_dim};margin-top:3px">'
                f'<span style="color:{text_dim}">Typical risks:</span> {risk_html}</div>'
                if risk_html else ""
            )
            + "</td></tr>"
        )
    return (
        f'<table style="width:100%;border-collapse:collapse;font-size:11px">'
        f'<tbody>{"".join(rows)}</tbody></table>'
    )


# ── Main entry ───────────────────────────────────────────────────


def render_partner_brain_sniff(qp: Dict[str, str] | None = None) -> str:
    _ = qp or {}

    from rcm_mc.pe_intelligence.unrealistic_on_face_check import run_sniff_test
    from rcm_mc.pe_intelligence.healthcare_thesis_archetype_recognizer import (
        recognize_healthcare_thesis_archetypes,
    )

    try:
        sniff_report = run_sniff_test(_build_sniff_inputs())
        hits = list(getattr(sniff_report, "fired", []) or [])
        sniff_note = getattr(sniff_report, "partner_note", "") or ""
        sniff_verdict = getattr(sniff_report, "recommendation", "") or ""
    except Exception:  # noqa: BLE001
        hits, sniff_note, sniff_verdict = [], "", ""

    try:
        archetype_report = recognize_healthcare_thesis_archetypes(_build_archetype_signals())
        matches = list(getattr(archetype_report, "matches", []) or [])
    except Exception:  # noqa: BLE001
        archetype_report = None
        matches = []

    text = P["text"]
    text_dim = P["text_dim"]
    acc = P["accent"]

    high_hits = sum(
        1 for h in hits if (getattr(h, "severity", "") or "").upper() in ("CRITICAL", "HIGH")
    )
    verdict_color = (
        P["critical"] if sniff_verdict.upper() in ("PASS_ON_FACE", "FAIL") else
        (P["warning"] if sniff_verdict.upper() in ("STRETCH", "CAUTION") else P["positive"])
    )

    kpi_strip = (
        f'<div style="display:flex;gap:12px;flex-wrap:wrap;margin-bottom:20px">'
        f"{_kpi_tile('Sniff hits', str(len(hits)), P['warning'] if hits else P['positive'])}"
        f"{_kpi_tile('High/critical', str(high_hits), P['critical'] if high_hits else P['text'])}"
        f"{_kpi_tile('Verdict', sniff_verdict or '—', verdict_color)}"
        f"{_kpi_tile('Archetypes matched', str(len(matches)))}"
        f"{_kpi_tile('Dominant archetype', (getattr(archetype_report, 'dominant_archetype', '') or '—').replace('_', ' '))}"
        f"</div>"
    )

    demo_banner = (
        f'<div style="padding:10px 14px;margin-bottom:16px;background:{P["panel"]};'
        f'border:1px solid {P["warning"]};border-left:3px solid {P["warning"]};'
        f'font-size:11px;color:{text_dim};line-height:1.5">'
        f'<span style="color:{P["warning"]};font-weight:700;letter-spacing:0.05em">'
        f"DEMO DATA:</span> "
        f"Sniff inputs crafted to trigger common traps (aggressive IRR, "
        f"MA bridge without named contract, 400-bps 1-yr margin expansion). "
        f"Archetype signals reflect a typical payer-mix-shift / outpatient-migration hybrid."
        f"</div>"
    )

    sniff_note_html = ""
    if sniff_note:
        sniff_note_html = (
            f'<div style="background:{P["panel"]};border:1px solid {P["border"]};'
            f'padding:14px 16px;margin-bottom:16px">'
            f'<div style="font-size:10px;color:{P["text_dim"]};letter-spacing:0.08em;'
            f'text-transform:uppercase;margin-bottom:6px;font-weight:600">Partner read</div>'
            f'<div style="font-size:12px;color:{P["text"]};line-height:1.6">'
            f"{_html.escape(sniff_note)}</div></div>"
        )

    body = (
        f'<div style="padding:20px;max-width:1400px;margin:0 auto">'
        f'<div style="margin-bottom:16px">'
        f'<a href="/partner-brain" style="color:{acc};font-size:11px;text-decoration:none">'
        f"← Partner Brain hub</a></div>"
        f'<h1 style="font-size:18px;font-weight:700;color:{text};letter-spacing:0.02em">'
        f"Partner Brain · Sniff Test & Archetype</h1>"
        f'<p style="font-size:12px;color:{text_dim};margin-top:4px;line-height:1.5">'
        f"Before the math. The on-face scorecard catches implausible "
        f"projections (IRR 28% on a critical-access hospital, dental DSO "
        f"at 4× revenue, MA bridge without a named contract). The "
        f"archetype recognizer tells you what kind of deal this is so the "
        f"right lever stack and named risks apply.</p>"
        f"{demo_banner}"
        f"{kpi_strip}"
        f'{ck_section_header("On-face sniff test", "implausibility flags raised before the valuation math", len(hits))}'
        f'<div style="margin-top:8px">{sniff_note_html}{_sniff_hits_table(hits)}</div>'
        f'<div style="margin-top:32px"></div>'
        f'{ck_section_header("Archetype recognition", "healthcare-PE thesis shape and its lever stack", len(matches))}'
        f'<div style="margin-top:8px">'
    )
    if archetype_report is not None:
        body += _archetype_banner(archetype_report)
    body += _archetype_matches_table(matches)
    body += "</div></div>"

    return chartis_shell(
        body=body, title="Partner Brain · Sniff Test", active_nav="/partner-brain"
    )
