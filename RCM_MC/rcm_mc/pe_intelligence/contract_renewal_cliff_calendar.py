"""Contract renewal cliff calendar — every contract that resets in hold.

Partner statement: "Stack every contract renewal —
commercial payer, GPO, IT vendor, real-estate lease,
key-employment agreement — by quarter. That's my
diligence calendar. The cliff is the quarter with the
most material dollars rolling over. Underwrite that
quarter explicitly. The rest of the calendar is
the warning system."

Distinct from:
- `payer_renegotiation_timing_model` — only
  commercial payer contracts.
- `reimbursement_cliff_calendar_2026_2029` —
  regulatory rule events only.
- `contract_diligence` — generic contract review.

This module aggregates ALL contract renewals across
contract types into one calendar, ranked by quarter,
with the dollar exposure flagged per renewal.

### Contract types and partner read

- `commercial_payer` — biggest dollar exposure;
  rate-cut risk
- `gpo_supply` — supply-chain rebate / unit-cost
  risk
- `it_vendor` — switching cost, transition risk
  (RCM/EHR/PM)
- `real_estate_lease` — rent step + retention
  risk if landlord won't renew
- `key_employment` — retention bonus / non-compete
  reset
- `physician_employment` — see physician_retention
  module too
- `medical_director` — typical 1-3yr terms with
  built-in rate review
- `risk_share_vbc` — population-risk contract
  re-rate

### Output

- per-quarter list of renewals
- the cliff quarter (most $ rolling over)
- contract-type concentration
- partner verdict: balanced / cliff_warning / lumpy
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Any, Dict, List, Optional


CONTRACT_TYPES = (
    "commercial_payer",
    "gpo_supply",
    "it_vendor",
    "real_estate_lease",
    "key_employment",
    "physician_employment",
    "medical_director",
    "risk_share_vbc",
)


@dataclass
class ContractRenewal:
    name: str
    contract_type: str
    expiration_date: date
    annual_value_m: float
    expected_rate_change_pct: float = 0.0
    notes: str = ""


@dataclass
class RenewalCalendarInputs:
    contracts: List[ContractRenewal] = field(
        default_factory=list)
    hold_start_date: date = date(2026, 1, 1)
    hold_years: int = 5


@dataclass
class QuarterStack:
    year: int
    quarter: int
    quarter_offset: int
    renewals_count: int
    total_annual_value_m: float
    contracts: List[Dict[str, Any]] = field(
        default_factory=list)


@dataclass
class RenewalCalendarReport:
    quarters: List[QuarterStack] = field(
        default_factory=list)
    total_renewals_in_hold: int = 0
    total_annual_value_in_hold_m: float = 0.0
    cliff_quarter_label: str = ""
    cliff_quarter_value_m: float = 0.0
    type_concentration: Dict[str, float] = field(
        default_factory=dict)
    verdict: str = "balanced"
    partner_note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "quarters": [
                {"year": q.year,
                 "quarter": q.quarter,
                 "quarter_offset": q.quarter_offset,
                 "renewals_count": q.renewals_count,
                 "total_annual_value_m":
                     q.total_annual_value_m,
                 "contracts": q.contracts}
                for q in self.quarters
            ],
            "total_renewals_in_hold":
                self.total_renewals_in_hold,
            "total_annual_value_in_hold_m":
                self.total_annual_value_in_hold_m,
            "cliff_quarter_label":
                self.cliff_quarter_label,
            "cliff_quarter_value_m":
                self.cliff_quarter_value_m,
            "type_concentration":
                self.type_concentration,
            "verdict": self.verdict,
            "partner_note": self.partner_note,
        }


def _quarter_offset(start: date, target: date) -> int:
    delta_days = (target - start).days
    return delta_days // 91


def build_renewal_calendar(
    inputs: RenewalCalendarInputs,
) -> RenewalCalendarReport:
    total_quarters = inputs.hold_years * 4
    quarter_buckets: Dict[int, QuarterStack] = {}
    for q in range(total_quarters):
        year = q // 4 + 1
        quarter = q % 4 + 1
        quarter_buckets[q] = QuarterStack(
            year=year,
            quarter=quarter,
            quarter_offset=q,
            renewals_count=0,
            total_annual_value_m=0.0,
            contracts=[],
        )

    type_totals: Dict[str, float] = {}
    total_value = 0.0
    total_count = 0

    for c in inputs.contracts:
        offset = _quarter_offset(
            inputs.hold_start_date, c.expiration_date
        )
        if not (0 <= offset < total_quarters):
            continue
        bucket = quarter_buckets[offset]
        bucket.renewals_count += 1
        bucket.total_annual_value_m += c.annual_value_m
        bucket.contracts.append({
            "name": c.name,
            "contract_type": c.contract_type,
            "expiration_date": c.expiration_date.isoformat(),
            "annual_value_m": round(c.annual_value_m, 2),
            "expected_rate_change_pct":
                c.expected_rate_change_pct,
            "notes": c.notes,
        })
        type_totals[c.contract_type] = (
            type_totals.get(c.contract_type, 0.0) +
            c.annual_value_m
        )
        total_value += c.annual_value_m
        total_count += 1

    sorted_quarters = sorted(
        quarter_buckets.values(),
        key=lambda q: q.quarter_offset,
    )

    # Cliff quarter = quarter with most $ rolling over
    cliff = max(
        sorted_quarters,
        key=lambda q: q.total_annual_value_m,
        default=None,
    )
    if cliff is None or cliff.total_annual_value_m == 0:
        cliff_label = ""
        cliff_value = 0.0
    else:
        cliff_label = f"Y{cliff.year}Q{cliff.quarter}"
        cliff_value = cliff.total_annual_value_m

    type_concentration = {
        k: round(v / total_value, 4) if total_value else 0.0
        for k, v in type_totals.items()
    }

    if total_count == 0:
        verdict = "balanced"
        note = (
            "No contracts roll over in hold window. "
            "Either hold is short or contract base is "
            "incomplete — verify contract inventory."
        )
    elif cliff_value > total_value * 0.40:
        verdict = "cliff_warning"
        note = (
            f"Cliff at {cliff_label}: "
            f"${cliff_value:.1f}M of "
            f"${total_value:.1f}M rolls in one quarter "
            "(>40% concentration). Underwrite that "
            "quarter explicitly; one bad outcome "
            "compounds."
        )
    elif cliff_value > total_value * 0.25:
        verdict = "lumpy"
        note = (
            f"Lumpy cliff at {cliff_label} "
            f"(${cliff_value:.1f}M / "
            f"${total_value:.1f}M). Manageable but "
            "give the cliff quarter pre-prep priority."
        )
    else:
        verdict = "balanced"
        note = (
            f"Balanced renewal calendar — top quarter "
            f"{cliff_label} only "
            f"${cliff_value:.1f}M / "
            f"${total_value:.1f}M. Standard cadence "
            "for renewal management."
        )

    return RenewalCalendarReport(
        quarters=sorted_quarters,
        total_renewals_in_hold=total_count,
        total_annual_value_in_hold_m=round(total_value, 2),
        cliff_quarter_label=cliff_label,
        cliff_quarter_value_m=round(cliff_value, 2),
        type_concentration=type_concentration,
        verdict=verdict,
        partner_note=note,
    )


def render_renewal_calendar_markdown(
    r: RenewalCalendarReport,
) -> str:
    lines = [
        "# Contract renewal cliff calendar",
        "",
        f"_Verdict: **{r.verdict}**_ — {r.partner_note}",
        "",
        f"- Total renewals in hold: "
        f"{r.total_renewals_in_hold}",
        f"- Total annual value: "
        f"${r.total_annual_value_in_hold_m:.1f}M",
        f"- Cliff quarter: {r.cliff_quarter_label} "
        f"(${r.cliff_quarter_value_m:.1f}M)",
        "",
        "## Type concentration",
    ]
    for t, share in sorted(
        r.type_concentration.items(),
        key=lambda kv: kv[1], reverse=True,
    ):
        lines.append(f"- {t}: {share:.0%}")
    lines.append("")
    lines.append("## Quarter stack")
    lines.append("")
    lines.append(
        "| Quarter | # renewals | $M annual value |")
    lines.append("|---|---|---|")
    for q in r.quarters:
        if q.renewals_count == 0:
            continue
        lines.append(
            f"| Y{q.year}Q{q.quarter} | "
            f"{q.renewals_count} | "
            f"${q.total_annual_value_m:.1f}M |"
        )
    return "\n".join(lines)
