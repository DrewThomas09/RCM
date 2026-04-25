"""Regulatory-Arbitrage Collapse Detector — /reg-arbitrage."""
from __future__ import annotations

import html as _html

from rcm_mc.ui._chartis_kit import P, chartis_shell, ck_kpi_block


def _sev_color(sev: str) -> str:
    return {
        "critical": P["critical"],
        "high":     P["negative"],
        "medium":   P["warning"],
        "low":      P["positive"],
    }.get(sev, P["text_dim"])


def _rec_color(rec: str) -> str:
    return {
        "STOP":                    P["critical"],
        "PROCEED_WITH_CONDITIONS": P["warning"],
        "PROCEED":                 P["positive"],
    }.get(rec, P["text_dim"])


def _arbitrage_definitions_table(items) -> str:
    bg = P["panel"]
    panel_alt = P["panel_alt"]
    border = P["border"]
    text = P["text"]
    text_dim = P["text_dim"]
    acc = P["accent"]
    cols = [
        ("ID", "left"), ("Arbitrage", "left"), ("Policy Anchor", "left"),
        ("Collapse Event", "left"), ("Collapse Date", "right"),
        ("Primary Specialties", "left"), ("NF Parallels", "left"),
    ]
    ths = "".join(
        f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>'
        for c, a in cols
    )
    trs = []
    for i, d in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        nf = ", ".join(d.failure_pattern_refs) if d.failure_pattern_refs else "—"
        cells = [
            f'<td style="padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{acc};font-weight:700">{_html.escape(d.arbitrage_id)}</td>',
            f'<td style="padding:5px 10px;font-size:11px;color:{text};font-weight:700">{_html.escape(d.short_name)}</td>',
            f'<td style="padding:5px 10px;font-size:10px;color:{text_dim};max-width:280px">{_html.escape(d.policy_anchor)}</td>',
            f'<td style="padding:5px 10px;font-size:10px;color:{text_dim};max-width:300px">{_html.escape(d.collapse_event)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{P["warning"]}">{_html.escape(d.collapse_date)}</td>',
            f'<td style="padding:5px 10px;font-size:10px;color:{text_dim};max-width:240px">{_html.escape(", ".join(d.primary_specialties))}</td>',
            f'<td style="padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{text_dim}">{_html.escape(nf)}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (
        f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
        f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>'
    )


def _portfolio_rollups_table(items) -> str:
    bg = P["panel"]
    panel_alt = P["panel_alt"]
    border = P["border"]
    text = P["text"]
    text_dim = P["text_dim"]
    cols = [
        ("ID", "left"), ("Arbitrage", "left"),
        ("Crit", "right"), ("High", "right"), ("Medium", "right"),
        ("Mean", "right"), ("P90", "right"), ("Max", "right"),
        ("Top Deal", "left"), ("Top Score", "right"),
    ]
    ths = "".join(
        f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>'
        for c, a in cols
    )
    trs = []
    for i, r in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        cells = [
            f'<td style="padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{P["accent"]};font-weight:700">{_html.escape(r.arbitrage_id)}</td>',
            f'<td style="padding:5px 10px;font-size:11px;color:{text};font-weight:700">{_html.escape(r.short_name)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{P["critical"]};font-weight:700">{r.deals_at_critical}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{P["negative"]};font-weight:700">{r.deals_at_high}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{P["warning"]}">{r.deals_at_medium}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{r.mean_score:.1f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{r.p90_score:.1f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{r.max_score:.1f}</td>',
            f'<td style="padding:5px 10px;font-size:10px;color:{text};max-width:300px">{_html.escape(r.top_deal_name[:60])}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{P["critical"]};font-weight:700">{r.top_deal_score:.1f}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (
        f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
        f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>'
    )


def _steward_matches_table(items) -> str:
    bg = P["panel"]
    panel_alt = P["panel_alt"]
    border = P["border"]
    text = P["text"]
    text_dim = P["text_dim"]
    if not items:
        return f'<div style="padding:12px;color:{text_dim};font-size:11px;font-style:italic">No deals stack ≥3 high-fragility arbitrages — Steward / Envision / CARD pattern absent from corpus.</div>'
    cols = [
        ("Deal", "left"), ("Year", "right"), ("Buyer", "left"),
        ("Composite", "right"), ("Matched", "left"),
        ("NF Parallels", "left"), ("Recommendation", "left"),
    ]
    ths = "".join(
        f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>'
        for c, a in cols
    )
    trs = []
    for i, m in enumerate(items[:30]):
        rb = panel_alt if i % 2 == 0 else bg
        rc = _rec_color(m.pre_mortem_recommendation)
        cells = [
            f'<td style="padding:5px 10px;font-size:11px;color:{text};font-weight:700;max-width:340px">{_html.escape(m.deal_name[:80])}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{m.deal_year}</td>',
            f'<td style="padding:5px 10px;font-size:10px;color:{text_dim};max-width:200px">{_html.escape(m.buyer[:50])}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:12px;color:{P["critical"]};font-weight:700">{m.composite_score:.1f}</td>',
            f'<td style="padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{P["accent"]}">{_html.escape(", ".join(m.matched_arbitrages))}</td>',
            f'<td style="padding:5px 10px;font-size:10px;color:{text_dim};max-width:260px">{_html.escape(", ".join(m.parallel_to_named_failures[:3]))}</td>',
            f'<td style="padding:5px 10px"><span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{rc};border:1px solid {rc};border-radius:2px;letter-spacing:0.06em;font-weight:700">{_html.escape(m.pre_mortem_recommendation)}</span></td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (
        f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
        f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>'
    )


def _top_profiles_table(profiles, limit: int = 25) -> str:
    bg = P["panel"]
    panel_alt = P["panel_alt"]
    border = P["border"]
    text = P["text"]
    text_dim = P["text_dim"]
    rows = sorted(profiles, key=lambda p: p.collapse_index, reverse=True)[:limit]
    cols = [
        ("Deal", "left"), ("Year", "right"), ("Sector", "left"),
        ("AC-1 NSA", "right"), ("AC-2 340B", "right"),
        ("AC-3 V28", "right"), ("AC-4 Medicaid", "right"),
        ("AC-5 REACH", "right"),
        ("Collapse Index", "right"), ("Dominant", "left"),
    ]
    ths = "".join(
        f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>'
        for c, a in cols
    )
    trs = []
    for i, p in enumerate(rows):
        rb = panel_alt if i % 2 == 0 else bg

        def cell(score: float) -> str:
            sev = "critical" if score >= 75 else "high" if score >= 55 else "medium" if score >= 30 else "low"
            color = _sev_color(sev)
            return f'<td style="text-align:right;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{color};font-weight:600">{score:.1f}</td>'

        cells = [
            f'<td style="padding:5px 10px;font-size:11px;color:{text};font-weight:700;max-width:320px">{_html.escape(p.deal_name[:75])}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{p.deal_year}</td>',
            f'<td style="padding:5px 10px;font-size:10px;color:{text_dim};max-width:160px">{_html.escape(p.sector_inferred)}</td>',
            cell(p.nsa_score),
            cell(p.pharmacy_340b_score),
            cell(p.ma_v28_score),
            cell(p.medicaid_mco_score),
            cell(p.aco_reach_score),
            f'<td style="text-align:right;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:12px;color:{P["critical"]};font-weight:700">{p.collapse_index:.1f}</td>',
            f'<td style="padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{P["accent"]}">{_html.escape(p.dominant_arbitrage)}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (
        f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
        f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>'
    )


def render_regulatory_arbitrage_collapse(qp: dict) -> str:
    from rcm_mc.data_public.regulatory_arbitrage_collapse import (
        compute_regulatory_arbitrage_collapse,
    )

    r = compute_regulatory_arbitrage_collapse()

    panel = P["panel"]
    panel_alt = P["panel_alt"]
    border = P["border"]
    text = P["text"]
    text_dim = P["text_dim"]
    acc = P["accent"]

    kpi_strip = (
        ck_kpi_block("Arbitrages", str(r.total_arbitrages), "AC-1 .. AC-5", "")
        + ck_kpi_block("Deals Scored", f"{r.total_deals_scored:,}", "from corpus", "")
        + ck_kpi_block("High-Fragility", f"{r.total_high_fragility_deals:,}", "≥1 arb at high+", "")
        + ck_kpi_block("Steward-Pattern", str(r.total_steward_pattern_deals), "≥3 high-frag arbs", "")
        + ck_kpi_block("Mean Collapse Index", f"{r.portfolio_collapse_index_mean:.1f}", "/ 100", "")
        + ck_kpi_block("Corpus Deals", f"{r.corpus_deal_count:,}", "", "")
    )

    cell = f"background:{panel};border:1px solid {border};padding:16px;margin-bottom:16px"
    h3 = f"font-size:11px;font-weight:600;letter-spacing:0.08em;color:{text_dim};text-transform:uppercase;margin-bottom:10px"

    body = f"""
<div style="padding:20px;max-width:1500px;margin:0 auto">
  <div style="margin-bottom:20px">
    <h1 style="font-size:18px;font-weight:700;color:{text};letter-spacing:0.02em">Regulatory-Arbitrage Collapse Detector — Gap J2 · <a href="/reg-arbitrage" style="font-family:JetBrains Mono,monospace;font-size:12px;color:{acc};text-decoration:none">/reg-arbitrage</a></h1>
    <p style="font-size:12px;color:{text_dim};margin-top:4px">Scores every corpus deal against five named regulatory arbitrages on a 0-100 fragility index — NSA / 340B / V28 / Medicaid MCO / ACO REACH — and surfaces the deals that stack ≥3 of them in the Steward / Envision / CARD pattern. Numpy-only · stdlib parsers · ProvenanceTracker on every score · KB {_html.escape(r.kb_version)} effective {_html.escape(r.kb_effective_date)}</p>
  </div>
  <div style="display:flex;flex-wrap:wrap;gap:8px;margin-bottom:20px">{kpi_strip}</div>

  <div style="{cell}"><div style="{h3}">The Five Named Arbitrages — Policy Anchor → Collapse Event</div>{_arbitrage_definitions_table(r.arbitrage_definitions)}</div>

  <div style="{cell}"><div style="{h3}">Portfolio Rollup — Per-Arbitrage Severity Distribution</div>{_portfolio_rollups_table(r.portfolio_rollups)}</div>

  <div style="{cell}"><div style="{h3}">Top 25 Most-Fragile Deals — Collapse Index Sort (Quadratic-Mean Roll-Up)</div>{_top_profiles_table(r.deal_profiles, 25)}</div>

  <div style="{cell}"><div style="{h3}">Steward-Pattern Matches — ≥3 Arbitrages at High Severity (Pre-Mortem)</div>{_steward_matches_table(r.steward_pattern_matches)}</div>

  <div style="background:{panel_alt};border:1px solid {border};border-left:3px solid {acc};padding:12px 16px;font-size:11px;color:{text_dim}">
    <strong style="color:{text}">Gap J2 thesis:</strong>
    Healthcare-PE diligence has historically priced regulatory arbitrage as durable revenue. Five
    of those arbitrages have collapsed (or are on a known collapse path) — NSA in 2022, 340B
    contract-pharmacy 2020-2024, MA V28 2024-2026 phase-in, Medicaid MCO concentration post-PHE,
    ACO REACH PY2026 transition. The Steward / Envision / CARD pattern is what happens when a
    single deal stacks <em>three or more</em> of these into one capital structure — the
    refinancing window closes before any single arbitrage gets re-priced.
    <br><br>
    <strong style="color:{text}">How to read the index:</strong>
    Per-arbitrage scores 0-100, severity bucketed at 30/55/75. Collapse index is a
    weight-quadratic mean (so a single 90 dominates five 30s — that's the Steward
    fingerprint). Steward-pattern match requires ≥3 arbitrages at severity ≥ high.
    Pre-mortem recommendation: STOP at composite ≥70, PROCEED_WITH_CONDITIONS at 55-70,
    PROCEED below.
    <br><br>
    <strong style="color:{text}">Provenance:</strong>
    Every per-arbitrage decision logs a primary-source citation — NSA / 45 CFR / IDR PUF for
    AC-1; HRSA OPAIS / Sanofi v HRSA / Genesis HC v Becerra for AC-2; CMS-HCC v28 / MedPAC for
    AC-3; CMS PHE Tracker / KFF / MACPAC for AC-4; CMS Innovation Center / MedPAC Ch 16 for
    AC-5. {len(r.provenance_entries):,} provenance entries were emitted on this run.
    <br><br>
    <strong style="color:{text}">Integration:</strong>
    Feeds <code style="color:{acc};font-family:JetBrains Mono,monospace">/named-failures</code>
    (NF-XX parallels), <code style="color:{acc};font-family:JetBrains Mono,monospace">/adversarial-engine</code>
    (bear-case overlay), and <code style="color:{acc};font-family:JetBrains Mono,monospace">/ic-brief</code>
    (per-target collapse-index line). Surfaces in P02 (quarterly market-structure scan) and
    P16 (failed-deal pre-mortem) prompts.
  </div>
</div>"""

    return chartis_shell(body, "Regulatory-Arbitrage Collapse — J2", active_nav="/reg-arbitrage")
