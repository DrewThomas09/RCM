"""Management incentive sizer — MIP / LTIP sizing + vesting.

Post-LBO management incentive plans typically come in two buckets:

- **MIP (Management Incentive Plan)** — equity or option pool,
  typically 8-15% of post-close equity, tiered: CEO ~2-4%, C-suite
  ~4-6% total, balance for broader management.
- **LTIP (Long-Term Incentive)** — cash-settled performance awards
  keyed to MOIC / IRR hurdles; typically 15-25% of CEO cash comp.

Market practice (partner-approximated, 2024):

- Platform LBOs: 10% MIP pool standard.
- Physician PPM: 12-15% pool (critical to retain senior docs).
- Smaller carve-outs: 8% pool; harder to justify more.
- Vesting: 4-year cliff + time-based, accelerated on MOIC hurdles
  (e.g., 100% vest at 2.5x MOIC).

This module takes deal size + type + a few partner preferences
and returns a recommended allocation + partner note.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class MIPInputs:
    post_close_equity_m: float
    deal_type: str = "platform"           # "platform" / "physician_ppm" /
                                          # "carve_out" / "add_on"
    ceo_cash_comp_k: float = 750.0
    total_management_headcount: int = 10
    ceo_is_founder: bool = False           # often gets retention premium
    time_to_target_moic_years: int = 5
    target_moic: float = 2.5


@dataclass
class MIPAllocation:
    layer: str                            # "ceo" / "c_suite" / "management"
    headcount: int
    pct_of_pool: float
    share_count_m: float                  # post-close shares / options
    note: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "layer": self.layer, "headcount": self.headcount,
            "pct_of_pool": self.pct_of_pool,
            "share_count_m": self.share_count_m,
            "note": self.note,
        }


@dataclass
class MIPPlan:
    mip_pool_pct: float                   # pool as % of post-close equity
    mip_pool_m: float                     # pool in $ equivalent
    ltip_annual_cash_k: float             # CEO LTIP cash target
    vesting: str
    accel_clause: str
    allocations: List[MIPAllocation] = field(default_factory=list)
    partner_note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "mip_pool_pct": self.mip_pool_pct,
            "mip_pool_m": self.mip_pool_m,
            "ltip_annual_cash_k": self.ltip_annual_cash_k,
            "vesting": self.vesting,
            "accel_clause": self.accel_clause,
            "allocations": [a.to_dict() for a in self.allocations],
            "partner_note": self.partner_note,
        }


BASE_POOL_PCT = {
    "platform": 0.10,
    "physician_ppm": 0.13,
    "carve_out": 0.08,
    "add_on": 0.05,
}


def size_mip(inputs: MIPInputs) -> MIPPlan:
    base_pct = BASE_POOL_PCT.get(inputs.deal_type, 0.10)
    # Adjustments.
    if inputs.ceo_is_founder:
        base_pct += 0.015        # retention premium
    if inputs.total_management_headcount >= 15:
        base_pct += 0.01         # broader plan distribution
    pool_pct = min(0.18, base_pct)

    pool_m = inputs.post_close_equity_m * pool_pct

    # Layer split.
    ceo_pct = 0.30 if inputs.ceo_is_founder else 0.25
    csuite_pct = 0.35
    mgmt_pct = 1.0 - ceo_pct - csuite_pct

    allocations = [
        MIPAllocation(
            layer="ceo", headcount=1,
            pct_of_pool=round(ceo_pct, 3),
            share_count_m=round(pool_m * ceo_pct, 2),
            note=("CEO gets largest single allocation; time-based 4yr "
                  "vest with MOIC accelerator."),
        ),
        MIPAllocation(
            layer="c_suite", headcount=4,
            pct_of_pool=round(csuite_pct, 3),
            share_count_m=round(pool_m * csuite_pct, 2),
            note=("COO / CFO / CRO / CMO typical coverage at this layer."),
        ),
        MIPAllocation(
            layer="management",
            headcount=max(1, inputs.total_management_headcount - 5),
            pct_of_pool=round(mgmt_pct, 3),
            share_count_m=round(pool_m * mgmt_pct, 2),
            note="Broader management, VP+ coverage; discretionary grants.",
        ),
    ]

    # LTIP annual target ~20% of CEO cash comp.
    ltip = inputs.ceo_cash_comp_k * 0.20

    vesting = "4-year cliff with quarterly vest post-cliff"
    accel = (f"100% MOIC accelerator at {inputs.target_moic:.1f}x; "
             f"50% at {inputs.target_moic - 0.5:.1f}x.")

    if pool_pct >= 0.15:
        note = (f"MIP pool {pool_pct*100:.1f}% of post-close equity "
                f"(${pool_m:,.1f}M). Above market median — justify "
                "on retention risk or founder relationship.")
    elif pool_pct <= 0.06:
        note = (f"MIP pool {pool_pct*100:.1f}% (${pool_m:,.1f}M) is "
                "thin — verify that management will engage at this level.")
    else:
        note = (f"MIP pool {pool_pct*100:.1f}% (${pool_m:,.1f}M) is "
                f"within market band for {inputs.deal_type}.")

    return MIPPlan(
        mip_pool_pct=round(pool_pct, 4),
        mip_pool_m=round(pool_m, 2),
        ltip_annual_cash_k=round(ltip, 2),
        vesting=vesting, accel_clause=accel,
        allocations=allocations,
        partner_note=note,
    )


def render_mip_markdown(plan: MIPPlan) -> str:
    lines = [
        "# Management incentive plan",
        "",
        f"_{plan.partner_note}_",
        "",
        f"- MIP pool: {plan.mip_pool_pct*100:.1f}% "
        f"(${plan.mip_pool_m:,.1f}M)",
        f"- LTIP annual cash target (CEO): ${plan.ltip_annual_cash_k:,.0f}K",
        f"- Vesting: {plan.vesting}",
        f"- Accelerator: {plan.accel_clause}",
        "",
        "## Allocations",
        "",
    ]
    for a in plan.allocations:
        lines.append(
            f"- **{a.layer}** (n={a.headcount}): "
            f"{a.pct_of_pool*100:.1f}% of pool "
            f"(${a.share_count_m:,.2f}M) — {a.note}"
        )
    return "\n".join(lines)
