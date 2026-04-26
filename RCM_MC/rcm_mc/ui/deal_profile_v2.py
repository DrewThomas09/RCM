"""Deal profile v2 — top-to-bottom investment narrative.

The existing ``deal_profile_page.py`` at /diligence/deal/<slug>
is a workflow tool: form for deal metadata + grid of analytic
links. Useful for an analyst running the platform, but not the
read partner wants when sitting down with a deal in front of them.

This module ships the IC-memo-style narrative read at
/deal/<deal_id>/profile, structured as 9 sections in canonical
investment-narrative order:

  1. Entity      — what is this asset, who owns it, where is it
  2. Market      — catchment demographics, growth, payer mix
  3. Comps       — comparable hospitals + relative positioning
  4. Metrics     — observed RCM performance vs benchmarks
  5. Predictions — model-derived forward estimates with intervals
  6. Bridge      — RCM → EBITDA value-creation lever decomposition
  7. Scenarios   — bull / base / bear with Monte Carlo where present
  8. Risks       — flagged red flags, conflicts, regulatory exposure
  9. Actions     — diligence questions + value-plan next steps

Each section opens with a sentence framing the numbers — partner
reads top-to-bottom and gets the deal story. Empty sections
collapse with a one-line note ('No comparable set built yet').

Public API::

    render_deal_profile_v2(store, deal_id) -> str
"""
from __future__ import annotations

import html as _html
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from .empty_states import empty_state, EmptyAction
# .colors / .loading / .nav / .responsive / .theme imports removed
# in the 2026-04-27 editorial port — chartis_shell() now provides
# the editorial chrome + responsive layout + theme cascade. The
# page-local _BG/_TEXT/_ACCENT constants below carry editorial hex
# values directly.

logger = logging.getLogger(__name__)


def _esc(s: Any) -> str:
    return _html.escape("" if s is None else str(s))


def _fmt_money(v: Optional[float]) -> str:
    if v is None:
        return "—"
    if abs(v) >= 1e9:
        return f"${v / 1e9:,.2f}B"
    if abs(v) >= 1e6:
        return f"${v / 1e6:,.1f}M"
    if abs(v) >= 1e3:
        return f"${v / 1e3:,.0f}K"
    return f"${v:,.0f}"


def _fmt_pct(v: Optional[float], digits: int = 1) -> str:
    if v is None:
        return "—"
    return f"{v * 100:+.{digits}f}%"


# Color palette — editorial port (2026-04-27): replaced dark-shell
# defaults with editorial palette values per EDITORIAL_STYLE_PORT.md
# §3 tokens. The page now passes through chartis_shell() so the
# editorial parchment background + topbar + sidebar render around
# this content; these values style the body content within.
_BG_PRIMARY = "#FFFFFF"   # was #0f172a (slate-900) → paper-pure
_BG_SURFACE = "#FFFFFF"   # was #1f2937 (gray-800) → white card
_BG_ELEVATED = "#FAF7F0"  # was #111827 (gray-900) → paper (off-white)
_BORDER = "#D6CFC0"       # was #374151 (gray-700) → editorial border
_TEXT = "#0F1C2E"         # was #f3f4f6 (gray-100) → ink (dark on light)
_TEXT_DIM = "#5C6878"     # was STATUS["neutral"] (~#94a3b8) → muted
_ACCENT = "#155752"       # was STATUS["info"] (Tailwind blue) → teal-deep
_GREEN = "#3F7D4D"        # editorial green
_AMBER = "#B7791F"        # editorial amber
_RED = "#A53A2D"          # editorial red


def _section_header(
    n: int, label: str, prose: str,
) -> str:
    return (
        f'<header style="margin:36px 0 14px 0;'
        f'padding-bottom:10px;border-bottom:1px solid '
        f'{_BORDER};">'
        f'<div style="display:flex;align-items:baseline;'
        f'gap:14px;margin-bottom:6px;">'
        f'<div style="font-size:11px;color:{_TEXT_DIM};'
        f'font-variant-numeric:tabular-nums;">'
        f'{n:02d}</div>'
        f'<h2 style="font-size:18px;color:{_TEXT};margin:0;'
        f'font-weight:600;">{_esc(label)}</h2></div>'
        f'<p style="font-size:13px;color:{_TEXT_DIM};margin:0;'
        f'max-width:720px;line-height:1.5;">{_esc(prose)}</p>'
        f'</header>')


def _empty_note(text: str) -> str:
    return (
        f'<div style="background:{_BG_ELEVATED};border:'
        f'1px solid {_BORDER};border-radius:8px;padding:'
        f'18px;color:{_TEXT_DIM};font-size:13px;'
        f'text-align:center;">{_esc(text)}</div>')


def _kv_row(key: str, value: Any) -> str:
    return (
        f'<tr><td style="padding:8px 16px;color:{_TEXT_DIM};'
        f'font-size:12px;">{_esc(key)}</td>'
        f'<td style="padding:8px 16px;color:{_TEXT};'
        f'font-variant-numeric:tabular-nums;">'
        f'{_esc(value)}</td></tr>')


def _kv_table(rows: List[tuple]) -> str:
    body = "".join(_kv_row(k, v) for k, v in rows)
    return (
        f'<table style="width:100%;border-collapse:collapse;'
        f'background:{_BG_SURFACE};border:1px solid {_BORDER};'
        f'border-radius:8px;overflow:hidden;">{body}'
        f'</table>')


# ── Section renderers ───────────────────────────────────────

def _entity_section(packet: Any) -> str:
    profile = getattr(packet, "profile", None)
    if profile is None:
        return (_section_header(
            1, "Entity",
            "No entity profile on the packet.")
            + _empty_note("Build the analysis packet."))
    name = getattr(profile, "name", None) or getattr(
        packet, "deal_name", "—")
    state = getattr(profile, "state", None) or "—"
    ccn = getattr(profile, "ccn", None) or "—"
    beds = getattr(profile, "beds", None)
    htype = getattr(profile, "hospital_type", None) or "—"
    ownership = getattr(
        profile, "ownership_type", None) or "—"
    fy = getattr(profile, "fiscal_year", None) or "—"

    rows = [
        ("Name", name),
        ("CCN", ccn),
        ("State", state),
        ("Hospital type", htype),
        ("Ownership", ownership),
        ("Beds", f"{beds:,}" if beds else "—"),
        ("Fiscal year", fy),
    ]
    prose = (
        f"{name} — a {htype.lower() if isinstance(htype, str) else 'hospital'} "
        f"in {state}{f' with {beds:,} beds' if beds else ''}. "
        f"This profile pulls from HCRIS + Hospital Compare; "
        f"every downstream metric attributes through to a "
        f"specific source.")
    return _section_header(1, "Entity", prose) + _kv_table(rows)


def _market_section(packet: Any) -> str:
    """Pull market context from packet.market or fall back to
    profile-level state info."""
    market = getattr(packet, "market_context", None)
    if not market:
        market = getattr(packet, "market", None)
    if not market:
        prose = (
            "No market context loaded — partner can run the "
            "Census + CDC PLACES + APCD ingestion to populate "
            "catchment demographics.")
        return _section_header(2, "Market", prose) + (
            _empty_note(
                "Run the market-context loader to populate "
                "catchment demographics."))

    if isinstance(market, dict):
        cbsa = market.get("cbsa") or "—"
        pop = market.get("population")
        growth = market.get("population_growth_5yr")
        income = market.get("median_household_income")
        uninsured = market.get("pct_uninsured")
        score = market.get("attractiveness_score")
    else:
        cbsa = getattr(market, "cbsa", "—")
        pop = getattr(market, "population", None)
        growth = getattr(
            market, "population_growth_5yr", None)
        income = getattr(
            market, "median_household_income", None)
        uninsured = getattr(market, "pct_uninsured", None)
        score = getattr(
            market, "attractiveness_score", None)

    rows = [
        ("CBSA", cbsa),
        ("Population", f"{pop:,}" if pop else "—"),
        ("5y growth",
         _fmt_pct(growth) if growth is not None else "—"),
        ("Median income",
         _fmt_money(income) if income else "—"),
        ("Uninsured rate",
         f"{uninsured * 100:.1f}%" if uninsured else "—"),
        ("Attractiveness score",
         f"{score:.2f} / 1.00" if score else "—"),
    ]
    score_read = ""
    if score is not None:
        if score >= 0.70:
            score_read = (
                f"{cbsa} scores {score:.2f} on the composite "
                f"attractiveness index — top-tier market for "
                f"healthcare PE.")
        elif score >= 0.50:
            score_read = (
                f"{cbsa} scores {score:.2f} — mid-tier market; "
                f"check growth and uninsured rate before "
                f"sizing.")
        else:
            score_read = (
                f"{cbsa} scores {score:.2f} — soft market; "
                f"the thesis needs a specific reason to be "
                f"there.")
    prose = (
        score_read or
        f"{cbsa} catchment demographics — population, age, "
        f"income, insurance coverage. The attractiveness "
        f"score weights growth (+30%), 65+ share (+20%), "
        f"income (+15%), inverse-uninsured (+15%), log-pop "
        f"(+10%), inverse-poverty (+10%).")
    return _section_header(2, "Market", prose) + _kv_table(rows)


def _comps_section(packet: Any) -> str:
    comps = getattr(packet, "comparables", None)
    members = getattr(comps, "members", []) if comps else []
    if not members:
        return _section_header(
            3, "Comparables",
            "No comparable set built yet."
        ) + _empty_note(
            "Build comparables via "
            "rcm_mc.ml.comparable_finder.")

    n = len(members)
    rows = []
    for c in members[:8]:
        ccn = getattr(c, "ccn", "—")
        name = getattr(c, "name", "—")
        sim = getattr(c, "similarity_score", None)
        beds = getattr(c, "beds", None)
        rows.append(
            f'<tr style="border-bottom:1px solid {_BORDER};">'
            f'<td style="padding:10px 16px;color:{_TEXT};">'
            f'{_esc(name)}</td>'
            f'<td style="padding:10px 16px;color:{_TEXT_DIM};'
            f'font-size:12px;">{_esc(ccn)}</td>'
            f'<td style="padding:10px 16px;text-align:right;'
            f'color:{_TEXT_DIM};font-variant-numeric:'
            f'tabular-nums;">'
            f'{f"{beds:,}" if beds else "—"}</td>'
            f'<td style="padding:10px 16px;text-align:right;'
            f'color:{_TEXT};font-variant-numeric:'
            f'tabular-nums;font-weight:500;">'
            f'{f"{sim:.2f}" if sim is not None else "—"}</td>'
            f'</tr>')
    prose = (
        f"{n} comparable hospitals selected by numeric-profile "
        f"distance. Similarity ranges 0-1; ≥0.85 indicates a "
        f"true peer. The top of the list anchors every "
        f"benchmark calculation downstream.")
    table = (
        f'<div style="background:{_BG_SURFACE};border:1px solid '
        f'{_BORDER};border-radius:8px;overflow:hidden;">'
        f'<table style="width:100%;border-collapse:collapse;">'
        f'<thead><tr style="background:{_BG_ELEVATED};">'
        f'<th style="padding:10px 16px;text-align:left;'
        f'font-size:11px;text-transform:uppercase;'
        f'letter-spacing:0.05em;color:{_TEXT_DIM};">'
        f'Hospital</th>'
        f'<th style="padding:10px 16px;text-align:left;'
        f'font-size:11px;text-transform:uppercase;'
        f'letter-spacing:0.05em;color:{_TEXT_DIM};">CCN</th>'
        f'<th style="padding:10px 16px;text-align:right;'
        f'font-size:11px;text-transform:uppercase;'
        f'letter-spacing:0.05em;color:{_TEXT_DIM};">Beds</th>'
        f'<th style="padding:10px 16px;text-align:right;'
        f'font-size:11px;text-transform:uppercase;'
        f'letter-spacing:0.05em;color:{_TEXT_DIM};">'
        f'Similarity</th>'
        f'</tr></thead><tbody>{"".join(rows)}</tbody></table></div>')
    return _section_header(3, "Comparables", prose) + table


def _metrics_section(packet: Any) -> str:
    metrics = getattr(packet, "observed_metrics", {})
    if not metrics:
        return _section_header(
            4, "Observed metrics",
            "No observed RCM metrics — needs HCRIS + claim "
            "data refresh."
        ) + _empty_note("No metric data on packet.")

    rows = []
    for key, m in list(metrics.items())[:10]:
        val = getattr(m, "value", None)
        unit = getattr(m, "unit", "")
        rows.append(_kv_row(
            _esc(key.replace("_", " ").title()),
            f"{val} {unit}".strip() if val is not None else "—"))
    prose = (
        f"{len(metrics)} observed RCM metrics from the data "
        f"layer. Where partner-supplied numbers are missing, "
        f"the predictor fills the gap (next section); the "
        f"completeness panel flags both low-confidence and "
        f"stale fields.")
    return _section_header(4, "Observed metrics", prose) + (
        f'<table style="width:100%;border-collapse:collapse;'
        f'background:{_BG_SURFACE};border:1px solid {_BORDER};'
        f'border-radius:8px;overflow:hidden;">'
        f'{"".join(rows)}</table>')


def _predictions_section(packet: Any) -> str:
    preds = getattr(packet, "predicted_metrics", {})
    if not preds:
        return _section_header(
            5, "Predictions",
            "No model predictions yet — partner can run the "
            "trained predictors against the public-data feature "
            "set."
        ) + _empty_note(
            "Predictor outputs not on packet.")

    rows = []
    for key, p in list(preds.items())[:10]:
        val = getattr(p, "value", None)
        ci_lo = getattr(p, "ci_low", None) or getattr(
            p, "ci_lo", None)
        ci_hi = getattr(p, "ci_high", None) or getattr(
            p, "ci_hi", None)
        method = getattr(p, "method", None) or "—"
        ci_text = ""
        if ci_lo is not None and ci_hi is not None:
            ci_text = f" ({ci_lo:.3f}–{ci_hi:.3f})"
        rows.append(_kv_row(
            _esc(key.replace("_", " ").title()),
            (f"{val:.3f}{ci_text} · {method}"
             if val is not None else "—")))
    prose = (
        f"{len(preds)} model-derived forward estimates. Each "
        f"prediction carries a 90% interval calibrated "
        f"against held-out hospitals — the /models/quality "
        f"dashboard shows actual coverage.")
    return _section_header(5, "Predictions", prose) + (
        f'<table style="width:100%;border-collapse:collapse;'
        f'background:{_BG_SURFACE};border:1px solid {_BORDER};'
        f'border-radius:8px;overflow:hidden;">'
        f'{"".join(rows)}</table>')


def _bridge_section(packet: Any) -> str:
    bridge = getattr(packet, "ebitda_bridge", None)
    if bridge is None:
        return _section_header(
            6, "EBITDA bridge",
            "No bridge built yet — needs RCM metrics + the "
            "research-band coefficients."
        ) + _empty_note("EBITDA bridge not populated.")

    current = getattr(bridge, "current_ebitda", 0)
    target = getattr(bridge, "target_ebitda", 0)
    total = getattr(bridge, "total_ebitda_impact", 0)
    impacts = getattr(bridge, "per_metric_impacts", [])
    if not impacts:
        return _section_header(
            6, "EBITDA bridge",
            "Bridge has no lever impacts."
        ) + _empty_note("No lever impacts.")

    rows = []
    for imp in impacts:
        metric = getattr(imp, "metric_key", "—")
        eb = getattr(imp, "ebitda_impact", 0)
        sign_color = _GREEN if eb >= 0 else _RED
        rows.append(
            f'<tr style="border-bottom:1px solid {_BORDER};">'
            f'<td style="padding:10px 16px;color:{_TEXT};">'
            f'{_esc(metric.replace("_", " ").title())}</td>'
            f'<td style="padding:10px 16px;text-align:right;'
            f'color:{sign_color};font-variant-numeric:'
            f'tabular-nums;font-weight:500;">'
            f'{_fmt_money(eb)}</td></tr>')
    prose = (
        f"Current EBITDA {_fmt_money(current)} → target "
        f"{_fmt_money(target)} via {len(impacts)} RCM levers. "
        f"Total recurring uplift: {_fmt_money(total)} "
        f"({_fmt_pct(total / current if current else None)})."
    )
    table = (
        f'<div style="background:{_BG_SURFACE};border:1px solid '
        f'{_BORDER};border-radius:8px;overflow:hidden;">'
        f'<table style="width:100%;border-collapse:collapse;">'
        f'<thead><tr style="background:{_BG_ELEVATED};">'
        f'<th style="padding:10px 16px;text-align:left;'
        f'font-size:11px;text-transform:uppercase;'
        f'letter-spacing:0.05em;color:{_TEXT_DIM};">Lever</th>'
        f'<th style="padding:10px 16px;text-align:right;'
        f'font-size:11px;text-transform:uppercase;'
        f'letter-spacing:0.05em;color:{_TEXT_DIM};">'
        f'EBITDA $</th>'
        f'</tr></thead><tbody>{"".join(rows)}</tbody></table></div>')
    return _section_header(6, "EBITDA bridge", prose) + table


def _scenarios_section(packet: Any) -> str:
    sim = getattr(packet, "simulation", None)
    sim_v2 = getattr(packet, "v2_simulation", None)
    has_sim = sim is not None or sim_v2 is not None
    if not has_sim:
        return _section_header(
            7, "Scenarios",
            "No Monte Carlo simulation run yet — bull/base/"
            "bear scenarios populate after the simulator runs."
        ) + _empty_note("No simulation outputs.")

    rows: List[tuple] = []
    if sim is not None:
        for attr in [
            "p10_ebitda", "p50_ebitda", "p90_ebitda",
            "expected_ebitda", "n_sims",
        ]:
            v = getattr(sim, attr, None)
            if v is None:
                continue
            label = attr.replace("_", " ").title()
            if "ebitda" in attr:
                rows.append((label, _fmt_money(v)))
            else:
                rows.append((label, f"{int(v):,}"))
    if not rows and isinstance(sim_v2, dict):
        for k in ("p10", "p50", "p90", "n_sims"):
            v = sim_v2.get(k)
            if v is None:
                continue
            rows.append((
                k.upper(),
                _fmt_money(v) if k != "n_sims"
                else f"{int(v):,}"))
    prose = (
        "Monte Carlo distribution across the value-creation "
        "levers. P10 = bear case (something goes wrong on "
        "multiple levers), P90 = bull case (things break right). "
        "The spread between them is the deal's risk envelope.")
    return _section_header(7, "Scenarios", prose) + (
        _kv_table(rows) if rows
        else _empty_note("Simulation populated but no headline "
                         "stats."))


def _risks_section(packet: Any) -> str:
    flags = getattr(packet, "risk_flags", [])
    if not flags:
        return _section_header(
            8, "Risks",
            "No risk flags raised — surfacing nothing is "
            "uncommon; double-check that the risk_flags pass "
            "ran."
        ) + _empty_note("No risks flagged.")

    sev_color = {
        "critical": _RED, "high": _RED,
        "medium": _AMBER, "low": _TEXT_DIM,
    }
    rows = []
    n_high = 0
    for f in flags:
        sev = str(getattr(f, "severity", "low")).lower()
        if sev in ("critical", "high"):
            n_high += 1
        color = sev_color.get(sev, _TEXT_DIM)
        msg = getattr(f, "message", "") or getattr(
            f, "title", "")
        rows.append(
            f'<div style="padding:14px 18px;border-bottom:'
            f'1px solid {_BORDER};display:flex;align-items:'
            f'center;gap:14px;">'
            f'<span style="display:inline-block;width:8px;'
            f'height:8px;border-radius:50%;background:'
            f'{color};flex-shrink:0;"></span>'
            f'<div style="flex:1;color:{_TEXT};font-size:13px;">'
            f'{_esc(msg)}</div>'
            f'<span style="font-size:11px;color:{color};'
            f'text-transform:uppercase;letter-spacing:0.05em;'
            f'font-weight:600;">{_esc(sev)}</span></div>')
    prose = (
        f"{len(flags)} risk flag"
        f"{'s' if len(flags) != 1 else ''}"
        + (f", {n_high} high-severity" if n_high
           else "")
        + ". Items left unaddressed in diligence become "
          "post-close surprises — every flag should map to a "
          "decision in the next section.")
    return _section_header(8, "Risks", prose) + (
        f'<div style="background:{_BG_SURFACE};border:'
        f'1px solid {_BORDER};border-radius:8px;overflow:'
        f'hidden;">{"".join(rows)}</div>')


def _actions_section(packet: Any) -> str:
    questions = getattr(packet, "diligence_questions", [])
    if not questions:
        return _section_header(
            9, "Actions",
            "No diligence questions queued — typically one "
            "per risk flag, but the auto-generation pass may "
            "not have run."
        ) + _empty_note("No actions queued.")

    pri_color = {
        "critical": _RED, "high": _AMBER,
        "medium": _ACCENT, "low": _TEXT_DIM,
    }
    rows = []
    for q in questions[:12]:
        pri = str(
            getattr(q, "priority", "medium")).lower()
        color = pri_color.get(pri, _TEXT_DIM)
        text = getattr(q, "question", "") or getattr(
            q, "text", "")
        rows.append(
            f'<div style="padding:14px 18px;border-bottom:'
            f'1px solid {_BORDER};display:flex;align-items:'
            f'baseline;gap:14px;">'
            f'<span style="font-size:11px;color:{color};'
            f'text-transform:uppercase;letter-spacing:0.05em;'
            f'font-weight:600;width:60px;flex-shrink:0;">'
            f'{_esc(pri)}</span>'
            f'<div style="flex:1;color:{_TEXT};font-size:13px;'
            f'line-height:1.5;">{_esc(text)}</div></div>')
    prose = (
        f"{len(questions)} diligence question"
        f"{'s' if len(questions) != 1 else ''} drafted from "
        f"the risk flags + completeness gaps + comp-set "
        f"variances. Each maps to a decision the partner "
        f"needs to make before closing.")
    return _section_header(9, "Actions", prose) + (
        f'<div style="background:{_BG_SURFACE};border:1px '
        f'solid {_BORDER};border-radius:8px;overflow:'
        f'hidden;">{"".join(rows)}</div>')


# ── Main render ─────────────────────────────────────────────

def _load_packet(store: Any, deal_id: str) -> Optional[Any]:
    """Load the latest packet for the deal, if one exists."""
    try:
        from ..analysis.analysis_store import (
            list_packets, load_packet_by_id,
        )
        rows = list_packets(store, deal_id) or []
        if not rows:
            return None
        return load_packet_by_id(store, rows[0]["id"])
    except Exception as exc:  # noqa: BLE001
        logger.debug(
            "packet load failed for %s: %s", deal_id, exc)
        return None


def render_deal_profile_v2(
    store: Any, deal_id: str,
) -> str:
    """Render the top-to-bottom narrative deal profile."""
    packet = _load_packet(store, deal_id)
    deal_name = (
        getattr(packet, "deal_name", deal_id)
        if packet else deal_id) or deal_id

    if packet is None:
        body = empty_state(
            f"No analysis packet found for {deal_id}",
            (f"Run `rcm-mc analysis {deal_id}` to build a "
             f"packet — every section on this page (entity, "
             f"market, comps, predictions, EBITDA bridge) "
             f"depends on it."),
            icon="◳",
            actions=[
                EmptyAction(
                    "View deal list", "/?v3=1"),
            ])
    else:
        body = (
            _entity_section(packet)
            + _market_section(packet)
            + _comps_section(packet)
            + _metrics_section(packet)
            + _predictions_section(packet)
            + _bridge_section(packet)
            + _scenarios_section(packet)
            + _risks_section(packet)
            + _actions_section(packet))

    # Editorial port (2026-04-27): drop the page's own <!doctype> +
    # theme_init_script() + theme_stylesheet() + theme_toggle() + body
    # tags. chartis_shell() now wraps the editorial chrome (parchment
    # topbar + breadcrumbs + PHI banner) and the editorial CSS via
    # /static/v3/chartis.css provides the body type/spacing.
    page_body = (
        f'<div style="max-width:1100px;margin:0 auto;'
        f'padding:1.5rem 1rem;">'
        f'<div style="display:flex;justify-content:'
        f'space-between;align-items:baseline;'
        f'margin-bottom:.5rem;">'
        f'<h1 style="font-size:1.5rem;color:{_TEXT};margin:0;'
        f'font-family:\'Source Serif 4\',Georgia,serif;font-weight:400;">'
        f'{_esc(deal_name)}</h1>'
        f'<div style="display:flex;gap:14px;font-size:12px;">'
        f'<a href="/deal/{_esc(deal_id)}?ui=v3" '
        f'style="color:{_ACCENT};">Detail →</a>'
        f'</div></div>'
        f'<p style="color:{_TEXT_DIM};font-size:13px;'
        f'margin:0 0 1rem 0;">Top-to-bottom investment '
        f'narrative — read sequentially.</p>'
        f'{body}'
        f'</div>'
    )

    from ._chartis_kit import chartis_shell
    return chartis_shell(
        page_body,
        title=f"Deal · {deal_name}",
        active_nav="DEALS",
        breadcrumbs=[
            ("Home", "/app"),
            ("Deals", "/deals"),
            (deal_name, None),
        ],
    )
