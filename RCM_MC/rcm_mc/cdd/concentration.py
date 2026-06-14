"""NEW-10 Customer concentration (top-N).

Revenue concentration by account: top 5, 10, and 20 shares, a Pareto curve, a
Herfindahl index, and a red flag when any single account exceeds 40 percent of
revenue. The partner view exposes ranks only; account names are internal-only.

Statistical and deterministic. No LLM on any path.
"""
from __future__ import annotations

from typing import Any, Dict, List, Mapping, Sequence

from .exhibit import Exhibit, Flag, Footnote, Reconciliation, Series, safe_div
from .registry import CddFeature, register

FEATURE_ID = "NEW-10"
SINGLE_ACCOUNT_THRESHOLD = 0.40
DEFAULT_TOP_NS = (5, 10, 20)


def customer_concentration(
    accounts: Sequence[Mapping[str, Any]],
    *,
    top_ns: Sequence[int] = DEFAULT_TOP_NS,
    single_account_threshold: float = SINGLE_ACCOUNT_THRESHOLD,
    source: str = "Target revenue by account",
    vintage: str = "",
    audience: str = "both",
) -> Exhibit:
    """Top-N revenue shares and single-account concentration flag.

    ``accounts``: records of {account, revenue}.
    """
    if not accounts:
        raise ValueError("customer_concentration requires at least one account")

    rows = [{"account": str(a["account"]), "revenue": float(a["revenue"])} for a in accounts]
    total = sum(r["revenue"] for r in rows)
    if total <= 0:
        raise ValueError("total revenue must be positive")

    rows.sort(key=lambda r: r["revenue"], reverse=True)
    shares = [safe_div(r["revenue"], total) for r in rows]

    top_n_shares: Dict[int, float] = {}
    for n in top_ns:
        top_n_shares[int(n)] = sum(shares[:n])

    max_share = shares[0]
    flags: List[Flag] = []
    if max_share > single_account_threshold:
        flags.append(Flag(
            code="single_account_over_40pct",
            severity="risk",
            message=(
                f"The largest account is {max_share*100:.1f} percent of revenue, "
                f"above the {single_account_threshold*100:.0f} percent red-flag line."
            ),
            source=source,
        ))

    # Pareto cumulative curve.
    cum = 0.0
    pareto: List[Dict[str, Any]] = []
    ranked_points: List[Dict[str, Any]] = []
    named_points: List[Dict[str, Any]] = []
    for i, (r, s) in enumerate(zip(rows, shares), start=1):
        cum += s
        pareto.append({"rank": i, "cumulative_share": cum})
        ranked_points.append({"label": f"#{i}", "value": s, "cumulative_share": cum})
        named_points.append({"label": r["account"], "value": s, "revenue": r["revenue"]})

    hhi = sum(s * s for s in shares)

    reconciliations = [
        Reconciliation(
            identity="account shares sum to 1.0",
            lhs=sum(shares),
            rhs=1.0,
            tolerance=1e-9,
        )
    ]

    series = [
        Series(name="Top accounts by rank", kind="bar", points=ranked_points),
        Series(name="Pareto cumulative share", kind="line",
               points=[{"label": f"#{p['rank']}", "value": p["cumulative_share"]} for p in pareto]),
        Series(name="Top accounts by name", kind="bar", internal_only=True, points=named_points),
    ]

    footnote = Footnote(
        source=source,
        vintage=vintage or "not stated",
        assumptions=[
            "Shares are account revenue divided by total revenue.",
            "Account names are internal-only; the partner view shows ranks.",
            f"Single-account red flag fires above {single_account_threshold*100:.0f} percent.",
        ],
    )

    ex = Exhibit(
        feature_id=FEATURE_ID,
        title="Customer concentration",
        audience=audience,
        series=series,
        footnote=footnote,
        flags=flags,
        reconciliations=reconciliations,
        summary=(
            f"{len(rows)} accounts. Largest {max_share*100:.1f} percent. "
            f"Top {min(top_ns)} is {top_n_shares[min(top_ns)]*100:.1f} percent."
        ),
        meta={
            "total": total,
            "max_share": max_share,
            "top_n_shares": top_n_shares,
            "hhi": hhi,
            "pareto": pareto,
            "ranked_shares": shares,
        },
    )
    return ex.validate()


def _demo() -> Exhibit:
    accounts = [
        {"account": "Northstar Health", "revenue": 45},
        {"account": "Cedar Clinics", "revenue": 30},
        {"account": "Lakeview", "revenue": 15},
        {"account": "Other", "revenue": 10},
    ]
    return customer_concentration(accounts, source="Demo revenue", vintage="2026")


register(
    CddFeature(
        feature_id=FEATURE_ID,
        title="Customer concentration (top-N)",
        audience="both",
        demo=_demo,
    )
)
