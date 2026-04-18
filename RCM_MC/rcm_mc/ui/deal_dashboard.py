"""SeekingChartis Deal Dashboard — unified single-deal view.

Shows all available information and models for a deal in one page
with clear navigation to every model output.
"""
from __future__ import annotations

import html
from typing import Any, Dict, List, Optional, Tuple

from .shell_v2 import shell_v2
from .brand import PALETTE


def _model_tile(
    code: str,
    href: str,
    title: str,
    desc: str,
    *,
    accent: str,
    inline_value: str = "",
    inline_color: str = "",
) -> str:
    """Render one model tile for the deal dashboard grid."""
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
.cad-modelgrid {{
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  gap: 0;
  border-top: 1px solid {PALETTE['border']};
  border-left: 1px solid {PALETTE['border']};
  margin-bottom: 12px;
}}
.cad-modeltile {{
  display: block;
  padding: 10px 14px 12px;
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
  margin-bottom: 6px;
  min-height: 16px;
}}
.cad-modeltile-title {{
  font-size: 12.5px;
  font-weight: 700;
  color: {PALETTE['text_primary']};
  letter-spacing: 0.04em;
  text-transform: uppercase;
  margin-bottom: 3px;
}}
.cad-modeltile-desc {{
  font-size: 10.5px;
  color: {PALETTE['text_muted']};
  font-family: {{font_mono}};
  letter-spacing: 0.02em;
  line-height: 1.5;
}}
.cad-modeltile:hover .cad-modeltile-title {{
  color: var(--tile-accent, {PALETTE['brand_accent']});
}}
.cad-deal-ident {{
  font-family: {{font_mono}};
  font-size: 10.5px;
  letter-spacing: 0.12em;
  color: {PALETTE['text_muted']};
  text-transform: uppercase;
}}
.cad-deal-ident .ident-key {{ color: {PALETTE['text_muted']}; }}
.cad-deal-ident .ident-val {{ color: {PALETTE['text_primary']}; font-weight: 600; }}
.cad-deal-ident .ident-sep {{ color: {PALETTE['border_light']}; padding: 0 8px; }}
""".replace("{font_mono}", "'JetBrains Mono', 'SF Mono', monospace")


def render_deal_dashboard(
    deal_id: str,
    profile: Dict[str, Any],
    has_packet: bool = False,
) -> str:
    """Render a unified deal dashboard with all model links."""
    name = html.escape(str(profile.get("name", deal_id)))
    did = html.escape(deal_id)
    state = html.escape(str(profile.get("state", "")))

    rev_h = float(profile.get("net_revenue", 0) or 0)
    margin_h = float(profile.get("ebitda_margin", 0.10) or 0.10)
    ebitda_h = rev_h * margin_h
    ev_h = ebitda_h * 11.0

    # Identity strip — Bloomberg-style DEAL / TICKER / STATE / EBITDA / EV
    ident_parts = [
        f'<span class="ident-key">DEAL</span> <span class="ident-val">{did}</span>',
    ]
    if state:
        ident_parts.append(
            f'<span class="ident-key">STATE</span> <span class="ident-val">{state}</span>'
        )
    if rev_h > 0:
        ident_parts.append(
            f'<span class="ident-key">NPR</span> '
            f'<span class="ident-val">${rev_h/1e6:,.0f}M</span>'
        )
        ident_parts.append(
            f'<span class="ident-key">EBITDA</span> '
            f'<span class="ident-val">${ebitda_h/1e6:,.0f}M</span>'
        )
        ident_parts.append(
            f'<span class="ident-key">EV</span> '
            f'<span class="ident-val">${ev_h/1e6:,.0f}M</span> '
            f'<span class="ident-key">@11.0x</span>'
        )
    ident_strip = (
        '<span class="ident-sep">|</span>'.join(ident_parts)
    )

    header = (
        f'<div class="cad-card" style="padding:14px 18px;">'
        f'<div style="display:flex;justify-content:space-between;align-items:start;gap:20px;">'
        f'<div style="flex:1;min-width:0;">'
        f'<div style="display:flex;align-items:center;gap:10px;margin-bottom:8px;">'
        f'<span class="cad-section-code">DEAL</span>'
        f'<h1 style="margin:0;font-size:18px;font-weight:700;letter-spacing:0.06em;'
        f'text-transform:uppercase;color:{PALETTE["text_primary"]};">{name}</h1>'
        f'</div>'
        f'<div class="cad-deal-ident">{ident_strip}</div>'
        f'</div>'
        f'<div style="display:flex;gap:6px;flex-shrink:0;">'
        + (f'<a href="/analysis/{did}" class="cad-btn cad-btn-primary" style="text-decoration:none;">Open Workbench &rarr;</a>' if has_packet else "")
        + f'<a href="/api/deals/{did}/package" class="cad-btn" style="text-decoration:none;">ZIP</a>'
        f'</div></div></div>'
    )

    # Profile metrics (KPI grid)
    metrics: List[Tuple[str, Any, str]] = [
        ("Denial Rate", profile.get("denial_rate"), "%"),
        ("Days in AR", profile.get("days_in_ar"), ""),
        ("Net Collection", profile.get("net_collection_rate"), "%"),
        ("Clean Claim Rate", profile.get("clean_claim_rate"), "%"),
        ("Cost to Collect", profile.get("cost_to_collect"), "%"),
        ("Claims Volume", profile.get("claims_volume"), ""),
        ("Bed Count", profile.get("bed_count"), ""),
        ("Net Revenue", profile.get("net_revenue"), "$M"),
    ]

    kpi_cards = ""
    for label, val, suffix in metrics:
        if val is None:
            continue
        try:
            v = float(val)
            if suffix == "$M":
                display = f"${v / 1e6:,.0f}M"
            elif suffix == "%":
                display = f"{v:.1f}%"
            else:
                display = f"{v:,.0f}"
        except (TypeError, ValueError):
            display = str(val)
        kpi_cards += (
            f'<div class="cad-kpi">'
            f'<div class="cad-kpi-value">{html.escape(display)}</div>'
            f'<div class="cad-kpi-label">{html.escape(label)}</div></div>'
        )

    profile_section = f'<div class="cad-kpi-grid">{kpi_cards}</div>' if kpi_cards else ""

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

    # Model grid — 17 tiles, each with a 3-letter code chip
    tiles: List[str] = [
        _model_tile(
            "DCF", f"/models/dcf/{did}", "DCF Valuation",
            "10% WACC · 5-year projection · sensitivity grid",
            accent=PALETTE["brand_accent"],
            inline_value=(f"${ev_est/1e6:,.0f}M EV" if ev_est > 0 else ""),
            inline_color=PALETTE["positive"],
        ),
        _model_tile(
            "LBO", f"/models/lbo/{did}", "LBO Returns",
            "S&U · debt schedule · returns waterfall",
            accent=PALETTE["brand_accent"],
            inline_value=(f"{irr_est:.0%} IRR" if irr_est else ""),
            inline_color=PALETTE["positive"] if irr_est > 0.15 else PALETTE["warning"],
        ),
        _model_tile(
            "FIN", f"/models/financials/{did}", "3-Statement Model",
            "Income · balance sheet · cash flow",
            accent=PALETTE["positive"],
        ),
        _model_tile(
            "MKT", f"/models/market/{did}", "Market & Moat",
            "HHI concentration · Mauboussin moat scoring",
            accent=PALETTE["positive"],
        ),
        _model_tile(
            "DEN", f"/models/denial/{did}", "Denial Drivers",
            ("Root-cause decomposition · est. "
             f"${recoverable/1e6:.1f}M recoverable" if recoverable > 0
             else "Root-cause decomposition · AR bridge"),
            accent=PALETTE["warning"],
            inline_value=(f"{dr_val:.1f}% → 8%" if dr_val > 8 else ""),
            inline_color=PALETTE["warning"],
        ),
        _model_tile(
            "PRS", f"/pressure?deal_id={did}", "Pressure Test",
            "Stress scenarios · severity-ranked risk flags",
            accent=PALETTE["negative"],
        ),
        _model_tile(
            "DLQ", f"/models/questions/{did}", "Diligence Questions",
            "Auto-generated data-room questions",
            accent=PALETTE["neutral"],
        ),
        _model_tile(
            "PLY", f"/models/playbook/{did}", "Value Creation Playbook",
            "Prioritized initiatives · EBITDA impact estimates",
            accent=PALETTE["neutral"],
        ),
        _model_tile(
            "WFL", f"/models/waterfall/{did}", "Returns Waterfall",
            "LP/GP split · tier allocation · IRR & MOIC",
            accent=PALETTE["brand_accent"],
        ),
        _model_tile(
            "BRG", f"/models/bridge/{did}", "EBITDA Bridge",
            "7-lever value creation · probability-weighted",
            accent=PALETTE["positive"],
        ),
        _model_tile(
            "CMP", f"/models/comparables/{did}", "Comparable Hospitals",
            "Nearest hospitals by profile distance (HCRIS)",
            accent=PALETTE["text_link"],
        ),
        _model_tile(
            "ANM", f"/models/anomalies/{did}", "Anomaly Detection",
            "Data-quality checks against HCRIS benchmarks",
            accent=PALETTE["warning"],
        ),
        _model_tile(
            "SVC", f"/models/service-lines/{did}", "Service Lines",
            "Revenue & margin by service line",
            accent=PALETTE["neutral"],
        ),
        _model_tile(
            "RET", f"/models/returns/{did}", "Returns & Covenant",
            "IRR · MOIC · covenant headroom · EBITDA cushion",
            accent=PALETTE["positive"],
        ),
        _model_tile(
            "DBT", f"/models/debt/{did}", "Debt Schedule",
            "Leverage trajectory & repayment schedule",
            accent=PALETTE["brand_accent"],
        ),
        _model_tile(
            "CHL", f"/models/challenge/{did}", "Challenge Solver",
            "Reverse analytics: what breaks the deal?",
            accent=PALETTE["negative"],
        ),
        _model_tile(
            "990", f"/models/irs990/{did}", "IRS 990 Cross-Check",
            "Non-profit financial verification",
            accent=PALETTE["positive"],
        ),
        _model_tile(
            "TRD", f"/models/trends/{did}", "Trend Forecast",
            "Per-metric trend detection & short-horizon forecast",
            accent=PALETTE["positive"],
        ),
        _model_tile(
            "PRV", f"/deal/{did}/partner-review", "Partner Review",
            "PE brain verdict: recommendation, bull/bear, investability",
            accent=PALETTE["brand_accent"],
        ),
        _model_tile(
            "RED", f"/deal/{did}/red-flags", "Red Flags",
            "Critical/high heuristic hits + reasonableness violations",
            accent=PALETTE["negative"],
        ),
        _model_tile(
            "ARC", f"/deal/{did}/archetype", "Archetype",
            "Sponsor-structure archetype match + time-series regime",
            accent=PALETTE["brand_accent"],
        ),
        _model_tile(
            "INV", f"/deal/{did}/investability", "Investability",
            "Composite 0-100 + exit readiness + three things to fix",
            accent=PALETTE["brand_accent"],
        ),
        _model_tile(
            "MKT", f"/deal/{did}/market-structure", "Market Structure",
            "HHI / CR3 / CR5 + fragmentation verdict + thesis hint",
            accent=PALETTE["brand_accent"],
        ),
    ]

    model_grid = (
        f'<div class="cad-card" style="padding:10px 14px 4px;">'
        f'<div style="display:flex;align-items:center;gap:10px;margin-bottom:8px;">'
        f'<h2 style="margin:0;">Analytical Models</h2>'
        f'<span class="cad-section-code">MDL · {len(tiles)}</span></div></div>'
        f'<div class="cad-modelgrid">{"".join(tiles)}</div>'
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
        f'</div></div>'
    )

    body = f'{header}{profile_section}{model_grid}{exports}'

    return shell_v2(
        body, name,
        active_nav="/analysis",
        subtitle=f"Deal {deal_id} · 17 analytical models · click any tile",
        extra_css=_MODEL_TILE_CSS,
    )
