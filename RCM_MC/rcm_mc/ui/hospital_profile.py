"""Hospital Profile Page — the 'stock quote' equivalent.

Click any CCN and get a full profile: fundamentals, ratings,
charts, comparables, news. Even for hospitals not in the portfolio.
"""
from __future__ import annotations

import html
from typing import Any, Dict, List, Optional

from .shell_v2 import shell_v2
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

    # Header
    header = (
        f'<div class="cad-card" style="display:flex;justify-content:space-between;align-items:start;">'
        f'<div>'
        f'<div style="display:flex;align-items:center;gap:12px;margin-bottom:8px;">'
        f'<span style="font-family:var(--cad-mono);font-size:13px;'
        f'color:{PALETTE["text_muted"]};background:{PALETTE["bg_tertiary"]};'
        f'padding:2px 8px;border-radius:4px;">CCN {ccn}</span>'
        f'<span class="cad-badge cad-badge-muted">{beds} beds</span>'
        f'<span class="cad-badge cad-badge-muted">{city}, {state}</span>'
        f'</div>'
        f'<h1 style="font-family:var(--cad-serif);font-size:24px;margin:0;">{name}</h1>'
        f'</div>'
        f'<div style="text-align:center;">'
        f'<div style="font-size:36px;font-weight:700;font-family:var(--cad-mono);'
        f'color:{grade_color};">{score_val}</div>'
        f'<div style="font-size:14px;font-weight:600;color:{grade_color};">'
        f'Grade: {grade}</div>'
        f'<div style="font-size:11px;color:{PALETTE["text_muted"]};">SeekingChartis Score</div>'
        f'</div></div>'
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
        f'<h2>Payer Mix</h2>'
        f'<div style="display:flex;gap:4px;height:24px;border-radius:4px;overflow:hidden;margin-bottom:8px;">'
        f'<div style="width:{med_pct*100:.0f}%;background:{PALETTE["brand_accent"]};" '
        f'title="Medicare {med_pct:.0%}"></div>'
        f'<div style="width:{mcd_pct*100:.0f}%;background:{PALETTE["warning"]};" '
        f'title="Medicaid {mcd_pct:.0%}"></div>'
        f'<div style="width:{comm_pct*100:.0f}%;background:{PALETTE["positive"]};" '
        f'title="Commercial {comm_pct:.0%}"></div>'
        f'</div>'
        f'<div style="display:flex;gap:16px;font-size:12px;">'
        f'<span><span style="color:{PALETTE["brand_accent"]};">&#9632;</span> Medicare {med_pct:.0%}</span>'
        f'<span><span style="color:{PALETTE["warning"]};">&#9632;</span> Medicaid {mcd_pct:.0%}</span>'
        f'<span><span style="color:{PALETTE["positive"]};">&#9632;</span> Commercial {comm_pct:.0%}</span>'
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
            f'<h2>Quality Metrics (CMS Care Compare)</h2>'
            f'<div class="cad-kpi-grid">{q_items}</div></div>'
        )

    # Score Breakdown
    components = score.components if hasattr(score, "components") else {}
    breakdown_rows = ""
    for comp, val in components.items():
        max_val = {"market_position": 35, "financial_health": 25,
                   "operational_quality": 20, "competitive_moat": 20}.get(comp, 25)
        pct = val / max_val * 100 if max_val > 0 else 0
        breakdown_rows += (
            f'<tr><td>{html.escape(comp.replace("_", " ").title())}</td>'
            f'<td class="num">{val:.0f} / {max_val}</td>'
            f'<td><div style="background:{PALETTE["bg_tertiary"]};border-radius:4px;height:8px;">'
            f'<div style="width:{pct:.0f}%;background:{PALETTE["brand_accent"]};'
            f'border-radius:4px;height:8px;"></div></div></td></tr>'
        )

    score_card = (
        f'<div class="cad-card">'
        f'<h2>Score Breakdown</h2>'
        f'<table class="cad-table"><thead><tr><th>Component</th>'
        f'<th>Score</th><th>Bar</th></tr></thead>'
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
                f'<tr><td><a href="/hospital/{c_ccn}">{c_name}</a></td>'
                f'<td class="num">{c_beds}</td>'
                f'<td class="num">${c_rev/1e6:,.0f}M</td></tr>'
            )
        comp_html = (
            f'<div class="cad-card">'
            f'<h2>Comparable Hospitals</h2>'
            f'<table class="cad-table"><thead><tr><th>Hospital</th>'
            f'<th>Beds</th><th>NPR</th></tr></thead>'
            f'<tbody>{comp_rows}</tbody></table></div>'
        )

    # Actions — one-click diligence creates a deal from this hospital's HCRIS data
    _btn_primary = 'text-decoration:none;background:var(--cad-accent);color:#fff;font-weight:600;'
    _btn_green = 'text-decoration:none;background:var(--cad-pos);color:#fff;font-weight:600;'
    _btn_orange = 'text-decoration:none;background:#e67e22;color:#fff;font-weight:600;'
    _btn = 'text-decoration:none;'

    actions = (
        f'<div class="cad-card">'
        # Primary workflow — the 4 things an analyst does first
        f'<div style="font-size:10px;color:var(--cad-text3);text-transform:uppercase;'
        f'letter-spacing:0.08em;font-weight:600;margin-bottom:6px;">DILIGENCE WORKFLOW</div>'
        f'<div style="display:flex;gap:8px;flex-wrap:wrap;margin-bottom:14px;">'
        f'<a href="/competitive-intel/{ccn}" class="cad-btn" style="{_btn_primary}">Competitive Intel</a>'
        f'<a href="/ebitda-bridge/{ccn}" class="cad-btn" style="{_btn_green}">EBITDA Bridge</a>'
        f'<a href="/data-room/{ccn}" class="cad-btn" style="{_btn_orange}">Data Room</a>'
        f'<a href="/ic-memo/{ccn}" class="cad-btn" style="{_btn_primary}">Generate IC Memo</a>'
        f'<a href="/scenarios/{ccn}" class="cad-btn" style="{_btn}">Scenarios</a>'
        f'</div>'
        # Secondary analysis
        f'<div style="font-size:10px;color:var(--cad-text3);text-transform:uppercase;'
        f'letter-spacing:0.08em;font-weight:600;margin-bottom:6px;">DEEP ANALYSIS</div>'
        f'<div style="display:flex;gap:6px;flex-wrap:wrap;margin-bottom:14px;">'
        f'<a href="/ml-insights/hospital/{ccn}" class="cad-btn" style="{_btn}font-size:11px;">ML Analysis</a>'
        f'<a href="/hospital/{ccn}/demand" class="cad-btn" style="{_btn}font-size:11px;">Demand</a>'
        f'<a href="/hospital/{ccn}/history" class="cad-btn" style="{_btn}font-size:11px;">3-Year History</a>'
        f'<a href="/portfolio/regression/hospital/{ccn}" class="cad-btn" style="{_btn}font-size:11px;">Stats</a>'
        f'<a href="/bayesian/hospital/{ccn}" class="cad-btn" style="{_btn}font-size:11px;">Bayesian</a>'
        f'</div>'
        # Financial models
        f'<div style="font-size:10px;color:var(--cad-text3);text-transform:uppercase;'
        f'letter-spacing:0.08em;font-weight:600;margin-bottom:6px;">FINANCIAL MODELS</div>'
        f'<div style="display:flex;gap:6px;flex-wrap:wrap;margin-bottom:10px;">'
        f'<a href="/models/dcf/{ccn}" class="cad-btn" style="{_btn}font-size:11px;">DCF</a>'
        f'<a href="/models/lbo/{ccn}" class="cad-btn" style="{_btn}font-size:11px;">LBO</a>'
        f'<a href="/models/financials/{ccn}" class="cad-btn" style="{_btn}font-size:11px;">3-Statement</a>'
        f'<a href="/models/returns/{ccn}" class="cad-btn" style="{_btn}font-size:11px;">Returns</a>'
        f'<a href="/models/market/{ccn}" class="cad-btn" style="{_btn}font-size:11px;">Market</a>'
        f'<a href="/models/denial/{ccn}" class="cad-btn" style="{_btn}font-size:11px;">Denial</a>'
        f'</div>'
        # Start diligence action
        f'<div style="border-top:1px solid var(--cad-border);padding-top:10px;'
        f'display:flex;gap:10px;align-items:center;">'
        f'<form method="POST" action="/hospital/{ccn}/start-diligence" style="display:inline;">'
        f'<button type="submit" class="cad-btn cad-btn-primary" '
        f'style="cursor:pointer;">Start Diligence &rarr;</button></form>'
        f'<form method="POST" action="/pipeline/add" style="display:inline;">'
        f'<input type="hidden" name="ccn" value="{ccn}">'
        f'<input type="hidden" name="name" value="{html.escape(name)}">'
        f'<input type="hidden" name="state" value="{html.escape(state)}">'
        f'<input type="hidden" name="beds" value="{int(beds)}">'
        f'<button type="submit" class="cad-btn" '
        f'style="cursor:pointer;border:none;font-size:11px;">+ Add to Pipeline</button></form>'
        f'<a href="/screen?state={state}" class="cad-btn" '
        f'style="{_btn}font-size:11px;">More in {state}</a>'
        f'<span style="font-size:10px;color:var(--cad-text3);">'
        f'Creates a deal from HCRIS data</span>'
        f'</div></div>'
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
                f'<h2>Team Notes</h2>'
                f'{comment_items}'
                f'<form method="POST" action="/team/comment" '
                f'style="display:flex;gap:8px;margin-top:8px;">'
                f'<input type="hidden" name="entity_type" value="hospital">'
                f'<input type="hidden" name="entity_id" value="{ccn}">'
                f'<input type="hidden" name="redirect" value="/hospital/{ccn}">'
                f'<input type="text" name="author" placeholder="Initials" '
                f'style="width:60px;padding:6px 8px;border:1px solid var(--cad-border);'
                f'border-radius:4px;background:var(--cad-bg3);color:var(--cad-text);'
                f'font-size:11px;box-sizing:border-box;">'
                f'<input type="text" name="body" placeholder="Add a note..." required '
                f'style="flex:1;padding:6px 8px;border:1px solid var(--cad-border);'
                f'border-radius:4px;background:var(--cad-bg3);color:var(--cad-text);'
                f'font-size:11px;box-sizing:border-box;">'
                f'<button type="submit" class="cad-btn" '
                f'style="font-size:11px;cursor:pointer;border:none;">Post</button>'
                f'</form></div>'
            )
        except Exception:
            pass

    body = f'{header}{thesis_html}{system_badge}{fundamentals}{payer_mix}{quality_section}{score_card}{comp_html}{comments_html}{actions}'

    return shell_v2(
        body, name,
        active_nav="/market-data/map",
        subtitle=f"CCN {ccn} — {city}, {state} — {beds} beds",
    )
