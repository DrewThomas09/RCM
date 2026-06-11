"""Texas infusion market — a full CDD diligence page.

Renders :func:`rcm_mc.diligence.texas_infusion.build_texas_infusion_analysis`
as the editorial diligence surface a deal team reads when sizing a
Texas infusion platform: TAM/SAM/SOM funnel, therapy-form + site-of-
care segmentation, chain-concentration HHI, payer mix, the Medicare
65+ tailwind, and the Texas structural factors. Every figure carries
its source; the page declares the model illustrative where it scales
public data.
"""
from __future__ import annotations

import html
from typing import Any, Dict, List

from ._chartis_kit import (
    chartis_shell, ck_kpi_block, ck_page_title, ck_section_header,
    ck_source_purpose,
)

_POS = "#0a8a5f"
_NEG = "#b5321e"
_WARN = "#b8732a"
_NAVY = "#0b2341"
_TEAL = "#1F7A75"
_DIM = "#465366"
_FAINT = "#7a8699"


def _money(v: float) -> str:
    if abs(v) >= 1e9:
        return f"${v/1e9:.2f}B"
    if abs(v) >= 1e6:
        return f"${v/1e6:.1f}M"
    return f"${v:,.0f}"


def _bar(pct: float, tone: str, width: int = 100) -> str:
    w = max(1.0, min(100.0, pct))
    return (
        f'<span style="display:inline-block;width:{width}px;height:9px;'
        f'background:#ece5d6;border-radius:2px;overflow:hidden;'
        f'vertical-align:middle;">'
        f'<span style="display:block;height:100%;width:{w:.0f}%;'
        f'background:{tone};"></span></span>')


def _kpi_strip(a: Dict[str, Any]) -> str:
    s = a["sizing"]
    demo = a["demographics"]
    return (
        '<div class="ck-kpi-grid">'
        + ck_kpi_block("TX infusion TAM", _money(s["tam"]),
                       sub="annual market, all sites")
        + ck_kpi_block("Addressable (SAM)", _money(s["sam"]),
                       sub=f'{s["sam_share"]*100:.0f}% of TAM · '
                           'platform-serviceable')
        + ck_kpi_block("Obtainable (SOM)", _money(s["som"]),
                       sub=f'{s["som_share"]*100:.0f}% of SAM · entry share')
        + ck_kpi_block("5-yr market CAGR",
                       f'{s["composite_cagr_pct"]:.1f}%',
                       sub="composite of named drivers")
        + ck_kpi_block("Chain HHI", f'{a["hhi"]:,.0f}',
                       sub=html.escape(a["hhi_band"]))
        + ck_kpi_block("Texans 65+",
                       f'{demo["seniors_65_plus"]/1e6:.2f}M',
                       sub=f'{demo["pct_age_65_plus"]*100:.1f}% of '
                           f'{demo["population"]/1e6:.1f}M — Medicare base')
        + '</div>'
    )


def _sizing_chain(a: Dict[str, Any]) -> str:
    rows = ""
    for st in a["sizing"]["steps"]:
        op = st["op"]
        val = st["value"]
        if op == "rate":
            val_s = f'×{val*100:.1f}%'
        elif op == "price":
            val_s = f'×${val:,.0f}'
        elif op == "mult":
            val_s = f'×{val:,.0f}'
        else:
            val_s = f'{val:,.0f}'
        run = st["running"]
        run_s = _money(run) if op == "price" else f'{run:,.0f}'
        rows += (
            f'<tr>'
            f'<td style="padding:6px 8px;">{html.escape(st["name"])}'
            f'<div style="font-size:10px;color:{_FAINT};">'
            f'{html.escape(st["source"])}</div></td>'
            f'<td class="num" style="padding:6px 8px;text-align:right;'
            f'font-variant-numeric:tabular-nums;color:{_DIM};">{val_s}</td>'
            f'<td class="num" style="padding:6px 8px;text-align:right;'
            f'font-variant-numeric:tabular-nums;font-weight:600;">'
            f'{run_s}'
            f'<span style="font-size:10px;color:{_FAINT};"> '
            f'{html.escape(st["unit"])}</span></td>'
            f'</tr>')
    return (
        '<div style="overflow-x:auto;"><table style="width:100%;'
        'border-collapse:collapse;font-size:12.5px;">'
        '<thead><tr style="border-bottom:2px solid #c9c1ac;">'
        '<th style="text-align:left;padding:6px 8px;">Driver (source)</th>'
        '<th style="text-align:right;padding:6px 8px;">Step</th>'
        '<th style="text-align:right;padding:6px 8px;">Running</th>'
        f'</tr></thead><tbody>{rows}</tbody></table></div>'
        f'<p style="font-size:11px;color:{_FAINT};margin:8px 0 0;">'
        'The chain is the methodology — TX patient base × infusion '
        'frequency × revenue per infusion. Every step is editable in '
        'the TAM/SAM builder.</p>')


def _segment_table(a: Dict[str, Any]) -> str:
    """Therapy-form segmentation with growth divergence (fastest ★)."""
    rows = ""
    for seg in a["sizing"]["segments"]:
        star = (' <span style="color:%s;font-weight:700;">★ fastest</span>'
                % _POS) if seg.get("is_fastest") else ""
        g = seg.get("growth_pct")
        g_s = (f'<span style="color:{_POS if g and g>=6 else _DIM};">'
               f'+{g:.0f}%</span>' if g is not None else "—")
        y5 = seg.get("tam_y_final")
        rows += (
            f'<tr>'
            f'<td style="padding:6px 8px;">{html.escape(seg["name"])}{star}'
            + (f'<div style="font-size:10px;color:{_FAINT};">'
               f'{html.escape(seg["note"])}</div>' if seg.get("note") else "")
            + f'</td>'
            f'<td class="num" style="padding:6px 8px;text-align:right;">'
            f'{seg["share_of_volume"]*100:.0f}%</td>'
            f'<td class="num" style="padding:6px 8px;text-align:right;'
            f'font-weight:600;">{_money(seg["tam_value"])}</td>'
            f'<td class="num" style="padding:6px 8px;text-align:right;">{g_s}</td>'
            f'<td class="num" style="padding:6px 8px;text-align:right;'
            f'color:{_DIM};">{_money(y5) if y5 else "—"}</td>'
            f'</tr>')
    return (
        '<div style="overflow-x:auto;"><table style="width:100%;'
        'border-collapse:collapse;font-size:12.5px;">'
        '<thead><tr style="border-bottom:2px solid #c9c1ac;">'
        '<th style="text-align:left;padding:6px 8px;">Therapy form</th>'
        '<th style="text-align:right;padding:6px 8px;">Share</th>'
        '<th style="text-align:right;padding:6px 8px;">TAM today</th>'
        '<th style="text-align:right;padding:6px 8px;">Growth</th>'
        '<th style="text-align:right;padding:6px 8px;">TAM Y5</th>'
        f'</tr></thead><tbody>{rows}</tbody></table></div>')


def _site_table(a: Dict[str, Any]) -> str:
    """Site-of-care segmentation — the HOPD → home/AIS migration in $."""
    rows = ""
    for s in a["site_of_care"]:
        g = s["growth_pct"]
        tone = _POS if g > 0 else _NEG
        g_s = f'<span style="color:{tone};font-weight:600;">{g:+.0f}%</span>'
        rows += (
            f'<tr>'
            f'<td style="padding:6px 8px;">{html.escape(s["site"])}'
            f'<div style="font-size:10px;color:{_FAINT};">'
            f'{html.escape(s["note"])}</div></td>'
            f'<td class="num" style="padding:6px 8px;text-align:right;">'
            f'{s["share"]*100:.0f}%</td>'
            f'<td class="num" style="padding:6px 8px;text-align:right;">'
            f'{_money(s["tam_today"])}</td>'
            f'<td class="num" style="padding:6px 8px;text-align:right;">{g_s}</td>'
            f'<td class="num" style="padding:6px 8px;text-align:right;'
            f'font-weight:600;color:{tone};">{_money(s["tam_y5"])}</td>'
            f'</tr>')
    return (
        '<div style="overflow-x:auto;"><table style="width:100%;'
        'border-collapse:collapse;font-size:12.5px;">'
        '<thead><tr style="border-bottom:2px solid #c9c1ac;">'
        '<th style="text-align:left;padding:6px 8px;">Site of care</th>'
        '<th style="text-align:right;padding:6px 8px;">Share</th>'
        '<th style="text-align:right;padding:6px 8px;">TAM today</th>'
        '<th style="text-align:right;padding:6px 8px;">Growth</th>'
        '<th style="text-align:right;padding:6px 8px;">TAM Y5</th>'
        f'</tr></thead><tbody>{rows}</tbody></table></div>'
        f'<p style="font-size:11px;color:{_FAINT};margin:8px 0 0;">'
        'The site-of-care shift is the thesis: HOPD volume (2–3× the '
        'suite rate) is being steered to home + ambulatory suites. HOPD '
        'is the only declining site.</p>')


def _metro_table(a: Dict[str, Any]) -> str:
    """Ranked metro breakdown — real CBSA ACS data + derived demand."""
    rows = ""
    for m in a["metros"]:
        att = m["attractiveness"]
        att_tone = _POS if att >= 90 else _TEAL if att >= 80 else _WARN
        rows += (
            f'<tr>'
            f'<td class="num" style="padding:6px 8px;font-weight:700;'
            f'color:{att_tone};">#{m["rank"]}</td>'
            f'<td style="padding:6px 8px;font-weight:600;">'
            f'{html.escape(m["metro"])}</td>'
            f'<td class="num" style="padding:6px 8px;text-align:right;">'
            f'{m["population"]/1e6:.2f}M</td>'
            f'<td class="num" style="padding:6px 8px;text-align:right;">'
            f'{m["seniors"]/1e3:,.0f}K</td>'
            f'<td class="num" style="padding:6px 8px;text-align:right;">'
            f'{m["infusion_patients"]:,}</td>'
            f'<td class="num" style="padding:6px 8px;text-align:right;">'
            f'{m["referral_density_per_100k"]:,.0f}</td>'
            f'<td class="num" style="padding:6px 8px;text-align:right;">'
            f'~{m["est_ais_centers"]}</td>'
            f'<td class="num" style="padding:6px 8px;text-align:right;'
            f'font-weight:700;color:{att_tone};">{att:.0f}</td>'
            f'</tr>')
    return (
        '<div style="overflow-x:auto;"><table style="width:100%;'
        'border-collapse:collapse;font-size:12px;">'
        '<thead><tr style="border-bottom:2px solid #c9c1ac;">'
        '<th style="text-align:left;padding:6px 8px;">Rank</th>'
        '<th style="text-align:left;padding:6px 8px;">Metro</th>'
        '<th style="text-align:right;padding:6px 8px;">Population</th>'
        '<th style="text-align:right;padding:6px 8px;">65+</th>'
        '<th style="text-align:right;padding:6px 8px;">Infusion pts</th>'
        '<th style="text-align:right;padding:6px 8px;">Per 100k</th>'
        '<th style="text-align:right;padding:6px 8px;">AIS (est)</th>'
        '<th style="text-align:right;padding:6px 8px;">Attract.</th>'
        f'</tr></thead><tbody>{rows}</tbody></table></div>'
        f'<p style="font-size:11px;color:{_FAINT};margin:8px 0 0;'
        f'line-height:1.55;">Population, 65+ share and rurality are REAL '
        'CBSA aggregates of member-county ACS data. Infusion patients '
        'apportion the TX base by metro senior + total population; '
        'referral density = patients per 100k residents; AIS counts are '
        'population-scaled estimates. Attractiveness (0–100) blends '
        'senior demand (log-scaled), 65+ growth, and a rural-route '
        'penalty — the four metros hold ~70% of Texans.</p>')


def _provider_panel(a: Dict[str, Any]) -> str:
    pl = a["provider_landscape"]
    hs = a["health_system_capacity"]
    frag = a["fragmentation"]
    return (
        '<div class="ck-kpi-grid" style="margin-bottom:10px;">'
        + ck_kpi_block("Home-infusion locations (est)",
                       f'~{pl["home_infusion_locations"]}',
                       sub="NHIA national × TX share")
        + ck_kpi_block("Ambulatory infusion centers (est)",
                       f'~{pl["ambulatory_infusion_centers"]}',
                       sub=f'growing ~{pl["ais_growth_pct"]:.0f}%/yr')
        + ck_kpi_block("Health-system (HOPD) capacity",
                       f'{hs["hopd_share"]*100:.0f}%',
                       sub="captive — outside the pool")
        + '</div>'
        + f'<p style="font-size:11px;color:{_FAINT};margin:0 0 12px;'
        f'line-height:1.55;">{html.escape(pl["note"])}</p>'
        + f'<div style="padding:10px 14px;background:#f7f3ea;'
        f'border-left:3px solid {_POS};border-radius:0 3px 3px 0;'
        f'font-size:12.5px;color:#1a2332;line-height:1.6;margin-bottom:10px;">'
        f'<strong>Competitive read:</strong> {html.escape(frag["verdict"])}'
        f'</div>'
        + f'<p style="font-size:12px;color:{_DIM};line-height:1.6;">'
        f'<strong>Health-system-owned capacity:</strong> '
        f'{html.escape(hs["note"])}</p>')


def _concentration(a: Dict[str, Any]) -> str:
    """Chain table + HHI read — the fragmentation that drives roll-up."""
    rows = ""
    for c in a["chains"]:
        tone = _NAVY if c["named"] else _FAINT
        rows += (
            f'<tr>'
            f'<td style="padding:5px 8px;color:{tone};'
            f'{"font-weight:600;" if c["named"] else ""}">'
            f'{html.escape(c["org"])}'
            f'<div style="font-size:10px;color:{_FAINT};">'
            f'{html.escape(c["note"])}</div></td>'
            f'<td class="num" style="padding:5px 8px;text-align:right;">'
            f'{c["share"]*100:.0f}%</td>'
            f'<td style="padding:5px 8px;">{_bar(c["share"]*100, tone, 120)}</td>'
            f'</tr>')
    band_tone = (_NEG if a["hhi"] > 2500 else _WARN if a["hhi"] >= 1500
                 else _POS)
    return (
        '<div style="overflow-x:auto;"><table style="width:100%;'
        'border-collapse:collapse;font-size:12.5px;">'
        '<thead><tr style="border-bottom:2px solid #c9c1ac;">'
        '<th style="text-align:left;padding:5px 8px;">Operator</th>'
        '<th style="text-align:right;padding:5px 8px;">Share</th>'
        '<th style="padding:5px 8px;"></th>'
        f'</tr></thead><tbody>{rows}</tbody></table></div>'
        f'<p style="font-size:12px;color:{_DIM};margin:10px 0 0;'
        f'line-height:1.6;">Named-chain <strong>HHI = '
        f'<span style="color:{band_tone};">{a["hhi"]:,.0f}</span></strong> '
        f'({html.escape(a["hhi_band"])}, DOJ/FTC 0–10,000 scale). A reading '
        'this low says the operator layer is <strong>fragmented</strong> — '
        'no single platform dominates and the regional/independent pool is '
        'the roll-up whitespace. This is the buy-and-build setup.</p>'
        f'<p style="font-size:9.5px;color:{_FAINT};margin:6px 0 0;">'
        'Shares are national operator estimates mapped to Texas '
        '(no TX-specific infusion provider census is vendored) — '
        'illustrative for the concentration read; HHI computed over the '
        'named chains only.</p>')


def _payer_section(a: Dict[str, Any]) -> str:
    rows = ""
    for p in a["payer_mix"]:
        rows += (
            f'<tr>'
            f'<td style="padding:6px 8px;font-weight:500;">'
            f'{html.escape(p["payer"])}'
            f'<div style="font-size:10px;color:{_FAINT};">'
            f'{html.escape(p["note"])}</div></td>'
            f'<td class="num" style="padding:6px 8px;text-align:right;">'
            f'{p["share"]*100:.0f}%</td>'
            f'<td style="padding:6px 8px;">{_bar(p["share"]*100, _TEAL, 120)}</td>'
            f'<td class="num" style="padding:6px 8px;text-align:right;'
            f'color:{_DIM};">{_money(p["tam_value"])}</td>'
            f'</tr>')
    return (
        '<div style="overflow-x:auto;"><table style="width:100%;'
        'border-collapse:collapse;font-size:12.5px;">'
        '<thead><tr style="border-bottom:2px solid #c9c1ac;">'
        '<th style="text-align:left;padding:6px 8px;">Payer</th>'
        '<th style="text-align:right;padding:6px 8px;">Share</th>'
        '<th style="padding:6px 8px;"></th>'
        '<th style="text-align:right;padding:6px 8px;">TAM $</th>'
        f'</tr></thead><tbody>{rows}</tbody></table></div>')


def _factors(a: Dict[str, Any]) -> str:
    out = ""
    for f in a["structural_factors"]:
        tone = _POS if f["tone"] == "positive" else _NEG
        sign = "▲" if f["tone"] == "positive" else "▼"
        out += (
            f'<div style="padding:9px 0;border-bottom:1px solid #e4ddca;">'
            f'<div style="font-size:12.5px;font-weight:600;color:#1a2332;">'
            f'<span style="color:{tone};">{sign}</span> '
            f'{html.escape(f["factor"])}</div>'
            f'<div style="font-size:11.5px;color:{_DIM};margin-top:2px;'
            f'line-height:1.55;">{html.escape(f["detail"])}</div></div>')
    return out


def _growth_drivers(a: Dict[str, Any]) -> str:
    out = ""
    for g in a["sizing"]["growth_drivers"]:
        tone = _POS if g["annual_pct"] > 0 else _NEG
        out += (
            f'<div style="padding:7px 0;border-bottom:1px solid #e4ddca;'
            f'display:flex;gap:10px;align-items:baseline;">'
            f'<span style="font-family:monospace;font-weight:700;color:{tone};'
            f'min-width:52px;">{g["annual_pct"]:+.1f}%</span>'
            f'<span><strong style="font-size:12px;">'
            f'{html.escape(g["name"])}</strong>'
            f'<div style="font-size:11px;color:{_DIM};">'
            f'{html.escape(g["note"])}</div></span></div>')
    return out


def render_texas_infusion_page() -> str:
    """Render the full Texas infusion diligence page."""
    from ..diligence.texas_infusion import build_texas_infusion_analysis
    a = build_texas_infusion_analysis()
    demo = a["demographics"]

    sources = "".join(
        f'<li style="margin:3px 0;font-size:11px;color:{_DIM};">'
        f'{html.escape(src)}</li>' for src in a["sources"])

    body = (
        ck_page_title(
            "Texas Infusion Market",
            eyebrow="DILIGENCE · MARKET SIZING",
            meta=f"TAM {_money(a['sizing']['tam'])} · "
                 f"{a['sizing']['composite_cagr_pct']:.1f}% CAGR · "
                 f"HHI {a['hhi']:,.0f} ({a['hhi_band']})",
        )
        + ck_source_purpose(
            purpose="Size and segment the Texas ambulatory + home "
                    "infusion market for a buy-and-build thesis.",
            universe="illustrative",
            source="NHIA + MedPAC demand magnitudes scaled to TX by "
                   "Census 2024 population share; ACS demographics; "
                   "DOJ/FTC HHI. Replace with engagement data before IC.",
        )
        + '<div class="ts-wrap" style="max-width:980px;">'
        + _kpi_strip(a)

        + ck_section_header("Market sizing — the driver chain",
                            eyebrow="TAM / SAM / SOM")
        + _sizing_chain(a)

        + ck_section_header("Segmentation by therapy form",
                            eyebrow="WHERE THE DOLLARS — AND THE GROWTH — ARE")
        + _segment_table(a)

        + ck_section_header("Segmentation by site of care",
                            eyebrow="THE SITE-OF-CARE SHIFT")
        + _site_table(a)

        + ck_section_header("Provider landscape & competitiveness",
                            eyebrow="COUNTS · CAPACITY · FRAGMENTATION")
        + _provider_panel(a)

        + ck_section_header("Metro attractiveness ranking",
                            eyebrow="HOUSTON · DFW · AUSTIN · SAN ANTONIO")
        + _metro_table(a)

        + ck_section_header("Concentration — operator landscape",
                            eyebrow="HHI · FRAGMENTATION → ROLL-UP")
        + _concentration(a)

        + ck_section_header("Payer mix",
                            eyebrow="COMMERCIAL-HEAVY · TX NON-EXPANSION")
        + _payer_section(a)

        + ck_section_header("Medicare population & demographics",
                            eyebrow="THE DEMAND TAILWIND")
        + (
            f'<div style="font-size:12.5px;color:{_DIM};line-height:1.7;">'
            f'<p>Texas has <strong>{demo["seniors_65_plus"]/1e6:.2f}M</strong> '
            f'residents aged 65+ ({demo["pct_age_65_plus"]*100:.1f}% of '
            f'{demo["population"]/1e6:.1f}M across {demo["counties"]} '
            f'counties) — the Medicare-covered base for infused therapies, '
            f'and one of the fastest-growing senior populations in the US '
            f'(Sun-Belt aging + net in-migration). The 65+ cohort drives '
            f'oncology-support, OPAT, and IVIG volume.</p>'
            f'<p style="margin-top:6px;"><strong>Growth trend:</strong> '
            f'{html.escape(a["population_growth"]["note"])}</p>'
            f'<p style="margin-top:6px;">Counterweights: a '
            f'<strong>{demo["uninsured_rate"]*100:.0f}% uninsured rate</strong> '
            f'(the highest in the US, a Medicaid-non-expansion consequence) '
            f'and <strong>{demo["pct_rural"]*100:.0f}% rural</strong> '
            f'population that complicates home-nurse route economics outside '
            f'the four big metros. Median household income '
            f'${demo["median_household_income"]:,.0f}.</p></div>')

        + ck_section_header("Five-year growth drivers",
                            eyebrow="WHICH LEVER CARRIES THE GROWTH")
        + _growth_drivers(a)

        + ck_section_header("Texas structural factors",
                            eyebrow="WHAT'S DIFFERENT ABOUT TEXAS")
        + _factors(a)

        + ck_section_header("Sources & basis", eyebrow="VERIFIABILITY")
        + f'<ul style="margin:0;padding-left:18px;">{sources}</ul>'
        + f'<p style="font-size:11px;color:{_FAINT};margin:10px 0 0;'
        f'line-height:1.6;">{html.escape(a["basis_note"])}</p>'
        + '<p style="font-size:11.5px;margin:10px 0 0;">'
        '<a href="/diligence/tam-sam?template=infusion" '
        f'style="color:{_NAVY};font-weight:600;text-decoration:none;">'
        'Open the editable infusion model in the TAM/SAM Builder →</a></p>'
        + '</div>'
    )

    from ._chartis_kit import ck_page_actions
    body = body + ck_page_actions()
    return chartis_shell(
        body, "Texas Infusion Market",
        active_nav="/diligence",
        subtitle=f"TAM {_money(a['sizing']['tam'])} · HHI {a['hhi']:,.0f}",
    )
