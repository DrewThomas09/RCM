"""NEW-28 Star-rating QBP sensitivity.

A Medicare Advantage contract's star rating drives two payment levers at once:
the quality bonus payment (4-plus stars adds 5 percent to the benchmark, 10 in
double-bonus counties) and the rebate-retention tier (50 / 65 / 70 percent of
the spread). Losing 4-star status removes the bonus and drops the retention
share, so plan payment can fall sharply on a half-star move. The published case
is CVS / Aetna's National PPO sliding from 4.5 to 3.5 stars, which contributed to
a roughly 40 percent year-over-year operating-income drop.

This exhibit prices plan payment across a set of star scenarios for one county
plan, holding FFS, quartile, and bid fixed, and surfaces the payment cliff when a
scenario crosses the 4-star quality-bonus threshold. It reuses the NEW-27 bid /
benchmark / rebate engine so the two exhibits never diverge.

Statistical and deterministic. No LLM on any path.
"""
from __future__ import annotations

from typing import Any, Dict, List, Sequence

from .exhibit import Exhibit, Flag, Footnote, Reconciliation, Series, safe_div
from .ma_bid_rebate import QBP_STAR_THRESHOLD, compute_components
from .registry import CddFeature, register

FEATURE_ID = "NEW-28"
DEFAULT_SCENARIOS = (5.0, 4.5, 4.0, 3.5, 3.0)


def star_qbp_sensitivity(
    *,
    ffs_percapita: float,
    quartile: int,
    bid: float,
    scenarios: Sequence[float] = DEFAULT_SCENARIOS,
    double_bonus: bool = False,
    raf: float = 1.0,
    current_stars: float | None = None,
    source: str = "CMS Star Ratings plus MA county benchmark",
    vintage: str = "",
    audience: str = "both",
) -> Exhibit:
    """Price plan payment across star scenarios and flag the 4-star cliff."""
    if not scenarios:
        raise ValueError("star_qbp_sensitivity requires at least one scenario")

    rows: List[Dict[str, Any]] = []
    for stars in scenarios:
        c = compute_components(
            ffs_percapita=ffs_percapita, quartile=quartile, stars=stars, bid=bid,
            double_bonus=double_bonus, raf=raf, apply_qbp=True,
        )
        rows.append({
            "stars": stars,
            "benchmark": c["benchmark"],
            "rebate_pct": c["rebate_pct"],
            "rebate": c["rebate"],
            "plan_payment": c["plan_payment"],
            "earns_qbp": stars >= QBP_STAR_THRESHOLD,
        })

    by_star = {r["stars"]: r for r in rows}
    payments = [r["plan_payment"] for r in rows]
    best = max(payments)
    worst = min(payments)
    swing = best - worst

    flags: List[Flag] = []
    # Does any adjacent scenario pair straddle the 4-star quality-bonus threshold?
    ordered = sorted(rows, key=lambda r: r["stars"])
    crosses = any(
        ordered[i]["stars"] < QBP_STAR_THRESHOLD <= ordered[i + 1]["stars"]
        for i in range(len(ordered) - 1)
    )
    if crosses:
        flags.append(Flag(
            code="crosses_4star_cliff",
            severity="risk",
            message=(
                "Scenarios straddle the 4-star quality-bonus threshold; crossing "
                "it removes the 5 percent bonus and cuts rebate retention."
            ),
            source=source,
        ))

    downgrade_loss = None
    if current_stars is not None:
        cur = compute_components(
            ffs_percapita=ffs_percapita, quartile=quartile, stars=current_stars,
            bid=bid, double_bonus=double_bonus, raf=raf, apply_qbp=True,
        )
        below = [r for r in rows if r["stars"] < current_stars]
        if below:
            nearest = max(below, key=lambda r: r["stars"])
            downgrade_loss = cur["plan_payment"] - nearest["plan_payment"]
            if downgrade_loss > 0:
                flags.append(Flag(
                    code="downgrade_payment_loss",
                    severity="warn",
                    message=(
                        f"A drop from {current_stars:.1f} to {nearest['stars']:.1f} stars "
                        f"cuts plan payment by {downgrade_loss:,.2f} per member per month."
                    ),
                    source=source,
                ))

    payment_steps = Series(name="Plan payment by star tier", kind="bar", points=[
        {"label": f"{r['stars']:.1f} stars", "value": r["plan_payment"]} for r in rows
    ])
    rebate_steps = Series(name="Rebate by star tier", kind="bar", points=[
        {"label": f"{r['stars']:.1f} stars", "value": r["rebate"]} for r in rows
    ])
    retention_steps = Series(
        name="Retention share by star tier", kind="bar", internal_only=True,
        points=[{"label": f"{r['stars']:.1f} stars", "value": r["rebate_pct"]} for r in rows],
    )

    # Reconcile: the payment swing equals best minus worst across scenarios.
    reconciliations = [
        Reconciliation(
            identity="payment swing equals best minus worst scenario",
            lhs=swing,
            rhs=best - worst,
            tolerance=1e-9,
        ),
    ]

    footnote = Footnote(
        source=source,
        vintage=vintage or "not stated",
        assumptions=[
            "Plan payment uses the NEW-27 bid, benchmark, and rebate engine with the quality bonus applied.",
            "Quality bonus adds 5 percent to the benchmark at 4-plus stars, 10 percent in double-bonus counties.",
            "Rebate retention is 50 percent below 3.5 stars, 65 percent at 3.5 to 4.0, and 70 percent at 4.5-plus.",
            "FFS, quartile, and bid are held fixed across scenarios so the swing is the pure star effect.",
        ],
    )

    ex = Exhibit(
        feature_id=FEATURE_ID,
        title="Star-rating QBP payment sensitivity",
        audience=audience,
        series=[payment_steps, rebate_steps, retention_steps],
        footnote=footnote,
        flags=flags,
        reconciliations=reconciliations,
        summary=(
            f"Plan payment ranges {worst:,.2f} to {best:,.2f} across "
            f"{len(rows)} star scenarios, a {swing:,.2f} per-member swing."
        ),
        meta={
            "rows": rows,
            "by_star": by_star,
            "best_payment": best,
            "worst_payment": worst,
            "swing": swing,
            "current_stars": current_stars,
            "downgrade_loss": downgrade_loss,
        },
    )
    return ex.validate()


def _demo() -> Exhibit:
    # National-PPO style case: a 4.5-star contract whose downgrade to 3.5 strips
    # both the quality bonus and the top rebate tier.
    return star_qbp_sensitivity(
        ffs_percapita=1000.0,
        quartile=1,
        bid=830.0,
        current_stars=4.5,
        source="Demo MA county benchmark with star scenarios",
        vintage="2025",
    )


register(
    CddFeature(
        feature_id=FEATURE_ID,
        title="Star-rating QBP payment sensitivity",
        audience="both",
        demo=_demo,
    )
)
