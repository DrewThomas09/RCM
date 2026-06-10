"""Roll-Up Scenario math — pro-forma combination of real HCRIS facilities.

The PE thesis-testing motion: "what does the platform look like after
acquisitions 1–3?" Everything here is arithmetic on filed HCRIS values —
no synthetic facilities, no invented volumes:

- aggregates (beds, inpatient days, net patient revenue) are sums of the
  selected facilities' filings; a facility missing a field contributes a
  GAP to that aggregate's coverage note, never a silent zero (sums state
  how many of N facilities they cover);
- the blended payer mix is DAY-WEIGHTED across facilities that report the
  split (NaN filings excluded from numerator and denominator);
- market share + HHI are computed on net-patient-revenue shares within the
  selected facilities' state, before vs after the combination. A state is a
  deliberately coarse antitrust market — callers must label it a screening
  proxy, not a relevant-market analysis. The DOJ/FTC 2023 merger-guidelines
  screening zone (post-merger HHI > 1800 and Δ > 100, or any Δ > 200 in a
  highly-concentrated market) is annotated, sourced to the guidelines.
- synergy is a USER ASSUMPTION (pct of combined operating expenses),
  default 0 — the module computes the arithmetic, the UI labels the basis.

Pure logic: pandas in, dataclasses out; no UI imports.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

import pandas as pd


@dataclass
class FacilityRow:
    ccn: str
    name: str
    state: str
    beds: Optional[float]
    inpatient_days: Optional[float]
    npr: Optional[float]
    opex: Optional[float]
    medicare_day_pct: Optional[float]
    medicaid_day_pct: Optional[float]


@dataclass
class Aggregate:
    value: Optional[float]
    covered: int                 # facilities contributing a real value
    n: int                       # facilities selected

    @property
    def complete(self) -> bool:
        return self.covered == self.n


@dataclass
class MarketView:
    state: str
    market_npr: float            # Σ NPR across the state's filings
    n_market: int
    share_before_max: float      # largest single selected facility's share
    share_after: float           # combined share
    hhi_before: float
    hhi_after: float

    @property
    def hhi_delta(self) -> float:
        return self.hhi_after - self.hhi_before


@dataclass
class RollupScenario:
    facilities: List[FacilityRow]
    beds: Aggregate
    inpatient_days: Aggregate
    npr: Aggregate
    opex: Aggregate
    blended_medicare_pct: Optional[float]
    blended_medicaid_pct: Optional[float]
    payer_mix_covered: int
    markets: List[MarketView] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)

    def synergy_ebitda(self, ga_pct: float) -> Optional[float]:
        """USER-ASSUMPTION synergy: ga_pct (0..1) of combined opex. Returns
        None when opex coverage is incomplete — a synergy number on top of a
        partially-known cost base would be fabrication."""
        if not self.opex.complete or not self.opex.value:
            return None
        ga = max(0.0, min(0.30, float(ga_pct)))   # >30% of opex is not credible
        return self.opex.value * ga


def _num(v) -> Optional[float]:
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return None if f != f else f


def _agg(vals: List[Optional[float]]) -> Aggregate:
    real = [v for v in vals if v is not None]
    return Aggregate(value=(sum(real) if real else None),
                     covered=len(real), n=len(vals))


def _hhi(shares: List[float]) -> float:
    """HHI on percentage-point shares (Σ (100·s)²), the antitrust convention."""
    return float(sum((100.0 * s) ** 2 for s in shares))


def build_scenario(hcris_df: pd.DataFrame, ccns: List[str]) -> RollupScenario:
    """Combine the selected CCNs into a pro-forma platform view."""
    sel = hcris_df[hcris_df["ccn"].astype(str).isin([str(c) for c in ccns])]
    facilities: List[FacilityRow] = []
    for _, r in sel.iterrows():
        facilities.append(FacilityRow(
            ccn=str(r.get("ccn")), name=str(r.get("name") or "—"),
            state=str(r.get("state") or ""),
            beds=_num(r.get("beds")),
            inpatient_days=_num(r.get("total_patient_days")),
            npr=_num(r.get("net_patient_revenue")),
            opex=_num(r.get("operating_expenses")),
            medicare_day_pct=_num(r.get("medicare_day_pct")),
            medicaid_day_pct=_num(r.get("medicaid_day_pct")),
        ))

    beds = _agg([f.beds for f in facilities])
    days = _agg([f.inpatient_days for f in facilities])
    npr = _agg([f.npr for f in facilities])
    opex = _agg([f.opex for f in facilities])

    # Day-weighted payer blend across facilities reporting BOTH days and the
    # split. NaN filings drop out of numerator and denominator alike.
    wm_num = wm_den = wd_num = 0.0
    mix_covered = 0
    for f in facilities:
        if f.inpatient_days and f.medicare_day_pct is not None \
                and f.medicaid_day_pct is not None:
            mix_covered += 1
            wm_num += f.inpatient_days * f.medicare_day_pct
            wd_num += f.inpatient_days * f.medicaid_day_pct
            wm_den += f.inpatient_days
    blended_mc = (wm_num / wm_den) if wm_den else None
    blended_md = (wd_num / wm_den) if wm_den else None

    scenario = RollupScenario(
        facilities=facilities, beds=beds, inpatient_days=days, npr=npr,
        opex=opex, blended_medicare_pct=blended_mc,
        blended_medicaid_pct=blended_md, payer_mix_covered=mix_covered)

    # Market share + HHI per state touched by ≥1 selected facility.
    for state in sorted({f.state for f in facilities if f.state}):
        mkt = hcris_df[hcris_df["state"] == state]
        mkt_npr = mkt["net_patient_revenue"].dropna()
        total = float(mkt_npr.sum())
        if not total:
            continue
        sel_in_state = [f for f in facilities if f.state == state and f.npr]
        if not sel_in_state:
            continue
        shares = (mkt_npr / total)
        sel_shares = [f.npr / total for f in sel_in_state]
        combined = sum(sel_shares)
        # Before: each selected facility is independent. After: they are one
        # firm — HHI changes by (Σs)² − Σ(s²), holding everyone else fixed.
        hhi_before = _hhi(list(shares))
        hhi_after = hhi_before - _hhi(sel_shares) + _hhi([combined])
        scenario.markets.append(MarketView(
            state=state, market_npr=total, n_market=int(len(mkt_npr)),
            share_before_max=max(sel_shares), share_after=combined,
            hhi_before=hhi_before, hhi_after=hhi_after))
        if len(sel_in_state) >= 2:
            scenario.notes.append(
                f"{len(sel_in_state)} selected facilities operate in {state} "
                "— in-state overlap; assess service-line/geographic overlap "
                "below state level before relying on the share math.")

    return scenario


def antitrust_note(m: MarketView) -> str:
    """Screening-zone annotation per the 2023 DOJ/FTC Merger Guidelines
    (§2.1 structural presumption: post-merger HHI > 1800 AND Δ > 100, or
    share > 30% with Δ > 100). State-level NPR is a coarse screening proxy —
    the note says which zone fired, never that a deal 'fails'."""
    d = m.hhi_delta
    if m.hhi_after > 1800 and d > 100:
        return ("Structural-presumption zone: post-combination HHI "
                f"{m.hhi_after:,.0f} (> 1800) with Δ {d:,.0f} (> 100) — "
                "expect agency screening attention (2023 Merger Guidelines "
                "§2.1; state-NPR proxy market).")
    if m.share_after > 0.30 and d > 100:
        return (f"Share {m.share_after:.0%} (> 30%) with HHI Δ {d:,.0f} "
                "(> 100) — within the guidelines' attention zone "
                "(state-NPR proxy market).")
    if d > 0:
        return (f"HHI Δ +{d:,.0f} to {m.hhi_after:,.0f} — below the "
                "structural-presumption thresholds on this proxy market.")
    return "No concentration change in this market."


def scenario_csv(s: RollupScenario) -> str:
    rows = ["section,key,value,coverage"]
    for f in s.facilities:
        rows.append(
            f'facility,{f.ccn} {f.name.replace(",", " ")},'
            f'npr={f.npr or ""}; days={f.inpatient_days or ""}; '
            f'beds={f.beds or ""},filed HCRIS')
    rows.append(f"combined,beds,{s.beds.value or ''},{s.beds.covered}/{s.beds.n}")
    rows.append(f"combined,inpatient_days,{s.inpatient_days.value or ''},"
                f"{s.inpatient_days.covered}/{s.inpatient_days.n}")
    rows.append(f"combined,net_patient_revenue,{s.npr.value or ''},"
                f"{s.npr.covered}/{s.npr.n}")
    if s.blended_medicare_pct is not None:
        rows.append(f"combined,blended_medicare_day_pct,"
                    f"{s.blended_medicare_pct:.4f},{s.payer_mix_covered}/{len(s.facilities)}")
    for m in s.markets:
        rows.append(f"market,{m.state} share_after,{m.share_after:.4f},n={m.n_market}")
        rows.append(f"market,{m.state} hhi_before,{m.hhi_before:.0f},")
        rows.append(f"market,{m.state} hhi_after,{m.hhi_after:.0f},")
    return "\n".join(rows)
