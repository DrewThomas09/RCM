"""IC Brief Assembler — /ic-brief. The VP's 11pm-Sunday tool."""
from __future__ import annotations

import html as _html
from typing import Dict
from rcm_mc.ui._chartis_kit import P, chartis_shell, ck_kpi_block


def _verdict_color(v: str) -> str:
    return {"GREEN": P["positive"], "YELLOW": P["warning"], "RED": P["negative"]}.get(v, P["text_dim"])


def _severity_color(s: str) -> str:
    return {"CRITICAL": P["negative"], "HIGH": P["negative"], "MEDIUM": P["warning"], "LOW": P["accent"]}.get(s, P["text_dim"])


def _parse_target_from_params(params: Dict) -> object:
    from rcm_mc.data_public.ic_brief import TargetInput, DEFAULT_DEMO_TARGET

    def _f(k, default):
        v = params.get(k)
        if v is None or v == "":
            return default
        try:
            return float(v)
        except (TypeError, ValueError):
            return default

    def _s(k, default):
        v = params.get(k)
        if v is None or v == "":
            return default
        return str(v)

    if not params:
        return DEFAULT_DEMO_TARGET

    return TargetInput(
        deal_name=_s("deal_name", DEFAULT_DEMO_TARGET.deal_name),
        sector=_s("sector", DEFAULT_DEMO_TARGET.sector),
        ev_mm=_f("ev_mm", DEFAULT_DEMO_TARGET.ev_mm),
        ebitda_mm=_f("ebitda_mm", DEFAULT_DEMO_TARGET.ebitda_mm),
        hold_years=_f("hold_years", DEFAULT_DEMO_TARGET.hold_years),
        commercial_share=_f("commercial_share", DEFAULT_DEMO_TARGET.commercial_share),
        medicare_share=_f("medicare_share", DEFAULT_DEMO_TARGET.medicare_share),
        medicaid_share=_f("medicaid_share", DEFAULT_DEMO_TARGET.medicaid_share),
        self_pay_share=_f("self_pay_share", DEFAULT_DEMO_TARGET.self_pay_share),
        region=_s("region", DEFAULT_DEMO_TARGET.region),
        facility_type=_s("facility_type", DEFAULT_DEMO_TARGET.facility_type),
        buyer=_s("buyer", DEFAULT_DEMO_TARGET.buyer),
        notes=_s("notes", DEFAULT_DEMO_TARGET.notes),
    )


def _form_html(target) -> str:
    panel = P["panel"]; border = P["border"]; text = P["text"]; text_dim = P["text_dim"]
    acc = P["accent"]
    input_style = (f"background:{P['bg']};border:1px solid {border};color:{text};"
                   f"font-family:JetBrains Mono,monospace;font-size:11px;padding:5px 8px;"
                   f"width:100%;box-sizing:border-box")
    label_style = f"display:block;font-size:10px;color:{text_dim};letter-spacing:0.06em;text-transform:uppercase;margin-bottom:3px"
    sectors = [
        "Gastroenterology", "Cardiology", "Orthopedics", "Dermatology", "Urology",
        "Ophthalmology", "Emergency Medicine", "Anesthesiology", "Oncology",
        "Primary Care", "Behavioral Health", "Radiology", "Home Health",
        "Physical Therapy", "Dental", "Fertility", "Nephrology", "Pain Management",
        "Lab / Pathology", "Hospital",
    ]
    facilities = ["Physician Group", "Hospital", "Ambulatory Surgery Center",
                  "Home Health Agency", "Dialysis Provider", "Behavioral Health Provider"]
    regions = ["Northeast", "Midwest", "South", "West"]

    def opts(values, current):
        out = []
        for v in values:
            sel = 'selected' if v == current else ''
            out.append(f'<option value="{_html.escape(v, quote=True)}" {sel}>{_html.escape(v)}</option>')
        return "".join(out)

    def field(label, html_in):
        return (f'<div><label style="{label_style}">{_html.escape(label)}</label>{html_in}</div>')

    return f"""
<form method="get" action="/ic-brief" style="background:{panel};border:1px solid {border};padding:14px 16px;margin-bottom:16px">
  <div style="font-size:11px;font-weight:700;color:{text};letter-spacing:0.08em;text-transform:uppercase;margin-bottom:10px">Target Input — paste from CIM</div>
  <div style="display:grid;grid-template-columns:2fr 1.2fr 0.8fr 0.8fr 0.7fr;gap:10px;margin-bottom:10px">
    {field("Deal name", f'<input type="text" name="deal_name" value="{_html.escape(target.deal_name, quote=True)}" style="{input_style}">')}
    {field("Sector / specialty", f'<select name="sector" style="{input_style}">{opts(sectors, target.sector)}</select>')}
    {field("EV ($M)", f'<input type="number" step="any" name="ev_mm" value="{target.ev_mm or ""}" style="{input_style}">')}
    {field("EBITDA ($M)", f'<input type="number" step="any" name="ebitda_mm" value="{target.ebitda_mm or ""}" style="{input_style}">')}
    {field("Hold (yrs)", f'<input type="number" step="any" name="hold_years" value="{target.hold_years}" style="{input_style}">')}
  </div>
  <div style="display:grid;grid-template-columns:0.8fr 0.8fr 0.8fr 0.8fr 1fr 1fr;gap:10px;margin-bottom:10px">
    {field("Commercial %", f'<input type="number" step="any" name="commercial_share" value="{target.commercial_share}" style="{input_style}">')}
    {field("Medicare %", f'<input type="number" step="any" name="medicare_share" value="{target.medicare_share}" style="{input_style}">')}
    {field("Medicaid %", f'<input type="number" step="any" name="medicaid_share" value="{target.medicaid_share}" style="{input_style}">')}
    {field("Self-Pay %", f'<input type="number" step="any" name="self_pay_share" value="{target.self_pay_share}" style="{input_style}">')}
    {field("Region", f'<select name="region" style="{input_style}">{opts(regions, target.region)}</select>')}
    {field("Facility type", f'<select name="facility_type" style="{input_style}">{opts(facilities, target.facility_type)}</select>')}
  </div>
  <div style="display:grid;grid-template-columns:1fr 3fr 0.8fr;gap:10px;margin-bottom:10px">
    {field("Buyer / sponsor", f'<input type="text" name="buyer" value="{_html.escape(target.buyer, quote=True)}" style="{input_style}">')}
    {field("Notes (thesis, risks, structure — free text)", f'<input type="text" name="notes" value="{_html.escape(target.notes, quote=True)}" style="{input_style}">')}
    <div style="display:flex;align-items:flex-end">
      <button type="submit" style="background:{acc};color:white;border:none;padding:8px 18px;font-family:JetBrains Mono,monospace;font-size:11px;letter-spacing:0.08em;text-transform:uppercase;cursor:pointer;width:100%;font-weight:700">▶ Run Brief</button>
    </div>
  </div>
  <div style="font-size:10px;color:{text_dim};font-family:JetBrains Mono,monospace">💡 Share this brief by copying the URL — every input is in the query string. Browser: <kbd>⌘+P</kbd> / <kbd>Ctrl+P</kbd> → Save as PDF for IC packet.</div>
</form>
"""


def _verdict_card(v) -> str:
    panel = P["panel"]; border = P["border"]; text = P["text"]; text_dim = P["text_dim"]
    vc = _verdict_color(v.verdict)
    return f"""
<div style="background:{panel};border:1px solid {border};border-left:4px solid {vc};padding:18px 20px;margin-bottom:16px">
  <div style="display:grid;grid-template-columns:140px 1fr 120px 120px 120px;gap:20px;align-items:center">
    <div>
      <div style="font-size:10px;color:{text_dim};letter-spacing:0.08em;text-transform:uppercase;margin-bottom:2px">Verdict</div>
      <div style="font-size:28px;font-weight:700;color:{vc};font-family:JetBrains Mono,monospace;letter-spacing:0.04em">{_html.escape(v.verdict)}</div>
      <div style="font-size:10px;color:{text_dim};font-family:JetBrains Mono,monospace;margin-top:4px">Composite {v.composite_score:.1f} / 100</div>
    </div>
    <div style="font-size:12px;color:{text};line-height:1.5">{_html.escape(v.one_line_take)}</div>
    <div>
      <div style="font-size:10px;color:{text_dim};letter-spacing:0.08em;text-transform:uppercase">Distress P</div>
      <div style="font-size:18px;font-weight:700;color:{vc};font-family:JetBrains Mono,monospace">{v.distress_probability*100:.1f}%</div>
    </div>
    <div>
      <div style="font-size:10px;color:{text_dim};letter-spacing:0.08em;text-transform:uppercase">NF Component</div>
      <div style="font-size:14px;font-weight:700;color:{text};font-family:JetBrains Mono,monospace">{v.nf_component:.1f}</div>
    </div>
    <div>
      <div style="font-size:10px;color:{text_dim};letter-spacing:0.08em;text-transform:uppercase">NCCI · Leverage</div>
      <div style="font-size:14px;font-weight:700;color:{text};font-family:JetBrains Mono,monospace">{v.ncci_component:.1f} · {v.leverage_component:.1f}</div>
    </div>
  </div>
</div>
"""


def _red_flag_card(flags) -> str:
    panel = P["panel"]; border = P["border"]; text = P["text"]; text_dim = P["text_dim"]
    if not flags:
        return ""
    rows = []
    for f in flags:
        sc = _severity_color(f.severity)
        rows.append(
            f'<div style="display:grid;grid-template-columns:30px 90px 1fr 1.3fr 1.3fr;gap:12px;padding:8px 0;border-top:1px solid {border};font-size:11px">'
            f'<div style="font-family:JetBrains Mono,monospace;color:{text_dim};font-size:10px">#{f.rank}</div>'
            f'<div><span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{sc};border:1px solid {sc};border-radius:2px;letter-spacing:0.06em;font-weight:700">{_html.escape(f.severity)}</span></div>'
            f'<div style="color:{text};font-weight:600">{_html.escape(f.flag)}</div>'
            f'<div style="color:{text_dim};font-size:10px"><strong style="color:{text}">Evidence:</strong> {_html.escape(f.evidence)}</div>'
            f'<div style="color:{text_dim};font-size:10px"><strong style="color:{text}">Mitigation:</strong> {_html.escape(f.mitigation)}</div>'
            f'</div>'
        )
    return (f'<div style="background:{panel};border:1px solid {border};padding:14px 18px;margin-bottom:16px">'
            f'<div style="font-size:11px;font-weight:700;color:{text};letter-spacing:0.08em;text-transform:uppercase;margin-bottom:6px">Red-Flag Scorecard — top 5 things to defend at IC</div>'
            f'{"".join(rows)}</div>')


def _pattern_match_card(matches) -> str:
    panel = P["panel"]; border = P["border"]; text = P["text"]; text_dim = P["text_dim"]
    acc = P["accent"]; neg = P["negative"]
    if not matches:
        content = (f'<div style="padding:6px 0;color:{text_dim};font-size:11px;font-style:italic">'
                   f'No named-failure patterns match above a 10-point threshold. Target does not structurally resemble any of the 16 decomposed historical bankruptcies.'
                   f'</div>')
    else:
        rows = []
        for m in matches:
            sc = neg if m.match_score >= 50 else (P["warning"] if m.match_score >= 30 else acc)
            rows.append(
                f'<div style="display:grid;grid-template-columns:70px 1fr 90px 60px 1fr;gap:12px;padding:6px 0;border-top:1px solid {border};font-size:11px">'
                f'<div style="font-family:JetBrains Mono,monospace;color:{text};font-weight:700">{_html.escape(m.pattern_id)}</div>'
                f'<div style="color:{text};font-weight:600">{_html.escape(m.case_name)}</div>'
                f'<div style="text-align:right;color:{sc};font-family:JetBrains Mono,monospace;font-weight:700">{m.match_score:.1f}</div>'
                f'<div style="text-align:center;color:{text_dim};font-size:10px">{m.pattern_filing_year}</div>'
                f'<div style="color:{text_dim};font-size:10px">{_html.escape(m.pattern_root_cause)}</div>'
                f'</div>'
            )
        content = "".join(rows)
    return (f'<div style="background:{panel};border:1px solid {border};padding:14px 18px;margin-bottom:16px">'
            f'<div style="font-size:11px;font-weight:700;color:{text};letter-spacing:0.08em;text-transform:uppercase;margin-bottom:6px">Named-Failure Pattern Match</div>'
            f'{content}</div>')


def _comps_card(comps) -> str:
    panel = P["panel"]; border = P["border"]; text = P["text"]; text_dim = P["text_dim"]
    acc = P["accent"]; pos = P["positive"]
    if not comps:
        content = f'<div style="color:{text_dim};font-size:11px;font-style:italic;padding:6px 0">No close comparables in corpus. Consider broadening sector keyword or expanding corpus.</div>'
    else:
        header = (f'<tr><th style="text-align:left;padding:4px 8px;font-size:10px;color:{text_dim};letter-spacing:0.05em;border-bottom:1px solid {border}">Deal</th>'
                  f'<th style="text-align:right;padding:4px 8px;font-size:10px;color:{text_dim};border-bottom:1px solid {border}">Yr</th>'
                  f'<th style="text-align:right;padding:4px 8px;font-size:10px;color:{text_dim};border-bottom:1px solid {border}">EV ($M)</th>'
                  f'<th style="text-align:right;padding:4px 8px;font-size:10px;color:{text_dim};border-bottom:1px solid {border}">Mult</th>'
                  f'<th style="text-align:right;padding:4px 8px;font-size:10px;color:{text_dim};border-bottom:1px solid {border}">MOIC</th>'
                  f'<th style="text-align:right;padding:4px 8px;font-size:10px;color:{text_dim};border-bottom:1px solid {border}">IRR</th>'
                  f'<th style="text-align:left;padding:4px 8px;font-size:10px;color:{text_dim};border-bottom:1px solid {border}">Payer Mix</th></tr>')
        rows = []
        for c in comps:
            ev_cell = f"${c.ev_mm:,.0f}" if c.ev_mm else "—"
            mult_cell = f"{c.implied_multiple:.2f}x" if c.implied_multiple else "—"
            moic_cell = f"{c.realized_moic:.2f}x" if c.realized_moic else "—"
            irr_cell = f"{c.realized_irr*100:.1f}%" if c.realized_irr else "—"
            moic_color = pos if c.realized_moic and c.realized_moic >= 2 else (
                P["warning"] if c.realized_moic and c.realized_moic >= 1 else P["negative"]) if c.realized_moic is not None else text_dim
            rows.append(
                f'<tr><td style="padding:4px 8px;font-family:JetBrains Mono,monospace;font-size:10px;color:{text}">{_html.escape(c.deal_name)}</td>'
                f'<td style="text-align:right;padding:4px 8px;font-size:10px;color:{text_dim}">{c.year}</td>'
                f'<td style="text-align:right;padding:4px 8px;font-family:JetBrains Mono,monospace;font-variant-numeric:tabular-nums;font-size:10px;color:{text}">{ev_cell}</td>'
                f'<td style="text-align:right;padding:4px 8px;font-family:JetBrains Mono,monospace;font-variant-numeric:tabular-nums;font-size:10px;color:{acc}">{mult_cell}</td>'
                f'<td style="text-align:right;padding:4px 8px;font-family:JetBrains Mono,monospace;font-variant-numeric:tabular-nums;font-size:10px;color:{moic_color};font-weight:700">{moic_cell}</td>'
                f'<td style="text-align:right;padding:4px 8px;font-family:JetBrains Mono,monospace;font-variant-numeric:tabular-nums;font-size:10px;color:{text_dim}">{irr_cell}</td>'
                f'<td style="padding:4px 8px;font-size:10px;color:{text_dim}">{_html.escape(c.payer_mix_summary)}</td></tr>'
            )
        content = f'<table style="width:100%;border-collapse:collapse;margin-top:8px"><thead>{header}</thead><tbody>{"".join(rows)}</tbody></table>'
    return (f'<div style="background:{panel};border:1px solid {border};padding:14px 18px;margin-bottom:16px">'
            f'<div style="font-size:11px;font-weight:700;color:{text};letter-spacing:0.08em;text-transform:uppercase;margin-bottom:6px">Top 5 Comparable Corpus Deals</div>'
            f'{content}</div>')


def _benchmark_card(deltas) -> str:
    panel = P["panel"]; border = P["border"]; text = P["text"]; text_dim = P["text_dim"]
    acc = P["accent"]; pos = P["positive"]
    if not deltas:
        return ""
    rows = []
    for d in deltas:
        pct_str = f"{d.target_percentile:.0f}th" if d.target_percentile is not None else "—"
        unit = d.unit if d.unit else ""
        if unit == "$":
            fmt = lambda v: f"${v:,.0f}"
        elif unit == "%":
            fmt = lambda v: f"{v:.1f}%"
        elif unit == "x":
            fmt = lambda v: f"{v:.1f}x"
        else:
            fmt = lambda v: f"{v:,.1f}"
        rows.append(
            f'<div style="padding:8px 0;border-top:1px solid {border};font-size:11px">'
            f'<div style="display:grid;grid-template-columns:110px 1fr 80px 80px 80px 80px;gap:10px;align-items:baseline">'
            f'<div style="font-family:JetBrains Mono,monospace;color:{text};font-weight:700">{_html.escape(d.curve_id)}</div>'
            f'<div style="color:{text}">{_html.escape(d.curve_name)}</div>'
            f'<div style="text-align:right;color:{text_dim};font-family:JetBrains Mono,monospace">P10: {fmt(d.p10)}</div>'
            f'<div style="text-align:right;color:{acc};font-family:JetBrains Mono,monospace;font-weight:700">P50: {fmt(d.p50)}</div>'
            f'<div style="text-align:right;color:{pos};font-family:JetBrains Mono,monospace">P90: {fmt(d.p90)}</div>'
            f'<div style="text-align:right;color:{text};font-family:JetBrains Mono,monospace;font-weight:700">Target: {pct_str}</div>'
            f'</div>'
            f'<div style="color:{text_dim};font-size:10px;margin-top:4px">{_html.escape(d.interpretation)}</div>'
            f'</div>'
        )
    return (f'<div style="background:{panel};border:1px solid {border};padding:14px 18px;margin-bottom:16px">'
            f'<div style="font-size:11px;font-weight:700;color:{text};letter-spacing:0.08em;text-transform:uppercase;margin-bottom:6px">Benchmark Positioning</div>'
            f'{"".join(rows)}</div>')


def _exposure_panels(ncci, oig, team) -> str:
    panel = P["panel"]; border = P["border"]; text = P["text"]; text_dim = P["text_dim"]
    acc = P["accent"]
    # NCCI
    ncci_items = ""
    for e in (ncci.get("top_edits") or [])[:3]:
        override = "MOD-OK" if e.get("override_allowed") else "HARD BUNDLE"
        ncci_items += (f'<li style="color:{text_dim};font-size:10px;margin-bottom:3px">'
                       f'<code style="color:{text};font-family:JetBrains Mono,monospace">{_html.escape(str(e.get("col1", "?")))}+{_html.escape(str(e.get("col2", "?")))}</code> '
                       f'[{override}]: {_html.escape(str(e.get("rationale", "")))}</li>')
    ncci_block = (f'<div style="flex:1">'
                  f'<div style="font-size:10px;color:{text_dim};letter-spacing:0.08em;text-transform:uppercase;margin-bottom:4px">NCCI Edit Exposure</div>'
                  f'<div style="font-size:11px;color:{text};margin-bottom:6px">Density <strong style="color:{acc}">{ncci.get("density", 0):.0f}</strong> '
                  f'· Override-eligible {ncci.get("override_pct", 0):.0f}% · {ncci.get("ptp_edits_affecting", 0)} PTP edits in specialty</div>'
                  f'<ul style="margin:0;padding-left:18px">{ncci_items or "<li style=\"color:#94a3b8;font-size:10px;font-style:italic\">No specialty-specific edits in library</li>"}</ul>'
                  f'</div>')

    # OIG
    oig_items = ""
    for it in (oig.get("top_items") or [])[:3]:
        ev_range = f"${it.get('typical_recovery_low', 0):.0f}M–${it.get('typical_recovery_high', 0):.0f}M"
        oig_items += (f'<li style="color:{text_dim};font-size:10px;margin-bottom:3px">'
                      f'<code style="color:{text};font-family:JetBrains Mono,monospace">{_html.escape(str(it.get("item_id", "?")))}</code>: '
                      f'{_html.escape(str(it.get("title", ""))[:100])} ({ev_range})</li>')
    oig_tier = str(oig.get("risk_tier", "UNKNOWN"))
    oig_tier_c = _severity_color(oig_tier) if oig_tier in ("CRITICAL","HIGH","MEDIUM") else text_dim
    oig_block = (f'<div style="flex:1">'
                 f'<div style="font-size:10px;color:{text_dim};letter-spacing:0.08em;text-transform:uppercase;margin-bottom:4px">OIG Work Plan Exposure</div>'
                 f'<div style="font-size:11px;color:{text};margin-bottom:6px">Tier <strong style="color:{oig_tier_c}">{_html.escape(oig_tier)}</strong> '
                 f'· Open/active: {oig.get("open_active_matches", 0)} · $ at risk: ${oig.get("exposure_mm", 0):.1f}M</div>'
                 f'<ul style="margin:0;padding-left:18px">{oig_items or "<li style=\"color:#94a3b8;font-size:10px;font-style:italic\">No active items for provider type</li>"}</ul>'
                 f'</div>')

    # TEAM
    if team:
        team_tier = str(team.get("risk_tier", "UNAFFECTED"))
        team_tier_c = _severity_color(team_tier) if team_tier in ("CRITICAL", "HIGH", "MEDIUM") else text_dim
        cbsas = ", ".join(str(c)[:30] for c in (team.get("matched_cbsas") or [])[:2])
        team_block = (f'<div style="flex:1">'
                      f'<div style="font-size:10px;color:{text_dim};letter-spacing:0.08em;text-transform:uppercase;margin-bottom:4px">TEAM Exposure (mandatory bundled)</div>'
                      f'<div style="font-size:11px;color:{text};margin-bottom:6px">Tier <strong style="color:{team_tier_c}">{_html.escape(team_tier)}</strong>'
                      f'{f" · PY5 downside ${team.get('py5_downside_mm', 0):.1f}M · CBSAs: {cbsas}" if team_tier != "UNAFFECTED" else ""}'
                      f'</div></div>')
    else:
        team_block = (f'<div style="flex:1">'
                      f'<div style="font-size:10px;color:{text_dim};letter-spacing:0.08em;text-transform:uppercase;margin-bottom:4px">TEAM Exposure</div>'
                      f'<div style="color:{text_dim};font-size:11px;font-style:italic">Not applicable — non-hospital target</div>'
                      f'</div>')

    return (f'<div style="background:{panel};border:1px solid {border};padding:14px 18px;margin-bottom:16px">'
            f'<div style="font-size:11px;font-weight:700;color:{text};letter-spacing:0.08em;text-transform:uppercase;margin-bottom:10px">Regulatory &amp; Compliance Exposure</div>'
            f'<div style="display:flex;gap:20px">{ncci_block}{oig_block}{team_block}</div>'
            f'</div>')


def _bear_card(narrative: str) -> str:
    panel = P["panel"]; border = P["border"]; text = P["text"]; text_dim = P["text_dim"]
    neg = P["negative"]
    return (f'<div style="background:{panel};border:1px solid {border};border-left:3px solid {neg};padding:14px 18px;margin-bottom:16px">'
            f'<div style="font-size:11px;font-weight:700;color:{text};letter-spacing:0.08em;text-transform:uppercase;margin-bottom:6px">Adversarial Engine — Bear-Case Memo</div>'
            f'<div style="font-size:11px;color:{text_dim};line-height:1.5;font-family:JetBrains Mono,monospace">{_html.escape(narrative)}</div>'
            f'</div>')


def _qa_card(questions) -> str:
    panel = P["panel"]; border = P["border"]; text = P["text"]; text_dim = P["text_dim"]
    acc = P["accent"]
    rows = []
    for q in questions:
        rows.append(
            f'<div style="padding:8px 0;border-top:1px solid {border};font-size:11px">'
            f'<div style="display:grid;grid-template-columns:110px 1fr;gap:12px">'
            f'<div style="font-family:JetBrains Mono,monospace;color:{acc};font-size:10px;letter-spacing:0.06em;text-transform:uppercase">{_html.escape(q.category)}</div>'
            f'<div>'
            f'<div style="color:{text};font-weight:600;margin-bottom:3px">Q: {_html.escape(q.question)}</div>'
            f'<div style="color:{text_dim};font-size:10px">Why: {_html.escape(q.why_it_matters)}</div>'
            f'<div style="color:{text_dim};font-size:10px;margin-top:2px">Expect: {_html.escape(q.expected_evidence)}</div>'
            f'</div></div></div>'
        )
    return (f'<div style="background:{panel};border:1px solid {border};padding:14px 18px;margin-bottom:16px">'
            f'<div style="font-size:11px;font-weight:700;color:{text};letter-spacing:0.08em;text-transform:uppercase;margin-bottom:6px">Management Questions for Diligence</div>'
            f'{"".join(rows)}</div>')


def _conditions_card(conditions) -> str:
    panel = P["panel"]; border = P["border"]; text = P["text"]; text_dim = P["text_dim"]
    acc = P["accent"]; pos = P["positive"]
    rows = []
    for c in conditions:
        rows.append(
            f'<div style="padding:8px 0;border-top:1px solid {border};font-size:11px">'
            f'<div style="display:grid;grid-template-columns:90px 100px 1fr;gap:12px">'
            f'<div style="font-family:JetBrains Mono,monospace;color:{acc};font-size:10px;font-weight:700;letter-spacing:0.06em;text-transform:uppercase">{_html.escape(c.day_range)}</div>'
            f'<div style="font-family:JetBrains Mono,monospace;color:{text_dim};font-size:10px">{_html.escape(c.owner)}</div>'
            f'<div>'
            f'<div style="color:{text};font-weight:600;margin-bottom:3px">{_html.escape(c.title)}</div>'
            f'<div style="color:{text_dim};font-size:10px">{_html.escape(c.description)}</div>'
            f'<div style="color:{pos};font-size:10px;margin-top:2px">Success: {_html.escape(c.success_metric)}</div>'
            f'</div></div></div>'
        )
    return (f'<div style="background:{panel};border:1px solid {border};padding:14px 18px;margin-bottom:16px">'
            f'<div style="font-size:11px;font-weight:700;color:{text};letter-spacing:0.08em;text-transform:uppercase;margin-bottom:6px">100-Day Conditions Precedent</div>'
            f'{"".join(rows)}</div>')


def render_ic_brief(params: dict = None) -> str:
    from rcm_mc.data_public.ic_brief import compute_ic_brief
    target = _parse_target_from_params(params or {})
    r = compute_ic_brief(target)

    panel = P["panel"]; panel_alt = P["panel_alt"]
    border = P["border"]; text = P["text"]; text_dim = P["text_dim"]
    acc = P["accent"]

    mult = r.target.ev_mm / r.target.ebitda_mm if (r.target.ev_mm and r.target.ebitda_mm) else None
    kpi_strip = (
        ck_kpi_block("EV", f"${r.target.ev_mm:,.0f}M" if r.target.ev_mm else "—", "", "") +
        ck_kpi_block("EBITDA", f"${r.target.ebitda_mm:,.1f}M" if r.target.ebitda_mm else "—", "", "") +
        ck_kpi_block("Entry Mult", f"{mult:.1f}x" if mult else "—", "EV/EBITDA", "") +
        ck_kpi_block("Hold", f"{r.target.hold_years:.0f} yrs", "", "") +
        ck_kpi_block("Commercial", f"{r.target.commercial_share*100:.0f}%", "", "") +
        ck_kpi_block("Government", f"{(r.target.medicare_share+r.target.medicaid_share)*100:.0f}%", "Mcare+Mcaid", "") +
        ck_kpi_block("Region", r.target.region, r.target.facility_type, "") +
        ck_kpi_block("Corpus", f"{r.corpus_deal_count:,}", "comps pool", "")
    )

    body = f"""
<div style="padding:20px;max-width:1400px;margin:0 auto">
  <div style="margin-bottom:14px">
    <h1 style="font-size:18px;font-weight:700;color:{text};letter-spacing:0.02em">IC Brief Assembler — {_html.escape(r.target.deal_name)}</h1>
    <p style="font-size:12px;color:{text_dim};margin-top:4px">Single-page VP brief · composes every platform module on your hypothetical target · share via URL · ⌘+P to print to PDF for the IC packet</p>
  </div>
  {_form_html(r.target)}
  <div style="display:flex;flex-wrap:wrap;gap:8px;margin-bottom:16px">{kpi_strip}</div>
  {_verdict_card(r.verdict)}
  {_red_flag_card(r.red_flags)}
  {_pattern_match_card(r.pattern_matches)}
  {_comps_card(r.comparable_deals)}
  {_benchmark_card(r.benchmark_deltas)}
  {_exposure_panels(r.ncci_exposure_summary, r.oig_exposure_summary, r.team_exposure_summary)}
  {_bear_card(r.bear_case_memo_narrative)}
  {_qa_card(r.management_questions)}
  {_conditions_card(r.conditions_precedent)}
  <div style="background:{panel_alt};border:1px solid {border};border-left:3px solid {acc};padding:10px 14px;font-size:10px;color:{text_dim};font-family:JetBrains Mono,monospace;line-height:1.5">
    <strong style="color:{text}">Methodology:</strong> {_html.escape(r.methodology_note)}
  </div>
</div>"""

    return chartis_shell(body, f"IC Brief — {r.target.deal_name[:40]}", active_nav="/ic-brief")
