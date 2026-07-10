"""IFT diligence question architecture page (``/ift-diligence``).

Renders the study's *question tree* — the layer behind the answered pages. For
every SOW slide it lays out the underlying main question, the sub-question tree,
the data / evidence that would prove the point, the persuasive visuals, and —
the value add over a static outline — a live cross-link to WHERE ON THIS PLATFORM
the answer already lives, plus the real connector datasets that feed the
evidence.

Reads :mod:`ift_diligence` (authored FRAMEWORK content) and resolves its
connector references against the live :mod:`ift_connectors` estate. Renders
entirely through ``chartis_shell`` + ``ck_*`` primitives; degrades to honest
notes and never raises.

Public API:
    render_ift_diligence(qs=None) -> str
"""
from __future__ import annotations

import html as _html
from typing import Dict, List, Optional, Tuple

from ._chartis_kit import (
    chartis_shell, ck_eyebrow, ck_next_section, ck_page_actions, ck_page_title,
    ck_panel, ck_section_header, ck_section_intro,
)
from ..market_reports import ift_diligence as _dg


def _esc(x: object) -> str:
    return _html.escape(str(x if x is not None else ""))


# ── Honesty chips (scoped ifq- classes) ──────────────────────────────────────
_BASIS_TITLES = {
    "FRAMEWORK": "An analytic framework / diligence question, not a figure.",
    "SOURCED": "Live — computed from our vendored / ingested estate.",
    "CONNECTOR": "A registered connector dataset — ingest-ready, honest fallback "
                 "offline.",
    "GOV": "A published government anchor (CMS, MedPAC, BLS, statute).",
    "ACADEMIC": "Authored market knowledge / a published study.",
    "ILLUSTRATIVE": "Modeled — the basis is named, not a filed figure.",
}
_BASIS_CLASS = {"FRAMEWORK": "framework", "SOURCED": "sourced",
                "CONNECTOR": "connector", "GOV": "gov",
                "ACADEMIC": "academic", "ILLUSTRATIVE": "illustrative"}


def _chip(basis: str) -> str:
    b = (basis or "FRAMEWORK").upper()
    key = b if b in _BASIS_TITLES else "FRAMEWORK"
    return (f'<span class="ifq-chip ifq-chip-{_BASIS_CLASS[key]}" '
            f'title="{_esc(_BASIS_TITLES[key])}">{key}</span>')


def _link_row(pairs: Tuple[Tuple[str, str], ...], *, label: str) -> str:
    """A row of arrow cross-links (label → href) into the live answer surfaces."""
    if not pairs:
        return ""
    links = "".join(
        f'<a href="{_esc(href)}">{_esc(txt)} &rarr;</a>' for txt, href in pairs)
    return (f'<div class="ifq-answer"><span class="ifq-answer-lab">{_esc(label)}'
            f'</span><div class="ifq-links">{links}</div></div>')


def _connector_chips(keys: Tuple[str, ...], ce) -> str:
    """Resolve slide/evidence connector keys to linked evidence chips. Drops any
    key that no longer resolves in the live estate (degrade, never break)."""
    if not (ce and ce.available and keys):
        return ""
    chips: List[str] = []
    for k in keys:
        p = ce.probes_by_key.get(k)
        if p is None:
            continue
        live = getattr(p, "available", False)
        cls = "ifq-cx-live" if live else "ifq-cx-gated"
        status = "LIVE" if live else "INGEST-READY"
        href = "/connector-estate?dataset=" + _esc(getattr(p, "dataset_id", ""))
        chips.append(
            f'<a class="ifq-cx {cls}" href="{href}" '
            f'title="{_esc(getattr(p, "ift_signal", ""))}">'
            f'{_esc(getattr(p, "title", k))} '
            f'<span class="ifq-cx-st">{status}</span></a>')
    if not chips:
        return ""
    return ('<div class="ifq-cxrow"><span class="ifq-cx-lab">Feeds from our '
            'connector estate</span>' + "".join(chips) + '</div>')


def _qgroup(group) -> str:
    lis = "".join(f"<li>{_esc(q)}</li>" for q in group.questions)
    return (f'<p class="ifq-sub">{_esc(group.heading)}</p>'
            f'<ul class="ifq-list">{lis}</ul>')


def _bullets(items, *, heading: str) -> str:
    if not items:
        return ""
    lis = "".join(f"<li>{_esc(it)}</li>" for it in items)
    return (f'<p class="ifq-sub">{_esc(heading)}</p>'
            f'<ul class="ifq-list ifq-list-plain">{lis}</ul>')


# ── Inline ANSWERS — pulled from the SAME sized modules the other pages read, so
#    each slide is question + answer in one place. Every builder degrades to ""
#    (never raises) and carries an honesty basis + source line. ────────────────
def _usd_b(x) -> str:
    try:
        return f"${float(x):,.2f}B"
    except (TypeError, ValueError):
        return "—"


def _usd_m(x) -> str:
    try:
        return f"${float(x) / 1e6:,.1f}M"
    except (TypeError, ValueError):
        return "—"


def _pct(x) -> str:
    try:
        return f"{float(x) * 100:.1f}%"
    except (TypeError, ValueError):
        return "—"


def _stat(value: str, label: str) -> str:
    return (f'<div class="ifq-stat"><div class="ifq-stat-v">{value}</div>'
            f'<div class="ifq-stat-l">{_esc(label)}</div></div>')


def _ans_wrap(inner: str, *, basis: str = "FRAMEWORK", source: str = "") -> str:
    if not inner:
        return ""
    src = (f'<p class="ifq-prompt" style="margin-top:2px;">Answer source: '
           f'{_esc(source)}</p>' if source else "")
    return ('<div class="ifq-ans"><span class="ifq-ans-lab">The answer, in this '
            f'study {_chip(basis)}</span>' + inner + src + '</div>')


def _ans_table(headers, rows, *, ift_col=None) -> str:
    def _cell(tag, i, v):
        cls = ' class="ifq-ift"' if ift_col is not None and i == ift_col else ""
        return f'<{tag}{cls}>{_esc(v)}</{tag}>'
    head = "".join(_cell("th", i, h) for i, h in enumerate(headers))
    body = "".join(
        "<tr>" + "".join(_cell("td", i, v) for i, v in enumerate(r)) + "</tr>"
        for r in rows)
    return ('<div class="ifq-wrap"><table class="ifq-tab"><thead><tr>'
            f'{head}</tr></thead><tbody>{body}</tbody></table></div>')


def _ans_cards(pairs) -> str:
    return ('<div class="ifq-grid">' + "".join(
        f'<div class="ifq-card"><h4>{_esc(t)}</h4><p>{_esc(d)}</p></div>'
        for t, d in pairs) + '</div>')


def _ans_cover() -> str:
    return _ans_wrap(
        '<p class="ifq-prose">This is a <strong>market-definition + '
        'commercial-diligence</strong> study with a company overlay: it defines '
        'the IFT market, sizes it, shows how health systems buy it, and positions '
        '<strong>MMT</strong> as the dedicated partner. Intended audience: the '
        'deal team / IC. Subject operator: MMT.</p>',
        basis="FRAMEWORK",
        source="Study framing (full synthesis on /ift-study)")


def _ans_vocabulary() -> str:
    from ..market_reports import ift_study as _st
    tm = _st.taxonomy_matrix()
    if not tm.available:
        return ""
    use = dict(tm.rows).get("Key use cases") or tm.rows[0][1]
    rows = [(col, use[i]) for i, col in enumerate(tm.columns)]
    return _ans_wrap(
        '<p class="ifq-prose">The five transport categories the study fixes as '
        'shared vocabulary — IFT is the facility-ordered, between-sites middle '
        'tier, distinct from 911, CCT (a tier <em>within</em> IFT), air, and '
        'NEMT.</p>'
        + _ans_table(("Category", "What it means — the key use case"), rows),
        basis="ACADEMIC", source=tm.source_label)


def _ans_definition() -> str:
    from ..market_reports import ift_study as _st
    tm = _st.taxonomy_matrix()
    tam_line = ""
    try:
        from ..market_reports import ift_analytics as _an
        t = _an.ground_tam()
        if getattr(t, "available", False):
            tam_line = (
                '<p class="ifq-prose">Sized boundary: TAM = all US ground '
                'interfacility ambulance = <strong>'
                f'{_usd_b(t.allpayer_tam_bn_central)}</strong> {_chip("FRAMEWORK")}'
                ' — excludes 911, air, and NEMT.</p>')
    except Exception:  # noqa: BLE001
        pass
    inside = ("Hospital→hospital up-transfers (stroke, STEMI, trauma, NICU); "
              "hospital→post-acute discharge legs (SNF / IRF / LTCH); "
              "facility-origin CCT / SCT; repatriation return legs.")
    outside = ("911 / scene response; air ambulance; Medicaid NEMT / "
               "wheelchair van; residence-origin and courier / organ transport.")
    return _ans_wrap(
        '<p class="ifq-prose"><strong>IFT is ambulance transport BETWEEN '
        'healthcare facilities, ordered by hospitals and health systems</strong> — '
        'defined by origin/destination and the hospital-as-buyer, not by vehicle '
        'type alone.</p>' + tam_line
        + _ans_table(("Inside core IFT", "Outside / adjacent"),
                     [(inside, outside)]),
        basis="FRAMEWORK",
        source=(tm.source_label if tm.available else ""))


def _ans_taxonomy() -> str:
    # DIGEST — the full 5-category × N-dimension matrix renders once, on
    # /ift-study (Dimension 1); the vocabulary block above already gives
    # the category one-liners.
    from ..market_reports import ift_study as _st
    tm = _st.taxonomy_matrix()
    if not tm.available:
        return ""
    dims = " · ".join(label for label, _cells in tm.rows)
    return _ans_wrap(
        f'<p class="ifq-prose">{_esc(tm.note)} The matrix compares the five '
        f'categories across: <strong>{_esc(dims)}</strong> — the full table '
        'lives on the <a href="/ift-study">investor study (Dimension 1)</a>, '
        'its single home.</p>',
        basis="ACADEMIC", source=tm.source_label + " · full matrix on /ift-study")


def _ans_markets_contrast() -> str:
    from ..market_reports import ift_study as _st
    tm = _st.taxonomy_matrix()
    if not tm.available:
        return ""
    idx = [0, tm.ift_col_index, len(tm.columns) - 1]      # 911 · IFT · NEMT
    headers = ("Dimension",) + tuple(tm.columns[i] for i in idx)
    rows = [(label,) + tuple(cells[i] for i in idx) for label, cells in tm.rows]
    return _ans_wrap(
        '<p class="ifq-prose">The three commercial markets side by side — same '
        'trucks, different customers, buyers, dispatch, payers, and failure '
        'modes.</p>' + _ans_table(headers, rows, ift_col=2),
        basis="ACADEMIC", source=tm.source_label)


def _ans_why_dedicated() -> str:
    from ..market_reports import ift_study as _st
    tm = _st.taxonomy_matrix()
    cards = _ans_cards(tm.why_dedicated_different) if (
        tm.available and tm.why_dedicated_different) else ""
    moat = ""
    try:
        from ..market_reports import ift_moat as _mo
        mf = _mo.moat_factors()
        if mf:
            moat = ('<p class="ifq-sub">The moat, factor by factor '
                    + _chip("FRAMEWORK") + '</p>'
                    + _ans_table(("Factor", "Why it makes the incumbent sticky"),
                                 [(f.name, f.why_it_matters) for f in mf]))
    except Exception:  # noqa: BLE001
        pass
    if not (cards or moat):
        return ""
    return _ans_wrap(cards + moat, basis="FRAMEWORK",
                     source=(tm.source_label if tm.available else ""))


def _ans_journey() -> str:
    # DIGEST — the full journey table renders once, on /ift-study; this
    # inline answer keeps the sourced anchor counts + the site list.
    from ..market_reports import ift_study as _st
    eco = _st.ecosystem()
    if not eco.available:
        return ""
    sites = " → ".join(row[0] for row in eco.journey)
    anchor = ""
    if eco.n_acute_scenarios or eco.postacute_destinations:
        anchor = (f'<p class="ifq-prose">{_chip("SOURCED")} Anchored to '
                  f'<strong>{eco.n_acute_scenarios}</strong> mapped acute-transfer '
                  f'scenarios and <strong>{eco.postacute_destinations:,}</strong> '
                  'real post-acute destinations.</p>')
    return _ans_wrap(
        f'<p class="ifq-prose">The continuum IFT connects: <strong>'
        f'{_esc(sites)}</strong> — each site\'s role and what IFT does there '
        'is tabled on the <a href="/ift-study">investor study (Dimension '
        '2)</a>, its single home.</p>' + anchor,
        basis="FRAMEWORK", source=eco.source_label + " · full table on /ift-study")


def _ans_participants() -> str:
    # DIGEST — participant cards render once, on /ift-study.
    from ..market_reports import ift_study as _st
    eco = _st.ecosystem()
    if not eco.available:
        return ""
    names = " · ".join(t for t, _d in eco.participants)
    return _ans_wrap(
        f'<p class="ifq-prose">Ecosystem participants: <strong>{_esc(names)}'
        '</strong> — each unpacked on the <a href="/ift-study">investor '
        'study (Dimension 2)</a>.</p>',
        basis="FRAMEWORK", source=eco.source_label)


def _ans_operating() -> str:
    # DIGEST — the full band taxonomy (definitions + addressable reads)
    # renders once, on /ift-study (2026-07-10 dedup); this inline answer
    # keeps the band names/shares and links to the canonical render.
    from ..market_reports import ift_study as _st
    om = _st.operating_models()
    if not (om.available and om.bands):
        return ""
    rows = []
    for b in om.bands:
        lo = getattr(b, "volume_share_low", None)
        hi = getattr(b, "volume_share_high", None)
        share = (f"{lo * 100:.0f}–{hi * 100:.0f}%"
                 if lo is not None and hi is not None else "—")
        rows.append((getattr(b, "name", ""), share))
    return _ans_wrap(
        f'<p class="ifq-prose"><strong>{_esc(om.classification_note)}</strong> '
        'Band names and volume shares below; the full taxonomy — '
        'definitions and per-band addressable reads — lives on the '
        '<a href="/ift-study">investor study (Dimension 3)</a>, its single '
        'home.</p>'
        + _ans_table(("Model", "Volume insourced"), rows),
        basis="FRAMEWORK", source=om.source_label + " · full taxonomy on /ift-study")


def _ans_procurement() -> str:
    # DIGEST — procurement mechanics render in full on /ift-study.
    from ..market_reports import ift_study as _st
    om = _st.operating_models()
    if not (om.available and om.procurement):
        return ""
    titles = " · ".join(t for t, _d in om.procurement)
    return _ans_wrap(
        f'<p class="ifq-prose">Procurement mechanics: <strong>{_esc(titles)}'
        '</strong> — each unpacked on the '
        '<a href="/ift-study">investor study (Dimension 3)</a>.</p>',
        basis="FRAMEWORK", source=om.source_label)


def _ans_challenges() -> str:
    # DIGEST — operational pain points render in full on /ift-study.
    from ..market_reports import ift_study as _st
    om = _st.operating_models()
    if not (om.available and om.pain_points):
        return ""
    titles = " · ".join(t for t, _d in om.pain_points)
    return _ans_wrap(
        f'<p class="ifq-prose">Operational pain points: <strong>{_esc(titles)}'
        '</strong> — each unpacked on the '
        '<a href="/ift-study">investor study (Dimension 3)</a>.</p>',
        basis="FRAMEWORK", source=om.source_label)


def _ans_mmt() -> str:
    from ..market_reports import ift_study as _st
    pos = _st.company_positioning("mmt")
    if not pos.available:
        return ""
    c = pos.subject
    fp = ", ".join(c.footprint_markets) if c.footprint_markets else "—"
    svc = "".join(f"<li>{_esc(s)}</li>" for s in c.services)
    body = (
        '<div class="ifq-card" style="border-left-width:4px;">'
        f'<h4>{_esc(c.name)} — {_esc(c.archetype)}</h4>'
        f'<p><strong>HQ.</strong> {_esc(c.hq)}<br>'
        f'<strong>Footprint.</strong> {_esc(c.footprint)}<br>'
        f'<strong>In-footprint metros.</strong> {_esc(fp)}<br>'
        f'<strong>Operating model.</strong> {_esc(c.operating_model)}<br>'
        f'<strong>Customers.</strong> {_esc(c.customer_relationships)}<br>'
        f'<strong>Dedicated vs EMS.</strong> {_esc(c.dedicated_vs_ems)}<br>'
        f'<strong>Strategic role.</strong> {_esc(c.strategic_role)}</p>'
        '<p style="margin-top:6px;"><strong>Services.</strong></p>'
        f'<ul class="ifq-list" style="margin-left:16px;">{svc}</ul></div>')
    return _ans_wrap(body, basis="FRAMEWORK", source=pos.source_label)


def _ans_dedicated() -> str:
    from ..market_reports import ift_study as _st
    pos = _st.company_positioning("mmt")
    if not pos.available:
        return ""
    parts: List[str] = []
    mp = pos.mmt_positioning
    if mp is not None and getattr(mp, "available", False) and mp.pillars:
        # DIGEST — the full pillar table (stance + vs-alternatives) renders
        # once, on /ift-study (Dimension 4); names + link here.
        names = " · ".join(getattr(p, "pillar", "") for p in mp.pillars)
        parts.append(
            '<p class="ifq-prose">The dedicated-partnership pillars: '
            f'<strong>{_esc(names)}</strong> — each stance and its read vs '
            'alternatives is tabled on the <a href="/ift-study">investor '
            'study (Dimension 4)</a>, its single home.</p>')
    if pos.field_:
        # DIGEST — the positioned field table renders once, on /ift-study;
        # names + archetypes here.
        names = " · ".join(
            f.name + (" ★" if f.is_subject else "") for f in pos.field_)
        parts.append(
            '<p class="ifq-prose">The positioned field: '
            f'<strong>{_esc(names)}</strong> — archetypes, footprints and '
            'the dedicated-vs-EMS read are tabled on the '
            '<a href="/ift-study">investor study (Dimension 4)</a>.</p>')
    if not parts:
        return ""
    return _ans_wrap("".join(parts), basis="FRAMEWORK", source=pos.source_label)


def _ans_strategic() -> str:
    rows = [
        ("Call-around across many vendors", "One accountable dedicated partner"),
        ("Unknown ETA / reactive escalation", "Integrated dispatch + ETA "
         "visibility"),
        ("No accountability, no SLAs", "Contracted SLAs + performance reporting"),
        ("Delayed discharge / blocked beds", "Protected throughput + bed "
         "turnover"),
        ("A transactional ride", "Infrastructure for care transitions"),
    ]
    growth = ""
    try:
        from ..market_reports import ift_tracking as _tr
        gb = _tr.growth_bridge()
        if getattr(gb, "available", False):
            growth = (
                '<p class="ifq-prose">Why the capability compounds: price '
                f'{gb.price_central_pct:.1f}%/yr × volume '
                f'{gb.volume_central_pct:.1f}%/yr = ~{gb.market_growth_central_pct:.1f}% '
                'organic market growth; plus consolidation → ~'
                f'{gb.platform_growth_central_pct:.1f}% platform growth. '
                + _chip("FRAMEWORK") + '</p>')
    except Exception:  # noqa: BLE001
        pass
    return _ans_wrap(
        _ans_table(("Transactional vendor — the old view",
                    "Strategic capability — the new view"), rows) + growth,
        basis="FRAMEWORK",
        source="Authored transformation framing; growth bridge from ift_tracking")


_ANSWER_BUILDERS = {
    "cover": _ans_cover,
    "vocabulary": _ans_vocabulary,
    "definition": _ans_definition,
    "taxonomy": _ans_taxonomy,
    "markets-contrast": _ans_markets_contrast,
    "why-dedicated": _ans_why_dedicated,
    "patient-journey": _ans_journey,
    "participants": _ans_participants,
    "operating-models": _ans_operating,
    "procurement": _ans_procurement,
    "challenges": _ans_challenges,
    "mmt-positioning": _ans_mmt,
    "dedicated-model": _ans_dedicated,
    "strategic-capability": _ans_strategic,
}


def _answer_for(slug: str) -> str:
    """Render the inline answer for a slide, or '' for dividers / on any failure
    (degrade, never raise)."""
    fn = _ANSWER_BUILDERS.get(slug)
    if not fn:
        return ""
    try:
        return fn() or ""
    except Exception:  # noqa: BLE001
        return ""


def _market_glance() -> str:
    """The study's headline sized answer — TAM / SAM / SOM up top, so the page
    opens with the number, not just the questions. Degrades to '' offline."""
    try:
        from ..market_reports import ift_analytics as _an
        t = _an.ground_tam()
        h = _an.health_system_sam()
    except Exception:  # noqa: BLE001
        return ""
    if not (getattr(t, "available", False) and getattr(h, "available", False)):
        return ""
    stats = (
        '<div class="ifq-stats">'
        + _stat(_usd_b(t.allpayer_tam_bn_central), "TAM · all US ground IFT")
        + _stat(_usd_b(h.sam_central_bn), "SAM · health systems")
        + _stat(_usd_m(h.som_central_m * 1e6), "SOM · current footprint")
        + _stat(_pct(getattr(h, "operator_share_of_sam", None)),
                "operator share of SAM")
        + '</div>')
    return (
        '<div class="ifq-ans" style="border-left-color:var(--sc-navy,#0b2341);">'
        '<span class="ifq-ans-lab">The market, sized — the study\'s headline '
        f'answer {_chip("FRAMEWORK")}</span>'
        '<p class="ifq-prose">All figures exclude 911, air, and NEMT; the full '
        'build is on <a href="/ift-markets" style="color:var(--sc-teal,#155752);">'
        '/ift-markets</a>.</p>' + stats + '</div>')


# ── Scoped stylesheet ────────────────────────────────────────────────────────
_STYLES = """<style>
.ifq-chip{display:inline-block;font-family:var(--sc-mono,Consolas,monospace);
font-size:9px;font-weight:600;letter-spacing:.06em;padding:1px 6px;border-radius:2px;
vertical-align:middle;}
.ifq-chip-framework{background:#ece9f2;color:#463a63;}
.ifq-chip-sourced{background:#e7efe9;color:#154e36;}
.ifq-chip-connector{background:#eef1f5;color:#31465e;border:1px solid #cdd6e2;}
.ifq-chip-gov{background:#e7efe9;color:#154e36;}
.ifq-chip-academic{background:#efeae0;color:#6b5426;}
.ifq-chip-illustrative{background:#f3ecd9;color:#7a5c1a;}
.ifq-prose{font-family:var(--sc-serif,Georgia,serif);font-size:14px;line-height:1.62;
color:var(--sc-text,#1a2332);max-width:90ch;margin:0 0 10px;}
.ifq-sub{font-family:var(--sc-mono,Consolas,monospace);font-size:11px;font-weight:600;
letter-spacing:.06em;text-transform:uppercase;color:var(--sc-teal,#155752);
margin:14px 0 6px;}
.ifq-mq{font-family:var(--sc-serif,Georgia,serif);font-size:15px;font-style:italic;
line-height:1.5;color:var(--sc-navy,#0b2341);border-left:3px solid var(--sc-teal,#155752);
padding:8px 0 8px 14px;margin:4px 0 10px;background:rgba(21,87,82,0.035);}
.ifq-prompt{font-family:var(--sc-mono,Consolas,monospace);font-size:11px;
color:var(--sc-muted,#6b6357);line-height:1.55;margin:0 0 8px;
border-left:2px solid var(--sc-border,#e4dccb);padding-left:10px;}
.ifq-prompt b{font-family:var(--sc-sans,Inter,system-ui,sans-serif);font-weight:700;
letter-spacing:.05em;text-transform:uppercase;font-size:9.5px;color:var(--sc-muted,#6b6357);}
.ifq-list{margin:2px 0 10px 20px;font-family:var(--sc-serif,Georgia,serif);
font-size:13px;line-height:1.55;color:var(--sc-text,#2a3340);}
.ifq-list li{margin:0 0 4px;}
.ifq-list-plain{list-style:square;}
.ifq-answer{display:flex;flex-wrap:wrap;align-items:baseline;gap:8px;margin:8px 0 4px;
padding:8px 12px;background:var(--sc-surface,#faf7f1);
border:1px solid var(--sc-border,#e4dccb);border-left:3px solid var(--sc-teal,#155752);
border-radius:4px;}
.ifq-answer-lab{font-family:var(--sc-mono,Consolas,monospace);font-size:9.5px;
font-weight:700;letter-spacing:.06em;text-transform:uppercase;
color:var(--sc-teal,#155752);}
.ifq-links{display:flex;flex-wrap:wrap;gap:6px 16px;}
.ifq-links a{font-family:var(--sc-mono,Consolas,monospace);font-size:11px;
font-weight:600;color:var(--sc-teal,#155752);text-decoration:none;}
.ifq-links a:hover{text-decoration:underline;}
.ifq-cxrow{margin:8px 0 2px;display:flex;flex-wrap:wrap;gap:5px;align-items:center;}
.ifq-cx-lab{font-family:var(--sc-mono,Consolas,monospace);font-size:9.5px;
font-weight:700;letter-spacing:.05em;text-transform:uppercase;
color:var(--sc-muted,#6b6357);margin-right:4px;}
.ifq-cx{display:inline-block;font-family:var(--sc-sans,Inter,system-ui,sans-serif);
font-size:11px;text-decoration:none;padding:3px 9px;border-radius:13px;
border:1px solid var(--sc-border,#e4dccb);background:#fff;color:var(--sc-text,#1a2332);}
.ifq-cx:hover{border-color:var(--sc-teal,#155752);}
.ifq-cx-st{font-family:var(--sc-mono,Consolas,monospace);font-size:8.5px;
font-weight:700;letter-spacing:.04em;margin-left:3px;}
.ifq-cx-live .ifq-cx-st{color:#154e36;}
.ifq-cx-gated{color:var(--sc-muted,#6b6357);}
.ifq-cx-gated .ifq-cx-st{color:#8a7f6b;}
.ifq-slidehd{font-family:var(--sc-mono,Consolas,monospace);font-size:10px;
font-weight:700;letter-spacing:.08em;color:var(--sc-teal,#155752);
display:inline-block;margin:0 0 2px;}
.ifq-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));
gap:12px;margin:6px 0 12px;}
.ifq-card{border:1px solid var(--sc-border,#e4dccb);border-left:3px solid
var(--sc-teal,#155752);border-radius:4px;padding:12px 14px;
background:var(--sc-surface,#faf7f1);}
.ifq-card h4{font-family:var(--sc-serif,Georgia,serif);font-size:14px;margin:0 0 5px;
color:var(--sc-text,#1a2332);}
.ifq-card p{font-family:var(--sc-serif,Georgia,serif);font-size:12.5px;line-height:1.5;
margin:0 0 6px;color:var(--sc-text,#2a3340);}
.ifq-story{border:1px solid var(--sc-border,#e4dccb);border-radius:6px;
background:var(--sc-navy,#0b2341);color:#f3efe6;padding:16px 20px;margin:6px 0 16px;}
.ifq-story b{color:#fff;}
.ifq-story-eyebrow{font-family:var(--sc-mono,Consolas,monospace);font-size:10px;
font-weight:700;letter-spacing:.1em;text-transform:uppercase;color:#a9c3bd;
margin:0 0 6px;}
.ifq-story p{font-family:var(--sc-serif,Georgia,serif);font-size:15px;line-height:1.55;
margin:0;max-width:96ch;}
.ifq-toc{columns:2;column-gap:28px;margin:8px 0 14px;padding:12px 16px;
background:var(--sc-surface,#faf7f1);border:1px solid var(--sc-border,#e4dccb);
border-radius:4px;}
.ifq-toc a{display:block;font-family:var(--sc-mono,Consolas,monospace);font-size:11px;
color:var(--sc-teal,#155752);text-decoration:none;padding:2px 0;break-inside:avoid;}
.ifq-wrap{overflow-x:auto;margin:5px 0 12px;}
.ifq-tab{border-collapse:collapse;width:100%;font-size:12.5px;
font-family:var(--sc-sans,Inter,system-ui,sans-serif);}
.ifq-tab th,.ifq-tab td{border:1px solid var(--sc-border,#e4dccb);padding:6px 9px;
text-align:left;vertical-align:top;line-height:1.45;}
.ifq-tab thead th{background:var(--sc-navy,#0b2341);color:#fff;font-weight:600;
font-size:11px;position:sticky;top:0;}
.ifq-tab tbody tr:nth-child(even){background:var(--sc-surface,#faf7f1);}
.ifq-tab td:first-child{font-weight:600;}
.ifq-estatecat{font-family:var(--sc-sans,Inter,system-ui,sans-serif);font-size:10px;
font-weight:700;letter-spacing:.07em;text-transform:uppercase;color:#fff;
background:var(--sc-teal,#155752);padding:5px 10px;}
.ifq-links-lg{display:flex;flex-wrap:wrap;gap:14px;margin:14px 0 4px;
font-family:var(--sc-mono,Consolas,monospace);font-size:11px;font-weight:600;}
.ifq-links-lg a{color:var(--sc-teal,#155752);text-decoration:none;}
.ifq-dl a{display:inline-block;font-family:var(--sc-mono,Consolas,monospace);
font-size:12px;font-weight:600;letter-spacing:.04em;text-decoration:none;color:#fff;
background:var(--sc-teal,#155752);padding:8px 15px;border-radius:3px;margin-top:6px;}
.ifq-ans{border:1px solid var(--sc-border,#e4dccb);border-left:3px solid
var(--sc-teal,#155752);border-radius:4px;background:#fff;padding:12px 14px;
margin:8px 0 12px;}
.ifq-ans-lab{display:block;font-family:var(--sc-mono,Consolas,monospace);
font-size:9.5px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;
color:var(--sc-teal,#155752);margin:0 0 8px;}
.ifq-tab td.ifq-ift,.ifq-tab th.ifq-ift{background:#eef5f1;}
.ifq-tab thead th.ifq-ift{background:#12463a;}
.ifq-stats{display:flex;flex-wrap:wrap;gap:8px;margin:6px 0 2px;}
.ifq-stat{flex:1 1 130px;background:var(--sc-surface,#faf7f1);
border:1px solid var(--sc-border,#e4dccb);border-radius:4px;padding:8px 12px;}
.ifq-stat-v{font-family:var(--sc-mono,Consolas,monospace);font-size:18px;
font-weight:700;color:var(--sc-navy,#0b2341);font-variant-numeric:tabular-nums;
line-height:1.15;}
.ifq-stat-l{font-size:9.5px;letter-spacing:.04em;text-transform:uppercase;
color:var(--sc-muted,#6b6357);margin-top:3px;}
</style>"""


def _crosslinks() -> str:
    return (
        '<div class="ifq-links-lg">'
        '<a href="/ift-demand">Demand deep-dive (national→subcounty) &rarr;</a>'
        '<a href="/ift-sourcing">Sourcing prompts — Part 1 &rarr;</a>'
        '<a href="/ift-study">Investor market study (4 dimensions) &rarr;</a>'
        '<a href="/ift-research">Market research brief (20 topics) &rarr;</a>'
        '<a href="/ift-markets">Geographic markets &amp; TAM/SAM/SOM &rarr;</a>'
        '<a href="/ift-clinical">Clinical demand engine &rarr;</a>'
        '<a href="/ift-mmt">MMT county deep dive &rarr;</a>'
        '<a href="/connector-estate">Live data-connector estate &rarr;</a>'
        '</div>')


def _toc(slides) -> str:
    links = [
        '<a href="#ifq-tree">0 · Master question tree (A / B / C)</a>',
    ]
    for s in slides:
        links.append(f'<a href="#ifq-slide-{_esc(s.slug)}">{s.num} &middot; '
                     f'{_esc(s.title)}</a>')
    links += [
        '<a href="#ifq-estate">Connector evidence estate</a>',
        '<a href="#ifq-evidence">Cross-slide evidence plan</a>',
        '<a href="#ifq-visuals">Best-overall visual package</a>',
        '<a href="#ifq-nuances">Nuances not to miss</a>',
    ]
    return f'<div class="ifq-toc">{"".join(links)}</div>'


def _story() -> str:
    return (
        '<div class="ifq-story">'
        '<div class="ifq-story-eyebrow">The core storyline</div>'
        '<p><b>IFT is not just "ambulance transportation."</b> It is a distinct '
        'operational layer inside the hospital care-continuum. The study proves '
        'that IFT differs from 911 EMS and NEMT across use case, buyer, acuity, '
        'economics, workflow, service expectations, and competitive basis — then '
        'shows where MMT fits and why a dedicated IFT partnership model may be '
        'structurally advantaged.</p>'
        '</div>')


# ── Master question tree (Section 0) ─────────────────────────────────────────
def _tree_section(mt) -> str:
    if not (mt and mt.available):
        return ""
    body = [f'<p class="ifq-prose">{_esc(mt.note)} {_chip("FRAMEWORK")}</p>']
    for br in mt.branches:
        body.append(f'<p class="ifq-sub" style="font-size:12px;color:'
                    f'var(--sc-navy,#0b2341);">{_esc(br.title)}</p>')
        body.append(f'<p class="ifq-mq">{_esc(br.main_question)}</p>')
        body.append(f'<p class="ifq-prose">{_esc(br.intro)}</p>')
        for g in br.groups:
            body.append(_qgroup(g))
    body.append(f'<p class="ifq-prompt">Source: {_esc(mt.source_label)}</p>')
    return ('<div id="ifq-tree">'
            + ck_section_header("0 — The master question tree",
                                eyebrow="WHAT THE MARKET IS · WHY IT MATTERS · "
                                        "WHY DEDICATED MAY WIN")
            + ck_panel("".join(body)) + '</div>')


# ── Per-slide architecture ───────────────────────────────────────────────────
def _slide_panel(s, ce) -> str:
    parts: List[str] = [
        f'<span class="ifq-slidehd">SLIDE {s.num} · {_esc(s.kind.upper())}</span>',
        f'<p class="ifq-prompt"><b>SOW prompt</b> — {_esc(s.prompt)}</p>',
        f'<p class="ifq-mq">{_esc(s.main_question)}</p>',
        # The ANSWER, inline — pulled from the same sized modules the other pages
        # render, so the question and its answer sit together.
        _answer_for(s.slug),
    ]
    if s.groups:
        parts.append('<p class="ifq-sub" style="color:var(--sc-navy,#0b2341);">'
                     'The sub-questions behind it</p>')
    for g in s.groups:
        parts.append(_qgroup(g))
    parts.append(_bullets(s.data_needed, heading="Data & evidence needed"))
    parts.append(_bullets(s.visuals, heading="Helpful visuals"))
    parts.append(_connector_chips(s.connector_keys, ce))
    parts.append(_link_row(s.answered_by, label="Go deeper on the sized pages"))
    return ck_panel("".join(p for p in parts if p),
                    title=f"{s.num}. {s.title}",
                    anchor_id=f"ifq-slide-{s.slug}")


def _slides_section(sa, ce) -> str:
    if not (sa and sa.available):
        return ""
    out = [
        ck_section_intro(
            "THE SLIDES, DECOMPOSED",
            "Every slide: the question, then the answer, in one place.",
            italic_word="answer",
            body=("For each SOW slide: the main diligence question, the actual "
                  "answer rendered inline from our sized modules, the sub-question "
                  "tree beneath it, the data / evidence that proves the point, the "
                  "persuasive visuals, the connector datasets that feed it, and a "
                  "link to go deeper on the sized pages.")),
    ]
    for s in sa.slides:
        out.append(_slide_panel(s, ce))
    return "".join(out)


# ── Connector evidence estate ────────────────────────────────────────────────
_CAT_LABEL = {
    "Supply": "Supply — who can run the transports",
    "Demand": "Demand — who needs to move",
    "Facilities": "Facilities — the origin / destination universe",
    "Reimbursement": "Reimbursement — how transports get paid",
    "Coverage": "Coverage — the medical-necessity rules",
    "Clinical": "Clinical — condition severity & coding",
    "Rural": "Rural — the mileage economics",
}


def _estate_section(ce) -> str:
    if not (ce and ce.available and ce.summary):
        return ""
    summ = ce.summary
    rows: List[str] = []
    for cat, _n in summ.by_category:
        group = [p for p in ce.probes if p.category == cat]
        if not group:
            continue
        rows.append(f'<tr><td colspan="4" class="ifq-estatecat">'
                    f'{_esc(_CAT_LABEL.get(cat, cat))}</td></tr>')
        for p in group:
            live = p.available
            status = (_chip("SOURCED") if live else _chip("CONNECTOR"))
            href = "/connector-estate?dataset=" + _esc(p.dataset_id)
            rows.append(
                '<tr>'
                f'<td><a href="{href}" style="color:var(--sc-teal,#155752);'
                f'text-decoration:none;">{_esc(p.title)}</a></td>'
                f'<td>{_esc(p.ift_signal)}</td>'
                f'<td>{status}</td>'
                f'<td style="font-family:var(--sc-mono,Consolas,monospace);'
                f'font-size:10px;color:var(--sc-muted,#6b6357);">'
                f'{_esc(p.connector)} · {_esc(p.dataset_id)}</td>'
                '</tr>')
    table = (
        '<div class="ifq-wrap"><table class="ifq-tab"><thead><tr>'
        '<th>Connector dataset</th><th>What it yields for IFT</th><th>Status</th>'
        '<th>Estate id</th></tr></thead>'
        f'<tbody>{"".join(rows)}</tbody></table></div>')
    note = (
        '<p class="ifq-prose">The evidence is wired to real datasets — every hook '
        'is a registered estate dataset, so each flips from <em>ingest-ready</em> '
        f'{_chip("CONNECTOR")} to <strong>live</strong> {_chip("SOURCED")} the '
        'moment the estate is ingested; offline each cites an honest GOV / '
        'ACADEMIC fallback, never a fabricated number. The per-slide chips above '
        'point back into this estate. '
        '<a href="/connector-estate" style="color:var(--sc-teal,#155752);">Browse '
        f'the full {summ.n_connectors}-connector estate &rarr;</a></p>')
    return ('<div id="ifq-estate">'
            + ck_section_header(
                "The connectors behind the evidence",
                eyebrow="LIVE DATA ESTATE",
                count=f"{summ.total} hooks / {summ.n_connectors} sources")
            + ck_panel(note + table) + '</div>')


# ── Cross-slide evidence plan ────────────────────────────────────────────────
def _evidence_section(ep, ce) -> str:
    if not (ep and ep.available):
        return ""
    cards: List[str] = []
    for src in ep.sources:
        lis = "".join(f"<li>{_esc(it)}</li>" for it in src.items)
        surface = _link_row(src.our_surface, label="Where it lives")
        cx = _connector_chips(src.connector_keys, ce)
        cards.append(
            '<div class="ifq-card">'
            f'<h4>{_esc(src.name)}</h4>'
            f'<p>{_esc(src.intro)}</p>'
            f'<ul class="ifq-list" style="margin-left:16px;">{lis}</ul>'
            f'{surface}{cx}</div>')
    return ('<div id="ifq-evidence">'
            + ck_section_header(
                "Cross-slide data & evidence plan",
                eyebrow="WHAT TO GATHER · AND WHERE IT LIVES", count=len(ep.sources))
            + ck_panel(
                '<p class="ifq-prose">The five evidence sources that answer the '
                'architecture — company data, primary interviews, contract review, '
                'competitor research, and health-system operating data — each '
                'mapped to the live platform surface and the connector datasets '
                f'that feed the analog. {_chip("FRAMEWORK")}</p>'
                f'<div class="ifq-grid">{"".join(cards)}</div>'
                f'<p class="ifq-prompt">Source: {_esc(ep.source_label)}</p>')
            + '</div>')


# ── Best-overall visual package ──────────────────────────────────────────────
def _visuals_section(vp) -> str:
    if not (vp and vp.available):
        return ""
    rows = ""
    for i, v in enumerate(vp.visuals, start=1):
        where = "".join(
            f'<a href="{_esc(href)}" style="color:var(--sc-teal,#155752);'
            f'text-decoration:none;">{_esc(txt)}</a><br>' for txt, href in v.where)
        rows += (f'<tr><td>{i}. {_esc(v.name)}</td><td>{_esc(v.purpose)}</td>'
                 f'<td>{where or "&mdash;"}</td></tr>')
    return ('<div id="ifq-visuals">'
            + ck_section_header(
                "Best-overall visual package",
                eyebrow="THE 15 HIGHEST-LEVERAGE VISUALS", count=len(vp.visuals))
            + ck_panel(
                '<p class="ifq-prose">The visuals that make the argument '
                'persuasive, ranked — each mapped to the live page that already '
                f'carries (or would carry) it. {_chip("FRAMEWORK")}</p>'
                '<div class="ifq-wrap"><table class="ifq-tab"><thead><tr>'
                '<th>Visual</th><th>What it proves</th><th>Where we render it</th>'
                f'</tr></thead><tbody>{rows}</tbody></table></div>'
                f'<p class="ifq-prompt">Source: {_esc(vp.source_label)}</p>')
            + '</div>')


# ── Nuances ──────────────────────────────────────────────────────────────────
def _nuances_section(ns) -> str:
    if not ns:
        return ""
    cards = "".join(
        f'<div class="ifq-card"><h4>{i}. {_esc(n.title)}</h4>'
        f'<p>{_esc(n.body)}</p></div>'
        for i, n in enumerate(ns, start=1))
    return ('<div id="ifq-nuances">'
            + ck_section_header(
                "The nuances not to miss", eyebrow="WHERE STUDIES GO WRONG",
                count=len(ns))
            + ck_panel(f'<div class="ifq-grid">{cards}</div>') + '</div>')


# ═══════════════════════════════════════════════════════════════════════════
def render_ift_diligence(qs: Optional[Dict[str, List[str]]] = None) -> str:
    """Render the IFT diligence question-architecture page. Degrades to honest
    notes if the offline modules are unavailable — never raises."""
    mt = _dg.master_tree()
    sa = _dg.slide_architecture()
    ep = _dg.evidence_plan()
    vp = _dg.visual_package()
    ns = _dg.nuances()
    ce = _dg.connector_evidence()
    summ = _dg.diligence_summary()

    meta = (f"{summ['n_slides']} slides · {summ['n_questions']} diligence "
            f"questions · answered inline · {summ['n_connector_hooks']} connector "
            f"hooks / {summ['n_connectors']} sources")
    head = ck_page_title(
        "IFT Diligence — Question Architecture",
        eyebrow="INTERFACILITY TRANSPORT · HOW THE STUDY IS INTERROGATED",
        meta=meta)
    explainer = (
        '<p class="ifq-prose" style="font-size:15px;">The <strong>question and the '
        'answer, in one place</strong>. For every slide in the IFT market study: '
        'the underlying diligence question, the sub-question tree beneath it, and — '
        'rendered inline — <strong>the actual answer</strong>, pulled from the same '
        'sized modules the other pages read (the taxonomy matrix, the patient '
        'journey, the operating-model bands, MMT positioning, the TAM/SAM/SOM). '
        'Each slide also carries the data / evidence that proves it, the persuasive '
        'visuals, the real <strong>connector datasets</strong> that feed it, and a '
        'link to go deeper. Questions are authored diligence knowledge '
        f'{_chip("FRAMEWORK")}; answers carry their own basis — {_chip("ACADEMIC")} '
        f'{_chip("FRAMEWORK")} {_chip("SOURCED")} — and the connector references '
        f'resolve live {_chip("CONNECTOR")}.</p>')

    body = "".join([
        _STYLES,
        head,
        explainer,
        _crosslinks(),
        _story(),
        _market_glance(),
        ck_section_intro(
            "HOW TO READ THIS",
            "Master tree first, then every slide — question and answer together.",
            italic_word="every",
            body=("Start with the three-branch master question tree (what the "
                  "market is, why it matters to health systems, and why a "
                  "dedicated provider may win). Then each SOW slide gives its "
                  "main question, the answer rendered inline from our sized "
                  "modules, the finer sub-questions, the evidence and visuals, "
                  "and the connectors that feed it. The estate, evidence plan, "
                  "visual package, and nuances close the loop.")),
        _toc(sa.slides),
        _tree_section(mt),
        _slides_section(sa, ce),
        _estate_section(ce),
        _evidence_section(ep, ce),
        _visuals_section(vp),
        _nuances_section(ns),
        _crosslinks(),
        '<div class="ifq-dl"><a href="/api/ift/markets.xlsx" download>Download the '
        'investor data pack (Excel) &darr;</a></div>',
        ck_next_section(
            "Get the sourcing prompts that gather the evidence for these questions "
            "(Part 1)",
            "/ift-sourcing", eyebrow="The sourcing", italic_word="sourcing"),
        ck_next_section(
            "Read the answers — the investor market study (4 dimensions + MMT)",
            "/ift-study", eyebrow="The answers", italic_word="investor"),
        ck_next_section(
            "See the market sized — geographic TAM / SAM / SOM, market by market",
            "/ift-markets", eyebrow="The numbers", italic_word="sized"),
        ck_next_section(
            "Browse the live data-connector estate behind the evidence",
            "/connector-estate", eyebrow="The data", italic_word="live"),
        ck_page_actions(),
    ])
    return chartis_shell(
        body, "IFT Diligence — Question Architecture", active_nav="/market",
        subtitle="Interfacility-transport diligence question architecture — the "
                 "question tree behind the study, cross-linked to the answers")
