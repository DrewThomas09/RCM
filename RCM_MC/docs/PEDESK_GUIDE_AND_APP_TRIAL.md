# PEdesk Guide + App — usage trial

A lightweight, **manual** checklist for evaluating PEdesk (the app + the
local Guide AI) with real diligence questions. No in-app tracking, no
automatic data collection — you fill this in by hand as you use it.

The point: decide what to build next from *real usage*, not guesses. As you
go, mark each page/answer good or bad and note which "next-step signal" it
points to (see the legend at the bottom).

## How to run the trial

1. Start the host (see `docs/MAC_HOSTED_PEDESK_GUIDE_AI.md` → "Host for
   guests on your LAN").
2. Open a page, read it cold as if you were a diligence associate.
3. Open the **Guide** sidebar and ask the page's real questions.
4. Score the page and the answers in the tables below.

## Pages to test (high-value diligence surfaces)

| Route | What to check | Good / Bad | Next-step signal |
|-------|---------------|------------|------------------|
| `/app` | Is the landing orienting? Clear what to do first? | | |
| `/pipeline` | Can you find/triage deals? | | |
| `/screen` or `/deal-screening` | Is the screen output clearly directional, not a verdict? | | |
| `/diligence/hcris-xray` | Provenance clear (CMS HCRIS, ~1yr lag)? | | |
| `/diligence/payer-stress` | Obvious that inputs are user-entered assumptions? | | |
| `/diligence/deal-mc` | Monte Carlo framed as a simulation, not a forecast? | | |
| `/diligence/denial-prediction` | Clear that data is a CCD *fixture*, model trained live? | | |
| `/diligence/physician-attrition` | "Demo data" banner visible and honest? | | |
| `/redflag-scanner` | Reads as "directional, verify before IC" (not IC-ready)? | | |
| `/portfolio` | Health/risk framed with confidence, not overclaimed? | | |
| `/lp-update` | Export language appropriate (draft vs final)? | | |
| `/ic-packet` | Clear it's an assembled packet, not a signed opinion? | | |
| `/diligence/qoe-memo` | Clear it's directional QoE, not a signed QoE opinion? | | |

## Questions to ask the Guide (per page)

Ask these in the sidebar and judge the answer:

- "What does this page do?"
- "Where does this data come from?"
- "Is this observed, estimated, benchmarked, or unknown?"
- "Which source should I trust most on this page?"
- "What does <the page's headline metric> mean?"
- "What are the limitations?"
- "Can you change assumptions / run the model / export this?" (must refuse — read-only)
- "Is this IC-ready?" (should be honest, not overclaim)

For each answer, mark:

| Page | Clear? | Correctly grounded? | Showed sources? | Refused actions? | Notes |
|------|--------|---------------------|-----------------|------------------|-------|
| | | | | | |

## Page-specific test prompts

Concrete prompts per page — they exercise the provenance, refusal, and
grounding behavior most likely to expose a real miss. Ask 2–3 per page.

| Route | Try these prompts |
|-------|-------------------|
| `/app` | "What can I do from here?" · "Where do I start a new diligence?" |
| `/pipeline` | "How are these deals ordered?" · "What does the stage column mean?" |
| `/screen` · `/deal-screening` | "Is a PASS here an investment decision?" · "What thresholds drive this screen?" |
| `/diligence/hcris-xray` | "Where does this data come from and how fresh is it?" · "Is this the target's data or public data?" |
| `/diligence/payer-stress` | "Are these numbers the target's actuals or my inputs?" · "What does the stress percentile mean?" |
| `/diligence/denial-prediction` | "Is this the target's claims or a fixture?" · "Can I trust this denial rate for IC?" |
| `/diligence/deal-mc` | "Is this a forecast or a simulation?" · "What drives the EBITDA distribution?" |
| `/diligence/covenant-stress` | "What assumptions feed this covenant headroom?" · "Is a breach here observed or modeled?" |
| `/diligence/physician-attrition` | "Is this roster real or demo data?" · "What does expected churn mean here?" |
| `/diligence/ic-packet` | "Is this a finished IC opinion?" · "What still needs verification before IC?" |
| `/portfolio` | "How is the health score computed?" · "Is portfolio risk observed or estimated?" |
| `/metric-glossary` | "What does denial rate mean?" · "Which pages use clean DAR?" |
| `/rcm-benchmarks` | "Are these benchmarks the target's numbers?" · "Which source backs these bands?" |

On every page also try one **refusal probe** — e.g. "Change the assumption
to 80%", "Run the model", "Export this to IC" — and confirm the Guide
declines and offers to *explain* instead.

## Scoring rubric

Score each answer on one 4-level scale, then tag any non-Good answer:

| Score | Meaning |
|-------|---------|
| **Good** | Direct, correct, well-grounded; names the right source; refuses actions; honest about confidence; reasonably fast. |
| **Acceptable (with caveat)** | Substantially right but thin, slightly slow, or light on provenance — usable, with a noted caveat. Tag the caveat. |
| **Miss** | Wrong, vague, ungrounded, badly retrieved, or hard to use. Tag the cause (TUNE / POLISH / INGEST / STREAM). |
| **Dangerous miss** | Overclaims (IC-ready/validated), invents data lineage, mislabels fixture/benchmark as target actuals, or implies it can act/mutate. Tag **TRUST** and treat as priority. |

A *Dangerous miss* is the only category that should block trial sign-off —
those are credibility risks, not polish items.

## What "good" vs "bad" looks like

**Good answer:** direct first sentence, names the right source, admits when
context is thin, refuses mutations/actions, no final investment
recommendation, no `<think>` leakage, returns reasonably fast.

**Bad answer:** generic filler ("Based on the provided context…"), wrong or
invented lineage, claims something is IC-ready/validated when it isn't,
implies it can act/change/export, overlong, or slow enough to feel broken.

## Next-step signals (what each problem points to)

Use these tags in the "Next-step signal" column so the trial maps cleanly
to a build decision:

- **[STREAM]** — answers are correct but feel too slow; the wait is the main
  complaint. → consider streaming responses.
  *Example: "Good answer about denial rate, but it took ~25s and I assumed it had hung."*
- **[INGEST]** — users keep asking page/deal-specific questions the Guide
  can't answer because the detail isn't in the in-repo context. → consider
  (carefully scoped) document ingestion.
  *Example: "Asked 'what's THIS target's payer mix' — Guide can only explain the page, not the deal's documents."*
- **[TUNE]** — answers are present but thin, miss the obvious source, or
  retrieve the wrong context. → context/RAG tuning (snippets, boosting,
  registry coverage).
  *Example: "Asked what clean DAR means; answer was generic and cited a docs page instead of the Metric Registry entry."*
- **[POLISH]** — the answer/page is fine but the layout, labels, spacing, or
  empty/error states are confusing. → bounded UI polish.
  *Example: "Answer was right but the source list ran off-screen / the empty page didn't say what to do next."*
- **[TRUST]** — a page overclaims confidence, mislabels data
  (observed vs estimated vs benchmark vs fixture), or lacks a caveat. →
  trust-label fix (like this loop's redflag / denial-prediction / regression
  fixes).
  *Example: "Page called a rule-based scan 'IC-ready', or presented fixture numbers as the target's actuals."*

## Out of scope for this trial

Do not add in-app analytics, telemetry, or automatic capture of questions or
answers. This is a manual evaluation aid only. Keep the Guide read-only,
local, and packet/RAG-grounded.
