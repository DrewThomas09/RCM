"""Customer concentration drilldown — top-N customer risk analysis.

Beyond simple "top customer = X% of revenue" metrics, partners
want:

- **Top-N revenue share** (top-1, top-5, top-10).
- **Customer HHI** on revenue (concentration index).
- **Churn risk per customer** — based on contract status,
  renewal date, relationship age.
- **Cross-sell upside** — customers underpenetrated vs platform
  product set.
- **Revenue-at-risk** — expected-value revenue loss over 12
  months.

Takes a list of customer records, returns a structured analysis
and a partner narrative.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class CustomerRecord:
    name: str
    annual_revenue_m: float
    contract_status: str = "active"       # "active" / "at_will" / "expiring"
    months_until_renewal: Optional[int] = None
    relationship_years: float = 3.0
    products_purchased: int = 1
    products_available: int = 1
    known_at_risk: bool = False


@dataclass
class CustomerRisk:
    name: str
    revenue_share_pct: float              # of total book
    churn_probability: float              # 0-1
    revenue_at_risk_m: float              # churn_p × revenue
    cross_sell_upside_m: float
    flags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "revenue_share_pct": self.revenue_share_pct,
            "churn_probability": self.churn_probability,
            "revenue_at_risk_m": self.revenue_at_risk_m,
            "cross_sell_upside_m": self.cross_sell_upside_m,
            "flags": list(self.flags),
        }


@dataclass
class ConcentrationAnalysis:
    top_1_pct: float
    top_5_pct: float
    top_10_pct: float
    customer_hhi: int
    total_revenue_at_risk_m: float
    total_cross_sell_upside_m: float
    customer_risks: List[CustomerRisk] = field(default_factory=list)
    partner_note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "top_1_pct": self.top_1_pct,
            "top_5_pct": self.top_5_pct,
            "top_10_pct": self.top_10_pct,
            "customer_hhi": self.customer_hhi,
            "total_revenue_at_risk_m": self.total_revenue_at_risk_m,
            "total_cross_sell_upside_m": self.total_cross_sell_upside_m,
            "customer_risks": [r.to_dict() for r in self.customer_risks],
            "partner_note": self.partner_note,
        }


def _churn_probability(c: CustomerRecord) -> float:
    """Heuristic churn probability over next 12 months."""
    p = 0.05  # base rate
    if c.known_at_risk:
        p = max(p, 0.60)
    if c.contract_status == "at_will":
        p += 0.20
    elif c.contract_status == "expiring":
        p += 0.15
    if c.months_until_renewal is not None and c.months_until_renewal <= 6:
        p += 0.10
    if c.relationship_years < 1.0:
        p += 0.10
    elif c.relationship_years >= 5.0:
        p -= 0.03
    return max(0.0, min(0.95, p))


def _flags(c: CustomerRecord, share: float, churn_p: float) -> List[str]:
    flags: List[str] = []
    if share >= 0.15:
        flags.append(f"Single-customer concentration {share*100:.0f}% "
                     "— diversification priority.")
    if c.known_at_risk:
        flags.append("Known at-risk customer — active mitigation required.")
    if c.contract_status == "at_will":
        flags.append("At-will contract — negotiate multi-year extension.")
    if (c.months_until_renewal is not None
            and c.months_until_renewal <= 6 and share >= 0.05):
        flags.append(f"Top-tier customer renewing in "
                     f"{c.months_until_renewal} months.")
    if churn_p >= 0.50:
        flags.append(f"Churn probability {churn_p*100:.0f}% — high.")
    return flags


def analyze_customers(records: List[CustomerRecord],
                      high_concentration_threshold: float = 0.25
                      ) -> ConcentrationAnalysis:
    total_rev = sum(c.annual_revenue_m for c in records)
    if total_rev <= 0:
        return ConcentrationAnalysis(
            top_1_pct=0.0, top_5_pct=0.0, top_10_pct=0.0,
            customer_hhi=0, total_revenue_at_risk_m=0.0,
            total_cross_sell_upside_m=0.0,
            partner_note="No customer revenue in the book.",
        )
    sorted_cust = sorted(records, key=lambda c: c.annual_revenue_m, reverse=True)

    def share(n: int) -> float:
        return sum(c.annual_revenue_m for c in sorted_cust[:n]) / total_rev

    t1, t5, t10 = share(1), share(5), share(10)

    # HHI on customer shares × 10000.
    hhi = int(sum(((c.annual_revenue_m / total_rev) * 100) ** 2
                   for c in records))

    risks: List[CustomerRisk] = []
    total_rar = 0.0
    total_cross = 0.0
    for c in sorted_cust:
        s = c.annual_revenue_m / total_rev
        p = _churn_probability(c)
        rar = p * c.annual_revenue_m
        cross = (max(0, c.products_available - c.products_purchased)
                 * (c.annual_revenue_m / max(1, c.products_purchased))
                 * 0.5)  # 50% realization assumption
        fl = _flags(c, s, p)
        risks.append(CustomerRisk(
            name=c.name,
            revenue_share_pct=round(s * 100, 2),
            churn_probability=round(p, 3),
            revenue_at_risk_m=round(rar, 2),
            cross_sell_upside_m=round(cross, 2),
            flags=fl,
        ))
        total_rar += rar
        total_cross += cross

    if t1 >= high_concentration_threshold:
        note = (f"Top customer is {t1*100:.0f}% of revenue — concentration "
                f"risk is material. HHI {hhi}. ${total_rar:,.1f}M "
                "expected revenue at risk next 12mo.")
    elif t5 >= 0.50:
        note = (f"Top-5 = {t5*100:.0f}% of revenue — moderately "
                f"concentrated. Manage renewals carefully.")
    else:
        note = (f"Customer base reasonably diversified: top-1 "
                f"{t1*100:.0f}%, top-10 {t10*100:.0f}%. HHI {hhi}.")

    return ConcentrationAnalysis(
        top_1_pct=round(t1 * 100, 2),
        top_5_pct=round(t5 * 100, 2),
        top_10_pct=round(t10 * 100, 2),
        customer_hhi=hhi,
        total_revenue_at_risk_m=round(total_rar, 2),
        total_cross_sell_upside_m=round(total_cross, 2),
        customer_risks=risks,
        partner_note=note,
    )


def render_concentration_markdown(a: ConcentrationAnalysis) -> str:
    lines = [
        "# Customer concentration drilldown",
        "",
        f"_{a.partner_note}_",
        "",
        f"- Top-1: {a.top_1_pct:.1f}%",
        f"- Top-5: {a.top_5_pct:.1f}%",
        f"- Top-10: {a.top_10_pct:.1f}%",
        f"- Customer HHI: {a.customer_hhi}",
        f"- Revenue at risk (12mo EV): ${a.total_revenue_at_risk_m:,.1f}M",
        f"- Cross-sell upside (50% realized): ${a.total_cross_sell_upside_m:,.1f}M",
        "",
        "| Customer | Share % | Churn p | Rev at risk | Cross-sell |",
        "|---|---:|---:|---:|---:|",
    ]
    for r in a.customer_risks[:20]:
        lines.append(
            f"| {r.name} | {r.revenue_share_pct:.1f}% | "
            f"{r.churn_probability:.2f} | ${r.revenue_at_risk_m:,.2f}M | "
            f"${r.cross_sell_upside_m:,.2f}M |"
        )
    return "\n".join(lines)
