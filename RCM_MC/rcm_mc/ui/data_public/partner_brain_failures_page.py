"""Partner Brain · Named Failures — /partner-brain/failures.

Fingerprint-matches the current deal against dated historical
healthcare-PE failures and runs the nine deal-smell detectors.
Modules surfaced:

- ``named_failure_library_v2`` — 5 dated failure patterns
  (MA startup unwind 2023, NSA platform rate shock 2022, PDGM 2020,
  behavioral staffing collapse 2024, MA provider-risk 2023)
- ``deal_smell_detectors`` — 9 detectors:
  rollup running out, denials papering over concentration, founder
  wants out, EBITDA pulled forward, covenant close to trip,
  clinician flight, organic declining under rollup, management
  churn, regulatory soft issues
- ``denial_fix_pace_detector`` — specific named trap
- ``medicare_advantage_bridge_trap`` — specific named trap
- ``payer_renegotiation_timing_model`` — specific named trap

Phase 1 runs these on a seeded mid-market acute-care demo context.
Future phase wires real-packet loading via ?deal_id=X.
"""
from __future__ import annotations

import html as _html
from datetime import date
from typing import Any, Dict, List, Optional

from rcm_mc.ui._chartis_kit import P, chartis_shell, ck_section_header


_SEVERITY_COLORS = {
    "CRITICAL": P["critical"],
    "HIGH": P["negative"],
    "MEDIUM": P["warning"],
    "LOW": P["text_dim"],
    "INFO": P["text_dim"],
}


def _pb_severity_badge(sev: str) -> str:
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
        f"{_html.escape(value)}</div>"
        f"</div>"
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


def _build_v2_matcher_ctx():
    """Build a HeuristicContext for match_failures_v2. Uses the same
    seeded mid-market acute-care deal as the Partner Review page."""
    from rcm_mc.pe_intelligence.heuristics import HeuristicContext

    return HeuristicContext(
        payer_mix={
            "medicare": 0.32,
            "medicare_advantage": 0.22,  # elevated MA share → triggers MA patterns
            "medicaid": 0.16,
            "commercial": 0.25,
            "self_pay": 0.05,
        },
        ebitda_m=42.0,
        revenue_m=410.0,
        bed_count=420,
        hospital_type="acute_care",
        state="IL",
        denial_rate=0.12,
        days_in_ar=55.0,
        clean_claim_rate=0.86,
        case_mix_index=1.62,
        ebitda_margin=0.102,
        exit_multiple=12.0,
        projected_irr=0.24,
        projected_moic=2.7,
        denial_improvement_bps_per_yr=180.0,
        revenue_growth_pct_per_yr=0.07,
        deal_structure="FFS",
        leverage_multiple=5.8,
    )


def _build_smell_ctx():
    from rcm_mc.pe_intelligence.deal_smell_detectors import SmellContext
    return SmellContext(
        revenue_growth_from_acquisition_pct=0.85,
        revenue_growth_organic_pct=-0.015,
        pipeline_count=2,
        platform_age_years=4,
        acquisitions_per_year=6,
        top_payer_share=0.42,
        denial_rate=0.115,
        denial_rate_trend="rising",
        founder_ceo_in_place=True,
        founder_retiring_flag=True,
        ceo_age_60_plus=True,
        management_transitions_last_2yr=1,
        recent_ebitda_jump_pct=0.28,
        pro_forma_addbacks_pct=0.12,
        close_deadline_weeks=3,
        leverage=5.8,
        covenant_headroom_pct=0.09,
        key_clinician_departures_12mo=4,
        clinician_headcount=60,
        cms_survey_issues=True,
        litigation_count=1,
    )


def _build_denial_fix_inputs():
    from rcm_mc.pe_intelligence.denial_fix_pace_detector import DenialFixInputs
    return DenialFixInputs(
        current_initial_denial_rate_pct=12.0,
        target_denial_rate_pct=5.0,   # 700bps target over only 2 years → trap territory
        target_years=2,
        category_mix_pct={
            "eligibility": 0.22,
            "authorization": 0.26,
            "medical_necessity": 0.18,
            "coding": 0.14,
            "timely_filing": 0.10,
            "other": 0.10,
        },
        named_ops_partner=False,
        it_platform_investment_m=1.2,
    )


def _build_ma_bridge_inputs():
    from rcm_mc.pe_intelligence.medicare_advantage_bridge_trap import MABridgeInputs
    return MABridgeInputs(
        ffs_annual_revenue_m=180.0,
        ffs_annual_rate_cut_pct=0.03,
        ma_lives_current=8_000,
        ma_lives_growth_rate_annual=0.15,
        ma_pmpm_claimed=1_050.0,
        pmpm_is_gross=True,
        net_pmpm_realization_pct=0.78,
        ma_contract_is_named=False,  # trap — MA bridge without named contract
        ma_cannibalization_pct=0.40,
        ffs_pmpm_net=720.0,
        projection_years=5,
    )


def _build_reneg_inputs():
    from rcm_mc.pe_intelligence.payer_renegotiation_timing_model import (
        PayerContract,
        PayerRenegotiationInputs,
    )
    return PayerRenegotiationInputs(
        contracts=[
            PayerContract(
                name="Regional BCBS",
                payer_mix_pct=0.27,
                expiration_date=date(2027, 6, 30),
                posture="commercial_hard",
                override_rate_change_pct=None,
                already_repriced_locked_in=False,
            ),
            PayerContract(
                name="Mega MA Plan",
                payer_mix_pct=0.14,
                expiration_date=date(2028, 1, 31),
                posture="ma_hard",
                override_rate_change_pct=None,
                already_repriced_locked_in=False,
            ),
            PayerContract(
                name="State Medicaid",
                payer_mix_pct=0.09,
                expiration_date=date(2027, 9, 1),
                posture="medicaid_hard",
                override_rate_change_pct=None,
                already_repriced_locked_in=False,
            ),
        ],
        hold_start_date=date(2026, 4, 1),
        hold_years=5,
        base_npr_m=410.0,
        contribution_margin_pct=0.45,
    )


# ── Rendering helpers ─────────────────────────────────────────────


def _v2_matches_table(matches: List[Any]) -> str:
    if not matches:
        return (
            f'<div style="font-size:11px;color:{P["text_dim"]};padding:12px">'
            f"No named-failure patterns matched.</div>"
        )
    bg = P["panel"]
    panel_alt = P["panel_alt"]
    border = P["border"]
    text = P["text"]
    text_dim = P["text_dim"]
    acc = P["accent"]

    rows = []
    for i, m in enumerate(matches):
        rb = panel_alt if i % 2 == 0 else bg
        pattern = getattr(m, "pattern_id", "") or ""
        score = getattr(m, "match_score_0_100", 0) or 0
        color = P["critical"] if score >= 70 else (P["warning"] if score >= 40 else P["text_dim"])
        name = getattr(m, "pattern_name", pattern) or pattern
        partner_note = getattr(m, "partner_commentary", "") or ""
        triggers = getattr(m, "triggers_matched", []) or []
        triggers_html = ", ".join(_html.escape(str(t)) for t in triggers[:6])

        rows.append(
            f'<tr style="background:{rb};vertical-align:top">'
            f'<td style="padding:10px 12px;width:100px">'
            f'<div style="font-size:20px;font-weight:700;color:{color};'
            f'font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace">{score}</div>'
            f'<div style="font-size:9px;color:{text_dim};letter-spacing:0.08em">MATCH</div>'
            f"</td>"
            f'<td style="padding:10px 12px">'
            f'<div style="font-size:12px;font-weight:700;color:{text}">{_html.escape(name)}</div>'
            f'<div style="font-size:10px;color:{text_dim};font-family:JetBrains Mono,monospace;'
            f'margin-top:2px">{_html.escape(pattern)}</div>'
            f'<div style="font-size:11px;color:{acc};font-style:italic;margin-top:6px;'
            f'line-height:1.5">"{_html.escape(partner_note)}"</div>'
            f'<div style="font-size:10px;color:{text_dim};margin-top:6px">'
            f'<span style="color:{text_dim}">Triggers:</span> {triggers_html}</div>'
            f"</td></tr>"
        )
    return (
        f'<table style="width:100%;border-collapse:collapse;font-size:11px">'
        f'<tbody>{"".join(rows)}</tbody></table>'
    )


def _smells_table(smells: List[Any]) -> str:
    if not smells:
        return (
            f'<div style="font-size:11px;color:{P["text_dim"]};padding:12px">'
            f"No deal smells detected on this context.</div>"
        )
    bg = P["panel"]
    panel_alt = P["panel_alt"]
    border = P["border"]
    text = P["text"]
    text_dim = P["text_dim"]
    acc = P["accent"]

    rows = []
    for i, s in enumerate(smells):
        rb = panel_alt if i % 2 == 0 else bg
        name = getattr(s, "name", "") or ""
        severity = getattr(s, "severity", "") or ""
        finding = getattr(s, "finding", "") or ""
        partner_note = getattr(s, "partner_note", "") or ""
        remediation = getattr(s, "remediation", "") or ""

        rem_html = (
            f'<div style="font-size:10px;color:{text_dim};margin-top:4px;'
            f'line-height:1.5"><span style="color:{text_dim}">Remediation:</span> '
            f"{_html.escape(remediation)}</div>"
            if remediation else ""
        )
        note_html = (
            f'<div style="font-size:11px;color:{acc};font-style:italic;margin-top:4px;'
            f'line-height:1.5">"{_html.escape(partner_note)}"</div>'
            if partner_note else ""
        )
        rows.append(
            f'<tr style="background:{rb};vertical-align:top">'
            f'<td style="padding:8px 12px;width:80px;text-align:center">{_pb_severity_badge(severity)}</td>'
            f'<td style="padding:8px 12px">'
            f'<div style="font-size:11px;font-weight:700;color:{text}">{_html.escape(name)}</div>'
            f'<div style="font-size:10px;color:{text_dim};margin-top:3px;line-height:1.5">'
            f"{_html.escape(finding)}</div>"
            f"{note_html}{rem_html}"
            f"</td></tr>"
        )
    return (
        f'<table style="width:100%;border-collapse:collapse;font-size:11px">'
        f'<tbody>{"".join(rows)}</tbody></table>'
    )


def _denial_fix_block(report: Any) -> str:
    verdict = getattr(report, "verdict", "") or ""
    note = getattr(report, "partner_note", "") or ""
    realistic = getattr(report, "realistic_achievable_bps", 0)
    target_bps = getattr(report, "target_bps", 0)

    color = P["critical"] if verdict == "AGGRESSIVE_TRAP" else (
        P["warning"] if verdict == "STRETCH" else P["positive"]
    )
    return (
        f'<div style="padding:4px 0">'
        f'<div style="display:flex;align-items:center;gap:10px;margin-bottom:8px">'
        f'<span style="font-size:10px;color:{color};border:1px solid {color};'
        f'padding:2px 8px;letter-spacing:0.08em;font-family:JetBrains Mono,monospace">'
        f"{_html.escape(str(verdict))}</span>"
        f'<span style="font-size:10px;color:{P["text_dim"]}">'
        f"target {target_bps:.0f} bps · achievable {realistic:.0f} bps</span>"
        f"</div>"
        f'<div style="font-size:11px;color:{P["text"]};line-height:1.6">{_html.escape(note)}</div>'
        f"</div>"
    )


def _ma_bridge_block(report: Any) -> str:
    verdict = getattr(report, "verdict", "") or ""
    note = getattr(report, "partner_note", "") or ""
    bridge_gap = getattr(report, "bridge_gap_m", 0) or 0
    color = P["critical"] if "TRAP" in verdict else P["warning"]
    return (
        f'<div style="padding:4px 0">'
        f'<div style="display:flex;align-items:center;gap:10px;margin-bottom:8px">'
        f'<span style="font-size:10px;color:{color};border:1px solid {color};'
        f'padding:2px 8px;letter-spacing:0.08em;font-family:JetBrains Mono,monospace">'
        f"{_html.escape(str(verdict))}</span>"
        f'<span style="font-size:10px;color:{P["text_dim"]}">'
        f"bridge gap ${bridge_gap:.1f}M</span>"
        f"</div>"
        f'<div style="font-size:11px;color:{P["text"]};line-height:1.6">{_html.escape(note)}</div>'
        f"</div>"
    )


def _reneg_block(report: Any) -> str:
    ebitda_impact = getattr(report, "total_ebitda_impact_m", 0) or 0
    npr_impact = getattr(report, "total_npr_impact_m", 0) or 0
    trap = bool(getattr(report, "trap_flag", False))
    note = getattr(report, "partner_note", "") or ""
    color = P["critical"] if trap else (
        P["warning"] if abs(ebitda_impact) >= 2 else P["text_dim"]
    )
    trap_badge = (
        f'<span style="font-size:9px;color:{P["critical"]};'
        f'border:1px solid {P["critical"]};padding:2px 6px;'
        f'letter-spacing:0.08em;font-family:JetBrains Mono,monospace">TRAP</span>'
    ) if trap else ""
    return (
        f'<div style="padding:4px 0">'
        f'<div style="display:flex;align-items:center;gap:10px;margin-bottom:8px;flex-wrap:wrap">'
        f'<span style="font-size:18px;font-weight:700;color:{color};'
        f'font-family:JetBrains Mono,monospace;font-variant-numeric:tabular-nums">'
        f"${ebitda_impact:+.1f}M</span>"
        f'<span style="font-size:9px;color:{P["text_dim"]};letter-spacing:0.08em">'
        f"EBITDA IMPACT OVER HOLD</span>"
        f'<span style="font-size:11px;color:{P["text_dim"]};font-family:JetBrains Mono,monospace">'
        f"NPR ${npr_impact:+.1f}M</span>"
        f"{trap_badge}"
        f"</div>"
        f'<div style="font-size:11px;color:{P["text"]};line-height:1.6">{_html.escape(note)}</div>'
        f"</div>"
    )


# ── Main entry ────────────────────────────────────────────────────


def render_partner_brain_failures(qp: Dict[str, str] | None = None) -> str:
    _ = qp or {}

    # Run all modules on the demo context.
    from rcm_mc.pe_intelligence.named_failure_library_v2 import match_failures_v2
    from rcm_mc.pe_intelligence.deal_smell_detectors import detect_smells
    from rcm_mc.pe_intelligence.denial_fix_pace_detector import analyze_denial_fix_pace
    from rcm_mc.pe_intelligence.medicare_advantage_bridge_trap import analyze_ma_bridge
    from rcm_mc.pe_intelligence.payer_renegotiation_timing_model import (
        project_payer_renegotiations,
    )

    try:
        v2_report = match_failures_v2(_build_v2_matcher_ctx())
        v2_matches = list(getattr(v2_report, "matches", []) or [])
    except Exception:  # noqa: BLE001
        v2_matches = []

    try:
        smell_report = detect_smells(_build_smell_ctx())
        smells = list(getattr(smell_report, "smells", []) or [])
    except Exception:  # noqa: BLE001
        smells = []

    try:
        denial_report = analyze_denial_fix_pace(_build_denial_fix_inputs())
    except Exception:  # noqa: BLE001
        denial_report = None

    try:
        ma_report = analyze_ma_bridge(_build_ma_bridge_inputs())
    except Exception:  # noqa: BLE001
        ma_report = None

    try:
        reneg_report = project_payer_renegotiations(_build_reneg_inputs())
    except Exception:  # noqa: BLE001
        reneg_report = None

    # Compose the page.
    bg = P["bg"]
    text = P["text"]
    text_dim = P["text_dim"]
    acc = P["accent"]

    high_matches = sum(
        1 for m in v2_matches if getattr(m, "match_score_0_100", 0) >= 70
    )
    critical_smells = sum(
        1 for s in smells if getattr(s, "severity", "").upper() == "CRITICAL"
    )
    high_smells = sum(
        1 for s in smells if getattr(s, "severity", "").upper() == "HIGH"
    )

    kpi_strip = (
        f'<div style="display:flex;gap:12px;flex-wrap:wrap;margin-bottom:20px">'
        f"{_kpi_tile('Named patterns scanned', str(len(v2_matches) + 3))}"
        f"{_kpi_tile('High-confidence matches (≥70)', str(high_matches), P['critical'] if high_matches else P['text'])}"
        f"{_kpi_tile('Deal smells fired', str(len(smells)), P['warning'] if smells else P['text'])}"
        f"{_kpi_tile('Critical smells', str(critical_smells), P['critical'] if critical_smells else P['text'])}"
        f"{_kpi_tile('High smells', str(high_smells), P['negative'] if high_smells else P['text'])}"
        f"</div>"
    )

    # Named trap subsections (each own named module).
    named_traps_html = ""
    if denial_report is not None:
        named_traps_html += _panel(
            "Denial-fix pace detector",
            _denial_fix_block(denial_report),
        )
    if ma_report is not None:
        named_traps_html += _panel(
            "MA bridge trap",
            _ma_bridge_block(ma_report),
        )
    if reneg_report is not None:
        named_traps_html += _panel(
            "Payer renegotiation timing",
            _reneg_block(reneg_report),
        )

    # Demo banner.
    demo_banner = (
        f'<div style="padding:10px 14px;margin-bottom:16px;background:{P["panel"]};'
        f'border:1px solid {P["warning"]};border-left:3px solid {P["warning"]};'
        f'font-size:11px;color:{text_dim};line-height:1.5">'
        f'<span style="color:{P["warning"]};font-weight:700;letter-spacing:0.05em">'
        f"DEMO DATA:</span> "
        f"All 5 modules running on seeded mid-market acute-care contexts. "
        f"Later phase wires real packet loading via <code>?deal_id=X</code>."
        f"</div>"
    )

    body = (
        f'<div style="padding:20px;max-width:1400px;margin:0 auto">'
        f'<div style="margin-bottom:16px">'
        f'<a href="/partner-brain" style="color:{acc};font-size:11px;text-decoration:none">'
        f"← Partner Brain hub</a></div>"
        f'<h1 style="font-size:18px;font-weight:700;color:{text};letter-spacing:0.02em">'
        f"Partner Brain · Named Failures</h1>"
        f'<p style="font-size:12px;color:{text_dim};margin-top:4px;line-height:1.5">'
        f"Fingerprint-matches against dated historical failures plus the "
        f"nine deal-smell detectors. If the current deal rhymes with MA "
        f"unwind 2023, NSA 2022, PDGM 2020, or any of the named traps, "
        f"it shows up here before the math does.</p>"
        f"{demo_banner}"
        f"{kpi_strip}"
        f'{ck_section_header("Named failure patterns (v2)", "historical pattern fingerprint matching", len(v2_matches))}'
        f'<div style="margin-top:8px">{_v2_matches_table(v2_matches)}</div>'
        f'<div style="margin-top:24px"></div>'
        f'{ck_section_header("Named traps — deep modules", "each module is a dated trap with its own math", 3)}'
        f"{named_traps_html}"
        f'<div style="margin-top:24px"></div>'
        f'{ck_section_header("Deal smell detectors", "9-detector scan for non-pattern red flags", len(smells))}'
        f'<div style="margin-top:8px">{_smells_table(smells)}</div>'
        f"</div>"
    )

    return chartis_shell(
        body=body, title="Partner Brain · Named Failures", active_nav="/partner-brain"
    )
