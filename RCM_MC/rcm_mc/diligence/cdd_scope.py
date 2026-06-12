"""CDD scope levels — how deep a commercial due diligence should go.

A CDD is not one product: the same workstreams run at four depths
depending on where the deal stands. Scoping wrong in either direction
is expensive — a full-scope build at indicative-bid stage burns fee
budget on a deal that may die in the process, and a desktop screen at
exclusivity leaves the IC underwriting unverified claims.

This module is the UI-free core:

- :data:`CDD_LEVELS` — the four standard engagement depths (desktop
  screen, red-flag CDD, full-scope CDD, confirmatory/bring-down),
  each with when to use it, duration stated as MARKET CONVENTION
  (not a quote), team shape, the decision it supports, and the
  deliverable.
- :data:`WORKSTREAMS` — the nine CDD workstreams, each mapped to the
  platform surface that executes it (the page doubles as the
  execution hub for a scoped engagement).
- :data:`DEPTH_MATRIX` — workstream × level depth (NONE / DESKTOP /
  TARGETED / FULL), monotone non-decreasing from L1 through L3 by
  construction (tested): a deeper level never does LESS of a
  workstream. L4 is confirmatory, so it re-narrows deliberately.
- :func:`recommend_level` — deterministic stage/familiarity/deal-type
  → level with the reasoning stated (a scoping aid, not a rule).
- :func:`level_task_list` — the concrete task list for a level
  (feeds the CSV export).
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

# Depth grades, in increasing order.
NONE = "NONE"
DESKTOP = "DESKTOP"
TARGETED = "TARGETED"
FULL = "FULL"
DEPTHS = (NONE, DESKTOP, TARGETED, FULL)


CDD_LEVELS: List[Dict[str, Any]] = [
    {
        "key": "l1",
        "label": "L1 · Desktop screen",
        "when": "Pre-IOI / teaser stage — deciding whether the deal "
                "deserves a bid at all, often across several "
                "simultaneous teasers.",
        "duration": "2–5 working days (market convention)",
        "team": "One analyst-day cadence; no external spend beyond "
                "the desk.",
        "decision": "Go / no-go on submitting an indicative bid.",
        "deliverable": "A 2–3 page screen memo: market size sanity, "
                       "obvious structural red flags, the three "
                       "questions a bid would have to answer.",
        "calls": 2,
        "note": "No primary research beyond at most two calibrating "
                "network calls — the desk does the work at this level.",
    },
    {
        "key": "l2",
        "label": "L2 · Red-flag CDD",
        "when": "Indicative bid in, process letter received — limited "
                "access, competing buyers, fee budget at risk if the "
                "process is lost.",
        "duration": "1–2 weeks (market convention)",
        "team": "Lean: one workstream lead + analyst; expert network "
                "opened.",
        "decision": "Proceed to a binding bid — and at what price "
                    "adjustment for what's now known.",
        "deliverable": "A red-flag report: the 3–5 thesis-critical "
                       "claims independently checked, kill-risks "
                       "named, the full-scope plan priced.",
        "calls": 8,
        "note": "Kill-risk focus by design: verify only what could "
                "change the bid, defer what merely refines it.",
    },
    {
        "key": "l3",
        "label": "L3 · Full-scope CDD",
        "when": "Exclusivity / LOI signed — full data-room access, "
                "the IC memo will rest on this work.",
        "duration": "3–6 weeks (market convention)",
        "team": "Full: workstream leads across market / competition / "
                "customers / pricing; the complete call program.",
        "decision": "The investment-committee underwrite: growth, "
                    "share, pricing and risk assumptions with "
                    "evidence behind each.",
        "deliverable": "The full CDD report with numbered exhibits, "
                       "the call-program evidence base, and the "
                       "model assumptions tied to sources.",
        "calls": 20,
        "note": "Every workstream runs to depth; the red-flag "
                "findings from L2 are re-based, not re-used.",
    },
    {
        "key": "l4",
        "label": "L4 · Confirmatory / bring-down",
        "when": "Post-IC, pre-close — confirming nothing material "
                "moved since the report; supporting SPA and "
                "financing Q&A.",
        "duration": "1–2 weeks alongside legal close (market "
                    "convention)",
        "team": "The L3 leads on call; no new workstreams opened.",
        "decision": "Close as underwritten, or reopen a specific "
                    "assumption with the seller.",
        "deliverable": "A bring-down memo: what changed since the "
                       "report date, callback notes, and answers "
                       "into the financing process.",
        "calls": 4,
        "note": "Deliberately narrow: re-verify movement, don't "
                "re-run the study. New questions route back to the "
                "L3 owner.",
    },
]

_LEVEL_BY_KEY: Dict[str, Dict[str, Any]] = {
    lv["key"]: lv for lv in CDD_LEVELS
}


def level(key: str) -> Optional[Dict[str, Any]]:
    return _LEVEL_BY_KEY.get(key)


# ── Workstreams, each mapped to its executing surface ───────────────

WORKSTREAMS: List[Dict[str, str]] = [
    {"key": "market_sizing", "label": "Market sizing (TAM/SAM/SOM)",
     "surface": "/diligence/tam-sam",
     "surface_label": "TAM / SAM Builder"},
    {"key": "demand_drivers", "label": "Demand & demographics",
     "surface": "/market-intel/geo",
     "surface_label": "Geographic Market Intel"},
    {"key": "competitive_landscape", "label": "Competitive landscape",
     "surface": "/diligence/hcris-xray",
     "surface_label": "HCRIS X-Ray (local market panel)"},
    {"key": "target_position", "label": "Target screening & position",
     "surface": "/target-screener",
     "surface_label": "Target Screener"},
    {"key": "voice_of_customer", "label": "Voice of customer (calls)",
     "surface": "/diligence/expert-calls",
     "surface_label": "Expert-Call Program"},
    {"key": "claims_crosscheck", "label": "Management-claim cross-check",
     "surface": "/diligence/cim-crosscheck",
     "surface_label": "CIM Cross-Check"},
    {"key": "pricing_reimbursement", "label": "Pricing & reimbursement",
     "surface": "/market-rates",
     "surface_label": "Market Rates"},
    {"key": "regulatory", "label": "Regulatory & policy exposure",
     "surface": "/diligence/regulatory-calendar",
     "surface_label": "Regulatory Calendar"},
    {"key": "synthesis", "label": "Synthesis & IC output",
     "surface": "/diligence/ic-packet",
     "surface_label": "IC Packet"},
]

_WS_BY_KEY = {w["key"]: w for w in WORKSTREAMS}


# Depth per workstream per level. L1→L3 must be monotone
# non-decreasing (a deeper engagement never does less); L4 narrows
# deliberately (confirmatory).
DEPTH_MATRIX: Dict[str, Dict[str, str]] = {
    "market_sizing":         {"l1": DESKTOP, "l2": DESKTOP,
                              "l3": FULL,    "l4": NONE},
    "demand_drivers":        {"l1": DESKTOP, "l2": DESKTOP,
                              "l3": FULL,    "l4": NONE},
    "competitive_landscape": {"l1": DESKTOP, "l2": TARGETED,
                              "l3": FULL,    "l4": DESKTOP},
    "target_position":       {"l1": DESKTOP, "l2": TARGETED,
                              "l3": FULL,    "l4": NONE},
    "voice_of_customer":     {"l1": NONE,    "l2": TARGETED,
                              "l3": FULL,    "l4": TARGETED},
    "claims_crosscheck":     {"l1": NONE,    "l2": TARGETED,
                              "l3": FULL,    "l4": TARGETED},
    "pricing_reimbursement": {"l1": DESKTOP, "l2": TARGETED,
                              "l3": FULL,    "l4": DESKTOP},
    "regulatory":            {"l1": DESKTOP, "l2": TARGETED,
                              "l3": FULL,    "l4": TARGETED},
    "synthesis":             {"l1": DESKTOP, "l2": TARGETED,
                              "l3": FULL,    "l4": TARGETED},
}


# What the workstream concretely does at each non-NONE depth. Keyed
# (workstream, depth); the task list renders these.
_TASKS: Dict[str, Dict[str, str]] = {
    "market_sizing": {
        DESKTOP: "Sanity-check the stated market size against the "
                 "platform's industry catalogue ceiling; note the "
                 "claimed CAGR vs the sector prior.",
        FULL: "Build the bottom-up driver tree (population → "
              "prevalence → treated → addressable revenue) with "
              "sourced steps and scenario presets.",
    },
    "demand_drivers": {
        DESKTOP: "Pull the target geography's demand profile (65+, "
                 "uninsured, income, disease burden) and note where "
                 "it cuts against the growth story.",
        FULL: "Per-county demand model for the actual footprint; "
              "payer-mix drift (MA penetration) quantified into the "
              "revenue assumptions.",
    },
    "competitive_landscape": {
        DESKTOP: "Name the competitors from public registries; state "
                 "concentration (HHI) for the proxy market.",
        TARGETED: "25-mile local-market read on the target's own "
                  "sites: who shares the catchment, radius HHI, "
                  "share-of-radius.",
        FULL: "Full landscape: every local market mapped, supply "
              "build (competitor capacity adds) from competitor "
              "calls, head-to-head win/loss from referrer calls.",
    },
    "target_position": {
        DESKTOP: "Screen the target against the universe: percentile "
                 "position on margin, payer mix, scale.",
        TARGETED: "Peer-band the thesis-critical metrics; flag where "
                  "the target is an outlier its CIM doesn't explain.",
        FULL: "Position fully evidenced: filed-data percentiles + "
              "call-program corroboration on the soft factors "
              "(reputation, stickiness).",
    },
    "voice_of_customer": {
        TARGETED: "A kill-risk call set (~8): referrers + one payer + "
                  "one former employee on the 3–5 claims that could "
                  "change the bid.",
        FULL: "The full 7-lens program (~20 calls) with cadence, "
              "topic triangulation, and every finding logged as "
              "tagged deal-note evidence.",
    },
    "claims_crosscheck": {
        TARGETED: "Cross-check the thesis-critical CIM claims "
                  "(market size, share, margin, payer mix) against "
                  "independent filed-data estimates; red flags only.",
        FULL: "Every quantitative CIM claim cross-checked with "
              "variance flags, claim percentiles, and the variance "
              "memo feeding the call program.",
    },
    "pricing_reimbursement": {
        DESKTOP: "Note the rate environment: the sector's fee-schedule "
                 "trajectory and the obvious rate cliffs.",
        TARGETED: "Target-specific read: where its realized rates sit "
                  "vs market, which payers carry the margin, "
                  "re-contracting exposure named.",
        FULL: "Rate-bridge the projections: payer-by-payer rate "
              "assumptions tied to filed benchmarks and payer-call "
              "evidence.",
    },
    "regulatory": {
        DESKTOP: "Scan the applicable rulemakings for the provider "
                 "type and state; list effective dates inside the "
                 "hold.",
        TARGETED: "The exposure read: which proposed/final rules hit "
                  "this target's economics, sized where the rule "
                  "states it.",
        FULL: "Full environment build: every material federal/state "
              "rule tagged tailwind/headwind with the diligence "
              "implication, expert-validated timelines.",
    },
    "synthesis": {
        DESKTOP: "The screen memo: three findings, three questions, "
                 "a recommendation.",
        TARGETED: "The red-flag report: kill-risks with evidence, "
                  "price-adjustment logic, the full-scope plan.",
        FULL: "The IC-grade CDD report: numbered exhibits, every "
              "assumption sourced, the evidence base attached.",
    },
}


def depth_for(workstream_key: str, level_key: str) -> str:
    return DEPTH_MATRIX.get(workstream_key, {}).get(level_key, NONE)


def level_task_list(level_key: str) -> List[Dict[str, str]]:
    """The concrete tasks for one level — only workstreams the level
    actually runs (NONE rows are omitted, not rendered as 'skip')."""
    if level(level_key) is None:
        return []
    out: List[Dict[str, str]] = []
    for ws in WORKSTREAMS:
        depth = depth_for(ws["key"], level_key)
        if depth == NONE:
            continue
        task = _TASKS.get(ws["key"], {}).get(depth, "")
        out.append({"workstream": ws["label"], "depth": depth,
                    "task": task, "surface": ws["surface"],
                    "surface_label": ws["surface_label"]})
    return out


# ── Recommender ─────────────────────────────────────────────────────

STAGES = ("screen", "bid", "exclusivity", "preclose")
FAMILIARITY = ("new", "adjacent", "known")
DEAL_TYPES = ("platform", "addon")


def recommend_level(stage: str, familiarity: str,
                    deal_type: str) -> Optional[Dict[str, Any]]:
    """Deterministic scoping aid: deal stage anchors the level;
    familiarity and platform-vs-add-on adjust within it. Returns the
    level dict + the reasoning + any adjustment notes; None for an
    invalid input (never a guessed scope)."""
    stage = (stage or "").strip().lower()
    familiarity = (familiarity or "").strip().lower()
    deal_type = (deal_type or "").strip().lower()
    if (stage not in STAGES or familiarity not in FAMILIARITY
            or deal_type not in DEAL_TYPES):
        return None
    notes: List[str] = []
    if stage == "screen":
        key = "l1"
        reason = ("Pre-IOI, the question is whether to bid at all — "
                  "desk work answers it; external spend doesn't.")
        if familiarity == "new" and deal_type == "platform":
            notes.append("New market + platform: add 1–2 calibrating "
                         "expert calls to the screen — the desk alone "
                         "misreads unfamiliar sectors.")
    elif stage == "bid":
        key = "l2"
        reason = ("In a competitive process with limited access, "
                  "scope to kill-risks: verify what could change the "
                  "bid, defer what refines it.")
        if familiarity == "known":
            notes.append("Known market: the red-flag set shrinks to "
                         "target-specific claims — the market view "
                         "carries over from prior work.")
        if deal_type == "addon":
            notes.append("Add-on: weight the call set toward overlap "
                         "and integration (shared referrers, payer "
                         "contract conflicts).")
    elif stage == "exclusivity":
        if deal_type == "addon" and familiarity == "known":
            key = "l2"
            reason = ("Known market, add-on: a full-scope re-build "
                      "duplicates the platform's CDD. Run a red-flag "
                      "scope on the target plus the integration "
                      "overlap, and re-base only what moved.")
        else:
            key = "l3"
            reason = ("Exclusivity is when the IC underwrite gets "
                      "built — every workstream runs to depth with "
                      "the full call program.")
            if familiarity == "new":
                notes.append("New market: start the expert-call "
                             "program in week 1 — booking lead times "
                             "are the critical path.")
    else:  # preclose
        key = "l4"
        reason = ("Post-IC the job is confirmation, not discovery: "
                  "re-verify movement since the report and support "
                  "the close process.")
        notes.append("Anything genuinely new found here routes back "
                     "to the L3 workstream owner — don't bring-down "
                     "a finding that was never made.")
    return {"level": level(key), "reason": reason, "notes": notes}
