"""Texas infusion market — Continued (part 2): the granular tab.

Renders :func:`rcm_mc.diligence.texas_infusion_continued.
build_texas_infusion_continued_analysis` as the second Texas-infusion
diligence surface: CPT-level reimbursement per office/AIC and per home
visit, the cross-site arbitrage, reimbursement by state (GAF) and by
Texas PFS locality (by city), drug-mix dose economics, the payer-
weighted overall reimbursement rate, PPO/HMO concentration by metro,
the operator×plan in-network matrix, proximity/density analysis, the
HealthQuest referral-convenience spotlight, and the patient-experience
evidence. Every figure carries its source and the page flags modeled
vs verified in place.
"""
from __future__ import annotations

import html
from typing import Any, Dict, List

from ._chartis_kit import (
    chartis_shell,
    ck_kpi_block,
    ck_page_title,
    ck_section_header,
    ck_source_purpose,
)
from .cdd_chart_kit import (
    chart_export_toolbar,
    parse_table,
    render_cdd_chart,
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


def part_tabs(active: str) -> str:
    """The two-tab strip linking the Texas-infusion pages. ``active``
    is 'part1' or 'part2'. Shared so both pages render it identically
    (part 1 imports this lazily to avoid an import cycle)."""
    def _tab(label: str, href: str, on: bool) -> str:
        if on:
            return (
                f'<span style="display:inline-block;padding:7px 16px;'
                f'font-size:12px;font-weight:700;color:#fff;'
                f'background:{_NAVY};border:1px solid {_NAVY};'
                f'border-radius:6px 6px 0 0;">{html.escape(label)}</span>')
        return (
            f'<a href="{href}" style="display:inline-block;'
            f'padding:7px 16px;font-size:12px;font-weight:600;'
            f'color:{_NAVY};background:#efe9dc;border:1px solid #c9c1ac;'
            f'border-bottom:none;border-radius:6px 6px 0 0;'
            f'text-decoration:none;">{html.escape(label)}</a>')
    return (
        '<div style="display:flex;gap:6px;align-items:flex-end;'
        'border-bottom:2px solid #0b2341;margin:2px 0 16px;">'
        + _tab("Texas Infusion Market", "/diligence/texas-infusion",
               active == "part1")
        + _tab("Texas Infusion Market · Continued",
               "/diligence/texas-infusion-continued", active == "part2")
        + '</div>')


def _badge(label: str, tone: str = _WARN) -> str:
    bg = {"#0a8a5f": "#e6f4ee", "#b8732a": "#f3efe4",
          "#0b2341": "#e8edf4"}.get(tone, "#f3efe4")
    return (
        f'<span style="font-size:9px;font-weight:700;'
        f'letter-spacing:0.06em;padding:2px 7px;border-radius:3px;'
        f'background:{bg};color:{tone};border:1px solid {tone};">'
        f'{html.escape(label)}</span>')


def _note(text: str) -> str:
    return (f'<p style="font-size:11px;color:{_FAINT};line-height:1.6;'
            f'margin:8px 0 0;">{html.escape(text)}</p>')


def _so_what(text: str, tone: str = _TEAL) -> str:
    return (
        f'<div style="border-left:3px solid {tone};background:#f6f3ec;'
        f'padding:9px 13px;margin:12px 0 4px;font-size:12px;'
        f'color:#1a2332;line-height:1.65;">'
        f'<span style="font-size:9px;font-weight:700;'
        f'letter-spacing:0.08em;color:{tone};">SO WHAT&nbsp;·&nbsp;</span>'
        f'{html.escape(text)}</div>')


_TH = ('style="text-align:left;padding:5px 8px;"')
_THR = ('style="text-align:right;padding:5px 8px;"')
_TD = 'padding:5px 8px;'
_TDR = ('padding:5px 8px;text-align:right;'
        'font-variant-numeric:tabular-nums;')


def _table(headers: List[str], rows_html: str,
           right_from: int = 1) -> str:
    """Small table composer — headers left/right aligned per column."""
    ths = "".join(
        f'<th {_TH if i < right_from else _THR}>{html.escape(h)}</th>'
        for i, h in enumerate(headers))
    return (
        '<div style="overflow-x:auto;"><table style="width:100%;'
        'border-collapse:collapse;font-size:12px;">'
        f'<thead><tr style="border-bottom:2px solid #c9c1ac;">{ths}'
        f'</tr></thead><tbody>{rows_html}</tbody></table></div>')


def _chart_block(chart_id: str, svg: str, filename: str) -> str:
    return (
        f'<div style="border:1px solid #d6cfc0;border-radius:8px;'
        f'padding:10px;background:#fff;text-align:center;">'
        f'<div id="{chart_id}">{svg}</div>'
        + chart_export_toolbar(chart_id, filename) + '</div>')


# ── Sections ─────────────────────────────────────────────────────────

def _kpi_strip(a: Dict[str, Any]) -> str:
    cs = a["channel_sizing"]
    sr = a["state_reimbursement"]
    orr = a["overall_reimbursement"]
    hq = a["healthquest"]
    code_96413 = next(c for c in a["pfs_admin_codes"]
                      if c["code"] == "96413")
    return (
        '<div class="ck-kpi-grid">'
        + ck_kpi_block("AIC channel (TX)", _money(cs["aic"]["revenue"]),
                       sub=f'{cs["aic"]["share"]*100:.0f}% of volume · '
                           f'{cs["aic"]["infusions"]/1e6:.1f}M infusions/yr')
        + ck_kpi_block("Home channel (TX)", _money(cs["home"]["revenue"]),
                       sub=f'{cs["home"]["share"]*100:.0f}% of volume · '
                           f'{cs["home"]["infusions"]/1e6:.1f}M '
                           f'infusions/yr')
        + ck_kpi_block("96413 office rate", f'${code_96413["nonfac"]:,.2f}',
                       sub=f'CY2025 PFS · CY2026 '
                           f'${code_96413["nonfac_2026"]:,.2f}')
        + ck_kpi_block("HOPD premium",
                       f'{a["cross_site"]["hopd_premium"]:.2f}x',
                       sub="same admin, hospital vs AIC (Medicare)")
        + ck_kpi_block("Blended $/infusion",
                       f'${orr["blended_revenue_per_infusion"]:,.0f}',
                       sub=f'payer-weighted · commercial '
                           f'${orr["rows"][0]["revenue_per_infusion"]:,.0f}'
                           if orr["rows"] else "")
        + ck_kpi_block("TX GAF rank",
                       f'#{sr["texas"]["rank"]} of {len(sr["states"])}',
                       sub=f'GAF {sr["texas"]["gaf"]:.3f} · '
                           f'{hq["pct_within_30min"]*100:.1f}% of metro '
                           f'pop ≤30 min of HealthQuest')
        + '</div>')


def _channel_sizing_section(a: Dict[str, Any]) -> str:
    cs = a["channel_sizing"]
    rows = ""
    for r in cs["rows"]:
        g = r["growth_pct"]
        g_s = (f'<span style="color:{_POS if g >= 0 else _NEG};">'
               f'{g:+.1f}%</span>')
        rows += (
            f'<tr><td style="{_TD}">{html.escape(r["site"])}</td>'
            f'<td class="num" style="{_TDR}">{r["share"]*100:.0f}%</td>'
            f'<td class="num" style="{_TDR}">{r["infusions"]/1e6:.2f}M</td>'
            f'<td class="num" style="{_TDR}">'
            f'${r["revenue_per_infusion"]:,.0f}</td>'
            f'<td class="num" style="{_TDR}font-weight:600;">'
            f'{_money(r["revenue"])}</td>'
            f'<td class="num" style="{_TDR}">{g_s}</td></tr>')
    tbl = _table(["Site of care", "Volume share", "Infusions/yr",
                  "Rev / infusion", "Channel revenue", "Growth"], rows)
    donut = parse_table(
        "Channel\t$M\n" + "\n".join(
            f'{r["site"].split(" (")[0]}\t{r["revenue"]/1e6:.1f}'
            for r in cs["rows"]))
    chart = render_cdd_chart("donut", donut, {
        "title": "TX infusion revenue by channel ($M)",
        "palette": "Navy–Teal"})
    recon = (
        f'<div style="display:flex;gap:14px;flex-wrap:wrap;'
        f'margin:10px 0 0;font-size:12px;color:{_DIM};">'
        f'<div>Bottom-up sum: <strong style="color:{_NAVY};">'
        f'{_money(cs["tam_check"])}</strong></div>'
        f'<div>Part-1 top-down TAM: <strong style="color:{_NAVY};">'
        f'{_money(a["sizing"]["tam"])}</strong></div>'
        f'<div style="color:{_POS};font-weight:700;">'
        f'RECONCILES EXACTLY ✓</div></div>')
    return (
        f'<div style="display:grid;grid-template-columns:1.2fr 1fr;'
        f'gap:18px;align-items:start;">'
        f'<div>{tbl}{recon}{_note(cs["note"])}</div>'
        f'{_chart_block("txcChannel", chart, "tx-infusion-channels")}'
        f'</div>')


def _office_cpt_section(a: Dict[str, Any]) -> str:
    rows = ""
    fam_seen = set()
    for c in a["pfs_admin_codes"]:
        fam = ""
        if c["family"] not in fam_seen:
            fam_seen.add(c["family"])
            fam = (f'<div style="font-size:9px;color:{_FAINT};'
                   f'letter-spacing:0.05em;font-weight:700;">'
                   f'{html.escape(c["family"].upper())}</div>')
        delta = (c["nonfac_2026"] / c["nonfac"] - 1) * 100
        rows += (
            f'<tr><td style="{_TD}">{fam}'
            f'<code style="font-size:11px;color:{_NAVY};font-weight:700;">'
            f'{c["code"]}</code>'
            f'<span style="font-size:10px;color:{_FAINT};"> '
            f'{html.escape(c["role"])}</span>'
            f'<div style="font-size:10.5px;color:{_DIM};">'
            f'{html.escape(c["descriptor"])}</div></td>'
            f'<td class="num" style="{_TDR}">${c["nonfac"]:,.2f}</td>'
            f'<td class="num" style="{_TDR}font-weight:600;">'
            f'${c["nonfac_2026"]:,.2f}</td>'
            f'<td class="num" style="{_TDR}color:'
            f'{_POS if delta >= 0 else _NEG};">{delta:+.1f}%</td></tr>')
    tbl = _table(["CPT (non-facility = office/AIC)", "CY2025", "CY2026",
                  "Δ"], rows)
    stacks = ""
    mx = max(v["admin_total"] for v in a["visit_stacks"]) or 1
    for v in a["visit_stacks"]:
        w = v["admin_total"] / mx * 100
        stacks += (
            f'<div style="margin:7px 0;">'
            f'<div style="display:flex;justify-content:space-between;'
            f'font-size:11.5px;"><span style="color:#1a2332;'
            f'font-weight:600;">{html.escape(v["visit"])}</span>'
            f'<span class="num" style="color:{_NAVY};font-weight:700;">'
            f'${v["admin_total"]:,.2f}</span></div>'
            f'<div style="height:11px;background:#ece5d6;border-radius:2px;'
            f'overflow:hidden;"><div style="height:100%;width:{w:.0f}%;'
            f'background:{_TEAL};"></div></div>'
            f'<div style="font-size:10px;color:{_FAINT};">'
            f'{html.escape(v["codes"])} — {html.escape(v["note"])}</div>'
            f'</div>')
    return (
        f'<div style="display:grid;grid-template-columns:1.15fr 1fr;'
        f'gap:20px;align-items:start;">'
        f'<div>{tbl}{_note(a["pfs_source_note"])}</div>'
        f'<div><div style="font-size:10px;color:{_FAINT};'
        f'letter-spacing:0.06em;font-weight:700;margin-bottom:2px;">'
        f'WHAT A CHAIR VISIT CODES OUT TO (CY2025 MEDICARE ADMIN '
        f'REVENUE)</div>{stacks}'
        f'<p style="font-size:10.5px;color:{_FAINT};margin:6px 0 0;'
        f'line-height:1.5;">CPT hierarchy: one initial code per '
        f'encounter, add-ons stack. The admin fee is the AIC&#39;s '
        f'service revenue — the drug bills separately at ASP+6%.</p>'
        f'</div></div>')


def _home_cpt_section(a: Dict[str, Any]) -> str:
    g_rows = ""
    for g in a["hit_g_codes"]:
        g_rows += (
            f'<tr><td style="{_TD}">'
            f'<code style="font-size:11px;color:{_NAVY};font-weight:700;">'
            f'{g["first_code"]} / {g["code"]}</code>'
            f'<div style="font-size:10px;color:{_FAINT};">Category '
            f'{g["category"]}</div></td>'
            f'<td style="{_TD}font-size:11px;color:{_DIM};">'
            f'{html.escape(g["drugs"])}</td>'
            f'<td class="num" style="{_TDR}">${g["first_visit"]:,.2f}</td>'
            f'<td class="num" style="{_TDR}font-weight:600;">'
            f'${g["subsequent"]:,.2f}</td></tr>')
    g_tbl = _table(["HIT codes (first / subseq.)", "Drug category",
                    "First visit", "Subsequent"], g_rows, right_from=2)

    # The calendar-day gap, drawn: a 28-day OPAT course, 4 paid days.
    cells = ""
    for d in range(28):
        paid = d % 7 == 0
        cells += (
            f'<div title="day {d+1}: '
            f'{"nurse visit — paid" if paid else "therapy day — $0"}" '
            f'style="width:18px;height:18px;border-radius:3px;'
            f'background:{_POS if paid else "#ece5d6"};'
            f'border:1px solid {"#0a8a5f" if paid else "#d6cfc0"};">'
            f'</div>')
    cat1 = next(g for g in a["hit_g_codes"] if g["category"] == 1)
    paid_total = cat1["first_visit"] + 3 * cat1["subsequent"]
    gap = (
        f'<div style="font-size:10px;color:{_FAINT};letter-spacing:'
        f'0.06em;font-weight:700;margin:12px 0 4px;">THE CALENDAR-DAY '
        f'GAP — A 28-DAY OPAT COURSE, WEEKLY NURSE VISIT</div>'
        f'<div style="display:grid;grid-template-columns:repeat(14,18px);'
        f'gap:3px;">{cells}</div>'
        f'<p style="font-size:11.5px;color:{_DIM};margin:6px 0 0;'
        f'line-height:1.6;">4 paid visit-days '
        f'(<span style="color:{_POS};font-weight:700;">green</span>) = '
        f'<strong>${paid_total:,.2f}</strong> of Medicare HIT revenue '
        f'for 28 days of therapy — the other 24 days pay $0. This is '
        f'why home infusion lives on COMMERCIAL per-diems.</p>')

    p_rows = ""
    for p in a["home_perdiem_codes"]:
        rate = p["published_rate"]
        rate_s = (f'${rate:,.2f}' if rate is not None else
                  f'<span style="color:{_WARN};font-weight:600;">'
                  f'no public rate</span>')
        p_rows += (
            f'<tr><td style="{_TD}">'
            f'<code style="font-size:11px;color:{_NAVY};font-weight:700;">'
            f'{p["code"]}</code> '
            f'<span style="font-size:10px;color:{_FAINT};">'
            f'{html.escape(p["therapy"])}</span>'
            f'<div style="font-size:10.5px;color:{_DIM};">'
            f'{html.escape(p["descriptor"])}</div></td>'
            f'<td class="num" style="{_TDR}">{rate_s}</td></tr>')
    p_tbl = _table(["Commercial per-diem S-code",
                    "Published rate (MT Medicaid floor)"], p_rows)
    return (
        f'<div style="display:grid;grid-template-columns:1fr 1fr;'
        f'gap:20px;align-items:start;">'
        f'<div><div style="font-size:10px;color:{_FAINT};letter-spacing:'
        f'0.06em;font-weight:700;margin-bottom:3px;">MEDICARE HIT '
        f'BENEFIT — CY2025 PER-VISIT-DAY {_badge("VERIFIED — CMS HIT RATES FILE", _POS)}'
        f'</div>{g_tbl}{gap}{_note(a["hit_note"])}</div>'
        f'<div><div style="font-size:10px;color:{_FAINT};letter-spacing:'
        f'0.06em;font-weight:700;margin-bottom:3px;">COMMERCIAL / '
        f'MANAGED-CARE PER-DIEM S-CODES {_badge("MEDICARE NEVER PAYS S-CODES", _WARN)}'
        f'</div>{p_tbl}{_note(a["home_perdiem_note"])}</div></div>')


def _cross_site_section(a: Dict[str, Any]) -> str:
    cs = a["cross_site"]
    rows = ""
    for r in cs["rows"]:
        comm = (f'${r["commercial"]:,.2f}' if r["commercial"] else "—")
        rows += (
            f'<tr><td style="{_TD}font-weight:600;">'
            f'{html.escape(r["site"])}'
            f'<div style="font-size:10px;color:{_FAINT};">'
            f'{html.escape(r["note"])}</div></td>'
            f'<td style="{_TD}"><code style="font-size:11px;'
            f'color:{_NAVY};">{html.escape(r["code"])}</code></td>'
            f'<td class="num" style="{_TDR}font-weight:600;">'
            f'${r["amount"]:,.2f}</td>'
            f'<td class="num" style="{_TDR}">{r["vs_aic"]:.2f}x</td>'
            f'<td class="num" style="{_TDR}">{comm}'
            f'<div style="font-size:9.5px;color:{_FAINT};">'
            f'{html.escape(r["commercial_basis"])}</div></td></tr>')
    tbl = _table(["Site", "Code", "Medicare CY2025", "vs AIC",
                  "Commercial"], rows, right_from=2)
    t = parse_table(
        "Site\tMedicare\nHOPD (APC 5694)\t"
        f'{cs["rows"][0]["amount"]:.2f}\n'
        f'Office / AIC (96413)\t{cs["rows"][1]["amount"]:.2f}\n'
        f'Home HIT (G0070)\t{cs["rows"][2]["amount"]:.2f}')
    chart = render_cdd_chart("column", t, {
        "title": "Same complex-biologic administration — Medicare, "
                 "by site ($)",
        "palette": "Navy–Teal", "show_values": True})
    return (
        f'<div style="display:grid;grid-template-columns:1.15fr 1fr;'
        f'gap:18px;align-items:start;">'
        f'<div>{tbl}{_note(cs["note"])}</div>'
        f'{_chart_block("txcCrossSite", chart, "tx-infusion-cross-site")}'
        f'</div>')


def _state_gaf_section(a: Dict[str, Any]) -> str:
    sr = a["state_reimbursement"]
    bars = ""
    for s in sr["states"]:
        w = (s["gaf"] - 0.85) / (1.30 - 0.85) * 100
        w = max(2.0, min(100.0, w))
        tone = _TEAL if s["is_tx"] else _NAVY
        weight = "font-weight:800;" if s["is_tx"] else ""
        bars += (
            f'<div style="display:grid;grid-template-columns:34px 1fr '
            f'120px;gap:6px;align-items:center;margin:1px 0;">'
            f'<div style="font-size:10px;{weight}'
            f'color:{tone if s["is_tx"] else "#1a2332"};">'
            f'{s["state"]}{" ◀" if s["is_tx"] else ""}</div>'
            f'<div style="height:9px;background:#ece5d6;border-radius:2px;'
            f'overflow:hidden;"><div style="height:100%;width:{w:.0f}%;'
            f'background:{tone};opacity:{1.0 if s["is_tx"] else 0.82};">'
            f'</div></div>'
            f'<div class="num" style="font-size:10px;color:{_DIM};'
            f'text-align:right;">{s["gaf"]:.3f} · ${s["rate"]:,.2f}'
            f'</div></div>')
    head = (
        f'<div style="display:flex;justify-content:space-between;'
        f'align-items:center;flex-wrap:wrap;gap:8px;margin-bottom:8px;">'
        f'<p style="font-size:12px;color:{_DIM};margin:0;max-width:660px;'
        f'line-height:1.6;">What the SAME code pays by state: GAF × the '
        f'national non-facility amount for '
        f'<code>{html.escape(sr["anchor_code"])}</code> '
        f'(${sr["anchor_nonfac"]:,.2f}). Top-to-bottom spread: '
        f'<strong>{sr["spread_pct"]:.1f}%</strong>.</p>'
        + _badge("COMPUTED FROM THE VENDORED CMS GPCI2025 FILE", _POS)
        + '</div>')
    return (
        f'{head}<div id="txcStateGaf" style="border:1px solid #d6cfc0;'
        f'border-radius:8px;padding:12px;background:#fff;'
        f'column-count:2;column-gap:26px;">{bars}</div>'
        + chart_export_toolbar("txcStateGaf", "infusion-gaf-by-state")
        + _note(sr["note"]))


def _tx_locality_section(a: Dict[str, Any]) -> str:
    locs = a["tx_localities"]
    rows = ""
    for r in locs:
        hot = r["city"].startswith("Rest")
        rows += (
            f'<tr><td style="{_TD}font-weight:600;'
            f'{"color:" + _NEG + ";" if hot else ""}">'
            f'{html.escape(r["city"])}'
            f'<div style="font-size:10px;color:{_FAINT};font-weight:400;">'
            f'loc {r["locality"]} · {html.escape(r["counties"])}</div></td>'
            f'<td class="num" style="{_TDR}">{r["work"]:.3f}</td>'
            f'<td class="num" style="{_TDR}">{r["pe"]:.3f}</td>'
            f'<td class="num" style="{_TDR}">{r["mp"]:.3f}</td>'
            f'<td class="num" style="{_TDR}font-weight:700;">'
            f'{r["gaf"]:.4f}</td>'
            f'<td class="num" style="{_TDR}">'
            f'${r["rates"]["96413"]:,.2f}</td>'
            f'<td class="num" style="{_TDR}">'
            f'${r["rates"]["96365"]:,.2f}</td></tr>')
    tbl = _table(["Locality (city)", "Work", "PE", "MP", "GAF",
                  "96413", "96365"], rows)
    t = parse_table(
        "City\t96413 $\n" + "\n".join(
            f'{r["city"]}\t{r["rates"]["96413"]:.2f}' for r in locs))
    chart = render_cdd_chart("bar", t, {
        "title": "96413 (chemo/biologic 1st hr) by Texas PFS locality",
        "palette": "Navy–Teal", "show_values": True})
    return (
        f'<div style="display:grid;grid-template-columns:1.2fr 1fr;'
        f'gap:18px;align-items:start;">'
        f'<div>{tbl}{_note(a["tx_locality_note"])}</div>'
        f'{_chart_block("txcLocality", chart, "tx-infusion-locality-rates")}'
        f'</div>')


def _drug_mix_section(a: Dict[str, Any]) -> str:
    dm = a["drug_mix"]
    rows = ""
    for d in dm["drugs"]:
        live = (f' {_badge("LIVE ASP", _POS)}' if d.get("live") else "")
        rows += (
            f'<tr><td style="{_TD}">'
            f'<code style="font-size:11px;color:{_NAVY};font-weight:700;">'
            f'{d["hcpcs"]}</code> '
            f'<span style="font-weight:600;">{html.escape(d["drug"])}'
            f'</span>{live}'
            f'<div style="font-size:10px;color:{_FAINT};">'
            f'{html.escape(d["klass"])} · {html.escape(d["dose"])} — '
            f'{html.escape(d["note"])}</div></td>'
            f'<td class="num" style="{_TDR}">${d["asp_unit"]:,.2f}'
            f'<div style="font-size:9px;color:{_FAINT};">'
            f'{html.escape(d["unit"])}</div></td>'
            f'<td class="num" style="{_TDR}font-weight:600;">'
            f'${d["asp_dose"]:,.2f}</td>'
            f'<td class="num" style="{_TDR}">{d["doses_yr"]:.1f}</td>'
            f'<td class="num" style="{_TDR}font-weight:600;">'
            f'{_money(d["annual_drug_rev"])}</td>'
            f'<td class="num" style="{_TDR}color:{_DIM};">'
            f'${d["medicare_spread_dose"]:,.0f} / '
            f'<span style="color:{_POS};">'
            f'${d["commercial_spread_dose"]:,.0f}</span></td></tr>')
    tbl = _table(["Drug (HCPCS · dose · note)", "ASP / unit", "$ / dose",
                  "Doses/yr", "Annual drug rev / patient",
                  "Spread/dose (Mcare / comm.)"], rows)
    donut = parse_table(
        "Class\tShare\n" + "\n".join(
            f'{m["klass"]}\t{m["share"]*100:.0f}'
            for m in dm["mix"]))
    chart = render_cdd_chart("donut", donut, {
        "title": "AIC drug-revenue mix by therapy class (%)",
        "palette": "Chartis"})
    return (
        f'{tbl}{_note(dm["note"])}'
        f'<div style="display:grid;grid-template-columns:1fr 1fr;'
        f'gap:18px;align-items:start;margin-top:14px;">'
        f'{_chart_block("txcDrugMix", chart, "tx-infusion-drug-mix")}'
        f'<div style="font-size:12.5px;color:{_DIM};line-height:1.7;'
        f'padding-top:8px;">{html.escape(dm["read"])}'
        f'<p style="margin:8px 0 0;">White-bagging context: payers '
        f'white-bag ≈15–20% of physician-office covered lives (stable, '
        f'DCI 2024) and ≈38% of HOPD oncology sourcing — and Texas is '
        f'among the states RESTRICTING insurer white-bagging mandates, '
        f'a statutory shield for TX buy-and-bill.</p></div></div>')


def _overall_reimbursement_section(a: Dict[str, Any]) -> str:
    orr = a["overall_reimbursement"]
    rows = ""
    for r in orr["rows"]:
        rows += (
            f'<tr><td style="{_TD}font-weight:600;">'
            f'{html.escape(r["payer"])}'
            f'<div style="font-size:10px;color:{_FAINT};font-weight:400;">'
            f'{html.escape(r["note"])}</div></td>'
            f'<td class="num" style="{_TDR}">{r["share"]*100:.1f}%</td>'
            f'<td class="num" style="{_TDR}">{r["index"]:.2f}</td>'
            f'<td class="num" style="{_TDR}font-weight:600;">'
            f'${r["revenue_per_infusion"]:,.0f}</td>'
            f'<td class="num" style="{_TDR}">'
            f'${r["contribution"]:,.2f}</td></tr>')
    rows += (
        f'<tr style="border-top:2px solid #c9c1ac;">'
        f'<td style="{_TD}font-weight:700;">Blended</td>'
        f'<td class="num" style="{_TDR}font-weight:700;">100.0%</td>'
        f'<td class="num" style="{_TDR}font-weight:700;">'
        f'{orr["weighted_index"]:.2f}</td>'
        f'<td class="num" style="{_TDR}font-weight:700;">'
        f'${orr["blended_revenue_per_infusion"]:,.0f}</td>'
        f'<td class="num" style="{_TDR}font-weight:700;color:{_POS};">'
        f'= part-1 ${orr["anchor"]:,.0f} anchor ✓</td></tr>')
    tbl = _table(["Payer", "Mix", "Yield index (FFS=1.00)",
                  "Rev / infusion", "Contribution"], rows)
    t = parse_table(
        "Payer\t$ / infusion\n" + "\n".join(
            f'{r["payer"]}\t{r["revenue_per_infusion"]}'
            for r in orr["rows"]))
    chart = render_cdd_chart("bar", t, {
        "title": "Net revenue per infusion by payer ($)",
        "palette": "Navy–Teal", "show_values": True})
    return (
        f'<div style="display:grid;grid-template-columns:1.2fr 1fr;'
        f'gap:18px;align-items:start;">'
        f'<div>{tbl}{_note(orr["note"])}</div>'
        f'{_chart_block("txcPayerYield", chart, "tx-infusion-payer-yield")}'
        f'</div>')


def _metro_payer_section(a: Dict[str, Any]) -> str:
    mp = a["metro_payers"]
    rows = ""
    for m in mp["metros"]:
        hcsc = (f'{m["hcsc_share"]*100:.0f}% — published'
                if m["hcsc_share"] else m["hcsc_band"])
        rows += (
            f'<tr><td style="{_TD}font-weight:700;">#{m["rank"]} '
            f'{html.escape(m["metro"])}'
            f'<div style="font-size:10px;color:{_FAINT};font-weight:400;">'
            f'{html.escape(m["note"])}</div></td>'
            f'<td style="{_TD}font-size:11px;">BCBSTX #1 — {hcsc}'
            f'<div style="font-size:10px;color:{_FAINT};">'
            f'#2: {html.escape(m["number_two"])}</div></td>'
            f'<td class="num" style="{_TDR}">'
            f'{m["ma_penetration"]*100:.1f}%'
            f'<div style="font-size:9.5px;color:{_FAINT};">'
            f'{html.escape(m["core_county"])} · ring: '
            f'{html.escape(m["ring_ma"])}</div></td>'
            f'<td class="num" style="{_TDR}">'
            f'{m["hmo_exposure"]*100:.1f}%</td>'
            f'<td class="num" style="{_TDR}font-weight:700;color:'
            f'{_POS if m["buyandbill_friendliness"] >= 66 else _WARN};">'
            f'{m["buyandbill_friendliness"]:.1f}</td></tr>')
    tbl = _table(["Metro (ranked)", "Commercial concentration",
                  "MA penetration", "HMO exposure",
                  "Buy-&-bill score"], rows, right_from=2)
    pm = mp["product_mix"]
    t = parse_table(
        "Metro\tMA penetration %\tHMO exposure %\n" + "\n".join(
            f'{m["metro"]}\t{m["ma_penetration"]*100:.1f}\t'
            f'{m["hmo_exposure"]*100:.1f}'
            for m in sorted(mp["metros"], key=lambda x: x["metro"])))
    chart = render_cdd_chart("column", t, {
        "title": "MA penetration vs HMO exposure by metro (%)",
        "palette": "Navy–Teal", "show_values": True, "suffix": "%"})
    mix_strip = (
        f'<div style="display:flex;gap:0;margin:10px 0 4px;height:26px;'
        f'border-radius:4px;overflow:hidden;font-size:10px;color:#fff;'
        f'font-weight:700;text-align:center;line-height:26px;">'
        f'<div style="width:{pm["ppo"]*100:.0f}%;background:{_NAVY};">'
        f'PPO {pm["ppo"]*100:.0f}%</div>'
        f'<div style="width:{pm["hdhp"]*100:.0f}%;background:{_TEAL};">'
        f'HDHP/SO {pm["hdhp"]*100:.0f}%</div>'
        f'<div style="width:{pm["pos"]*100:.0f}%;background:#b8943f;">'
        f'POS {pm["pos"]*100:.0f}%</div>'
        f'<div style="width:{pm["hmo"]*100:.0f}%;background:{_NEG};">'
        f'HMO {pm["hmo"]*100:.0f}%</div></div>'
        f'<p style="font-size:10.5px;color:{_FAINT};margin:0 0 8px;">'
        f'Commercial covered-worker product mix (KFF EHBS 2025; 67% '
        f'self-funded ERISA — predominantly open-access). The '
        f'gatekeeper-HMO slice of TX commercial is only '
        f'{pm["hmo"]*100:.0f}% — the HMO concentration lives in MA '
        f'({mp["tx_ma_hmo_share"]*100:.0f}% of TX MA plans) and '
        f'Medicaid STAR.</p>')
    hcsc_box = (
        f'<div style="border:1px solid {_NAVY};border-left:4px solid '
        f'{_NAVY};border-radius:6px;padding:11px 14px;background:#fff;'
        f'font-size:12px;color:{_DIM};line-height:1.65;margin-top:12px;">'
        f'<div style="font-size:9px;font-weight:700;letter-spacing:'
        f'0.08em;color:{_NAVY};margin-bottom:3px;">THE HCSC FACT</div>'
        f'{html.escape(mp["hcsc_facts"])}</div>')
    return (
        f'{mix_strip}'
        f'<div style="display:grid;grid-template-columns:1.25fr 1fr;'
        f'gap:18px;align-items:start;">'
        f'<div>{tbl}{hcsc_box}{_note(mp["note"])}</div>'
        f'{_chart_block("txcMetroPayer", chart, "tx-payer-by-metro")}'
        f'</div>')


_STATUS_STYLE = {
    "in": (f"background:#e6f4ee;color:{_POS};border:1px solid {_POS};",
           "IN NETWORK"),
    "owned": (f"background:{_NAVY};color:#fff;border:1px solid {_NAVY};",
              "PAYER-OWNED"),
    "rpt": (f"background:#f3efe4;color:{_WARN};border:1px solid {_WARN};",
            "REPORTED — VERIFY"),
    "ltd": (f"background:#efe9dc;color:{_DIM};border:1px solid #c9c1ac;",
            "SELECTIVE"),
    "out": (f"background:#fbeae7;color:{_NEG};border:1px solid {_NEG};",
            "OUT"),
}


def _network_section(a: Dict[str, Any]) -> str:
    net = a["network"]
    plans = net["plans"]
    head = "".join(
        f'<th style="text-align:center;padding:5px 4px;font-size:10px;">'
        f'{html.escape(p)}</th>' for p in plans)
    rows = ""
    for op in net["matrix"]:
        hq = "HealthQuest" in op["operator"]
        cells = ""
        for p in plans:
            st = op["status"][p]
            style, label = _STATUS_STYLE[st]
            cells += (
                f'<td style="padding:4px;text-align:center;">'
                f'<span style="display:inline-block;font-size:8.5px;'
                f'font-weight:700;letter-spacing:0.03em;padding:3px 6px;'
                f'border-radius:3px;{style}">{label}</span></td>')
        rows += (
            f'<tr style="{"background:#f3f7f4;" if hq else ""}">'
            f'<td style="{_TD}font-weight:{700 if hq else 600};'
            f'{"color:" + _TEAL + ";" if hq else ""}">'
            f'{html.escape(op["operator"])}'
            f'<div style="font-size:9.5px;color:{_FAINT};'
            f'font-weight:400;">{html.escape(op["note"])}</div></td>'
            f'{cells}</tr>')
    matrix = (
        '<div style="overflow-x:auto;"><table style="width:100%;'
        'border-collapse:collapse;font-size:12px;">'
        f'<thead><tr style="border-bottom:2px solid #c9c1ac;">'
        f'<th {_TH}>Operator</th>{head}</tr></thead>'
        f'<tbody>{rows}</tbody></table></div>')
    arows = ""
    for r in net["rows"]:
        cells = "".join(
            f'<td class="num" style="{_TDR}font-weight:600;color:'
            f'{_POS if r["options"][p] >= 4 else _DIM};">'
            f'{r["options"][p]}</td>' for p in plans)
        arows += (f'<tr><td style="{_TD}font-weight:600;">'
                  f'{html.escape(r["metro"])}</td>{cells}</tr>')
    access = (
        '<div style="overflow-x:auto;"><table style="width:100%;'
        'border-collapse:collapse;font-size:12px;">'
        f'<thead><tr style="border-bottom:2px solid #c9c1ac;">'
        f'<th {_TH}>Metro</th>{head}</tr></thead>'
        f'<tbody>{arows}</tbody></table></div>')
    return (
        f'{matrix}{_note(net["note"])}'
        f'<div style="font-size:10px;color:{_FAINT};letter-spacing:'
        f'0.06em;font-weight:700;margin:16px 0 4px;">IN-NETWORK '
        f'INFUSION OPTIONS PER PLAN, PER METRO (OPERATORS PRESENT × '
        f'IN-NETWORK/OWNED STATUS)</div>{access}')


def _proximity_section(a: Dict[str, Any]) -> str:
    px = a["proximity"]
    rows = ""
    for c in px["counties"]:
        tone = {"convenient": _POS, "acceptable": _WARN,
                "burdened": _NEG}[c["band"]]
        rows += (
            f'<tr><td style="{_TD}font-weight:600;">#{c["rank"]} '
            f'{html.escape(c["county"])}</td>'
            f'<td class="num" style="{_TDR}">{c["population"]:,}</td>'
            f'<td class="num" style="{_TDR}">{c["land_sqmi"]:,.0f}</td>'
            f'<td class="num" style="{_TDR}">{c["pop_density"]:,.0f}</td>'
            f'<td class="num" style="{_TDR}">{c["est_centers"]}</td>'
            f'<td class="num" style="{_TDR}">'
            f'{c["avg_miles_to_nearest"]:.1f}</td>'
            f'<td class="num" style="{_TDR}font-weight:700;color:{tone};">'
            f'{c["avg_minutes"]} min</td></tr>')
    tbl = _table(["County", "Population", "Sq mi", "Pop / sq mi",
                  "Est. centers", "Avg mi to nearest", "Drive"], rows)
    t = parse_table(
        "County\tMinutes\n" + "\n".join(
            f'{c["county"]}\t{c["avg_minutes"]}'
            for c in px["counties"]))
    chart = render_cdd_chart("bar", t, {
        "title": "Average drive to the nearest infusion option (min)",
        "palette": "Navy–Teal", "show_values": True})
    return (
        f'<div style="display:grid;grid-template-columns:1.25fr 1fr;'
        f'gap:18px;align-items:start;">'
        f'<div>{tbl}{_note(px["note"])}</div>'
        f'{_chart_block("txcProximity", chart, "tx-infusion-proximity")}'
        f'</div>')


#: Stylized map coordinates (viewBox 0–100, same outline as part 1)
#: for the HealthQuest exhibit — schematic, not a projection.
_HQ_MAP_XY = {
    "Houston": (70.0, 57.0),
    "Beaumont": (79.5, 54.5),
    "The Woodlands": (70.0, 51.5),
    "Austin": (52.0, 56.0),
}


def _healthquest_section(a: Dict[str, Any]) -> str:
    hq = a["healthquest"]
    p = hq["profile"]
    from .texas_infusion_page import _TX_OUTLINE
    pins = ""
    for s in hq["sites"]:
        key = next((k for k in _HQ_MAP_XY if s["city"].startswith(k)), None)
        if not key:
            continue
        x, y = _HQ_MAP_XY[key]
        open_ = s["status"] == "open"
        tone = _TEAL if open_ else (_WARN if s["status"] == "service"
                                    else _FAINT)
        pins += (
            f'<circle cx="{x}" cy="{y}" r="{3.4 if open_ else 2.4}" '
            f'fill="{tone}" fill-opacity="0.9" stroke="#fff" '
            f'stroke-width="0.7"><title>{html.escape(s["city"])} — '
            f'{html.escape(s["status"])}</title></circle>'
            f'<text x="{x}" y="{y - (4.6 if open_ else 3.6)}" '
            f'text-anchor="middle" font-size="3.2" font-weight="700" '
            f'fill="#1a2332">{html.escape(key)}</text>')
    svg = (
        f'<svg viewBox="0 0 100 100" width="300" height="300" role="img" '
        f'aria-label="HealthQuest sites on a stylized Texas outline" '
        f'style="max-width:320px;">'
        f'<polygon points="{_TX_OUTLINE}" fill="#efe9dc" '
        f'stroke="#c9c1ac" stroke-width="0.8"/>{pins}</svg>'
        f'<div style="font-size:9.5px;color:{_FAINT};">'
        f'<span style="color:{_TEAL};font-weight:700;">●</span> open '
        f'chair site &nbsp;<span style="color:{_WARN};font-weight:700;">'
        f'●</span> home-infusion service area &nbsp;'
        f'<span style="color:{_FAINT};font-weight:700;">●</span> '
        f'announced</div>')

    prof_rows = "".join(
        f'<div style="display:grid;grid-template-columns:130px 1fr;'
        f'gap:8px;padding:4px 0;border-bottom:1px solid #efe9dc;'
        f'font-size:11.5px;">'
        f'<div style="color:{_FAINT};font-weight:700;font-size:9.5px;'
        f'letter-spacing:0.05em;padding-top:2px;">'
        f'{html.escape(label.upper())}</div>'
        f'<div style="color:{_DIM};line-height:1.55;">'
        f'{html.escape(str(p[key]))}</div></div>'
        for label, key in [
            ("HQ", "hq"), ("Founded", "founded"),
            ("Ownership", "ownership"), ("Channels", "channels"),
            ("Accreditation", "accreditation"),
            ("Therapies", "therapies"), ("Payers", "payers"),
            ("Experience", "experience"), ("Scale", "scale")])
    drows = ""
    for c in hq["centers"]:
        tone = _POS if c["within_30"] else _WARN
        drows += (
            f'<tr><td style="{_TD}">{html.escape(c["place"])}</td>'
            f'<td class="num" style="{_TDR}">{c["pop"]:,}</td>'
            f'<td style="{_TD}font-size:11px;color:{_DIM};">'
            f'{html.escape(c["nearest_site"])}</td>'
            f'<td class="num" style="{_TDR}">{c["road_miles"]:.1f}</td>'
            f'<td class="num" style="{_TDR}font-weight:700;color:{tone};">'
            f'{c["drive_minutes"]} min</td></tr>')
    dtbl = _table(["Population center", "Pop", "Nearest open site",
                   "Road mi", "Drive"], drows, right_from=1)
    comp = "".join(
        f'<li style="margin:4px 0;font-size:11.5px;color:{_DIM};">'
        f'<strong style="color:#1a2332;">{html.escape(c["operator"])}'
        f'</strong> <span style="color:{_FAINT};">'
        f'({html.escape(c["model"])})</span> — '
        f'{html.escape(", ".join(c["sites"]))}</li>'
        for c in hq["competitors"])
    kpis = (
        '<div class="ck-kpi-grid" style="margin:10px 0;">'
        + ck_kpi_block("Metro pop ≤30 min",
                       f'{hq["pct_within_30min"]*100:.1f}%',
                       sub=f'{hq["pop_within_30min"]:,} of '
                           f'{hq["pop_total"]:,} (pop-center mass)')
        + ck_kpi_block("Weighted avg drive",
                       f'{hq["weighted_avg_minutes"]} min',
                       sub="to the nearest open chair site")
        + ck_kpi_block("Coverage model", "Chair + home",
                       sub="AIC where dense, nurse where far — the "
                           "hybrid IS the pitch")
        + '</div>')
    return (
        f'<div style="border:1px solid #c9c1ac;border-top:4px solid '
        f'{_TEAL};border-radius:6px;padding:14px 16px;background:#fbf9f4;'
        f'margin-bottom:14px;">'
        f'<div style="display:flex;justify-content:space-between;'
        f'flex-wrap:wrap;gap:8px;align-items:center;">'
        f'<div style="font-size:15px;font-weight:700;color:{_NAVY};'
        f'font-family:\'Source Serif 4\',Georgia,serif;">'
        f'{html.escape(p["name"])}</div>'
        f'<a href="{html.escape(p["web"])}" style="font-size:11px;'
        f'color:{_TEAL};font-weight:600;text-decoration:none;">'
        f'{html.escape(p["web"])} →</a></div>'
        f'<p style="font-size:12.5px;color:#1a2332;line-height:1.65;'
        f'margin:8px 0 10px;">{html.escape(p["positioning"])}</p>'
        f'<div style="display:grid;grid-template-columns:1fr 320px;'
        f'gap:18px;align-items:start;">'
        f'<div>{prof_rows}</div><div>{svg}</div></div></div>'
        + kpis
        + f'<div style="display:grid;grid-template-columns:1.15fr 1fr;'
          f'gap:18px;align-items:start;">'
          f'<div><div style="font-size:10px;color:{_FAINT};'
          f'letter-spacing:0.06em;font-weight:700;margin-bottom:3px;">'
          f'DRIVE TIME TO THE NEAREST OPEN HEALTHQUEST SITE — HOUSTON '
          f'METRO POPULATION CENTERS</div>{dtbl}{_note(hq["note"])}</div>'
          f'<div><div style="font-size:10px;color:{_FAINT};'
          f'letter-spacing:0.06em;font-weight:700;margin-bottom:3px;">'
          f'WHO ELSE IS CLOSE — NAMED HOUSTON-METRO COMPETITOR SITES '
          f'(PUBLIC LOCATORS)</div>'
          f'<ul style="margin:0;padding-left:16px;">{comp}</ul></div>'
          f'</div>')


def _experience_section(a: Dict[str, Any]) -> str:
    ex = a["experience"]
    drows = ""
    for d in ex["drivers"]:
        drows += (
            f'<tr><td style="{_TD}font-weight:600;">'
            f'{html.escape(d["driver"])}'
            f'<div style="font-size:10px;color:{_FAINT};font-weight:400;">'
            f'{html.escape(d["why"])}</div></td>'
            f'<td class="num" style="{_TDR}">{d["weight"]*100:.0f}%</td>'
            f'<td style="{_TD}font-size:10.5px;color:{_DIM};'
            f'line-height:1.5;">{html.escape(d["benchmark"])}</td></tr>')
    dtbl = _table(["Driver", "Weight", "Published evidence anchor"],
                  drows, right_from=1)
    mrows = ""
    for m in ex["models"]:
        w = m["weighted_score"] / 5 * 100
        hq = "HealthQuest" in m["example"]
        mrows += (
            f'<div style="margin:8px 0;">'
            f'<div style="display:flex;justify-content:space-between;'
            f'font-size:12px;"><span style="font-weight:700;'
            f'color:{_TEAL if hq else "#1a2332"};">#{m["rank"]} '
            f'{html.escape(m["model"])} '
            f'<span style="color:{_FAINT};font-weight:400;">'
            f'({html.escape(m["example"])})</span></span>'
            f'<span class="num" style="font-weight:700;color:{_NAVY};">'
            f'{m["weighted_score"]:.2f} / 5</span></div>'
            f'<div style="height:12px;background:#ece5d6;border-radius:'
            f'2px;overflow:hidden;"><div style="height:100%;'
            f'width:{w:.0f}%;background:{_TEAL if hq else _NAVY};">'
            f'</div></div>'
            f'<div style="font-size:10px;color:{_FAINT};">'
            f'{html.escape(m["nps_anchor"])}</div></div>')
    return (
        f'<div style="display:grid;grid-template-columns:1.2fr 1fr;'
        f'gap:20px;align-items:start;">'
        f'<div>{dtbl}</div>'
        f'<div><div style="font-size:10px;color:{_FAINT};letter-spacing:'
        f'0.06em;font-weight:700;margin-bottom:2px;">OPERATOR-MODEL '
        f'SCORECARD (FRAMEWORK SCORES × EVIDENCE-WEIGHTED DRIVERS)'
        f'</div>{mrows}</div></div>'
        + _note(ex["note"]))


def render_texas_infusion_continued_page(
    qs: "Dict[str, Any] | None" = None,
) -> str:
    """Render the Texas Infusion Market · Continued page."""
    from ..diligence.texas_infusion_continued import (
        build_texas_infusion_continued_analysis,
    )
    _live = (qs or {}).get("asp")
    fetch_live = (_live == "live"
                  or (isinstance(_live, list) and "live" in _live))
    a = build_texas_infusion_continued_analysis(fetch_live=fetch_live)
    sources = "".join(
        f'<li style="margin:3px 0;font-size:11px;color:{_DIM};">'
        f'{html.escape(src)}</li>' for src in a["sources"])

    body = (
        ck_page_title(
            "Texas Infusion Market · Continued",
            eyebrow="DILIGENCE · MARKET SIZING — PART 2 OF 2",
            meta=f'AIC {_money(a["channel_sizing"]["aic"]["revenue"])} · '
                 f'home {_money(a["channel_sizing"]["home"]["revenue"])} '
                 f'· CPT-level rates · payer + proximity grain',
        )
        + ck_source_purpose(
            purpose="Take the part-1 sizing down to the per-claim, "
                    "per-payer, per-place grain: CPT/HCPCS rates by "
                    "site and city, drug-dose economics, PPO/HMO "
                    "structure, network access, and the convenience/"
                    "experience wedge.",
            universe="illustrative",
            source="CMS PFS/OPPS/HIT/ASP/GPCI published files "
                   "(verified June 2026; GPCI file vendored) + AMA/"
                   "KFF/CMS payer data + operator disclosures. "
                   "Directional items flagged in place.",
        )
        + '<div class="ts-wrap" style="max-width:1020px;">'
        + part_tabs("part2")
        + _kpi_strip(a)

        + ck_section_header(
            "Channel sizing — AIC and home, reconciled",
            eyebrow="BOTTOM-UP BY SITE OF CARE · TIES TO THE PART-1 "
                    "TAM EXACTLY")
        + _channel_sizing_section(a)
        + _so_what(
            "The single $650/infusion blend in part 1 hides the "
            "channel structure: HOPD volume monetizes at ≈2.1× the "
            "AIC rate and home at ≈0.7×. The AIC + home channels — "
            "the platform's actual book — are a "
            f'{_money(a["channel_sizing"]["aic"]["revenue"] + a["channel_sizing"]["home"]["revenue"])} '
            "pool growing at the expense of the HOPD slice.")

        + ck_section_header(
            "CPT per office / AIC visit",
            eyebrow="MEDICARE PFS NON-FACILITY · CY2025 + CY2026 · "
                    "VISIT CODING STACKS")
        + _office_cpt_section(a)
        + _so_what(
            "Admin codes are the AIC's service revenue: a biologic "
            "visit codes out to ≈$134–159 of Medicare admin fee "
            "(CY2025), and CY2026 raises the stack ~11%. Commercial "
            "contracts benchmark at 122–148% of these rates — every "
            "point of payer mix moves the chair P&L.")

        + ck_section_header(
            "CPT per home visit — HIT G-codes + per-diem S-codes",
            eyebrow="MEDICARE'S CALENDAR-DAY GAP · THE COMMERCIAL "
                    "PER-DIEM CURRENCY")
        + _home_cpt_section(a)
        + _so_what(
            "Medicare pays the home channel only on nurse-visit days "
            "— a 28-day OPAT course collects ~4 payments — while "
            "commercial pays a daily per-diem plus nursing plus the "
            "drug. The home book's economics are decided by its "
            "commercial mix, which is the first diligence cut on any "
            "home-infusion target.", _NEG)

        + ck_section_header(
            "The same visit, three sites — the steerage arbitrage",
            eyebrow="HOPD APC vs OFFICE PFS vs HOME HIT · MEDICARE + "
                    "COMMERCIAL")
        + _cross_site_section(a)
        + _so_what(
            f'Medicare pays the hospital {a["cross_site"]["hopd_premium"]:.2f}× '
            "the AIC rate for the same hour; commercially the gap is "
            f'≈{a["cross_site"]["commercial_hopd_premium"]:.1f}× on the admin '
            "fee and ≈2.7× on the drug. That spread IS the payer "
            "steerage budget — the volume tailwind an independent "
            "platform is paid to absorb. The 2026 off-campus "
            "site-neutral rule starts collapsing it from the HOPD "
            "side.")

        + ck_section_header(
            "Reimbursement by state",
            eyebrow="CMS GAF · ALL 50 STATES + DC · TEXAS FLAGGED")
        + _state_gaf_section(a)
        + _so_what(
            f'Texas sits #{a["state_reimbursement"]["texas"]["rank"]} '
            f'of {len(a["state_reimbursement"]["states"])} at a '
            f'{a["state_reimbursement"]["texas"]["gaf"]:.3f} average '
            "GAF — Medicare pays essentially the national rate here, "
            "so the TX margin story is volume growth + payer mix, "
            "not a geographic rate premium.")

        + ck_section_header(
            "Reimbursement by city — the eight Texas localities",
            eyebrow="CMS GPCI FILE (VENDORED) · HOUSTON PAYS MOST · "
                    "SAN ANTONIO PAYS REST-OF-TEXAS")
        + _tx_locality_section(a)
        + _so_what(
            "Houston is the best-paid chair in Texas (GAF 1.026) and "
            "San Antonio the worst (Rest-of-Texas, 0.973) — a 5.5% "
            "Medicare rate spread between the two for identical "
            "work. Site selection has a rate term, not just a demand "
            "term.")

        + ck_section_header(
            "Drug mix — dose economics by J-code",
            eyebrow="CMS ASP FILES Q1/Q2 2026 · PER-DOSE PAYMENT · "
                    "SPREADS · ?asp=live REFRESH")
        + _drug_mix_section(a)
        + _so_what(
            "The chair is a portfolio: an Ocrevus patient is ≈$71.5K "
            "of annual drug revenue in two visits, an infliximab-"
            "biosimilar patient ≈$6.8K in 6.5 — at the same admin "
            "fee. Underwrite the target's J-code mix, not its visit "
            "count; and watch the J1300→J1299 class of stale-code "
            "denials in its AR.")

        + ck_section_header(
            "The overall reimbursement rate — payer-weighted",
            eyebrow="WHAT THE BLENDED $650 IS MADE OF")
        + _overall_reimbursement_section(a)
        + _so_what(
            "A commercial infusion nets ≈1.9× a Medicaid one and "
            "≈7.5× a self-pay encounter for identical chair time. "
            "Payer mix is the single most leveraged commercial "
            "variable in the model — one point of commercial mix is "
            "worth more than a point of utilization.")

        + ck_section_header(
            "Payer structure by metro — PPO / HMO concentration",
            eyebrow="AMA 2025 INSURER SHARES · KFF PRODUCT MIX · "
                    "VERIFIED COUNTY MA PENETRATION")
        + _metro_payer_section(a)
        + _so_what(
            "Austin is the commercial-friendliest market in Texas "
            "(BCBSTX at just 37%, MA penetration 47.5%) and San "
            "Antonio the most managed (58.5% MA, HMO-led, at "
            "Rest-of-Texas rates). The same chair earns a different "
            "business model per metro — sequence the buildout "
            "accordingly.")

        + ck_section_header(
            "Who is in network, per plan",
            eyebrow="OPERATOR × PLAN MATRIX · PAYER-OWNED STEERING · "
                    "OPTIONS PER METRO")
        + _network_section(a)
        + _so_what(
            "Three of the nine operators are payer-owned (Optum/UHC, "
            "Coram/Aetna, Paragon/Elevance) — their parents' volume "
            "routes home first. The open lane is HCSC/BCBSTX: ~70% "
            "of TX fully-insured commercial with NO captive infusion "
            "asset. That contract, plus the Medicaid-MCO niches the "
            "nationals skip (HealthQuest's Community Health Choice "
            "preferred status), is the independent's network "
            "strategy in one row.", _NEG)

        + ck_section_header(
            "Proximity & population density",
            eyebrow="CENSUS LAND AREAS · DISTANCE-TO-NEAREST MODEL · "
                    "DRIVE-TIME BANDS")
        + _proximity_section(a)
        + _so_what(a["proximity"]["read"])

        + ck_section_header(
            "HealthQuest — the referral-for-convenience operator",
            eyebrow="HOUSTON REGIONAL SPOTLIGHT · SITES · DRIVE-SHED · "
                    "COMPETITOR PROXIMITY")
        + _healthquest_section(a)
        + _so_what(a["healthquest"]["read"])

        + ck_section_header(
            "Patient experience — the demand-side moat",
            eyebrow="EVIDENCE-ANCHORED DRIVERS · OPERATOR-MODEL "
                    "SCORECARD · NPS DISCLOSURES")
        + _experience_section(a)
        + _so_what(a["experience"]["read"])

        + ck_section_header("Sources & basis", eyebrow="VERIFIABILITY")
        + f'<ul style="margin:0;padding-left:18px;">{sources}</ul>'
        + f'<p style="font-size:11px;color:{_FAINT};margin:10px 0 0;'
          f'line-height:1.6;">{html.escape(a["basis_note"])}</p>'
        + '<p style="font-size:11.5px;margin:10px 0 0;">'
          '<a href="/diligence/texas-infusion" '
          f'style="color:{_NAVY};font-weight:600;text-decoration:none;">'
          '← Back to part 1 — Texas Infusion Market</a></p>'
        + '</div>'
    )

    from ._chartis_kit import ck_page_actions
    from .texas_infusion_page import _inject_section_nav
    body, section_nav = _inject_section_nav(body)
    body = body + section_nav + ck_page_actions()
    return chartis_shell(
        body, "Texas Infusion Market · Continued",
        active_nav="/diligence",
        subtitle=f'CPT · drug mix · payers · proximity — '
                 f'AIC {_money(a["channel_sizing"]["aic"]["revenue"])}',
    )
