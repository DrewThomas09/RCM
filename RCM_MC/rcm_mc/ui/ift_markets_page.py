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
from ._chart_kit import (
    ck_bar_chart, ck_chart_assets, ck_chart_grid, ck_hbar_chart,
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
        # connector estate
        ".ift-estate-note{font-size:12.5px;color:var(--sc-text,#1a2332);"
        "line-height:1.55;max-width:82ch;margin:8px 0 10px;}"
        ".ift-estate-cat{font-family:var(--sc-sans);font-size:10px;font-weight:700;"
        "letter-spacing:0.07em;text-transform:uppercase;color:#fff;"
        "background:var(--sc-teal,#155752);padding:5px 10px;}"
        ".ift-estate-link{font-weight:600;color:var(--sc-navy,#0b2341);"
        "text-decoration:none;border-bottom:1px solid rgba(21,87,82,0.35);}"
        ".ift-estate-link:hover{color:var(--sc-teal,#155752);}"
        ".ift-estate-ds{font-family:var(--sc-mono);font-size:10px;"
        "color:var(--sc-text-faint,#7a8699);margin-top:2px;}"
        ".ift-estate-cite{font-size:11px;}"
        ".ift-estate-tbl td{font-size:11.5px;}"
        # tables
        ".ift-table{width:100%;border-collapse:collapse;background:#fff;"
        "border:1px solid var(--sc-rule,#d6cfc0);font-size:12px;margin:0 0 6px;}"
        ".ift-table th{text-align:left;padding:7px 10px;font-family:var(--sc-sans);"
        "font-size:9.5px;font-weight:600;letter-spacing:0.06em;text-transform:"
        "uppercase;color:var(--sc-text-dim,#465366);position:sticky;top:0;"
        "background:var(--sc-surface,#faf7f1);z-index:1;"
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
               f"{hs.insource_ceiling[0]*100:.1f}–{hs.insource_ceiling[2]*100:.1f}%",
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
               (f"{hs.sam_over_som_multiple:.2f}x"
                if hs.sam_over_som_multiple else "—"),
               "structural headroom beyond the current metros")
        + '</div>'
        f'<p class="ift-mono-src">{_source_chip(hs.source_label)}</p>'
        f'<p class="ift-prose">{_esc(hs.note)}</p>'
    )
    return header + ck_panel(body)


def _th(*cols: str) -> str:
    return ("<thead><tr>"
            + "".join(f"<th>{_esc(c)}</th>" for c in cols) + "</tr></thead>")


def _market_education_section() -> str:
    """Chapter one of the SOW: IFT is its own market — not 911, not NEMT, not air.
    Investors mis-price MMT when they anchor to 911 EMS or low-acuity brokers."""
    header = ck_section_header(
        "What IFT is — and what it is not",
        eyebrow="MARKET EDUCATION / THE BOUNDARY")
    body = (
        '<p class="ift-prose"><strong>IFT is ambulance transport BETWEEN '
        'healthcare facilities, ordered by hospitals and health systems.</strong> '
        'It is a health-system operating function — a bed-clearing, '
        'throughput-protecting service with its own customers, purchasing '
        'decisions, operating requirements, and reimbursement dynamics. It is the '
        'market MMT is actually in.</p>'
        '<div class="ift-table-wrap"><table class="ift-table">'
        + _th("IFT is", "IFT is NOT", "Why the distinction matters")
        + '<tbody>'
        '<tr><td>Hospital-to-hospital up-transfers to higher acuity (stroke, STEMI, '
        'trauma, NICU)</td><td><strong>911 / scene response</strong> — dispatched '
        'to a scene, not a facility; a different network, customer, and payer.</td>'
        '<td rowspan="4">Investors mis-price the asset when they compare MMT to '
        '911 EMS or low-acuity brokers. IFT has different customers (health-system '
        'transfer centers, not municipalities), different operating requirements '
        '(dedicated, scheduled, higher-acuity), and different reimbursement '
        '(ALS/CCT-skewed + commercial). Sizing off the whole ambulance or NEMT '
        'market is the single biggest error.</td></tr>'
        '<tr><td>Hospital-to-post-acute discharge legs (SNF / IRF / LTCH)</td>'
        '<td><strong>NEMT</strong> — Medicaid wheelchair van / livery / rideshare; '
        'a separate federally-mandated benefit, low acuity.</td></tr>'
        '<tr><td>Facility-origin critical-care / specialty transport (SCT, ECMO, '
        'neonatal)</td><td><strong>Air ambulance</strong> — a separate market with '
        'its own economics and balance-billing dynamics.</td></tr>'
        '<tr><td>Dedicated, scheduled, health-system-integrated ground missions</td>'
        '<td><strong>Generic medical logistics</strong> — organ / courier / '
        'non-patient transport.</td></tr>'
        '</tbody></table></div>'
        '<p class="ift-mono-src">Boundary held throughout this study: TAM counts '
        'ONLY US ground IFT. ' + _basis_chip("ILLUSTRATIVE") + '</p>')
    return header + ck_panel(body)


def _growth_levers_section() -> str:
    """The three things to TRACK: price/reimbursement inflation, volume/demographics,
    and consolidation (big systems getting bigger)."""
    header = ck_section_header(
        "Why the market grows — the three levers",
        eyebrow="GROWTH / PRICE x VOLUME + CONSOLIDATION")
    try:
        from ..market_reports import ift_tracking as _t
        bridge = _t.growth_bridge()
        levers = _t.all_levers()
    except Exception:  # noqa: BLE001
        bridge = levers = None
    if not (bridge and getattr(bridge, "available", False)):
        return header + ck_panel(
            '<p class="ift-prose">The growth-lever build is unavailable offline.</p>')

    def _pc(v):
        return f"{v:.1f}%/yr" if isinstance(v, (int, float)) else "—"

    kpis = (
        '<div class="ift-kpi-grid">'
        + _kpi("Price / reimbursement", _pc(bridge.price_central_pct),
               "AFS AIF + commercial OON + escalators")
        + _kpi("Volume / demographics", _pc(bridge.volume_central_pct),
               "aging + acuity + ED boarding + post-acute")
        + _kpi("= Organic market growth", _pc(bridge.market_growth_central_pct),
               f"range {_pc(bridge.market_growth_low_pct)}"
               f"-{bridge.market_growth_high_pct:.1f}%")
        + _kpi("+ Consolidation (share-shift)",
               _pc(bridge.consolidation_share_shift_central_pct),
               "big systems getting bigger — NOT organic")
        + _kpi("= Platform growth", _pc(bridge.platform_growth_central_pct),
               "what a well-positioned operator compounds")
        + '</div>')
    lever_rows = ""
    for lv in (levers or []):
        if not getattr(lv, "available", False):
            continue
        for comp in getattr(lv, "components", []):
            lever_rows += (
                "<tr>"
                f"<td>{_esc(comp.name)}</td>"
                f'<td class="ift-num">{_esc(comp.value)}</td>'
                f"<td>{_basis_chip(str(comp.basis).split()[0] if comp.basis else 'ILLUSTRATIVE')}</td>"
                f"<td>{_esc(comp.detail)}</td></tr>")
    table = (
        '<p class="ift-sub">Lever detail</p>'
        '<div class="ift-table-wrap"><table class="ift-table">'
        + _th("Driver", "Value", "Basis", "Detail")
        + f"<tbody>{lever_rows}</tbody></table></div>"
        f'<p class="ift-mono-src">{_source_chip(bridge.source_label)}</p>'
        f'<p class="ift-prose">{_esc(bridge.note)}</p>')
    return header + ck_panel(
        f'<p class="ift-prose"><strong>{_esc(bridge.headline)}</strong></p>'
        + kpis + table)


def _competitive_section() -> str:
    """Competitive archetypes + MMT positioning — MMT is not competing against many
    pure-play IFT platforms; most alternatives are 911-heavy / mixed / subscale."""
    header = ck_section_header(
        "Competitive landscape — archetypes & MMT's position",
        eyebrow="COMPETITION / WHERE MMT WINS")
    try:
        from ..market_reports import ift_competitive as _c
        arch = _c.competitive_archetypes()
        pos = _c.mmt_positioning()
    except Exception:  # noqa: BLE001
        arch = pos = None
    if not (arch and getattr(arch, "archetypes", None)):
        return header + ck_panel(
            '<p class="ift-prose">The competitive build is unavailable offline.</p>')
    arows = ""
    for a in arch.archetypes:
        arows += (
            "<tr>"
            f"<td><strong>{_esc(a.name)}</strong></td>"
            f"<td>{_esc(a.ift_posture)}</td>"
            f"<td>{_esc(a.scale_magnitude)}</td>"
            f"<td>{_esc('; '.join(a.example_operators) if isinstance(a.example_operators,(list,tuple)) else a.example_operators)}</td>"
            f"<td>{_esc(a.mmt_advantage)}</td></tr>")
    body = (
        '<p class="ift-prose">MMT is the <strong>dedicated outsourced IFT '
        'partner</strong> for health systems. Most alternatives are 911-heavy, '
        'mixed-model, regional, or subscale — the whitespace is a pure-play, '
        'health-system-integrated ground-IFT platform.</p>'
        '<div class="ift-table-wrap"><table class="ift-table">'
        + _th("Archetype", "IFT posture", "Scale", "Example operators (public)",
              "MMT advantage")
        + f"<tbody>{arows}</tbody></table></div>")
    if pos and getattr(pos, "pillars", None):
        prows = ""
        for p in pos.pillars:
            prows += (
                "<tr>"
                f"<td><strong>{_esc(p.pillar)}</strong></td>"
                f"<td>{_esc(p.mmt_stance)}</td>"
                f"<td>{_esc(p.vs_alternatives)}</td></tr>")
        body += (
            '<p class="ift-sub">MMT positioning</p>'
            '<div class="ift-table-wrap"><table class="ift-table">'
            + _th("Pillar", "MMT stance", "vs alternatives")
            + f"<tbody>{prows}</tbody></table></div>")
    body += ('<p class="ift-mono-src">Operator names are public / company-web, '
             'named honestly; scale &amp; contestability reads are '
             + _basis_chip("ILLUSTRATIVE") + '; density is '
             + _basis_chip("SOURCED") + '.</p>')
    return header + ck_panel(body)


def _insourcing_section() -> str:
    """The SOW's trickiest topic: classify by transport VOLUME, not asset ownership;
    the biller proxy is the insource ceiling; gross up claims for direct-bill/unbilled."""
    header = ck_section_header(
        "Insource vs outsource — and why claims undercount",
        eyebrow="ADDRESSABILITY / THE CLAIMS NUANCE")
    try:
        from ..market_reports import ift_insourcing as _i
        fw = _i.insourcing_framework()
        proxy = _i.biller_proxy()
        gross = _i.claims_grossup()
    except Exception:  # noqa: BLE001
        fw = proxy = gross = None
    if not (fw and getattr(fw, "bands", None)):
        return header + ck_panel(
            '<p class="ift-prose">The insourcing build is unavailable offline.</p>')
    brows = ""
    for b in fw.bands:
        share = f"{b.volume_share_low*100:.0f}-{b.volume_share_high*100:.0f}%"
        brows += (
            "<tr>"
            f"<td><strong>{_esc(b.name)}</strong></td>"
            f'<td class="ift-num">{_esc(share)}</td>'
            f"<td>{_esc(b.definition)}</td>"
            f"<td>{_esc(b.addressable_read)}</td></tr>")
    body = (
        '<p class="ift-prose"><strong>Classify by transport VOLUME, not asset '
        'ownership.</strong> A system that owns a few ambulances but outsources '
        'most of its IFT is hybrid-mostly-outsourced, not insourced — the '
        'addressable residual is real.</p>'
        '<div class="ift-table-wrap"><table class="ift-table">'
        + _th("Band (by volume share insourced)", "Insourced vol", "Definition",
              "Addressable read")
        + f"<tbody>{brows}</tbody></table></div>")
    if proxy and getattr(proxy, "available", False):
        body += (
            '<p class="ift-sub">The biller proxy = the insource ceiling</p>'
            f'<p class="ift-prose">{_esc(proxy.proxy_rule)}</p>'
            '<div class="ift-kpi-grid">'
            + _kpi("Insource ceiling", _pct(proxy.ceiling_central),
                   f"{_pct(proxy.ceiling_low)}-{_pct(proxy.ceiling_high)} "
                   "(health-system-biller upper bound)")
            + _kpi("Addressable (1 - ceiling)", _pct(proxy.addressable_central),
                   "what an outsourced operator can win")
            + '</div>')
    if gross and getattr(gross, "available", False):
        body += (
            '<p class="ift-sub">Why claims UNDERCOUNT — the gross-up</p>'
            f'<p class="ift-prose">{_esc(gross.headline)}</p>'
            '<div class="ift-kpi-grid">'
            + _kpi("Claims-observed", _usd_b(gross.claims_observed_bn),
                   "what claims alone show")
            + _kpi("Gross-up multiple",
                   f"{gross.multiplier_central:.2f}x",
                   "direct-bill (mom-and-pop -> hospital) + unbilled")
            + _kpi("True market", _usd_b(gross.true_market_bn),
                   "grossed up for the undercount")
            + '</div>'
            f'<p class="ift-mono-src">{_source_chip(gross.source_label)}</p>')
    return header + ck_panel(body)


def _moat_section() -> str:
    """Stickiness = first-call + 85%+ share-of-wallet + co-located assets + workflow
    integration + local density + switching costs + cross-market proof. Not software."""
    header = ck_section_header(
        "Why MMT is sticky — the moat scorecard",
        eyebrow="DEFENSIBILITY / 7 FACTORS + PROOF")
    try:
        from ..market_reports import ift_moat as _mo
        factors = _mo.moat_factors()
        board = _mo.market_moat_scores()
        proofs = _mo.proof_points()
    except Exception:  # noqa: BLE001
        factors = board = proofs = None
    if not factors:
        return header + ck_panel(
            '<p class="ift-prose">The moat build is unavailable offline.</p>')
    frows = ""
    for f in factors:
        frows += (
            "<tr>"
            f"<td><strong>{_esc(f.name)}</strong></td>"
            f"<td>{_esc(f.definition)}</td>"
            f"<td>{_esc(f.why_it_matters)}</td>"
            f"<td>{_esc(f.target or '—')}</td></tr>")
    body = (
        '<p class="ift-prose">Stickiness is not software alone. It compounds from '
        'first-call volume, 85%+ share-of-wallet, co-located dedicated assets, '
        'health-system workflow integration, local operating density, and high '
        'switching costs — evidenced across multiple markets.</p>'
        '<div class="ift-table-wrap"><table class="ift-table">'
        + _th("Factor", "Definition", "Why it matters", "Target")
        + f"<tbody>{frows}</tbody></table></div>")
    if board and getattr(board, "rows", None):
        fnames = [f.name for f in factors]
        srows = ""
        for mk in board.rows:
            if not getattr(mk, "available", True):
                continue
            by_name = {fs.factor_name: fs.score for fs in mk.factors}
            cells = "".join(
                f'<td>{_esc(by_name.get(n, "—"))}</td>' for n in fnames)
            srows += (
                "<tr>"
                f"<td><strong>{_esc(mk.name)}</strong></td>"
                f"{cells}"
                f'<td class="ift-num">{mk.composite_index:.2f}</td>'
                f"<td>{_esc(mk.overall_verdict)}</td></tr>")
        body += (
            '<p class="ift-sub">Per-market moat scores (ordinal; composite '
            '1.00-3.00, ILLUSTRATIVE)</p>'
            '<div class="ift-table-wrap"><table class="ift-table">'
            + _th("Metro", *([n for n in fnames] + ["Composite", "Verdict"]))
            + f"<tbody>{srows}</tbody></table></div>")
    if proofs and getattr(proofs, "points", None):
        prows = ""
        for pt in proofs.points:
            fns = ("; ".join(pt.factor_names)
                   if isinstance(pt.factor_names, (list, tuple)) else pt.factor_names)
            prows += (
                "<tr>"
                f"<td><strong>{_esc(pt.market)}</strong></td>"
                f"<td>{_esc(fns)}</td>"
                f"<td>{_esc(pt.claim)}</td>"
                f"<td>{_esc(pt.evidence)}</td></tr>")
        body += (
            '<p class="ift-sub">Cross-market proof points — a new entrant cannot '
            'easily replace the incumbent</p>'
            '<div class="ift-table-wrap"><table class="ift-table">'
            + _th("Market", "Factors proven", "Claim", "Evidence")
            + f"<tbody>{prows}</tbody></table></div>")
    body += ('<p class="ift-mono-src">Density is ' + _basis_chip("SOURCED")
             + '; the other factor reads + the composite are ordinal '
             + _basis_chip("ILLUSTRATIVE")
             + '; proof-point evidence is analyst/public-web, named honestly.</p>')
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
def _charts_section(sam_by_name: Dict[str, float]) -> str:
    """The visual 'at a glance' strip — SVG charts for the funnel, the three
    growth levers, the per-metro SOM ranking, and the per-metro moat composite.
    Every chart degrades to '' (dropped by ck_chart_grid) if its data is
    unavailable, so this never raises and never leaves an empty hole."""
    cards: List[str] = []

    # 1) TAM -> SAM -> SOM funnel (all in $M so the three tiers share a scale).
    try:
        tam = _an.ground_tam()
        hs = _an.health_system_sam()
        if tam.available and hs.available:
            funnel = [
                ("TAM · all ground IFT", tam.allpayer_tam_bn_central * 1000.0, "navy"),
                ("SAM · health systems", hs.sam_central_bn * 1000.0, "teal"),
                ("SOM · footprint", hs.som_central_m, "positive"),
            ]
            cards.append(ck_hbar_chart(
                "TAM → SAM → SOM ($M)", funnel,
                value_fmt=lambda v: (f"${v/1000:,.1f}B" if v >= 1000
                                     else f"${v:,.0f}M"),
                subtitle="The funnel, one scale — SAM is the structural prize, "
                         "SOM the current footprint (ILLUSTRATIVE).",
                source="ift_analytics · ILLUSTRATIVE build on GOV/SOURCED anchors",
                label_w=170.0))
    except Exception:  # noqa: BLE001
        pass

    # 2) The three growth levers (%/yr; consolidation is a share-shift).
    try:
        from ..market_reports import ift_tracking as _t
        gb = _t.growth_bridge()
        if gb.available:
            levers = [
                ("Price / reimbursement", gb.price_central_pct, "teal"),
                ("Volume / demographics", gb.volume_central_pct, "positive"),
                ("Consolidation (share-shift)",
                 gb.consolidation_share_shift_central_pct, "navy"),
            ]
            cards.append(ck_bar_chart(
                "Three growth levers (%/yr)", levers,
                value_fmt=lambda v: f"{v:+.1f}%",
                subtitle="Price × volume compound to organic market growth; "
                         "consolidation is a platform share-shift, not organic.",
                source="ift_tracking · GOV AIF anchor + ILLUSTRATIVE composites"))
    except Exception:  # noqa: BLE001
        pass

    # 3) Per-metro SOM ranking (top markets by serviceable dollars).
    try:
        if sam_by_name:
            top = sorted(sam_by_name.items(), key=lambda kv: kv[1],
                         reverse=True)[:12]
            items = [(name, val / 1e6, "teal") for name, val in top]
            cards.append(ck_hbar_chart(
                "Footprint SOM by metro ($M)", items,
                value_fmt=lambda v: f"${v:,.1f}M",
                subtitle="Where the current-footprint serviceable dollars "
                         "concentrate (bottom-up, ILLUSTRATIVE).",
                source="ift_analytics.sam_formula · SOURCED structure × "
                       "ILLUSTRATIVE levers", label_w=150.0))
    except Exception:  # noqa: BLE001
        pass

    # 4) Per-metro moat composite (ordinal 1.00-3.00).
    try:
        from ..market_reports import ift_moat as _mo
        board = _mo.market_moat_scores()
        rows = [r for r in getattr(board, "rows", [])
                if getattr(r, "available", True)]
        if rows:
            rows = sorted(rows, key=lambda r: r.composite_index, reverse=True)[:12]
            items = [(r.name, r.composite_index, "navy") for r in rows]
            cards.append(ck_hbar_chart(
                "Moat composite by metro (1.00–3.00)", items,
                value_fmt=lambda v: f"{v:.2f}",
                reference=("mid", 2.0),
                subtitle="Higher = stickier incumbency (first-call, density, "
                         "switching costs) — ordinal, ILLUSTRATIVE composite.",
                source="ift_moat · ift_geo reads × SOURCED density",
                label_w=150.0))
    except Exception:  # noqa: BLE001
        pass

    grid = ck_chart_grid(*cards)
    if not grid:
        return ""
    return (ck_section_header("At a glance", eyebrow="THE NUMBERS, VISUALLY")
            + grid)


def _connector_estate_section() -> str:
    """The live data-connector estate behind the study — every IFT-relevant
    public-data hook, its status (live vs ingest-ready), what it yields, and a
    link into the estate browser. Surfaces the same map the workbook's
    Connectors sheet carries, so the pages and the download agree. Degrades to
    "" if the estate module is unavailable."""
    try:
        from ..market_reports import ift_connectors as _ic
    except Exception:  # noqa: BLE001
        return ""
    try:
        probes = _ic.connector_estate_map()
        summ = _ic.estate_summary(probes)
    except Exception:  # noqa: BLE001
        return ""
    if not probes:
        return ""
    kpis = (
        '<div class="ift-kpi-grid">'
        + _kpi("Connector hooks", str(summ.total),
               f"{summ.available} live · {summ.gated} ingest-ready")
        + _kpi("Public-data sources", str(summ.n_connectors),
               "CMS · Census · BLS · CDC · HRSA · NPPES …")
        + _kpi("Signal categories", str(len(summ.by_category)),
               " · ".join(c for c, _ in summ.by_category))
        + '</div>')
    _CAT_LABEL = {
        "Supply": "Supply — who can run the transports",
        "Demand": "Demand — who needs to move",
        "Facilities": "Facilities — the origin/destination universe",
        "Reimbursement": "Reimbursement — how transports get paid",
        "Coverage": "Coverage — the medical-necessity rules",
        "Clinical": "Clinical — condition severity & coding",
        "Rural": "Rural — the mileage economics",
    }
    body_rows: List[str] = []
    for cat, _n in summ.by_category:
        group = [p for p in probes if p.category == cat]
        if not group:
            continue
        body_rows.append(
            f'<tr><td colspan="4" class="ift-estate-cat">'
            f'{_esc(_CAT_LABEL.get(cat, cat))}</td></tr>')
        for p in group:
            live = p.available
            status = (
                '<span class="ift-chip ift-chip-sourced">LIVE</span>' if live
                else '<span class="ift-chip ift-chip-connector">INGEST-READY'
                     '</span>')
            href = "/connector-estate?dataset=" + _esc(p.dataset_id)
            body_rows.append(
                '<tr>'
                f'<td><a class="ift-estate-link" href="{href}">'
                f'{_esc(p.title)}</a><div class="ift-estate-ds">'
                f'{_esc(p.connector)} · {_esc(p.dataset_id)}</div></td>'
                f'<td>{_esc(p.ift_signal)}</td>'
                f'<td>{status}</td>'
                f'<td class="ift-estate-cite">{_source_chip(p.source_label)}</td>'
                '</tr>')
    table = (
        '<div class="ift-table-wrap"><table class="ift-table ift-estate-tbl">'
        '<thead><tr><th>Connector</th><th>What it yields for IFT</th>'
        '<th>Status</th><th>Source / fallback</th></tr></thead>'
        f'<tbody>{"".join(body_rows)}</tbody></table></div>')
    note = (
        '<p class="ift-estate-note">The wiring is real — every dataset is a '
        'registered estate dataset, so each hook flips from <em>ingest-ready</em> '
        'to <strong>live</strong> the moment the estate is ingested. Offline, '
        'each cites an honest GOV/ACADEMIC fallback — never a fabricated number. '
        '<a href="/connector-estate">Browse the full 16-connector estate &rarr;</a>'
        '</p>')
    return (
        ck_section_header(
            "Live data estate", eyebrow="THE CONNECTORS BEHIND THE STUDY",
            count=f"{summ.total} hooks / {summ.n_connectors} sources")
        + kpis + note + table)


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

    download = (
        '<div style="margin:14px 0 6px;padding:14px 18px;border:1px solid '
        'var(--sc-border,#e4dccb);border-left:3px solid var(--sc-teal,#155752);'
        'border-radius:4px;background:var(--sc-surface,#faf7f1);display:flex;'
        'flex-wrap:wrap;gap:12px;align-items:center;justify-content:space-between;">'
        '<div style="font-family:var(--sc-serif,Georgia,serif);font-size:14px;'
        'color:var(--sc-text,#1a2332);max-width:78ch;">'
        '<strong>Investor data pack.</strong> Every sourced figure — the '
        'TAM&nbsp;&rarr;&nbsp;SAM&nbsp;&rarr;&nbsp;SOM build, each target market\'s '
        'facility structure and sizing, the clinical demand spine, and the '
        'competitive / insourcing / moat / three-lever layers — in one auditable '
        'workbook, every cell carrying its honesty basis.</div>'
        '<div style="flex:none;display:flex;gap:8px;align-items:center;">'
        '<a href="/connector-estate" '
        'style="font-family:var(--sc-mono,Consolas,monospace);font-size:12px;'
        'font-weight:600;letter-spacing:0.04em;text-decoration:none;'
        'color:var(--sc-teal,#155752);border:1px solid var(--sc-teal,#155752);'
        'padding:8px 14px;border-radius:3px;">Data estate</a>'
        '<a href="/api/ift/markets.xlsx" download '
        'style="font-family:var(--sc-mono,Consolas,monospace);'
        'font-size:12px;font-weight:600;letter-spacing:0.04em;text-decoration:none;'
        'color:#fff;background:var(--sc-teal,#155752);padding:9px 16px;'
        'border-radius:3px;">Download Excel &darr;</a></div></div>')

    parts: List[str] = [
        _styles(),
        ck_chart_assets(),
        ck_eyebrow("IFT Target Markets"),
        head,
        _legend_row(),
        kpi_strip,
        _charts_section(sam_by_name),
        download,
        intro,
        # Chapter one — teach the market: IFT is its own thing (not 911/NEMT/air).
        _market_education_section(),
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
        # The investor questions: why it grows, who competes, is it addressable,
        # and why the incumbent is sticky.
        _growth_levers_section(),
        _competitive_section(),
        _insourcing_section(),
        _moat_section(),
        _footprint_table(structures, sam_by_name),
        _footprint_map(structures),
        # The live data-connector estate behind every SOURCED figure.
        _connector_estate_section(),
        # Per-metro deep-dives, grouped by state
        ck_section_intro(
            "THE DEEP-DIVES", "Every target metro, grouped by state.",
            italic_word="Every",
            body=("Anchor systems (the demand generators), the SOURCED density "
                  "behind the demand, who runs the transfers today, and the "
                  "moat that makes the incumbent hard to displace.")),
        _region_sections(structures, sam_by_name),
        ck_next_section(
            "Read the full investor market study (taxonomy, ecosystem, "
            "health-system POV, MMT vs the field)",
            "/ift-study",
            eyebrow="Investor study", italic_word="investor"),
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
