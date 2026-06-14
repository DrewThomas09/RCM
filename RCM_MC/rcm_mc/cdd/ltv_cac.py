"""NEW-06 Cohort-based LTV / CAC.

Empirically realized cumulative lifetime value per starting customer, the
Social-Capital style: cumulative cohort revenue times gross margin, divided by
the number of customers the cohort started with. Not a formula LTV. Reports the
payback month (first age where cumulative LTV per customer covers CAC) and the
LTV:CAC ratio against the 3:1 reference line. Cohort revenues reconcile to a
stated total within 2 percent.

Statistical and deterministic. No LLM on any path.
"""
from __future__ import annotations

from typing import Any, Dict, List, Mapping, Optional, Sequence

from .exhibit import Exhibit, Flag, Footnote, Reconciliation, Series, safe_div
from .registry import CddFeature, register

FEATURE_ID = "NEW-06"
LTV_CAC_REFERENCE = 3.0
RECON_TOLERANCE = 0.02  # 2 percent


def _cohort_curve(
    revenue_by_age: Mapping[Any, float],
    n_customers: int,
    cac_per_customer: float,
    gross_margin: float,
) -> Dict[str, Any]:
    ages = sorted(int(a) for a in revenue_by_age)
    cum_rev = 0.0
    curve: List[Dict[str, float]] = []
    payback_month: Optional[int] = None
    for a in ages:
        cum_rev += float(revenue_by_age[a])
        ltv_pc = safe_div(cum_rev * gross_margin, n_customers)
        if payback_month is None and ltv_pc >= cac_per_customer:
            payback_month = a
        curve.append({"age_months": a, "cum_revenue": cum_rev, "ltv_per_customer": ltv_pc})
    final_ltv = curve[-1]["ltv_per_customer"] if curve else 0.0
    return {
        "curve": curve,
        "final_ltv_per_customer": final_ltv,
        "cac_per_customer": cac_per_customer,
        "ltv_cac_ratio": safe_div(final_ltv, cac_per_customer),
        "payback_month": payback_month,
        "total_revenue": cum_rev,
        "n_customers": n_customers,
    }


def ltv_cac(
    cohorts: Sequence[Mapping[str, Any]],
    *,
    gross_margin: float = 1.0,
    total_revenue: Optional[float] = None,
    ltv_cac_reference: float = LTV_CAC_REFERENCE,
    source: str = "Cohort revenue and CAC",
    vintage: str = "",
    audience: str = "both",
) -> Exhibit:
    """Per-cohort realized LTV, payback month, and LTV:CAC ratio.

    ``cohorts``: records of {cohort, n_customers, cac (per customer unless
    cac_is_total), revenue_by_age: {age_month: cohort revenue in that month}}.
    """
    if not cohorts:
        raise ValueError("ltv_cac requires at least one cohort")
    if not (0.0 < gross_margin <= 1.0):
        raise ValueError(f"gross_margin must be in (0, 1], got {gross_margin}")

    flags: List[Flag] = []
    per_cohort: Dict[str, Any] = {}
    sum_revenue = 0.0
    ratio_points: List[Dict[str, Any]] = []
    ltv_curve_points: List[Dict[str, Any]] = []

    for c in cohorts:
        label = str(c["cohort"])
        n = int(c["n_customers"])
        if n <= 0:
            raise ValueError(f"cohort {label}: n_customers must be positive")
        cac_total = float(c["cac"])
        cac_pc = cac_total if c.get("cac_is_per_customer", True) else safe_div(cac_total, n)
        res = _cohort_curve(c["revenue_by_age"], n, cac_pc, gross_margin)
        per_cohort[label] = res
        sum_revenue += res["total_revenue"]
        ratio_points.append({"label": label, "value": res["ltv_cac_ratio"]})
        for pt in res["curve"]:
            ltv_curve_points.append({"label": f"{label} m{pt['age_months']}",
                                     "value": pt["ltv_per_customer"]})
        if res["ltv_cac_ratio"] < ltv_cac_reference:
            flags.append(Flag(
                code="below_3to1",
                severity="warn",
                message=(
                    f"Cohort {label} LTV:CAC is {res['ltv_cac_ratio']:.2f}, below "
                    f"the {ltv_cac_reference:.0f} to 1 reference."
                ),
            ))
        if res["payback_month"] is None:
            flags.append(Flag(
                code="never_pays_back",
                severity="risk",
                message=f"Cohort {label} cumulative LTV never covers CAC over the observed window.",
            ))

    reconciliations: List[Reconciliation] = []
    if total_revenue is not None and total_revenue > 0:
        gap_rel = safe_div(abs(sum_revenue - total_revenue), total_revenue)
        reconciliations.append(Reconciliation(
            identity="sum of cohort revenue reconciles to total within 2 percent",
            lhs=gap_rel,
            rhs=0.0,
            tolerance=RECON_TOLERANCE,
        ))
        if gap_rel > RECON_TOLERANCE:
            flags.append(Flag(
                code="revenue_reconciliation_gap",
                severity="risk",
                message=(
                    f"Cohort revenue sum diverges from total by {gap_rel*100:.1f} "
                    "percent, above the 2 percent tolerance."
                ),
                source=source,
            ))

    series = [
        Series(name="LTV to CAC ratio", kind="bar", points=ratio_points,
               internal_only=False),
        Series(name="Cumulative LTV per customer", kind="line", points=ltv_curve_points),
    ]

    footnote = Footnote(
        source=source,
        vintage=vintage or "not stated",
        assumptions=[
            "LTV is empirically realized cumulative revenue times gross margin per starting customer.",
            "Payback month is the first age where cumulative LTV per customer covers CAC.",
            f"Reference line is {ltv_cac_reference:.0f} to 1.",
        ],
    )

    ex = Exhibit(
        feature_id=FEATURE_ID,
        title="Cohort LTV to CAC",
        audience=audience,
        series=series,
        footnote=footnote,
        flags=flags,
        reconciliations=reconciliations,
        summary=f"{len(per_cohort)} cohort(s). Reference line {ltv_cac_reference:.0f} to 1.",
        meta={
            "cohorts": per_cohort,
            "sum_revenue": sum_revenue,
            "ltv_cac_reference": ltv_cac_reference,
            "gross_margin": gross_margin,
        },
    )
    return ex.validate()


def _demo() -> Exhibit:
    cohorts = [{
        "cohort": "2024",
        "n_customers": 100,
        "cac": 50.0,
        "revenue_by_age": {1: 2000, 2: 2000, 3: 1500, 4: 1500, 5: 1000, 6: 1000},
    }]
    return ltv_cac(cohorts, total_revenue=9100.0, source="Demo cohorts", vintage="2026")


register(
    CddFeature(
        feature_id=FEATURE_ID,
        title="Cohort-based LTV/CAC",
        audience="both",
        demo=_demo,
    )
)
