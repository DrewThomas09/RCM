"""Named-Failure Library — /named-failures."""
from __future__ import annotations

import html as _html
from rcm_mc.ui._chartis_kit import P, chartis_shell, ck_kpi_block


def _tier_color(t: str) -> str:
    return {
        "CRITICAL": P["negative"],
        "HIGH":     P["negative"],
        "MEDIUM":   P["warning"],
        "LOW":      P["accent"],
        "CLEAN":    P["text_dim"],
    }.get(t, P["text_dim"])


def _severity_color(s: str) -> str:
    return {
        "critical": P["negative"],
        "warning":  P["warning"],
        "context":  P["text_dim"],
    }.get(s, P["text_dim"])


def _fmt_mm(v):
    if v is None:
        return "—"
    return f"${v:,.0f}M"


def _fmt_turns(v):
    if v is None:
        return "—"
    return f"{v:.1f}x"


def _pattern_catalog_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; neg = P["negative"]
    cols = [("ID", "left"), ("Case Name", "left"), ("Filing Yr", "right"),
            ("Jurisdiction", "left"), ("Sector", "left"),
            ("Pre-Pet EV", "right"), ("Pre-Pet EBITDA", "right"),
            ("Peak Leverage", "right"), ("Root Cause", "left")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, p in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        ebitda_cell = _fmt_mm(p.pre_petition_ebitda_mm)
        ebitda_color = neg if p.pre_petition_ebitda_mm is not None and p.pre_petition_ebitda_mm < 0 else text
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:700">{_html.escape(p.pattern_id)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:11px;color:{text};font-weight:700;max-width:240px">{_html.escape(p.case_name)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{acc};font-weight:600">{p.filing_year}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{text_dim}">{_html.escape(p.jurisdiction)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim};max-width:220px">{_html.escape(p.sector)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{_fmt_mm(p.pre_petition_ev_mm)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{ebitda_color};font-weight:700">{ebitda_cell}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{_fmt_turns(p.peak_leverage_turns)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim};max-width:540px">{_html.escape(p.root_cause_short)}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _coverage_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]; neg = P["negative"]
    cols = [("ID", "left"), ("Case", "left"), ("Sector", "left"),
            ("Corpus Matches", "right"), ("High-Match (≥60)", "right"),
            ("Critical Signals", "right"), ("Keywords", "right"),
            ("Est. EV at Risk ($M)", "right")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, c in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        hi_c = neg if c.high_match_count >= 3 else (acc if c.high_match_count >= 1 else text_dim)
        ev_c = neg if c.estimated_aggregate_ev_at_risk_mm >= 1000 else (
               acc if c.estimated_aggregate_ev_at_risk_mm >= 100 else text_dim)
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:700">{_html.escape(c.pattern_id)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:11px;color:{text};font-weight:600;max-width:240px">{_html.escape(c.case_name)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim};max-width:220px">{_html.escape(c.sector)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{c.corpus_matches:,}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{hi_c};font-weight:700">{c.high_match_count}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{c.critical_signals}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{c.keyword_count}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{ev_c};font-weight:700">${c.estimated_aggregate_ev_at_risk_mm:,.1f}M</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _exposure_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]
    cols = [("Deal", "left"), ("Year", "right"), ("Buyer", "left"),
            ("Top Pattern Matched", "left"), ("Match Score", "right"),
            ("Patterns Matched", "right"), ("Risk Tier", "center")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, e in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        tc = _tier_color(e.risk_tier)
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">{_html.escape(e.deal_name)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{e.year or "—"}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim};max-width:220px">{_html.escape(e.buyer)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{acc};max-width:260px">{_html.escape(e.top_pattern_id)} — {_html.escape(e.top_pattern_case[:36])}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{tc};font-weight:700">{e.top_match_score:.2f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{e.total_patterns_matched}</td>',
            f'<td style="text-align:center;padding:5px 10px"><span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{tc};border:1px solid {tc};border-radius:2px;letter-spacing:0.06em">{_html.escape(e.risk_tier)}</span></td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _signals_table(patterns) -> str:
    """Flattened view: one row per (pattern × threshold)."""
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]
    cols = [("Pattern", "left"), ("Signal Name", "left"),
            ("Threshold", "left"), ("Severity", "center")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    rowi = 0
    for p in patterns:
        for t in p.thresholds:
            rb = panel_alt if rowi % 2 == 0 else bg
            rowi += 1
            sc = _severity_color(t.severity)
            cells = [
                f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">{_html.escape(p.pattern_id)} — {_html.escape(p.case_name[:28])}</td>',
                f'<td style="text-align:left;padding:5px 10px;font-size:11px;color:{text};max-width:280px">{_html.escape(t.signal_name)}</td>',
                f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{acc};max-width:340px">{_html.escape(t.threshold_description)}</td>',
                f'<td style="text-align:center;padding:5px 10px"><span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{sc};border:1px solid {sc};border-radius:2px;letter-spacing:0.06em">{_html.escape(t.severity.upper())}</span></td>',
            ]
            trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _citations_table(patterns) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]
    cols = [("Pattern", "left"), ("Case", "left"), ("Citations", "left")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, p in enumerate(patterns):
        rb = panel_alt if i % 2 == 0 else bg
        cite_html = "<br>".join(f"• {_html.escape(c)}" for c in p.citations)
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:700;vertical-align:top">{_html.escape(p.pattern_id)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:11px;color:{acc};font-weight:600;vertical-align:top;max-width:220px">{_html.escape(p.case_name)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim};max-width:760px;vertical-align:top;line-height:1.5">{cite_html}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def render_named_failure_library(params: dict = None) -> str:
    from rcm_mc.data_public.named_failure_library import compute_named_failure_library
    r = compute_named_failure_library()

    panel = P["panel"]; panel_alt = P["panel_alt"]
    border = P["border"]; text = P["text"]; text_dim = P["text_dim"]
    acc = P["accent"]

    kpi_strip = (
        ck_kpi_block("Named Patterns", str(r.total_patterns), "", "") +
        ck_kpi_block("Signal Thresholds", str(r.total_signals), "", "") +
        ck_kpi_block("Critical Signals", str(r.total_critical_signals), "", "") +
        ck_kpi_block("Deals w/ Match", f"{r.deals_with_any_match:,}", "", "") +
        ck_kpi_block("CRITICAL Tier", str(r.critical_risk_deals), "", "") +
        ck_kpi_block("Aggregate EV at Risk", f"${r.aggregate_ev_at_risk_mm:,.0f}M", "", "") +
        ck_kpi_block("Corpus Deals", f"{r.corpus_deal_count:,}", "", "")
    )

    catalog_tbl = _pattern_catalog_table(r.patterns)
    coverage_tbl = _coverage_table(r.pattern_coverage)
    exposure_tbl = _exposure_table(r.deal_exposures)
    signals_tbl = _signals_table(r.patterns)
    cites_tbl = _citations_table(r.patterns)

    cell = f"background:{panel};border:1px solid {border};padding:16px;margin-bottom:16px"
    h3 = f"font-size:11px;font-weight:600;letter-spacing:0.08em;color:{text_dim};text-transform:uppercase;margin-bottom:10px"

    body = f"""
<div style="padding:20px;max-width:1400px;margin:0 auto">
  <div style="margin-bottom:20px">
    <h1 style="font-size:18px;font-weight:700;color:{text};letter-spacing:0.02em">Named-Failure Library — Healthcare-PE Bankruptcy Pattern Engine</h1>
    <p style="font-size:12px;color:{text_dim};margin-top:4px">{r.total_patterns} named patterns · {r.total_signals} signal thresholds ({r.total_critical_signals} critical) · {r.deals_with_any_match:,} corpus deals match ≥1 pattern · {r.critical_risk_deals} CRITICAL-tier · ${r.aggregate_ev_at_risk_mm:,.0f}M aggregate EV at risk across pattern-matched deals — Blueprint Moat Layer 3 (the 'Wikipedia of RCM diligence failures')</p>
  </div>
  <div style="display:flex;flex-wrap:wrap;gap:8px;margin-bottom:20px">{kpi_strip}</div>
  <div style="{cell}"><div style="{h3}">Named-Failure Catalog — 16 Decomposed Cases</div>{catalog_tbl}</div>
  <div style="{cell}"><div style="{h3}">Pattern Coverage — Corpus Matches + Estimated EV at Risk per Pattern</div>{coverage_tbl}</div>
  <div style="{cell}"><div style="{h3}">Top 60 Corpus Deal Exposures — Live Pattern-Match Scores</div>{exposure_tbl}</div>
  <div style="{cell}"><div style="{h3}">Signal Threshold Catalog — per Pattern</div>{signals_tbl}</div>
  <div style="{cell}"><div style="{h3}">Primary-Source Citations</div>{cites_tbl}</div>
  <div style="background:{panel_alt};border:1px solid {border};border-left:3px solid {acc};padding:12px 16px;font-size:11px;color:{text_dim};margin-bottom:16px">
    <strong style="color:{text}">Named-Failure Library Thesis:</strong>
    Every healthcare-PE bankruptcy since 2015 decomposed into (a) root-cause mechanism, (b) pre-facto signals
    that would have flagged it, (c) specific numerical/categorical thresholds, (d) primary-source citations from
    bankruptcy filings, FTC consent orders, and DOJ settlements.
    The library's match() engine scores every corpus deal against every pattern's keyword + sector + structural
    fingerprint — producing a live "what's your deal most resemble" signal pre-close.
    Current coverage: Steward (NF-01), Envision (NF-02), APP (NF-03), Cano (NF-04), Prospect (NF-05),
    Wellpath (NF-06), Quorum (NF-07), Adeptus (NF-08), Hahnemann (NF-09), CareMax (NF-10),
    Envision-USAP-TeamHealth FTC cluster (NF-11), Babylon (NF-12),
    21st Century Oncology (NF-13), IntegraMed (NF-14), Pipeline Health (NF-15), Akumin (NF-16).
    Top pattern coverage by corpus matches surfaces: hospital / health-system deals broadly match
    Steward + Prospect + Pipeline + Quorum + Hahnemann (the REIT-sale-leaseback + safety-net + rural-spin-off
    family); specialty-physician-rollup deals match Envision + APP + USAP (NSA + antitrust cluster);
    MA-risk primary care deals match Cano + CareMax + Babylon. The CRITICAL tier is the highest-confidence
    pre-close watchlist — deals whose keyword and sector footprint align with ≥ 2 named patterns at ≥ 70 match score.
    Defensibility: this library requires reading bankruptcy filings, first-day declarations, examiner reports,
    and mapping deal structure to failure mechanism. A single analyst adds ~1–2 patterns per month; the library
    compounds over time.
    Unlike catalog-only competitors, every pattern here is callable via
    <code style="color:{acc};font-family:JetBrains Mono,monospace">_match_one(deal, pattern)</code>
    and runs against any live target's name / notes / buyer / sector fields in sub-second time.
  </div>
</div>"""

    return chartis_shell(body, "Named-Failure Library", active_nav="/named-failures")
