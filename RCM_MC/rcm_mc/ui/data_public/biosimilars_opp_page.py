"""Biosimilars Opportunity Analyzer — /biosimilars."""
from __future__ import annotations

import html as _html
from rcm_mc.ui._chartis_kit import P, chartis_shell, ck_kpi_block, ck_data_cell, ck_page_title

_EXPLAINER_CSS = """<style>
.ck-bio-explainer{font-family:var(--sc-serif,'Georgia',serif);
  font-size:15px;line-height:1.55;color:var(--sc-text-dim,#4a4a4a);
  margin:0 0 var(--sc-s-6,18px) 0;max-width:72ch;}
.ck-bio-explainer em{color:var(--sc-teal-ink,#155752);font-style:italic;}
</style>"""


def _waves_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; neg = P["negative"]; acc = P["accent"]
    cols = [("Reference Drug","left"),("Class","left"),("LoE Year","right"),("Sales ($B)","right"),
            ("Biosimilars","right"),("Interchangeable","center"),("Price Decline","right"),("Y3 Adoption","right")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    for i, w in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        cells = [
            f'{ck_data_cell(f"""{_html.escape(w.reference_drug)}""", mono=True, weight=600)}',
            f'{ck_data_cell(f"""{_html.escape(w.class_area)}""", mono=True, tone="dim")}',
            f'{ck_data_cell(f"""{w.loe_year}""", align="right", mono=True, tone="acc")}',
            f'{ck_data_cell(f"""${w.reference_annual_sales_b:,.2f}""", align="right", mono=True)}',
            f'{ck_data_cell(f"""{w.biosimilars_launched}""", align="right", mono=True, tone="dim")}',
            f'<td style="text-align:center;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{pos if w.interchangeable_approved else text_dim};font-weight:700">{"YES" if w.interchangeable_approved else "NO"}</td>',
            f'{ck_data_cell(f"""{w.reference_price_decline_pct * 100:+.0f}%""", align="right", mono=True, tone="neg")}',
            f'{ck_data_cell(f"""{w.biosimilar_adoption_y3_pct * 100:.1f}%""", align="right", mono=True, tone="pos", weight=700)}',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _economics_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; acc = P["accent"]
    cols = [("Reference","left"),("Ref WAC/Dose","right"),("Bio WAC/Dose","right"),("ASP+6 Ref","right"),
            ("ASP+6 Bio","right"),("Ref Margin/Dose","right"),("Bio Margin/Dose","right"),("Volume","right"),("Opportunity ($M)","right")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    for i, e in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        cells = [
            f'{ck_data_cell(f"""{_html.escape(e.reference_drug)}""", mono=True, weight=600)}',
            f'{ck_data_cell(f"""${e.reference_wac_per_dose:,.2f}""", align="right", mono=True)}',
            f'{ck_data_cell(f"""${e.biosimilar_wac_per_dose:,.2f}""", align="right", mono=True, tone="pos")}',
            f'{ck_data_cell(f"""${e.asp_plus_6_reference:,.2f}""", align="right", mono=True, tone="dim")}',
            f'{ck_data_cell(f"""${e.asp_plus_6_biosimilar:,.2f}""", align="right", mono=True, tone="dim")}',
            f'{ck_data_cell(f"""${e.provider_margin_reference:,.2f}""", align="right", mono=True)}',
            f'{ck_data_cell(f"""${e.provider_margin_biosimilar:,.2f}""", align="right", mono=True, tone="acc", weight=700)}',
            f'{ck_data_cell(f"""{e.annual_volume_platform:,}""", align="right", mono=True, tone="dim")}',
            f'{ck_data_cell(f"""${e.revenue_opportunity_mm:,.2f}""", align="right", mono=True, tone="pos", weight=700)}',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _sites_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; acc = P["accent"]
    cols = [("Site Type","left"),("Biologic Volume","right"),("Adoption","right"),
            ("Margin/Dose ($)","right"),("Annual Margin ($M)","right"),("Y3 Growth","right")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    for i, s in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        a_c = pos if s.biosimilar_adoption_pct >= 0.60 else (acc if s.biosimilar_adoption_pct >= 0.50 else text_dim)
        cells = [
            f'{ck_data_cell(f"""{_html.escape(s.site_type)}""", mono=True, weight=600)}',
            f'{ck_data_cell(f"""{s.biologic_volume_annual:,}""", align="right", mono=True)}',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{a_c};font-weight:700">{s.biosimilar_adoption_pct * 100:.1f}%</td>',
            f'{ck_data_cell(f"""${s.margin_per_dose:,.2f}""", align="right", mono=True, tone="acc")}',
            f'{ck_data_cell(f"""${s.annual_biosimilar_margin_mm:,.2f}""", align="right", mono=True, tone="pos", weight=700)}',
            f'{ck_data_cell(f"""{s.growth_y3_pct * 100:+.1f}%""", align="right", mono=True, tone="acc")}',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _interchangeable_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]
    cols = [("Biosimilar","left"),("Reference","left"),("Interchangeable Date","left"),
            ("States Auto-Sub","right"),("Notification","left"),("Impact","left")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    for i, it in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        cells = [
            f'{ck_data_cell(f"""{_html.escape(it.biosimilar)}""", mono=True, weight=600)}',
            f'{ck_data_cell(f"""{_html.escape(it.reference)}""", mono=True, tone="dim")}',
            f'{ck_data_cell(f"""{_html.escape(it.interchangeable_date)}""", mono=True, tone="pos")}',
            f'{ck_data_cell(f"""{it.state_pharmacy_sub_allowed}""", align="right", mono=True)}',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(it.notification_requirement)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(it.automatic_sub_impact)}</td>',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _dynamics_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; neg = P["negative"]; warn = P["warning"]; acc = P["accent"]
    cols = [("Class","left"),("Biosimilar Count","right"),("Y1 Erosion","right"),("Y3 Erosion","right"),
            ("Leader Share Y3","right"),("Negotiating Leverage","left")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    for i, d in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        e_c = neg if d.price_erosion_y3_pct >= 0.60 else warn
        cells = [
            f'{ck_data_cell(f"""{_html.escape(d.class_area)}""", mono=True, weight=600)}',
            f'{ck_data_cell(f"""{d.biosimilar_count}""", align="right", mono=True)}',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{warn}">{d.price_erosion_y1_pct * 100:-.0f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{e_c};font-weight:700">{d.price_erosion_y3_pct * 100:-.0f}%</td>',
            f'{ck_data_cell(f"""{d.market_leader_share_y3_pct * 100:.0f}%""", align="right", mono=True, tone="acc")}',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(d.provider_negotiating_leverage)}</td>',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def render_biosimilars(params: dict = None) -> str:
    from rcm_mc.data_public.biosimilars_opp import compute_biosimilars_opp
    r = compute_biosimilars_opp()

    bg = P["bg"]; panel = P["panel"]; panel_alt = P["panel_alt"]
    border = P["border"]; text = P["text"]; text_dim = P["text_dim"]
    pos = P["positive"]; acc = P["accent"]

    kpi_strip = (
        ck_kpi_block("LoE Waves", str(r.total_loe_waves), "", "") +
        ck_kpi_block("Reference Sales", f"${r.total_reference_sales_b:,.1f}B", "", "") +
        ck_kpi_block("Annual Opportunity", f"${r.total_annual_opportunity_mm:,.1f}M", "", "") +
        ck_kpi_block("Annual Margin", f"${r.total_margin_mm:,.1f}M", "", "") +
        ck_kpi_block("Weighted Y3 Adoption", f"{r.weighted_adoption_y3_pct * 100:.1f}%", "", "") +
        ck_kpi_block("Interchangeable Bios", str(sum(1 for w in r.waves if w.interchangeable_approved)), "", "") +
        ck_kpi_block("Active Classes", str(len(r.dynamics)), "", "") +
        ck_kpi_block("Corpus Deals", f"{r.corpus_deal_count:,}", "", "")
    )

    w_tbl = _waves_table(r.waves)
    e_tbl = _economics_table(r.economics)
    s_tbl = _sites_table(r.sites)
    i_tbl = _interchangeable_table(r.interchangeable)
    d_tbl = _dynamics_table(r.dynamics)

    cell = f"background:{panel};border:1px solid {border};padding:16px;margin-bottom:16px"
    h3 = f"font-size:11px;font-weight:600;letter-spacing:0.08em;color:{text_dim};text-transform:uppercase;margin-bottom:10px"

    page_title = ck_page_title(
        "Biosimilars Opportunity Analyzer",
        eyebrow="BIOSIMILARS OPP",
        meta=(
            f"{r.total_loe_waves} LoE waves · "
            f"${r.total_reference_sales_b:,.1f}B reference sales · "
            f"{r.corpus_deal_count:,} corpus deals"
        ),
    )
    bio_explainer = (
        '<p class="ck-bio-explainer">'
        "<em>What the biosimilars opportunity reveals on this deal.</em> "
        "LoE wave schedule, ASP+6% economics, provider margin capture, "
        "interchangeable status, and competitive dynamics across the platform's "
        "infusion and dispensing sites."
        "</p>"
    )
    body = page_title + bio_explainer + f"""
<div class="ck-page-wrap">
  <div style="display:flex;flex-wrap:wrap;gap:8px;margin-bottom:20px">{kpi_strip}</div>
  <div style="{cell}"><div style="{h3}">LoE Wave Schedule &amp; Adoption Curves</div>{w_tbl}</div>
  <div style="{cell}"><div style="{h3}">Per-Drug Economics — Reference vs Biosimilar</div>{e_tbl}</div>
  <div style="{cell}"><div style="{h3}">Site-Level Adoption &amp; Margin Capture</div>{s_tbl}</div>
  <div style="{cell}"><div style="{h3}">FDA Interchangeable Designation Status</div>{i_tbl}</div>
  <div style="{cell}"><div style="{h3}">Class-Level Competitive Dynamics</div>{d_tbl}</div>
  <div style="background:{panel_alt};border:1px solid {border};border-left:3px solid {acc};padding:12px 16px;font-size:11px;color:{text_dim};margin-bottom:16px">
    <strong style="color:{text}">Biosimilars Thesis:</strong> {r.total_loe_waves} LoE waves representing ${r.total_reference_sales_b:,.1f}B in reference-drug sales.
    Weighted Y3 biosimilar adoption reaches {r.weighted_adoption_y3_pct * 100:.1f}% across the platform — driven by interchangeable status, payer formulary steering, and provider-economics alignment.
    Provider economics: biosimilar margin per dose is typically 60-70% below reference in absolute terms (ASP+6% math) but provider still captures meaningful absolute margin — and volume grows as biosimilars expand access.
    Total annual margin opportunity ${r.total_margin_mm:,.1f}M across infusion/dispensing sites. Humira wave (2023 LoE, 10 biosimilars, 2 interchangeable) is the reference playbook;
    Stelara (2025) and Eylea (2025) are the next-wave opportunities. Oncology and rheum/IBD infusion sites capture the largest absolute dollars.
  </div>
</div>"""

    return chartis_shell(body, "Biosimilars", active_nav="/biosimilars",
        extra_css=_EXPLAINER_CSS)
