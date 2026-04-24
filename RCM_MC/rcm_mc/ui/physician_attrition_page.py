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
from ._chartis_kit import P, chartis_shell
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
""".format(
        tx=P["text"], td=P["text_dim"], tf=P["text_faint"],
        pn=P["panel"], pa=P["panel_alt"],
        bd=P["border"], ac=P["accent"],
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
        out.append(
            f'<a href="/diligence/physician-attrition?band={key}" '
            f'style="display:inline-block;padding:4px 12px;'
            f'margin-right:6px;font-size:10px;letter-spacing:1.2px;'
            f'text-transform:uppercase;font-weight:600;'
            f'border:1px solid {color};border-radius:3px;'
            f'color:{"#0a0e17" if is_active else color};'
            f'background:{color if is_active else "transparent"};'
            f'text-decoration:none;transition:all 120ms ease;">'
            f'{html.escape(label)}</a>'
        )
    return (
        f'<div style="margin:18px 0 12px 0;display:flex;'
        f'align-items:center;gap:12px;flex-wrap:wrap;">'
        f'<span style="font-size:9px;color:{P["text_faint"]};'
        f'letter-spacing:1.3px;text-transform:uppercase;'
        f'font-weight:600;">Quick filter:</span>'
        + "".join(out)
        + f'<span style="flex:1;"></span>'
        f'<span style="font-size:10px;color:{P["text_faint"]};'
        f'font-style:italic;">Use the search box below for fine '
        f'filtering, or press '
        f'<kbd style="padding:1px 5px;border:1px solid currentColor;'
        f'border-radius:2px;">/</kbd> to focus it.</span>'
        f'</div>'
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
            f'<div style="display:grid;grid-template-columns:180px 70px 70px 1fr;'
            f'gap:10px;align-items:baseline;padding:4px 0;'
            f'border-bottom:1px solid {P["border_dim"]};font-size:11px;">'
            f'<span style="color:{P["text_dim"]};" '
            f'title="{html.escape(tooltip)}">'
            f'{html.escape(_driver_readable(name))}</span>'
            f'<span style="font-family:\'JetBrains Mono\',monospace;'
            f'color:{P["text"]};text-align:right;">{value:.3f}</span>'
            f'<span style="font-family:\'JetBrains Mono\',monospace;'
            f'color:{contrib_color};text-align:right;">{contribution:+.2f}</span>'
            f'<span style="color:{P["text_faint"]};font-size:10px;">'
            f'{html.escape(source)}</span></div>'
        )
    return (
        f'<details style="margin-top:12px;">'
        f'<summary style="cursor:pointer;color:{P["text_dim"]};'
        f'letter-spacing:1.2px;text-transform:uppercase;'
        f'font-weight:600;font-size:10px;padding:6px 0;">'
        f'Full feature vector · click to expand</summary>'
        f'<div style="margin-top:8px;">'
        f'<div style="display:grid;grid-template-columns:180px 70px 70px 1fr;'
        f'gap:10px;padding:4px 0;border-bottom:1px solid {P["border"]};'
        f'font-size:9px;letter-spacing:1.2px;text-transform:uppercase;'
        f'color:{P["text_faint"]};font-weight:700;">'
        f'<span>Feature</span>'
        f'<span style="text-align:right;">Value</span>'
        f'<span style="text-align:right;">β·x</span>'
        f'<span>Source</span></div>'
        f'{"".join(rows)}'
        f'<div style="margin-top:8px;font-size:10px;'
        f'color:{P["text_faint"]};line-height:1.55;">'
        f'Features in [0, 1] · β·x is the feature\'s contribution to '
        f'log-odds of flight (red raises probability, green lowers). '
        f'Sum + intercept (−3.2) = log-odds; sigmoid → probability.</div>'
        f'</div></details>'
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
            f'<div style="display:flex;align-items:center;gap:8px;'
            f'margin:3px 0;font-size:10.5px;">'
            f'<span style="min-width:140px;color:{P["text_dim"]};" '
            f'title="{html.escape(tooltip)}">'
            f'{html.escape(label)}</span>'
            f'<span style="flex:1;height:6px;background:{P["border_dim"]};'
            f'border-radius:3px;overflow:hidden;">'
            f'<span style="display:block;height:100%;width:{pct:.1f}%;'
            f'background:{band_color};opacity:0.75;"></span></span>'
            f'<span style="min-width:44px;text-align:right;'
            f'color:{band_color};font-family:\'JetBrains Mono\',monospace;'
            f'font-variant-numeric:tabular-nums;">'
            f'{val:+.2f}</span>'
            f'</div>'
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
        f'<div class="pa-kpi-grid">'
        f'<div class="pa-kpi">'
        f'<div class="pa-kpi__label">Roster size</div>'
        f'<div class="pa-kpi__val" style="color:{P["text"]};">'
        f'{roster_num}</div>'
        f'<div class="pa-kpi__band" style="color:{P["text_faint"]};">'
        f'{crit} critical · {high} high · {report.medium_count} medium · '
        f'{report.low_count} low</div></div>'
        f'<div class="pa-kpi">'
        f'<div class="pa-kpi__label">Total collections</div>'
        f'<div class="pa-kpi__val" style="color:{P["text"]};">'
        f'{collections_num}</div>'
        f'<div class="pa-kpi__band" style="color:{P["text_faint"]};">'
        f'roster annual collections · hover for source</div></div>'
        f'<div class="pa-kpi">'
        f'<div class="pa-kpi__label">Expected $ at risk</div>'
        f'<div class="pa-kpi__val" style="color:{at_risk_color};">'
        f'{at_risk_num}</div>'
        f'<div class="pa-kpi__band" style="color:{at_risk_color};">'
        f'{at_risk/collections*100 if collections > 0 else 0:.1f}% of roster · '
        f'18-mo horizon</div></div>'
        f'<div class="pa-kpi">'
        f'<div class="pa-kpi__label">EBITDA bridge hit</div>'
        f'<div class="pa-kpi__val" style="color:{conf_color};">'
        f'{bridge_num}</div>'
        f'<div class="pa-kpi__band" style="color:{conf_color};">'
        f'{bridge.confidence} confidence · '
        f'{bridge.realization_probability*100:.0f}% realization</div></div>'
        f'</div>'
    )

    return (
        f'<div style="padding:24px 0 16px 0;border-bottom:1px solid '
        f'{P["border"]};margin-bottom:22px;">'
        f'<div class="pa-eyebrow">Physician Attrition</div>'
        f'<div class="pa-h1">{html.escape(target_name)}</div>'
        f'<div style="font-size:11px;color:{P["text_faint"]};margin-top:4px;">'
        f'18-month flight-risk · 9-feature model · {roster} providers scored</div>'
        f'<div class="pa-callout {banner_class}">{html.escape(banner)}</div>'
        f'<div class="pa-callout">'
        f'<strong style="color:{P["text"]};">What this shows: </strong>'
        f'{summary}</div>'
        f'{kpi_row}'
        f'</div>'
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
            f'<div class="pa-bond">'
            f'<strong style="color:{P["text"]};">Retention bond sizing: </strong>'
            f'<span class="pa-bond__num">${rec.suggested_bond_usd:,.0f}</span> '
            f'({rec.retention_years}y lockup) — bonds this provider to the '
            f'target through year-{rec.retention_years}.'
            f'</div>'
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
        f'<div style="margin-top:6px;display:flex;gap:8px;'
        f'align-items:center;">'
        f'{_band_badge(score.band)}'
        f'<span style="color:{P["text_faint"]};font-size:11px;'
        f'font-family:\'JetBrains Mono\',monospace;">'
        f'${score.collections_annual_usd:,.0f} annual collections'
        f'</span></div>'
        f'<div class="pa-driver-chips">'
        f'<div style="font-size:9px;color:{P["text_faint"]};'
        f'letter-spacing:1.2px;text-transform:uppercase;'
        f'font-weight:600;margin-bottom:4px;">Top drivers</div>'
        f'{drivers_html}</div>'
        f'</div>'
        f'<div class="pa-card__sim">'
        f'<div class="pa-card__top">18-mo flight probability</div>'
        f'<div class="pa-card__sim-val" style="color:{band_color};">'
        f'{score.probability*100:.0f}<span style="font-size:16px;opacity:.7;">%</span>'
        f'</div>'
        f'<div style="font-size:10px;color:{band_color};margin-top:2px;'
        f'font-weight:600;">'
        f'~${score.expected_collections_at_risk_usd:,.0f} at risk</div>'
        f'</div>'
        f'</div>'
        f'{mini_bar}'
        f'<div style="margin-top:14px;font-size:12px;color:{P["text_dim"]};'
        f'line-height:1.6;">'
        f'<strong style="color:{P["text"]};">Partner recommendation: </strong>'
        f'{html.escape(rec.recommendation)}</div>'
        f'{bond_html}'
        f'{_feature_vector_drilldown(score)}'
        f'<div style="margin-top:10px;font-size:10px;'
        f'color:{P["text_faint"]};">'
        f'<a href="/diligence/physician-attrition?compare={html.escape(score.provider_id)}" '
        f'style="color:{P["accent"]};text-decoration:none;">'
        f'Add to compare →</a>'
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
    conf_color = {
        "HIGH": P["positive"], "MEDIUM": P["warning"],
        "LOW": P["negative"],
    }.get(b.confidence, P["text_dim"])
    return (
        f'<div class="pa-bridge">'
        f'<div class="pa-eyebrow">EBITDA Bridge · Physician-Attrition Lever</div>'
        f'<div style="font-size:16px;color:{P["text"]};font-weight:600;'
        f'margin-top:2px;">Data-driven input for Deal MC</div>'
        f'<div class="pa-bridge__grid">'
        f'<div><div style="font-size:9px;color:{P["text_faint"]};'
        f'letter-spacing:.5px;text-transform:uppercase;">EBITDA at risk</div>'
        f'<div style="font-size:22px;font-family:\'JetBrains Mono\',monospace;'
        f'font-weight:700;color:{P["negative"]};">'
        f'${b.ebitda_at_risk_usd:,.0f}</div></div>'
        f'<div><div style="font-size:9px;color:{P["text_faint"]};'
        f'letter-spacing:.5px;text-transform:uppercase;">'
        f'Collections lost (projected)</div>'
        f'<div style="font-size:18px;color:{P["text"]};">'
        f'${b.expected_collections_lost_usd:,.0f}</div></div>'
        f'<div><div style="font-size:9px;color:{P["text_faint"]};'
        f'letter-spacing:.5px;text-transform:uppercase;">'
        f'Attrition as % collections</div>'
        f'<div style="font-size:18px;color:{P["text"]};">'
        f'{b.attrition_pct_of_collections*100:.1f}%</div></div>'
        f'<div><div style="font-size:9px;color:{P["text_faint"]};'
        f'letter-spacing:.5px;text-transform:uppercase;">Confidence</div>'
        f'<div style="font-size:18px;color:{conf_color};font-weight:600;">'
        f'{html.escape(b.confidence)}</div></div>'
        f'</div>'
        f'<div style="margin-top:14px;font-size:11.5px;color:{P["text_dim"]};'
        f'line-height:1.6;max-width:880px;">'
        f'<strong style="color:{P["text"]};">How to use: </strong>'
        f'Feed the attrition-pct-of-collections value into the Deal MC '
        f'<code style="color:{P["text_dim"]};">physician_attrition_pct</code> '
        f'driver instead of the industry-default 5%. The bridge EBITDA-hit '
        f'assumes a {b.ebitda_margin_assumed*100:.0f}% EBITDA margin on '
        f'physician-group collections and a {b.realization_probability*100:.0f}% '
        f'realization rate over the 18-month horizon given a standard '
        f'earn-out structure.</div>'
        f'</div>'
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
        return (
            '<div class="pa-callout warn" style="margin-top:16px;">'
            'None of the provided provider IDs were found in the '
            'current roster. Check the ?compare= parameter against '
            'the roster table below.</div>'
        )

    # Build feature-by-feature comparison matrix.
    rows: List[str] = []
    for name in resolved[0].features.FEATURE_NAMES:
        cells = [
            f'<div style="color:{P["text_dim"]};" '
            f'title="{html.escape(_DRIVER_EXPLAINER.get(name, ""))}">'
            f'{html.escape(_driver_readable(name))}</div>'
        ]
        vals = [getattr(s.features, name) for s in resolved]
        max_v = max(vals) if vals else 0.0
        for v in vals:
            # Highlight the worst (highest) feature value across
            # providers — that's the one drivin the delta.
            is_max = (abs(v - max_v) < 1e-9 and max_v > 0.01)
            cells.append(
                f'<div style="text-align:right;'
                f'font-family:\'JetBrains Mono\',monospace;'
                f'color:{P["negative"] if is_max else P["text"]};'
                f'font-weight:{"700" if is_max else "400"};">'
                f'{v:.3f}</div>'
            )
        rows.append(
            f'<div style="display:grid;grid-template-columns:'
            f'220px repeat({len(resolved)}, 1fr);gap:14px;'
            f'padding:5px 0;border-bottom:1px solid {P["border_dim"]};'
            f'font-size:11.5px;">'
            + "".join(cells)
            + f'</div>'
        )

    header_cells = [
        f'<div style="color:{P["text_faint"]};font-size:9px;'
        f'letter-spacing:1.3px;text-transform:uppercase;'
        f'font-weight:700;">Feature</div>'
    ]
    sim_cells = [
        f'<div style="color:{P["text_faint"]};font-size:9px;'
        f'letter-spacing:1.3px;text-transform:uppercase;'
        f'font-weight:700;">Probability</div>'
    ]
    band_cells = [
        f'<div style="color:{P["text_faint"]};font-size:9px;'
        f'letter-spacing:1.3px;text-transform:uppercase;'
        f'font-weight:700;">Band</div>'
    ]
    bond_cells = [
        f'<div style="color:{P["text_faint"]};font-size:9px;'
        f'letter-spacing:1.3px;text-transform:uppercase;'
        f'font-weight:700;">Suggested bond</div>'
    ]
    for s in resolved:
        band_color = P.get(_BAND_COLOR[s.band], P["text_dim"])
        header_cells.append(
            f'<div style="text-align:right;color:{P["text"]};'
            f'font-weight:700;font-size:14px;">'
            f'{html.escape(s.provider_id)}<br>'
            f'<span style="font-size:10px;color:{P["text_faint"]};'
            f'font-weight:400;">'
            f'{html.escape(s.specialty.replace("_", " "))}</span></div>'
        )
        sim_cells.append(
            f'<div style="text-align:right;color:{band_color};'
            f'font-family:\'JetBrains Mono\',monospace;'
            f'font-weight:700;font-size:18px;">'
            f'{s.probability*100:.0f}%</div>'
        )
        band_cells.append(
            f'<div style="text-align:right;">'
            f'{_band_badge(s.band)}</div>'
        )
        bond = s.recommendation.suggested_bond_usd or 0.0
        bond_cells.append(
            f'<div style="text-align:right;color:{P["text"]};'
            f'font-family:\'JetBrains Mono\',monospace;">'
            f'{"$" + format(int(bond), ",") if bond > 0 else "—"}'
            f'{" / " + str(s.recommendation.retention_years) + "y" if s.recommendation.retention_years else ""}'
            f'</div>'
        )

    tpl = 'display:grid;grid-template-columns:220px repeat({n}, 1fr);gap:14px;'
    grid = tpl.format(n=len(resolved))

    return (
        f'<div style="padding:20px 0 16px 0;border-bottom:1px solid '
        f'{P["border"]};margin-bottom:22px;">'
        f'<div class="pa-eyebrow">Compare providers</div>'
        f'<div class="pa-h1">{html.escape(target_name)} · '
        f'{len(resolved)}-way comparison</div>'
        f'<div class="pa-callout">'
        f'<strong style="color:{P["text"]};">How to read: </strong>'
        f'Column per provider. Feature rows highlight the worst '
        f'(highest-value) cell in red. Use this to answer '
        f'"which provider needs the bigger bond" or "which driver '
        f'is actually different between these two?"</div>'
        f'<div style="margin-top:18px;padding:16px 20px;'
        f'background:{P["panel"]};border:1px solid {P["border"]};'
        f'border-radius:4px;">'
        f'<div style="{grid}padding:8px 0;border-bottom:2px solid {P["border"]};">'
        + "".join(header_cells) + "</div>"
        f'<div style="{grid}padding:10px 0;border-bottom:1px solid {P["border"]};">'
        + "".join(sim_cells) + "</div>"
        f'<div style="{grid}padding:8px 0;">'
        + "".join(band_cells) + "</div>"
        f'<div style="{grid}padding:8px 0;border-bottom:2px solid {P["border"]};">'
        + "".join(bond_cells) + "</div>"
        f'<div style="margin-top:10px;">'
        + "".join(rows) + "</div>"
        f'</div>'
        f'<div style="margin-top:14px;">'
        f'<a href="/diligence/physician-attrition" '
        f'style="color:{P["accent"]};font-size:11px;">'
        f'← Back to full roster</a></div>'
        f'</div>'
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
    crosslink = (
        f'<div style="margin-top:14px;padding:10px 14px;'
        f'background:{P["panel_alt"]};border-left:2px solid '
        f'{P["accent"]};border-radius:0 3px 3px 0;font-size:11.5px;'
        f'color:{P["text_dim"]};line-height:1.6;">'
        f'<strong style="color:{P["text"]};">Related: </strong>'
        f'<a href="/diligence/physician-eu" '
        f'style="color:{P["accent"]};text-decoration:none;">'
        f'Physician Economic Units →</a> '
        f'tells you who SHOULD leave (per-provider P&L + loss-maker '
        f'tail). Together with this flight-risk view, the complete '
        f'physician-portfolio optimization picture.'
        f'</div>'
    )

    body = (
        _scoped_styles()
        + '<div class="pa-wrap">'
        + hero_and_bridge
        + crosslink
        + _band_filter_chips(band_filter)
        + (
            f'<div class="pa-section-label">'
            f'High + critical providers · {len(focus_scores)} '
            f'shown · retention action required</div>'
            + cards
            if focus_scores
            else f'<div class="pa-callout good" style="margin-top:16px;">'
                 f'No providers are in the '
                 f'{html.escape((band_filter or "HIGH/CRITICAL").upper())} '
                 f'band. No retention bonds required for the filtered view.</div>'
        )
        + '<div class="pa-section-label">'
          'Full roster · sortable · filterable · CSV export</div>'
        + _roster_table(filtered, providers_by_id)
        + '</div>'
        + bookmark_hint()
    )

    return chartis_shell(
        body, f"Physician Attrition — {target_name}",
        subtitle="Predictive RCM analytic",
    )
