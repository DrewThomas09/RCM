"""PE Desk Deal Dashboard — unified single-deal view.

Shows all available information and models for a deal in one page
with clear navigation to every model output.
"""
from __future__ import annotations

import html
from typing import Any, Dict, List, Optional, Tuple

from ._chartis_kit import (
    chartis_shell, ck_eyebrow, ck_fmt_currency, ck_fmt_num,
    ck_fmt_pct, ck_kpi_block, ck_next_section, ck_page_explainer,
    ck_page_title, ck_provenance_tooltip, ck_value_anchor,
)
from .brand import PALETTE


# Tile category palette — Phase: \"editorial refresh\" replaces the
# six-color-and-no-legend approach with four semantic categories.
# Each tile is assigned to one of these; the panel headers spell out
# the meaning, so the color is read as a category code, not random.
_CATEGORY_COLORS = {
    "valuation":   PALETTE["brand_accent"],   # teal — DCF / LBO / waterfall
    "operations":  PALETTE["positive"],       # green — financials / market / service
    "risk":        PALETTE["warning"],        # bronze — denial / pressure / anomaly / stress
    "synthesis":   PALETTE["text_link"],      # navy — partner review / IC / archetype
}


def _model_tile(
    code: str,
    href: str,
    title: str,
    desc: str,
    *,
    category: str = "synthesis",
    inline_value: str = "",
    inline_color: str = "",
) -> str:
    """Render one model tile for the deal dashboard grid.

    ``category`` is one of valuation / operations / risk / synthesis;
    drives the left-border accent color via _CATEGORY_COLORS so the
    tiles read as a typed catalog instead of a rainbow.
    """
    accent = _CATEGORY_COLORS.get(category, PALETTE["brand_accent"])
    inline = ""
    if inline_value:
        c = inline_color or accent
        inline = (
            f'<span class="cad-mono" style="color:{c};font-size:11.5px;'
            f'font-weight:600;letter-spacing:0.02em;">{html.escape(inline_value)}</span>'
        )
    return (
        f'<a href="{href}" class="cad-modeltile" style="--tile-accent:{accent};">'
        f'<div class="cad-modeltile-head">'
        f'<span class="cad-section-code" style="color:{accent};">{html.escape(code)}</span>'
        f'{inline}'
        f'</div>'
        f'<div class="cad-modeltile-title">{html.escape(title)}</div>'
        f'<div class="cad-modeltile-desc">{html.escape(desc)}</div>'
        f'</a>'
    )


_MODEL_TILE_CSS = f"""
/* Tile grid — 4 columns at desktop, collapses gracefully via
 * auto-fit + a min cell width. Earlier version used 240px min
 * which produced 7-8 columns and felt Bloomberg-terminal dense;
 * 280px gives ~4-5 columns at 1440px, ~3 on a 13\" laptop. */
.cad-modelgrid {{
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 0;
  border-top: 1px solid {PALETTE['border']};
  border-left: 1px solid {PALETTE['border']};
  margin-bottom: 12px;
}}
.cad-modeltile {{
  display: block;
  padding: 14px 16px 16px;
  background: {PALETTE['bg_secondary']};
  border-right: 1px solid {PALETTE['border']};
  border-bottom: 1px solid {PALETTE['border']};
  border-left: 3px solid var(--tile-accent, {PALETTE['brand_accent']});
  margin-left: -1px;
  text-decoration: none;
  color: inherit;
  transition: background 0.1s;
}}
.cad-modeltile:hover {{
  background: {PALETTE['bg_tertiary']};
}}
.cad-modeltile-head {{
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
  min-height: 16px;
}}
/* Tile title — editorial-refresh swap: Source Serif, navy,
 * title case (not Bloomberg uppercase 12.5px bold). Sits as
 * the H3 equivalent of the tile. */
.cad-modeltile-title {{
  font-family: var(--sc-serif, 'Source Serif 4', Georgia, serif);
  font-size: 16px;
  font-weight: 500;
  color: {PALETTE['text_primary']};
  letter-spacing: -0.005em;
  line-height: 1.25;
  margin-bottom: 4px;
}}
.cad-modeltile-desc {{
  font-size: 11.5px;
  color: {PALETTE['text_muted']};
  font-family: var(--sc-sans, Inter, sans-serif);
  letter-spacing: 0.0em;
  line-height: 1.5;
}}
.cad-modeltile:hover .cad-modeltile-title {{
  color: var(--tile-accent, {PALETTE['brand_accent']});
}}
/* Category section header above each tile group. Stays out of the
 * grid (it's a sibling above), so the grid layout doesn't get
 * fragmented. */
.cad-modelgroup-head {{
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  margin: 22px 0 10px;
}}
.cad-modelgroup-head h3 {{
  font-family: var(--sc-serif, 'Source Serif 4', Georgia, serif);
  font-weight: 500;
  font-size: 18px;
  color: {PALETTE['text_primary']};
  margin: 0;
}}
.cad-modelgroup-head .cad-modelgroup-count {{
  font-family: var(--sc-mono, 'JetBrains Mono', monospace);
  font-size: 10px;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: {PALETTE['text_muted']};
}}
.cad-modelgroup-head .cad-modelgroup-dot {{
  display: inline-block;
  width: 9px;
  height: 9px;
  border-radius: 50%;
  margin-right: 6px;
  vertical-align: middle;
}}
""".replace("{font_mono}", "'JetBrains Mono', 'SF Mono', monospace")


def _exports_registry(exports: "list | None") -> str:
    """P5 exhibit registry — the deal's previously generated artifacts
    from the ``generated_exports`` audit table. Read-only; empty → ""."""
    if not exports:
        return ""
    rows = ""
    for e in exports[:10]:
        size = e.get("file_size_bytes")
        size_s = (f"{size/1024:.0f} KB" if size else "—")
        rows += (
            f'<tr><td style="padding:3px 8px;font-family:var(--cad-mono);'
            f'font-weight:700;">{html.escape(str(e.get("format", "")))}</td>'
            f'<td style="padding:3px 8px;font-family:var(--cad-mono);'
            f'font-size:10.5px;">{html.escape(str(e.get("generated_at", ""))[:19])}</td>'
            f'<td style="padding:3px 8px;font-size:11px;">'
            f'{html.escape(str(e.get("generated_by") or "—"))}</td>'
            f'<td class="num" style="padding:3px 8px;text-align:right;'
            f'font-size:11px;">{size_s}</td></tr>')
    return (
        f'<div style="margin-top:12px;">'
        f'<div style="font-family:var(--cad-mono);font-size:10px;'
        f'letter-spacing:0.08em;color:{PALETTE["text_muted"]};'
        f'text-transform:uppercase;margin-bottom:4px;">'
        f'Previously generated · registry ({len(exports)})</div>'
        f'<table style="width:100%;border-collapse:collapse;font-size:12px;">'
        f'<thead><tr style="border-bottom:1px solid {PALETTE["border"]};">'
        f'<th style="text-align:left;padding:3px 8px;">Format</th>'
        f'<th style="text-align:left;padding:3px 8px;">Generated</th>'
        f'<th style="text-align:left;padding:3px 8px;">By</th>'
        f'<th style="text-align:right;padding:3px 8px;">Size</th>'
        f'</tr></thead><tbody>{rows}</tbody></table></div>')


def render_deal_dashboard(
    deal_id: str,
    profile: Dict[str, Any],
    has_packet: bool = False,
    exports: "list | None" = None,
) -> str:
    """Render a unified deal dashboard with all model links.

    ``exports`` — recent rows from the ``generated_exports`` registry
    (P5): the deal's previously generated artifacts render as a
    read-only audit list under the export buttons, so a partner can see
    what's already been produced (and when, by whom) before
    regenerating. None/empty → no panel, nothing fabricated.
    """
    name = str(profile.get("name", deal_id))
    did = html.escape(deal_id)
    state = str(profile.get("state", ""))

    rev_h = float(profile.get("net_revenue", 0) or 0)

    # Title meta is the deal's IDENTITY line — state + id only. The
    # financials (NPR / EBITDA / EV) used to live here too, but the
    # "DEAL SNAPSHOT" value-anchor immediately below is the canonical
    # valuation readout, so repeating them in the title stacked the
    # same numbers three deep (title → anchor → KPI strip). Identity
    # here, valuation in the anchor, operating profile in the KPI strip
    # — each number has exactly one home now.
    meta_parts = []
    if state:
        meta_parts.append(f"State {state}")
    meta_parts.append(f"Deal {deal_id}")
    # Workstream H: a deal anchored to a real facility names its CCN in
    # the identity line — the metrics trace to a filing, not a fiction.
    if profile.get("hcris_ccn"):
        fy = profile.get("hcris_fy")
        meta_parts.append(
            f"HCRIS CCN {profile['hcris_ccn']}"
            + (f" · FY{int(fy)}" if fy else ""))

    title_block = ck_page_title(
        name,
        eyebrow="DEAL DASHBOARD",
        meta=" · ".join(meta_parts),
    )

    # Editorial action row — Open Workbench + ZIP rendered as inline
    # action links right of the title, no card chrome.
    action_links = []
    if has_packet:
        action_links.append(
            f'<a href="/analysis/{did}" class="cad-btn cad-btn-primary" '
            'style="text-decoration:none;">Open Workbench &rarr;</a>'
        )
    action_links.append(
        f'<a href="/api/deals/{did}/package" class="cad-btn" '
        'style="text-decoration:none;">Download ZIP</a>'
    )
    # P1 — carry this deal as ambient context; module links in the
    # active-deal bar open pre-scoped to it on every page.
    action_links.append(
        f'<a href="/deal-context?set={did}&return=/deal/{did}" class="cad-btn" '
        'style="text-decoration:none;" title="Module links in the bar open '
        'pre-scoped to this deal on every page.">Set Active Deal</a>'
    )
    action_row = (
        '<div style="display:flex;gap:6px;margin:0 0 16px;flex-wrap:wrap;">'
        + "".join(action_links)
        + '</div>'
    )

    # Derived inline estimates
    rev_val = float(profile.get("net_revenue", 0) or 0)
    margin_val = float(profile.get("ebitda_margin", 0.10) or 0.10)
    dr_val = float(profile.get("denial_rate", 12) or 12)
    ebitda_est = rev_val * margin_val
    ev_est = ebitda_est * 11.0
    equity_est = ev_est * 0.35
    irr_est = (
        ((ev_est * 1.15 ** 5 * 12.0 * 0.35) / equity_est) ** 0.2 - 1
        if equity_est > 0 else 0
    )
    recoverable = rev_val * max(0, dr_val - 8) / 100 * 0.3

    # Model grid — 26 tiles grouped into 4 semantic categories.
    # Per-tile color drops from "random palette pick" to a typed
    # category code (Valuation = teal · Operations = green ·
    # Risk = bronze · Synthesis = navy), with section headers so
    # the colors carry meaning instead of looking like a rainbow.
    valuation_tiles = [
        _model_tile(
            "DCF", f"/models/dcf/{did}", "DCF Valuation",
            "10% WACC · 5-year projection · sensitivity grid",
            category="valuation",
            inline_value=(f"{ck_fmt_currency(ev_est)} EV" if ev_est > 0 else ""),
            inline_color=PALETTE["positive"],
        ),
        _model_tile(
            "LBO", f"/models/lbo/{did}", "LBO Returns",
            "S&U · debt schedule · returns waterfall",
            category="valuation",
            inline_value=(f"{irr_est:.0%} IRR" if irr_est else ""),
            inline_color=PALETTE["positive"] if irr_est > 0.15 else PALETTE["warning"],
        ),
        _model_tile(
            "WFL", f"/models/waterfall/{did}", "Returns Waterfall",
            "LP/GP split · tier allocation · IRR & MOIC",
            category="valuation",
        ),
        _model_tile(
            "BRG", f"/models/bridge/{did}", "EBITDA Bridge",
            "7-lever value creation · probability-weighted",
            category="valuation",
        ),
        _model_tile(
            "CMP", f"/models/comparables/{did}", "Comparable Hospitals",
            "Nearest hospitals by profile distance (HCRIS)",
            category="valuation",
        ),
        _model_tile(
            "DBT", f"/models/debt/{did}", "Debt Schedule",
            "Leverage trajectory & repayment schedule",
            category="valuation",
        ),
        _model_tile(
            "RET", f"/models/returns/{did}", "Returns & Covenant",
            "IRR · MOIC · covenant headroom · EBITDA cushion",
            category="valuation",
        ),
    ]
    operations_tiles = [
        _model_tile(
            "FIN", f"/models/financials/{did}", "3-Statement Model",
            "Income · balance sheet · cash flow",
            category="operations",
        ),
        _model_tile(
            "MKT", f"/models/market/{did}", "Market & Moat",
            "HHI concentration · Mauboussin moat scoring",
            category="operations",
        ),
        _model_tile(
            "DEN", f"/models/denial/{did}", "Denial Drivers",
            ("Root-cause decomposition · est. "
             f"{ck_fmt_currency(recoverable)} recoverable" if recoverable > 0
             else "Root-cause decomposition · AR bridge"),
            category="operations",
            # Only quote a denial trajectory when the rate was ENTERED —
            # the 12% model default must not read as the deal's number.
            inline_value=(
                f"{dr_val:.1f}% → 8%"
                if profile.get("denial_rate") not in (None, "")
                and dr_val > 8 else ""),
            inline_color=PALETTE["warning"],
        ),
        _model_tile(
            "SVC", f"/models/service-lines/{did}", "Service Lines",
            "Revenue & margin by service line",
            category="operations",
        ),
        _model_tile(
            "PLY", f"/models/playbook/{did}", "Value Creation Playbook",
            "Prioritized initiatives · EBITDA impact estimates",
            category="operations",
        ),
        _model_tile(
            "MKS", f"/deal/{did}/market-structure", "Market Structure",
            "HHI / CR3 / CR5 + fragmentation verdict + thesis hint",
            category="operations",
        ),
        _model_tile(
            "WHT", f"/deal/{did}/white-space", "White Space",
            "Geographic / segment / channel adjacencies with scores",
            category="operations",
        ),
        _model_tile(
            "TRD", f"/models/trends/{did}", "Trend Forecast",
            "Per-metric trend detection & short-horizon forecast",
            category="operations",
        ),
    ]
    risk_tiles = [
        _model_tile(
            "PRS", f"/pressure?deal_id={did}", "Pressure Test",
            "Stress scenarios · severity-ranked risk flags",
            category="risk",
        ),
        _model_tile(
            "STR", f"/deal/{did}/stress", "Stress Grid",
            "Scenario stress grid: rate / volume / multiple / lever shocks",
            category="risk",
        ),
        _model_tile(
            "ANM", f"/models/anomalies/{did}", "Anomaly Detection",
            "Data-quality checks against HCRIS benchmarks",
            category="risk",
        ),
        _model_tile(
            "CHL", f"/models/challenge/{did}", "Challenge Solver",
            "Reverse analytics: what breaks the deal?",
            category="risk",
        ),
        _model_tile(
            "RED", f"/deal/{did}/red-flags", "Red Flags",
            "Critical / high heuristic hits + reasonableness violations",
            category="risk",
        ),
        _model_tile(
            "990", f"/models/irs990/{did}", "IRS 990 Cross-Check",
            "Non-profit financial verification",
            category="risk",
        ),
    ]
    synthesis_tiles = [
        _model_tile(
            "PRV", f"/deal/{did}/partner-review", "Partner Review",
            "PE brain verdict: recommendation, bull/bear, investability",
            category="synthesis",
        ),
        _model_tile(
            "INV", f"/deal/{did}/investability", "Investability",
            "Composite 0-100 + exit readiness + three things to fix",
            category="synthesis",
        ),
        _model_tile(
            "ARC", f"/deal/{did}/archetype", "Archetype",
            "Sponsor-structure archetype match + time-series regime",
            category="synthesis",
        ),
        _model_tile(
            "ICP", f"/deal/{did}/ic-packet", "IC Packet",
            "Master bundle: IC memo + cheatsheet + 100-day + bear book",
            category="synthesis",
        ),
        _model_tile(
            "DLQ", f"/models/questions/{did}", "Diligence Questions",
            "Auto-generated data-room questions",
            category="synthesis",
        ),
    ]

    def _group(label: str, tiles_list: List[str], category: str) -> str:
        color = _CATEGORY_COLORS[category]
        return (
            '<div class="cad-modelgroup-head">'
            f'<h3><span class="cad-modelgroup-dot" '
            f'style="background:{color};"></span>{html.escape(label)}</h3>'
            f'<span class="cad-modelgroup-count">'
            f'{len(tiles_list)} models</span>'
            '</div>'
            f'<div class="cad-modelgrid">{"".join(tiles_list)}</div>'
        )

    model_grid = (
        _group("Valuation", valuation_tiles, "valuation")
        + _group("Operations", operations_tiles, "operations")
        + _group("Risk", risk_tiles, "risk")
        + _group("Synthesis", synthesis_tiles, "synthesis")
    )
    total_tiles = (
        len(valuation_tiles) + len(operations_tiles)
        + len(risk_tiles) + len(synthesis_tiles)
    )

    # Export strip
    exports = (
        f'<div class="cad-card">'
        f'<div style="display:flex;align-items:center;gap:10px;margin-bottom:8px;">'
        f'<h2 style="margin:0;">Export &amp; Download</h2>'
        f'<span class="cad-section-code">EXP</span></div>'
        f'<div style="display:flex;gap:6px;flex-wrap:wrap;">'
        f'<a href="/api/deals/{did}/dcf" class="cad-btn" style="text-decoration:none;">DCF JSON</a>'
        f'<a href="/api/deals/{did}/lbo" class="cad-btn" style="text-decoration:none;">LBO JSON</a>'
        f'<a href="/api/deals/{did}/financials" class="cad-btn" style="text-decoration:none;">Financials JSON</a>'
        f'<a href="/api/deals/{did}/market" class="cad-btn" style="text-decoration:none;">Market JSON</a>'
        f'<a href="/api/deals/{did}/denial-drivers" class="cad-btn" style="text-decoration:none;">Denial JSON</a>'
        f'<a href="/api/deals/{did}/memo" class="cad-btn" style="text-decoration:none;">IC Memo</a>'
        f'<a href="/api/deals/{did}/package" class="cad-btn cad-btn-primary" style="text-decoration:none;">'
        f'Full Package (ZIP)</a>'
        f'</div>'
        f'{_exports_registry(exports)}'
        f'</div>'
    )

    # Operating-profile KPI strip — COMPLEMENTS the "DEAL SNAPSHOT"
    # value-anchor above rather than repeating it. The anchor owns the
    # valuation story (EV · net revenue · recoverable EBITDA · IRR); this
    # strip owns the operating facts the anchor can't carry — bed count,
    # initial-denial rate, EBITDA margin. Previously this was a second
    # copy of EV + recoverable, stacking the identical numbers right
    # under the anchor. One home per metric now.
    # ENTERED-basis pass (PAGE_INVENTORY top fix): these are the
    # partner's OWN entered numbers — badge them as such, and never
    # render the model's fallback constants (12% denial / 10% margin,
    # which the derived ESTIMATES above legitimately use) as if they
    # were the deal's observed values. Missing → em-dash, no badge.
    from ._chartis_kit import ck_basis_badge
    bed_count = profile.get("bed_count")
    bed_count_display = (
        f"{int(bed_count):,}{ck_basis_badge('entered')}"
        if bed_count not in (None, "") else "—"
    )
    dr_raw = profile.get("denial_rate")
    denial_display = (
        f"{float(dr_raw):.1f}%{ck_basis_badge('entered')}"
        if dr_raw not in (None, "") else "—"
    )
    margin_raw = profile.get("ebitda_margin")
    margin_display = (
        f"{ck_fmt_pct(float(margin_raw))}{ck_basis_badge('entered')}"
        if margin_raw not in (None, "") else "—"
    )
    # Glossary links from the KPI cards (PAGE_INVENTORY "partial" fix):
    # ck_kpi_block ESCAPES the label by contract, so the link lives in
    # the trusted sub line — metric_label_link falls back to plain text
    # for keys without a glossary card (no dead links).
    from ._glossary_link import metric_label_link

    def _gloss(key: str) -> str:
        link = metric_label_link("glossary →", key)
        return f" · {link}" if link.startswith("<a") else ""

    kpi_strip = (
        '<div class="ck-kpi-grid" '
        'style="grid-template-columns:repeat(3,1fr);'
        'gap:8px;margin:8px 0 16px;">'
        + ck_kpi_block("Bed Count", bed_count_display, "HCRIS / entered")
        + ck_kpi_block("Denial Rate", denial_display,
                       ("initial denials" if dr_raw not in (None, "")
                        else "not entered — estimates use the 12% model "
                             "default") + _gloss("denial_rate"))
        + ck_kpi_block("EBITDA Margin", margin_display,
                       ("of net revenue" if margin_raw not in (None, "")
                        else "not entered — estimates use the 10% model "
                             "default") + _gloss("ebitda_margin"))
        + '</div>'
    )

    # Forward action — the analysis workbench is the deeper surface
    # (full packet, scenarios, provenance). This used to self-link back
    # to /deal/{deal_id} — the very page being viewed — which read as a
    # dead link. Point it where the partner actually goes next.
    next_up = ck_next_section(
        "Open the analysis workbench",
        f"/analysis/{deal_id}",
        eyebrow="Up next",
        italic_word="workbench",
    )

    # Explainer in the partner-canonical position (right below the
    # title) — same Portfolio-Heatmap pattern used elsewhere on the
    # diligence surfaces.
    explainer = ck_page_explainer(
        "Every analysis on this deal, in one place.",
        (
            f"All {total_tiles} analytical models grouped into four "
            "categories — valuation, operations, risk, synthesis. "
            "Click any tile to drop into that model with the deal's "
            "data pre-loaded. The snapshot above carries the rough "
            "EV + recoverable-EBITDA estimates the deeper models refine; "
            "the strip beside it is the operating profile."
        ),
    )

    # Lead takeaway — orient the partner with the deal's scale and the
    # recoverable-EBITDA opportunity before the model grid. EV /
    # recoverable are the same indicative estimates the KPI strip and
    # tiles show; opportunity is suppressed when there's nothing to
    # recover rather than shown as $0.
    # ck_fmt_currency rolls to $B at ≥$1B (house style) — a platform-scale
    # deal's EV/NPR reads "$1.19B", not "$1,194M".
    lead_anchor = ck_value_anchor(
        "DEAL SNAPSHOT",
        f"{ck_fmt_currency(ev_est)} EV" if ev_est > 0 else "EV —",
        delta=(f"{ck_fmt_currency(rev_h)} net revenue" if rev_h > 0 else ""),
        opportunity=(
            f"{ck_fmt_currency(recoverable)} recoverable EBITDA"
            if recoverable > 0 else ""
        ),
        target=f"~{irr_est:.0%} indicative IRR" if irr_est else "",
        tone="teal",
    )
    body = (
        title_block + lead_anchor + explainer + action_row + kpi_strip
        + model_grid + exports + next_up
    )

    return chartis_shell(
        body, name,
        active_nav="/analysis",
        subtitle=f"Deal {deal_id} · {total_tiles} analytical models",
        extra_css=_MODEL_TILE_CSS,
    )
