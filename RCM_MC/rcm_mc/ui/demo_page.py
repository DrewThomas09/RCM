"""Demo Mode page — /demo.

The partner-facing tutorial entry point (reached from Settings → Demo Mode).
One click loads a curated, credible **KKR healthcare portfolio** into the
workspace so the command center, portfolio map, alerts, cohorts, deal pages and
PE math all populate with real deals — letting the demo showcase every feature
with true (real deals / disclosed EVs) and consistent (modeled ops) numbers.
Also offers the same data as downloadable ingestion files (JSON + CSV) plus
step-by-step instructions, so a partner can learn the import format too.
"""
from __future__ import annotations

import html as _html
from typing import Optional

from ._chartis_kit import chartis_shell, ck_page_title
from ..demo.kkr_demo import KKR_DEMO_DEALS, demo_deal_rows, entry_ebitda_mm


def _ev(mm: int, real: bool) -> str:
    s = f"${mm/1000:.1f}B" if mm >= 1000 else f"${mm:,.0f}M"
    return s if real else s + "*"


_TIER_COLOR = {"green": "#0a8a5f", "amber": "#b8732a", "red": "#b5321e"}


def render_demo_page(loaded: bool = False, deal_count: int = 0) -> str:
    """Render the Demo Mode page.

    ``loaded`` — the KKR demo portfolio is already present in this workspace.
    ``deal_count`` — number of deals currently in the workspace (any source).
    """
    rows = demo_deal_rows()
    n = len(rows)
    total_ev = sum(r["entry_ev_mm"] for r in rows)
    disclosed = sum(1 for r in rows if r["ev_disclosed"])

    title = ck_page_title(
        "Demo Mode — KKR healthcare portfolio",
        eyebrow="TUTORIAL",
        meta=f"{n} real KKR deals · ${total_ev/1000:.0f}B entry EV · "
             f"{disclosed} disclosed EVs · one-click load",
    )

    # --- Load / status action -------------------------------------------------
    if loaded:
        action = (
            '<div style="border:1px solid #0a8a5f;background:#eef7f1;border-radius:4px;'
            'padding:16px 18px;margin:6px 0 20px;">'
            '<div style="font-weight:600;color:#0a8a5f;font-size:15px;">✓ Demo portfolio loaded</div>'
            f'<div style="color:#1a2332;font-size:12px;margin-top:4px;">The KKR portfolio is in your '
            f'workspace ({deal_count} deals). Open the command center to see it populated.</div>'
            '<div style="margin-top:12px;">'
            '<a href="/app" style="display:inline-block;background:#0b2341;color:#fff;text-decoration:none;'
            'padding:8px 16px;border-radius:3px;font-size:12px;font-weight:600;">→ Open command center</a>'
            '<a href="/portfolio/map" style="display:inline-block;margin-left:8px;color:#155752;'
            'text-decoration:none;padding:8px 12px;font-size:12px;">Portfolio map</a>'
            '<a href="/alerts" style="display:inline-block;margin-left:4px;color:#155752;'
            'text-decoration:none;padding:8px 12px;font-size:12px;">Alerts</a>'
            '</div></div>'
        )
    else:
        warn = (f'<div style="color:#b8732a;font-size:11px;margin-top:8px;">'
                f'Note: your workspace already has {deal_count} deal(s); loading the demo adds the '
                f'KKR deals alongside them.</div>' if deal_count else '')
        action = (
            '<div style="border:1px solid #d6cfc0;background:#faf7f0;border-radius:4px;'
            'padding:16px 18px;margin:6px 0 20px;">'
            '<div style="font-weight:600;color:#1a2332;font-size:15px;">Load the demo portfolio</div>'
            '<div style="color:#465366;font-size:12px;margin-top:4px;">'
            'Seeds your workspace with the KKR deals below (snapshots, MOIC/IRR, covenant headroom, '
            'RCM metrics, quarterly variance, tags &amp; owners) so every surface populates. '
            'Idempotent — safe to click more than once.</div>'
            '<form method="post" action="/demo/load" style="margin-top:12px;">'
            '<button type="submit" style="background:#0b2341;color:#fff;border:none;'
            'padding:9px 18px;border-radius:3px;font-size:12px;font-weight:600;cursor:pointer;">'
            'Load KKR demo portfolio</button></form>'
            + warn + '</div>'
        )

    # --- Step-by-step tutorial ------------------------------------------------
    steps = [
        ("Load the demo", "Click <b>Load KKR demo portfolio</b> above. The workspace fills with KKR's "
         "real healthcare deals."),
        ("Open the command center", "Go to <a href='/app' style='color:#155752'>the command center</a> — "
         "the home view now shows KKR's portfolio: health bands, alerts, top movers, EBITDA at risk."),
        ("Explore the portfolio map &amp; cohorts", "<a href='/portfolio/map' style='color:#155752'>Portfolio map</a>, "
         "<a href='/cohorts' style='color:#155752'>cohorts</a>, and <a href='/watchlist' style='color:#155752'>watchlist</a> "
         "all resolve to these KKR deals."),
        ("Drill into a deal", "Open any deal (e.g. Cotiviti, or the distressed Envision) for the snapshot trail, "
         "variance, RCM profile, PE bridge, covenant headroom and health trend."),
        ("Check the alerts", "<a href='/alerts' style='color:#155752'>Alerts</a> fire on the stressed deals "
         "(Envision's tripped covenant, the amber names) — ack / snooze / escalate to see the lifecycle."),
        ("(Optional) inspect the data", "Download the ingestion files below to see the exact import format, "
         "or hand them to a colleague."),
    ]
    steps_html = "".join(
        f'<li style="margin:8px 0;font-size:12.5px;color:#1a2332;line-height:1.5;">'
        f'<b>{_html.escape(t)}</b> — {body}</li>' for t, body in steps
    )
    tutorial = (
        '<div style="border:1px solid #d6cfc0;border-radius:4px;padding:14px 20px 16px;margin-bottom:20px;background:#fff;">'
        '<div style="font-family:JetBrains Mono,monospace;font-size:10px;letter-spacing:.08em;'
        'text-transform:uppercase;color:#5c6878;margin-bottom:6px;">How to run the demo</div>'
        f'<ol style="margin:0;padding-left:22px;">{steps_html}</ol></div>'
    )

    # --- Downloads ------------------------------------------------------------
    downloads = (
        '<div style="margin-bottom:20px;font-size:12px;color:#465366;">'
        '<b style="color:#1a2332;">Demo ingestion files:</b> '
        '<a href="/demo/download/kkr-deals.json" style="color:#155752;text-decoration:none;border:1px solid #d6cfc0;'
        'border-radius:3px;padding:4px 10px;margin-left:6px;">↓ kkr-deals.json</a> '
        '<a href="/demo/download/kkr-deals.csv" style="color:#155752;text-decoration:none;border:1px solid #d6cfc0;'
        'border-radius:3px;padding:4px 10px;margin-left:4px;">↓ kkr-deals.csv</a>'
        '</div>'
    )

    # --- Preview table of the portfolio --------------------------------------
    trows = []
    for i, s in enumerate(sorted(KKR_DEMO_DEALS, key=lambda d: -d["ev_mm"])):
        stripe = ' style="background:var(--sc-bone,#faf7f0)"' if i % 2 else ""
        tc = _TIER_COLOR.get(s["tier"], "#465366")
        trows.append(
            f'<tr{stripe}>'
            f'<td style="padding:4px 10px;font-size:11px;">{_html.escape(s["name"])}</td>'
            f'<td style="padding:4px 10px;font-size:11px;color:#465366;">{_html.escape(s["sector"].replace("_"," "))}</td>'
            f'<td style="padding:4px 10px;font-size:11px;text-align:right;font-family:JetBrains Mono,monospace;">{s["year"]}</td>'
            f'<td style="padding:4px 10px;font-size:11px;text-align:right;font-family:JetBrains Mono,monospace;">{_ev(s["ev_mm"], s["ev_real"])}</td>'
            f'<td style="padding:4px 10px;font-size:11px;text-align:right;font-family:JetBrains Mono,monospace;">{s["moic"]:.1f}x</td>'
            f'<td style="padding:4px 10px;font-size:10px;text-transform:uppercase;color:{tc};font-weight:600;">{s["tier"]}</td>'
            '</tr>'
        )
    table = (
        '<div style="border:1px solid #d6cfc0;border-radius:4px;overflow:hidden;">'
        '<table style="width:100%;border-collapse:collapse;">'
        '<thead><tr style="background:#0b2341;color:#fff;">'
        '<th style="padding:6px 10px;text-align:left;font-size:10px;">Deal</th>'
        '<th style="padding:6px 10px;text-align:left;font-size:10px;">Sector</th>'
        '<th style="padding:6px 10px;text-align:right;font-size:10px;">Entry</th>'
        '<th style="padding:6px 10px;text-align:right;font-size:10px;">EV</th>'
        '<th style="padding:6px 10px;text-align:right;font-size:10px;">MOIC</th>'
        '<th style="padding:6px 10px;text-align:left;font-size:10px;">Tier</th>'
        f'</tr></thead><tbody>{"".join(trows)}</tbody></table></div>'
        '<div style="font-size:9.5px;color:#7a8699;margin-top:6px;">'
        '* modeled EV (sector-typical multiple); unmarked EVs are publicly disclosed. '
        'Operating metrics, leverage, MOIC/IRR and variance are modeled from each deal\'s performance '
        'tier — realistic and internally consistent, not audited returns. Deals are real KKR investments.'
        '</div>'
    )

    body = (
        '<div class="ck-page-wrap" style="max-width:1000px;margin:0 auto;">'
        + title + action + tutorial + downloads + table + '</div>'
    )
    return chartis_shell(
        body, "Demo Mode", active_nav="/settings",
        subtitle="Load a credible KKR healthcare portfolio to showcase every feature",
    )
