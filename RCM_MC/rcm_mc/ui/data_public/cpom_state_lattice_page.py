"""CPOM State Lattice — /cpom-lattice."""
from __future__ import annotations

import html as _html
from rcm_mc.ui._chartis_kit import P, chartis_shell, ck_kpi_block


def _tier_color(t: str) -> str:
    return {"strict": P["negative"], "moderate": P["warning"],
            "friendly": P["positive"], "none": P["text_dim"]}.get(t, P["text_dim"])


def _risk_tier_color(t: str) -> str:
    return {"CRITICAL": P["negative"], "HIGH": P["negative"],
            "MEDIUM": P["warning"], "LOW": P["accent"]}.get(t, P["text_dim"])


def _risk_score_color(s: int) -> str:
    if s >= 70: return P["negative"]
    if s >= 55: return P["warning"]
    if s >= 40: return P["accent"]
    return P["positive"]


def _states_table(states) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]
    cols = [("St", "left"), ("State", "left"), ("Tier", "center"),
            ("MSO-Friendly", "center"), ("Fee Split", "center"),
            ("Non-Compete", "left"), ("Recent Enf.", "right"),
            ("PE Intensity", "center"), ("Risk Score", "right"),
            ("Key Statute", "left")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    # Sort: strict tier first, then by risk score desc
    tier_order = {"strict": 0, "moderate": 1, "friendly": 2, "none": 3}
    ranked = sorted(states, key=lambda s: (tier_order.get(s.regime_tier, 9), -s.structural_risk_score))
    for i, s in enumerate(ranked):
        rb = panel_alt if i % 2 == 0 else bg
        tc = _tier_color(s.regime_tier)
        rc = _risk_score_color(s.structural_risk_score)
        mso_mark = "✓" if s.mso_friendly else "—"
        mso_c = pos if s.mso_friendly else text_dim
        fs_mark = "✓" if s.fee_splitting_allowed else "✗"
        fs_c = pos if s.fee_splitting_allowed else P["negative"]
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:700">{_html.escape(s.state_code)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:11px;color:{text};font-weight:600">{_html.escape(s.state_name)}</td>',
            f'<td style="text-align:center;padding:5px 10px"><span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{tc};border:1px solid {tc};border-radius:2px;letter-spacing:0.06em;font-weight:700">{_html.escape(s.regime_tier.upper())}</span></td>',
            f'<td style="text-align:center;padding:5px 10px;color:{mso_c};font-family:JetBrains Mono,monospace;font-size:12px;font-weight:700">{mso_mark}</td>',
            f'<td style="text-align:center;padding:5px 10px;color:{fs_c};font-family:JetBrains Mono,monospace;font-size:12px;font-weight:700">{fs_mark}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim};max-width:220px">{_html.escape(s.non_compete_enforceability)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{s.recent_enforcement_count}</td>',
            f'<td style="text-align:center;padding:5px 10px;font-size:10px;color:{acc};font-family:JetBrains Mono,monospace">{_html.escape(s.pe_activity_intensity)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{rc};font-weight:700">{s.structural_risk_score}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{text_dim};max-width:240px">{_html.escape(s.key_statute[:60])}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _detail_cards(states) -> str:
    """Per-state detail card for the top-10 PE-active states."""
    panel = P["panel"]; border = P["border"]; text = P["text"]; text_dim = P["text_dim"]
    acc = P["accent"]; pos = P["positive"]; neg = P["negative"]
    # Pick strict + top PE-active states
    featured = [s for s in states if s.regime_tier == "strict" or s.pe_activity_intensity in ("very high", "high")][:12]
    cards = []
    for s in featured:
        tc = _tier_color(s.regime_tier)
        enforce_list = "".join(f'<li style="font-size:10px;color:{text_dim};margin-bottom:2px">{_html.escape(e)}</li>' for e in s.notable_enforcement[:3])
        permitted_list = ", ".join(s.permitted_structures[:4])
        cards.append(f"""
<div style="background:{panel};border:1px solid {border};border-left:3px solid {tc};padding:14px 18px;margin-bottom:14px">
  <div style="display:flex;justify-content:space-between;align-items:baseline;margin-bottom:8px">
    <div style="font-size:13px;font-weight:700;color:{text}">{_html.escape(s.state_name)} ({_html.escape(s.state_code)})</div>
    <div style="display:flex;gap:6px">
      <span style="display:inline-block;padding:3px 10px;font-size:10px;font-family:JetBrains Mono,monospace;color:{tc};border:1px solid {tc};border-radius:2px;letter-spacing:0.08em;font-weight:700">{_html.escape(s.regime_tier.upper())}</span>
      <span style="display:inline-block;padding:3px 10px;font-size:10px;font-family:JetBrains Mono,monospace;color:{_risk_score_color(s.structural_risk_score)};border:1px solid {_risk_score_color(s.structural_risk_score)};border-radius:2px;letter-spacing:0.08em;font-weight:700">RISK {s.structural_risk_score}</span>
    </div>
  </div>
  <div style="font-size:11px;color:{text};line-height:1.5;margin-bottom:8px">{_html.escape(s.cpom_doctrine_summary)}</div>
  <div style="display:grid;grid-template-columns:1fr 1fr;gap:20px;font-size:10px;color:{text_dim}">
    <div>
      <div style="color:{text};font-weight:700;letter-spacing:0.06em;text-transform:uppercase;margin-bottom:4px;font-size:10px">Permitted Structures</div>
      <div>{_html.escape(permitted_list)}</div>
      <div style="margin-top:8px;color:{text};font-weight:700;letter-spacing:0.06em;text-transform:uppercase;font-size:10px">Non-Compete</div>
      <div>{_html.escape(s.non_compete_enforceability)}</div>
    </div>
    <div>
      <div style="color:{text};font-weight:700;letter-spacing:0.06em;text-transform:uppercase;margin-bottom:4px;font-size:10px">Recent Enforcement ({s.recent_enforcement_count})</div>
      <ul style="margin:0;padding-left:16px">{enforce_list or '<li style="font-size:10px;color:' + text_dim + '">No notable actions in last 5yr</li>'}</ul>
    </div>
  </div>
  <div style="margin-top:10px;padding-top:10px;border-top:1px dashed {border};font-size:10px;color:{text};line-height:1.5">
    <strong style="color:{acc}">Diligence note:</strong> {_html.escape(s.diligence_note)}
  </div>
  <div style="margin-top:6px;font-size:9px;color:{text_dim};font-family:JetBrains Mono,monospace">Statute: {_html.escape(s.key_statute)} · Body: {_html.escape(s.key_regulatory_body)} · Last revised: {s.last_revised_year}</div>
</div>""")
    return "".join(cards)


def _enforcement_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]
    cols = [("Year", "right"), ("State/Forum", "left"), ("Type", "left"),
            ("Case / Subject", "left"), ("Summary", "left"), ("Citation", "left")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, a in enumerate(sorted(items, key=lambda x: -x.year)):
        rb = panel_alt if i % 2 == 0 else bg
        cells = [
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{acc};font-weight:700">{a.year}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:700">{_html.escape(a.state)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim};max-width:180px">{_html.escape(a.action_type)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:11px;color:{text};font-weight:600;max-width:220px">{_html.escape(a.target_or_case)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim};max-width:420px">{_html.escape(a.summary)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{acc};max-width:240px">{_html.escape(a.citation)}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _overlays_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]
    cols = [("Deal", "left"), ("Year", "right"), ("State", "center"),
            ("Regime", "center"), ("MSO Friendly", "center"),
            ("Risk Score", "right"), ("Concerns", "left"), ("Tier", "center")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, o in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        tc = _risk_tier_color(o.risk_tier)
        rc = _risk_score_color(o.structural_risk_score)
        rg_c = _tier_color(o.state_regime_tier)
        mso_mark = "✓" if o.mso_friendly else "—"
        concerns = "; ".join(o.enforcement_concerns[:3])
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">{_html.escape(o.deal_name)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{o.deal_year or "—"}</td>',
            f'<td style="text-align:center;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:700">{_html.escape(o.inferred_state)}</td>',
            f'<td style="text-align:center;padding:5px 10px"><span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{rg_c};border:1px solid {rg_c};border-radius:2px;letter-spacing:0.06em">{_html.escape(o.state_regime_tier.upper())}</span></td>',
            f'<td style="text-align:center;padding:5px 10px;color:{acc};font-family:JetBrains Mono,monospace;font-size:12px;font-weight:700">{mso_mark}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{rc};font-weight:700">{o.structural_risk_score}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim};max-width:360px">{_html.escape(concerns)}</td>',
            f'<td style="text-align:center;padding:5px 10px"><span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{tc};border:1px solid {tc};border-radius:2px;letter-spacing:0.06em;font-weight:700">{_html.escape(o.risk_tier)}</span></td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def render_cpom_lattice(params: dict = None) -> str:
    from rcm_mc.data_public.cpom_state_lattice import compute_cpom_state_lattice
    r = compute_cpom_state_lattice()

    panel = P["panel"]; panel_alt = P["panel_alt"]
    border = P["border"]; text = P["text"]; text_dim = P["text_dim"]
    acc = P["accent"]

    kpi_strip = (
        ck_kpi_block("States + DC", str(r.total_states), f"KB {r.knowledge_base_version}", "") +
        ck_kpi_block("Strict Tier", str(r.strict_tier_count), "CPOM enforced", "") +
        ck_kpi_block("Moderate Tier", str(r.moderate_tier_count), "", "") +
        ck_kpi_block("Friendly Tier", str(r.friendly_tier_count), "direct-employ OK", "") +
        ck_kpi_block("MSO-Friendly", f"{r.mso_friendly_count}/{r.total_states}", "", "") +
        ck_kpi_block("Avg Risk Score", f"{r.avg_risk_score:.1f}", "0-100", "") +
        ck_kpi_block("Corpus Overlays", str(r.corpus_deals_with_state_match), f"CRITICAL: {r.critical_exposure_count}", "") +
        ck_kpi_block("Corpus Deals", f"{r.corpus_deal_count:,}", "", "")
    )

    states_tbl = _states_table(r.states)
    details = _detail_cards(r.states)
    enforce_tbl = _enforcement_table(r.enforcement_actions)
    overlays_tbl = _overlays_table(r.corpus_overlays)
    citations_html = "<br>".join(f"• {_html.escape(c)}" for c in r.source_citations)

    cell = f"background:{panel};border:1px solid {border};padding:16px;margin-bottom:16px"
    h3 = f"font-size:11px;font-weight:600;letter-spacing:0.08em;color:{text_dim};text-transform:uppercase;margin-bottom:10px"

    body = f"""
<div style="padding:20px;max-width:1400px;margin:0 auto">
  <div style="margin-bottom:20px">
    <h1 style="font-size:18px;font-weight:700;color:{text};letter-spacing:0.02em">Corporate Practice of Medicine — 50-State Compliance Lattice</h1>
    <p style="font-size:12px;color:{text_dim};margin-top:4px">{r.total_states}-state + DC structured CPOM + MSO + fee-splitting + non-compete matrix · {r.strict_tier_count} strict / {r.moderate_tier_count} moderate / {r.friendly_tier_count} friendly · {r.critical_exposure_count} CRITICAL corpus overlays (CA/NY-concentrated) · KB {r.knowledge_base_version} effective {r.effective_date}</p>
  </div>
  <div style="display:flex;flex-wrap:wrap;gap:8px;margin-bottom:20px">{kpi_strip}</div>
  <div style="{cell}"><div style="{h3}">50-State CPOM Matrix — Tier · MSO · Non-Compete · Statute</div>{states_tbl}</div>
  <div style="{cell}"><div style="{h3}">Corpus Overlay — Physician-Group Deals × Inferred State × Structural Risk</div>{overlays_tbl}</div>
  <div style="{cell}"><div style="{h3}">Key Enforcement Actions + Statute Changes (12 curated)</div>{enforce_tbl}</div>
  <div style="margin-top:24px">
    <div style="{h3}">Detailed State Profiles — Top PE-Active Jurisdictions</div>
    {details}
  </div>
  <div style="background:{panel_alt};border:1px solid {border};border-left:3px solid {acc};padding:12px 16px;font-size:11px;color:{text_dim};margin-bottom:16px">
    <strong style="color:{text}">CPOM Lattice Thesis:</strong>
    Every PE-backed physician group investment must thread the needle of state-specific
    CPOM doctrine. CA and NY (strict) require Friendly PC / MSO structures with defensible
    management-fee calibration; FL and CO (friendly) allow direct corporate employment;
    the 33 moderate states each have specific PC formation requirements and fee-splitting
    restrictions.
    <br><br>
    <strong style="color:{text}">Why this matters now:</strong>
    The 2022-2025 wave of state-level transaction-review laws — CA OHCA (§ 127500 et seq.),
    OR HCMO (HB 4130), MA HPC material-change review, WA HB 2548, CT OHS — adds mandatory
    pre-transaction notice for deals in multiple states. A PE physician-group platform with
    CA+NY+MA footprint faces three parallel state-review regimes on top of CPOM compliance.
    Time-to-close extends 90-180 days beyond baseline.
    <br><br>
    <strong style="color:{text}">Integration with IC Brief:</strong>
    Every physician-group TargetInput in <code style="color:{acc};font-family:JetBrains Mono,monospace">/ic-brief</code>
    should surface the state regime tier + risk score + recent-enforcement concerns.
    Future iterations will wire this automatically via region keyword → state inference.
    <br><br>
    <strong style="color:{text}">KB provenance (versioned, cited):</strong>
    <div style="font-family:JetBrains Mono,monospace;color:{text_dim};font-size:10px;line-height:1.5;margin-top:4px">
    KB version: {r.knowledge_base_version} · Effective: {r.effective_date}<br>
    {citations_html}<br><br>
    <em>Individual state citations embedded per-state row. Enforcement actions table cites
    specific press releases, statute enactments, and court cases. This lattice is informational;
    structural opinions should be obtained from state-licensed healthcare counsel.</em>
    </div>
  </div>
</div>"""

    return chartis_shell(body, "CPOM State Lattice", active_nav="/cpom-lattice")
