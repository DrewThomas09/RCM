# PEdesk Deal Lifecycle Model

**Status:** proposal for review (Phase 5). No behavior is implemented here.

The product should make the deal lifecycle obvious: where a target is born,
how it becomes an opportunity, how it is diligenced, and how it becomes a
portfolio holding. Each stage owns **one data object** and is served by **one
nav section**.

---

## Lifecycle stages

| # | Stage | Question answered | Nav section | Data object | Pages |
|---|---|---|---|---|---|
| 1 | **Discover** | "What targets exist?" | Source | *CMS provider* (market) | Target Screener · CMS Sector Screeners · Thesis Workspace |
| 2 | **Evaluate** | "Is this target interesting?" | Source → Diligence | *target candidate* | CMS Provider X-Ray · HCRIS X-Ray · Deal Quality Score |
| 3 | **Promote** | "Make it an opportunity." | Pipeline | *opportunity (USER-DEAL)* | New Deal / Import Deal / "Promote to Pipeline" |
| 4 | **Manage** | "Where is it in our process?" | Pipeline | *opportunity* | Deal Pipeline · stage tracker · next actions |
| 5 | **Diligence** | "Should we buy, at what price/risk?" | Diligence | *deal workspace* | Deal Screening/Thesis · IC Packet · EBITDA Bridge · Deal Risk · Payer Analysis |
| 6 | **Decide** | "Close or pass." | Pipeline | *opportunity (closed/passed)* | Pipeline closed/pass records |
| 7 | **Monitor** | "How is the asset doing?" | Portfolio / Home | *portfolio holding (USER-PORT)* | Portfolio Map · Heatmap · Active Holdings · LP Update · Command Center |

**Data objects, in order:** `CMS provider` → `target candidate` →
`opportunity` → `deal workspace` → `portfolio holding`. A clean product makes
each transition an explicit, named action.

---

## Promotion actions (the transitions)

| Transition | Action (button) | Where it should live | Exists today? |
|---|---|---|---|
| CMS provider → target candidate | **"Add to targets"** | Target Screener, X-Ray pages | ⚠️ partial / unclear |
| target candidate → opportunity | **"Promote to Pipeline"** | Deal Quality Score, X-Ray | ❌ missing/implicit |
| opportunity → diligence workspace | **"Open diligence"** | Deal Pipeline row | ⚠️ partial |
| opportunity → portfolio holding | **"Mark as acquired / Add holding"** | Pipeline (on close) | ❌ missing |
| import external target/deal | **"Import Deal"** | Source / Pipeline | ✅ exists (`/deals` New Deal — name unclear) |

**Missing actions today** (the gaps that make the product feel disconnected):
- No explicit **"Promote to Pipeline"** from a screener/X-Ray result.
- No explicit **"Mark as acquired → portfolio holding"** transition.
- The **"New Deal"** entry point's verb is ambiguous (create opportunity vs.
  import target vs. add holding).

---

## "New Deal" disambiguation (proposal)

The single "New Deal" action conflates three jobs. Split/rename by intent:

| If the user wants to… | Name it | Creates |
|---|---|---|
| capture a market target to watch | **Add Target** | target candidate |
| bring in an external/known deal | **Import Deal** | opportunity (USER-DEAL) |
| start a fresh opportunity record | **Create Opportunity** | opportunity (USER-DEAL) |
| record an owned asset | **Add Portfolio Holding** | portfolio holding (USER-PORT) |

---

## Honesty constraints at each stage

- **Pipeline** shows only real/user-entered opportunity records. If none:
  *"No deals in the pipeline yet — promote a target from Source, or Import a
  Deal."* Never backfill with corpus deals.
- **Portfolio** shows only real holdings. If none: *"No active portfolio
  records loaded yet."* The 655-deal corpus is **not** portfolio.
- **Source / Diligence** clearly read **CMS public data** (market), labeled as
  such; X-Ray outputs stay "association/benchmark, not a verdict."

---

## How this maps to the proposed nav

`Source = stages 1–2 · Pipeline = stages 3–4,6 · Diligence = stage 5 ·
Portfolio/Home = stage 7 · Research = the corpus/reference that informs all
stages but owns none of the user's deal objects.`

This is the spine the IA audit (`PEDESK_PRODUCT_IA_AUDIT.md`) reorganizes the
nav around.
