"""SeekingChartis Financial Models — browser-rendered DCF, LBO, 3-Statement.

Renders financial model outputs as rich HTML tables instead of raw JSON.
Accessed via /models/dcf/<deal_id>, /models/lbo/<deal_id>, /models/financials/<deal_id>.
"""
from __future__ import annotations

import html
from typing import Any, Dict, List, Optional

from ._chartis_kit import chartis_shell
from .brand import PALETTE


def _model_nav(deal_id: str, active: str = "") -> str:
    """Shared model ribbon — three logical groups rather than a flat
    19-link strip that nobody could scan.

    Pre-Phase-W2: 19 links in one row (PRF MEM BRG CI SCN AI DCF LBO
    FIN MKT DEN RET LVR WFL PLY TRD PRED MEM2). Partners couldn't find
    anything. Many routes duplicated (BRG and LVR, MEM and MEM2) or
    pointed at pages superseded by the /analysis workbench tabs.

    Post: three groups on one row —
      Workbench — the comprehensive view (back-link to /analysis)
      Models    — deep-dive on specific calculations (DCF/LBO/Bridge/3-Stmt)
      Context   — peer + market + playbook (IC Memo / Market / Playbook)

    Every route still served by the router; the dropped links live in
    the Cmd+K palette. This function controls only what the horizontal
    ribbon shows. Eight links total.
    """
    did = html.escape(deal_id)
    # Three groups, separated by a thin divider in the rendered nav.
    workbench = [
        ("WB", "Workbench", f"/analysis/{did}", "workbench"),
    ]
    models = [
        ("DCF", "DCF",      f"/models/dcf/{did}",        "dcf"),
        ("LBO", "LBO",      f"/models/lbo/{did}",        "lbo"),
        ("BRG", "Bridge",   f"/models/bridge/{did}",     "bridge"),
        ("FIN", "3-Stmt",   f"/models/financials/{did}", "financials"),
    ]
    context = [
        ("MKT", "Market",   f"/models/market/{did}",     "market"),
        ("PLY", "Playbook", f"/models/playbook/{did}",   "playbook"),
        ("MEM", "IC Memo",  f"/ic-memo/{did}",           "ic_memo"),
    ]

    def _items_html(group, first_starts_group=False):
        out = []
        for i, (code, label, href, key) in enumerate(group):
            classes = "cad-modelnav-item"
            if key == active:
                classes += " active"
            if first_starts_group and i == 0:
                classes += " new-group"
            out.append(
                f'<a href="{href}" class="{classes}">'
                f'<span class="cad-modelnav-code">{code}</span>'
                f'<span class="cad-modelnav-label">{html.escape(label)}</span>'
                f'</a>'
            )
        return "".join(out)

    return (
        f'<style>'
        f'.cad-modelnav{{display:flex;flex-wrap:wrap;gap:0;margin-bottom:14px;'
        f'border:1px solid {PALETTE["border"]};background:{PALETTE["bg_secondary"]};'
        f'border-left:3px solid {PALETTE["accent_amber"]};}}'
        f'.cad-modelnav-dash{{display:flex;align-items:center;gap:6px;padding:8px 12px;'
        f'text-decoration:none;color:{PALETTE["text_primary"]};'
        f'background:#03050a;border-right:1px solid {PALETTE["border"]};'
        f'font-family:var(--cad-mono);font-size:10px;font-weight:700;'
        f'letter-spacing:0.14em;text-transform:uppercase;}}'
        f'.cad-modelnav-dash:hover{{color:{PALETTE["accent_amber"]};}}'
        f'.cad-modelnav-item{{display:flex;align-items:center;gap:6px;padding:6px 12px;'
        f'text-decoration:none;color:{PALETTE["text_secondary"]};'
        f'border-right:1px solid {PALETTE["border"]};'
        f'transition:background 0.1s,color 0.1s;}}'
        f'.cad-modelnav-item.new-group{{'
        f'border-left:2px solid {PALETTE["accent_amber"]};margin-left:-1px;}}'
        f'.cad-modelnav-item:hover{{background:{PALETTE["bg_tertiary"]};color:{PALETTE["text_primary"]};}}'
        f'.cad-modelnav-item.active{{background:{PALETTE["bg_tertiary"]};'
        f'color:{PALETTE["accent_amber"]};'
        f'box-shadow:inset 0 -2px 0 {PALETTE["accent_amber"]};}}'
        f'.cad-modelnav-code{{font-family:var(--cad-mono);font-size:9px;font-weight:700;'
        f'letter-spacing:0.14em;color:{PALETTE["accent_amber"]};'
        f'padding:1px 4px;border:1px solid {PALETTE["border_light"]};}}'
        f'.cad-modelnav-item.active .cad-modelnav-code{{'
        f'background:{PALETTE["accent_amber"]};color:#000;border-color:{PALETTE["accent_amber"]};}}'
        f'.cad-modelnav-label{{font-size:11px;font-weight:600;'
        f'letter-spacing:0.04em;text-transform:uppercase;}}'
        f'</style>'
        f'<div class="cad-modelnav">'
        f'<a href="/deal/{did}" class="cad-modelnav-dash">&larr; Dashboard</a>'
        f'{_items_html(workbench)}'
        f'{_items_html(models, first_starts_group=True)}'
        f'{_items_html(context, first_starts_group=True)}'
        f'</div>'
    )


def _fmt_m(val: Any) -> str:
    """Format as $XM."""
    if val is None:
        return "—"
    try:
        v = float(val)
        if abs(v) >= 1e9:
            return f"${v / 1e9:,.1f}B"
        return f"${v / 1e6:,.1f}M"
    except (TypeError, ValueError):
        return "—"


def _fmt_pct(val: Any, is_fraction: bool = False) -> str:
    """Format a percentage.

    Auto-detect mode (is_fraction=False): values with ``abs(v) < 1``
    are treated as fractions (0.10 → "10.0%"); values ≥ 1 are treated
    as already-%. This is the legacy path for assumption fields like
    WACC / terminal_growth.

    Explicit fraction mode (is_fraction=True): always treats input as
    a fraction. Callers rendering IRR ≥ 100% (e.g., 1.3022 on an
    absurd LBO output) must pass ``is_fraction=True`` so 1.3 doesn't
    render as "1.3%" when it means "130%".
    """
    if val is None:
        return "—"
    try:
        v = float(val)
        if is_fraction or abs(v) < 1:
            return f"{v:.1%}"
        return f"{v:.1f}%"
    except (TypeError, ValueError):
        return "—"


def _fmt_x(val: Any) -> str:
    if val is None:
        return "—"
    try:
        return f"{float(val):.2f}x"
    except (TypeError, ValueError):
        return "—"


def render_dcf_page(deal_id: str, deal_name: str, dcf: Dict[str, Any]) -> str:
    """Render DCF model as a full browser page."""
    assumptions = dcf.get("assumptions", {})
    projections = dcf.get("projections", [])
    ev = dcf.get("enterprise_value", 0)
    pv_cf = dcf.get("pv_cash_flows", 0)
    pv_term = dcf.get("pv_terminal", 0)
    tv = dcf.get("terminal_value", 0)

    # KPIs
    kpis = (
        f'<div class="cad-kpi-grid">'
        f'<div class="cad-kpi"><div class="cad-kpi-value">{_fmt_m(ev)}</div>'
        f'<div class="cad-kpi-label">Enterprise Value</div></div>'
        f'<div class="cad-kpi"><div class="cad-kpi-value">{_fmt_m(pv_cf)}</div>'
        f'<div class="cad-kpi-label">PV of Cash Flows</div></div>'
        f'<div class="cad-kpi"><div class="cad-kpi-value">{_fmt_m(pv_term)}</div>'
        f'<div class="cad-kpi-label">PV of Terminal Value</div></div>'
        f'<div class="cad-kpi"><div class="cad-kpi-value">{_fmt_m(tv)}</div>'
        f'<div class="cad-kpi-label">Terminal Value</div></div>'
        f'<div class="cad-kpi"><div class="cad-kpi-value">{_fmt_pct(assumptions.get("wacc"))}</div>'
        f'<div class="cad-kpi-label">WACC</div></div>'
        f'<div class="cad-kpi"><div class="cad-kpi-value">{_fmt_pct(assumptions.get("terminal_growth"))}</div>'
        f'<div class="cad-kpi-label">Terminal Growth</div></div>'
        f'</div>'
    )

    # Projections table
    proj_rows = ""
    for p in projections:
        yr = p.get("year", "")
        proj_rows += (
            f'<tr>'
            f'<td class="num" style="font-weight:600;">Year {yr}</td>'
            f'<td class="num">{_fmt_m(p.get("revenue"))}</td>'
            f'<td class="num">{_fmt_m(p.get("ebitda"))}</td>'
            f'<td class="num">{_fmt_pct(p.get("ebitda_margin"))}</td>'
            f'<td class="num">{_fmt_m(p.get("free_cash_flow"))}</td>'
            f'<td class="num">{_fmt_m(p.get("pv_fcf"))}</td>'
            f'</tr>'
        )
    proj_table = (
        f'<div class="cad-card">'
        f'<div style="display:flex;align-items:center;gap:10px;margin-bottom:10px;">'
        f'<h2 style="margin:0;">Cash Flow Projections</h2>'
        f'<span class="cad-section-code">PROJ</span></div>'
        f'<table class="cad-table crosshair"><thead><tr>'
        f'<th>Year</th><th>Revenue</th><th>EBITDA</th>'
        f'<th>Margin</th><th>FCF</th><th>PV(FCF)</th>'
        f'</tr></thead><tbody>{proj_rows}</tbody></table></div>'
    ) if proj_rows else ""

    # Sensitivity matrix with heatmap cells
    sensitivity = dcf.get("sensitivity", {})
    sens_html = ""
    if sensitivity:
        matrix = sensitivity.get("wacc_x_growth", sensitivity.get("matrix", []))
        if isinstance(matrix, list) and matrix:
            # First compute min/max across all cells for heatmap scaling
            all_vals = []
            for row in matrix[:8]:
                for cell in (row.get("values", []) if isinstance(row, dict) else []):
                    v = cell.get("ev", cell.get("value", 0)) if isinstance(cell, dict) else cell
                    try:
                        all_vals.append(float(v))
                    except (TypeError, ValueError):
                        pass
            vmin = min(all_vals) if all_vals else 0
            vmax = max(all_vals) if all_vals else 1
            vrange = (vmax - vmin) or 1

            rows_h = ""
            for row in matrix[:8]:
                cells = ""
                for cell in (row.get("values", []) if isinstance(row, dict) else []):
                    v = cell.get("ev", cell.get("value", 0)) if isinstance(cell, dict) else cell
                    try:
                        pos = (float(v) - vmin) / vrange
                    except (TypeError, ValueError):
                        pos = 0.5
                    # reverse: high EV = green (heat-1), low EV = red (heat-5)
                    if pos > 0.8: heat = "cad-heat-1"
                    elif pos > 0.6: heat = "cad-heat-2"
                    elif pos > 0.4: heat = "cad-heat-3"
                    elif pos > 0.2: heat = "cad-heat-4"
                    else: heat = "cad-heat-5"
                    cells += f'<td class="num {heat}" style="font-weight:600;">{_fmt_m(v)}</td>'
                label = row.get("wacc", row.get("label", "")) if isinstance(row, dict) else ""
                rows_h += (
                    f'<tr><td class="num" style="font-weight:700;background:'
                    f'{PALETTE["bg_tertiary"]};">{_fmt_pct(label)}</td>{cells}</tr>'
                )

            sens_html = (
                f'<div class="cad-card">'
                f'<div style="display:flex;align-items:center;gap:10px;margin-bottom:10px;">'
                f'<h2 style="margin:0;">Sensitivity: WACC × Terminal Growth</h2>'
                f'<span class="cad-section-code">SENS</span></div>'
                f'<p style="font-family:var(--cad-mono);font-size:10.5px;'
                f'letter-spacing:0.06em;color:{PALETTE["text_muted"]};'
                f'text-transform:uppercase;margin-bottom:8px;">'
                f'Enterprise value · green = high EV · red = low EV</p>'
                f'<table class="cad-table"><thead><tr><th>WACC ↓ / Growth →</th>'
                f'</tr></thead><tbody>{rows_h}</tbody></table></div>'
            )

    # Assumptions panel
    assume_items = ""
    for k, v in assumptions.items():
        if k in ("wacc", "terminal_growth"):
            continue
        assume_items += (
            f'<div style="display:flex;justify-content:space-between;padding:6px 0;'
            f'border-bottom:1px solid {PALETTE["border"]};font-family:var(--cad-mono);'
            f'font-size:11px;letter-spacing:0.04em;">'
            f'<span style="color:{PALETTE["text_muted"]};text-transform:uppercase;">'
            f'{html.escape(k.replace("_", " "))}</span>'
            f'<span style="color:{PALETTE["text_primary"]};font-weight:600;">'
            f'{_fmt_m(v) if isinstance(v, (int, float)) and abs(float(v)) > 1000 else html.escape(str(v))}</span>'
            f'</div>'
        )
    assume_section = (
        f'<div class="cad-card">'
        f'<div style="display:flex;align-items:center;gap:10px;margin-bottom:10px;">'
        f'<h2 style="margin:0;">Assumptions</h2>'
        f'<span class="cad-section-code">ASSM</span></div>'
        f'<div>{assume_items}</div></div>'
    ) if assume_items else ""

    # Actions
    actions = (
        f'<div class="cad-card" style="display:flex;gap:8px;flex-wrap:wrap;">'
        f'<a href="/api/deals/{html.escape(deal_id)}/dcf" class="cad-btn" '
        f'style="text-decoration:none;">Raw JSON</a>'
        f'<a href="/models/lbo/{html.escape(deal_id)}" class="cad-btn" '
        f'style="text-decoration:none;">LBO Model</a>'
        f'<a href="/models/financials/{html.escape(deal_id)}" class="cad-btn" '
        f'style="text-decoration:none;">3-Statement</a>'
        f'<a href="/analysis/{html.escape(deal_id)}" class="cad-btn cad-btn-primary" '
        f'style="text-decoration:none;">Full Analysis</a></div>'
    )

    # Interpretation — what this means
    wacc = float(assumptions.get("wacc", 0.10))
    growth = float(assumptions.get("terminal_growth", 0.025))
    tv_pct = pv_term / ev * 100 if ev > 0 else 0
    interp = (
        f'<div class="cad-card" style="border-left:3px solid {PALETTE["brand_accent"]};">'
        f'<div style="display:flex;align-items:center;gap:10px;margin-bottom:10px;">'
        f'<h2 style="margin:0;">Interpretation</h2>'
        f'<span class="cad-section-code">INT</span></div>'
        f'<div style="font-size:12.5px;color:{PALETTE["text_secondary"]};line-height:1.7;">'
        f'<p>At a WACC of <strong>{wacc:.1%}</strong> and terminal growth of '
        f'<strong>{growth:.1%}</strong>, enterprise value is <strong>{_fmt_m(ev)}</strong>. '
        f'Terminal value accounts for <strong>{tv_pct:.0f}%</strong> of total EV — '
        f'{"typical range (60-80%)" if 55 < tv_pct < 85 else "consider sensitivity to terminal assumptions"}.</p>'
        f'<p style="margin-top:8px;"><strong>Next steps:</strong> '
        f'Check the <a href="/models/lbo/{html.escape(deal_id)}" style="color:{PALETTE["text_link"]};">LBO model</a> '
        f'to see equity returns at this entry price, or the '
        f'<a href="/models/bridge/{html.escape(deal_id)}" style="color:{PALETTE["text_link"]};">EBITDA bridge</a> '
        f'to model value creation levers.</p>'
        f'</div></div>'
    )

    nav = _model_nav(deal_id, "dcf")
    body = f'{nav}{kpis}{proj_table}{interp}{sens_html}{assume_section}{actions}'
    return chartis_shell(body, f"DCF — {html.escape(deal_name)}",
                    active_nav="/analysis",
                    subtitle=f"Enterprise Value: {_fmt_m(ev)}")


def render_lbo_page(deal_id: str, deal_name: str, lbo: Dict[str, Any]) -> str:
    """Render LBO model as a full browser page."""
    returns = lbo.get("returns", {})
    sources = lbo.get("sources_and_uses", {})
    schedule = lbo.get("debt_schedule", [])
    annual = lbo.get("annual_projections", [])

    irr = returns.get("irr", 0)
    hold_years = lbo.get("hold_years", returns.get("hold_years", 5))
    moic = returns.get("moic", 0)
    entry_ev = sources.get("total_sources", 0) or lbo.get("entry_ev", 0)
    exit_ev = returns.get("exit_ev", 0)
    equity_invested = sources.get("equity", 0) or returns.get("equity_invested", 0)

    irr_color = PALETTE["positive"] if irr and irr > 0.20 else (
        PALETTE["warning"] if irr and irr > 0.15 else PALETTE["negative"])

    kpis = (
        f'<div class="cad-kpi-grid">'
        f'<div class="cad-kpi"><div class="cad-kpi-value" style="color:{irr_color};">'
        f'{_fmt_pct(irr, is_fraction=True)}</div>'
        f'<div class="cad-kpi-label">IRR</div></div>'
        f'<div class="cad-kpi"><div class="cad-kpi-value">{_fmt_x(moic)}</div>'
        f'<div class="cad-kpi-label">MOIC</div></div>'
        f'<div class="cad-kpi"><div class="cad-kpi-value">{_fmt_m(entry_ev)}</div>'
        f'<div class="cad-kpi-label">Entry EV</div></div>'
        f'<div class="cad-kpi"><div class="cad-kpi-value">{_fmt_m(exit_ev)}</div>'
        f'<div class="cad-kpi-label">Exit EV</div></div>'
        f'<div class="cad-kpi"><div class="cad-kpi-value">{_fmt_m(equity_invested)}</div>'
        f'<div class="cad-kpi-label">Equity Invested</div></div>'
        f'</div>'
    )

    # Sources & Uses
    su_html = ""
    if sources:
        total_s = sources.get("total_sources", 0) or sum(
            float(v) for k, v in sources.items()
            if k != "total_sources" and isinstance(v, (int, float))
        )
        su_rows = ""
        for k, v in sources.items():
            if k == "total_sources":
                continue
            try:
                pct = float(v) / total_s * 100 if total_s else 0
            except (TypeError, ValueError):
                pct = 0
            su_rows += (
                f'<tr><td style="font-weight:600;">{html.escape(k.replace("_", " ").title())}</td>'
                f'<td class="num">{_fmt_m(v)}</td>'
                f'<td class="num">{pct:.1f}%</td>'
                f'<td><div class="cad-bar" style="width:100%;">'
                f'<div class="cad-bar-fill" style="width:{pct:.0f}%;background:{PALETTE["brand_accent"]};"></div>'
                f'</div></td></tr>'
            )
        su_html = (
            f'<div class="cad-card">'
            f'<div style="display:flex;align-items:center;gap:10px;margin-bottom:10px;">'
            f'<h2 style="margin:0;">Sources &amp; Uses</h2>'
            f'<span class="cad-section-code">S&amp;U</span>'
            f'<span style="font-family:var(--cad-mono);font-size:10px;'
            f'letter-spacing:0.08em;color:{PALETTE["text_muted"]};'
            f'text-transform:uppercase;margin-left:auto;">'
            f'Total · {_fmt_m(total_s)}</span></div>'
            f'<table class="cad-table"><thead><tr>'
            f'<th>Item</th><th>Amount</th><th>%</th><th>Distribution</th>'
            f'</tr></thead><tbody>{su_rows}</tbody></table></div>'
        )

    # Annual projections with leverage heatmap
    annual_html = ""
    if annual:
        ann_rows = ""
        for yr in annual[:7]:
            lev = yr.get("leverage") or yr.get("net_debt_ebitda")
            try:
                lev_v = float(lev) if lev is not None else None
            except (TypeError, ValueError):
                lev_v = None
            if lev_v is None:
                heat = ""
            elif lev_v < 3: heat = "cad-heat-1"
            elif lev_v < 4.5: heat = "cad-heat-2"
            elif lev_v < 6: heat = "cad-heat-3"
            elif lev_v < 7.5: heat = "cad-heat-4"
            else: heat = "cad-heat-5"
            ann_rows += (
                f'<tr>'
                f'<td class="num" style="font-weight:700;color:{PALETTE["accent_amber"]};">Y{yr.get("year", "")}</td>'
                f'<td class="num">{_fmt_m(yr.get("revenue"))}</td>'
                f'<td class="num">{_fmt_m(yr.get("ebitda"))}</td>'
                f'<td class="num">{_fmt_m(yr.get("debt_balance") or yr.get("total_debt"))}</td>'
                f'<td class="num">{_fmt_m(yr.get("interest_expense") or yr.get("interest"))}</td>'
                f'<td class="num {heat}" style="font-weight:600;">{_fmt_x(lev)}</td>'
                f'</tr>'
            )
        annual_html = (
            f'<div class="cad-card">'
            f'<div style="display:flex;align-items:center;gap:10px;margin-bottom:10px;">'
            f'<h2 style="margin:0;">Annual Projections</h2>'
            f'<span class="cad-section-code">ANN</span>'
            f'<span style="font-family:var(--cad-mono);font-size:10px;'
            f'letter-spacing:0.08em;color:{PALETTE["text_muted"]};'
            f'text-transform:uppercase;margin-left:auto;">'
            f'Leverage · green &lt;3x · red &gt;7.5x</span></div>'
            f'<table class="cad-table crosshair"><thead><tr>'
            f'<th>Year</th><th>Revenue</th><th>EBITDA</th>'
            f'<th>Debt</th><th>Interest</th><th>Leverage</th>'
            f'</tr></thead><tbody>{ann_rows}</tbody></table></div>'
        )

    # Returns waterfall
    waterfall_html = ""
    if returns:
        wf_rows = ""
        for k, v in returns.items():
            if k in ("irr", "moic"):
                continue
            wf_rows += (
                f'<tr><td style="font-weight:600;">{html.escape(k.replace("_", " ").title())}</td>'
                f'<td class="num">{_fmt_m(v) if isinstance(v, (int, float)) and abs(float(v)) > 1000 else _fmt_pct(v) if isinstance(v, float) and abs(v) < 10 else html.escape(str(v))}</td></tr>'
            )
        waterfall_html = (
            f'<div class="cad-card">'
            f'<div style="display:flex;align-items:center;gap:10px;margin-bottom:10px;">'
            f'<h2 style="margin:0;">Returns Waterfall</h2>'
            f'<span class="cad-section-code">WFL</span></div>'
            f'<table class="cad-table"><thead><tr>'
            f'<th>Component</th><th>Value</th>'
            f'</tr></thead><tbody>{wf_rows}</tbody></table></div>'
        )

    actions = (
        f'<div class="cad-card" style="display:flex;gap:8px;flex-wrap:wrap;">'
        f'<a href="/api/deals/{html.escape(deal_id)}/lbo" class="cad-btn" '
        f'style="text-decoration:none;">Raw JSON</a>'
        f'<a href="/models/dcf/{html.escape(deal_id)}" class="cad-btn" '
        f'style="text-decoration:none;">DCF Model</a>'
        f'<a href="/models/financials/{html.escape(deal_id)}" class="cad-btn" '
        f'style="text-decoration:none;">3-Statement</a>'
        f'<a href="/analysis/{html.escape(deal_id)}" class="cad-btn cad-btn-primary" '
        f'style="text-decoration:none;">Full Analysis</a></div>'
    )

    # Interpretation
    irr_assessment = (
        "exceeds the typical 20% hurdle — strong candidate" if irr and irr > 0.20
        else "meets the 15-20% range — acceptable with operational upside" if irr and irr > 0.15
        else "below 15% hurdle — requires significant value creation thesis" if irr
        else "could not be computed"
    )
    interp = (
        f'<div class="cad-card" style="border-left:3px solid {irr_color};">'
        f'<div style="display:flex;align-items:center;gap:10px;margin-bottom:10px;">'
        f'<h2 style="margin:0;">Interpretation</h2>'
        f'<span class="cad-section-code" style="color:{irr_color};border-color:{irr_color};">INT</span></div>'
        f'<div style="font-size:12.5px;color:{PALETTE["text_secondary"]};line-height:1.7;">'
        f'<p>At <strong>{_fmt_x(moic)}</strong> MOIC and <strong>{_fmt_pct(irr, is_fraction=True)}</strong> IRR '
        f'over <strong>{hold_years:.0f} years</strong>, this deal {irr_assessment}.</p>'
        f'<p style="margin-top:8px;"><strong>Key drivers:</strong> '
        f'Check the <a href="/models/bridge/{html.escape(deal_id)}" style="color:{PALETTE["text_link"]};">EBITDA bridge</a> '
        f'to identify highest-probability levers, the '
        f'<a href="/models/debt/{html.escape(deal_id)}" style="color:{PALETTE["text_link"]};">debt schedule</a> '
        f'for leverage trajectory, or the '
        f'<a href="/models/challenge/{html.escape(deal_id)}" style="color:{PALETTE["text_link"]};">challenge solver</a> '
        f'to see what breaks the deal.</p>'
        f'</div></div>'
    )

    nav = _model_nav(deal_id, "lbo")
    body = f'{nav}{kpis}{su_html}{annual_html}{interp}{waterfall_html}{actions}'
    return chartis_shell(body, f"LBO — {html.escape(deal_name)}",
                    active_nav="/analysis",
                    subtitle=f"IRR: {_fmt_pct(irr, is_fraction=True)} | MOIC: {_fmt_x(moic)}")


def render_financials_page(deal_id: str, deal_name: str, model: Dict[str, Any]) -> str:
    """Render 3-statement model as a full browser page."""

    def _statement_table(title: str, items: Any) -> str:
        if not items:
            return ""
        if isinstance(items, dict):
            items = items.get("line_items", items.get("items", []))
        if not isinstance(items, list):
            return ""
        rows = ""
        for item in items:
            label = html.escape(str(item.get("label", item.get("line_item", ""))))
            value = item.get("value", item.get("amount", 0))
            source = item.get("source", "")
            indent = item.get("indent", 0)
            bold = item.get("is_total", False) or item.get("bold", False)
            style = f'padding-left:{12 + indent * 16}px;'
            if bold:
                style += 'font-weight:700;'
            src_badge = ""
            if source:
                src_cls = {
                    "HCRIS": "cad-badge-green",
                    "deal_profile": "cad-badge-blue",
                    "benchmark": "cad-badge-amber",
                    "computed": "cad-badge-muted",
                }.get(source, "cad-badge-muted")
                src_badge = f' <span class="cad-badge {src_cls}" style="font-size:9px;">{html.escape(source)}</span>'
            rows += (
                f'<tr>'
                f'<td style="{style}">{label}{src_badge}</td>'
                f'<td class="num">{_fmt_m(value)}</td>'
                f'</tr>'
            )
        return (
            f'<div class="cad-card">'
            f'<h2>{html.escape(title)}</h2>'
            f'<table class="cad-table"><thead><tr>'
            f'<th>Line Item</th><th>Amount</th>'
            f'</tr></thead><tbody>{rows}</tbody></table></div>'
        )

    is_section = _statement_table(
        "Income Statement",
        model.get("income_statement", model.get("is", [])),
    )
    bs_section = _statement_table(
        "Balance Sheet",
        model.get("balance_sheet", model.get("bs", [])),
    )
    cf_section = _statement_table(
        "Cash Flow Statement",
        model.get("cash_flow", model.get("cf", [])),
    )

    # Summary KPIs
    summary = model.get("summary", {})
    kpis = ""
    if summary:
        kpis = '<div class="cad-kpi-grid">'
        for k, v in list(summary.items())[:6]:
            kpis += (
                f'<div class="cad-kpi"><div class="cad-kpi-value">'
                f'{_fmt_m(v) if isinstance(v, (int, float)) and abs(float(v)) > 1000 else _fmt_pct(v) if isinstance(v, float) and abs(v) < 1 else html.escape(str(v))}'
                f'</div><div class="cad-kpi-label">{html.escape(k.replace("_", " ").title())}</div></div>'
            )
        kpis += '</div>'

    actions = (
        f'<div class="cad-card" style="display:flex;gap:8px;flex-wrap:wrap;">'
        f'<a href="/api/deals/{html.escape(deal_id)}/financials" class="cad-btn" '
        f'style="text-decoration:none;">Raw JSON</a>'
        f'<a href="/models/dcf/{html.escape(deal_id)}" class="cad-btn" '
        f'style="text-decoration:none;">DCF Model</a>'
        f'<a href="/models/lbo/{html.escape(deal_id)}" class="cad-btn" '
        f'style="text-decoration:none;">LBO Model</a>'
        f'<a href="/analysis/{html.escape(deal_id)}" class="cad-btn cad-btn-primary" '
        f'style="text-decoration:none;">Full Analysis</a></div>'
    )

    # Interpretation
    interp = (
        f'<div class="cad-card" style="border-left:3px solid {PALETTE["brand_accent"]};">'
        f'<h2>What This Means</h2>'
        f'<div style="font-size:12.5px;color:{PALETTE["text_secondary"]};line-height:1.7;">'
        f'<p>This 3-statement model reconstructs the hospital\'s income statement, balance sheet, '
        f'and cash flow from HCRIS cost report data. Each line item is tagged with its data source: '
        f'<span class="cad-badge cad-badge-green" style="font-size:9px;">HCRIS</span> (actual reported), '
        f'<span class="cad-badge cad-badge-blue" style="font-size:9px;">deal_profile</span> (user input), '
        f'<span class="cad-badge cad-badge-amber" style="font-size:9px;">benchmark</span> (industry estimate), '
        f'<span class="cad-badge cad-badge-muted" style="font-size:9px;">computed</span> (derived).</p>'
        f'<p style="margin-top:6px;">Use this to identify data quality: lines tagged "benchmark" are '
        f'estimates that should be validated during diligence. Request actual data for these items '
        f'via <a href="/models/questions/{html.escape(deal_id)}" style="color:{PALETTE["text_link"]};">'
        f'diligence questions</a>.</p>'
        f'</div></div>'
    )

    nav = _model_nav(deal_id, "financials")
    body = f'{nav}{kpis}{is_section}{bs_section}{interp}{cf_section}{actions}'
    return chartis_shell(body, f"Financials — {html.escape(deal_name)}",
                    active_nav="/analysis",
                    subtitle="3-statement model reconstructed from HCRIS + deal profile")
