"""IFT market-level research brief page (``/ift-research``).

Renders the deep, MARKET-focused research: market definition + taxonomy (reused
from ift_study), the IBISWorld industry-structure context, and the authored
market-research sections (metrics, unit economics, technology, regulatory,
segmentation, sizing, reimbursement, growth, evidence). No company-specific
analysis. Every table carries an honesty basis chip. Degrades, never raises.
"""
from __future__ import annotations

import html as _html
from typing import Any, Dict, List, Optional

from ._chartis_kit import (
    chartis_shell, ck_page_actions, ck_page_title, ck_panel, ck_section_header,
)
from ..market_reports import ift_research as _rs
from ..market_reports import ift_study as _st


def _esc(x: object) -> str:
    return _html.escape(str(x if x is not None else ""))


_BASIS_TITLES = {
    "GOV": "A published government figure (CMS, MedPAC, BLS, statute).",
    "SOURCED": "Computed from our vendored data.",
    "ACADEMIC": "A published study / industry report.",
    "ILLUSTRATIVE": "Modeled — the basis is named, not a filed figure.",
    "FRAMEWORK": "An analytic framework or definition, not a figure.",
}
_BASIS_CLASS = {"GOV": "gov", "SOURCED": "sourced", "ACADEMIC": "academic",
                "ILLUSTRATIVE": "illustrative", "FRAMEWORK": "framework"}


def _chip(basis: str) -> str:
    b = (basis or "FRAMEWORK").upper()
    key = b if b in _BASIS_TITLES else "FRAMEWORK"
    return (f'<span class="irs-chip irs-chip-{_BASIS_CLASS[key]}" '
            f'title="{_esc(_BASIS_TITLES[key])}">{key}</span>')


_STYLES = """<style>
.irs-chip{display:inline-block;font-family:var(--sc-mono,Consolas,monospace);
font-size:9px;font-weight:600;letter-spacing:.06em;padding:1px 6px;border-radius:2px;
vertical-align:middle;}
.irs-chip-gov{background:#e7efe9;color:#154e36;}
.irs-chip-sourced{background:#e9eef5;color:#243b57;}
.irs-chip-academic{background:#efeae0;color:#6b5426;}
.irs-chip-illustrative{background:#f3ecd9;color:#7a5c1a;}
.irs-chip-framework{background:#ece9f2;color:#463a63;}
.irs-src{font-family:var(--sc-mono,Consolas,monospace);font-size:10px;
color:var(--sc-muted,#6b6357);margin:5px 0 2px;line-height:1.5;}
.irs-prose{font-family:var(--sc-serif,Georgia,serif);font-size:14px;line-height:1.62;
color:var(--sc-text,#1a2332);max-width:90ch;margin:0 0 10px;}
.irs-sub{font-family:var(--sc-mono,Consolas,monospace);font-size:11px;font-weight:600;
letter-spacing:.06em;text-transform:uppercase;color:var(--sc-teal,#155752);
margin:16px 0 7px;}
.irs-wrap{overflow-x:auto;margin:5px 0 12px;}
.irs-tab{border-collapse:collapse;width:100%;font-size:12.5px;
font-family:var(--sc-sans,Inter,system-ui,sans-serif);}
.irs-tab th,.irs-tab td{border:1px solid var(--sc-border,#e4dccb);padding:6px 9px;
text-align:left;vertical-align:top;line-height:1.45;}
.irs-tab thead th{background:var(--sc-navy,#0b2341);color:#fff;font-weight:600;
font-size:11px;}
.irs-tab tbody tr:nth-child(even){background:var(--sc-surface,#faf7f1);}
.irs-tab td:first-child{font-weight:600;}
.irs-list{margin:2px 0 10px 20px;font-family:var(--sc-serif,Georgia,serif);
font-size:13.5px;line-height:1.6;color:var(--sc-text,#2a3340);}
.irs-toc{columns:2;column-gap:28px;margin:8px 0 14px;padding:12px 16px;
background:var(--sc-surface,#faf7f1);border:1px solid var(--sc-border,#e4dccb);
border-radius:4px;}
.irs-toc a{display:block;font-family:var(--sc-mono,Consolas,monospace);font-size:11.5px;
color:var(--sc-teal,#155752);text-decoration:none;padding:2px 0;break-inside:avoid;}
.irs-links{display:flex;flex-wrap:wrap;gap:16px;margin:14px 0 4px;
font-family:var(--sc-mono,Consolas,monospace);font-size:11px;font-weight:600;}
.irs-links a{color:var(--sc-teal,#155752);text-decoration:none;}
.irs-cardgrid{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));
gap:12px;margin:6px 0 12px;}
.irs-card{border:1px solid var(--sc-border,#e4dccb);border-left:3px solid
var(--sc-teal,#155752);border-radius:4px;padding:11px 13px;
background:var(--sc-surface,#faf7f1);}
.irs-card h4{font-family:var(--sc-serif,Georgia,serif);font-size:14px;margin:0 0 4px;}
.irs-card p{font-family:var(--sc-serif,Georgia,serif);font-size:12.5px;line-height:1.5;
margin:0;color:var(--sc-text,#2a3340);}
</style>"""


def _render_subsection(ss: Dict[str, Any]) -> str:
    heading = _esc(ss.get("heading", ""))
    basis = ss.get("basis", "FRAMEWORK")
    source = ss.get("source", "")
    head = f'<p class="irs-sub">{heading} {_chip(basis)}</p>' if heading else ""
    body = ""
    if ss.get("kind") == "table" and ss.get("columns"):
        cols = "".join(f"<th>{_esc(c)}</th>" for c in ss["columns"])
        rows = ""
        for r in ss.get("rows", []):
            tds = "".join(f"<td>{_esc(c)}</td>" for c in r)
            rows += f"<tr>{tds}</tr>"
        body = ('<div class="irs-wrap"><table class="irs-tab"><thead><tr>'
                f'{cols}</tr></thead><tbody>{rows}</tbody></table></div>')
    elif ss.get("bullets"):
        lis = "".join(f"<li>{_esc(b)}</li>" for b in ss["bullets"])
        body = f'<ul class="irs-list">{lis}</ul>'
    src = f'<p class="irs-src">Source: {_esc(source)}</p>' if source else ""
    return head + body + src


def _render_section(sec: Dict[str, Any], n: int) -> str:
    sid = _esc(sec.get("id", f"s{n}"))
    title = _esc(sec.get("title", ""))
    intro = _esc(sec.get("intro", ""))
    subs = "".join(_render_subsection(ss) for ss in sec.get("subsections", []))
    return (
        f'<div id="rs-{sid}">'
        + ck_section_header(f"{n}. {sec.get('title','')}",
                            eyebrow="MARKET RESEARCH")
        + ck_panel((f'<p class="irs-prose">{intro}</p>' if intro else "") + subs)
        + '</div>')


def _market_definition_block() -> str:
    """Sections 1-2 reused from ift_study: the concise definition + taxonomy matrix
    (rendered compactly here as the research brief's opening)."""
    tm = _st.taxonomy_matrix()
    if not tm.available:
        return ""
    head = "".join(f"<th>{_esc(c)}</th>" for c in tm.columns)
    body = ""
    for label, cells in tm.rows:
        tds = "".join(f"<td>{_esc(v)}</td>" for v in cells)
        body += f'<tr><td>{_esc(label)}</td>{tds}</tr>'
    return (
        '<div id="rs-definition">'
        + ck_section_header("1. Market definition & taxonomy",
                            eyebrow="MARKET RESEARCH")
        + ck_panel(
            '<p class="irs-prose"><strong>Definition.</strong> Interfacility '
            'transfer (IFT) is the medically-supervised movement of a patient '
            '<em>between healthcare facilities</em> by ground ambulance, ordered '
            'by a hospital or health-system transfer center. It is defined by '
            'ORIGIN/DESTINATION (facility-to-facility, not scene or residence) '
            'and by the hospital as the buyer — not by vehicle type alone. It is '
            'a transport category, an ambulance-service line, AND a health-system '
            'operations function at once.</p>'
            '<p class="irs-prose"><strong>Boundary.</strong> Inside: hospital→'
            'hospital up-transfers, hospital→post-acute discharge legs, '
            'facility-origin recurring round-trips, and CCT/SCT (high-acuity IFT). '
            'Outside/adjacent: 911 scene response, air medical, Medicaid NEMT / '
            'wheelchair-van, and residence-origin transport. ' + _chip("FRAMEWORK")
            + '</p>'
            '<p class="irs-sub">Transportation taxonomy — IFT vs the adjacent '
            'categories ' + _chip("ACADEMIC") + '</p>'
            '<div class="irs-wrap"><table class="irs-tab"><thead><tr>'
            f'<th>Dimension</th>{head}</tr></thead><tbody>{body}</tbody>'
            '</table></div>'
            f'<p class="irs-src">Source: {_esc(tm.source_label)}</p>')
        + '</div>')


def _industry_context_block() -> str:
    ic = _rs.industry_context()
    if not ic.available:
        return ""
    cards = "".join(
        f'<div class="irs-card"><h4>{_esc(t)}</h4><p>{_esc(d)}</p></div>'
        for t, d in ic.items)
    return (
        '<div id="rs-industry">'
        + ck_section_header("2. Industry structure (report context)",
                            eyebrow="MARKET RESEARCH")
        + ck_panel(
            '<p class="irs-prose">How the broader ambulance industry is '
            'structured, from the IBISWorld industry report — the qualitative '
            'frame around the ground-IFT slice. ' + _chip("ACADEMIC") + ' '
            '<em>(The report\'s numeric series are chart images; figures on this '
            'page use our GOV / market-research anchors, not invented '
            'industry-report numbers.)</em></p>'
            f'<div class="irs-cardgrid">{cards}</div>'
            f'<p class="irs-src">Source: {_esc(ic.source_label)}</p>')
        + '</div>')


def _ecosystem_block() -> str:
    """Section 3 — patient journey & ecosystem (reused from ift_study)."""
    eco = _st.ecosystem()
    if not eco.available:
        return ""
    jrows = "".join(
        f'<tr><td>{_esc(site)}</td><td>{_esc(role)}</td><td>{_esc(desc)}</td></tr>'
        for site, role, desc in eco.journey)
    parts = "".join(
        f'<div class="irs-card"><h4>{_esc(name)}</h4><p>{_esc(desc)}</p></div>'
        for name, desc in eco.participants)
    anchor = ""
    if eco.n_acute_scenarios or eco.postacute_destinations:
        anchor = (f'<p class="irs-prose">{_chip("SOURCED")} Anchored to '
                  f'{eco.n_acute_scenarios} mapped acute-transfer scenarios and '
                  f'{eco.postacute_destinations:,} real post-acute destinations '
                  '(<a href="/ift-clinical" style="color:var(--sc-teal,#155752);">'
                  'clinical demand engine &rarr;</a>).</p>')
    return (
        '<div id="rs-ecosystem">'
        + ck_section_header("3. Patient journey & ecosystem",
                            eyebrow="MARKET RESEARCH")
        + ck_panel(
            '<p class="irs-prose">IFT is the connective tissue of the acute → '
            'post-acute continuum — every up-transfer to a higher level of care '
            'and every discharge step-down is a mission, with a paired '
            'repatriation leg. ' + _chip("FRAMEWORK") + '</p>'
            '<div class="irs-wrap"><table class="irs-tab"><thead><tr>'
            '<th>Site of care</th><th>Role</th><th>What IFT does</th></tr>'
            f'</thead><tbody>{jrows}</tbody></table></div>' + anchor
            + '<p class="irs-sub">Ecosystem participants ' + _chip("FRAMEWORK")
            + '</p>' + f'<div class="irs-cardgrid">{parts}</div>'
            f'<p class="irs-src">Source: {_esc(eco.source_label)}</p>')
        + '</div>')


def _operating_models_block() -> str:
    """Section 4 — health-system operating models & procurement (reused)."""
    om = _st.operating_models()
    if not om.available:
        return ""
    brows = ""
    for b in om.bands:
        lo = getattr(b, "volume_share_low", None)
        hi = getattr(b, "volume_share_high", None)
        share = (f"{lo*100:.0f}–{hi*100:.0f}%" if lo is not None and hi is not None
                 else "—")
        brows += (f'<tr><td>{_esc(getattr(b, "name", ""))}</td><td>{_esc(share)}</td>'
                  f'<td>{_esc(getattr(b, "definition", ""))}</td>'
                  f'<td>{_esc(getattr(b, "addressable_read", ""))}</td></tr>')
    proc = "".join(
        f'<div class="irs-card"><h4>{_esc(t)}</h4><p>{_esc(d)}</p></div>'
        for t, d in om.procurement)
    pain = "".join(
        f'<div class="irs-card"><h4>{_esc(t)}</h4><p>{_esc(d)}</p></div>'
        for t, d in om.pain_points)
    return (
        '<div id="rs-operating">'
        + ck_section_header("4. Operating models, procurement & pain points",
                            eyebrow="MARKET RESEARCH")
        + ck_panel(
            f'<p class="irs-prose"><strong>{_chip("ILLUSTRATIVE")} '
            f'{_esc(om.classification_note)}</strong></p>'
            '<p class="irs-sub">Operating models — classified by delivered volume '
            + _chip("ILLUSTRATIVE") + '</p>'
            '<div class="irs-wrap"><table class="irs-tab"><thead><tr>'
            '<th>Model</th><th>Volume insourced</th><th>Definition</th>'
            '<th>Addressable read</th></tr></thead>'
            f'<tbody>{brows}</tbody></table></div>'
            '<p class="irs-sub">Procurement ' + _chip("FRAMEWORK") + '</p>'
            f'<div class="irs-cardgrid">{proc}</div>'
            '<p class="irs-sub">Operational pain points ' + _chip("FRAMEWORK")
            + '</p>' + f'<div class="irs-cardgrid">{pain}</div>'
            f'<p class="irs-src">Source: {_esc(om.source_label)}</p>')
        + '</div>')


def _competitive_types_block() -> str:
    """Section 5 — competitive landscape by provider TYPE (market-level, no
    company names; company-specific positioning stays on /ift-study)."""
    ct = _rs.competitor_types()
    if not (ct and ct.available and ct.rows):
        return ""
    head = "".join(f"<th>{_esc(c)}</th>" for c in ct.columns)
    rows = "".join(
        "<tr>" + "".join(f"<td>{_esc(cell)}</td>" for cell in r) + "</tr>"
        for r in ct.rows)
    return (
        '<div id="rs-competitive">'
        + ck_section_header("5. Competitive landscape by provider type",
                            eyebrow="MARKET RESEARCH")
        + ck_panel(
            '<p class="irs-prose">The IFT field by provider TYPE. Most '
            'alternatives are 911-heavy, mixed-model, or subscale; dedicated IFT '
            'competes on facility integration and local density. This brief stays '
            'at the type level — company-specific positioning is on the '
            '<a href="/ift-study" style="color:var(--sc-teal,#155752);">investor '
            'study</a>. ' + _chip("FRAMEWORK") + '</p>'
            '<div class="irs-wrap"><table class="irs-tab"><thead><tr>'
            f'{head}</tr></thead><tbody>{rows}</tbody></table></div>'
            f'<p class="irs-src">Source: {_esc(ct.source_label)}</p>')
        + '</div>')


_REUSED_TOC = [
    ("rs-ecosystem", "Patient journey & ecosystem"),
    ("rs-operating", "Operating models, procurement & pain points"),
    ("rs-competitive", "Competitive landscape by provider type"),
]


def _toc(sections: List[Dict[str, Any]]) -> str:
    links = ['<a href="#rs-definition">1. Market definition &amp; taxonomy</a>',
             '<a href="#rs-industry">2. Industry structure (report context)</a>']
    n = 3
    for anchor, title in _REUSED_TOC:
        links.append(f'<a href="#{anchor}">{n}. {_esc(title)}</a>')
        n += 1
    for sec in sections:
        links.append(f'<a href="#rs-{_esc(sec.get("id",""))}">{n}. '
                     f'{_esc(sec.get("title",""))}</a>')
        n += 1
    return f'<div class="irs-toc">{"".join(links)}</div>'


def _crosslinks() -> str:
    return (
        '<div class="irs-links">'
        '<a href="/ift-study">Investor study (4 dimensions + MMT) &rarr;</a>'
        '<a href="/ift-markets">Geographic markets &amp; TAM/SAM/SOM &rarr;</a>'
        '<a href="/ift-clinical">Clinical demand engine &rarr;</a>'
        '<a href="/api/ift/markets.xlsx" download>Excel data pack &darr;</a>'
        '</div>')


def render_ift_research(qs: Optional[Dict[str, List[str]]] = None) -> str:
    """Render the IFT market-level research brief. Degrades, never raises."""
    sections = _rs.research_sections()
    meta = (f"{5 + len(sections)} sections · market-level (no company-specific "
            "analysis) · every table basis-labelled")
    head = ck_page_title(
        "IFT Market Research Brief",
        eyebrow="INTERFACILITY TRANSPORT · MARKET-LEVEL RESEARCH", meta=meta)
    explainer = (
        '<p class="irs-prose" style="font-size:15px;">A deep, market-level research '
        'brief on ground <strong>interfacility transport (IFT)</strong> — market '
        'definition and taxonomy, the industry structure, patient journeys, health-'
        'system operating models and procurement, operational pain points, '
        'performance metrics, reimbursement, unit economics, the competitive '
        'landscape by type, technology, regulatory factors, growth, segmentation, '
        'sizing methodology, and evidence quality. Deliberately MARKET-focused — no '
        'individual company\'s positioning or footprint. Every table carries an '
        'honesty basis: ' + _chip("GOV") + ' ' + _chip("ACADEMIC") + ' '
        + _chip("ILLUSTRATIVE") + ' ' + _chip("FRAMEWORK") + '.</p>')

    # 1-2 scaffold, 3-5 reused, 6+ authored.
    authored = "".join(_render_section(s, i)
                       for i, s in enumerate(sections, start=6))
    body = "".join([
        _STYLES, head, explainer, _crosslinks(),
        _toc(sections),
        _market_definition_block(),
        _industry_context_block(),
        _ecosystem_block(),
        _operating_models_block(),
        _competitive_types_block(),
        authored,
        _crosslinks(),
        ck_page_actions(),
    ])
    return chartis_shell(
        body, "IFT Market Research Brief", active_nav="/market",
        subtitle="Market-level interfacility-transport research brief")
