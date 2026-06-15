"""Healthcare Verticals 2025-2026 pages — /healthcare-verticals[/<id>].

Renders the public-source-synthesis reference bundle (loaded from
``rcm_mc.data.healthcare_verticals``) as an editorial Chartis dossier: a grouped
index of 17 specialized/adjacent/emerging US healthcare verticals, plus a
per-vertical detail surface with the FY/CY2026 payment economics, cross-vertical
unit economics, market structure, workforce, and provenance.

Honesty: this is a PUBLIC_SOURCE_SYNTHESIS (CMS rules, MedPAC, NIC MAP, USRDS,
SAMHSA, HRSA, CDC ART, PHI) — NOT licensed-IBISWorld-derived and NOT
provider-specific. Every row carries source + confidence; ranges stay ranges.
"""
from __future__ import annotations

import html as _html
from typing import Dict, List, Optional

from rcm_mc.ui._chartis_kit import (
    P, chartis_shell, ck_kpi_block, ck_page_title, ck_source_purpose,
)
from rcm_mc.data import healthcare_verticals as _hv

# Provenance chip — deliberately distinct wording from the industry_intel
# "Licensed report derived" chip so the licensing boundary is never blurred.
_SYNTH_CHIP = (
    f'<span style="display:inline-block;background:{P["accent"]};color:#fff;'
    f'font-size:9px;font-weight:700;letter-spacing:0.08em;padding:2px 8px;'
    f'border-radius:3px;text-transform:uppercase">Public-source synthesis</span>')


def _conf_chip(conf: str) -> str:
    conf = (conf or "").lower()
    tone = {"high": P["positive"], "medium": P["warning"], "low": P["negative"]}.get(
        conf, P["text_dim"])
    return (f'<span style="display:inline-block;color:{tone};font-size:9px;'
            f'font-weight:700;letter-spacing:0.05em;text-transform:uppercase">'
            f'{_html.escape(conf or "—")}</span>')


def _fmt_size(v: str, unit: str) -> str:
    """Market-size cell: $M collapses to $bn above 1,000; counts get commas."""
    try:
        n = float(v)
    except (TypeError, ValueError):
        return _html.escape(str(v or "—"))
    u = (unit or "").strip()
    if u.startswith("USD millions"):
        tail = u[len("USD millions"):].strip()
        body = f"${n/1000:,.2f}bn" if n >= 1000 else f"${n:,.0f}M"
        return f"{body} {_html.escape(tail)}".strip()
    return f"{n:,.0f} {_html.escape(u)}".strip()


def _hbar(label: str, value: float, vmax: float, *, suffix: str = "",
          tone: Optional[str] = None) -> str:
    """One diverging horizontal bar. Negative values render in the negative
    palette and grow leftward-equivalent (width by |value|)."""
    pct = 0.0 if vmax <= 0 else min(abs(value) / vmax, 1.0) * 100
    color = tone or (P["negative"] if value < 0 else P["positive"])
    val_txt = f"{value:+.1f}{suffix}" if suffix == "%" else f"{value:,.0f}{suffix}"
    return (
        f'<div style="display:flex;align-items:center;gap:10px;margin:3px 0">'
        f'<div style="flex:0 0 220px;font-size:12px;color:{P["text"]}">{_html.escape(label)}</div>'
        f'<div style="flex:1;background:{P["panel_alt"]};border-radius:3px;height:16px">'
        f'<div style="width:{pct:.1f}%;background:{color};height:16px;border-radius:3px"></div></div>'
        f'<div style="flex:0 0 70px;text-align:right;font-variant-numeric:tabular-nums;'
        f'font-size:12px;color:{P["text"]}">{val_txt}</div></div>')


def _panel(title: str, inner: str) -> str:
    cell = f"background:{P['panel']};border:1px solid {P['border']};padding:16px;margin-bottom:16px"
    h3 = (f"font-family:var(--sc-sans);font-size:11px;font-weight:600;"
          f"letter-spacing:0.08em;color:{P['text_dim']};text-transform:uppercase;margin-bottom:10px")
    return f'<div style="{cell}"><div style="{h3}">{_html.escape(title)}</div>{inner}</div>'


# ── Index — /healthcare-verticals ───────────────────────────────────────────
def render_verticals_intel_index(params: dict = None) -> str:
    verticals = _hv.load_verticals()
    updates = _hv.load_payment_updates()
    genes = _hv.load_gene_therapy_prices()
    sources = _hv.load_sources()

    # KPI strip
    kpis = (
        ck_kpi_block("Verticals", str(len(verticals)), "Groups A–E", "")
        + ck_kpi_block("FY/CY2026 rate actions", str(len(updates)),
                       "SNF · hospice · home health · ESRD", "")
        + ck_kpi_block("Gene therapies priced", str(len(genes)), "WAC list", "")
        + ck_kpi_block("Cited data sources", str(len(sources)),
                       "federal / industry / company", ""))
    kpi_block = f'<div class="ck-kpi-grid" style="margin-bottom:16px">{kpis}</div>'

    # Payment-update bar chart (diverging — home health is negative).
    upd_rows = []
    vmax = 0.0
    for u in updates:
        try:
            vmax = max(vmax, abs(float(u["net_update_pct"])))
        except (TypeError, ValueError, KeyError):
            pass
    for u in updates:
        try:
            val = float(u["net_update_pct"])
        except (TypeError, ValueError, KeyError):
            continue
        upd_rows.append(_hbar(f'{u.get("setting","")} ({u.get("fiscal_period","")})',
                              val, vmax, suffix="%"))
    upd_panel = _panel("FY/CY2026 net payment updates", "".join(upd_rows)) if upd_rows else ""

    # Grouped tables A→E.
    by_group: Dict[str, List[dict]] = {}
    for v in verticals:
        by_group.setdefault(v.get("group", "?"), []).append(v)

    sections = ""
    for g in sorted(by_group):
        rows = ""
        for v in by_group[g]:
            vid = v.get("vertical_id", "")
            rows += (
                f'<tr style="border-bottom:1px solid {P["border"]}">'
                f'<td style="padding:9px 12px"><a href="/healthcare-verticals/{_html.escape(vid)}" '
                f'style="color:{P["accent"]};font-weight:600;text-decoration:none">'
                f'{_html.escape(v.get("vertical_name",""))}</a></td>'
                f'<td style="padding:9px 12px;font-size:11px;color:{P["text_dim"]}">{_html.escape(v.get("payment_system",""))}</td>'
                f'<td style="padding:9px 12px;font-size:11px;color:{P["text_dim"]};font-variant-numeric:tabular-nums">{_fmt_size(v.get("market_size",""), v.get("market_size_unit",""))}</td>'
                f'<td style="padding:9px 12px;font-size:11px;color:{P["text_dim"]}">{_html.escape(v.get("primary_payer",""))}</td>'
                f'<td style="padding:9px 12px;font-size:11px;color:{P["text_dim"]}">{_html.escape(v.get("consolidation",""))}</td>'
                f'</tr>')
        table = (
            f'<table style="width:100%;border-collapse:collapse;background:{P["panel"]};'
            f'border:1px solid {P["border"]};margin-bottom:6px"><thead>'
            f'<tr style="border-bottom:2px solid {P["border"]};text-align:left;color:{P["text_dim"]};font-size:10px;text-transform:uppercase">'
            f'<th style="padding:8px 12px">Vertical</th><th style="padding:8px 12px">Payment system</th>'
            f'<th style="padding:8px 12px">Market size</th><th style="padding:8px 12px">Primary payer</th>'
            f'<th style="padding:8px 12px">Structure</th></tr></thead><tbody>{rows}</tbody></table>')
        label = _hv.GROUPS.get(g, g)
        sections += (
            f'<h3 style="font-family:var(--sc-sans);font-size:12px;font-weight:700;'
            f'letter-spacing:0.06em;color:{P["text"]};text-transform:uppercase;'
            f'margin:18px 0 8px">Group {_html.escape(g)} · {_html.escape(label)}</h3>{table}')

    body = (
        ck_page_title("Healthcare Verticals 2025–2026", eyebrow="RESEARCH · VERTICALS",
                      meta=f"{len(verticals)} specialized, adjacent & emerging US healthcare "
                           f"verticals · public-source synthesis")
        + ck_source_purpose(
            purpose="Frame the 17 specialized/adjacent/emerging healthcare "
                    "verticals: payment system, market size, structure, and the "
                    "FY/CY2026 rate environment — chart-ready for a sector thesis.",
            universe="public-source-synthesis", confidence="mixed",
            source=_hv.ATTRIBUTION + ". Industry-level, not provider-specific; "
                   "ranges kept as ranges; figures flagged unverifiable marked low-confidence.",
            next_action="Open a vertical for its payment economics, unit economics, and sources")
        + f'<p style="margin:6px 0 16px">{_SYNTH_CHIP}</p>'
        + kpi_block + upd_panel + sections)
    return chartis_shell(body, "Healthcare Verticals", active_nav="/healthcare-verticals",
                         editorial_intro={
                             "eyebrow": "HEALTHCARE VERTICALS 2025–2026",
                             "headline": "Seventeen verticals, one chart-ready reference.",
                             "italic_word": "chart-ready",
                             "body": "A public-source synthesis of the specialized, adjacent and "
                                     "emerging US healthcare verticals — CMS rate rules, market "
                                     "structure, and per-unit economics, every figure sourced."})


# ── Detail — /healthcare-verticals/<vertical_id> ────────────────────────────
def render_vertical_intel(vertical_id: str, params: dict = None) -> str:
    v = _hv.vertical_by_id(vertical_id)
    if not v:
        body = ck_page_title("Vertical not found", eyebrow="RESEARCH · VERTICALS") + \
            f'<p style="color:{P["text_dim"]}">No vertical "{_html.escape(str(vertical_id))}". ' \
            f'<a href="/healthcare-verticals" style="color:{P["accent"]}">Back to Healthcare Verticals</a>.</p>'
        return chartis_shell(body, "Vertical", active_nav="/healthcare-verticals")

    vid = v["vertical_id"]
    group_label = _hv.GROUPS.get(v.get("group", ""), v.get("group", ""))

    # KPIs
    kpis = (
        ck_kpi_block("Market size", _fmt_size(v.get("market_size",""), v.get("market_size_unit","")),
                     f'as of {_html.escape(v.get("market_size_year","") or "—")}', "")
        + ck_kpi_block("Primary payer", _html.escape(v.get("primary_payer","—")), "", "")
        + ck_kpi_block("Structure", _html.escape(v.get("consolidation","—")), "", ""))
    kpi_block = f'<div class="ck-kpi-grid" style="margin-bottom:16px">{kpis}</div>'

    panels = ""

    # Definition / payment mechanics
    notes = v.get("notes", "")
    prose = f"font-family:var(--sc-serif);font-size:14px;line-height:1.65;color:{P['text']};margin:0"
    panels += _panel(
        "Payment system & mechanics",
        f'<p style="{prose}"><b>{_html.escape(v.get("payment_system",""))}</b> · '
        f'unit: {_html.escape(v.get("payment_unit","—"))}.'
        + (f' {_html.escape(notes)}' if notes else "") + '</p>')

    # FY/CY2026 payment update + build-up waterfall
    upd = _hv.load_payment_updates(vid)
    buildup = _hv.load_payment_buildup(vid)
    if upd or buildup:
        inner = ""
        for u in upd:
            try:
                val = float(u["net_update_pct"])
                inner += _hbar(f'Net update · {u.get("fiscal_period","")} ({u.get("rule_id","")})',
                               val, abs(val) or 1, suffix="%")
            except (TypeError, ValueError, KeyError):
                pass
        if buildup:
            comps = [b for b in buildup if b.get("is_total") not in ("1", 1)]
            vmax = max((abs(float(b.get("value_pct") or 0)) for b in comps), default=1) or 1
            for b in comps:
                try:
                    inner += _hbar(_html.escape(b.get("component","")),
                                   float(b["value_pct"]), vmax, suffix="%")
                except (TypeError, ValueError, KeyError):
                    pass
        panels += _panel("FY/CY2026 payment update — rate build-up", inner)

    # Unit economics
    ue = _hv.load_unit_economics(vid)
    if ue:
        rows = ""
        for r in ue:
            lo, hi = r.get("value_low",""), r.get("value_high","")
            try:
                rng = f"{float(lo):,.2f}" if lo == hi else f"{float(lo):,.2f} – {float(hi):,.2f}"
            except (TypeError, ValueError):
                rng = _html.escape(f"{lo}–{hi}")
            rows += (f'<tr><td style="padding:4px 10px">{_html.escape(r.get("unit_label",""))}</td>'
                     f'<td style="padding:4px 10px;text-align:right;font-variant-numeric:tabular-nums">{rng} {_html.escape(r.get("unit",""))}</td>'
                     f'<td style="padding:4px 10px;text-align:right">{_conf_chip(r.get("confidence",""))}</td></tr>')
        panels += _panel("Unit economics",
                         f'<table style="width:100%;border-collapse:collapse;font-size:12px">'
                         f'<tbody>{rows}</tbody></table>')

    # Gene-therapy price table (cell & gene therapy only)
    if vid == "cell_gene_therapy":
        genes = _hv.load_gene_therapy_prices()
        grows = ""
        for g in genes:
            try:
                price = f"${float(g['list_price_usd'])/1e6:,.2f}M"
            except (TypeError, ValueError, KeyError):
                price = _html.escape(str(g.get("list_price_usd","—")))
            grows += (f'<tr><td style="padding:4px 10px">{_html.escape(g.get("therapy",""))}</td>'
                      f'<td style="padding:4px 10px;color:{P["text_dim"]}">{_html.escape(g.get("indication",""))}</td>'
                      f'<td style="padding:4px 10px;color:{P["text_dim"]};font-size:11px">{_html.escape(g.get("platform",""))}</td>'
                      f'<td style="padding:4px 10px;text-align:right;font-variant-numeric:tabular-nums">{price}</td></tr>')
        panels += _panel("Cell & gene therapy — WAC list prices (descending)",
                         f'<table style="width:100%;border-collapse:collapse;font-size:12px"><thead>'
                         f'<tr style="color:{P["text_dim"]};text-align:left;border-bottom:1px solid {P["border"]}">'
                         f'<th style="padding:4px 10px">Therapy</th><th style="padding:4px 10px">Indication</th>'
                         f'<th style="padding:4px 10px">Platform</th><th style="padding:4px 10px;text-align:right">List price</th>'
                         f'</tr></thead><tbody>{grows}</tbody></table>')

    # Market structure
    ms = _hv.load_market_structure(vid)
    if ms:
        rows = ""
        for m in ms:
            share = m.get("combined_share_pct","")
            share_txt = f'{float(share):.1f}%' if share not in ("", None) and _is_num(share) else "—"
            rows += (f'<tr><td style="padding:4px 10px">{_html.escape(m.get("leaders",""))}</td>'
                     f'<td style="padding:4px 10px;text-align:right;font-variant-numeric:tabular-nums">{share_txt}</td>'
                     f'<td style="padding:4px 10px;color:{P["text_dim"]};font-size:11px">{_html.escape(m.get("share_basis",""))}</td></tr>')
        panels += _panel("Market structure & concentration",
                         f'<table style="width:100%;border-collapse:collapse;font-size:12px">'
                         f'<tbody>{rows}</tbody></table>')

    # Workforce
    wf = _hv.load_workforce(vid)
    if wf:
        rows = "".join(
            f'<tr><td style="padding:4px 10px">{_html.escape(w.get("metric",""))}</td>'
            f'<td style="padding:4px 10px;text-align:right;font-variant-numeric:tabular-nums">{_html.escape(str(w.get("value","")))} {_html.escape(w.get("unit",""))}</td>'
            f'<td style="padding:4px 10px;color:{P["text_dim"]};font-size:11px">{_html.escape(w.get("as_of",""))}</td></tr>'
            for w in wf)
        panels += _panel("Workforce", f'<table style="width:100%;border-collapse:collapse;font-size:12px"><tbody>{rows}</tbody></table>')

    # Sources
    srcs = _hv.load_sources(vid)
    if srcs:
        items = "".join(
            f'<li style="margin-bottom:3px">{_html.escape(s.get("source",""))} '
            f'<span style="color:{P["text_dim"]};font-size:11px">· {_html.escape(s.get("source_type",""))}</span></li>'
            for s in srcs)
        panels += _panel("Data sources",
                         f'<ul style="margin:0;padding-left:18px;font-size:12px;line-height:1.6">{items}</ul>')

    body = (
        ck_page_title(v.get("vertical_name",""), eyebrow="RESEARCH · VERTICALS",
                      meta=f'Group {v.get("group","")} · {_html.escape(group_label)} · '
                           f'<a href="/healthcare-verticals" style="color:inherit">all verticals</a>')
        + ck_source_purpose(
            purpose="Payment economics, unit economics, market structure and "
                    "workforce for this vertical — sourced and chart-ready.",
            universe="public-source-synthesis", confidence="mixed",
            source=_hv.ATTRIBUTION + ". Industry-level, not provider-specific.",
            next_action="Cross-check the per-unit economics against the target's own financials")
        + f'<p style="margin:6px 0 16px">{_SYNTH_CHIP} '
        + f'<span style="margin-left:10px;color:{P["text_dim"]};font-size:11px;'
        + f'text-transform:uppercase;letter-spacing:0.05em">confidence</span> '
        + f'{_conf_chip(_overall_conf(vid))}</p>'
        + kpi_block + panels)
    return chartis_shell(body, v.get("vertical_name",""), active_nav="/healthcare-verticals")


def _is_num(x) -> bool:
    try:
        float(x)
        return True
    except (TypeError, ValueError):
        return False


def _overall_conf(vertical_id: str) -> str:
    v = _hv.vertical_by_id(vertical_id)
    return (v or {}).get("confidence", "mixed")
