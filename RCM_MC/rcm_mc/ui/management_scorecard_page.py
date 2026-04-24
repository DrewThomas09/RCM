"""Management Scorecard page at /diligence/management.

Per-executive scored cards + roster-level aggregate + named
haircut recommendation that flows into the EBITDA bridge.

Demo roster seeds a plausible 4-person C-suite so the page is
never empty. Real engagements would hydrate from Deal Profile
metadata + partner reference notes.
"""
from __future__ import annotations

import html
from typing import Any, Dict, List, Optional

from ..diligence.management_scorecard import (
    BridgeHaircutInput, ComplevelBand, Executive, ExecutiveScore,
    ForecastHistory, ManagementReport, PriorRole, RedFlag, Role,
    analyze_team,
)
from ._chartis_kit import P, chartis_shell
from .power_ui import (
    bookmark_hint, export_json_panel, provenance, sortable_table,
)


def _scoped_styles() -> str:
    css = """
.ms-wrap{{font-family:"Helvetica Neue",Arial,sans-serif;}}
.ms-eyebrow{{font-size:11px;letter-spacing:1.6px;text-transform:uppercase;
color:{tf};font-weight:600;}}
.ms-h1{{font-size:26px;color:{tx};font-weight:600;line-height:1.15;
margin:4px 0 0 0;letter-spacing:-.2px;}}
.ms-callout{{background:{pa};padding:12px 16px;
border-left:3px solid {ac};border-radius:0 3px 3px 0;
font-size:12px;color:{td};line-height:1.65;max-width:880px;margin-top:12px;}}
.ms-callout.alert{{border-left-color:{ne};color:{ne};
font-weight:600;font-size:13px;}}
.ms-callout.warn{{border-left-color:{wn};color:{wn};
font-weight:600;font-size:13px;}}
.ms-callout.good{{border-left-color:{po};color:{po};
font-weight:600;font-size:13px;}}
.ms-section-label{{font-size:10px;letter-spacing:1.6px;text-transform:uppercase;
font-weight:700;color:{tf};margin:22px 0 10px 0;}}
.ms-kpi-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));
gap:14px;margin-top:18px;}}
.ms-kpi{{background:{pn};border:1px solid {bd};border-radius:4px;
padding:14px 16px;}}
.ms-kpi__label{{font-size:9px;letter-spacing:1.4px;text-transform:uppercase;
color:{tf};margin-bottom:6px;font-weight:600;}}
.ms-kpi__val{{font-size:28px;line-height:1;font-family:"JetBrains Mono",monospace;
font-variant-numeric:tabular-nums;font-weight:700;}}
.ms-card{{background:{pn};border:1px solid {bd};border-radius:4px;
margin-bottom:14px;overflow:hidden;
transition:border-color 140ms ease,box-shadow 140ms ease;}}
.ms-card:hover{{border-color:{tf};box-shadow:0 6px 16px rgba(0,0,0,0.3);}}
.ms-card__band{{height:3px;}}
.ms-card__body{{padding:16px 20px;}}
.ms-card__head{{display:flex;justify-content:space-between;
align-items:flex-start;gap:18px;flex-wrap:wrap;}}
.ms-card__meta{{min-width:280px;}}
.ms-card__name{{font-size:17px;color:{tx};font-weight:600;
letter-spacing:-.15px;}}
.ms-card__role{{font-size:10px;letter-spacing:1.3px;text-transform:uppercase;
color:{tf};margin-bottom:4px;}}
.ms-card__overall{{text-align:right;min-width:130px;}}
.ms-card__overall-val{{font-size:36px;line-height:1;
font-family:"JetBrains Mono",monospace;font-weight:700;
font-variant-numeric:tabular-nums;}}
.ms-dim-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));
gap:14px;margin-top:14px;}}
.ms-dim{{background:{pa};border-radius:3px;padding:10px 12px;
border-left:2px solid {bd};}}
.ms-dim__label{{font-size:9px;letter-spacing:1.3px;text-transform:uppercase;
color:{tf};font-weight:600;margin-bottom:3px;}}
.ms-dim__score{{font-size:18px;font-family:"JetBrains Mono",monospace;
font-variant-numeric:tabular-nums;font-weight:700;margin-bottom:4px;}}
.ms-dim__reason{{font-size:11px;color:{td};line-height:1.5;}}
.ms-flag{{background:{pa};padding:8px 12px;border-left:2px solid {ne};
border-radius:0 3px 3px 0;margin:6px 0;font-size:11.5px;color:{td};
line-height:1.55;}}
.ms-flag__severity{{font-size:9px;letter-spacing:1.3px;text-transform:uppercase;
font-weight:700;margin-right:6px;}}
.ms-haircut{{background:{pn};border:1px solid {bd};border-radius:4px;
padding:16px 20px;margin-top:16px;position:relative;overflow:hidden;}}
.ms-haircut::before{{content:"";position:absolute;top:0;left:0;right:0;
height:2px;background:linear-gradient(90deg,{ne},{ac});}}
""".format(
        tx=P["text"], td=P["text_dim"], tf=P["text_faint"],
        pn=P["panel"], pa=P["panel_alt"],
        bd=P["border"], ac=P["accent"],
        po=P["positive"], wn=P["warning"], ne=P["negative"],
    )
    return f"<style>{css}</style>"


def _demo_team() -> List[Executive]:
    """An 4-exec demo C-suite with a mix of strengths + red flags."""
    return [
        Executive(
            name="Jane Doe",
            role=Role.CEO,
            years_in_role=3.5,
            years_at_facility=3.5,
            total_cash_comp_usd=900_000,
            has_equity_rollover=True,
            has_clawback_provisions=True,
            performance_weighted_bonus=True,
            comp_band=ComplevelBand.P75,
            forecast_history=[
                ForecastHistory("Q1 2025", "EBITDA", 8_500_000, 7_900_000),
                ForecastHistory("Q2 2025", "EBITDA", 9_000_000, 7_800_000),
                ForecastHistory("Q3 2025", "EBITDA", 9_500_000, 8_200_000),
                ForecastHistory("Q4 2025", "EBITDA", 10_000_000, 8_800_000),
            ],
            prior_roles=[
                PriorRole(employer="RegionCo Health", role="CEO",
                          start_year=2017, end_year=2021,
                          outcome="STRONG_EXIT"),
                PriorRole(employer="Steward Regional", role="COO",
                          start_year=2014, end_year=2017,
                          outcome="CHAPTER_11"),
            ],
            reference_note=(
                "Partner call with 2 prior board members — "
                "credited for RegionCo turnaround; Steward role "
                "was operational, not strategic."
            ),
        ),
        Executive(
            name="Robert Smith",
            role=Role.CFO,
            years_in_role=2.0,
            years_at_facility=2.0,
            total_cash_comp_usd=520_000,
            has_equity_rollover=True,
            has_clawback_provisions=False,
            performance_weighted_bonus=False,
            comp_band=ComplevelBand.P50,
            forecast_history=[
                ForecastHistory("Q1 2025", "Revenue", 60_000_000, 58_000_000),
                ForecastHistory("Q2 2025", "Revenue", 62_000_000, 60_500_000),
                ForecastHistory("Q3 2025", "Revenue", 64_000_000, 62_000_000),
            ],
            prior_roles=[
                PriorRole(employer="HealthCo", role="VP Finance",
                          start_year=2020, end_year=2023,
                          outcome="IN_PROGRESS"),
            ],
        ),
        Executive(
            name="Marcus Chen",
            role=Role.COO,
            years_in_role=6.0,
            years_at_facility=6.0,
            total_cash_comp_usd=480_000,
            has_equity_rollover=True,
            has_clawback_provisions=True,
            comp_band=ComplevelBand.P50,
            prior_roles=[
                PriorRole(employer="NationalHealth", role="VP Ops",
                          start_year=2012, end_year=2018,
                          outcome="STRONG_PUBLIC"),
            ],
        ),
        Executive(
            name="Dr. Patricia Okafor",
            role=Role.CMO,
            years_in_role=0.8,
            years_at_facility=0.8,
            total_cash_comp_usd=650_000,
            comp_band=ComplevelBand.ABOVE_P90,
            prior_roles=[
                PriorRole(employer="Academic Medical Center",
                          role="Dept Chief", start_year=2015,
                          end_year=2024, outcome="IN_PROGRESS"),
            ],
            reference_note=(
                "Recent hire — partner should ask why the prior CMO "
                "left; comp above p90 is Stark-exposed."
            ),
        ),
    ]


# ────────────────────────────────────────────────────────────────────
# Helpers
# ────────────────────────────────────────────────────────────────────

def _score_color(score: int) -> str:
    if score >= 80:
        return P["positive"]
    if score >= 60:
        return P["text"]
    if score >= 40:
        return P["warning"]
    return P["negative"]


_SEVERITY_COLOR: Dict[str, str] = {
    "CRITICAL": "critical",
    "HIGH": "negative",
    "MEDIUM": "warning",
    "LOW": "text_dim",
}


_DIMENSION_TOOLTIPS: Dict[str, str] = {
    "Forecast reliability": (
        "Score from historical guidance-vs-actual data. 100 = hit "
        "every period; 0 = missed by 20%+ on average. <40 triggers "
        "a bridge-lever haircut on FY1 guidance."
    ),
    "Comp structure": (
        "Score combines FMV band (p50 / p75 / above-p90) × equity "
        "rollover × clawbacks × performance-weighted bonus. Above-p90 "
        "is Stark-exposed; below-p50 is retention risk."
    ),
    "Tenure": (
        "Years at facility. 100 at ≥5 years, 0 at <1 year, linear "
        "between. Short tenure means reference the predecessor."
    ),
    "Prior-role reputation": (
        "Weighted by most recent → oldest. Each prior role scored "
        "by outcome: strong exit 100 · in-progress 60 · Ch.11 or "
        "distressed sale <30. Ch.11 outcomes trigger CRITICAL flag."
    ),
}


def _dim_tile(label: str, score: int, reason: str) -> str:
    color = _score_color(score)
    band_label = (
        "STRONG" if score >= 80
        else "GOOD" if score >= 60
        else "WEAK" if score >= 40
        else "RED FLAG"
    )
    tooltip = _DIMENSION_TOOLTIPS.get(label, "")
    tooltip_attr = (
        f' title="{html.escape(tooltip)}"' if tooltip else ""
    )
    return (
        f'<div class="ms-dim" style="border-left-color:{color};"'
        f'{tooltip_attr}>'
        f'<div class="ms-dim__label">{html.escape(label)}</div>'
        f'<div class="ms-dim__score" style="color:{color};">'
        f'{score}<span style="font-size:11px;opacity:.6;"> / 100</span>'
        f'</div>'
        f'<div style="font-size:9px;letter-spacing:1.2px;'
        f'text-transform:uppercase;color:{color};font-weight:700;'
        f'margin-bottom:4px;">{band_label}</div>'
        f'<div class="ms-dim__reason">{html.escape(reason)}</div>'
        f'</div>'
    )


def _score_band_legend() -> str:
    """Same legend as Exit Timing — reinforces the consistent
    0-40 red / 40-70 amber / 70-100 green pattern across pages."""
    return (
        f'<div style="display:flex;gap:10px;align-items:center;'
        f'flex-wrap:wrap;font-size:10px;color:{P["text_faint"]};'
        f'letter-spacing:.5px;margin:14px 0 6px 0;">'
        f'<span>Score bands:</span>'
        f'<span style="color:{P["negative"]};font-weight:600;">'
        f'◆ 0-40 red flag</span>'
        f'<span style="color:{P["warning"]};font-weight:600;">'
        f'◆ 40-60 weak</span>'
        f'<span style="color:{P["text"]};font-weight:600;">'
        f'◆ 60-80 good</span>'
        f'<span style="color:{P["positive"]};font-weight:600;">'
        f'◆ 80-100 strong</span>'
        f'</div>'
    )


def _flag_block(flag: RedFlag) -> str:
    color_key = _SEVERITY_COLOR.get(flag.severity, "text_faint")
    color = P.get(color_key, P["text_faint"])
    return (
        f'<div class="ms-flag" style="border-left-color:{color};">'
        f'<span class="ms-flag__severity" style="color:{color};">'
        f'{html.escape(flag.severity)}</span>'
        f'{html.escape(flag.detail)}</div>'
    )


def _exec_card(s: ExecutiveScore) -> str:
    overall_color = _score_color(s.overall)
    band_color = (
        P["negative"] if s.is_red_flag
        else P["positive"] if s.overall >= 75
        else P["warning"] if s.overall >= 55
        else P["negative"]
    )
    flags_html = "".join(_flag_block(f) for f in s.red_flags)
    reference = ""
    if s.executive.reference_note:
        reference = (
            f'<div style="margin-top:10px;padding:8px 12px;'
            f'background:{P["panel_alt"]};border-left:2px solid '
            f'{P["accent"]};font-style:italic;font-size:11.5px;'
            f'color:{P["text_dim"]};line-height:1.55;'
            f'border-radius:0 3px 3px 0;">'
            f'<strong style="color:{P["text"]};font-style:normal;'
            f'font-size:9px;letter-spacing:1.2px;text-transform:uppercase;'
            f'margin-right:4px;">Reference note:</strong>'
            f'{html.escape(s.executive.reference_note)}</div>'
        )
    haircut_line = ""
    if s.guidance_haircut_pct and s.guidance_haircut_pct > 0.01:
        haircut_line = (
            f'<div style="margin-top:10px;padding:8px 12px;'
            f'background:{P["panel_alt"]};border-left:2px solid '
            f'{P["warning"]};border-radius:0 3px 3px 0;'
            f'font-size:11.5px;color:{P["warning"]};font-weight:600;'
            f'line-height:1.5;">'
            f'Suggested guidance haircut: '
            f'{s.guidance_haircut_pct*100:.1f}% '
            f'based on this executive\'s historical miss rate.'
            f'</div>'
        )
    return (
        f'<div class="ms-card">'
        f'<div class="ms-card__band" style="background:{band_color};"></div>'
        f'<div class="ms-card__body">'
        f'<div class="ms-card__head">'
        f'<div class="ms-card__meta">'
        f'<div class="ms-card__role">'
        f'{html.escape(s.executive.role.value)} · '
        f'{s.executive.years_at_facility or s.executive.years_in_role or 0:.1f}y tenure'
        f'</div>'
        f'<div class="ms-card__name">{html.escape(s.executive.name)}</div>'
        f'<div style="font-size:10px;color:{P["text_faint"]};'
        f'margin-top:2px;letter-spacing:1px;">'
        f'Confidence: {html.escape(s.confidence)}</div>'
        f'</div>'
        f'<div class="ms-card__overall">'
        f'<div class="ms-card__role">Overall</div>'
        f'<div class="ms-card__overall-val" style="color:{overall_color};">'
        f'{s.overall}<span style="font-size:14px;opacity:.6;"> / 100</span>'
        f'</div>'
        f'</div>'
        f'</div>'
        f'<div class="ms-dim-grid">'
        f'{_dim_tile("Forecast reliability", s.forecast_reliability, s.forecast_reason)}'
        f'{_dim_tile("Comp structure", s.comp_structure, s.comp_reason)}'
        f'{_dim_tile("Tenure", s.tenure, s.tenure_reason)}'
        f'{_dim_tile("Prior-role reputation", s.prior_role_reputation, s.prior_reason)}'
        f'</div>'
        f'{flags_html}'
        f'{haircut_line}'
        f'{reference}'
        f'</div>'
        f'</div>'
    )


def _hero(report: ManagementReport, target_name: str) -> str:
    overall_color = _score_color(report.aggregate_overall)

    if report.has_critical_flags:
        banner_class = "alert"
    elif report.red_flag_count > 3:
        banner_class = "warn"
    elif report.aggregate_overall >= 75:
        banner_class = "good"
    else:
        banner_class = "warn"

    haircut_num_html = "—"
    haircut_detail = ""
    if report.bridge_haircut and report.bridge_haircut.recommended_haircut_pct > 0:
        hc = report.bridge_haircut
        haircut_num_html = provenance(
            f'{hc.recommended_haircut_pct*100:.1f}%',
            source="BridgeHaircutInput",
            formula="max(ceo_miss_rate, cfo_miss_rate) capped at 25%",
            detail=(
                "Applied to management's FY1 EBITDA guidance. This "
                "is the expected-miss adjustment based on historical "
                "guidance-vs-actual data from the CEO + CFO."
            ),
        )
        if hc.dollar_adjustment_usd:
            haircut_detail = (
                f'≈ ${hc.dollar_adjustment_usd:,.0f} EBITDA adjustment'
            )

    return (
        f'<div style="padding:22px 0 16px 0;border-bottom:1px solid '
        f'{P["border"]};margin-bottom:22px;">'
        f'<div class="ms-eyebrow">Management Scorecard</div>'
        f'<div class="ms-h1">{html.escape(target_name)}</div>'
        f'<div style="font-size:11px;color:{P["text_faint"]};margin-top:4px;">'
        f'{report.team_size} executive'
        f'{"s" if report.team_size != 1 else ""} scored · '
        f'{report.aggregate_confidence} confidence · '
        f'{report.red_flag_count} red flags '
        f'({report.critical_flag_count} critical)</div>'
        f'<div class="ms-callout {banner_class}">'
        f'{html.escape(report.summary)}</div>'
        f'<div class="ms-kpi-grid">'
        f'<div class="ms-kpi">'
        f'<div class="ms-kpi__label">Team aggregate</div>'
        f'<div class="ms-kpi__val" style="color:{overall_color};">'
        f'{report.aggregate_overall}<span style="font-size:14px;opacity:.6;"> / 100</span>'
        f'</div>'
        f'<div style="font-size:10px;color:{P["text_faint"]};margin-top:3px;">'
        f'role-weighted (CEO 35% · CFO 25% · COO 20% · other 20%)</div>'
        f'</div>'
        f'<div class="ms-kpi">'
        f'<div class="ms-kpi__label">Team size</div>'
        f'<div class="ms-kpi__val" style="color:{P["text"]};">'
        f'{report.team_size}</div>'
        f'<div style="font-size:10px;color:{P["text_faint"]};margin-top:3px;">'
        f'C-suite profiles assembled</div>'
        f'</div>'
        f'<div class="ms-kpi">'
        f'<div class="ms-kpi__label">Red flags</div>'
        f'<div class="ms-kpi__val" style="color:'
        f'{P["negative"] if report.red_flag_count > 0 else P["positive"]};">'
        f'{report.red_flag_count}</div>'
        f'<div style="font-size:10px;color:{P["text_faint"]};margin-top:3px;">'
        f'{report.critical_flag_count} CRITICAL</div>'
        f'</div>'
        f'<div class="ms-kpi">'
        f'<div class="ms-kpi__label">Guidance haircut</div>'
        f'<div class="ms-kpi__val" style="color:'
        f'{P["warning"] if report.bridge_haircut and report.bridge_haircut.recommended_haircut_pct > 0.05 else P["text_faint"]};">'
        f'{haircut_num_html}</div>'
        f'<div style="font-size:10px;color:{P["text_faint"]};margin-top:3px;">'
        f'{html.escape(haircut_detail) or "applied to FY1 EBITDA"}</div>'
        f'</div>'
        f'</div>'
        f'</div>'
    )


def _bridge_haircut_block(haircut: Optional[BridgeHaircutInput]) -> str:
    if haircut is None or haircut.recommended_haircut_pct <= 0.01:
        return ""
    conf_color = {
        "HIGH": P["positive"], "MEDIUM": P["warning"],
        "LOW": P["negative"],
    }.get(haircut.confidence, P["text_dim"])
    dollar_html = (
        f'<div><div style="font-size:9px;color:{P["text_faint"]};'
        f'letter-spacing:1.2px;text-transform:uppercase;'
        f'font-weight:600;">Dollar adjustment</div>'
        f'<div style="font-size:22px;color:{P["negative"]};'
        f'font-family:\'JetBrains Mono\',monospace;font-weight:700;">'
        f'${haircut.dollar_adjustment_usd:,.0f}</div>'
        f'<div style="font-size:10px;color:{P["text_faint"]};">'
        f'applied to FY1 EBITDA guidance</div></div>'
    ) if haircut.dollar_adjustment_usd else ""
    return (
        f'<div class="ms-haircut">'
        f'<div class="ms-eyebrow">EBITDA Bridge · Management-Reliability Lever</div>'
        f'<div style="font-size:16px;color:{P["text"]};font-weight:600;'
        f'margin-top:2px;">Forecast haircut recommendation</div>'
        f'<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));'
        f'gap:18px;margin-top:14px;">'
        f'<div><div style="font-size:9px;color:{P["text_faint"]};'
        f'letter-spacing:1.2px;text-transform:uppercase;'
        f'font-weight:600;">Recommended haircut</div>'
        f'<div style="font-size:28px;color:{P["warning"]};'
        f'font-family:\'JetBrains Mono\',monospace;font-weight:700;">'
        f'{haircut.recommended_haircut_pct*100:.1f}%</div>'
        f'<div style="font-size:10px;color:{P["text_faint"]};">'
        f'of FY1 EBITDA guidance</div></div>'
        f'{dollar_html}'
        f'<div><div style="font-size:9px;color:{P["text_faint"]};'
        f'letter-spacing:1.2px;text-transform:uppercase;'
        f'font-weight:600;">Source executives</div>'
        f'<div style="font-size:14px;color:{P["text"]};'
        f'font-weight:600;margin-top:4px;">'
        f'{html.escape(", ".join(haircut.source_executives) or "—")}</div>'
        f'<div style="font-size:10px;color:{P["text_faint"]};">'
        f'historical miss rate</div></div>'
        f'<div><div style="font-size:9px;color:{P["text_faint"]};'
        f'letter-spacing:1.2px;text-transform:uppercase;'
        f'font-weight:600;">Confidence</div>'
        f'<div style="font-size:18px;color:{conf_color};font-weight:600;'
        f'margin-top:4px;">{html.escape(haircut.confidence)}</div>'
        f'<div style="font-size:10px;color:{P["text_faint"]};">'
        f'data breadth</div></div>'
        f'</div>'
        f'<div style="margin-top:14px;padding:10px 14px;'
        f'background:{P["panel_alt"]};border-left:2px solid '
        f'{P["accent"]};border-radius:0 3px 3px 0;'
        f'font-size:11.5px;color:{P["text_dim"]};line-height:1.6;'
        f'max-width:880px;">'
        f'<strong style="color:{P["text"]};">How to use: </strong>'
        f'{html.escape(haircut.narrative)}'
        f'</div></div>'
    )


def render_management_scorecard_page(
    qs: Optional[Dict[str, List[str]]] = None,
) -> str:
    qs = qs or {}
    target_name = (qs.get("target_name") or ["Target Hospital System"])[0]

    # Guidance EBITDA if supplied — converts haircut % into a $ value
    guidance = None
    raw_gde = (qs.get("guidance_ebitda_usd") or [""])[0].strip()
    if raw_gde:
        try:
            guidance = float(raw_gde)
        except ValueError:
            pass

    team = _demo_team()
    report = analyze_team(team, guidance_ebitda_usd=guidance)

    hero_and_haircut = export_json_panel(
        _hero(report, target_name)
        + _bridge_haircut_block(report.bridge_haircut),
        payload=report.to_dict(),
        name="management_scorecard_report",
    )

    # Focus cards: critical red flags first
    critical = [s for s in report.scores if s.is_red_flag]
    other = [s for s in report.scores if not s.is_red_flag]
    focus_cards = "".join(_exec_card(s) for s in critical + other)

    # How-to-read + score-band legend — renders above the card list
    # so first-time readers see the mental model before the numbers.
    howto = (
        f'<div style="background:{P["panel_alt"]};border-left:3px solid '
        f'{P["accent"]};padding:12px 16px;margin-top:16px;'
        f'border-radius:0 3px 3px 0;font-size:12px;color:{P["text_dim"]};'
        f'line-height:1.65;max-width:880px;">'
        f'<strong style="color:{P["text"]};">How to read these cards: </strong>'
        f'Each executive scores 0–100 on four dimensions. Overall score '
        f'is a weighted average with a red-flag override — any dimension '
        f'below 30 caps overall at 40 so partners see structural '
        f'problems. Card color band reflects overall score. Hover each '
        f'dimension tile for the specific definition. Red-flag rows at '
        f'the bottom of each card are the partner-actionable items.'
        f'{_score_band_legend()}'
        f'</div>'
    )
    body = (
        _scoped_styles()
        + '<div class="ms-wrap">'
        + hero_and_haircut
        + howto
        + f'<div class="ms-section-label">'
          f'Executive scorecards · red flags first</div>'
        + focus_cards
        + '</div>'
        + bookmark_hint()
    )
    return chartis_shell(
        body,
        f"Management Scorecard — {target_name}",
        subtitle="Forecast reliability × comp × tenure × prior role",
    )
