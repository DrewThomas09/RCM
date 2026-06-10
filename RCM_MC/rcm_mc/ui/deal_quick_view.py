"""PE Desk Deal Quick View — fallback when full analysis unavailable.

Shows deal profile data with direct links to all available models.
Used when a deal is freshly created and hasn't been through the full
analysis pipeline yet.
"""
from __future__ import annotations

import html
from typing import Any, Dict, Optional

from ._chartis_kit import (
    chartis_shell, ck_basis_badge, ck_fmt_currency, ck_fmt_num, ck_kpi_block,
    ck_next_section, ck_peer_percentile, ck_provenance_tooltip,
)

# Which direction is good, per profile metric — drives the percentile-chip
# tone. Metrics not listed render the chip in neutral ink.
_HIGHER_IS_BETTER = {
    "denial_rate": False, "days_in_ar": False, "cost_to_collect": False,
    "net_collection_rate": True, "clean_claim_rate": True,
}

# Percent-point profile metrics with their realistic range (per the metric
# glossary). Used for a soft unit-mistake check: a partner entering the
# FRACTION (0.945) instead of percent points (94.5) — or swapping a rate into
# the wrong field — produces an implausible display like "0.9%" net
# collection. We show what was entered, but flag it for review.
_PCT_SANITY = {
    "Net Collection": (80.0, 100.0),    # glossary: typically 92–99%
    "Clean Claim Rate": (60.0, 100.0),  # typically 75–98%
    "Denial Rate": (0.0, 40.0),         # initial denials rarely exceed ~25%
    "Cost to Collect": (0.0, 15.0),     # typically 2–5% of NPR
}
from .brand import PALETTE


def render_deal_quick_view(
    deal_id: str,
    profile: Dict[str, Any],
    error_msg: str = "",
    peer_deals: Any = None,
) -> str:
    """Render a deal overview with links to all models."""
    name = html.escape(str(profile.get("name", deal_id)))
    did = html.escape(deal_id)

    # Error banner if workbench failed
    error_html = ""
    if error_msg:
        error_html = (
            f'<div class="cad-card" style="border-left:3px solid {PALETTE["warning"]};">'
            f'<p style="color:{PALETTE["warning"]};font-size:12.5px;">'
            f'Full analysis workbench unavailable: {html.escape(error_msg[:200])}</p>'
            f'<p style="color:{PALETTE["text_muted"]};font-size:12px;margin-top:4px;">'
            f'The individual models below still work. Run a full analysis to unlock the workbench.</p>'
            f'</div>'
        )

    # Flatten nested observed_metrics ({metric: {"value": …}}) into the flat
    # keys this view reads — packet-seeded deals store them nested, and the
    # view used to show "No profile metrics yet" while the data sat right
    # there (same shape issue fixed in store.list_deals()).
    om = profile.get("observed_metrics") or {}
    if isinstance(om, dict):
        profile = dict(profile)
        for _k, _entry in om.items():
            if _k in profile:
                continue
            if isinstance(_entry, dict) and "value" in _entry:
                profile[_k] = _entry["value"]
            elif isinstance(_entry, (int, float)):
                profile[_k] = _entry

    # Profile KPIs
    kpi_fields = [
        ("Denial Rate", profile.get("denial_rate"), "%", None, "denial_rate"),
        ("Days in AR", profile.get("days_in_ar"), "", None, "days_in_ar"),
        ("Net Collection", profile.get("net_collection_rate"), "%", None, "net_collection_rate"),
        ("Clean Claim Rate", profile.get("clean_claim_rate"), "%", None, "clean_claim_rate"),
        ("Cost to Collect", profile.get("cost_to_collect"), "%", None, "cost_to_collect"),
        ("Net Revenue", profile.get("net_revenue"), "$M", 1e6, None),
        ("Bed Count", profile.get("bed_count"), "", None, None),
        ("Claims Volume", profile.get("claims_volume"), "", None, None),
    ]

    def _peer_chip(metric_key: Optional[str], val: Any) -> str:
        # P4 slice 1: percentile vs the OTHER deals in the book. Excludes
        # this deal itself so the rank reads "vs peers", not "vs self+peers".
        # A chip must never 500 the page — any malformed frame is just no chip.
        if peer_deals is None or metric_key is None or val is None:
            return ""
        try:
            df = peer_deals
            if metric_key not in df.columns or "deal_id" not in df.columns:
                return ""
            others = df[df["deal_id"].astype(str) != str(deal_id)][metric_key]
            chip = ck_peer_percentile(
                val, list(others), peer_label="portfolio deals",
                higher_is_better=_HIGHER_IS_BETTER.get(metric_key))
            return f'<div style="margin-top:3px;">{chip}</div>' if chip else ""
        except Exception:  # noqa: BLE001
            return ""

    kpi_cards = ""
    populated = 0
    for label, val, suffix, scale, metric_key in kpi_fields:
        if val is not None:
            populated += 1
            verify_flag = ""
            try:
                v = float(val)
                if scale:
                    # House style: roll up to $B at ≥$1B so a >$1B anchor deal
                    # reads "$1.19B" not "$1,194M". ck_fmt_currency takes raw
                    # dollars; net_revenue is stored in dollars (scale=1e6 was
                    # only the legacy M-divisor).
                    display = ck_fmt_currency(v)
                elif suffix == "%":
                    display = f"{v:.1f}%"
                    lo, hi = _PCT_SANITY.get(label, (None, None))
                    if lo is not None and not (lo <= v <= hi):
                        verify_flag = (
                            '<span style="color:var(--sc-warning,#b8732a);'
                            'cursor:help;margin-left:4px;" title="Outside the '
                            f'typical {lo:g}–{hi:g}% range for this metric — '
                            'check the entry (percent points expected, e.g. '
                            '94.5, not 0.945).">⚠</span>'
                        )
                else:
                    display = f"{v:,.0f}"
            except (TypeError, ValueError):
                display = str(val)

            kpi_cards += ck_kpi_block(
                label,
                html.escape(display) + verify_flag + _peer_chip(metric_key, val))

    # Workstream H — composite-demo anchor: when the deal names a REAL
    # facility anchor, show its filed financials (ACTUAL, sourced) and say
    # plainly that the RCM metrics below are illustrative demo values.
    anchor = profile.get("facility_anchor") or {}
    anchor_html = ""
    if anchor.get("ccn"):
        _m = anchor.get("operating_margin")
        _npr = anchor.get("net_patient_revenue")
        _beds = anchor.get("beds")
        anchor_html = (
            f'<div class="cad-card" style="margin:0 0 10px;">'
            f'<p class="ck-section-body" style="margin:0;font-size:12px;">'
            f'Composite demo deal — financial anchor is the real filing of '
            f'<strong>{html.escape(str(anchor.get("name", "")))}</strong> '
            f'(CCN <a href="/diligence/hcris-xray?ccn={html.escape(str(anchor["ccn"]))}" '
            f'style="color:{PALETTE["text_link"]};">{html.escape(str(anchor["ccn"]))}</a>, '
            f'{html.escape(str(anchor.get("state", "")))})'
            f'{ck_basis_badge("actual")}: '
            f'{f"{ck_fmt_currency(_npr)} NPR" if _npr else ""}'
            f'{f" · {int(_beds)} beds" if _beds else ""}'
            f'{f" · {_m*100:+.1f}% operating margin" if _m is not None else ""}'
            f' — FY{anchor.get("fiscal_year", "")} '
            f'{html.escape(str(anchor.get("source", "")))}. '
            f'The RCM metrics below are <strong>illustrative demo values</strong> '
            f'(HCRIS files no denial/collection fields).</p></div>')

    profile_section = (
        anchor_html +
        # Basis disclosure: these are the deal's SELF-REPORTED RCM metrics
        # (partner-entered via /import), not a public filing or a model.
        f'<p class="ck-section-body" style="margin:0 0 8px;font-size:11px;'
        f'color:var(--sc-text-dim,#6a7480);">Deal profile metrics'
        f'{ck_basis_badge("entered")} — '
        f'<a href="/import" style="color:{PALETTE["text_link"]};">edit via Import</a> · '
        f'<a href="/deal-context?set={html.escape(deal_id)}&return=/deal/{html.escape(deal_id)}" '
        f'style="color:{PALETTE["text_link"]};" title="Carry this deal as ambient '
        f'context: every module link in the bar opens pre-scoped to it.">'
        f'set as active deal</a>.</p>'
        f'<div class="ck-kpi-grid">{kpi_cards}</div>'
        if kpi_cards else
        anchor_html +
        f'<div class="cad-card"><p style="color:{PALETTE["text_muted"]};">'
        f'No profile metrics yet. '
        f'<a href="/import" style="color:{PALETTE["text_link"]};">Edit deal profile</a>.</p></div>'
    )

    # Completeness
    total_fields = 8
    pct = populated / total_fields * 100
    bar_color = PALETTE["positive"] if pct > 70 else (PALETTE["warning"] if pct > 40 else PALETTE["negative"])
    # Cycle 55 — provenance on the completeness summary.
    completeness_value = ck_provenance_tooltip(
        "Data completeness",
        f'<span style="color:{bar_color};">{populated}/{total_fields} fields</span>',
        explainer=(
            f"Profile fields populated out of {total_fields} the "
            f"platform expects. Above 70% green (analyses run on "
            f"observed data), 40-70% amber (some imputation), "
            f"below 40% red (Bayesian priors dominate predictions)."
        ),
    )
    completeness = (
        f'<div class="cad-card">'
        f'<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">'
        f'<h2>Data Completeness</h2>'
        f'<span class="cad-mono">{completeness_value}</span>'
        f'</div>'
        f'<div style="background:{PALETTE["bg_tertiary"]};border-radius:6px;height:10px;">'
        f'<div style="width:{pct:.0f}%;background:{bar_color};border-radius:6px;height:10px;"></div>'
        f'</div></div>'
    )

    # Action cards — these are the money section
    models_section = (
        f'<div class="cad-card"><h2>Available Models & Analysis</h2>'
        f'<p style="color:{PALETTE["text_secondary"]};font-size:12.5px;margin-bottom:16px;">'
        f'Click any model to run it instantly on this deal\'s profile data.</p></div>'

        f'<div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:12px;">'

        f'<a href="/models/dcf/{did}" class="cad-card" style="text-decoration:none;color:inherit;">'
        f'<h3 style="color:{PALETTE["brand_accent"]};">DCF Valuation</h3>'
        f'<div style="font-size:12px;color:{PALETTE["text_secondary"]};">'
        f'5-year cash flow projection with WACC sensitivity matrix</div></a>'

        f'<a href="/models/lbo/{did}" class="cad-card" style="text-decoration:none;color:inherit;">'
        f'<h3 style="color:{PALETTE["brand_accent"]};">LBO Model</h3>'
        f'<div style="font-size:12px;color:{PALETTE["text_secondary"]};">'
        f'Sources & uses, debt schedule, IRR/MOIC returns</div></a>'

        f'<a href="/models/financials/{did}" class="cad-card" style="text-decoration:none;color:inherit;">'
        f'<h3 style="color:{PALETTE["brand_accent"]};">3-Statement</h3>'
        f'<div style="font-size:12px;color:{PALETTE["text_secondary"]};">'
        f'IS + BS + CF reconstructed from HCRIS + profile</div></a>'

        f'<a href="/models/market/{did}" class="cad-card" style="text-decoration:none;color:inherit;">'
        f'<h3 style="color:{PALETTE["positive"]};">Market Analysis</h3>'
        f'<div style="font-size:12px;color:{PALETTE["text_secondary"]};">'
        f'HHI, competitors, Mauboussin moat assessment</div></a>'

        f'<a href="/models/denial/{did}" class="cad-card" style="text-decoration:none;color:inherit;">'
        f'<h3 style="color:{PALETTE["warning"]};">Denial Drivers</h3>'
        f'<div style="font-size:12px;color:{PALETTE["text_secondary"]};">'
        f'Root cause decomposition with dollar impacts</div></a>'

        f'<a href="/pressure?deal_id={did}" class="cad-card" style="text-decoration:none;color:inherit;">'
        f'<h3 style="color:{PALETTE["negative"]};">Pressure Test</h3>'
        f'<div style="font-size:12px;color:{PALETTE["text_secondary"]};">'
        f'Stress scenarios with risk flags</div></a>'

        f'</div>'
    )

    # Export & API links
    export_section = (
        f'<div class="cad-card">'
        f'<h2>Export & Download</h2>'
        f'<div style="display:flex;gap:8px;flex-wrap:wrap;">'
        f'<a href="/api/deals/{did}/dcf" class="cad-btn" style="text-decoration:none;">'
        f'DCF JSON</a>'
        f'<a href="/api/deals/{did}/lbo" class="cad-btn" style="text-decoration:none;">'
        f'LBO JSON</a>'
        f'<a href="/api/deals/{did}/financials" class="cad-btn" style="text-decoration:none;">'
        f'Financials JSON</a>'
        f'<a href="/models/market/{did}" class="cad-btn" style="text-decoration:none;">'
        f'Market JSON</a>'
        f'<a href="/models/denial/{did}" class="cad-btn" style="text-decoration:none;">'
        f'Denial Drivers JSON</a>'
        f'<a href="/api/deals/{did}/memo" class="cad-btn" style="text-decoration:none;">'
        f'IC Memo</a>'
        f'<a href="/api/deals/{did}/validate" class="cad-btn" style="text-decoration:none;">'
        f'Validate</a>'
        f'<a href="/api/deals/{did}/completeness" class="cad-btn" style="text-decoration:none;">'
        f'Completeness</a>'
        f'</div></div>'
    )

    next_up = ck_next_section(
        "Open the full deal profile",
        f"/deal/{did}",
        eyebrow="Up next",
        italic_word="profile",
    )
    body = f'{error_html}{profile_section}{completeness}{models_section}{export_section}{next_up}'

    return chartis_shell(
        body, name,
        active_nav="/analysis",
        subtitle=f"Deal: {did} — {populated} of {total_fields} profile fields populated",
        editorial_intro={
            "eyebrow": "DEAL QUICK VIEW",
            "headline": "Where the deal's profile lives in one glance.",
            "italic_word": "one",
            "body": (
                "Compact profile view for fast triage - sector, "
                "size, headline economics, completeness grade. "
                "Use this from the pipeline screen before "
                "committing to a full analysis run."
            ),
        },
    )
