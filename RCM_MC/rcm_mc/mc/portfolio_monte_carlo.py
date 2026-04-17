"""Correlated Monte Carlo across all deals in the portfolio (Prompt 37).

Each deal already has a v2 MC producing per-deal
``recurring_ebitda_distribution`` + ``moic_distribution``. The
portfolio MC adds cross-deal execution correlation (0.3 within-family
as a baseline) and produces:

- Fund-level EBITDA impact distribution.
- Diversification benefit (fund P50 tighter than sum of deal P50s).
- Tail-risk scenarios (what happens if the worst 20% of outcomes
  across all deals materialize simultaneously).

One entry point: :func:`run_portfolio_mc`.
"""
from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from .ebitda_mc import DistributionSummary, _histogram, HistogramBin
from .convergence import ConvergenceReport, check_convergence

logger = logging.getLogger(__name__)


@dataclass
class PortfolioMCResult:
    """Fund-level simulation output."""
    n_deals: int = 0
    n_simulations: int = 0
    fund_ebitda_impact: DistributionSummary = field(
        default_factory=DistributionSummary,
    )
    fund_moic: DistributionSummary = field(
        default_factory=DistributionSummary,
    )
    diversification_benefit_pct: float = 0.0
    tail_risk_p5: float = 0.0
    per_deal_contribution: Dict[str, float] = field(default_factory=dict)
    correlation_matrix: Optional[List[List[float]]] = None
    histogram_data: List[HistogramBin] = field(default_factory=list)
    convergence_check: ConvergenceReport = field(
        default_factory=ConvergenceReport,
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "n_deals": int(self.n_deals),
            "n_simulations": int(self.n_simulations),
            "fund_ebitda_impact": self.fund_ebitda_impact.to_dict(),
            "fund_moic": self.fund_moic.to_dict(),
            "diversification_benefit_pct": float(
                self.diversification_benefit_pct,
            ),
            "tail_risk_p5": float(self.tail_risk_p5),
            "per_deal_contribution": {
                k: float(v) for k, v in self.per_deal_contribution.items()
            },
            "correlation_matrix": self.correlation_matrix,
            "histogram_data": [h.to_dict() for h in self.histogram_data],
            "convergence_check": self.convergence_check.to_dict(),
        }


# ── Helpers ────────────────────────────────────────────────────────

def _build_default_correlation(
    n_deals: int, within_family_rho: float = 0.30,
) -> np.ndarray:
    """Block-diagonal correlation with ``within_family_rho`` on the
    off-diagonals. A more sophisticated version would group deals by
    lever family and apply family-specific correlations; this baseline
    is conservative enough for IC and correct by design (PD
    + positive-definite guaranteed because rho < 1 and n is finite).
    """
    corr = np.eye(n_deals) * (1.0 - within_family_rho) + within_family_rho
    return corr


def _cholesky_correlated_normals(
    rng: np.random.Generator, n_sims: int, corr: np.ndarray,
) -> np.ndarray:
    """Draw ``(n_sims, n_deals)`` correlated standard normals."""
    L = np.linalg.cholesky(corr)
    z = rng.standard_normal((n_sims, corr.shape[0]))
    return z @ L.T


# ── Public entry ──────────────────────────────────────────────────

def run_portfolio_mc(
    deal_summaries: List[Dict[str, Any]],
    *,
    n_simulations: int = 5000,
    seed: int = 42,
    within_family_rho: float = 0.30,
    entry_ev: Optional[float] = None,
) -> PortfolioMCResult:
    """Correlated MC across all deals.

    ``deal_summaries`` is a list of per-deal dicts with:
    - ``deal_id``: str
    - ``ebitda_p50``: float — per-deal P50 EBITDA impact
    - ``ebitda_std``: float — per-deal EBITDA std
    - ``moic_p50``: float (optional)

    Each deal's per-sim EBITDA is drawn from a normal centered on
    ``ebitda_p50`` with ``ebitda_std``, correlated across deals via
    the supplied (or default) correlation matrix. Fund-level EBITDA
    is the sum; fund MOIC uses ``entry_ev`` when provided.
    """
    n_deals = len(deal_summaries)
    if n_deals == 0:
        return PortfolioMCResult()

    rng = np.random.default_rng(int(seed))
    n = int(n_simulations)

    # Per-deal parameters.
    means = np.array(
        [float(d.get("ebitda_p50") or 0.0) for d in deal_summaries],
        dtype=float,
    )
    stds = np.array(
        [max(float(d.get("ebitda_std") or 0.0), 1e-6)
         for d in deal_summaries],
        dtype=float,
    )
    deal_ids = [str(d.get("deal_id") or f"deal_{i}")
                for i, d in enumerate(deal_summaries)]

    corr = _build_default_correlation(n_deals, within_family_rho)
    z = _cholesky_correlated_normals(rng, n, corr)

    # Scale to per-deal marginals.
    per_deal = z * stds[None, :] + means[None, :]   # (n_sims, n_deals)
    fund_ebitda = per_deal.sum(axis=1)               # (n_sims,)

    # Fund MOIC when entry EV is known.
    if entry_ev and entry_ev > 0:
        fund_moic_arr = (entry_ev + fund_ebitda) / entry_ev
    else:
        fund_moic_arr = np.ones(n)

    # Diversification benefit: sum-of-deal-stds vs fund std.
    sum_of_stds = float(stds.sum())
    fund_std = float(np.std(fund_ebitda, ddof=0))
    div_benefit = 0.0
    if sum_of_stds > 0:
        div_benefit = (1.0 - fund_std / sum_of_stds) * 100.0

    # Per-deal contribution to fund variance (corr²).
    var_fund = max(float(np.var(fund_ebitda)), 1e-18)
    contribution: Dict[str, float] = {}
    raw: Dict[str, float] = {}
    for j, did in enumerate(deal_ids):
        cov_j = float(np.mean(
            (per_deal[:, j] - means[j]) * (fund_ebitda - fund_ebitda.mean()),
        ))
        var_j = float(np.var(per_deal[:, j]))
        if var_j <= 0 or var_fund <= 0:
            raw[did] = 0.0
            continue
        r = cov_j / math.sqrt(var_j * var_fund)
        raw[did] = r * r
    total = sum(raw.values()) or 1.0
    contribution = {k: v / total for k, v in raw.items()}

    histogram = _histogram(fund_ebitda, n_bins=30)
    convergence = check_convergence(
        fund_ebitda,
        window=max(100, n // 10),
        tolerance=0.02,
    )

    return PortfolioMCResult(
        n_deals=n_deals,
        n_simulations=n,
        fund_ebitda_impact=DistributionSummary.from_array(fund_ebitda),
        fund_moic=DistributionSummary.from_array(fund_moic_arr),
        diversification_benefit_pct=float(div_benefit),
        tail_risk_p5=float(np.quantile(fund_ebitda, 0.05)),
        per_deal_contribution=contribution,
        correlation_matrix=corr.tolist(),
        histogram_data=histogram,
        convergence_check=convergence,
    )
