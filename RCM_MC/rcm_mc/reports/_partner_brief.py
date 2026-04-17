"""Partner brief: one-page IC-ready HTML exec summary.

The full ``report.html`` is audit-grade — every section carries a "Why this
matters" block, a glossary, methodology, risk register, and scenario explorer.
That's what an analyst defends in IC. It's not what a partner reads before IC.

This module produces a tight single-page ``partner_brief.html`` with:

- Header: target name + CCN + generated date
- Evidence band: data-confidence grade + observed/total ratio
- Three headline KPIs: EBITDA opportunity, EV at multiple, P10→P90 range
- Three key insights (from :func:`rcm_mc.reporting.actionable_insights`)
- Benchmark gap table: target vs industry avg vs top-decile
- Peer percentile summary (if peer comparison ran)
- Management-plan miss headline (if pressure test ran)
- Bottom-line paragraph + next steps
- Footer pointer to the full report

No nav, no explorer, no glossary. Self-contained single-file HTML.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import pandas as pd
import yaml

from ._report_helpers import _build_benchmark_gap_table, _read_csv_if_exists
from .reporting import actionable_insights, pretty_money


_BRIEF_CSS = """
  :root {
    --primary: #0f4c81; --accent: #0891b2;
    --slate: #0f172a; --gray: #475569; --border: #e2e8f0;
    --bg: #ffffff; --card-bg: #f8fafc;
    --green: #059669; --amber: #d97706; --red: #dc2626;
  }
  * { box-sizing: border-box; }
  body {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    margin: 0; padding: 0; background: var(--bg); color: var(--slate);
    line-height: 1.55; font-size: 14px;
  }
  .brief { max-width: 820px; margin: 0 auto; padding: 2rem 2.5rem; }
  header h1 {
    font-size: 1.65rem; font-weight: 700; margin: 0 0 0.25rem 0;
    background: linear-gradient(135deg, var(--primary) 0%, var(--accent) 100%);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    background-clip: text;
  }
  header .meta { color: var(--gray); font-size: 0.85rem; margin-bottom: 1.5rem; }
  .evidence-band {
    padding: 0.85rem 1.1rem; border-radius: 10px;
    font-size: 0.95rem; margin: 0 0 1.5rem 0;
    border-left: 5px solid var(--grade-color, var(--gray));
    background: var(--card-bg);
  }
  .evidence-band.grade-A { --grade-color: var(--green); }
  .evidence-band.grade-B { --grade-color: var(--accent); }
  .evidence-band.grade-C { --grade-color: var(--amber); }
  .evidence-band.grade-D { --grade-color: var(--red); }
  .evidence-band strong { color: var(--slate); }
  .kpi-grid {
    display: grid; grid-template-columns: repeat(3, 1fr); gap: 0.75rem;
    margin: 0 0 1.5rem 0;
  }
  .kpi-card {
    background: var(--card-bg); border: 1px solid var(--border);
    border-radius: 10px; padding: 1rem 1.1rem; text-align: center;
  }
  .kpi-card .label {
    font-size: 0.7rem; font-weight: 600; color: var(--gray);
    text-transform: uppercase; letter-spacing: 0.04em; margin-bottom: 0.25rem;
  }
  .kpi-card .value {
    font-size: 1.45rem; font-weight: 700; color: var(--primary);
    font-variant-numeric: tabular-nums;
  }
  .kpi-card.accent .value { color: var(--accent); }
  h2 {
    font-size: 1.05rem; font-weight: 600; margin: 1.4rem 0 0.5rem 0;
    color: var(--slate); padding-bottom: 0.3rem;
    border-bottom: 1.5px solid var(--border);
  }
  ul.insights { margin: 0.3rem 0 0 1.2rem; padding: 0; }
  ul.insights li { margin: 0.3rem 0; font-size: 0.92rem; }
  table {
    border-collapse: collapse; width: 100%; margin: 0.5rem 0 1rem 0;
    font-size: 0.85rem; background: var(--card-bg); border-radius: 8px;
    overflow: hidden;
  }
  th, td { border: 1px solid var(--border); padding: 7px 10px; text-align: left; }
  td.num { text-align: right; font-variant-numeric: tabular-nums; }
  th { background: #eef2f7; font-weight: 600; color: var(--slate); }
  .badge { display: inline-block; padding: 1px 7px; border-radius: 10px; font-size: 0.75rem; font-weight: 600; }
  .badge-green { background: #ecfdf5; color: var(--green); }
  .badge-amber { background: #fffbeb; color: var(--amber); }
  .badge-red { background: #fef2f2; color: var(--red); }
  .bottom-line {
    background: linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 100%);
    padding: 1rem 1.2rem; border-radius: 10px; margin: 1.25rem 0;
    border-left: 4px solid var(--primary); font-size: 0.95rem;
  }
  .bottom-line strong { color: var(--primary); }
  footer {
    margin-top: 1.75rem; padding-top: 0.75rem; border-top: 1px dashed var(--border);
    font-size: 0.75rem; color: var(--gray); font-style: italic; text-align: center;
  }
  @media print {
    body { font-size: 11pt; }
    .brief { padding: 0.5in; }
    .evidence-band, .kpi-card, .bottom-line { break-inside: avoid; }
  }
"""


def _load_grade(outdir: str) -> Optional[Dict[str, Any]]:
    """Pull grade + counts from provenance.json (set by :mod:`rcm_mc.sources`)."""
    path = os.path.join(outdir, "provenance.json")
    if not os.path.isfile(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            doc = json.load(f)
    except (OSError, json.JSONDecodeError):
        return None
    sources = doc.get("sources") or {}
    counts = sources.get("counts") or {}
    total = int(counts.get("total") or 0)
    if total == 0:
        return None
    return {
        "grade": str(sources.get("grade", "?")),
        "observed": int(counts.get("observed") or 0),
        "prior": int(counts.get("prior") or 0),
        "assumed": int(counts.get("assumed") or 0),
        "total": total,
    }


def _load_cfg(path: Optional[str]) -> Optional[Dict[str, Any]]:
    if not path or not os.path.isfile(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    except (OSError, yaml.YAMLError):
        return None


def _render_evidence_band(grade: Optional[Dict[str, Any]]) -> str:
    if not grade:
        return ""
    g = grade["grade"]
    return (
        f'<div class="evidence-band grade-{g}">'
        f"<strong>Evidence grade {g}</strong>: "
        f"{grade['observed']} of {grade['total']} inputs observed "
        f"({grade['observed'] / grade['total'] * 100:.0f}%), "
        f"{grade['prior']} priors, {grade['assumed']} assumptions."
        "</div>"
    )


def _render_headline(summary_df: pd.DataFrame, ev_multiple: float) -> str:
    if summary_df is None or "ebitda_drag" not in summary_df.index:
        return '<div class="kpi-grid"><div class="kpi-card"><div class="label">No summary data</div></div></div>'
    row = summary_df.loc["ebitda_drag"]
    ebitda_mean = float(row["mean"])
    ev_mean = ebitda_mean * ev_multiple
    ev_p10 = float(row["p10"]) * ev_multiple
    ev_p90 = float(row["p90"]) * ev_multiple
    return f"""
    <div class="kpi-grid">
      <div class="kpi-card">
        <div class="label">EBITDA Opportunity</div>
        <div class="value">{pretty_money(ebitda_mean)}</div>
      </div>
      <div class="kpi-card accent">
        <div class="label">Enterprise Value ({ev_multiple:.0f}x)</div>
        <div class="value">{pretty_money(ev_mean)}</div>
      </div>
      <div class="kpi-card">
        <div class="label">Range (P10 → P90 EV)</div>
        <div class="value">{pretty_money(ev_p10)} → {pretty_money(ev_p90)}</div>
      </div>
    </div>"""


def _render_insights(summary_df: pd.DataFrame, sens_df: Optional[pd.DataFrame], ev_multiple: float) -> str:
    if summary_df is None or "ebitda_drag" not in summary_df.index:
        return ""
    try:
        insights = actionable_insights(summary_df, sens_df, ev_multiple=ev_multiple)
    except (KeyError, ValueError, IndexError):
        # actionable_insights expects a full summary (drag_denial_writeoff,
        # drag_underpay_leakage, etc.); degrade quietly on partial input so the
        # brief still renders the headline KPIs.
        return ""
    if not insights:
        return ""
    top3 = insights[:3]
    bullets = "".join(f"<li>{_escape(item)}</li>" for item in top3)
    return f"<h2>Key insights</h2><ul class='insights'>{bullets}</ul>"


def _escape(s: Any) -> str:
    """Minimal HTML escape for user-visible strings that may contain < > &."""
    from html import escape as _html_escape
    return _html_escape(str(s))


def _render_peer_percentiles(outdir: str) -> str:
    """Compact percentile summary if peer comparison ran."""
    path = os.path.join(outdir, "peer_target_percentiles.csv")
    df = _read_csv_if_exists(path)
    if df is None or df.empty:
        return ""
    rows: List[str] = []
    for _, r in df.iterrows():
        kpi = str(r.get("kpi", "")).replace("_", " ").title()
        target = r.get("target")
        pct = r.get("target_percentile")
        if pd.isna(pct):
            continue
        pct_f = float(pct)
        if pct_f >= 75:
            badge = f'<span class="badge badge-green">{pct_f:.0f}th %ile</span>'
        elif pct_f <= 25:
            badge = f'<span class="badge badge-red">{pct_f:.0f}th %ile</span>'
        else:
            badge = f'<span class="badge badge-amber">{pct_f:.0f}th %ile</span>'
        # Format target value by KPI type
        tgt_str = _fmt_kpi_value(str(r.get("kpi", "")), target)
        rows.append(f"<tr><td>{kpi}</td><td class='num'>{tgt_str}</td><td>{badge}</td></tr>")
    if not rows:
        return ""
    body = "".join(rows)
    return f"""
    <h2>Peer position</h2>
    <p style="color: var(--gray); font-size: 0.85rem; margin: 0.25rem 0;">
      Target's rank against matched CMS HCRIS peers.
    </p>
    <table>
      <tr><th>Metric</th><th>Target</th><th>Rank</th></tr>
      {body}
    </table>"""


def _fmt_kpi_value(kpi: str, v: Any) -> str:
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return "—"
    try:
        f = float(v)
    except (TypeError, ValueError):
        return "—"
    # Derived-ratio KPIs from Brick 22: formatted as percent or per-unit money
    if kpi == "operating_margin" or kpi.endswith("_pct"):
        return f"{f*100:.1f}%"
    if kpi in ("cost_per_patient_day", "npsr_per_bed"):
        return pretty_money(f)
    if kpi == "payer_mix_hhi":
        return f"{f:.3f}"
    if "revenue" in kpi or "expenses" in kpi or "income" in kpi:
        return pretty_money(f)
    # integer count fallback
    return f"{f:,.0f}"


def _render_pe_bridge_and_returns(outdir: str) -> str:
    """PE IC block: value bridge summary + base-case returns + covenant status.

    Loads the four JSON artifacts written by ``pe_integration.py`` and
    surfaces them as the single "deal-math" section a partner skims for
    go/no-go. Bridge chart → IRR/MOIC → covenant headroom is the canonical
    IC pre-read order.
    """
    import json as _json

    bridge_path = os.path.join(outdir, "pe_bridge.json")
    returns_path = os.path.join(outdir, "pe_returns.json")
    covenant_path = os.path.join(outdir, "pe_covenant.json")

    blocks: List[str] = []

    if os.path.isfile(bridge_path) and os.path.isfile(returns_path):
        with open(bridge_path, encoding="utf-8") as f:
            bridge = _json.load(f)
        with open(returns_path, encoding="utf-8") as f:
            returns = _json.load(f)

        # Top-level headline row
        entry_ev = bridge.get("entry_ev", 0)
        exit_ev = bridge.get("exit_ev", 0)
        moic = returns.get("moic", 0)
        irr = returns.get("irr", 0)
        hold = returns.get("hold_years", 0)

        moic_class = "badge-green" if moic >= 2.5 else (
            "badge-amber" if moic >= 2.0 else "badge-red"
        )
        irr_class = "badge-green" if irr >= 0.25 else (
            "badge-amber" if irr >= 0.18 else "badge-red"
        )

        # Bridge components table
        rows = []
        for comp in bridge.get("components") or []:
            step = _escape(str(comp.get("step", "")))
            value = pretty_money(float(comp.get("value") or 0))
            share = comp.get("share_of_creation")
            share_cell = ""
            if share is not None:
                try:
                    share_cell = f"{float(share)*100:+.0f}%"
                except (TypeError, ValueError):
                    pass
            note = _escape(str(comp.get("note", "")))
            is_endpoint = step in ("Entry EV", "Exit EV")
            weight = "font-weight: 600;" if is_endpoint else ""
            rows.append(
                f"<tr style='{weight}'><td>{step}</td>"
                f"<td class='num'>{value}</td>"
                f"<td class='num'>{share_cell}</td>"
                f"<td style='color: var(--gray); font-size: 0.85rem;'>{note}</td></tr>"
            )
        bridge_table = "".join(rows)

        blocks.append(f"""
        <h2>PE Deal Math — {hold:g}-year hold</h2>
        <p style="margin: 0.25rem 0;">
          <span class="badge {moic_class}">MOIC {moic:.2f}x</span>
          <span class="badge {irr_class}">IRR {irr*100:.1f}%</span>
          <span style="color: var(--gray); font-size: 0.9rem;">
            Entry EV {pretty_money(entry_ev)} → Exit EV {pretty_money(exit_ev)}
          </span>
        </p>
        <table>
          <tr><th>Bridge step</th><th>Value</th><th>Share</th><th>Basis</th></tr>
          {bridge_table}
        </table>""")

    if os.path.isfile(covenant_path):
        with open(covenant_path, encoding="utf-8") as f:
            cov = _json.load(f)
        headroom = float(cov.get("covenant_headroom_turns") or 0)
        cushion = float(cov.get("ebitda_cushion_pct") or 0)
        status_cls = "badge-green" if headroom >= 1.0 else (
            "badge-amber" if headroom >= 0 else "badge-red"
        )
        status_label = "SAFE" if headroom >= 1.0 else (
            "TIGHT" if headroom >= 0 else "TRIPPED"
        )
        blocks.append(f"""
        <h3 style="margin-top: 1rem;">Covenant headroom</h3>
        <p style="margin: 0.25rem 0;">
          <span class="badge {status_cls}">{status_label}</span>
          Actual {cov.get('actual_leverage', 0):.2f}x vs covenant
          {cov.get('covenant_max_leverage', 0):.2f}x —
          {headroom:+.2f} turns headroom,
          EBITDA cushion {cushion*100:+.0f}% (trips at
          {pretty_money(float(cov.get('covenant_trips_at_ebitda') or 0))}).
        </p>""")

    return "".join(blocks)


def _render_trend_signals(outdir: str) -> str:
    """Compact YoY signals block if multi-year HCRIS data was materialized.

    Pulls ``trend_signals.csv`` written by ``rcm-mc run``. Formats each row
    as one line with a colored direction glyph + metric + delta + start→end.
    """
    path = os.path.join(outdir, "trend_signals.csv")
    df = _read_csv_if_exists(path)
    if df is None or df.empty:
        return ""
    # Color by severity (metric-aware) so "up" on operating_expenses doesn't
    # read green. Falls back to amber/neutral when severity is missing (older
    # cached CSVs from pre-B30 runs).
    severity_class = {"favorable": "badge-green", "concerning": "badge-red",
                      "neutral": "badge-amber"}
    arrow_glyph = {"up": "↑", "down": "↓", "flat": "→"}

    rows: List[str] = []
    for _, r in df.iterrows():
        direction = str(r.get("direction") or "flat")
        glyph = arrow_glyph.get(direction, "·")
        severity = str(r.get("severity") or "neutral")
        badge_cls = severity_class.get(severity, "badge-amber")
        metric = str(r.get("metric") or "").replace("_", " ")
        pts = r.get("pts_change")
        pct = r.get("pct_change")
        if pd.notna(pts):
            delta_txt = f"{float(pts):+.1f} pts"
            start_txt = _fmt_kpi_value(str(r.get("metric") or ""), r.get("start_value"))
            end_txt = _fmt_kpi_value(str(r.get("metric") or ""), r.get("end_value"))
        else:
            delta_txt = f"{float(pct)*100:+.1f}%" if pd.notna(pct) else "—"
            start_txt = _fmt_kpi_value(str(r.get("metric") or ""), r.get("start_value"))
            end_txt = _fmt_kpi_value(str(r.get("metric") or ""), r.get("end_value"))
        rows.append(
            f"<tr><td>{_escape(metric)}</td>"
            f"<td><span class='badge {badge_cls}'>{glyph} {_escape(delta_txt)}</span></td>"
            f"<td class='num'>{_escape(start_txt)} → {_escape(end_txt)}</td></tr>"
        )
    if not rows:
        return ""

    # Use first row's start/end years for section header
    first = df.iloc[0]
    sy = int(first["start_year"]) if pd.notna(first.get("start_year")) else None
    ey = int(first["end_year"]) if pd.notna(first.get("end_year")) else None
    span = f" ({sy}→{ey})" if sy and ey else ""

    # Watchlist header — partners skim this before reading the table
    severities = df["severity"].tolist() if "severity" in df.columns else []
    n_concerning = sum(1 for s in severities if s == "concerning")
    n_favorable = sum(1 for s in severities if s == "favorable")
    watchlist_parts: List[str] = []
    if n_concerning:
        watchlist_parts.append(
            f"<span class='badge badge-red'>{n_concerning} concerning</span>"
        )
    if n_favorable:
        watchlist_parts.append(
            f"<span class='badge badge-green'>{n_favorable} favorable</span>"
        )
    watchlist_html = ""
    if watchlist_parts:
        watchlist_html = (
            "<p style='margin: 0.25rem 0;'>Watchlist: "
            + " ".join(watchlist_parts) + "</p>"
        )

    body = "".join(rows)
    return f"""
    <h2>Multi-year trend{_escape(span)}</h2>
    <p style="color: var(--gray); font-size: 0.85rem; margin: 0.25rem 0;">
      HCRIS first → last fiscal year on file for the target.
    </p>
    {watchlist_html}
    <table>
      <tr><th>Metric</th><th>Change</th><th>Start → End</th></tr>
      {body}
    </table>"""


def _render_pressure_headline(outdir: str) -> str:
    """One-line summary from the pressure test miss scenarios, if present."""
    path = os.path.join(outdir, "pressure_test_miss_scenarios.csv")
    df = _read_csv_if_exists(path)
    if df is None or df.empty or "achievement" not in df.columns:
        return ""
    try:
        zero = df[df["achievement"] == 0.0]["ebitda_drag_mean"].iloc[0]
        full = df[df["achievement"] == 1.0]["ebitda_drag_mean"].iloc[0]
    except (IndexError, KeyError):
        return ""
    recoverable = zero - full
    return f"""
    <h2>Management plan pressure-test</h2>
    <p style="margin: 0.3rem 0;">
      Full plan delivery would take EBITDA drag from <strong>{pretty_money(zero)}</strong>
      (status quo) to <strong>{pretty_money(full)}</strong> —
      <strong>{pretty_money(recoverable)}</strong> of the modeled drag is contingent
      on management execution. See Plan Miss Scenarios tab for 50% / 75% paths.
    </p>"""


def _render_bottom_line(
    summary_df: pd.DataFrame,
    ev_multiple: float,
    grade: Optional[Dict[str, Any]],
) -> str:
    if summary_df is None or "ebitda_drag" not in summary_df.index:
        return '<div class="bottom-line">Run the model with valid configs to size the deal opportunity.</div>'
    ebitda_mean = float(summary_df.loc["ebitda_drag", "mean"])
    ev_mean = ebitda_mean * ev_multiple
    ev_p10 = float(summary_df.loc["ebitda_drag", "p10"]) * ev_multiple
    ev_p90 = float(summary_df.loc["ebitda_drag", "p90"]) * ev_multiple

    grade_clause = ""
    if grade:
        g = grade["grade"]
        if g in ("A", "B"):
            grade_clause = f" Evidence grade <strong>{g}</strong> supports underwriting the modeled range."
        elif g == "C":
            grade_clause = f" Evidence grade <strong>{g}</strong> — validate the top data gaps before closing."
        elif g == "D":
            grade_clause = f" Evidence grade <strong>{g}</strong> — the headline is directionally right but needs target-data calibration before underwriting."

    return f"""
    <div class="bottom-line">
      <strong>Bottom line.</strong> Closing the gap between target RCM performance and
      best-practice benchmarks represents a <strong>{pretty_money(ev_mean)}</strong>
      enterprise-value opportunity at {ev_multiple:.0f}x
      (range {pretty_money(ev_p10)} to {pretty_money(ev_p90)}).{grade_clause}
    </div>"""


def build_partner_brief(
    outdir: str,
    *,
    hospital_name: Optional[str] = None,
    ev_multiple: float = 8.0,
    actual_config_path: Optional[str] = None,
    benchmark_config_path: Optional[str] = None,
    out_path: Optional[str] = None,
) -> str:
    """Render ``partner_brief.html`` in ``outdir`` and return its path."""
    outdir = str(outdir)
    out_path = out_path or os.path.join(outdir, "partner_brief.html")

    summary_df = _read_csv_if_exists(os.path.join(outdir, "summary.csv"), index_col=0)
    sens_df = _read_csv_if_exists(os.path.join(outdir, "sensitivity.csv"))
    # sensitivity.csv may have been moved into _detail/ by the bundle step
    if sens_df is None:
        sens_df = _read_csv_if_exists(os.path.join(outdir, "_detail", "sensitivity.csv"))

    grade = _load_grade(outdir)
    actual_cfg = _load_cfg(actual_config_path)
    benchmark_cfg = _load_cfg(benchmark_config_path)

    ccn = None
    if actual_cfg and isinstance(actual_cfg.get("hospital"), dict):
        ccn = actual_cfg["hospital"].get("ccn")
    hosp_display = (
        hospital_name
        or (actual_cfg or {}).get("hospital", {}).get("name")
        or "Target Hospital"
    )

    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    meta_line = f"{_escape(hosp_display)} | Generated {ts} | Confidential"
    if ccn:
        meta_line = f"{_escape(hosp_display)} | CCN {_escape(ccn)} | Generated {ts} | Confidential"

    gap_table_html = _build_benchmark_gap_table(actual_cfg, benchmark_cfg)

    parts: List[str] = [
        "<!doctype html>",
        '<html lang="en"><head><meta charset="utf-8">',
        f"<title>RCM Partner Brief — {_escape(hosp_display)}</title>",
        f"<style>{_BRIEF_CSS}</style></head><body>",
        '<div class="brief">',
        "<header>",
        f"<h1>RCM Due Diligence Brief — {_escape(hosp_display)}</h1>",
        f'<div class="meta">{meta_line}</div>',
        "</header>",
        _render_evidence_band(grade),
        _render_headline(summary_df, ev_multiple),
        _render_insights(summary_df, sens_df, ev_multiple),
    ]
    if gap_table_html:
        # The shared helper outputs "Benchmark Gap Analysis" as an h3 in a card;
        # strip the heading here so the brief stays visually lean.
        parts.append("<h2>Benchmark gap</h2>")
        parts.append(gap_table_html)
    parts.append(_render_peer_percentiles(outdir))
    parts.append(_render_trend_signals(outdir))
    parts.append(_render_pe_bridge_and_returns(outdir))
    parts.append(_render_pressure_headline(outdir))
    parts.append(_render_bottom_line(summary_df, ev_multiple, grade))
    parts.append(
        '<footer>Full audit-grade report at <code>report.html</code> — '
        "includes methodology, glossary, sensitivity detail, and scenario explorer.</footer>"
    )
    parts.append("</div></body></html>")

    from ..ui._html_polish import polish_tables_in_html
    html = polish_tables_in_html("\n".join(parts))

    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)
    return out_path
