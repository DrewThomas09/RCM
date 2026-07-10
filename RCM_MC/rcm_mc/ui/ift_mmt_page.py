"""MMT county-by-MSA deep dive (``/ift-mmt``).

Renders :mod:`rcm_mc.market_reports.ift_mmt` — Midwest Medical Transport's
footprint resolved to its 22 counties across 7 CBSAs, the age-split ground-IFT
demand model, the county-grain connector coverage, the ICD-10-validated clinical
drivers, and the per-metro competitive read. Editorial-Chartis page: opens with
``ck_page_title``, a KPI strip via ``ck_kpi_block``, then sourced tables with
honesty chips. Degrades but never raises — a missing analytic drops its section.
"""
from __future__ import annotations

import html as _html
from typing import List, Optional

from ._chartis_kit import (
    chartis_shell, ck_kpi_block, ck_page_actions, ck_page_title,
    ck_section_header,
)
from ..market_reports import ift_mmt as _m


def _esc(x: object) -> str:
    return _html.escape(str(x if x is not None else ""))


def _num(x: object) -> str:
    try:
        return f"{int(round(float(x))):,}"
    except (TypeError, ValueError):
        return "—"


def _usd(x: object) -> str:
    try:
        v = float(x)
    except (TypeError, ValueError):
        return "—"
    if abs(v) >= 1e6:
        return f"${v / 1e6:,.2f}M"
    return f"${v:,.0f}"


def _pct(x: object) -> str:
    try:
        return f"{float(x) * 100:.1f}%"
    except (TypeError, ValueError):
        return "—"


_BASIS_TITLES = {
    "GOV": "A published government figure (OMB delineations, 2020 Census, CMS).",
    "SOURCED": "Computed from our vendored / ingested data.",
    "ACADEMIC": "A published study / analyst estimate.",
    "DERIVED": "Computed by an explicit equation from GOV/SOURCED/ACADEMIC "
               "inputs — the equation and inputs are stated.",
    "FRAMEWORK": "An analyst scaffold — a stated assumption structure to be "
                 "replaced by company data in diligence, never a filed figure.",
    "ILLUSTRATIVE": "Modeled — the basis is named, not a filed figure.",
    "CONNECTOR": "A network-gated connector dataset — ingest-ready, honest "
                 "fallback offline.",
}


def _chip(basis: str) -> str:
    b = (basis or "ILLUSTRATIVE").upper()
    key = ("GOV" if b.startswith("GOV") else "SOURCED" if b.startswith("SOURCED")
           else "ACADEMIC" if b.startswith("ACADEMIC")
           else "DERIVED" if b.startswith("DERIVED")
           else "FRAMEWORK" if b.startswith("FRAMEWORK")
           else "CONNECTOR" if b.startswith("CONNECTOR")
           else "ILLUSTRATIVE")
    return (f'<span class="mmt-chip mmt-chip-{key.lower()}" '
            f'title="{_esc(_BASIS_TITLES[key])}">{key}</span>')


_STYLES = """<style>
.mmt-chip{display:inline-block;font-family:var(--sc-mono,Consolas,monospace);
font-size:9px;font-weight:700;letter-spacing:.06em;padding:1px 6px;border-radius:2px;
vertical-align:middle;text-transform:uppercase;}
.mmt-chip-gov{background:#e7efe9;color:#154e36;}
.mmt-chip-sourced{background:#e0efed;color:#0f3d39;}
.mmt-chip-academic{background:#e6edf7;color:#243b57;}
.mmt-chip-derived{background:#e9e6f4;color:#3d3268;}
.mmt-chip-framework{background:#efe9e2;color:#6a4e2a;}
.mmt-chip-illustrative{background:#f6eee0;color:#7a5c1a;}
.mmt-chip-connector{background:#edecea;color:#5a5a5a;}
.mmt-prose{font-family:var(--sc-serif,Georgia,serif);font-size:14.5px;line-height:1.62;
color:var(--sc-text,#1a2332);max-width:88ch;margin:0 0 12px;}
.mmt-cta{display:flex;flex-wrap:wrap;gap:10px;margin:12px 0 18px;}
.mmt-cta a{font-family:var(--sc-mono,Consolas,monospace);font-size:12px;font-weight:600;
letter-spacing:.04em;text-decoration:none;padding:9px 15px;border-radius:3px;}
.mmt-cta a.solid{color:#fff;background:var(--sc-teal,#155752);}
.mmt-cta a.ghost{color:var(--sc-teal,#155752);border:1px solid var(--sc-teal,#155752);}
.mmt-wrap{overflow-x:auto;margin:6px 0 16px;}
.mmt-tab{border-collapse:collapse;width:100%;font-size:12.5px;
font-family:var(--sc-sans,Inter,system-ui,sans-serif);}
.mmt-tab th,.mmt-tab td{border:1px solid var(--sc-border,#e4dccb);padding:7px 10px;
text-align:left;vertical-align:top;line-height:1.45;}
.mmt-tab thead th{background:var(--sc-navy,#0b2341);color:#fff;font-weight:600;
font-size:11px;letter-spacing:.02em;position:sticky;top:0;z-index:1;}
.mmt-tab tbody tr:nth-child(even){background:var(--sc-surface,#faf7f1);}
.mmt-tab tbody tr:hover{background:#f3eee2;}
.mmt-tab .num{font-variant-numeric:tabular-nums;font-family:var(--sc-mono,Consolas,monospace);
text-align:right;white-space:nowrap;}
.mmt-tab .lab{font-weight:600;white-space:nowrap;}
.mmt-tab tr.mmt-cbsa td{background:#12463a;color:#fff;font-weight:600;
font-family:var(--sc-mono,Consolas,monospace);font-size:11px;letter-spacing:.05em;
text-transform:uppercase;}
.mmt-note{font-family:var(--sc-mono,Consolas,monospace);font-size:10.5px;
color:var(--sc-muted,#6b6357);margin:2px 0 14px;line-height:1.5;max-width:96ch;}
</style>"""


def _cta() -> str:
    return (
        '<div class="mmt-cta">'
        '<a class="solid" href="/api/ift/markets.xlsx" download>Download the '
        'workbook (MMT sheets) &darr;</a>'
        '<a class="ghost" href="/connector-estate">Live data-connector estate '
        '&rarr;</a>'
        '<a class="ghost" href="/api/ift/mmt.json">Model JSON (API) &rarr;</a>'
        '<a class="ghost" href="/ift-markets">Target-markets funnel &rarr;</a>'
        '<a class="ghost" href="/ift-study">Investor study &rarr;</a>'
        '</div>')


def _kpi_strip(s) -> str:
    # No `code=` badges here — six bracket chips rendered as a row of
    # floating debris next to the values (2026-07-10 audit).
    kpis = [
        ck_kpi_block("CBSAs served", str(s.n_cbsa),
                     f"{s.n_msa} MSA · {s.n_micro} micro"),
        ck_kpi_block("Counties", str(s.n_county),
                     f"{s.n_states} states · {s.n_metros} metros"),
        ck_kpi_block("Population (2020)", _num(s.pop_2020), "US Census"),
        ck_kpi_block("65+ share", _pct(s.senior_share),
                     f"{_num(s.pop_65_plus)} seniors"),
        ck_kpi_block("Derived IFT demand floor", f"{_num(s.demand_missions)}/yr",
                     "measured-base per-capita × pop (DERIVED)"),
        ck_kpi_block("Demand $ floor", _usd(s.demand_dollars),
                     "at $469/leg — the Medicare avg (MedPAC-derived)"),
    ]
    return '<div class="ck-kpi-grid">' + "".join(kpis) + "</div>"


def _cbsa_table() -> str:
    cbsas = _m.footprint_cbsas()
    if not cbsas:
        return ""
    rows = []
    for b in cbsas:
        rows.append(
            "<tr>"
            f'<td class="lab">{_esc(b.name)}</td>'
            f"<td>{_esc(b.kind)}</td>"
            f"<td>{_esc(b.metro)}</td>"
            f'<td class="num">{_num(len(b.counties))}</td>'
            f'<td class="num">{_num(b.pop_2020)}</td>'
            f'<td class="num">{_num(b.pop_65_plus)}</td>'
            f'<td class="num">{_num(b.demand_missions)}</td>'
            f'<td class="num">{_usd(b.demand_dollars)}</td>'
            "</tr>")
    return (
        ck_section_header("Footprint by CBSA", eyebrow="SEVEN CORE-BASED "
                          "STATISTICAL AREAS", count=len(cbsas))
        + '<div class="mmt-wrap"><table class="mmt-tab"><thead><tr>'
        "<th>CBSA</th><th>Type</th><th>Metro</th><th>Counties</th>"
        "<th>Pop 2020</th><th>65+</th><th>Demand legs/yr</th><th>Demand $</th>"
        f"</tr></thead><tbody>{''.join(rows)}</tbody></table></div>"
        f'<p class="mmt-note">Delineations {_chip("GOV")} OMB 2023 · population '
        f'{_chip("GOV")} 2020 Census · demand {_chip("DERIVED")} 2020 pop × '
        "the measured-base per-capita floor (3.47M national NEDS+NIS legs ÷ "
        "331.4M) · $ at the $469 Medicare-average floor.</p>")


def _county_table() -> str:
    cbsas = _m.footprint_cbsas()
    if not cbsas:
        return ""
    body = []
    for b in cbsas:
        body.append(
            f'<tr class="mmt-cbsa"><td colspan="8">{_esc(b.name)} '
            f"({_esc(b.kind)}) — {_esc(b.metro)}</td></tr>")
        for c in sorted(b.counties, key=lambda x: -x.pop_2020):
            d = _m.county_demand(c)
            note = c.seat + ((" · " + c.note) if c.note else "")
            body.append(
                "<tr>"
                f'<td class="lab">{_esc(c.name)}</td>'
                f"<td>{_esc(c.state)}</td>"
                f'<td class="num">{_esc(c.fips)}</td>'
                f"<td>{_esc(c.role)}</td>"
                f'<td class="num">{_num(c.pop_2020)}</td>'
                f'<td class="num">{_num(c.pop_65_plus)}</td>'
                f'<td class="num">{_num(d.demand_missions)}</td>'
                f"<td>{_esc(note)}</td>"
                "</tr>")
    return (
        ck_section_header("Every county MMT serves", eyebrow="THE 22-COUNTY "
                          "TERRITORY, BY CBSA", count=len(_m.MMT_COUNTIES))
        + '<div class="mmt-wrap"><table class="mmt-tab"><thead><tr>'
        "<th>County</th><th>St</th><th>FIPS</th><th>Role</th><th>Pop 2020</th>"
        "<th>65+ (est)</th><th>Demand legs/yr</th><th>Seat / anchor node</th>"
        f"</tr></thead><tbody>{''.join(body)}</tbody></table></div>"
        f'<p class="mmt-note">County↔CBSA {_chip("GOV")} OMB 2023 · pop '
        f'{_chip("GOV")} 2020 Census · 65+ share tier-based pending the ACS '
        f'connector (flagged) · demand {_chip("DERIVED")} measured-base '
        "per-capita floor. Roles: core / suburban / rural-feeder.</p>")


def _connector_table() -> str:
    cov = _m.county_connector_coverage()
    if not cov:
        return ""
    n_live = sum(1 for c in cov if c.available)
    rows = []
    for c in cov:
        status = (_chip("SOURCED") + " live" if c.available
                  else _chip("CONNECTOR") + " ingest-ready")
        href = "/connector-estate?dataset=" + _esc(c.dataset_id)
        rows.append(
            "<tr>"
            f'<td class="lab"><a href="{href}" style="color:var(--sc-navy,#0b2341);'
            f'text-decoration:none;border-bottom:1px solid rgba(21,87,82,.35);">'
            f"{_esc(c.title)}</a></td>"
            f"<td>{_esc(c.grain)}</td>"
            f"<td>{_esc(c.yields)}</td>"
            f"<td>{status}</td>"
            "</tr>")
    return (
        ck_section_header("County-grain data-connector coverage",
                          eyebrow="EVERY CMS / CDC / CENSUS / NPPES HOOK",
                          count=f"{len(cov)} hooks")
        + f'<p class="mmt-note">{n_live} live / {len(cov) - n_live} '
        "ingest-ready. Every dataset is registered and filtered to MMT's "
        "FIPS/state — it flips from ingest-ready to live the moment the estate "
        "is ingested; offline each cites an honest GOV fallback.</p>"
        '<div class="mmt-wrap"><table class="mmt-tab"><thead><tr>'
        "<th>Connector</th><th>Resolves to</th><th>What it yields for MMT</th>"
        f"<th>Status</th></tr></thead><tbody>{''.join(rows)}</tbody></table></div>")


def _clinical_table() -> str:
    drivers = _m.clinical_drivers(14)
    if not drivers:
        return ""
    rows = []
    for d in drivers:
        rows.append(
            "<tr>"
            f'<td class="lab">{_esc(d.condition)}</td>'
            f"<td>{_esc(d.family)}</td>"
            f"<td>{_esc(d.transfer_type)}</td>"
            f"<td>{_esc(d.icd10)}</td>"
            f'<td class="num">{d.codes_valid}/{d.codes_total}</td>'
            "</tr>")
    return (
        ck_section_header("Acute-transfer clinical drivers",
                          eyebrow="THE DEMAND ENGINE (ICD-10 VALIDATED)",
                          count=len(drivers))
        + '<div class="mmt-wrap"><table class="mmt-tab"><thead><tr>'
        "<th>Condition</th><th>Family</th><th>Transfer</th><th>ICD-10-CM</th>"
        f"<th>Codes ok</th></tr></thead><tbody>{''.join(rows)}</tbody></table></div>"
        f'<p class="mmt-note">Conditions ranked by demographic CAGR '
        f'{_chip("DERIVED")}; national volumes {_chip("GOV")}/'
        f'{_chip("ACADEMIC")}; ICD-10-CM codes {_chip("SOURCED")} validated '
        "against the code set.</p>")


def _metro_read() -> str:
    reads = _m.mmt_metro_reads()
    if not reads:
        return ""
    rows = []
    for r in reads:
        comp = "; ".join(r.competitors) or "—"
        rows.append(
            "<tr>"
            f'<td class="lab">{_esc(r.metro)}</td>'
            f'<td class="num">{r.n_counties}</td>'
            f'<td class="num">{_num(r.pop_2020)}</td>'
            f'<td class="num">{_num(r.demand_missions)}</td>'
            f"<td>{_esc(r.insource_read)}</td>"
            f"<td>{_esc(comp)}</td>"
            "</tr>")
    return (
        ck_section_header("Per-metro competitive & moat read",
                          eyebrow="WHERE MMT COMPETES, COUNTY-TIED",
                          count=len(reads))
        + '<div class="mmt-wrap"><table class="mmt-tab"><thead><tr>'
        "<th>Metro</th><th>Counties</th><th>Pop</th><th>Demand legs/yr</th>"
        "<th>Insource-vs-outsource read</th><th>Competing operators</th>"
        f"</tr></thead><tbody>{''.join(rows)}</tbody></table></div>"
        f'<p class="mmt-note">Operator names {_chip("GOV")} PUBLIC / company-web, '
        "named honestly; the reads are analyst knowledge, not our data.</p>")


def _serviceable_section() -> str:
    sm = _m.mmt_serviceable_model()
    if not sm.rows:
        return ""
    kpis = (
        '<div class="ck-kpi-grid">'
        + ck_kpi_block("Footprint IFT demand", f"{_num(sm.total_demand)}/yr",
                       "ground-IFT legs (modeled)", code="DEMAND")
        + ck_kpi_block("Serviceable (outsourced)",
                       f"{_num(sm.total_serviceable)}/yr",
                       f"{_pct(sm.footprint_serviceable_share)} of demand",
                       code="SAM")
        + ck_kpi_block("MMT SOM", f"{_num(sm.mmt_som_missions)}/yr",
                       "MMT-winnable legs", code="SOM")
        + ck_kpi_block("MMT SOM revenue", _usd(sm.mmt_som_dollars),
                       "@ $1,300/leg (illustrative)", code="$")
        + "</div>")
    rows = []
    for r in sm.rows:
        rows.append(
            "<tr>"
            f'<td class="lab">{_esc(r.metro)}</td>'
            f"<td>{_esc(r.insource_class)}</td>"
            f'<td class="num">{_num(r.demand_missions)}</td>'
            f'<td class="num">{_pct(r.serviceable_share)}</td>'
            f'<td class="num">{_num(r.serviceable_missions)}</td>'
            f'<td class="num">{_pct(r.mmt_share)}</td>'
            f'<td class="num">{_num(r.mmt_missions)}</td>'
            f'<td class="num">{_usd(r.mmt_revenue)}</td>'
            "</tr>")
    return (
        ck_section_header("Serviceable market (SOM)",
                          eyebrow="DEMAND → s(m) → MMT-WINNABLE BOOK",
                          count=_usd(sm.mmt_som_dollars))
        + kpis
        + '<div class="mmt-wrap"><table class="mmt-tab"><thead><tr>'
        "<th>Metro</th><th>Insource archetype</th><th>Demand legs/yr</th>"
        "<th>s(m)</th><th>Serviceable legs/yr</th><th>MMT share</th>"
        "<th>MMT legs/yr</th><th>MMT revenue</th></tr></thead>"
        f"<tbody>{''.join(rows)}</tbody></table></div>"
        f'<p class="mmt-note">s(m) {_chip("FRAMEWORK")} reuses the study '
        "funnel's serviceable share by insource archetype, so this SOM agrees "
        f"with the market model; MMT share {_chip('ILLUSTRATIVE')} from the "
        "ift_geo competitive reads.</p>")


def _operating_section() -> str:
    op = _m.mmt_operating_model()
    if not op.metrics:
        return ""
    rows = []
    for mtr in op.metrics:
        rows.append(
            "<tr>"
            f'<td class="lab">{_esc(mtr.name)}</td>'
            f'<td class="num">{_esc(mtr.value)}</td>'
            f"<td>{_chip(mtr.basis)}</td>"
            f"<td>{_esc(mtr.detail)}</td>"
            "</tr>")
    return (
        ck_section_header("Operating model — unit economics",
                          eyebrow="THE COST STRUCTURE & MARGIN LEVERS")
        + f'<p class="mmt-prose">{_esc(op.headline)}</p>'
        '<div class="mmt-wrap"><table class="mmt-tab"><thead><tr>'
        "<th>Metric</th><th>Value</th><th>Basis</th><th>Detail</th>"
        f"</tr></thead><tbody>{''.join(rows)}</tbody></table></div>"
        f'<p class="mmt-note">Published benchmarks {_chip("SOURCED")} '
        f'{_chip("GOV")} — GADCS (federal ambulance cost collection), '
        "MedPAC, HCCI, AIMHI; DERIVED lines show their equations. GADCS "
        "figures were captured from trade coverage of the report and sit "
        "in the re-verify queue until the CMS PDFs are re-pulled. No "
        "fabricated per-leg P&L appears here — MMT's actual margin is a "
        "diligence request.</p>")


def _scorecard_section() -> str:
    sc = _m.mmt_positioning_scorecard()
    if not sc:
        return ""
    rows = []
    for r in sc:
        rows.append(
            "<tr>"
            f'<td class="lab">{_esc(r.factor)}</td>'
            f"<td>{_esc(r.mmt)}</td>"
            f"<td>{_esc(r.ameripro)}</td>"
            f"<td>{_esc(r.national_ems)}</td>"
            f"<td>{_esc(r.municipal)}</td>"
            "</tr>")
    return (
        ck_section_header("Positioning scorecard",
                          eyebrow="MMT VS THE COMPETITIVE FIELD", count=len(sc))
        + '<div class="mmt-wrap"><table class="mmt-tab"><thead><tr>'
        "<th>Factor</th><th>MMT (subject)</th><th>AmeriPro</th>"
        "<th>National EMS (GMR/AMR)</th><th>Municipal / 911</th>"
        f"</tr></thead><tbody>{''.join(rows)}</tbody></table></div>"
        f'<p class="mmt-note">Reads {_chip("GOV")} analyst knowledge; operator '
        "names PUBLIC / company-web, no exclusivities asserted.</p>")


def _payer_section() -> str:
    pm = _m.mmt_payer_mix()
    if not pm.rows:
        return ""
    rows = []
    for r in pm.rows:
        rows.append(
            "<tr>"
            f'<td class="lab">{_esc(r.payer)}</td>'
            f'<td class="num">{_pct(r.share)}</td>'
            f'<td class="num">{r.rate_multiple:.2f}x</td>'
            f'<td class="num">{_pct(r.revenue_share)}</td>'
            f'<td class="num">{_usd(r.revenue_dollars)}</td>'
            "</tr>")
    return (
        ck_section_header("Payer mix", eyebrow="THE REVENUE BLEND BEHIND $/LEG")
        + f'<p class="mmt-prose">Commercial is ~{_pct(0.30)} of transports but '
        f'<strong>{_pct(pm.commercial_revenue_share)} of revenue</strong> — the '
        "2.0× commercial multiple over Medicare (HCCI 2022) makes payer mix "
        "the single biggest revenue lever.</p>"
        '<div class="mmt-wrap"><table class="mmt-tab" style="max-width:640px;">'
        "<thead><tr><th>Payer</th><th>% transports</th><th>Rate vs Medicare</th>"
        "<th>% revenue</th><th>SOM revenue</th></tr></thead>"
        f"<tbody>{''.join(rows)}</tbody></table></div>"
        f'<p class="mmt-note">{_esc(pm.note)}</p>')


def _scenario_section() -> str:
    sc = _m.mmt_som_scenario()
    if not sc.levers:
        return ""
    kpis = (
        '<div class="ck-kpi-grid">'
        + ck_kpi_block("Downside SOM", _usd(sc.downside_som),
                       "combined moderate", code="DOWN")
        + ck_kpi_block("Base SOM", _usd(sc.base_som), "modeled central",
                       code="BASE")
        + ck_kpi_block("Upside SOM", _usd(sc.upside_som),
                       "combined moderate", code="UP")
        + "</div>")
    rows = []
    for lv in sc.levers:
        rows.append(
            "<tr>"
            f'<td class="lab">{_esc(lv.name)}</td>'
            f'<td class="num">{_usd(lv.low_som)}</td>'
            f'<td class="num">{_usd(lv.high_som)}</td>'
            f'<td class="num">{_pct(lv.swing_pct)}</td>'
            "</tr>")
    return (
        ck_section_header("SOM scenario band", eyebrow="THE RANGE, NOT A POINT")
        + kpis
        + '<div class="mmt-wrap"><table class="mmt-tab" style="max-width:640px;">'
        "<thead><tr><th>Lever (swung one-at-a-time)</th><th>SOM low</th>"
        "<th>SOM high</th><th>Swing</th></tr></thead>"
        f"<tbody>{''.join(rows)}</tbody></table></div>"
        f'<p class="mmt-note">The SOM is multiplicative in each lever, so a swing '
        f"scales the base directly. {_chip('FRAMEWORK')} — a stated range, not data.</p>")


def _opportunity_section() -> str:
    opp = _m.mmt_county_opportunity()
    if not opp:
        return ""
    rows = []
    for o in opp:
        rows.append(
            "<tr>"
            f'<td class="num">{o.rank}</td>'
            f'<td class="lab">{_esc(o.name)}</td>'
            f"<td>{_esc(o.state)}</td>"
            f"<td>{_esc(o.metro)}</td>"
            f'<td class="num">{_num(o.demand_missions)}</td>'
            f'<td class="num">{_num(o.serviceable_missions)}</td>'
            f'<td class="num">{_usd(o.opportunity_revenue)}</td>'
            f'<td class="num">{_usd(o.mmt_current_revenue)}</td>'
            f'<td class="num">{_usd(o.headroom_revenue)}</td>'
            "</tr>")
    return (
        ck_section_header("County opportunity ranking",
                          eyebrow="WHERE MMT SHOULD FOCUS", count=len(opp))
        + '<div class="mmt-wrap"><table class="mmt-tab"><thead><tr>'
        "<th>#</th><th>County</th><th>St</th><th>Metro</th><th>Demand legs/yr</th>"
        "<th>Serviceable legs/yr</th><th>Contestable $</th><th>MMT current $</th>"
        f"<th>Headroom $</th></tr></thead><tbody>{''.join(rows)}</tbody>"
        "</table></div>"
        f'<p class="mmt-note">Contestable = county demand × s(m); the '
        "current/headroom split is on the metro's MMT share. "
        f'{_chip("FRAMEWORK")} — reuses the serviceable model.</p>')


def _accounts_section() -> str:
    accts = _m.mmt_anchor_accounts()
    if not accts:
        return ""
    cards = []
    _TIER = {"captive-network": "#b5321e", "regional-hub": "#155752",
             "independent": "#b8732a"}
    for a in accts:
        color = _TIER.get(a.tier, "#155752")
        cards.append(
            '<div style="border:1px solid var(--sc-border,#e4dccb);'
            f'border-left:3px solid {color};border-radius:4px;padding:13px 15px;'
            'background:var(--sc-surface,#faf7f1);">'
            f'<div style="font-family:var(--sc-serif,Georgia,serif);font-size:15px;'
            f'font-weight:600;">{_esc(a.system)}</div>'
            f'<div style="font-family:var(--sc-mono,Consolas,monospace);'
            f'font-size:9.5px;font-weight:700;letter-spacing:.05em;color:{color};'
            f'text-transform:uppercase;margin:2px 0 6px;">{_esc(a.tier)} · '
            f'{_esc("; ".join(a.metros))}</div>'
            f'<div style="font-size:12px;line-height:1.5;margin-bottom:5px;">'
            f'<b>Posture:</b> {_esc(a.insource_posture)}</div>'
            f'<div style="font-size:12px;line-height:1.5;margin-bottom:5px;'
            f'color:#0f3d39;"><b>MMT play:</b> {_esc(a.mmt_strategy)}</div>'
            f'<div style="font-size:12px;line-height:1.5;color:#7a3218;">'
            f'<b>Risk:</b> {_esc(a.risk)}</div></div>')
    return (
        ck_section_header("Anchor-system account map",
                          eyebrow="THE TRANSFER-CENTER GTM", count=len(accts))
        + '<div style="display:grid;grid-template-columns:repeat(auto-fit,'
        'minmax(340px,1fr));gap:12px;margin:6px 0 14px;">'
        + "".join(cards) + "</div>"
        f'<p class="mmt-note">Systems / facilities {_chip("GOV")} PUBLIC / '
        "company-web; strategy &amp; risk are analyst framework.</p>")


def _growth_section() -> str:
    gp = _m.mmt_growth_projection()
    if not (gp.available and gp.years):
        return ""
    kpis = (
        '<div class="ck-kpi-grid">'
        + ck_kpi_block("SOM today", _usd(gp.start_revenue),
                       "modeled serviceable revenue", code="SOM")
        + ck_kpi_block("Base case (5-yr)", _usd(gp.base_5yr),
                       f"{_pct(gp.base_cagr)}/yr organic", code="BASE")
        + ck_kpi_block("Platform case (5-yr)", _usd(gp.platform_5yr),
                       f"{_pct(gp.platform_cagr)}/yr w/ consolidation",
                       code="PLAT")
        + "</div>")
    rows = []
    for y in gp.years:
        lbl = "Today" if y.year_offset == 0 else f"+{y.year_offset} yr"
        rows.append(
            "<tr>"
            f'<td class="lab">{_esc(lbl)}</td>'
            f'<td class="num">{_usd(y.base_revenue)}</td>'
            f'<td class="num">{_usd(y.platform_revenue)}</td>'
            "</tr>")
    return (
        ck_section_header("Growth projection", eyebrow="THE SOM REVENUE "
                          "TRAJECTORY (3-LEVER BRIDGE)")
        + kpis
        + '<div class="mmt-wrap"><table class="mmt-tab" style="max-width:520px;">'
        "<thead><tr><th>Year</th><th>Base revenue</th><th>Platform revenue</th>"
        f"</tr></thead><tbody>{''.join(rows)}</tbody></table></div>"
        f'<p class="mmt-note">{_esc(gp.headline)}. Growth {_chip("ILLUSTRATIVE")} '
        "from the study's three-lever bridge — price (GOV AIF-anchored) × volume "
        "(demographic CAGR) = market; × consolidation = platform.</p>")


def _swot_section() -> str:
    sw = _m.mmt_swot()
    if not sw:
        return ""
    quads = [
        ("Strengths", sw.strengths, "#0a8a5f"),
        ("Weaknesses", sw.weaknesses, "#b8732a"),
        ("Opportunities", sw.opportunities, "#155752"),
        ("Threats", sw.threats, "#b5321e"),
    ]
    cells = []
    for label, items, color in quads:
        lis = "".join(f"<li style='margin:4px 0;'>{_esc(x)}</li>" for x in items)
        cells.append(
            '<div style="border:1px solid var(--sc-border,#e4dccb);'
            f'border-top:3px solid {color};border-radius:4px;padding:12px 14px;'
            'background:var(--sc-surface,#faf7f1);">'
            f'<div style="font-family:var(--sc-mono,Consolas,monospace);'
            f'font-size:11px;font-weight:700;letter-spacing:.06em;'
            f'text-transform:uppercase;color:{color};margin-bottom:6px;">'
            f'{_esc(label)}</div>'
            f'<ul style="margin:0;padding-left:18px;font-size:12.5px;'
            f'line-height:1.5;">{lis}</ul></div>')
    return (
        ck_section_header("SWOT", eyebrow="THE STRATEGIC READ, FOOTPRINT-TIED")
        + '<div style="display:grid;grid-template-columns:repeat(auto-fit,'
        'minmax(320px,1fr));gap:12px;margin:6px 0 14px;">'
        + "".join(cells) + "</div>")


def _diligence_section() -> str:
    d = _m.mmt_diligence()
    if not (d.value_levers or d.risks or d.questions):
        return ""
    def _cards(items, sev):
        out = ['<div class="ist-grid" style="grid-template-columns:'
               'repeat(auto-fit,minmax(300px,1fr));display:grid;gap:12px;'
               'margin:6px 0 14px;">']
        for it in items:
            tag = (f'<span style="font-family:var(--sc-mono,Consolas,monospace);'
                   f'font-size:9px;font-weight:700;letter-spacing:.05em;'
                   f'color:var(--sc-teal,#155752);">{_esc(it.tag)}</span>'
                   if it.tag else "")
            out.append(
                '<div style="border:1px solid var(--sc-border,#e4dccb);'
                'border-left:3px solid var(--sc-teal,#155752);border-radius:4px;'
                'padding:12px 14px;background:var(--sc-surface,#faf7f1);">'
                f'<div style="font-family:var(--sc-serif,Georgia,serif);'
                f'font-size:14px;font-weight:600;margin-bottom:4px;">'
                f'{_esc(it.title)}</div>{tag}'
                f'<div style="font-size:12.5px;line-height:1.5;margin-top:4px;'
                f'color:var(--sc-text,#1a2332);">{_esc(it.detail)}</div></div>')
        out.append("</div>")
        return "".join(out)
    ql = "".join(f"<li style='margin:5px 0;'>{_esc(q)}</li>" for q in d.questions)
    return (
        ck_section_header("Diligence — value levers, risks & questions",
                          eyebrow="THE THESIS A BUYER UNDERWRITES")
        + '<p class="mmt-note" style="font-weight:600;color:var(--sc-teal,#155752);">'
        "VALUE-CREATION LEVERS</p>" + _cards(d.value_levers, "")
        + '<p class="mmt-note" style="font-weight:600;color:var(--sc-warning,#b8732a);">'
        "RISKS</p>" + _cards(d.risks, "")
        + '<p class="mmt-note" style="font-weight:600;">DILIGENCE QUESTIONS</p>'
        f'<ol style="font-size:13px;line-height:1.5;max-width:92ch;'
        f'padding-left:20px;">{ql}</ol>'
        f'<p class="mmt-note">Analyst framework {_chip("GOV")} tied to the county '
        "model + ift_geo reads — a diligence scaffold, not a filed figure.</p>")


# ─────────────────────────────────────────────────────────────────────────────
# Company-truth sections (2026-07-10 research pull) — who MMT actually is.
# These render from ift_company / ift_health_systems / ift_npi_landscape and
# sit ABOVE the county model, which is re-framed as the legacy-core deep dive.
# ─────────────────────────────────────────────────────────────────────────────
def _company_kpis() -> str:
    try:
        from ..market_reports import ift_company as _co
        states = _co.npi_states()
        n_npi = len(_co.MMT_NPI_LOCATIONS)
    except Exception:  # noqa: BLE001
        return ""
    kpis = [
        ck_kpi_block("States of operation", "13",
                     "company claim, 2026 (PRESS)"),
        ck_kpi_block("Org NPIs on file", str(n_npi),
                     f"{len(states)} states (NPPES, 2026-07-10)"),
        ck_kpi_block("Team members", "2,800+", "company claim, 2026 (PRESS)"),
        ck_kpi_block("Fleet", "500+", "vehicles incl. air + para-transit "
                     "(PRESS)"),
        ck_kpi_block("Missions / year", "200,000+",
                     "Jan 2022 deal release (PRESS)"),
        ck_kpi_block("Sponsor", "Harbour Point",
                     "recap Jan 2022 · Headway co-invest"),
    ]
    return '<div class="ck-kpi-grid">' + "".join(kpis) + "</div>"


def _estate_section() -> str:
    try:
        from ..market_reports import ift_company as _co
        core = _co.legacy_core_locations()
        exp = _co.expansion_locations()
        stations = _co.MMT_WEB_STATIONS
    except Exception:  # noqa: BLE001
        return ""

    def _rows(locs):
        out = []
        for l in locs:
            out.append(
                "<tr>"
                f'<td class="num">{_esc(l.npi)}</td>'
                f'<td class="lab">{_esc(l.city)}, {_esc(l.state)}</td>'
                f"<td>{_esc(l.name)}</td>"
                f"<td>{_esc(l.address)}</td>"
                f"<td>{_esc(l.note)}</td>"
                "</tr>")
        return "".join(out)

    head = ("<thead><tr><th>NPI</th><th>City</th><th>Registered name / DBA"
            "</th><th>Practice address</th><th>Note</th></tr></thead>")
    web = ", ".join(f"{c}, {st}" for c, st in stations)
    return (
        ck_section_header("The location estate — NPPES-verified",
                          eyebrow="WHO MMT ACTUALLY IS",
                          count=len(core) + len(exp))
        + '<p class="mmt-prose">The prior read modeled MMT as a Nebraska–Iowa '
        "operator. The NPI registry says otherwise: the legacy core "
        "(NE/IA/SD, below left of the divider) now sits inside a "
        "<strong>13-state platform</strong> whose 2023–24 enumerations "
        "(Des Moines, Omaha, Kansas City) and OH/IN/WI/CO/RI/NC/VA units "
        "track the Harbour Point expansion play.</p>"
        f'<p class="mmt-note">LEGACY CORE (NE · IA · SD) {_chip("SOURCED")}</p>'
        f'<div class="mmt-wrap"><table class="mmt-tab">{head}'
        f"<tbody>{_rows(core)}</tbody></table></div>"
        f'<p class="mmt-note">EXPANSION UNITS (2022–) {_chip("SOURCED")}</p>'
        f'<div class="mmt-wrap"><table class="mmt-tab">{head}'
        f"<tbody>{_rows(exp)}</tbody></table></div>"
        f'<p class="mmt-note">Station cities named by company/web sources '
        f"without a separate captured NPI (subparts often bill under a "
        f"parent): {_esc(web)}. NPPES pull 2026-07-10; the VA record's "
        "same-org link is flagged, not asserted.</p>")


def _ownership_section() -> str:
    try:
        from ..market_reports import ift_company as _co
        tl = _co.OWNERSHIP_TIMELINE
        est = _co.REVENUE_ESTIMATES
        est_read = _co.REVENUE_ESTIMATE_READ
        srcs = _co.SOURCES
    except Exception:  # noqa: BLE001
        return ""
    rows = []
    for ev in tl:
        src = srcs.get(ev.source_key)
        link = (f'<a href="{_esc(src.url)}" target="_blank" rel="noopener">'
                f"{_esc(src.basis)}</a>" if src else "")
        rows.append(
            "<tr>"
            f'<td class="lab">{_esc(ev.year)}</td>'
            f"<td><strong>{_esc(ev.event)}</strong><br>"
            f'<span style="font-size:12px;color:var(--sc-muted,#6b6357);">'
            f"{_esc(ev.detail)}</span></td>"
            f"<td>{link}</td></tr>")
    est_rows = "".join(
        "<tr>"
        f'<td class="lab">{_esc(srcs[e.source_key].label.split(" ")[0])}</td>'
        f"<td>{_esc(e.value)}</td>"
        f'<td>{_esc(e.as_of)}</td></tr>' for e in est if e.source_key in srcs)
    return (
        ck_section_header("Ownership & scale — the PE trail",
                          eyebrow="1987 FOUNDING → HARBOUR POINT PLATFORM")
        + '<div class="mmt-wrap"><table class="mmt-tab"><thead><tr>'
        "<th>Year</th><th>Event</th><th>Basis</th></tr></thead>"
        f"<tbody>{''.join(rows)}</tbody></table></div>"
        + ck_section_header("Third-party revenue estimates — shown, "
                            "not blended", eyebrow="HANDLE WITH CARE")
        + '<div class="mmt-wrap"><table class="mmt-tab"><thead><tr>'
        "<th>Estimator</th><th>Estimate</th><th>As of</th></tr></thead>"
        f"<tbody>{est_rows}</tbody></table></div>"
        f'<p class="mmt-prose">{_esc(est_read)}</p>')


def _customers_section() -> str:
    try:
        from ..market_reports import ift_health_systems as _hs
        systems = _hs.systems()
        statewide = _hs.STATEWIDE
    except Exception:  # noqa: BLE001
        return ""
    cards = []
    for s in systems:
        fac_rows = "".join(
            "<tr>"
            f'<td class="lab">{_esc(f.name)}</td>'
            f"<td>{_esc(f.city)}, {_esc(f.state)}</td>"
            f'<td class="num">{_esc(f.beds)}</td>'
            f'<td class="num">{_esc(f.ccn or "—")}</td>'
            "</tr>" for f in s.facilities)
        catalysts = "".join(f"<li style='margin:4px 0;'>{_esc(c)}</li>"
                            for c in s.catalysts)
        links = " · ".join(
            f'<a href="{_esc(u)}" target="_blank" rel="noopener">source</a>'
            for u in s.sources)
        cards.append(
            '<div style="border:1px solid var(--sc-border,#e4dccb);'
            'border-radius:4px;padding:14px 16px;margin:0 0 14px;'
            'background:var(--sc-surface,#faf7f1);">'
            f'<div style="font-family:var(--sc-serif,Georgia,serif);'
            f'font-size:16px;font-weight:600;">{_esc(s.name)}'
            f'<span style="font-size:12px;font-weight:400;color:'
            f'var(--sc-muted,#6b6357);"> · {_esc(s.hq)}</span></div>'
            f'<p class="mmt-prose" style="margin:6px 0;">{_esc(s.role)}</p>'
            f'<div class="mmt-wrap"><table class="mmt-tab"><thead><tr>'
            f"<th>Facility</th><th>City</th><th>Beds</th><th>CCN</th>"
            f"</tr></thead><tbody>{fac_rows}</tbody></table></div>"
            f'<p class="mmt-note"><strong>Transfer coordination:</strong> '
            f"{_esc(s.transfer_center)}</p>"
            f'<p class="mmt-note"><strong>Transport posture:</strong> '
            f"{_esc(s.ems_posture)}</p>"
            + (f'<p class="mmt-note" style="font-weight:600;">CATALYSTS</p>'
               f'<ul style="font-size:12.5px;line-height:1.5;max-width:92ch;'
               f'padding-left:20px;margin:2px 0 8px;">{catalysts}</ul>'
               if s.catalysts else "")
            + f'<p class="mmt-prose" style="font-style:italic;">'
            f"{_esc(s.ift_read)}</p>"
            f'<p class="mmt-note">{links}</p></div>')
    return (
        ck_section_header("Hospital-system customer deep dives",
                          eyebrow="THE ACCOUNTS THAT GENERATE THE TRANSFERS",
                          count=len(systems))
        + f'<p class="mmt-prose">Statewide frame: {_esc(statewide["ne_hospitals"])}. '
        f'{_esc(statewide["transfer_center_stats"])} '
        f'{_esc(statewide["maternity"])}</p>'
        + "".join(cards))


def _competitors_section() -> str:
    try:
        from ..market_reports import ift_npi_landscape as _npi
        summ = _npi.summary()
        comps = _npi.COMPETITORS
    except Exception:  # noqa: BLE001
        return ""
    if not summ.get("available"):
        return ""
    ne, ia = summ["ne"], summ["ia"]
    labels = _npi.CATEGORY_LABELS
    count_rows = "".join(
        "<tr>"
        f'<td class="lab">{_esc(labels.get(cat, cat))}</td>'
        f'<td class="num">{_num(ne.get(cat, 0))}</td>'
        f'<td class="num">{_num(ia.get(cat, 0))}</td>'
        "</tr>" for cat in ("private", "hospital-owned",
                            "municipal-fire-volunteer", "air"))
    comp_rows = "".join(
        "<tr>"
        f'<td class="lab">{_esc(c.name)}</td>'
        f"<td>{_esc(c.base)}</td>"
        f"<td>{_esc(c.archetype)}</td>"
        f"<td>{_esc(c.read)} "
        f'<a href="{_esc(c.source_url)}" target="_blank" rel="noopener">'
        f"source</a></td></tr>" for c in comps)
    return (
        ck_section_header("Competitive landscape — from the registry, "
                          "not a guess",
                          eyebrow=f"NPPES SWEEP · {summ['total_orgs']} ORG "
                                  "NPIS · PULLED 2026-07-10")
        + f'<p class="mmt-prose">{_esc(summ["read"])}</p>'
        + '<div class="mmt-wrap"><table class="mmt-tab"><thead><tr>'
        "<th>Category</th><th>NE org NPIs</th><th>IA org NPIs</th>"
        f"</tr></thead><tbody>{count_rows}</tbody></table></div>"
        f'<p class="mmt-note">{_esc(summ["source_label"])} · NPPES matches '
        "mailing OR practice address, so each state includes some "
        "out-of-state-practice orgs; small squads often hold 2–3 NPIs.</p>"
        + '<div class="mmt-wrap"><table class="mmt-tab"><thead><tr>'
        "<th>Competitor</th><th>Base</th><th>Archetype</th>"
        "<th>The read</th></tr></thead>"
        f"<tbody>{comp_rows}</tbody></table></div>"
        f'<p class="mmt-note">Claims-data next step {_chip("CONNECTOR")}: '
        "rank these suppliers by Medicare services + payments via the "
        "pinned data.cms.gov datasets (Medicare Physician & Other "
        "Practitioners by Provider & Service, CY2020–23 UUIDs in "
        "ift_npi_landscape.CLAIMS_RECIPE) — egress-blocked from this "
        "environment, runs from any unblocked network via "
        "connectors/cms_open_data.</p>")


def _litigation_section() -> str:
    try:
        from ..market_reports import ift_company as _co
        lits = _co.LITIGATION
        read = _co.LITIGATION_READ
        srcs = _co.SOURCES
    except Exception:  # noqa: BLE001
        return ""
    rows = "".join(
        "<tr>"
        f'<td class="lab">{_esc(l.case)}</td>'
        f"<td>{_esc(l.court)}</td>"
        f'<td class="num">{_esc(l.filed)}</td>'
        f"<td>{_esc(l.nature)}</td>"
        f"<td>{_esc(l.status)} "
        + (f'<a href="{_esc(srcs[l.source_key].url)}" target="_blank" '
           f'rel="noopener">docket</a>' if l.source_key in srcs else "")
        + "</td></tr>" for l in lits)
    return (
        ck_section_header("Litigation & agency records — public dockets",
                          eyebrow="COURT TRAIL", count=len(lits))
        + '<div class="mmt-wrap"><table class="mmt-tab"><thead><tr>'
        "<th>Case</th><th>Court</th><th>Filed</th><th>Nature</th>"
        f"<th>Status</th></tr></thead><tbody>{rows}</tbody></table></div>"
        f'<p class="mmt-prose">{_esc(read)}</p>')


def _demand_band_section() -> str:
    try:
        band = _m.footprint_demand_band()
        outlook = _m.footprint_volume_outlook()
    except Exception:  # noqa: BLE001
        return ""
    scen_rows = "".join(
        "<tr>"
        f'<td class="lab">{_esc(s.name)}</td>'
        f'<td class="num">{s.cagr_pct:.1f}%/yr</td>'
        f'<td class="num">+{s.five_yr_pct:.1f}%</td>'
        f"<td>{_esc(s.equation)}</td>"
        f"<td>{_esc(s.basis)}</td>"
        "</tr>" for s in outlook.scenarios)
    catalysts = "".join(f"<li style='margin:5px 0;'>{_esc(c)}</li>"
                        for c in outlook.catalysts)
    return (
        ck_section_header("Footprint demand band — derived, bracketed",
                          eyebrow="THE MEASURED BASE, TWO ALLOCATIONS")
        + '<p class="mmt-prose">The footprint demand read is a '
        f"<strong>bracket, not a point</strong>: {_num(band.lo_legs)}–"
        f"{_num(band.hi_legs)} acute IFT legs/yr "
        f"({_usd(band.lo_dollars)}–{_usd(band.hi_dollars)} at the $469 "
        "Medicare-average floor). Both bounds are allocations of the "
        "measured national transfer base — the equations:</p>"
        f'<p class="mmt-note">POP-SHARE&nbsp; {_esc(band.equation_flat)}'
        f"<br>65+-SHARE&nbsp; {_esc(band.equation_senior)}"
        f"<br>{_esc(band.caveat)}</p>"
        + ck_section_header("Potential volume increase — the scenario "
                            "band", eyebrow="MSA × CENSUS × NEDS, TIED "
                            "TOGETHER")
        + '<div class="mmt-wrap"><table class="mmt-tab"><thead><tr>'
        "<th>Scenario</th><th>CAGR</th><th>5-yr</th><th>Equation</th>"
        f"<th>Basis</th></tr></thead><tbody>{scen_rows}</tbody></table></div>"
        + '<p class="mmt-note" style="font-weight:600;">FOOTPRINT '
        "CATALYSTS — DOCUMENTED, NOT QUANTIFIED</p>"
        f'<ul style="font-size:12.5px;line-height:1.55;max-width:96ch;'
        f'padding-left:20px;margin:2px 0 8px;">{catalysts}</ul>'
        f'<p class="mmt-note">{_esc(outlook.caveat)}</p>')


def _growth_counties_section() -> str:
    try:
        rows = _m.county_growth()
    except Exception:  # noqa: BLE001
        rows = []
    if not rows:
        return ""
    body = "".join(
        "<tr>"
        f'<td class="lab">{_esc(r.county.name)}, {_esc(r.county.state)}</td>'
        f"<td>{_esc(r.county.metro)}</td>"
        f'<td class="num">{_num(r.pop_2020)}</td>'
        f'<td class="num">{_num(r.pop_2024)}</td>'
        f'<td class="num">{"+" if r.growth_pct >= 0 else ""}'
        f"{r.growth_pct:.1f}%</td>"
        f'<td class="num">{"+" if r.cagr_pct >= 0 else ""}'
        f"{r.cagr_pct:.1f}%</td>"
        "</tr>" for r in rows)
    return (
        ck_section_header("County population growth, 2020 → 2024",
                          eyebrow="MEASURED, NOT PROJECTED",
                          count=len(rows))
        + '<p class="mmt-prose">Where the footprint is actually growing — '
        "Vintage-2024 Census estimates against the 2020 decennial count. "
        "Sarpy (Omaha's southern suburb ring) leads; the rural-feeder "
        "counties without a captured 2024 figure are omitted rather than "
        "imputed.</p>"
        + '<div class="mmt-wrap"><table class="mmt-tab"><thead><tr>'
        "<th>County</th><th>Metro</th><th>Pop 2020</th><th>Pop 2024 est.</th>"
        "<th>Growth</th><th>CAGR</th></tr></thead>"
        f"<tbody>{body}</tbody></table></div>"
        f'<p class="mmt-note">{_esc(rows[0].basis)}</p>')


def _core_divider() -> str:
    return (
        ck_section_header("The legacy core, county by county",
                          eyebrow="NE + WESTERN IA — WHERE THE MODEL HAS "
                                  "COUNTY-GRAIN DATA")
        + '<p class="mmt-prose">Everything below resolves the ORIGINAL '
        "NE/IA service area to the county grain — 22 counties across 7 "
        "CBSAs. It is the deepest-data slice of the platform, not the "
        "whole platform: the 2022– expansion units (KC, OH, IN, WI, CO, "
        "RI, NC) do not yet have county models and are sized only by "
        "their NPPES presence above.</p>")


def render_ift_mmt(qs=None) -> str:
    """Render the MMT company deep-dive page. Degrades but never raises."""
    try:
        s = _m.footprint_summary()
    except Exception:  # noqa: BLE001
        s = None
    head = ck_page_title(
        "Midwest Medical Transport — Company Deep Dive",
        eyebrow="MMT AMBULANCE · INTERFACILITY TRANSPORT · SUBJECT OPERATOR",
        meta=("13-state IFT platform · Harbour Point Capital (2022) · "
              "23 org NPIs · legacy core: 22 NE/IA counties, 7 CBSAs"))
    explainer = (
        '<p class="mmt-prose">MMT is the study\'s deep-dive subject — an '
        "interfacility-transport specialist founded 1987 in Columbus, NE "
        "(explicitly 'not a 911 service'), now a private-equity platform. "
        "This page is the company file: the NPPES-verified location "
        "estate, the ownership trail, the hospital-system accounts that "
        "generate the transfers, the competitive field computed from the "
        "registry, and the public court record — then the legacy-core "
        f"county model. Estate + registry reads are {_chip('SOURCED')}, "
        "press/deal facts carry their links, geography is "
        f"{_chip('GOV')} (OMB 2023 · 2020 Census).</p>")
    parts: List[str] = [_STYLES, head, explainer, _cta(), _company_kpis()]
    parts += [
        _estate_section(), _ownership_section(), _customers_section(),
        _competitors_section(), _litigation_section(),
        _core_divider(),
    ]
    if s:
        parts.append(_kpi_strip(s))
    parts += [
        _cbsa_table(), _county_table(), _demand_band_section(),
        _growth_counties_section(), _serviceable_section(),
        _scenario_section(), _opportunity_section(), _operating_section(),
        _payer_section(), _growth_section(), _connector_table(),
        _clinical_table(), _metro_read(),
        _accounts_section(), _scorecard_section(), _swot_section(),
        _diligence_section(), _cta(), ck_page_actions(),
    ]
    return chartis_shell(
        "".join(parts), "MMT — Company Deep Dive", active_nav="/market",
        subtitle="Midwest Medical Transport · the company file + the "
                 "legacy-core county model")
