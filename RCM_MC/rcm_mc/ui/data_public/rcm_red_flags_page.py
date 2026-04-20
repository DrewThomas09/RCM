"""RCM Red Flag Detector — corpus-driven risk factors for healthcare PE deals.

Analyzes the corpus for characteristics statistically associated with
sub-threshold returns (MOIC < 2.0×) and presents them as a scored
risk checklist for a target deal. Also shows base rates per risk factor.
"""
from __future__ import annotations

import html
import importlib
import math
from collections import defaultdict
from typing import Any, Dict, List, Optional, Tuple


def _load_corpus() -> List[Dict[str, Any]]:
    from rcm_mc.data_public.deals_corpus import _SEED_DEALS
    deals: List[Dict[str, Any]] = list(_SEED_DEALS)
    for i in range(2, 41):
        try:
            mod = importlib.import_module(f"rcm_mc.data_public.extended_seed_{i}")
            key = f"EXTENDED_SEED_DEALS_{i}"
            deals += getattr(mod, key, [])
        except Exception:
            pass
    return deals


from rcm_mc.ui._chartis_kit import P, _MONO, _SANS, chartis_shell, ck_section_header


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


def _gov_pct(d: Dict) -> Optional[float]:
    pm = d.get("payer_mix")
    if isinstance(pm, dict):
        return (pm.get("medicare", 0) + pm.get("medicaid", 0))
    return None


# ---------------------------------------------------------------------------
# Risk factor definitions
# ---------------------------------------------------------------------------
# Each factor: (id, label, description, test_fn(d) -> bool, risk_weight)
# test_fn returns True if the risk factor is PRESENT for this deal
# weight = contribution to composite risk score (0–100)

_RISK_FACTORS: List[Tuple[str, str, str, Any, int]] = [
    (
        "high_entry_multiple",
        "Rich Entry Multiple (EV/EBITDA ≥14×)",
        "Corpus data shows P50 MOIC declines meaningfully above 14×. High entry multiples compress return headroom.",
        lambda d: (_ev_ebitda(d) or 0) >= 14,
        20,
    ),
    (
        "very_high_entry",
        "Very Rich Entry (EV/EBITDA ≥18×)",
        "Above 18× EV/EBITDA, corpus win rate drops sharply. Less than 40% of such deals achieve 2.0× MOIC.",
        lambda d: (_ev_ebitda(d) or 0) >= 18,
        15,
    ),
    (
        "heavy_medicare",
        "Medicare-Heavy Payer Mix (≥60%)",
        "Heavy Medicare exposure creates regulatory/reimbursement risk. Corpus shows lower median MOIC for MC-heavy deals.",
        lambda d: (d.get("payer_mix", {}) if isinstance(d.get("payer_mix"), dict) else {}).get("medicare", 0) >= 0.60,
        15,
    ),
    (
        "medicaid_heavy",
        "Medicaid-Heavy Mix (≥40%)",
        "Medicaid rate cuts and state budget exposure create revenue risk. Corpus Medicaid-heavy deals average 1.8× MOIC.",
        lambda d: (d.get("payer_mix", {}) if isinstance(d.get("payer_mix"), dict) else {}).get("medicaid", 0) >= 0.40,
        15,
    ),
    (
        "low_commercial",
        "Low Commercial Mix (<25%)",
        "Commercial payer drives clean-claim rate and net revenue yield. Below 25% commercial, pricing power is limited.",
        lambda d: (_comm_pct(d) or 1) < 0.25 if isinstance(d.get("payer_mix"), dict) else False,
        10,
    ),
    (
        "long_hold",
        "Extended Hold (≥8 years)",
        "Corpus shows J-curve compression above 8 years. Deals held >8y have median MOIC below 2.0× unless exceptional.",
        lambda d: (d.get("hold_years") or 0) >= 8,
        10,
    ),
    (
        "mega_deal",
        "Mega Deal (EV ≥$5B)",
        "Large deal sizes compress IRR due to capital deployed / limited exit liquidity. Corpus mega-deal IRR P50 is ~12%.",
        lambda d: (d.get("ev_mm") or 0) >= 5000,
        10,
    ),
    (
        "pre_2010_vintage",
        "Pre-2010 Vintage",
        "Pre-ACA deals face different regulatory environment. Less relevant as comparables; ACA expansion created new dynamics.",
        lambda d: (d.get("year") or 9999) < 2010,
        5,
    ),
    (
        "no_sector",
        "Undisclosed Sector",
        "Missing sector data reduces analytical confidence and benchmark comparability.",
        lambda d: not d.get("sector"),
        5,
    ),
]


def _compute_corpus_base_rates(corpus: List[Dict]) -> List[Dict]:
    """For each risk factor, compute base rate and MOIC impact from corpus."""
    results = []
    for factor_id, label, desc, test_fn, weight in _RISK_FACTORS:
        flagged = [d for d in corpus if test_fn(d)]
        not_flagged = [d for d in corpus if not test_fn(d)]

        flagged_moics  = [d["realized_moic"] for d in flagged    if d.get("realized_moic") is not None]
        clean_moics    = [d["realized_moic"] for d in not_flagged if d.get("realized_moic") is not None]

        flagged_p50 = _percentile(flagged_moics, 50)
        clean_p50   = _percentile(clean_moics, 50)
        base_rate   = len(flagged) / len(corpus) * 100 if corpus else 0
        flagged_sub2 = sum(1 for m in flagged_moics if m < 2.0) / len(flagged_moics) * 100 if flagged_moics else None

        results.append({
            "id": factor_id,
            "label": label,
            "desc": desc,
            "weight": weight,
            "count": len(flagged),
            "base_rate": base_rate,
            "flagged_moic_p50": flagged_p50,
            "clean_moic_p50": clean_p50,
            "flagged_sub2_pct": flagged_sub2,
        })
    return results


def _input_form(params: Dict[str, str]) -> str:
    def v(k: str, d: str = "") -> str:
        return html.escape(params.get(k, d))

    return f"""<form method="GET" action="/rcm-red-flags" style="display:grid;grid-template-columns:repeat(4,1fr);gap:8px;align-items:end">
  <div>
    <label style="display:block;font-size:10px;color:{P['text_dim']};margin-bottom:3px;font-family:{_SANS}">EV ($M)</label>
    <input name="ev_mm" value="{v('ev_mm')}" type="number" step="1" min="0" style="width:100%;background:{P['panel_alt']};color:{P['text']};border:1px solid {P['border']};padding:5px 8px;font-family:{_MONO};font-size:12px" placeholder="e.g. 350">
  </div>
  <div>
    <label style="display:block;font-size:10px;color:{P['text_dim']};margin-bottom:3px;font-family:{_SANS}">EV/EBITDA</label>
    <input name="ev_ebitda" value="{v('ev_ebitda')}" type="number" step="0.1" min="0" style="width:100%;background:{P['panel_alt']};color:{P['text']};border:1px solid {P['border']};padding:5px 8px;font-family:{_MONO};font-size:12px" placeholder="e.g. 11.5">
  </div>
  <div>
    <label style="display:block;font-size:10px;color:{P['text_dim']};margin-bottom:3px;font-family:{_SANS}">HOLD YEARS</label>
    <input name="hold_years" value="{v('hold_years')}" type="number" step="0.5" min="0" style="width:100%;background:{P['panel_alt']};color:{P['text']};border:1px solid {P['border']};padding:5px 8px;font-family:{_MONO};font-size:12px" placeholder="e.g. 5">
  </div>
  <div>
    <label style="display:block;font-size:10px;color:{P['text_dim']};margin-bottom:3px;font-family:{_SANS}">MEDICARE %</label>
    <input name="medicare_pct" value="{v('medicare_pct')}" type="number" step="1" min="0" max="100" style="width:100%;background:{P['panel_alt']};color:{P['text']};border:1px solid {P['border']};padding:5px 8px;font-family:{_MONO};font-size:12px" placeholder="e.g. 40">
  </div>
  <div>
    <label style="display:block;font-size:10px;color:{P['text_dim']};margin-bottom:3px;font-family:{_SANS}">MEDICAID %</label>
    <input name="medicaid_pct" value="{v('medicaid_pct')}" type="number" step="1" min="0" max="100" style="width:100%;background:{P['panel_alt']};color:{P['text']};border:1px solid {P['border']};padding:5px 8px;font-family:{_MONO};font-size:12px" placeholder="e.g. 15">
  </div>
  <div>
    <label style="display:block;font-size:10px;color:{P['text_dim']};margin-bottom:3px;font-family:{_SANS}">COMMERCIAL %</label>
    <input name="comm_pct" value="{v('comm_pct')}" type="number" step="1" min="0" max="100" style="width:100%;background:{P['panel_alt']};color:{P['text']};border:1px solid {P['border']};padding:5px 8px;font-family:{_MONO};font-size:12px" placeholder="e.g. 45">
  </div>
  <div>
    <label style="display:block;font-size:10px;color:{P['text_dim']};margin-bottom:3px;font-family:{_SANS}">VINTAGE YEAR</label>
    <input name="year" value="{v('year')}" type="number" step="1" min="1990" max="2030" style="width:100%;background:{P['panel_alt']};color:{P['text']};border:1px solid {P['border']};padding:5px 8px;font-family:{_MONO};font-size:12px" placeholder="e.g. 2022">
  </div>
  <div style="display:flex;align-items:flex-end">
    <button type="submit" style="background:{P['accent']};color:#fff;border:none;padding:7px 24px;font-family:{_MONO};font-size:12px;cursor:pointer">SCORE DEAL</button>
  </div>
</form>"""


def _score_bar(score: int, w: int = 200) -> str:
    col = P["negative"] if score >= 60 else (P["warning"] if score >= 30 else P["positive"])
    bar_w = int(score / 100 * w)
    label = "HIGH RISK" if score >= 60 else ("MODERATE" if score >= 30 else "LOW RISK")
    return (
        f'<div style="margin:10px 0">'
        f'<svg width="{w}" height="20" style="display:block;margin-bottom:4px">'
        f'<rect x="0" y="4" width="{w}" height="12" fill="{P["panel"]}" stroke="{P["border"]}" stroke-width="1"/>'
        f'<rect x="1" y="5" width="{bar_w}" height="10" fill="{col}"/>'
        f'</svg>'
        f'<span style="font-size:13px;font-family:{_MONO};color:{col};font-weight:700">{score} / 100 — {label}</span>'
        f'</div>'
    )


def render_rcm_red_flags(params: Dict[str, str]) -> str:
    corpus = _load_corpus()
    base_rates = _compute_corpus_base_rates(corpus)

    def _flt(k: str) -> Optional[float]:
        try:
            return float(params[k]) if params.get(k, "").strip() else None
        except (ValueError, TypeError):
            return None

    ev_mm         = _flt("ev_mm")
    ev_ebitda_val = _flt("ev_ebitda")
    hold_years    = _flt("hold_years")
    medicare_raw  = _flt("medicare_pct")
    medicaid_raw  = _flt("medicaid_pct")
    comm_raw      = _flt("comm_pct")
    year_raw      = _flt("year")

    has_inputs = any(x is not None for x in [ev_mm, ev_ebitda_val, hold_years, medicare_raw, medicaid_raw, comm_raw])

    # build synthetic deal dict for scoring
    deal_dict: Dict[str, Any] = {}
    if ev_mm:               deal_dict["ev_mm"] = ev_mm
    if ev_ebitda_val:       deal_dict["ev_ebitda"] = ev_ebitda_val
    if hold_years:          deal_dict["hold_years"] = hold_years
    if year_raw:            deal_dict["year"] = int(year_raw)
    deal_dict["sector"] = "User Input"  # present to avoid no_sector flag

    if any(x is not None for x in [medicare_raw, medicaid_raw, comm_raw]):
        mc  = (medicare_raw  or 0) / 100
        mcd = (medicaid_raw  or 0) / 100
        com = (comm_raw      or 0) / 100
        sp  = max(0, 1 - mc - mcd - com)
        deal_dict["payer_mix"] = {
            "medicare": mc, "medicaid": mcd,
            "commercial": com, "self_pay": sp,
        }

    # score
    total_score = 0
    flag_results: List[Dict] = []
    for factor_id, label, desc, test_fn, weight in _RISK_FACTORS:
        triggered = test_fn(deal_dict) if has_inputs else False
        total_score += weight if triggered else 0
        flag_results.append({
            "id": factor_id,
            "label": label,
            "desc": desc,
            "weight": weight,
            "triggered": triggered,
        })

    # Risk summary section
    deal_score_html = ""
    if has_inputs:
        triggered_flags = [f for f in flag_results if f["triggered"]]
        score_bar = _score_bar(total_score)
        flag_items = "".join(
            f'<div style="display:flex;gap:10px;align-items:flex-start;padding:8px 0;border-bottom:1px solid {P["border_dim"]}">'
            f'<div style="font-size:14px;color:{"#0a8a5f" if not f["triggered"] else "#b5321e"};margin-top:1px">{"●" if f["triggered"] else "○"}</div>'
            f'<div style="flex:1">'
            f'<div style="font-size:11px;font-weight:600;color:{"#b5321e" if f["triggered"] else P["text_dim"]};font-family:{_SANS}">{html.escape(f["label"])} <span style="font-size:9px;color:{P["text_faint"]}">[{f["weight"]}pts]</span></div>'
            f'<div style="font-size:10px;color:{P["text_faint"]};font-family:{_SANS};margin-top:2px">{html.escape(f["desc"])}</div>'
            f'</div>'
            f'</div>'
            for f in flag_results
        )
        deal_score_html = f"""
<div style="background:{P['panel_alt']};border:1px solid {P['border']};padding:14px;margin-bottom:16px">
  <div style="font-size:9px;color:{P['text_dim']};font-family:{_SANS};letter-spacing:.1em;margin-bottom:8px">COMPOSITE RISK SCORE</div>
  {score_bar}
  <div style="font-size:10px;color:{P['text_faint']};font-family:{_SANS};margin-bottom:12px">{len(triggered_flags)} of {len(_RISK_FACTORS)} risk factors triggered.</div>
  <div style="font-size:9px;color:{P['text_dim']};font-family:{_SANS};letter-spacing:.1em;margin-bottom:8px;border-top:1px solid {P['border']};padding-top:8px">RISK FACTOR CHECKLIST</div>
  {flag_items}
</div>"""

    # Corpus base rates table
    br_rows = ""
    for i, factor in enumerate(base_rates):
        bg = P["row_stripe"] if i % 2 else P["panel"]
        fp50 = factor["flagged_moic_p50"]
        cp50 = factor["clean_moic_p50"]
        sub2 = factor["flagged_sub2_pct"]
        impact = ""
        if fp50 and cp50:
            diff = fp50 - cp50
            col = P["negative"] if diff < -0.3 else (P["warning"] if diff < 0 else P["positive"])
            sign = "+" if diff > 0 else ""
            impact = f'<span style="font-size:10px;font-family:{_MONO};color:{col};font-variant-numeric:tabular-nums">{sign}{diff:.2f}× vs clean</span>'
        br_rows += (
            f'<tr style="background:{bg}">'
            f'<td style="padding:4px 8px;font-size:11px">{html.escape(factor["label"])}</td>'
            f'<td style="padding:4px 8px;font-size:10px;font-family:{_MONO};text-align:right;font-variant-numeric:tabular-nums">{factor["count"]}</td>'
            f'<td style="padding:4px 8px;font-size:10px;font-family:{_MONO};text-align:right;font-variant-numeric:tabular-nums">{factor["base_rate"]:.0f}%</td>'
            f'<td style="padding:4px 8px;font-size:11px;font-family:{_MONO};text-align:right;color:{P["negative"] if (fp50 or 0) < 2.0 else P["warning"]};font-variant-numeric:tabular-nums">{f"{fp50:.2f}×" if fp50 else "—"}</td>'
            f'<td style="padding:4px 8px;font-size:10px;font-family:{_MONO};text-align:right;color:{P["text_dim"]};font-variant-numeric:tabular-nums">{f"{cp50:.2f}×" if cp50 else "—"}</td>'
            f'<td style="padding:4px 8px">{impact}</td>'
            f'<td style="padding:4px 8px;font-size:10px;font-family:{_MONO};text-align:right;font-variant-numeric:tabular-nums">{f"{sub2:.0f}%" if sub2 is not None else "—"}</td>'
            f'<td style="padding:4px 8px;font-size:10px;font-family:{_MONO};text-align:right;font-variant-numeric:tabular-nums">{factor["weight"]}</td>'
            f'</tr>'
        )

    th = f"padding:4px 8px;font-size:9px;letter-spacing:.08em;color:{P['text_dim']};font-family:{_SANS};border-bottom:1px solid {P['border']};position:sticky;top:0;background:{P['panel_alt']}"
    base_rate_table = f"""<div style="border:1px solid {P['border']};overflow-x:auto">
<table style="width:100%;border-collapse:collapse">
<thead><tr style="background:{P['panel_alt']}">
  <th style="{th}">RISK FACTOR</th>
  <th style="{th};text-align:right">CORPUS N</th>
  <th style="{th};text-align:right">BASE RATE</th>
  <th style="{th};text-align:right">FLAGGED MOIC P50</th>
  <th style="{th};text-align:right">CLEAN MOIC P50</th>
  <th style="{th}">IMPACT</th>
  <th style="{th};text-align:right">SUB-2.0× RATE</th>
  <th style="{th};text-align:right">SCORE WT</th>
</tr></thead>
<tbody>{br_rows}</tbody>
</table></div>"""

    empty_msg = "" if has_inputs else f"""
<div style="background:{P['panel_alt']};border:1px solid {P['border']};padding:20px;text-align:center;margin-bottom:16px">
  <div style="font-size:12px;color:{P['text_dim']};font-family:{_SANS}">Enter deal characteristics above to score against corpus risk factors.</div>
</div>"""

    body = f"""
<div style="padding:16px 20px;max-width:1200px">
  {ck_section_header("RCM RED FLAG DETECTOR", f"Corpus-driven risk factor scoring — {len(corpus):,} transactions", None)}
  <div style="background:{P['panel']};border:1px solid {P['border']};padding:14px;margin-bottom:16px">
    <div style="font-size:9px;color:{P['text_dim']};font-family:{_SANS};letter-spacing:.08em;margin-bottom:10px">DEAL PARAMETERS</div>
    {_input_form(params)}
  </div>
  {empty_msg}
  {deal_score_html}
  <div style="margin-bottom:8px;font-size:9px;color:{P['text_dim']};font-family:{_SANS};letter-spacing:.1em;border-bottom:1px solid {P['border']};padding-bottom:4px">
    CORPUS BASE RATES — RISK FACTOR IMPACT ON REALIZED MOIC
  </div>
  {base_rate_table}
  <div style="margin-top:8px;font-size:10px;color:{P['text_faint']};font-family:{_SANS}">
    "Flagged" = corpus deals where this risk factor is present. "Clean" = all others. Sub-2.0× Rate = share of flagged deals with MOIC &lt; 2.0×. Score weight = contribution to composite risk score (max 100). Corpus: {len(corpus):,} deals.
  </div>
</div>"""

    return chartis_shell(body, "RCM Red Flag Detector", active_nav="/rcm-red-flags",
                         subtitle=f"{len(_RISK_FACTORS)} risk factors — {len(corpus):,} deal corpus")
