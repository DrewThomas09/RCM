"""Platform vs. add-on classifier — 2-4 turns of multiple.

Partner statement: "Every seller pitches their company as
a platform. Most are add-ons. Platforms trade at 12-15x;
add-ons at 8-9x. If we misclassify at underwrite, we lose
2-4 turns of entry. Classify before you price."

Distinct from:
- `add_on_fit_scorer` — scores a specific add-on for a
  platform.
- `ma_pipeline` — tracks the M&A pipeline generally.

### What makes a platform

Partners apply a checklist. A **platform** has:

1. EBITDA ≥ $25M (scale threshold).
2. Standalone back-office (EHR, PMS, RCM, HR, finance).
3. Management team owns at least 3 P&L lines.
4. Geographic or specialty scale that could absorb an
   add-on.
5. Bankable standalone — syndicate could lend to it
   alone.
6. Subsector brand / recognition.
7. Integration capability — has done at least 1 add-on
   internally or has operator who has.
8. Board / governance model ready for sponsor oversight.

An **add-on** has ≤ 3 of these. A **hybrid** has 4-6.

### Multiple-guidance ladder

- `platform` (7-8/8) → supports 11-14x multiple range.
- `hybrid` (4-6/8) → supports 9-11x; price at platform
  discount but not add-on.
- `add_on` (≤ 3/8) → supports 7-9x; fold into an
  existing platform, don't build around.

### Why partners care

The #1 overpayment pattern in healthcare PE is paying
platform multiples for add-on-scale assets. This module
is the pre-LOI classification gate.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class PlatformClassifierInputs:
    ebitda_m: float = 0.0
    standalone_back_office: bool = False
    pnl_lines_under_mgmt: int = 0
    geographic_or_specialty_scale: bool = False
    bankable_standalone: bool = False
    subsector_brand_recognition: bool = False
    integration_capability_proven: bool = False
    board_governance_ready: bool = False


@dataclass
class ClassifierDimension:
    name: str
    passed: bool
    partner_comment: str


@dataclass
class PlatformClassificationReport:
    score: int                             # 0-8
    tier: str                              # platform / hybrid / add_on
    supported_multiple_range: str          # e.g., "11-14x"
    dimensions: List[ClassifierDimension] = field(default_factory=list)
    partner_note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "score": self.score,
            "tier": self.tier,
            "supported_multiple_range":
                self.supported_multiple_range,
            "dimensions": [
                {"name": d.name, "passed": d.passed,
                 "partner_comment": d.partner_comment}
                for d in self.dimensions
            ],
            "partner_note": self.partner_note,
        }


def classify_platform_vs_addon(
    inputs: PlatformClassifierInputs,
) -> PlatformClassificationReport:
    dims: List[ClassifierDimension] = []

    # 1. EBITDA ≥ 25.
    ebitda_ok = inputs.ebitda_m >= 25.0
    dims.append(ClassifierDimension(
        name="ebitda_at_scale_threshold",
        passed=ebitda_ok,
        partner_comment=(
            f"EBITDA ${inputs.ebitda_m:,.1f}M ≥ $25M "
            "platform threshold."
            if ebitda_ok else
            f"EBITDA ${inputs.ebitda_m:,.1f}M below $25M "
            "platform threshold — sub-scale."
        ),
    ))

    # 2. Standalone back-office.
    dims.append(ClassifierDimension(
        name="standalone_back_office",
        passed=inputs.standalone_back_office,
        partner_comment=(
            "Standalone back-office (EHR / PMS / RCM) — "
            "platform-capable systems."
            if inputs.standalone_back_office else
            "No standalone back-office — platform-level "
            "systems would need investment."
        ),
    ))

    # 3. ≥ 3 P&L lines.
    pnl_ok = inputs.pnl_lines_under_mgmt >= 3
    dims.append(ClassifierDimension(
        name="pnl_lines_under_mgmt_gte_3",
        passed=pnl_ok,
        partner_comment=(
            f"{inputs.pnl_lines_under_mgmt} P&L lines — "
            "management depth."
            if pnl_ok else
            f"{inputs.pnl_lines_under_mgmt} P&L lines — "
            "management thin; plan owned by CEO."
        ),
    ))

    # 4. Geographic / specialty scale.
    dims.append(ClassifierDimension(
        name="geographic_or_specialty_scale",
        passed=inputs.geographic_or_specialty_scale,
        partner_comment=(
            "Geographic / specialty scale to absorb "
            "add-ons."
            if inputs.geographic_or_specialty_scale else
            "No scale to absorb add-ons — bolt-on-of-"
            "bolt-on risk."
        ),
    ))

    # 5. Bankable standalone.
    dims.append(ClassifierDimension(
        name="bankable_standalone",
        passed=inputs.bankable_standalone,
        partner_comment=(
            "Bankable standalone — syndicate would lend."
            if inputs.bankable_standalone else
            "Not bankable standalone — needs sponsor "
            "credit support."
        ),
    ))

    # 6. Brand recognition.
    dims.append(ClassifierDimension(
        name="subsector_brand_recognition",
        passed=inputs.subsector_brand_recognition,
        partner_comment=(
            "Subsector brand — recognized in deal flow."
            if inputs.subsector_brand_recognition else
            "No subsector brand — physician / referral "
            "flow not earned."
        ),
    ))

    # 7. Integration capability.
    dims.append(ClassifierDimension(
        name="integration_capability_proven",
        passed=inputs.integration_capability_proven,
        partner_comment=(
            "Integration capability proven — done it "
            "before."
            if inputs.integration_capability_proven else
            "No integration track record — platform "
            "thesis requires it."
        ),
    ))

    # 8. Board / governance ready.
    dims.append(ClassifierDimension(
        name="board_governance_ready",
        passed=inputs.board_governance_ready,
        partner_comment=(
            "Governance / board structure ready for "
            "sponsor oversight."
            if inputs.board_governance_ready else
            "Governance not ready — 90-day sponsor "
            "onboarding required."
        ),
    ))

    score = sum(1 for d in dims if d.passed)
    if score >= 7:
        tier = "platform"
        mult_range = "11-14x"
        note = (
            f"Platform ({score}/8). Supports 11-14x "
            "multiple. Partner: price to platform; "
            "underwrite add-ons in the thesis."
        )
    elif score >= 4:
        tier = "hybrid"
        mult_range = "9-11x"
        note = (
            f"Hybrid ({score}/8). Supports 9-11x. Partner: "
            "platform-discount; acknowledge build-out "
            "required."
        )
    else:
        tier = "add_on"
        mult_range = "7-9x"
        note = (
            f"Add-on ({score}/8). Supports 7-9x. Partner: "
            "fold into existing platform or build a "
            "platform around another asset — this is not "
            "a platform."
        )

    return PlatformClassificationReport(
        score=score,
        tier=tier,
        supported_multiple_range=mult_range,
        dimensions=dims,
        partner_note=note,
    )


def render_platform_classification_markdown(
    r: PlatformClassificationReport,
) -> str:
    lines = [
        "# Platform vs. add-on classification",
        "",
        f"**Tier:** `{r.tier}` ({r.score}/8)",
        "",
        f"**Supported multiple range:** "
        f"{r.supported_multiple_range}",
        "",
        f"_{r.partner_note}_",
        "",
        "| Dimension | Passed | Partner comment |",
        "|---|---|---|",
    ]
    for d in r.dimensions:
        check = "✓" if d.passed else "✗"
        lines.append(
            f"| {d.name} | {check} | {d.partner_comment} |"
        )
    return "\n".join(lines)
