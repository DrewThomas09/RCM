"""SeekingChartis Financial Models — browser-rendered DCF, LBO, 3-Statement.

Renders financial model outputs as rich HTML tables instead of raw JSON.
Accessed via /models/dcf/<deal_id>, /models/lbo/<deal_id>, /models/financials/<deal_id>.
"""
from __future__ import annotations

import html
from typing import Any, Dict, List, Optional

from .shell_v2 import shell_v2
from .brand import PALETTE


def _model_nav(deal_id: str, active: str = "") -> str:
    """Shared navigation bar for all model pages."""
    did = html.escape(deal_id)
    links = [
        ("Profile", f"/hospital/{did}", "profile"),
        ("IC Memo", f"/ic-memo/{did}", "ic_memo"),
        ("EBITDA Bridge", f"/ebitda-bridge/{did}", "ebitda_bridge"),
        ("Comp Intel", f"/competitive-intel/{did}", "comp_intel"),
        ("Scenarios", f"/scenarios/{did}", "scenarios"),
        ("ML", f"/ml-insights/hospital/{did}", "ml"),
        ("DCF", f"/models/dcf/{did}", "dcf"),
        ("LBO", f"/models/lbo/{did}", "lbo"),
        ("3-Statement", f"/models/financials/{did}", "financials"),
        ("Market", f"/models/market/{did}", "market"),
        ("Denial", f"/models/denial/{did}", "denial"),
        ("Returns", f"/models/returns/{did}", "returns"),
        ("Bridge", f"/models/bridge/{did}", "bridge"),
        ("Waterfall", f"/models/waterfall/{did}", "waterfall"),
        ("Playbook", f"/models/playbook/{did}", "playbook"),
        ("Trends", f"/models/trends/{did}", "trends"),
        ("Predicted", f"/models/predicted/{did}", "predicted"),
        ("Memo", f"/models/memo/{did}", "memo"),
    ]
    items = ""
    for label, href, key in links:
        style = (
            f'background:{PALETTE["brand_accent"]};color:white;border-color:{PALETTE["brand_accent"]};'
            if key == active else ""
        )
        items += (
            f'<a href="{href}" class="cad-btn" '
            f'style="text-decoration:none;font-size:11px;padding:5px 10px;{style}">{label}</a>'
        )
    return (
        f'<div style="display:flex;gap:6px;flex-wrap:wrap;margin-bottom:16px;'
        f'padding-bottom:12px;border-bottom:1px solid {PALETTE["border"]};">'
        f'<a href="/deal/{did}" class="cad-btn cad-btn-primary" '
        f'style="text-decoration:none;font-size:11px;padding:5px 10px;">Dashboard</a>'
        f'{items}</div>'
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


def _fmt_pct(val: Any) -> str:
    if val is None:
        return "—"
    try:
        v = float(val)
        if abs(v) < 1:
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
        f'<h2>Cash Flow Projections</h2>'
        f'<table class="cad-table"><thead><tr>'
        f'<th>Year</th><th>Revenue</th><th>EBITDA</th>'
        f'<th>Margin</th><th>FCF</th><th>PV(FCF)</th>'
        f'</tr></thead><tbody>{proj_rows}</tbody></table></div>'
    ) if proj_rows else ""

    # Sensitivity matrix
    sensitivity = dcf.get("sensitivity", {})
    sens_html = ""
    if sensitivity:
        matrix = sensitivity.get("wacc_x_growth", sensitivity.get("matrix", []))
        if isinstance(matrix, list) and matrix:
            rows_h = ""
            for row in matrix[:8]:
                cells = ""
                for cell in (row.get("values", []) if isinstance(row, dict) else []):
                    v = cell.get("ev", cell.get("value", 0)) if isinstance(cell, dict) else cell
                    cells += f'<td class="num">{_fmt_m(v)}</td>'
                label = row.get("wacc", row.get("label", "")) if isinstance(row, dict) else ""
                rows_h += f'<tr><td class="num" style="font-weight:600;">{_fmt_pct(label)}</td>{cells}</tr>'

            sens_html = (
                f'<div class="cad-card">'
                f'<h2>Sensitivity: WACC x Terminal Growth</h2>'
                f'<p style="font-size:12px;color:{PALETTE["text_secondary"]};margin-bottom:8px;">'
                f'Enterprise value under different WACC and terminal growth rate combinations.</p>'
                f'<table class="cad-table"><thead><tr><th>WACC ↓ / Growth →</th>'
                f'</tr></thead><tbody>{rows_h}</tbody></table></div>'
            )

    # Assumptions
    assume_items = ""
    for k, v in assumptions.items():
        if k in ("wacc", "terminal_growth"):
            continue
        assume_items += (
            f'<div style="display:flex;justify-content:space-between;padding:4px 0;'
            f'border-bottom:1px solid {PALETTE["border"]};">'
            f'<span style="color:{PALETTE["text_secondary"]};">'
            f'{html.escape(k.replace("_", " ").title())}</span>'
            f'<span class="cad-mono">{_fmt_m(v) if isinstance(v, (int, float)) and abs(float(v)) > 1000 else html.escape(str(v))}</span>'
            f'</div>'
        )
    assume_section = (
        f'<div class="cad-card">'
        f'<h2>Assumptions</h2>'
        f'<div style="font-size:12.5px;">{assume_items}</div></div>'
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
        f'<h2>What This Means</h2>'
        f'<div style="font-size:12.5px;color:{PALETTE["text_secondary"]};line-height:1.7;">'
        f'<p>At a WACC of {wacc:.1%} and terminal growth of {growth:.1%}, '
        f'this hospital\'s enterprise value is <strong>{_fmt_m(ev)}</strong>. '
        f'Terminal value accounts for {tv_pct:.0f}% of total EV — '
        f'{"this is typical (60-80%)" if 55 < tv_pct < 85 else "consider sensitivity to terminal assumptions"}.</p>'
        f'<p style="margin-top:6px;"><strong>Next steps:</strong> '
        f'Check the <a href="/models/lbo/{html.escape(deal_id)}" style="color:{PALETTE["text_link"]};">LBO model</a> '
        f'to see equity returns at this entry price, or the '
        f'<a href="/models/bridge/{html.escape(deal_id)}" style="color:{PALETTE["text_link"]};">EBITDA bridge</a> '
        f'to model value creation levers.</p>'
        f'</div></div>'
    )

    nav = _model_nav(deal_id, "dcf")
    body = f'{nav}{kpis}{proj_table}{interp}{sens_html}{assume_section}{actions}'
    return shell_v2(body, f"DCF — {html.escape(deal_name)}",
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
        f'{_fmt_pct(irr)}</div>'
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
        su_rows = ""
        for k, v in sources.items():
            if k == "total_sources":
                continue
            su_rows += (
                f'<tr><td>{html.escape(k.replace("_", " ").title())}</td>'
                f'<td class="num">{_fmt_m(v)}</td></tr>'
            )
        su_html = (
            f'<div class="cad-card">'
            f'<h2>Sources &amp; Uses</h2>'
            f'<table class="cad-table"><thead><tr>'
            f'<th>Item</th><th>Amount</th>'
            f'</tr></thead><tbody>{su_rows}</tbody></table></div>'
        )

    # Annual projections
    annual_html = ""
    if annual:
        ann_rows = ""
        for yr in annual[:7]:
            ann_rows += (
                f'<tr>'
                f'<td class="num" style="font-weight:600;">Year {yr.get("year", "")}</td>'
                f'<td class="num">{_fmt_m(yr.get("revenue"))}</td>'
                f'<td class="num">{_fmt_m(yr.get("ebitda"))}</td>'
                f'<td class="num">{_fmt_m(yr.get("debt_balance") or yr.get("total_debt"))}</td>'
                f'<td class="num">{_fmt_m(yr.get("interest_expense") or yr.get("interest"))}</td>'
                f'<td class="num">{_fmt_x(yr.get("leverage") or yr.get("net_debt_ebitda"))}</td>'
                f'</tr>'
            )
        annual_html = (
            f'<div class="cad-card">'
            f'<h2>Annual Projections</h2>'
            f'<table class="cad-table"><thead><tr>'
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
                f'<tr><td>{html.escape(k.replace("_", " ").title())}</td>'
                f'<td class="num">{_fmt_m(v) if isinstance(v, (int, float)) and abs(float(v)) > 1000 else _fmt_pct(v) if isinstance(v, float) and abs(v) < 10 else html.escape(str(v))}</td></tr>'
            )
        waterfall_html = (
            f'<div class="cad-card">'
            f'<h2>Returns Waterfall</h2>'
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
        f'<h2>What This Means</h2>'
        f'<div style="font-size:12.5px;color:{PALETTE["text_secondary"]};line-height:1.7;">'
        f'<p>At {_fmt_x(moic)} MOIC and {_fmt_pct(irr)} IRR over {hold_years:.0f} years, '
        f'this deal {irr_assessment}.</p>'
        f'<p style="margin-top:6px;"><strong>Key drivers:</strong> '
        f'Check the <a href="/models/bridge/{html.escape(deal_id)}" style="color:{PALETTE["text_link"]};">EBITDA bridge</a> '
        f'to identify the highest-probability value levers, and the '
        f'<a href="/models/debt/{html.escape(deal_id)}" style="color:{PALETTE["text_link"]};">debt schedule</a> '
        f'for the leverage trajectory. Use the '
        f'<a href="/models/challenge/{html.escape(deal_id)}" style="color:{PALETTE["text_link"]};">challenge solver</a> '
        f'to see what breaks the deal.</p>'
        f'</div></div>'
    )

    nav = _model_nav(deal_id, "lbo")
    body = f'{nav}{kpis}{su_html}{annual_html}{interp}{waterfall_html}{actions}'
    return shell_v2(body, f"LBO — {html.escape(deal_name)}",
                    active_nav="/analysis",
                    subtitle=f"IRR: {_fmt_pct(irr)} | MOIC: {_fmt_x(moic)}")


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
    return shell_v2(body, f"Financials — {html.escape(deal_name)}",
                    active_nav="/analysis",
                    subtitle="3-statement model reconstructed from HCRIS + deal profile")
