"""SeekingChartis Verticals — ASC, Behavioral Health, MSO bridges.

Shows sub-sector capabilities beyond acute care hospitals.
"""
from __future__ import annotations

import html
from typing import Any, Dict, List

from .shell_v2 import shell_v2
from ..verticals.asc.ontology import ASC_METRIC_REGISTRY  # noqa: F401
from ..verticals.behavioral_health.ontology import BH_METRIC_REGISTRY  # noqa: F401
from ..verticals.mso.ontology import MSO_METRIC_REGISTRY  # noqa: F401
from .brand import PALETTE


def render_verticals() -> str:
    """Render the healthcare verticals overview."""

    verticals = [
        {
            "name": "Acute Care Hospitals",
            "icon": "&#127973;",
            "status": "Full Coverage",
            "status_cls": "cad-badge-green",
            "description": (
                "The core SeekingChartis capability. 6,000+ hospitals from HCRIS with "
                "complete financial profiles, market analysis, and diligence tools."
            ),
            "metrics": "38-metric registry: denial rate, AR days, net collection, clean claim rate, "
                       "cost to collect, payer mix, bed count, case mix index, occupancy, margins",
            "models": ["DCF", "LBO", "3-Statement", "EBITDA Bridge", "Denial Drivers",
                       "Market Moat", "Pressure Test", "Monte Carlo"],
            "link": "/market-data/map",
        },
        {
            "name": "Ambulatory Surgery Centers (ASC)",
            "icon": "&#129658;",
            "status": "Bridge Available",
            "status_cls": "cad-badge-blue",
            "description": (
                "ASC-specific value bridge with metrics adapted for outpatient surgery: "
                "case volume by specialty, net revenue per case, OR utilization, supply costs, "
                "and payer-specific reimbursement modeling."
            ),
            "metrics": "Case volume, revenue per case, OR utilization, supply cost ratio, "
                       "anesthesia hours, same-day discharge rate, infection rate",
            "models": ["ASC Value Bridge", "Case Mix Optimization", "Payer Renegotiation"],
            "link": "/library",
        },
        {
            "name": "Behavioral Health",
            "icon": "&#129504;",
            "status": "Bridge Available",
            "status_cls": "cad-badge-blue",
            "description": (
                "Behavioral health value bridge with inpatient/outpatient split, "
                "length of stay optimization, readmission reduction, and Medicaid-heavy "
                "payer mix modeling. Accounts for regulatory complexity."
            ),
            "metrics": "Avg length of stay, readmission rate, bed occupancy, staff-to-patient ratio, "
                       "Medicaid mix, prior auth denial rate, seclusion/restraint incidents",
            "models": ["BH Value Bridge", "LOS Optimization", "Workforce Planning"],
            "link": "/library",
        },
        {
            "name": "Management Service Organizations (MSO)",
            "icon": "&#128188;",
            "status": "Bridge Available",
            "status_cls": "cad-badge-blue",
            "description": (
                "MSO value bridge for physician practice management: revenue per provider, "
                "collections rate, coding accuracy across practices, referral network value, "
                "and centralization synergy modeling."
            ),
            "metrics": "Revenue per provider, collections rate, practice count, referral volume, "
                       "coding accuracy, payer contract leverage, centralization savings",
            "models": ["MSO Value Bridge", "Practice Consolidation", "Revenue Cycle Centralization"],
            "link": "/library",
        },
    ]

    cards = ""
    for v in verticals:
        model_badges = " ".join(
            f'<span class="cad-badge cad-badge-muted" style="font-size:10px;margin:1px;">'
            f'{html.escape(m)}</span>'
            for m in v["models"]
        )
        cards += (
            f'<div class="cad-card" style="border-left:3px solid {PALETTE["brand_accent"]};">'
            f'<div style="display:flex;justify-content:space-between;align-items:start;margin-bottom:8px;">'
            f'<div style="display:flex;gap:8px;align-items:center;">'
            f'<span style="font-size:24px;">{v["icon"]}</span>'
            f'<h2 style="margin:0;">{html.escape(v["name"])}</h2>'
            f'</div>'
            f'<span class="cad-badge {v["status_cls"]}">{v["status"]}</span>'
            f'</div>'
            f'<p style="font-size:12.5px;color:{PALETTE["text_secondary"]};line-height:1.6;margin-bottom:8px;">'
            f'{html.escape(v["description"])}</p>'
            f'<div style="font-size:11px;color:{PALETTE["text_muted"]};margin-bottom:8px;">'
            f'<strong>Key Metrics:</strong> {html.escape(v["metrics"])}</div>'
            f'<div style="margin-bottom:8px;">{model_badges}</div>'
            f'<div style="display:flex;gap:8px;">'
            f'<a href="{v["link"]}" class="cad-btn cad-btn-primary" style="text-decoration:none;font-size:12px;">'
            f'{"Screen Hospitals" if v["link"] == "/market-data/map" else "View in Library"}</a>'
            f'<a href="/screen" class="cad-btn" style="text-decoration:none;font-size:12px;">'
            f'Hospital Screener</a>'
            f'<a href="/import" class="cad-btn" style="text-decoration:none;font-size:12px;">'
            f'Import Deal</a>'
            f'</div>'
            f'</div>'
        )

    # Check which vertical bridges are loaded
    vert_status = {}
    for vert_name, vert_mod in [
        ("ASC", "rcm_mc.verticals.asc.bridge"),
        ("Behavioral Health", "rcm_mc.verticals.behavioral_health.bridge"),
        ("MSO", "rcm_mc.verticals.mso.bridge"),
    ]:
        try:
            __import__(vert_mod)
            vert_status[vert_name] = True
        except Exception:
            vert_status[vert_name] = False

    # Also check the vertical registry
    try:
        from ..verticals.registry import list_verticals
        registered = list_verticals()
    except Exception:
        registered = []

    # Build metric registry tables for each vertical
    registry_html = ""
    registries = [
        ("ASC Metric Registry", ASC_METRIC_REGISTRY),
        ("Behavioral Health Metric Registry", BH_METRIC_REGISTRY),
        ("MSO Metric Registry", MSO_METRIC_REGISTRY),
    ]
    for reg_name, reg in registries:
        if not reg:
            continue
        rows = ""
        for key, info in list(reg.items())[:10]:
            display = info.get("display_name", key.replace("_", " ").title())
            category = info.get("category", "")
            unit = info.get("unit", "")
            bench = info.get("benchmark_p50", "")
            rows += (
                f'<tr>'
                f'<td style="font-weight:500;">{html.escape(display)}</td>'
                f'<td><span class="cad-badge cad-badge-muted">{html.escape(category)}</span></td>'
                f'<td class="num">{html.escape(str(unit))}</td>'
                f'<td class="num">{bench}</td>'
                f'</tr>'
            )
        if rows:
            registry_html += (
                f'<div class="cad-card">'
                f'<h2>{html.escape(reg_name)} ({len(reg)} metrics)</h2>'
                f'<table class="cad-table"><thead><tr>'
                f'<th>Metric</th><th>Category</th><th>Unit</th><th>Benchmark P50</th>'
                f'</tr></thead><tbody>{rows}</tbody></table></div>'
            )

    body = (
        f'<div class="cad-card">'
        f'<p style="color:{PALETTE["text_secondary"]};font-size:12.5px;">'
        f'SeekingChartis supports multiple healthcare sub-sectors beyond acute care. '
        f'Each vertical has its own metric registry, value bridge model, and diligence framework.</p>'
        f'</div>'
        f'{cards}'
        f'{registry_html}'
    )

    return shell_v2(
        body, "Healthcare Verticals",
        subtitle="Acute Care, ASC, Behavioral Health, MSO",
    )
