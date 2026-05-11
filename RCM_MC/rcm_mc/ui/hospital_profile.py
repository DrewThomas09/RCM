"""Hospital Profile Page — the 'stock quote' equivalent.

Click any CCN and get a full profile: fundamentals, ratings,
charts, comparables, news. Even for hospitals not in the portfolio.
"""
from __future__ import annotations

import html
from typing import Any, Dict, List, Optional

from ._chartis_kit import (
    chartis_shell, ck_kpi_block, ck_next_section, ck_panel,
    ck_section_intro, ck_signal_badge,
)
from ._provenance_tooltip import provenance_tooltip
from .brand import PALETTE
from .provenance import build_provenance_graph


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

    # Phase 4C: build a ProvenanceGraph for "explain this number"
    # tooltips. operating_margin and revenue_per_bed are computed
    # locally above so they aren't in the raw hospital dict —
    # splice them in alongside the raw HCRIS values before
    # building the graph. ml_predictions is empty here (this
    # page reads HCRIS-derived hospital records directly, not
    # packet-driven predictions).
    _rev_per_bed = npr / beds if beds > 0 else 0
    _prov_profile = {
        **hospital,
        "operating_margin": margin,
        "revenue_per_bed": _rev_per_bed,
    }
    prov_graph = build_provenance_graph(
        ccn=str(hospital.get("ccn", "")),
        hcris_profile=_prov_profile,
        ml_predictions={},
        db_path=db_path,
    )

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

    hp_styles = f"""
<style>
.cad-deal-ident{{font-family:var(--cad-mono);font-size:10.5px;
letter-spacing:0.12em;color:{PALETTE["text_muted"]};text-transform:uppercase;}}
.cad-deal-ident .ident-key{{color:{PALETTE["text_muted"]};}}
.cad-deal-ident .ident-val{{color:{PALETTE["text_primary"]};font-weight:600;}}
.cad-deal-ident .ident-sep{{color:{PALETTE["border_light"]};padding:0 8px;}}
.hp-grade-block{{display:flex;flex-direction:column;align-items:center;
padding:12px 22px;border:1px solid {PALETTE["border_light"]};
background:#03050a;min-width:120px;}}
.hp-grade-val{{font-family:var(--cad-mono);font-size:32px;font-weight:700;
line-height:1;letter-spacing:-0.02em;}}
.hp-grade-label{{font-family:var(--cad-mono);font-size:10.5px;letter-spacing:0.18em;
text-transform:uppercase;margin-top:4px;}}
.hp-grade-sub{{font-family:var(--cad-mono);font-size:9px;letter-spacing:0.12em;
text-transform:uppercase;color:{PALETTE["text_muted"]};margin-top:3px;}}
.hp-header-row{{display:flex;justify-content:space-between;align-items:center;gap:20px;}}
.hp-payer-bar{{display:flex;gap:0;height:14px;overflow:hidden;
margin-bottom:8px;border:1px solid {PALETTE["border"]};}}
.hp-payer-legend{{display:flex;gap:20px;font-family:var(--cad-mono);
font-size:10.5px;letter-spacing:0.06em;text-transform:uppercase;}}
.hp-comment-row{{padding:6px 0;border-bottom:1px solid var(--cad-border);font-size:12px;}}
.hp-action-group{{display:flex;align-items:center;gap:10px;margin:10px 0 6px;}}
.hp-action-btns{{display:flex;gap:6px;flex-wrap:wrap;}}
.hp-action-bottom{{border-top:1px solid {PALETTE["border"]};padding-top:12px;
margin-top:14px;display:flex;gap:8px;align-items:center;flex-wrap:wrap;}}
.hp-comment-form{{margin-top:12px;}}
.hp-comment-author{{width:72px;}}
.hp-comment-body{{flex:1;min-width:200px;}}
</style>
"""
    header = ck_section_intro(
        eyebrow=f"HOSPITAL PROFILE · CCN {ccn}",
        headline=f"{name} — {city}, {state}.",
        italic_word=name,
        body=(
            f"{beds:,} licensed beds · ${npr/1e6:,.1f}M net patient "
            f"revenue · {margin:.1%} operating margin · "
            f"SeekingChartis score {score_val}/100 (grade {grade})."
        ),
    ) + ck_panel(
        '<div class="hp-header-row">'
        f'<div class="cad-deal-ident">{ident}</div>'
        '<div class="hp-grade-block">'
        f'<div class="hp-grade-val" style="color:{grade_color};">{score_val}</div>'
        f'<div class="hp-grade-label" style="color:{grade_color};">{grade}</div>'
        '<div class="hp-grade-sub">SeekingChartis Score</div>'
        '</div></div>',
        title="Identity",
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
        system_badge = ck_panel(
            '<p class="ck-section-body">'
            f'<strong>{system}</strong> {ck_signal_badge("Health System", tone="neutral")}'
            '</p>',
            title="System Affiliation",
        )

    # Fundamentals — KPI strip
    rev_per_bed = npr / beds if beds > 0 else 0
    fundamentals = (
        '<div class="ck-kpi-strip">'
        + ck_kpi_block(
            "Net Patient Revenue",
            provenance_tooltip(label="Net Patient Revenue", value=f"${npr/1e6:,.1f}M", graph=prov_graph, metric_key="net_patient_revenue"),
            help={
                "definition": (
                    "Net Patient Revenue — billed services minus "
                    "contractual allowances, bad debt, and charity "
                    "care. The cash-realisable top line."
                ),
                "citation": "HFMA Glossary",
            },
        )
        + ck_kpi_block(
            "Operating Margin",
            provenance_tooltip(label="Operating Margin", value=f"{margin:.1%}", graph=prov_graph, metric_key="operating_margin"),
            help={
                "definition": (
                    "Operating income divided by total revenue. "
                    "Community-hospital margins typically run 2-4%; "
                    "regional hospitals 4-7%; academic medical "
                    "centers can run negative on operations and "
                    "make it back on research / grants."
                ),
            },
        )
        + ck_kpi_block(
            "Net Income",
            provenance_tooltip(label="Net Income", value=f"${ni/1e6:,.1f}M", graph=prov_graph, metric_key="net_income"),
            help={
                "definition": (
                    "Bottom-line earnings after operating income, "
                    "interest, taxes, and non-operating items. "
                    "Differs from EBITDA — which strips out the "
                    "below-the-line items PE partners model "
                    "separately in the bridge."
                ),
            },
        )
        + ck_kpi_block(
            "Licensed Beds",
            provenance_tooltip(label="Licensed Beds", value=f"{beds}", graph=prov_graph, metric_key="beds"),
        )
        + ck_kpi_block(
            "Revenue per Bed",
            provenance_tooltip(label="Revenue per Bed", value=f"${rev_per_bed/1e3:,.0f}K", graph=prov_graph, metric_key="revenue_per_bed"),
            help={
                "definition": (
                    "Productivity proxy — NPR per licensed bed. "
                    "Compares throughput and case mix across "
                    "hospitals of different sizes. Community "
                    "hospitals run $1.2-1.8M/bed; specialty "
                    "centers can run $3-5M/bed."
                ),
            },
        )
        + ck_kpi_block(
            "Operating Expenses",
            provenance_tooltip(label="Operating Expenses", value=f"${opex/1e6:,.1f}M", graph=prov_graph, metric_key="operating_expenses"),
        )
        + '</div>'
    )

    # Payer Mix
    payer_mix = ck_panel(
        '<div class="hp-payer-bar">'
        f'<div style="width:{med_pct*100:.0f}%;background:{PALETTE["brand_accent"]};"></div>'
        f'<div style="width:{mcd_pct*100:.0f}%;background:{PALETTE["warning"]};"></div>'
        f'<div style="width:{comm_pct*100:.0f}%;background:{PALETTE["positive"]};"></div>'
        '</div>'
        '<div class="hp-payer-legend">'
        f'<span style="color:{PALETTE["brand_accent"]};">■ MEDICARE · {med_pct:.0%}</span>'
        f'<span style="color:{PALETTE["warning"]};">■ MEDICAID · {mcd_pct:.0%}</span>'
        f'<span style="color:{PALETTE["positive"]};">■ COMMERCIAL · {comm_pct:.0%}</span>'
        '</div>',
        title="Payer Mix",
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
        quality_section = ck_panel(
            '<p class="ck-eyebrow">Source · CMS Care Compare</p>'
            f'<div class="ck-kpi-strip">{q_items}</div>',
            title="Quality Metrics",
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

    score_card = ck_panel(
        f'<p class="ck-eyebrow">Composite · {score_val}/100</p>'
        '<table class="cad-table"><thead><tr><th>Component</th>'
        '<th>Score</th><th>Max</th><th>%</th><th>Distribution</th></tr></thead>'
        f'<tbody>{breakdown_rows}</tbody></table>',
        title="Score Breakdown",
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
        comp_html = ck_panel(
            '<table class="cad-table crosshair"><thead><tr>'
            '<th>CCN</th><th>Hospital</th><th>Beds</th><th>NPR</th></tr></thead>'
            f'<tbody>{comp_rows}</tbody></table>',
            title="Comparable Hospitals",
        )

    # Actions — diligence workflow, deep analysis, financial models
    def _group(code: str, label: str, links):
        items = "".join(
            f'<a href="{href}" class="cad-btn">{html.escape(txt)}</a> '
            for href, txt in links
        )
        return (
            '<div class="hp-action-group">'
            f'<span class="cad-section-code">{code}</span>'
            f'<span class="cad-label">{label}</span></div>'
            f'<div class="hp-action-btns">{items}</div>'
        )

    actions = ck_panel(
        _group("WF", "Diligence Workflow", [
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
        + '<div class="hp-action-bottom">'
        + f'<form method="POST" action="/hospital/{ccn}/start-diligence" style="margin:0;">'
        + '<button type="submit" class="cad-btn cad-btn-primary">'
          'Start Diligence &rarr;</button></form>'
        + '<form method="POST" action="/pipeline/add" style="margin:0;">'
        + f'<input type="hidden" name="ccn" value="{ccn}">'
        + f'<input type="hidden" name="name" value="{html.escape(name)}">'
        + f'<input type="hidden" name="state" value="{html.escape(state)}">'
        + f'<input type="hidden" name="beds" value="{int(beds)}">'
        + '<button type="submit" class="cad-btn">+ PIPELINE</button></form>'
        + f'<a href="/screen?state={state}" class="cad-btn">MORE IN {state}</a>'
        + '</div>',
        title="Actions",
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
                    '<div class="hp-comment-row">'
                    f'<strong>{html.escape(c.author[:10])}</strong> '
                    f'<span class="ck-eyebrow">{c.created_at[:16]}</span>'
                    f'<div>{html.escape(c.body[:200])}</div>'
                    '</div>'
                )

            comments_html = ck_panel(
                f'<p class="ck-eyebrow">{len(comments)} entries</p>'
                f'{comment_items}'
                f'<form method="POST" action="/team/comment" class="cad-form-row hp-comment-form">'
                f'<input type="hidden" name="entity_type" value="hospital">'
                f'<input type="hidden" name="entity_id" value="{ccn}">'
                f'<input type="hidden" name="redirect" value="/hospital/{ccn}">'
                f'<input class="cad-input hp-comment-author" type="text" name="author" placeholder="INITS">'
                f'<input class="cad-input hp-comment-body" type="text" name="body" placeholder="Add a note..." required>'
                f'<button type="submit" class="cad-btn cad-btn-primary">Post &rarr;</button>'
                f'</form>',
                title="Team Notes",
            )
        except Exception:
            pass

    next_up = ck_next_section(
        "Open the hospital's history",
        f"/hospital/{ccn}/history",
        eyebrow="Continue —",
        italic_word="history",
    )
    body = (
        f'{hp_styles}{header}{thesis_html}{system_badge}{fundamentals}'
        f'{payer_mix}{quality_section}{score_card}{comp_html}'
        f'{comments_html}{actions}{next_up}'
    )

    return chartis_shell(
        body, name,
        active_nav="/market-data/map",
        subtitle=f"CCN {ccn} — {city}, {state} — {beds} beds",
    )
