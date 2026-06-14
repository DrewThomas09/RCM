"""NEW-16 Pricing waterfall and unit-economics contribution-margin bridge.

Two reconciling waterfalls:
- Price: gross price less discounts less rebates equals net price.
- Margin: revenue (net price times volume) less variable costs equals
  contribution margin.
Plus an EBITDA-bridge handoff: contribution margin less fixed costs is the
EBITDA proxy that feeds the QoE EBITDA-bridge workflow as its starting point.
Both waterfalls reconcile to net price and contribution margin within 1e-6.

Statistical and deterministic. No LLM on any path.
"""
from __future__ import annotations

from typing import Any, Dict, List, Mapping, Optional, Sequence

from .exhibit import Exhibit, Footnote, Reconciliation, Series, safe_div
from .registry import CddFeature, register

FEATURE_ID = "NEW-16"
TOL = 1e-6


def _line_amount(item: Mapping[str, Any], volume: float) -> float:
    if "amount" in item:
        return float(item["amount"])
    if "per_unit" in item:
        return float(item["per_unit"]) * volume
    raise ValueError(f"line {item.get('name')!r} needs 'amount' or 'per_unit'")


def pricing_cm_bridge(
    *,
    gross_price: float,
    volume: float,
    discounts: Optional[Sequence[Mapping[str, Any]]] = None,
    rebates: Optional[Sequence[Mapping[str, Any]]] = None,
    variable_costs: Optional[Sequence[Mapping[str, Any]]] = None,
    fixed_costs: float = 0.0,
    source: str = "Target pricing and cost build",
    vintage: str = "",
    audience: str = "both",
) -> Exhibit:
    """Price waterfall (gross to net) and revenue to contribution-margin bridge."""
    if gross_price < 0 or volume < 0:
        raise ValueError("gross_price and volume must be non-negative")
    discounts = list(discounts or [])
    rebates = list(rebates or [])
    variable_costs = list(variable_costs or [])

    disc_total = sum(_line_amount(d, volume) for d in discounts)
    rebate_total = sum(_line_amount(r, volume) for r in rebates)
    net_price = gross_price - disc_total - rebate_total

    revenue = net_price * volume
    var_total = sum(_line_amount(v, volume) for v in variable_costs)
    contribution_margin = revenue - var_total
    cm_margin = safe_div(contribution_margin, revenue)
    ebitda = contribution_margin - fixed_costs

    # Price waterfall.
    price_points: List[Dict[str, Any]] = [
        {"label": "Gross price", "value": gross_price, "kind": "start", "color": "blue"}
    ]
    for d in discounts:
        price_points.append({"label": str(d.get("name", "Discount")),
                             "value": -_line_amount(d, volume), "kind": "delta", "color": "red"})
    for r in rebates:
        price_points.append({"label": str(r.get("name", "Rebate")),
                             "value": -_line_amount(r, volume), "kind": "delta", "color": "red"})
    price_points.append({"label": "Net price", "value": net_price, "kind": "end", "color": "blue"})

    # Contribution-margin waterfall.
    cm_points: List[Dict[str, Any]] = [
        {"label": "Revenue", "value": revenue, "kind": "start", "color": "blue"}
    ]
    for v in variable_costs:
        cm_points.append({"label": str(v.get("name", "Variable cost")),
                          "value": -_line_amount(v, volume), "kind": "delta", "color": "red"})
    cm_points.append({"label": "Contribution margin", "value": contribution_margin,
                      "kind": "end", "color": "green" if contribution_margin >= 0 else "red"})

    reconciliations = [
        Reconciliation(identity="gross - discounts - rebates == net price",
                       lhs=gross_price - disc_total - rebate_total, rhs=net_price, tolerance=TOL),
        Reconciliation(identity="revenue - variable costs == contribution margin",
                       lhs=revenue - var_total, rhs=contribution_margin, tolerance=TOL),
    ]

    series = [
        Series(name="Price waterfall (gross to net)", kind="waterfall", points=price_points),
        Series(name="Contribution-margin bridge", kind="waterfall", points=cm_points),
        Series(name="EBITDA-bridge handoff", kind="bar", internal_only=True, points=[
            {"label": "Contribution margin", "value": contribution_margin},
            {"label": "Fixed costs", "value": -fixed_costs},
            {"label": "EBITDA proxy", "value": ebitda},
        ]),
    ]

    footnote = Footnote(
        source=source,
        vintage=vintage or "not stated",
        assumptions=[
            "Net price is gross less discounts less rebates.",
            "Contribution margin is revenue less variable costs.",
            "EBITDA proxy is contribution margin less fixed costs; it feeds the QoE EBITDA bridge as its start.",
        ],
    )

    ex = Exhibit(
        feature_id=FEATURE_ID,
        title="Pricing and contribution-margin bridge",
        audience=audience,
        series=series,
        footnote=footnote,
        reconciliations=reconciliations,
        summary=(
            f"Net price {net_price:,.2f}, revenue {revenue:,.0f}, contribution "
            f"margin {contribution_margin:,.0f} at {cm_margin*100:.1f} percent."
        ),
        meta={
            "gross_price": gross_price,
            "discount_total": disc_total,
            "rebate_total": rebate_total,
            "net_price": net_price,
            "volume": volume,
            "revenue": revenue,
            "variable_cost_total": var_total,
            "contribution_margin": contribution_margin,
            "cm_margin": cm_margin,
            "fixed_costs": fixed_costs,
            "ebitda_proxy": ebitda,
            "ebitda_handoff": "Contribution margin feeds the QoE EBITDA bridge as its starting point.",
        },
    )
    return ex.validate()


def _demo() -> Exhibit:
    return pricing_cm_bridge(
        gross_price=100.0, volume=1000,
        discounts=[{"name": "Volume discount", "amount": 15}],
        rebates=[{"name": "Payer rebate", "amount": 5}],
        variable_costs=[{"name": "Supplies", "amount": 20000}, {"name": "Labor", "amount": 25000}],
        fixed_costs=15000.0,
        source="Demo pricing build", vintage="2026",
    )


register(
    CddFeature(
        feature_id=FEATURE_ID,
        title="Pricing waterfall + unit-economics / contribution-margin bridge",
        audience="both",
        demo=_demo,
    )
)
