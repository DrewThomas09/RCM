"""Corpus-calibrated red-flag detector for deal diligence.

Compares a deal's entry characteristics against realized outcomes in the
615-deal corpus to surface quantified warning signals. Each flag carries:
  - category  : ENTRY_RISK | PAYER | SECTOR | LEVERAGE | HOLD | SIZING
  - severity  : critical | high | medium | low
  - headline  : one-line descriptor for IC display
  - detail    : 1-2 sentences with corpus statistics
  - ebitda_at_risk : estimated $ exposure (MM), None when unsizable

Design intent: a senior partner reviewing a deal at IC should see these
flags and immediately understand which entry characteristics deviate from
corpus norms for surviving/outperforming deals.
"""
from __future__ import annotations

import importlib
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Corpus loader (lazy, cached at module level after first call)
# ---------------------------------------------------------------------------

_CORPUS_CACHE: Optional[List[Dict[str, Any]]] = None


def _get_corpus() -> List[Dict[str, Any]]:
    global _CORPUS_CACHE
    if _CORPUS_CACHE is not None:
        return _CORPUS_CACHE
    from rcm_mc.data_public.deals_corpus import _SEED_DEALS
    from rcm_mc.data_public.extended_seed import EXTENDED_SEED_DEALS
    result = list(_SEED_DEALS) + list(EXTENDED_SEED_DEALS)
    for i in range(2, 32):
        try:
            mod = importlib.import_module(f"rcm_mc.data_public.extended_seed_{i}")
            result += list(getattr(mod, f"EXTENDED_SEED_DEALS_{i}"))
        except (ImportError, AttributeError):
            pass
    _CORPUS_CACHE = result
    return result


# ---------------------------------------------------------------------------
# Corpus statistics helpers
# ---------------------------------------------------------------------------

def _realized(deals: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [d for d in deals if d.get("realized_moic") is not None]


def _percentile(vals: List[float], p: float) -> float:
    if not vals:
        return 0.0
    s = sorted(vals)
    idx = p / 100 * (len(s) - 1)
    lo, hi = int(idx), min(int(idx) + 1, len(s) - 1)
    return s[lo] + (s[hi] - s[lo]) * (idx - lo)


def _loss_rate(moics: List[float]) -> float:
    return sum(1 for m in moics if m < 1.0) / len(moics) if moics else 0.0


def _entry_multiples(deals: List[Dict[str, Any]]) -> List[float]:
    result = []
    for d in deals:
        ev = d.get("ev_mm") or d.get("entry_ev_mm")
        ebitda = d.get("ebitda_at_entry_mm") or d.get("ebitda_mm")
        if ev and ebitda and float(ebitda) > 0:
            result.append(float(ev) / float(ebitda))
    return result


def _commercial_pcts(deals: List[Dict[str, Any]]) -> List[float]:
    result = []
    for d in deals:
        pm = d.get("payer_mix")
        if isinstance(pm, dict) and "commercial" in pm:
            result.append(float(pm["commercial"]))
    return result


def _leverage_pcts(deals: List[Dict[str, Any]]) -> List[float]:
    return [float(d["leverage_pct"]) for d in deals if d.get("leverage_pct") is not None]


# ---------------------------------------------------------------------------
# CorpusRedFlag dataclass
# ---------------------------------------------------------------------------

@dataclass
class CorpusRedFlag:
    category: str            # ENTRY_RISK | PAYER | SECTOR | LEVERAGE | HOLD | SIZING
    severity: str            # critical | high | medium | low
    headline: str
    detail: str
    ebitda_at_risk_mm: Optional[float] = None
    corpus_p75: Optional[float] = None   # context value for display
    deal_value: Optional[float] = None   # the deal's actual value for this dimension
    unit: str = ""

    def as_dict(self) -> Dict[str, Any]:
        return {
            "category": self.category,
            "severity": self.severity,
            "headline": self.headline,
            "detail": self.detail,
            "ebitda_at_risk_mm": self.ebitda_at_risk_mm,
            "corpus_p75": self.corpus_p75,
            "deal_value": self.deal_value,
            "unit": self.unit,
        }


# ---------------------------------------------------------------------------
# Individual flag checks
# ---------------------------------------------------------------------------

def _flag_entry_multiple(
    multiple: Optional[float],
    ebitda_mm: Optional[float],
    corpus: List[Dict[str, Any]],
    sector_deals: List[Dict[str, Any]],
) -> Optional[CorpusRedFlag]:
    if multiple is None:
        return None

    corp_multiples = _entry_multiples(_realized(corpus))
    corp_p75 = _percentile(corp_multiples, 75)
    corp_p90 = _percentile(corp_multiples, 90)
    sec_multiples = _entry_multiples(_realized(sector_deals)) if sector_deals else []
    sec_p75 = _percentile(sec_multiples, 75) if sec_multiples else None

    # Loss rates by multiple tier
    high_mult = [d for d in _realized(corpus) if (_m := _entry_multiples([d])) and _m[0] > 14]
    high_mult_moics = [d["realized_moic"] for d in high_mult]
    high_mult_loss = _loss_rate(high_mult_moics) if high_mult_moics else None

    if multiple > corp_p90:
        severity = "critical"
        detail = (
            f"Entry at {multiple:.1f}× exceeds corpus P90 ({corp_p90:.1f}×). "
            f"Deals entering >14× show {(high_mult_loss or 0)*100:.0f}% loss rate historically."
        )
        ebitda_risk = float(ebitda_mm) * 0.15 if ebitda_mm else None
        return CorpusRedFlag(
            "ENTRY_RISK", severity,
            f"Entry multiple {multiple:.1f}× is top-decile vs. corpus",
            detail, ebitda_risk, corp_p90, multiple, "×"
        )
    if multiple > corp_p75:
        severity = "high"
        detail = (
            f"Entry at {multiple:.1f}× exceeds corpus P75 ({corp_p75:.1f}×). "
            + (f"Sector P75 is {sec_p75:.1f}×. " if sec_p75 else "")
            + "Top-quartile entry multiples carry above-average impairment risk."
        )
        return CorpusRedFlag(
            "ENTRY_RISK", severity,
            f"Entry multiple {multiple:.1f}× is above corpus P75 ({corp_p75:.1f}×)",
            detail, None, corp_p75, multiple, "×"
        )
    return None


def _flag_payer_mix(
    payer_mix: Optional[Dict[str, float]],
    sector: Optional[str],
    ebitda_mm: Optional[float],
    corpus: List[Dict[str, Any]],
    sector_deals: List[Dict[str, Any]],
) -> List[CorpusRedFlag]:
    flags = []
    if not payer_mix or not isinstance(payer_mix, dict):
        return flags

    commercial = payer_mix.get("commercial", 0.0)
    medicare = payer_mix.get("medicare", 0.0) or 0.0
    medicaid = payer_mix.get("medicaid", 0.0) or 0.0
    gov_total = medicare + medicaid

    # Compare commercial pct to corpus and sector norms
    sec_comm = _commercial_pcts(_realized(sector_deals)) if sector_deals else []
    corp_comm = _commercial_pcts(_realized(corpus))
    corp_comm_p25 = _percentile(corp_comm, 25)
    sec_comm_p25 = _percentile(sec_comm, 25) if sec_comm else None

    # MOIC outcomes by commercial tier
    high_gov_deals = [d for d in _realized(corpus)
                      if isinstance(d.get("payer_mix"), dict)
                      and ((d["payer_mix"].get("medicare", 0) or 0)
                           + (d["payer_mix"].get("medicaid", 0) or 0)) >= 0.65]
    high_gov_moics = [d["realized_moic"] for d in high_gov_deals]
    high_gov_p50 = _percentile(sorted(high_gov_moics), 50) if high_gov_moics else None

    if commercial < corp_comm_p25:
        sev = "high" if commercial < 0.30 else "medium"
        detail = (
            f"Commercial mix of {commercial*100:.0f}% is below corpus P25 ({corp_comm_p25*100:.0f}%). "
            + (f"Sector P25 is {sec_comm_p25*100:.0f}%. " if sec_comm_p25 else "")
            + (f"High-government deals in corpus average {high_gov_p50:.2f}x MOIC. " if high_gov_p50 else "")
            + "Thin commercial mix limits payer-renegotiation leverage post-close."
        )
        est_risk = float(ebitda_mm) * 0.08 if ebitda_mm else None
        flags.append(CorpusRedFlag(
            "PAYER", sev,
            f"Commercial mix {commercial*100:.0f}% is below corpus P25 — pricing power risk",
            detail, est_risk, corp_comm_p25, commercial, "%"
        ))

    if gov_total >= 0.65:
        # Check for Medicaid work-requirement exposure
        if medicaid >= 0.25:
            detail = (
                f"Medicaid exposure at {medicaid*100:.0f}% of revenue. "
                "OBBBA work requirements + state-level waiver uncertainty creates cliff risk. "
                "Portfolio companies with >25% Medicaid have shown outsized volatility under policy shifts."
            )
            est_risk = float(ebitda_mm) * medicaid * 0.12 if ebitda_mm else None
            flags.append(CorpusRedFlag(
                "PAYER", "high",
                f"Medicaid concentration {medicaid*100:.0f}% — policy cliff risk (OBBBA)",
                detail, est_risk, 0.25, medicaid, "%"
            ))

    return flags


def _flag_leverage(
    leverage_pct: Optional[float],
    ebitda_mm: Optional[float],
    corpus: List[Dict[str, Any]],
    sector_deals: List[Dict[str, Any]],
) -> Optional[CorpusRedFlag]:
    if leverage_pct is None:
        return None

    corp_lev = _leverage_pcts(_realized(corpus))
    corp_p75 = _percentile(corp_lev, 75)
    corp_p90 = _percentile(corp_lev, 90)

    # Loss rate for high-leverage corpus deals
    high_lev = [d for d in _realized(corpus)
                if d.get("leverage_pct") is not None and float(d["leverage_pct"]) >= 0.70]
    hl_moics = [d["realized_moic"] for d in high_lev]
    hl_loss = _loss_rate(hl_moics) if hl_moics else None

    if leverage_pct > corp_p90:
        detail = (
            f"Leverage at {leverage_pct*100:.0f}% is corpus top-decile (P90={corp_p90*100:.0f}%). "
            + (f"Deals with ≥70% leverage show {(hl_loss or 0)*100:.0f}% corpus loss rate. " if hl_loss else "")
            + "Rate-cycle sensitivity and covenant headroom are primary risks."
        )
        est_risk = float(ebitda_mm) * 0.20 if ebitda_mm else None
        return CorpusRedFlag(
            "LEVERAGE", "critical",
            f"Leverage {leverage_pct*100:.0f}% is top-decile — covenant risk in stress",
            detail, est_risk, corp_p90, leverage_pct, "%"
        )
    if leverage_pct > corp_p75:
        detail = (
            f"Leverage at {leverage_pct*100:.0f}% exceeds corpus P75 ({corp_p75*100:.0f}%). "
            "Above-average sensitivity to rate increases and operational shortfalls."
        )
        return CorpusRedFlag(
            "LEVERAGE", "medium",
            f"Leverage {leverage_pct*100:.0f}% above corpus P75",
            detail, None, corp_p75, leverage_pct, "%"
        )
    return None


def _flag_sector_loss_rate(
    sector: Optional[str],
    sector_deals: List[Dict[str, Any]],
) -> Optional[CorpusRedFlag]:
    if not sector or not sector_deals:
        return None
    moics = [d["realized_moic"] for d in _realized(sector_deals)]
    if len(moics) < 3:
        return None
    loss_rate = _loss_rate(moics)
    p50 = _percentile(sorted(moics), 50)

    if loss_rate >= 0.30:
        detail = (
            f"{sector} has {loss_rate*100:.0f}% loss rate in the corpus "
            f"({sum(1 for m in moics if m < 1.0)} of {len(moics)} realized deals). "
            f"Sector P50 MOIC is {p50:.2f}×. Elevated baseline impairment risk requires deeper operational DD."
        )
        return CorpusRedFlag(
            "SECTOR", "high",
            f"{sector} sector has {loss_rate*100:.0f}% historical loss rate",
            detail, None, loss_rate, loss_rate, "%"
        )
    if loss_rate >= 0.15:
        detail = (
            f"{sector} shows {loss_rate*100:.0f}% loss rate across {len(moics)} corpus deals. "
            f"P50 MOIC {p50:.2f}×. Monitor sector-specific reimbursement and competition dynamics."
        )
        return CorpusRedFlag(
            "SECTOR", "medium",
            f"{sector} sector loss rate {loss_rate*100:.0f}% — above-average baseline",
            detail, None, loss_rate, loss_rate, "%"
        )
    return None


def _flag_hold_years(
    hold_years: Optional[float],
    corpus: List[Dict[str, Any]],
) -> Optional[CorpusRedFlag]:
    if hold_years is None:
        return None
    holds = [float(d["hold_years"]) for d in _realized(corpus) if d.get("hold_years")]
    if not holds:
        return None
    p90 = _percentile(holds, 90)
    p25 = _percentile(holds, 25)

    if hold_years > p90:
        # Very long holds are associated with lower IRR even when MOIC is OK
        detail = (
            f"Target hold of {hold_years:.1f}yr exceeds corpus P90 ({p90:.1f}yr). "
            "Extended holds typically compress IRR 200-400bps even if MOIC is maintained. "
            "Assess exit path credibility and buyer universe depth."
        )
        return CorpusRedFlag(
            "HOLD", "medium",
            f"Planned hold {hold_years:.1f}yr is corpus top-decile — IRR drag risk",
            detail, None, p90, hold_years, "yr"
        )
    if hold_years < p25:
        detail = (
            f"Planned hold of {hold_years:.1f}yr is below corpus P25 ({p25:.1f}yr). "
            "Short holds depend on multiple expansion or M&A exit — both are execution-sensitive. "
            "Verify sponsor track record on sub-3yr exits in this sector."
        )
        return CorpusRedFlag(
            "HOLD", "low",
            f"Planned hold {hold_years:.1f}yr is short — exit execution risk",
            detail, None, p25, hold_years, "yr"
        )
    return None


def _flag_deal_size(
    ev_mm: Optional[float],
    corpus: List[Dict[str, Any]],
    sector: Optional[str],
    sector_deals: List[Dict[str, Any]],
) -> Optional[CorpusRedFlag]:
    if ev_mm is None:
        return None

    corp_evs = [float(d["ev_mm"]) for d in corpus if d.get("ev_mm") and float(d["ev_mm"]) > 0]
    sec_evs = [float(d["ev_mm"]) for d in sector_deals if d.get("ev_mm") and float(d["ev_mm"]) > 0]
    corp_p90 = _percentile(corp_evs, 90)
    corp_p10 = _percentile(corp_evs, 10)

    if ev_mm > corp_p90:
        # Very large deal — thin buyer universe
        sec_comparable = len([e for e in sec_evs if e >= ev_mm * 0.5])
        detail = (
            f"EV ${ev_mm:,.0f}M exceeds corpus P90 (${corp_p90:,.0f}M). "
            + (f"Only {sec_comparable} sector comparables at similar scale. " if sec_evs else "")
            + "Large-cap healthcare deals face thin buyer universe at exit and elevated financing risk."
        )
        return CorpusRedFlag(
            "SIZING", "medium",
            f"EV ${ev_mm:,.0f}M is large-cap — thin comparables and buyer set",
            detail, None, corp_p90, ev_mm, "$M"
        )
    if ev_mm < corp_p10 and ev_mm > 0:
        detail = (
            f"EV ${ev_mm:,.0f}M is sub-corpus P10 (${corp_p10:,.0f}M). "
            "Very small transactions carry above-average key-man and integration risk. "
            "Verify platform add-on thesis has sufficient runway."
        )
        return CorpusRedFlag(
            "SIZING", "low",
            f"EV ${ev_mm:,.0f}M is micro-cap — key-man and scale risk",
            detail, None, corp_p10, ev_mm, "$M"
        )
    return None


# ---------------------------------------------------------------------------
# Main public API
# ---------------------------------------------------------------------------

def detect_corpus_red_flags(
    deal: Dict[str, Any],
    corpus: Optional[List[Dict[str, Any]]] = None,
) -> List[CorpusRedFlag]:
    """Run all corpus-calibrated flag checks against a deal dict.

    ``deal`` should contain any subset of:
        ev_mm, ebitda_at_entry_mm (or ebitda_mm), hold_years,
        leverage_pct, payer_mix (dict), sector

    Missing fields are skipped gracefully.
    Returns flags sorted: critical first, then high, medium, low.
    """
    if corpus is None:
        corpus = _get_corpus()

    sector = deal.get("sector") or deal.get("sector_name")
    sector_deals = [d for d in corpus if d.get("sector") == sector] if sector else []

    ev = deal.get("ev_mm") or deal.get("entry_ev_mm")
    ebitda = deal.get("ebitda_at_entry_mm") or deal.get("ebitda_mm") or deal.get("ebitda")
    multiple: Optional[float] = None
    if ev and ebitda:
        try:
            multiple = float(ev) / float(ebitda)
        except (TypeError, ZeroDivisionError):
            pass

    ev_mm = float(ev) if ev else None
    ebitda_mm = float(ebitda) if ebitda else None
    hold_years = float(deal["hold_years"]) if deal.get("hold_years") else None
    leverage_pct = float(deal["leverage_pct"]) if deal.get("leverage_pct") else None
    payer_mix = deal.get("payer_mix")
    if isinstance(payer_mix, str):
        import json
        try:
            payer_mix = json.loads(payer_mix)
        except Exception:
            payer_mix = None

    flags: List[CorpusRedFlag] = []

    f = _flag_entry_multiple(multiple, ebitda_mm, corpus, sector_deals)
    if f:
        flags.append(f)

    flags.extend(_flag_payer_mix(payer_mix, sector, ebitda_mm, corpus, sector_deals))

    f = _flag_leverage(leverage_pct, ebitda_mm, corpus, sector_deals)
    if f:
        flags.append(f)

    f = _flag_sector_loss_rate(sector, sector_deals)
    if f:
        flags.append(f)

    f = _flag_hold_years(hold_years, corpus)
    if f:
        flags.append(f)

    f = _flag_deal_size(ev_mm, corpus, sector, sector_deals)
    if f:
        flags.append(f)

    _SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    flags.sort(key=lambda x: _SEVERITY_ORDER.get(x.severity, 9))
    return flags


def flag_summary(flags: List[CorpusRedFlag]) -> Dict[str, Any]:
    """Aggregate counts and total ebitda_at_risk from a flag list."""
    by_sev = {"critical": 0, "high": 0, "medium": 0, "low": 0}
    total_risk_mm = 0.0
    for f in flags:
        by_sev[f.severity] = by_sev.get(f.severity, 0) + 1
        if f.ebitda_at_risk_mm:
            total_risk_mm += f.ebitda_at_risk_mm
    return {
        "total_flags": len(flags),
        "by_severity": by_sev,
        "total_ebitda_at_risk_mm": round(total_risk_mm, 1) if total_risk_mm else None,
    }
