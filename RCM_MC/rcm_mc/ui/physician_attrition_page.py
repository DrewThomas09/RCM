"""Physician Attrition page at /diligence/physician-attrition.

Takes a roster of providers (from the shared demo fixture, query
params, or a future Deal Profile writeback) and renders:

    1. Hero — total EBITDA-at-risk + band counts + partner alert
       banner when CRITICAL providers concentrate revenue
    2. Flight-risk roster — sortable + CSV-exportable table of
       every provider with probability, band, collections at risk,
       and top drivers
    3. High/critical detail cards — per-provider card showing
       drivers, recommendation, and suggested retention bond
    4. Bridge lever card — EBITDA-at-risk hand-off to Deal MC /
       EBITDA bridge

Interpretability-first: every number is labelled, unit-explicit,
peer-banded, and has a plain-English "What this shows" callout.
"""
from __future__ import annotations

import html
from typing import Any, Dict, List, Optional

from ..diligence.physician_attrition import (
    AttritionReport, FlightRiskBand, ProviderAttritionScore,
    analyze_roster,
)
from ..diligence.physician_comp.comp_ingester import Provider
from ._chartis_kit import (
    P, chartis_shell, ck_kpi_block, ck_page_title, ck_panel,
    ck_section_header, ck_section_intro, ck_signal_badge,
)
from .power_ui import (
    bookmark_hint, export_json_panel, provenance, sortable_table,
)


# ────────────────────────────────────────────────────────────────────
# Scoped styles
# ────────────────────────────────────────────────────────────────────

def _scoped_styles() -> str:
    css = """
.pa-wrap{{font-family:"Helvetica Neue",Arial,sans-serif;}}
.pa-eyebrow{{font-size:11px;letter-spacing:1.6px;text-transform:uppercase;
color:{tf};font-weight:600;}}
.pa-h1{{font-size:26px;color:{tx};font-weight:600;line-height:1.15;
margin:4px 0 0 0;letter-spacing:-.2px;}}
.pa-callout{{background:{pa};padding:12px 16px;
border-left:3px solid {ac};border-radius:0 3px 3px 0;
font-size:12px;color:{td};line-height:1.65;max-width:880px;margin-top:12px;}}
.pa-callout.alert{{border-left-color:{ne};color:{ne};
font-weight:600;font-size:13px;}}
.pa-callout.warn{{border-left-color:{wn};color:{wn};
font-weight:600;font-size:13px;}}
.pa-callout.good{{border-left-color:{po};color:{po};
font-weight:600;font-size:13px;}}
.pa-section-label{{font-size:10px;letter-spacing:1.6px;text-transform:uppercase;
font-weight:700;color:{tf};margin:22px 0 10px 0;}}
.pa-kpi-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));
gap:14px;margin-top:18px;}}
.pa-kpi{{background:{pn};border:1px solid {bd};border-radius:4px;
padding:14px 16px;}}
.pa-kpi__label{{font-size:9px;letter-spacing:1.4px;text-transform:uppercase;
color:{tf};margin-bottom:6px;font-weight:600;}}
.pa-kpi__val{{font-size:26px;line-height:1;font-family:"JetBrains Mono",monospace;
font-variant-numeric:tabular-nums;font-weight:700;}}
.pa-kpi__band{{font-size:10px;margin-top:4px;font-weight:600;}}
.pa-card{{background:{pn};border:1px solid {bd};border-radius:4px;
margin-bottom:14px;overflow:hidden;
transition:transform 140ms ease,border-color 140ms ease,box-shadow 140ms ease;}}
.pa-card:hover{{transform:translateY(-1px);border-color:{tf};
box-shadow:0 8px 20px rgba(0,0,0,0.35);}}
.pa-card__band{{height:3px;}}
.pa-card__body{{padding:16px 20px;}}
.pa-card__head{{display:flex;justify-content:space-between;
align-items:flex-start;gap:18px;flex-wrap:wrap;}}
.pa-card__meta{{min-width:280px;}}
.pa-card__title{{font-size:17px;color:{tx};font-weight:600;
letter-spacing:-.15px;}}
.pa-card__top{{font-size:10px;letter-spacing:1.3px;text-transform:uppercase;
color:{tf};margin-bottom:4px;}}
.pa-card__sim{{text-align:right;min-width:140px;}}
.pa-card__sim-val{{font-size:32px;line-height:1;
font-family:"JetBrains Mono",monospace;font-weight:700;
font-variant-numeric:tabular-nums;}}
.pa-driver-chips{{margin-top:10px;}}
.pa-driver{{display:inline-block;padding:3px 9px;margin:2px 4px 2px 0;
border:1px solid currentColor;font-size:10px;border-radius:3px;
background:{pn};}}
.pa-bond{{margin-top:12px;padding:10px 14px;background:{pa};
border-left:2px solid {ac};font-size:12px;line-height:1.6;
color:{td};border-radius:0 3px 3px 0;}}
.pa-bond__num{{font-family:"JetBrains Mono",monospace;
font-variant-numeric:tabular-nums;color:{tx};font-weight:700;}}
.pa-pill{{display:inline-block;padding:2px 9px;font-size:9px;
letter-spacing:1.3px;text-transform:uppercase;font-weight:700;
border-radius:3px;border:1px solid currentColor;}}
.pa-bridge{{background:{pn};border:1px solid {bd};border-radius:4px;
padding:16px 20px;margin-top:18px;position:relative;overflow:hidden;}}
.pa-bridge::before{{content:"";position:absolute;top:0;left:0;right:0;
height:2px;background:linear-gradient(90deg,{po},{ac});}}
.pa-bridge__grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));
gap:18px;margin-top:14px;}}
@media (max-width:720px){{.pa-card__head{{flex-direction:column;}}
.pa-card__sim{{text-align:left;}}}}
.pa-card__band-row{{margin-top:6px;display:flex;gap:8px;align-items:center;}}
.pa-card__collections{{color:{tf};font-size:11px;
font-family:"JetBrains Mono",monospace;}}
.pa-driver-label{{font-size:9px;color:{tf};letter-spacing:1.2px;
text-transform:uppercase;font-weight:600;margin-bottom:4px;}}
.pa-sim-pct{{font-size:16px;opacity:.7;}}
.pa-sim-sub{{font-size:10px;margin-top:2px;font-weight:600;}}
.pa-rec{{margin-top:14px;font-size:12px;color:{td};line-height:1.6;}}
.pa-rec strong{{color:{tx};}}
.pa-compare{{margin-top:10px;font-size:10px;color:{tf};}}
.pa-compare-link{{color:{ac};text-decoration:none;}}
.pa-fv-row{{display:grid;grid-template-columns:180px 70px 70px 1fr;
gap:10px;align-items:baseline;padding:4px 0;
border-bottom:1px solid {bdim};font-size:11px;}}
.pa-fv-name{{color:{td};}}
.pa-fv-val{{font-family:"JetBrains Mono",monospace;color:{tx};text-align:right;}}
.pa-fv-contrib{{font-family:"JetBrains Mono",monospace;text-align:right;}}
.pa-fv-source{{color:{tf};font-size:10px;}}
.pa-fv-details{{margin-top:12px;}}
.pa-fv-details summary{{cursor:pointer;color:{td};letter-spacing:1.2px;
text-transform:uppercase;font-weight:600;font-size:10px;padding:6px 0;}}
.pa-fv-body{{margin-top:8px;}}
.pa-fv-header{{display:grid;grid-template-columns:180px 70px 70px 1fr;
gap:10px;padding:4px 0;border-bottom:1px solid {bd};
font-size:9px;letter-spacing:1.2px;text-transform:uppercase;
color:{tf};font-weight:700;}}
.pa-fv-th-right{{text-align:right;}}
.pa-band-chip{{display:inline-block;padding:4px 12px;margin-right:6px;
font-size:10px;letter-spacing:1.2px;text-transform:uppercase;
font-weight:600;border:1px solid currentColor;border-radius:3px;
text-decoration:none;transition:all 120ms ease;}}
.pa-band-chip-row{{margin:18px 0 12px 0;display:flex;align-items:center;
gap:12px;flex-wrap:wrap;}}
.pa-band-chip-label{{font-size:9px;color:{tf};letter-spacing:1.3px;
text-transform:uppercase;font-weight:600;}}
.pa-band-chip-spacer{{flex:1;}}
.pa-band-chip-hint{{font-size:10px;color:{tf};font-style:italic;}}
.pa-band-chip-kbd{{padding:1px 5px;border:1px solid currentColor;border-radius:2px;}}
.pa-mini-row{{display:flex;align-items:center;gap:8px;margin:3px 0;font-size:10.5px;}}
.pa-mini-label{{min-width:140px;color:{td};}}
.pa-mini-track{{flex:1;height:6px;background:{bdim};border-radius:3px;overflow:hidden;}}
.pa-mini-fill{{display:block;height:100%;opacity:0.75;}}
.pa-mini-value{{min-width:44px;text-align:right;
font-family:"JetBrains Mono",monospace;
font-variant-numeric:tabular-nums;}}
""".format(
        tx=P["text"], td=P["text_dim"], tf=P["text_faint"],
        pn=P["panel"], pa=P["panel_alt"],
        bd=P["border"], bdim=P.get("border_dim", P["border"]),
        ac=P["accent"],
        po=P["positive"], wn=P["warning"], ne=P["negative"],
    )
    return f"<style>{css}</style>"


# ────────────────────────────────────────────────────────────────────
# Demo roster — matches physician_comp's demo shape for the
# /diligence/risk-workbench?demo=steward style hydration
# ────────────────────────────────────────────────────────────────────

def _demo_roster() -> Dict[str, Any]:
    """Returns (providers, metadata dicts). Partners can override via
    Deal Profile writeback eventually; for now this seeds the page
    when no roster is supplied."""
    providers = [
        Provider(provider_id="P001", npi="1234567890",
                 specialty="ORTHOPEDIC_SURGERY",
                 employment_status="W2",
                 base_salary_usd=450_000, wrvus_annual=7500,
                 collections_annual_usd=2_400_000),
        Provider(provider_id="P002", npi="1234567891",
                 specialty="CARDIOLOGY",
                 employment_status="PARTNER",
                 base_salary_usd=600_000, wrvus_annual=10_000,
                 collections_annual_usd=3_200_000),
        Provider(provider_id="P003", npi="1234567892",
                 specialty="FAMILY_MEDICINE",
                 employment_status="W2",
                 base_salary_usd=280_000, wrvus_annual=5500,
                 collections_annual_usd=850_000),
        Provider(provider_id="P004", npi="1234567893",
                 specialty="EMERGENCY_MEDICINE",
                 employment_status="1099",
                 base_salary_usd=420_000, wrvus_annual=8000,
                 collections_annual_usd=1_600_000),
        Provider(provider_id="P005", npi="1234567894",
                 specialty="ANESTHESIOLOGY",
                 employment_status="LOCUM",
                 base_salary_usd=500_000, wrvus_annual=6500,
                 collections_annual_usd=1_900_000),
        Provider(provider_id="P006", npi="1234567895",
                 specialty="GASTROENTEROLOGY",
                 employment_status="PARTNER",
                 base_salary_usd=650_000, wrvus_annual=9000,
                 collections_annual_usd=2_800_000),
        Provider(provider_id="P007", npi="1234567896",
                 specialty="UROLOGY",
                 employment_status="W2",
                 base_salary_usd=500_000, wrvus_annual=7000,
                 collections_annual_usd=2_100_000),
        Provider(provider_id="P008", npi="1234567897",
                 specialty="INTERNAL_MEDICINE",
                 employment_status="W2",
                 base_salary_usd=290_000, wrvus_annual=5200,
                 collections_annual_usd=900_000),
    ]
    return {
        "providers": providers,
        "years_at_facility": {
            "P001": 2, "P002": 15, "P003": 8, "P004": 1,
            "P005": 0.5, "P006": 12, "P007": 4, "P008": 9,
        },
        "ages": {
            "P001": 42, "P002": 58, "P003": 48, "P004": 32,
            "P005": 36, "P006": 55, "P007": 45, "P008": 51,
        },
        "yoy_collections_slopes": {
            "P001": -0.02, "P002": 0.05, "P003": -0.10,
            "P004": 0.00, "P005": -0.08, "P006": 0.03,
            "P007": -0.05, "P008": 0.01,
        },
        "local_competitors": 80,
        "ownership_type": "independent",
    }


# ────────────────────────────────────────────────────────────────────
# Hero
# ────────────────────────────────────────────────────────────────────

_BAND_COLOR = {
    FlightRiskBand.CRITICAL: "negative",
    FlightRiskBand.HIGH: "warning",
    FlightRiskBand.MEDIUM: "text_dim",
    FlightRiskBand.LOW: "positive",
}


def _band_badge(band: FlightRiskBand) -> str:
    color = P.get(_BAND_COLOR[band], P["text_dim"])
    return (
        f'<span class="pa-pill" style="color:{color};">'
        f'{html.escape(band.value)}</span>'
    )


def _driver_readable(name: str) -> str:
    return {
        "comp_gap_normalized": "Comp vs FMV gap",
        "tenure_short": "Short tenure",
        "age_inflection": "Age peak",
        "productivity_decline": "Productivity decline",
        "local_competitor_density": "Competitor density",
        "stark_overlap_flag": "Stark overlap",
        "employment_status_risk": "Employment status",
        "solo_line_revenue_share": "Revenue concentration",
        "specialty_mobility": "Specialty mobility",
    }.get(name, name)


# Tooltip-ready explanation per driver. Rendered as `title=` so it
# surfaces on hover without needing a JS framework.
_DRIVER_EXPLAINER: Dict[str, str] = {
    "comp_gap_normalized": (
        "Absolute distance from specialty FMV p50. Providers far "
        "below market can leave for a raise; providers far above "
        "may be unwound at close under Stark compliance."
    ),
    "tenure_short": (
        "Years at current facility. New hires (<1y) have ~3x the "
        "18-month attrition rate of 10-year veterans."
    ),
    "age_inflection": (
        "U-shape around mid-career: 30s job-hop for advancement, "
        "60+ retirement risk. 40-55 is the stable core."
    ),
    "productivity_decline": (
        "Year-over-year collections slope. Declining production "
        "often signals the provider is already disengaging or "
        "interviewing."
    ),
    "local_competitor_density": (
        "Number of same-specialty providers in the CBSA relative "
        "to roster size. More alternatives = easier to leave."
    ),
    "stark_overlap_flag": (
        "Provider appears in the Stark red-line findings. Comp "
        "structures exceeding FMV under Stark are typically "
        "restructured at close, triggering exit."
    ),
    "employment_status_risk": (
        "LOCUM > 1099 > W2 > PARTNER in flight risk. Equity "
        "holders are stickiest; contractor relationships are "
        "designed to be short-term."
    ),
    "solo_line_revenue_share": (
        "Provider's share of roster collections. High "
        "concentration amplifies the dollar consequence of flight "
        "even when probability is moderate."
    ),
    "specialty_mobility": (
        "Surgical subspecialties (ortho, ENT, ophth) plug into any "
        "ASC; primary care is patient-panel-bound and less mobile."
    ),
}


def _band_filter_chips(current: str = "") -> str:
    """Clickable chips that filter the page to one band.

    The server honours ``?band=CRITICAL|HIGH|MEDIUM|LOW|ALL``; chips
    are just GET links so no JS is required. The active chip is
    highlighted. Pairs naturally with the sortable_table filter
    input below — chips are for coarse filtering, the search box
    is for fine.
    """
    bands = [
        ("ALL", "All bands", "text_dim"),
        ("CRITICAL", "Critical", "negative"),
        ("HIGH", "High", "warning"),
        ("MEDIUM", "Medium", "text_dim"),
        ("LOW", "Low", "positive"),
    ]
    active = (current or "ALL").upper()
    out = []
    for key, label, tone in bands:
        color = P.get(tone, P["text_dim"])
        is_active = (key == active)
        active_cls = " pa-band-chip-active" if is_active else ""
        bg = color if is_active else "transparent"
        fg = "#0a0e17" if is_active else color
        out.append(
            f'<a href="/diligence/physician-attrition?band={key}" '
            f'class="pa-band-chip{active_cls}" '
            f'style="border-color:{color};color:{fg};background:{bg};">'
            f'{html.escape(label)}</a>'
        )
    return (
        '<div class="pa-band-chip-row">'
        '<span class="pa-band-chip-label">Quick filter:</span>'
        + "".join(out)
        + '<span class="pa-band-chip-spacer"></span>'
        '<span class="pa-band-chip-hint">Use the search box below for fine '
        'filtering, or press <kbd class="pa-band-chip-kbd">/</kbd> to focus it.</span>'
        '</div>'
    )


def _feature_vector_drilldown(score: ProviderAttritionScore) -> str:
    """Collapsible <details> block showing the full 9-feature vector
    with the β·x contribution for each feature + the feature's
    provenance source.

    Default-closed so the card stays dense — partner reading is not
    interrupted unless they want to drill."""
    rows: List[str] = []
    for name in score.features.FEATURE_NAMES:
        value = getattr(score.features, name)
        contribution = score.contributions.get(name, 0.0)
        source = score.features.provenance.get(name, "")
        tooltip = _DRIVER_EXPLAINER.get(name, "")
        # Sign-coloured contribution
        contrib_color = (
            P["negative"] if contribution > 0.01
            else P["positive"] if contribution < -0.01
            else P["text_faint"]
        )
        rows.append(
            '<div class="pa-fv-row">'
            f'<span class="pa-fv-name" title="{html.escape(tooltip)}">'
            f'{html.escape(_driver_readable(name))}</span>'
            f'<span class="pa-fv-val">{value:.3f}</span>'
            f'<span class="pa-fv-contrib" style="color:{contrib_color};">'
            f'{contribution:+.2f}</span>'
            f'<span class="pa-fv-source">{html.escape(source)}</span></div>'
        )
    return (
        '<details class="pa-fv-details">'
        '<summary>Full feature vector · click to expand</summary>'
        '<div class="pa-fv-body">'
        '<div class="pa-fv-header">'
        '<span>Feature</span>'
        '<span class="pa-fv-th-right">Value</span>'
        '<span class="pa-fv-th-right">β·x</span>'
        '<span>Source</span></div>'
        f'{"".join(rows)}'
        '<p class="ck-eyebrow">'
        'Features in [0, 1] · β·x is the feature\'s contribution to '
        'log-odds of flight (red raises probability, green lowers). '
        'Sum + intercept (−3.2) = log-odds; sigmoid → probability.</p>'
        '</div></details>'
    )


def _contribution_mini_bar(
    score: "ProviderAttritionScore", max_contribution: float,
) -> str:
    """Horizontal bar chart of the top drivers' log-odds contributions.

    Visually shows which 2-3 features are doing the work behind the
    probability — the "why" behind the flight-risk band.
    """
    # Pull top 4 positive contributions (excluding intercept).
    contribs = [
        (name, val) for name, val in score.contributions.items()
        if name != "intercept" and val > 0
    ]
    contribs.sort(key=lambda t: t[1], reverse=True)
    contribs = contribs[:4]
    if not contribs:
        return ""
    band_color = P.get(_BAND_COLOR[score.band], P["text_dim"])
    rows = []
    scale = max(max_contribution, max(v for _, v in contribs), 0.01)
    for name, val in contribs:
        pct = (val / scale) * 100
        label = _driver_readable(name)
        tooltip = _DRIVER_EXPLAINER.get(name, "")
        rows.append(
            '<div class="pa-mini-row">'
            f'<span class="pa-mini-label" title="{html.escape(tooltip)}">'
            f'{html.escape(label)}</span>'
            '<span class="pa-mini-track">'
            f'<span class="pa-mini-fill" '
            f'style="width:{pct:.1f}%;background:{band_color};"></span></span>'
            f'<span class="pa-mini-value" style="color:{band_color};">'
            f'{val:+.2f}</span>'
            '</div>'
        )
    return (
        f'<div style="margin-top:12px;padding:10px 12px;'
        f'background:{P["panel_alt"]};border-radius:3px;'
        f'border:1px solid {P["border_dim"]};">'
        f'<div style="font-size:9px;color:{P["text_faint"]};'
        f'letter-spacing:1.2px;text-transform:uppercase;'
        f'font-weight:600;margin-bottom:6px;">'
        f'Log-odds contribution (top drivers · hover for detail)</div>'
        f'{"".join(rows)}</div>'
    )


def _hero(report: AttritionReport, target_name: str) -> str:
    roster = report.roster_size
    crit = report.critical_count
    high = report.high_count
    collections = report.total_collections_usd
    at_risk = report.total_expected_collections_at_risk_usd
    top_share = report.top_at_risk_contributors_pct_of_roster

    # Partner-speak banner keyed off CRITICAL count + concentration
    if crit >= 2 and top_share >= 0.50:
        banner_class = "alert"
        banner = (
            f"⚠ {crit} providers are CRITICAL flight-risk and the top-20% "
            f"of the roster concentrates {top_share*100:.0f}% of the at-risk "
            f"collections. This deal cannot close safely without retention "
            f"bonds for the named CRITICAL providers."
        )
    elif crit >= 1 or high >= 3:
        banner_class = "warn"
        banner = (
            f"{crit} CRITICAL · {high} HIGH flight-risk providers. "
            f"Earn-out must include retention milestones for each "
            f"HIGH/CRITICAL named provider. Model a "
            f"${report.bridge_input.ebitda_at_risk_usd:,.0f} EBITDA "
            f"hit in the Deal MC physician-attrition driver."
        )
    elif high >= 1 or report.medium_count >= 3:
        banner_class = "warn"
        banner = (
            f"{high} HIGH · {report.medium_count} MEDIUM risk providers. "
            f"No structural change needed at signing but 100-day plan "
            f"should include retention outreach for the HIGH band."
        )
    else:
        banner_class = "good"
        banner = (
            f"Roster is stable — 0 CRITICAL, {high} HIGH. The "
            f"physician-attrition lever in the EBITDA bridge can be "
            f"modeled at the baseline specialty churn rate (~5%)."
        )

    # Peer physician turnover (Seeking Alpha / 10-K disclosures
    # aggregated). Gives partners a "your target vs public peers"
    # framing without leaving the page.
    peer_benchmark = ""
    try:
        from ..market_intel import peer_physician_turnover_stats
        stats = peer_physician_turnover_stats()
        if stats["count"] > 0:
            peer_median = stats["median"]
            # Implied aggregate flight rate of the scored roster —
            # probability-weighted attrition percentage of collections.
            implied = (
                at_risk / collections if collections > 0 else 0.0
            )
            if implied > peer_median * 1.3:
                peer_verdict = (
                    f"Your roster's implied attrition rate "
                    f"({implied*100:.1f}%) is materially above the "
                    f"public-peer median ({peer_median*100:.1f}%, "
                    f"n={stats['count']} disclosures)."
                )
            elif implied < peer_median * 0.8:
                peer_verdict = (
                    f"Your roster's implied attrition rate "
                    f"({implied*100:.1f}%) is below the public-peer "
                    f"median ({peer_median*100:.1f}%, n={stats['count']} "
                    f"disclosures) — favorable signal."
                )
            else:
                peer_verdict = (
                    f"Implied attrition rate ({implied*100:.1f}%) is "
                    f"in line with the public-peer median "
                    f"({peer_median*100:.1f}%, n={stats['count']})."
                )
            peer_benchmark = f" {peer_verdict}"
    except Exception:  # noqa: BLE001
        peer_benchmark = ""

    summary = (
        f"Flight-risk probabilities were computed for all {roster} "
        f"providers using a 9-feature model (comp gap vs FMV, tenure, "
        f"age inflection, productivity trend, local competitor density, "
        f"Stark overlap, employment status, revenue concentration, "
        f"specialty mobility). "
        f"Expected collections at risk sums to "
        f"${at_risk:,.0f} ({at_risk/collections*100 if collections > 0 else 0:.1f}% of "
        f"roster revenue). The top-20% of providers concentrates "
        f"{top_share*100:.1f}% of that risk — retention actions should "
        f"focus there.{peer_benchmark}"
    )

    # Four KPI tiles
    at_risk_color = (
        P["negative"] if at_risk / max(collections, 1) > 0.15
        else P["warning"] if at_risk / max(collections, 1) > 0.05
        else P["positive"]
    )
    bridge = report.bridge_input
    conf_color = {
        "HIGH": P["positive"], "MEDIUM": P["warning"],
        "LOW": P["negative"],
    }.get(bridge.confidence if bridge else "MEDIUM", P["text_dim"])

    # Inline provenance on every hero number — hover for source +
    # formula.  The numbers become partner-defensible on their own.
    roster_num = provenance(
        str(roster),
        source="AttritionReport.roster_size",
        formula="count(providers in roster)",
        detail=(
            "Number of providers scored by the Predictive "
            "Physician Attrition Model."
        ),
    )
    collections_num = provenance(
        f'${collections/1e6:,.1f}M',
        source="sum(provider.collections_annual_usd)",
        formula="SUM(collections_annual_usd) over roster",
        detail=(
            "Sum of annual collections across all scored providers. "
            "Denominator for the at-risk-percent calculation."
        ),
    )
    at_risk_num = provenance(
        f'${at_risk/1e6:,.1f}M',
        source="AttritionReport.total_expected_collections_at_risk_usd",
        formula=(
            "SUM(probability × collections_annual_usd) over roster"
        ),
        detail=(
            "Expected-value calculation: each provider's 18-month "
            "flight probability × their annual collections. Not a "
            "point estimate; partners should read the band counts "
            "alongside this number."
        ),
    )
    bridge_num = provenance(
        f'${bridge.ebitda_at_risk_usd/1e3:,.0f}K',
        source="BridgeLeverInput.ebitda_at_risk_usd",
        formula=(
            f"expected_collections_lost × ebitda_margin · "
            f"expected_collections_lost = total_at_risk × "
            f"realization_probability ({bridge.realization_probability:.0%}) · "
            f"ebitda_margin = {bridge.ebitda_margin_assumed:.0%}"
        ),
        detail=(
            "Data-driven input for the Deal MC "
            "physician_attrition_pct driver. Replaces the industry-"
            "default 5% attrition rate with a per-provider roll-up."
        ),
    )

    kpi_row = (
        '<div class="ck-kpi-strip">'
        + ck_kpi_block(
            "Roster size", roster_num,
            sub=(
                f"{crit} critical · {high} high · {report.medium_count} medium · "
                f"{report.low_count} low"
            ),
        )
        + ck_kpi_block(
            "Total collections", collections_num,
            sub="roster annual collections · hover for source",
        )
        + ck_kpi_block(
            "Expected $ at risk", at_risk_num,
            sub=(
                f"{at_risk/collections*100 if collections > 0 else 0:.1f}% "
                f"of roster · 18-mo horizon"
            ),
        )
        + ck_kpi_block(
            "EBITDA bridge hit", bridge_num,
            sub=(
                f"{bridge.confidence} confidence · "
                f"{bridge.realization_probability*100:.0f}% realization"
            ),
        )
        + "</div>"
    )

    intro = ck_section_intro(
        eyebrow="Physician Attrition",
        headline=html.escape(target_name),
        body=(
            f"18-month flight-risk · 9-feature model · "
            f"{roster} providers scored"
        ),
        italic_word="attrition",
    )
    return (
        f'{intro}'
        f'<div class="pa-callout {banner_class}">{html.escape(banner)}</div>'
        f'<p class="ck-section-body">'
        f'<strong>What this shows: </strong>{summary}</p>'
        f'{kpi_row}'
    )


# ────────────────────────────────────────────────────────────────────
# Per-provider cards
# ────────────────────────────────────────────────────────────────────

def _card(
    score: ProviderAttritionScore,
    max_contribution: float = 0.0,
) -> str:
    band_color = P.get(_BAND_COLOR[score.band], P["text_dim"])
    rec = score.recommendation
    drivers_html = "".join(
        f'<span class="pa-driver" style="color:{band_color};" '
        f'title="{html.escape(_DRIVER_EXPLAINER.get(d, ""))}">'
        f'{html.escape(_driver_readable(d))}</span>'
        for d in score.top_drivers
    )
    mini_bar = _contribution_mini_bar(score, max_contribution)
    bond_html = ""
    if rec.suggested_bond_usd:
        bond_html = (
            '<div class="pa-bond">'
            '<strong>Retention bond sizing: </strong>'
            f'<span class="pa-bond__num">${rec.suggested_bond_usd:,.0f}</span> '
            f'({rec.retention_years}y lockup) — bonds this provider to the '
            f'target through year-{rec.retention_years}.'
            '</div>'
        )
    return (
        f'<div class="pa-card">'
        f'<div class="pa-card__band" style="background:{band_color};"></div>'
        f'<div class="pa-card__body">'
        f'<div class="pa-card__head">'
        f'<div class="pa-card__meta">'
        f'<div class="pa-card__top">'
        f'{html.escape(score.specialty.replace("_", " "))} · '
        f'{html.escape(score.npi or "no NPI")}</div>'
        f'<div class="pa-card__title">{html.escape(score.provider_id)}</div>'
        f'<div class="pa-card__band-row">'
        f'{_band_badge(score.band)}'
        f'<span class="pa-card__collections">'
        f'${score.collections_annual_usd:,.0f} annual collections'
        f'</span></div>'
        f'<div class="pa-driver-chips">'
        f'<div class="pa-driver-label">Top drivers</div>'
        f'{drivers_html}</div>'
        f'</div>'
        f'<div class="pa-card__sim">'
        f'<div class="pa-card__top">18-mo flight probability</div>'
        f'<div class="pa-card__sim-val" style="color:{band_color};">'
        f'{score.probability*100:.0f}<span class="pa-sim-pct">%</span>'
        f'</div>'
        f'<div class="pa-sim-sub" style="color:{band_color};">'
        f'~${score.expected_collections_at_risk_usd:,.0f} at risk</div>'
        f'</div>'
        f'</div>'
        f'{mini_bar}'
        f'<div class="pa-rec">'
        f'<strong>Partner recommendation: </strong>'
        f'{html.escape(rec.recommendation)}</div>'
        f'{bond_html}'
        f'{_feature_vector_drilldown(score)}'
        f'<div class="pa-compare">'
        f'<a href="/diligence/physician-attrition?compare={html.escape(score.provider_id)}" '
        f'class="pa-compare-link">Add to compare →</a>'
        f'</div>'
        f'</div>'
        f'</div>'
    )


# ────────────────────────────────────────────────────────────────────
# Roster table
# ────────────────────────────────────────────────────────────────────

def _roster_table(
    report: AttritionReport,
    providers_by_id: Optional[Dict[str, Provider]] = None,
) -> str:
    """Render the full roster as a sortable/exportable table.

    ``providers_by_id`` is required to resolve the employment_status
    value cleanly (the features.provenance string is awkward for
    display; the Provider dataclass carries it verbatim).
    """
    if not report.scores:
        return ""
    providers_by_id = providers_by_id or {}
    headers = [
        "Provider", "Specialty", "Employment",
        "Flight prob", "Band", "Collections", "$ at risk", "Top driver",
    ]
    rows: List[List[str]] = []
    keys: List[List[Any]] = []
    for s in report.scores:
        band_color = P.get(_BAND_COLOR[s.band], P["text_dim"])
        band_html = (
            f'<span style="color:{band_color};font-weight:600;">'
            f'{html.escape(s.band.value)}</span>'
        )
        provider = providers_by_id.get(s.provider_id)
        emp_raw = getattr(provider, "employment_status", None) or "—"
        emp = emp_raw.replace("_", " ")
        top_driver = _driver_readable(s.top_drivers[0]) if s.top_drivers else "—"
        rows.append([
            s.provider_id,
            s.specialty.replace("_", " "),
            emp,
            f"{s.probability*100:.1f}%",
            band_html,
            f"${s.collections_annual_usd:,.0f}",
            f"${s.expected_collections_at_risk_usd:,.0f}",
            top_driver,
        ])
        keys.append([
            s.provider_id, s.specialty, emp,
            s.probability, s.band.value,
            s.collections_annual_usd,
            s.expected_collections_at_risk_usd,
            top_driver,
        ])
    return sortable_table(
        headers, rows, name="attrition_roster", sort_keys=keys,
    )


# ────────────────────────────────────────────────────────────────────
# Bridge lever card
# ────────────────────────────────────────────────────────────────────

def _bridge_card(report: AttritionReport) -> str:
    b = report.bridge_input
    if b is None:
        return ""
    conf_tone = {
        "HIGH": "positive", "MEDIUM": "warning", "LOW": "negative",
    }.get(b.confidence, "neutral")
    conf_badge = ck_signal_badge(html.escape(b.confidence), tone=conf_tone)
    bridge_inner = (
        '<p class="ck-section-body">Data-driven input for Deal MC.</p>'
        '<div class="ck-kpi-strip">'
        + ck_kpi_block("EBITDA at risk", f"${b.ebitda_at_risk_usd:,.0f}")
        + ck_kpi_block(
            "Collections lost (projected)",
            f"${b.expected_collections_lost_usd:,.0f}",
        )
        + ck_kpi_block(
            "Attrition as % collections",
            f"{b.attrition_pct_of_collections*100:.1f}%",
        )
        + ck_kpi_block("Confidence", conf_badge)
        + '</div>'
        + '<p class="ck-section-body">'
        '<strong>How to use:</strong> '
        'Feed the attrition-pct-of-collections value into the Deal MC '
        '<code>physician_attrition_pct</code> '
        'driver instead of the industry-default 5%. The bridge EBITDA-hit '
        f'assumes a {b.ebitda_margin_assumed*100:.0f}% EBITDA margin on '
        'physician-group collections and a '
        f'{b.realization_probability*100:.0f}% realization rate over the '
        '18-month horizon given a standard earn-out structure.</p>'
    )
    return ck_panel(
        bridge_inner,
        title="EBITDA Bridge · Physician-Attrition Lever",
    )


# ────────────────────────────────────────────────────────────────────
# Public entry
# ────────────────────────────────────────────────────────────────────

def _compare_view(
    report: AttritionReport,
    providers_by_id: Dict[str, Provider],
    compare_ids: List[str],
    target_name: str,
) -> str:
    """Render a side-by-side comparison of 2-3 providers.

    Shows the feature vector, probability, recommendation, and bond
    sizing in a column-per-provider layout. Partners use this to
    answer "which provider needs the bigger bond" or "why is X
    higher than Y."
    """
    score_by_id = {s.provider_id: s for s in report.scores}
    resolved = [score_by_id[pid] for pid in compare_ids if pid in score_by_id]
    if not resolved:
        return ck_panel(
            '<p class="ck-section-body">'
            'None of the provided provider IDs were found in the '
            'current roster. Check the ?compare= parameter against '
            'the roster table below.</p>',
            title="Compare providers — no matches",
        )

    # Build feature-by-feature comparison table.
    feature_cols = "".join(
        f'<th class="num">{html.escape(s.provider_id)}<br>'
        f'<span class="pa-cmp-spec">{html.escape(s.specialty.replace("_", " "))}</span></th>'
        for s in resolved
    )
    sim_cells_html = "".join(
        f'<td class="num"><strong>{s.probability*100:.0f}%</strong></td>'
        for s in resolved
    )
    band_cells_html = "".join(
        f'<td class="num">{_band_badge(s.band)}</td>' for s in resolved
    )
    bond_cells_html = "".join(
        f'<td class="num">'
        f'{"$" + format(int(s.recommendation.suggested_bond_usd or 0), ",") if (s.recommendation.suggested_bond_usd or 0) > 0 else "—"}'
        f'{" / " + str(s.recommendation.retention_years) + "y" if s.recommendation.retention_years else ""}'
        '</td>'
        for s in resolved
    )

    feature_rows: List[str] = []
    for name in resolved[0].features.FEATURE_NAMES:
        vals = [getattr(s.features, name) for s in resolved]
        max_v = max(vals) if vals else 0.0
        cells = []
        for v in vals:
            is_max = (abs(v - max_v) < 1e-9 and max_v > 0.01)
            cls = "num cad-neg" if is_max else "num"
            wt = "<strong>" if is_max else ""
            wt_close = "</strong>" if is_max else ""
            cells.append(f'<td class="{cls}">{wt}{v:.3f}{wt_close}</td>')
        feature_rows.append(
            '<tr>'
            f'<td title="{html.escape(_DRIVER_EXPLAINER.get(name, ""))}">'
            f'{html.escape(_driver_readable(name))}</td>'
            + "".join(cells)
            + '</tr>'
        )

    intro = ck_section_intro(
        eyebrow="Compare providers",
        headline=f"{html.escape(target_name)} · {len(resolved)}-way comparison.",
        italic_word="comparison",
        body=(
            "Column per provider. Feature rows highlight the worst "
            "(highest-value) cell in red. Use this to answer "
            "'which provider needs the bigger bond' or 'which driver "
            "is actually different between these two?'"
        ),
    )
    table_html = (
        '<table class="cad-table">'
        '<thead><tr><th>Feature</th>'
        f'{feature_cols}</tr></thead>'
        '<tbody>'
        f'<tr><td><strong>Probability</strong></td>{sim_cells_html}</tr>'
        f'<tr><td><strong>Band</strong></td>{band_cells_html}</tr>'
        f'<tr><td><strong>Suggested bond</strong></td>{bond_cells_html}</tr>'
        + "".join(feature_rows)
        + '</tbody></table>'
    )
    return (
        intro
        + ck_panel(table_html, title=f"{len(resolved)}-way comparison")
        + '<p class="ck-section-body">'
        + '<a href="/diligence/physician-attrition" class="ck-link">'
        + '← Back to full roster</a></p>'
    )


def _parse_compare_ids(qs: Dict[str, List[str]]) -> List[str]:
    """Accept either ?compare=P1,P2 or repeated ?compare=P1&compare=P2."""
    raw = qs.get("compare") or []
    ids: List[str] = []
    for entry in raw:
        for tok in str(entry).split(","):
            tok = tok.strip()
            if tok and tok not in ids:
                ids.append(tok)
    return ids[:4]  # cap at 4 for readable layout


def _filter_by_band(
    report: AttritionReport, band: str,
) -> AttritionReport:
    """Returns a shallow-filtered view of the report limited to
    ``band``. ``ALL`` or empty returns the original.

    Recomputes band counts to match the visible set so the hero
    numbers line up with what's shown below.
    """
    band = (band or "").upper()
    if not band or band == "ALL":
        return report
    valid = {b.value for b in FlightRiskBand}
    if band not in valid:
        return report
    keep = [s for s in report.scores if s.band.value == band]
    # Preserve most fields but adjust the per-band counts so the
    # hero reflects the filtered view.
    filtered = AttritionReport(
        scores=keep,
        roster_size=len(keep),
        critical_count=sum(1 for s in keep if s.band == FlightRiskBand.CRITICAL),
        high_count=sum(1 for s in keep if s.band == FlightRiskBand.HIGH),
        medium_count=sum(1 for s in keep if s.band == FlightRiskBand.MEDIUM),
        low_count=sum(1 for s in keep if s.band == FlightRiskBand.LOW),
        total_collections_usd=sum(s.collections_annual_usd for s in keep),
        total_expected_collections_at_risk_usd=sum(
            s.expected_collections_at_risk_usd for s in keep
        ),
        top_at_risk_contributors_pct_of_roster=(
            report.top_at_risk_contributors_pct_of_roster
        ),
        bridge_input=report.bridge_input,
    )
    return filtered


def render_physician_attrition_page(
    qs: Optional[Dict[str, List[str]]] = None,
) -> str:
    qs = qs or {}

    target_name = (qs.get("target_name") or ["Target Physician Group"])[0]
    cfg = _demo_roster()
    providers = cfg["providers"]
    report = analyze_roster(
        providers,
        years_at_facility=cfg["years_at_facility"],
        ages=cfg["ages"],
        yoy_collections_slopes=cfg["yoy_collections_slopes"],
        local_competitors=cfg["local_competitors"],
        ownership_type=cfg["ownership_type"],
    )
    providers_by_id = {p.provider_id: p for p in providers}

    # Compare mode takes precedence — it's a separate view.
    compare_ids = _parse_compare_ids(qs)
    if compare_ids:
        body = (
            _scoped_styles()
            + '<div class="pa-wrap">'
            + _compare_view(
                report, providers_by_id, compare_ids, target_name,
            )
            + '</div>'
            + bookmark_hint()
        )
        return chartis_shell(
            body,
            f"Physician Attrition · Compare — {target_name}",
            subtitle="Predictive RCM analytic",
        )

    # Normal view — possibly with a band filter applied.
    band_filter = (qs.get("band") or [""])[0]
    filtered = _filter_by_band(report, band_filter)

    # Top HIGH/CRITICAL cards — share a common log-odds scale so bars
    # compare visually across providers.
    focus_scores = filtered.high_or_critical_scores[:6]
    max_contribution = 0.0
    for s in focus_scores:
        for name, val in s.contributions.items():
            if name != "intercept" and val > max_contribution:
                max_contribution = val
    cards = "".join(
        _card(s, max_contribution=max_contribution)
        for s in focus_scores
    )

    # Full report JSON for export
    hero_and_bridge = export_json_panel(
        _hero(filtered, target_name) + _bridge_card(filtered),
        payload=report.to_dict(),
        name="physician_attrition_report",
    )

    # Cross-link to Physician Economic Units — PPAM tells you who's
    # likely to leave; EU tells you who should.
    crosslink = ck_panel(
        '<p class="ck-section-body">'
        '<strong>Related: </strong>'
        '<a href="/diligence/physician-eu" class="ck-link">'
        'Physician Economic Units →</a> '
        'tells you who SHOULD leave (per-provider P&L + loss-maker '
        'tail). Together with this flight-risk view, the complete '
        'physician-portfolio optimization picture.</p>',
        title="Cross-reference",
    )

    if focus_scores:
        focus_block = (
            ck_section_header(
                f"High + critical providers · {len(focus_scores)} "
                "shown · retention action required",
                eyebrow="ROSTER FOCUS",
            )
            + cards
        )
    else:
        focus_block = ck_panel(
            '<p class="ck-section-body">'
            f'No providers are in the {html.escape((band_filter or "HIGH/CRITICAL").upper())} '
            'band. No retention bonds required for the filtered view.</p>',
            title="Roster focus",
        )

    body = (
        _scoped_styles()
        + ck_page_title(
            "Physician Attrition",
            eyebrow="RCM DILIGENCE",
            meta=f"Target: {target_name} · predictive churn analytic",
        )
        + '<div class="pa-wrap">'
        + hero_and_bridge
        + crosslink
        + _band_filter_chips(band_filter)
        + focus_block
        + ck_section_header(
            "Full roster · sortable · filterable · CSV export",
            eyebrow="ALL PROVIDERS",
        )
        + _roster_table(filtered, providers_by_id)
        + '</div>'
        + bookmark_hint()
    )

    return chartis_shell(
        body, f"Physician Attrition — {target_name}",
        active_nav="/diligence/physician-attrition",
        subtitle="Predictive RCM analytic",
    )
