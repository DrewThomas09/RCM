"""Interfacility Transport — Target Markets (``/ift-markets``).

A premium editorial geographic deep-dive for the ground-IFT target operator's
actual footprint. It renders entirely from ``chartis_shell`` + ``ck_*``
primitives (the market-report idiom) and every figure carries an honesty basis
chip, so a partner never mistakes a modeled number for a filed one.

Structure:

  * editorial head + honesty legend;
  * a NATIONAL OVERVIEW — the US ground-IFT **TAM** (top-down from the GOV
    MedPAC anchor, every modeled line ILLUSTRATIVE, ex-NEMT/ex-air) and the
    footprint **SAM** (bottom-up from the real origins/destinations in the
    target metros), both from :mod:`ift_analytics` / :mod:`ift_geo`;
  * a footprint-at-a-glance table (every target metro, its SOURCED facility
    counts, and its ILLUSTRATIVE per-metro SAM) plus a footprint US map;
  * a DEEP-DIVE SUBSECTION PER TARGET METRO, grouped by state/region — the
    anchor health SYSTEMS (IFT demand generators), the SOURCED hospital +
    post-acute density, the competitive insource-vs-outsource read, and the
    MOAT verdict.

This page is deliberately NOT wired through the shared market-report renderer
(``ui/market_report_page.py``) — it is a standalone surface reached at
``/ift-markets`` with its own scoped ``ift-*`` stylesheet, so it never collides
with the concurrently-authored market-report fan-out.

Design contract mirrors the analytics it reads: the render function **degrades,
never raises** — if the offline structure is unavailable it renders an honest
empty note instead of 500-ing.

Public API:
    render_ift_markets() -> str
"""
from __future__ import annotations

import html as _html
from typing import Dict, List, Optional

from ._chartis_kit import (
    chartis_shell, ck_editorial_head, ck_eyebrow, ck_next_section,
    ck_page_actions, ck_panel, ck_provenance_tooltip, ck_section_header,
    ck_section_intro,
)
from .us_geo_map import render_us_geo_map
from ..market_reports import ift_analytics as _an
from ..market_reports import ift_geo as _geo


def _esc(x: object) -> str:
    return _html.escape(str(x if x is not None else ""))


# ── Honesty basis chips (scoped ift- classes so they never collide with the
#    market-report renderer's ck-mr- chips, same visual contract) ─────────────
_BASIS_KEYS = ("SOURCED", "GOV", "ACADEMIC", "ILLUSTRATIVE", "INDUSTRY",
               "INTERNAL", "CONNECTOR", "PUBLIC")
_BASIS_TITLE = {
    "SOURCED": "Computed from OUR vendored CMS estate (hospital_coords + HCRIS "
               "+ the post-acute provider rolls).",
    "GOV": "A published government figure (CMS, MedPAC, USRDS, Census).",
    "ACADEMIC": "A real academic / peer-reviewed citation.",
    "ILLUSTRATIVE": "Modeled — the basis is named, not a filed figure.",
    "INDUSTRY": "An industry / trade source.",
    "INTERNAL": "A PE Desk internal surface (deep-dive, corpus, sizing).",
    "CONNECTOR": "A network-gated connector dataset (ingest-ready, honest "
                 "fallback offline).",
    "PUBLIC": "Public / company-web knowledge, named honestly and labelled — "
              "no contract exclusivities asserted.",
}


def _basis_key(label: str) -> str:
    up = (label or "").strip().upper()
    for k in _BASIS_KEYS:
        if up.startswith(k):
            return k
    # "connector · ..." and "PUBLIC-WEB" style labels used by ift_geo.
    if up.startswith("PUBLIC"):
        return "PUBLIC"
    if up.startswith("CONNECTOR"):
        return "CONNECTOR"
    return "ILLUSTRATIVE"


def _basis_chip(basis: str) -> str:
    b = _basis_key(basis)
    return (f'<span class="ift-chip ift-chip-{b.lower()}" '
            f'title="{_esc(_BASIS_TITLE.get(b, _BASIS_TITLE["ILLUSTRATIVE"]))}">'
            f'{_esc(b)}</span>')


def _source_chip(source_label: str) -> str:
    """A basis chip plus the muted remainder of a ``basis · source`` label."""
    b = _basis_key(source_label)
    rest = source_label.split("·", 1)[1].strip() if "·" in source_label else ""
    tail = (f' <span class="ift-src">{_esc(rest)}</span>' if rest else "")
    return _basis_chip(b) + tail


def _legend_row() -> str:
    chips = "".join(_basis_chip(k) for k in
                    ("SOURCED", "GOV", "ILLUSTRATIVE", "PUBLIC"))
    return (
        '<div class="ift-legend">'
        '<span class="ift-legend-lab">Every figure is labelled</span>'
        f'{chips}'
        '<span class="ift-legend-note">SOURCED = our CMS estate · GOV = CMS/'
        'MedPAC · ILLUSTRATIVE = modeled w/ basis · PUBLIC = company-web, '
        'labelled</span>'
        '</div>'
    )


# ── Number helpers ──────────────────────────────────────────────────────────
def _usd_m(x: float) -> str:
    try:
        return f"${x / 1e6:,.2f}M"
    except (TypeError, ValueError):
        return "—"


def _usd_b(x: float) -> str:
    try:
        return f"${x:,.2f}B"
    except (TypeError, ValueError):
        return "—"


def _num(x: object, dash: str = "—") -> str:
    try:
        return f"{int(round(float(x))):,}"
    except (TypeError, ValueError):
        return dash


def _pct(x: Optional[float], dash: str = "—") -> str:
    if x is None:
        return dash
    try:
        return f"{float(x) * 100:.1f}%"
    except (TypeError, ValueError):
        return dash


def _stat(value: str, label: str) -> str:
    return (
        '<div class="ift-stat">'
        f'<div class="ift-stat-v sc-num">{value}</div>'
        f'<div class="ift-stat-l">{_esc(label)}</div>'
        '</div>'
    )


def _kpi(label: str, value: str, sub: str) -> str:
    return (
        '<div class="ift-kpi">'
        f'<div class="ift-kpi-label">{_esc(label)}</div>'
        f'<div class="ift-kpi-value sc-num">{value}</div>'
        f'<div class="ift-kpi-sub">{_esc(sub)}</div>'
        '</div>'
    )


# ── Scoped stylesheet ───────────────────────────────────────────────────────
def _styles() -> str:
    return (
        "<style>"
        ".ift-chip{display:inline-block;font-family:var(--sc-mono);font-size:9px;"
        "font-weight:700;letter-spacing:0.06em;padding:1px 6px;border-radius:3px;"
        "vertical-align:middle;margin:0 2px 2px 0;text-transform:uppercase;"
        "border:1px solid transparent;}"
        ".ift-chip-sourced{color:#0f3d39;border-color:var(--sc-teal,#155752);"
        "background:rgba(21,87,82,0.08);}"
        ".ift-chip-gov{color:#123a63;border-color:var(--sc-navy,#0b2341);"
        "background:rgba(11,35,65,0.06);}"
        ".ift-chip-academic{color:#5a3b12;border-color:var(--sc-warning,#b8732a);"
        "background:rgba(184,115,42,0.08);}"
        ".ift-chip-illustrative{color:#5c6878;"
        "border-color:var(--sc-text-faint,#7a8699);background:rgba(122,134,153,0.08);}"
        ".ift-chip-public{color:#4a3766;border-color:#7a5ca8;"
        "background:rgba(122,92,168,0.08);}"
        ".ift-chip-connector{color:#5c6878;border-color:var(--sc-rule-2,#bfb6a2);}"
        ".ift-chip-industry{color:#5c6878;border-color:var(--sc-rule-2,#bfb6a2);}"
        ".ift-chip-internal{color:#0f3d39;border-color:var(--sc-teal,#155752);}"
        ".ift-src{font-size:10px;color:var(--sc-text-dim,#465366);"
        "font-family:var(--sc-mono);}"
        ".ift-legend{margin:10px 0 4px;font-size:11px;"
        "color:var(--sc-text-dim,#465366);}"
        ".ift-legend-lab{font-family:var(--sc-mono);font-size:10px;"
        "letter-spacing:0.06em;text-transform:uppercase;margin-right:8px;}"
        ".ift-legend-note{display:block;margin-top:4px;font-size:10.5px;"
        "color:var(--sc-text-faint,#7a8699);}"
        # KPI strip
        ".ift-kpi-grid{display:grid;grid-template-columns:repeat(auto-fit,"
        "minmax(150px,1fr));gap:12px;margin:12px 0 6px;}"
        ".ift-kpi{background:#fff;border:1px solid var(--sc-rule,#d6cfc0);"
        "border-radius:4px;padding:12px 14px;}"
        ".ift-kpi-label{font-family:var(--sc-sans);font-size:10px;font-weight:600;"
        "letter-spacing:0.06em;text-transform:uppercase;"
        "color:var(--sc-text-dim,#465366);margin-bottom:5px;}"
        ".ift-kpi-value{font-family:var(--sc-mono);font-size:20px;font-weight:700;"
        "color:var(--sc-text,#1a2332);line-height:1.15;font-variant-numeric:"
        "tabular-nums;}"
        ".ift-kpi-sub{font-size:10.5px;color:var(--sc-text-faint,#7a8699);"
        "margin-top:4px;}"
        # tables
        ".ift-table{width:100%;border-collapse:collapse;background:#fff;"
        "border:1px solid var(--sc-rule,#d6cfc0);font-size:12px;margin:0 0 6px;}"
        ".ift-table th{text-align:left;padding:7px 10px;font-family:var(--sc-sans);"
        "font-size:9.5px;font-weight:600;letter-spacing:0.06em;text-transform:"
        "uppercase;color:var(--sc-text-dim,#465366);"
        "border-bottom:1px solid var(--sc-rule,#d6cfc0);}"
        ".ift-table td{padding:7px 10px;"
        "border-bottom:1px solid var(--sc-panel-alt,#ece5d6);vertical-align:top;"
        "color:var(--sc-text,#1a2332);line-height:1.5;}"
        ".ift-table tbody tr:hover{background:var(--sc-panel-alt,#f3eee2);}"
        ".ift-num{font-variant-numeric:tabular-nums;font-family:var(--sc-mono);"
        "text-align:right;white-space:nowrap;}"
        ".ift-table-wrap{overflow-x:auto;margin:0 0 6px;}"
        # prose
        ".ift-prose{font-family:var(--sc-serif,Georgia,serif);font-size:14px;"
        "line-height:1.65;color:var(--sc-text,#1a2332);margin:0 0 10px;max-width:76ch;}"
        ".ift-sub{font-family:var(--sc-sans);font-size:10px;font-weight:700;"
        "letter-spacing:0.07em;text-transform:uppercase;"
        "color:var(--sc-teal,#155752);margin:14px 0 6px;}"
        ".ift-list{margin:0 0 10px;padding-left:20px;font-size:13px;line-height:1.65;"
        "color:var(--sc-text,#1a2332);}"
        ".ift-list li{margin:0 0 5px;}"
        # stat strip
        ".ift-stats{display:flex;flex-wrap:wrap;gap:8px;margin:4px 0 8px;}"
        ".ift-stat{flex:1 1 96px;min-width:92px;background:var(--sc-panel-alt,#f3eee2);"
        "border:1px solid var(--sc-rule,#d6cfc0);border-radius:4px;padding:7px 10px;}"
        ".ift-stat-v{font-family:var(--sc-mono);font-size:15px;font-weight:700;"
        "color:var(--sc-text,#1a2332);font-variant-numeric:tabular-nums;line-height:1.1;}"
        ".ift-stat-l{font-size:9.5px;letter-spacing:0.04em;text-transform:uppercase;"
        "color:var(--sc-text-dim,#465366);margin-top:3px;}"
        # operator chips
        ".ift-ops span{display:inline-block;font-size:11px;padding:3px 9px;"
        "margin:0 5px 5px 0;border:1px solid var(--sc-rule,#d6cfc0);border-radius:14px;"
        "background:#fff;color:var(--sc-text,#1a2332);}"
        # metro meta strip
        ".ift-meta{font-family:var(--sc-mono);font-size:11px;"
        "color:var(--sc-text-dim,#465366);margin:0 0 8px;letter-spacing:0.02em;}"
        ".ift-meta b{color:var(--sc-text,#1a2332);}"
        # caveat note
        ".ift-caveat{border-left:3px solid var(--sc-warning,#b8732a);"
        "background:rgba(184,115,42,0.06);padding:8px 12px;margin:8px 0 4px;"
        "font-size:12px;line-height:1.55;color:var(--sc-text,#1a2332);}"
        ".ift-caveat b{font-family:var(--sc-mono);font-size:9.5px;letter-spacing:0.06em;"
        "text-transform:uppercase;color:var(--sc-warning,#b8732a);}"
        ".ift-verdict{border-left:3px solid var(--sc-teal,#155752);"
        "background:rgba(21,87,82,0.05);padding:10px 14px;margin:6px 0 4px;}"
        ".ift-mono-src{font-size:10.5px;color:var(--sc-text-dim,#465366);"
        "font-family:var(--sc-mono);margin:2px 0 8px;}"
        ".ift-rollmeta{margin:2px 0 8px;font-family:var(--sc-mono);font-size:12px;"
        "color:var(--sc-text-dim,#465366);}"
        ".ift-rollmeta b{color:var(--sc-text,#1a2332);}"
        "</style>"
    )


# ═══════════════════════════════════════════════════════════════════════════
#  National overview — TAM (top-down) + SAM (bottom-up footprint)
# ═══════════════════════════════════════════════════════════════════════════
def _tam_section() -> str:
    tam = _an.ground_tam()
    header = ck_section_header(
        "National TAM — US ground interfacility ambulance",
        eyebrow="THE MARKET, TOP-DOWN")
    if not tam.available:
        return header + ck_panel(
            '<p class="ift-prose">The national ground-IFT TAM build is '
            'unavailable offline.</p>')

    step_rows = "".join(
        "<tr>"
        f"<td>{_esc(s.label)}</td>"
        f'<td class="ift-num">{_esc(s.value)}</td>'
        f"<td>{_basis_chip(s.basis)}</td>"
        f'<td>{_esc(s.detail)}</td>'
        "</tr>"
        for s in tam.steps)
    excl = "".join(f"<li>{_esc(x)}</li>" for x in tam.exclusions)

    body = (
        f'<p class="ift-prose"><strong>{_esc(tam.headline)}</strong></p>'
        '<p class="ift-prose">TAM is <em>all US ground interfacility ambulance '
        'missions</em> — the BLS/ALS/CCT/SCT interfacility slice (HCPCS '
        'A0426/A0428 BLS, A0427/A0429 ALS, A0433 ALS2, A0434 SCT + A0425 ground '
        'mileage). It EXCLUDES NEMT and EXCLUDES air. The line-level Medicare '
        'Part-B path is the SOURCED spine once the estate is ingested; offline '
        'it degrades to this GOV-anchored, ILLUSTRATIVE top-down build — present '
        'it as a range, never a point.</p>'
        '<div class="ift-table-wrap"><table class="ift-table"><thead><tr>'
        '<th>Build step</th><th>Value</th><th>Basis</th><th>Detail</th>'
        f'</tr></thead><tbody>{step_rows}</tbody></table></div>'
        f'<p class="ift-mono-src">{_source_chip(tam.source_label)}</p>'
        '<p class="ift-sub">Explicitly excluded from TAM</p>'
        f'<ul class="ift-list">{excl}</ul>'
        f'<p class="ift-prose">{_esc(tam.note)}</p>'
    )
    return header + ck_panel(body)


def _sam_section(rollup, sam) -> str:
    header = ck_section_header(
        "Footprint SOM — bottom-up from the real market structure",
        eyebrow="THE SERVICEABLE-OBTAINABLE FOOTPRINT")
    if not (rollup and rollup.available) or not (sam and sam.available):
        return header + ck_panel(
            '<p class="ift-prose">The footprint SOM build is unavailable '
            'offline.</p>')

    crosscheck = (_usd_m(sam.sam_crosscheck_dollars)
                  if sam.sam_crosscheck_dollars is not None else "—")
    body = (
        '<p class="ift-prose">This is the <strong>SOM</strong> — what is '
        'serviceable-obtainable inside the operator\'s CURRENT footprint, not the '
        'structural SAM above. It is <em>not</em> a percentage of TAM: it is '
        'built bottom-up from the real origins and destinations inside the '
        "target operator's actual metros — the hospitals (IFT origins) and "
        'post-acute facilities (discharge destinations), the '
        'transfer/discharge volume they generate that needs ground IFT, and a '
        'realistically-serviceable share s(m) keyed to the insource-vs-outsource '
        'structure of each market. Per metro: '
        '<strong>SOM(m) = [ discharge&nbsp;base &times; f_IFT + SNF&nbsp;legs ] '
        '&times; s(m) &times; r_IFT(m)</strong>.</p>'
        # footprint counts
        '<p class="ift-sub">Footprint at a glance (SOURCED)</p>'
        '<div class="ift-stats">'
        + _stat(_num(rollup.n_metros), "target metros")
        + _stat(_num(rollup.n_regions), "state regions")
        + _stat(_num(rollup.n_hospitals), "hospitals (origins)")
        + _stat(_num(rollup.hcris_beds), "HCRIS beds")
        + _stat(_num(rollup.n_snf), "SNFs")
        + _stat(_num(rollup.snf_beds), "SNF beds")
        + _stat(_num(rollup.n_irf), "IRFs")
        + _stat(_num(rollup.n_ltch), "LTCHs")
        + _stat(_num(rollup.n_hospice), "hospices")
        + _stat(_num(rollup.n_home_health), "home-health")
        + _stat(_num(rollup.n_dialysis), "dialysis")
        + '</div>'
        f'<p class="ift-mono-src">{_source_chip(rollup.source_label)}</p>'
        # share of national
        '<p class="ift-sub">Share of national (footprint STATES vs the full '
        'US rolls)</p>'
        '<p class="ift-rollmeta">'
        f'Footprint-state hospitals <b>{_num(rollup.footprint_state_hospitals)}</b> '
        f'of <b>{_num(rollup.n_hospitals_national)}</b> national '
        f'= <b>{_pct(rollup.hospitals_national_share)}</b> &middot; '
        f'footprint-state SNF beds <b>{_num(rollup.footprint_state_snf_beds)}</b> '
        f'of <b>{_num(rollup.snf_beds_national)}</b> '
        f'= <b>{_pct(rollup.snf_beds_national_share)}</b> '
        f'{_basis_chip("SOURCED")}</p>'
        # SOM dollars
        '<p class="ift-sub">Serviceable-obtainable footprint (ILLUSTRATIVE levers '
        'on the SOURCED structure)</p>'
        '<div class="ift-kpi-grid">'
        + _kpi("SOM — central", _usd_m(sam.sam_dollars_central),
               f"range {_usd_m(sam.sam_dollars_low)}–{_usd_m(sam.sam_dollars_high)}")
        + _kpi("Ground-IFT demand", _num(sam.total_demand_missions) + " mis/yr",
               "acute discharges + SNF recurring legs")
        + _kpi("Serviceable missions", _num(sam.total_serviceable_missions) + "/yr",
               f"{_pct(sam.serviceable_share_of_national_volume)} of the ~4-5M "
               "national ground-IFT volume")
        + _kpi("Bed-share cross-check", crosscheck,
               f"beds {_pct(sam.bed_share_of_national)} of national × TAM × "
               "s_avg — reconciles")
        + '</div>'
        f'<p class="ift-mono-src">{_source_chip(sam.source_label)}</p>'
        f'<p class="ift-prose">{_esc(sam.note)}</p>'
        # the ILLUSTRATIVE levers, named
        '<p class="ift-mono-src">'
        'Levers (all ILLUSTRATIVE, basis named): f_IFT = ground-IFT fraction of '
        'discharges; &lambda;_return = SNF&rarr;hospital/dialysis recurring legs '
        'per occupied bed/yr; s(m) = serviceable share 0.15–0.30 by '
        'insource-vs-outsource archetype; r_IFT = blended all-payer net revenue '
        'per transport (rural carries the super-rural mileage uplift). '
        + _basis_chip("ILLUSTRATIVE") + '</p>'
    )
    return header + ck_panel(body)


def _health_system_sam_section() -> str:
    """SAM = multi-hospital health systems — the STRUCTURAL addressable market,
    triangulated top-down (ratio) × bottoms-up (structure), ±MSA, with the
    health-system-biller insource ceiling and the ~1% nascent operator share."""
    header = ck_section_header(
        "National SAM — multi-hospital health systems",
        eyebrow="THE STRUCTURAL MARKET, TWO WAYS")
    try:
        hs = _an.health_system_sam()
    except Exception:  # noqa: BLE001
        hs = None
    if not (hs and hs.available):
        return header + ck_panel(
            '<p class="ift-prose">The structural SAM build is unavailable '
            'offline.</p>')

    step_rows = "".join(
        "<tr>"
        f"<td>{_esc(s.label)}</td>"
        f'<td class="ift-num">{_esc(s.value)}</td>'
        f"<td>{_basis_chip(s.basis)}</td>"
        f"<td>{_esc(s.detail)}</td>"
        "</tr>"
        for s in hs.steps)

    body = (
        f'<p class="ift-prose"><strong>{_esc(hs.headline)}</strong></p>'
        '<p class="ift-prose">The <strong>SAM</strong> is the market the operator '
        'actually competes for — the ground IFT of <em>multi-hospital health '
        'systems</em> that is addressable by an outsourced provider. It is sized '
        '<strong>two independent ways</strong> and triangulated: '
        '<strong>(A) top-down</strong>, a ratio build off the TAM '
        '(× the multi-hospital-system share of IFT dollars × the addressable '
        'share, where addressable = 1 − the health-system-biller insource '
        'ceiling); and <strong>(B) bottoms-up</strong>, the structure proxy for a '
        'claims-driven build — the SOURCED footprint SAM-per-bed scaled to the '
        'national multi-hospital-system bed base. The true bottoms-up build sums '
        'the claims whose origin or destination NPI sits in a multi-hospital '
        'system, split by billing-NPI ownership; that needs claims we do not hold '
        'offline, so (B) is the honest stand-in and reads low.</p>'
        # dual-method KPI band
        '<div class="ift-kpi-grid">'
        + _kpi("SAM — triangulated", _usd_b(hs.sam_central_bn),
               f"range {_usd_b(hs.sam_low_bn)}–{_usd_b(hs.sam_high_bn)}")
        + _kpi("(A) top-down ratio", _usd_b(hs.sam_td_central_bn),
               f"MSA-restricted {_usd_b(hs.sam_td_msa_central_bn)}")
        + _kpi("(B) bottoms-up structure",
               _usd_b(hs.sam_bu_central_bn) if hs.sam_bu_central_bn else "—",
               "Komodo-claims proxy (structure-extrapolated)")
        + _kpi("Insource ceiling ι",
               f"{hs.insource_ceiling[0]*100:.0f}–{hs.insource_ceiling[2]*100:.0f}%",
               "health-system-biller upper bound (non-addressable)")
        + '</div>'
        # the build steps
        '<p class="ift-sub">The funnel, step by step</p>'
        '<div class="ift-table-wrap"><table class="ift-table"><thead><tr>'
        '<th>Step</th><th>Value</th><th>Basis</th><th>Detail</th>'
        f'</tr></thead><tbody>{step_rows}</tbody></table></div>'
        # the nascent-share read
        '<p class="ift-sub">TAM &rarr; SAM &rarr; SOM, and where the operator sits</p>'
        '<div class="ift-kpi-grid">'
        + _kpi("TAM (all ground IFT)", _usd_b(hs.tam_central_bn),
               "no 911, no air, no NEMT")
        + _kpi("SAM (health systems)", _usd_b(hs.sam_central_bn),
               "structural, addressable")
        + _kpi("SOM (current footprint)", _usd_m(hs.som_central_m * 1e6),
               f"~{_pct(hs.operator_share_of_sam)} held today ≈ "
               f"{_usd_m(hs.operator_current_revenue_m * 1e6)}")
        + _kpi("SAM ÷ SOM headroom",
               (f"{hs.sam_over_som_multiple:.0f}×"
                if hs.sam_over_som_multiple else "—"),
               "structural headroom beyond the current metros")
        + '</div>'
        f'<p class="ift-mono-src">{_source_chip(hs.source_label)}</p>'
        f'<p class="ift-prose">{_esc(hs.note)}</p>'
    )
    return header + ck_panel(body)


def _footprint_table(structures, sam_by_name: Dict[str, float]) -> str:
    """Every target metro, its SOURCED facility counts, and its ILLUSTRATIVE
    per-metro SAM — one scannable table (the per-state numeric table)."""
    header = ck_section_header(
        "Every target metro at a glance", eyebrow="THE FOOTPRINT, IN NUMBERS",
        count=len(structures))
    if not structures:
        return header + ck_panel(
            '<p class="ift-prose">No metro structure computed offline.</p>')
    rows = "".join(
        "<tr>"
        f'<td><a href="#ift-{_esc(s.name.lower().replace(" ", "-").replace("/", "").replace("(", "").replace(")", ""))}" '
        f'class="ck-arrow">{_esc(s.name)}</a></td>'
        f"<td>{_esc(s.region_label)}</td>"
        f'<td class="ift-num">{_num(s.n_hospitals)}</td>'
        f'<td class="ift-num">{_num(s.hcris_beds)}</td>'
        f'<td class="ift-num">{_num(s.n_snf)}</td>'
        f'<td class="ift-num">{_num(s.snf_beds)}</td>'
        f'<td class="ift-num">{_num(s.n_irf)}</td>'
        f'<td class="ift-num">{_num(s.n_ltch)}</td>'
        f'<td class="ift-num">{_num(s.n_hospice)}</td>'
        f'<td class="ift-num">{_num(s.n_dialysis)}</td>'
        f'<td class="ift-num">{_esc(s.density_tier)}</td>'
        f'<td class="ift-num">{_usd_m(sam_by_name.get(s.name, 0.0))}</td>'
        "</tr>"
        for s in structures)
    body = (
        '<div class="ift-table-wrap"><table class="ift-table"><thead><tr>'
        '<th>Metro</th><th>State / region</th><th>Hosp</th><th>HCRIS beds</th>'
        '<th>SNF</th><th>SNF beds</th><th>IRF</th><th>LTCH</th><th>Hospice</th>'
        '<th>Dialysis</th><th>Density</th><th>SAM ($M)</th>'
        f'</tr></thead><tbody>{rows}</tbody></table></div>'
        '<p class="ift-mono-src">Origin + destination counts and HCRIS beds are '
        + _basis_chip("SOURCED")
        + ' (our vendored CMS estate); per-metro SAM is '
        + _basis_chip("ILLUSTRATIVE")
        + ' (SOURCED structure × labelled levers). Density tier reads the '
        'origin+destination node cluster — the unit-hour-utilization / deadhead '
        'moat.</p>'
    )
    return header + ck_panel(body)


def _footprint_map(structures) -> str:
    """A footprint US map shaded by the number of target metros touching each
    state (structural, from the registry). Honest, self-contained SVG."""
    per_state: Dict[str, int] = {}
    for md in _geo.MARKETS:
        for st in md.states:
            per_state[st.upper()] = per_state.get(st.upper(), 0) + 1
    if not per_state:
        return ""
    the_map = render_us_geo_map(
        {k: float(v) for k, v in per_state.items()},
        metric_label="target metros",
        value_format=lambda v: f"{int(v)}",
        map_title="Target-operator footprint — states by number of target metros",
        exposure_label="Target metros in state (low&nbsp;→&nbsp;high)",
        accent_label="—",
        caveat_text=(
            "Approximate Albers-projected US state map (public-domain Census "
            "boundaries). Shading is the count of target metros that touch each "
            "footprint state (bi-state metros — Kansas City KS/MO, Omaha NE/IA "
            "— count in both). Structural, from the footprint registry — not a "
            "facility-location map."),
        empty_message="")
    return (
        ck_section_header("Footprint map", eyebrow="WHERE THE OPERATOR RUNS")
        + ck_panel(the_map))


# ═══════════════════════════════════════════════════════════════════════════
#  Per-metro deep-dive card
# ═══════════════════════════════════════════════════════════════════════════
def _metro_anchor(name: str) -> str:
    return ("ift-" + name.lower().replace(" ", "-").replace("/", "")
            .replace("(", "").replace(")", ""))


def _metro_card(s, sam_dollars: float) -> str:
    """One target metro's deep-dive: anchor systems, SOURCED density, the
    insource-vs-outsource read, and the moat verdict."""
    anchors = "".join(f"<li>{_esc(a)}</li>" for a in s.anchor_systems) or \
        "<li>—</li>"
    ops = "".join(f"<span>{_esc(o)}</span>" for o in s.named_operators)
    caveats = "".join(
        f'<div class="ift-caveat"><b>Data caveat</b> — {_esc(c)}</div>'
        for c in s.data_caveats)

    # SOURCED density stat strip.
    stats = (
        '<div class="ift-stats">'
        + _stat(_num(s.n_hospitals), "hospitals")
        + _stat(_num(s.hcris_beds), "HCRIS beds")
        + _stat(_num(s.n_snf), "SNFs")
        + _stat(_num(s.snf_beds), "SNF beds")
        + _stat(_num(s.n_irf), "IRFs")
        + _stat(f"{_num(s.n_ltch)}/{_num(s.ltch_beds)}", "LTCH / beds")
        + _stat(_num(s.n_hospice), "hospices")
        + _stat(_num(s.n_home_health), "home-health")
        + _stat(_num(s.n_dialysis), "dialysis")
        + '</div>'
    )

    rural_tag = " · rural long-leg" if s.rural else ""
    meta = (
        '<div class="ift-meta">'
        f'<b>{_esc(s.profile)}</b>{_esc(rural_tag)} &middot; '
        f'density <b>{_esc(s.density_tier)}</b> &middot; '
        f'archetype <b>{_esc(s.insource_class)}</b> &middot; '
        f'metro SAM <b>{_usd_m(sam_dollars)}</b> {_basis_chip("ILLUSTRATIVE")}'
        '</div>'
    )

    body = (
        meta
        + '<p class="ift-sub">Anchor health systems — the IFT demand generators '
        '&amp; transfer/referral network</p>'
        f'<ul class="ift-list">{anchors}</ul>'
        + '<p class="ift-sub">Hospital + post-acute density (SOURCED origins &amp; '
        'destinations)</p>'
        + stats
        + f'<p class="ift-prose">{_esc(s.density_note)}</p>'
        + f'<p class="ift-mono-src">{_source_chip(s.source_label)}</p>'
        + '<p class="ift-sub">Competitive read — insource vs outsource</p>'
        + f'<p class="ift-prose">{_esc(s.insource_read)}</p>'
        + (f'<div class="ift-ops">{ops}</div>' if ops else "")
        + '<p class="ift-mono-src">Operators named from public / company web, '
        'labelled ' + _basis_chip("PUBLIC")
        + ' — no contract exclusivities asserted.</p>'
        + '<p class="ift-sub">Moat verdict</p>'
        + f'<div class="ift-verdict"><p class="ift-prose" style="margin:0;">'
        f'{_esc(s.moat_note)}</p></div>'
        + caveats
    )
    return ck_panel(body, title=s.name, anchor_id=_metro_anchor(s.name))


def _region_sections(structures, sam_by_name: Dict[str, float]) -> str:
    """Group the metro cards by state/region, in registry order."""
    by_region: Dict[str, List] = {}
    for s in structures:
        by_region.setdefault(s.region, []).append(s)

    out: List[str] = []
    for region_key, region_label in _geo.REGION_LABELS.items():
        metros = by_region.get(region_key, [])
        if not metros:
            continue
        out.append(ck_section_header(
            region_label, eyebrow="TARGET STATE / REGION", count=len(metros)))
        for s in metros:
            out.append(_metro_card(s, sam_by_name.get(s.name, 0.0)))
    return "".join(out)


# ═══════════════════════════════════════════════════════════════════════════
#  Page
# ═══════════════════════════════════════════════════════════════════════════
def render_ift_markets() -> str:
    """Render the IFT geographic deep-dive page. Degrades to an honest note if
    the offline structure is unavailable — never raises."""
    structures = _geo.all_metros()
    rollup = _geo.footprint_rollup()
    tam = _an.ground_tam()
    sam = _an.sam_formula()
    sam_by_name: Dict[str, float] = {}
    if sam and sam.available:
        for r in sam.rows:
            sam_by_name[r.name] = r.sam_dollars

    tam_central = (_usd_b(tam.allpayer_tam_bn_central)
                   if (tam and tam.available) else "—")
    sam_central = (_usd_m(sam.sam_dollars_central)
                   if (sam and sam.available) else "—")
    try:
        _hs = _an.health_system_sam()
    except Exception:  # noqa: BLE001
        _hs = None
    samhs_central = (_usd_b(_hs.sam_central_bn)
                     if (_hs and _hs.available) else "—")

    head = ck_editorial_head(
        "INTERFACILITY TRANSPORT · TARGET MARKETS",
        "Interfacility Transport — Target Markets",
        meta=(f"{_num(rollup.n_metros)} METROS · {_num(rollup.n_regions)} STATE "
              f"REGIONS · {_num(rollup.n_hospitals)} HOSPITALS · TAM {tam_central} · "
              f"SAM {samhs_central} · SOM {sam_central}"),
        lede_italic_phrase="Ground IFT, market by market —",
        lede_body=("the anchor health systems that generate the transfers, the "
                   "real hospital and post-acute density behind the demand, and "
                   "the insource-vs-outsource moat that decides who wins each "
                   "metro."),
        source_note=("Facility counts SOURCED from our vendored CMS estate; "
                     "anchor systems &amp; operators public/company-web, "
                     "labelled; every sizing lever labelled GOV or ILLUSTRATIVE."),
        show_legend=True,
    )

    # National-overview KPI strip.
    kpi_tam = ck_provenance_tooltip(
        "US ground-IFT TAM", f'{tam_central} {_basis_chip("ILLUSTRATIVE")}',
        explainer=(tam.headline if (tam and tam.available)
                   else "Top-down from the GOV MedPAC anchor, ex-NEMT ex-air."))
    kpi_samhs = ck_provenance_tooltip(
        "SAM — health systems", f'{samhs_central} {_basis_chip("ILLUSTRATIVE")}',
        explainer=(_hs.headline if (_hs and _hs.available)
                   else "Multi-hospital-health-system IFT, addressable by an "
                   "outsourced operator — top-down ratio × bottoms-up structure."),
        inject_css=False)
    kpi_sam = ck_provenance_tooltip(
        "Footprint SOM", f'{sam_central} {_basis_chip("ILLUSTRATIVE")}',
        explainer=("Serviceable-obtainable in the current footprint — bottom-up "
                   "from the real origins/destinations in the target metros × "
                   "labelled serviceable-share levers."),
        inject_css=False)
    kpi_strip = (
        '<div class="ift-kpi-grid">'
        + _kpi("US ground-IFT TAM", kpi_tam, "top-down, ex-NEMT ex-air")
        + _kpi("SAM — health systems", kpi_samhs, "structural, addressable")
        + _kpi("Footprint SOM", kpi_sam, "current markets, serviceable")
        + _kpi("Target metros", _num(rollup.n_metros),
               f"across {_num(rollup.n_regions)} state regions")
        + _kpi("Hospitals (origins)", _num(rollup.n_hospitals),
               f"{_num(rollup.hcris_beds)} HCRIS beds")
        + _kpi("SNF beds (destinations)", _num(rollup.snf_beds),
               f"{_num(rollup.n_snf)} SNFs — the discharge engine")
        + '</div>'
    )

    intro = ck_section_intro(
        "HOW TO READ THIS",
        "National frame first, then every metro up close.",
        italic_word="every",
        body=("Start with the funnel — TAM (all US ground IFT), SAM (the "
              "multi-hospital-health-system market, sized two ways), and SOM (the "
              "operator's current footprint, bottom-up from the real market "
              "structure). Then each target metro gets a deep-dive: its anchor "
              "systems and their transfer network, its SOURCED hospital + "
              "post-acute density, the competitive insource-vs-outsource read, "
              "and the moat verdict."))

    parts: List[str] = [
        _styles(),
        ck_eyebrow("IFT Target Markets"),
        head,
        _legend_row(),
        kpi_strip,
        intro,
        # National overview
        ck_section_intro(
            "NATIONAL OVERVIEW", "The funnel: TAM → SAM → SOM.",
            italic_word="funnel",
            body=("TAM is all US ground IFT (no 911, no air, no NEMT). SAM is the "
                  "structural market — the multi-hospital-health-system IFT that an "
                  "outsourced operator can address, sized top-down (ratio) and "
                  "bottoms-up (claims-structure proxy), ±MSA. SOM is what is "
                  "serviceable in the operator's current footprint; the operator "
                  "holds ~1% of SAM today.")),
        _tam_section(),
        _health_system_sam_section(),
        _sam_section(rollup, sam),
        _footprint_table(structures, sam_by_name),
        _footprint_map(structures),
        # Per-metro deep-dives, grouped by state
        ck_section_intro(
            "THE DEEP-DIVES", "Every target metro, grouped by state.",
            italic_word="Every",
            body=("Anchor systems (the demand generators), the SOURCED density "
                  "behind the demand, who runs the transfers today, and the "
                  "moat that makes the incumbent hard to displace.")),
        _region_sections(structures, sam_by_name),
        ck_next_section(
            "See the clinical acute-transfer demand engine behind this volume",
            "/ift-clinical",
            eyebrow="Demand driver", italic_word="clinical"),
        ck_next_section(
            "Read the full Interfacility Transport market report",
            "/market/interfacility_transport",
            eyebrow="Up next", italic_word="full"),
        ck_page_actions(),
    ]
    return chartis_shell("".join(parts),
                         "Interfacility Transport — Target Markets",
                         active_nav="/market")
