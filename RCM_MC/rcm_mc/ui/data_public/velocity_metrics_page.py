"""Velocity Metrics — /velocity. Moat 6 instrumentation."""
from __future__ import annotations

import html as _html
from typing import Optional
from rcm_mc.ui._chartis_kit import P, chartis_shell, ck_kpi_block


def _state_color(s: str) -> str:
    if "STRONG" in s: return P["positive"]
    if "MEDIUM" in s: return P["accent"]
    if "NASCENT" in s: return P["warning"]
    if "IGNORED" in s: return P["negative"]
    return P["text_dim"]


def _category_color(c: str) -> str:
    return {
        "knowledge": P["accent"], "benchmark": P["positive"],
        "moat-engine": P["negative"], "regulatory": P["warning"],
        "ml": P["accent"], "infra": P["text_dim"], "ui": P["accent"],
    }.get(c, P["text_dim"])


def _pct_color(p: Optional[float]) -> str:
    if p is None: return P["text_dim"]
    if p >= 80: return P["positive"]
    if p >= 40: return P["accent"]
    if p >= 15: return P["warning"]
    return P["negative"]


def _moat_status_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]
    cols = [("#", "right"), ("Moat Layer", "left"), ("State", "center"),
            ("Instrumented Modules", "right"), ("Item Count", "right"),
            ("Recent Additions", "right")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, m in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        sc = _state_color(m.state)
        cells = [
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:700">{m.layer_number}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:11px;color:{text};font-weight:600;max-width:260px">{_html.escape(m.layer_name)}</td>',
            f'<td style="text-align:center;padding:5px 10px"><span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{sc};border:1px solid {sc};border-radius:2px;letter-spacing:0.06em;font-weight:700">{_html.escape(m.state)}</span></td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{len(m.instrumented_modules)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos};font-weight:700">{m.item_count_total:,}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{acc};font-weight:700">+{m.recent_additions}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _libraries_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]
    cols = [("Library", "left"), ("Category", "center"),
            ("Current", "right"), ("Target", "right"),
            ("% of Target", "right"), ("Gap", "right"),
            ("This Cycle +", "right"), ("Note", "left")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    ranked = sorted(items, key=lambda m: (-m.current_count))
    for i, m in enumerate(ranked):
        rb = panel_alt if i % 2 == 0 else bg
        cc = _category_color(m.category)
        pct = m.pct_of_target
        pct_c = P["positive"] if pct and pct >= 80 else (
            P["accent"] if pct and pct >= 40 else (
            P["warning"] if pct and pct >= 15 else P["negative"]))
        gap_str = f"{m.gap_to_target:,}" if m.gap_to_target is not None else "—"
        target_str = f"{m.blueprint_target:,}" if m.blueprint_target else "—"
        pct_str = f"{pct:.1f}%" if pct is not None else "—"
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:700">{_html.escape(m.library_name)}</td>',
            f'<td style="text-align:center;padding:5px 10px"><span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{cc};border:1px solid {cc};border-radius:2px;letter-spacing:0.06em">{_html.escape(m.category)}</span></td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos};font-weight:700">{m.current_count:,}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{target_str}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pct_c};font-weight:700">{pct_str}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{gap_str}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{acc};font-weight:700">+{m.additions_last_cycle}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim};max-width:440px">{_html.escape(m.cumulative_growth_note)}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _inventory_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]
    cols = [("Module", "left"), ("Category", "center"),
            ("First Committed", "right"), ("SHA", "center"),
            ("LOC", "right"), ("Items", "right"), ("Label", "left")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, r in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        cc = _category_color(r.category)
        item_str = f"{r.item_count:,}" if r.item_count is not None else "—"
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:700">{_html.escape(r.module_name)}</td>',
            f'<td style="text-align:center;padding:5px 10px"><span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{cc};border:1px solid {cc};border-radius:2px;letter-spacing:0.06em">{_html.escape(r.category)}</span></td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{acc};font-weight:600">{_html.escape(r.committed_date)}</td>',
            f'<td style="text-align:center;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{text_dim}">{_html.escape(r.committed_commit)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{r.lines_of_code:,}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos};font-weight:700">{item_str}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(r.item_label)}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _cadence_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]
    cols = [("Month", "left"), ("Modules Added", "right"),
            ("Commits", "right"), ("Categories Touched", "left")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, c in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        cats = ", ".join(c.categories_touched)
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:700">{_html.escape(c.year_month)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos};font-weight:700">{c.modules_added}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{c.commits_count}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{acc};max-width:540px">{_html.escape(cats)}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def render_velocity_metrics(params: dict = None) -> str:
    from rcm_mc.data_public.velocity_metrics import compute_velocity_metrics
    r = compute_velocity_metrics()

    panel = P["panel"]; panel_alt = P["panel_alt"]
    border = P["border"]; text = P["text"]; text_dim = P["text_dim"]
    acc = P["accent"]

    kpi_strip = (
        ck_kpi_block("Shipped Modules", str(r.total_shipped_modules), "data_public/", "") +
        ck_kpi_block("Lines of Code", f"{r.total_lines_of_code:,}", "knowledge modules", "") +
        ck_kpi_block("Knowledge Items", f"{r.total_knowledge_items:,}", "across all libraries", "") +
        ck_kpi_block("Commits", str(r.total_commits), "total", "") +
        ck_kpi_block("Days Active", str(r.days_elapsed), "first → latest", "") +
        ck_kpi_block("Modules/Day", f"{r.modules_per_day:.1f}", "", "") +
        ck_kpi_block("Items/Day", f"{r.items_per_day:,.0f}", "", "") +
        ck_kpi_block("Corpus Deals", f"{r.corpus_deal_count:,}", "", "")
    )

    moat_tbl = _moat_status_table(r.moat_status)
    libs_tbl = _libraries_table(r.library_metrics)
    inv_tbl = _inventory_table(r.module_inventory)
    cadence_tbl = _cadence_table(r.cadence_by_month)

    cell = f"background:{panel};border:1px solid {border};padding:16px;margin-bottom:16px"
    h3 = f"font-size:11px;font-weight:600;letter-spacing:0.08em;color:{text_dim};text-transform:uppercase;margin-bottom:10px"

    body = f"""
<div style="padding:20px;max-width:1400px;margin:0 auto">
  <div style="margin-bottom:20px">
    <h1 style="font-size:18px;font-weight:700;color:{text};letter-spacing:0.02em">Velocity Metrics — Moat 6 Instrumentation</h1>
    <p style="font-size:12px;color:{text_dim};margin-top:4px">The self-instrumentation layer flagged IGNORED across 3 prior cycles. Now live. Makes the platform's own growth rate visible — per the blueprint, "every new target diligenced, every new regulation ingested, every new bankruptcy decomposed → library compounds." This page tracks it.</p>
  </div>
  <div style="display:flex;flex-wrap:wrap;gap:8px;margin-bottom:20px">{kpi_strip}</div>
  <div style="{cell}"><div style="{h3}">Moat Layer Status — All 7 Layers, Live Count</div>{moat_tbl}</div>
  <div style="{cell}"><div style="{h3}">Libraries — Current vs Blueprint Target, This-Cycle Additions</div>{libs_tbl}</div>
  <div style="{cell}"><div style="{h3}">Module Inventory — Every Shipped data_public Module (Git Add History)</div>{inv_tbl}</div>
  <div style="{cell}"><div style="{h3}">Cadence by Month — Module-Add Rate + Commit Count + Category Diversity</div>{cadence_tbl}</div>
  <div style="background:{panel_alt};border:1px solid {border};border-left:3px solid {acc};padding:12px 16px;font-size:11px;color:{text_dim};margin-bottom:16px">
    <strong style="color:{text}">Velocity Thesis:</strong>
    Moat 6 was the single IGNORED layer across the first 3 session cycles. Now instrumented.
    This page reads module-add dates from git history + live item counts from each
    shipped <code style="color:{acc};font-family:JetBrains Mono,monospace">compute_*()</code>
    function. Updates automatically as new modules ship. No manual curation required.
    <br><br>
    <strong style="color:{text}">What to read:</strong>
    The libraries table shows current-vs-target for every curated asset. Blueprint
    targets are the blueprint's stated goals; gap numbers are what's left to build.
    The "This Cycle +" column shows recently-added items so you can see what was
    shipped most recently. The cadence table shows the commit rhythm.
    <br><br>
    <strong style="color:{text}">What a buyer-firm sees:</strong>
    Velocity + Track Record together are the double-barrel credibility proof.
    Track Record answers "does it catch real failures?" (yes, 10/10 at LBO date).
    Velocity answers "does it stay current?" (yes, N modules/day, M items added
    this cycle, Blueprint targets visible). Together they convert one-time demo
    momentum into an ongoing-platform value proposition.
    <br><br>
    <strong style="color:{text}">Integrations:</strong>
    Cross-links to <code style="color:{acc};font-family:JetBrains Mono,monospace">/track-record</code>
    (the 'would have flagged' companion page) and
    <code style="color:{acc};font-family:JetBrains Mono,monospace">/corpus-dashboard</code>
    (the corpus-level view). This page is the platform-level counterpart.
    <br><br>
    <strong style="color:{text}">Reads git state at import:</strong>
    <code style="color:{acc};font-family:JetBrains Mono,monospace">subprocess.run(["git", "log", ...])</code>
    at first call. Falls back gracefully if not in a repo (e.g., pip-installed
    deployment). Zero new runtime deps.
  </div>
</div>"""

    return chartis_shell(body, "Velocity Metrics — Moat 6", active_nav="/velocity")
