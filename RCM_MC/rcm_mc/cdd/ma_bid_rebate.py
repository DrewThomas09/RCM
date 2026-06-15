"""NEW-27 Medicare Advantage bid / benchmark / rebate waterfall.

The core MA payment formula. CMS sets a county benchmark as a percent of
fee-for-service (FFS) spending by quartile (lowest-spending counties at 115
percent, highest at 95 percent). A four-plus star contract adds a quality bonus
(5 percent, or 10 percent in double-bonus counties) to the benchmark. A plan
bids what it needs to deliver Part A and B services; when the bid is below the
benchmark the plan keeps a rebate equal to a star-tier share (50 / 65 / 70
percent) of the spread, and that rebate must fund supplemental benefits, reduced
cost-sharing, or premium buy-downs. The portion CMS does not pay out as a rebate
is program savings versus the benchmark.

This module reproduces that decomposition as an auditable waterfall and a
benchmark-allocation bar, with reconciliations that prove the pieces tie to the
benchmark. The published KFF worked example (115 percent benchmark on $1,000
FFS, an $830 bid, 70 percent retention) is reproduced exactly in the golden test.

Statistical and deterministic. No LLM on any path.
"""
from __future__ import annotations

from typing import Any, Dict

from .exhibit import Exhibit, Flag, Footnote, Reconciliation, Series, safe_div
from .registry import CddFeature, register

FEATURE_ID = "NEW-27"

# Benchmark as a fraction of FFS by FFS-spending quartile (ACA). Quartile 1 is
# the lowest-spending quartile (highest benchmark); quartile 4 the highest.
QUARTILE_BENCHMARK = {1: 1.15, 2: 1.075, 3: 1.00, 4: 0.95}

QBP_BONUS = 0.05            # quality bonus added to benchmark for 4+ stars
QBP_DOUBLE_BONUS = 0.10     # double-bonus counties
QBP_STAR_THRESHOLD = 4.0


def rebate_pct_for_stars(stars: float) -> float:
    """Rebate retention share of (benchmark minus bid), by star tier."""
    if stars >= 4.5:
        return 0.70
    if stars >= 3.5:
        return 0.65
    return 0.50


def benchmark_pct(quartile: int, stars: float, *, double_bonus: bool, apply_qbp: bool) -> float:
    """Benchmark as a fraction of FFS, including the quality bonus when earned."""
    if quartile not in QUARTILE_BENCHMARK:
        raise ValueError(f"quartile must be one of {sorted(QUARTILE_BENCHMARK)}")
    base = QUARTILE_BENCHMARK[quartile]
    if apply_qbp and stars >= QBP_STAR_THRESHOLD:
        base += QBP_DOUBLE_BONUS if double_bonus else QBP_BONUS
    return base


def compute_components(
    *,
    ffs_percapita: float,
    quartile: int,
    stars: float,
    bid: float,
    double_bonus: bool = False,
    raf: float = 1.0,
    apply_qbp: bool = True,
) -> Dict[str, Any]:
    """Pure compute of the bid / benchmark / rebate decomposition.

    Returns benchmark, rebate, plan payment, enrollee premium, CMS-retained
    savings, and the risk-adjusted final payment. All per-member-per-month.
    """
    if ffs_percapita <= 0:
        raise ValueError("ffs_percapita must be positive")
    if bid < 0:
        raise ValueError("bid must be non-negative")
    if raf <= 0:
        raise ValueError("raf must be positive")

    bpct = benchmark_pct(quartile, stars, double_bonus=double_bonus, apply_qbp=apply_qbp)
    benchmark = ffs_percapita * bpct
    rpct = rebate_pct_for_stars(stars)

    if bid < benchmark:
        spread = benchmark - bid
        rebate = rpct * spread
        cms_retained = spread - rebate  # program savings vs benchmark
        plan_payment = bid + rebate
        enrollee_premium = 0.0
    else:
        spread = 0.0
        rebate = 0.0
        cms_retained = 0.0
        plan_payment = benchmark
        enrollee_premium = bid - benchmark  # enrollee makes up the difference

    final_payment = plan_payment * raf
    capped_bid = min(bid, benchmark)
    return {
        "ffs_percapita": ffs_percapita,
        "benchmark_pct": bpct,
        "benchmark": benchmark,
        "bid": bid,
        "capped_bid": capped_bid,
        "stars": stars,
        "rebate_pct": rpct,
        "spread": spread,
        "rebate": rebate,
        "cms_retained": cms_retained,
        "plan_payment": plan_payment,
        "enrollee_premium": enrollee_premium,
        "raf": raf,
        "final_payment": final_payment,
        "program_vs_ffs": plan_payment - ffs_percapita,
        "double_bonus": double_bonus,
        "apply_qbp": apply_qbp,
    }


def ma_bid_rebate(
    *,
    ffs_percapita: float,
    quartile: int,
    stars: float,
    bid: float,
    double_bonus: bool = False,
    raf: float = 1.0,
    apply_qbp: bool = True,
    source: str = "CMS MA Rate Announcement / county FFS benchmark",
    vintage: str = "",
    audience: str = "both",
) -> Exhibit:
    """Build the MA bid / benchmark / rebate exhibit for one county plan."""
    c = compute_components(
        ffs_percapita=ffs_percapita, quartile=quartile, stars=stars, bid=bid,
        double_bonus=double_bonus, raf=raf, apply_qbp=apply_qbp,
    )

    flags = []
    if stars >= QBP_STAR_THRESHOLD and apply_qbp:
        flags.append(Flag(
            code="qbp_earned",
            severity="info",
            message=(
                f"Contract at {stars:.1f} stars earns the quality bonus "
                f"({'10' if double_bonus else '5'} percent of benchmark)."
            ),
            source=source,
        ))
    if stars < 3.5:
        flags.append(Flag(
            code="low_star_rebate",
            severity="warn",
            message=(
                f"Below 3.5 stars the plan keeps only 50 percent of the spread, "
                f"the lowest rebate tier, which shrinks supplemental-benefit funding."
            ),
            source=source,
        ))
    if c["enrollee_premium"] > 0:
        flags.append(Flag(
            code="bid_above_benchmark",
            severity="risk",
            message=(
                f"Bid {c['bid']:,.2f} exceeds benchmark {c['benchmark']:,.2f}; the "
                f"enrollee pays the {c['enrollee_premium']:,.2f} difference as premium."
            ),
            source=source,
        ))
    if c["program_vs_ffs"] > 0 and c["enrollee_premium"] == 0:
        flags.append(Flag(
            code="program_cost_over_ffs",
            severity="warn",
            message=(
                f"Plan payment {c['plan_payment']:,.2f} exceeds FFS "
                f"{c['ffs_percapita']:,.2f}; the program pays more than fee-for-service here."
            ),
            source=source,
        ))

    # Payment-build waterfall: bid is the starting total, rebate adds to it, the
    # plan payment is the ending total. Totals blue, the rebate increase green.
    payment_waterfall = Series(name="Plan payment build", kind="waterfall", points=[
        {"label": "Plan bid", "value": c["bid"], "kind": "total", "color": "blue"},
        {"label": "Rebate retained", "value": c["rebate"], "kind": "delta", "color": "green"},
        {"label": "Plan payment", "value": c["plan_payment"], "kind": "total", "color": "blue"},
    ])
    # Benchmark allocation: where the benchmark dollar goes. Ties to benchmark.
    allocation = Series(name="Benchmark allocation", kind="bar", points=[
        {"label": "To plan as bid", "value": c["capped_bid"]},
        {"label": "To plan as rebate", "value": c["rebate"]},
        {"label": "Retained by CMS", "value": c["cms_retained"]},
    ])
    # FFS comparison baseline, for the program-cost-vs-FFS read.
    ffs_compare = Series(name="Payment vs FFS", kind="bar", points=[
        {"label": "FFS per capita", "value": c["ffs_percapita"]},
        {"label": "Benchmark", "value": c["benchmark"]},
        {"label": "Plan payment", "value": c["plan_payment"]},
    ])
    rebate_detail = Series(name="Rebate retention detail", kind="bar", internal_only=True, points=[
        {"label": "Spread", "value": c["spread"]},
        {"label": "Retention pct", "value": c["rebate_pct"]},
        {"label": "Rebate", "value": c["rebate"]},
    ])

    reconciliations = [
        Reconciliation(
            identity="rebate equals retention pct times spread",
            lhs=c["rebate"],
            rhs=c["rebate_pct"] * c["spread"],
            tolerance=1e-9,
        ),
        Reconciliation(
            identity="capped bid plus rebate plus CMS-retained equals benchmark",
            lhs=c["capped_bid"] + c["rebate"] + c["cms_retained"],
            rhs=c["benchmark"],
            tolerance=1e-9,
        ),
        Reconciliation(
            identity="plan payment equals capped bid plus rebate",
            lhs=c["plan_payment"],
            rhs=c["capped_bid"] + c["rebate"],
            tolerance=1e-9,
        ),
        Reconciliation(
            identity="enrollee premium equals bid above benchmark",
            lhs=c["enrollee_premium"],
            rhs=max(c["bid"] - c["benchmark"], 0.0),
            tolerance=1e-9,
        ),
    ]

    footnote = Footnote(
        source=source,
        vintage=vintage or "not stated",
        assumptions=[
            "Benchmark is FFS per capita times the quartile factor (115 / 107.5 / 100 / 95 percent), plus a quality bonus of 5 percent (10 in double-bonus counties) for 4-plus stars.",
            "Rebate is the star-tier retention share (50 / 65 / 70 percent) of benchmark minus bid; the remainder is program savings versus the benchmark.",
            "Rebate must fund supplemental benefits, reduced cost-sharing, or premium buy-downs, net of admin and margin.",
            "Final payment is risk-adjusted by the enrollee RAF over 1.0.",
        ],
    )

    save_txt = (
        f"costs {c['program_vs_ffs']:,.2f} above FFS"
        if c["program_vs_ffs"] > 0 else f"saves {-c['program_vs_ffs']:,.2f} versus FFS"
    )
    ex = Exhibit(
        feature_id=FEATURE_ID,
        title="MA bid, benchmark, and rebate waterfall",
        audience=audience,
        series=[payment_waterfall, allocation, ffs_compare, rebate_detail],
        footnote=footnote,
        flags=flags,
        reconciliations=reconciliations,
        summary=(
            f"Benchmark {c['benchmark']:,.2f}, bid {c['bid']:,.2f}, rebate "
            f"{c['rebate']:,.2f} at {c['rebate_pct']*100:.0f} percent retention. "
            f"Plan payment {c['plan_payment']:,.2f} {save_txt}."
        ),
        meta=c,
    )
    return ex.validate()


def _demo() -> Exhibit:
    # KFF worked example: 115 percent benchmark on $1,000 FFS = $1,150; a plan
    # bidding $830 with 70 percent retention keeps a $224 rebate. apply_qbp is
    # off here so the benchmark matches the published $1,150 figure exactly.
    return ma_bid_rebate(
        ffs_percapita=1000.0,
        quartile=1,
        stars=4.5,
        bid=830.0,
        apply_qbp=False,
        source="KFF Medicare Advantage payment illustration",
        vintage="2024",
    )


register(
    CddFeature(
        feature_id=FEATURE_ID,
        title="MA bid / benchmark / rebate waterfall",
        audience="both",
        demo=_demo,
    )
)
