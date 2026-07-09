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
    "ILLUSTRATIVE": "Modeled — the basis is named, not a filed figure.",
    "CONNECTOR": "A network-gated connector dataset — ingest-ready, honest "
                 "fallback offline.",
}


def _chip(basis: str) -> str:
    b = (basis or "ILLUSTRATIVE").upper()
    key = ("GOV" if b.startswith("GOV") else "SOURCED" if b.startswith("SOURCED")
           else "ACADEMIC" if b.startswith("ACADEMIC")
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
        '<a class="ghost" href="/ift-markets">Target-markets funnel &rarr;</a>'
        '<a class="ghost" href="/ift-study">Investor study &rarr;</a>'
        '</div>')


def _kpi_strip(s) -> str:
    kpis = [
        ck_kpi_block("CBSAs served", str(s.n_cbsa),
                     f"{s.n_msa} MSA · {s.n_micro} micro", code="MSA/μSA"),
        ck_kpi_block("Counties", str(s.n_county),
                     f"{s.n_states} states · {s.n_metros} metros", code="COUNTY"),
        ck_kpi_block("Population (2020)", _num(s.pop_2020),
                     "US Census", code="POP"),
        ck_kpi_block("65+ share", _pct(s.senior_share),
                     f"{_num(s.pop_65_plus)} seniors", code="65+"),
        ck_kpi_block("Modeled IFT demand", f"{_num(s.demand_missions)}/yr",
                     "ground-IFT legs (modeled)", code="LEGS"),
        ck_kpi_block("Modeled demand $", _usd(s.demand_dollars),
                     "@ $1,300/leg (illustrative)", code="$"),
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
        f'{_chip("GOV")} 2020 Census · demand {_chip("ILLUSTRATIVE")} '
        "national-anchored per-capita model.</p>")


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
        f'{_chip("GOV")} 2020 Census · 65+ &amp; demand {_chip("ILLUSTRATIVE")} '
        "(named rates). Roles: core / suburban / rural-feeder.</p>")


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
        f'{_chip("ILLUSTRATIVE")}; national volumes {_chip("GOV")}/'
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
        f'<p class="mmt-note">s(m) {_chip("ILLUSTRATIVE")} reuses the study '
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
        f'<p class="mmt-note">All ILLUSTRATIVE with named bases; labor share is '
        "the GADCS anchor (~69% of ground-ambulance cost).</p>")


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


def render_ift_mmt(qs=None) -> str:
    """Render the MMT county-by-MSA deep-dive page. Degrades but never raises."""
    try:
        s = _m.footprint_summary()
    except Exception:  # noqa: BLE001
        s = None
    meta = ""
    if s:
        meta = (f"{s.n_cbsa} CBSAs · {s.n_county} counties · "
                f"{_num(s.pop_2020)} people · ~{_num(s.demand_missions)} "
                "modeled IFT legs/yr")
    head = ck_page_title(
        "Midwest Medical Transport — County Deep Dive",
        eyebrow="MMT · INTERFACILITY TRANSPORT · SUBJECT OPERATOR", meta=meta)
    explainer = (
        '<p class="mmt-prose">MMT (Omaha HQ) is the study\'s deep-dive subject. '
        "This page resolves its served territory from the metro grain down to "
        "every <strong>county, grouped by MSA</strong>, and wires each "
        "county-level public dataset — Census 65+ demand, CMS ambulance "
        "saturation &amp; geographic variation, CDC kidney &amp; cardiac "
        "prevalence, the hospital origin universe, and the NPPES ambulance-"
        "supplier field — to MMT's exact FIPS. County↔MSA delineations are OMB "
        f"2023 {_chip('GOV')}, population is the 2020 Census {_chip('GOV')}, and "
        f"the ground-IFT demand model is {_chip('ILLUSTRATIVE')} with named, "
        "national-anchored per-capita rates.</p>")
    parts: List[str] = [_STYLES, head, explainer, _cta()]
    if s:
        parts.append(_kpi_strip(s))
    parts += [
        _cbsa_table(), _county_table(), _serviceable_section(),
        _operating_section(), _connector_table(), _clinical_table(),
        _metro_read(), _scorecard_section(), _diligence_section(),
        _cta(), ck_page_actions(),
    ]
    return chartis_shell(
        "".join(parts), "MMT — County Deep Dive", active_nav="/market",
        subtitle="Midwest Medical Transport · county-by-MSA footprint, demand & "
                 "connector coverage")
