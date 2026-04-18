"""Pricing power diagnostic — can this company raise prices?

Pricing power is the most durable margin lever. Partners score it
across dimensions:

- **Payer concentration** — fewer large payers = LESS pricing power
  (they negotiate).
- **Market share in service area** — higher share = more pricing
  power (must-have status).
- **Service differentiation** — specialty care, CoE designations,
  superior outcomes → pricing power.
- **Contract structure** — fee-for-service (weak) vs capitation
  (strong) vs value-based (growing).
- **Payer-mix profile** — Medicare/Medicaid-heavy (no pricing
  power) vs commercial-heavy (strong).
- **Pricing history** — consistent rate increases recorded.

Output: score 0-100 and a partner note on pricing strategy.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class PricingPowerInputs:
    top_payer_share_pct: float = 0.30     # largest payer % of revenue
    local_market_share_pct: float = 0.15  # share of local service area
    is_center_of_excellence: bool = False
    has_exclusive_service_line: bool = False
    contract_mix_fee_for_service_pct: float = 0.80
    contract_mix_capitation_pct: float = 0.10
    contract_mix_value_based_pct: float = 0.10
    commercial_payer_pct: float = 0.50
    medicare_pct: float = 0.30
    medicaid_pct: float = 0.20
    historical_annual_rate_increase_pct: float = 0.03


@dataclass
class PricingFinding:
    dimension: str
    score_0_100: int
    rationale: str


@dataclass
class PricingPowerReport:
    overall_score_0_100: int
    findings: List[PricingFinding] = field(default_factory=list)
    partner_note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "overall_score_0_100": self.overall_score_0_100,
            "findings": [
                {"dimension": f.dimension, "score_0_100": f.score_0_100,
                 "rationale": f.rationale} for f in self.findings
            ],
            "partner_note": self.partner_note,
        }


# Dimension weights sum to 1.0.
DIMENSION_WEIGHTS = {
    "payer_concentration": 0.20,
    "market_share": 0.20,
    "differentiation": 0.20,
    "contract_structure": 0.15,
    "payer_mix": 0.15,
    "pricing_history": 0.10,
}


def assess_pricing_power(inputs: PricingPowerInputs) -> PricingPowerReport:
    findings: List[PricingFinding] = []

    # Payer concentration (inverted — high share of top payer = weak).
    if inputs.top_payer_share_pct >= 0.50:
        pc_score = 20
        pc_r = (f"Top payer {inputs.top_payer_share_pct*100:.0f}% — "
                "severe concentration, payer dictates rate.")
    elif inputs.top_payer_share_pct >= 0.30:
        pc_score = 45
        pc_r = (f"Top payer {inputs.top_payer_share_pct*100:.0f}% — "
                "moderate concentration.")
    else:
        pc_score = 75
        pc_r = (f"Top payer {inputs.top_payer_share_pct*100:.0f}% — "
                "diversified payer base.")
    findings.append(PricingFinding("payer_concentration", pc_score, pc_r))

    # Market share.
    if inputs.local_market_share_pct >= 0.40:
        ms_score = 90
        ms_r = (f"Local market share {inputs.local_market_share_pct*100:.0f}% "
                "— must-have provider, strong pricing leverage.")
    elif inputs.local_market_share_pct >= 0.20:
        ms_score = 65
        ms_r = (f"Local market share {inputs.local_market_share_pct*100:.0f}% "
                "— material position.")
    else:
        ms_score = 35
        ms_r = (f"Local market share {inputs.local_market_share_pct*100:.0f}% "
                "— marginal position; limited negotiating leverage.")
    findings.append(PricingFinding("market_share", ms_score, ms_r))

    # Differentiation.
    diff_score = 30
    reasons = []
    if inputs.is_center_of_excellence:
        diff_score += 30
        reasons.append("Center of Excellence")
    if inputs.has_exclusive_service_line:
        diff_score += 30
        reasons.append("exclusive service line")
    diff_score = min(100, diff_score)
    if reasons:
        diff_r = f"{', '.join(reasons)} supports premium rates."
    else:
        diff_r = ("No standout differentiation — commodity services "
                  "have limited pricing power.")
    findings.append(PricingFinding("differentiation", diff_score, diff_r))

    # Contract structure.
    cs_score = (int(inputs.contract_mix_capitation_pct * 100 * 1.0) +
                int(inputs.contract_mix_value_based_pct * 100 * 0.8) +
                int(inputs.contract_mix_fee_for_service_pct * 100 * 0.3))
    cs_score = min(100, cs_score)
    cs_r = (f"FFS {inputs.contract_mix_fee_for_service_pct*100:.0f}% / "
            f"Cap {inputs.contract_mix_capitation_pct*100:.0f}% / "
            f"VBC {inputs.contract_mix_value_based_pct*100:.0f}% mix.")
    findings.append(PricingFinding("contract_structure", cs_score, cs_r))

    # Payer mix.
    commercial = inputs.commercial_payer_pct
    if commercial >= 0.60:
        pm_score = 85
        pm_r = (f"Commercial {commercial*100:.0f}% — strong "
                "pricing exposure.")
    elif commercial >= 0.40:
        pm_score = 60
        pm_r = (f"Commercial {commercial*100:.0f}% — balanced.")
    else:
        pm_score = 30
        pm_r = (f"Commercial only {commercial*100:.0f}% — Medicare/Medicaid "
                "dominant, no pricing power on the dominant book.")
    findings.append(PricingFinding("payer_mix", pm_score, pm_r))

    # Pricing history.
    r = inputs.historical_annual_rate_increase_pct
    if r >= 0.05:
        hist_score = 90
        hist_r = (f"Historical rate increases {r*100:.1f}%/yr — "
                  "proven pricing power.")
    elif r >= 0.03:
        hist_score = 65
        hist_r = (f"Historical rate increases {r*100:.1f}%/yr — "
                  "average.")
    else:
        hist_score = 30
        hist_r = (f"Historical rate increases only {r*100:.1f}%/yr — "
                  "weak evidence of pricing power.")
    findings.append(PricingFinding("pricing_history", hist_score, hist_r))

    # Weighted overall.
    overall = int(round(sum(
        f.score_0_100 * DIMENSION_WEIGHTS.get(f.dimension, 0.0)
        for f in findings
    )))

    if overall >= 75:
        note = (f"Pricing power score {overall}/100 — strong. Model "
                "3-4% annual rate increases in the base case.")
    elif overall >= 55:
        note = (f"Pricing power score {overall}/100 — moderate. Model "
                "2-3% annual rate increases and stress-test at flat.")
    elif overall >= 35:
        note = (f"Pricing power score {overall}/100 — weak. Model "
                "0-1.5% rate increases and focus value creation on "
                "volume/cost.")
    else:
        note = (f"Pricing power score {overall}/100 — very weak. "
                "Pricing is not a lever in this deal.")

    return PricingPowerReport(
        overall_score_0_100=overall,
        findings=findings,
        partner_note=note,
    )


def render_pricing_power_markdown(r: PricingPowerReport) -> str:
    lines = [
        "# Pricing power diagnostic",
        "",
        f"_{r.partner_note}_",
        "",
        f"- Overall score: **{r.overall_score_0_100}/100**",
        "",
        "## Dimensions",
        "",
    ]
    for f in r.findings:
        lines.append(f"- **{f.dimension}** ({f.score_0_100}/100): "
                     f"{f.rationale}")
    return "\n".join(lines)
