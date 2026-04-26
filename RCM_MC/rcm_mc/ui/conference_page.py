"""SeekingChartis Conference Roadmap — healthcare PE events calendar.

Curated calendar of healthcare investment conferences, PE summits, and
industry events relevant to hospital M&A diligence teams.
"""
from __future__ import annotations

import html as _html
import urllib.parse as _urlparse
from typing import Any, Dict, List, Optional

from ._chartis_kit import chartis_shell
from .brand import PALETTE

CONFERENCES = [
    {
        "name": "J.P. Morgan Healthcare Conference",
        "date": "2027-01-12",
        "end_date": "2027-01-15",
        "location": "San Francisco, CA",
        "category": "Investment",
        "tier": "flagship",
        "description": (
            "The largest and most informative healthcare investment symposium in "
            "the industry. 450+ presenting companies, 9,000+ attendees. Essential "
            "for PE deal sourcing and management meetings."
        ),
        "relevance": "Deal sourcing, management meetings, market intelligence",
        "url": "",
    },
    {
        "name": "HIMSS Global Health Conference",
        "date": "2027-03-03",
        "end_date": "2027-03-06",
        "location": "Las Vegas, NV",
        "category": "Health IT",
        "tier": "flagship",
        "description": (
            "Premier health IT event. 45,000+ attendees across health systems, "
            "payers, and vendors. Key for understanding technology transformation "
            "in target hospitals and RCM vendor landscape."
        ),
        "relevance": "RCM technology assessment, vendor diligence, digital transformation",
        "url": "",
    },
    {
        "name": "Becker's Hospital Review Annual Meeting",
        "date": "2027-04-07",
        "end_date": "2027-04-10",
        "location": "Chicago, IL",
        "category": "Operations",
        "tier": "major",
        "description": (
            "2,500+ hospital and health system leaders. Tracks on finance, "
            "operations, and strategy. Strong for understanding operator "
            "perspectives on M&A and value creation."
        ),
        "relevance": "Operator perspectives, M&A sentiment, operational best practices",
        "url": "",
    },
    {
        "name": "Healthcare Private Equity Association Summit",
        "date": "2027-02-24",
        "end_date": "2027-02-25",
        "location": "New York, NY",
        "category": "PE/M&A",
        "tier": "flagship",
        "description": (
            "The premier PE-specific healthcare event. LPs, GPs, and advisors "
            "discuss deal structures, regulatory outlook, and sector opportunities. "
            "High-density networking for deal origination."
        ),
        "relevance": "LP/GP networking, deal structuring, regulatory outlook",
        "url": "",
    },
    {
        "name": "AHA Annual Membership Meeting",
        "date": "2027-05-04",
        "end_date": "2027-05-06",
        "location": "Washington, DC",
        "category": "Policy",
        "tier": "major",
        "description": (
            "American Hospital Association annual gathering. Policy-focused — "
            "Medicare/Medicaid reimbursement outlook, regulatory priorities, "
            "workforce challenges. Essential for understanding policy headwinds."
        ),
        "relevance": "Reimbursement outlook, regulatory risk, policy headwinds",
        "url": "",
    },
    {
        "name": "HFMA Annual Conference",
        "date": "2027-06-22",
        "end_date": "2027-06-25",
        "location": "Nashville, TN",
        "category": "Finance",
        "tier": "major",
        "description": (
            "Healthcare Financial Management Association. Deep-dive on revenue "
            "cycle, payer contracting, cost management. The go-to event for "
            "understanding RCM operational best practices and benchmarks."
        ),
        "relevance": "Revenue cycle benchmarks, payer contracting, cost optimization",
        "url": "",
    },
    {
        "name": "McDermott Will & Emery Health Capital Conference",
        "date": "2027-03-17",
        "end_date": "2027-03-18",
        "location": "Chicago, IL",
        "category": "PE/M&A",
        "tier": "major",
        "description": (
            "Legal and regulatory perspective on healthcare transactions. "
            "Antitrust, CON laws, FTC enforcement trends. Critical for "
            "understanding deal execution risk and regulatory timelines."
        ),
        "relevance": "Antitrust risk, deal structuring, regulatory timelines",
        "url": "",
    },
    {
        "name": "Jefferies Healthcare Conference",
        "date": "2027-06-03",
        "end_date": "2027-06-05",
        "location": "New York, NY",
        "category": "Investment",
        "tier": "major",
        "description": (
            "Sell-side healthcare conference with 150+ presenting companies. "
            "Strong coverage of healthcare services, managed care, and life "
            "sciences. Good for public comp intelligence."
        ),
        "relevance": "Public comp intelligence, management access, sector trends",
        "url": "",
    },
    {
        "name": "ACHE Congress on Healthcare Leadership",
        "date": "2027-03-24",
        "end_date": "2027-03-27",
        "location": "Chicago, IL",
        "category": "Operations",
        "tier": "standard",
        "description": (
            "American College of Healthcare Executives. 4,000+ C-suite hospital "
            "leaders. Focus on leadership, strategy, and governance. Useful for "
            "understanding management quality indicators."
        ),
        "relevance": "Management quality assessment, governance best practices",
        "url": "",
    },
    {
        "name": "Health Evolution Summit",
        "date": "2027-04-28",
        "end_date": "2027-04-30",
        "location": "Dana Point, CA",
        "tier": "flagship",
        "category": "Investment",
        "description": (
            "Invitation-only summit for healthcare CEOs, investors, and innovators. "
            "300 attendees, highly curated. Among the most influential events "
            "for healthcare investment strategy and sector direction."
        ),
        "relevance": "Strategic direction, C-level access, investment thesis development",
        "url": "",
    },
    {
        "name": "MGMA Annual Conference",
        "date": "2027-10-05",
        "end_date": "2027-10-08",
        "location": "Denver, CO",
        "category": "Operations",
        "tier": "standard",
        "description": (
            "Medical Group Management Association. Focus on physician practice "
            "operations, MSO models, and value-based care. Relevant for PE "
            "firms investing in physician practice platforms."
        ),
        "relevance": "MSO/physician practice diligence, VBC models",
        "url": "",
    },
    {
        "name": "CMS IPPS Final Rule Release",
        "date": "2027-08-01",
        "end_date": "2027-08-01",
        "location": "Virtual (Federal Register)",
        "category": "Policy",
        "tier": "flagship",
        "description": (
            "Annual Medicare inpatient prospective payment system update. Sets "
            "payment rates, quality adjustments, and policy changes for the "
            "upcoming fiscal year. Directly impacts hospital revenue models."
        ),
        "relevance": "Medicare rate update, payment policy, financial model inputs",
        "url": "",
    },
    {
        "name": "Goldman Sachs Healthcare Conference",
        "date": "2027-06-10",
        "end_date": "2027-06-12",
        "location": "Rancho Palos Verdes, CA",
        "category": "Investment",
        "tier": "major",
        "description": (
            "Premier sell-side event for healthcare investors. 100+ presenting "
            "companies across services, devices, and managed care. Essential "
            "for public comp valuation benchmarking."
        ),
        "relevance": "Valuation benchmarks, management meetings, sector outlook",
        "url": "",
    },
    {
        "name": "National Rural Health Association Conference",
        "date": "2027-05-12",
        "end_date": "2027-05-14",
        "location": "New Orleans, LA",
        "category": "Operations",
        "tier": "standard",
        "description": (
            "Focus on rural and critical access hospitals. 3,000+ attendees. "
            "Relevant for PE firms evaluating rural hospital acquisitions, "
            "CAH conversion strategies, and rural health program funding."
        ),
        "relevance": "Rural hospital diligence, CAH strategy, federal funding",
        "url": "",
    },
    {
        "name": "AHLA Health Law Connections",
        "date": "2027-06-30",
        "end_date": "2027-07-02",
        "location": "San Diego, CA",
        "category": "Policy",
        "tier": "standard",
        "description": (
            "American Health Law Association annual event. Regulatory compliance, "
            "fraud and abuse, Stark/Anti-Kickback enforcement trends. Critical "
            "for understanding legal risk in healthcare transactions."
        ),
        "relevance": "Compliance risk, Stark/AKS, transaction legal diligence",
        "url": "",
    },
    {
        "name": "Leerink Partners Global Healthcare Conference",
        "date": "2027-02-10",
        "end_date": "2027-02-12",
        "location": "New York, NY",
        "category": "Investment",
        "tier": "standard",
        "description": (
            "Healthcare-focused investment bank conference with strong coverage "
            "of healthcare services sector. Key for management meetings with "
            "public healthcare services companies."
        ),
        "relevance": "Healthcare services sector analysis, management access",
        "url": "",
    },
]

CATEGORY_COLORS = {
    "Investment": PALETTE.get("brand_accent", "#2d6ba4"),
    "PE/M&A": PALETTE.get("positive", "#2ecc71"),
    "Policy": PALETTE.get("warning", "#f39c12"),
    "Operations": PALETTE.get("text_link", "#5b9bd5"),
    "Finance": PALETTE.get("text_secondary", "#a0aec0"),
    "Health IT": PALETTE.get("negative", "#e74c3c"),
}

TIER_BADGE = {
    "flagship": ("cad-badge-green", "Flagship"),
    "major": ("cad-badge-blue", "Major"),
    "standard": ("cad-badge-muted", "Standard"),
}


def render_conference_roadmap(category: str = "all") -> str:
    """Render the conference roadmap page."""
    events = sorted(CONFERENCES, key=lambda e: e["date"])

    if category != "all":
        events = [e for e in events if e["category"].lower() == category.lower()]

    categories = sorted({e["category"] for e in CONFERENCES})
    cat_tabs = '<a href="/conferences" class="cad-tab{}" style="text-decoration:none;">All</a>'.format(
        " cad-tab-active" if category == "all" else ""
    )
    for cat in categories:
        active = " cad-tab-active" if category.lower() == cat.lower() else ""
        # URL-encode the category for the query string. Categories like
        # "Health IT" contain spaces that html.escape() leaves as literal
        # spaces — those land in the href as "Health IT" and produce a
        # malformed URL. urllib.parse.quote_plus produces "Health+IT".
        # Visible-text rendering still uses html.escape (XSS guard).
        cat_url = _urlparse.quote_plus(cat.lower())
        cat_tabs += (
            f'<a href="/conferences?cat={cat_url}" '
            f'class="cad-tab{active}" style="text-decoration:none;">{_html.escape(cat)}</a>'
        )

    # Quarter grouping
    from collections import defaultdict
    quarters: Dict[str, List[Dict]] = defaultdict(list)
    for e in events:
        year = e["date"][:4]
        month = int(e["date"][5:7])
        q = f"{year} Q{(month - 1) // 3 + 1}"
        quarters[q].append(e)

    timeline_html = ""
    for quarter, q_events in quarters.items():
        cards = ""
        for ev in q_events:
            name = _html.escape(ev["name"])
            date = ev["date"]
            end = ev.get("end_date", "")
            loc = _html.escape(ev["location"])
            cat = ev["category"]
            cat_color = CATEGORY_COLORS.get(cat, "#718096")
            tier = ev.get("tier", "standard")
            badge_class, badge_label = TIER_BADGE.get(tier, ("cad-badge-muted", "Standard"))
            desc = _html.escape(ev["description"])
            relevance = _html.escape(ev.get("relevance", ""))

            date_display = date
            if end and end != date:
                date_display = f"{date} — {end}"

            cards += (
                f'<div class="cad-card" style="margin-bottom:8px;padding:16px;">'
                f'<div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:8px;">'
                f'<div>'
                f'<div style="font-weight:600;font-size:14px;">{name}</div>'
                f'<div style="font-size:12px;color:var(--cad-text2);margin-top:2px;">'
                f'{date_display} &middot; {loc}</div>'
                f'</div>'
                f'<div style="display:flex;gap:6px;flex-shrink:0;">'
                f'<span class="cad-badge" style="background:{cat_color};color:#fff;font-size:10px;'
                f'padding:2px 8px;border-radius:3px;">{_html.escape(cat)}</span>'
                f'<span class="cad-badge {badge_class}" style="font-size:10px;padding:2px 8px;'
                f'border-radius:3px;">{badge_label}</span>'
                f'</div></div>'
                f'<p style="font-size:12.5px;color:var(--cad-text);line-height:1.6;margin:0 0 8px;">{desc}</p>'
                f'<div style="font-size:11px;color:var(--cad-text3);">'
                f'<strong>Diligence Relevance:</strong> {relevance}</div>'
                f'</div>'
            )

        timeline_html += (
            f'<div style="margin-bottom:20px;">'
            f'<h2 style="font-size:14px;color:var(--cad-accent);margin-bottom:8px;'
            f'padding-bottom:4px;border-bottom:1px solid var(--cad-border);">{_html.escape(quarter)}</h2>'
            f'{cards}</div>'
        )

    # Summary sidebar
    total = len(CONFERENCES)
    flagship_count = sum(1 for e in CONFERENCES if e.get("tier") == "flagship")
    cat_counts = {}
    for e in CONFERENCES:
        cat_counts[e["category"]] = cat_counts.get(e["category"], 0) + 1

    cat_breakdown = ""
    for cat, count in sorted(cat_counts.items(), key=lambda x: -x[1]):
        color = CATEGORY_COLORS.get(cat, "#718096")
        cat_breakdown += (
            f'<div style="display:flex;justify-content:space-between;padding:4px 0;'
            f'font-size:12px;border-bottom:1px solid var(--cad-border);">'
            f'<span style="color:{color};">{_html.escape(cat)}</span>'
            f'<span class="cad-mono">{count}</span></div>'
        )

    summary = (
        f'<div class="cad-card" style="margin-bottom:12px;">'
        f'<h2 style="font-size:13px;margin-bottom:8px;">Event Summary</h2>'
        f'<div class="cad-kpi-grid" style="grid-template-columns:1fr 1fr;gap:8px;margin-bottom:10px;">'
        f'<div class="cad-kpi"><div class="cad-kpi-value" style="font-size:20px;">{total}</div>'
        f'<div class="cad-kpi-label">Total Events</div></div>'
        f'<div class="cad-kpi"><div class="cad-kpi-value" style="font-size:20px;color:var(--cad-pos);">'
        f'{flagship_count}</div>'
        f'<div class="cad-kpi-label">Flagship</div></div>'
        f'</div>'
        f'{cat_breakdown}</div>'
    )

    planning_tips = (
        f'<div class="cad-card" style="border-left:3px solid var(--cad-accent);">'
        f'<h2 style="font-size:13px;margin-bottom:8px;">Planning Tips</h2>'
        f'<ul style="font-size:12px;color:var(--cad-text2);line-height:1.8;padding-left:16px;">'
        f'<li>Book J.P. Morgan meetings 6-8 weeks in advance</li>'
        f'<li>HFMA is best for RCM benchmarking conversations</li>'
        f'<li>CMS IPPS rule release directly impacts financial models — schedule review within 48h</li>'
        f'<li>HPEA Summit is highest-value per-hour for GP networking</li>'
        f'<li>Becker\'s attracts hospital CFOs — ideal for management reference checks</li>'
        f'</ul></div>'
    )

    body = (
        f'<div style="display:flex;gap:6px;flex-wrap:wrap;margin-bottom:16px;">{cat_tabs}</div>'
        f'<div style="display:grid;grid-template-columns:1fr 300px;gap:16px;">'
        f'<div>{timeline_html}</div>'
        f'<div>{summary}{planning_tips}</div>'
        f'</div>'
    )

    return chartis_shell(
        body,
        "Conference Roadmap",
        active_nav="/conferences",
        subtitle=f"{len(events)} events | Healthcare PE diligence conference calendar",
        extra_css=(
            ".cad-tab{display:inline-block;padding:6px 14px;font-size:12px;"
            "color:var(--cad-text2);border:1px solid var(--cad-border);border-radius:3px;"
            "cursor:pointer;transition:all 0.15s;}"
            ".cad-tab:hover{border-color:var(--cad-accent);color:var(--cad-text);}"
            ".cad-tab-active{background:var(--cad-accent);color:#fff;border-color:var(--cad-accent);}"
            ".cad-badge-green{background:var(--cad-pos);color:#fff;}"
            ".cad-badge-blue{background:var(--cad-accent);color:#fff;}"
            ".cad-badge-muted{background:var(--cad-border);color:var(--cad-text2);}"
        ),
    )
