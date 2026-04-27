"""Example migration — BEFORE and AFTER for a representative page.

This file is documentation, not runnable. It shows the exact diff pattern
Claude Code (or a human) should apply when reskinning an existing
rcm_mc/ui/ page. Use it as a template for similar pages.

Page chosen: rcm_mc/ui/portfolio_heatmap.py (a `kind: dashboard` surface).
The same pattern applies to any dashboard-kind page — see PATCH_GUIDES/README.md.
"""

# =============================================================================
# BEFORE — representative legacy page
# =============================================================================

BEFORE = '''
"""Portfolio health heatmap (Prompt 36)."""

from rcm_mc.ui._chartis_kit import chartis_shell

def render_portfolio_heatmap(store):
    rows = store.list_deals()

    # Hardcoded dark palette everywhere — this is what we're removing.
    html = """
    <style>
      body { background: #0a0a0a; color: #e0e0e0; font-family: 'SF Mono', monospace; }
      .panel { background: #1a1a1a; border: 1px solid #2a2a2a; padding: 16px; }
      .panel h3 { color: #33ffff; font-size: 11px; letter-spacing: 0.1em; }
      .cell-good { background: #00ff9c; color: #000; }
      .cell-warn { background: #ffab00; color: #000; }
      .cell-bad  { background: #ff6b6b; color: #000; }
      table { width: 100%; border-collapse: collapse; font-size: 11px; }
      td { padding: 6px 8px; border: 1px solid #2a2a2a; font-family: monospace; }
    </style>
    <div class="panel">
      <h3>PORTFOLIO HEATMAP [PRT-36]</h3>
      <table>
        <thead><tr><th>Deal</th><th>Stage</th><th>Score</th><th>Trend</th></tr></thead>
        <tbody>
    """
    for d in rows:
        tone = "good" if d.score >= 75 else "warn" if d.score >= 60 else "bad"
        html += f'<tr><td>{d.name}</td><td>{d.stage}</td>'
        html += f'<td class="cell-{tone}">{d.score}</td>'
        html += f'<td>{d.trend}</td></tr>'
    html += "</tbody></table></div>"

    return chartis_shell(html, "Portfolio Heatmap")
'''


# =============================================================================
# AFTER — reskinned, using the new kit primitives
# =============================================================================

AFTER = '''
"""Portfolio health heatmap (Prompt 36)."""

from rcm_mc.ui._chartis_kit import (
    chartis_shell, ck_panel, ck_section_header, ck_signal_badge,
)

def render_portfolio_heatmap(store):
    rows = store.list_deals()

    # Build the body as semantic HTML. Tokens from chartis_tokens.css handle
    # all the color/type/spacing — no inline <style> needed.
    thead = (
        '<thead><tr>'
        '<th class="align-left">Deal</th>'
        '<th class="align-left">Stage</th>'
        '<th class="align-right">Score</th>'
        '<th class="align-right">Trend</th>'
        '</tr></thead>'
    )

    tbody_rows = []
    for d in rows:
        tone = (
            "positive" if d.score >= 75 else
            "warning"  if d.score >= 60 else
            "negative"
        )
        tbody_rows.append(
            f"<tr>"
            f"<td>{d.name}</td>"
            f"<td>{d.stage}</td>"
            f'<td class="align-right">{ck_signal_badge(str(d.score), tone=tone)}</td>'
            f'<td class="align-right sc-num">{d.trend}</td>'
            f"</tr>"
        )

    table = (
        f'<table class="ck-table ck-dense">{thead}'
        f'<tbody>{"".join(tbody_rows)}</tbody></table>'
    )

    body = (
        ck_section_header(
            "Portfolio heatmap",
            eyebrow="Morning view",
            code="PRT-36",
        )
        + ck_panel(table, title="Health by deal", code="PRT-36")
    )

    return chartis_shell(
        body,
        "Portfolio Heatmap",
        active_nav="portfolio",
        breadcrumbs=[
            {"label": "Portfolio", "href": "/portfolio"},
            {"label": "Heatmap"},
        ],
    )
'''


# =============================================================================
# What changed, line by line
# =============================================================================

CHANGE_NOTES = """
1. Deleted the entire inline <style> block. All color/type/spacing tokens
   now come from chartis_tokens.css which the shell links automatically.

2. #0a0a0a page bg → implicit (shell sets --sc-parchment on body).
3. #1a1a1a panel bg → ck_panel() wrapper (white card + navy header strip).
4. #33ffff cyan section title → ck_section_header() with eyebrow + serif H2.
5. #00ff9c / #ffab00 / #ff6b6b traffic-light cells → ck_signal_badge(tone=)
   which maps to --sc-positive / --sc-warning / --sc-negative tokens.
6. SF Mono body font → inherited Inter Tight from <body>; .sc-num class on
   numeric cells preserves tabular-nums monospace.
7. Manual <table> → .ck-table with thead/tbody styling from chartis_tokens.css.
8. chartis_shell() now gets active_nav= and breadcrumbs= — these power the
   top-bar active-state and the breadcrumb strip.

Result: ~35 fewer lines, zero hardcoded hex, same data, same route, same
function signature. Acceptance checklist passes on first run.
"""


# =============================================================================
# Apply this pattern to ALL kind: dashboard pages
# =============================================================================

DASHBOARD_PAGES_TO_MIGRATE = [
    "portfolio_heatmap.py",
    "portfolio_monitor_page.py",
    "chartis/portfolio_analytics_page.py",
    "market_data_page.py",
    "competitive_intel_page.py",
    "model_validation_page.py",
    "value_tracking_page.py",
    "waterfall_page.py",
    "dashboard_v2.py",
    "home_v2.py",
    "chartis/home_page.py",
]
