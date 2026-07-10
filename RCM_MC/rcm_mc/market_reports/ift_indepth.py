"""IFT In-Depth (``/ift-indepth``) — the answered question architecture.

This module is the data layer for the In-Depth surface: the ten study
questions, every subsection converted into a CONCLUSION-LED block, and every
subquestion answered in one line (or explicitly skipped with the reason —
company-internal figures are diligence requests, never inventions).

Writing contract (enforced by tests):
  * every block leads with a conclusion, then why-true findings, then the
    implication, then cited evidence;
  * evidence bases use the suite vocabulary — GOV / SOURCED / ACADEMIC /
    DERIVED / FRAMEWORK — no ILLUSTRATIVE anywhere;
  * a subquestion is either answered or carries a skip reason; blanks fail
    the tests;
  * banned filler phrases ("the market is evolving rapidly", "uniquely
    positioned", …) fail the tests.

Content lives in sibling modules (``ift_indepth_q1`` … ``ift_indepth_q910``)
so each question stays reviewable; this module owns the contract and the
aggregation. Degrades — never raises.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


@dataclass(frozen=True)
class SubQ:
    """One subquestion. ``a`` is the one-line answer; when a question is
    genuinely unanswerable from desk research (company-internal data), ``a``
    stays empty and ``skip`` names the reason — honesty over invention."""
    q: str
    a: str = ""
    skip: str = ""


@dataclass(frozen=True)
class Evidence:
    text: str            # the fact, with its number
    basis: str           # GOV | SOURCED | ACADEMIC | DERIVED | FRAMEWORK
    source: str          # publisher / study, year
    url: str = ""


@dataclass(frozen=True)
class Block:
    """One subsection of a question, answered in the study's format."""
    key: str
    title: str
    conclusion: str
    why_true: Tuple[str, ...]
    why_matters: str
    evidence: Tuple[Evidence, ...] = ()
    subqs: Tuple[SubQ, ...] = ()


@dataclass(frozen=True)
class QuestionDef:
    num: int
    slug: str
    title: str
    storyline: str                 # the question's one-line conclusion
    visual_key: str                # which page visual renders for it
    blocks: Tuple[Block, ...] = ()


# The five-step arc the page opens with.
STORYLINE: Tuple[str, ...] = (
    "IFT is structurally distinct",
    "it is essential to care transitions",
    "health systems use several imperfect models",
    "those models create measurable operational problems",
    "MMT's model is designed to address those problems",
)

BANNED_PHRASES: Tuple[str, ...] = (
    "the market is evolving rapidly",
    "is a critical component of healthcare",
    "uniquely positioned",
    "plays an important role",
    "there are several key stakeholders",
    "face numerous challenges",
)


def questions() -> Tuple[QuestionDef, ...]:
    """All ten questions, aggregated from the content modules. A content
    module that fails to import drops its questions (degrade, never raise)."""
    out: List[QuestionDef] = []
    for mod_name in ("ift_indepth_q1", "ift_indepth_q23", "ift_indepth_q456",
                     "ift_indepth_q78", "ift_indepth_q910"):
        try:
            mod = __import__(f"rcm_mc.market_reports.{mod_name}",
                             fromlist=["QUESTIONS"])
            out.extend(mod.QUESTIONS)
        except Exception:  # noqa: BLE001
            continue
    return tuple(sorted(out, key=lambda q: q.num))


def question(num: int) -> Optional[QuestionDef]:
    for q in questions():
        if q.num == num:
            return q
    return None


def coverage() -> Dict[str, int]:
    """Counts the tests + the page footer report: how many subquestions are
    answered vs explicitly skipped."""
    n_q = n_blocks = n_sub = n_ans = n_skip = 0
    for q in questions():
        n_q += 1
        for b in q.blocks:
            n_blocks += 1
            for s in b.subqs:
                n_sub += 1
                if s.a:
                    n_ans += 1
                elif s.skip:
                    n_skip += 1
    return {"questions": n_q, "blocks": n_blocks, "subquestions": n_sub,
            "answered": n_ans, "skipped": n_skip,
            "unaccounted": n_sub - n_ans - n_skip}
