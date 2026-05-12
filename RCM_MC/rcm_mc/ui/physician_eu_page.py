"""Physician Economic Unit page at /diligence/physician-eu.

Ranks every provider by contribution margin, identifies loss-makers
at current comp vs at FMV, and surfaces the "drop these named
providers at close" roster-optimization bridge lever.

The partner-facing output: "Dr. X, Y, Z are net-negative contributors
even at FMV comp. Dropping them at close via retention structure adds
$4.2M/year — 12% EBITDA uplift." Named providers, specific dollar
deltas, direct deal-structure implication.
"""
from __future__ import annotations

import html
from typing import Any, Dict, List, Optional

from ..diligence.physician_eu import (
    EconomicUnitReport, ProviderEconomicUnit, RosterOptimization,
    analyze_roster_eu,
)
from ..diligence.physician_comp.comp_ingester import Provider
from ._chartis_kit import (
    P, chartis_shell, ck_kpi_block, ck_next_section, ck_page_title,
    ck_panel, ck_section_intro, ck_signal_badge,
)
from .power_ui import (
    bookmark_hint, export_json_panel, provenance, sortable_table,
)


def _scoped_styles() -> str:
    css = """
.peu-wrap{{font-family:"Helvetica Neue",Arial,sans-serif;}}
.peu-eyebrow{{font-size:11px;letter-spacing:1.6px;text-transform:uppercase;
color:{tf};font-weight:600;}}
.peu-h1{{font-size:26px;color:{tx};font-weight:600;line-height:1.15;
margin:4px 0 0 0;letter-spacing:-.2px;}}
.peu-callout{{background:{pa};padding:12px 16px;
border-left:3px solid {ac};border-radius:0 3px 3px 0;
font-size:12px;color:{td};line-height:1.65;max-width:880px;margin-top:12px;}}
.peu-callout.alert{{border-left-color:{ne};color:{ne};
font-weight:600;font-size:13px;}}
.peu-callout.warn{{border-left-color:{wn};color:{wn};
font-weight:600;font-size:13px;}}
.peu-callout.good{{border-left-color:{po};color:{po};
font-weight:600;font-size:13px;}}
.peu-section-label{{font-size:10px;letter-spacing:1.6px;text-transform:uppercase;
font-weight:700;color:{tf};margin:22px 0 10px 0;}}
.peu-kpi-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));
gap:14px;margin-top:18px;}}
.peu-kpi{{background:{pn};border:1px solid {bd};border-radius:4px;
padding:14px 16px;}}
.peu-kpi__label{{font-size:9px;letter-spacing:1.4px;text-transform:uppercase;
color:{tf};margin-bottom:6px;font-weight:600;}}
.peu-kpi__val{{font-size:26px;line-height:1;font-family:"JetBrains Mono",monospace;
font-variant-numeric:tabular-nums;font-weight:700;}}
.peu-kpi__band{{font-size:10px;margin-top:4px;font-weight:600;}}
.peu-opt{{background:{pn};border:1px solid {bd};border-radius:4px;
padding:16px 20px;margin-top:18px;position:relative;overflow:hidden;}}
.peu-opt::before{{content:"";position:absolute;top:0;left:0;right:0;
height:2px;background:linear-gradient(90deg,{po},{ac});}}
.peu-candidate{{background:{pa};border-left:3px solid {ne};
padding:10px 14px;margin:6px 0;border-radius:0 3px 3px 0;
font-size:12px;color:{td};line-height:1.6;}}
.peu-candidate__head{{display:flex;justify-content:space-between;
align-items:baseline;gap:10px;flex-wrap:wrap;}}
.peu-candidate__id{{color:{tx};font-weight:600;font-size:13px;}}
.peu-candidate__spec{{color:{tf};font-size:10px;letter-spacing:1.1px;
text-transform:uppercase;}}
.peu-candidate__contrib{{font-family:"JetBrains Mono",monospace;
font-variant-numeric:tabular-nums;color:{ne};font-weight:700;}}
""".format(
        tx=P["text"], td=P["text_dim"], tf=P["text_faint"],
        pn=P["panel"], pa=P["panel_alt"],
        bd=P["border"], ac=P["accent"],
        po=P["positive"], wn=P["warning"], ne=P["negative"],
    )
    return f"<style>{css}</style>"


def _demo_roster() -> List[Provider]:
    """An 8-provider demo roster with a mix of high contributors,
    average contributors, and structural loss-makers — the kind of
    roster a physician-group deal actually presents."""
    return [
        Provider(provider_id="P001", specialty="ORTHOPEDIC_SURGERY",
                 employment_status="PARTNER",
                 base_salary_usd=550_000,
                 productivity_bonus_usd=250_000,
                 wrvus_annual=7500,
                 collections_annual_usd=2_500_000),
        Provider(provider_id="P002", specialty="CARDIOLOGY",
                 employment_status="PARTNER",
                 base_salary_usd=600_000,
                 productivity_bonus_usd=300_000,
                 wrvus_annual=10_000,
                 collections_annual_usd=3_200_000),
        Provider(provider_id="P003", specialty="ANESTHESIOLOGY",
                 employment_status="W2",
                 base_salary_usd=480_000,
                 wrvus_annual=6500,
                 collections_annual_usd=1_700_000),
        Provider(provider_id="P004", specialty="EMERGENCY_MEDICINE",
                 employment_status="W2",
                 base_salary_usd=420_000,
                 wrvus_annual=8000,
                 collections_annual_usd=1_500_000),
        Provider(provider_id="P005", specialty="UROLOGY",
                 employment_status="W2",
                 base_salary_usd=500_000,
                 productivity_bonus_usd=200_000,
                 wrvus_annual=7000,
                 collections_annual_usd=2_100_000),
        # Structural loss-maker — overpaid for collections
        Provider(provider_id="P006", specialty="FAMILY_MEDICINE",
                 employment_status="W2",
                 base_salary_usd=450_000,
                 wrvus_annual=4500,
                 collections_annual_usd=500_000),
        # Loss-maker even at FMV
        Provider(provider_id="P007", specialty="PEDIATRICS",
                 employment_status="W2",
                 base_salary_usd=380_000,
                 wrvus_annual=3800,
                 collections_annual_usd=350_000),
        Provider(provider_id="P008", specialty="INTERNAL_MEDICINE",
                 employment_status="W2",
                 base_salary_usd=290_000,
                 wrvus_annual=5200,
                 collections_annual_usd=900_000),
    ]


def _hero(
    report: EconomicUnitReport, target_name: str,
) -> str:
    # Headline numbers
    total_coll = report.total_collections_usd
    total_comp = report.total_comp_usd
    total_ohd = report.total_overhead_usd
    total_contrib = report.total_contribution_usd
    margin = report.aggregate_contribution_margin_pct

    margin_color = (
        P["positive"] if margin >= 0.35
        else P["warning"] if margin >= 0.15
        else P["negative"]
    )

    # Partner-speak banner keyed off optimization outcome.
    opt = report.optimization
    if opt and opt.candidates:
        banner_class = "alert"
        banner = (
            f"⚠ {len(opt.candidates)} provider"
            f"{'s' if len(opt.candidates) != 1 else ''} "
            f"are net-negative contributors even at FMV comp. "
            f"Dropping them at close via retention structure adds "
            f"${opt.ebitda_uplift_usd:,.0f} annual EBITDA — "
            f"{opt.ebitda_uplift_pct_of_roster*100:.1f}% lift on "
            f"baseline. Quote this in the bid."
        )
    elif report.loss_makers_at_current_comp > 0:
        banner_class = "warn"
        banner = (
            f"{report.loss_makers_at_current_comp} provider"
            f"{'s' if report.loss_makers_at_current_comp != 1 else ''} "
            f"currently loss-making at observed comp, but all "
            f"become profitable when comp is restructured to FMV "
            f"p50. Action: restructure comp via earn-out, don't "
            f"drop the providers."
        )
    elif margin >= 0.35:
        banner_class = "good"
        banner = (
            f"Roster contribution margin ({margin*100:.1f}%) is at "
            f"or above the physician-group peer norm (30-40%). "
            f"No structural comp restructure needed; no drop "
            f"candidates. Revenue concentration in the top-10% "
            f"of providers is {report.top_decile_contribution_share*100:.0f}% "
            f"of positive contribution."
        )
    else:
        banner_class = "warn"
        banner = (
            f"Aggregate contribution margin ({margin*100:.1f}%) is "
            f"below the physician-group peer norm (30-40%). "
            f"Investigate overhead allocation assumption + tail "
            f"providers before signaling a drop."
        )

    summary = (
        f"Per-provider P&L computed across {report.roster_size} providers. "
        f"Collections ${total_coll:,.0f} minus comp ${total_comp:,.0f} "
        f"minus overhead ${total_ohd:,.0f} (allocated "
        f"{report.overhead_method.replace('_', ' ')} at "
        f"{report.overhead_pct*100:.0f}% of revenue) = aggregate "
        f"contribution ${total_contrib:,.0f} ({margin*100:.1f}% margin). "
        f"Rankings in the roster table below; drop candidates highlighted "
        f"in the Roster Optimization block."
    )

    coll_num = provenance(
        f'${total_coll/1e6:,.1f}M',
        source="sum(provider.collections_annual_usd)",
        formula="SUM(collections_annual_usd) over roster",
        detail=(
            "CCD-derived collections when available; caller-"
            "supplied otherwise. Directly comparable to HCRIS "
            "total operating revenue."
        ),
    )
    comp_num = provenance(
        f'${total_comp/1e6:,.1f}M',
        source="sum(provider.total_comp_usd)",
        formula=(
            "SUM(base + productivity_bonus + stipend + "
            "call_coverage + admin) over roster"
        ),
        detail=(
            "Gross comp — includes all directed comp that "
            "flows from arrangements."
        ),
    )
    contrib_num = provenance(
        f'${total_contrib/1e6:,.1f}M',
        source="sum(contribution_usd)",
        formula=(
            "SUM(collections - comp - allocated_overhead) per provider"
        ),
        detail=(
            "Aggregate contribution margin. This is the roster's "
            "pre-shared-services EBITDA contribution."
        ),
    )
    margin_num = provenance(
        f'{margin*100:.1f}%',
        source="total_contribution / total_collections",
        formula="aggregate_contribution / aggregate_collections",
        detail=(
            "Physician-group peer norm is 30-40%. Below 15% "
            "suggests structural overpay on the tail."
        ),
    )

    kpi_row = (
        '<div class="ck-kpi-strip">'
        + ck_kpi_block(
            "Roster collections", coll_num,
            sub=f"{report.roster_size} providers · sum annual",
            help={
                "definition": (
                    "Sum of annual professional collections across "
                    "the roster. The denominator for contribution "
                    "margin and the comp-to-revenue ratio."
                ),
            },
        )
        + ck_kpi_block(
            "Total comp", comp_num,
            sub=f"{total_comp/total_coll*100 if total_coll > 0 else 0:.1f}% of revenue",
            help={
                "definition": (
                    "Sum of physician compensation (base + RVU + "
                    "bonus). Peer-norm comp-to-revenue runs 45-55% "
                    "for hospital-based specialties; >60% signals "
                    "under-leveraged practice economics."
                ),
            },
        )
        + ck_kpi_block(
            "Aggregate contribution", contrib_num,
            sub=f"{margin_num} margin · peer norm 30-40%",
            help={
                "definition": (
                    "Collections minus comp minus practice expenses "
                    "= contribution to facility/management. Peer "
                    "norm 30-40%; below 20% the practice is on the "
                    "edge of subsidising its own roster."
                ),
            },
        )
        + ck_kpi_block(
            "Loss-makers", f"{report.loss_makers_at_current_comp}",
            sub=f"observed · {report.loss_makers_at_fmv_comp} @ FMV",
            help={
                "definition": (
                    "Count of providers whose comp exceeds their "
                    "personal collections — they cost the practice "
                    "money. The 'at FMV' column shows how many "
                    "would still be loss-makers if comp were "
                    "renegotiated to fair-market-value benchmark."
                ),
            },
        )
        + '</div>'
    )

    intro = ck_section_intro(
        eyebrow="PHYSICIAN ECONOMIC UNITS",
        headline=f"{html.escape(target_name)} — per-provider P&L.",
        italic_word="per-provider",
        body=(
            f"{html.escape(banner)} "
            f"Overhead allocation: {report.overhead_method.replace('_', ' ')} "
            f"at {report.overhead_pct*100:.0f}% of revenue."
        ),
    )
    explainer = ck_panel(
        f'<p class="ck-section-body"><strong>What this shows:</strong> {summary}</p>',
        title="Methodology",
    )
    return f'{intro}{explainer}{kpi_row}'


def _optimization_block(opt: RosterOptimization) -> str:
    """The partner-action block — which providers to drop + $."""
    if not opt.candidates:
        return ck_panel(
            '<p class="ck-section-body">'
            '<strong>No drop candidates.</strong> All providers '
            'generate positive contribution when comp is restructured '
            'to specialty p50 FMV. No roster-level optimization '
            'action required — restructure over-paid providers via '
            'earn-out; keep the roster intact.</p>',
            title="Roster Optimization",
        )

    conf_tone = {
        "HIGH": "positive", "MEDIUM": "warning", "LOW": "negative",
    }.get(opt.confidence, "neutral")
    conf_badge = ck_signal_badge(html.escape(opt.confidence), tone=conf_tone)

    candidate_rows = []
    for c in opt.candidates:
        fmv_text = (
            f'FMV p50 ${c.fmv_p50_comp_usd:,.0f}'
            if c.fmv_p50_comp_usd else "no FMV benchmark"
        )
        candidate_rows.append(
            f'<div class="peu-candidate">'
            f'<div class="peu-candidate__head">'
            f'<span class="peu-candidate__id">'
            f'{html.escape(c.provider_id)}</span>'
            f'<span class="peu-candidate__spec">'
            f'{html.escape(c.specialty.replace("_", " "))} · '
            f'{html.escape(c.employment_status)}</span>'
            f'<span class="peu-candidate__contrib">'
            f'contribution ${c.contribution_usd:,.0f} @ current · '
            f'${c.fmv_neutral_contribution_usd or 0:,.0f} @ FMV</span>'
            f'</div>'
            '<p class="ck-section-body">'
            f'Collections ${c.collections_annual_usd:,.0f} · '
            f'comp ${c.total_comp_usd:,.0f} ({html.escape(fmv_text)}) · '
            f'overhead ${c.allocated_overhead_usd:,.0f}. '
            'Negative contribution persists even when comp is cut to '
            'specialty FMV — structurally uneconomic at any comp.'
            '</p>'
            f'</div>'
        )

    inner = (
        '<p class="ck-section-body">'
        '<strong>Drop named loss-makers at close.</strong></p>'
        '<div class="ck-kpi-strip">'
        + ck_kpi_block(
            "EBITDA uplift", f"${opt.ebitda_uplift_usd:,.0f}",
            sub=f"{opt.ebitda_uplift_pct_of_roster*100:.1f}% of roster baseline",
        )
        + ck_kpi_block(
            "Drop candidates", f"{len(opt.candidates)}",
            sub="structurally uneconomic @ FMV",
        )
        + ck_kpi_block(
            "Revenue forgone", f"${opt.total_revenue_forgone_usd:,.0f}",
            sub="collections lost at drop",
        )
        + ck_kpi_block(
            "Confidence", conf_badge,
            sub="realization likelihood",
        )
        + '</div>'
        + "".join(candidate_rows)
        + '<p class="ck-section-body">'
        '<strong>How to use: </strong>'
        'Quote the EBITDA uplift as an offer-shape modification in '
        'the bid ("our bid includes a 2-year retention structure '
        f'that drops {len(opt.candidates)} named underperformers for '
        f'a ${opt.ebitda_uplift_usd/1e6:,.1f}M EBITDA lift"). Combined '
        "with PPAM (who's likely to leave), this is the complete "
        'physician-portfolio optimization view.</p>'
    )
    return ck_panel(
        inner, title="Roster Optimization · EBITDA uplift lever",
    )


def _roster_table(report: EconomicUnitReport) -> str:
    headers = [
        "Rank", "Provider", "Specialty", "Employment",
        "Collections", "Comp", "Overhead", "Contribution",
        "Margin", "FMV contrib",
    ]
    rows: List[List[str]] = []
    keys: List[List[Any]] = []
    for u in report.units:
        if u.is_loss_maker_at_fmv:
            contrib_color = P["negative"]
            margin_color = P["negative"]
        elif u.is_loss_maker_observed:
            contrib_color = P["warning"]
            margin_color = P["warning"]
        elif u.contribution_margin_pct >= 0.40:
            contrib_color = P["positive"]
            margin_color = P["positive"]
        else:
            contrib_color = P["text"]
            margin_color = P["text"]
        contrib_html = (
            f'<span style="color:{contrib_color};'
            f'font-weight:600;">${u.contribution_usd:,.0f}</span>'
        )
        margin_html = (
            f'<span style="color:{margin_color};">'
            f'{u.contribution_margin_pct*100:+.1f}%</span>'
        )
        fmv_html = (
            f'${u.fmv_neutral_contribution_usd:,.0f}'
            if u.fmv_neutral_contribution_usd is not None else "—"
        )
        rows.append([
            str(u.contribution_rank),
            u.provider_id,
            u.specialty.replace("_", " "),
            u.employment_status,
            f'${u.collections_annual_usd:,.0f}',
            f'${u.total_comp_usd:,.0f}',
            f'${u.allocated_overhead_usd:,.0f}',
            contrib_html,
            margin_html,
            fmv_html,
        ])
        keys.append([
            u.contribution_rank, u.provider_id, u.specialty,
            u.employment_status,
            u.collections_annual_usd, u.total_comp_usd,
            u.allocated_overhead_usd, u.contribution_usd,
            u.contribution_margin_pct,
            u.fmv_neutral_contribution_usd or 0,
        ])
    return sortable_table(
        headers, rows, name="physician_eu_roster", sort_keys=keys,
    )


def render_physician_eu_page(
    qs: Optional[Dict[str, List[str]]] = None,
) -> str:
    qs = qs or {}
    target_name = (qs.get("target_name") or ["Target Physician Group"])[0]
    overhead_pct_raw = (qs.get("overhead_pct") or [""])[0]
    try:
        overhead_pct = (
            float(overhead_pct_raw) if overhead_pct_raw else 0.23
        )
    except ValueError:
        overhead_pct = 0.23
    overhead_method = (
        qs.get("overhead_method") or ["revenue_weighted"]
    )[0]
    if overhead_method not in (
        "revenue_weighted", "equal_share", "wrvu_weighted",
    ):
        overhead_method = "revenue_weighted"

    roster = _demo_roster()
    report = analyze_roster_eu(
        roster,
        overhead_pct=overhead_pct,
        overhead_method=overhead_method,
    )

    hero_and_opt = export_json_panel(
        _hero(report, target_name) + _optimization_block(
            report.optimization
            or __import__(
                "rcm_mc.diligence.physician_eu", fromlist=["RosterOptimization"],
            ).RosterOptimization()
        ),
        payload=report.to_dict(),
        name="physician_eu_report",
    )

    # Cross-link to PPAM (flight risk) and physician comp panel
    crosslink = ck_panel(
        '<p class="ck-section-body">'
        '<strong>Related analytics: </strong>'
        '<a href="/diligence/physician-attrition" class="ck-link">'
        'Physician Attrition (PPAM) →</a> '
        "tells you who's LIKELY to leave. This page tells you who "
        'SHOULD leave. Together they form the complete physician-'
        'portfolio optimization view.</p>',
        title="Cross-reference",
    )

    title = ck_page_title(
        "Provider Economics",
        eyebrow="RCM DILIGENCE",
        meta=f"Target: {target_name} · per-provider P&L",
    )
    body = (
        _scoped_styles()
        + title
        + '<div class="peu-wrap">'
        + hero_and_opt
        + crosslink
        + ck_panel(
            _roster_table(report),
            title="Full roster · ranked by contribution · sortable + CSV export",
        )
        + '</div>'
        + bookmark_hint()
        + ck_next_section(
            "Pressure-test attrition risk",
            "/diligence/physician-attrition",
            eyebrow="Continue —",
            italic_word="attrition",
        )
    )
    return chartis_shell(
        body,
        f"Physician Economic Units — {target_name}",
        active_nav="/diligence/physician-eu",
        subtitle="Per-provider P&L · bridge-lever analytic",
    )
