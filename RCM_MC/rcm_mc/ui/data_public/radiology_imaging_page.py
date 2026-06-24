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


# ── Outsourced service model — competitive landscape (Dimension 3) ────────────
def _score_dots(n: int) -> str:
    """Render a 1-5 score as filled/empty dots for fast visual scanning."""
    n = max(0, min(5, int(n)))
    acc = P["accent"]; faint = P["text_faint"]
    filled = "".join(f'<span style="color:{acc}">●</span>' for _ in range(n))
    empty = "".join(f'<span style="color:{faint}">○</span>' for _ in range(5 - n))
    return (f'<span style="font-family:JetBrains Mono,monospace;font-size:11px;letter-spacing:1px" '
            f'title="{n}/5">{filled}{empty}</span>')


def _service_model_table(items) -> str:
    text_dim = P["text_dim"]
    cols = [("Delivery Model", "left"), ("On-Site", "center"), ("Scale", "center"),
            ("Subspec.", "center"), ("Tech/AI", "center"), ("Reliability", "center"),
            ("MD Align.", "center"), ("Cost", "center"), ("Pricing Basis", "left")]
    trs = []
    for m in items:
        cells = [
            ck_data_cell(_html.escape(m.model), mono=True, weight=700),
            f'<td style="text-align:center;padding:5px 8px">{_score_dots(m.on_site_presence)}</td>',
            f'<td style="text-align:center;padding:5px 8px">{_score_dots(m.scale)}</td>',
            f'<td style="text-align:center;padding:5px 8px">{_score_dots(m.subspecialty_depth)}</td>',
            f'<td style="text-align:center;padding:5px 8px">{_score_dots(m.tech_ai)}</td>',
            f'<td style="text-align:center;padding:5px 8px">{_score_dots(m.coverage_reliability)}</td>',
            f'<td style="text-align:center;padding:5px 8px">{_score_dots(m.physician_alignment)}</td>',
            f'<td style="text-align:center;padding:5px 8px;font-family:JetBrains Mono,monospace;font-size:10px;color:{P["positive"]};font-weight:700">{_html.escape(m.cost_position)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(m.pricing_basis)}</td>',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    body = _table(cols, "".join(trs))
    # Strength/weakness read below the score matrix.
    sw = []
    for m in items:
        sw.append(
            f'<div style="margin-bottom:8px;font-size:10px;color:{text_dim}">'
            f'<strong style="color:{P["text"]}">{_html.escape(m.model)}</strong> — '
            f'<span style="color:{P["positive"]}">+ {_html.escape(m.strengths)}</span> '
            f'<span style="color:{P["negative"]}">− {_html.escape(m.weaknesses)}</span></div>'
        )
    legend = ('<div style="font-size:10px;color:var(--sc-text-faint);margin:6px 0 10px;'
              'font-family:JetBrains Mono,monospace">● = strength on axis (1-5) · '
              '$ = cheapest per-read · the local group is the share-donor; platforms take share on cost</div>')
    return body + legend + "".join(sw)


def _sla_table(items) -> str:
    text_dim = P["text_dim"]
    cols = [("SLA Tier", "left"), ("Turnaround Target", "center"), ("Scope", "left"), ("Pricing Note", "left")]
    trs = []
    for s in items:
        cells = [
            ck_data_cell(_html.escape(s.tier), mono=True, weight=700),
            ck_data_cell(_html.escape(s.turnaround_target), align="center", mono=True, tone="acc", weight=700),
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(s.scope)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(s.pricing_note)}</td>',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return _table(cols, "".join(trs))


def _staffing_table(items) -> str:
    text_dim = P["text_dim"]; text = P["text"]
    cols = [("Reading-Labor Model", "left"), ("Cost Structure", "left"), ("When Used", "left"), ("Economics", "left")]
    trs = []
    for s in items:
        fixed = "fixed" in s.cost_structure.lower()
        c_color = P["negative"] if fixed else P["positive"]
        cells = [
            ck_data_cell(_html.escape(s.model), mono=True, weight=700),
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;font-family:JetBrains Mono,monospace;color:{c_color};font-weight:700">{_html.escape(s.cost_structure)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(s.when_used)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text}">{_html.escape(s.economics)}</td>',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return _table(cols, "".join(trs))


def _switching_table(items) -> str:
    text_dim = P["text_dim"]
    u_color = {"high": P["negative"], "medium": P["warning"], "low": P["positive"]}
    cols = [("Switching Trigger", "left"), ("Mechanism", "left"), ("Early Signal", "left"), ("Urgency", "center")]
    trs = []
    for s in items:
        uc = u_color.get(s.urgency, text_dim)
        cells = [
            ck_data_cell(_html.escape(s.trigger), mono=True, weight=700),
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(s.mechanism)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(s.early_signal)}</td>',
            f'<td style="text-align:center;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:9px;color:{uc};font-weight:700">{_html.escape(s.urgency.upper())}</td>',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return _table(cols, "".join(trs))


def _decision_table(items) -> str:
    text_dim = P["text_dim"]; text = P["text"]
    w_color = {"primary": P["negative"], "secondary": P["warning"], "tertiary": P["accent"], "minimal": P["text_faint"]}
    cols = [("#", "center"), ("Purchasing Criterion", "left"), ("Weight", "center"), ("Rationale", "left")]
    trs = []
    for d in sorted(items, key=lambda x: x.rank):
        wc = w_color.get(d.weight, text_dim)
        cells = [
            ck_data_cell(str(d.rank), align="center", mono=True, weight=700, tone="acc"),
            ck_data_cell(_html.escape(d.criterion), mono=True, weight=600),
            f'<td style="text-align:center;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:9px;color:{wc};font-weight:700">{_html.escape(d.weight.upper())}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text}">{_html.escape(d.rationale)}</td>',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return _table(cols, "".join(trs))


def _outsourced_econ_table(items) -> str:
    text_dim = P["text_dim"]; text = P["text"]
    d_color = {"revenue": P["positive"], "cost": P["negative"], "margin": P["accent"]}
    cols = [("Line Item", "left"), ("Type", "center"), ("Note", "left")]
    trs = []
    for e in items:
        dc = d_color.get(e.direction, text_dim)
        weight = 700 if e.direction == "margin" else 600
        cells = [
            ck_data_cell(_html.escape(e.line_item), mono=True, weight=weight),
            f'<td style="text-align:center;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:9px;color:{dc};font-weight:700">{_html.escape(e.direction.upper())}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text}">{_html.escape(e.note)}</td>',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return _table(cols, "".join(trs))


def _ai_vendor_role_table(items) -> str:
    text_dim = P["text_dim"]; text = P["text"]
    l_color = {"high": P["positive"], "medium": P["warning"], "low": P["text_faint"]}
    cols = [("AI Vendor Role", "left"), ("Scenario", "left"), ("Likelihood", "center"), ("Implication", "left")]
    trs = []
    for a in items:
        lc = l_color.get(a.likelihood, text_dim)
        cells = [
            ck_data_cell(_html.escape(a.role), mono=True, weight=700),
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(a.scenario)}</td>',
            f'<td style="text-align:center;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:9px;color:{lc};font-weight:700">{_html.escape(a.likelihood.upper())}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text}">{_html.escape(a.implication)}</td>',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return _table(cols, "".join(trs))


# ── Texas deep-dive (reuses the infusion county base) ────────────────────────
def _tx_banner(r) -> str:
    navy = P["navy"]; on = P["on_navy"]; on_dim = P["on_navy_dim"]
    return (
        f'<div style="background:{navy};color:{on};border:1px solid {navy};'
        f'padding:14px 18px;margin:22px 0 14px;border-left:4px solid var(--sc-teal,#155752)">'
        f'<div style="font-family:JetBrains Mono,monospace;font-size:10px;letter-spacing:0.14em;'
        f'text-transform:uppercase;color:{on_dim};margin-bottom:4px">Geographic Deep-Dive</div>'
        f'<div style="font-family:Source Serif 4,Georgia,serif;font-size:19px;font-weight:600">'
        f'Texas + the {r.operating_state_count}-state operating footprint</div>'
        f'<div style="font-size:11px;color:{on_dim};margin-top:5px">'
        f'TX home market: {r.counties_modeled} counties · {r.tx_population:,} people · '
        f'{r.tx_uninsured_rate*100:.0f}% uninsured · MAC Novitas (JH) — '
        f'footprint spans {r.operating_state_count} states / all {r.mac_count} MACs · '
        f'<span style="font-family:JetBrains Mono,monospace">data: {_html.escape(r.data_mode)}</span></div>'
        f'</div>'
    )


def _tx_market_table(items) -> str:
    text_dim = P["text_dim"]
    cols = [("Metric", "left"), ("Value", "right"), ("Detail", "left"), ("Source", "left")]
    trs = []
    for m in items:
        trs.append('<tr>' + "".join([
            ck_data_cell(_html.escape(m.metric), mono=True, weight=600),
            ck_data_cell(_html.escape(m.value), align="right", mono=True, tone="acc", weight=700),
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(m.detail)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:9px;font-family:JetBrains Mono,monospace;color:{P["text_faint"]}">{_html.escape(m.source)}</td>',
        ]) + '</tr>')
    return _table(cols, "".join(trs))


def _tx_cms_table(items) -> str:
    text_dim = P["text_dim"]; acc = P["accent"]
    cols = [("Connection", "left"), ("Kind", "center"), ("Identifier", "left"), ("Detail", "left")]
    trs = []
    for c in items:
        ident = (f'<a href="{_html.escape(c.url)}" target="_blank" rel="noopener" '
                 f'style="color:{acc};text-decoration:none;font-weight:700">{_html.escape(c.identifier)}</a>')
        trs.append('<tr>' + "".join([
            ck_data_cell(_html.escape(c.label), mono=True, weight=600),
            f'<td style="text-align:center;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:9px;color:{text_dim};font-weight:700">{_html.escape(c.kind)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px">{ident}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(c.detail)}</td>',
        ]) + '</tr>')
    return _table(cols, "".join(trs))


def _tx_gpci_table(items) -> str:
    text_dim = P["text_dim"]
    cols = [("PFS Locality", "left"), ("Work GPCI", "right"), ("PE GPCI", "right"),
            ("MP GPCI", "right"), ("Read Economics", "left")]
    trs = []
    for g in items:
        rural = "Rest of Texas" in g.locality
        pe_color = P["negative"] if rural else (P["positive"] if g.pe_gpci >= 0.99 else P["text"])
        trs.append('<tr>' + "".join([
            ck_data_cell(_html.escape(g.locality), mono=True, weight=700 if rural else 600),
            ck_data_cell(f"{g.work_gpci:.3f}", align="right", mono=True, tone="dim"),
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pe_color};font-weight:700">{g.pe_gpci:.3f}</td>',
            ck_data_cell(f"{g.mp_gpci:.3f}", align="right", mono=True, tone="dim"),
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(g.read_economics)}</td>',
        ]) + '</tr>')
    legend = ('<div style="font-size:10px;color:var(--sc-text-faint);margin-top:6px;'
              'font-family:JetBrains Mono,monospace">PE GPCI is the swing — metros price above 1.0, '
              '\'Rest of Texas\' below, so the identical read pays less in the rural counties (approx CY2025).</div>')
    return _tx_market_wrap(_table(cols, "".join(trs)) + legend)


def _tx_market_wrap(inner: str) -> str:
    return inner


def _tx_metro_county_table(items) -> str:
    text_dim = P["text_dim"]
    cols = [("County", "left"), ("Population", "right"), ("65+", "right"),
            ("Imaging Demand Share", "right"), ("Tier", "center")]
    trs = []
    for c in items:
        trs.append('<tr>' + "".join([
            ck_data_cell(_html.escape(c.county), mono=True, weight=700),
            ck_data_cell(f"{c.population:,}", align="right", mono=True),
            ck_data_cell(f"{c.pct_65_plus*100:.0f}%", align="right", mono=True, tone="dim"),
            ck_data_cell(f"{c.imaging_demand_share:.2f}%", align="right", mono=True, tone="acc", weight=700, bar=c.imaging_demand_share / max(d.imaging_demand_share for d in items) * 100.0),
            f'<td style="text-align:center;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:9px;color:{text_dim}">{_html.escape(c.tier.upper())}</td>',
        ]) + '</tr>')
    return _table(cols, "".join(trs))


def _tx_rural_gap_table(items) -> str:
    cols = [("County", "left"), ("Population", "right"), ("Rural", "right"), ("65+", "right"),
            ("Uninsured", "right"), ("Coverage-Gap Score", "right")]
    trs = []
    for c in items:
        trs.append('<tr>' + "".join([
            ck_data_cell(_html.escape(c.county), mono=True, weight=700),
            ck_data_cell(f"{c.population:,}", align="right", mono=True),
            ck_data_cell(f"{c.pct_rural*100:.0f}%", align="right", mono=True, tone="dim"),
            ck_data_cell(f"{c.pct_65_plus*100:.0f}%", align="right", mono=True, tone="dim"),
            ck_data_cell(f"{c.uninsured_rate*100:.0f}%", align="right", mono=True, tone="neg"),
            ck_data_cell(f"{c.coverage_gap_score:.0f}", align="right", mono=True, tone="warning", weight=700, bar=c.coverage_gap_score),
        ]) + '</tr>')
    return _table(cols, "".join(trs))


def _tx_profile_table(items) -> str:
    text_dim = P["text_dim"]; text = P["text"]
    cols = [("Attribute", "left"), ("Profile (public)", "left"), ("Dimension-3 read", "left")]
    trs = []
    for p in items:
        trs.append('<tr>' + "".join([
            ck_data_cell(_html.escape(p.attribute), mono=True, weight=700),
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text}">{_html.escape(p.value)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(p.dimension3_read)}</td>',
        ]) + '</tr>')
    return _table(cols, "".join(trs))


def _tx_payer_chart(items) -> str:
    tone = {"Commercial / employer": "positive", "Medicare (FFS + MA)": "navy",
            "Medicaid (TX)": "warning", "Self-pay / uninsured": "negative"}
    rows = [ck_bar_row(p.payer, f"{p.share_pct:.0f}%", p.share_pct, tone=tone.get(p.payer, "teal")) for p in items]
    return ('<div style="margin-bottom:14px">' + "".join(rows) +
            '<div style="font-size:10px;color:var(--sc-text-faint);margin-top:6px;'
            'font-family:JetBrains Mono,monospace">Texas payer mix (reused from the infusion model) · '
            'TX non-expansion + ~20% uninsured makes the rural-read payer drag real</div></div>')


# ── Operating footprint (the public coverage map) ────────────────────────────
def _tx_operating_table(items) -> str:
    text_dim = P["text_dim"]
    region_color = {"Texas": P["accent"], "Southern Plains": P["warning"],
                    "Upper Midwest": P["positive"], "Southeast": P["negative"], "Florida": P["navy"]}
    cols = [("State", "left"), ("Region", "center"), ("MAC", "left"),
            ("Medicaid", "center"), ("Payer Skew", "left"), ("Competitive / Tele Dynamic", "left")]
    trs = []
    for s in items:
        rc = region_color.get(s.region, text_dim)
        exp = s.medicaid_expansion
        e_color = P["positive"] if "expanded" in exp else P["warning"]
        trs.append('<tr>' + "".join([
            ck_data_cell(f"{_html.escape(s.state)} ({_html.escape(s.postal)})", mono=True, weight=700),
            f'<td style="text-align:center;padding:5px 8px;font-family:JetBrains Mono,monospace;font-size:9px;color:{rc};font-weight:700">{_html.escape(s.region.upper())}</td>',
            ck_data_cell(_html.escape(s.mac), mono=True, tone="acc"),
            f'<td style="text-align:center;padding:5px 8px;font-family:JetBrains Mono,monospace;font-size:9px;color:{e_color};font-weight:700">{_html.escape(exp.split(" ")[0].upper())}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(s.payer_skew)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(s.competitive_note)}</td>',
        ]) + '</tr>')
    return _table(cols, "".join(trs))


def _tx_region_payer_table(items) -> str:
    text_dim = P["text_dim"]
    cols = [("Operating Region", "left"), ("States", "left"), ("Mix (Comm·MCR·MCD·Unins)", "left"),
            ("Comm", "right"), ("MCR", "right"), ("MCD", "right"), ("Unins", "right"), ("Dynamics", "left")]
    trs = []
    for m in items:
        stack = _payer_stack(m.medicare_pct, m.medicaid_pct, m.commercial_pct, m.uninsured_pct)
        trs.append('<tr>' + "".join([
            ck_data_cell(_html.escape(m.region), mono=True, weight=700),
            f'<td style="text-align:left;padding:5px 10px;font-size:9px;font-family:JetBrains Mono,monospace;color:{text_dim}">{_html.escape(m.states)}</td>',
            f'<td style="padding:5px 10px">{stack}</td>',
            ck_data_cell(f"{m.commercial_pct:.0f}%", align="right", mono=True, tone="pos", weight=600),
            ck_data_cell(f"{m.medicare_pct:.0f}%", align="right", mono=True),
            ck_data_cell(f"{m.medicaid_pct:.0f}%", align="right", mono=True, tone="dim"),
            ck_data_cell(f"{m.uninsured_pct:.0f}%", align="right", mono=True, tone="neg"),
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(m.dynamics)}</td>',
        ]) + '</tr>')
    legend = ('<div style="font-size:10px;color:var(--sc-text-faint);margin-top:6px;'
              'font-family:JetBrains Mono,monospace">Upper-Midwest is the richest payer mix (low uninsured, '
              'commercial-strong); the Southeast + Texas carry the Medicaid-gap + uninsured drag (mostly non-expansion).</div>')
    return _table(cols, "".join(trs)) + legend


def _tx_service_lines_table(items) -> str:
    text_dim = P["text_dim"]; text = P["text"]
    cols = [("Service Line", "left"), ("What it is", "left"), ("Competitive Edge", "left")]
    trs = []
    for s in items:
        trs.append('<tr>' + "".join([
            ck_data_cell(_html.escape(s.line), mono=True, weight=700),
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(s.description)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text}">{_html.escape(s.competitive_edge)}</td>',
        ]) + '</tr>')
    return _table(cols, "".join(trs))


def _tx_tele_trends_table(items) -> str:
    text_dim = P["text_dim"]; text = P["text"]
    cols = [("Teleradiology Trend", "left"), ("Detail", "left"), ("Hybrid Implication", "left")]
    trs = []
    for t in items:
        gap = "nighthawk" in t.trend.lower() or "priors" in t.trend.lower()
        name_cell = ck_data_cell(_html.escape(t.trend), mono=True, weight=700)
        if gap:  # spotlight the structural weakness the hybrid beats
            name_cell = (f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;'
                         f'font-size:11px;font-weight:700;color:{P["negative"]}">★ {_html.escape(t.trend)}</td>')
        trs.append('<tr>' + "".join([
            name_cell,
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(t.detail)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text}">{_html.escape(t.hybrid_implication)}</td>',
        ]) + '</tr>')
    return _table(cols, "".join(trs))


def _tx_ai_workflow_table(items) -> str:
    text_dim = P["text_dim"]; text = P["text"]
    cols = [("Theme", "left"), ("The reality", "left"), ("Evidence / read", "left")]
    trs = []
    for a in items:
        trs.append('<tr>' + "".join([
            ck_data_cell(_html.escape(a.theme), mono=True, weight=700),
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text}">{_html.escape(a.reality)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(a.evidence)}</td>',
        ]) + '</tr>')
    return _table(cols, "".join(trs))


# ── Competitor double-click · rural targeting · NPPES evidence · provenance ───
def _tx_competitor_table(items) -> str:
    text_dim = P["text_dim"]; text = P["text"]
    cols = [("Player", "left"), ("Scale", "left"), ("Model", "left"), ("On-Site", "center"),
            ("IR", "center"), ("Subspec", "center"), ("Tech/AI", "center"), ("Capital / NSA / Posture", "left"),
            ("Rural-Fit", "center"), ("Edge", "left")]
    trs = []
    for c in items:
        rural = "Coaxion" in c.player
        name = (f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;'
                f'font-size:11px;font-weight:700;color:{P["accent"] if rural else text}">'
                f'{"★ " if rural else ""}{_html.escape(c.player)}</td>')
        trs.append('<tr>' + "".join([
            name,
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;font-family:JetBrains Mono,monospace;color:{text_dim}">{_html.escape(c.scale)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(c.model)}</td>',
            f'<td style="text-align:center;padding:5px 6px">{_score_dots(c.on_site)}</td>',
            f'<td style="text-align:center;padding:5px 6px">{_score_dots(c.ir)}</td>',
            f'<td style="text-align:center;padding:5px 6px">{_score_dots(c.subspecialty)}</td>',
            f'<td style="text-align:center;padding:5px 6px">{_score_dots(c.tech_ai)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(c.capital_posture)}</td>',
            f'<td style="text-align:center;padding:5px 8px;font-family:JetBrains Mono,monospace;font-size:10px;'
            f'color:{P["positive"] if rural else text_dim};font-weight:700">{_html.escape(c.rural_fit)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text}">{_html.escape(c.edge)}</td>',
        ]) + '</tr>')
    return _table(cols, "".join(trs))


def _tx_rural_targeting_table(items) -> str:
    text_dim = P["text_dim"]; text = P["text"]
    cols = [("Metric", "left"), ("Footprint", "right"), ("Baseline", "left"), ("Takeaway", "left")]
    trs = []
    for m in items:
        trs.append('<tr>' + "".join([
            ck_data_cell(_html.escape(m.metric), mono=True, weight=600),
            ck_data_cell(_html.escape(m.footprint_value), align="right", mono=True, tone="acc", weight=700),
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;font-family:JetBrains Mono,monospace;color:{text_dim}">{_html.escape(m.baseline)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text}">{_html.escape(m.takeaway)}</td>',
        ]) + '</tr>')
    return _table(cols, "".join(trs))


def _tx_npi_evidence_table(items) -> str:
    text_dim = P["text_dim"]; text = P["text"]; acc = P["accent"]
    cols = [("Finding", "left"), ("Evidence (live NPPES)", "left"), ("What it proves", "left"), ("Source", "center")]
    trs = []
    for e in items:
        link = (f'<a href="{_html.escape(e.npi_url)}" target="_blank" rel="noopener" '
                f'style="color:{acc};text-decoration:none;font-weight:700">NPPES ↗</a>')
        trs.append('<tr>' + "".join([
            ck_data_cell(_html.escape(e.finding), mono=True, weight=700),
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;font-family:JetBrains Mono,monospace;color:{text}">{_html.escape(e.evidence)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(e.proves)}</td>',
            f'<td style="text-align:center;padding:5px 10px;font-size:10px">{link}</td>',
        ]) + '</tr>')
    return _table(cols, "".join(trs))


def _tx_provenance_table(items) -> str:
    text_dim = P["text_dim"]; text = P["text"]; acc = P["accent"]; pos = P["positive"]
    cols = [("Market Claim", "left"), ("Dataset", "left"), ("How it proves it", "left"), ("Status", "center"), ("Link", "center")]
    trs = []
    for d in items:
        status = (f'<span style="color:{pos};font-weight:700">● LIVE</span>' if d.live
                  else f'<span style="color:{text_dim}">link</span>')
        link = (f'<a href="{_html.escape(d.link)}" target="_blank" rel="noopener" '
                f'style="color:{acc};text-decoration:none;font-weight:700">source ↗</a>')
        trs.append('<tr>' + "".join([
            ck_data_cell(_html.escape(d.claim), mono=True, weight=600),
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text};font-weight:600">{_html.escape(d.dataset)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(d.how)}</td>',
            f'<td style="text-align:center;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:9px">{status}</td>',
            f'<td style="text-align:center;padding:5px 10px;font-size:10px">{link}</td>',
        ]) + '</tr>')
    return _table(cols, "".join(trs))


# ─────────────────────────────────────────────────────────────────────────────
# Render
# ─────────────────────────────────────────────────────────────────────────────
def render_radiology_imaging(params: dict = None) -> str:
    from rcm_mc.data_public.radiology_imaging import compute_radiology_imaging
    r = compute_radiology_imaging()
    from rcm_mc.data_public.texas_radiology import compute_texas_radiology
    tx = compute_texas_radiology()

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
    _d3_note = _note(
        "Outsourced radiology service model:",
        "the structural shift underneath the reads — hospitals moving interpretation off local groups onto "
        "outsourced platforms. This layer frames the competing delivery models, the turnaround-SLA pricing "
        "(reads are priced on turnaround, not volume), the on-site-fixed vs hawk-per-read labor economics, "
        "the triggers that push a hospital to switch, the purchasing hierarchy (cost first, proximity "
        "irrelevant), and where AI vendors land. Generic industry mechanics — archetype-level, not any one "
        "operator.",
    )
    _tx_note = _note(
        "Texas demand model — reused, not re-derived:",
        f"imaging demand and the rural coverage gap below are computed from the committed {tx.counties_modeled}-county "
        "Texas ACS aggregate already vendored for the infusion geography model, on the SAME senior/population "
        "apportionment (0.60·senior-share + 0.40·population-share) — radiology demand, like infusion, skews to an "
        "aging, dispersed population. The coverage-gap score (rural × aging, discounted in the metros) flags the "
        "sparse counties a sparse-market on-site+tele hybrid actually serves.",
    )
    _tx_profile_note = _note(
        "Texas-HQ outsourced platform (public profile):",
        "a Lubbock, TX-headquartered hybrid 24/7 on-site + teleradiology platform serving hospitals, imaging "
        "centers and clinics across 15+ states with AI-supported diagnostic and interventional reads. Public-source "
        "company facts (coaxionradiology.com / ZoomInfo), framed as Texas market intelligence — the Lubbock hub maps "
        "onto the West-Texas rural coverage gap, and the on-site+tele+IR scope is the single-vendor hybrid archetype.",
    )
    _footprint_note = _note(
        "Where they operate (the public coverage map):",
        f"{tx.operating_state_count} states across five regions — Texas, the Southern Plains (OK·KS·NE·NM), the "
        f"Upper Midwest / Dakotas (MN·SD·ND·WI), the Southeast (AL·GA·TN·NC·KY·MS) and north Florida. That footprint "
        f"spans all {tx.mac_count} Medicare MACs at once, so the platform credentials and complies across seven "
        f"different local-coverage (LCD) regimes — a real operating-complexity and a barrier-to-entry for sub-scale rivals.",
    )
    _ai_workflow_note = _note(
        "Where AI actually helps the read:",
        "market-intelligence read (public industry knowledge — Viz/Aidoc/Rad AI/Harrison.ai/PowerScribe) on the "
        "detection-vs-reporting split. The proven ROI is on the reporting side (auto-impression saves time on every "
        "patient and eases the shortage); detection/triage time-savings have underwhelmed. The binding barrier is "
        "infrastructure — archaic on-prem systems, no cloud platform at scale, no common patient ID to tie priors "
        "together — not model capability. Radiologists stay human-in-the-loop; the role evolves.",
    )
    _competitor_note = _note(
        "Same market, different geometry:",
        "the two incumbents and the rural challenger occupy different points. RP goes where the VOLUME is (metros, "
        "big systems) and carries the leverage + NSA-IDR exposure; vRad is national pure-tele (no on-site, no IR); "
        "the rural challenger is hybrid on-site+tele+IR into the markets both skip. Scored on what a rural CAH "
        "actually needs (rural-fit, /12). Public-company facts (filings, rating agencies, Georgetown CHIR, press).",
    )
    _rural_note = _note(
        "Quantified from real data:",
        "computed over all 3,143 US counties (the same vendored ACS base the page reuses). The footprint is "
        "deliberately rural, concentrates in the rural-radiology white space, and targets the 'triple-bind' "
        "counties — highest imaging demand, worst payer mix, no local radiologist — that pure-tele and metro-scale "
        "both skip.",
    )
    _provenance_note = _note(
        "Nothing here is hand-waved:",
        "every load-bearing market claim is tagged with the public dataset that proves it and a link to pull it. "
        "● LIVE = queried this session (CMS Coverage API + NPPES NPI Registry); the rest link to the authoritative "
        "CMS / Georgetown / Neiman / SEC source to pull.",
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
  {_tx_banner(tx)}
  {_section("Texas — Market & CMS (Novitas MAC · GPCI localities)", _tx_market_table(tx.market_stats) + _tx_cms_table(tx.cms_connections) + _tx_gpci_table(tx.gpci_localities))}
  {_section("Texas — Imaging Demand by County (top metros)", _tx_note + _tx_metro_county_table(tx.metro_counties))}
  {_section("Texas — Rural Coverage Gap (the on-site + tele opportunity)", _tx_rural_gap_table(tx.rural_gap_counties))}
  {_section("Texas — Outsourced Platform Profile + Payer Mix", _tx_profile_note + _tx_profile_table(tx.outsourced_profile) + _tx_payer_chart(tx.payer_shares))}
  {_section("Operating Footprint — states served, by MAC region", _footprint_note + _tx_operating_table(tx.operating_states))}
  {_section("Payer Mix by Operating Region", _tx_region_payer_table(tx.region_payer_mix))}
  {_section("Service Lines — on-site · tele · diagnostic · interventional", _tx_service_lines_table(tx.service_lines))}
  {_section("Teleradiology Trends — incl. the nighthawk priors / context gap", _tx_tele_trends_table(tx.teleradiology_trends))}
  {_section("AI Workflow Reality — where AI actually helps the read", _ai_workflow_note + _tx_ai_workflow_table(tx.ai_workflow))}
  {_section("Competitor Double-Click — RP vs vRad vs the rural challenger", _competitor_note + _tx_competitor_table(tx.competitors))}
  {_section("Rural Targeting — quantified (3,143-county analysis)", _rural_note + _tx_rural_targeting_table(tx.rural_targeting))}
  {_section("Evidence in the Data — live NPPES NPI Registry", _tx_npi_evidence_table(tx.npi_evidence))}
  {_section("Data Provenance — every claim → the public dataset that proves it", _provenance_note + _tx_provenance_table(tx.data_provenance))}
  {_section("Outsourced Service Model — Competing Delivery Models", _d3_note + _service_model_table(r.service_models))}
  {_section("Turnaround SLA Tiers — priced on turnaround, not volume", _sla_table(r.sla_tiers))}
  {_section("Reading-Labor Economics — on-site fixed vs Day/Night-Hawk per-read", _staffing_table(r.staffing_models))}
  {_section("Outsourced-Platform Economics — collections, subsidy, per-read", _outsourced_econ_table(r.outsourced_economics))}
  {_section("Switching Triggers — what moves a hospital off its local group", _switching_table(r.switching_triggers))}
  {_section("Hospital Purchasing Hierarchy — cost first, proximity irrelevant", _decision_table(r.decision_criteria))}
  {_section("AI Vendor Role — competitor, enabler, embedded, or target?", _ai_vendor_role_table(r.ai_vendor_roles))}
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
        f"{r.cms_connections} CMS connections · {r.mac_payers} MAC payers · "
        f"{len(r.service_models)} service models · RP diligence · {len(r.ai_build_stages)}-stage AI build · "
        f"TEXAS deep-dive ({tx.counties_modeled} counties · {tx.operating_state_count}-state footprint · all {tx.mac_count} MACs) · "
        f"3-player tear-sheet · NPPES evidence · {len(tx.data_provenance)}-row data-provenance map"
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
