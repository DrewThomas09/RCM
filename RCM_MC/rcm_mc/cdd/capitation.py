"""NEW-20 Capitation / lives model with the MSSP shared-savings waterfall.

The capitation archetype is the most rule-bound of the five: CMS regulation
fixes most of the mechanics. Revenue is attributed lives carried as
member-months, priced at a risk-adjusted PMPM:

    risk-adjusted PMPM = base benchmark PMPM * RAF
    revenue            = risk-adjusted PMPM * member-months

Two regulatory gates then apply. The medical loss ratio test floors the share
of premium that must go to care (85 percent for Medicaid managed care and MA);
below it the plan owes a remittance. The MSSP shared-savings waterfall compares
actual expenditure to a benchmark, tests the gap against the minimum savings (or
loss) rate, and shares the result at the track's sharing rate scaled by quality.

This module computes all three and reconciles revenue against its PMPM identity
so a test can prove the arithmetic ties out.

Statistical and deterministic. No LLM on any path.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from .exhibit import Exhibit, Flag, Footnote, Reconciliation, Series, safe_div
from .registry import CddFeature, register

FEATURE_ID = "NEW-20"
MLR_FLOOR = 0.85  # ACA / CMS statutory floor


def capitation_revenue(
    attributed_lives: float,
    months: float,
    base_pmpm: float,
    raf: float,
) -> Dict[str, float]:
    """Risk-adjusted capitation revenue from lives, months, base PMPM, and RAF."""
    if attributed_lives < 0 or months < 0 or base_pmpm < 0:
        raise ValueError("lives, months, and base_pmpm must be non-negative")
    if raf < 0:
        raise ValueError("RAF must be non-negative")
    member_months = attributed_lives * months
    risk_adjusted_pmpm = base_pmpm * raf
    revenue = risk_adjusted_pmpm * member_months
    return {
        "member_months": member_months,
        "risk_adjusted_pmpm": risk_adjusted_pmpm,
        "revenue": revenue,
    }


def mlr_test(
    clinical_spend: float,
    quality_improvement_spend: float,
    premium: float,
    *,
    floor: float = MLR_FLOOR,
) -> Dict[str, float]:
    """Medical loss ratio and the remittance owed when it falls below the floor.

    MLR counts clinical plus quality-improvement spend over premium. A plan
    below the floor owes the shortfall times premium back to the payer.
    """
    if premium <= 0:
        raise ValueError("premium must be positive")
    mlr = safe_div(clinical_spend + quality_improvement_spend, premium, default=0.0)
    remittance = max(0.0, (floor - mlr)) * premium
    return {"mlr": mlr, "below_floor": mlr < floor, "remittance": remittance}


def shared_savings_waterfall(
    benchmark: float,
    actual: float,
    *,
    msr: float,
    sharing_rate: float,
    quality_score: float = 1.0,
    two_sided: bool = False,
    mlr_threshold: Optional[float] = None,
    savings_cap_pct: Optional[float] = None,
    loss_cap_pct: Optional[float] = None,
) -> Dict[str, Any]:
    """MSSP shared-savings (and shared-loss) settlement.

    ``benchmark`` is expected expenditure, ``actual`` is realized. Gross savings
    are ``benchmark - actual`` (positive is savings). Savings count only once the
    gap clears the minimum savings rate ``msr``; earned savings are then
    ``gross * sharing_rate * quality_score``, capped at ``savings_cap_pct`` of
    benchmark. Under a two-sided model, losses past the minimum loss rate
    ``mlr_threshold`` are repaid at the loss-sharing rate ``1 - sharing_rate``,
    capped at ``loss_cap_pct`` of benchmark.
    """
    if benchmark <= 0:
        raise ValueError("benchmark must be positive")
    if not (0.0 <= sharing_rate <= 1.0):
        raise ValueError("sharing_rate must be in [0, 1]")
    if not (0.0 <= quality_score <= 1.0):
        raise ValueError("quality_score must be in [0, 1]")

    gross = benchmark - actual
    gross_pct = gross / benchmark
    settlement = 0.0
    status = "neutral"

    if gross >= 0:
        if gross_pct >= msr:
            earned = gross * sharing_rate * quality_score
            if savings_cap_pct is not None:
                earned = min(earned, benchmark * savings_cap_pct)
            settlement = earned
            status = "savings_earned"
        else:
            status = "below_msr"
    else:
        loss = -gross
        loss_pct = loss / benchmark
        if two_sided:
            threshold = mlr_threshold if mlr_threshold is not None else msr
            if loss_pct >= threshold:
                loss_share_rate = 1.0 - sharing_rate
                owed = loss * loss_share_rate
                if loss_cap_pct is not None:
                    owed = min(owed, benchmark * loss_cap_pct)
                settlement = -owed
                status = "loss_owed"
            else:
                status = "below_mlr"
        else:
            status = "one_sided_no_downside"

    return {
        "gross_savings": gross,
        "gross_savings_pct": gross_pct,
        "settlement": settlement,
        "status": status,
    }


def capitation_model(
    *,
    attributed_lives: float,
    months: float,
    base_pmpm: float,
    raf: float,
    clinical_spend: float,
    quality_improvement_spend: float = 0.0,
    benchmark_pmpm: Optional[float] = None,
    msr: float = 0.02,
    sharing_rate: float = 0.50,
    quality_score: float = 1.0,
    two_sided: bool = False,
    mlr_threshold: Optional[float] = None,
    source: str = "Actuarial filings and ACO election",
    vintage: str = "",
    audience: str = "both",
) -> Exhibit:
    """Full capitation economics: revenue, MLR gate, and shared-savings settlement.

    Premium for the MLR test is the risk-adjusted capitation revenue. The
    shared-savings benchmark defaults to the base PMPM if a separate
    ``benchmark_pmpm`` is not supplied; actual is the clinical spend per member-
    month grossed back to total. The exhibit reconciles revenue to its PMPM
    identity so the arithmetic is provable.
    """
    rev = capitation_revenue(attributed_lives, months, base_pmpm, raf)
    member_months = rev["member_months"]
    revenue = rev["revenue"]

    mlr = mlr_test(clinical_spend, quality_improvement_spend, revenue)

    bench_pmpm = benchmark_pmpm if benchmark_pmpm is not None else base_pmpm * raf
    benchmark_total = bench_pmpm * member_months
    actual_total = clinical_spend
    waterfall = shared_savings_waterfall(
        benchmark_total,
        actual_total,
        msr=msr,
        sharing_rate=sharing_rate,
        quality_score=quality_score,
        two_sided=two_sided,
        mlr_threshold=mlr_threshold,
    )

    flags: List[Flag] = []
    if mlr["below_floor"]:
        flags.append(
            Flag(
                code="mlr_below_floor",
                severity="risk",
                message=(
                    f"Medical loss ratio is {mlr['mlr']*100:.1f} percent, below the "
                    f"{MLR_FLOOR*100:.0f} percent floor. A remittance of "
                    f"{mlr['remittance']:,.0f} is owed."
                ),
                source=source,
            )
        )
    if waterfall["status"] == "loss_owed":
        flags.append(
            Flag(
                code="shared_loss",
                severity="warn",
                message=(
                    "Spend exceeded the benchmark past the minimum loss rate, so "
                    "the ACO owes shared losses under its two-sided track."
                ),
                source=source,
            )
        )

    reconciliations = [
        Reconciliation(
            identity="revenue == risk-adjusted PMPM * member-months",
            lhs=revenue,
            rhs=rev["risk_adjusted_pmpm"] * member_months,
            tolerance=max(1.0, revenue * 1e-9),
        )
    ]

    series = [
        Series(
            name="Capitation economics",
            kind="bar",
            points=[
                {"label": "Risk-adjusted revenue", "value": revenue},
                {"label": "Clinical spend", "value": clinical_spend},
                {"label": "Shared-savings settlement", "value": waterfall["settlement"]},
            ],
        ),
        Series(
            name="Per-member-month detail",
            kind="bar",
            internal_only=True,
            points=[
                {"label": "Base PMPM", "value": base_pmpm},
                {"label": "RAF", "value": raf},
                {"label": "Risk-adjusted PMPM", "value": rev["risk_adjusted_pmpm"]},
                {"label": "MLR", "value": mlr["mlr"]},
            ],
        ),
    ]

    footnote = Footnote(
        source=source,
        vintage=vintage or "not stated",
        assumptions=[
            "Revenue is attributed member-months at a risk-adjusted PMPM (base times RAF).",
            f"MLR floor is {MLR_FLOOR*100:.0f} percent; a shortfall owes a remittance.",
            "Shared savings count only once the gap clears the minimum savings rate.",
        ],
    )

    ex = Exhibit(
        feature_id=FEATURE_ID,
        title="Capitation and shared-savings model",
        audience=audience,
        series=series,
        footnote=footnote,
        flags=flags,
        reconciliations=reconciliations,
        summary=(
            f"Revenue {revenue:,.0f} on {member_months:,.0f} member-months, "
            f"MLR {mlr['mlr']*100:.1f} percent, settlement "
            f"{waterfall['settlement']:,.0f} ({waterfall['status']})."
        ),
        meta={
            "member_months": member_months,
            "risk_adjusted_pmpm": rev["risk_adjusted_pmpm"],
            "revenue": revenue,
            "mlr": mlr["mlr"],
            "mlr_remittance": mlr["remittance"],
            "benchmark_total": benchmark_total,
            "gross_savings": waterfall["gross_savings"],
            "settlement": waterfall["settlement"],
            "waterfall_status": waterfall["status"],
        },
    )
    return ex.validate()


def _demo() -> Exhibit:
    return capitation_model(
        attributed_lives=10_000,
        months=12,
        base_pmpm=800.0,
        raf=1.045,
        clinical_spend=88_000_000.0,
        quality_improvement_spend=2_000_000.0,
        msr=0.02,
        sharing_rate=0.50,
        quality_score=0.95,
        source="Demo ACO filing",
        vintage="2026",
    )


register(
    CddFeature(
        feature_id=FEATURE_ID,
        title="Capitation / lives and shared-savings model",
        audience="both",
        demo=_demo,
    )
)
