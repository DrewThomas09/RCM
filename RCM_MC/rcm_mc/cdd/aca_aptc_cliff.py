"""NEW-30 ACA enhanced-APTC subsidy cliff.

The premium tax credit caps a marketplace enrollee's benchmark-plan premium at
an applicable percent of income. The enhanced schedule (ARPA / IRA) zeroed the
contribution below 150 percent of poverty, capped it at 8.5 percent, and extended
eligibility above 400 percent of poverty. That schedule expires at the end of
2025; the original schedule reverts to higher applicable percentages and restores
the 400 percent cliff, above which an enrollee loses all premium assistance.

This exhibit prices the net benchmark premium for a set of enrollees under both
the enhanced and the sunset schedules, surfaces the dollar and percent premium
shock, and flags the 400 percent cliff. KFF projects subsidized premium payments
rise about 114 percent on average when the enhanced credits lapse.

Statistical and deterministic. No LLM on any path.
"""
from __future__ import annotations

from typing import Any, Dict, List, Mapping, Sequence

from .exhibit import Exhibit, Flag, Footnote, Reconciliation, Series, safe_div
from .registry import CddFeature, register

FEATURE_ID = "NEW-30"

# 2024 federal poverty line for a single-person household (annual dollars).
FPL_BASE_SINGLE_2024 = 15060.0

# Applicable-percentage breakpoints: (FPL percent, applicable fraction of income).
# Linear interpolation within the range; see regime handling for the tails.
ENHANCED_BREAKS = [(150.0, 0.0), (200.0, 0.02), (250.0, 0.04), (300.0, 0.06), (400.0, 0.085)]
ORIGINAL_BREAKS = [
    (100.0, 0.0207), (133.0, 0.0310), (150.0, 0.0414), (200.0, 0.0652),
    (250.0, 0.0833), (300.0, 0.0983), (400.0, 0.0983),
]

ENHANCED_CAP = 0.085      # applicable percent never exceeds this under enhanced
CLIFF_FPL = 400.0         # original schedule gives no credit above this
PREMIUM_SHOCK_PCT = 0.20  # flag a net-premium rise above this share


def _interp(breaks: Sequence, fpl_pct: float) -> float:
    lo_pct, lo_val = breaks[0]
    if fpl_pct <= lo_pct:
        return lo_val
    for (p0, v0), (p1, v1) in zip(breaks, breaks[1:]):
        if fpl_pct <= p1:
            frac = safe_div(fpl_pct - p0, p1 - p0, default=0.0)
            return v0 + frac * (v1 - v0)
    return breaks[-1][1]


def applicable_percent(fpl_pct: float, regime: str) -> float | None:
    """Applicable percent of income, or None when the enrollee gets no credit."""
    if regime == "enhanced":
        if fpl_pct >= CLIFF_FPL:
            return ENHANCED_CAP
        return _interp(ENHANCED_BREAKS, fpl_pct)
    if regime == "sunset":
        if fpl_pct > CLIFF_FPL:
            return None  # the restored cliff: no premium assistance
        return _interp(ORIGINAL_BREAKS, fpl_pct)
    raise ValueError("regime must be 'enhanced' or 'sunset'")


def compute_aptc(
    fpl_pct: float,
    benchmark_premium: float,
    regime: str,
    *,
    fpl_base: float = FPL_BASE_SINGLE_2024,
) -> Dict[str, Any]:
    """Net benchmark premium and credit for one enrollee under one schedule."""
    if benchmark_premium < 0:
        raise ValueError("benchmark_premium must be non-negative")
    income = (fpl_pct / 100.0) * fpl_base
    pct = applicable_percent(fpl_pct, regime)
    if pct is None:
        required = benchmark_premium  # no credit, enrollee pays full benchmark
        aptc = 0.0
        eligible = False
    else:
        required = pct * income
        aptc = max(0.0, benchmark_premium - required)
        eligible = True
    net_premium = benchmark_premium - aptc
    return {
        "regime": regime,
        "fpl_pct": fpl_pct,
        "income": income,
        "applicable_pct": pct,
        "required_contribution": required,
        "aptc": aptc,
        "net_premium": net_premium,
        "eligible": eligible,
    }


def aca_aptc_cliff(
    enrollees: Sequence[Mapping[str, Any]],
    *,
    fpl_base: float = FPL_BASE_SINGLE_2024,
    source: str = "KFF marketplace tracker / ACA applicable-percentage tables",
    vintage: str = "",
    audience: str = "both",
) -> Exhibit:
    """Compare net benchmark premium under enhanced vs sunset credit schedules.

    ``enrollees``: records of {label?, fpl_pct, benchmark_premium}.
    """
    if not enrollees:
        raise ValueError("aca_aptc_cliff requires at least one enrollee")

    rows: List[Dict[str, Any]] = []
    flags: List[Flag] = []
    cliff_hits = 0
    for e in enrollees:
        fpl_pct = float(e["fpl_pct"])
        bench = float(e["benchmark_premium"])
        label = str(e.get("label", f"{fpl_pct:.0f} pct FPL"))
        enhanced = compute_aptc(fpl_pct, bench, "enhanced", fpl_base=fpl_base)
        sunset = compute_aptc(fpl_pct, bench, "sunset", fpl_base=fpl_base)
        delta = sunset["net_premium"] - enhanced["net_premium"]
        pct_change = safe_div(delta, enhanced["net_premium"], default=0.0)
        if not sunset["eligible"]:
            cliff_hits += 1
        rows.append({
            "label": label,
            "fpl_pct": fpl_pct,
            "benchmark_premium": bench,
            "enhanced_net": enhanced["net_premium"],
            "sunset_net": sunset["net_premium"],
            "delta": delta,
            "pct_change": pct_change,
            "sunset_eligible": sunset["eligible"],
            "enhanced": enhanced,
            "sunset": sunset,
        })

    if cliff_hits:
        flags.append(Flag(
            code="subsidy_cliff",
            severity="risk",
            message=(
                f"{cliff_hits} enrollee(s) above 400 percent of poverty lose all premium "
                f"assistance when the enhanced credits expire."
            ),
            source=source,
        ))
    worst_shock = max((r["pct_change"] for r in rows), default=0.0)
    if worst_shock >= PREMIUM_SHOCK_PCT:
        flags.append(Flag(
            code="premium_shock",
            severity="warn",
            message=(
                f"Net benchmark premium rises up to {worst_shock*100:.0f} percent for some "
                f"enrollees when the enhanced schedule reverts."
            ),
            source=source,
        ))

    enhanced_series = Series(name="Net premium under enhanced credits", kind="bar", points=[
        {"label": r["label"], "value": r["enhanced_net"]} for r in rows
    ])
    sunset_series = Series(name="Net premium after enhanced credits expire", kind="bar", points=[
        {"label": r["label"], "value": r["sunset_net"]} for r in rows
    ])
    contribution_line = Series(
        name="Required contribution percent by income", kind="line", internal_only=True,
        points=[{
            "label": r["label"],
            "enhanced": r["enhanced"]["applicable_pct"],
            "sunset": r["sunset"]["applicable_pct"],
        } for r in rows],
    )

    total_enhanced = sum(r["enhanced_net"] for r in rows)
    total_sunset = sum(r["sunset_net"] for r in rows)
    # Reconcile each regime: net premium plus credit equals benchmark.
    enh_check = sum(r["enhanced"]["net_premium"] + r["enhanced"]["aptc"] for r in rows)
    sun_check = sum(r["sunset"]["net_premium"] + r["sunset"]["aptc"] for r in rows)
    total_bench = sum(r["benchmark_premium"] for r in rows)
    reconciliations = [
        Reconciliation(
            identity="enhanced net premium plus credit equals benchmark",
            lhs=enh_check, rhs=total_bench, tolerance=1e-9,
        ),
        Reconciliation(
            identity="sunset net premium plus credit equals benchmark",
            lhs=sun_check, rhs=total_bench, tolerance=1e-9,
        ),
    ]

    footnote = Footnote(
        source=source,
        vintage=vintage or "not stated",
        assumptions=[
            "Benchmark plan is the second-lowest-cost silver; the credit caps the enrollee's benchmark premium.",
            "Enhanced schedule zeroes contribution below 150 percent of poverty, caps it at 8.5 percent, and extends above 400 percent.",
            "Sunset schedule restores the pre-ARPA applicable percentages and the 400 percent eligibility cliff.",
            f"Income is the FPL percent times the {fpl_base:,.0f} single-household poverty line.",
        ],
    )

    ex = Exhibit(
        feature_id=FEATURE_ID,
        title="ACA enhanced-APTC subsidy cliff",
        audience=audience,
        series=[enhanced_series, sunset_series, contribution_line],
        footnote=footnote,
        flags=flags,
        reconciliations=reconciliations,
        summary=(
            f"{len(rows)} enrollee(s). Net benchmark premium totals {total_enhanced:,.2f} "
            f"under enhanced credits, rising to {total_sunset:,.2f} when they expire."
        ),
        meta={
            "rows": rows,
            "total_enhanced_net": total_enhanced,
            "total_sunset_net": total_sunset,
            "cliff_hits": cliff_hits,
            "fpl_base": fpl_base,
        },
    )
    return ex.validate()


def _demo() -> Exhibit:
    # One enrollee at the 400 percent boundary keeps a smaller credit under the
    # sunset schedule; one just above 400 percent falls off the restored cliff.
    enrollees = [
        {"label": "400 pct FPL", "fpl_pct": 400.0, "benchmark_premium": 7000.0},
        {"label": "450 pct FPL", "fpl_pct": 450.0, "benchmark_premium": 7000.0},
    ]
    return aca_aptc_cliff(enrollees, source="Demo marketplace enrollees", vintage="2025")


register(
    CddFeature(
        feature_id=FEATURE_ID,
        title="ACA enhanced-APTC subsidy cliff",
        audience="both",
        demo=_demo,
    )
)
