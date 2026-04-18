"""RAC / OIG audit exposure estimator — the number partners fear.

Partners in healthcare PE are terrified of RAC (Recovery Audit
Contractor) and OIG audits because the dollars are disproportionate
and the audits are retroactive. This module sizes the $ exposure
given packet signals:

- Medicare FFS revenue share + coding-aggression signals.
- Historical denial rate + RAC-finding rate.
- Whether CDI program is in place or not.
- CMI uplift claimed (a claimed CMI lift invites RAC scrutiny
  proportional to the gap).
- Open FCA / whistleblower exposure.

Output: expected-loss $ range (low / mid / high), audit hit rate
assumption, and a partner note on whether this is material vs
base EBITDA.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class RACInputs:
    medicare_ffs_revenue_m: float = 0.0
    historical_denial_rate: float = 0.08
    claimed_cmi_uplift: float = 0.0          # pts above baseline
    cdi_program_in_place: bool = False
    aggressive_coding_flags: int = 0         # count from prior audits
    open_fca_exposure: bool = False
    base_ebitda_m: float = 0.0


@dataclass
class RACExposureReport:
    base_audit_hit_rate: float
    adjusted_audit_hit_rate: float
    exposed_revenue_m: float
    expected_loss_low_m: float
    expected_loss_mid_m: float
    expected_loss_high_m: float
    loss_as_pct_of_ebitda: float
    partner_note: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "base_audit_hit_rate": self.base_audit_hit_rate,
            "adjusted_audit_hit_rate": self.adjusted_audit_hit_rate,
            "exposed_revenue_m": self.exposed_revenue_m,
            "expected_loss_low_m": self.expected_loss_low_m,
            "expected_loss_mid_m": self.expected_loss_mid_m,
            "expected_loss_high_m": self.expected_loss_high_m,
            "loss_as_pct_of_ebitda": self.loss_as_pct_of_ebitda,
            "partner_note": self.partner_note,
        }


def estimate_rac_exposure(inputs: RACInputs) -> RACExposureReport:
    # Base RAC hit rate: 1-2% of Medicare FFS revenue historically.
    base_rate = 0.015

    # Adjust by signals.
    rate = base_rate
    if inputs.historical_denial_rate >= 0.12:
        rate += 0.010
    elif inputs.historical_denial_rate >= 0.08:
        rate += 0.003
    if inputs.claimed_cmi_uplift >= 0.10:
        rate += 0.015
    elif inputs.claimed_cmi_uplift >= 0.05:
        rate += 0.008
    if not inputs.cdi_program_in_place:
        rate += 0.005
    rate += 0.005 * min(5, inputs.aggressive_coding_flags)
    if inputs.open_fca_exposure:
        rate += 0.025

    rate = min(0.15, rate)

    # RAC takeback typical: 2-3 years of revenue under review.
    review_years = 3
    exposed_rev = inputs.medicare_ffs_revenue_m * review_years
    expected_mid = exposed_rev * rate
    expected_low = expected_mid * 0.50
    expected_high = expected_mid * 2.0

    loss_pct_ebitda = (expected_mid / inputs.base_ebitda_m
                        if inputs.base_ebitda_m > 0 else 0.0)

    if loss_pct_ebitda >= 0.30:
        note = (f"RAC exposure ~${expected_mid:,.1f}M mid-case is "
                f"{loss_pct_ebitda*100:.0f}% of base EBITDA. This is "
                "an IC-blocking number — forensic billing diligence "
                "is non-negotiable; partner should not approve "
                "without an adjustment to purchase price.")
    elif loss_pct_ebitda >= 0.10:
        note = (f"RAC exposure ~${expected_mid:,.1f}M "
                f"({loss_pct_ebitda*100:.0f}% of EBITDA) is "
                "material. Structure purchase-price earn-out or "
                "indemnity for the audit window.")
    elif loss_pct_ebitda >= 0.03:
        note = (f"RAC exposure ~${expected_mid:,.1f}M is modest but "
                "not ignorable. Standard reps & warranties with "
                "typical insurance coverage.")
    elif inputs.medicare_ffs_revenue_m > 0:
        note = (f"RAC exposure immaterial at ${expected_mid:,.2f}M. "
                "Not a meaningful lever in this deal.")
    else:
        note = ("No meaningful Medicare FFS exposure — RAC risk is "
                "not applicable.")

    return RACExposureReport(
        base_audit_hit_rate=round(base_rate, 4),
        adjusted_audit_hit_rate=round(rate, 4),
        exposed_revenue_m=round(exposed_rev, 2),
        expected_loss_low_m=round(expected_low, 2),
        expected_loss_mid_m=round(expected_mid, 2),
        expected_loss_high_m=round(expected_high, 2),
        loss_as_pct_of_ebitda=round(loss_pct_ebitda, 4),
        partner_note=note,
    )


def render_rac_markdown(r: RACExposureReport) -> str:
    lines = [
        "# RAC / OIG audit exposure",
        "",
        f"_{r.partner_note}_",
        "",
        f"- Base audit hit rate: "
        f"{r.base_audit_hit_rate*100:.2f}%",
        f"- Adjusted for signals: "
        f"{r.adjusted_audit_hit_rate*100:.2f}%",
        f"- Exposed revenue (3-year look-back): "
        f"${r.exposed_revenue_m:,.1f}M",
        f"- Expected loss low: ${r.expected_loss_low_m:,.2f}M",
        f"- Expected loss mid: ${r.expected_loss_mid_m:,.2f}M",
        f"- Expected loss high: ${r.expected_loss_high_m:,.2f}M",
        f"- Mid vs base EBITDA: "
        f"{r.loss_as_pct_of_ebitda*100:.1f}%",
    ]
    return "\n".join(lines)
