"""Comparable Deal Finder — find corpus matches for a target deal.

User inputs deal characteristics; system returns ranked corpus comparables
with similarity scores, percentile ranks, and a summary benchmark block.
More focused than the IC Memo Generator — purely on peer identification.
"""
from __future__ import annotations

import html
import importlib
import math
from typing import Any, Dict, List, Optional, Tuple


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
from rcm_mc.ui.chartis._helpers import render_page_explainer


def _percentile_rank(val: float, vals: List[float]) -> float:
    if not vals:
        return 50.0
    return round(sum(1 for v in vals if v < val) / len(vals) * 100, 1)


def _percentile(vals: List[float], p: float) -> Optional[float]:
    if not vals:
        return None
    s = sorted(vals)
    idx = (len(s) - 1) * p / 100
    lo, hi = int(idx), min(int(idx) + 1, len(s) - 1)
    return s[lo] + (s[hi] - s[lo]) * (idx - lo)


def _ev_ebitda(d: Dict) -> Optional[float]:
    ev = d.get("ev_mm")
    eb = d.get("ebitda_at_entry_mm") or d.get("ebitda_mm")
    if ev and eb and eb > 0:
        return ev / eb
    stored = d.get("ev_ebitda")
    return stored if stored and stored > 0 else None


def _comm_pct(d: Dict) -> Optional[float]:
    pm = d.get("payer_mix")
    if isinstance(pm, dict):
        return pm.get("commercial")
    return None


def _similarity_score(
    d: Dict,
    sector: Optional[str],
    ev_mm: Optional[float],
    ev_ebitda_val: Optional[float],
    comm_pct: Optional[float],
    year: Optional[int],
) -> float:
    score = 0.0

    # sector match (highest weight)
    d_sector = d.get("sector")
    if sector and d_sector:
        if sector.lower() == d_sector.lower():
            score += 45
        elif sector.lower() in d_sector.lower() or d_sector.lower() in sector.lower():
            score += 22

    # EV size similarity
    d_ev = d.get("ev_mm")
    if ev_mm and d_ev:
        ratio = min(ev_mm, d_ev) / max(ev_mm, d_ev)
        score += 25 * ratio

    # EV/EBITDA similarity
    d_mult = _ev_ebitda(d)
    if ev_ebitda_val and d_mult:
        diff = abs(ev_ebitda_val - d_mult)
        score += max(0, 15 - diff * 2)

    # commercial payer similarity
    d_comm = _comm_pct(d)
    if comm_pct is not None and d_comm is not None:
        diff = abs(comm_pct - d_comm)
        score += max(0, 10 - diff * 20)

    # vintage proximity (within 5 years)
    d_yr = d.get("year")
    if year and d_yr:
        diff = abs(year - d_yr)
        score += max(0, 5 - diff)

    return score


_SECTOR_OPTIONS = [
    "", "Acute Care / Hospital", "Ambulatory Surgery Center",
    "Autism / ABA Therapy", "Behavioral Health",
    "Cardiology", "Clinical Research / CRO",
    "Dental / DSO", "Dermatology", "Dialysis",
    "Digital Health Platforms", "Digital Therapeutics",
    "Emergency Medicine / EMS", "Fertility / Reproductive",
    "Gastroenterology", "GI / Endoscopy",
    "Health IT / RCM SaaS", "Hearing Health / Audiology",
    "Home Health / Hospice", "Hospitalist / IPC",
    "Infusion Therapy", "Kidney Care / ESRD",
    "Lab / Diagnostics", "Managed Care / Health Plan",
    "Medicare Advantage Health Plans",
    "Medical Staffing / Locum Tenens",
    "Musculoskeletal / Orthopedics",
    "Neonatal / Neonatology", "Nephrology",
    "Neurology", "Oncology", "Ophthalmology",
    "Orthopedics / MSK", "Palliative Care / Hospice",
    "Pediatrics / NICU", "Pharmacy Benefit Management (PBM)",
    "Physical Therapy / Rehab", "Post-Acute / SNF",
    "Primary Care / VBC", "Psychiatry / Mental Health",
    "Radiation Oncology", "Radiology / Imaging",
    "Rural Health", "Sleep Medicine",
    "Specialty Pharmacy", "Stroke / Neurovascular Care",
    "Substance Abuse / SUD", "Telehealth",
    "Urgent Care", "Vision Care", "Women's Health",
    "Workers' Compensation Managed Care", "Wound Care",
]


def _input_css() -> str:
    return (
        f"width:100%;background:{P['panel_alt']};color:{P['text']};"
        f"border:1px solid {P['border']};padding:5px 8px;"
        f"font-family:{_MONO};font-size:12px;font-variant-numeric:tabular-nums;"
    )


def _input_form(params: Dict[str, str], n_corpus: int) -> str:
    def v(k: str, d: str = "") -> str:
        return html.escape(params.get(k, d))

    sector_opts = "".join(
        f'<option value="{html.escape(s)}" {"selected" if v("sector") == s else ""}>{html.escape(s) or "— Any sector —"}</option>'
        for s in _SECTOR_OPTIONS
    )
    n_opts = "".join(
        f'<option value="{n}" {"selected" if v("max_comps","15")==str(n) else ""}>{n} comps</option>'
        for n in [5, 10, 15, 20, 25]
    )

    return f"""<form method="GET" action="/find-comps" style="display:grid;grid-template-columns:repeat(4,1fr);gap:8px;align-items:end">
  <div>
    <label style="display:block;font-size:10px;color:{P['text_dim']};margin-bottom:3px;font-family:{_SANS}">SECTOR</label>
    <select name="sector" style="{_input_css()}">{sector_opts}</select>
  </div>
  <div>
    <label style="display:block;font-size:10px;color:{P['text_dim']};margin-bottom:3px;font-family:{_SANS}">EV ($M)</label>
    <input name="ev_mm" value="{v('ev_mm')}" type="number" step="1" min="0" style="{_input_css()}" placeholder="e.g. 300">
  </div>
  <div>
    <label style="display:block;font-size:10px;color:{P['text_dim']};margin-bottom:3px;font-family:{_SANS}">EV/EBITDA</label>
    <input name="ev_ebitda" value="{v('ev_ebitda')}" type="number" step="0.1" min="0" style="{_input_css()}" placeholder="e.g. 11.5">
  </div>
  <div>
    <label style="display:block;font-size:10px;color:{P['text_dim']};margin-bottom:3px;font-family:{_SANS}">COMMERCIAL PAYER %</label>
    <input name="comm_pct" value="{v('comm_pct')}" type="number" step="1" min="0" max="100" style="{_input_css()}" placeholder="e.g. 55">
  </div>
  <div>
    <label style="display:block;font-size:10px;color:{P['text_dim']};margin-bottom:3px;font-family:{_SANS}">VINTAGE YEAR</label>
    <input name="year" value="{v('year')}" type="number" step="1" min="1990" max="2030" style="{_input_css()}" placeholder="e.g. 2021">
  </div>
  <div>
    <label style="display:block;font-size:10px;color:{P['text_dim']};margin-bottom:3px;font-family:{_SANS}">MAX COMPS</label>
    <select name="max_comps" style="{_input_css()}">{n_opts}</select>
  </div>
  <div style="grid-column:span 2;display:flex;align-items:flex-end;gap:8px">
    <button type="submit" style="background:{P['accent']};color:#fff;border:none;padding:7px 24px;font-family:{_MONO};font-size:12px;cursor:pointer;letter-spacing:.05em">FIND COMPS</button>
    <a href="/find-comps" style="font-size:11px;color:{P['text_dim']};font-family:{_SANS};text-decoration:none;padding:7px 12px;border:1px solid {P['border']}">CLEAR</a>
    <span style="font-size:10px;color:{P['text_faint']};font-family:{_SANS};margin-left:4px">Corpus: {n_corpus:,} deals</span>
  </div>
</form>"""


def _comp_row(i: int, d: Dict, sim: float, corpus_moic_p50: Optional[float]) -> str:
    bg = P["row_stripe"] if i % 2 else P["panel"]
    name = html.escape(d.get("deal_name", "")[:44])
    sector = html.escape((d.get("sector") or "—")[:28])
    buyer = html.escape((d.get("buyer") or "—")[:30])
    yr = str(d.get("year") or "—")
    ev = d.get("ev_mm")
    ev_str = f"${ev:,.0f}M" if ev else "—"
    mult = _ev_ebitda(d)
    mult_str = f"{mult:.1f}×" if mult else "—"
    moic = d.get("realized_moic")
    irr  = d.get("realized_irr")
    hold = d.get("hold_years")
    moic_str = f"{moic:.2f}×" if moic else "—"
    irr_str  = f"{irr*100:.1f}%" if irr else "—"
    hold_str = f"{hold:.1f}y" if hold else "—"
    moic_col = P["positive"] if (moic or 0) >= 2.5 else (P["warning"] if (moic or 0) >= 2.0 else P["text"])
    pm = d.get("payer_mix")
    comm_s = f"{pm.get('commercial',0)*100:.0f}%" if isinstance(pm, dict) else "—"

    # similarity bar
    sim_bar_w = int(min(sim / 85.0, 1.0) * 60)
    sim_bar = f'<svg width="60" height="10" style="vertical-align:middle"><rect x="0" y="3" width="60" height="4" fill="{P["panel"]}"/><rect x="0" y="3" width="{sim_bar_w}" height="4" fill="{P["accent"]}"/></svg><span style="font-size:9px;font-family:{_MONO};color:{P["text_dim"]};margin-left:3px">{sim:.0f}</span>'

    return (
        f'<tr style="background:{bg}">'
        f'<td style="padding:5px 8px;font-size:10px;font-family:{_MONO};color:{P["text_faint"]};font-variant-numeric:tabular-nums">#{i+1}</td>'
        f'<td style="padding:5px 8px;font-size:11px;white-space:nowrap">{name}</td>'
        f'<td style="padding:5px 8px;font-size:10px;color:{P["text_dim"]}">{sector}</td>'
        f'<td style="padding:5px 8px;font-size:10px;color:{P["text_dim"]}">{buyer[:24]}</td>'
        f'<td style="padding:5px 8px;font-size:10px;font-family:{_MONO};text-align:right;font-variant-numeric:tabular-nums">{yr}</td>'
        f'<td style="padding:5px 8px;font-size:10px;font-family:{_MONO};text-align:right;font-variant-numeric:tabular-nums">{ev_str}</td>'
        f'<td style="padding:5px 8px;font-size:10px;font-family:{_MONO};text-align:right;font-variant-numeric:tabular-nums">{mult_str}</td>'
        f'<td style="padding:5px 8px;font-size:12px;font-family:{_MONO};text-align:right;font-weight:700;color:{moic_col};font-variant-numeric:tabular-nums">{moic_str}</td>'
        f'<td style="padding:5px 8px;font-size:10px;font-family:{_MONO};text-align:right;font-variant-numeric:tabular-nums">{irr_str}</td>'
        f'<td style="padding:5px 8px;font-size:10px;font-family:{_MONO};text-align:right;font-variant-numeric:tabular-nums">{hold_str}</td>'
        f'<td style="padding:5px 8px;font-size:10px;font-family:{_MONO};text-align:right;font-variant-numeric:tabular-nums">{comm_s}</td>'
        f'<td style="padding:5px 8px">{sim_bar}</td>'
        f'</tr>'
    )


def _benchmark_strip(comps: List[Dict], corpus: List[Dict]) -> str:
    """KPI strip showing peer median vs corpus median."""
    peer_moics = [d["realized_moic"] for d in comps if d.get("realized_moic") is not None]
    peer_irrs  = [d["realized_irr"]  for d in comps if d.get("realized_irr")  is not None]
    peer_mults = [_ev_ebitda(d) for d in comps if _ev_ebitda(d) is not None]
    corp_moics = [d["realized_moic"] for d in corpus if d.get("realized_moic") is not None]

    peer_moic_p50 = _percentile(peer_moics, 50)
    corp_moic_p50 = _percentile(corp_moics, 50)
    peer_irr_p50  = _percentile(peer_irrs, 50)
    peer_mult_p50 = _percentile(peer_mults, 50)

    vs_corpus = ""
    if peer_moic_p50 and corp_moic_p50:
        diff = peer_moic_p50 - corp_moic_p50
        col = P["positive"] if diff > 0 else P["negative"]
        vs_corpus = f'<span style="font-size:9px;color:{col};margin-left:4px">{"+" if diff > 0 else ""}{diff:.2f}× vs corpus</span>'

    kpis = [
        ("PEER COUNT",     str(len(comps)),                                   P["text"]),
        ("PEER MOIC P50",  f"{peer_moic_p50:.2f}×" if peer_moic_p50 else "—", P["positive"] if (peer_moic_p50 or 0) >= 2.5 else P["warning"]),
        ("CORPUS MOIC P50",f"{corp_moic_p50:.2f}×" if corp_moic_p50 else "—", P["text_dim"]),
        ("PEER IRR P50",   f"{peer_irr_p50*100:.1f}%" if peer_irr_p50 else "—", P["text"]),
        ("PEER MULT P50",  f"{peer_mult_p50:.1f}×"   if peer_mult_p50 else "—", P["text"]),
    ]

    items = "".join(
        f'<div style="background:{P["panel_alt"]};border:1px solid {P["border"]};padding:7px 12px">'
        f'<div style="font-size:9px;color:{P["text_dim"]};font-family:{_SANS};letter-spacing:.08em;margin-bottom:2px">{lbl}</div>'
        f'<div style="font-size:14px;font-family:{_MONO};color:{col};font-variant-numeric:tabular-nums">{val}</div>'
        f'</div>'
        for lbl, val, col in kpis
    )
    return f'<div style="display:grid;grid-template-columns:repeat(5,1fr);gap:6px;margin-bottom:14px">{items}{vs_corpus}</div>'


def render_find_comps(params: Dict[str, str]) -> str:
    corpus = _load_corpus()

    def _flt(k: str) -> Optional[float]:
        try:
            return float(params[k]) if params.get(k, "").strip() else None
        except (ValueError, TypeError):
            return None

    sector = params.get("sector", "").strip() or None
    ev_mm  = _flt("ev_mm")
    ev_ebitda_val = _flt("ev_ebitda")
    comm_raw = _flt("comm_pct")
    comm_pct = comm_raw / 100 if comm_raw is not None else None
    year = int(_flt("year") or 0) or None
    try:
        max_comps = min(25, max(5, int(params.get("max_comps", "15"))))
    except (ValueError, TypeError):
        max_comps = 15

    has_inputs = any(x is not None for x in [sector, ev_mm, ev_ebitda_val, comm_pct, year])

    result_html = ""
    if has_inputs:
        scored: List[Tuple[float, Dict]] = []
        for d in corpus:
            sim = _similarity_score(d, sector, ev_mm, ev_ebitda_val, comm_pct, year)
            if sim > 0:
                scored.append((sim, d))
        scored.sort(key=lambda x: -x[0])

        comps = [d for _, d in scored[:max_comps]]
        scores = {id(d): sim for sim, d in scored[:max_comps]}

        benchmark = _benchmark_strip(comps, corpus)

        th = (
            f"padding:4px 8px;font-size:9px;letter-spacing:.08em;"
            f"color:{P['text_dim']};font-family:{_SANS};font-weight:600;"
            f"border-bottom:2px solid {P['border']};white-space:nowrap;"
            f"position:sticky;top:0;background:{P['panel_alt']}"
        )
        header = f"""<tr style="background:{P['panel_alt']}">
  <th style="{th}">RANK</th>
  <th style="{th}">DEAL</th>
  <th style="{th}">SECTOR</th>
  <th style="{th}">BUYER</th>
  <th style="{th};text-align:right">YEAR</th>
  <th style="{th};text-align:right">EV</th>
  <th style="{th};text-align:right">EV/EBITDA</th>
  <th style="{th};text-align:right">MOIC</th>
  <th style="{th};text-align:right">IRR</th>
  <th style="{th};text-align:right">HOLD</th>
  <th style="{th};text-align:right">COMM%</th>
  <th style="{th}">SIMILARITY</th>
</tr>"""

        rows = "".join(_comp_row(i, d, scores[id(d)], None) for i, d in enumerate(comps))

        if not comps:
            rows = f'<tr><td colspan="12" style="padding:20px;text-align:center;color:{P["text_dim"]};font-size:12px">No comparables found. Try broadening the sector or removing some filters.</td></tr>'

        result_html = f"""
{benchmark}
<div style="overflow-x:auto;border:1px solid {P['border']}">
  <table style="width:100%;border-collapse:collapse;min-width:1000px">
    <thead>{header}</thead>
    <tbody>{rows}</tbody>
  </table>
</div>
<div style="margin-top:6px;font-size:10px;color:{P['text_faint']};font-family:{_SANS}">
  Similarity score: sector match (45pts) + EV proximity (25pts) + EV/EBITDA (15pts) + payer mix (10pts) + vintage (5pts).
  {len(scored)} deals scored; showing top {len(comps)}.
</div>"""

    empty_msg = "" if has_inputs else f"""
<div style="background:{P['panel_alt']};border:1px solid {P['border']};padding:24px;text-align:center;margin-bottom:16px">
  <div style="font-size:12px;color:{P['text_dim']};font-family:{_SANS}">Enter one or more deal characteristics above to find corpus comparables.</div>
  <div style="font-size:10px;color:{P['text_faint']};font-family:{_SANS};margin-top:6px">Matches ranked by weighted similarity across sector, size, multiple, payer mix, and vintage.</div>
</div>"""

    n = len(corpus)
    body = f"""
<div style="padding:16px 20px;max-width:1400px">
  {ck_section_header("COMPARABLE DEAL FINDER", f"Corpus-ranked peer identification — {n:,} transactions", None)}
  <div style="background:{P['panel']};border:1px solid {P['border']};padding:14px;margin-bottom:16px">
    <div style="font-size:9px;color:{P['text_dim']};font-family:{_SANS};letter-spacing:.08em;margin-bottom:10px">SEARCH PARAMETERS</div>
    {_input_form(params, n)}
  </div>
  {empty_msg}
  {result_html}
</div>"""

    explainer = render_page_explainer(
        what=(
            "Takes target-deal inputs (sector, size, payer mix, hold, "
            "thesis) and returns the closest corpus comparables ranked "
            "by composite similarity score, with percentile ranks and "
            "a summary benchmark block. More focused than the IC-Memo "
            "generator — purely peer identification."
        ),
        source="data_public/find_comps.py (similarity scoring).",
        page_key="find-comps",
    )
    subtitle = f"Searching {n:,} deals" if has_inputs else "Find deal comparables"
    return chartis_shell(explainer + body, "Find Comps", active_nav="/find-comps", subtitle=subtitle)
