"""IFT demand deep-dive page (``/ift-demand``).

National → regional → subcounty demand, trailed over time. Renders the CMS HCPCS
code analysis (BLS / ALS / SCT × emergency), the emergency-vs-non-emergency
prevalence, the demographic + facility base, the time series, the regional
roll-up, and MMT's exact operating counties + customer concentration + growth.

Reads :mod:`ift_demand` (which reuses the sized estate) plus :mod:`ift_mmt` for
the granular county layer. Renders through ``chartis_shell`` + ``ck_*``; degrades
to honest notes and never raises.

Public API:
    render_ift_demand(qs=None) -> str
"""
from __future__ import annotations

import html as _html
from typing import Dict, List, Optional

from ._chartis_kit import (
    chartis_shell, ck_next_section, ck_page_actions, ck_page_title, ck_panel,
    ck_section_header, ck_section_intro,
)
from ._chart_kit import ck_bar_chart, ck_chart_assets, ck_chart_grid, ck_hbar_chart
from ..market_reports import ift_demand as _dm


def _esc(x: object) -> str:
    return _html.escape(str(x if x is not None else ""))


_BASIS_TITLES = {
    "GOV": "A published government figure (CMS, MedPAC, Census, HCRIS).",
    "SOURCED": "Computed from our vendored CMS estate.",
    "ILLUSTRATIVE": "Modeled — the basis is named, not a filed figure.",
    "FRAMEWORK": "An analytic classification, not a figure.",
    "ACADEMIC": "A published study / analyst estimate.",
}
_BASIS_CLASS = {"GOV": "gov", "SOURCED": "sourced", "ILLUSTRATIVE": "illustrative",
                "FRAMEWORK": "framework", "ACADEMIC": "academic"}


def _chip(basis: str) -> str:
    b = (basis or "ILLUSTRATIVE").upper()
    key = b if b in _BASIS_TITLES else "ILLUSTRATIVE"
    return (f'<span class="ifd-chip ifd-chip-{_BASIS_CLASS[key]}" '
            f'title="{_esc(_BASIS_TITLES[key])}">{key}</span>')


def _num(x, dash="—") -> str:
    try:
        return f"{int(round(float(x))):,}"
    except (TypeError, ValueError):
        return dash


def _usd_m(x) -> str:
    try:
        return f"${float(x) / 1e6:,.1f}M"
    except (TypeError, ValueError):
        return "—"


def _pct(x) -> str:
    try:
        return f"{float(x):.1f}%"
    except (TypeError, ValueError):
        return "—"


def _kpi(label, value, sub) -> str:
    return ('<div class="ifd-kpi">'
            f'<div class="ifd-kpi-l">{_esc(label)}</div>'
            f'<div class="ifd-kpi-v">{value}</div>'
            f'<div class="ifd-kpi-s">{_esc(sub)}</div></div>')


def _table(headers, rows, *, hi_col=None) -> str:
    def _hcls(i):
        return ' class="ifd-hi"' if hi_col is not None and i == hi_col else ""
    head = "".join(f'<th{_hcls(i)}>{_esc(h)}</th>' for i, h in enumerate(headers))
    body = "".join(
        "<tr>" + "".join(f'<td{_hcls(i)}>{_esc(v)}</td>' for i, v in enumerate(r))
        + "</tr>" for r in rows)
    return ('<div class="ifd-wrap"><table class="ifd-tab"><thead><tr>'
            f'{head}</tr></thead><tbody>{body}</tbody></table></div>')


_STYLES = """<style>
.ifd-chip{display:inline-block;font-family:var(--sc-mono,Consolas,monospace);
font-size:9px;font-weight:600;letter-spacing:.06em;padding:1px 6px;border-radius:2px;
vertical-align:middle;margin:0 1px;}
.ifd-chip-gov{background:#e7efe9;color:#154e36;}
.ifd-chip-sourced{background:#e9eef5;color:#243b57;}
.ifd-chip-illustrative{background:#f3ecd9;color:#7a5c1a;}
.ifd-chip-framework{background:#ece9f2;color:#463a63;}
.ifd-chip-academic{background:#efeae0;color:#6b5426;}
.ifd-prose{font-family:var(--sc-serif,Georgia,serif);font-size:14px;line-height:1.62;
color:var(--sc-text,#1a2332);max-width:92ch;margin:0 0 10px;}
.ifd-sub{font-family:var(--sc-mono,Consolas,monospace);font-size:11px;font-weight:600;
letter-spacing:.06em;text-transform:uppercase;color:var(--sc-teal,#155752);margin:14px 0 6px;}
.ifd-src{font-family:var(--sc-mono,Consolas,monospace);font-size:10px;
color:var(--sc-muted,#6b6357);margin:6px 0 2px;line-height:1.5;}
.ifd-kpi-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));
gap:12px;margin:10px 0 6px;}
.ifd-kpi{background:#fff;border:1px solid var(--sc-border,#e4dccb);border-radius:4px;
padding:11px 13px;}
.ifd-kpi-l{font-family:var(--sc-sans,Inter,system-ui,sans-serif);font-size:10px;
font-weight:600;letter-spacing:.05em;text-transform:uppercase;
color:var(--sc-muted,#6b6357);margin-bottom:4px;}
.ifd-kpi-v{font-family:var(--sc-mono,Consolas,monospace);font-size:19px;font-weight:700;
color:var(--sc-navy,#0b2341);font-variant-numeric:tabular-nums;line-height:1.15;}
.ifd-kpi-s{font-size:10.5px;color:var(--sc-muted,#6b6357);margin-top:3px;}
.ifd-wrap{overflow-x:auto;margin:5px 0 10px;}
.ifd-tab{border-collapse:collapse;width:100%;font-size:12px;
font-family:var(--sc-sans,Inter,system-ui,sans-serif);}
.ifd-tab th,.ifd-tab td{border:1px solid var(--sc-border,#e4dccb);padding:6px 9px;
text-align:left;vertical-align:top;line-height:1.42;}
.ifd-tab thead th{background:var(--sc-navy,#0b2341);color:#fff;font-weight:600;
font-size:10.5px;position:sticky;top:0;}
.ifd-tab tbody tr:nth-child(even){background:var(--sc-surface,#faf7f1);}
.ifd-tab td.ifd-hi,.ifd-tab th.ifd-hi{background:#eef5f1;}
.ifd-tab thead th.ifd-hi{background:#12463a;}
.ifd-num{font-variant-numeric:tabular-nums;font-family:var(--sc-mono,Consolas,monospace);}
.ifd-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));
gap:12px;margin:6px 0 12px;}
.ifd-card{border:1px solid var(--sc-border,#e4dccb);border-left:3px solid
var(--sc-teal,#155752);border-radius:4px;padding:11px 13px;
background:var(--sc-surface,#faf7f1);}
.ifd-card h4{font-family:var(--sc-serif,Georgia,serif);font-size:14px;margin:0 0 4px;}
.ifd-card p{font-family:var(--sc-serif,Georgia,serif);font-size:12.5px;line-height:1.5;
margin:0 0 5px;color:var(--sc-text,#2a3340);}
.ifd-links{display:flex;flex-wrap:wrap;gap:14px;margin:14px 0 4px;
font-family:var(--sc-mono,Consolas,monospace);font-size:11px;font-weight:600;}
.ifd-links a{color:var(--sc-teal,#155752);text-decoration:none;}
.ifd-ts{border-left:3px solid var(--sc-navy,#0b2341);padding:8px 0 8px 12px;
margin:8px 0;background:rgba(11,35,65,0.03);}
.ifd-ts-h{font-family:var(--sc-mono,Consolas,monospace);font-size:11px;font-weight:700;
color:var(--sc-navy,#0b2341);margin:0 0 3px;}
.ifd-ts-p{font-family:var(--sc-mono,Consolas,monospace);font-size:12px;
color:var(--sc-text,#2a3340);margin:0;}
</style>"""


def _crosslinks() -> str:
    return (
        '<div class="ifd-links">'
        '<a href="/ift-hs-demand">Health-system demand sizing (HCRIS) &rarr;</a>'
        '<a href="/ift-clinical">Clinical demand engine &rarr;</a>'
        '<a href="/ift-mmt">MMT county deep-dive &rarr;</a>'
        '<a href="/ift-markets">Geographic markets / TAM-SAM-SOM &rarr;</a>'
        '<a href="/ift-sourcing">Sourcing prompts &rarr;</a>'
        '<a href="/ift-diligence">Diligence question architecture &rarr;</a>'
        '<a href="/connector-estate">Live data-connector estate &rarr;</a>'
        '</div>')


# ── National frame ───────────────────────────────────────────────────────────
def _national_section(nf) -> str:
    if not (nf and nf.available):
        return ""
    kpis = (
        '<div class="ifd-kpi-grid">'
        + _kpi("US ground-IFT TAM", f'{nf.tam_central_bn:.1f}B {_chip("ILLUSTRATIVE")}',
               "central, all-payer, ex-NEMT ex-air")
        + _kpi("IFT legs / yr", f"{nf.ift_legs_low_m:.0f}-{nf.ift_legs_high_m:.0f}M",
               "all-payer ground interfacility")
        + _kpi("US hospitals (origins)", _num(nf.n_hospitals_national),
               f'{_chip("SOURCED")} the IFT origin universe')
        + _kpi("Post-acute destinations", _num(nf.postacute_destinations),
               f'{_chip("SOURCED")} SNF/IRF/LTACH/hospice/HHA')
        + _kpi("Volume growth", _pct(nf.volume_growth_pct),
               "aging + acuity (the demand engine)")
        + _kpi("Organic market growth", _pct(nf.market_growth_pct),
               "price × volume")
        + '</div>')
    bands = "".join(
        f'<div class="ifd-card"><h4>{_esc(b)}</h4><p>{_esc(read)}</p></div>'
        for b, read in nf.age_bands)
    return (
        ck_section_header("National frame — the demand base & its growth",
                          eyebrow="STEP 1 · NATIONAL")
        + ck_panel(
            '<p class="ifd-prose">The national demand base: the origin/destination '
            'facility universe, the sized TAM and leg volume, and the demographic '
            'engine underneath the growth. IFT demand is aging-driven — the 75-84 '
            'band crossing in this decade is the inflection.</p>'
            + kpis
            + '<p class="ifd-sub">The demographic engine — age bands ' + _chip("GOV")
            + ' ' + _chip("ILLUSTRATIVE") + '</p>'
            + f'<div class="ifd-grid">{bands}</div>'
            + f'<p class="ifd-src">Source: {_esc(nf.source_label)}</p>'))


# ── CMS HCPCS code analysis ──────────────────────────────────────────────────
def _hcpcs_section(hc) -> str:
    if not (hc and hc.available):
        return ""
    rows = [(r.hcpcs, r.descriptor, r.acuity_group, r.emergency, f"{r.rvu:.2f}",
             r.ift_relevance) for r in hc.rows]
    type_cards = "".join(
        f'<div class="ifd-card"><h4>{_esc(t.acuity_type)} — RVU '
        f'{t.rvu_low:.2f}–{t.rvu_high:.2f} <span style="font-family:var(--sc-mono);'
        f'font-size:10px;color:var(--sc-muted,#6b6357);">'
        f'{_esc(", ".join(t.codes))}</span></h4><p>{_esc(t.read)}</p></div>'
        for t in hc.types)
    return (
        ck_section_header("CMS code analysis — BLS / ALS / SCT × emergency",
                          eyebrow="STEP 2 · THE CODES")
        + ck_panel(
            '<p class="ifd-prose">The ground ambulance base HCPCS, mapped to the '
            'three interfacility acuity types (<strong>BLS / ALS / SCT</strong>) '
            'and the <strong>emergency vs non-emergency</strong> split. The RVU '
            'column (42 CFR 414.610) is the spend lever; the relevance column is '
            'where each code sits in the IFT book.</p>'
            '<p class="ifd-sub">The three IFT acuity types</p>'
            + f'<div class="ifd-grid">{type_cards}</div>'
            '<p class="ifd-sub">Every base code, classified</p>'
            + _table(("HCPCS", "Descriptor", "Type", "Emergency?", "RVU",
                      "Interfacility relevance"), rows, hi_col=2)
            + f'<p class="ifd-prose">{_chip("FRAMEWORK")} {_esc(hc.note)}</p>'
            + f'<p class="ifd-src">Source: {_esc(hc.source_label)}</p>'))


# ── Emergency vs non-emergency prevalence ────────────────────────────────────
def _prevalence_section(ep) -> str:
    if not (ep and ep.available):
        return ""
    fam_rows = [(k, _num(v)) for k, v in ep.by_family.items()]
    tt_rows = [(k, _num(v)) for k, v in ep.by_transfer_type.items()]
    kpis = (
        '<div class="ifd-kpi-grid">'
        + _kpi("Emergent scenarios", _num(ep.n_emergent_scenarios),
               "escalation / up-transfer (by count)")
        + _kpi("Non-emergent scenarios", _num(ep.n_nonemergent_scenarios),
               "step-down + direct-admit + down/lateral")
        + _kpi("CCT/SCT (by volume)", _pct((ep.cct_sct_share or 0) * 100),
               "the high-acuity escalation weight")
        + _kpi("High-acuity incl. behavioral", _pct((ep.high_acuity_share or 0) * 100),
               "of the escalation book, volume-weighted")
        + '</div>')
    return (
        ck_section_header("Emergency vs non-emergency — the prevalence read",
                          eyebrow="STEP 3 · EMERGENCY / NON-EMERGENCY")
        + ck_panel(
            '<p class="ifd-prose">Two lenses that point opposite ways — the key '
            'nuance. By clinical SCENARIO the registry skews to emergent '
            'escalation up-transfers; by VOLUME the engine is the non-emergency '
            'post-acute discharge book that ages in.</p>'
            + kpis
            + '<p class="ifd-sub">Registry by family &amp; transfer type '
            + _chip("SOURCED") + '</p>'
            '<div class="ifd-grid">'
            '<div>' + _table(("Family", "Scenarios"), fam_rows) + '</div>'
            '<div>' + _table(("Transfer type", "Scenarios"), tt_rows) + '</div>'
            '</div>'
            + f'<p class="ifd-prose">{_esc(ep.note)}</p>'
            + f'<p class="ifd-src">Source: {_esc(ep.source_label)}</p>'))


# ── Time series ──────────────────────────────────────────────────────────────
def _timeseries_section(ts) -> str:
    if not (ts and ts.available):
        return ""
    blocks = []
    for s in ts.series:
        pts = " · ".join(f"{p.label} {p.value:g}{s.unit}" for p in s.points)
        blocks.append(
            f'<div class="ifd-ts"><p class="ifd-ts-h">{_esc(s.title)} '
            f'{_chip(s.basis)} <span style="font-weight:400;color:var(--sc-muted,'
            f'#6b6357);">({_esc(s.window)})</span></p>'
            f'<p class="ifd-ts-p">{_esc(pts)}</p>'
            f'<p class="ifd-src">{_esc(s.note)}</p></div>')
    return (
        ck_section_header("Trailed over time — the three windows",
                          eyebrow="STEP 4 · OVER TIME")
        + ck_panel(
            '<p class="ifd-prose">Demand trailed across the series we hold: the '
            'backward HCRIS occupancy panel, the GOV price (AIF) series, and the '
            'forward MMT growth projection. Different windows, stitched — read each '
            'on its own basis.</p>'
            + "".join(blocks)
            + f'<p class="ifd-src">Source: {_esc(ts.source_label)}</p>'))


# ── Regional roll-up ─────────────────────────────────────────────────────────
def _regional_section(regions) -> str:
    if not regions:
        return ""
    rows = [(r.region_label, _num(r.n_metros), _num(r.n_hospitals),
             _num(r.hcris_beds), _num(r.n_snf), _num(r.snf_beds),
             _num(r.n_postacute_destinations), _num(r.n_dialysis),
             _usd_m(r.sam_dollars)) for r in regions]
    return (
        ck_section_header("Regional breakdown — facilities, demand & growth",
                          eyebrow="STEP 5 · BY REGION", count=len(regions))
        + ck_panel(
            '<p class="ifd-prose">The SOURCED facility base rolled up to each '
            'region — hospitals (IFT origins), beds, and post-acute destinations '
            '(the discharge demand) — with the ILLUSTRATIVE per-region demand-$ '
            '(SAM) as the sizing proxy. Every region shares the same aging demand '
            'tailwind; the density and post-acute depth is what varies.</p>'
            + _table(("Region", "Metros", "Hospitals", "HCRIS beds", "SNFs",
                      "SNF beds", "Post-acute nodes", "Dialysis", "Demand $ (SAM)"),
                     rows)
            + f'<p class="ifd-src">Facility counts {_chip("SOURCED")} (our vendored '
            f'CMS estate); per-region demand $ {_chip("ILLUSTRATIVE")} '
            '(SOURCED structure × labelled levers).</p>'))


# ── MMT granular (subcounty + customers + growth) ────────────────────────────
def _mmt_section() -> str:
    try:
        from ..market_reports import ift_mmt as _mmt
        fs = _mmt.footprint_summary()
        cbsas = _mmt.footprint_cbsas()
        accounts = _mmt.mmt_anchor_accounts()
        gp = _mmt.mmt_growth_projection(horizon=5)
        opp = _mmt.mmt_county_opportunity()
    except Exception:  # noqa: BLE001
        return ""
    if not cbsas:
        return ""
    kpis = (
        '<div class="ifd-kpi-grid">'
        + _kpi("Counties", _num(fs.n_county),
               f"{_num(fs.n_cbsa)} CBSAs across {_num(fs.n_states)} states")
        + _kpi("Footprint population", _num(fs.pop_2020),
               f'{_chip("GOV")} 2020 Census')
        + _kpi("65+ population", _num(fs.pop_65_plus),
               f"{_pct(fs.senior_share * 100)} senior share")
        + _kpi("Modeled demand", _num(fs.demand_missions) + " legs/yr",
               f'{_usd_m(fs.demand_dollars)} {_chip("ILLUSTRATIVE")}')
        + '</div>')
    # CBSA / subcounty demand table
    cbsa_rows = []
    for b in cbsas:
        cbsa_rows.append((f"{b.name} ({b.kind})", b.metro, _num(len(b.counties)),
                          _num(b.pop_2020), _num(b.pop_65_plus),
                          _num(b.demand_missions), _usd_m(b.demand_dollars)))
    # county detail (subcounty)
    county_rows = []
    for b in cbsas:
        for c in b.counties:
            cd = _mmt.county_demand(c)
            county_rows.append((c.name + ", " + c.state, c.cbsa_name, c.role,
                                _num(c.pop_2020), _num(c.pop_65_plus),
                                _num(cd.demand_missions)))
    # customer concentration (anchor accounts)
    acct_cards = "".join(
        f'<div class="ifd-card"><h4>{_esc(a.system)} '
        f'<span style="font-family:var(--sc-mono);font-size:10px;'
        f'color:var(--sc-muted,#6b6357);">{_esc(a.tier)}</span></h4>'
        f'<p><strong>Metros.</strong> {_esc(", ".join(a.metros))}</p>'
        f'<p><strong>Strategy.</strong> {_esc(a.mmt_strategy)}</p>'
        f'<p><strong>Risk.</strong> {_esc(a.risk)}</p></div>'
        for a in accounts)
    growth = ""
    if gp and getattr(gp, "available", False):
        growth = (
            '<p class="ifd-sub">Growth — SOM projected over 5 years '
            + _chip("ILLUSTRATIVE") + '</p>'
            f'<p class="ifd-prose">{_esc(gp.headline)}</p>')
    opp_rows = []
    for o in (opp or [])[:10]:
        opp_rows.append((
            _esc(getattr(o, "county", getattr(o, "name", ""))),
            _esc(getattr(o, "metro", "")),
            _num(getattr(o, "score", getattr(o, "opportunity_score", 0)))))
    opp_block = ""
    if opp_rows:
        opp_block = (
            '<p class="ifd-sub">County opportunity ranking (top 10)</p>'
            + _table(("County", "Metro", "Score"),
                     [(a, b, c) for a, b, c in opp_rows]))
    return (
        ck_section_header("MMT granular — exact counties, customers & growth",
                          eyebrow="STEP 6 · WHERE THEY OPERATE")
        + ck_panel(
            '<p class="ifd-prose">Down to the operator\'s real footprint — the '
            'seven CBSAs and their counties, the modeled demand by subcounty, '
            'where the anchor customers concentrate, and the growth on the current '
            'book.</p>'
            + kpis
            + '<p class="ifd-sub">Demand by CBSA</p>'
            + _table(("CBSA", "Metro", "Counties", "Population", "65+",
                      "Demand (legs/yr)", "Demand $"), cbsa_rows)
            + '<p class="ifd-sub">Demand by subcounty (all 22 counties)</p>'
            + _table(("County", "CBSA", "Role", "Population", "65+",
                      "Demand (legs/yr)"), county_rows)
            + '<p class="ifd-sub">Where customers concentrate — anchor accounts '
            + _chip("ACADEMIC") + '</p>'
            + f'<div class="ifd-grid">{acct_cards}</div>'
            + growth + opp_block
            + f'<p class="ifd-src">Population {_chip("GOV")} (2020 Census); demand '
            f'{_chip("ILLUSTRATIVE")} (age-split per-capita rates); accounts '
            'public/company-web, labelled.</p>'))


# ── Charts ───────────────────────────────────────────────────────────────────
def _charts(regions, hc, ts) -> str:
    cards: List[str] = []
    try:
        if regions:
            items = [(r.region_label, r.sam_dollars / 1e6, "teal") for r in regions]
            cards.append(ck_hbar_chart(
                "Demand $ by region (SAM, $M)", items,
                value_fmt=lambda v: f"${v:,.1f}M",
                subtitle="Where footprint demand concentrates (ILLUSTRATIVE on "
                         "SOURCED facility structure).",
                source="ift_demand.regional_demand", label_w=180.0))
    except Exception:  # noqa: BLE001
        pass
    try:
        if hc and hc.available:
            items = [(f"{r.hcpcs} {r.acuity_group}", r.rvu,
                      "navy" if r.acuity_group == "SCT" else
                      ("teal" if r.acuity_group == "ALS" else "positive"))
                     for r in hc.rows]
            cards.append(ck_bar_chart(
                "RVU by ambulance HCPCS", items,
                value_fmt=lambda v: f"{v:.2f}",
                subtitle="The spend ladder — SCT (3.25) vs BLS non-emergency "
                         "(1.00); IFT over-indexes on ALS2/SCT.",
                source="ift_analytics fee-schedule RVUs (42 CFR 414.610, GOV)"))
    except Exception:  # noqa: BLE001
        pass
    try:
        proj = next((s for s in (ts.series if ts else []) if s.key == "mmt_projection"), None)
        if proj:
            items = [(p.label, p.value, "teal") for p in proj.points]
            cards.append(ck_bar_chart(
                "MMT SOM revenue over 5 yrs ($M)", items,
                value_fmt=lambda v: f"${v:,.1f}M",
                subtitle="Forward projection at organic market growth "
                         "(ILLUSTRATIVE).",
                source="ift_mmt.mmt_growth_projection"))
    except Exception:  # noqa: BLE001
        pass
    grid = ck_chart_grid(*cards)
    if not grid:
        return ""
    return (ck_section_header("At a glance", eyebrow="THE DEMAND, VISUALLY") + grid)


# ═══════════════════════════════════════════════════════════════════════════
def render_ift_demand(qs: Optional[Dict[str, List[str]]] = None) -> str:
    """Render the IFT demand deep-dive. Degrades to honest notes, never raises."""
    nf = _dm.national_frame()
    hc = _dm.hcpcs_acuity_analysis()
    ep = _dm.emergency_prevalence()
    ts = _dm.demand_time_series()
    regions = _dm.regional_demand()
    summ = _dm.demand_summary()

    meta = (f"national → {summ['n_regions']} regions → {summ['n_counties']} "
            f"counties · {summ['n_hospitals_national']:,} US hospitals · "
            f"{summ['n_hcpcs']} HCPCS × BLS/ALS/SCT × emergency · trailed over time")
    head = ck_page_title(
        "IFT Demand Deep-Dive", eyebrow="INTERFACILITY TRANSPORT · DEMAND, "
        "NATIONAL → SUBCOUNTY", meta=meta)
    explainer = (
        '<p class="ifd-prose" style="font-size:15px;">The demand story end to end, '
        'and everything connects: the national base and its demographic engine, the '
        '<strong>CMS code analysis</strong> across the three IFT acuity types '
        '(BLS / ALS / SCT) and the <strong>emergency vs non-emergency</strong> '
        'split, the demand <strong>trailed over time</strong>, then down through '
        'the <strong>regions</strong> to the operator\'s <strong>exact counties</strong> '
        'and where its <strong>customers concentrate</strong>. Every figure carries '
        'its basis — ' + _chip("GOV") + ' ' + _chip("SOURCED") + ' '
        + _chip("ILLUSTRATIVE") + ' ' + _chip("FRAMEWORK") + '.</p>')

    body = "".join([
        _STYLES,
        ck_chart_assets(),
        head,
        explainer,
        _crosslinks(),
        ck_section_intro(
            "HOW TO READ THIS",
            "National first, then down to the exact counties they run.",
            italic_word="exact",
            body=("National demand base & demographics → the CMS codes by acuity "
                  "type and emergency split → the emergency/non-emergency "
                  "prevalence → the series over time → the regional roll-up → and "
                  "MMT's counties, customers, and growth.")),
        _charts(regions, hc, ts),
        _national_section(nf),
        _hcpcs_section(hc),
        _prevalence_section(ep),
        _timeseries_section(ts),
        _regional_section(regions),
        _mmt_section(),
        _crosslinks(),
        ck_next_section(
            "Drill into the clinical demand engine (conditions → codes → volume)",
            "/ift-clinical", eyebrow="The engine", italic_word="clinical"),
        ck_next_section(
            "See MMT's county-by-MSA deep-dive in full",
            "/ift-mmt", eyebrow="The operator", italic_word="county"),
        ck_page_actions(),
    ])
    return chartis_shell(
        body, "IFT Demand Deep-Dive", active_nav="/market",
        subtitle="Interfacility-transport demand — national to subcounty, by CMS "
                 "acuity code and emergency split, trailed over time")
