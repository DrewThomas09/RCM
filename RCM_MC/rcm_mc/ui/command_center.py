"""SeekingChartis Command Center — the page that answers 'what should I do today?'

For new users (no deals): screening-focused with hospital universe stats,
quick-screen buttons, and market intelligence highlights.

For returning users (deals in portfolio): pipeline status, monitoring
alerts, recent activity, and deal health overview.

Always shows: data estate summary, model health, and market pulse.
"""
from __future__ import annotations

import html as _html
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from ..portfolio.store import PortfolioStore
from ._chartis_kit import chartis_shell
from .brand import PALETTE
from .provenance import source_tag, Source


def _fm(val: float) -> str:
    if abs(val) >= 1e12:
        return f"${val/1e12:.1f}T"
    if abs(val) >= 1e9:
        return f"${val/1e9:.1f}B"
    if abs(val) >= 1e6:
        return f"${val/1e6:.0f}M"
    return f"${val:,.0f}"


def render_command_center(
    hcris_df: pd.DataFrame,
    db_path: str,
) -> str:
    """Render the command center home page."""

    n_hospitals = len(hcris_df)
    now = datetime.now(timezone.utc)

    # ── Load portfolio state ──
    # Route through PortfolioStore so the connection inherits the
    # canonical PRAGMA foreign_keys=ON, busy_timeout=5000, and
    # row_factory=sqlite3.Row. Closes one of the 8 documented
    # dispatcher bypasses (campaign target 4E).
    store = PortfolioStore(db_path)
    deals = []
    alerts = []
    try:
        with store.connect() as con:
            deal_rows = con.execute(
                "SELECT deal_id, name, profile_json, created_at "
                "FROM deals WHERE archived_at IS NULL "
                "ORDER BY created_at DESC"
            ).fetchall()
            for r in deal_rows:
                deals.append({"deal_id": r["deal_id"], "name": r["name"],
                               "created_at": r["created_at"]})
            try:
                alert_rows = con.execute(
                    "SELECT deal_id, severity, kind, message, fired_at "
                    "FROM alerts WHERE acked_at IS NULL "
                    "ORDER BY fired_at DESC LIMIT 5"
                ).fetchall()
                alerts = [dict(r) for r in alert_rows]
            except Exception:  # noqa: BLE001 — alerts table is optional
                pass
    except Exception:  # noqa: BLE001 — empty/unbuilt DB falls through
        pass

    # Load pipeline data through the same canonical seam.
    pipeline_hospitals = []
    saved_searches = []
    try:
        from ..data.pipeline import list_pipeline, list_searches, pipeline_summary
        with store.connect() as con:
            pipeline_hospitals = list_pipeline(con)
            saved_searches = list_searches(con)
            pipe_summary = pipeline_summary(con)
    except Exception:  # noqa: BLE001 — pipeline tables are optional
        pipe_summary = {}

    has_portfolio = len(deals) > 0
    has_pipeline = len(pipeline_hospitals) > 0

    # ── Universe stats ──
    total_revenue = float(hcris_df["net_patient_revenue"].fillna(0).sum())
    total_beds = int(hcris_df["beds"].fillna(0).sum())
    n_states_raw = hcris_df["state"].nunique() if "state" in hcris_df.columns else 0
    n_states = 50  # Display as 50 states + DC + territories
    n_territories = max(0, n_states_raw - 51)

    if "operating_margin" not in hcris_df.columns:
        safe_rev = hcris_df["net_patient_revenue"].where(hcris_df["net_patient_revenue"] > 1e5)
        hcris_df = hcris_df.copy()
        raw_margin = (safe_rev - hcris_df["operating_expenses"]) / safe_rev
        hcris_df["operating_margin"] = raw_margin.clip(-0.5, 1.0)
        # Data-quality: flag hospitals whose raw margin was outside
        # [-100%, +100%] (obvious HCRIS filing artifacts — opex 2-1000x revenue,
        # negative revenue, etc.) so they don't inflate the distressed count.
        hcris_df["_dq_ok_margin"] = raw_margin.between(-1.0, 1.0) | raw_margin.isna()
    else:
        hcris_df = hcris_df.copy()
        hcris_df["_dq_ok_margin"] = True

    # Median uses only margins that survived the clamp (excludes garbage filings)
    dq_mask = hcris_df.get("_dq_ok_margin", pd.Series(True, index=hcris_df.index))
    clean_margins = hcris_df.loc[dq_mask.fillna(False), "operating_margin"].dropna()
    median_margin = float(clean_margins.median()) if len(clean_margins) else 0.0
    # Distressed = operating margin < -5% AND data is credible
    distressed = int((clean_margins < -0.05).sum())

    pe_targets = hcris_df[
        (hcris_df["beds"] >= 100) & (hcris_df["beds"] <= 500) &
        (hcris_df["net_patient_revenue"] >= 5e7)
    ]
    n_pe_targets = len(pe_targets)

    sections = []

    # ── Hero KPIs ──
    sections.append(
        f'<div class="cad-kpi-grid" style="grid-template-columns:repeat(6,1fr);">'
        f'<div class="cad-kpi"><div class="cad-kpi-value">{n_hospitals:,}</div>'
        f'<div class="cad-kpi-label">Hospitals {source_tag(Source.HCRIS, "FY2022")}</div></div>'
        f'<div class="cad-kpi"><div class="cad-kpi-value">{n_pe_targets:,}</div>'
        f'<div class="cad-kpi-label">PE-Sized Targets</div></div>'
        f'<div class="cad-kpi"><div class="cad-kpi-value">{_fm(total_revenue)}</div>'
        f'<div class="cad-kpi-label">Total NPSR</div></div>'
        f'<div class="cad-kpi"><div class="cad-kpi-value">{median_margin:.1%}</div>'
        f'<div class="cad-kpi-label">Median Margin</div></div>'
        f'<div class="cad-kpi"><div class="cad-kpi-value" style="color:var(--cad-neg);">{distressed:,}</div>'
        f'<div class="cad-kpi-label">Distressed (&lt;-5%)</div></div>'
        f'<div class="cad-kpi"><div class="cad-kpi-value">{len(deals)}</div>'
        f'<div class="cad-kpi-label">Active Deals</div></div>'
        f'</div>'
    )

    # ── Quick Actions bar — terminal-style command strip ──
    sections.append(
        f'<div class="cad-card" style="padding:8px 14px;">'
        f'<div style="display:flex;gap:8px;flex-wrap:wrap;align-items:center;">'
        f'<span class="cad-section-code" style="margin-right:4px;">QS</span>'
        f'<span style="font-size:10px;font-family:var(--cad-mono);letter-spacing:0.12em;'
        f'color:var(--cad-text3);text-transform:uppercase;margin-right:6px;">Quick Screens</span>'
        f'<a href="/predictive-screener?region=Southeast&min_beds=200&max_beds=400&max_margin=0.05&min_uplift=3000000" '
        f'class="cad-btn" style="text-decoration:none;">SE · 200-400 · &gt;$3M</a>'
        f'<a href="/predictive-screener?min_beds=100&max_margin=0&sort=est_uplift" '
        f'class="cad-btn" style="text-decoration:none;">Neg margin · 100+</a>'
        f'<a href="/predictive-screener?region=Midwest&min_beds=50&max_beds=200" '
        f'class="cad-btn" style="text-decoration:none;">Midwest · small</a>'
        f'<a href="/predictive-screener?min_beds=300&sort=est_uplift" '
        f'class="cad-btn" style="text-decoration:none;">Large · max uplift</a>'
        f'<a href="/predictive-screener" class="cad-btn cad-btn-primary" '
        f'style="text-decoration:none;margin-left:auto;">Open Screener &rarr;</a>'
        f'</div></div>'
    )

    # ── Pipeline section (if hospitals tracked) ──
    if has_pipeline:
        active_pipe = [h for h in pipeline_hospitals if h.stage not in ("closed", "passed")]
        pipe_rows = ""
        for h in active_pipe[:6]:
            pipe_rows += (
                f'<tr>'
                f'<td><a href="/hospital/{_html.escape(h.ccn)}" '
                f'style="color:var(--cad-link);text-decoration:none;font-weight:500;">'
                f'{_html.escape(h.hospital_name[:25])}</a></td>'
                f'<td style="font-size:10px;">'
                f'<span style="background:var(--cad-accent);color:#fff;padding:1px 6px;'
                f'border-radius:2px;font-size:9px;text-transform:uppercase;">'
                f'{_html.escape(h.stage)}</span></td>'
                f'<td style="font-size:11px;">'
                f'<a href="/ebitda-bridge/{_html.escape(h.ccn)}" '
                f'style="color:var(--cad-link);text-decoration:none;">Bridge</a></td>'
                f'</tr>'
            )

        search_links = ""
        for s in saved_searches[:3]:
            qs = "&".join(f'{k}={v}' for k, v in s.filters.items() if v)
            search_links += (
                f'<a href="/predictive-screener?{_html.escape(qs)}" '
                f'style="display:block;padding:4px 0;font-size:12px;'
                f'color:var(--cad-link);text-decoration:none;">'
                f'{_html.escape(s.name)} ({s.last_result_count} results)</a>'
            )

        pipe_left = (
            f'<div class="cad-card">'
            f'<div style="display:flex;justify-content:space-between;align-items:center;'
            f'margin-bottom:6px;">'
            f'<div style="display:flex;align-items:center;gap:10px;">'
            f'<h2 style="margin:0;">Pipeline ({len(active_pipe)})</h2>'
            f'<span class="cad-section-code">PIPE</span></div>'
            f'<a href="/pipeline" style="font-size:10.5px;font-family:var(--cad-mono);'
            f'letter-spacing:0.06em;text-transform:uppercase;color:var(--cad-link);'
            f'text-decoration:none;">Full Pipeline &rarr;</a></div>'
            f'<table class="cad-table"><tbody>{pipe_rows}</tbody></table></div>'
        )

        pipe_right = ""
        if search_links:
            pipe_right = (
                f'<div class="cad-card">'
                f'<h2>Saved Searches</h2>'
                f'{search_links}'
                f'<a href="/pipeline" style="font-size:11px;color:var(--cad-link);'
                f'text-decoration:none;display:block;margin-top:6px;">Manage &rarr;</a></div>'
            )

        sections.append(
            f'<div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;">'
            f'<div>{pipe_left}</div><div>{pipe_right}</div></div>'
        )

    # ── Portfolio section (if deals exist) ──
    if has_portfolio:
        deal_rows = ""
        for d in deals[:8]:
            did = _html.escape(d["deal_id"])
            dname = _html.escape(str(d["name"])[:30])
            deal_rows += (
                f'<tr>'
                f'<td><a href="/deal/{did}" '
                f'style="color:var(--cad-link);text-decoration:none;font-weight:500;">'
                f'{dname}</a></td>'
                f'<td style="font-size:11px;">'
                f'<a href="/ebitda-bridge/{did}" style="color:var(--cad-link);text-decoration:none;">'
                f'Bridge</a> · '
                f'<a href="/ic-memo/{did}" style="color:var(--cad-link);text-decoration:none;">'
                f'Memo</a> · '
                f'<a href="/data-room/{did}" style="color:var(--cad-link);text-decoration:none;">'
                f'Data Room</a></td>'
                f'</tr>'
            )

        alert_items = ""
        if alerts:
            for a in alerts[:3]:
                sev = a.get("severity", "info")
                sev_color = {"red": "var(--cad-neg)", "amber": "var(--cad-warn)"}.get(sev, "var(--cad-text3)")
                alert_items += (
                    f'<div style="display:flex;gap:6px;padding:4px 0;font-size:12px;'
                    f'border-bottom:1px solid var(--cad-border);">'
                    f'<span style="color:{sev_color};font-weight:700;font-size:10px;'
                    f'text-transform:uppercase;">{_html.escape(sev)}</span>'
                    f'<span style="color:var(--cad-text2);">'
                    f'{_html.escape(str(a.get("message", ""))[:60])}</span></div>'
                )

        left = (
            f'<div class="cad-card">'
            f'<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">'
            f'<div style="display:flex;align-items:center;gap:10px;">'
            f'<h2 style="margin:0;">Active Deals ({len(deals)})</h2>'
            f'<span class="cad-section-code">DLS</span></div>'
            f'<a href="/portfolio/monitor" style="font-size:10.5px;font-family:var(--cad-mono);'
            f'letter-spacing:0.06em;text-transform:uppercase;color:var(--cad-link);'
            f'text-decoration:none;">Monitor &rarr;</a></div>'
            f'<table class="cad-table"><tbody>{deal_rows}</tbody></table></div>'
        )

        right = ""
        if alert_items:
            right = (
                f'<div class="cad-card" style="border-left:3px solid var(--cad-neg);">'
                f'<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;">'
                f'<div style="display:flex;align-items:center;gap:10px;">'
                f'<h2 style="margin:0;">Alerts ({len(alerts)})</h2>'
                f'<span class="cad-section-code" style="color:var(--cad-neg);">ALRT</span></div>'
                f'<a href="/alerts" style="font-size:10.5px;font-family:var(--cad-mono);'
                f'letter-spacing:0.06em;text-transform:uppercase;color:var(--cad-link);'
                f'text-decoration:none;">View all &rarr;</a></div>'
                f'{alert_items}</div>'
            )
        else:
            right = (
                f'<div class="cad-card" style="border-left:3px solid var(--cad-pos);">'
                f'<div style="display:flex;align-items:center;gap:10px;margin-bottom:4px;">'
                f'<h2 style="margin:0;">No Active Alerts</h2>'
                f'<span class="cad-section-code" style="color:var(--cad-pos);">OK</span></div>'
                f'<p style="font-size:11.5px;color:var(--cad-text2);">All deals on track.</p></div>'
            )

        sections.append(
            f'<div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;">'
            f'<div>{left}</div><div>{right}</div></div>'
        )

    # ── Market highlights (always shown) ──
    top_states = hcris_df.groupby("state").agg(
        n=("ccn", "count"),
        med_margin=("operating_margin", "median"),
        total_rev=("net_patient_revenue", "sum"),
    ).sort_values("total_rev", ascending=False).head(8)

    state_rows = ""
    for st, row in top_states.iterrows():
        m = row["med_margin"]
        # 5-tier heatmap: >5% green, 2-5% light-green, 0-2% neutral, -3..0 amber, <-3 red
        if m > 0.05:
            heat = "cad-heat-1"
        elif m > 0.02:
            heat = "cad-heat-2"
        elif m > 0:
            heat = "cad-heat-3"
        elif m > -0.03:
            heat = "cad-heat-4"
        else:
            heat = "cad-heat-5"
        state_rows += (
            f'<tr>'
            f'<td><a href="/market-data/state/{_html.escape(str(st))}" '
            f'style="color:var(--cad-link);text-decoration:none;font-weight:600;">'
            f'{_html.escape(str(st))}</a></td>'
            f'<td class="num">{int(row["n"])}</td>'
            f'<td class="num">{_fm(row["total_rev"])}</td>'
            f'<td class="num {heat}" style="font-weight:600;">{m:.1%}</td>'
            f'</tr>'
        )

    # Size distribution
    beds = hcris_df["beds"].dropna()
    size_data = {
        "< 50 beds": int((beds < 50).sum()),
        "50-99": int(((beds >= 50) & (beds < 100)).sum()),
        "100-249": int(((beds >= 100) & (beds < 250)).sum()),
        "250-499": int(((beds >= 250) & (beds < 500)).sum()),
        "500+": int((beds >= 500).sum()),
    }

    size_bars = ""
    max_count = max(size_data.values()) if size_data else 1
    for label, count in size_data.items():
        pct = count / max_count * 100
        size_bars += (
            f'<div style="display:flex;align-items:center;gap:8px;padding:3px 0;font-size:11px;">'
            f'<span style="width:60px;color:var(--cad-text3);">{label}</span>'
            f'<div style="flex:1;background:var(--cad-bg3);border-radius:2px;height:12px;">'
            f'<div style="width:{pct:.0f}%;background:var(--cad-accent);border-radius:2px;'
            f'height:12px;"></div></div>'
            f'<span class="cad-mono" style="width:40px;text-align:right;">{count:,}</span></div>'
        )

    sections.append(
        f'<div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;">'
        f'<div class="cad-card">'
        f'<div style="display:flex;align-items:center;gap:10px;">'
        f'<h2 style="margin:0;">Top Markets by Revenue</h2>'
        f'<span class="cad-section-code">MKT</span></div>'
        f'<table class="cad-table"><thead><tr>'
        f'<th>State</th><th>Hospitals</th><th>Total NPSR</th><th>Med. Margin</th>'
        f'</tr></thead><tbody>{state_rows}</tbody></table></div>'
        f'<div class="cad-card">'
        f'<div style="display:flex;align-items:center;gap:10px;">'
        f'<h2 style="margin:0;">Hospital Size Distribution</h2>'
        f'<span class="cad-section-code">SIZ</span></div>'
        f'<p style="font-size:10.5px;font-family:var(--cad-mono);letter-spacing:0.04em;'
        f'color:var(--cad-text3);margin-bottom:10px;text-transform:uppercase;">'
        f'{n_pe_targets:,} hospitals in 100-500 bed PE target range</p>'
        f'{size_bars}</div></div>'
    )

    # ── Platform capabilities (for new users) ──
    if not has_portfolio:
        sections.append(
            f'<div class="cad-card" style="border-left:3px solid var(--cad-accent);">'
            f'<h2>Getting Started</h2>'
            f'<div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:16px;font-size:12.5px;">'
            f'<div>'
            f'<div style="font-weight:600;color:var(--cad-accent);margin-bottom:4px;">1. Screen</div>'
            f'<p style="color:var(--cad-text2);line-height:1.7;">'
            f'Use the <a href="/predictive-screener" style="color:var(--cad-link);">Deal Screener</a> '
            f'to filter {n_hospitals:,} hospitals by geography, size, margins, and ML-predicted '
            f'RCM improvement potential.</p></div>'
            f'<div>'
            f'<div style="font-weight:600;color:var(--cad-accent);margin-bottom:4px;">2. Analyze</div>'
            f'<p style="color:var(--cad-text2);line-height:1.7;">'
            f'Click any hospital for competitive intel, EBITDA bridge, '
            f'scenario modeling, and a one-click IC memo — all from public data.</p></div>'
            f'<div>'
            f'<div style="font-weight:600;color:var(--cad-accent);margin-bottom:4px;">3. Diligence</div>'
            f'<p style="color:var(--cad-text2);line-height:1.7;">'
            f'Enter seller data in the <strong>Data Room</strong>. Our Bayesian engine '
            f'blends it with ML predictions and recalculates the bridge automatically.</p></div>'
            f'</div></div>'
        )

    # ── Data & Model health ──
    sections.append(
        f'<div class="cad-card" style="font-size:11px;color:var(--cad-text3);'
        f'display:flex;justify-content:space-between;padding:10px 16px;">'
        f'<span>Data: CMS HCRIS FY2022 | {n_hospitals:,} hospitals | '
        f'50 states + DC | {total_beds:,} beds</span>'
        f'<span>'
        f'{source_tag(Source.HCRIS)} {source_tag(Source.ML_PREDICTION)} '
        f'{source_tag(Source.COMPUTED)}'
        f'</span></div>'
    )

    body = "\n".join(sections)

    return chartis_shell(
        body, "SeekingChartis",
        active_nav="/home",
        subtitle=(
            f"{n_hospitals:,} hospitals | {n_pe_targets:,} PE targets | "
            f"{len(deals)} active deals"
        ),
        show_ticker=True,
    )
