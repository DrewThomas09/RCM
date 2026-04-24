"""NCCI Edit Compliance Scanner — /ncci-scanner."""
from __future__ import annotations

import html as _html
from rcm_mc.ui._chartis_kit import P, chartis_shell, ck_kpi_block


def _tier_color(t: str) -> str:
    return {
        "HIGH": P["negative"],
        "MEDIUM": P["warning"],
        "LOW": P["positive"],
    }.get(t, P["text_dim"])


def _indicator_label(ind: int) -> tuple[str, str]:
    if ind == 0:
        return ("HARD BUNDLE", P["negative"])
    if ind == 1:
        return ("MOD OVERRIDE", P["warning"])
    return ("N/A", P["text_dim"])


def _risk_label(audit_risk: str) -> str:
    r = audit_risk.lower()
    if r == "high":
        return P["negative"]
    if r == "medium":
        return P["warning"]
    return P["positive"]


def _status_color(s: str) -> str:
    return {
        "open": P["negative"],
        "active": P["warning"],
        "completed": P["text_dim"],
    }.get(s, P["text_dim"])


def _ptp_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]
    cols = [("Col 1 CPT", "left"), ("Col 2 CPT", "left"), ("Col 1 Service", "left"),
            ("Col 2 Service", "left"), ("Specialty", "left"),
            ("Annual Vol (M)", "right"), ("Allowed $", "right"),
            ("Override", "center"), ("Effective", "right")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    # Sort by annual claim volume × allowed amount (PE-exposure proxy)
    ranked = sorted(items, key=lambda e: e.annual_claim_volume_m * e.typical_allowed_col1, reverse=True)
    for i, e in enumerate(ranked):
        rb = panel_alt if i % 2 == 0 else bg
        ov_label, ov_c = _indicator_label(e.modifier_indicator)
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:700">{_html.escape(e.column1_code)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{acc};font-weight:700">{_html.escape(e.column2_code)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim};max-width:240px">{_html.escape(e.col1_descriptor)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim};max-width:240px">{_html.escape(e.col2_descriptor)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text}">{_html.escape(e.specialty)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos};font-weight:700">{e.annual_claim_volume_m:.2f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">${e.typical_allowed_col1:,.2f}</td>',
            f'<td style="text-align:center;padding:5px 10px"><span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{ov_c};border:1px solid {ov_c};border-radius:2px;letter-spacing:0.06em">{ov_label}</span></td>',
            f'<td style="text-align:right;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(e.effective_date)}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _mue_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]
    cols = [("CPT / HCPCS", "left"), ("Descriptor", "left"), ("Max Units", "right"),
            ("Adjudication", "left"), ("Specialty", "left"), ("Rationale", "left")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, m in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:700">{_html.escape(m.code)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim};max-width:240px">{_html.escape(m.descriptor)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos};font-weight:700">{m.mue_value}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{acc}">{_html.escape(m.mue_adjudication_type)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text}">{_html.escape(m.specialty)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim};max-width:380px">{_html.escape(m.rationale)}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _footprint_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]; neg = P["negative"]
    cols = [("Specialty", "left"), ("Top CPTs", "left"), ("Claim Vol (M/yr)", "right"),
            ("PTP Edits", "right"), ("MUE Limits", "right"),
            ("Density Score", "right"), ("Override %", "right")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, f in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        d_c = neg if f.edit_density_score >= 55 else (acc if f.edit_density_score >= 25 else text_dim)
        o_c = pos if f.override_eligibility_pct >= 50 else (acc if f.override_eligibility_pct >= 30 else text_dim)
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:700">{_html.escape(f.specialty)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{acc};max-width:320px">{_html.escape(f.top_cpt_codes)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{f.annual_claim_volume_m:,.1f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{f.ptp_edits_affecting}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{f.mue_limits_affecting}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{d_c};font-weight:700">{f.edit_density_score:.2f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{o_c};font-weight:700">{f.override_eligibility_pct:.1f}%</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _exposure_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]
    cols = [("Deal", "left"), ("Year", "right"), ("Buyer", "left"),
            ("Inferred Specialty", "left"), ("Density", "right"),
            ("PTP Edits", "right"), ("Override %", "right"),
            ("EV ($M)", "right"), ("Denial Exp ($M/yr)", "right"),
            ("Risk Tier", "center")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, d in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        tc = _tier_color(d.risk_tier)
        ev_cell = f"${d.ev_mm:,.1f}" if d.ev_mm is not None else "—"
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">{_html.escape(d.deal_name)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{d.year or "—"}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim};max-width:200px">{_html.escape(d.buyer)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{acc}">{_html.escape(d.inferred_specialty)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{tc};font-weight:700">{d.edit_density_score:.2f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{d.ptp_edits_affecting}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{d.override_eligibility_pct:.1f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos}">{ev_cell}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{acc};font-weight:700">${d.estimated_annual_denial_exposure_m:,.2f}</td>',
            f'<td style="text-align:center;padding:5px 10px"><span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{tc};border:1px solid {tc};border-radius:2px;letter-spacing:0.06em">{_html.escape(d.risk_tier)}</span></td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _modifier_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]
    cols = [("Mod", "left"), ("Name", "left"), ("Use Case", "left"),
            ("Success %", "right"), ("Audit Risk", "center"), ("Notes", "left")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, m in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        r_c = _risk_label(m.audit_risk)
        s_c = pos if m.success_rate_pct >= 85 else (acc if m.success_rate_pct >= 75 else text_dim)
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:700">{_html.escape(m.modifier)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:11px;color:{text};font-weight:600">{_html.escape(m.full_name)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim};max-width:260px">{_html.escape(m.use_case)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{s_c};font-weight:700">{m.success_rate_pct:.1f}%</td>',
            f'<td style="text-align:center;padding:5px 10px"><span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{r_c};border:1px solid {r_c};border-radius:2px;letter-spacing:0.06em">{_html.escape(m.audit_risk.upper())}</span></td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim};max-width:340px">{_html.escape(m.notes)}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _crosswalk_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]
    cols = [("Edit Category", "left"), ("OIG Work Plan Item", "left"),
            ("Year", "right"), ("Status", "center"),
            ("Typical Recovery ($M)", "right"), ("Affected Specialties", "left")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, c in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        s_c = _status_color(c.status)
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:700">{_html.escape(c.edit_category)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim};max-width:380px">{_html.escape(c.oig_work_plan_item)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{acc};font-weight:600">{c.year_added}</td>',
            f'<td style="text-align:center;padding:5px 10px"><span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{s_c};border:1px solid {s_c};border-radius:2px;letter-spacing:0.06em">{_html.escape(c.status.upper())}</span></td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos};font-weight:700">${c.typical_recovery_m:,.1f}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim};max-width:260px">{_html.escape(c.affected_specialties)}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def render_ncci_scanner(params: dict = None) -> str:
    from rcm_mc.data_public.ncci_edits import compute_ncci_scanner
    r = compute_ncci_scanner()

    panel = P["panel"]; panel_alt = P["panel_alt"]
    border = P["border"]; text = P["text"]; text_dim = P["text_dim"]
    acc = P["accent"]

    kpi_strip = (
        ck_kpi_block("PTP Edits Tracked", str(r.total_ptp_edits), "", "") +
        ck_kpi_block("MUE Limits", str(r.total_mue_limits), "", "") +
        ck_kpi_block("Specialties Profiled", str(r.total_specialties_profiled), "", "") +
        ck_kpi_block("Avg Override Elig.", f"{r.avg_override_eligibility_pct:.1f}%", "", "") +
        ck_kpi_block("HIGH-Risk Deals", str(r.high_risk_deals), "", "") +
        ck_kpi_block("Total Denial Exp.", f"${r.total_estimated_denial_exposure_m:,.0f}M", "", "") +
        ck_kpi_block("Corpus Deals", f"{r.corpus_deal_count:,}", "", "")
    )

    ptp_tbl = _ptp_table(r.ptp_edits)
    mue_tbl = _mue_table(r.mue_limits)
    fp_tbl = _footprint_table(r.specialty_footprints)
    ex_tbl = _exposure_table(r.deal_exposures)
    mod_tbl = _modifier_table(r.modifier_overrides)
    xw_tbl = _crosswalk_table(r.audit_crosswalks)

    cell = f"background:{panel};border:1px solid {border};padding:16px;margin-bottom:16px"
    h3 = f"font-size:11px;font-weight:600;letter-spacing:0.08em;color:{text_dim};text-transform:uppercase;margin-bottom:10px"

    body = f"""
<div style="padding:20px;max-width:1400px;margin:0 auto">
  <div style="margin-bottom:20px">
    <h1 style="font-size:18px;font-weight:700;color:{text};letter-spacing:0.02em">NCCI Edit Compliance Scanner</h1>
    <p style="font-size:12px;color:{text_dim};margin-top:4px">{r.total_ptp_edits} curated PTP code-pair edits · {r.total_mue_limits} MUE unit-of-service limits · {r.total_specialties_profiled} specialty footprints · {r.high_risk_deals} HIGH-risk deals in corpus · ${r.total_estimated_denial_exposure_m:,.0f}M aggregate annual denial exposure — {r.corpus_deal_count:,} corpus deals scanned</p>
  </div>
  <div style="display:flex;flex-wrap:wrap;gap:8px;margin-bottom:20px">{kpi_strip}</div>
  <div style="{cell}"><div style="{h3}">High-Impact PTP Edits — ranked by national annual $ exposure</div>{ptp_tbl}</div>
  <div style="{cell}"><div style="{h3}">Medically Unlikely Edits (MUE) — Unit-of-Service Caps</div>{mue_tbl}</div>
  <div style="{cell}"><div style="{h3}">Specialty Footprint — Edit Density by Specialty</div>{fp_tbl}</div>
  <div style="{cell}"><div style="{h3}">Top 50 Corpus Deals by Inferred NCCI Edit Exposure</div>{ex_tbl}</div>
  <div style="{cell}"><div style="{h3}">Modifier Override Reference — the billing-team operational lever</div>{mod_tbl}</div>
  <div style="{cell}"><div style="{h3}">NCCI → OIG Work Plan Audit Crosswalk</div>{xw_tbl}</div>
  <div style="background:{panel_alt};border:1px solid {border};border-left:3px solid {acc};padding:12px 16px;font-size:11px;color:{text_dim};margin-bottom:16px">
    <strong style="color:{text}">NCCI Diligence Thesis:</strong>
    Every Medicare claim is scrubbed against NCCI PTP + MUE edits before payment;
    commercial payers layer identical logic via ClaimsXten / TriZetto engines.
    A target's code-pair footprint is therefore a direct measurable driver of pre-adjustment billing risk —
    independent of what the QoR package claims about clean-claim rates.
    Across the {r.corpus_deal_count:,}-deal corpus, inferred specialty classification shows
    <strong style="color:{text}">{r.high_risk_deals} deals</strong> in the HIGH-density tier (edit density ≥55) with
    <strong style="color:{text}">${r.total_estimated_denial_exposure_m:,.0f}M</strong> estimated aggregate annual denial exposure.
    Fertility, Physical Therapy, Pain Management, and Dermatology rollups sit disproportionately in the top quartile —
    driven by modifier-59/25 override patterns that are active OIG Work Plan audit targets.
    {r.avg_override_eligibility_pct:.1f}% of tracked PTP edits permit modifier override, but the 59-modifier carries a
    high audit-risk tag; the X{{EPSU}} variants (XE/XS/XP/XU, 2015) are the post-diligence remediation lever a
    new billing-ops team should push toward during the 100-day plan.
    Crosswalk to active OIG Work Plan items shows ${sum(c.typical_recovery_m for c in r.audit_crosswalks):,.0f}M in
    typical-recovery program-wide at federal audit focus today —
    pre-close modeling should haircut EBITDA for expected-case recoupment in any specialty above the 75th density percentile.
  </div>
</div>"""

    return chartis_shell(body, "NCCI Edit Compliance Scanner", active_nav="/ncci-scanner")
