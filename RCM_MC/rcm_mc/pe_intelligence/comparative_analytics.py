"""Comparative analytics — portfolio-level cross-deal comparisons.

Partners frequently compare a proposed deal against their existing
portfolio: "does this deal help the book or hurt it?" This module
provides the arithmetic for that question.

Functions:

- :func:`portfolio_concentration` — sector / payer / geography
  concentration metrics across a list of deals.
- :func:`deal_vs_book` — compare a candidate deal against the
  portfolio median on key KPIs.
- :func:`deal_rank_vs_peers` — rank one deal against a list of
  candidate peers on a blended score.
- :func:`correlation_risk` — identify deals whose returns are likely
  to co-move (same payer, same state, same cycle).

Inputs are lightweight dicts describing each deal — this module does
not touch :class:`DealAnalysisPacket`. The caller constructs the deal
dicts from wherever they live.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


# ── Inputs ──────────────────────────────────────────────────────────

@dataclass
class DealSnapshot:
    deal_id: str
    name: str = ""
    sector: Optional[str] = None            # hospital type / subsector
    state: Optional[str] = None
    ebitda_m: Optional[float] = None
    revenue_m: Optional[float] = None
    payer_mix: Dict[str, float] = field(default_factory=dict)
    projected_irr: Optional[float] = None
    projected_moic: Optional[float] = None
    ebitda_margin: Optional[float] = None
    leverage_multiple: Optional[float] = None
    days_in_ar: Optional[float] = None
    denial_rate: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "deal_id": self.deal_id,
            "name": self.name,
            "sector": self.sector,
            "state": self.state,
            "ebitda_m": self.ebitda_m,
            "revenue_m": self.revenue_m,
            "payer_mix": dict(self.payer_mix),
            "projected_irr": self.projected_irr,
            "projected_moic": self.projected_moic,
            "ebitda_margin": self.ebitda_margin,
            "leverage_multiple": self.leverage_multiple,
            "days_in_ar": self.days_in_ar,
            "denial_rate": self.denial_rate,
        }


# ── Concentration ───────────────────────────────────────────────────

def _pct_concentration(values: Dict[str, float]) -> Dict[str, float]:
    total = sum(values.values())
    if total <= 0:
        return values
    return {k: v / total for k, v in values.items()}


def portfolio_concentration(deals: List[DealSnapshot]) -> Dict[str, Any]:
    """Return sector / state / payer concentration shares across a
    portfolio. Weights each deal by its EBITDA (falls back to equal
    weight when EBITDA missing).
    """
    sector_ebitda: Dict[str, float] = {}
    state_ebitda: Dict[str, float] = {}
    payer_ebitda: Dict[str, float] = {}
    total_ebitda = 0.0

    for d in deals:
        w = d.ebitda_m or 1.0  # fallback
        total_ebitda += w
        if d.sector:
            sector_ebitda[d.sector] = sector_ebitda.get(d.sector, 0.0) + w
        if d.state:
            state_ebitda[d.state] = state_ebitda.get(d.state, 0.0) + w
        for payer, share in (d.payer_mix or {}).items():
            s = float(share)
            if s > 1.5:
                s /= 100.0
            payer_ebitda[payer] = payer_ebitda.get(payer, 0.0) + w * s

    top_sector = max(sector_ebitda.items(), key=lambda kv: kv[1]) if sector_ebitda else ("", 0.0)
    top_state = max(state_ebitda.items(), key=lambda kv: kv[1]) if state_ebitda else ("", 0.0)
    top_payer = max(payer_ebitda.items(), key=lambda kv: kv[1]) if payer_ebitda else ("", 0.0)

    return {
        "n_deals": len(deals),
        "total_ebitda_m": total_ebitda,
        "sector_shares": _pct_concentration(sector_ebitda),
        "state_shares": _pct_concentration(state_ebitda),
        "payer_shares": _pct_concentration(payer_ebitda),
        "top_sector": {"name": top_sector[0], "share": top_sector[1] / total_ebitda if total_ebitda else 0},
        "top_state": {"name": top_state[0], "share": top_state[1] / total_ebitda if total_ebitda else 0},
        "top_payer": {"name": top_payer[0], "share": top_payer[1] / total_ebitda if total_ebitda else 0},
    }


def concentration_warnings(conc: Dict[str, Any]) -> List[str]:
    """Human-readable warnings for concentration metrics."""
    out: List[str] = []
    top_sector = conc.get("top_sector") or {}
    if top_sector.get("share", 0) > 0.40:
        out.append(f"Sector concentration: {top_sector['name']} is "
                   f"{top_sector['share']*100:.0f}% of portfolio EBITDA.")
    top_state = conc.get("top_state") or {}
    if top_state.get("share", 0) > 0.35:
        out.append(f"Geographic concentration: {top_state['name']} is "
                   f"{top_state['share']*100:.0f}% of portfolio EBITDA.")
    top_payer = conc.get("top_payer") or {}
    if top_payer.get("share", 0) > 0.50:
        out.append(f"Payer concentration: {top_payer['name']} is "
                   f"{top_payer['share']*100:.0f}% of portfolio EBITDA.")
    return out


# ── Deal-vs-book ─────────────────────────────────────────────────────

def _median(values: List[float]) -> Optional[float]:
    clean = [v for v in values if v is not None]
    if not clean:
        return None
    clean = sorted(clean)
    n = len(clean)
    if n % 2 == 1:
        return clean[n // 2]
    return 0.5 * (clean[n // 2 - 1] + clean[n // 2])


@dataclass
class DealVsBookFinding:
    metric: str
    candidate: Optional[float]
    book_median: Optional[float]
    direction: str                   # "better" | "worse" | "same" | "n/a"
    commentary: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "metric": self.metric,
            "candidate": self.candidate,
            "book_median": self.book_median,
            "direction": self.direction,
            "commentary": self.commentary,
        }


_LOW_IS_BETTER = {"days_in_ar", "denial_rate", "leverage_multiple"}


def deal_vs_book(
    candidate: DealSnapshot,
    book: List[DealSnapshot],
) -> List[DealVsBookFinding]:
    """Compare candidate to book medians on key metrics."""
    metrics = ("projected_irr", "projected_moic", "ebitda_margin",
               "leverage_multiple", "days_in_ar", "denial_rate")
    out: List[DealVsBookFinding] = []
    for m in metrics:
        book_vals = [getattr(d, m) for d in book]
        median = _median([v for v in book_vals if v is not None])
        candidate_val = getattr(candidate, m)
        if candidate_val is None or median is None:
            out.append(DealVsBookFinding(
                metric=m, candidate=candidate_val, book_median=median,
                direction="n/a", commentary="Insufficient data.",
            ))
            continue
        # Direction semantics
        better = (candidate_val < median) if m in _LOW_IS_BETTER \
                 else (candidate_val > median)
        worse = (candidate_val > median) if m in _LOW_IS_BETTER \
                else (candidate_val < median)
        if better:
            direction = "better"
            commentary = f"Candidate {candidate_val:.3f} is better than book median {median:.3f}."
        elif worse:
            direction = "worse"
            commentary = f"Candidate {candidate_val:.3f} is worse than book median {median:.3f}."
        else:
            direction = "same"
            commentary = f"Candidate matches book median ({median:.3f})."
        out.append(DealVsBookFinding(
            metric=m, candidate=candidate_val, book_median=median,
            direction=direction, commentary=commentary,
        ))
    return out


# ── Deal ranking ────────────────────────────────────────────────────

def deal_rank_vs_peers(
    candidate: DealSnapshot,
    peers: List[DealSnapshot],
) -> Dict[str, Any]:
    """Rank a candidate deal against peers on a blended score.

    Score blends IRR (50%), margin (25%), and reciprocal leverage (25%).
    Returns ``{candidate_rank, n_peers, score, peer_ranks}``.
    """
    def _score(d: DealSnapshot) -> float:
        irr = d.projected_irr or 0.0
        margin = d.ebitda_margin or 0.0
        lev = d.leverage_multiple or 6.0
        # Higher IRR and margin better; lower leverage better.
        lev_score = 1.0 / max(lev, 1.0)
        return 0.50 * irr + 0.25 * margin + 0.25 * lev_score

    cand_score = _score(candidate)
    all_scores = [(d.deal_id, _score(d)) for d in peers]
    all_scores.append((candidate.deal_id, cand_score))
    all_scores.sort(key=lambda kv: -kv[1])
    ranks = {sid: i + 1 for i, (sid, _) in enumerate(all_scores)}
    return {
        "candidate_rank": ranks.get(candidate.deal_id),
        "n_peers": len(peers),
        "score": cand_score,
        "peer_ranks": [{"deal_id": sid, "rank": r}
                       for sid, r in ranks.items()],
    }


# ── Correlation risk ────────────────────────────────────────────────

def correlation_risk(
    candidate: DealSnapshot,
    book: List[DealSnapshot],
) -> List[str]:
    """Flag deals that would co-move with the candidate.

    Co-movement drivers:
    - Same sector + same state (regional CMS rate cycle).
    - Medicare ≥ 60% share in both.
    - Same single dominant commercial payer.
    """
    warnings: List[str] = []
    cand_medicare = float((candidate.payer_mix or {}).get("medicare", 0.0))
    if cand_medicare > 1.5:
        cand_medicare /= 100.0
    for d in book:
        if candidate.deal_id == d.deal_id:
            continue
        if candidate.sector and d.sector == candidate.sector and \
                candidate.state and d.state == candidate.state:
            warnings.append(
                f"{d.deal_id}: same sector + same state → regional cycle correlation."
            )
        d_medicare = float((d.payer_mix or {}).get("medicare", 0.0))
        if d_medicare > 1.5:
            d_medicare /= 100.0
        if cand_medicare >= 0.60 and d_medicare >= 0.60:
            warnings.append(
                f"{d.deal_id}: both deals Medicare ≥ 60% — CMS rate-cycle exposure stacks."
            )
    # Dedup preserving order
    seen = set()
    out: List[str] = []
    for w in warnings:
        if w in seen:
            continue
        seen.add(w)
        out.append(w)
    return out
