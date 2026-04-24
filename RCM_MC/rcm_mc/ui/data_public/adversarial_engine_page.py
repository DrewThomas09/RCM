"""Adversarial Diligence Engine — /adversarial-engine."""
from __future__ import annotations

import html as _html
from rcm_mc.ui._chartis_kit import P, chartis_shell, ck_kpi_block


def _rec_color(rec: str) -> str:
    return {
        "STOP": P["negative"],
        "PROCEED_WITH_CONDITIONS": P["warning"],
        "PROCEED": P["positive"],
    }.get(rec, P["text_dim"])


def _stress_color(s: str) -> str:
    return {
        "BROKEN": P["negative"],
        "FRAGILE": P["warning"],
        "HOLDS": P["positive"],
    }.get(s, P["text_dim"])


def _severity_color(s: str) -> str:
    return {
        "critical": P["negative"],
        "warning": P["warning"],
        "context": P["text_dim"],
    }.get(s, P["text_dim"])


def _summary_table(memos) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]
    cols = [("Deal", "left"), ("Year", "right"), ("Buyer", "left"),
            ("EV ($M)", "right"), ("Entry Mult", "right"),
            ("Broken", "right"), ("Bear MOIC", "right"),
            ("Cap-Loss P", "right"), ("Recommendation", "center")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, m in enumerate(memos):
        rb = panel_alt if i % 2 == 0 else bg
        rc = _rec_color(m.recommendation)
        closs = m.worst_case_mc.capital_loss_probability
        cc = P["negative"] if closs >= 0.40 else (P["warning"] if closs >= 0.20 else P["text_dim"])
        ev_cell = f"${m.ev_mm:,.0f}" if m.ev_mm else "—"
        mult_cell = f"{m.implied_multiple:.1f}x" if m.implied_multiple else "—"
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">{_html.escape(m.deal_name)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{m.year or "—"}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim};max-width:200px">{_html.escape(m.buyer)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos};font-weight:700">{ev_cell}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{mult_cell}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{rc};font-weight:700">{m.critical_assumptions_broken}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{acc};font-weight:700">{m.probability_weighted_bear_moic:.2f}x</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{cc}">{closs*100:.1f}%</td>',
            f'<td style="text-align:center;padding:5px 10px"><span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{rc};border:1px solid {rc};border-radius:2px;letter-spacing:0.06em;font-weight:700">{_html.escape(m.recommendation.replace("_", " "))}</span></td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _catalog_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]
    cols = [("Deal", "left"), ("Year", "right"), ("Cat.", "left"),
            ("Assumption", "left"), ("Stress", "center"),
            ("Matched Patterns", "left"), ("Severity", "center")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    # Only show BROKEN + FRAGILE rows (the bear-case content), limit to 120
    bear_rows = [c for c in items if c.stress_result in ("BROKEN", "FRAGILE")][:120]
    for i, c in enumerate(bear_rows):
        rb = panel_alt if i % 2 == 0 else bg
        sc = _stress_color(c.stress_result)
        sec = _severity_color(c.severity)
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{text};font-weight:600;max-width:240px">{_html.escape(c.deal_name[:44])}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:10px;color:{text_dim}">{c.deal_year or "—"}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{acc}">{_html.escape(c.category)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim};max-width:320px">{_html.escape(c.assumption_statement)}</td>',
            f'<td style="text-align:center;padding:5px 10px"><span style="display:inline-block;padding:2px 8px;font-size:9px;font-family:JetBrains Mono,monospace;color:{sc};border:1px solid {sc};border-radius:2px;letter-spacing:0.06em;font-weight:700">{_html.escape(c.stress_result)}</span></td>',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{text_dim};max-width:200px">{_html.escape(c.matched_pattern)}</td>',
            f'<td style="text-align:center;padding:5px 10px"><span style="display:inline-block;padding:2px 6px;font-size:9px;font-family:JetBrains Mono,monospace;color:{sec};border:1px solid {sec};border-radius:2px;letter-spacing:0.06em">{_html.escape(c.severity.upper())}</span></td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _memo_detail(memo) -> str:
    panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]
    rc = _rec_color(memo.recommendation)
    # Build stress list
    stress_rows = []
    for s in memo.stress_results:
        sc = _stress_color(s.stress_result)
        matched = ", ".join(s.matched_nf_patterns) if s.matched_nf_patterns else "—"
        stress_rows.append(
            f'<div style="display:grid;grid-template-columns:60px 90px 1fr;gap:8px;padding:6px 0;border-top:1px solid {border};font-size:11px">'
            f'<code style="color:{acc};font-family:JetBrains Mono,monospace">{_html.escape(s.assumption_id)}</code>'
            f'<span style="color:{sc};font-family:JetBrains Mono,monospace;font-weight:700;font-size:10px">{_html.escape(s.stress_result)}</span>'
            f'<div><div style="color:{text};margin-bottom:2px">{_html.escape(s.assumption_statement)}</div>'
            f'<div style="color:{text_dim};font-size:10px">Rationale: {_html.escape(s.stress_rationale[:340])}</div>'
            f'<div style="color:{text_dim};font-size:10px;margin-top:2px"><strong>Matched patterns:</strong> {_html.escape(matched)} &middot; <strong>P10/P25 benchmark:</strong> {_html.escape(s.worst_quartile_value)}</div>'
            f'</div></div>'
        )
    stress_html = "".join(stress_rows)

    mc = memo.worst_case_mc
    return f"""
<div style="background:{panel_alt};border:1px solid {border};border-left:3px solid {rc};padding:14px 16px;margin-bottom:14px">
  <div style="display:flex;justify-content:space-between;align-items:baseline;margin-bottom:8px">
    <div style="font-size:13px;font-weight:700;color:{text}">{_html.escape(memo.deal_name)} <span style="color:{text_dim};font-weight:400;font-family:JetBrains Mono,monospace;font-size:11px">({memo.year})</span></div>
    <div><span style="display:inline-block;padding:4px 10px;font-size:11px;font-family:JetBrains Mono,monospace;color:{rc};border:1px solid {rc};border-radius:2px;letter-spacing:0.08em;font-weight:700">{_html.escape(memo.recommendation.replace("_", " "))}</span></div>
  </div>
  <div style="font-size:11px;color:{text_dim};margin-bottom:10px">
    Buyer: {_html.escape(memo.buyer)} &middot;
    EV: {"$%.0fM" % memo.ev_mm if memo.ev_mm else "—"} &middot;
    Entry multiple: {"%.1fx" % memo.implied_multiple if memo.implied_multiple else "—"} &middot;
    Broken: <strong style="color:{_rec_color('STOP') if memo.critical_assumptions_broken >= 2 else text}">{memo.critical_assumptions_broken}</strong> &middot;
    MC p10={mc.worst_quartile_moic_p10:.2f}x / p50={mc.worst_quartile_moic_p50:.2f}x / mean={mc.worst_quartile_moic_mean:.2f}x &middot;
    Capital-loss: <strong>{mc.capital_loss_probability*100:.1f}%</strong> &middot;
    Severe-loss: {mc.severe_loss_probability*100:.1f}%
  </div>
  {stress_html}
  <div style="margin-top:12px;padding:10px 12px;background:{P["bg"]};border:1px solid {border};font-size:10px;color:{text_dim};font-family:JetBrains Mono,monospace;line-height:1.5">
    <strong style="color:{text}">Red-team summary:</strong> {_html.escape(memo.red_team_summary)}
  </div>
</div>
"""


def render_adversarial_engine(params: dict = None) -> str:
    from rcm_mc.data_public.adversarial_engine import compute_adversarial_engine
    r = compute_adversarial_engine()

    panel = P["panel"]; panel_alt = P["panel_alt"]
    border = P["border"]; text = P["text"]; text_dim = P["text_dim"]
    acc = P["accent"]

    kpi_strip = (
        ck_kpi_block("Memos Generated", str(r.total_memos), "", "") +
        ck_kpi_block("Assumptions Decomposed", str(r.total_assumptions), "", "") +
        ck_kpi_block("Broken Assumptions", str(r.total_broken_assumptions), "", "") +
        ck_kpi_block("STOP Recommendation", str(r.deals_stop_recommendation), "", "") +
        ck_kpi_block("PROCEED w/ Conditions", str(r.deals_proceed_with_conditions), "", "") +
        ck_kpi_block("PROCEED", str(r.deals_proceed), "", "") +
        ck_kpi_block("Avg Bear MOIC", f"{r.avg_bear_moic:.2f}x", "", "") +
        ck_kpi_block("Corpus Deals", f"{r.corpus_deal_count:,}", "", "")
    )

    summary_tbl = _summary_table(r.memos)
    catalog_tbl = _catalog_table(r.assumption_catalog)

    # Pick 3 representative memos for detail view: one STOP, one PWC, one PROCEED
    by_rec = {}
    for m in r.memos:
        by_rec.setdefault(m.recommendation, []).append(m)
    detail_picks = []
    for rec in ("STOP", "PROCEED_WITH_CONDITIONS", "PROCEED"):
        if by_rec.get(rec):
            # Highest-broken for STOP; middle for PWC; cleanest for PROCEED
            if rec == "STOP":
                detail_picks.append(sorted(by_rec[rec], key=lambda m: m.critical_assumptions_broken, reverse=True)[0])
            elif rec == "PROCEED":
                detail_picks.append(sorted(by_rec[rec], key=lambda m: m.critical_assumptions_broken)[0])
            else:
                detail_picks.append(by_rec[rec][0])
    detail_html = "".join(_memo_detail(m) for m in detail_picks)

    cell = f"background:{panel};border:1px solid {border};padding:16px;margin-bottom:16px"
    h3 = f"font-size:11px;font-weight:600;letter-spacing:0.08em;color:{text_dim};text-transform:uppercase;margin-bottom:10px"

    body = f"""
<div style="padding:20px;max-width:1400px;margin:0 auto">
  <div style="margin-bottom:20px">
    <h1 style="font-size:18px;font-weight:700;color:{text};letter-spacing:0.02em">Adversarial Diligence Engine — Auto-Generated Bear-Case Memos</h1>
    <p style="font-size:12px;color:{text_dim};margin-top:4px">{r.total_memos} memos across top-EV + top-NF-match + diverse corpus samples · {r.total_assumptions} assumptions decomposed · {r.total_broken_assumptions} broken · {r.deals_stop_recommendation} STOP · {r.deals_proceed_with_conditions} PROCEED_WITH_CONDITIONS · {r.deals_proceed} PROCEED · avg bear MOIC {r.avg_bear_moic:.2f}x — Blueprint Moat Layer 5</p>
  </div>
  <div style="display:flex;flex-wrap:wrap;gap:8px;margin-bottom:20px">{kpi_strip}</div>
  <div style="{cell}"><div style="{h3}">Memo Summary — All Recommendations Ranked by Broken Assumptions</div>{summary_tbl}</div>
  <div style="{cell}"><div style="{h3}">Broken &amp; Fragile Assumption Catalog — Only Bear-Case Rows</div>{catalog_tbl}</div>
  <div style="{cell}"><div style="{h3}">Sample Memo Details — Representative STOP / PROCEED_WITH_CONDITIONS / PROCEED</div>{detail_html}</div>
  <div style="background:{panel_alt};border:1px solid {border};border-left:3px solid {acc};padding:12px 16px;font-size:11px;color:{text_dim};margin-bottom:16px">
    <strong style="color:{text}">Adversarial Engine Thesis:</strong>
    The typical PE diligence artifact confirms the investment thesis — it starts from "the deal works" and
    accumulates supporting evidence. The adversarial engine flips the framing: for each deal, decompose the
    implicit PE thesis into five load-bearing assumptions (Growth, Multiple, PayerMix, Leverage, OpImprovement),
    stress-test each against the Named-Failure Library + NCCI edit density + benchmark-curve worst quartile,
    run a worst-quartile Monte Carlo at 2,000 iterations, produce a structured red-team memo.
    <br><br>
    <strong style="color:{text}">Three things this surfaces that a confirming diligence would miss:</strong>
    (1) Implicit assumptions — the deal thesis rarely writes down what it's assuming about payer mix and
    leverage servicing; the engine extracts them. (2) Pattern overlap — same keyword/sector footprint as
    a historical bankruptcy is an explicit flag. (3) Probability-weighted bear MOIC — not worst-case
    deterministic, but actuarial: what's the expected MOIC if the bear story plays out?
    <br><br>
    <strong style="color:{text}">Methodology:</strong> <code style="color:{acc};font-family:JetBrains Mono,monospace">{_html.escape(r.methodology[:420])}</code>
    <br><br>
    <strong style="color:{text}">Integration:</strong> This engine composes all five Moat Layers:
    Layer 1 (knowledge graph — NCCI edits as stress oracle),
    Layer 2 (benchmark library — worst-quartile distributional priors),
    Layer 3 (named-failure library — pattern match drives stress severity),
    Layer 4 (backtesting — distress probability calibration),
    Layer 5 (this engine).
    The Moat compounds: every additional NF pattern, benchmark curve, or NCCI edit makes this engine sharper.
  </div>
</div>"""

    return chartis_shell(body, "Adversarial Diligence Engine", active_nav="/adversarial-engine")
