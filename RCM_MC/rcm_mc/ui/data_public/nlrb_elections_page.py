"""NLRB Healthcare Union-Election Filings — /nlrb-elections."""
from __future__ import annotations

import html as _html
from rcm_mc.ui._chartis_kit import P, chartis_shell, ck_kpi_block


def _tier_color(t: str) -> str:
    return {"CRITICAL": P["negative"], "HIGH": P["negative"],
            "MEDIUM": P["warning"], "LOW": P["accent"]}.get(t, P["text_dim"])


def _outcome_color(o: str) -> str:
    return {"certified": P["negative"], "pending": P["warning"],
            "withdrew": P["positive"], "decert-fail": P["positive"],
            "ulp-filed": P["warning"]}.get(o, P["text_dim"])


def _intensity_color(s: int) -> str:
    if s >= 75: return P["negative"]
    if s >= 50: return P["warning"]
    if s >= 25: return P["accent"]
    return P["text_dim"]


def _cases_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]; neg = P["negative"]
    cols = [("Case #", "left"), ("Filed", "right"), ("Employer", "left"),
            ("Petitioner", "left"), ("State", "center"),
            ("Unit", "left"), ("Size", "right"),
            ("Outcome", "center"), ("Vote Y/N", "right"),
            ("PE Context", "left")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    ranked = sorted(items, key=lambda c: c.filing_date, reverse=True)
    for i, c in enumerate(ranked):
        rb = panel_alt if i % 2 == 0 else bg
        oc = _outcome_color(c.outcome)
        vote_cell = "—"
        if c.yes_votes is not None and c.no_votes is not None:
            vote_cell = f"{c.yes_votes:,} / {c.no_votes:,}"
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{text};font-weight:600">{_html.escape(c.case_number)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:10px;color:{text_dim}">{_html.escape(c.filing_date)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:11px;color:{text};font-weight:600;max-width:240px">{_html.escape(c.employer)}<div style="font-size:9px;color:{text_dim};font-weight:400;margin-top:1px">{_html.escape(c.parent_system)}</div></td>',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{acc};max-width:180px">{_html.escape(c.petitioner)}</td>',
            f'<td style="text-align:center;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:700">{_html.escape(c.state)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim};max-width:200px">{_html.escape(c.occupation_mix)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{neg};font-weight:700">{c.bargaining_unit_size:,}</td>',
            f'<td style="text-align:center;padding:5px 10px"><span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{oc};border:1px solid {oc};border-radius:2px;letter-spacing:0.06em;font-weight:700">{_html.escape(c.outcome.upper())}</span></td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:10px;color:{pos}">{vote_cell}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim};max-width:220px">{_html.escape(c.pe_ownership_context)}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _unions_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]; neg = P["negative"]
    cols = [("Short Name", "left"), ("Full Name", "left"), ("Affiliation", "left"),
            ("Members (HC)", "right"), ("Active States", "left"),
            ("Target Occupations", "left"), ("Win Rate", "right")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    ranked = sorted(items, key=lambda u: -u.est_healthcare_members)
    for i, u in enumerate(ranked):
        rb = panel_alt if i % 2 == 0 else bg
        wr_c = neg if u.typical_win_rate_pct >= 85 else (P["warning"] if u.typical_win_rate_pct >= 75 else acc)
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:700">{_html.escape(u.short_name)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:11px;color:{text};max-width:320px">{_html.escape(u.full_name)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim};max-width:160px">{_html.escape(u.national_affiliation)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos};font-weight:700">{u.est_healthcare_members:,}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{acc};max-width:200px">{_html.escape(", ".join(u.active_states))}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim};max-width:300px">{_html.escape(u.typical_target_occupations)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{wr_c};font-weight:700">{u.typical_win_rate_pct:.0f}%</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _state_intensity_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]; neg = P["negative"]
    cols = [("State", "center"), ("Cases", "right"), ("Unit Size", "right"),
            ("Certified", "right"), ("Withdrew", "right"), ("Pending", "right"),
            ("Top Petitioner", "left"), ("Top Employer", "left"),
            ("Corpus Deals", "right"), ("Intensity", "right")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, s in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        ic = _intensity_color(s.intensity_score)
        cells = [
            f'<td style="text-align:center;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:12px;color:{text};font-weight:700">{_html.escape(s.state)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{s.case_count}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{neg};font-weight:700">{s.total_bargaining_unit_size:,}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{neg}">{s.certified_outcome_count}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos}">{s.withdrew_count}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{P["warning"]}">{s.pending_count}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{acc};max-width:160px">{_html.escape(s.top_petitioner)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim};max-width:200px">{_html.escape(s.top_employer_by_volume)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">{s.pe_deal_count_in_corpus}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:12px;color:{ic};font-weight:700">{s.intensity_score}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _overlays_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]
    cols = [("Deal", "left"), ("Year", "right"), ("State", "center"),
            ("Provider Type", "left"), ("NLRB Cases", "right"),
            ("Intensity", "right"), ("Applicable Unions", "left"),
            ("Risk Tier", "center"), ("Rationale", "left")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, o in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        tc = _tier_color(o.risk_tier)
        ic = _intensity_color(o.state_intensity_score)
        unions = ", ".join(o.applicable_unions[:3])
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">{_html.escape(o.deal_name)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{o.deal_year or "—"}</td>',
            f'<td style="text-align:center;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:700">{_html.escape(o.inferred_state)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{acc}">{_html.escape(o.inferred_provider_type)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{o.matched_nlrb_cases}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{ic};font-weight:700">{o.state_intensity_score}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{acc};max-width:220px">{_html.escape(unions)}</td>',
            f'<td style="text-align:center;padding:5px 10px"><span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{tc};border:1px solid {tc};border-radius:2px;letter-spacing:0.06em;font-weight:700">{_html.escape(o.risk_tier)}</span></td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim};max-width:380px">{_html.escape(o.rationale[:300])}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def render_nlrb_elections(params: dict = None) -> str:
    from rcm_mc.data_public.nlrb_elections import compute_nlrb_elections
    r = compute_nlrb_elections()

    panel = P["panel"]; panel_alt = P["panel_alt"]
    border = P["border"]; text = P["text"]; text_dim = P["text_dim"]
    acc = P["accent"]

    kpi_strip = (
        ck_kpi_block("NLRB Cases", str(r.total_cases), r.data_coverage_range, "") +
        ck_kpi_block("Certified", str(r.total_certified), "election wins", "") +
        ck_kpi_block("Pending", str(r.total_pending), "awaiting election", "") +
        ck_kpi_block("Workers Covered", f"{r.total_bargaining_unit_covered:,}", "in curated units", "") +
        ck_kpi_block("Unions Tracked", str(r.total_unions_tracked), "", "") +
        ck_kpi_block("Avg Win Rate", f"{r.avg_union_win_rate_pct:.1f}%", "historical", "") +
        ck_kpi_block("CRITICAL Deals", str(r.critical_risk_corpus_deals), "", "") +
        ck_kpi_block("Corpus Deals", f"{r.corpus_deal_count:,}", "", "")
    )

    cases_tbl = _cases_table(r.cases)
    unions_tbl = _unions_table(r.unions)
    intensity_tbl = _state_intensity_table(r.state_intensities)
    overlays_tbl = _overlays_table(r.corpus_overlays)
    citations_html = "<br>".join(f"• {_html.escape(c)}" for c in r.source_citations)

    cell = f"background:{panel};border:1px solid {border};padding:16px;margin-bottom:16px"
    h3 = f"font-size:11px;font-weight:600;letter-spacing:0.08em;color:{text_dim};text-transform:uppercase;margin-bottom:10px"

    body = f"""
<div style="padding:20px;max-width:1400px;margin:0 auto">
  <div style="margin-bottom:20px">
    <h1 style="font-size:18px;font-weight:700;color:{text};letter-spacing:0.02em">NLRB Healthcare Union-Election Filings — 2020-2025</h1>
    <p style="font-size:12px;color:{text_dim};margin-top:4px">{r.total_cases} curated NLRB healthcare petitions covering {r.total_bargaining_unit_covered:,} workers · {r.total_certified} certified / {r.total_pending} pending · {r.total_unions_tracked} unions tracked · {r.critical_risk_corpus_deals} CRITICAL + {r.high_risk_corpus_deals} HIGH corpus deal overlays · KB {r.knowledge_base_version} effective {r.effective_date}</p>
  </div>
  <div style="display:flex;flex-wrap:wrap;gap:8px;margin-bottom:20px">{kpi_strip}</div>
  <div style="{cell}"><div style="{h3}">State Union-Organizing Intensity — Top 20</div>{intensity_tbl}</div>
  <div style="{cell}"><div style="{h3}">Top 60 Corpus Deal Risk Overlays — Healthcare Deals in High-Intensity States</div>{overlays_tbl}</div>
  <div style="{cell}"><div style="{h3}">Healthcare Unions Tracked — Campaign Focus + Historical Win Rates</div>{unions_tbl}</div>
  <div style="{cell}"><div style="{h3}">Curated NLRB Petitions — {r.total_cases} Recent Cases (Most Recent First)</div>{cases_tbl}</div>
  <div style="background:{panel_alt};border:1px solid {border};border-left:3px solid {acc};padding:12px 16px;font-size:11px;color:{text_dim};margin-bottom:16px">
    <strong style="color:{text}">Union-Risk Thesis:</strong>
    Healthcare has been the #1 union-organizing sector 2020-2025. The 2023 wave started
    with NYSNA at Mount Sinai + Montefiore, spread to CIR/SEIU residents across
    Stanford, Penn, Mount Sinai, Montefiore, Jefferson, then the Kaiser/SEIU-UHW/CWA
    multi-discipline expansion. Every hospital, home-health, SNF, and behavioral-health
    deal in a high-intensity state (CA/NY/MA/IL/PA) carries near-term union risk.
    <br><br>
    <strong style="color:{text}">Economic cost of certification:</strong>
    First CBA typically adds 8-15% to wage costs over 18-24 months (AHA + BLS wage
    data). Staffing disruption during negotiation periods is non-trivial. Strikes
    (see Mount Sinai 2023, St. Vincent 2021-2022, Kaiser 2023) carry 5-10% revenue
    impact during active strike days.
    <br><br>
    <strong style="color:{text}">Corpus exposure:</strong>
    {r.critical_risk_corpus_deals} CRITICAL-tier corpus deals plus {r.high_risk_corpus_deals} HIGH-tier
    are in top-quartile-intensity states. Top-5: Prospect Medical (CA), Sutter (CA),
    Optum/DaVita Medical (CA), Northwell (NY), Kaiser (CA). PE-backed deals especially
    (Prospect, UHS, Acadia, Surgery Partners) show recent activity.
    <br><br>
    <strong style="color:{text}">Integration:</strong>
    Cross-links to <code style="color:{acc};font-family:JetBrains Mono,monospace">/cpom-lattice</code>
    (state-level organizing + non-compete regime together define labor-cost trajectory)
    and <code style="color:{acc};font-family:JetBrains Mono,monospace">/ic-brief</code>
    (healthcare targets in HIGH-intensity states should auto-flag union risk).
    <code style="color:{acc};font-family:JetBrains Mono,monospace">/rag</code> indexes cases
    for citation-grounded retrieval.
    <br><br>
    <strong style="color:{text}">KB provenance (versioned, cited):</strong>
    <div style="font-family:JetBrains Mono,monospace;color:{text_dim};font-size:10px;line-height:1.5;margin-top:4px">
    KB version: {r.knowledge_base_version} · Data coverage: {r.data_coverage_range} · Effective: {r.effective_date}<br>
    {citations_html}<br><br>
    <em>NLRB case data is public. Case numbers are from NLRB.gov public case search; some
    sensitive cases sanitized where employer-identification beyond what unions have
    publicly announced would be inappropriate for a planning artifact.</em>
    </div>
  </div>
</div>"""

    return chartis_shell(body, "NLRB Healthcare Union-Election Filings", active_nav="/nlrb-elections")
