"""White-space detection — where is the unserved opportunity.

Partners look at a target and ask: "what adjacencies can this asset
grow into?" White-space analysis surfaces three dimensions:

- **Geographic** — regions / states where the target is absent but
  peers operate, AND where sector demand indicators suggest demand.
- **Segment** — service lines / subsectors adjacent to the target's
  core that it could enter with modest capability build.
- **Channel** — payer / contracting channels the target has not yet
  developed (commercial direct, medicare advantage, ACO risk).

Each opportunity gets an attractiveness score (0..1) blending
addressable size, competitive intensity, and proximity-to-core.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


# ── Illustrative catalog of common adjacencies by subsector ─────────

_ADJACENCIES: Dict[str, Dict[str, List[str]]] = {
    "acute_care": {
        "segment": ["outpatient imaging", "ambulatory surgery",
                    "behavioral health", "cardiology specialty"],
        "channel": ["medicare_advantage", "direct-contracting",
                    "bundled payments"],
    },
    "asc": {
        "segment": ["specialty (ortho/ophth/pain)", "outpatient imaging"],
        "channel": ["commercial_direct", "bundled payments"],
    },
    "behavioral": {
        "segment": ["IOP/PHP step-down", "SUD/detox",
                    "autism services"],
        "channel": ["medicaid_managed_care", "employer_direct"],
    },
    "post_acute": {
        "segment": ["home health", "hospice", "assisted living"],
        "channel": ["medicare_advantage", "I-SNPs"],
    },
    "specialty": {
        "segment": ["ASC joint venture", "telehealth adjunct"],
        "channel": ["medicare_advantage", "employer_direct"],
    },
    "outpatient": {
        "segment": ["urgent care", "primary care", "dx imaging"],
        "channel": ["capitation", "value-based"],
    },
    "critical_access": {
        "segment": ["telehealth", "swing beds"],
        "channel": ["medicare_advantage"],
    },
}


@dataclass
class WhiteSpaceOpportunity:
    dimension: str              # "geographic" | "segment" | "channel"
    name: str
    score: float                # 0..1 attractiveness
    rationale: str = ""
    barriers: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "dimension": self.dimension,
            "name": self.name,
            "score": self.score,
            "rationale": self.rationale,
            "barriers": list(self.barriers),
        }


@dataclass
class WhiteSpaceResult:
    opportunities: List[WhiteSpaceOpportunity] = field(default_factory=list)
    top_dimension: Optional[str] = None
    partner_note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "opportunities": [o.to_dict() for o in self.opportunities],
            "top_dimension": self.top_dimension,
            "partner_note": self.partner_note,
        }


@dataclass
class WhiteSpaceInputs:
    subsector: Optional[str] = None
    state: Optional[str] = None
    existing_states: List[str] = field(default_factory=list)
    existing_segments: List[str] = field(default_factory=list)
    existing_channels: List[str] = field(default_factory=list)
    candidate_states: List[str] = field(default_factory=list)
    candidate_segments: List[str] = field(default_factory=list)
    candidate_channels: List[str] = field(default_factory=list)


def _subsector_key(s: str) -> str:
    aliases = {
        "hospital": "acute_care", "acute": "acute_care",
        "snf": "post_acute", "ltach": "post_acute",
        "psych": "behavioral", "clinic": "outpatient",
        "cah": "critical_access",
    }
    return aliases.get(s.lower().strip(), s.lower().strip())


def _score_geographic(ex: List[str], cand: List[str]) -> List[WhiteSpaceOpportunity]:
    ex_set = {s.upper() for s in ex if s}
    out: List[WhiteSpaceOpportunity] = []
    for s in cand:
        s_up = (s or "").upper()
        if not s_up or s_up in ex_set:
            continue
        # Simple attractiveness heuristic: adjacent state = higher, distant = lower.
        score = 0.6 if _is_adjacent(ex_set, s_up) else 0.4
        out.append(WhiteSpaceOpportunity(
            dimension="geographic",
            name=s_up,
            score=score,
            rationale=(f"Candidate state {s_up} with no current footprint."
                       + (" Adjacent to existing operations." if score >= 0.6
                          else " Distant from current footprint.")),
            barriers=["regulatory re-licensing", "payer contracting"]
                     if score < 0.6 else ["regulatory re-licensing"],
        ))
    return out


# Rough US census-region adjacency table (intentionally coarse).
_REGION = {
    "WEST": {"WA", "OR", "CA", "NV", "ID", "MT", "WY", "UT", "CO", "AZ", "NM", "AK", "HI"},
    "MIDWEST": {"ND", "SD", "NE", "KS", "MN", "IA", "MO", "WI", "IL", "IN", "MI", "OH"},
    "SOUTH": {"TX", "OK", "AR", "LA", "MS", "AL", "TN", "KY", "WV", "VA", "NC", "SC", "GA", "FL", "MD", "DE", "DC"},
    "NORTHEAST": {"ME", "NH", "VT", "MA", "RI", "CT", "NY", "NJ", "PA"},
}


def _is_adjacent(ex_set: set, state: str) -> bool:
    if not ex_set or not state:
        return False
    for region, members in _REGION.items():
        if state in members and ex_set & members:
            return True
    return False


def _score_segment(subsector: Optional[str],
                   ex: List[str],
                   cand: List[str]) -> List[WhiteSpaceOpportunity]:
    ex_set = {s.lower() for s in ex if s}
    # Merge caller candidates with registry adjacencies.
    default_adj: List[str] = []
    if subsector:
        default_adj = _ADJACENCIES.get(_subsector_key(subsector), {}).get("segment", [])
    all_cand = list(dict.fromkeys([*cand, *default_adj]))

    out: List[WhiteSpaceOpportunity] = []
    for seg in all_cand:
        if not seg or seg.lower() in ex_set:
            continue
        # Registry-adjacency candidates score higher for proximity-to-core.
        is_reg = seg in default_adj
        score = 0.70 if is_reg else 0.45
        out.append(WhiteSpaceOpportunity(
            dimension="segment",
            name=seg,
            score=score,
            rationale=(f"Service-line extension into {seg}."
                       + (" Registry-recognized adjacency." if is_reg
                          else " Custom candidate — validate proximity.")),
            barriers=["clinical capability build", "credentialing"]
                     if not is_reg else ["credentialing"],
        ))
    return out


def _score_channel(subsector: Optional[str],
                   ex: List[str],
                   cand: List[str]) -> List[WhiteSpaceOpportunity]:
    ex_set = {s.lower() for s in ex if s}
    default_ch: List[str] = []
    if subsector:
        default_ch = _ADJACENCIES.get(_subsector_key(subsector), {}).get("channel", [])
    all_cand = list(dict.fromkeys([*cand, *default_ch]))

    out: List[WhiteSpaceOpportunity] = []
    for ch in all_cand:
        if not ch or ch.lower() in ex_set:
            continue
        is_reg = ch in default_ch
        score = 0.65 if is_reg else 0.40
        out.append(WhiteSpaceOpportunity(
            dimension="channel",
            name=ch,
            score=score,
            rationale=(f"Channel expansion into {ch}."
                       + (" Registry-recognized." if is_reg
                          else " Custom channel — validate demand.")),
            barriers=["contract build", "payer credentialing"],
        ))
    return out


def _partner_note(opps: List[WhiteSpaceOpportunity], top_dim: Optional[str]) -> str:
    if not opps:
        return ("No white-space opportunities surfaced — target already covers "
                "the attainable adjacencies.")
    strong = [o for o in opps if o.score >= 0.65]
    if strong and top_dim:
        labels = {
            "geographic": "regional expansion",
            "segment": "service-line extension",
            "channel": "payer / channel build",
        }
        return (f"Best adjacency is {labels.get(top_dim, top_dim)} "
                f"({len(strong)} high-score opportunit{'y' if len(strong)==1 else 'ies'}).")
    return ("Adjacency candidates exist but require capability build — "
            "treat as upside only.")


def detect_white_space(inputs: WhiteSpaceInputs) -> WhiteSpaceResult:
    """Detect white-space opportunities across the three dimensions."""
    opps: List[WhiteSpaceOpportunity] = []
    opps.extend(_score_geographic(inputs.existing_states,
                                  inputs.candidate_states))
    opps.extend(_score_segment(inputs.subsector, inputs.existing_segments,
                               inputs.candidate_segments))
    opps.extend(_score_channel(inputs.subsector, inputs.existing_channels,
                               inputs.candidate_channels))
    # Sort by score descending.
    opps.sort(key=lambda o: -o.score)

    # Top dimension = the dimension with the highest aggregate score.
    agg: Dict[str, float] = {}
    for o in opps:
        agg[o.dimension] = agg.get(o.dimension, 0.0) + o.score
    top_dim = max(agg.items(), key=lambda kv: kv[1])[0] if agg else None

    return WhiteSpaceResult(
        opportunities=opps,
        top_dimension=top_dim,
        partner_note=_partner_note(opps, top_dim),
    )


def top_opportunities(result: WhiteSpaceResult,
                      *, n: int = 3) -> List[WhiteSpaceOpportunity]:
    return result.opportunities[:max(n, 1)]
