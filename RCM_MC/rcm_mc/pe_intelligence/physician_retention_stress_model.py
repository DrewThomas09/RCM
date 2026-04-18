"""Physician retention stress — what if top-N earners leave post-close.

Partner statement: "In a physician-driven business,
the EBITDA is the physicians. If we close the deal
and the top 3 producers leave — because they didn't
like our employment agreements, or they waited 90
days for the retention cliff, or they never bought in
on the thesis — half the model goes with them. I need
to know, before I write the check, what happens to
EBITDA if 1, 2, 3, or 5 top earners walk. And I need
the retention package priced against that stress, not
against the average physician."

Distinct from:
- `physician_compensation_benchmark` — wRVU & comp
  benchmarking against MGMA.
- `physician_comp_normalization_check` — validates
  comp-normalization add-back claims.
- `physician_group_friction_scorer` — 10 post-close
  friction points (scoring).

This module is the **stress test**: given a list of
the top physicians by revenue contribution, model the
EBITDA impact of losing 1, 2, 3, and 5 of them, with
assumptions about:

- physician revenue that walks vs. stays with
  patients who stay under other providers;
- replacement-physician ramp time (6-18 months to
  productive);
- locum costs while filling;
- re-credentialing calendar;
- and the retention-package premium needed to move
  the probability of stay from baseline to
  deal-dependent.

### Retention premium benchmarks (healthcare PE)

- Non-owner employed: minimal retention risk; no
  incentive needed (base + WRVU already covers them).
- Owner physicians rolling equity: 5-10% rollover
  standard; partnership vesting over 3-5 years.
- Owner physicians cashing out: the hard case —
  retention bonus of 1x annual comp typical, vested
  over 3-4 years.
- Key specialty physicians with outside options: add
  extra bond of 20-40% of comp vesting over 3 years
  (knowing some will bolt anyway).

### Output per stress tier

- EBITDA at risk ($ and %).
- Net-of-replacement EBITDA over 12 / 24 months.
- Retention package needed to materially de-risk.
- Partner verdict: **acceptable / price-in / walk**.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class Physician:
    name: str
    annual_revenue_m: float
    annual_comp_m: float
    owner: bool = False
    outside_options: bool = False  # in-demand specialty
    retention_bonus_signed_m: float = 0.0
    contributing_margin_pct: float = 0.40
    # share of revenue that FOLLOWS the physician if
    # they leave (new practice, referrals follow).
    revenue_portability_pct: float = 0.55


@dataclass
class RetentionStressInputs:
    physicians: List[Physician] = field(default_factory=list)
    replacement_ramp_months: int = 12
    locum_cost_m_per_month: float = 0.040  # $40k/mo
    recruiting_cost_per_replacement_m: float = 0.08  # $80k
    deal_ev_m: float = 300.0


@dataclass
class RetentionStressTier:
    tier_label: str
    physicians_lost_count: int
    revenue_lost_m: float
    ebitda_at_risk_m: float
    ebitda_at_risk_pct_of_deal_ev: float
    net_ebitda_trough_m: float
    retention_package_needed_m: float
    replacement_cost_m: float
    partner_verdict: str
    partner_read: str


@dataclass
class RetentionStressReport:
    baseline_ebitda_m: float = 0.0
    tiers: List[RetentionStressTier] = field(
        default_factory=list)
    overall_verdict: str = "acceptable"
    partner_note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "baseline_ebitda_m": self.baseline_ebitda_m,
            "tiers": [
                {"tier_label": t.tier_label,
                 "physicians_lost_count":
                     t.physicians_lost_count,
                 "revenue_lost_m": t.revenue_lost_m,
                 "ebitda_at_risk_m":
                     t.ebitda_at_risk_m,
                 "ebitda_at_risk_pct_of_deal_ev":
                     t.ebitda_at_risk_pct_of_deal_ev,
                 "net_ebitda_trough_m":
                     t.net_ebitda_trough_m,
                 "retention_package_needed_m":
                     t.retention_package_needed_m,
                 "replacement_cost_m":
                     t.replacement_cost_m,
                 "partner_verdict": t.partner_verdict,
                 "partner_read": t.partner_read}
                for t in self.tiers
            ],
            "overall_verdict": self.overall_verdict,
            "partner_note": self.partner_note,
        }


def _physician_annual_ebitda(p: Physician) -> float:
    """Physician-attributable EBITDA — revenue × margin, net of comp.

    Comp is already in cash cost; margin reflects the
    practice-level contribution. Simplified: revenue ×
    contributing_margin_pct.
    """
    return p.annual_revenue_m * p.contributing_margin_pct


def _retention_bond_needed(p: Physician) -> float:
    """Retention bonus needed to de-risk this physician.

    - Non-owner, no outside options: covered by base
      comp. Zero.
    - Owner cashing out: ~1.0x annual comp (vested 3-
      5yrs).
    - Non-owner with outside options: 0.3x comp (3yr
      vesting).
    - Owner + outside options: 1.5x (hard case).
    """
    if not p.owner and not p.outside_options:
        return 0.0
    if p.owner and p.outside_options:
        return p.annual_comp_m * 1.5
    if p.owner:
        return p.annual_comp_m * 1.0
    return p.annual_comp_m * 0.3


def _lost_ebitda_from_physician(
    p: Physician,
    replacement_ramp_months: int,
    locum_cost_per_month_m: float,
    recruiting_cost_m: float,
) -> Tuple[float, float, float]:
    """Return (revenue_lost_m_annualized,
    ebitda_trough_m_over_ramp, replacement_cost_m)."""
    # Revenue that permanently walks: portability × annual.
    revenue_walks = (
        p.annual_revenue_m * p.revenue_portability_pct
    )
    # EBITDA lost on walked revenue (permanent):
    ebitda_lost_walked = (
        revenue_walks * p.contributing_margin_pct
    )
    # EBITDA lost during ramp on the non-walked
    # portion (while replacement ramps up):
    ramp_years = replacement_ramp_months / 12.0
    # Ramp assumption: replacement averages 50%
    # productivity over ramp period.
    revenue_stays = p.annual_revenue_m * (
        1 - p.revenue_portability_pct)
    ebitda_ramp_hit = (
        revenue_stays * 0.5 * ramp_years *
        p.contributing_margin_pct
    )
    # Locum + recruiting cost:
    locum_cost = (
        locum_cost_per_month_m * replacement_ramp_months
    )
    replacement_cost = locum_cost + recruiting_cost_m

    ebitda_trough = (
        ebitda_lost_walked * ramp_years +
        ebitda_ramp_hit + replacement_cost
    )
    return revenue_walks, ebitda_trough, replacement_cost


def run_retention_stress(
    inputs: RetentionStressInputs,
) -> RetentionStressReport:
    physicians = sorted(
        inputs.physicians,
        key=lambda p: p.annual_revenue_m,
        reverse=True,
    )
    baseline_ebitda = sum(
        _physician_annual_ebitda(p) for p in physicians
    )

    tier_specs = [
        ("lose_top_1", 1),
        ("lose_top_2", 2),
        ("lose_top_3", 3),
        ("lose_top_5", 5),
    ]
    tiers: List[RetentionStressTier] = []

    for label, count in tier_specs:
        if count > len(physicians):
            count = len(physicians)
        lost = physicians[:count]
        total_rev_lost = 0.0
        total_ebitda_at_risk = 0.0
        total_trough = 0.0
        total_replacement = 0.0
        total_retention = 0.0
        for p in lost:
            rev_walks, trough, replacement = (
                _lost_ebitda_from_physician(
                    p,
                    inputs.replacement_ramp_months,
                    inputs.locum_cost_m_per_month,
                    inputs.recruiting_cost_per_replacement_m,
                )
            )
            # Full-year EBITDA at-risk (steady state after
            # replacement hires and ramps). The permanent
            # walked-revenue ebitda times margin stays lost.
            ebitda_at_risk = (
                rev_walks * p.contributing_margin_pct
            )
            total_rev_lost += p.annual_revenue_m
            total_ebitda_at_risk += ebitda_at_risk
            total_trough += trough
            total_replacement += replacement
            total_retention += max(
                0.0,
                _retention_bond_needed(p) -
                p.retention_bonus_signed_m,
            )

        net_trough = baseline_ebitda - total_trough
        pct_of_ev = (
            total_ebitda_at_risk * 10.0 /
            max(1.0, inputs.deal_ev_m)
        )
        # EBITDA at risk @ 10x multiple impact vs. deal EV
        # (partner's reflex conversion)

        if total_ebitda_at_risk / max(0.01, baseline_ebitda) > 0.30:
            verdict = "walk"
            read = (
                f"Losing top {count} physicians costs "
                f"~${total_ebitda_at_risk:.1f}M EBITDA "
                "(> 30% of baseline) — the business is "
                "over-concentrated in provider talent. "
                "Walk unless retention package is "
                f"pre-signed ≥${total_retention:.1f}M."
            )
        elif total_ebitda_at_risk / max(0.01, baseline_ebitda) > 0.15:
            verdict = "price_in"
            read = (
                f"Losing top {count} costs "
                f"~${total_ebitda_at_risk:.1f}M "
                "EBITDA — price the retention package "
                f"(${total_retention:.1f}M) into the "
                "deal; haircut purchase price if "
                "seller won't fund it."
            )
        else:
            verdict = "acceptable"
            read = (
                f"Top-{count} loss absorbable "
                f"(~${total_ebitda_at_risk:.1f}M at "
                "risk). Standard retention package "
                "sufficient."
            )

        tiers.append(RetentionStressTier(
            tier_label=label,
            physicians_lost_count=count,
            revenue_lost_m=round(total_rev_lost, 2),
            ebitda_at_risk_m=round(
                total_ebitda_at_risk, 2),
            ebitda_at_risk_pct_of_deal_ev=round(
                pct_of_ev, 4),
            net_ebitda_trough_m=round(net_trough, 2),
            retention_package_needed_m=round(
                total_retention, 2),
            replacement_cost_m=round(
                total_replacement, 2),
            partner_verdict=verdict,
            partner_read=read,
        ))

    # Overall verdict: worst of top-3 tier
    top3_tier = next(
        (t for t in tiers if t.tier_label == "lose_top_3"),
        None,
    )
    if top3_tier is None:
        overall = "acceptable"
        note = "No physicians provided — cannot stress."
    elif top3_tier.partner_verdict == "walk":
        overall = "walk"
        note = (
            "Top-3 loss is deal-killing. Provider "
            "concentration is so high that standard "
            "retention packages don't cover the "
            "downside. Walk unless seller will indemnify "
            "the top-3 loss scenario or the retention "
            "package is pre-signed."
        )
    elif top3_tier.partner_verdict == "price_in":
        overall = "price_in"
        note = (
            "Top-3 loss is meaningful. Require pre-"
            f"signed retention package of "
            f"${top3_tier.retention_package_needed_m:.1f}M "
            "as closing condition; haircut purchase "
            "price by equivalent if seller won't fund."
        )
    else:
        overall = "acceptable"
        note = (
            "Provider concentration is manageable — "
            "top-3 loss absorbs within standard "
            "retention architecture."
        )

    return RetentionStressReport(
        baseline_ebitda_m=round(baseline_ebitda, 2),
        tiers=tiers,
        overall_verdict=overall,
        partner_note=note,
    )


def render_retention_stress_markdown(
    r: RetentionStressReport,
) -> str:
    lines = [
        "# Physician retention stress",
        "",
        f"_Overall verdict: **{r.overall_verdict}**_ — "
        f"{r.partner_note}",
        "",
        f"- Baseline EBITDA (physician-attributed): "
        f"${r.baseline_ebitda_m:.1f}M",
        "",
        "| Tier | Lost | Rev lost $M | EBITDA at risk | "
        "Retention pkg $M | Replacement $M | Verdict |",
        "|---|---|---|---|---|---|---|",
    ]
    for t in r.tiers:
        lines.append(
            f"| {t.tier_label} | "
            f"{t.physicians_lost_count} | "
            f"{t.revenue_lost_m:.1f} | "
            f"${t.ebitda_at_risk_m:.2f}M | "
            f"${t.retention_package_needed_m:.2f} | "
            f"${t.replacement_cost_m:.2f} | "
            f"{t.partner_verdict} |"
        )
    return "\n".join(lines)
