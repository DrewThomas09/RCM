"""Change-my-mind diligence plan — the partner's follow-up ask list.

Partner statement: "Tell me the three things I'd
need to see to change my mind. Not abstract concerns
— specific data I can get in diligence. If I can't
tell you the source, the hypothesis is air. If I
can't tell you the calendar days, I can't sequence
the diligence. Every hypothesis that flips the call
must have an owner, a source, a cost, and a date."

Distinct from `ic_decision_synthesizer` (one
recommendation + 3 flip-the-call signals, abstract).
This module is the **operational plan**: for each
hypothesis that would flip the IC call, the specific
diligence action that closes it.

### Shape of the output

For each hypothesis:
- **direction** — `flip_to_invest` or `flip_to_pass`.
- **hypothesis** — one sentence, falsifiable.
- **data_needed** — the specific number / document /
  interview output.
- **source** — management_meeting / qofe / payer_call /
  site_visit / customer_call / legal_drop /
  third_party_specialist.
- **cost_usd** — out-of-pocket estimate.
- **calendar_days** — time to close this hypothesis.
- **likelihood_pct** — rough odds we get the answer we
  need in the available window.
- **evidence_test** — what answer would confirm / deny.

### Ranking: cheapest-highest-likelihood first

The partner sequences diligence to close the
cheapest, highest-likelihood flippers first — if they
close, you've bought conviction or saved weeks. This
module outputs the **ordered** ask list.

### Total-plan verdict

- **closable_in_2_weeks** — all flip-signals have
  sources that resolve in < 14 days and cost < $50k.
  Run the full plan before IC reconvenes.
- **needs_4_weeks** — expert interviews / site
  visits lengthen the path.
- **irreducible** — at least one hypothesis cannot be
  closed in diligence (e.g., regulatory outcome, Q+1
  earnings). Partner has to take the bet without
  confirming.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


DIR_FLIP_TO_INVEST = "flip_to_invest"
DIR_FLIP_TO_PASS = "flip_to_pass"

SRC_MM = "management_meeting"
SRC_QOFE = "qofe"
SRC_PAYER = "payer_call"
SRC_SITE = "site_visit"
SRC_CUST = "customer_call"
SRC_LEGAL = "legal_drop"
SRC_EXPERT = "third_party_specialist"
SRC_DATA_ROOM = "data_room_pull"


@dataclass
class ChangeMyMindInputs:
    current_recommendation: str = "DILIGENCE MORE"
    # ranked flip-invest hypotheses — most important first
    flip_to_invest_hypotheses: List[str] = field(
        default_factory=list)
    # ranked flip-pass hypotheses
    flip_to_pass_hypotheses: List[str] = field(
        default_factory=list)
    # diligence window available (calendar days until IC)
    diligence_window_days: int = 21
    # budget ceiling on incremental spend
    diligence_budget_remaining_usd: float = 150000.0


@dataclass
class ChangeMyMindItem:
    direction: str
    hypothesis: str
    data_needed: str
    source: str
    cost_usd: float
    calendar_days: int
    likelihood_pct: float
    evidence_test: str
    sequence_rank: int = 0
    closable_in_window: bool = True


@dataclass
class ChangeMyMindPlan:
    items: List[ChangeMyMindItem] = field(
        default_factory=list)
    total_incremental_cost_usd: float = 0.0
    longest_calendar_days: int = 0
    verdict: str = "closable_in_2_weeks"
    partner_note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "items": [
                {"direction": i.direction,
                 "hypothesis": i.hypothesis,
                 "data_needed": i.data_needed,
                 "source": i.source,
                 "cost_usd": i.cost_usd,
                 "calendar_days": i.calendar_days,
                 "likelihood_pct": i.likelihood_pct,
                 "evidence_test": i.evidence_test,
                 "sequence_rank": i.sequence_rank,
                 "closable_in_window":
                     i.closable_in_window}
                for i in self.items
            ],
            "total_incremental_cost_usd":
                self.total_incremental_cost_usd,
            "longest_calendar_days":
                self.longest_calendar_days,
            "verdict": self.verdict,
            "partner_note": self.partner_note,
        }


# A compact catalog of common healthcare-PE flip
# hypotheses keyed to phrases. The module looks for
# keywords in the input hypothesis text and assembles
# the best-fit diligence action. If nothing matches,
# a generic "management meeting probe" action is
# synthesized so every hypothesis has some closure.
HYPOTHESIS_CATALOG: List[Dict[str, Any]] = [
    {
        "keywords": ["denial", "denials", "initial denial"],
        "data_needed": (
            "monthly initial-denial rate by payer, "
            "trailing 18 months, with service-line cut"),
        "source": SRC_DATA_ROOM,
        "cost_usd": 0.0,
        "calendar_days": 5,
        "likelihood_pct": 0.90,
        "evidence_test": (
            "denial-rate trend confirms / contradicts "
            "the 200 bps/yr improvement assumed in the "
            "bridge"),
    },
    {
        "keywords": ["payer", "contract", "renegotiat",
                     "rate"],
        "data_needed": (
            "top-5 payer contract dates + current rate "
            "vs. market; signed renewal letters of "
            "intent, if any"),
        "source": SRC_PAYER,
        "cost_usd": 25000.0,
        "calendar_days": 14,
        "likelihood_pct": 0.65,
        "evidence_test": (
            "payer reps will confirm rate trajectory "
            "and any pending notices to terminate"),
    },
    {
        "keywords": ["ebitda", "add-back", "addback",
                     "quality of earnings", "qofe"],
        "data_needed": (
            "big-4 QofE report with management "
            "add-back schedule line-item reviewed"),
        "source": SRC_QOFE,
        "cost_usd": 125000.0,
        "calendar_days": 35,
        "likelihood_pct": 0.95,
        "evidence_test": (
            "QofE pro-forma EBITDA within 3% of "
            "management-stated, add-backs > 80% "
            "survival"),
    },
    {
        "keywords": ["cms", "survey", "deficienc",
                     "2567"],
        "data_needed": (
            "CMS 2567 survey history + plan of "
            "correction status, last 36 months"),
        "source": SRC_LEGAL,
        "cost_usd": 10000.0,
        "calendar_days": 10,
        "likelihood_pct": 0.85,
        "evidence_test": (
            "no unresolved immediate jeopardy or G-"
            "level tags"),
    },
    {
        "keywords": ["physician", "provider",
                     "comp", "productivity"],
        "data_needed": (
            "physician-level comp schedule with wRVU "
            "productivity and retention-by-cohort"),
        "source": SRC_MM,
        "cost_usd": 0.0,
        "calendar_days": 7,
        "likelihood_pct": 0.70,
        "evidence_test": (
            "comp normalization claim is supported by "
            "under-market comp vs. MGMA"),
    },
    {
        "keywords": ["culture", "ceo", "leadership",
                     "management team"],
        "data_needed": (
            "3 structured reference calls + 1 site "
            "visit with unprompted staff"),
        "source": SRC_SITE,
        "cost_usd": 8000.0,
        "calendar_days": 12,
        "likelihood_pct": 0.75,
        "evidence_test": (
            "reference-call tone + site-visit morale "
            "consistent with management pitch"),
    },
    {
        "keywords": ["customer", "concentrat", "top-5",
                     "client"],
        "data_needed": (
            "3 reference calls with top-5 customers; "
            "contract dates and satisfaction"),
        "source": SRC_CUST,
        "cost_usd": 15000.0,
        "calendar_days": 10,
        "likelihood_pct": 0.60,
        "evidence_test": (
            "customer tone confirms no pending RFP "
            "or rate-reset threat"),
    },
    {
        "keywords": ["cyber", "breach", "hipaa",
                     "security"],
        "data_needed": (
            "24-month cyber incident log + HHS-OCR "
            "breach-portal search + penetration-test "
            "summary"),
        "source": SRC_LEGAL,
        "cost_usd": 20000.0,
        "calendar_days": 14,
        "likelihood_pct": 0.85,
        "evidence_test": (
            "no unreported reportable breach + tested "
            "incident-response runbook"),
    },
    {
        "keywords": ["litigation", "lawsuit", "legal"],
        "data_needed": (
            "full open-litigation inventory + counsel "
            "opinion on expected cost"),
        "source": SRC_LEGAL,
        "cost_usd": 15000.0,
        "calendar_days": 10,
        "likelihood_pct": 0.80,
        "evidence_test": (
            "aggregate counsel-estimated exposure < "
            "R&W escrow cap"),
    },
    {
        "keywords": ["regulatory", "obbba", "medicaid",
                     "medicare", "reimbursement",
                     "site-neutral"],
        "data_needed": (
            "sector policy specialist interview +"
            " CMS proposed-rule review"),
        "source": SRC_EXPERT,
        "cost_usd": 25000.0,
        "calendar_days": 14,
        "likelihood_pct": 0.70,
        "evidence_test": (
            "specialist gives a < 3% expected-NPR "
            "impact by 2028"),
    },
    {
        "keywords": ["integration", "synerg",
                     "merger", "bolt-on", "add-on"],
        "data_needed": (
            "integration-plan document + named "
            "integration lead + 6-bolt-on pipeline "
            "with LOI status"),
        "source": SRC_MM,
        "cost_usd": 0.0,
        "calendar_days": 7,
        "likelihood_pct": 0.75,
        "evidence_test": (
            "named lead has integrated platform "
            "before + pipeline is real-named, not "
            "aspirational"),
    },
    {
        "keywords": ["growth", "same-store", "organic",
                     "volume"],
        "data_needed": (
            "monthly same-store volume + rate + mix "
            "decomposition, trailing 24 months"),
        "source": SRC_DATA_ROOM,
        "cost_usd": 0.0,
        "calendar_days": 7,
        "likelihood_pct": 0.85,
        "evidence_test": (
            "organic same-store growth > 4%; M&A not "
            "masking decline"),
    },
]


def _match_hypothesis(text: str) -> Dict[str, Any]:
    low = text.lower()
    best: Optional[Dict[str, Any]] = None
    best_hits = 0
    for entry in HYPOTHESIS_CATALOG:
        hits = sum(1 for kw in entry["keywords"] if kw in low)
        if hits > best_hits:
            best_hits = hits
            best = entry
    if best is None:
        return {
            "data_needed": (
                "structured management-meeting probe "
                "with pre-briefed follow-ups"),
            "source": SRC_MM,
            "cost_usd": 0.0,
            "calendar_days": 7,
            "likelihood_pct": 0.55,
            "evidence_test": (
                "management answer directly "
                "confirms or denies hypothesis with "
                "numbers, not narrative"),
        }
    return best


def plan_change_my_mind(
    inputs: ChangeMyMindInputs,
) -> ChangeMyMindPlan:
    items: List[ChangeMyMindItem] = []

    def build(dir_: str, hyp_list: List[str]) -> None:
        for h in hyp_list:
            entry = _match_hypothesis(h)
            items.append(ChangeMyMindItem(
                direction=dir_,
                hypothesis=h,
                data_needed=entry["data_needed"],
                source=entry["source"],
                cost_usd=float(entry["cost_usd"]),
                calendar_days=int(entry["calendar_days"]),
                likelihood_pct=float(
                    entry["likelihood_pct"]),
                evidence_test=entry["evidence_test"],
                closable_in_window=(
                    entry["calendar_days"] <=
                    inputs.diligence_window_days and
                    entry["cost_usd"] <=
                    inputs.diligence_budget_remaining_usd
                ),
            ))

    build(DIR_FLIP_TO_INVEST,
          inputs.flip_to_invest_hypotheses)
    build(DIR_FLIP_TO_PASS,
          inputs.flip_to_pass_hypotheses)

    # Sequence: cheapest-highest-likelihood first. Score
    # = likelihood / (1 + cost/1000 + days/7). Higher is
    # earlier in the queue.
    def score(i: ChangeMyMindItem) -> float:
        denom = 1.0 + i.cost_usd / 1000.0 + i.calendar_days / 7.0
        return i.likelihood_pct / max(denom, 0.1)

    items.sort(key=score, reverse=True)
    for rank, i in enumerate(items, start=1):
        i.sequence_rank = rank

    total_cost = sum(i.cost_usd for i in items)
    longest = max((i.calendar_days for i in items),
                  default=0)

    any_outside = any(
        not i.closable_in_window for i in items)
    if any_outside:
        if total_cost > inputs.diligence_budget_remaining_usd * 2:
            verdict = "irreducible"
            note = (
                "At least one hypothesis cannot be closed "
                "in the available window or budget. "
                "Partner must decide with an open question; "
                "build deal-structure protection (escrow, "
                "earn-out, walk-right) around the "
                "irreducible item rather than try to "
                "diligence past it."
            )
        else:
            verdict = "needs_4_weeks"
            note = (
                f"Full ask list closes in "
                f"~{longest} calendar days and "
                f"${total_cost:,.0f}. Extend diligence "
                "window or de-scope lowest-"
                "likelihood asks."
            )
    elif total_cost > inputs.diligence_budget_remaining_usd:
        verdict = "needs_4_weeks"
        note = (
            f"Plan exceeds budget "
            f"(${total_cost:,.0f} vs. "
            f"${inputs.diligence_budget_remaining_usd:,.0f}). "
            "Either request additional diligence spend or "
            "drop lowest-likelihood items."
        )
    else:
        verdict = "closable_in_2_weeks"
        note = (
            f"All {len(items)} flip hypotheses are "
            f"closable in the window "
            f"(~${total_cost:,.0f} / "
            f"{longest} days). Run the plan before IC "
            "reconvenes."
        )

    return ChangeMyMindPlan(
        items=items,
        total_incremental_cost_usd=round(total_cost, 2),
        longest_calendar_days=longest,
        verdict=verdict,
        partner_note=note,
    )


def render_change_my_mind_markdown(
    p: ChangeMyMindPlan,
) -> str:
    lines = [
        "# Change-my-mind diligence plan",
        "",
        f"_Verdict: **{p.verdict}**_ — {p.partner_note}",
        "",
        f"- Total cost: ${p.total_incremental_cost_usd:,.0f}",
        f"- Longest path: {p.longest_calendar_days} days",
        "",
        "| # | Direction | Hypothesis | Source | Days | Cost | Likelihood | In window |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for i in p.items:
        lines.append(
            f"| {i.sequence_rank} | {i.direction} | "
            f"{i.hypothesis} | {i.source} | "
            f"{i.calendar_days} | "
            f"${i.cost_usd:,.0f} | "
            f"{i.likelihood_pct:.0%} | "
            f"{'✓' if i.closable_in_window else '✗'} |"
        )
    return "\n".join(lines)
