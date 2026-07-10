"""In-Depth IFT — BLS · ALS1 · ALS2 · CCT (/in-depth-ift-bls-als1-als2-cct).

The clinical-service-level research page: how Basic Life Support, ALS Level 1,
ALS Level 2, and Specialty/Critical Care Transport differ in the care
delivered, patients served, staffing, equipment, operating complexity,
reimbursement, and IFT relevance — with the four-column comparison table the
study asked for at the top (comprehensive definition / typical clinical needs
/ typical operational needs / reimbursement differences).

Contract (inherited from ``rcm_mc.market_reports.ift_service_levels``):
ZERO illustrative figures anywhere; every fact renders with its basis chip
(GOV / ACADEMIC / SOURCED / DERIVED / FRAMEWORK) and its source(s) as LINKS
right next to the information; verbatim regulatory quotes render inline.

Read-only companions in the IFT estate (cross-linked, never modified here):
``/ift`` hub, ``/ift-demand``, ``/ift-clinical``, ``/ift-research``,
``/ift-markets``. Wired at ``/in-depth-ift-bls-als1-als2-cct`` in server.py.
"""
from __future__ import annotations

import html as _html
from typing import Dict, List, Optional, Tuple

from ._chartis_kit import (
    chartis_shell,
    ck_kpi_block,
    ck_page_explainer,
    ck_page_title,
    ck_signal_badge,
)
from ._chart_kit import (
    ck_bar_chart, ck_chart_assets, ck_chart_grid, ck_hbar_chart,
)
from ..market_reports import ift_service_levels as M


def _e(v) -> str:
    return _html.escape("" if v is None else str(v))


# Basis chip tones on the semantic Chartis palette (mirrors the IFT pages).
_CHIP_TONE = {
    "GOV": ("#155752", "#155752"),
    "SOURCED": ("#0a8a5f", "#0a8a5f"),
    "ACADEMIC": ("#0b2341", "#0b2341"),
    "DERIVED": ("#3d3268", "#7a6aa8"),
    "FRAMEWORK": ("#463a63", "#7a6aa8"),
}


def _chip(basis: str) -> str:
    ink, border = _CHIP_TONE.get(basis, ("#5c5546", "#a89e8a"))
    return (f'<span class="isl-chip" style="color:{ink};'
            f'border-color:{border};">{_e(basis)}</span>')


def _short_label(label: str) -> str:
    """Compact link text: publisher/document id before the long descriptor."""
    for sep in (" — ", " – "):
        if sep in label:
            return label.split(sep, 1)[0]
    return label if len(label) <= 46 else label[:44] + "…"


def _links(srcs) -> str:
    out = []
    for s in srcs:
        out.append(f'<a class="isl-src" href="{_e(s.url)}" target="_blank" '
                   f'rel="noopener" title="{_e(s.label)}">'
                   f'{_e(_short_label(s.label))}</a>')
    return '<span class="isl-srcs">' + " · ".join(out) + "</span>"


def _quote(q: str) -> str:
    if not q:
        return ""
    return f'<div class="isl-quote">&ldquo;{_e(q)}&rdquo;</div>'


def _fact_li(f, *, with_quote: bool = True) -> str:
    return ("<li>" + _e(f.text) + " " + _chip(f.basis) + " " + _links(f.srcs)
            + (_quote(f.quote) if with_quote else "") + "</li>")


def _fact_list(facts, *, with_quote: bool = True) -> str:
    return ('<ul class="isl-facts">'
            + "".join(_fact_li(f, with_quote=with_quote) for f in facts)
            + "</ul>")


def _section(anchor: str, eyebrow: str, title: str, blurb: str) -> str:
    return (f'<section class="isl-sec" id="{_e(anchor)}">'
            f'<div class="isl-eyebrow">{_e(eyebrow)}</div>'
            f'<h2>{_e(title)}</h2>'
            f'<p class="isl-blurb">{_e(blurb)}</p></section>')


_STYLES = """<style>
.isl-chip{display:inline-block;font:600 9px/1.5 ui-monospace,monospace;
  letter-spacing:.08em;border:1px solid;border-radius:3px;padding:0 5px;
  vertical-align:1px;white-space:nowrap;}
.isl-srcs{font-size:11px;color:var(--sc-muted,#6b6357);}
.isl-src{color:var(--sc-teal,#155752);text-decoration:underline dotted;
  text-underline-offset:2px;white-space:nowrap;}
.isl-quote{font:italic 11.5px/1.55 Georgia,serif;color:#4a4438;margin:4px 0 2px;
  padding:4px 10px;border-left:3px solid var(--sc-teal,#155752);
  background:var(--sc-surface,#faf7f1);}
.isl-facts{margin:4px 0 6px;padding-left:18px;}
.isl-facts li{margin:0 0 9px;font-size:13px;line-height:1.55;}
.isl-wrap{overflow-x:auto;margin:6px 0 12px;}
.isl-tab{border-collapse:collapse;width:100%;font-size:12.5px;
  background:var(--sc-panel,#fff);}
.isl-tab th,.isl-tab td{border:1px solid var(--sc-border,#e4dccb);
  padding:7px 10px;vertical-align:top;text-align:left;line-height:1.5;}
.isl-tab thead th{background:var(--sc-navy,#0b2341);color:#fff;font-weight:600;
  white-space:nowrap;}
.isl-tab tbody tr:nth-child(even){background:var(--sc-surface,#faf7f1);}
.isl-tab td.isl-lvl{background:#eef5f1;font-weight:700;white-space:nowrap;
  min-width:118px;}
.isl-top .isl-facts{padding-left:14px;margin:0;}
.isl-top .isl-facts li{margin:0 0 8px;font-size:12px;}
.isl-top td{min-width:250px;}
.isl-sec{margin:26px 0 8px;}
.isl-eyebrow{font:600 10px/1.6 ui-monospace,monospace;letter-spacing:.14em;
  color:var(--sc-teal,#155752);text-transform:uppercase;}
.isl-sec h2{font:700 21px/1.25 Georgia,serif;color:var(--sc-navy,#0b2341);
  margin:2px 0 4px;}
.isl-blurb{font-size:13px;color:#4a4438;max-width:960px;margin:0 0 6px;}
.isl-links a{display:inline-block;margin:0 14px 6px 0;font-size:12.5px;
  color:var(--sc-teal,#155752);}
.isl-verdict{border:1px solid var(--sc-border,#e4dccb);border-left:5px solid
  var(--sc-positive,#0a8a5f);background:var(--sc-panel,#fff);
  padding:12px 16px;margin:8px 0 14px;}
.isl-verdict .isl-statement{font:italic 15px/1.6 Georgia,serif;
  color:var(--sc-navy,#0b2341);margin:0 0 8px;}
.isl-kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));
  gap:10px;margin:12px 0 4px;}
.isl-num{font-variant-numeric:tabular-nums;}
.isl-bib{columns:2;column-gap:28px;font-size:12px;}
.isl-bib li{margin:0 0 7px;break-inside:avoid;}
@media (max-width:760px){.isl-bib{columns:1;}}
</style>"""


# ─────────────────────────────────────────────────────────────────────────────
# Blocks
# ─────────────────────────────────────────────────────────────────────────────

def _crosslinks() -> str:
    return ('<div class="isl-links">'
            '<a href="/ift">IFT study hub &rarr;</a>'
            '<a href="/ift-demand">Demand deep-dive &rarr;</a>'
            '<a href="/ift-clinical">Clinical demand engine &rarr;</a>'
            '<a href="/ift-research">Market research brief &rarr;</a>'
            '<a href="/ift-markets">Geographic markets &rarr;</a>'
            '<a href="/ift-diligence">Diligence architecture &rarr;</a>'
            '</div>')


def _kpi_row() -> str:
    k = M.kpis()
    cells = [
        ck_kpi_block("Ground RVU span", _e(k["rvu_span"]),
                     "BLS anchor 1.00 → SCT 3.25 · 42 CFR 414.610"),
        ck_kpi_block("CY2026 base-rate span",
                     _e(k["cy2026_base_span"]),
                     f"CF ${k['cy2026_cf']:,.2f} · ${k['cy2026_mileage']:.2f}/mi"),
        ck_kpi_block("Medicare FFS ground (2024)",
                     _e(k["medicare_transports_2024"]),
                     f"{_e(k['medicare_spend_2024'])} paid · MedPAC"),
        ck_kpi_block("All-payer level mix", "56 / 42 / 3",
                     "BLS / ALS1 / ALS2+SCT % of transports · GADCS"),
        ck_kpi_block("Interfacility share of EMS",
                     "12.5%", "of 60.3M activations, NEMSIS 2024"),
        ck_kpi_block("SCT share of Medicare ground", _e(k["sct_share"]),
                     "71,279 claims CY2024 — the premium, thin tier"),
    ]
    return '<div class="isl-kpis">' + "".join(cells) + "</div>"


def _top_table() -> str:
    """THE required table: level × (definition | clinical | operational |
    reimbursement), every cell sourced+linked."""
    rows: List[str] = []
    for lv in M.service_levels():
        codes = ", ".join(f"{c} ({r:.2f} RVU)" for c, _d, r in lv.hcpcs)
        def_cell = ("<ul class='isl-facts'><li>" + _e(lv.definition.text)
                    + " " + _chip(lv.definition.basis) + " "
                    + _links(lv.definition.srcs)
                    + _quote(lv.definition.quote) + "</li></ul>")
        rows.append(
            "<tr>"
            f'<td class="isl-lvl">{_e(lv.key)}<div style="font-weight:400;'
            f'font-size:10.5px;color:#6b6357;">{_e(lv.name)}<br>{_e(codes)}'
            "</div></td>"
            f"<td>{def_cell}</td>"
            f"<td>{_fact_list(lv.clinical, with_quote=False)}</td>"
            f"<td>{_fact_list(lv.operational, with_quote=False)}</td>"
            f"<td>{_fact_list(lv.reimbursement, with_quote=False)}</td>"
            "</tr>")
    return ('<div class="isl-wrap"><table class="isl-tab isl-top"><thead><tr>'
            "<th>Service level</th>"
            "<th>1 · Comprehensive definition</th>"
            "<th>2 · Typical clinical needs</th>"
            "<th>3 · Typical operational needs</th>"
            "<th>4 · Reimbursement differences</th>"
            "</tr></thead><tbody>" + "".join(rows)
            + "</tbody></table></div>")


def _boundaries() -> str:
    items = []
    for lv in M.service_levels():
        b = lv.boundary
        items.append(
            f"<li><strong>{_e(lv.key)}</strong> — " + _e(b.text) + " "
            + _chip(b.basis) + " " + _links(b.srcs) + _quote(b.quote)
            + "</li>")
    return '<ul class="isl-facts">' + "".join(items) + "</ul>"


def _use_cases() -> str:
    items = []
    for lv in M.service_levels():
        for f in lv.use_cases:
            items.append(f"<li><strong>{_e(lv.key)}</strong> — " + _e(f.text)
                         + " " + _chip(f.basis) + " " + _links(f.srcs)
                         + "</li>")
    return '<ul class="isl-facts">' + "".join(items) + "</ul>"


def _charts() -> str:
    cards: List[str] = []
    try:
        fees = M.fee_rows()
        items = [(f"{r.hcpcs} {r.level}", r.cy2026_base,
                  "navy" if r.hcpcs in ("A0433", "A0434") else "teal")
                 for r in fees]
        cards.append(ck_bar_chart(
            "CY2026 national unadjusted base rate ($)", items,
            value_fmt=lambda v: f"${v:,.0f}",
            subtitle="RVU × $284.56 conversion factor — the payment ladder "
                     "the four levels sit on (GOV constants, DERIVED "
                     "arithmetic).",
            source="CMS CY2026 Ambulance Fee Schedule PUF · 42 CFR 414.610 · "
                   "MedPAC June 2026"))
    except Exception:  # noqa: BLE001
        pass
    try:
        mix = M.medicare_mix()
        items = [(f"{m.hcpcs} {m.level}", m.services / 1000.0,
                  "warning" if m.hcpcs in ("A0433", "A0434") else "teal")
                 for m in sorted(mix, key=lambda x: -x.services)]
        cards.append(ck_hbar_chart(
            "CY2024 Medicare allowed services by code (000s)", items,
            value_fmt=lambda v: f"{v:,.0f}k",
            subtitle="FFS supplier claims — ALS2 (85k) and SCT (71k) are "
                     "rounding errors next to the BLS/ALS1 books (GOV).",
            source="CMS Medicare Physician & Other Practitioners by "
                   "Geography & Service, CY2024",
            label_w=210.0))
    except Exception:  # noqa: BLE001
        pass
    try:
        wages = M.wage_ladder()
        items = [(f"{w.occupation}", float(w.median_wage), "teal")
                 for w in wages]
        cards.append(ck_bar_chart(
            "Median annual wage by crew credential ($, May 2025)", items,
            value_fmt=lambda v: f"${v/1000:,.0f}k",
            subtitle="Each level up substitutes scarcer, costlier labor — "
                     "EMT → paramedic → RT → RN (GOV, BLS OEWS).",
            source="BLS OEWS May 2025 · SOC 29-2042/29-2043/29-1126/29-1141"))
    except Exception:  # noqa: BLE001
        pass
    try:
        mix = M.medicare_mix()
        items = [(m.hcpcs, m.share_pct,
                  "navy" if m.hcpcs in ("A0433", "A0434") else "muted")
                 for m in mix]
        cards.append(ck_bar_chart(
            "Share of CY2024 Medicare ground transports (%)", items,
            value_fmt=lambda v: f"{v:.1f}%",
            subtitle="DERIVED shares of the six-code total (9.64M supplier "
                     "services).",
            source="CMS CY2024 by-Geography-and-Service national rows"))
    except Exception:  # noqa: BLE001
        pass
    return ck_chart_grid(*cards) or ""


def _fee_table() -> str:
    rows = []
    for r in M.fee_rows():
        rows.append(
            "<tr>"
            f"<td class='isl-lvl'>{_e(r.hcpcs)}</td>"
            f"<td>{_e(r.level)}</td>"
            f"<td class='isl-num'>{r.rvu:.2f}</td>"
            f"<td class='isl-num'>${r.cy2026_base:,.2f}</td>"
            f"<td class='isl-num'>{r.cy2024_services:,}</td>"
            f"<td class='isl-num'>${r.cy2024_avg_allowed:,.2f}</td>"
            f"<td class='isl-num'>${r.cy2024_avg_paid:,.2f}</td>"
            f"<td class='isl-num'>{r.cy2024_providers:,}</td>"
            "</tr>")
    src_row = _links(M.fee_rows()[0].srcs) if M.fee_rows() else ""
    return ('<div class="isl-wrap"><table class="isl-tab"><thead><tr>'
            "<th>HCPCS</th><th>Level</th><th>RVU</th>"
            "<th>CY2026 base (national)</th><th>CY2024 services</th>"
            "<th>CY2024 avg allowed</th><th>CY2024 avg paid</th>"
            "<th>Billing suppliers</th>"
            "</tr></thead><tbody>" + "".join(rows) + "</tbody></table></div>"
            + f'<p style="font-size:11.5px;">Sources: {src_row} — mileage '
              "A0425 pays separately ($9.15/mi national CY2026; 98.9M "
              "Medicare miles CY2024).</p>")


def _connector_note() -> str:
    """Live-estate status for the two reused connectors (read-only)."""
    try:
        cr = M.connector_reads()
    except Exception:  # noqa: BLE001
        return ""
    pb = cr.get("part_b") or {}
    qc = cr.get("qcew") or {}
    shared = cr.get("shared_medicare_volume") or {}
    bits = []
    pb_name = _e(pb.get("dataset_id")
                 or "physician/supplier procedure summary")
    if pb.get("available"):
        bits.append("Part B ambulance-HCPCS connector: "
                    f"<strong>live</strong> ({pb_name}).")
    else:
        bits.append(f"Part B ambulance-HCPCS connector ({pb_name}): "
                    "offline here — the CY2024 figures above cite the "
                    "published CMS file directly.")
    if qc.get("available"):
        bits.append("BLS QCEW NAICS 621910 employment connector: "
                    "<strong>live</strong>.")
    else:
        bits.append("BLS QCEW NAICS 621910 (ambulance employment) "
                    "connector: offline here — wages cite OEWS directly.")
    if shared:
        bits.append("Shared volume anchor from the IFT evidence registry: "
                    f"{_e(shared.get('value'))} "
                    f'(<a class="isl-src" href="{_e(shared.get("url"))}" '
                    f'target="_blank" rel="noopener">'
                    f'{_e(_short_label(str(shared.get("source"))))}</a>).')
    return ('<p style="font-size:12px;color:#4a4438;">'
            + " ".join(bits) + "</p>")


def _progression_table() -> str:
    rows = []
    for p in M.acuity_progression():
        rows.append(
            "<tr>"
            f"<td class='isl-lvl'>{_e(p.dimension)}</td>"
            f"<td>{_e(p.bls)}</td><td>{_e(p.als1)}</td>"
            f"<td>{_e(p.als2)}</td><td>{_e(p.sct)}</td>"
            f"<td>{_links(p.srcs)}</td>"
            "</tr>")
    return ('<div class="isl-wrap"><table class="isl-tab"><thead><tr>'
            "<th>What increases</th><th>BLS</th><th>ALS1</th><th>ALS2</th>"
            "<th>SCT / CCT</th><th>Sources</th>"
            "</tr></thead><tbody>" + "".join(rows) + "</tbody></table></div>")


def _crew_table() -> str:
    rows = []
    for c in M.crew_matrix():
        cell = lambda f: (_e(f.text) + " " + _chip(f.basis) + " "  # noqa: E731
                          + _links(f.srcs))
        rows.append(
            "<tr>"
            f"<td class='isl-lvl'>{_e(c.level)}</td>"
            f"<td>{cell(c.federal_minimum)}</td>"
            f"<td>{cell(c.state_examples)}</td>"
            f"<td>{cell(c.certifications)}</td>"
            "</tr>")
    return ('<div class="isl-wrap"><table class="isl-tab"><thead><tr>'
            "<th>Level</th><th>Federal minimum (Medicare)</th>"
            "<th>State staffing examples</th><th>Certifications</th>"
            "</tr></thead><tbody>" + "".join(rows) + "</tbody></table></div>")


def _wage_table() -> str:
    rows = []
    for w in M.wage_ladder():
        rows.append(
            "<tr>"
            f"<td class='isl-lvl'>{_e(w.occupation)}</td>"
            f"<td class='isl-num'>{_e(w.soc)}</td>"
            f"<td class='isl-num'>{w.employment:,}</td>"
            f"<td class='isl-num'>${w.median_wage:,}</td>"
            f"<td class='isl-num'>${w.mean_wage:,}</td>"
            f"<td>{_links((w.src,))}</td>"
            "</tr>")
    return ('<div class="isl-wrap"><table class="isl-tab"><thead><tr>'
            "<th>Occupation</th><th>SOC</th><th>US employment</th>"
            "<th>Median wage</th><th>Mean wage</th><th>Source</th>"
            "</tr></thead><tbody>" + "".join(rows) + "</tbody></table></div>")


def _edge_table() -> str:
    rows = []
    for ec in M.edge_cases():
        rows.append(
            "<tr>"
            f"<td class='isl-lvl' style='min-width:170px;'>{_e(ec.scenario)}"
            "</td>"
            f"<td><strong>{_e(ec.likely_level)}</strong></td>"
            f"<td>{_e(ec.determinant)}</td>"
            f"<td>{_e(ec.ambiguity)}</td>"
            f"<td>{_chip(ec.basis)} {_links(ec.srcs)}</td>"
            "</tr>")
    return ('<div class="isl-wrap"><table class="isl-tab"><thead><tr>'
            "<th>Scenario</th><th>Likely level</th>"
            "<th>Key determining fact</th><th>Ambiguity / alternative</th>"
            "<th>Basis · sources</th>"
            "</tr></thead><tbody>" + "".join(rows) + "</tbody></table></div>")


def _myth_table() -> str:
    rows = []
    for m in M.misconceptions():
        rows.append(
            "<tr>"
            f"<td style='min-width:200px;'><strong>{_e(m.myth)}</strong></td>"
            f"<td>{_e(m.reality)} {_links(m.srcs)}</td>"
            "</tr>")
    return ('<div class="isl-wrap"><table class="isl-tab"><thead><tr>'
            "<th>Misconception</th><th>What the sources actually say</th>"
            "</tr></thead><tbody>" + "".join(rows) + "</tbody></table></div>")


def _verdict_block() -> str:
    c = M.conclusion_test()
    return ('<div class="isl-verdict">'
            f'<p class="isl-statement">&ldquo;{_e(c.statement)}&rdquo;</p>'
            + ck_signal_badge(c.verdict, tone="positive")
            + "<h3 style='font-size:14px;margin:12px 0 2px;'>Why it holds"
              "</h3>" + _fact_list(c.support)
            + "<h3 style='font-size:14px;margin:12px 0 2px;'>Where it needs "
              "refining</h3>" + _fact_list(c.refinements)
            + "</div>")


def _bibliography() -> str:
    items = []
    for s in M.bibliography():
        items.append(f'<li><a class="isl-src" href="{_e(s.url)}" '
                     f'target="_blank" rel="noopener">{_e(s.label)}</a></li>')
    return '<ol class="isl-bib">' + "".join(items) + "</ol>"


# ─────────────────────────────────────────────────────────────────────────────
# Renderer
# ─────────────────────────────────────────────────────────────────────────────

def render_ift_service_levels(
        qs: Optional[Dict[str, List[str]]] = None) -> str:
    """Render the page. Pure function of the model; degrades, never raises."""
    summ = M.summary()
    meta = (f"{summ['n_facts']} sourced facts · {summ['n_sources']} linked "
            f"primary sources · {summ['n_edge_cases']} edge cases · "
            f"{summ['n_misconceptions']} misconceptions corrected · "
            "zero illustrative figures")
    head = ck_page_title(
        "In-Depth IFT — BLS · ALS1 · ALS2 · CCT",
        eyebrow="INTERFACILITY TRANSPORT · CLINICAL SERVICE LEVELS",
        meta=meta)
    explainer = ck_page_explainer(
        "The four service levels are four different products — clinically, "
        "operationally, and economically.",
        "This page answers the service-level research architecture end to "
        "end: what defines BLS, ALS1, ALS2 and Specialty/Critical Care "
        "Transport (the comparison table below), what each level requires "
        "clinically and operationally, how reimbursement differs, where the "
        "boundaries and edge cases sit, and whether the study's core "
        "conclusion survives the evidence. Every figure and claim carries "
        "its basis chip and a link to the primary source next to it — "
        "regulations (eCFR), CMS manuals and fee-schedule files, GAO/MedPAC/"
        "OIG, the national scope-of-practice model, state EMS rules, CAMTS "
        "standards, BLS wage data, NEMSIS, and peer-reviewed studies. "
        "Nothing on this page is illustrative.",
        source="rcm_mc.market_reports.ift_service_levels — verified against "
               "primary sources July 2026; shares the IFT estate's "
               "connectors read-only")

    parts: List[str] = [
        _STYLES, ck_chart_assets(), head, explainer, _crosslinks(),
        _kpi_row(),

        _section("table", "THE TABLE", "The four levels side by side",
                 "Definition, clinical needs, operational needs, and "
                 "reimbursement — each cell carries its own sources. "
                 "Verbatim regulatory definitions expand under column 1."),
        _top_table(),

        _section("framework", "§1 · WHAT IS BEING CLASSIFIED",
                 "Classification framework",
                 "Before defining levels: what the ladder classifies, who "
                 "decides, and why clinical, billed, and paid levels can "
                 "legitimately diverge."),
        _fact_list(M.classification_framework()),

        _section("boundaries", "BOUNDARIES", "What separates each level "
                 "from the one below",
                 "The discriminating line at each rung — the facts that "
                 "move a trip up or down the ladder."),
        _boundaries(),

        _section("charts", "VISUAL LADDERS", "Payment, volume, and labor "
                 "in one view",
                 "Real published values only — fee-schedule dollars, CY2024 "
                 "Medicare claim counts, and May 2025 wage data."),
        _charts(),

        _section("fee", "§12 · REIMBURSEMENT", "Fee schedule & payment "
                 "mechanics",
                 "The HCPCS/RVU ladder with CY2026 national rates and "
                 "CY2024 utilization, then the mechanics: geographic "
                 "adjustment, mileage, inflation updates, add-ons, and the "
                 "cost/margin evidence."),
        _fee_table(),
        _fact_list(M.payment_mechanics()),

        _section("mix", "§13 · VOLUME & MARKET RELEVANCE",
                 "Service mix and where IFT lives",
                 "How the four levels split the transport book across "
                 "GADCS (all-payer), Medicare claims, and NEMSIS activation "
                 "data — and the live-connector status for the underlying "
                 "datasets."),
        _fact_list(M.mix_readings()),
        _connector_note(),

        _section("progression", "§6 · ACUITY PROGRESSION",
                 "What actually increases across the ladder",
                 "Stability, monitoring, intervention, decision-making, "
                 "crew, payment, and volume — plus the two places the "
                 "clean ladder bends."),
        _progression_table(),
        _fact_list(M.progression_findings()),

        _section("crew", "§7 · CREW & LABOR", "Staffing floors, state "
                 "rules, certifications, wages",
                 "The federal minimums, how four verified states staff the "
                 "top tier differently, the credential ladder, and the "
                 "labor-market numbers that make staffing the binding "
                 "constraint."),
        _crew_table(),
        _wage_table(),
        _fact_list(M.workforce_facts()),

        _section("equipment", "§8 · EQUIPMENT & VEHICLE",
                 "What must be on the truck",
                 "The national BLS/ALS equipment lists, the CCT add-ons, "
                 "and why the chassis is not what defines the level."),
        _fact_list(M.equipment_facts()),

        _section("meds", "§9 · MEDICATION RULES",
                 "How medications move the classification",
                 "Who may give or maintain what, what counts toward ALS2, "
                 "and why titration is the SCT tell."),
        _fact_list(M.medication_rules()),

        _section("necessity", "§10 · NECESSITY, DOCUMENTATION & DENIALS",
                 "The paperwork that decides whether anyone gets paid",
                 "Medical necessity, physician certification statements, "
                 "prior authorization, origin/destination gates, and the "
                 "audit record."),
        _fact_list(M.necessity_and_denials()),

        _section("payers", "§12b · PAYER DIFFERENCES",
                 "Medicare is the vocabulary, not the whole market",
                 "Commercial vs Medicare pricing, surprise-billing status, "
                 "and how level recognition travels across payers."),
        _fact_list(M.payer_differences()),

        _section("states", "§15 · STATE VARIATION",
                 "The same patient, a different required crew",
                 "Verified state rules showing why the top of the ladder "
                 "moves at state lines."),
        _fact_list(M.state_variation()),

        _section("edges", "§17 · EDGE CASES",
                 "Nineteen ambiguous scenarios, classified",
                 "Each with its likely level, the determining fact, and "
                 "the honest source of ambiguity."),
        _edge_table(),

        _section("usecases", "§11 · TYPICAL IFT USE CASES BY LEVEL",
                 "Where each level shows up in interfacility work",
                 "The characteristic origin→destination patterns, sourced."),
        _use_cases(),

        _section("myths", "§18 · MISCONCEPTIONS",
                 "Twelve things the market gets wrong",
                 "Each myth against what the primary sources actually say."),
        _myth_table(),

        _section("verdict", "§20 · THE CONCLUSION UNDER TEST",
                 "Does the thesis statement survive the evidence?",
                 "The exact statement the study set out to test, the "
                 "verdict, and the refinements the evidence forces."),
        _verdict_block(),

        _section("sources", "SOURCES", "Bibliography",
                 "Every primary source used on this page, deduplicated — "
                 f"{summ['n_sources']} documents, all linked."),
        _bibliography(),
        _crosslinks(),
    ]

    return chartis_shell(
        "".join(parts),
        "In-Depth IFT — BLS · ALS1 · ALS2 · CCT",
        active_nav="/research",
        subtitle="Clinical service levels in depth · fully sourced, zero "
                 "illustrative",
    )
