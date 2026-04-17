"""Deal risk matrix — multi-dimensional risk scoring for healthcare PE deals.

Produces a structured risk assessment across six dimensions:
  1. Reimbursement risk   – payer mix concentration, Medicare/Medicaid exposure
  2. Leverage risk        – entry multiple vs sector, EV/EBITDA bands
  3. Execution risk       – deal complexity, carve-out, distressed
  4. Regulatory risk      – CON laws, surprise billing, DOJ/OIG exposure
  5. Market risk          – competitive dynamics, single-market concentration
  6. Operational risk     – margin quality, COVID recovery, staffing

Public API:
    RiskDimension                       dataclass
    RiskMatrix                          dataclass
    score_reimbursement_risk(deal)      -> RiskDimension
    score_leverage_risk(deal)           -> RiskDimension
    score_execution_risk(deal)          -> RiskDimension
    score_regulatory_risk(deal)         -> RiskDimension
    score_market_risk(deal)             -> RiskDimension
    score_operational_risk(deal)        -> RiskDimension
    build_risk_matrix(deal)             -> RiskMatrix
    risk_matrix_text(matrix)            -> str
    risk_matrix_summary(deals)          -> list[dict]
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class RiskDimension:
    """Score and findings for one risk dimension (0-100, higher = riskier)."""
    name: str
    score: float           # 0 (no risk) – 100 (extreme risk)
    level: str             # low / medium / high / critical
    drivers: List[str] = field(default_factory=list)
    mitigants: List[str] = field(default_factory=list)


@dataclass
class RiskMatrix:
    """Full risk assessment for a deal."""
    source_id: str
    deal_name: str
    dimensions: List[RiskDimension] = field(default_factory=list)
    composite_score: float = 0.0   # weighted average, 0-100
    composite_level: str = "low"
    overall_signal: str = "green"  # green / yellow / amber / red

    def as_dict(self) -> dict:
        return {
            "source_id": self.source_id,
            "deal_name": self.deal_name,
            "composite_score": self.composite_score,
            "composite_level": self.composite_level,
            "overall_signal": self.overall_signal,
            "dimensions": [
                {
                    "name": d.name,
                    "score": d.score,
                    "level": d.level,
                    "drivers": d.drivers,
                    "mitigants": d.mitigants,
                }
                for d in self.dimensions
            ],
        }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _safe_float(v: Any) -> Optional[float]:
    if v is None:
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _payer_share(deal: Dict, key: str) -> float:
    """Return share (0-1) for a given payer key from deal payer_mix."""
    import json
    pm = deal.get("payer_mix")
    if isinstance(pm, str):
        try:
            pm = json.loads(pm)
        except Exception:
            return 0.0
    if not isinstance(pm, dict):
        return 0.0
    return float(pm.get(key, 0) or 0)


def _level(score: float) -> str:
    if score >= 75:
        return "critical"
    if score >= 55:
        return "high"
    if score >= 35:
        return "medium"
    return "low"


# ---------------------------------------------------------------------------
# Dimension scorers
# ---------------------------------------------------------------------------

def score_reimbursement_risk(deal: Dict[str, Any]) -> RiskDimension:
    """Score reimbursement/payer risk based on payer mix composition."""
    score = 0.0
    drivers: List[str] = []
    mitigants: List[str] = []

    medicaid = _payer_share(deal, "medicaid")
    medicare = _payer_share(deal, "medicare")
    commercial = _payer_share(deal, "commercial")
    govt_total = medicaid + medicare

    if govt_total > 0.80:
        score += 35
        drivers.append(f"Government payer concentration {govt_total:.0%}")
    elif govt_total > 0.65:
        score += 20
        drivers.append(f"Elevated government exposure {govt_total:.0%}")

    if medicaid > 0.55:
        score += 25
        drivers.append(f"Medicaid >55% — state budget / rate reform risk")
    elif medicaid > 0.40:
        score += 12
        drivers.append(f"Medicaid {medicaid:.0%} — moderate state exposure")

    if medicare > 0.75:
        score += 20
        drivers.append(f"Medicare >75% — sequestration / MA penetration risk")
    elif medicare > 0.55:
        score += 10
        drivers.append(f"Medicare {medicare:.0%} — moderate CMS rate dependency")

    if commercial >= 0.40:
        mitigants.append(f"Commercial payer mix {commercial:.0%} supports rate negotiation")
    if commercial < 0.15 and deal.get("payer_mix"):
        score += 10
        drivers.append("Very low commercial mix limits rate leverage")

    return RiskDimension(
        name="reimbursement",
        score=min(100.0, round(score, 1)),
        level=_level(score),
        drivers=drivers,
        mitigants=mitigants,
    )


def score_leverage_risk(deal: Dict[str, Any]) -> RiskDimension:
    """Score leverage / valuation risk from entry multiple."""
    score = 0.0
    drivers: List[str] = []
    mitigants: List[str] = []

    ev_ebitda = _safe_float(deal.get("ev_ebitda"))
    deal_type = str(deal.get("deal_type") or "")
    ebitda = _safe_float(deal.get("ebitda_mm") or deal.get("ebitda_at_entry_mm"))
    ev = _safe_float(deal.get("ev_mm"))

    if ev_ebitda is not None:
        if ev_ebitda > 20:
            score += 40
            drivers.append(f"EV/EBITDA {ev_ebitda:.1f}x — extreme premium (>20x)")
        elif ev_ebitda > 15:
            score += 25
            drivers.append(f"EV/EBITDA {ev_ebitda:.1f}x — high multiple (>15x)")
        elif ev_ebitda > 12:
            score += 12
            drivers.append(f"EV/EBITDA {ev_ebitda:.1f}x — above sector median")
        else:
            mitigants.append(f"Entry multiple {ev_ebitda:.1f}x within historical range")

    if ebitda is not None and ebitda < 0:
        score += 30
        drivers.append(f"Negative EBITDA ${ebitda:.0f}M — pre-profitability investment")
    elif ebitda is not None and ev is not None and ev > 0:
        margin_implied = ebitda / ev if ev > 0 else None
        if margin_implied is not None and margin_implied < 0.05:
            score += 15
            drivers.append("Very thin implied EBITDA margin (<5% of EV)")

    if "distressed" in deal_type or "bankruptcy" in deal_type:
        score -= 10  # lower leverage risk (buying at discount)
        mitigants.append("Distressed entry — likely below-market multiple")

    if "take_private" in deal_type:
        score += 10
        drivers.append("Take-private premium adds to entry cost")

    return RiskDimension(
        name="leverage",
        score=max(0.0, min(100.0, round(score, 1))),
        level=_level(max(0.0, score)),
        drivers=drivers,
        mitigants=mitigants,
    )


def score_execution_risk(deal: Dict[str, Any]) -> RiskDimension:
    """Score execution risk from deal complexity, integration difficulty."""
    score = 0.0
    drivers: List[str] = []
    mitigants: List[str] = []

    deal_type = str(deal.get("deal_type") or "").lower()
    notes = str(deal.get("notes") or "").lower()
    ev = _safe_float(deal.get("ev_mm"))

    if "carve_out" in deal_type or "carve-out" in deal_type:
        score += 25
        drivers.append("Carve-out — systems, contracts, TSA execution risk")
    if "merger" in deal_type:
        score += 20
        drivers.append("Merger — integration complexity, culture risk")
    if "distressed" in deal_type:
        score += 30
        drivers.append("Distressed — operational stabilization required")
    if "ipo" in deal_type:
        score += 15
        drivers.append("IPO — market timing, lock-up and valuation execution risk")
    if "roll_up" in deal_type or "roll-up" in notes:
        score += 20
        drivers.append("Roll-up / platform — multi-site integration complexity")
    if "add_on" in deal_type:
        score += 8
        drivers.append("Add-on — integration into existing platform")

    if any(k in notes for k in ["bankruptcy", "doj", "settlement", "fraud"]):
        score += 20
        drivers.append("Legal/regulatory history in notes")
    if "spac" in notes:
        score += 15
        drivers.append("SPAC structure — sponsor alignment and dilution risk")

    if ev is not None and ev > 10000:
        score += 10
        drivers.append(f"Large-cap deal (>${ev/1000:.0f}B EV) — complexity premium")

    if "lbo" in deal_type and not any(k in drivers for k in ["Distressed", "Carve"]):
        mitigants.append("Standard LBO structure — proven execution playbook")

    return RiskDimension(
        name="execution",
        score=min(100.0, round(score, 1)),
        level=_level(score),
        drivers=drivers,
        mitigants=mitigants,
    )


def score_regulatory_risk(deal: Dict[str, Any]) -> RiskDimension:
    """Score regulatory risk based on sector-specific exposure."""
    score = 0.0
    drivers: List[str] = []
    mitigants: List[str] = []

    notes = str(deal.get("notes") or "").lower()
    name = str(deal.get("deal_name") or "").lower()

    regulatory_keywords = {
        "doj": ("DOJ investigation/settlement risk", 30),
        "oig": ("OIG compliance exposure", 25),
        "fraud": ("Fraud/abuse history in notes", 30),
        "settlement": ("Legal settlement in notes", 20),
        "antitrust": ("Antitrust review risk", 25),
        "con law": ("CON law — certificate of need restrictions", 15),
        "nsb": ("NSA surprise billing risk", 20),
        "nsa": ("NSA surprise billing risk", 20),
        "rebate": ("PBM rebate/transparency reform risk", 20),
        "sequestration": ("Medicare sequestration exposure", 10),
        "medicaid expansion": ("Medicaid expansion policy dependency", 15),
    }

    for keyword, (msg, pts) in regulatory_keywords.items():
        if keyword in notes:
            score += pts
            drivers.append(msg)

    medicaid = _payer_share(deal, "medicaid")
    if medicaid > 0.50:
        score += 10
        drivers.append(f"High Medicaid {medicaid:.0%} — state legislative risk")

    if not drivers:
        mitigants.append("No acute regulatory red flags identified in notes")

    return RiskDimension(
        name="regulatory",
        score=min(100.0, round(score, 1)),
        level=_level(score),
        drivers=drivers,
        mitigants=mitigants,
    )


def score_market_risk(deal: Dict[str, Any]) -> RiskDimension:
    """Score market and competitive risk."""
    score = 0.0
    drivers: List[str] = []
    mitigants: List[str] = []

    notes = str(deal.get("notes") or "").lower()
    region = str(deal.get("region") or "").lower()

    if "single" in notes and ("state" in notes or "market" in notes):
        score += 25
        drivers.append("Single-state / single-market concentration")
    if "rural" in notes or "rural" in region:
        score += 15
        drivers.append("Rural market — limited patient volume, recruitment risk")
    if "urban" in notes:
        mitigants.append("Urban market — higher density, competitive but large TAM")
    if "national" in region.lower() or region.lower() == "national":
        mitigants.append("National platform — geographic diversification")

    if any(k in notes for k in ["competition", "competitive", "market share"]):
        score += 10
        drivers.append("Competitive dynamics noted")

    deal_type = str(deal.get("deal_type") or "").lower()
    if "joint_venture" in deal_type:
        score += 10
        drivers.append("JV governance complexity — partner alignment risk")

    if not drivers:
        mitigants.append("No acute market concentration issues identified")

    return RiskDimension(
        name="market",
        score=min(100.0, round(score, 1)),
        level=_level(score),
        drivers=drivers,
        mitigants=mitigants,
    )


def score_operational_risk(deal: Dict[str, Any]) -> RiskDimension:
    """Score operational risk from margin, staffing, and COVID recovery."""
    score = 0.0
    drivers: List[str] = []
    mitigants: List[str] = []

    ebitda = _safe_float(deal.get("ebitda_mm") or deal.get("ebitda_at_entry_mm"))
    ev = _safe_float(deal.get("ev_mm"))
    notes = str(deal.get("notes") or "").lower()
    moic = _safe_float(deal.get("realized_moic"))

    if ebitda is not None and ebitda < 0:
        score += 30
        drivers.append(f"Negative EBITDA ${ebitda:.0f}M — turnaround required")
    elif ebitda is not None and ev is not None and ev > 0:
        implied_margin_pct = ebitda / ev
        if implied_margin_pct < 0.04:
            score += 15
            drivers.append("Thin margin (<4% EV) — limited cushion for cost inflation")

    staffing_keywords = ["staffing", "travel nurse", "labor", "workforce"]
    if any(k in notes for k in staffing_keywords):
        score += 15
        drivers.append("Staffing / labor cost pressure noted")

    covid_keywords = ["covid", "pandemic", "occupancy recovery"]
    if any(k in notes for k in covid_keywords):
        score += 10
        drivers.append("COVID disruption / occupancy recovery dependency")

    if moic is not None and moic < 0.5:
        score += 20
        drivers.append(f"Historical realized MOIC {moic:.2f}x suggests operational issues")

    if not drivers:
        mitigants.append("No acute operational risk indicators identified")

    return RiskDimension(
        name="operational",
        score=min(100.0, round(score, 1)),
        level=_level(score),
        drivers=drivers,
        mitigants=mitigants,
    )


# ---------------------------------------------------------------------------
# Composite matrix builder
# ---------------------------------------------------------------------------

# Dimension weights (must sum to 1.0)
_WEIGHTS = {
    "reimbursement": 0.25,
    "leverage": 0.20,
    "execution": 0.20,
    "regulatory": 0.15,
    "market": 0.10,
    "operational": 0.10,
}


def build_risk_matrix(deal: Dict[str, Any]) -> RiskMatrix:
    """Build a full risk matrix for a single deal."""
    dimensions = [
        score_reimbursement_risk(deal),
        score_leverage_risk(deal),
        score_execution_risk(deal),
        score_regulatory_risk(deal),
        score_market_risk(deal),
        score_operational_risk(deal),
    ]

    composite = sum(
        d.score * _WEIGHTS.get(d.name, 0.10) for d in dimensions
    )
    composite = round(composite, 1)

    level = _level(composite)
    signal_map = {"low": "green", "medium": "yellow", "high": "amber", "critical": "red"}
    signal = signal_map.get(level, "green")

    return RiskMatrix(
        source_id=str(deal.get("source_id") or ""),
        deal_name=str(deal.get("deal_name") or ""),
        dimensions=dimensions,
        composite_score=composite,
        composite_level=level,
        overall_signal=signal,
    )


# ---------------------------------------------------------------------------
# Output helpers
# ---------------------------------------------------------------------------

def risk_matrix_text(matrix: RiskMatrix) -> str:
    """Formatted text risk matrix report."""
    signal_icons = {"green": "[GREEN]", "yellow": "[YELLOW]", "amber": "[AMBER]", "red": "[RED]"}
    icon = signal_icons.get(matrix.overall_signal, "[?]")
    lines = [
        f"Risk Matrix: {matrix.deal_name}",
        "=" * 65,
        f"  Composite Score : {matrix.composite_score:.1f}/100  "
        f"Level: {matrix.composite_level.upper()}  Signal: {icon}",
        "-" * 65,
    ]
    for d in matrix.dimensions:
        bar = "█" * int(d.score / 10) + "░" * (10 - int(d.score / 10))
        lines.append(f"  {d.name.capitalize():<16} {bar}  {d.score:>5.1f}  [{d.level.upper()}]")
        for drv in d.drivers[:2]:
            lines.append(f"    ↑ {drv}")
        for mit in d.mitigants[:1]:
            lines.append(f"    ✓ {mit}")
    lines.append("=" * 65)
    return "\n".join(lines) + "\n"


def risk_matrix_summary(deals: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Build risk matrices for all deals and return sorted summary."""
    rows = []
    for d in deals:
        m = build_risk_matrix(d)
        rows.append({
            "source_id": m.source_id,
            "deal_name": m.deal_name,
            "composite_score": m.composite_score,
            "composite_level": m.composite_level,
            "overall_signal": m.overall_signal,
            "reimbursement_score": next((x.score for x in m.dimensions if x.name == "reimbursement"), 0),
            "leverage_score": next((x.score for x in m.dimensions if x.name == "leverage"), 0),
            "execution_score": next((x.score for x in m.dimensions if x.name == "execution"), 0),
        })
    rows.sort(key=lambda r: -r["composite_score"])
    return rows
