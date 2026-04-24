"""Counterfactual Advisor page — premium Bloomberg-tier design.

Design principles used here:

    - Strict 4/8/12/16/24/32/48 spacing scale; no ad-hoc paddings.
    - Typographic hierarchy: eyebrow (9px uppercase letter-spaced)
      → headline (22-32px serif/mono) → body (12-13px) → caption
      (10-11px muted).
    - Severity as colored left-border + colored pill badges;
      no coloured backgrounds except the hero stat.
    - JetBrains Mono for every number. Inter Tight for everything
      else.
    - Every interactive element has a hover transition.
    - One stat-card component, one insight-card component, one
      metric-row component — reused. Reduces design surface area.

The page uses the existing Chartis shell, which already ships the
Bloomberg-style left nav + dark palette. This module focuses on
the content surface only.
"""
from __future__ import annotations

import html
from typing import Any, Dict, List, Optional
from urllib.parse import urlencode

from ..diligence.counterfactual import (
    CounterfactualLever, CounterfactualSet, advise_all,
    counterfactual_bridge_lever, run_counterfactuals_from_ccd,
    summarize_ccd_inputs,
)
from ._chartis_kit import P, chartis_shell


# ── Design system primitives ──────────────────────────────────────

# Spacing scale. Use via f"{S[1]}" etc. to keep spacing disciplined.
S = (0, 4, 8, 12, 16, 24, 32, 48, 64)

_SEVERITY_COLOR = {
    "GREEN":      P["positive"],
    "LOW":        P["positive"],
    "IMMATERIAL": P["positive"],
    "YELLOW":     P["warning"],
    "WATCH":      P["warning"],
    "MEDIUM":     P["warning"],
    "RED":        P["negative"],
    "HIGH":       P["negative"],
    "CRITICAL":   P["negative"],
    "UNKNOWN":    P["text_faint"],
}


def _feasibility_color(f: str) -> str:
    return {
        "HIGH": P["positive"],
        "MEDIUM": P["warning"],
        "LOW": P["negative"],
    }.get(f, P["text_dim"])


def _page_style() -> str:
    """Scoped style block — every class prefixed with `cf-` so it
    does not collide with the Chartis shell or other pages."""
    return f"""<style>
/* ── Counterfactual Advisor — scoped premium design ── */
.cf-hero {{
    padding: {S[5]}px 0 {S[3]}px 0;
    border-bottom: 1px solid {P["border"]};
    margin-bottom: {S[5]}px;
}}
.cf-hero-top {{
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    gap: {S[3]}px;
}}
.cf-eyebrow {{
    font-size: 9px;
    letter-spacing: 1.5px;
    text-transform: uppercase;
    color: {P["text_faint"]};
    font-weight: 600;
    margin-bottom: {S[2]}px;
}}
.cf-title {{
    font-size: 26px;
    color: {P["text"]};
    font-weight: 600;
    letter-spacing: -0.2px;
}}
.cf-download {{
    font-size: 10px;
    color: {P["accent"]};
    letter-spacing: 1px;
    text-transform: uppercase;
    font-weight: 600;
    border: 1px solid {P["border"]};
    padding: 6px 14px;
    border-radius: 3px;
    text-decoration: none;
    transition: all 0.15s ease;
    white-space: nowrap;
}}
.cf-download:hover {{
    background: {P["accent"]};
    color: {P["panel"]};
    border-color: {P["accent"]};
    text-decoration: none;
}}
.cf-stats {{
    display: flex;
    gap: {S[7]}px;
    margin-top: {S[4]}px;
    align-items: flex-end;
}}
.cf-stat {{
    display: flex;
    flex-direction: column;
    gap: {S[1]}px;
}}
.cf-stat-label {{
    font-size: 9px;
    letter-spacing: 1px;
    text-transform: uppercase;
    color: {P["text_faint"]};
    font-weight: 600;
}}
.cf-stat-value {{
    font-size: 36px;
    font-weight: 700;
    font-family: 'JetBrains Mono', monospace;
    font-variant-numeric: tabular-nums;
    line-height: 1;
    letter-spacing: -0.5px;
}}
.cf-stat-value.cf-dollar {{
    font-size: 28px;
}}

.cf-ccd-summary {{
    background: {P["panel_alt"]};
    border: 1px solid {P["border"]};
    border-radius: 4px;
    padding: {S[3]}px {S[4]}px;
    margin-bottom: {S[5]}px;
}}
.cf-ccd-summary-label {{
    font-size: 9px;
    letter-spacing: 1.5px;
    text-transform: uppercase;
    color: {P["text_faint"]};
    font-weight: 600;
    margin-bottom: {S[2]}px;
}}
.cf-ccd-grid {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
    gap: {S[3]}px {S[5]}px;
}}
.cf-ccd-cell {{
    display: flex;
    flex-direction: column;
    gap: 2px;
}}
.cf-ccd-cell-label {{
    font-size: 10px;
    color: {P["text_faint"]};
}}
.cf-ccd-cell-value {{
    font-family: 'JetBrains Mono', monospace;
    font-size: 13px;
    color: {P["text"]};
    font-variant-numeric: tabular-nums;
}}

.cf-section-head {{
    font-size: 10px;
    letter-spacing: 1.5px;
    text-transform: uppercase;
    color: {P["text_faint"]};
    font-weight: 700;
    margin: {S[6]}px 0 {S[3]}px 0;
}}

.cf-card {{
    background: {P["panel"]};
    border: 1px solid {P["border"]};
    border-radius: 4px;
    border-left-width: 4px;
    padding: {S[4]}px {S[5]}px;
    margin-bottom: {S[3]}px;
    transition: border-color 0.2s ease, transform 0.2s ease;
}}
.cf-card:hover {{
    transform: translateY(-1px);
}}
.cf-card-head {{
    display: flex;
    justify-content: space-between;
    gap: {S[3]}px;
    align-items: flex-start;
    margin-bottom: {S[3]}px;
}}
.cf-card-head-left {{
    flex: 1;
    min-width: 0;
}}
.cf-card-module {{
    font-size: 9px;
    letter-spacing: 1.5px;
    text-transform: uppercase;
    color: {P["text_faint"]};
    font-weight: 600;
    margin-bottom: {S[1]}px;
}}
.cf-card-action {{
    font-size: 16px;
    color: {P["text"]};
    font-weight: 600;
    line-height: 1.4;
    letter-spacing: -0.1px;
}}
.cf-band-row {{
    margin-top: {S[2]}px;
    display: flex;
    align-items: center;
    gap: {S[2]}px;
    flex-wrap: wrap;
}}
.cf-pill {{
    display: inline-block;
    font-size: 9px;
    letter-spacing: 1px;
    text-transform: uppercase;
    font-weight: 700;
    padding: 3px 8px;
    border-radius: 2px;
    background: {P["panel_alt"]};
}}
.cf-arrow {{
    color: {P["text_dim"]};
    font-size: 12px;
    margin: 0 2px;
}}
.cf-feasibility {{
    font-size: 9px;
    letter-spacing: 1px;
    text-transform: uppercase;
    font-weight: 600;
    margin-left: {S[2]}px;
}}
.cf-savings-cell {{
    text-align: right;
    min-width: 140px;
}}
.cf-savings-label {{
    font-size: 9px;
    letter-spacing: 1px;
    text-transform: uppercase;
    color: {P["text_faint"]};
    font-weight: 600;
    margin-bottom: 2px;
}}
.cf-savings-value {{
    font-size: 20px;
    font-weight: 700;
    font-family: 'JetBrains Mono', monospace;
    color: {P["positive"]};
    font-variant-numeric: tabular-nums;
    line-height: 1;
}}
.cf-savings-qual {{
    font-size: 11px;
    color: {P["text_faint"]};
    font-style: italic;
}}
.cf-narrative {{
    font-size: 12px;
    color: {P["text_dim"]};
    line-height: 1.55;
    margin-top: {S[2]}px;
}}
.cf-implication {{
    font-size: 11px;
    color: {P["text_faint"]};
    line-height: 1.55;
    margin-top: {S[3]}px;
    padding-top: {S[3]}px;
    border-top: 1px solid {P["border"]};
}}
.cf-implication-label {{
    color: {P["text_dim"]};
    font-weight: 600;
    font-size: 10px;
    letter-spacing: .5px;
    text-transform: uppercase;
    margin-right: {S[1]}px;
}}

.cf-bridge {{
    margin-top: {S[6]}px;
    background: {P["panel"]};
    border: 1px solid {P["border"]};
    border-radius: 4px;
    padding: {S[5]}px;
    position: relative;
    overflow: hidden;
}}
.cf-bridge::before {{
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 2px;
    background: linear-gradient(90deg, {P["positive"]}, {P["accent"]});
}}
.cf-bridge-head {{
    display: flex;
    gap: {S[6]}px;
    align-items: flex-end;
    margin-top: {S[2]}px;
}}
.cf-bridge-stat {{
    display: flex;
    flex-direction: column;
    gap: 2px;
}}
.cf-bridge-impact {{
    font-size: 24px;
    font-weight: 700;
    font-family: 'JetBrains Mono', monospace;
    color: {P["positive"]};
    line-height: 1;
}}
.cf-prov-table {{
    width: 100%;
    margin-top: {S[4]}px;
    border-collapse: collapse;
    font-size: 11px;
}}
.cf-prov-table th {{
    text-align: left;
    padding: {S[2]}px {S[3]}px;
    border-bottom: 1px solid {P["border"]};
    color: {P["text_dim"]};
    font-size: 9px;
    letter-spacing: 1px;
    text-transform: uppercase;
    font-weight: 600;
}}
.cf-prov-table td {{
    padding: {S[2]}px {S[3]}px;
    border-bottom: 1px solid {P["border_dim"]
        if "border_dim" in P else P["border"]};
    color: {P["text"]};
}}
.cf-prov-table td.cf-num {{
    font-family: 'JetBrains Mono', monospace;
    text-align: right;
}}

.cf-empty {{
    padding: {S[5]}px {S[6]}px;
    background: {P["panel"]};
    border-left: 3px solid {P["positive"]};
    border-radius: 4px;
    margin-top: {S[3]}px;
}}
.cf-empty-head {{
    font-size: 15px;
    color: {P["positive"]};
    font-weight: 600;
}}
.cf-empty-body {{
    font-size: 12px;
    color: {P["text_dim"]};
    margin-top: {S[1]}px;
    line-height: 1.5;
}}

.cf-form {{
    background: {P["panel"]};
    border: 1px solid {P["border"]};
    border-radius: 4px;
    padding: {S[5]}px {S[6]}px;
    max-width: 560px;
    margin-top: {S[3]}px;
}}
.cf-form-label {{
    font-size: 9px;
    letter-spacing: 1.5px;
    text-transform: uppercase;
    color: {P["text_faint"]};
    font-weight: 600;
    display: block;
    margin-top: {S[3]}px;
    margin-bottom: {S[1]}px;
}}
.cf-form-label:first-of-type {{
    margin-top: 0;
}}
.cf-form input, .cf-form select {{
    width: 100%;
    padding: {S[2]}px {S[3]}px;
    background: {P["panel_alt"]};
    color: {P["text"]};
    border: 1px solid {P["border"]};
    font-family: inherit;
    font-size: 12px;
    transition: border-color 0.15s ease;
}}
.cf-form input:focus, .cf-form select:focus {{
    outline: none;
    border-color: {P["accent"]};
}}
.cf-form button {{
    margin-top: {S[4]}px;
    padding: {S[3]}px {S[5]}px;
    background: {P["accent"]};
    color: {P["panel"]};
    border: 0;
    font-size: 10px;
    letter-spacing: 1.5px;
    text-transform: uppercase;
    font-weight: 700;
    cursor: pointer;
    transition: transform 0.15s ease;
}}
.cf-form button:hover {{
    transform: translateY(-1px);
}}
</style>"""


# ── Landing page ──────────────────────────────────────────────────

def _landing_page() -> str:
    from ..diligence._pages import AVAILABLE_FIXTURES
    options = "".join(
        f'<option value="{html.escape(name)}">{html.escape(label)}</option>'
        for name, label in AVAILABLE_FIXTURES
    )
    body = (
        _page_style()
        + '<div class="cf-hero">'
        + '<div class="cf-eyebrow">Counterfactual Advisor</div>'
        + '<div class="cf-title">What Would Change Our Mind?</div>'
        + f'<div style="font-size:13px;color:{P["text_dim"]};'
        + f'max-width:720px;line-height:1.6;margin-top:{S[3]}px;">'
        + 'For every RED / CRITICAL finding, the advisor back-solves '
        + 'the minimum input change that flips the band — the answer '
        + 'to the partner question: <em style="color:'
        + f'{P["text"]};">is there an offer modification that fixes '
        + 'this?</em> Runs across CPOM, NSA, Steward Score, TEAM, '
        + 'antitrust, cyber, and site-neutral.</div>'
        + '</div>'
        + '<form method="GET" action="/diligence/counterfactual" class="cf-form">'
        + '<label class="cf-form-label">Dataset</label>'
        + f'<select name="dataset" required><option value="">— pick a CCD fixture —</option>{options}</select>'
        + '<label class="cf-form-label">Structure (optional)</label>'
        + '<select name="legal_structure">'
        + '<option value="">(none)</option>'
        + '<option>FRIENDLY_PC_PASS_THROUGH</option>'
        + '<option>MSO_PC_MANAGEMENT_FEE</option>'
        + '<option>DIRECT_EMPLOYMENT</option>'
        + '<option>PROFESSIONAL_LLC</option></select>'
        + '<label class="cf-form-label">States (comma-separated)</label>'
        + '<input name="states" placeholder="OR, WA">'
        + '<label class="cf-form-label">Specialty (optional — enables NSA)</label>'
        + '<input name="specialty" placeholder="EMERGENCY_MEDICINE">'
        + '<label class="cf-form-label">Landlord (optional — enables Steward)</label>'
        + '<input name="landlord" placeholder="Medical Properties Trust">'
        + '<button type="submit">Run advisor</button>'
        + '</form>'
    )
    return chartis_shell(
        body, "RCM Diligence — Counterfactual Advisor",
        subtitle="What Would Change Your Mind",
    )


# ── Section renderers ────────────────────────────────────────────

def _render_hero(
    dataset: str, cf_set: CounterfactualSet,
    lever: CounterfactualLever,
    download_url: str,
) -> str:
    # Hero color reflects overall posture.
    if cf_set.critical_findings_addressed == 0 and not cf_set.items:
        primary_color = P["positive"]
    elif cf_set.critical_findings_addressed <= 2:
        primary_color = P["warning"]
    else:
        primary_color = P["negative"]
    bridge_dollar_str = (
        f'${lever.ebitda_impact_usd:,.0f}'
        if lever.ebitda_impact_usd > 0 else "—"
    )
    return (
        f'<div class="cf-hero">'
        f'  <div class="cf-hero-top">'
        f'    <div>'
        f'      <div class="cf-eyebrow">Counterfactual Advisor</div>'
        f'      <div class="cf-title">{html.escape(dataset)}</div>'
        f'    </div>'
        f'    <a href="{html.escape(download_url)}" target="_blank" '
        f'class="cf-download">Download JSON</a>'
        f'  </div>'
        f'  <div class="cf-stats">'
        f'    <div class="cf-stat">'
        f'      <div class="cf-stat-label">Counterfactuals</div>'
        f'      <div class="cf-stat-value" style="color:{primary_color};">'
        f'{len(cf_set.items)}</div>'
        f'    </div>'
        f'    <div class="cf-stat">'
        f'      <div class="cf-stat-label">Critical addressed</div>'
        f'      <div class="cf-stat-value" style="color:{primary_color};">'
        f'{cf_set.critical_findings_addressed}</div>'
        f'    </div>'
        f'    <div class="cf-stat">'
        f'      <div class="cf-stat-label">Bridge lever (EBITDA)</div>'
        f'      <div class="cf-stat-value cf-dollar" style="color:{P["positive"]};">'
        f'{bridge_dollar_str}</div>'
        f'    </div>'
        f'  </div>'
        f'</div>'
    )


def _render_ccd_summary(summary: Dict[str, Any]) -> str:
    cells = [
        ("Claims in CCD", f"{summary.get('claim_count', 0):,}"),
        ("Total paid", f"${summary.get('total_paid_usd', 0):,.0f}"),
        ("OON paid",   f"${summary.get('oon_paid_usd', 0):,.0f}"),
        ("OON share",  f"{(summary.get('oon_share') or 0)*100:.1f}%"),
        ("HOPD revenue",
         f"${summary.get('hopd_revenue_usd', 0):,.0f}"),
        ("Commercial HHI",
         f"{summary.get('commercial_hhi'):,.0f}"
         if summary.get("commercial_hhi") is not None else "—"),
    ]
    cell_html = "".join(
        f'<div class="cf-ccd-cell">'
        f'<div class="cf-ccd-cell-label">{html.escape(label)}</div>'
        f'<div class="cf-ccd-cell-value">{html.escape(val)}</div>'
        f'</div>'
        for label, val in cells
    )
    return (
        f'<div class="cf-ccd-summary">'
        f'<div class="cf-ccd-summary-label">Derived from CCD</div>'
        f'<div class="cf-ccd-grid">{cell_html}</div>'
        f'</div>'
    )


def _render_counterfactuals(cf_set: CounterfactualSet) -> str:
    if not cf_set.items:
        return (
            '<div class="cf-empty">'
            '<div class="cf-empty-head">No RED or CRITICAL findings.</div>'
            '<div class="cf-empty-body">Nothing for the advisor to '
            'counterfactual. Proceed to the Risk Workbench for the '
            'full panel view.</div>'
            '</div>'
        )
    rows: List[str] = []
    for cf in cf_set.items:
        orig_color = _SEVERITY_COLOR.get(cf.original_band, P["text"])
        target_color = _SEVERITY_COLOR.get(cf.target_band, P["text"])
        feas_color = _feasibility_color(cf.feasibility)
        if cf.estimated_dollar_impact_usd > 0:
            dollar_html = (
                f'<div class="cf-savings-value">'
                f'${cf.estimated_dollar_impact_usd:,.0f}</div>'
            )
        else:
            dollar_html = '<div class="cf-savings-qual">qualitative</div>'
        rows.append(
            f'<div class="cf-card" style="border-left-color:{target_color};">'
            f'  <div class="cf-card-head">'
            f'    <div class="cf-card-head-left">'
            f'      <div class="cf-card-module">{html.escape(cf.module)}</div>'
            f'      <div class="cf-card-action">{html.escape(cf.change_description)}</div>'
            f'      <div class="cf-band-row">'
            f'        <span class="cf-pill" style="color:{orig_color};">'
            f'{html.escape(cf.original_band)}</span>'
            f'        <span class="cf-arrow">→</span>'
            f'        <span class="cf-pill" style="color:{target_color};">'
            f'{html.escape(cf.target_band)}</span>'
            f'        <span class="cf-feasibility" style="color:{feas_color};">'
            f'feasibility {html.escape(cf.feasibility)}</span>'
            f'      </div>'
            f'    </div>'
            f'    <div class="cf-savings-cell">'
            f'      <div class="cf-savings-label">Savings estimate</div>'
            f'      {dollar_html}'
            f'    </div>'
            f'  </div>'
            f'  <div class="cf-narrative">{html.escape(cf.narrative)}</div>'
            f'  <div class="cf-implication">'
            f'<span class="cf-implication-label">Deal structure:</span>'
            f'{html.escape(cf.deal_structure_implication)}</div>'
            f'</div>'
        )
    return (
        f'<div class="cf-section-head">Counterfactuals</div>'
        f'{"".join(rows)}'
    )


def _render_bridge_lever(lever: CounterfactualLever) -> str:
    if lever.ebitda_impact_usd <= 0:
        return ""
    conf_color = {
        "HIGH": P["positive"],
        "MEDIUM": P["warning"],
        "LOW": P["negative"],
    }.get(lever.confidence, P["text_dim"])
    prov_rows = "".join(
        f'<tr>'
        f'<td>{html.escape(p["module"])}</td>'
        f'<td style="font-family:\'JetBrains Mono\',monospace;font-size:10px;">'
        f'{html.escape(p["lever"])}</td>'
        f'<td class="cf-num">${p["raw_impact_usd"]:,.0f}</td>'
        f'<td class="cf-num">${p["effective_impact_usd"]:,.0f}</td>'
        f'<td>{html.escape(p["feasibility"])}</td>'
        f'</tr>'
        for p in lever.provenance
    )
    return (
        f'<div class="cf-bridge">'
        f'  <div class="cf-eyebrow">EBITDA Bridge Lever</div>'
        f'  <div style="font-size:18px;color:{P["text"]};font-weight:600;'
        f'margin-top:{S[1]}px;">Reg-Risk Mitigation (Counterfactual)</div>'
        f'  <div class="cf-bridge-head">'
        f'    <div class="cf-bridge-stat">'
        f'      <div class="cf-stat-label">EBITDA impact</div>'
        f'      <div class="cf-bridge-impact">${lever.ebitda_impact_usd:,.0f}</div>'
        f'    </div>'
        f'    <div class="cf-bridge-stat">'
        f'      <div class="cf-stat-label">Realization prob.</div>'
        f'      <div style="font-size:15px;color:{P["text"]};font-weight:500;">'
        f'{lever.realization_probability*100:.0f}%</div>'
        f'    </div>'
        f'    <div class="cf-bridge-stat">'
        f'      <div class="cf-stat-label">Confidence</div>'
        f'      <div style="font-size:15px;color:{conf_color};font-weight:600;">'
        f'{html.escape(lever.confidence)}</div>'
        f'    </div>'
        f'  </div>'
        f'  <table class="cf-prov-table">'
        f'    <thead><tr>'
        f'      <th>Module</th><th>Lever</th>'
        f'      <th style="text-align:right;">Raw</th>'
        f'      <th style="text-align:right;">Effective</th>'
        f'      <th>Feasibility</th>'
        f'    </tr></thead>'
        f'    <tbody>{prov_rows}</tbody>'
        f'  </table>'
        f'</div>'
    )


# ── Public entry ─────────────────────────────────────────────────

def render_counterfactual_page(
    *,
    dataset: str = "",
    metadata: Optional[Dict[str, Any]] = None,
) -> str:
    if not dataset:
        return _landing_page()
    from ..diligence._pages import _resolve_dataset
    ds_path = _resolve_dataset(dataset)
    if ds_path is None:
        return _landing_page()
    try:
        from ..diligence import ingest_dataset
        ccd = ingest_dataset(ds_path)
    except Exception as exc:  # noqa: BLE001
        return chartis_shell(
            f'<div style="padding:{S[5]}px;color:{P["negative"]};">'
            f'Failed to ingest {html.escape(dataset)}: '
            f'{html.escape(str(exc))}</div>',
            "Counterfactual Advisor",
        )
    ccd_summary = summarize_ccd_inputs(ccd)
    cf_set = run_counterfactuals_from_ccd(ccd, metadata=metadata or {})
    lever = counterfactual_bridge_lever(cf_set)

    # JSON download URL carrying the same query string.
    download_qs: Dict[str, str] = {"dataset": dataset}
    if metadata:
        for k, v in metadata.items():
            download_qs[k] = (
                ",".join(str(x) for x in v) if isinstance(v, (list, tuple))
                else str(v)
            )
    download_url = (
        f"/api/counterfactual/{dataset}?{urlencode(download_qs)}"
    )
    body = (
        _page_style()
        + _render_hero(dataset, cf_set, lever, download_url)
        + _render_ccd_summary(ccd_summary)
        + _render_counterfactuals(cf_set)
        + _render_bridge_lever(lever)
    )
    return chartis_shell(
        body,
        f"Counterfactual Advisor — {dataset}",
        subtitle="What Would Change Your Mind",
    )
