"""CON (Certificate of Need) state exposure — protection vs. barrier.

Partner statement: "CON states protect incumbents
but block expansion. If the deal is already the
dominant operator in a CON state, the moat is real;
if we're trying to build de novos in a CON state,
every site needs a board application and a 12-18
month hearing. The CON question isn't binary — it's
'are we incumbent or entrant in each footprint
state?'"

Distinct from:
- `state_scope_of_practice_exposure` — CPOM + non-
  compete.
- `multi_state_regulatory_complexity_scorer` —
  general complexity.

This module classifies per-state CON exposure as
protection (we're incumbent) vs. barrier (we're
trying to expand).

### Per-state CON catalog

CON coverage varies by service type. Hospital beds
are CON-regulated in ~35 states; ASC in ~25; home
health in ~15. This module focuses on
**hospital/ASC/home health/hospice** as the most
common deal-relevant lines.

### Output

Per footprint-state CON posture (strict / moderate /
none) and per-line CON exposure (protection /
barrier / mixed / none).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


# Per-state CON strictness for common service lines.
# "strict" = CON required + active enforcement
# "moderate" = CON for some service types / thresholds
# "none" = CON repealed or not enforced
CON_STATE_BOOK: Dict[str, Dict[str, str]] = {
    "AL": {"hospital": "strict", "asc": "strict",
           "home_health": "strict", "hospice": "strict"},
    "CT": {"hospital": "strict", "asc": "strict",
           "home_health": "strict", "hospice": "moderate"},
    "FL": {"hospital": "moderate", "asc": "none",
           "home_health": "strict", "hospice": "strict"},
    "GA": {"hospital": "strict", "asc": "moderate",
           "home_health": "strict", "hospice": "strict"},
    "HI": {"hospital": "strict", "asc": "strict",
           "home_health": "strict", "hospice": "moderate"},
    "IL": {"hospital": "strict", "asc": "moderate",
           "home_health": "strict", "hospice": "moderate"},
    "KY": {"hospital": "strict", "asc": "moderate",
           "home_health": "strict", "hospice": "strict"},
    "MA": {"hospital": "strict", "asc": "moderate",
           "home_health": "moderate", "hospice": "moderate"},
    "MD": {"hospital": "strict", "asc": "strict",
           "home_health": "strict", "hospice": "moderate"},
    "MI": {"hospital": "strict", "asc": "strict",
           "home_health": "moderate", "hospice": "moderate"},
    "MS": {"hospital": "strict", "asc": "strict",
           "home_health": "strict", "hospice": "strict"},
    "NC": {"hospital": "strict", "asc": "strict",
           "home_health": "strict", "hospice": "strict"},
    "NY": {"hospital": "strict", "asc": "strict",
           "home_health": "strict", "hospice": "strict"},
    "OH": {"hospital": "moderate", "asc": "none",
           "home_health": "none", "hospice": "none"},
    "TN": {"hospital": "strict", "asc": "moderate",
           "home_health": "strict", "hospice": "strict"},
    "VA": {"hospital": "strict", "asc": "strict",
           "home_health": "strict", "hospice": "strict"},
    "WA": {"hospital": "strict", "asc": "moderate",
           "home_health": "none", "hospice": "moderate"},
    "WV": {"hospital": "strict", "asc": "strict",
           "home_health": "strict", "hospice": "strict"},
    "TX": {"hospital": "none", "asc": "none",
           "home_health": "none", "hospice": "none"},
    "CA": {"hospital": "none", "asc": "none",
           "home_health": "none", "hospice": "none"},
    "AZ": {"hospital": "none", "asc": "none",
           "home_health": "none", "hospice": "none"},
    "CO": {"hospital": "none", "asc": "none",
           "home_health": "none", "hospice": "none"},
    "KS": {"hospital": "none", "asc": "none",
           "home_health": "none", "hospice": "none"},
    "NM": {"hospital": "none", "asc": "none",
           "home_health": "none", "hospice": "none"},
    "ID": {"hospital": "none", "asc": "none",
           "home_health": "none", "hospice": "none"},
    "PA": {"hospital": "none", "asc": "none",
           "home_health": "none", "hospice": "none"},
    "UT": {"hospital": "none", "asc": "none",
           "home_health": "none", "hospice": "none"},
    "WY": {"hospital": "none", "asc": "none",
           "home_health": "none", "hospice": "none"},
}


@dataclass
class CONStateExposure:
    state: str
    share_of_npr_pct: float
    is_incumbent: bool = True
    """Is deal the incumbent operator (CON protection)
    or trying to expand (CON barrier)?"""
    primary_line: str = "hospital"


@dataclass
class CONAssessorInputs:
    footprint: List[CONStateExposure] = field(
        default_factory=list)


@dataclass
class CONStateHit:
    state: str
    in_catalog: bool
    con_status: str
    share_of_npr_pct: float
    is_incumbent: bool
    primary_line: str
    exposure_type: str  # "protection" / "barrier" / "neutral"


@dataclass
class CONAssessorReport:
    hits: List[CONStateHit] = field(default_factory=list)
    protection_share_pct: float = 0.0
    barrier_share_pct: float = 0.0
    verdict: str = "neutral"
    partner_note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "hits": [
                {"state": h.state,
                 "in_catalog": h.in_catalog,
                 "con_status": h.con_status,
                 "share_of_npr_pct": h.share_of_npr_pct,
                 "is_incumbent": h.is_incumbent,
                 "primary_line": h.primary_line,
                 "exposure_type": h.exposure_type}
                for h in self.hits
            ],
            "protection_share_pct":
                self.protection_share_pct,
            "barrier_share_pct":
                self.barrier_share_pct,
            "verdict": self.verdict,
            "partner_note": self.partner_note,
        }


def assess_con_state_exposure(
    inputs: CONAssessorInputs,
) -> CONAssessorReport:
    if not inputs.footprint:
        return CONAssessorReport(
            partner_note=(
                "No state footprint — verify which "
                "states the deal operates in."
            ),
        )

    hits: List[CONStateHit] = []
    protection_share = 0.0
    barrier_share = 0.0

    for fp in inputs.footprint:
        state = fp.state.upper()
        book = CON_STATE_BOOK.get(state)
        if book is None:
            hits.append(CONStateHit(
                state=state,
                in_catalog=False,
                con_status="unknown",
                share_of_npr_pct=round(
                    fp.share_of_npr_pct, 4),
                is_incumbent=fp.is_incumbent,
                primary_line=fp.primary_line,
                exposure_type="unknown",
            ))
            continue

        con_for_line = book.get(
            fp.primary_line, "none")
        if con_for_line == "none":
            exposure = "neutral"
        elif fp.is_incumbent:
            exposure = "protection"
            protection_share += fp.share_of_npr_pct
        else:
            exposure = "barrier"
            barrier_share += fp.share_of_npr_pct

        hits.append(CONStateHit(
            state=state,
            in_catalog=True,
            con_status=con_for_line,
            share_of_npr_pct=round(
                fp.share_of_npr_pct, 4),
            is_incumbent=fp.is_incumbent,
            primary_line=fp.primary_line,
            exposure_type=exposure,
        ))

    if protection_share >= 0.50:
        verdict = "incumbent_moat"
        note = (
            f"{protection_share:.0%} of NPR in CON "
            "states where we're incumbent — durable "
            "moat against entrants; protect via CON "
            "board relationships."
        )
    elif barrier_share >= 0.30:
        verdict = "expansion_blocked"
        note = (
            f"{barrier_share:.0%} of NPR in CON states "
            "as entrant — capacity expansion thesis "
            "faces 12-18 month CON hearings per site. "
            "Price the regulatory friction into "
            "timeline + capex."
        )
    elif protection_share > 0 and barrier_share > 0:
        verdict = "mixed"
        note = (
            f"Mixed CON exposure: "
            f"{protection_share:.0%} protected, "
            f"{barrier_share:.0%} as entrant. Per-"
            "state strategy needed."
        )
    else:
        verdict = "neutral"
        note = (
            "Footprint is primarily in non-CON states "
            "— no regulatory moat nor barrier."
        )

    return CONAssessorReport(
        hits=hits,
        protection_share_pct=round(
            protection_share, 4),
        barrier_share_pct=round(barrier_share, 4),
        verdict=verdict,
        partner_note=note,
    )


def render_con_exposure_markdown(
    r: CONAssessorReport,
) -> str:
    lines = [
        "# CON state exposure",
        "",
        f"_Verdict: **{r.verdict}**_ — {r.partner_note}",
        "",
        f"- Protection share: "
        f"{r.protection_share_pct:.0%}",
        f"- Barrier share: "
        f"{r.barrier_share_pct:.0%}",
        "",
        "| State | Share | CON status | Line | Role | Exposure |",
        "|---|---|---|---|---|---|",
    ]
    for h in r.hits:
        lines.append(
            f"| {h.state} | "
            f"{h.share_of_npr_pct:.0%} | "
            f"{h.con_status} | {h.primary_line} | "
            f"{'incumbent' if h.is_incumbent else 'entrant'} | "
            f"{h.exposure_type} |"
        )
    return "\n".join(lines)
