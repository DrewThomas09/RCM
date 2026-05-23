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
- **[INGEST]** — users keep asking page/deal-specific questions the Guide
  can't answer because the detail isn't in the in-repo context. → consider
  (carefully scoped) document ingestion.
- **[TUNE]** — answers are present but thin, miss the obvious source, or
  retrieve the wrong context. → context/RAG tuning (snippets, boosting,
  registry coverage).
- **[POLISH]** — the answer/page is fine but the layout, labels, spacing, or
  empty/error states are confusing. → bounded UI polish.
- **[TRUST]** — a page overclaims confidence, mislabels data
  (observed vs estimated vs benchmark vs fixture), or lacks a caveat. →
  trust-label fix (like this loop's redflag / denial-prediction / regression
  fixes).

## Out of scope for this trial

Do not add in-app analytics, telemetry, or automatic capture of questions or
answers. This is a manual evaluation aid only. Keep the Guide read-only,
local, and packet/RAG-grounded.
