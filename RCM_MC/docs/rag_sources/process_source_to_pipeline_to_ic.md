# Process: Source → Pipeline → Diligence → IC

How a deal moves through PEdesk from market discovery to investment committee,
so the Guide can answer "what's the workflow", "when do I promote", "what
happens at each stage", and "where do I see the next step".

## The end-to-end journey

```
SOURCE                  PIPELINE / DILIGENCE                     IC
─────────               ────────────────────────                 ──
/target-screener  →  promote  →  /diligence/checklist  →  /diligence/ic-packet  →
/source                          /diligence/hcris-xray         /ic-memo
/screen                          /diligence/bridge-audit       /exports
/predictive-screener             /diligence/payer-stress
                                 /diligence/risk-workbench
                                 /diligence/denial-prediction
                                 /diligence/physician-eu
                                 (plus the 60+ other diligence surfaces)
```

Once IC clears, the deal moves into **post-close**:

```
POST-CLOSE              ONGOING                       EXIT
──────────              ────────                      ────
/portfolio/monitor  →  /alerts  →  /escalations  →  /diligence/exit-timing  →
/watchlist                                          /diligence/deal-autopsy
/my/<owner>                                         /lp-update
```

## Stage by stage

### 1. Source (market discovery)

Operates on the public CMS / provider universe. Target candidates are not
yet tracked deals — they're entries in the corpus.

- `/target-screener` is the 6-screen workbench (Main / Inspector /
  Columns / Compare / Just-missed / Saved). See the
  `target_screener_workbench.md` card.
- `/source` runs a thesis-driven sourcing (matches a target profile to
  the universe).
- `/screen` runs a filter-based hospital screener.
- `/predictive-screener` runs the trained model against the corpus.

Output: a shortlist of candidates worth deeper look. Each row has an
`X-Ray` action that jumps to public-data X-Ray (`/diligence/xray`,
`/diligence/hcris-xray`).

### 2. Promote to Pipeline

The act of moving a candidate from "market data" to "your tracked deal".
Promotion creates a row in the SQLite deal store with a unique
`deal_id`, an owner, and an initial stage. From this point the deal has
**user data confidence** — analysis surfaces ALL operate on your live
state, not the public market.

Surfaces:

- `/pipeline` — deal pipeline by stage (sourcing → LOI → diligence → IC
  → close). Promote action lives at `/api/deals/new` (POST).
- `/new-deal/upload` — bulk-promotes via CSV / JSON.

### 3. Diligence

The deal is in the deal store; diligence pages render real per-deal
analysis. Each diligence page has its own narrow purpose:

- `/diligence/checklist` — items + status + owners
- `/diligence/hcris-xray` — close read of HCRIS data (public baseline)
- `/diligence/bridge-audit` — pressure-test EBITDA bridge
- `/diligence/payer-stress` — stress against payer-mix shifts
- `/diligence/risk-workbench` — 9-panel structural-risk panorama
- `/diligence/denial-prediction` — RCM uplift estimator
- `/diligence/physician-eu` — per-provider economics
- `/diligence/exit-timing` — exit-window optimization
- `/diligence/value` — value-creation plan builder
- `/diligence/qoe-memo` — QoE memo assembler
- (60+ more surfaces — see `/diligence/index`)

Output: every page's output flows into the **Deal Analysis Packet** (see
the `analysis_packet.md` card), the single object every IC packet renders
from.

### 4. IC Packet

`/diligence/ic-packet` auto-assembles an investment-committee read for a
deal from the packet:

- Thesis (purpose of the investment)
- Base case (the central return expectation)
- Bear case (what breaks the thesis)
- Comparables (peer benchmarks)
- Exit path (timing + buyer-fit)
- Key partner questions (auto-generated from gaps in the packet)

`/ic-memo` produces the long-form memo.
`/exports` is where the rendered IC packet artifact lives + audit trail.

### 5. Post-close monitoring

Once the deal closes, the workflow shifts from "should we buy" to "are we
realizing the plan":

- `/portfolio/monitor` — daily dashboard with per-deal health score (see
  `health_score_methodology.md`).
- `/alerts` — rule-based signals (covenant trip, EBITDA miss, etc.) — see
  `process_alerts_lifecycle.md`.
- `/escalations` — red alerts open more than N days.
- `/watchlist` — pinned subset of deals.
- `/my/<owner>` — partner-personal dashboard.

### 6. Exit / Wind-down

- `/diligence/exit-timing` — when to start the process.
- `/diligence/deal-autopsy` — retrospective on closed deals.
- `/lp-update` — produce the LP update artifact.
- `/exports` — long-term archive of everything sent to LPs.

## How the Guide should reason about "where am I"

When a partner asks "what should I do next", the answer depends on **where
the deal sits**:

- Market candidate (no `deal_id` yet) → Source stage. Action: review the
  X-Ray, decide whether to promote.
- Promoted but no analysis packet → Pipeline stage. Action: open the
  checklist, prioritise diligence surfaces.
- Packet built but no IC packet → Diligence stage. Action: assemble the
  IC packet.
- IC packet exists → Investment-committee stage. Action: schedule IC,
  cite the analysis.
- Closed deal → Post-close. Action: watch `/portfolio/monitor` for
  health-score regressions.

The `/methodology` page documents the full workflow; this card is the
RAG-readable summary.

## Why this matters for the Guide

Many partner questions hide a workflow context. "How risky is this
deal?" means something different at sourcing (HCRIS X-Ray + risk
workbench) vs post-close (alerts + health score). The Guide should
infer the stage from the surface the partner is on and answer
accordingly.
