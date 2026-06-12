"""Expert-call program — the voice-of-customer workstream of a CDD.

A commercial due diligence stands on primary research: structured calls
with the people who actually live in the target's market — referring
physicians, payer contracting executives, competitor operators, former
employees. The platform's public-data surfaces (CIM Cross-Check, TAM /
SAM, local market) answer what the filings can answer; the call program
answers what only humans can: switching behavior, reputation, contract
renewal intent, why patients/referrers actually choose the target.

This module is the UI-free core:

- :data:`STAKEHOLDER_TYPES` — the seven lenses of a standard program,
  each with who they are, what only they can tell you, a recommended
  call count, and the lens's systematic bias (every source lies in a
  predictable direction; the guide says which).
- :data:`QUESTION_BANK` — curated questions per lens, each tagged with
  its CDD topic and a "listen for" line (what a strong vs concerning
  answer sounds like). A starting point, NOT engagement-specific
  design — stated on-page.
- :func:`build_call_guide` — an ordered, printable guide for one lens:
  compliance-safe opening, questions grouped by topic, closing asks.
- :func:`program_plan` — the call mix for a target program size,
  scaled from the per-lens recommendations.
- :func:`coverage_read` — honest gap read over completed-call counts:
  a lens with one call is single-source, zero is a blind spot; never
  averages it away into a fake "80% done".
"""
from __future__ import annotations

import math
from typing import Any, Dict, List, Optional

# CDD topics every program must triangulate. Order = guide order.
CDD_TOPICS: List[str] = [
    "demand", "competition", "pricing_reimbursement",
    "stickiness", "labor", "growth", "risks",
]

_TOPIC_LABELS: Dict[str, str] = {
    "demand": "Demand & volume drivers",
    "competition": "Competitive position",
    "pricing_reimbursement": "Pricing & reimbursement",
    "stickiness": "Switching & stickiness",
    "labor": "Labor & clinical staffing",
    "growth": "Growth & whitespace",
    "risks": "Risks & disruption",
}


def topic_label(key: str) -> str:
    return _TOPIC_LABELS.get(key, key.replace("_", " ").title())


# ── The seven lenses ────────────────────────────────────────────────
# target_calls sums to 20 — the standard 3–4 week CDD program size;
# program_plan() scales proportionally for other totals.

STAKEHOLDER_TYPES: List[Dict[str, Any]] = [
    {
        "key": "referring_physician",
        "label": "Referring physician",
        "who": "Physicians who send (or could send) patients to the "
               "target — the demand side of a provider business.",
        "why": "Only referrers can tell you whether volume is loyalty "
               "or inertia, who they'd switch to, and what would make "
               "them switch tomorrow.",
        "target_calls": 5,
        "sourcing": "Expert networks; NPPES referral-pattern pulls; "
                    "the target's own referrer list (request in the "
                    "data room, then call OFF-list names too).",
        "bias": "Active referrers self-select as satisfied — the "
                "referrers who already left tell the churn story. "
                "Insist on lapsed referrers in the sample.",
    },
    {
        "key": "payer_exec",
        "label": "Payer / contracting executive",
        "who": "Network-management and contracting leads at the "
               "commercial plans and MA carriers the target bills.",
        "why": "Only payers can tell you whether the target's rates "
               "are above-market (re-contracting risk) and whether "
               "it is must-have or substitutable in network design.",
        "target_calls": 3,
        "sourcing": "Expert networks (current execs usually can't "
                    "speak — book RECENTLY DEPARTED contracting "
                    "leads from the named plans).",
        "bias": "Payers talk their book: every provider is "
                "'overpaid' in a payer interview. Calibrate against "
                "filed rate data, not adjectives.",
    },
    {
        "key": "competitor_exec",
        "label": "Competitor executive",
        "who": "Current or former operators at the named local "
               "competitors (the X-Ray's 25-mile panel is the list).",
        "why": "Competitors know where the target wins and loses "
               "head-to-head, and what capacity they themselves are "
               "adding — the supply-side counter to the growth plan.",
        "target_calls": 3,
        "sourcing": "Former executives via expert networks only — "
                    "current competitor staff raise process-integrity "
                    "and antitrust-communication concerns.",
        "bias": "Competitors disparage by default and overstate "
                "their own pipelines. Use them for facts (capacity, "
                "wins/losses), not for opinions on the target.",
    },
    {
        "key": "former_employee",
        "label": "Former employee of the target",
        "who": "Operators who left the target in the last ~24 months "
               "— ops leaders, clinic managers, RCM staff.",
        "why": "The only lens on what the CIM leaves out: real "
               "scheduling utilization, leadership turnover causes, "
               "whether reported KPIs are managed or measured.",
        "target_calls": 3,
        "sourcing": "Expert networks; LinkedIn alumni searches. "
                    "Compliance screen is strictest here (no MNPI, "
                    "no documents, NDA check before booking).",
        "bias": "Departure bias cuts both ways — disgruntled leavers "
                "overstate dysfunction, recent retirees sugarcoat. "
                "Ask for verifiable specifics, discard adjectives.",
    },
    {
        "key": "site_administrator",
        "label": "Site-of-care administrator",
        "who": "Administrators at the facilities the target's model "
               "depends on — discharging hospitals, host health "
               "systems, referring facility networks.",
        "why": "They control the channel: discharge protocols, "
               "preferred-provider lists, in-housing plans that can "
               "reroute the target's volume with one policy memo.",
        "target_calls": 2,
        "sourcing": "Expert networks; case-management and discharge-"
                    "planning leads at the named local hospitals.",
        "bias": "Administrators describe official policy, not actual "
                "practice at the bedside. Cross-check with the "
                "referring-physician calls.",
    },
    {
        "key": "patient_advocate",
        "label": "Patient / caregiver voice",
        "who": "Patient-advocacy organizations and caregiver "
               "communities for the target's clinical population.",
        "why": "Access, out-of-pocket burden, and reputation among "
               "patients — the demand-quality signal no operator "
               "interview carries.",
        "target_calls": 2,
        "sourcing": "Condition-specific advocacy groups; moderated "
                    "caregiver communities. Never patients of the "
                    "target recruited via the target.",
        "bias": "Advocacy staff generalize from the loudest cases. "
                "Treat as directional color on access + affordability, "
                "never as a volume estimate.",
    },
    {
        "key": "industry_expert",
        "label": "Industry / reimbursement expert",
        "who": "Former CMS / MAC / state-agency staff, sector "
               "consultants, association economists.",
        "why": "The regulatory and reimbursement trajectory — which "
               "of the platform's modeled headwinds are actually "
               "moving, and on what clock.",
        "target_calls": 2,
        "sourcing": "Expert networks; named authors of the sector's "
                    "rule-comment letters; association staff.",
        "bias": "Experts extrapolate confidently beyond their last "
                "direct exposure. Date-stamp everything ('as of "
                "when?') and weight recency.",
    },
]

_STAKEHOLDER_BY_KEY: Dict[str, Dict[str, Any]] = {
    s["key"]: s for s in STAKEHOLDER_TYPES
}


def stakeholder(key: str) -> Optional[Dict[str, Any]]:
    return _STAKEHOLDER_BY_KEY.get(key)


# ── Question bank ───────────────────────────────────────────────────
# Each entry: topic (CDD_TOPICS), question, listen_for (what a strong
# vs concerning answer sounds like — the analyst's scoring aid).

QUESTION_BANK: Dict[str, List[Dict[str, str]]] = {
    "referring_physician": [
        {"topic": "demand",
         "question": "Walk me through the last three patients you "
                     "referred for this service — where did each go, "
                     "and why that site?",
         "listen_for": "Strong: names the target unprompted with a "
                       "clinical reason. Concerning: 'whoever has the "
                       "next slot' — volume is capacity overflow, not "
                       "preference."},
        {"topic": "stickiness",
         "question": "What would have to change for you to send those "
                     "patients somewhere else?",
         "listen_for": "Strong: a high bar (quality incident, access "
                       "collapse). Concerning: 'a rep visit and an "
                       "easier fax line' — switching cost is near zero."},
        {"topic": "competition",
         "question": "Who else covers this service within your "
                     "referral radius, and how do they differ?",
         "listen_for": "Strong: target differentiated on something "
                       "patients feel (access, outcomes). Concerning: "
                       "referrer can't articulate a difference."},
        {"topic": "demand",
         "question": "Is your referral volume for this service growing, "
                     "flat, or shrinking — and what's driving that?",
         "listen_for": "Triangulates the TAM growth assumption with "
                       "ground truth; 'shrinking — we manage it "
                       "in-house now' is a thesis-level red flag."},
        {"topic": "stickiness",
         "question": "How does the target make referring easy or hard — "
                     "intake speed, reporting back, scheduling?",
         "listen_for": "Operational stickiness is buyable and fixable; "
                       "'reports never come back' is churn in motion "
                       "AND a value-creation lever."},
        {"topic": "risks",
         "question": "Have you ever pulled referrals from a provider in "
                     "this category? What triggered it?",
         "listen_for": "The actual churn trigger in this market — "
                       "compare against what the target could plausibly "
                       "do under cost pressure."},
    ],
    "payer_exec": [
        {"topic": "pricing_reimbursement",
         "question": "Where does this target sit versus market on your "
                     "fee schedule — and is that position defensible at "
                     "the next renewal?",
         "listen_for": "Strong: at/below market or must-have. "
                       "Concerning: 'top quartile and we know it' — "
                       "the re-contracting haircut is the bear case."},
        {"topic": "competition",
         "question": "If this provider left your network tomorrow, what "
                     "would happen to your members' access?",
         "listen_for": "The must-have test. 'We'd route to X and Y by "
                       "Friday' means zero negotiating leverage."},
        {"topic": "pricing_reimbursement",
         "question": "What's your plan's direction on site-of-care "
                     "steerage for these services over the next 2–3 "
                     "years?",
         "listen_for": "Confirms or breaks the site-shift tailwind the "
                       "model assumes — with the payer's own timeline."},
        {"topic": "risks",
         "question": "What utilization-management changes are coming for "
                     "these codes — prior auth, step therapy, white-"
                     "bagging?",
         "listen_for": "Each named UM program is a revenue-cycle cost "
                       "the QoE must carry; 'under review' clusters "
                       "before implementation."},
        {"topic": "growth",
         "question": "Are you narrowing or broadening networks in this "
                     "category — and what gets a provider added?",
         "listen_for": "Whitespace reality check: de-novo sites only "
                       "work if plans are still contracting them."},
        {"topic": "demand",
         "question": "What's happening to your MA vs commercial mix in "
                     "this market, and how does that change what you "
                     "pay for this service?",
         "listen_for": "Mix shift to MA usually compresses realized "
                       "rates — quantifies the payer-mix drift the "
                       "screener flags."},
    ],
    "competitor_exec": [
        {"topic": "competition",
         "question": "When you compete head-to-head with the target for "
                     "a referral source or contract, who wins and why?",
         "listen_for": "Specific named wins/losses beat adjectives. "
                       "Symmetric answers ('we split on geography') "
                       "suggest a commodity service."},
        {"topic": "growth",
         "question": "What capacity are you adding in this market over "
                     "the next 24 months — sites, chairs, staff?",
         "listen_for": "Sums with other competitor calls into a supply "
                       "build; if supply growth > demand growth, the "
                       "pricing assumptions are at risk."},
        {"topic": "pricing_reimbursement",
         "question": "How do you price against the target — premium, "
                     "parity, or discount — and is anyone buying share?",
         "listen_for": "'Buying share' (discounting to win contracts) "
                       "is the leading indicator of a rate war."},
        {"topic": "labor",
         "question": "Where do you hire your clinical staff from, and "
                     "what are you paying versus two years ago?",
         "listen_for": "If competitors poach from the target's labor "
                       "pool at +20%, the margin bridge's labor line "
                       "is stale."},
        {"topic": "stickiness",
         "question": "When an account moves between you and the target, "
                     "what actually moves it?",
         "listen_for": "The real switching mechanics of this market — "
                       "service, price, relationships, or contracts."},
        {"topic": "risks",
         "question": "What's the thing in this market that keeps you up "
                     "at night?",
         "listen_for": "Operators name the real structural risk faster "
                       "than any desk model; convergence across calls "
                       "is signal."},
    ],
    "former_employee": [
        {"topic": "demand",
         "question": "When you were there, how full was the schedule "
                     "really — and how was utilization measured versus "
                     "reported?",
         "listen_for": "Gap between managed and measured KPIs is a QoE "
                       "finding; 'we counted holds as booked' is a "
                       "restatement risk."},
        {"topic": "labor",
         "question": "Why did you leave, and who else left around the "
                     "same time?",
         "listen_for": "Clustered departures around one leader or one "
                       "policy change locate the org risk precisely."},
        {"topic": "stickiness",
         "question": "Which referrer or payer relationships were held "
                     "personally by specific people — and are those "
                     "people still there?",
         "listen_for": "Relationship-held revenue is key-person risk "
                       "the CIM never discloses."},
        {"topic": "growth",
         "question": "Of the growth initiatives pitched while you were "
                     "there, which actually shipped and which quietly "
                     "died?",
         "listen_for": "The de-novo / expansion track record — the "
                       "base-rate for the growth plan you're "
                       "underwriting."},
        {"topic": "risks",
         "question": "If a buyer asked you 'what will surprise me in "
                     "year one?', what would you tell them?",
         "listen_for": "Specifics with names and dates are gold; "
                       "vague griping is departure bias — discard."},
        {"topic": "competition",
         "question": "Which competitor did leadership actually worry "
                     "about, and what did they do about it?",
         "listen_for": "Internal threat ranking versus the CIM's "
                       "competitive section — divergence is the story."},
    ],
    "site_administrator": [
        {"topic": "demand",
         "question": "How do your discharge planners choose among "
                     "providers in this category — formal list, "
                     "protocol, or habit?",
         "listen_for": "Habit-driven channels are durable but "
                       "unmanaged; formal lists can be re-bid against "
                       "the target overnight."},
        {"topic": "risks",
         "question": "Is your system evaluating bringing this service "
                     "in-house or into a preferred partnership?",
         "listen_for": "In-housing by the channel owner is the "
                       "existential version of customer concentration."},
        {"topic": "stickiness",
         "question": "What does the target do operationally that makes "
                     "your team's discharges easier or harder?",
         "listen_for": "Acceptance speed, weekend coverage, intake "
                       "responsiveness — the operational moat, or its "
                       "absence."},
        {"topic": "competition",
         "question": "Which alternative providers have pitched you in "
                     "the last year, and did any get added?",
         "listen_for": "Live measure of how contested the channel is "
                       "and how high the entry bar actually sits."},
        {"topic": "demand",
         "question": "How are your discharge volumes in the relevant "
                     "service lines trending?",
         "listen_for": "The upstream volume faucet for the target's "
                       "referral-dependent revenue."},
    ],
    "patient_advocate": [
        {"topic": "demand",
         "question": "When families in your community need this service, "
                     "what's the actual experience of getting access — "
                     "wait times, distance, denials?",
         "listen_for": "Unmet-demand evidence supports the growth "
                       "thesis; 'plenty of slots everywhere' undercuts "
                       "the capacity-constrained story."},
        {"topic": "pricing_reimbursement",
         "question": "What do patients end up paying out of pocket, and "
                     "where does affordability actually break?",
         "listen_for": "Out-of-pocket burden is the bad-debt and "
                       "patient-pay risk in human terms."},
        {"topic": "stickiness",
         "question": "Do patients in your community distinguish between "
                     "providers of this service? On what basis?",
         "listen_for": "Brand reality check — most provider 'brands' "
                       "don't exist for patients; access and referral "
                       "decide."},
        {"topic": "risks",
         "question": "What complaints about providers in this category "
                     "reach you most often?",
         "listen_for": "Recurring complaint themes (billing surprise, "
                       "staffing churn) preview reputational and "
                       "regulatory exposure."},
    ],
    "industry_expert": [
        {"topic": "pricing_reimbursement",
         "question": "Of the reimbursement changes proposed for this "
                     "sector, which will actually finalize, and on what "
                     "timeline?",
         "listen_for": "Sorts the regulatory page's PROPOSED items "
                       "into 'moving' vs 'perennial' — with dates, "
                       "not vibes."},
        {"topic": "risks",
         "question": "Where has enforcement attention in this sector "
                     "actually gone in the last 18 months?",
         "listen_for": "Enforcement follows patterns; if the target's "
                       "billing model matches the pattern, that's a "
                       "diligence workstream, not a footnote."},
        {"topic": "growth",
         "question": "Which markets or models in this sector are "
                     "overbuilt already, and which still have room?",
         "listen_for": "Cross-checks the whitespace math with someone "
                       "who's watched the last three roll-ups end."},
        {"topic": "competition",
         "question": "Who are the consolidators actually paying up in "
                     "this sector right now, and what are they paying "
                     "for?",
         "listen_for": "The exit-multiple assumption tested against "
                       "live buyer behavior."},
        {"topic": "demand",
         "question": "What's the strongest argument that this sector's "
                     "demand growth disappoints — and how would we see "
                     "it early?",
         "listen_for": "A good expert can argue the bear case with "
                       "leading indicators; 'demand only grows' is a "
                       "lens failure, swap the expert."},
    ],
}


# Compliance-safe opening + closing, shared across lenses. These are
# the standard expert-network rules; stating them in the guide keeps
# every call inside process-integrity lines.
_OPENING: List[str] = [
    "Introduce yourself and the purpose at the level agreed with the "
    "network: an investor evaluating the sector (never name the "
    "target unless cleared, and never name the process).",
    "Confirm the compliance ground rules out loud: no material "
    "non-public information, nothing covered by an NDA or duty to a "
    "current employer, no confidential pricing from current "
    "negotiations.",
    "Confirm their relevant vantage point and date-stamp it: role, "
    "geography, and when they last had direct exposure ('as of "
    "when?' attaches to every answer).",
]

_CLOSING: List[str] = [
    "Ask the open question: 'What should I have asked that I "
    "didn't?' — the best finding on many calls.",
    "Ask for referrals: 'Who sees a different side of this than you "
    "do?' Two names per call keeps the program pipeline full.",
    "Immediately after the call, write the structured note: 2–3 "
    "findings, each tagged to a thesis hypothesis as SUPPORTS / "
    "CONTRADICTS / NEW QUESTION, with the speaker's vantage point "
    "and date-stamp. An untagged call note is color, not evidence.",
]


def build_call_guide(stakeholder_key: str,
                     deal_name: str = "") -> Optional[Dict[str, Any]]:
    """Assemble the printable guide for one lens: opening script,
    questions grouped in CDD-topic order, closing asks. Returns None
    for an unknown lens — never a fabricated generic guide."""
    s = stakeholder(stakeholder_key)
    if s is None:
        return None
    bank = QUESTION_BANK.get(stakeholder_key, [])
    grouped: List[Dict[str, Any]] = []
    for topic in CDD_TOPICS:
        qs = [q for q in bank if q["topic"] == topic]
        if qs:
            grouped.append({"topic": topic, "label": topic_label(topic),
                            "questions": qs})
    return {
        "stakeholder": s,
        "deal_name": deal_name,
        "opening": list(_OPENING),
        "sections": grouped,
        "question_count": len(bank),
        "closing": list(_CLOSING),
    }


def program_plan(total_calls: int = 20) -> List[Dict[str, Any]]:
    """Scale the per-lens recommended counts to ``total_calls``.

    Largest-remainder apportionment so the plan always sums exactly
    to the target; every lens keeps at least 1 call when the program
    is big enough (>= number of lenses), because a zero-call lens is
    a designed-in blind spot."""
    total_calls = max(0, int(total_calls))
    base_total = sum(s["target_calls"] for s in STAKEHOLDER_TYPES)
    if total_calls == 0 or base_total == 0:
        return [{"stakeholder": s, "calls": 0, "share_pct": 0.0}
                for s in STAKEHOLDER_TYPES]
    raw = [(s, total_calls * s["target_calls"] / base_total)
           for s in STAKEHOLDER_TYPES]
    plan = [{"stakeholder": s, "calls": int(math.floor(r)),
             "_frac": r - math.floor(r)} for s, r in raw]
    remainder = total_calls - sum(p["calls"] for p in plan)
    for p in sorted(plan, key=lambda p: p["_frac"], reverse=True):
        if remainder <= 0:
            break
        p["calls"] += 1
        remainder -= 1
    if total_calls >= len(STAKEHOLDER_TYPES):
        # Lift any zero-call lens to 1, taking from the largest counts.
        for p in plan:
            if p["calls"] == 0:
                donor = max(plan, key=lambda q: q["calls"])
                if donor["calls"] > 1:
                    donor["calls"] -= 1
                    p["calls"] = 1
    for p in plan:
        p.pop("_frac", None)
        p["share_pct"] = round(100.0 * p["calls"] / total_calls, 1)
    return plan


# Coverage statuses, in severity order.
COVERED = "COVERED"
THIN = "THIN"            # exactly one call — single-source evidence
UNCOVERED = "UNCOVERED"  # zero calls — designed-in blind spot


def coverage_read(completed: Dict[str, int],
                  total_calls: int = 20) -> Dict[str, Any]:
    """Honest read of program progress per lens.

    A lens is COVERED only with >=2 completed calls (one human is an
    anecdote); THIN at exactly 1; UNCOVERED at 0. The headline is the
    worst lens, never an average — '85% of calls done' with the payer
    lens at zero is not 85% done."""
    plan = {p["stakeholder"]["key"]: p["calls"]
            for p in program_plan(total_calls)}
    rows: List[Dict[str, Any]] = []
    for s in STAKEHOLDER_TYPES:
        done = max(0, int(completed.get(s["key"], 0) or 0))
        target = plan.get(s["key"], 0)
        if done >= 2:
            status = COVERED
        elif done == 1:
            status = THIN
        else:
            status = UNCOVERED
        rows.append({"stakeholder": s, "done": done, "target": target,
                     "status": status})
    total_done = sum(r["done"] for r in rows)
    uncovered = [r for r in rows if r["status"] == UNCOVERED]
    thin = [r for r in rows if r["status"] == THIN]
    findings: List[str] = []
    if total_done == 0:
        findings.append("No calls logged yet — the program plan below "
                        "is the starting allocation.")
    else:
        if uncovered:
            names = ", ".join(r["stakeholder"]["label"] for r in uncovered)
            findings.append(
                f"Blind spot{'s' if len(uncovered) > 1 else ''}: "
                f"{names} — zero calls. Whatever this lens would have "
                f"said is absent from the work product, not neutral.")
        if thin:
            names = ", ".join(r["stakeholder"]["label"] for r in thin)
            findings.append(
                f"Single-source: {names} — one call is an anecdote; a "
                f"second voice is needed before anything from this "
                f"lens carries weight in the memo.")
        if not uncovered and not thin:
            findings.append(
                "Every lens has two or more voices — findings can be "
                "triangulated across stakeholder types.")
    return {
        "rows": rows,
        "total_done": total_done,
        "total_target": sum(plan.values()),
        "findings": findings,
        "complete": (total_done > 0 and not uncovered and not thin),
    }
