"""Management compensation — MIP / LTIP sanity checks.

Partner-prudent ranges for healthcare-PE comp plans:

- **Management equity pool (MIP)** — 8-15% of fully-diluted pool for
  the top ~20 executives.
- **CEO allocation of MIP** — 30-50% of the pool.
- **Vesting** — 4-5 year ratable, cliff at 12 months.
- **Acceleration** — single-trigger is aggressive; double-trigger
  is standard.
- **LTIP** — annual cash performance bonus 25-75% of base depending
  on level.
- **Equity rollover** — 5-15% rollover for seller-CEOs aligns
  incentives without over-concentration.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class CompPlanInputs:
    mip_pool_pct: Optional[float] = None
    ceo_mip_share_pct: Optional[float] = None
    vesting_years: Optional[float] = None
    cliff_months: Optional[int] = None
    acceleration_type: Optional[str] = None    # "single" | "double" | "none"
    ceo_equity_rollover_pct: Optional[float] = None
    ltip_bonus_multiple_base: Optional[float] = None  # e.g. 0.50 = 50%
    performance_vesting_pct: Optional[float] = None   # fraction of grant tied to perf


@dataclass
class CompFinding:
    area: str
    status: str                      # "standard" | "aggressive" | "light" | "unknown"
    detail: str
    remediation: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "area": self.area,
            "status": self.status,
            "detail": self.detail,
            "remediation": self.remediation,
        }


@dataclass
class CompReport:
    findings: List[CompFinding] = field(default_factory=list)
    partner_note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "findings": [f.to_dict() for f in self.findings],
            "partner_note": self.partner_note,
        }


# ── Checks ──────────────────────────────────────────────────────────

def _pct(v: Optional[float]) -> Optional[float]:
    if v is None:
        return None
    f = float(v)
    if f > 1.5:
        f /= 100.0
    return f


def _check_mip_pool(inputs: CompPlanInputs) -> Optional[CompFinding]:
    v = _pct(inputs.mip_pool_pct)
    if v is None:
        return None
    if v < 0.05:
        return CompFinding(
            area="mip_pool",
            status="light",
            detail=f"MIP pool {v*100:.1f}% is below the 8-15% peer band.",
            remediation="Expand pool to ≥10% to attract and retain talent.",
        )
    if v > 0.20:
        return CompFinding(
            area="mip_pool",
            status="aggressive",
            detail=f"MIP pool {v*100:.1f}% is above the 8-15% peer band.",
            remediation="Narrow pool or tighten vesting; risk of carry dilution.",
        )
    return CompFinding(
        area="mip_pool", status="standard",
        detail=f"MIP pool {v*100:.1f}% — within peer range.",
    )


def _check_ceo_share(inputs: CompPlanInputs) -> Optional[CompFinding]:
    v = _pct(inputs.ceo_mip_share_pct)
    if v is None:
        return None
    if v < 0.25:
        return CompFinding(
            area="ceo_mip_share",
            status="light",
            detail=f"CEO {v*100:.0f}% of MIP is below the 30-50% peer range.",
            remediation="Reallocate to give CEO meaningful wealth-creation event.",
        )
    if v > 0.60:
        return CompFinding(
            area="ceo_mip_share",
            status="aggressive",
            detail=f"CEO {v*100:.0f}% of MIP is above the 30-50% peer range.",
            remediation="Broaden share to retain L2 leaders.",
        )
    return CompFinding(
        area="ceo_mip_share", status="standard",
        detail=f"CEO {v*100:.0f}% of MIP — within peer range.",
    )


def _check_vesting(inputs: CompPlanInputs) -> Optional[CompFinding]:
    if inputs.vesting_years is None:
        return None
    v = float(inputs.vesting_years)
    if v < 3:
        return CompFinding(
            area="vesting",
            status="light",
            detail=f"Vesting period {v:.1f}yr is below peer standard (4-5).",
            remediation="Extend vesting to align with hold duration.",
        )
    if v > 6:
        return CompFinding(
            area="vesting",
            status="aggressive",
            detail=f"Vesting period {v:.1f}yr is above peer standard (4-5).",
            remediation="Shorten vesting so it doesn't outlast the hold.",
        )
    return CompFinding(
        area="vesting", status="standard",
        detail=f"Vesting period {v:.1f}yr — within peer standard.",
    )


def _check_cliff(inputs: CompPlanInputs) -> Optional[CompFinding]:
    if inputs.cliff_months is None:
        return None
    c = int(inputs.cliff_months)
    if c < 6:
        return CompFinding(
            area="cliff",
            status="light",
            detail=f"Cliff {c}mo is below the 12mo peer standard.",
            remediation="Extend cliff to protect against early departures.",
        )
    if c > 24:
        return CompFinding(
            area="cliff",
            status="aggressive",
            detail=f"Cliff {c}mo is longer than typical; retention risk.",
            remediation="Ease cliff so executives stay beyond year 1.",
        )
    return CompFinding(
        area="cliff", status="standard",
        detail=f"Cliff {c}mo — within peer standard.",
    )


def _check_acceleration(inputs: CompPlanInputs) -> Optional[CompFinding]:
    a = (inputs.acceleration_type or "").lower()
    if not a:
        return None
    if a == "single":
        return CompFinding(
            area="acceleration",
            status="aggressive",
            detail=("Single-trigger acceleration vests on sale alone — "
                    "erodes alignment with the acquirer."),
            remediation="Negotiate double-trigger (sale + involuntary term).",
        )
    if a == "double":
        return CompFinding(
            area="acceleration", status="standard",
            detail="Double-trigger acceleration — peer standard.",
        )
    if a == "none":
        return CompFinding(
            area="acceleration",
            status="light",
            detail="No acceleration — management may depart pre-close.",
            remediation="Consider double-trigger to retain through close.",
        )
    return None


def _check_rollover(inputs: CompPlanInputs) -> Optional[CompFinding]:
    v = _pct(inputs.ceo_equity_rollover_pct)
    if v is None:
        return None
    if v < 0.05:
        return CompFinding(
            area="ceo_rollover",
            status="light",
            detail=f"CEO rollover {v*100:.0f}% is below the 5-15% alignment range.",
            remediation="Require minimum 5% rollover — alignment signal.",
        )
    if v > 0.30:
        return CompFinding(
            area="ceo_rollover",
            status="aggressive",
            detail=f"CEO rollover {v*100:.0f}% is above the 5-15% range.",
            remediation="Consider step-down mechanic to limit single-executive risk.",
        )
    return CompFinding(
        area="ceo_rollover", status="standard",
        detail=f"CEO rollover {v*100:.0f}% — within alignment range.",
    )


def _check_ltip(inputs: CompPlanInputs) -> Optional[CompFinding]:
    if inputs.ltip_bonus_multiple_base is None:
        return None
    v = float(inputs.ltip_bonus_multiple_base)
    if v > 1.5:
        v /= 100.0
    if v < 0.15:
        return CompFinding(
            area="ltip",
            status="light",
            detail=f"LTIP {v*100:.0f}% of base — below 25-75% peer range.",
            remediation="Raise annual performance-bonus opportunity.",
        )
    if v > 1.0:
        return CompFinding(
            area="ltip",
            status="aggressive",
            detail=f"LTIP {v*100:.0f}% of base — above typical peer range.",
            remediation="Validate achievability of targets.",
        )
    return CompFinding(
        area="ltip", status="standard",
        detail=f"LTIP {v*100:.0f}% of base — within peer range.",
    )


def _check_perf_vesting(inputs: CompPlanInputs) -> Optional[CompFinding]:
    v = _pct(inputs.performance_vesting_pct)
    if v is None:
        return None
    if v < 0.20:
        return CompFinding(
            area="performance_vesting",
            status="light",
            detail=f"Performance-vesting {v*100:.0f}% — below 25-50% peer range.",
            remediation="Tie more of the grant to lever-specific metrics.",
        )
    if v > 0.70:
        return CompFinding(
            area="performance_vesting",
            status="aggressive",
            detail=f"Performance-vesting {v*100:.0f}% — retention risk.",
            remediation="Balance against time-vesting to retain in tough cycles.",
        )
    return CompFinding(
        area="performance_vesting", status="standard",
        detail=f"Performance-vesting {v*100:.0f}% — within peer range.",
    )


# ── Orchestrator ────────────────────────────────────────────────────

def review_comp_plan(inputs: CompPlanInputs) -> CompReport:
    findings: List[CompFinding] = []
    for fn in (_check_mip_pool, _check_ceo_share, _check_vesting,
               _check_cliff, _check_acceleration, _check_rollover,
               _check_ltip, _check_perf_vesting):
        f = fn(inputs)
        if f is not None:
            findings.append(f)
    n_aggressive = sum(1 for f in findings if f.status == "aggressive")
    n_light = sum(1 for f in findings if f.status == "light")
    if n_aggressive == 0 and n_light == 0:
        note = "Comp plan is standard — no material remediation required."
    elif n_aggressive + n_light <= 2:
        note = (f"{n_aggressive} aggressive + {n_light} light item(s) to "
                "align before close.")
    else:
        note = (f"Comp plan requires material re-design — {n_aggressive} "
                f"aggressive, {n_light} light.")
    return CompReport(findings=findings, partner_note=note)


def render_comp_plan_markdown(report: CompReport) -> str:
    lines = [
        "# Management compensation review",
        "",
        f"_{report.partner_note}_",
        "",
        "| Area | Status | Detail | Remediation |",
        "|---|---|---|---|",
    ]
    for f in report.findings:
        lines.append(
            f"| {f.area} | {f.status} | {f.detail} | {f.remediation} |"
        )
    return "\n".join(lines)
