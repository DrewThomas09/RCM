"""Referring Radiology & Diagnostic Imaging atlas — /radiology-imaging.

Renders the data_public.radiology_imaging result: the CMS claims atlas
(radiology CPT/HCPCS with CY2025 PFS economics), mammography & breast imaging,
the live CMS coverage-connection loop (NCDs/LCDs), MAC payer jurisdictions,
state- and county-level data (incl. payer mix), the big freestanding operators,
the AI-implementation landscape, and the recent macro factors.
"""
from __future__ import annotations

import html as _html

from rcm_mc.ui._chartis_kit import (
    P,
    chartis_shell,
    ck_bar_row,
    ck_data_cell,
    ck_kpi_block,
    ck_page_actions,
    ck_value_anchor,
)


def _modality_tone(modality: str) -> str:
    return {
        "Mammography": "teal",
        "CT": "navy",
        "MRI": "positive",
        "Ultrasound": "warning",
        "PET/CT": "negative",
        "Nuclear": "negative",
        "X-ray": "navy",
        "DXA": "warning",
    }.get(modality, "teal")


def _section(title: str, inner: str) -> str:
    panel = P["panel"]; border = P["border"]; text_dim = P["text_dim"]
    cell = f"background:{panel};border:1px solid {border};padding:16px;margin-bottom:16px"
    h3 = (f"font-size:11px;font-weight:600;letter-spacing:0.08em;color:{text_dim};"
          f"text-transform:uppercase;margin-bottom:10px")
    return f'<div style="{cell}"><div style="{h3}">{_html.escape(title)}</div>{inner}</div>'


def _table(cols, rows_html: str) -> str:
    ths = "".join(ck_data_cell(c, align=a, is_header=True) for c, a in cols)
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{rows_html}</tbody></table></div>')


# ─────────────────────────────────────────────────────────────────────────────
# 1) CMS claims atlas — CPT/HCPCS codes
# ─────────────────────────────────────────────────────────────────────────────
def _cpt_table(items) -> str:
    text_dim = P["text_dim"]
    cols = [("CPT/HCPCS", "left"), ("Modality", "center"), ("Descriptor", "left"),
            ("Cat.", "center"), ("Work RVU", "right"), ("Global $", "right"),
            ("Prof (26) $", "right"), ("Tech (TC) $", "right"), ("~Part-B vol (k)", "right")]
    trs = []
    for c in items:
        tone = _modality_tone(c.modality)
        cat_color = {"screening": P["positive"], "screening-addon": P["accent"],
                     "diagnostic": P["text_dim"]}.get(c.category, P["text_dim"])
        cells = [
            ck_data_cell(_html.escape(c.code), mono=True, weight=700),
            f'<td style="text-align:center;padding:5px 10px;font-family:JetBrains Mono,monospace;'
            f'font-size:10px;color:var(--sc-{tone},{P["accent"]});font-weight:700">{_html.escape(c.modality)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(c.descriptor)}</td>',
            f'<td style="text-align:center;padding:5px 10px;font-family:JetBrains Mono,monospace;'
            f'font-size:9px;color:{cat_color};font-weight:700">{_html.escape(c.category.upper())}</td>',
            ck_data_cell(f"{c.work_rvu:.2f}", align="right", mono=True, tone="dim"),
            ck_data_cell(f"${c.global_rate:,.2f}", align="right", mono=True, tone="pos", weight=700),
            ck_data_cell(f"${c.prof_26:,.2f}", align="right", mono=True, tone="acc"),
            ck_data_cell(f"${c.tech_tc:,.2f}", align="right", mono=True),
            ck_data_cell(f"{c.annual_medicare_vol_k:,.0f}", align="right", mono=True, tone="dim"),
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return _table(cols, "".join(trs))


def _modality_chart(items) -> str:
    """Advanced-imaging Part-B volume by modality — where the claims dollars
    concentrate before the partner reads the code grid."""
    by_mod = {}
    for c in items:
        by_mod.setdefault(c.modality, 0.0)
        by_mod[c.modality] += c.annual_medicare_vol_k
    total = sum(by_mod.values()) or 1.0
    ranked = sorted(by_mod.items(), key=lambda kv: kv[1], reverse=True)
    rows = [ck_bar_row(m, f"{v:,.0f}k", v / total * 100.0, tone=_modality_tone(m)) for m, v in ranked]
    return (
        '<div style="margin-bottom:14px">' + "".join(rows) +
        '<div style="font-size:10px;color:var(--sc-text-faint);margin-top:6px;'
        'font-family:JetBrains Mono,monospace">Bar = share of tracked Part-B service volume · '
        'value = approx services (thousands) · tone = modality</div></div>'
    )


# ─────────────────────────────────────────────────────────────────────────────
# 2) Mammography & breast imaging
# ─────────────────────────────────────────────────────────────────────────────
def _mammography_table(items) -> str:
    text_dim = P["text_dim"]
    cols = [("Metric", "left"), ("Value", "right"), ("Detail", "left"), ("Source", "left")]
    trs = []
    for m in items:
        cells = [
            ck_data_cell(_html.escape(m.metric), mono=True, weight=600),
            ck_data_cell(_html.escape(m.value), align="right", mono=True, tone="acc", weight=700),
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(m.detail)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:9px;font-family:JetBrains Mono,monospace;'
            f'color:{P["text_faint"]}">{_html.escape(m.source)}</td>',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return _table(cols, "".join(trs))


# ─────────────────────────────────────────────────────────────────────────────
# 3) CMS coverage connections — the loop
# ─────────────────────────────────────────────────────────────────────────────
def _coverage_table(items) -> str:
    text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]; warn = P["warning"]
    cols = [("Type", "center"), ("ID", "left"), ("Imaging Topic", "left"), ("Policy Title", "left"),
            ("Contractor (MAC)", "left"), ("Effective", "center"), ("Updated", "center"), ("Status", "center")]
    trs = []
    for c in items:
        t_color = P["navy"] if c.doc_type == "NCD" else acc
        s_color = pos if c.status == "active" else warn
        id_link = (f'<a href="{_html.escape(c.url)}" target="_blank" rel="noopener" '
                   f'style="color:{acc};text-decoration:none;font-weight:700">{_html.escape(c.display_id)}</a>')
        cells = [
            f'<td style="text-align:center;padding:5px 10px;font-family:JetBrains Mono,monospace;'
            f'font-size:10px;color:{t_color};font-weight:700">{_html.escape(c.doc_type)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px">{id_link}</td>',
            ck_data_cell(_html.escape(c.topic), mono=True, weight=600),
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(c.title)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(c.contractor)}</td>',
            ck_data_cell(_html.escape(c.effective_date), align="center", mono=True, tone="dim"),
            ck_data_cell(_html.escape(c.last_updated), align="center", mono=True, tone="acc"),
            f'<td style="text-align:center;padding:5px 10px;font-family:JetBrains Mono,monospace;'
            f'font-size:9px;color:{s_color};font-weight:700">{_html.escape(c.status.upper())}</td>',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return _table(cols, "".join(trs))


# ─────────────────────────────────────────────────────────────────────────────
# 4) MAC payer jurisdictions
# ─────────────────────────────────────────────────────────────────────────────
def _mac_table(items) -> str:
    text_dim = P["text_dim"]
    cols = [("MAC (Part-B payer)", "left"), ("Jurisdiction", "center"), ("States", "left"),
            ("# States", "right"), ("Contracts", "right"), ("Note", "left")]
    trs = []
    for m in items:
        cells = [
            ck_data_cell(_html.escape(m.mac_name), mono=True, weight=600),
            ck_data_cell(_html.escape(m.jurisdiction), align="center", mono=True, tone="acc", weight=700),
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(m.part_b_states)}</td>',
            ck_data_cell(str(m.state_count), align="right", mono=True),
            ck_data_cell(str(m.contract_records), align="right", mono=True, tone="dim"),
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(m.note)}</td>',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return _table(cols, "".join(trs))


# ─────────────────────────────────────────────────────────────────────────────
# 5a) State profiles
# ─────────────────────────────────────────────────────────────────────────────
def _state_table(items) -> str:
    text_dim = P["text_dim"]
    cols = [("State", "left"), ("MAC", "left"), ("Juris.", "center"), ("Imaging Centers", "right"),
            ("MQSA Fac.", "right"), ("Medicare Img $M", "right"), ("Util / 1k benes", "right"),
            ("DBT (3D) %", "right")]
    trs = []
    for s in items:
        cells = [
            ck_data_cell(f"{_html.escape(s.state)} ({_html.escape(s.postal)})", mono=True, weight=700),
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(s.mac_name)}</td>',
            ck_data_cell(_html.escape(s.mac_jurisdiction), align="center", mono=True, tone="acc"),
            ck_data_cell(f"{s.imaging_centers:,}", align="right", mono=True, weight=600),
            ck_data_cell(f"{s.mqsa_facilities:,}", align="right", mono=True),
            ck_data_cell(f"${s.medicare_imaging_spend_mm:,.0f}", align="right", mono=True, tone="pos", weight=600),
            ck_data_cell(f"{s.util_per_1k_benes:,.0f}", align="right", mono=True, tone="dim"),
            ck_data_cell(f"{s.dbt_penetration_pct:.0f}%", align="right", mono=True, tone="acc"),
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return _table(cols, "".join(trs))


def _state_chart(items) -> str:
    ranked = sorted(items, key=lambda s: s.imaging_centers, reverse=True)
    total = sum(s.imaging_centers for s in items) or 1
    rows = [ck_bar_row(f"{s.state} · {s.mac_jurisdiction}", f"{s.imaging_centers:,}",
                       s.imaging_centers / total * 100.0, tone="teal") for s in ranked]
    return ('<div style="margin-bottom:14px">' + "".join(rows) +
            '<div style="font-size:10px;color:var(--sc-text-faint);margin-top:6px;'
            'font-family:JetBrains Mono,monospace">Bar = share of tracked freestanding imaging centers · '
            'label shows the Medicare MAC jurisdiction that prices each state\'s Part-B imaging</div></div>')


# ─────────────────────────────────────────────────────────────────────────────
# 5b) County payer mix — stacked payer bars
# ─────────────────────────────────────────────────────────────────────────────
def _payer_stack(medicare, medicaid, commercial, uninsured) -> str:
    segs = [
        (commercial, P["positive"], "Commercial"),
        (medicare, P["navy"], "Medicare"),
        (medicaid, P["warning"], "Medicaid"),
        (uninsured, P["negative"], "Uninsured"),
    ]
    bars = "".join(
        f'<span title="{lbl} {v:.0f}%" style="display:inline-block;height:11px;width:{max(0.5, v):.1f}%;'
        f'background:{color}"></span>'
        for v, color, lbl in segs
    )
    return (f'<span style="display:inline-flex;width:160px;border:1px solid {P["border"]};'
            f'vertical-align:middle;overflow:hidden">{bars}</span>')


def _county_table(items) -> str:
    text_dim = P["text_dim"]
    cols = [("County", "left"), ("State", "center"), ("FIPS", "center"), ("Pop (k)", "right"),
            ("Payer Mix (Comm·MCR·MCD·Unins)", "left"), ("Medicare %", "right"), ("Medicaid %", "right"),
            ("Commercial %", "right"), ("Unins %", "right"), ("Centers", "right"), ("Dominant", "center")]
    trs = []
    for c in items:
        dom_color = {"Commercial": P["positive"], "Medicaid": P["warning"],
                     "Medicare": P["navy"]}.get(c.dominant_payer, P["text_dim"])
        cells = [
            ck_data_cell(_html.escape(c.county), mono=True, weight=600),
            ck_data_cell(_html.escape(c.state), align="center", mono=True, tone="dim"),
            ck_data_cell(_html.escape(c.fips), align="center", mono=True, tone="dim"),
            ck_data_cell(f"{c.population_k:,.0f}", align="right", mono=True),
            f'<td style="padding:5px 10px">{_payer_stack(c.medicare_pct, c.medicaid_pct, c.commercial_pct, c.uninsured_pct)}</td>',
            ck_data_cell(f"{c.medicare_pct:.0f}%", align="right", mono=True),
            ck_data_cell(f"{c.medicaid_pct:.0f}%", align="right", mono=True, tone="dim"),
            ck_data_cell(f"{c.commercial_pct:.0f}%", align="right", mono=True, tone="pos", weight=600),
            ck_data_cell(f"{c.uninsured_pct:.0f}%", align="right", mono=True, tone="neg"),
            ck_data_cell(f"{c.imaging_centers:,}", align="right", mono=True, tone="dim"),
            f'<td style="text-align:center;padding:5px 10px;font-family:JetBrains Mono,monospace;'
            f'font-size:9px;color:{dom_color};font-weight:700">{_html.escape(c.dominant_payer.upper())}</td>',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return _table(cols, "".join(trs))


# ─────────────────────────────────────────────────────────────────────────────
# 6) Big players
# ─────────────────────────────────────────────────────────────────────────────
def _players_table(items) -> str:
    text_dim = P["text_dim"]
    cols = [("Operator", "left"), ("Ownership", "left"), ("Sponsor / Cap", "left"),
            ("Centers", "right"), ("Footprint", "left"), ("AI Platform", "left"), ("Note", "left")]
    trs = []
    for p in items:
        cells = [
            ck_data_cell(_html.escape(p.name), mono=True, weight=700),
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(p.ownership)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(p.sponsor)}</td>',
            ck_data_cell(f"{p.centers:,}", align="right", mono=True, tone="acc", weight=700),
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(p.footprint_states)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(p.ai_platform)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(p.note)}</td>',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return _table(cols, "".join(trs))


def _players_chart(items) -> str:
    # Exclude the long-tail aggregate so the named operators are legible.
    named = [p for p in items if p.centers < 1000]
    ranked = sorted(named, key=lambda p: p.centers, reverse=True)
    mx = max((p.centers for p in ranked), default=1)
    rows = [ck_bar_row(p.name, f"{p.centers:,}", p.centers / mx * 100.0, tone="navy") for p in ranked]
    return ('<div style="margin-bottom:14px">' + "".join(rows) +
            '<div style="font-size:10px;color:var(--sc-text-faint);margin-top:6px;'
            'font-family:JetBrains Mono,monospace">Bar = center count vs largest named operator · '
            'the ~5,800-center long tail (independents) is the roll-up runway, shown in the table</div></div>')


# ─────────────────────────────────────────────────────────────────────────────
# 7) AI implementation
# ─────────────────────────────────────────────────────────────────────────────
def _ai_table(items) -> str:
    text_dim = P["text_dim"]
    cols = [("Vendor", "left"), ("Product", "left"), ("FDA", "left"), ("Modality", "center"),
            ("Use Case", "left"), ("Reimbursement Path", "left"), ("Code", "center"), ("Adoption", "left")]
    trs = []
    for a in items:
        cells = [
            ck_data_cell(_html.escape(a.vendor), mono=True, weight=700),
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(a.product)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:9px;font-family:JetBrains Mono,monospace;'
            f'color:{P["positive"]}">{_html.escape(a.fda_status)}</td>',
            ck_data_cell(_html.escape(a.modality), align="center", mono=True, tone="acc"),
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(a.use_case)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(a.reimbursement_path)}</td>',
            ck_data_cell(_html.escape(a.code), align="center", mono=True, tone="dim"),
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(a.adoption)}</td>',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return _table(cols, "".join(trs))


# ─────────────────────────────────────────────────────────────────────────────
# 8) Recent factors
# ─────────────────────────────────────────────────────────────────────────────
def _factors_table(items) -> str:
    text_dim = P["text_dim"]
    cols = [("Factor", "left"), ("Category", "center"), ("Detail", "left"), ("Direction", "center"), ("Year", "center")]
    trs = []
    for f in items:
        d_color = {"tailwind": P["positive"], "headwind": P["negative"], "mixed": P["warning"]}.get(f.direction, P["text_dim"])
        d_arrow = {"tailwind": "▲ TAILWIND", "headwind": "▼ HEADWIND", "mixed": "◆ MIXED"}.get(f.direction, f.direction.upper())
        cells = [
            ck_data_cell(_html.escape(f.factor), mono=True, weight=600),
            f'<td style="text-align:center;padding:5px 10px;font-family:JetBrains Mono,monospace;'
            f'font-size:9px;color:{text_dim}">{_html.escape(f.category.upper())}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(f.detail)}</td>',
            f'<td style="text-align:center;padding:5px 10px;font-family:JetBrains Mono,monospace;'
            f'font-size:9px;color:{d_color};font-weight:700">{d_arrow}</td>',
            ck_data_cell(_html.escape(f.year), align="center", mono=True, tone="dim"),
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return _table(cols, "".join(trs))


# ─────────────────────────────────────────────────────────────────────────────
# 9) Payer-type share
# ─────────────────────────────────────────────────────────────────────────────
def _payer_share_chart(items) -> str:
    tone_map = {"Commercial / Employer": "positive", "Medicare FFS": "navy",
                "Medicare Advantage": "teal", "Medicaid / Managed Medicaid": "warning",
                "Self-pay / Other": "negative"}
    rows = [ck_bar_row(f"{p.payer_type}  ({p.trend})", f"{p.imaging_revenue_share_pct:.0f}%",
                       p.imaging_revenue_share_pct, tone=tone_map.get(p.payer_type, "teal"))
            for p in items]
    return ('<div style="margin-bottom:14px">' + "".join(rows) +
            '<div style="font-size:10px;color:var(--sc-text-faint);margin-top:6px;'
            'font-family:JetBrains Mono,monospace">Approx imaging-revenue share by payer type · '
            'commercial is the rate driver; Medicare FFS rate is PFS-cut-exposed; MA is the fastest-growing mix</div></div>')


# ── Modality sub-segments ────────────────────────────────────────────────────
def _modality_segment_table(items) -> str:
    text_dim = P["text_dim"]
    cols = [("Modality", "left"), ("US Mkt $B", "right"), ("Vol / yr (M)", "right"),
            ("Growth", "right"), ("Avg Medicare $", "right"), ("Capex / unit $k", "right"),
            ("Gross Margin", "right"), ("Room min", "right"), ("Supply Dependency", "left"), ("Dynamics", "left")]
    trs = []
    for m in items:
        vol = f"{m.annual_volume_mm:,.0f}" if m.annual_volume_mm else "—"
        avg = f"${m.avg_medicare_global:,.0f}" if m.avg_medicare_global else "—"
        room = f"{m.room_time_min}" if m.room_time_min else "—"
        cells = [
            ck_data_cell(_html.escape(m.modality), mono=True, weight=700),
            ck_data_cell(f"${m.us_market_bn:,.1f}", align="right", mono=True, tone="pos", weight=600),
            ck_data_cell(vol, align="right", mono=True),
            ck_data_cell(f"{m.growth_pct:.0f}%", align="right", mono=True, tone="acc"),
            ck_data_cell(avg, align="right", mono=True),
            ck_data_cell(f"{m.equipment_capex_k:,.0f}", align="right", mono=True, tone="dim"),
            ck_data_cell(f"{m.gross_margin_pct:.0f}%", align="right", mono=True, weight=600),
            ck_data_cell(room, align="right", mono=True, tone="dim"),
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(m.supply_exposure)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(m.dynamics)}</td>',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return _table(cols, "".join(trs))


def _modality_segment_chart(items) -> str:
    ranked = sorted(items, key=lambda m: m.us_market_bn, reverse=True)
    total = sum(m.us_market_bn for m in items) or 1.0
    tone = {"CT (computed tomography)": "navy", "MRI (magnetic resonance)": "positive",
            "Mammography / breast": "teal", "PET/CT & nuclear medicine": "negative"}
    rows = [ck_bar_row(f"{m.modality}  (+{m.growth_pct:.0f}%/yr)", f"${m.us_market_bn:,.1f}B",
                       m.us_market_bn / total * 100.0, tone=tone.get(m.modality, "warning")) for m in ranked]
    return ('<div style="margin-bottom:14px">' + "".join(rows) +
            '<div style="font-size:10px;color:var(--sc-text-faint);margin-top:6px;'
            'font-family:JetBrains Mono,monospace">Bar = approx US services-revenue share by modality · '
            'value = $B · label shows volume CAGR (illustrative)</div></div>')


# ── Supply shocks ────────────────────────────────────────────────────────────
def _supply_shock_table(items) -> str:
    text_dim = P["text_dim"]; text = P["text"]
    sev_color = {"high": P["negative"], "medium": P["warning"], "low": P["positive"]}
    cols = [("Supply Shock", "left"), ("Cat.", "center"), ("Mechanism", "left"),
            ("Peak Impact", "left"), ("Window", "center"), ("Exposure", "left"),
            ("Mitigation", "left"), ("Severity", "center")]
    trs = []
    for s in items:
        sc = sev_color.get(s.severity, text_dim)
        cells = [
            ck_data_cell(_html.escape(s.shock), mono=True, weight=700),
            f'<td style="text-align:center;padding:5px 10px;font-family:JetBrains Mono,monospace;'
            f'font-size:9px;color:{text_dim}">{_html.escape(s.category.upper())}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(s.mechanism)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text}">{_html.escape(s.peak_impact)}</td>',
            ck_data_cell(_html.escape(s.window), align="center", mono=True, tone="dim"),
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(s.exposure)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(s.mitigation)}</td>',
            f'<td style="text-align:center;padding:5px 10px;font-family:JetBrains Mono,monospace;'
            f'font-size:9px;color:{sc};font-weight:700">{_html.escape(s.severity.upper())}</td>',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return _table(cols, "".join(trs))


# ── Unit economics (center P&L waterfall) ────────────────────────────────────
def _unit_econ_table(items) -> str:
    text_dim = P["text_dim"]; text = P["text"]; pos = P["positive"]; neg = P["negative"]; panel_alt = P["panel_alt"]
    cols = [("Line Item", "left"), ("% of Net Revenue", "right"), ("Per Blended Study", "right"), ("Note", "left")]
    trs = []
    for u in items:
        pct_color = pos if u.pct_of_revenue > 0 else neg
        row_bg = f"background:{panel_alt}" if u.is_total else ""
        weight = 700 if u.is_total else 400
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;'
            f'font-size:11px;font-weight:{weight};color:{text};{row_bg}">{_html.escape(u.line_item)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;'
            f'font-family:JetBrains Mono,monospace;font-size:11px;font-weight:{weight};color:{pct_color};{row_bg}">{u.pct_of_revenue:+.0f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;'
            f'font-family:JetBrains Mono,monospace;font-size:11px;font-weight:{weight};color:{pct_color};{row_bg}">${u.per_scan:,.2f}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim};{row_bg}">{_html.escape(u.note)}</td>',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return _table(cols, "".join(trs))


def _econ_driver_table(items) -> str:
    text_dim = P["text_dim"]
    cols = [("Driver", "left"), ("Definition", "left"), ("Typical", "left"), ("Why it moves the P&L", "left")]
    trs = []
    for d in items:
        cells = [
            ck_data_cell(_html.escape(d.driver), mono=True, weight=700),
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(d.definition)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;font-family:JetBrains Mono,monospace;color:{P["accent"]}">{_html.escape(d.typical_value)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(d.lever)}</td>',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return _table(cols, "".join(trs))


# ── Radiology Partners diligence ─────────────────────────────────────────────
def _rp_diligence_table(items) -> str:
    text_dim = P["text_dim"]; text = P["text"]
    flag_color = {"positive": P["positive"], "watch": P["warning"], "risk": P["negative"]}
    flag_label = {"positive": "✓ STRENGTH", "watch": "◆ WATCH", "risk": "▼ RISK"}
    cols = [("Area", "center"), ("Metric", "left"), ("Value", "left"), ("Diligence Read", "left"), ("Flag", "center")]
    trs = []
    for d in items:
        fc = flag_color.get(d.flag, text_dim)
        cells = [
            f'<td style="text-align:center;padding:5px 10px;font-family:JetBrains Mono,monospace;'
            f'font-size:9px;color:{text_dim}">{_html.escape(d.category.upper())}</td>',
            ck_data_cell(_html.escape(d.metric), mono=True, weight=600),
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;font-family:JetBrains Mono,monospace;color:{text}">{_html.escape(d.value)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(d.assessment)}</td>',
            f'<td style="text-align:center;padding:5px 10px;font-family:JetBrains Mono,monospace;'
            f'font-size:9px;color:{fc};font-weight:700">{_html.escape(flag_label.get(d.flag, d.flag.upper()))}</td>',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return _table(cols, "".join(trs))


# ── AI model build ───────────────────────────────────────────────────────────
def _ai_build_table(items) -> str:
    text_dim = P["text_dim"]; text = P["text"]
    cols = [("Stage", "left"), ("What it takes", "left"), ("Cost", "center"), ("Time", "center"), ("Key Risk", "left")]
    trs = []
    for s in items:
        cells = [
            ck_data_cell(_html.escape(s.stage), mono=True, weight=700),
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(s.description)}</td>',
            f'<td style="text-align:center;padding:5px 10px;font-size:10px;font-family:JetBrains Mono,monospace;color:{text}">{_html.escape(s.typical_cost)}</td>',
            f'<td style="text-align:center;padding:5px 10px;font-size:10px;font-family:JetBrains Mono,monospace;color:{P["accent"]}">{_html.escape(s.typical_time)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{P["negative"]}">{_html.escape(s.key_risk)}</td>',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return _table(cols, "".join(trs))


def _ai_build_vs_buy_table(items) -> str:
    text_dim = P["text_dim"]; text = P["text"]
    cols = [("Dimension", "left"), ("Build", "left"), ("Buy / License", "left"), ("Verdict", "center")]
    trs = []
    for b in items:
        cells = [
            ck_data_cell(_html.escape(b.dimension), mono=True, weight=700),
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(b.build)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(b.buy)}</td>',
            f'<td style="text-align:center;padding:5px 10px;font-size:10px;font-family:JetBrains Mono,monospace;color:{P["accent"]};font-weight:700">{_html.escape(b.verdict)}</td>',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return _table(cols, "".join(trs))


# ─────────────────────────────────────────────────────────────────────────────
# Render
# ─────────────────────────────────────────────────────────────────────────────
def render_radiology_imaging(params: dict = None) -> str:
    from rcm_mc.data_public.radiology_imaging import compute_radiology_imaging
    r = compute_radiology_imaging()

    panel_alt = P["panel_alt"]; border = P["border"]; text = P["text"]
    text_dim = P["text_dim"]; acc = P["accent"]

    kpi_strip = (
        ck_kpi_block("Imaging Market", f"${r.market_size_bn:,.1f}B", "freestanding centers (IBISWorld)", "") +
        ck_kpi_block("Imaging Centers", f"{r.freestanding_centers:,}", "freestanding / IDTF", "") +
        ck_kpi_block("Modalities", f"{len(r.modality_segments)}", "sub-segments broken out", "") +
        ck_kpi_block("Center EBITDA", f"~{r.center_ebitda_margin_pct:.0f}%", f"on ~${r.center_revenue_mm:,.1f}M revenue", "") +
        ck_kpi_block("Supply Shocks", f"{len(r.supply_shocks)}", "tracked disruptions", "") +
        ck_kpi_block("MQSA Facilities", f"{r.mqsa_facilities:,}", "FDA-certified mammography", "") +
        ck_kpi_block("Mammograms / yr", f"{r.annual_mammograms_mm:,.0f}M", f"DBT (3D) at {r.dbt_adoption_pct:.0f}% of facilities", "") +
        ck_kpi_block("CPT/HCPCS Codes", f"{r.cpt_codes_tracked}", "claims atlas", "") +
        ck_kpi_block("CMS Connections", f"{r.cms_connections}", f"{r.ncd_count} NCD · {r.lcd_count} LCD (live)", "") +
        ck_kpi_block("MAC Payers", f"{r.mac_payers}", "Part-B imaging jurisdictions", "") +
        ck_kpi_block("FDA AI Devices", f"{r.fda_ai_radiology_devices:,}", "radiology AI/ML clearances", "") +
        ck_kpi_block("2025 PFS CF", f"${r.pfs_conversion_factor_2025:.2f}", "conversion factor", "")
    )

    value_anchor = ck_value_anchor(
        "REFERRING RADIOLOGY & DIAGNOSTIC IMAGING",
        f"${r.market_size_bn:,.1f}B market",
        delta=f"{r.freestanding_centers:,} freestanding centers · ~4.6% volume CAGR (2018-24)",
        opportunity=f"~5,800 centers still independent — the roll-up runway",
        target=f"{r.cms_connections} live CMS coverage connections wired ({r.ncd_count} national NCDs + {r.lcd_count} local LCDs)",
        tone="teal",
    )

    loop_note = (
        f'<div style="background:{panel_alt};border:1px solid {border};border-left:3px solid {acc};'
        f'padding:12px 16px;font-size:11px;color:{text_dim};margin-bottom:14px">'
        f'<strong style="color:{text}">The CMS connection loop:</strong> '
        f'<code>build_cms_connections()</code> iterates an imaging coverage-topic registry and '
        f'materialises one connection per live Medicare policy — {r.ncd_count} national NCDs (Computed '
        f'Tomography 220.1, MRI 220.2, LDCT lung screening 210.14, PET-FDG 220.6.17, …) that bind every '
        f'MAC, plus {r.lcd_count} local LCDs (the CGS breast-imaging L33950, the CCTA / cardiac-CT family) '
        f'that bind only their issuing contractor. Document IDs, display IDs and effective dates are the '
        f'real values from the CMS Coverage API (api.coverage.cms.gov) — every ID links to the source policy. '
        f'This is why the same scan can be covered differently county-to-county.</div>'
    )

    def _note(lead: str, rest: str) -> str:
        return (
            f'<div style="background:{panel_alt};border:1px solid {border};border-left:3px solid {acc};'
            f'padding:12px 16px;font-size:11px;color:{text_dim};margin-bottom:14px">'
            f'<strong style="color:{text}">{lead}</strong> {rest}</div>'
        )

    _unit_econ_note = _note(
        "Reading the P&L:",
        "a representative scaled freestanding multi-modality center nets ~$190 per blended study at "
        f"~{r.center_revenue_mm:,.1f}M revenue and ~{r.center_ebitda_margin_pct:.0f}% EBITDA. Equipment + occupancy "
        "are mostly fixed, so utilization is the dominant lever — each incremental scan drops ~70-80% to "
        "contribution. A technical-only (TC) center sends reads out and forgoes the -26 professional line. "
        "Illustrative, not a specific company's actuals.",
    )
    _shock_note = _note(
        "Why supply shocks matter here:",
        "imaging is a capital- and consumable-intensive business sitting on concentrated supply chains — a "
        "single contrast plant, a handful of helium sources, a few isotope reactors, two-country scanner "
        "manufacturing. Each shock maps to a specific modality's P&L; severity is recurrence-weighted.",
    )
    _rp_note = _note(
        "Radiology Partners (RP):",
        "the largest US radiology practice and the reference LBO in the sector — a scale-and-leverage case "
        "study. The thesis is national density + data + AI (Aidoc) + teleradiology (vRad); the central risk "
        "is the balance sheet (the 2025 restructuring S&P treated as distressed). Figures are sourced "
        "estimates from public reporting; verify against primary filings before relying on them.",
    )
    _ai_build_note = _note(
        "How to build an imaging AI model:",
        "the realistic pipeline from a labeled study corpus through FDA clearance to deployment. The hard "
        "part is not the model — it is data rights, multi-site validation against distribution shift, and "
        "the reimbursement gap (most cleared imaging AI has no dedicated payment, so ROI is throughput and "
        "quality, not a billable code). See Build-vs-Buy below for the platform decision.",
    )

    footer = (
        f'<div style="background:{panel_alt};border:1px solid {border};border-left:3px solid {acc};'
        f'padding:12px 16px;font-size:11px;color:{text_dim};margin-bottom:16px">'
        f'<strong style="color:{text}">Referring Radiology & Imaging atlas:</strong> '
        f'CY2025 PFS allowables are approximate national averages (paid amounts are GPCI-localized per locality); '
        f'global ≈ professional (mod 26) + technical (mod TC). Mammography screening (77067) is a preventive '
        f'benefit with no patient cost-share; the 3D add-on (77063) is the 2D→3D upgrade economics. '
        f'NCD / LCD IDs and the seven-MAC roster are live from the CMS Coverage API; imaging-center counts, '
        f'county payer-mix shares and operator center counts are sourced estimates labelled as such. '
        f'County payer mix is an insurance-coverage split (ACS / CMS-enrollment proxy), not a contracted-revenue mix. '
        f'Cross-references: /cms-data-browser (PFS/OPPS rate data), /payer-concentration (denials & NSA), '
        f'/payer-intelligence (payer mix), /ai-operating-model (AI portfolio).</div>'
    )

    body = f"""
<div class="ck-page-wrap">
  <div class="ck-kpi-grid" style="margin-bottom:20px">{kpi_strip}</div>
  {value_anchor}
  {_section("CMS Claims Atlas — Radiology CPT/HCPCS (approx CY2025 PFS · global = prof + tech)", _modality_chart(r.cpt_codes) + _cpt_table(r.cpt_codes))}
  {_section("Radiology Broken Into Sub-Segments — the modality economics", _modality_segment_chart(r.modality_segments) + _modality_segment_table(r.modality_segments))}
  {_section("Mammography & Breast Imaging — 2D, 3D/DBT, MQSA & density rule", _mammography_table(r.mammography_stats))}
  {_section("CMS Coverage Connections — live NCDs & LCDs (the loop)", loop_note + _coverage_table(r.coverage_connections))}
  {_section("MAC Payer Jurisdictions — who prices Part-B imaging, by state", _mac_table(r.mac_jurisdictions))}
  {_section("State-Level Data — imaging centers, MQSA facilities, Medicare spend, DBT penetration", _state_chart(r.state_profiles) + _state_table(r.state_profiles))}
  {_section("County-Level Payer Mix — the biggest imaging counties in the main states", _county_table(r.county_payer_mix))}
  {_section("Imaging-Center Unit Economics — a representative multi-modality P&L", _unit_econ_note + _unit_econ_table(r.unit_economics))}
  {_section("Economic Drivers — the levers that move an imaging P&L", _econ_driver_table(r.economic_drivers))}
  {_section("Supply Shocks — the disruptions that hit imaging economics", _shock_note + _supply_shock_table(r.supply_shocks))}
  {_section("Big Players — the large freestanding operators (+ Radiology Partners reads)", _players_chart(r.big_players) + _players_table(r.big_players))}
  {_section("Radiology Partners — Diligence Deep-Dive (largest US practice)", _rp_note + _rp_diligence_table(r.rp_diligence))}
  {_section("AI Implementation — FDA-cleared algorithms, vendors & reimbursement", _ai_table(r.ai_implementations))}
  {_section("AI Imaging — How To Build a Model (the pipeline)", _ai_build_note + _ai_build_table(r.ai_build_stages))}
  {_section("AI Imaging — Build vs Buy", _ai_build_vs_buy_table(r.ai_build_vs_buy))}
  {_section("Imaging Payer-Type Revenue Share", _payer_share_chart(r.payer_shares))}
  {_section("Recent Important Factors (2024-2026)", _factors_table(r.recent_factors))}
  {footer}
</div>"""

    body = body + ck_page_actions()
    meta_line = (
        f"{r.cpt_codes_tracked} CPT/HCPCS codes · {len(r.modality_segments)} modality segments · "
        f"{r.cms_connections} CMS connections ({r.ncd_count} NCD · {r.lcd_count} LCD) · "
        f"{r.mac_payers} MAC payers · {len(r.state_profiles)} states · {len(r.county_payer_mix)} counties · "
        f"{len(r.supply_shocks)} supply shocks · {len(r.economic_drivers)} economic drivers · "
        f"{len(r.big_players)} operators · RP diligence · {len(r.ai_build_stages)}-stage AI build"
    )
    return chartis_shell(
        body, "Referring Radiology & Diagnostic Imaging",
        active_nav="/radiology-imaging",
        subtitle=meta_line,
        editorial_intro={
            "eyebrow": "RADIOLOGY & IMAGING ATLAS",
            "headline": (
                "The claims, coverage, payers, players and AI of US diagnostic imaging — in one surface."
            ),
            "italic_word": "imaging",
            "body": (
                "Radiology CPT/HCPCS economics (incl. 2D & 3D mammography), the live CMS "
                "coverage loop (NCDs + LCDs), the seven MAC payers and their state jurisdictions, "
                "state- and county-level imaging data with payer mix, the big freestanding "
                "operators, and the AI-implementation landscape. Source: "
                "data_public/radiology_imaging.py + CMS Coverage API + FDA MQSA + public filings."
            ),
        },
    )
