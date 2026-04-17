"""Labor-cost analytics — staffing mix + productivity + wage pressure.

Labor is 50-60% of OpEx for most healthcare operators. This module
evaluates:

- **Contract / agency share** — higher = margin fragility (rate-
  sensitive).
- **Overtime share** — overtime dependency signals staffing shortage.
- **Nurse-to-patient ratios** — regulatory (CA) + quality-sensitive.
- **Wage growth vs CPI** — healthy labor markets grow at CPI+1%;
  above that compresses margin.
- **Productivity (volume per FTE)** — 10-15% improvement is a
  common lever.

Outputs a 0..1 labor-risk score + partner-voice commentary + $-
impact estimate for shocks.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class LaborInputs:
    total_labor_spend: Optional[float] = None       # $ annual
    contract_labor_share: Optional[float] = None    # fraction 0..1
    overtime_share: Optional[float] = None          # fraction of hours
    nurse_patient_ratio: Optional[float] = None     # patients per nurse (higher = worse)
    wage_growth_yoy: Optional[float] = None         # fraction
    local_cpi: Optional[float] = None               # fraction (default 3%)
    productivity_volume_per_fte: Optional[float] = None
    peer_productivity: Optional[float] = None


@dataclass
class LaborFinding:
    metric: str
    observed: Any
    score: float                      # 0..1 risk (higher = more risk)
    partner_note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "metric": self.metric,
            "observed": self.observed,
            "score": self.score,
            "partner_note": self.partner_note,
        }


@dataclass
class LaborProfile:
    findings: List[LaborFinding] = field(default_factory=list)
    composite_risk: float = 0.0                     # 0..1
    shock_impact_10pct_wage: float = 0.0             # $ hit if wages +10%
    lever_savings_5pct_productivity: float = 0.0    # $ save if +5% productivity
    verdict: str = ""
    partner_note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "findings": [f.to_dict() for f in self.findings],
            "composite_risk": self.composite_risk,
            "shock_impact_10pct_wage": self.shock_impact_10pct_wage,
            "lever_savings_5pct_productivity": self.lever_savings_5pct_productivity,
            "verdict": self.verdict,
            "partner_note": self.partner_note,
        }


# ── Scorers ────────────────────────────────────────────────────────

def _score_contract_labor(share: Optional[float]) -> Optional[LaborFinding]:
    if share is None:
        return None
    v = float(share)
    if v > 1.5:
        v /= 100.0
    if v < 0.08:
        score = 0.10
        note = "Low contract-labor exposure."
    elif v < 0.15:
        score = 0.30
        note = "Moderate contract-labor exposure."
    elif v < 0.25:
        score = 0.60
        note = "Elevated contract-labor — rate volatility matters."
    else:
        score = 0.90
        note = "High contract-labor dependency — significant rate-shock risk."
    return LaborFinding(
        metric="contract_labor_share",
        observed=v, score=score, partner_note=note,
    )


def _score_overtime(share: Optional[float]) -> Optional[LaborFinding]:
    if share is None:
        return None
    v = float(share)
    if v > 1.5:
        v /= 100.0
    if v < 0.05:
        return LaborFinding(metric="overtime_share", observed=v, score=0.10,
                            partner_note="Low overtime — staffing adequate.")
    if v < 0.10:
        return LaborFinding(metric="overtime_share", observed=v, score=0.30,
                            partner_note="Modest overtime — watch for drift.")
    if v < 0.18:
        return LaborFinding(metric="overtime_share", observed=v, score=0.60,
                            partner_note="Elevated overtime — indicates staffing shortage.")
    return LaborFinding(metric="overtime_share", observed=v, score=0.90,
                        partner_note="Excessive overtime — structural staffing problem.")


def _score_ratio(ratio: Optional[float]) -> Optional[LaborFinding]:
    if ratio is None:
        return None
    v = float(ratio)
    if v <= 4:
        return LaborFinding(metric="nurse_patient_ratio", observed=v, score=0.10,
                            partner_note="Strong nurse coverage.")
    if v <= 6:
        return LaborFinding(metric="nurse_patient_ratio", observed=v, score=0.40,
                            partner_note="Typical nurse coverage.")
    if v <= 8:
        return LaborFinding(metric="nurse_patient_ratio", observed=v, score=0.70,
                            partner_note="Thin nurse coverage — quality and retention risk.")
    return LaborFinding(metric="nurse_patient_ratio", observed=v, score=0.95,
                        partner_note="Very thin nurse coverage — regulatory / quality exposure.")


def _score_wage_growth(wage: Optional[float],
                       cpi: Optional[float]) -> Optional[LaborFinding]:
    if wage is None:
        return None
    w = float(wage)
    c = float(cpi) if cpi is not None else 0.03
    delta = w - c
    if delta <= 0.01:
        return LaborFinding(
            metric="wage_growth_vs_cpi",
            observed={"wage": w, "cpi": c}, score=0.20,
            partner_note="Wage growth tracking CPI — no material drift.")
    if delta <= 0.03:
        return LaborFinding(
            metric="wage_growth_vs_cpi",
            observed={"wage": w, "cpi": c}, score=0.50,
            partner_note=f"Wage growth +{delta*100:.1f} pp over CPI.")
    return LaborFinding(
        metric="wage_growth_vs_cpi",
        observed={"wage": w, "cpi": c}, score=0.80,
        partner_note=f"Wages outpacing CPI by {delta*100:.1f} pp — margin compression risk.")


def _score_productivity(vol: Optional[float],
                        peer: Optional[float]) -> Optional[LaborFinding]:
    if vol is None or peer is None or peer <= 0:
        return None
    ratio = float(vol) / float(peer)
    if ratio >= 1.05:
        return LaborFinding(
            metric="productivity_vs_peer",
            observed=ratio, score=0.15,
            partner_note="Above-peer productivity — lever largely captured.")
    if ratio >= 0.95:
        return LaborFinding(
            metric="productivity_vs_peer",
            observed=ratio, score=0.35,
            partner_note="At peer productivity — modest lever available.")
    if ratio >= 0.85:
        return LaborFinding(
            metric="productivity_vs_peer",
            observed=ratio, score=0.65,
            partner_note="Below-peer productivity — 5-10% lever credible.")
    return LaborFinding(
        metric="productivity_vs_peer",
        observed=ratio, score=0.85,
        partner_note="Materially below peer productivity — 10%+ lever but "
                    "usually means management overhaul needed.")


# ── Profile orchestrator ──────────────────────────────────────────

def analyze_labor_profile(inputs: LaborInputs) -> LaborProfile:
    findings = [
        _score_contract_labor(inputs.contract_labor_share),
        _score_overtime(inputs.overtime_share),
        _score_ratio(inputs.nurse_patient_ratio),
        _score_wage_growth(inputs.wage_growth_yoy, inputs.local_cpi),
        _score_productivity(inputs.productivity_volume_per_fte,
                            inputs.peer_productivity),
    ]
    findings = [f for f in findings if f is not None]
    if not findings:
        return LaborProfile(
            verdict="unknown",
            partner_note="No labor metrics provided.",
        )

    composite = sum(f.score for f in findings) / len(findings)

    # $ shock impact: 10% wage shock on labor spend.
    shock = 0.0
    if inputs.total_labor_spend is not None:
        shock = -float(inputs.total_labor_spend) * 0.10
    lever_savings = 0.0
    if inputs.total_labor_spend is not None:
        # 5% productivity → ~5% labor savings via headcount normalization.
        lever_savings = float(inputs.total_labor_spend) * 0.05

    if composite >= 0.70:
        verdict = "drag"
        note = (f"Labor profile is a drag — composite risk {composite:.2f}. "
                "Address staffing stability before the lever plan matters.")
    elif composite >= 0.45:
        verdict = "moderate"
        note = ("Labor profile is manageable but watch the drift. Contract/"
                "overtime dependency is the variable to track.")
    else:
        verdict = "strong"
        note = "Labor profile is in shape — lever room exists but not urgent."

    return LaborProfile(
        findings=findings,
        composite_risk=round(composite, 4),
        shock_impact_10pct_wage=round(shock, 2),
        lever_savings_5pct_productivity=round(lever_savings, 2),
        verdict=verdict,
        partner_note=note,
    )


def render_labor_profile_markdown(profile: LaborProfile) -> str:
    lines = [
        "# Labor profile",
        "",
        f"**Verdict:** {profile.verdict}  ",
        f"**Composite risk:** {profile.composite_risk:.2f}  ",
        f"**10% wage shock impact:** ${profile.shock_impact_10pct_wage:,.0f}  ",
        f"**5% productivity lever savings:** ${profile.lever_savings_5pct_productivity:,.0f}",
        "",
        f"_{profile.partner_note}_",
        "",
        "| Metric | Observed | Risk | Note |",
        "|---|---:|---:|---|",
    ]
    for f in profile.findings:
        obs = f.observed
        if isinstance(obs, float):
            obs_str = f"{obs*100:.1f}%" if obs < 1.5 else f"{obs:.2f}"
        else:
            obs_str = str(obs)
        lines.append(
            f"| {f.metric} | {obs_str} | {f.score:.2f} | {f.partner_note} |"
        )
    return "\n".join(lines)
