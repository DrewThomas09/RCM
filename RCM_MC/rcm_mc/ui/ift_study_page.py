"""IFT Market Study page (``/ift-study``) — the investor-study synthesis.

Answers the SOW's four dimensions (market context taxonomy, the IFT ecosystem,
the health-system POV on operating models, and company positioning) by stitching
the offline IFT modules together. Defaults to the MMT deep-dive; ``?company=<slug>``
swaps Dimension 4 to any competitor in the space. Renders entirely through
``chartis_shell`` + ``ck_*`` — degrades to honest notes, never raises.
"""
from __future__ import annotations

import html as _html
from typing import Dict, List, Optional

from ._chartis_kit import (
    chartis_shell, ck_page_actions, ck_page_title, ck_panel, ck_section_header,
    ck_section_intro,
)
from ._chart_kit import ck_bar_chart, ck_chart_assets, ck_chart_grid, ck_hbar_chart
from ..market_reports import ift_study as _st


def _esc(x: object) -> str:
    return _html.escape(str(x if x is not None else ""))


_BASIS_TITLES = {
    "GOV": "A published government figure (CMS, MedPAC, USRDS, Census).",
    "SOURCED": "Computed from our vendored data.",
    "ACADEMIC": "A published study / analyst estimate.",
    "ILLUSTRATIVE": "Modeled — the basis is named, not a filed figure.",
}


def _chip(basis: str) -> str:
    b = (basis or "ILLUSTRATIVE").upper()
    key = ("GOV" if b.startswith("GOV") else "SOURCED" if b.startswith("SOURCED")
           else "ACADEMIC" if b.startswith("ACADEMIC") else "ILLUSTRATIVE")
    return (f'<span class="ist-chip ist-chip-{key.lower()}" '
            f'title="{_esc(_BASIS_TITLES[key])}">{key}</span>')


def _src(label: str) -> str:
    return f'<p class="ist-src">Source: {_esc(label)}</p>' if label else ""


_STYLES = """<style>
.ist-chip{display:inline-block;font-family:var(--sc-mono,Consolas,monospace);
font-size:9px;font-weight:600;letter-spacing:.06em;padding:1px 6px;border-radius:2px;
vertical-align:middle;}
.ist-chip-gov{background:#e7efe9;color:#154e36;}
.ist-chip-sourced{background:#e9eef5;color:#243b57;}
.ist-chip-academic{background:#efeae0;color:#6b5426;}
.ist-chip-illustrative{background:#f3ecd9;color:#7a5c1a;}
.ist-src{font-family:var(--sc-mono,Consolas,monospace);font-size:10px;
color:var(--sc-muted,#6b6357);margin:6px 0 2px;line-height:1.5;}
.ist-prose{font-family:var(--sc-serif,Georgia,serif);font-size:14px;line-height:1.62;
color:var(--sc-text,#1a2332);max-width:88ch;margin:0 0 10px;}
.ist-sub{font-family:var(--sc-mono,Consolas,monospace);font-size:11px;font-weight:600;
letter-spacing:.08em;text-transform:uppercase;color:var(--sc-teal,#155752);
margin:16px 0 8px;}
.ist-wrap{overflow-x:auto;margin:6px 0 12px;}
.ist-tab{border-collapse:collapse;width:100%;font-size:12.5px;
font-family:var(--sc-sans,Inter,system-ui,sans-serif);}
.ist-tab th,.ist-tab td{border:1px solid var(--sc-border,#e4dccb);padding:7px 10px;
text-align:left;vertical-align:top;line-height:1.45;}
.ist-tab thead th{background:var(--sc-navy,#0b2341);color:#fff;font-weight:600;
font-size:11px;letter-spacing:.02em;position:sticky;top:0;}
.ist-tab .ist-rowlabel{background:var(--sc-surface,#faf7f1);font-weight:600;
white-space:nowrap;}
.ist-tab td.ist-ift,.ist-tab th.ist-ift{background:#eef5f1;
box-shadow:inset 3px 0 0 var(--sc-teal,#155752),inset -3px 0 0 var(--sc-teal,#155752);}
.ist-tab th.ist-ift{background:#12463a;}
.ist-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));
gap:12px;margin:6px 0 14px;}
.ist-card{border:1px solid var(--sc-border,#e4dccb);border-left:3px solid
var(--sc-teal,#155752);border-radius:4px;padding:12px 14px;
background:var(--sc-surface,#faf7f1);}
.ist-card h4{font-family:var(--sc-serif,Georgia,serif);font-size:14.5px;
margin:0 0 5px;color:var(--sc-text,#1a2332);}
.ist-card p{font-family:var(--sc-serif,Georgia,serif);font-size:13px;line-height:1.55;
margin:0;color:var(--sc-text,#2a3340);}
.ist-companybar{display:flex;flex-wrap:wrap;gap:7px;margin:8px 0 14px;}
.ist-companybar a{font-family:var(--sc-mono,Consolas,monospace);font-size:11px;
font-weight:600;letter-spacing:.03em;text-decoration:none;padding:5px 11px;
border-radius:3px;border:1px solid var(--sc-border,#e4dccb);
color:var(--sc-teal,#155752);background:#fff;}
.ist-companybar a.on{background:var(--sc-teal,#155752);color:#fff;
border-color:var(--sc-teal,#155752);}
.ist-companybar a.subject{border-color:var(--sc-teal,#155752);}
.ist-links{display:flex;flex-wrap:wrap;gap:16px;margin:14px 0 4px;
font-family:var(--sc-mono,Consolas,monospace);font-size:11px;font-weight:600;}
.ist-links a{color:var(--sc-teal,#155752);text-decoration:none;}
.ist-dl a{display:inline-block;font-family:var(--sc-mono,Consolas,monospace);
font-size:12px;font-weight:600;letter-spacing:.04em;text-decoration:none;color:#fff;
background:var(--sc-teal,#155752);padding:8px 15px;border-radius:3px;}
</style>"""


# ── Dimension 1 — Market context ─────────────────────────────────────────────
def _dimension1() -> str:
    tm = _st.taxonomy_matrix()
    if not tm.available:
        return ""
    ncol = len(tm.columns)
    head = "".join(
        f'<th class="{"ist-ift" if i == tm.ift_col_index else ""}">{_esc(c)}</th>'
        for i, c in enumerate(tm.columns))
    body = ""
    for label, cells in tm.rows:
        tds = "".join(
            f'<td class="{"ist-ift" if i == tm.ift_col_index else ""}">{_esc(v)}</td>'
            for i, v in enumerate(cells))
        body += (f'<tr><th class="ist-rowlabel">{_esc(label)}</th>{tds}</tr>')
    matrix = (
        '<div class="ist-wrap"><table class="ist-tab"><thead><tr>'
        f'<th>Dimension</th>{head}</tr></thead><tbody>{body}</tbody></table></div>'
        + f'<p class="ist-prose">{_chip("ACADEMIC")} {_esc(tm.note)}</p>'
        + _src(tm.source_label))
    why = "".join(
        f'<div class="ist-card"><h4>{_esc(t)}</h4><p>{_esc(d)}</p></div>'
        for t, d in tm.why_dedicated_different)
    return (
        ck_section_header(
            "Dimension 1 — Market context",
            eyebrow="THE TAXONOMY: IFT IS NOT 911 / NEMT / AIR")
        + ck_panel(
            '<p class="ist-prose"><strong>IFT is a hospital-ordered B2B operating '
            'service</strong> — the medically-supervised movement of patients '
            '<em>between facilities</em> by ground ambulance, ordered by hospital '
            'transfer centers. It is distinct from consumer 911, from specialty '
            'critical-care transport (a tier <em>within</em> IFT), from air, and '
            'from the Medicaid NEMT benefit. The matrix below is the market '
            'framework the rest of the study rests on — the IFT column is '
            'highlighted.</p>'
            + matrix
            + '<p class="ist-sub">Why dedicated IFT competes on different '
              'dimensions — a sustainable advantage</p>'
            + f'<div class="ist-grid">{why}</div>'))


# ── Dimension 2 — IFT ecosystem ──────────────────────────────────────────────
def _dimension2() -> str:
    eco = _st.ecosystem()
    if not eco.available:
        return ""
    jrows = "".join(
        f'<tr><th class="ist-rowlabel">{_esc(site)}</th>'
        f'<td>{_esc(role)}</td><td>{_esc(desc)}</td></tr>'
        for site, role, desc in eco.journey)
    journey = (
        '<div class="ist-wrap"><table class="ist-tab"><thead><tr>'
        '<th>Site of care</th><th>Role in the journey</th><th>What IFT does</th>'
        f'</tr></thead><tbody>{jrows}</tbody></table></div>')
    parts = "".join(
        f'<div class="ist-card"><h4>{_esc(name)}</h4><p>{_esc(desc)}</p></div>'
        for name, desc in eco.participants)
    anchors = ""
    if eco.n_acute_scenarios or eco.postacute_destinations:
        anchors = (
            f'<p class="ist-prose">{_chip("SOURCED")} Anchored to the real '
            f'clinical spine: <strong>{eco.n_acute_scenarios}</strong> mapped '
            f'acute-transfer scenarios and <strong>{eco.postacute_destinations:,}'
            '</strong> SOURCED post-acute destinations '
            '(<a href="/ift-clinical" style="color:var(--sc-teal,#155752);">the '
            'clinical demand engine &rarr;</a>).</p>')
    return (
        ck_section_header(
            "Dimension 2 — The IFT ecosystem",
            eyebrow="THE PATIENT JOURNEY + THE PARTICIPANTS")
        + ck_panel(
            '<p class="ist-prose">IFT is the connective tissue of the acute → '
            'post-acute continuum. Every up-transfer to a higher level of care '
            'and every discharge step-down is a mission — and each escalation '
            'implies a paired repatriation leg. The journey runs from the '
            'community/referring hospital and ED through the tertiary hub to '
            'IRF / LTACH / SNF and home / hospice.</p>'
            + journey + anchors
            + '<p class="ist-sub">The participants transport connects</p>'
            + f'<div class="ist-grid">{parts}</div>'
            + _src(eco.source_label)))


# ── Dimension 3 — Health-system POV ──────────────────────────────────────────
def _dimension3() -> str:
    om = _st.operating_models()
    if not om.available:
        return ""
    band_tbl = ""
    if om.bands:
        brows = ""
        for b in om.bands:
            lo = getattr(b, "volume_share_low", None)
            hi = getattr(b, "volume_share_high", None)
            share = (f"{lo*100:.0f}–{hi*100:.0f}%" if lo is not None
                     and hi is not None else "—")
            brows += (
                f'<tr><th class="ist-rowlabel">{_esc(getattr(b, "name", ""))}</th>'
                f'<td>{_esc(share)}</td>'
                f'<td>{_esc(getattr(b, "definition", ""))}</td>'
                f'<td>{_esc(getattr(b, "addressable_read", ""))}</td></tr>')
        band_tbl = (
            '<p class="ist-sub">Operating models — classified by delivered '
            'transport VOLUME</p>'
            '<div class="ist-wrap"><table class="ist-tab"><thead><tr>'
            '<th>Model</th><th>Volume share insourced</th><th>Definition</th>'
            '<th>Addressable read</th></tr></thead>'
            f'<tbody>{brows}</tbody></table></div>')
    proc = "".join(
        f'<div class="ist-card"><h4>{_esc(t)}</h4><p>{_esc(d)}</p></div>'
        for t, d in om.procurement)
    pain = "".join(
        f'<div class="ist-card"><h4>{_esc(t)}</h4><p>{_esc(d)}</p></div>'
        for t, d in om.pain_points)
    return (
        ck_section_header(
            "Dimension 3 — The health-system POV",
            eyebrow="INSOURCED / OUTSOURCED / HYBRID · PROCUREMENT · PAIN")
        + ck_panel(
            f'<p class="ist-prose"><strong>{_chip("ILLUSTRATIVE")} '
            f'{_esc(om.classification_note)}</strong></p>'
            + band_tbl
            + '<p class="ist-sub">How health systems procure transportation</p>'
            + f'<div class="ist-grid">{proc}</div>'
            + '<p class="ist-sub">The operational pain under current models '
              '(detailed in the market page)</p>'
            + f'<div class="ist-grid">{pain}</div>'
            + f'<p class="ist-prose">{_esc(om.note)}</p>'
            + _src(om.source_label)))


# ── Dimension 4 — Company positioning ────────────────────────────────────────
def _company_bar(pos) -> str:
    links = ""
    for c in pos.field_:
        cls = "on subject" if c.slug == pos.subject.slug else (
            "subject" if c.is_subject else "")
        star = " ★" if c.is_subject else ""
        links += (f'<a class="{cls}" href="/ift-study?company={_esc(c.slug)}">'
                  f'{_esc(c.name)}{star}</a>')
    return ('<p class="ist-sub">Company positioning — pick a player (★ = the '
            'deep-dive subject, MMT)</p>'
            f'<div class="ist-companybar">{links}</div>')


def _dimension4(pos) -> str:
    if not pos.available:
        return ""
    c = pos.subject
    fp = (", ".join(c.footprint_markets) if c.footprint_markets
          else "outside the 20-metro footprint")
    svc = "".join(f"<li>{_esc(s)}</li>" for s in c.services)
    subject_block = (
        f'<div class="ist-card" style="border-left-width:4px;">'
        f'<h4>{_esc(c.name)} — {_esc(c.archetype)}'
        f'{" ★ deep-dive subject" if c.is_subject else ""}</h4>'
        f'<p><strong>HQ.</strong> {_esc(c.hq)}<br>'
        f'<strong>Footprint.</strong> {_esc(c.footprint)}<br>'
        f'<strong>In-footprint metros.</strong> {_esc(fp)} '
        f'<em style="font-size:11px;color:var(--sc-muted,#6b6357);">(registry read '
        f'over public-web operator names)</em><br>'
        f'<strong>Operating model.</strong> {_esc(c.operating_model)}<br>'
        f'<strong>Customer relationships.</strong> {_esc(c.customer_relationships)}'
        f'<br><strong>Dedicated vs EMS.</strong> {_esc(c.dedicated_vs_ems)}<br>'
        f'<strong>Strategic role.</strong> {_esc(c.strategic_role)}<br>'
        f'<strong>vs MMT.</strong> {_esc(c.mmt_contrast)}</p>'
        f'<p style="margin-top:6px;"><strong>Services.</strong></p>'
        f'<ul style="margin:2px 0 0 18px;font-family:var(--sc-serif,Georgia,serif);'
        f'font-size:13px;line-height:1.5;">{svc}</ul></div>')

    # MMT structured pillars (only rendered when MMT is the subject / always shown
    # as the reference model).
    pillars_block = ""
    mp = pos.mmt_positioning
    if mp is not None and getattr(mp, "available", False) and mp.pillars:
        prow = ""
        for p in mp.pillars:
            prow += (
                f'<tr><th class="ist-rowlabel">{_esc(getattr(p, "pillar", ""))}</th>'
                f'<td>{_esc(getattr(p, "mmt_stance", ""))}</td>'
                f'<td>{_esc(getattr(p, "vs_alternatives", ""))}</td></tr>')
        pillars_block = (
            '<p class="ist-sub">The dedicated-partnership model — MMT stickiness '
            'pillars</p>'
            '<div class="ist-wrap"><table class="ist-tab"><thead><tr>'
            '<th>Pillar</th><th>MMT stance</th><th>vs the alternatives</th>'
            f'</tr></thead><tbody>{prow}</tbody></table></div>')

    # The competitive field table.
    frows = ""
    for f in pos.field_:
        nfp = len(f.footprint_markets)
        frows += (
            f'<tr><th class="ist-rowlabel">{_esc(f.name)}'
            f'{" ★" if f.is_subject else ""}</th>'
            f'<td>{_esc(f.archetype)}</td>'
            f'<td>{nfp}</td>'
            f'<td>{_esc(f.dedicated_vs_ems)}</td></tr>')
    field_tbl = (
        '<p class="ist-sub">The competitive field — every player, positioned</p>'
        '<div class="ist-wrap"><table class="ist-tab"><thead><tr>'
        '<th>Company</th><th>Archetype</th><th>Footprint metros</th>'
        '<th>Dedicated vs EMS</th></tr></thead>'
        f'<tbody>{frows}</tbody></table></div>')

    return (
        ck_section_header(
            "Dimension 4 — Company positioning",
            eyebrow="MMT (THE SUBJECT) vs THE FIELD")
        + ck_panel(
            '<p class="ist-prose">MMT is the dedicated outsourced IFT partner — '
            'the model that treats hospital patient movement as a <em>strategic '
            'operating capability</em>, not a transactional ride. Every other '
            'player is positioned against it: national 911-first platforms, '
            'scaled regional privates, and insourced hospital programs.</p>'
            + _company_bar(pos)
            + subject_block
            + pillars_block
            + field_tbl
            + f'<p class="ist-prose">{_esc(pos.note)}</p>'
            + _src(pos.source_label)))


# ── Visuals ──────────────────────────────────────────────────────────────────
def _study_charts(pos) -> str:
    cards: List[str] = []
    try:
        items = [(c.name, float(len(c.footprint_markets)),
                  "teal" if c.is_subject else "navy") for c in pos.field_]
        items = [it for it in items if it[1] > 0]
        if items:
            items.sort(key=lambda t: t[1], reverse=True)
            cards.append(ck_hbar_chart(
                "Competitive footprint (metros in our 20-market set)", items,
                value_fmt=lambda v: f"{int(v)}",
                subtitle="Where each player appears across the target footprint "
                         "(registry read over public-web operator names).",
                source="ift_study · ift_geo public-web operator registry",
                label_w=210.0))
    except Exception:  # noqa: BLE001
        pass
    try:
        from ..market_reports import ift_analytics as _an
        tam = _an.ground_tam(); hs = _an.health_system_sam()
        if tam.available and hs.available:
            cards.append(ck_bar_chart(
                "The prize: TAM / SAM / SOM ($M)", [
                    ("TAM", tam.allpayer_tam_bn_central * 1000.0, "navy"),
                    ("SAM", hs.sam_central_bn * 1000.0, "teal"),
                    ("SOM", hs.som_central_m, "positive")],
                value_fmt=lambda v: (f"${v/1000:,.1f}B" if v >= 1000
                                     else f"${v:,.0f}M"),
                subtitle="All ground IFT → multi-hospital health systems → the "
                         "operator footprint (ILLUSTRATIVE).",
                source="ift_analytics · full build on /ift-markets"))
    except Exception:  # noqa: BLE001
        pass
    grid = ck_chart_grid(*cards)
    return grid or ""


def _crosslinks() -> str:
    return (
        '<div class="ist-links">'
        '<a href="/ift-markets">Geographic markets &amp; TAM/SAM/SOM &rarr;</a>'
        '<a href="/ift-clinical">Clinical demand engine &rarr;</a>'
        '<a href="/market/interfacility_transport">Full IFT market report &rarr;</a>'
        '</div>'
        '<div class="ist-dl" style="margin:12px 0 4px;">'
        '<a href="/api/ift/markets.xlsx" download>Download the investor data '
        'pack (Excel) &darr;</a></div>')


def render_ift_study(qs: Optional[Dict[str, List[str]]] = None) -> str:
    """Render the IFT Market Study page. ``?company=<slug>`` selects the
    Dimension-4 subject (default MMT). Degrades but never raises."""
    company_slug = None
    if qs:
        vals = qs.get("company")
        if vals:
            company_slug = vals[0]
    pos = _st.company_positioning(company_slug)
    summ = _st.study_summary()

    meta = (f"4 dimensions · {summ['n_taxonomy_modalities']} transport modalities "
            f"× {summ['n_taxonomy_dimensions']} axes · {summ['n_companies']} "
            f"companies · subject: {pos.subject.name}")
    head = ck_page_title(
        "IFT Market Study", eyebrow="INTERFACILITY TRANSPORT · INVESTOR STUDY",
        meta=meta)
    explainer = (
        '<p class="ist-prose" style="font-size:15px;">An investor-ready market '
        'study for the ground <strong>interfacility transport (IFT)</strong> '
        'space: what the market is, how big it is and why it grows, how health '
        'systems buy it, and how <strong>Midwest Medical Transport (MMT)</strong> '
        'is positioned. Every figure carries an honesty basis chip — '
        f'{_chip("GOV")} {_chip("SOURCED")} {_chip("ACADEMIC")} {_chip("ILLUSTRATIVE")} '
        '— and the four dimensions synthesize the sized market pages and the '
        'downloadable data pack below.</p>')

    body = "".join([
        _STYLES,
        ck_chart_assets(),
        head,
        explainer,
        _crosslinks(),
        ck_section_intro(
            "THE FRAMEWORK", "Four dimensions, one market thesis.",
            italic_word="Four",
            body=("Market context (what IFT is and why it is its own market), "
                  "the ecosystem (the patient journey it connects), the "
                  "health-system POV (how it is delivered and bought), and "
                  "company positioning (MMT vs the field).")),
        _study_charts(pos),
        _dimension1(),
        _dimension2(),
        _dimension3(),
        _dimension4(pos),
        _crosslinks(),
        ck_page_actions(),
    ])
    return chartis_shell(
        body, "IFT Market Study", active_nav="/market",
        subtitle="Investor market study · IFT market, ecosystem, health-system "
                 "POV, and company positioning")
