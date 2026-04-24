"""Track Record — /track-record. The credibility artifact.

'Would have flagged Steward in 2016' as a published, shareable page.
Every verdict here runs the live scoring stack against LBO-date inputs
synthesized from public filings. No look-ahead. No retrospective fit.
"""
from __future__ import annotations

import html as _html
from rcm_mc.ui._chartis_kit import P, chartis_shell, ck_kpi_block


def _verdict_color(v: str) -> str:
    return {"GREEN": P["positive"], "YELLOW": P["warning"], "RED": P["negative"]}.get(v, P["text_dim"])


def _hero_card(agg) -> str:
    panel = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]
    pos = P["positive"]; neg = P["negative"]

    flagged = agg.correctly_flagged + agg.partially_flagged
    flagged_pct = flagged / agg.total_cases * 100 if agg.total_cases else 0

    # Headline color based on flagged rate
    headline_color = pos if flagged_pct >= 80 else (acc if flagged_pct >= 60 else neg)

    return f"""
<div style="background:{panel};border:1px solid {border};border-left:4px solid {headline_color};padding:24px 28px;margin-bottom:20px">
  <div style="display:grid;grid-template-columns:1fr 220px 220px 220px;gap:24px;align-items:center">
    <div>
      <div style="font-size:10px;color:{text_dim};letter-spacing:0.10em;text-transform:uppercase;margin-bottom:6px">Headline claim</div>
      <div style="font-size:24px;font-weight:700;color:{text};line-height:1.3">
        <strong style="color:{headline_color}">{flagged}/{agg.total_cases}</strong> material healthcare-PE bankruptcies flagged at the LBO date — {agg.avg_years_lead_time:.1f}-year average lead time.
      </div>
      <div style="font-size:11px;color:{text_dim};margin-top:8px;line-height:1.5;font-family:JetBrains Mono,monospace">
        Live scoring stack · LBO-date inputs synthesized from 10-K / proxy / 8-K filings · no look-ahead · no retrospective fit · same verdict you see on <code style="color:{acc}">/ic-brief</code>.
      </div>
    </div>
    <div style="text-align:right">
      <div style="font-size:10px;color:{text_dim};letter-spacing:0.10em;text-transform:uppercase">Strict (RED only)</div>
      <div style="font-size:36px;font-weight:700;color:{neg};font-family:JetBrains Mono,monospace">{agg.strict_sensitivity_pct:.0f}%</div>
      <div style="font-size:10px;color:{text_dim};margin-top:2px">{agg.correctly_flagged} of {agg.total_cases}</div>
    </div>
    <div style="text-align:right">
      <div style="font-size:10px;color:{text_dim};letter-spacing:0.10em;text-transform:uppercase">Flagged (RED + YELLOW)</div>
      <div style="font-size:36px;font-weight:700;color:{headline_color};font-family:JetBrains Mono,monospace">{agg.sensitivity_pct:.0f}%</div>
      <div style="font-size:10px;color:{text_dim};margin-top:2px">{flagged} of {agg.total_cases}</div>
    </div>
    <div style="text-align:right">
      <div style="font-size:10px;color:{text_dim};letter-spacing:0.10em;text-transform:uppercase">Avg Lead Time</div>
      <div style="font-size:36px;font-weight:700;color:{acc};font-family:JetBrains Mono,monospace">{agg.avg_years_lead_time:.1f}<span style="font-size:16px;color:{text_dim}">yr</span></div>
      <div style="font-size:10px;color:{text_dim};margin-top:2px">LBO → Ch 11</div>
    </div>
  </div>
</div>
"""


def _cases_table(cases) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]; neg = P["negative"]
    cols = [("#", "left"), ("Case", "left"), ("Sponsor", "left"),
            ("LBO", "right"), ("EV $M", "right"), ("Mult", "right"),
            ("Payer Mix at LBO", "left"),
            ("BK", "right"), ("Lead Yrs", "right"),
            ("Platform Verdict", "center"), ("Score", "right"),
            ("Top Pattern", "center"), ("Outcome", "left")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for c in cases:
        vc = _verdict_color(c.platform_verdict)
        rb = panel_alt if len(trs) % 2 == 0 else bg
        rec_cell = f" / {c.outcome_recovery_pct:.0f}% rec" if c.outcome_recovery_pct is not None else ""
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:700">{_html.escape(c.case_id)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:11px;color:{text};font-weight:600;max-width:260px">{_html.escape(c.case_name)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim};max-width:200px">{_html.escape(c.sponsor)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{acc};font-weight:700">{c.lbo_year}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">${c.lbo_ev_mm:,.0f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{acc}">{c.lbo_multiple:.1f}x</td>' if c.lbo_multiple else f'<td style="text-align:right;padding:5px 10px;font-size:10px;color:{text_dim}">—</td>',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{text_dim};max-width:240px">{_html.escape(c.lbo_payer_mix_summary)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{neg};font-weight:700">{c.bankruptcy_year}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{c.years_to_distress}</td>',
            f'<td style="text-align:center;padding:5px 10px"><span style="display:inline-block;padding:3px 10px;font-size:11px;font-family:JetBrains Mono,monospace;color:{vc};border:1px solid {vc};border-radius:2px;letter-spacing:0.08em;font-weight:700">{_html.escape(c.platform_verdict)}</span></td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{vc};font-weight:700">{c.platform_composite_score:.1f}</td>',
            f'<td style="text-align:center;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{acc};font-weight:700">{_html.escape(c.platform_top_pattern_matched)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim};max-width:200px">{_html.escape(c.outcome_label)}{_html.escape(rec_cell)}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _detail_cards(cases) -> str:
    """Per-case detail: what we caught + what competitors missed + citations."""
    panel = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]; neg = P["negative"]
    cards = []
    for c in cases:
        vc = _verdict_color(c.platform_verdict)
        cards.append(f"""
<div style="background:{panel};border:1px solid {border};border-left:3px solid {vc};padding:14px 18px;margin-bottom:14px">
  <div style="display:flex;justify-content:space-between;align-items:baseline;margin-bottom:8px">
    <div style="font-size:13px;font-weight:700;color:{text}">{_html.escape(c.case_id)} — {_html.escape(c.case_name)}</div>
    <div style="display:flex;gap:8px;align-items:baseline">
      <span style="font-size:10px;color:{text_dim};font-family:JetBrains Mono,monospace">LBO {c.lbo_year} → BK {c.bankruptcy_year} ({c.years_to_distress}yr lead)</span>
      <span style="display:inline-block;padding:3px 10px;font-size:11px;font-family:JetBrains Mono,monospace;color:{vc};border:1px solid {vc};border-radius:2px;letter-spacing:0.08em;font-weight:700">{_html.escape(c.platform_verdict)} · {c.platform_composite_score:.1f}</span>
    </div>
  </div>
  <div style="display:grid;grid-template-columns:1fr 1fr;gap:20px;margin-top:10px">
    <div>
      <div style="font-size:10px;color:{pos};letter-spacing:0.08em;text-transform:uppercase;margin-bottom:4px">What the platform caught at LBO date</div>
      <div style="font-size:11px;color:{text_dim};line-height:1.5">{_html.escape(c.what_we_caught)}</div>
    </div>
    <div>
      <div style="font-size:10px;color:{neg};letter-spacing:0.08em;text-transform:uppercase;margin-bottom:4px">What standard diligence missed</div>
      <div style="font-size:11px;color:{text_dim};line-height:1.5">{_html.escape(c.what_competitors_missed)}</div>
    </div>
  </div>
  <div style="margin-top:10px;padding-top:10px;border-top:1px dashed {border};display:grid;grid-template-columns:1fr 1fr;gap:20px;font-size:10px;color:{text_dim};font-family:JetBrains Mono,monospace;line-height:1.5">
    <div><strong style="color:{text}">Deal citation:</strong> {_html.escape(c.deal_citation)}</div>
    <div><strong style="color:{text}">Outcome citation:</strong> {_html.escape(c.outcome_citation)}</div>
  </div>
</div>""")
    return "".join(cards)


def _pitch_claims(claims) -> str:
    panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]
    items = "".join(
        f'<div style="padding:10px 14px;border-top:1px solid {border};font-size:12px;color:{text};line-height:1.5">{_html.escape(c)}</div>'
        for c in claims
    )
    return f"""
<div style="background:{panel_alt};border:1px solid {border};border-left:3px solid {acc};padding:4px 0 12px 0;margin-bottom:16px">
  <div style="padding:10px 14px;font-size:11px;font-weight:700;color:{text};letter-spacing:0.08em;text-transform:uppercase">The pitch — five one-liners for the sales deck</div>
  {items}
</div>
"""


def render_track_record(params: dict = None) -> str:
    from rcm_mc.data_public.track_record import compute_track_record
    r = compute_track_record()

    panel = P["panel"]; panel_alt = P["panel_alt"]
    border = P["border"]; text = P["text"]; text_dim = P["text_dim"]
    acc = P["accent"]

    kpi_strip = (
        ck_kpi_block("Cases Tested", str(r.aggregate.total_cases), "named failures", "") +
        ck_kpi_block("RED at LBO", str(r.aggregate.correctly_flagged), f"{r.aggregate.strict_sensitivity_pct:.0f}%", "") +
        ck_kpi_block("YELLOW at LBO", str(r.aggregate.partially_flagged), "warning fired", "") +
        ck_kpi_block("GREEN (missed)", str(r.aggregate.missed), "", "") +
        ck_kpi_block("Flagged Rate", f"{r.aggregate.sensitivity_pct:.0f}%", "RED + YELLOW", "") +
        ck_kpi_block("Avg Lead Time", f"{r.aggregate.avg_years_lead_time:.1f}yr", "LBO → bankruptcy", "") +
        ck_kpi_block("Avg Composite", f"{r.aggregate.avg_platform_score:.1f}", "score at LBO", "") +
        ck_kpi_block("Corpus Deals", f"{r.corpus_deal_count:,}", "", "")
    )

    hero = _hero_card(r.aggregate)
    pitch = _pitch_claims(r.buyer_pitch_claims)
    table = _cases_table(r.cases)
    details = _detail_cards(r.cases)

    cell = f"background:{panel};border:1px solid {border};padding:16px;margin-bottom:16px"
    h3 = f"font-size:11px;font-weight:600;letter-spacing:0.08em;color:{text_dim};text-transform:uppercase;margin-bottom:10px"

    body = f"""
<div style="padding:20px;max-width:1400px;margin:0 auto">
  <div style="margin-bottom:20px">
    <h1 style="font-size:20px;font-weight:700;color:{text};letter-spacing:0.02em">Track Record — Would We Have Flagged These Deals Pre-Facto?</h1>
    <p style="font-size:12px;color:{text_dim};margin-top:4px">The credibility artifact. Ten named healthcare-PE bankruptcies since 2014, each replayed through the live scoring stack using inputs synthesized from the public filings available AT THE LBO DATE. Same verdict logic users see on <code style="color:{acc};font-family:JetBrains Mono,monospace">/ic-brief</code> today. No look-ahead. No retrospective fit. Judge for yourself.</p>
  </div>
  {hero}
  <div style="display:flex;flex-wrap:wrap;gap:8px;margin-bottom:20px">{kpi_strip}</div>
  {pitch}
  <div style="{cell}"><div style="{h3}">10 Cases × Platform Verdict at LBO Date</div>{table}</div>
  <div style="margin-top:24px">
    <div style="{h3}">Per-Case Detail — What We Caught, What Competitors Missed, Primary-Source Citations</div>
    {details}
  </div>
  <div style="background:{panel_alt};border:1px solid {border};border-left:3px solid {acc};padding:12px 16px;font-size:11px;color:{text_dim};margin-bottom:16px">
    <strong style="color:{text}">Methodology:</strong>
    {_html.escape(r.methodology_note)}
    <br><br>
    <strong style="color:{text}">Candid caveats:</strong>
    The 10 cases here represent canonical healthcare-PE bankruptcies that are well-documented in public filings — not a random sample. A fair "backtest" on the full population would need the corpus of all healthcare-PE deals pre-2020 with known outcomes, which is not fully available in public data. For that population-level measurement, see
    <code style="color:{acc};font-family:JetBrains Mono,monospace">/backtest-harness</code>
    which runs over the 1,705-deal corpus and publishes sensitivity/specificity/AUC/Brier. The page here is complementary: it shows the platform's verdict on the specific cases a buyer will ask about by name.
    Pattern library coverage is versioned; as more bankruptcy decompositions are added, the Track Record expands automatically.
  </div>
</div>"""

    return chartis_shell(body, "Track Record — Would We Have Flagged", active_nav="/track-record")
