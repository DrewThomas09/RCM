"""M&A integration scoreboard — track bolt-on integration progress.

Roll-up / platform deals close many bolt-ons. Each one needs to
hit integration milestones: IT cutover, brand migration, billing
on platform codes, customer retention, synergy realization.

This module scores each deal's integration health and rolls up
across the platform to produce a scoreboard:

- **Per-deal health 0-100** — weighted across dimensions.
- **Platform average health** — book-weighted.
- **Laggards** — deals below threshold.
- **Red flags** — missed milestones, customer churn, synergy
  shortfall.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


DIMENSION_WEIGHTS = {
    "it_cutover": 0.20,
    "billing_conversion": 0.20,
    "synergy_realization": 0.25,
    "customer_retention": 0.20,
    "employee_retention": 0.10,
    "brand_migration": 0.05,
}


@dataclass
class BoltOnInputs:
    name: str
    close_date: str                       # ISO date
    months_since_close: int
    platform_revenue_m: float
    bolton_revenue_m: float
    it_cutover_pct: float = 0.0           # 0-1.0, fraction complete
    billing_conversion_pct: float = 0.0
    synergy_target_m: float = 0.0
    synergy_realized_m: float = 0.0
    customer_retention_pct: float = 1.0   # retained revenue vs T-3mo baseline
    employee_retention_pct: float = 1.0
    brand_migration_pct: float = 0.0
    target_months_to_complete: int = 18


@dataclass
class BoltOnScore:
    name: str
    health_0_100: int
    dimension_scores: Dict[str, int]
    red_flags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "health_0_100": self.health_0_100,
            "dimension_scores": dict(self.dimension_scores),
            "red_flags": list(self.red_flags),
        }


@dataclass
class IntegrationScoreboard:
    deals: List[BoltOnScore] = field(default_factory=list)
    platform_health: int = 0              # book-weighted
    laggard_names: List[str] = field(default_factory=list)
    partner_note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "deals": [d.to_dict() for d in self.deals],
            "platform_health": self.platform_health,
            "laggard_names": list(self.laggard_names),
            "partner_note": self.partner_note,
        }


def _expected_progress(months: int, target: int) -> float:
    """Expected fraction complete by now if on schedule."""
    if target <= 0:
        return 1.0
    return min(1.0, max(0.0, months / target))


def _score_dimension(actual_pct: float, expected_pct: float) -> int:
    """0-100 score — ratio of actual to expected, clamped."""
    if expected_pct <= 0.0:
        return 100 if actual_pct >= 1.0 else 50
    ratio = actual_pct / expected_pct
    if ratio >= 1.0:
        return 100
    return max(0, int(round(ratio * 100)))


def score_bolton(b: BoltOnInputs) -> BoltOnScore:
    exp = _expected_progress(b.months_since_close, b.target_months_to_complete)

    dims: Dict[str, int] = {}
    dims["it_cutover"] = _score_dimension(b.it_cutover_pct, exp)
    dims["billing_conversion"] = _score_dimension(b.billing_conversion_pct, exp)
    # Synergy realization.
    if b.synergy_target_m > 0:
        syn_pct = (b.synergy_realized_m / b.synergy_target_m
                   if b.synergy_target_m > 0 else 0.0)
        dims["synergy_realization"] = _score_dimension(syn_pct, exp)
    else:
        dims["synergy_realization"] = 100  # no target = N/A
    # Customer retention: flat out, not progress-based.
    dims["customer_retention"] = max(0, min(100,
                                              int(b.customer_retention_pct * 100)))
    dims["employee_retention"] = max(0, min(100,
                                              int(b.employee_retention_pct * 100)))
    dims["brand_migration"] = _score_dimension(b.brand_migration_pct, exp)

    health = int(round(sum(
        dims[d] * DIMENSION_WEIGHTS[d] for d in DIMENSION_WEIGHTS
    )))

    red: List[str] = []
    if dims["customer_retention"] < 90:
        red.append(f"Customer retention {dims['customer_retention']}% "
                   "(below 90% threshold).")
    if dims["synergy_realization"] < 50 and b.synergy_target_m > 0:
        red.append(f"Synergy realization {dims['synergy_realization']} "
                   "below expected curve.")
    if dims["employee_retention"] < 80:
        red.append(f"Employee retention {dims['employee_retention']}%.")
    if (b.months_since_close >= b.target_months_to_complete
            and (dims["it_cutover"] < 100 or dims["billing_conversion"] < 100)):
        red.append("Target complete-by date passed with IT/billing incomplete.")

    return BoltOnScore(
        name=b.name, health_0_100=health,
        dimension_scores=dims, red_flags=red,
    )


def build_scoreboard(boltons: List[BoltOnInputs],
                      laggard_threshold: int = 70) -> IntegrationScoreboard:
    scores = [score_bolton(b) for b in boltons]

    total_rev = sum(b.bolton_revenue_m for b in boltons)
    if total_rev > 0:
        weighted = sum(
            s.health_0_100 * b.bolton_revenue_m
            for s, b in zip(scores, boltons)
        ) / total_rev
    else:
        weighted = (sum(s.health_0_100 for s in scores) / len(scores)
                    if scores else 0.0)

    laggards = [s.name for s in scores
                if s.health_0_100 < laggard_threshold]

    if not scores:
        note = "No bolt-ons in the book."
    elif weighted >= 85:
        note = (f"Platform integration is strong (avg "
                f"{int(weighted)}/100). {len(laggards)} laggard(s).")
    elif weighted >= 70:
        note = (f"Platform integration is fair (avg "
                f"{int(weighted)}/100). Focus on the {len(laggards)} "
                f"laggard(s): {', '.join(laggards[:3])}.")
    else:
        note = (f"Platform integration is weak (avg "
                f"{int(weighted)}/100). Broad-based issues; elevate "
                "to platform PMO.")

    return IntegrationScoreboard(
        deals=scores,
        platform_health=int(round(weighted)),
        laggard_names=laggards,
        partner_note=note,
    )


def render_scoreboard_markdown(sb: IntegrationScoreboard) -> str:
    lines = [
        "# M&A integration scoreboard",
        "",
        f"_{sb.partner_note}_",
        "",
        f"- Platform health: **{sb.platform_health}/100**",
        f"- Laggards: {', '.join(sb.laggard_names) if sb.laggard_names else '—'}",
        "",
        "| Deal | Health | IT | Billing | Synergy | Cust ret | Emp ret |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for d in sb.deals:
        ds = d.dimension_scores
        lines.append(
            f"| {d.name} | {d.health_0_100} | {ds.get('it_cutover', 0)} | "
            f"{ds.get('billing_conversion', 0)} | "
            f"{ds.get('synergy_realization', 0)} | "
            f"{ds.get('customer_retention', 0)} | "
            f"{ds.get('employee_retention', 0)} |"
        )
    return "\n".join(lines)
