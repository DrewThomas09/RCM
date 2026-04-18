"""Process stopwatch — what deal timing tells the partner.

Partners read process timing the way cardiologists read EKGs.
The banker's process runs at a certain tempo; deviations carry
information:

- **Tight close clock** (< 4 weeks from LOI to expected close)
  — banker is trying to prevent deep diligence. Probably aware
  of an issue.
- **Second round after first walked** — the first buyer found
  something. What?
- **Extended process with no winner** (90+ days in round 2) —
  process is broken. Either price is too high or diligence
  surfaced something.
- **Buyer count collapsed round-to-round** — either the asset
  is losing traction or a specific issue spread through the
  buyer group.
- **Banker aggressively defending price** — weak comps; no
  natural clearing price.
- **Seller re-engaging passed buyers** — process failed first
  run; partner should ask what changed.
- **Quiet during diligence** — no news is often bad news;
  diligence is surfacing things.

This module takes process-timing signals and returns a partner-
voice read on what the clock is saying.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ProcessTiming:
    weeks_from_teaser_to_loi: int = 6
    weeks_from_loi_to_expected_close: int = 12
    round_count: int = 2                    # how many rounds run so far
    round_1_bidders: int = 12
    round_2_bidders: int = 5
    bidders_walked_in_round_1: int = 0
    bidders_walked_in_round_2: int = 0
    banker_rigidity_on_price: bool = False  # banker aggressively defending
    seller_reengaged_prior_passers: bool = False
    silence_during_diligence: bool = False
    repriced_downward_already: bool = False


@dataclass
class ProcessReadout:
    name: str
    severity: str                           # "low" / "medium" / "high"
    signal: str
    partner_commentary: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "severity": self.severity,
            "signal": self.signal,
            "partner_commentary": self.partner_commentary,
        }


@dataclass
class ProcessReport:
    readouts: List[ProcessReadout] = field(default_factory=list)
    high_count: int = 0
    partner_note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "readouts": [r.to_dict() for r in self.readouts],
            "high_count": self.high_count,
            "partner_note": self.partner_note,
        }


def _tight_close(p: ProcessTiming) -> Optional[ProcessReadout]:
    if p.weeks_from_loi_to_expected_close <= 4:
        return ProcessReadout(
            name="tight_close_clock", severity="high",
            signal=(f"LOI-to-close clock is "
                     f"{p.weeks_from_loi_to_expected_close} weeks."),
            partner_commentary=(
                "Tight close clocks exist to prevent deep diligence. "
                "Banker is either running a clean Monday-morning "
                "process or hiding something. Insist on standard "
                "QofE and forensic billing timelines or pass."),
        )
    return None


def _bidder_collapse(p: ProcessTiming) -> Optional[ProcessReadout]:
    if (p.round_1_bidders > 0
            and p.round_2_bidders / max(1, p.round_1_bidders) <= 0.25):
        return ProcessReadout(
            name="bidder_collapse", severity="high",
            signal=(f"Bidders went from {p.round_1_bidders} to "
                     f"{p.round_2_bidders} round-to-round."),
            partner_commentary=(
                "When a buyer pool collapses > 75%, a specific "
                "finding is spreading through the group. Usually "
                "billing, payer, or regulatory. Get the data that "
                "killed round 1."),
        )
    return None


def _extended_round_2(p: ProcessTiming) -> Optional[ProcessReadout]:
    if p.round_count >= 2 and p.seller_reengaged_prior_passers:
        return ProcessReadout(
            name="process_relaunched", severity="high",
            signal="Seller is re-engaging buyers who previously passed.",
            partner_commentary=(
                "First process failed. Before round 2, a partner "
                "asks what the seller changed — price, structure, "
                "disclosures? Re-engagement without a changed "
                "package is a tell."),
        )
    return None


def _repriced(p: ProcessTiming) -> Optional[ProcessReadout]:
    if p.repriced_downward_already:
        return ProcessReadout(
            name="repriced_during_process", severity="medium",
            signal="Asking price has already been reset downward.",
            partner_commentary=(
                "Price resets in-process tell the partner: the "
                "market priced this below the banker's expectation. "
                "Use that as leverage; don't let the banker anchor "
                "on the original ask."),
        )
    return None


def _banker_rigid(p: ProcessTiming) -> Optional[ProcessReadout]:
    if p.banker_rigidity_on_price:
        return ProcessReadout(
            name="banker_rigid_on_price", severity="medium",
            signal="Banker aggressively defending price with no flex.",
            partner_commentary=(
                "Aggressive price defense usually means weak comps "
                "and no natural clearing price. Price is an anchor, "
                "not a number backed by buyer interest."),
        )
    return None


def _diligence_silence(p: ProcessTiming) -> Optional[ProcessReadout]:
    if p.silence_during_diligence:
        return ProcessReadout(
            name="diligence_silence", severity="medium",
            signal="Seller / management have gone quiet during diligence.",
            partner_commentary=(
                "No news during diligence is often bad news. Third-"
                "party reports are surfacing items management "
                "doesn't want to engage on. Press harder."),
        )
    return None


def _bidders_walked(p: ProcessTiming) -> Optional[ProcessReadout]:
    total_walked = p.bidders_walked_in_round_1 + p.bidders_walked_in_round_2
    if total_walked >= 3:
        return ProcessReadout(
            name="multiple_walks", severity="medium",
            signal=(f"{total_walked} bidders have walked mid-process."),
            partner_commentary=(
                "Multiple walks = something in the data room pattern-"
                "matches to an issue several sponsors recognize. "
                "Call a peer partner — what did they find?"),
        )
    return None


DETECTORS = (
    _tight_close,
    _bidder_collapse,
    _extended_round_2,
    _bidders_walked,
    _repriced,
    _banker_rigid,
    _diligence_silence,
)


def read_process(p: ProcessTiming) -> ProcessReport:
    readouts = [d(p) for d in DETECTORS]
    readouts = [r for r in readouts if r is not None]
    high = sum(1 for r in readouts if r.severity == "high")

    if high >= 2:
        note = (f"{high} high-severity process signals — the clock "
                "itself is telling you to be careful. Press banker "
                "for what's actually happening in the room.")
    elif high == 1:
        top = next(r for r in readouts if r.severity == "high")
        note = (f"One high-severity process tell: '{top.name}'. "
                "Investigate before moving forward.")
    elif readouts:
        note = (f"{len(readouts)} medium process signals — noted. "
                "Fold into diligence questions.")
    else:
        note = ("Process tempo reads normal. No signals suggesting "
                "buyer-side leverage or hidden issues.")

    return ProcessReport(
        readouts=readouts,
        high_count=high,
        partner_note=note,
    )


def render_process_markdown(r: ProcessReport) -> str:
    lines = [
        "# Process stopwatch",
        "",
        f"_{r.partner_note}_",
        "",
    ]
    for ro in r.readouts:
        lines.append(f"## {ro.name} ({ro.severity.upper()})")
        lines.append(f"- **Signal:** {ro.signal}")
        lines.append(f"- **Partner commentary:** {ro.partner_commentary}")
        lines.append("")
    return "\n".join(lines)
