"""Unrealistic on face — the pre-math reflex.

Partner statement: "I don't need to do the math to
know something is wrong. A 400M NPR rural critical-
access hospital projecting 28% IRR is a red flag on
its face. A standalone skilled nursing facility
buying at 9× trailing with 85% Medicare is a red flag
on its face. A dental DSO at 4× revenue with 25%
contribution margin is a red flag on its face. The
math comes later. The sniff test is what saves the
team from spending three weeks modeling a deal that
the senior partner could have passed on by reading
the first page of the teaser."

Distinct from:
- `reasonableness` — per-cell band checks after the
  math is built.
- `heuristics` — post-model rules.
- `red_flags` — structured red-flag catalog.
- `deal_smell_detectors` — 9 combined-signal patterns.

This module runs **before** the math — on teaser /
CIM-level inputs — and surfaces the "this doesn't
smell right" patterns an experienced partner would
flag in 10 seconds. The checks are deliberately
coarse; precision is not the point. The point is to
avoid three-week diligences on deals that fail the
sniff test.

### 14 sniff-test patterns (healthcare-PE canon)

1. **rural_critical_access_high_irr** — rural CAH or
   rural hospital + sponsor IRR > 20%.
2. **snf_high_medicare_high_multiple** — standalone SNF
   + Medicare mix > 70% + EV/EBITDA > 7×.
3. **dental_dso_revenue_multiple** — dental practice at
   > 3× revenue (partner reflex: dental doesn't trade
   on revenue multiples).
4. **outsized_npr_for_ownership** — physician-owned
   group with NPR > $500M claiming minority-seller
   structure (doesn't sell well).
5. **single_asset_high_leverage** — single-site, single-
   specialty + leverage > 5× (concentration + leverage
   combo).
6. **400_bps_margin_expansion_1yr** — claim of margin
   expansion > 400 bps in year 1.
7. **medicare_advantage_to_offset_ffs_cuts** — MA
   growth "covers" reg pressure without named contract
   (overlap with MA bridge trap; caught here at face).
8. **payer_mix_below_35pct_commercial_exit_14x** — exit
   multiple > 13× with < 35% commercial (exit buyer
   will not pay strategic mult for Medicaid-heavy).
9. **standalone_diagnostics_pama_pricing** — standalone
   lab / imaging + PAMA phase rollout in hold period
   (pricing cliff).
10. **non_scaled_home_health_high_margin** — < $40M
    home health + EBITDA margin > 20% (not realistic
    post-PDGM).
11. **rollup_platform_0_cio** — roll-up strategy + no
    named CIO / systems integration leader.
12. **pennsylvania_cpom_physician_group** — CA /
    NY / TX / others CPOM-strict state + physician-
    employed MSO + claim of "clean" structure without
    MSO/PC model verification.
13. **non_profit_to_forprofit_flip_high_margin** —
    recently-converted nonprofit with post-conversion
    EBITDA margin > 2× pre-conversion (sniff: one-time
    reclassification, not real).
14. **critical_access_24x7_unit_margin_improv** —
    critical-access hospital + margin improvement
    claim > 300 bps (regulatory floor + labor
    structure makes it implausible).

### Output

Fired sniff-test patterns + recommendation:
- **stop_work** — 3+ patterns or any kill-level
  pattern fires.
- **senior_partner_review** — 1-2 patterns; escalate
  before spending more associate hours.
- **proceed_with_diligence** — 0 patterns; normal
  path.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class SniffTestInputs:
    subsector: str = "generic"  # e.g. "rural_hospital", "snf", "dental_dso"
    is_rural_critical_access: bool = False
    is_standalone_snf: bool = False
    is_dental_dso: bool = False
    is_standalone_diagnostics: bool = False
    is_home_health: bool = False
    is_rollup_platform: bool = False
    is_cpom_strict_state: bool = False
    recently_converted_nonprofit: bool = False
    is_critical_access_hospital: bool = False
    single_site_single_specialty: bool = False
    npr_m: float = 0.0
    projected_sponsor_irr: float = 0.15
    medicare_mix_pct: float = 0.20
    commercial_mix_pct: float = 0.40
    ev_to_ebitda_multiple: float = 8.0
    ev_to_revenue_multiple: float = 1.5
    leverage_turns: float = 4.0
    margin_expansion_1yr_bps: float = 100.0
    ebitda_margin_pct: float = 0.15
    ma_narrative_present: bool = False
    ma_contract_named: bool = False
    exit_multiple_assumption: float = 10.0
    pama_in_hold: bool = False
    revenue_m: float = 100.0
    has_named_cio: bool = True
    mso_pc_model_verified: bool = True
    pre_conversion_ebitda_margin_pct: float = 0.05


@dataclass
class SniffHit:
    name: str
    kill_level: bool
    message: str


@dataclass
class SniffTestReport:
    fired: List[SniffHit] = field(default_factory=list)
    recommendation: str = "proceed_with_diligence"
    partner_note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "fired": [
                {"name": h.name,
                 "kill_level": h.kill_level,
                 "message": h.message}
                for h in self.fired
            ],
            "recommendation": self.recommendation,
            "partner_note": self.partner_note,
        }


def _rural_cah_high_irr(i: SniffTestInputs) -> Optional[SniffHit]:
    if (i.is_rural_critical_access and
            i.projected_sponsor_irr > 0.20):
        return SniffHit(
            name="rural_critical_access_high_irr",
            kill_level=True,
            message=(
                f"Rural CAH projecting "
                f"{i.projected_sponsor_irr:.0%} IRR — "
                "structurally capped by Medicare FFS "
                "reimbursement and labor floor; red "
                "flag on its face."
            ),
        )
    return None


def _snf_medicare_multiple(i: SniffTestInputs) -> Optional[SniffHit]:
    if (i.is_standalone_snf and
            i.medicare_mix_pct > 0.70 and
            i.ev_to_ebitda_multiple > 7.0):
        return SniffHit(
            name="snf_high_medicare_high_multiple",
            kill_level=True,
            message=(
                f"SNF with {i.medicare_mix_pct:.0%} "
                f"Medicare at {i.ev_to_ebitda_multiple:.1f}× "
                "EV/EBITDA — PDPM pressure + Medicare "
                "rate risk makes multiple unjustifiable."
            ),
        )
    return None


def _dental_revenue_mult(i: SniffTestInputs) -> Optional[SniffHit]:
    if (i.is_dental_dso and
            i.ev_to_revenue_multiple > 3.0):
        return SniffHit(
            name="dental_dso_revenue_multiple",
            kill_level=True,
            message=(
                f"Dental DSO at "
                f"{i.ev_to_revenue_multiple:.1f}× "
                "revenue — dental doesn't trade on "
                "revenue; recheck what's in the "
                "numerator."
            ),
        )
    return None


def _single_asset_leverage(i: SniffTestInputs) -> Optional[SniffHit]:
    if (i.single_site_single_specialty and
            i.leverage_turns > 5.0):
        return SniffHit(
            name="single_asset_high_leverage",
            kill_level=False,
            message=(
                f"Single-site/single-specialty with "
                f"{i.leverage_turns:.1f}× leverage — "
                "concentration + leverage combo; any "
                "regulatory event is existential."
            ),
        )
    return None


def _margin_expansion(i: SniffTestInputs) -> Optional[SniffHit]:
    if i.margin_expansion_1yr_bps > 400:
        return SniffHit(
            name="400_bps_margin_expansion_1yr",
            kill_level=False,
            message=(
                f"Claim of {i.margin_expansion_1yr_bps:.0f} "
                "bps margin expansion in year 1 exceeds "
                "top-decile operator pace; where does it "
                "actually come from?"
            ),
        )
    return None


def _ma_covers_ffs(i: SniffTestInputs) -> Optional[SniffHit]:
    if i.ma_narrative_present and not i.ma_contract_named:
        return SniffHit(
            name="medicare_advantage_to_offset_ffs_cuts",
            kill_level=False,
            message=(
                "MA-will-cover-FFS narrative without a "
                "named MA contract — force the bridge "
                "math (see ma_bridge module)."
            ),
        )
    return None


def _exit_mult_low_commercial(i: SniffTestInputs) -> Optional[SniffHit]:
    if (i.exit_multiple_assumption > 13.0 and
            i.commercial_mix_pct < 0.35):
        return SniffHit(
            name="payer_mix_below_35pct_commercial_exit_14x",
            kill_level=False,
            message=(
                f"Exit mult "
                f"{i.exit_multiple_assumption:.1f}× with "
                f"{i.commercial_mix_pct:.0%} commercial — "
                "strategic buyer won't pay platform mult "
                "for Medicaid-heavy mix."
            ),
        )
    return None


def _diagnostics_pama(i: SniffTestInputs) -> Optional[SniffHit]:
    if i.is_standalone_diagnostics and i.pama_in_hold:
        return SniffHit(
            name="standalone_diagnostics_pama_pricing",
            kill_level=False,
            message=(
                "Standalone lab/imaging with PAMA "
                "phase rollout in hold — price the "
                "cliff; partners have lost money on "
                "this before."
            ),
        )
    return None


def _hh_high_margin(i: SniffTestInputs) -> Optional[SniffHit]:
    if (i.is_home_health and
            i.revenue_m < 40 and
            i.ebitda_margin_pct > 0.20):
        return SniffHit(
            name="non_scaled_home_health_high_margin",
            kill_level=False,
            message=(
                f"Sub-$40M home health at "
                f"{i.ebitda_margin_pct:.0%} margin — "
                "not realistic post-PDGM without "
                "sustained capture-rate explanation."
            ),
        )
    return None


def _rollup_no_cio(i: SniffTestInputs) -> Optional[SniffHit]:
    if i.is_rollup_platform and not i.has_named_cio:
        return SniffHit(
            name="rollup_platform_0_cio",
            kill_level=False,
            message=(
                "Roll-up strategy without named CIO / "
                "integration leader — platform "
                "execution will stall in year 1."
            ),
        )
    return None


def _cpom_unverified(i: SniffTestInputs) -> Optional[SniffHit]:
    if (i.is_cpom_strict_state and
            not i.mso_pc_model_verified):
        return SniffHit(
            name="cpom_physician_group_unverified",
            kill_level=False,
            message=(
                "CPOM-strict state (CA / NY / TX / "
                "others) with physician-group MSO "
                "claim but no verified MSO/PC model — "
                "corporate-practice-of-medicine risk."
            ),
        )
    return None


def _nonprofit_flip(i: SniffTestInputs) -> Optional[SniffHit]:
    if (i.recently_converted_nonprofit and
            i.pre_conversion_ebitda_margin_pct > 0 and
            i.ebitda_margin_pct >
            2 * i.pre_conversion_ebitda_margin_pct):
        return SniffHit(
            name="non_profit_to_forprofit_flip_high_margin",
            kill_level=False,
            message=(
                f"Post-conversion margin "
                f"{i.ebitda_margin_pct:.0%} vs. pre "
                f"{i.pre_conversion_ebitda_margin_pct:.0%} — "
                "suggests one-time reclassification, "
                "not recurring EBITDA."
            ),
        )
    return None


def _cah_margin_improv(i: SniffTestInputs) -> Optional[SniffHit]:
    if (i.is_critical_access_hospital and
            i.margin_expansion_1yr_bps > 300):
        return SniffHit(
            name="critical_access_24x7_unit_margin_improv",
            kill_level=False,
            message=(
                "Critical-access hospital with > 300 "
                "bps margin improvement claim — reg "
                "floor + 24/7 labor structure makes "
                "this implausible."
            ),
        )
    return None


def _outsized_npr(i: SniffTestInputs) -> Optional[SniffHit]:
    if i.npr_m > 500 and i.subsector == "physician_group":
        return SniffHit(
            name="outsized_npr_for_ownership",
            kill_level=False,
            message=(
                f"Physician-owned group at "
                f"${i.npr_m:.0f}M NPR claiming "
                "minority-seller structure — size-vs-"
                "structure mismatch; seller usually "
                "wants rollover and control, not "
                "minority."
            ),
        )
    return None


_CHECKS = [
    _rural_cah_high_irr,
    _snf_medicare_multiple,
    _dental_revenue_mult,
    _outsized_npr,
    _single_asset_leverage,
    _margin_expansion,
    _ma_covers_ffs,
    _exit_mult_low_commercial,
    _diagnostics_pama,
    _hh_high_margin,
    _rollup_no_cio,
    _cpom_unverified,
    _nonprofit_flip,
    _cah_margin_improv,
]


def run_sniff_test(
    inputs: SniffTestInputs,
) -> SniffTestReport:
    fired: List[SniffHit] = []
    for check in _CHECKS:
        hit = check(inputs)
        if hit is not None:
            fired.append(hit)

    any_kill = any(h.kill_level for h in fired)
    if any_kill or len(fired) >= 3:
        rec = "stop_work"
        note = (
            f"{len(fired)} sniff-test patterns fired — "
            "do not spend more associate hours until "
            "senior partner reviews. The red flag is "
            "visible on the teaser; get opinion before "
            "diligencing."
        )
    elif len(fired) >= 1:
        rec = "senior_partner_review"
        note = (
            f"{len(fired)} sniff-test pattern(s) fired "
            "— escalate to senior partner before "
            "committing more diligence spend; coarse "
            "checks but they hold up."
        )
    else:
        rec = "proceed_with_diligence"
        note = (
            "No sniff-test patterns fired at teaser "
            "level. Proceed to standard diligence."
        )

    return SniffTestReport(
        fired=fired,
        recommendation=rec,
        partner_note=note,
    )


def render_sniff_markdown(r: SniffTestReport) -> str:
    flag = {
        "stop_work": "⚠ stop work",
        "senior_partner_review": "↑ escalate",
        "proceed_with_diligence": "proceed",
    }.get(r.recommendation, r.recommendation)
    lines = [
        "# Unrealistic-on-face sniff test",
        "",
        f"_**{flag}**_ — {r.partner_note}",
        "",
        "## Patterns fired",
    ]
    if r.fired:
        for h in r.fired:
            kill = " (kill)" if h.kill_level else ""
            lines.append(f"- **{h.name}**{kill}: {h.message}")
    else:
        lines.append("- None")
    return "\n".join(lines)
