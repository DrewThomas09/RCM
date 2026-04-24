"""Deal-level Monte Carlo engine.

For each Monte Carlo trial we draw:

    organic_growth_rate            ~ N(mu, sigma)   revenue CAGR
    denial_rate_improvement_pp     ~ N             denial-reduction uplift
    payer_mix_shift_commercial_pp  ~ N             shift in commercial mix
    reg_headwind_realization       ~ Beta(a, b)    0..1 fraction of RED
                                                   regulatory $ that actually
                                                   lands
    lease_escalator_pct            ~ Normal around mean
    physician_attrition_pct        ~ Beta
    cyber_incident_probability     ~ Bernoulli per year
    v28_revenue_compression_pct    ~ N centered at CMS 3.12%
    exit_multiple                  ~ Normal centered on peer median
    multiple_arbitrage             ~ N              entry_multiple − exit_multiple

Each trial computes:
    revenue_t = revenue_{t-1} × (1 + growth)
    ebitda_margin_t = base_margin
                      + denial_improvement_margin_effect
                      - reg_headwind_margin_hit
                      - lease_escalator_effect
                      - physician_attrition_effect
                      - cyber_reserve
                      - v28_revenue_compression × medicare_share
    ebitda_t = revenue_t × margin_t
    debt_balance_t = debt_t-1 − fcf_t
    exit_ev = ebitda_5 × exit_multiple
    exit_equity = exit_ev − debt_balance_5
    moic = exit_equity / equity_check
    irr = (moic)^(1/hold_years) − 1

Uses stdlib random — no numpy dependency. Runs 5k trials in <1s
on a laptop.
"""
from __future__ import annotations

import math
import random
import statistics
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple


DEFAULT_HOLD_YEARS = 5
DEFAULT_N_RUNS = 3000


# ── Scenario input dataclass ───────────────────────────────────────

@dataclass
class DealScenario:
    """Inputs a partner would type at deal-bid time.

    All distributional parameters default to industry-aggregate
    anchors; callers override per target. Every mean/sd is documented
    inline so a reviewer can tune the baseline."""
    # Deal structure
    enterprise_value_usd: float
    equity_check_usd: float
    debt_usd: float
    entry_multiple: float                    # EV / EBITDA at entry
    hold_years: int = DEFAULT_HOLD_YEARS

    # Baseline financials
    revenue_year0_usd: float = 0.0
    ebitda_year0_usd: float = 0.0
    medicare_share: float = 0.30             # for V28 impact scaling

    # Growth assumptions.
    organic_growth_mean: float = 0.04
    organic_growth_sd: float = 0.025

    # Denial-rate improvement. pp of revenue recovered. Default
    # mirrors the v1 bridge lever anchor ($8-15M on $400M NPR → 2pp
    # margin lift when denials cut in half).
    denial_improvement_pp_mean: float = 0.015
    denial_improvement_pp_sd: float = 0.008

    # Regulatory headwind realization. 0 means none of the flagged
    # RED $ lands; 1 means all of it lands. Beta parameters.
    reg_headwind_usd: float = 0.0            # total $ at risk from advisor
    reg_headwind_realization_alpha: float = 2.0
    reg_headwind_realization_beta: float = 3.0  # mean = 0.4, skewed

    # Lease escalator.
    lease_escalator_mean: float = 0.025
    lease_escalator_sd: float = 0.008
    lease_to_revenue_baseline: float = 0.04

    # Physician attrition (Cano / Envision pattern amplifier).
    physician_attrition_alpha: float = 1.5
    physician_attrition_beta: float = 8.0    # mean ~16%
    provider_concentration_top5: float = 0.30  # dampens / amplifies

    # Cyber — annual incident probability + expected loss.
    cyber_incident_prob_per_year: float = 0.05
    cyber_expected_loss_usd_if_incident: float = 5_000_000

    # V28 recalibration — revenue compression if MA-risk exposed.
    v28_compression_mean: float = 0.0312     # CMS aggregate projection
    v28_compression_sd: float = 0.015

    # Exit multiple.
    exit_multiple_mean: float = 8.5
    exit_multiple_sd: float = 1.5

    # Multiple arbitrage drift — typically negative (entry premium).
    multiple_arb_mean: float = 0.0

    # RNG seed.
    seed: int = 42


# ── Result dataclasses ────────────────────────────────────────────

@dataclass
class YearBand:
    year: int
    p10: float
    p25: float
    p50: float
    p75: float
    p90: float
    mean: float

    def to_dict(self) -> Dict[str, Any]:
        return self.__dict__.copy()


@dataclass
class MOICBucket:
    lower: float
    upper: float
    probability: float
    count: int

    def to_dict(self) -> Dict[str, Any]:
        return self.__dict__.copy()


@dataclass
class DriverContribution:
    driver: str
    mean_impact_usd: float
    share_of_variance: float         # 0..1, sums across drivers ≤ 1

    def to_dict(self) -> Dict[str, Any]:
        return self.__dict__.copy()


@dataclass
class DriverAttribution:
    contributions: List[DriverContribution] = field(default_factory=list)
    unexplained_share: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "contributions": [c.to_dict() for c in self.contributions],
            "unexplained_share": self.unexplained_share,
        }


@dataclass
class StressResult:
    driver: str
    shock_label: str
    shock_delta_pct: float
    base_moic: float
    stressed_moic: float
    moic_impact: float                 # stressed - base

    def to_dict(self) -> Dict[str, Any]:
        return self.__dict__.copy()


@dataclass
class DealMCResult:
    scenario_name: str
    n_runs: int
    hold_years: int

    # Distributions across hold_years.
    revenue_bands: List[YearBand] = field(default_factory=list)
    ebitda_bands: List[YearBand] = field(default_factory=list)

    # Exit.
    moic_p10: float = 0.0
    moic_p25: float = 0.0
    moic_p50: float = 0.0
    moic_p75: float = 0.0
    moic_p90: float = 0.0
    moic_mean: float = 0.0

    irr_p10: float = 0.0
    irr_p25: float = 0.0
    irr_p50: float = 0.0
    irr_p75: float = 0.0
    irr_p90: float = 0.0
    irr_mean: float = 0.0

    prob_sub_1x: float = 0.0
    prob_sub_2x: float = 0.0
    prob_over_3x: float = 0.0

    moic_histogram: List[MOICBucket] = field(default_factory=list)
    attribution: Optional[DriverAttribution] = None
    stress_results: List[StressResult] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "scenario_name": self.scenario_name,
            "n_runs": self.n_runs,
            "hold_years": self.hold_years,
            "revenue_bands": [b.to_dict() for b in self.revenue_bands],
            "ebitda_bands": [b.to_dict() for b in self.ebitda_bands],
            "moic_p10": self.moic_p10, "moic_p25": self.moic_p25,
            "moic_p50": self.moic_p50, "moic_p75": self.moic_p75,
            "moic_p90": self.moic_p90, "moic_mean": self.moic_mean,
            "irr_p10": self.irr_p10, "irr_p25": self.irr_p25,
            "irr_p50": self.irr_p50, "irr_p75": self.irr_p75,
            "irr_p90": self.irr_p90, "irr_mean": self.irr_mean,
            "prob_sub_1x": self.prob_sub_1x,
            "prob_sub_2x": self.prob_sub_2x,
            "prob_over_3x": self.prob_over_3x,
            "moic_histogram": [b.to_dict() for b in self.moic_histogram],
            "attribution": (
                self.attribution.to_dict() if self.attribution else None
            ),
            "stress_results": [s.to_dict() for s in self.stress_results],
        }


# ── Statistical helpers ───────────────────────────────────────────

def _percentile(values: Sequence[float], q: float) -> float:
    if not values:
        return 0.0
    srt = sorted(values)
    n = len(srt)
    if n == 1:
        return srt[0]
    # Linear-interpolation percentile (matches numpy default).
    pos = (n - 1) * q
    lo = int(math.floor(pos))
    hi = int(math.ceil(pos))
    if lo == hi:
        return srt[lo]
    weight = pos - lo
    return srt[lo] * (1 - weight) + srt[hi] * weight


def _band_for_year(values: Sequence[float], year: int) -> YearBand:
    return YearBand(
        year=year,
        p10=_percentile(values, 0.10),
        p25=_percentile(values, 0.25),
        p50=_percentile(values, 0.50),
        p75=_percentile(values, 0.75),
        p90=_percentile(values, 0.90),
        mean=statistics.fmean(values) if values else 0.0,
    )


def _beta_sample(rng: random.Random, a: float, b: float) -> float:
    """Sample from Beta(a, b). stdlib has this."""
    return rng.betavariate(a, b)


def _histogram(values: Sequence[float], bins: Sequence[Tuple[float, float]]) -> List[MOICBucket]:
    n = len(values) or 1
    out: List[MOICBucket] = []
    for lo, hi in bins:
        cnt = sum(1 for v in values if lo <= v < hi)
        out.append(MOICBucket(
            lower=lo, upper=hi,
            probability=cnt / n, count=cnt,
        ))
    return out


def _default_moic_bins() -> List[Tuple[float, float]]:
    return [
        (0.0, 0.5), (0.5, 1.0), (1.0, 1.5), (1.5, 2.0),
        (2.0, 2.5), (2.5, 3.0), (3.0, 4.0), (4.0, 10.0),
    ]


# ── One trial ─────────────────────────────────────────────────────

def _draw_scenario(
    scn: DealScenario, rng: random.Random,
) -> Dict[str, Any]:
    return {
        "organic_growth": rng.gauss(
            scn.organic_growth_mean, scn.organic_growth_sd,
        ),
        "denial_improvement_pp": max(0.0, rng.gauss(
            scn.denial_improvement_pp_mean,
            scn.denial_improvement_pp_sd,
        )),
        "reg_realization": _beta_sample(
            rng,
            scn.reg_headwind_realization_alpha,
            scn.reg_headwind_realization_beta,
        ),
        "lease_escalator": max(0.0, rng.gauss(
            scn.lease_escalator_mean, scn.lease_escalator_sd,
        )),
        "physician_attrition": _beta_sample(
            rng,
            scn.physician_attrition_alpha,
            scn.physician_attrition_beta,
        ),
        "cyber_incidents": [
            rng.random() < scn.cyber_incident_prob_per_year
            for _ in range(scn.hold_years)
        ],
        "v28_compression": max(0.0, rng.gauss(
            scn.v28_compression_mean, scn.v28_compression_sd,
        )),
        "exit_multiple": max(3.0, rng.gauss(
            scn.exit_multiple_mean, scn.exit_multiple_sd,
        )),
        "multiple_arb": rng.gauss(scn.multiple_arb_mean, 0.5),
    }


def _simulate_one(
    scn: DealScenario, draw: Dict[str, Any],
) -> Dict[str, Any]:
    """Run one trial and return the path + exit summary."""
    revenues = [scn.revenue_year0_usd]
    ebitdas = [scn.ebitda_year0_usd]
    margin0 = (
        scn.ebitda_year0_usd / scn.revenue_year0_usd
        if scn.revenue_year0_usd > 0 else 0.15
    )

    growth = draw["organic_growth"]
    denial_impr = draw["denial_improvement_pp"]
    reg_real = draw["reg_realization"]
    lease_esc = draw["lease_escalator"]
    attr = draw["physician_attrition"]
    v28 = draw["v28_compression"]
    cyber_events = draw["cyber_incidents"]

    # Reg headwind is a flat $ hit per year × realization fraction.
    # Spread evenly across hold to match typical reg-erosion profile.
    reg_per_year = (
        scn.reg_headwind_usd * reg_real / scn.hold_years
        if scn.hold_years > 0 else 0.0
    )
    # Lease growth compounds; start at baseline lease/revenue ratio.
    lease_ratio = scn.lease_to_revenue_baseline

    for y in range(1, scn.hold_years + 1):
        # Revenue grows; attrition takes a haircut weighted by
        # concentration (top5 × attrition affects more revenue).
        attrition_haircut = attr * scn.provider_concentration_top5
        effective_growth = growth - attrition_haircut
        new_rev = revenues[-1] * (1 + effective_growth)
        # Apply V28 compression to medicare-exposed portion.
        new_rev = new_rev * (1 - v28 * scn.medicare_share)

        # Margin evolves: denial improvement flows to margin; lease
        # escalator grows lease/revenue ratio so margin shrinks;
        # cyber incident takes a one-time hit.
        lease_ratio = lease_ratio * (1 + lease_esc) / (1 + effective_growth)
        # Denial improvement is a margin uplift that saturates after
        # year 2 (partners get the easy wins first).
        denial_uplift_y = denial_impr * min(1.0, y / 2.0)
        margin_y = (
            margin0
            + denial_uplift_y
            - (lease_ratio - scn.lease_to_revenue_baseline)
        )
        # Reg headwind: subtract from absolute EBITDA (pre-margin).
        ebitda_y = new_rev * max(0.0, margin_y) - reg_per_year
        if cyber_events[y - 1]:
            ebitda_y -= scn.cyber_expected_loss_usd_if_incident

        revenues.append(new_rev)
        ebitdas.append(ebitda_y)

    # Exit.
    exit_ebitda = ebitdas[-1]
    exit_ev = exit_ebitda * draw["exit_multiple"]
    # Simple debt paydown: 50% of cumulative EBITDA goes to debt.
    cum_ebitda = sum(ebitdas[1:])
    debt_paydown = min(scn.debt_usd, 0.5 * cum_ebitda)
    exit_debt = max(0.0, scn.debt_usd - debt_paydown)
    exit_equity = max(0.0, exit_ev - exit_debt)

    moic = (
        exit_equity / scn.equity_check_usd
        if scn.equity_check_usd > 0 else 0.0
    )
    irr = (
        (moic ** (1 / scn.hold_years)) - 1
        if moic > 0 and scn.hold_years > 0 else -1.0
    )

    return {
        "revenues": revenues,
        "ebitdas": ebitdas,
        "exit_ev": exit_ev,
        "exit_equity": exit_equity,
        "moic": moic,
        "irr": irr,
        "draw": draw,
    }


# ── Attribution ───────────────────────────────────────────────────

def _attribute_drivers(
    trials: List[Dict[str, Any]], base_scn: DealScenario,
) -> DriverAttribution:
    """Variance decomposition by correlation² across trials.

    Each driver's share-of-variance ≈ r² with the MOIC distribution,
    normalised so the shares sum to the explained variance. The
    unexplained residual is surfaced separately."""
    if not trials:
        return DriverAttribution()
    moics = [t["moic"] for t in trials]
    moic_mean = statistics.fmean(moics)
    moic_var = statistics.pvariance(moics, moic_mean)
    if moic_var <= 0:
        return DriverAttribution()
    drivers = (
        ("organic_growth", "Organic growth"),
        ("denial_improvement_pp", "Denial-rate improvement"),
        ("reg_realization", "Regulatory headwind realization"),
        ("lease_escalator", "Lease escalator"),
        ("physician_attrition", "Physician attrition"),
        ("v28_compression", "V28 (MA) compression"),
        ("exit_multiple", "Exit multiple"),
    )
    contributions: List[DriverContribution] = []
    sum_r2 = 0.0
    for key, label in drivers:
        xs = [t["draw"][key] for t in trials]
        x_mean = statistics.fmean(xs)
        x_var = statistics.pvariance(xs, x_mean)
        if x_var <= 0:
            continue
        cov = statistics.fmean(
            [(xs[i] - x_mean) * (moics[i] - moic_mean)
             for i in range(len(xs))],
        )
        r = cov / math.sqrt(x_var * moic_var)
        r2 = r * r
        sum_r2 += r2
        # Mean impact: dEBITDA_exit / dX at first-order approx —
        # we estimate by linear regression slope × std(X).
        slope = cov / x_var
        mean_impact = slope * math.sqrt(x_var)
        contributions.append(DriverContribution(
            driver=label,
            mean_impact_usd=mean_impact * base_scn.equity_check_usd,
            share_of_variance=0.0,  # filled below
        ))
    if sum_r2 <= 0:
        return DriverAttribution()
    # Normalise r² shares; cap sum at 1.0 (they may exceed 1 if
    # drivers correlate — cap preserves interpretability).
    total = min(sum_r2, 1.0)
    unexplained = max(0.0, 1.0 - sum_r2)
    for c, (key, _) in zip(contributions, drivers):
        xs = [t["draw"][key] for t in trials]
        x_mean = statistics.fmean(xs)
        x_var = statistics.pvariance(xs, x_mean)
        cov = statistics.fmean(
            [(xs[i] - x_mean) * (moics[i] - moic_mean)
             for i in range(len(xs))],
        )
        r = cov / math.sqrt(x_var * moic_var) if x_var > 0 else 0
        c.share_of_variance = (r * r) / sum_r2 * total
    # Sort by share descending.
    contributions.sort(key=lambda c: -c.share_of_variance)
    return DriverAttribution(
        contributions=contributions,
        unexplained_share=unexplained,
    )


# ── Stress tests ──────────────────────────────────────────────────

def stress_test_drivers(
    scn: DealScenario,
    *,
    n_runs: int = 500,
    shocks: Optional[Dict[str, float]] = None,
) -> List[StressResult]:
    """One-at-a-time sensitivity. For each driver, shock its mean
    by ``shocks[driver]`` (default: +1 standard-deviation move for
    normal drivers, +20% for bounded ones), re-run the MC, and
    report the MOIC delta. Produces the sensitivity tornado."""
    if shocks is None:
        shocks = {}
    base_result = run_deal_monte_carlo(
        scn, n_runs=n_runs, attribute=False, stress=False,
    )
    base_moic = base_result.moic_p50
    out: List[StressResult] = []
    # For each driver, perturb.
    perturbations = [
        ("organic_growth_mean",
         "Organic growth −1σ", -scn.organic_growth_sd),
        ("denial_improvement_pp_mean",
         "Denial improvement −50%",
         -scn.denial_improvement_pp_mean * 0.5),
        ("reg_headwind_usd",
         "Reg headwind +$50M", 50_000_000),
        ("lease_escalator_mean",
         "Lease escalator +100bps", 0.01),
        ("v28_compression_mean",
         "V28 compression +100bps", 0.01),
        ("exit_multiple_mean",
         "Exit multiple −1.0x", -1.0),
        ("cyber_incident_prob_per_year",
         "Cyber prob → 15%", 0.10),
    ]
    for field_name, label, delta in perturbations:
        try:
            kwargs = {f.name: getattr(scn, f.name)
                      for f in _dc_fields(scn)}
            kwargs[field_name] = getattr(scn, field_name) + delta
            stressed_scn = DealScenario(**kwargs)
            stressed = run_deal_monte_carlo(
                stressed_scn, n_runs=n_runs,
                attribute=False, stress=False,
            )
            out.append(StressResult(
                driver=label,
                shock_label=label,
                shock_delta_pct=0.0,  # encoded in the label
                base_moic=base_moic,
                stressed_moic=stressed.moic_p50,
                moic_impact=stressed.moic_p50 - base_moic,
            ))
        except Exception:  # noqa: BLE001 — individual stress failure
            continue
    out.sort(key=lambda s: s.moic_impact)
    return out


def _dc_fields(scn: Any):
    """Iterate over dataclass fields — import dataclasses lazily."""
    import dataclasses
    return dataclasses.fields(scn)


# ── Entry point ───────────────────────────────────────────────────

def run_deal_monte_carlo(
    scn: DealScenario,
    *,
    n_runs: int = DEFAULT_N_RUNS,
    scenario_name: str = "Base",
    attribute: bool = True,
    stress: bool = True,
) -> DealMCResult:
    """Run the Monte Carlo. Returns the full :class:`DealMCResult`.

    ``n_runs=3000`` is the sweet spot — attribution stabilises,
    runtime stays <1s on a laptop. ``attribute`` + ``stress`` are
    independent flags; both default True.
    """
    rng = random.Random(scn.seed)
    trials: List[Dict[str, Any]] = []
    for _ in range(n_runs):
        draw = _draw_scenario(scn, rng)
        trial = _simulate_one(scn, draw)
        trials.append(trial)

    revenues_by_year = [[t["revenues"][y] for t in trials]
                        for y in range(scn.hold_years + 1)]
    ebitdas_by_year = [[t["ebitdas"][y] for t in trials]
                       for y in range(scn.hold_years + 1)]
    moics = sorted(t["moic"] for t in trials)
    irrs = sorted(t["irr"] for t in trials)

    result = DealMCResult(
        scenario_name=scenario_name,
        n_runs=n_runs,
        hold_years=scn.hold_years,
        revenue_bands=[
            _band_for_year(revenues_by_year[y], y)
            for y in range(scn.hold_years + 1)
        ],
        ebitda_bands=[
            _band_for_year(ebitdas_by_year[y], y)
            for y in range(scn.hold_years + 1)
        ],
        moic_p10=_percentile(moics, 0.10),
        moic_p25=_percentile(moics, 0.25),
        moic_p50=_percentile(moics, 0.50),
        moic_p75=_percentile(moics, 0.75),
        moic_p90=_percentile(moics, 0.90),
        moic_mean=statistics.fmean(moics) if moics else 0.0,
        irr_p10=_percentile(irrs, 0.10),
        irr_p25=_percentile(irrs, 0.25),
        irr_p50=_percentile(irrs, 0.50),
        irr_p75=_percentile(irrs, 0.75),
        irr_p90=_percentile(irrs, 0.90),
        irr_mean=statistics.fmean(irrs) if irrs else 0.0,
        prob_sub_1x=sum(1 for m in moics if m < 1.0) / max(len(moics), 1),
        prob_sub_2x=sum(1 for m in moics if m < 2.0) / max(len(moics), 1),
        prob_over_3x=sum(1 for m in moics if m >= 3.0) / max(len(moics), 1),
        moic_histogram=_histogram(moics, _default_moic_bins()),
    )
    if attribute:
        result.attribution = _attribute_drivers(trials, scn)
    if stress:
        result.stress_results = stress_test_drivers(
            scn, n_runs=max(500, n_runs // 4),
        )
    return result
