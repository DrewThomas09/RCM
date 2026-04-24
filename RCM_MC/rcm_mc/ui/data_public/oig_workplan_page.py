"""OIG Work Plan Tracker — /oig-workplan."""
from __future__ import annotations

import html as _html
from rcm_mc.ui._chartis_kit import P, chartis_shell, ck_kpi_block


def _tier_color(t: str) -> str:
    return {"CRITICAL": P["negative"], "HIGH": P["negative"],
            "MEDIUM": P["warning"], "LOW": P["accent"]}.get(t, P["text_dim"])


def _status_color(s: str) -> str:
    return {"open": P["negative"], "active": P["warning"],
            "completed": P["text_dim"], "withdrawn": P["text_dim"]}.get(s, P["text_dim"])


def _risk_color(r: str) -> str:
    return {"high": P["negative"], "medium": P["warning"], "low": P["accent"]}.get(r, P["text_dim"])


def _items_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]
    cols = [("Item", "left"), ("Yr", "right"), ("Title", "left"),
            ("Provider Type", "left"), ("Topic", "left"),
            ("Status", "center"), ("Risk", "center"),
            ("Recovery Low-High $M", "right"), ("Report", "left")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    ranked = sorted(items, key=lambda x: (x.status not in ("open", "active"), -x.typical_recovery_high_mm))
    for i, it in enumerate(ranked):
        rb = panel_alt if i % 2 == 0 else bg
        sc = _status_color(it.status)
        rc = _risk_color(it.enforcement_risk)
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:700">{_html.escape(it.item_id)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:10px;color:{text_dim}">{it.year_added}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:11px;color:{text};font-weight:600;max-width:300px">{_html.escape(it.title)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{acc};max-width:200px">{_html.escape(it.provider_type)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim};max-width:200px">{_html.escape(it.topic_category)}</td>',
            f'<td style="text-align:center;padding:5px 10px"><span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{sc};border:1px solid {sc};border-radius:2px;letter-spacing:0.06em;font-weight:700">{_html.escape(it.status.upper())}</span></td>',
            f'<td style="text-align:center;padding:5px 10px"><span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{rc};border:1px solid {rc};border-radius:2px;letter-spacing:0.06em">{_html.escape(it.enforcement_risk.upper())}</span></td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos};font-weight:700">${it.typical_recovery_low_mm:.0f}–${it.typical_recovery_high_mm:.0f}M</td>',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{text_dim};max-width:220px">{_html.escape(it.report_reference)}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _categories_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]
    cols = [("Provider Type", "left"), ("Items", "right"),
            ("Open", "right"), ("Active", "right"), ("Completed", "right"),
            ("Aggregate Recovery $M", "right"), ("High Risk", "right"),
            ("Years", "center")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, c in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:700">{_html.escape(c.provider_type)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{c.item_count}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{P["negative"]}">{c.open_count}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{P["warning"]}">{c.active_count}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{c.completed_count}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos};font-weight:700">${c.aggregate_recovery_mid_mm:,.0f}M</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{acc}">{c.high_risk_count}</td>',
            f'<td style="text-align:center;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{text_dim}">{c.oldest_item_year}-{c.newest_item_year}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _exposures_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]
    cols = [("Deal", "left"), ("Year", "right"), ("Provider Type", "left"),
            ("Matched Items", "right"), ("Open+Active", "right"),
            ("Exposure $M", "right"), ("Top Item", "left"), ("Tier", "center")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, e in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        tc = _tier_color(e.risk_tier)
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">{_html.escape(e.deal_name)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{e.year or "—"}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{acc}">{_html.escape(e.inferred_provider_type)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{e.matched_items}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{acc};font-weight:700">{e.open_active_matches}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos};font-weight:700">${e.total_exposure_mid_mm:,.2f}M</td>',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{text_dim};max-width:260px">{_html.escape(e.top_item_id)} — {_html.escape(e.top_item_title[:42])}</td>',
            f'<td style="text-align:center;padding:5px 10px"><span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{tc};border:1px solid {tc};border-radius:2px;letter-spacing:0.06em;font-weight:700">{_html.escape(e.risk_tier)}</span></td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _crosswalk_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]
    cols = [("OIG Item", "left"), ("Title", "left"),
            ("NCCI Edit Category", "left"), ("Combined Exposure Note", "left")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, c in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:700">{_html.escape(c.wp_item_id)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:11px;color:{text};max-width:280px">{_html.escape(c.wp_title)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{acc};max-width:240px">{_html.escape(c.ncci_edit_category)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim};max-width:500px">{_html.escape(c.combined_exposure_note)}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def render_oig_workplan(params: dict = None) -> str:
    from rcm_mc.data_public.oig_workplan import compute_oig_workplan
    r = compute_oig_workplan()

    panel = P["panel"]; panel_alt = P["panel_alt"]
    border = P["border"]; text = P["text"]; text_dim = P["text_dim"]
    acc = P["accent"]

    kpi_strip = (
        ck_kpi_block("Total Items", str(r.total_items), "2015-2026", "") +
        ck_kpi_block("Open", str(r.total_open), "active audit", "") +
        ck_kpi_block("Active", str(r.total_active), "report in progress", "") +
        ck_kpi_block("Completed", str(r.total_completed), "public reports", "") +
        ck_kpi_block("Aggregate Recovery", f"${r.aggregate_recovery_mid_mm:,.0f}M", "midpoint", "") +
        ck_kpi_block("Corpus Matched", f"{r.deals_with_any_match:,}", "", "") +
        ck_kpi_block("CRITICAL Deals", str(r.critical_risk_deals), "", "") +
        ck_kpi_block("Corpus Deals", f"{r.corpus_deal_count:,}", "", "")
    )

    items_tbl = _items_table(r.items)
    cat_tbl = _categories_table(r.categories)
    exp_tbl = _exposures_table(r.deal_exposures)
    xw_tbl = _crosswalk_table(r.ncci_crosswalks)

    cell = f"background:{panel};border:1px solid {border};padding:16px;margin-bottom:16px"
    h3 = f"font-size:11px;font-weight:600;letter-spacing:0.08em;color:{text_dim};text-transform:uppercase;margin-bottom:10px"

    body = f"""
<div style="padding:20px;max-width:1400px;margin:0 auto">
  <div style="margin-bottom:20px">
    <h1 style="font-size:18px;font-weight:700;color:{text};letter-spacing:0.02em">OIG Work Plan Tracker</h1>
    <p style="font-size:12px;color:{text_dim};margin-top:4px">{r.total_items} OIG Work Plan items 2015-2026 ({r.total_open} open + {r.total_active} active + {r.total_completed} completed) · ${r.aggregate_recovery_mid_mm:,.0f}M aggregate recovery midpoint · {r.deals_with_any_match:,} corpus deals match at least one item · KB {r.knowledge_base_version} effective {r.knowledge_base_effective_date}</p>
  </div>
  <div style="display:flex;flex-wrap:wrap;gap:8px;margin-bottom:20px">{kpi_strip}</div>
  <div style="{cell}"><div style="{h3}">Work Plan Items — {r.total_items} curated (open/active first)</div>{items_tbl}</div>
  <div style="{cell}"><div style="{h3}">Provider-Type Rollup — Where Audit $ Concentrates</div>{cat_tbl}</div>
  <div style="{cell}"><div style="{h3}">Top 60 Corpus Deal Exposures — Matched Work Plan Items</div>{exp_tbl}</div>
  <div style="{cell}"><div style="{h3}">NCCI Crosswalk — Work Plan Items ↔ NCCI Edit Categories</div>{xw_tbl}</div>
  <div style="background:{panel_alt};border:1px solid {border};border-left:3px solid {acc};padding:12px 16px;font-size:11px;color:{text_dim};margin-bottom:16px">
    <strong style="color:{text}">OIG Work Plan Thesis:</strong>
    The HHS OIG Work Plan is the single most actionable forward-looking audit-risk
    signal for PE healthcare diligence. Active items tell you exactly which billing
    patterns federal auditors are challenging NOW; completed items with their recovery
    amounts inform expected-value reserve modeling. Cross-links to /ncci-scanner
    surface the specific CPT-pair patterns OIG is enforcing.
    <br><br>
    <strong style="color:{text}">KB provenance (cited):</strong>
    CMS Transmittal Register, OIG press releases + audit reports, HHS-OIG Work Plan
    public page, Federal Register-published guidance.
  </div>
</div>"""

    return chartis_shell(body, "OIG Work Plan Tracker", active_nav="/oig-workplan")
