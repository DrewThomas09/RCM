"""Payer-contract Monte Carlo rate-shock simulator.

Given a target's claimed payer mix, simulate per-payer rate
movements over a 5-year hold using the curated rate-movement
priors, apply concentration penalties, and produce:

    * per-payer expected rate move (median) + distribution (p10/p90)
    * aggregate NPR impact path with p10/p50/p90 cones
    * EBITDA at risk per year
    * concentration-risk verdict (PASS / CAUTION / WARNING / FAIL)
    * partner-facing headline naming the worst exposed payer and
      the probable EBITDA drag
    * contract-renewal timeline

Concentration penalty: when the Top-1 payer share crosses 30%,
aggregate NPR volatility gets amplified by (1 + (top_1 - 0.30) × 2).
When Top-2 combined crosses 50%, additional penalty kicks in.
These coefficients match the empirical heuristics PE credit funds
use in concentration-adjusted covenant design.
"""
from __future__ import annotations

import math
import random
import statistics
from dataclasses import dataclass, field
from datetime import date, timedelta
from enum import Enum
from typing import (
    Any, Dict, List, Mapping, Optional, Sequence, Tuple,
)

from .payer_library import (
    PAYER_PRIORS, PayerCategory, PayerPrior, classify_payer,
    get_payer,
)


class PayerStressVerdict(str, Enum):
    PASS = "PASS"
    CAUTION = "CAUTION"
    WARNING = "WARNING"
    FAIL = "FAIL"


@dataclass(frozen=True)
class PayerMixEntry:
    """One payer in the target's mix."""
    payer_name: str                  # free text — classifier maps to prior
    share_of_npr: float              # 0..1 — fraction of total NPR
    contract_renewal_date: Optional[str] = None  # ISO (optional)
    current_rate_adjustment_pct: Optional[float] = None
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "payer_name": self.payer_name,
            "share_of_npr": self.share_of_npr,
            "contract_renewal_date": self.contract_renewal_date,
            "current_rate_adjustment_pct":
                self.current_rate_adjustment_pct,
            "notes": self.notes,
        }


@dataclass
class PayerStressRow:
    """Per-payer output."""
    payer_name: str
    payer_id: Optional[str]
    category: Optional[str]
    share_of_npr: float
    npr_attributed_usd: float
    # Stress results
    median_rate_move: float          # signed fraction, e.g. -0.01 = -1%
    p10_rate_move: float
    p90_rate_move: float
    median_npr_delta_usd: float
    p10_npr_delta_usd: float
    p90_npr_delta_usd: float
    contract_renewal_date: Optional[str] = None
    negotiating_leverage: float = 0.5
    churn_prob: float = 0.0
    narrative: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "payer_name": self.payer_name,
            "payer_id": self.payer_id,
            "category": self.category,
            "share_of_npr": self.share_of_npr,
            "npr_attributed_usd": self.npr_attributed_usd,
            "median_rate_move": self.median_rate_move,
            "p10_rate_move": self.p10_rate_move,
            "p90_rate_move": self.p90_rate_move,
            "median_npr_delta_usd": self.median_npr_delta_usd,
            "p10_npr_delta_usd": self.p10_npr_delta_usd,
            "p90_npr_delta_usd": self.p90_npr_delta_usd,
            "contract_renewal_date": self.contract_renewal_date,
            "negotiating_leverage": self.negotiating_leverage,
            "churn_prob": self.churn_prob,
            "narrative": self.narrative,
        }


@dataclass
class YearlyNPRImpact:
    """Per-year aggregate NPR impact across simulated paths."""
    year: int
    p10_npr_delta_usd: float
    p50_npr_delta_usd: float
    p90_npr_delta_usd: float
    median_ebitda_impact_usd: float
    p10_ebitda_impact_usd: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "year": self.year,
            "p10_npr_delta_usd": self.p10_npr_delta_usd,
            "p50_npr_delta_usd": self.p50_npr_delta_usd,
            "p90_npr_delta_usd": self.p90_npr_delta_usd,
            "median_ebitda_impact_usd": self.median_ebitda_impact_usd,
            "p10_ebitda_impact_usd": self.p10_ebitda_impact_usd,
        }


@dataclass
class PayerStressReport:
    """Top-level output."""
    target_name: str
    n_paths: int
    horizon_years: int
    total_npr_usd: float
    total_ebitda_usd: float
    # Composition stats
    top_1_share: float
    top_2_share: float
    top_3_share: float
    hhi_index: float                 # Herfindahl-Hirschman concentration
    concentration_amplifier: float
    # Per-payer
    per_payer: List[PayerStressRow] = field(default_factory=list)
    # Aggregate path
    yearly_impact: List[YearlyNPRImpact] = field(default_factory=list)
    # Terminal aggregates
    median_cumulative_npr_delta_usd: float = 0.0
    p10_cumulative_npr_delta_usd: float = 0.0
    p90_cumulative_npr_delta_usd: float = 0.0
    median_cumulative_ebitda_impact_usd: float = 0.0
    p10_cumulative_ebitda_impact_usd: float = 0.0
    # Verdict
    verdict: PayerStressVerdict = PayerStressVerdict.PASS
    risk_score: float = 0.0           # 0-100
    headline: str = ""
    rationale: str = ""
    unclassified_share: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "target_name": self.target_name,
            "n_paths": self.n_paths,
            "horizon_years": self.horizon_years,
            "total_npr_usd": self.total_npr_usd,
            "total_ebitda_usd": self.total_ebitda_usd,
            "top_1_share": self.top_1_share,
            "top_2_share": self.top_2_share,
            "top_3_share": self.top_3_share,
            "hhi_index": self.hhi_index,
            "concentration_amplifier": self.concentration_amplifier,
            "per_payer": [p.to_dict() for p in self.per_payer],
            "yearly_impact": [
                y.to_dict() for y in self.yearly_impact
            ],
            "median_cumulative_npr_delta_usd":
                self.median_cumulative_npr_delta_usd,
            "p10_cumulative_npr_delta_usd":
                self.p10_cumulative_npr_delta_usd,
            "p90_cumulative_npr_delta_usd":
                self.p90_cumulative_npr_delta_usd,
            "median_cumulative_ebitda_impact_usd":
                self.median_cumulative_ebitda_impact_usd,
            "p10_cumulative_ebitda_impact_usd":
                self.p10_cumulative_ebitda_impact_usd,
            "verdict": self.verdict.value,
            "risk_score": self.risk_score,
            "headline": self.headline,
            "rationale": self.rationale,
            "unclassified_share": self.unclassified_share,
        }


# ────────────────────────────────────────────────────────────────────
# Sampling + concentration helpers
# ────────────────────────────────────────────────────────────────────

def _lognormal_params_from_quantiles(
    p25: float, median: float, p75: float,
) -> Tuple[float, float]:
    """Back-solve normal (mu, sigma) for the *rate move* distribution.

    Rate moves are small (-0.10 to +0.10) and can be negative, so we
    model them as Normal(mu, sigma) directly rather than lognormal.
    p75 − p25 ≈ 1.349 × sigma, median ≈ mu.
    """
    mu = float(median)
    sigma = max(0.005, (float(p75) - float(p25)) / 1.349)
    return mu, sigma


def _compute_concentration_amplifier(
    shares: Sequence[float],
) -> float:
    """Amplifier on NPR volatility driven by payer concentration.

    Top-1 > 30%: amplifier = 1 + (top_1 - 0.30) × 2
    Top-2 > 50% combined: additional +0.10
    Top-3 > 70% combined: additional +0.10
    Floor 1.0 (no amplifier for diversified mix)."""
    if not shares:
        return 1.0
    s = sorted(shares, reverse=True)
    amp = 1.0
    if s[0] > 0.30:
        amp += (s[0] - 0.30) * 2.0
    if len(s) >= 2 and (s[0] + s[1]) > 0.50:
        amp += 0.10
    if len(s) >= 3 and (s[0] + s[1] + s[2]) > 0.70:
        amp += 0.10
    return amp


def _hhi(shares: Sequence[float]) -> float:
    """Herfindahl-Hirschman Index (sum of squared shares, ×10,000).
    HHI > 2500 = concentrated, HHI > 1500 = moderately concentrated."""
    return sum((s * 100) ** 2 for s in shares) if shares else 0.0


def _inverse_normal(u: float) -> float:
    """Stdlib-only Beasley-Springer-Moro inverse normal."""
    if u <= 0:
        u = 1e-9
    if u >= 1:
        u = 1 - 1e-9
    a = [
        -3.969683028665376e+01, 2.209460984245205e+02,
        -2.759285104469687e+02, 1.383577518672690e+02,
        -3.066479806614716e+01, 2.506628277459239e+00,
    ]
    b = [
        -5.447609879822406e+01, 1.615858368580409e+02,
        -1.556989798598866e+02, 6.680131188771972e+01,
        -1.328068155288572e+01,
    ]
    c = [
        -7.784894002430293e-03, -3.223964580411365e-01,
        -2.400758277161838e+00, -2.549732539343734e+00,
        4.374664141464968e+00, 2.938163982698783e+00,
    ]
    d = [
        7.784695709041462e-03, 3.224671290700398e-01,
        2.445134137142996e+00, 3.754408661907416e+00,
    ]
    plow = 0.02425
    phigh = 1 - plow
    if u < plow:
        q = math.sqrt(-2 * math.log(u))
        return (
            ((((c[0]*q+c[1])*q+c[2])*q+c[3])*q+c[4])*q+c[5]
        ) / ((((d[0]*q+d[1])*q+d[2])*q+d[3])*q+1)
    if u <= phigh:
        q = u - 0.5
        r = q * q
        return (
            ((((a[0]*r+a[1])*r+a[2])*r+a[3])*r+a[4])*r+a[5]
        ) * q / (((((b[0]*r+b[1])*r+b[2])*r+b[3])*r+b[4])*r+1)
    q = math.sqrt(-2 * math.log(1 - u))
    return -(
        ((((c[0]*q+c[1])*q+c[2])*q+c[3])*q+c[4])*q+c[5]
    ) / ((((d[0]*q+d[1])*q+d[2])*q+d[3])*q+1)


def _percentile(xs: Sequence[float], q: float) -> float:
    if not xs:
        return 0.0
    s = sorted(xs)
    idx = int(q * (len(s) - 1))
    return s[max(0, min(len(s) - 1, idx))]


# ────────────────────────────────────────────────────────────────────
# Main simulator
# ────────────────────────────────────────────────────────────────────

def run_payer_stress(
    *,
    target_name: str = "Target",
    mix: Sequence[PayerMixEntry],
    total_npr_usd: float,
    total_ebitda_usd: Optional[float] = None,
    horizon_years: int = 5,
    n_paths: int = 500,
    seed: int = 42,
    ebitda_pass_through: float = 0.70,
) -> PayerStressReport:
    """Monte Carlo rate-shock simulation.

    Per path per year per payer:
        * Sample rate move from Normal(mu, sigma) derived from the
          payer's prior quantiles.
        * Modulate by the payer's renewal_prob_12mo — payers whose
          contract isn't up for renewal this year see a dampened
          move (20% of full).
        * Add a tail-risk event (churn) with probability churn_prob
          that applies an extra -15% rate shock.

    Aggregate NPR impact per year = Σ (payer_share × rate_move) ×
    concentration_amplifier × total_npr_usd.

    EBITDA impact = NPR impact × ebitda_pass_through (default 70%;
    the variable portion that flows through to EBITDA given fixed
    clinical + facility costs).

    Returns a ``PayerStressReport`` with per-payer + per-year + total
    aggregates + verdict.
    """
    if not mix:
        return PayerStressReport(
            target_name=target_name,
            n_paths=0, horizon_years=horizon_years,
            total_npr_usd=total_npr_usd,
            total_ebitda_usd=total_ebitda_usd or 0.0,
            top_1_share=0.0, top_2_share=0.0, top_3_share=0.0,
            hhi_index=0.0, concentration_amplifier=1.0,
            verdict=PayerStressVerdict.PASS,
            headline="No payer mix supplied — stress test skipped.",
            rationale="Supply a target payer mix to run the simulator.",
        )

    rng = random.Random(seed)
    # Classify each payer and pull its prior
    classified: List[Tuple[PayerMixEntry, Optional[PayerPrior]]] = []
    unclassified_share = 0.0
    for entry in mix:
        prior = classify_payer(entry.payer_name)
        classified.append((entry, prior))
        if prior is None:
            unclassified_share += entry.share_of_npr

    shares = [e.share_of_npr for e in mix]
    top_sorted = sorted(shares, reverse=True)
    top_1 = top_sorted[0] if top_sorted else 0.0
    top_2 = sum(top_sorted[:2])
    top_3 = sum(top_sorted[:3])
    hhi = _hhi(shares)
    amp = _compute_concentration_amplifier(shares)

    # Precompute (mu, sigma) per payer
    params: List[Tuple[float, float, float, float]] = []
    # (mu, sigma, renewal_prob_12mo, churn_prob)
    for entry, prior in classified:
        if prior is None:
            # Default: mild mu, wide sigma
            mu = 0.0
            sigma = 0.04
            renewal = 0.5
            churn = 0.08
        else:
            mu, sigma = _lognormal_params_from_quantiles(
                prior.rate_move_p25,
                prior.rate_move_median,
                prior.rate_move_p75,
            )
            renewal = prior.renewal_prob_12mo
            churn = prior.churn_prob
        params.append((mu, sigma, renewal, churn))

    # Storage: per_path_yearly[path][year] = total NPR delta
    per_path_yearly: List[List[float]] = [
        [0.0] * horizon_years for _ in range(n_paths)
    ]
    # Per-payer accumulators: per_payer_rate_moves[i] = list[rate moves
    # experienced over horizon (one per path)]
    per_payer_rate_moves: List[List[float]] = [
        [] for _ in mix
    ]
    per_payer_npr_deltas: List[List[float]] = [
        [] for _ in mix
    ]

    for path_idx in range(n_paths):
        cumulative_per_payer = [0.0] * len(mix)
        for year in range(horizon_years):
            year_npr_delta = 0.0
            for i, entry in enumerate(mix):
                mu, sigma, renewal, churn = params[i]
                # Renewal gate — if not renewing this year, dampen the
                # move to 20% of full (year-over-year drift)
                z = _inverse_normal(rng.random())
                rate_move = mu + sigma * z
                if rng.random() > renewal:
                    rate_move *= 0.2
                # Tail churn
                if rng.random() < churn:
                    rate_move -= 0.15
                cumulative_per_payer[i] += rate_move
                # Effective rate on the payer's NPR: original rate
                # × (1 + cumulative_rate_move)^year vs (1 + 0)^year
                # Simpler approximation: NPR delta this year =
                # payer_share × total_npr × rate_move (applied on the
                # year's revenue)
                payer_npr = entry.share_of_npr * total_npr_usd
                year_npr_delta += payer_npr * rate_move
            # Apply concentration amplifier
            year_npr_delta *= amp
            per_path_yearly[path_idx][year] = year_npr_delta

        for i, entry in enumerate(mix):
            per_payer_rate_moves[i].append(cumulative_per_payer[i])
            per_payer_npr_deltas[i].append(
                cumulative_per_payer[i]
                * entry.share_of_npr * total_npr_usd,
            )

    # Per-payer roll-up
    per_payer_rows: List[PayerStressRow] = []
    for i, (entry, prior) in enumerate(classified):
        rates = per_payer_rate_moves[i]
        deltas = per_payer_npr_deltas[i]
        median_rate = _percentile(rates, 0.50)
        p10_rate = _percentile(rates, 0.10)
        p90_rate = _percentile(rates, 0.90)
        median_delta = _percentile(deltas, 0.50)
        p10_delta = _percentile(deltas, 0.10)
        p90_delta = _percentile(deltas, 0.90)

        if prior:
            narrative = (
                f"{prior.name} ({prior.category.value.replace('_', ' ')}): "
                f"cumulative rate move median {median_rate*100:+.2f}%, "
                f"tail (P10) {p10_rate*100:+.2f}%. "
                f"Negotiating leverage {int(prior.negotiating_leverage*100)}/100, "
                f"churn risk {int(prior.churn_prob*100)}%. "
                + (prior.behavior_notes or "")
            )
        else:
            narrative = (
                f"{entry.payer_name}: unclassified payer. "
                f"Falls back to neutral prior (μ=0, σ=4%). "
                f"Supply payer id for calibrated stress."
            )
        per_payer_rows.append(PayerStressRow(
            payer_name=entry.payer_name,
            payer_id=prior.payer_id if prior else None,
            category=prior.category.value if prior else None,
            share_of_npr=entry.share_of_npr,
            npr_attributed_usd=entry.share_of_npr * total_npr_usd,
            median_rate_move=median_rate,
            p10_rate_move=p10_rate,
            p90_rate_move=p90_rate,
            median_npr_delta_usd=median_delta,
            p10_npr_delta_usd=p10_delta,
            p90_npr_delta_usd=p90_delta,
            contract_renewal_date=entry.contract_renewal_date,
            negotiating_leverage=(
                prior.negotiating_leverage if prior else 0.5
            ),
            churn_prob=prior.churn_prob if prior else 0.08,
            narrative=narrative,
        ))

    # Per-year roll-up
    yearly_impact: List[YearlyNPRImpact] = []
    for y in range(horizon_years):
        year_deltas = [p[y] for p in per_path_yearly]
        p10 = _percentile(year_deltas, 0.10)
        p50 = _percentile(year_deltas, 0.50)
        p90 = _percentile(year_deltas, 0.90)
        med_ebitda = p50 * ebitda_pass_through
        p10_ebitda = p10 * ebitda_pass_through
        yearly_impact.append(YearlyNPRImpact(
            year=y + 1,
            p10_npr_delta_usd=p10,
            p50_npr_delta_usd=p50,
            p90_npr_delta_usd=p90,
            median_ebitda_impact_usd=med_ebitda,
            p10_ebitda_impact_usd=p10_ebitda,
        ))

    # Cumulative (terminal) aggregates
    cumulative = [sum(p) for p in per_path_yearly]
    cum_p10 = _percentile(cumulative, 0.10)
    cum_p50 = _percentile(cumulative, 0.50)
    cum_p90 = _percentile(cumulative, 0.90)
    cum_ebitda_median = cum_p50 * ebitda_pass_through
    cum_ebitda_p10 = cum_p10 * ebitda_pass_through

    # Verdict
    if total_ebitda_usd and total_ebitda_usd > 0:
        annual_ebitda_at_risk_pct = (
            abs(cum_ebitda_p10) / (total_ebitda_usd * horizon_years)
        )
    else:
        annual_ebitda_at_risk_pct = abs(cum_p10) / max(
            total_npr_usd * horizon_years, 1.0,
        )
    if annual_ebitda_at_risk_pct > 0.10 or top_1 > 0.40:
        verdict = PayerStressVerdict.FAIL
    elif annual_ebitda_at_risk_pct > 0.05 or top_1 > 0.30:
        verdict = PayerStressVerdict.WARNING
    elif annual_ebitda_at_risk_pct > 0.02 or top_1 > 0.20:
        verdict = PayerStressVerdict.CAUTION
    else:
        verdict = PayerStressVerdict.PASS

    # Risk score 0-100
    risk_score = min(100.0, max(0.0, (
        annual_ebitda_at_risk_pct * 400
        + max(0.0, top_1 - 0.20) * 150
        + (hhi / 10000) * 20
    )))

    # Headline
    worst_payer = min(
        per_payer_rows, key=lambda r: r.median_npr_delta_usd,
    ) if per_payer_rows else None
    if worst_payer and worst_payer.median_npr_delta_usd < 0:
        worst_msg = (
            f"{worst_payer.payer_name} drags cumulative NPR by "
            f"${worst_payer.median_npr_delta_usd/1e6:,.1f}M at median"
        )
    else:
        worst_msg = "no single payer materially negative"

    headline_parts: List[str] = []
    if verdict == PayerStressVerdict.FAIL:
        headline_parts.append(
            f"Payer concentration is material — P10 5-year EBITDA "
            f"drag is ${cum_ebitda_p10/1e6:,.1f}M."
        )
    elif verdict == PayerStressVerdict.WARNING:
        headline_parts.append(
            f"Payer mix carries elevated stress — P10 5-year "
            f"EBITDA drag ${cum_ebitda_p10/1e6:,.1f}M."
        )
    elif verdict == PayerStressVerdict.CAUTION:
        headline_parts.append(
            f"Payer mix is balanced but watch the top payer — "
            f"P10 drag ${cum_ebitda_p10/1e6:,.1f}M."
        )
    else:
        headline_parts.append(
            f"Payer mix passes stress test — even P10 case only "
            f"moves EBITDA by ${cum_ebitda_p10/1e6:,.1f}M."
        )
    headline_parts.append(worst_msg + ".")
    headline = " ".join(headline_parts)

    rationale_bits: List[str] = []
    rationale_bits.append(
        f"Top-1 share {top_1*100:.0f}%, Top-3 share {top_3*100:.0f}%, "
        f"HHI {hhi:.0f}."
    )
    rationale_bits.append(
        f"Concentration amplifier {amp:.2f}× applied to volatility."
    )
    if unclassified_share > 0.10:
        rationale_bits.append(
            f"{unclassified_share*100:.0f}% of mix unclassified — "
            f"add payer IDs to calibrate."
        )
    rationale = " ".join(rationale_bits)

    return PayerStressReport(
        target_name=target_name,
        n_paths=n_paths,
        horizon_years=horizon_years,
        total_npr_usd=total_npr_usd,
        total_ebitda_usd=total_ebitda_usd or 0.0,
        top_1_share=top_1, top_2_share=top_2, top_3_share=top_3,
        hhi_index=hhi,
        concentration_amplifier=amp,
        per_payer=sorted(
            per_payer_rows, key=lambda r: -r.share_of_npr,
        ),
        yearly_impact=yearly_impact,
        median_cumulative_npr_delta_usd=cum_p50,
        p10_cumulative_npr_delta_usd=cum_p10,
        p90_cumulative_npr_delta_usd=cum_p90,
        median_cumulative_ebitda_impact_usd=cum_ebitda_median,
        p10_cumulative_ebitda_impact_usd=cum_ebitda_p10,
        verdict=verdict,
        risk_score=risk_score,
        headline=headline,
        rationale=rationale,
        unclassified_share=unclassified_share,
    )


# ────────────────────────────────────────────────────────────────────
# Convenience — default mix for a generic acute hospital
# ────────────────────────────────────────────────────────────────────

def default_hospital_mix() -> List[PayerMixEntry]:
    """A generic 300-bed community hospital payer mix.

    Based on ~2024 HCRIS-median hospital reporting:
        Medicare FFS     ~ 34%
        Medicare Advantage ~ 18%
        Medicaid FFS     ~ 9%
        Medicaid managed ~ 10%
        UnitedHealthcare ~ 8%
        Anthem / Blues   ~ 10%
        Aetna            ~ 6%
        Cigna            ~ 4%
        Self-pay         ~ 1%
    """
    return [
        PayerMixEntry("Medicare FFS", 0.34,
                      contract_renewal_date="annual"),
        PayerMixEntry("Medicare Advantage", 0.18,
                      contract_renewal_date="2026-12-31"),
        PayerMixEntry("Medicaid FFS", 0.09),
        PayerMixEntry("Medicaid managed", 0.10,
                      contract_renewal_date="2027-06-30"),
        PayerMixEntry("UnitedHealthcare", 0.08,
                      contract_renewal_date="2026-09-30"),
        PayerMixEntry("Anthem", 0.10,
                      contract_renewal_date="2027-03-31"),
        PayerMixEntry("Aetna", 0.06,
                      contract_renewal_date="2028-01-31"),
        PayerMixEntry("Cigna", 0.04,
                      contract_renewal_date="2027-01-31"),
        PayerMixEntry("Self-pay", 0.01),
    ]
