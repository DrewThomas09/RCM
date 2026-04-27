"""SeekingChartis Portfolio Overview — unified portfolio intelligence page.

Replaces the heatmap as the default portfolio view with a comprehensive
overview: KPI summary, health distribution, deal table with inline
sparklines, regression insights, and export links.
"""
from __future__ import annotations

import html
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from ._chartis_kit import chartis_shell
from ._glossary_link import metric_label_link
from ._provenance_tooltip import provenance_tooltip
from ..provenance.graph import NodeType, ProvenanceGraph, ProvenanceNode
from .brand import PALETTE


# Phase 4A: portfolio-overview label → glossary-key reverse map.
# Three KPI cards and two table column headers reference RCM
# metrics that have canonical /metric-glossary entries.
_LABEL_TO_GLOSSARY_KEY = {
    "Avg Denial Rate":   "denial_rate",
    "Avg Days in AR":    "days_in_ar",
    "Avg Net Collection": "net_collection_rate",
    "Total Net Revenue": "net_patient_revenue",
    "Denial":            "denial_rate",
    "AR":                "days_in_ar",
    "NPR":               "net_patient_revenue",
}


def _health_badge(score: float) -> str:
    if score >= 70:
        return f'<span class="cad-badge cad-badge-green">{score:.0f}</span>'
    if score >= 40:
        return f'<span class="cad-badge cad-badge-amber">{score:.0f}</span>'
    return f'<span class="cad-badge cad-badge-red">{score:.0f}</span>'


def _sparkline_svg(values: List[float], width: int = 60, height: int = 20) -> str:
    """Tiny inline SVG sparkline."""
    if not values or len(values) < 2:
        return ""
    mn, mx = min(values), max(values)
    rng = mx - mn if mx != mn else 1
    points = []
    for i, v in enumerate(values):
        x = i / (len(values) - 1) * width
        y = height - ((v - mn) / rng) * height
        points.append(f"{x:.1f},{y:.1f}")
    poly = " ".join(points)
    color = PALETTE["positive"] if values[-1] >= values[0] else PALETTE["negative"]
    return (
        f'<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}" '
        f'style="vertical-align:middle;">'
        f'<polyline points="{poly}" fill="none" stroke="{color}" stroke-width="1.5"/>'
        f'</svg>'
    )


def _fmt_money(val: Any, scale: float = 1e6) -> str:
    if val is None:
        return "—"
    try:
        v = float(val) / scale
        return f"${v:,.0f}M"
    except (TypeError, ValueError):
        return "—"


def _fmt_pct(val: Any) -> str:
    if val is None:
        return "—"
    try:
        return f"{float(val):.1f}%"
    except (TypeError, ValueError):
        return "—"


def _compute_regression(deals: pd.DataFrame) -> str:
    """Mini regression: what drives denial rates across the portfolio?"""
    if len(deals) < 4:
        return ""

    target = "denial_rate"
    features = ["days_in_ar", "net_collection_rate", "clean_claim_rate", "cost_to_collect"]
    available = [f for f in features if f in deals.columns and deals[f].notna().sum() >= 3]

    if not available or target not in deals.columns or deals[target].notna().sum() < 3:
        return ""

    try:
        df = deals.dropna(subset=[target] + available)
        if len(df) < 3:
            return ""

        X = df[available].fillna(0).values.astype(float)
        y = df[target].fillna(0).values.astype(float)

        X_mean = X.mean(axis=0)
        X_std = X.std(axis=0)
        X_std[X_std == 0] = 1
        X_norm = (X - X_mean) / X_std
        X_aug = np.column_stack([np.ones(len(X_norm)), X_norm])

        beta = np.linalg.lstsq(X_aug, y, rcond=None)[0]
        y_hat = X_aug @ beta
        ss_res = np.sum((y - y_hat) ** 2)
        ss_tot = np.sum((y - y.mean()) ** 2)
        r2 = 1 - ss_res / ss_tot if ss_tot > 0 else 0

        rows = ""
        for i, feat in enumerate(available):
            coef = beta[i + 1]
            color = PALETTE["negative"] if coef > 0 else PALETTE["positive"]
            sign = "+" if coef > 0 else ""
            bar_w = min(100, abs(coef) / max(abs(beta[1:]).max(), 0.001) * 100)
            rows += (
                f'<tr>'
                f'<td>{html.escape(feat.replace("_", " ").title())}</td>'
                f'<td class="num" style="color:{color};">{sign}{coef:.3f}</td>'
                f'<td><div style="background:{PALETTE["bg_tertiary"]};border-radius:4px;height:8px;">'
                f'<div style="width:{bar_w:.0f}%;background:{color};'
                f'border-radius:4px;height:8px;"></div></div></td>'
                f'</tr>'
            )

        return (
            f'<div class="cad-card">'
            f'<div style="display:flex;align-items:center;gap:10px;margin-bottom:10px;">'
            f'<h2 style="margin:0;">Denial Rate Drivers</h2>'
            f'<span class="cad-section-code">REG</span></div>'
            f'<div style="display:flex;gap:12px;margin-bottom:12px;">'
            f'<div class="cad-kpi" style="flex:1;">'
            f'<div class="cad-kpi-value">{r2:.0%}</div>'
            f'<div class="cad-kpi-label">R-Squared</div></div>'
            f'<div class="cad-kpi" style="flex:1;">'
            f'<div class="cad-kpi-value">{len(df)}</div>'
            f'<div class="cad-kpi-label">Deals Analyzed</div></div>'
            f'</div>'
            f'<p style="font-size:12px;color:{PALETTE["text_secondary"]};margin-bottom:10px;">'
            f'Standardized OLS coefficients. Positive = increases denial rate (bad).</p>'
            f'<table class="cad-table"><thead><tr>'
            f'<th>Variable</th><th>Coefficient</th><th>Impact</th>'
            f'</tr></thead><tbody>{rows}</tbody></table></div>'
        )
    except Exception:
        return ""


def render_portfolio_overview(
    deals: pd.DataFrame,
    store: Any = None,
) -> str:
    """Render the portfolio overview page."""

    n = len(deals)

    if n == 0:
        empty = (
            f'<div class="cad-card" style="text-align:center;padding:40px;">'
            f'<h2 style="font-size:18px;margin-bottom:12px;">No Deals in Portfolio</h2>'
            f'<p style="color:{PALETTE["text_secondary"]};margin-bottom:16px;">'
            f'Create deals to see portfolio analytics, health scores, and regression insights.</p>'
            f'<div style="display:flex;gap:12px;justify-content:center;">'
            f'<a href="/import" class="cad-btn cad-btn-primary" style="text-decoration:none;">'
            f'+ New Deal</a>'
            f'<a href="/screen" class="cad-btn" style="text-decoration:none;">Screen Hospitals</a>'
            f'<a href="/market-data/map" class="cad-btn" style="text-decoration:none;">'
            f'Market Data</a></div></div>'
        )
        return chartis_shell(empty, "Portfolio", active_nav="/portfolio",
                        subtitle="No deals yet")

    # KPI summary
    avg_denial = deals["denial_rate"].dropna().mean() if "denial_rate" in deals.columns else None
    avg_ar = deals["days_in_ar"].dropna().mean() if "days_in_ar" in deals.columns else None
    total_rev = deals["net_revenue"].dropna().sum() if "net_revenue" in deals.columns else None
    avg_ncr = deals["net_collection_rate"].dropna().mean() if "net_collection_rate" in deals.columns else None

    # Phase 4C: build a portfolio-level provenance graph by hand —
    # build_provenance_graph is per-deal HCRIS-shaped so it isn't
    # the right constructor here. Each KPI is an AGGREGATED node
    # (cohort mean / sum across deals) keyed at observed:<metric>
    # so the explainer's resolver finds it. Only nodes whose KPI
    # has a real (non-None) value get added — the helper falls
    # through to plain text for KPIs that show "—".
    prov_graph = ProvenanceGraph()
    if total_rev is not None and total_rev > 0:
        prov_graph.add_node(ProvenanceNode(
            id="observed:net_patient_revenue",
            label="Total Net Revenue (Portfolio Sum)",
            node_type=NodeType.AGGREGATED,
            value=float(total_rev), unit="USD",
            source="PORTFOLIO",
            source_detail=f"sum across {n} deal(s)",
        ))
    if avg_denial is not None:
        prov_graph.add_node(ProvenanceNode(
            id="observed:denial_rate",
            label="Avg Denial Rate (Portfolio Mean)",
            node_type=NodeType.AGGREGATED,
            value=float(avg_denial), unit="pct",
            source="PORTFOLIO",
            source_detail=f"mean across {n} deal(s)",
        ))
    if avg_ar is not None:
        prov_graph.add_node(ProvenanceNode(
            id="observed:days_in_ar",
            label="Avg Days in AR (Portfolio Mean)",
            node_type=NodeType.AGGREGATED,
            value=float(avg_ar), unit="days",
            source="PORTFOLIO",
            source_detail=f"mean across {n} deal(s)",
        ))
    if avg_ncr is not None:
        prov_graph.add_node(ProvenanceNode(
            id="observed:net_collection_rate",
            label="Avg Net Collection Rate (Portfolio Mean)",
            node_type=NodeType.AGGREGATED,
            value=float(avg_ncr), unit="pct",
            source="PORTFOLIO",
            source_detail=f"mean across {n} deal(s)",
        ))

    kpis = (
        f'<div class="cad-kpi-grid">'
        f'<div class="cad-kpi"><div class="cad-kpi-value">{n}</div>'
        f'<div class="cad-kpi-label">Active Deals</div></div>'
        f'<div class="cad-kpi"><div class="cad-kpi-value">'
        f'{provenance_tooltip(label="Total Net Revenue", value=(_fmt_money(total_rev) if total_rev else "—"), graph=prov_graph, metric_key="net_patient_revenue")}</div>'
        f'<div class="cad-kpi-label">{metric_label_link("Total Net Revenue", _LABEL_TO_GLOSSARY_KEY["Total Net Revenue"])}</div></div>'
        f'<div class="cad-kpi"><div class="cad-kpi-value">'
        f'{provenance_tooltip(label="Avg Denial Rate", value=(_fmt_pct(avg_denial) if avg_denial else "—"), graph=prov_graph, metric_key="denial_rate", inject_css=False)}</div>'
        f'<div class="cad-kpi-label">{metric_label_link("Avg Denial Rate", _LABEL_TO_GLOSSARY_KEY["Avg Denial Rate"])}</div></div>'
        f'<div class="cad-kpi"><div class="cad-kpi-value">'
        f'{provenance_tooltip(label="Avg Days in AR", value=(f"{avg_ar:.0f}" if avg_ar else "—"), graph=prov_graph, metric_key="days_in_ar", inject_css=False)}'
        f'</div><div class="cad-kpi-label">{metric_label_link("Avg Days in AR", _LABEL_TO_GLOSSARY_KEY["Avg Days in AR"])}</div></div>'
        f'<div class="cad-kpi"><div class="cad-kpi-value">'
        f'{provenance_tooltip(label="Avg Net Collection", value=(_fmt_pct(avg_ncr) if avg_ncr else "—"), graph=prov_graph, metric_key="net_collection_rate", inject_css=False)}</div>'
        f'<div class="cad-kpi-label">{metric_label_link("Avg Net Collection", _LABEL_TO_GLOSSARY_KEY["Avg Net Collection"])}</div></div>'
        f'</div>'
    )

    # Health distribution
    health_counts = {"green": 0, "amber": 0, "red": 0}
    if "health_score" in deals.columns:
        for _, d in deals.iterrows():
            hs = d.get("health_score")
            if hs is not None:
                try:
                    s = float(hs)
                    if s >= 70:
                        health_counts["green"] += 1
                    elif s >= 40:
                        health_counts["amber"] += 1
                    else:
                        health_counts["red"] += 1
                except (TypeError, ValueError):
                    pass

    total_health = sum(health_counts.values())
    health_bar = ""
    if total_health > 0:
        gp = health_counts["green"] / total_health * 100
        ap = health_counts["amber"] / total_health * 100
        rp = health_counts["red"] / total_health * 100
        health_bar = (
            f'<div class="cad-card">'
            f'<div style="display:flex;align-items:center;gap:10px;margin-bottom:10px;">'
            f'<h2 style="margin:0;">Health Distribution</h2>'
            f'<span class="cad-section-code">HLTH</span>'
            f'<span style="font-family:var(--cad-mono);font-size:10px;'
            f'letter-spacing:0.08em;color:{PALETTE["text_muted"]};'
            f'text-transform:uppercase;margin-left:auto;">N = {total_health}</span>'
            f'</div>'
            f'<div style="display:flex;gap:0;height:14px;overflow:hidden;margin-bottom:8px;'
            f'border:1px solid {PALETTE["border"]};">'
            f'<div style="width:{gp:.0f}%;background:{PALETTE["positive"]};" title="Green: {health_counts["green"]}"></div>'
            f'<div style="width:{ap:.0f}%;background:{PALETTE["warning"]};" title="Amber: {health_counts["amber"]}"></div>'
            f'<div style="width:{rp:.0f}%;background:{PALETTE["negative"]};" title="Red: {health_counts["red"]}"></div>'
            f'</div>'
            f'<div style="display:flex;gap:20px;font-family:var(--cad-mono);font-size:10.5px;'
            f'letter-spacing:0.06em;text-transform:uppercase;">'
            f'<span style="color:{PALETTE["positive"]};">&#9632; GREEN · {health_counts["green"]} ({gp:.0f}%)</span>'
            f'<span style="color:{PALETTE["warning"]};">&#9632; AMBER · {health_counts["amber"]} ({ap:.0f}%)</span>'
            f'<span style="color:{PALETTE["negative"]};">&#9632; RED · {health_counts["red"]} ({rp:.0f}%)</span>'
            f'</div></div>'
        )

    # Deal table with vs-average comparison
    avg_dr_val = avg_denial if avg_denial else 12
    avg_ar_val = avg_ar if avg_ar else 48
    rows = ""
    for _, d in deals.head(30).iterrows():
        did = html.escape(str(d.get("deal_id", "")))
        if not did:
            continue
        name = html.escape(str(d.get("name", did)))
        stage = html.escape(str(d.get("stage", "pipeline")))
        dr = d.get("denial_rate")
        ar = d.get("days_in_ar")
        rev = d.get("net_revenue")

        dr_color = PALETTE["negative"] if dr and float(dr) > 15 else (
            PALETTE["warning"] if dr and float(dr) > 12 else PALETTE["positive"]
        ) if dr else PALETTE["text_muted"]

        # vs-average delta
        dr_delta = ""
        if dr is not None and avg_dr_val:
            diff = float(dr) - avg_dr_val
            dc = PALETTE["negative"] if diff > 0 else PALETTE["positive"]
            dr_delta = f' <span style="font-size:10px;color:{dc};">({diff:+.1f})</span>'

        ar_str = f'{float(ar):.0f}' if ar else "—"
        ar_delta = ""
        if ar is not None and avg_ar_val:
            diff = float(ar) - avg_ar_val
            dc = PALETTE["negative"] if diff > 0 else PALETTE["positive"]
            ar_delta = f' <span style="font-size:10px;color:{dc};">({diff:+.0f})</span>'

        rows += (
            f'<tr>'
            f'<td><a href="/deal/{did}" class="cad-ticker-id" style="text-decoration:none;">{did}</a></td>'
            f'<td><a href="/deal/{did}" style="font-weight:600;color:{PALETTE["text_primary"]};text-decoration:none;">{name}</a></td>'
            f'<td><span class="cad-badge cad-badge-muted">{stage}</span></td>'
            f'<td class="num" style="color:{dr_color};font-weight:600;">{_fmt_pct(dr)}{dr_delta}</td>'
            f'<td class="num">{ar_str}{ar_delta}</td>'
            f'<td class="num">{_fmt_money(rev)}</td>'
            f'<td style="white-space:nowrap;">'
            f'<a href="/deal/{did}" class="cad-badge cad-badge-blue" '
            f'style="text-decoration:none;">DASH</a> '
            f'<a href="/models/dcf/{did}" class="cad-badge cad-badge-muted" '
            f'style="text-decoration:none;">DCF</a> '
            f'<a href="/models/bridge/{did}" class="cad-badge cad-badge-muted" '
            f'style="text-decoration:none;">BRG</a>'
            f'</td></tr>'
        )

    table = (
        f'<div class="cad-card cad-table-sticky">'
        f'<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;">'
        f'<div style="display:flex;align-items:center;gap:10px;">'
        f'<h2 style="margin:0;">All Deals ({n})</h2>'
        f'<span class="cad-section-code">DLS</span></div>'
        f'<div style="display:flex;gap:6px;">'
        f'<a href="/api/export/portfolio.csv" class="cad-btn" style="text-decoration:none;">Export CSV</a>'
        f'<a href="/import" class="cad-btn cad-btn-primary" style="text-decoration:none;">+ New Deal</a>'
        f'</div></div>'
        f'<table class="cad-table crosshair"><thead><tr>'
        f'<th>ID</th><th>Name</th><th>Stage</th>'
        f'<th>{metric_label_link("Denial", _LABEL_TO_GLOSSARY_KEY["Denial"])}</th>'
        f'<th>{metric_label_link("AR", _LABEL_TO_GLOSSARY_KEY["AR"])}</th>'
        f'<th>{metric_label_link("NPR", _LABEL_TO_GLOSSARY_KEY["NPR"])}</th>'
        f'<th>Actions</th></tr></thead>'
        f'<tbody>{rows}</tbody></table></div>'
    )

    # Regression
    regression = _compute_regression(deals)

    # Opportunity summary — how much value is sitting in the portfolio
    total_rev = deals["net_revenue"].dropna().sum() if "net_revenue" in deals.columns else 0
    avg_dr = deals["denial_rate"].dropna().mean() if "denial_rate" in deals.columns else 0
    recoverable = 0
    if avg_dr and avg_dr > 8 and total_rev:
        recoverable = total_rev * (avg_dr - 8) / 100 * 0.3

    opportunity = ""
    if recoverable > 0:
        opportunity = (
            f'<div class="cad-card" style="border-left:3px solid {PALETTE["positive"]};">'
            f'<div style="display:flex;align-items:center;gap:10px;margin-bottom:10px;">'
            f'<h2 style="margin:0;">Portfolio Value Opportunity</h2>'
            f'<span class="cad-section-code" style="color:{PALETTE["positive"]};">OPP</span></div>'
            f'<div style="display:flex;gap:24px;align-items:center;">'
            f'<div style="min-width:170px;">'
            f'<div class="cad-kpi-value" style="color:{PALETTE["positive"]};font-size:24px;">'
            f'${recoverable/1e6:.1f}M</div>'
            f'<div class="cad-kpi-label">Recoverable Revenue</div></div>'
            f'<div style="flex:1;font-size:12px;color:{PALETTE["text_secondary"]};line-height:1.6;">'
            f'Reducing portfolio avg denial rate from <strong>{avg_dr:.1f}%</strong> to the '
            f'<strong>8%</strong> industry target. Assumes 30% of excess denials recoverable through '
            f'prior authorization, coding accuracy, and payer renegotiation.</div>'
            f'</div></div>'
        )

    # Cross-deal synergy estimate
    synergy_section = ""
    if n >= 2 and total_rev and total_rev > 0:
        rcm_cost_base = total_rev * 0.06
        synergy_pct = min(0.25, 0.08 + 0.03 * (n - 2))
        synergy_ebitda = rcm_cost_base * synergy_pct
        synergy_section = (
            f'<div class="cad-card" style="border-left:3px solid {PALETTE["brand_accent"]};">'
            f'<div style="display:flex;align-items:center;gap:10px;margin-bottom:10px;">'
            f'<h2 style="margin:0;">Cross-Deal RCM Synergy</h2>'
            f'<span class="cad-section-code" style="color:{PALETTE["brand_accent"]};">SYN</span></div>'
            f'<div style="display:flex;gap:24px;align-items:center;">'
            f'<div style="min-width:170px;">'
            f'<div class="cad-kpi-value" style="color:{PALETTE["brand_accent"]};font-size:24px;">'
            f'${synergy_ebitda/1e6:.1f}M</div>'
            f'<div class="cad-kpi-label">Annual Synergy EBITDA</div></div>'
            f'<div style="flex:1;font-size:12px;color:{PALETTE["text_secondary"]};line-height:1.6;">'
            f'Shared-services model: <strong>{n}</strong> platforms × '
            f'<strong>${rcm_cost_base/1e6:.0f}M</strong> RCM cost base × '
            f'<strong>{synergy_pct:.0%}</strong> savings from coding centralization, '
            f'shared denial management, payer contract leverage. '
            f'At 11x = <strong>${synergy_ebitda * 11/1e6:.0f}M</strong> equity value.</div>'
            f'</div></div>'
        )

    # Navigation — dense Bloomberg tile grid
    deal_ids = ",".join(html.escape(str(d.get("deal_id", ""))) for _, d in deals.head(3).iterrows())
    nav_tiles = [
        ("REG", "/portfolio/regression", "Regression", "Denial rate drivers"),
        ("CMP", f"/compare?deals={deal_ids}", "Compare Deals", "Side-by-side radar"),
        ("MAP", "/market-data/map", "Market Heatmap", "National drill-down"),
        ("SCR", "/screen?preset=turnaround", "Find More Deals", "HCRIS turnaround screen"),
        ("CSV", "/api/export/portfolio.csv", "Export CSV", "Portfolio download"),
        ("SCN", "/scenarios", "Scenarios", "Rate & volume shocks"),
    ]
    tiles_html = "".join(
        f'<a href="{href}" class="cad-ptile">'
        f'<div class="cad-ptile-code">{code}</div>'
        f'<div class="cad-ptile-title">{html.escape(title)}</div>'
        f'<div class="cad-ptile-desc">{html.escape(desc)}</div></a>'
        for code, href, title, desc in nav_tiles
    )
    nav_links = (
        f'<style>.cad-ptile{{display:block;padding:10px 14px;background:var(--ck-panel);'
        f'border-right:1px solid {PALETTE["border"]};border-bottom:1px solid {PALETTE["border"]};'
        f'text-decoration:none;color:inherit;transition:background 0.1s;}}'
        f'.cad-ptile:hover{{background:{PALETTE["bg_tertiary"]};}}'
        f'.cad-ptile:hover .cad-ptile-code{{color:{PALETTE["accent_amber"]};}}'
        f'.cad-ptile:hover .cad-ptile-title{{color:{PALETTE["accent_amber"]};}}'
        f'.cad-ptile-code{{font-family:var(--cad-mono);font-size:9px;font-weight:700;'
        f'letter-spacing:0.18em;color:{PALETTE["text_muted"]};margin-bottom:4px;}}'
        f'.cad-ptile-title{{font-size:12.5px;font-weight:600;color:{PALETTE["text_primary"]};'
        f'letter-spacing:0.02em;margin-bottom:2px;text-transform:uppercase;}}'
        f'.cad-ptile-desc{{font-size:10.5px;color:{PALETTE["text_muted"]};'
        f'font-family:var(--cad-mono);letter-spacing:0.01em;}}</style>'
        f'<div class="cad-card" style="margin-bottom:0;padding:8px 14px;">'
        f'<div style="display:flex;align-items:center;gap:10px;">'
        f'<h2 style="margin:0;">Portfolio Tools</h2>'
        f'<span class="cad-section-code">NAV</span></div></div>'
        f'<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:0;'
        f'border-top:1px solid {PALETTE["border"]};border-left:1px solid {PALETTE["border"]};">'
        f'{tiles_html}</div>'
    )

    # Editorial section header — eyebrow + serif h2 + lede.
    deals_label = f"{n} active deal" + ("s" if n != 1 else "")
    page_head = (
        '<div class="sect">'
        '<div>'
        '<div class="micro">PORTFOLIO &nbsp;·&nbsp; OVERVIEW</div>'
        '<h2>Active deals,<br/><em>at a glance</em>.</h2>'
        '</div>'
        '<p class="desc">'
        f'{deals_label} across the fund. KPI roll-ups across denial / DAR / '
        'collection rate, health distribution, opportunity ranking, and '
        'cross-portfolio synergy signals — every value linked to the deal '
        'page that owns it.'
        '</p>'
        '</div>'
    )

    body = f'{page_head}{kpis}{health_bar}{opportunity}{synergy_section}{table}{regression}{nav_links}'

    return chartis_shell(
        body, "Portfolio",
        active_nav="/portfolio",
        subtitle=f"{deals_label} — portfolio analytics & intelligence",
    )
