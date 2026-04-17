"""GP Benchmarking — compare a specific GP's portfolio performance vs corpus peers.

User selects/inputs a GP name; system shows their corpus deals, compares
MOIC/IRR/sector mix vs corpus and sector peers. Useful for LP due diligence.
"""
from __future__ import annotations

import html
import importlib
import re
from collections import defaultdict
from typing import Any, Dict, List, Optional


def _load_corpus() -> List[Dict[str, Any]]:
    from rcm_mc.data_public.deals_corpus import _SEED_DEALS
    deals: List[Dict[str, Any]] = list(_SEED_DEALS)
    for i in range(2, 40):
        try:
            mod = importlib.import_module(f"rcm_mc.data_public.extended_seed_{i}")
            key = f"EXTENDED_SEED_DEALS_{i}"
            deals += getattr(mod, key, [])
        except Exception:
            pass
    return deals


from rcm_mc.ui._chartis_kit import P, _MONO, _SANS, chartis_shell, ck_section_header


def _normalize(buyer: str) -> str:
    if not buyer:
        return ""
    primary = re.split(r"[/;]", buyer)[0].strip()
    primary = re.sub(r"\s+(Fund|PE|Partners|Capital|Growth)?\s*(X{0,3})(I{0,3}|IV|VI{0,3}|IX|X{0,3})\b", "", primary, flags=re.I).strip()
    return re.sub(r"\s+[IVXLC]+$", "", primary).strip() or buyer


def _percentile(vals: List[float], p: float) -> Optional[float]:
    if not vals:
        return None
    s = sorted(vals)
    idx = (len(s) - 1) * p / 100
    lo, hi = int(idx), min(int(idx) + 1, len(s) - 1)
    return s[lo] + (s[hi] - s[lo]) * (idx - lo)


def _pct_rank(val: float, vals: List[float]) -> float:
    if not vals:
        return 50.0
    return round(sum(1 for v in vals if v < val) / len(vals) * 100, 1)


def _input_form(params: Dict[str, str], gps: List[str]) -> str:
    def v(k: str, d: str = "") -> str:
        return html.escape(params.get(k, d))

    gp_opts = "".join(
        f'<option value="{html.escape(g)}" {"selected" if v("gp") == g else ""}>{html.escape(g)}</option>'
        for g in [""] + sorted(gps)
    )

    return f"""<form method="GET" action="/gp-benchmarking" style="display:grid;grid-template-columns:2fr 1fr auto;gap:8px;align-items:end">
  <div>
    <label style="display:block;font-size:10px;color:{P['text_dim']};margin-bottom:3px;font-family:{_SANS}">SELECT GP / SPONSOR</label>
    <select name="gp" style="width:100%;background:{P['panel_alt']};color:{P['text']};border:1px solid {P['border']};padding:5px 8px;font-family:{_MONO};font-size:12px">{gp_opts}</select>
  </div>
  <div>
    <label style="display:block;font-size:10px;color:{P['text_dim']};margin-bottom:3px;font-family:{_SANS}">OR TYPE GP NAME</label>
    <input name="gp_text" value="{v('gp_text')}" style="width:100%;background:{P['panel_alt']};color:{P['text']};border:1px solid {P['border']};padding:5px 8px;font-family:{_MONO};font-size:12px" placeholder="e.g. KKR">
  </div>
  <div style="display:flex;align-items:flex-end">
    <button type="submit" style="background:{P['accent']};color:#fff;border:none;padding:7px 20px;font-family:{_MONO};font-size:12px;cursor:pointer">ANALYZE</button>
  </div>
</form>"""


def _gauge_svg(pct: float, label: str, w: int = 110, h: int = 70) -> str:
    import math
    cx, cy, r = w // 2, h - 8, h - 14
    angle = math.radians(180 - pct * 1.8)
    nx = cx + r * math.cos(angle)
    ny = cy - r * math.sin(angle)
    col = P["positive"] if pct >= 60 else (P["warning"] if pct >= 35 else P["negative"])
    return (
        f'<svg width="{w}" height="{h}" style="overflow:visible">'
        f'<path d="M {cx-r},{cy} A {r},{r} 0 0,1 {cx+r},{cy}" fill="none" stroke="{P["border"]}" stroke-width="7"/>'
        f'<path d="M {cx-r},{cy} A {r},{r} 0 0,1 {nx:.1f},{ny:.1f}" fill="none" stroke="{col}" stroke-width="7" stroke-linecap="butt"/>'
        f'<text x="{cx}" y="{cy-4}" fill="{col}" text-anchor="middle" font-size="15" font-family="{_MONO}" font-variant-numeric="tabular-nums">{pct:.0f}</text>'
        f'<text x="{cx}" y="{cy+10}" fill="{P["text_dim"]}" text-anchor="middle" font-size="8" font-family="{_SANS}">pctile</text>'
        f'<text x="{cx}" y="{h-1}" fill="{P["text_dim"]}" text-anchor="middle" font-size="8" font-family="{_SANS}">{html.escape(label)}</text>'
        f'</svg>'
    )


def render_gp_benchmarking(params: Dict[str, str]) -> str:
    corpus = _load_corpus()

    # get all unique GPs with 2+ deals
    gp_counts: Dict[str, int] = defaultdict(int)
    for d in corpus:
        gp = _normalize(d.get("buyer") or "")
        if gp:
            gp_counts[gp] += 1
    gps = [g for g, n in gp_counts.items() if n >= 2]

    gp_name = params.get("gp_text", "").strip() or params.get("gp", "").strip()

    result_html = ""
    if gp_name:
        gp_norm = _normalize(gp_name)
        gp_deals = [
            d for d in corpus
            if gp_norm.lower() in _normalize(d.get("buyer") or "").lower()
            or _normalize(d.get("buyer") or "").lower() in gp_norm.lower()
        ]

        if not gp_deals:
            result_html = f'<div style="padding:20px;background:{P["panel_alt"]};border:1px solid {P["warning"]};color:{P["warning"]};font-size:12px;font-family:{_SANS}">No deals found for "{html.escape(gp_name)}" in corpus. Try a partial name match.</div>'
        else:
            gp_moics = [d["realized_moic"] for d in gp_deals if d.get("realized_moic") is not None]
            gp_irrs  = [d["realized_irr"]  for d in gp_deals if d.get("realized_irr")  is not None]
            corp_moics = [d["realized_moic"] for d in corpus if d.get("realized_moic") is not None]
            corp_irrs  = [d["realized_irr"]  for d in corpus if d.get("realized_irr")  is not None]

            gp_p50  = _percentile(gp_moics, 50)
            gp_irr50 = _percentile(gp_irrs, 50)
            corp_p50 = _percentile(corp_moics, 50)
            moic_rank = _pct_rank(gp_p50 or 0, corp_moics)
            irr_rank  = _pct_rank(gp_irr50 or 0, corp_irrs) if gp_irr50 else None
            win_rate  = sum(1 for m in gp_moics if m >= 2.0) / len(gp_moics) * 100 if gp_moics else None
            loss_rate = sum(1 for m in gp_moics if m < 1.5)  / len(gp_moics) * 100 if gp_moics else None

            # sectors
            sectors: Dict[str, int] = defaultdict(int)
            for d in gp_deals:
                if d.get("sector"):
                    sectors[d["sector"]] += 1
            top_secs = sorted(sectors.items(), key=lambda x: -x[1])[:5]
            secs_str = ", ".join(f"{html.escape(s)} ({n})" for s, n in top_secs)

            # KPIs
            kpis = [
                ("DEALS IN CORPUS", str(len(gp_deals)), P["text"]),
                ("MOIC P50", f"{gp_p50:.2f}×" if gp_p50 else "—", P["positive"] if (gp_p50 or 0) >= 2.5 else P["warning"]),
                ("CORPUS MOIC P50", f"{corp_p50:.2f}×" if corp_p50 else "—", P["text_dim"]),
                ("IRR P50", f"{gp_irr50*100:.1f}%" if gp_irr50 else "—", P["text"]),
                ("WIN RATE", f"{win_rate:.0f}%" if win_rate is not None else "—", P["positive"] if (win_rate or 0) >= 60 else P["warning"]),
                ("LOSS RATE", f"{loss_rate:.0f}%" if loss_rate is not None else "—", P["negative"] if (loss_rate or 0) >= 20 else P["text"]),
            ]
            kpi_strip = "".join(
                f'<div style="background:{P["panel_alt"]};border:1px solid {P["border"]};padding:8px 12px">'
                f'<div style="font-size:9px;color:{P["text_dim"]};font-family:{_SANS};letter-spacing:.08em;margin-bottom:2px">{lbl}</div>'
                f'<div style="font-size:15px;font-family:{_MONO};color:{col};font-variant-numeric:tabular-nums">{val}</div>'
                f'</div>'
                for lbl, val, col in kpis
            )
            kpi_div = f'<div style="display:grid;grid-template-columns:repeat(6,1fr);gap:6px;margin-bottom:14px">{kpi_strip}</div>'

            # gauges
            gauges = ""
            if gp_p50 and corp_moics:
                gauges += _gauge_svg(moic_rank, "MOIC rank")
            if irr_rank is not None:
                gauges += _gauge_svg(irr_rank, "IRR rank")
            gauge_row = (
                f'<div style="display:flex;gap:20px;align-items:center;padding:10px 14px;background:{P["panel_alt"]};border:1px solid {P["border"]};margin-bottom:14px">'
                f'<div style="font-size:9px;color:{P["text_dim"]};font-family:{_SANS};writing-mode:vertical-lr;transform:rotate(180deg)">vs CORPUS</div>'
                f'{gauges}'
                f'<div style="font-size:10px;color:{P["text_faint"]};font-family:{_SANS};flex:1">Percentile rank of this GP\'s P50 MOIC vs all {len(corp_moics)} disclosed corpus returns. Higher = better.</div>'
                f'</div>'
            )

            # deal table
            rows = ""
            for i, d in enumerate(sorted(gp_deals, key=lambda x: -(x.get("realized_moic") or 0))):
                bg = P["row_stripe"] if i % 2 else P["panel"]
                moic = d.get("realized_moic")
                irr  = d.get("realized_irr")
                moic_col = P["positive"] if (moic or 0) >= 2.5 else (P["warning"] if (moic or 0) >= 2.0 else P["text"])
                rows += (
                    f'<tr style="background:{bg}">'
                    f'<td style="padding:4px 8px;font-size:11px">{html.escape(d.get("deal_name","")[:44])}</td>'
                    f'<td style="padding:4px 8px;font-size:10px;color:{P["text_dim"]}">{html.escape((d.get("sector") or "—")[:24])}</td>'
                    f'<td style="padding:4px 8px;font-size:10px;font-family:{_MONO};text-align:right;font-variant-numeric:tabular-nums">{d.get("year","—")}</td>'
                    f'<td style="padding:4px 8px;font-size:10px;font-family:{_MONO};text-align:right;font-variant-numeric:tabular-nums">{f"${d["ev_mm"]:,.0f}M" if d.get("ev_mm") else "—"}</td>'
                    f'<td style="padding:4px 8px;font-size:12px;font-family:{_MONO};text-align:right;font-weight:700;color:{moic_col};font-variant-numeric:tabular-nums">{f"{moic:.2f}×" if moic else "—"}</td>'
                    f'<td style="padding:4px 8px;font-size:10px;font-family:{_MONO};text-align:right;font-variant-numeric:tabular-nums">{f"{irr*100:.1f}%" if irr else "—"}</td>'
                    f'<td style="padding:4px 8px;font-size:10px;font-family:{_MONO};text-align:right;font-variant-numeric:tabular-nums">{f"{d["hold_years"]:.1f}y" if d.get("hold_years") else "—"}</td>'
                    f'</tr>'
                )

            th = f"padding:4px 8px;font-size:9px;letter-spacing:.08em;color:{P['text_dim']};font-family:{_SANS};border-bottom:1px solid {P['border']}"
            deal_table = f"""<div style="border:1px solid {P['border']};overflow-x:auto">
<table style="width:100%;border-collapse:collapse">
<thead><tr style="background:{P['panel_alt']}">
  <th style="{th}">DEAL</th><th style="{th}">SECTOR</th>
  <th style="{th};text-align:right">YEAR</th><th style="{th};text-align:right">EV</th>
  <th style="{th};text-align:right">MOIC</th><th style="{th};text-align:right">IRR</th>
  <th style="{th};text-align:right">HOLD</th>
</tr></thead><tbody>{rows}</tbody></table></div>"""

            result_html = f"""
<div style="padding:10px 14px;background:{P['panel_alt']};border:1px solid {P['border']};margin-bottom:14px">
  <span style="font-size:10px;color:{P['text_dim']};font-family:{_SANS}">SECTOR FOCUS: </span>
  <span style="font-size:10px;color:{P['text']};font-family:{_SANS}">{secs_str or "—"}</span>
</div>
{kpi_div}
{gauge_row}
<div style="font-size:9px;color:{P['text_dim']};font-family:{_SANS};letter-spacing:.1em;margin-bottom:6px;border-bottom:1px solid {P['border']};padding-bottom:4px">
  ALL CORPUS DEALS — {html.escape(gp_name)} (SORTED BY MOIC)
</div>
{deal_table}"""

    empty_msg = "" if gp_name else f'<div style="background:{P["panel_alt"]};border:1px solid {P["border"]};padding:24px;text-align:center"><div style="font-size:12px;color:{P["text_dim"]};font-family:{_SANS}">Select a GP from the dropdown or type a name to view their corpus performance.</div></div>'

    body = f"""
<div style="padding:16px 20px;max-width:1200px">
  {ck_section_header("GP BENCHMARKING", f"Sponsor performance vs corpus peers — {len(corpus):,} transactions", None)}
  <div style="background:{P['panel']};border:1px solid {P['border']};padding:14px;margin-bottom:16px">
    {_input_form(params, gps)}
  </div>
  {empty_msg}
  {result_html}
</div>"""

    title = f"GP Benchmarking — {html.escape(gp_name)}" if gp_name else "GP Benchmarking"
    return chartis_shell(body, title, active_nav="/gp-benchmarking",
                         subtitle=f"{len(gps)} GPs in corpus")
