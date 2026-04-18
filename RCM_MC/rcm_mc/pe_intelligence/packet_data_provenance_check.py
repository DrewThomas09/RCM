"""Packet data provenance — how much do we actually know?

Partner statement: "When the seller says 'EBITDA is $75M,'
what I hear is 'management's number is $75M.' When QofE
says it, I hear '$75M, roughly.' When my team rebuilt it
from GL, I hear '$75M.' Same number, three different
confidences."

Partners implicitly weight packet data by source. The
packet builder doesn't. This module makes that weighting
explicit: tag each packet field with its provenance,
compute a confidence-weighted score, and surface the
fields that need independent verification before IC.

### 7 provenance tiers

Weights are partner-judgment. Higher = more trustworthy.

- `seller_mgmt_unverified` — 0.40 — management's words.
- `seller_banker_book` — 0.50 — CIM / teaser.
- `qofe_preliminary` — 0.65 — incomplete QofE.
- `qofe_complete` — 0.85 — final QofE report.
- `third_party_diligence` — 0.90 — legal / clinical /
  IT / insurance.
- `public_data` — 0.95 — CMS, HCRIS, audited 10-K.
- `partner_team_modeled` — 1.00 — our own rebuild.

### Output

- Weighted confidence score (0-100).
- List of fields below confidence threshold.
- Partner note: which fields must be independently
  verified before IC.

### Why this matters

Partners have been burned by closing on packets where
the headline EBITDA came from management-only sources.
After QofE, the number dropped 10%. This module is the
pre-IC discipline: name what we've verified vs. what
we've accepted on faith.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


PROVENANCE_WEIGHTS: Dict[str, float] = {
    "seller_mgmt_unverified": 0.40,
    "seller_banker_book": 0.50,
    "qofe_preliminary": 0.65,
    "qofe_complete": 0.85,
    "third_party_diligence": 0.90,
    "public_data": 0.95,
    "partner_team_modeled": 1.00,
}

# Fields where partners demand high-provenance data.
# If any of these are below qofe_complete tier, partner
# flags for pre-IC verification.
HIGH_STAKES_FIELDS: List[str] = [
    "reported_ebitda",
    "recurring_vs_onetime_ebitda",
    "working_capital_peg",
    "debt_balance",
    "payer_mix",
    "top_customer_concentration",
    "physician_productivity_rvu",
    "cms_star_rating",
    "open_audit_exposure",
    "pending_litigation_exposure",
]


@dataclass
class PacketField:
    name: str
    provenance: str                        # key into weights table
    weight_in_thesis: float = 1.0          # importance multiplier


@dataclass
class PacketProvenanceInputs:
    fields: List[PacketField] = field(default_factory=list)
    confidence_threshold: float = 0.70


@dataclass
class FieldAssessment:
    name: str
    provenance: str
    confidence_weight: float
    thesis_weight: float
    is_below_threshold: bool
    is_high_stakes: bool
    partner_commentary: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "provenance": self.provenance,
            "confidence_weight": self.confidence_weight,
            "thesis_weight": self.thesis_weight,
            "is_below_threshold": self.is_below_threshold,
            "is_high_stakes": self.is_high_stakes,
            "partner_commentary": self.partner_commentary,
        }


@dataclass
class PacketProvenanceReport:
    overall_confidence_score: float        # 0-100
    fields_below_threshold: List[str] = field(default_factory=list)
    high_stakes_unverified: List[str] = field(default_factory=list)
    field_assessments: List[FieldAssessment] = field(default_factory=list)
    partner_note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "overall_confidence_score":
                self.overall_confidence_score,
            "fields_below_threshold":
                list(self.fields_below_threshold),
            "high_stakes_unverified":
                list(self.high_stakes_unverified),
            "field_assessments":
                [a.to_dict() for a in self.field_assessments],
            "partner_note": self.partner_note,
        }


def _commentary(f: PacketField, weight: float,
                is_high_stakes: bool, below_threshold: bool) -> str:
    if is_high_stakes and below_threshold:
        return (
            f"HIGH-STAKES field on {f.provenance} "
            f"(weight {weight:.2f}). Partner: verify via "
            "QofE or 3rd-party before IC."
        )
    if below_threshold:
        return (
            f"Below confidence threshold ({f.provenance}, "
            f"weight {weight:.2f}). Flag for diligence if "
            "load-bearing."
        )
    if is_high_stakes:
        return (
            f"High-stakes field on {f.provenance} "
            f"(weight {weight:.2f}). Meets partner bar."
        )
    return (
        f"Field on {f.provenance} (weight {weight:.2f})."
    )


def check_packet_provenance(
    inputs: PacketProvenanceInputs,
) -> PacketProvenanceReport:
    assessments: List[FieldAssessment] = []
    weighted_sum = 0.0
    weight_total = 0.0
    below: List[str] = []
    high_stakes_unv: List[str] = []

    for f in inputs.fields:
        w = PROVENANCE_WEIGHTS.get(f.provenance, 0.40)
        below_t = w < inputs.confidence_threshold
        hs = f.name in HIGH_STAKES_FIELDS
        assessments.append(FieldAssessment(
            name=f.name,
            provenance=f.provenance,
            confidence_weight=w,
            thesis_weight=f.weight_in_thesis,
            is_below_threshold=below_t,
            is_high_stakes=hs,
            partner_commentary=_commentary(f, w, hs, below_t),
        ))
        weighted_sum += w * f.weight_in_thesis
        weight_total += f.weight_in_thesis
        if below_t:
            below.append(f.name)
        if hs and below_t:
            high_stakes_unv.append(f.name)

    score_0_100 = (
        (weighted_sum / weight_total) * 100.0
        if weight_total > 0 else 0.0
    )

    # Partner note.
    if not assessments:
        note = (
            "No packet fields tagged for provenance. "
            "Partner: tag at minimum the EBITDA, working "
            "capital, and payer-mix fields before IC."
        )
    elif high_stakes_unv:
        note = (
            f"{len(high_stakes_unv)} high-stakes field(s) "
            "still on seller-supplied provenance: "
            f"{', '.join(high_stakes_unv[:3])}. Partner: "
            "these must be QofE-verified or third-party-"
            "verified before IC."
        )
    elif below:
        note = (
            f"{len(below)} field(s) below confidence "
            "threshold. Partner: ensure no thesis-"
            "critical lever depends on any of them."
        )
    elif score_0_100 >= 85:
        note = (
            f"Packet confidence {score_0_100:.0f}/100. "
            "Partner-level discipline in sourcing; "
            "proceed to IC."
        )
    else:
        note = (
            f"Packet confidence {score_0_100:.0f}/100. "
            "Acceptable but flag the lowest-provenance "
            "fields in the IC memo appendix."
        )

    return PacketProvenanceReport(
        overall_confidence_score=round(score_0_100, 1),
        fields_below_threshold=below,
        high_stakes_unverified=high_stakes_unv,
        field_assessments=assessments,
        partner_note=note,
    )


def list_provenance_tiers() -> List[str]:
    return list(PROVENANCE_WEIGHTS.keys())


def render_packet_provenance_markdown(
    r: PacketProvenanceReport,
) -> str:
    lines = [
        "# Packet data provenance",
        "",
        f"_{r.partner_note}_",
        "",
        f"- Overall confidence: "
        f"{r.overall_confidence_score:.1f}/100",
        f"- Fields below threshold: "
        f"{len(r.fields_below_threshold)}",
        f"- High-stakes unverified: "
        f"{len(r.high_stakes_unverified)}",
        "",
        "| Field | Provenance | Weight | High-stakes | "
        "Below threshold | Partner comment |",
        "|---|---|---|---|---|---|",
    ]
    for a in r.field_assessments:
        lines.append(
            f"| {a.name} | {a.provenance} | "
            f"{a.confidence_weight:.2f} | "
            f"{'Y' if a.is_high_stakes else 'N'} | "
            f"{'Y' if a.is_below_threshold else 'N'} | "
            f"{a.partner_commentary} |"
        )
    return "\n".join(lines)
