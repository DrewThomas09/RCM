"""Hospital Profile Page — the 'stock quote' equivalent.

Click any CCN and get a full profile: fundamentals, ratings,
charts, comparables, news. Even for hospitals not in the portfolio.
"""
from __future__ import annotations

import html
from typing import Any, Dict, List, Optional

from ._chartis_kit import chartis_shell
from .brand import PALETTE


def render_hospital_profile(
    hospital: Dict[str, Any],
    score: Any,
    comparables: List[Dict[str, Any]] = None,
    hcris_df: Any = None,
    db_path: Optional[str] = None,
) -> str:
    """Render a full hospital profile page."""
    ccn = html.escape(str(hospital.get("ccn", "")))
    name = html.escape(str(hospital.get("name", "Unknown Hospital")))
    city = html.escape(str(hospital.get("city", "")))
    state = html.escape(str(hospital.get("state", "")))
    beds = int(hospital.get("beds", 0))
    npr = float(hospital.get("net_patient_revenue", 0))
    opex = float(hospital.get("operating_expenses", 0))
    ni = float(hospital.get("net_income", 0))
    margin = (npr - opex) / npr if npr > 1e5 and opex > 0 else 0
    margin = max(-1.0, min(1.0, margin))
    med_pct = float(hospital.get("medicare_day_pct", 0))
    mcd_pct = float(hospital.get("medicaid_day_pct", 0))
    comm_pct = max(0, 1.0 - med_pct - mcd_pct)

    grade = score.grade if hasattr(score, "grade") else "—"
    score_val = score.score if hasattr(score, "score") else 0
    grade_color = {
        "A+": "#10b981", "A": "#10b981", "A-": "#10b981",
        "B+": "#3b82f6", "B": "#3b82f6", "B-": "#3b82f6",
        "C+": "#f59e0b", "C": "#f59e0b", "C-": "#f59e0b",
    }.get(grade, "#ef4444")

    # Identity strip (Bloomberg security header)
    ident = (
        f'<span class="ident-key">CCN</span> <span class="ident-val">{ccn}</span>'
        f'<span class="ident-sep">|</span>'
        f'<span class="ident-key">LOC</span> <span class="ident-val">{city}, {state}</span>'
        f'<span class="ident-sep">|</span>'
        f'<span class="ident-key">BEDS</span> <span class="ident-val">{beds:,}</span>'
        f'<span class="ident-sep">|</span>'
        f'<span class="ident-key">NPR</span> <span class="ident-val">${npr/1e6:,.1f}M</span>'
        f'<span class="ident-sep">|</span>'
        f'<span class="ident-key">MARGIN</span> '
        f'<span class="ident-val" style="color:{grade_color};">{margin:.1%}</span>'
    )

    header = (
        f'<style>'
        f'.cad-deal-ident{{font-family:var(--cad-mono);font-size:10.5px;'
        f'letter-spacing:0.12em;color:{PALETTE["text_muted"]};text-transform:uppercase;}}'
        f'.cad-deal-ident .ident-key{{color:{PALETTE["text_muted"]};}}'
        f'.cad-deal-ident .ident-val{{color:{PALETTE["text_primary"]};font-weight:600;}}'
        f'.cad-deal-ident .ident-sep{{color:{PALETTE["border_light"]};padding:0 8px;}}'
        f'.cad-grade-block{{display:flex;flex-direction:column;align-items:center;'
        f'padding:12px 22px;border:1px solid {PALETTE["border_light"]};'
        f'background:#03050a;min-width:120px;}}'
        f'.cad-grade-val{{font-family:var(--cad-mono);font-size:32px;font-weight:700;'
        f'line-height:1;letter-spacing:-0.02em;}}'
        f'.cad-grade-label{{font-family:var(--cad-mono);font-size:10.5px;letter-spacing:0.18em;'
        f'text-transform:uppercase;margin-top:4px;}}'
        f'.cad-grade-sub{{font-family:var(--cad-mono);font-size:9px;letter-spacing:0.12em;'
        f'text-transform:uppercase;color:{PALETTE["text_muted"]};margin-top:3px;}}'
        f'</style>'
        f'<div class="cad-card" style="padding:14px 18px;">'
        f'<div style="display:flex;justify-content:space-between;align-items:center;gap:20px;">'
        f'<div style="flex:1;min-width:0;">'
        f'<div style="display:flex;align-items:center;gap:10px;margin-bottom:8px;">'
        f'<span class="cad-section-code">HOSP</span>'
        f'<h1 style="margin:0;font-size:17px;font-weight:700;letter-spacing:0.06em;'
        f'text-transform:uppercase;color:{PALETTE["text_primary"]};">{name}</h1>'
        f'</div>'
        f'<div class="cad-deal-ident">{ident}</div>'
        f'</div>'
        f'<div class="cad-grade-block">'
        f'<div class="cad-grade-val" style="color:{grade_color};">{score_val}</div>'
        f'<div class="cad-grade-label" style="color:{grade_color};">{grade}</div>'
        f'<div class="cad-grade-sub">SeekingChartis Score</div>'
        f'</div></div></div>'
    )

    # Additional metrics from HCRIS
    medicare_days = float(hospital.get("total_medicare_days", hospital.get("medicare_days", 0)))
    medicaid_days = float(hospital.get("total_medicaid_days", hospital.get("medicaid_days", 0)))
    total_days = float(hospital.get("total_patient_days", medicare_days + medicaid_days + 1))
    occupancy = float(hospital.get("occupancy_rate", 0))
    case_mix = float(hospital.get("case_mix_index", hospital.get("cmi", 0)))
    system = html.escape(str(hospital.get("system_name", hospital.get("system_affiliation", ""))))

    # System affiliation
    system_badge = ""
    if system and system != "None" and system != "":
        system_badge = (
            f'<div class="cad-card" style="padding:12px 16px;">'
            f'<div style="display:flex;justify-content:space-between;align-items:center;">'
            f'<div>'
            f'<div style="font-size:11px;color:{PALETTE["text_muted"]};text-transform:uppercase;">System Affiliation</div>'
            f'<div style="font-weight:600;">{system}</div></div>'
            f'<span class="cad-badge cad-badge-blue">Health System</span></div></div>'
        )

    # Fundamentals — two rows of KPIs
    rev_per_bed = npr / beds if beds > 0 else 0
    fundamentals = (
        f'<div class="cad-kpi-grid">'
        f'<div class="cad-kpi"><div class="cad-kpi-value">${npr/1e6:,.1f}M</div>'
        f'<div class="cad-kpi-label">Net Patient Revenue</div></div>'
        f'<div class="cad-kpi"><div class="cad-kpi-value">{margin:.1%}</div>'
        f'<div class="cad-kpi-label">Operating Margin</div></div>'
        f'<div class="cad-kpi"><div class="cad-kpi-value">${ni/1e6:,.1f}M</div>'
        f'<div class="cad-kpi-label">Net Income</div></div>'
        f'<div class="cad-kpi"><div class="cad-kpi-value">{beds}</div>'
        f'<div class="cad-kpi-label">Licensed Beds</div></div>'
        f'<div class="cad-kpi"><div class="cad-kpi-value">${rev_per_bed/1e3:,.0f}K</div>'
        f'<div class="cad-kpi-label">Revenue per Bed</div></div>'
        f'<div class="cad-kpi"><div class="cad-kpi-value">${opex/1e6:,.1f}M</div>'
        f'<div class="cad-kpi-label">Operating Expenses</div></div>'
        f'</div>'
    )

    # Payer Mix
    payer_mix = (
        f'<div class="cad-card">'
        f'<div style="display:flex;align-items:center;gap:10px;margin-bottom:10px;">'
        f'<h2 style="margin:0;">Payer Mix</h2>'
        f'<span class="cad-section-code">PYR</span></div>'
        f'<div style="display:flex;gap:0;height:14px;overflow:hidden;margin-bottom:8px;'
        f'border:1px solid {PALETTE["border"]};">'
        f'<div style="width:{med_pct*100:.0f}%;background:{PALETTE["brand_accent"]};" '
        f'title="Medicare {med_pct:.0%}"></div>'
        f'<div style="width:{mcd_pct*100:.0f}%;background:{PALETTE["warning"]};" '
        f'title="Medicaid {mcd_pct:.0%}"></div>'
        f'<div style="width:{comm_pct*100:.0f}%;background:{PALETTE["positive"]};" '
        f'title="Commercial {comm_pct:.0%}"></div>'
        f'</div>'
        f'<div style="display:flex;gap:20px;font-family:var(--cad-mono);font-size:10.5px;'
        f'letter-spacing:0.06em;text-transform:uppercase;">'
        f'<span style="color:{PALETTE["brand_accent"]};">&#9632; MEDICARE · {med_pct:.0%}</span>'
        f'<span style="color:{PALETTE["warning"]};">&#9632; MEDICAID · {mcd_pct:.0%}</span>'
        f'<span style="color:{PALETTE["positive"]};">&#9632; COMMERCIAL · {comm_pct:.0%}</span>'
        f'</div></div>'
    )

    # Quality metrics (from CMS Care Compare when available)
    star = hospital.get("star_rating")
    readmit = hospital.get("readmission_rate")
    mortality = hospital.get("mortality_rate")
    hcahps = hospital.get("patient_experience_rating")
    quality_section = ""
    if any(v is not None for v in [star, readmit, mortality, hcahps]):
        q_items = ""
        if star is not None:
            stars = "&#9733;" * int(float(star)) + "&#9734;" * (5 - int(float(star)))
            q_items += (
                f'<div class="cad-kpi"><div class="cad-kpi-value" style="color:{PALETTE["warning"]};">'
                f'{stars}</div><div class="cad-kpi-label">CMS Star Rating ({float(star):.0f}/5)</div></div>'
            )
        if readmit is not None:
            q_items += (
                f'<div class="cad-kpi"><div class="cad-kpi-value">{float(readmit):.1f}%</div>'
                f'<div class="cad-kpi-label">Readmission Rate</div></div>'
            )
        if mortality is not None:
            q_items += (
                f'<div class="cad-kpi"><div class="cad-kpi-value">{float(mortality):.1f}%</div>'
                f'<div class="cad-kpi-label">Mortality Rate</div></div>'
            )
        if hcahps is not None:
            q_items += (
                f'<div class="cad-kpi"><div class="cad-kpi-value">{float(hcahps):.1f}/5</div>'
                f'<div class="cad-kpi-label">Patient Experience</div></div>'
            )
        quality_section = (
            f'<div class="cad-card">'
            f'<div style="display:flex;align-items:center;gap:10px;margin-bottom:10px;">'
            f'<h2 style="margin:0;">Quality Metrics</h2>'
            f'<span class="cad-section-code">QLT</span>'
            f'<span style="font-family:var(--cad-mono);font-size:9.5px;'
            f'letter-spacing:0.1em;color:{PALETTE["text_muted"]};text-transform:uppercase;">'
            f'Source · CMS Care Compare</span></div>'
            f'<div class="cad-kpi-grid">{q_items}</div></div>'
        )

    # Score Breakdown
    components = score.components if hasattr(score, "components") else {}
    breakdown_rows = ""
    for comp, val in components.items():
        max_val = {"market_position": 35, "financial_health": 25,
                   "operational_quality": 20, "competitive_moat": 20}.get(comp, 25)
        pct = val / max_val * 100 if max_val > 0 else 0
        # 5-tier heatmap for percentage
        if pct > 80: heat = "cad-heat-1"
        elif pct > 60: heat = "cad-heat-2"
        elif pct > 40: heat = "cad-heat-3"
        elif pct > 20: heat = "cad-heat-4"
        else: heat = "cad-heat-5"
        bar_fill = {
            "cad-heat-1": PALETTE["positive"],
            "cad-heat-2": PALETTE["positive"],
            "cad-heat-3": PALETTE["brand_accent"],
            "cad-heat-4": PALETTE["warning"],
            "cad-heat-5": PALETTE["negative"],
        }[heat]
        breakdown_rows += (
            f'<tr><td style="font-weight:600;">{html.escape(comp.replace("_", " ").title())}</td>'
            f'<td class="num {heat}" style="font-weight:600;">{val:.0f}</td>'
            f'<td class="num">{max_val}</td>'
            f'<td class="num">{pct:.0f}%</td>'
            f'<td style="width:100%;"><div class="cad-bar" style="width:100%;">'
            f'<div class="cad-bar-fill" style="width:{pct:.0f}%;background:{bar_fill};"></div>'
            f'</div></td></tr>'
        )

    score_card = (
        f'<div class="cad-card">'
        f'<div style="display:flex;align-items:center;gap:10px;margin-bottom:10px;">'
        f'<h2 style="margin:0;">Score Breakdown</h2>'
        f'<span class="cad-section-code">SC</span>'
        f'<span style="font-family:var(--cad-mono);font-size:10px;letter-spacing:0.06em;'
        f'color:{PALETTE["text_muted"]};text-transform:uppercase;margin-left:auto;">'
        f'Composite · {score_val}/100</span></div>'
        f'<table class="cad-table"><thead><tr><th>Component</th>'
        f'<th>Score</th><th>Max</th><th>%</th><th>Distribution</th></tr></thead>'
        f'<tbody>{breakdown_rows}</tbody></table></div>'
    )

    # Comparables
    comp_html = ""
    if comparables:
        comp_rows = ""
        for c in comparables[:5]:
            c_ccn = html.escape(str(c.get("ccn", "")))
            c_name = html.escape(str(c.get("name", ""))[:40])
            c_beds = int(c.get("beds", 0))
            c_rev = float(c.get("revenue", 0))
            comp_rows += (
                f'<tr>'
                f'<td><a href="/hospital/{c_ccn}" class="cad-ticker-id" '
                f'style="text-decoration:none;">{c_ccn}</a></td>'
                f'<td><a href="/hospital/{c_ccn}" '
                f'style="color:{PALETTE["text_primary"]};text-decoration:none;font-weight:600;">'
                f'{c_name}</a></td>'
                f'<td class="num">{c_beds:,}</td>'
                f'<td class="num">${c_rev/1e6:,.0f}M</td></tr>'
            )
        comp_html = (
            f'<div class="cad-card cad-table-sticky">'
            f'<div style="display:flex;align-items:center;gap:10px;margin-bottom:10px;">'
            f'<h2 style="margin:0;">Comparable Hospitals</h2>'
            f'<span class="cad-section-code">CMP</span></div>'
            f'<table class="cad-table crosshair"><thead><tr>'
            f'<th>CCN</th><th>Hospital</th><th>Beds</th><th>NPR</th></tr></thead>'
            f'<tbody>{comp_rows}</tbody></table></div>'
        )

    # Actions — diligence workflow, deep analysis, financial models
    def _group(code: str, label: str, links):
        items = "".join(
            f'<a href="{href}" class="cad-btn" style="text-decoration:none;">{html.escape(txt)}</a>'
            for href, txt in links
        )
        return (
            f'<div style="display:flex;align-items:center;gap:10px;margin:10px 0 6px;">'
            f'<span class="cad-section-code">{code}</span>'
            f'<span class="cad-label">{label}</span></div>'
            f'<div style="display:flex;gap:6px;flex-wrap:wrap;">{items}</div>'
        )

    actions = (
        f'<div class="cad-card">'
        f'<div style="display:flex;align-items:center;gap:10px;">'
        f'<h2 style="margin:0;">Actions</h2>'
        f'<span class="cad-section-code">ACT</span></div>'
        + _group("WF", "Diligence Workflow", [
            (f"/competitive-intel/{ccn}", "Competitive Intel"),
            (f"/ebitda-bridge/{ccn}", "EBITDA Bridge"),
            (f"/data-room/{ccn}", "Data Room"),
            (f"/ic-memo/{ccn}", "IC Memo"),
            (f"/scenarios/{ccn}", "Scenarios"),
        ])
        + _group("AI", "Deep Analysis", [
            (f"/ml-insights/hospital/{ccn}", "ML Analysis"),
            (f"/hospital/{ccn}/demand", "Demand"),
            (f"/hospital/{ccn}/history", "3-Year History"),
            (f"/portfolio/regression/hospital/{ccn}", "Stats"),
            (f"/bayesian/hospital/{ccn}", "Bayesian"),
        ])
        + _group("FIN", "Financial Models", [
            (f"/models/dcf/{ccn}", "DCF"),
            (f"/models/lbo/{ccn}", "LBO"),
            (f"/models/financials/{ccn}", "3-Statement"),
            (f"/models/returns/{ccn}", "Returns"),
            (f"/models/market/{ccn}", "Market"),
            (f"/models/denial/{ccn}", "Denial"),
        ])
        + f'<div style="border-top:1px solid {PALETTE["border"]};padding-top:12px;margin-top:14px;'
          f'display:flex;gap:8px;align-items:center;flex-wrap:wrap;">'
        + f'<form method="POST" action="/hospital/{ccn}/start-diligence" style="margin:0;">'
        + f'<button type="submit" class="cad-btn cad-btn-primary" style="cursor:pointer;">'
          f'Start Diligence &rarr;</button></form>'
        + f'<form method="POST" action="/pipeline/add" style="margin:0;">'
        + f'<input type="hidden" name="ccn" value="{ccn}">'
        + f'<input type="hidden" name="name" value="{html.escape(name)}">'
        + f'<input type="hidden" name="state" value="{html.escape(state)}">'
        + f'<input type="hidden" name="beds" value="{int(beds)}">'
        + f'<button type="submit" class="cad-btn" style="cursor:pointer;">+ PIPELINE</button></form>'
        + f'<a href="/screen?state={state}" class="cad-btn" style="text-decoration:none;">'
          f'MORE IN {state}</a>'
        + f'<span style="font-family:var(--cad-mono);font-size:9.5px;'
          f'letter-spacing:0.1em;color:{PALETTE["text_muted"]};text-transform:uppercase;'
          f'margin-left:auto;">Start Diligence · creates a deal from HCRIS</span>'
        + f'</div></div>'
    )

    # Investment thesis card (synthesizes all ML models)
    thesis_html = ""
    if hcris_df is not None:
        try:
            from .thesis_card import render_thesis_card
            thesis_html = render_thesis_card(ccn, hcris_df, db_path=db_path)
        except Exception:
            pass

    # Team comments section
    comments_html = ""
    if db_path:
        try:
            import sqlite3 as _sql_cm
            from ..data.team import get_comments, _ensure_tables as _team_ensure
            _con = _sql_cm.connect(db_path)
            _team_ensure(_con)
            comments = get_comments(_con, "hospital", ccn, limit=5)
            _con.close()

            comment_items = ""
            for c in comments:
                comment_items += (
                    f'<div style="padding:6px 0;border-bottom:1px solid var(--cad-border);font-size:12px;">'
                    f'<span style="font-weight:600;color:var(--cad-text);">{html.escape(c.author[:10])}</span>'
                    f'<span style="color:var(--cad-text3);font-size:10px;margin-left:6px;">'
                    f'{c.created_at[:16]}</span>'
                    f'<div style="color:var(--cad-text2);margin-top:2px;">{html.escape(c.body[:200])}</div>'
                    f'</div>'
                )

            comments_html = (
                f'<div class="cad-card">'
                f'<div style="display:flex;align-items:center;gap:10px;margin-bottom:10px;">'
                f'<h2 style="margin:0;">Team Notes</h2>'
                f'<span class="cad-section-code">NOTE</span>'
                f'<span style="font-family:var(--cad-mono);font-size:9.5px;'
                f'letter-spacing:0.1em;color:var(--cad-text3);text-transform:uppercase;">'
                f'{len(comments)} entries</span></div>'
                f'{comment_items}'
                f'<form method="POST" action="/team/comment" '
                f'class="cad-form-row" style="margin-top:12px;">'
                f'<input type="hidden" name="entity_type" value="hospital">'
                f'<input type="hidden" name="entity_id" value="{ccn}">'
                f'<input type="hidden" name="redirect" value="/hospital/{ccn}">'
                f'<input class="cad-input" type="text" name="author" placeholder="INITS" '
                f'style="width:72px;">'
                f'<input class="cad-input" type="text" name="body" placeholder="Add a note..." '
                f'required style="flex:1;min-width:200px;">'
                f'<button type="submit" class="cad-btn cad-btn-primary" '
                f'style="cursor:pointer;">Post &rarr;</button>'
                f'</form></div>'
            )
        except Exception:
            pass

    body = f'{header}{thesis_html}{system_badge}{fundamentals}{payer_mix}{quality_section}{score_card}{comp_html}{comments_html}{actions}'

    return chartis_shell(
        body, name,
        active_nav="/market-data/map",
        subtitle=f"CCN {ccn} — {city}, {state} — {beds} beds",
    )
