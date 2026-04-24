"""Regulatory Risk Packet — composite of five submodule outputs.

``RegulatoryRiskPacket`` is the dataclass that attaches to a
``DealAnalysisPacket`` at step 5.5 (after comparables, before
reimbursement). It carries the outputs from each of the five
regulatory submodules and computes a single composite
GREEN / YELLOW / RED score.

Composite scoring (worst-of):

    RED        — any submodule returns RED (voided-contract CPOM
                 ban, >5% NSA IDR revenue loss, TEAM losing tier,
                 antitrust 30-day notice trigger, site-neutral
                 legislative-scenario >20% erosion)
    YELLOW     — any submodule returns YELLOW but none RED
    GREEN      — all submodules GREEN or UNKNOWN
    UNKNOWN    — not enough data to score at least one submodule
                 and no submodule returned anything worse

RED means "do not close without regulatory remediation." YELLOW
means "add to IC open-question list." GREEN means "no material
finding on this vector."
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml


CONTENT_DIR = Path(__file__).parent / "content"


class RegulatoryBand(str, Enum):
    """Traffic-light banding reused across submodules."""
    GREEN   = "GREEN"
    YELLOW  = "YELLOW"
    RED     = "RED"
    UNKNOWN = "UNKNOWN"


def worst_band(bands: List[RegulatoryBand]) -> RegulatoryBand:
    """Return the worst-of bands. UNKNOWN defers to any real band;
    only when ALL inputs are UNKNOWN do we return UNKNOWN."""
    if not bands:
        return RegulatoryBand.UNKNOWN
    order = [RegulatoryBand.RED, RegulatoryBand.YELLOW,
             RegulatoryBand.GREEN]
    for tier in order:
        if any(b == tier for b in bands):
            return tier
    return RegulatoryBand.UNKNOWN


def load_yaml(name: str) -> Dict[str, Any]:
    """Load one content YAML by basename (without .yaml)."""
    path = CONTENT_DIR / f"{name}.yaml"
    if not path.exists():
        raise FileNotFoundError(
            f"regulatory content missing: {path}"
        )
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


@dataclass
class CPOMExposure:
    """One state's CPOM posture vs. the target's structure."""
    state_code: str
    state_name: str
    statute: str
    effective_date: Optional[str] = None
    compliance_deadline: Optional[str] = None
    band: RegulatoryBand = RegulatoryBand.GREEN
    voided_contracts: List[str] = field(default_factory=list)
    remediation_cost_usd: float = 0.0
    days_to_deadline: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "state_code": self.state_code,
            "state_name": self.state_name,
            "statute": self.statute,
            "effective_date": self.effective_date,
            "compliance_deadline": self.compliance_deadline,
            "band": self.band.value,
            "voided_contracts": list(self.voided_contracts),
            "remediation_cost_usd": self.remediation_cost_usd,
            "days_to_deadline": self.days_to_deadline,
        }


@dataclass
class CPOMReport:
    target_structure: str
    footprint_states: List[str]
    per_state: List[CPOMExposure] = field(default_factory=list)
    overall_band: RegulatoryBand = RegulatoryBand.GREEN
    total_remediation_usd: float = 0.0
    maintenance_required: bool = False
    content_last_reviewed: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "target_structure": self.target_structure,
            "footprint_states": list(self.footprint_states),
            "per_state": [s.to_dict() for s in self.per_state],
            "overall_band": self.overall_band.value,
            "total_remediation_usd": self.total_remediation_usd,
            "maintenance_required": self.maintenance_required,
            "content_last_reviewed": self.content_last_reviewed,
        }


@dataclass
class NSAExposure:
    specialty: str
    oon_revenue_share: float           # fraction
    dollars_at_risk_usd: float
    qpa_shortfall_pct: float
    idr_challenge_probability: float   # 0..1
    band: RegulatoryBand = RegulatoryBand.GREEN
    case_study_match: Optional[str] = None
    month_by_month_cash_impact_usd: List[float] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "specialty": self.specialty,
            "oon_revenue_share": self.oon_revenue_share,
            "dollars_at_risk_usd": self.dollars_at_risk_usd,
            "qpa_shortfall_pct": self.qpa_shortfall_pct,
            "idr_challenge_probability": self.idr_challenge_probability,
            "band": self.band.value,
            "case_study_match": self.case_study_match,
            "month_by_month_cash_impact_usd": list(
                self.month_by_month_cash_impact_usd
            ),
        }


@dataclass
class SiteNeutralExposure:
    scenario: str
    annual_revenue_erosion_usd: float
    annual_revenue_erosion_pct: float
    phase_in_years: int
    affected_cpt_families: List[str]
    band: RegulatoryBand = RegulatoryBand.GREEN
    recoupment_340b_usd: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "scenario": self.scenario,
            "annual_revenue_erosion_usd": self.annual_revenue_erosion_usd,
            "annual_revenue_erosion_pct": self.annual_revenue_erosion_pct,
            "phase_in_years": self.phase_in_years,
            "affected_cpt_families": list(self.affected_cpt_families),
            "band": self.band.value,
            "recoupment_340b_usd": self.recoupment_340b_usd,
        }


@dataclass
class TEAMExposure:
    in_mandatory_cbsa: bool
    cbsa_code: Optional[str]
    cbsa_name: Optional[str]
    track: str
    annual_pnl_impact_usd: float
    expected_loss_per_case_usd: float
    mandatory_episodes: List[str]
    band: RegulatoryBand = RegulatoryBand.GREEN

    def to_dict(self) -> Dict[str, Any]:
        return {
            "in_mandatory_cbsa": self.in_mandatory_cbsa,
            "cbsa_code": self.cbsa_code,
            "cbsa_name": self.cbsa_name,
            "track": self.track,
            "annual_pnl_impact_usd": self.annual_pnl_impact_usd,
            "expected_loss_per_case_usd": self.expected_loss_per_case_usd,
            "mandatory_episodes": list(self.mandatory_episodes),
            "band": self.band.value,
        }


@dataclass
class AntitrustExposure:
    target_specialty: str
    target_msas: List[str]
    acquisition_count: int
    estimated_hhi: Optional[float]
    thirty_day_ftc_notice_triggered: bool
    band: RegulatoryBand = RegulatoryBand.GREEN
    matching_precedents: List[str] = field(default_factory=list)
    remediation_options: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "target_specialty": self.target_specialty,
            "target_msas": list(self.target_msas),
            "acquisition_count": self.acquisition_count,
            "estimated_hhi": self.estimated_hhi,
            "thirty_day_ftc_notice_triggered":
                self.thirty_day_ftc_notice_triggered,
            "band": self.band.value,
            "matching_precedents": list(self.matching_precedents),
            "remediation_options": list(self.remediation_options),
        }


@dataclass
class RegulatoryRiskPacket:
    """The composite that attaches to DealAnalysisPacket."""
    computed_at: str = ""
    target_name: str = ""

    cpom: Optional[CPOMReport] = None
    nsa: Optional[NSAExposure] = None
    site_neutral: Optional[SiteNeutralExposure] = None
    team: Optional[TEAMExposure] = None
    antitrust: Optional[AntitrustExposure] = None

    composite_band: RegulatoryBand = RegulatoryBand.UNKNOWN
    total_dollars_at_risk_usd: float = 0.0
    critical_findings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "computed_at": self.computed_at,
            "target_name": self.target_name,
            "cpom": self.cpom.to_dict() if self.cpom else None,
            "nsa": self.nsa.to_dict() if self.nsa else None,
            "site_neutral": (
                self.site_neutral.to_dict() if self.site_neutral else None
            ),
            "team": self.team.to_dict() if self.team else None,
            "antitrust": (
                self.antitrust.to_dict() if self.antitrust else None
            ),
            "composite_band": self.composite_band.value,
            "total_dollars_at_risk_usd": self.total_dollars_at_risk_usd,
            "critical_findings": list(self.critical_findings),
        }


def compose_packet(
    *,
    target_name: str,
    cpom: Optional[CPOMReport] = None,
    nsa: Optional[NSAExposure] = None,
    site_neutral: Optional[SiteNeutralExposure] = None,
    team: Optional[TEAMExposure] = None,
    antitrust: Optional[AntitrustExposure] = None,
) -> RegulatoryRiskPacket:
    """Build the composite packet. Composite band = worst-of."""
    bands: List[RegulatoryBand] = []
    dollars = 0.0
    critical: List[str] = []
    if cpom is not None:
        bands.append(cpom.overall_band)
        dollars += cpom.total_remediation_usd
        if cpom.overall_band == RegulatoryBand.RED:
            critical.append(
                f"CPOM: voided-contract risk across "
                f"{len([s for s in cpom.per_state if s.band == RegulatoryBand.RED])} "
                f"states — remediation ~${cpom.total_remediation_usd:,.0f}"
            )
    if nsa is not None:
        bands.append(nsa.band)
        dollars += nsa.dollars_at_risk_usd
        if nsa.band == RegulatoryBand.RED:
            critical.append(
                f"NSA IDR: ${nsa.dollars_at_risk_usd:,.0f} at risk"
                + (f" — matches {nsa.case_study_match}" if nsa.case_study_match else "")
            )
    if site_neutral is not None:
        bands.append(site_neutral.band)
        dollars += site_neutral.annual_revenue_erosion_usd
        if site_neutral.band == RegulatoryBand.RED:
            critical.append(
                f"Site-neutral: {site_neutral.scenario} scenario erodes "
                f"${site_neutral.annual_revenue_erosion_usd:,.0f}/yr"
            )
    if team is not None:
        bands.append(team.band)
        if team.annual_pnl_impact_usd < 0:
            dollars += -team.annual_pnl_impact_usd
        if team.band == RegulatoryBand.RED:
            critical.append(
                f"TEAM: annual P&L impact ${team.annual_pnl_impact_usd:,.0f} "
                f"under {team.track}"
            )
    if antitrust is not None:
        bands.append(antitrust.band)
        if antitrust.band == RegulatoryBand.RED:
            critical.append(
                f"Antitrust: 30-day FTC notice triggered for "
                f"{antitrust.target_specialty} in "
                f"{', '.join(antitrust.target_msas)}"
            )

    return RegulatoryRiskPacket(
        computed_at=datetime.now(timezone.utc).isoformat(),
        target_name=target_name,
        cpom=cpom, nsa=nsa, site_neutral=site_neutral,
        team=team, antitrust=antitrust,
        composite_band=worst_band(bands),
        total_dollars_at_risk_usd=dollars,
        critical_findings=critical,
    )
