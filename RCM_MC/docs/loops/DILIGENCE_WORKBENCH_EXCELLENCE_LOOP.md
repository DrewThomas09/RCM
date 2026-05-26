# PEdesk Diligence Workbench Excellence Loop

A long autonomous product-build loop: make PEdesk's Diligence, Tools, Market
Intelligence, Industry Intelligence, and provider analytics feel like the
best-in-class healthcare-finance analytics workbench — better organized,
better visualized, more source-backed, more useful for deal teams, and more
honest than static competitors. **Intentionally too large to finish in one
run — keep improving until loop_end.**

## Standard for every page
Each page must be exactly one of: **live source-backed analysis** ·
**contextual market/industry intelligence** · **user-data-required (with
activation path)** · **research/reference (with provenance)** · **deferred
(with reason)**. No toy calculators, synthetic dashboards, prototype dumps,
uninterpreted tables, or finished-looking pages with no real source.

Honesty: no fake/synthetic-as-live data, no unsupported benchmark claims, no
invented payer mix / market share / model performance / portfolio / comp /
debt / AR / claims / contract data. Unbacked pages get a label: USER DATA
REQUIRED · DATA REQUIRED · ILLUSTRATIVE · EXPERIMENTAL · RESEARCH REFERENCE ·
DEFERRED WITH REASON.

Do NOT touch: login/auth/session · Caddy · systemd · deploy workflow ·
secrets · .pedesk_prod.env · Ollama/Tailscale · RAG runtime infra ·
destructive migrations · #579/#580.

Auto-merge (after green CI + mergeable): diligence/tools page improvements,
source/purpose headers, DATA REQUIRED panels, import templates, Guide
contexts, RAG source docs, visual/chart/table improvements, data-verification
validators, route audits, source docs, market/industry/provider analytics
enhancements, real-data wiring on existing/public data, tests.

---

## Run ledger

- **loop_start:** 2026-05-26T04:18:53Z
- **loop_end (target):** 2026-05-26T12:18:53Z (loop_start + 8h)
- **start main SHA:** 878fcb65

### PRs opened
- (none yet — scorecard PR in flight)

### PRs merged
- (none yet this loop)

### Deployed SHAs
- 878fcb65 (loop start, /healthz ok)

### Pages improved
- (none yet)

### Charts improved
- (none yet)

### Guide contexts added
- (none yet)

### Data sources added
- (none yet)

### Synthetic / DATA REQUIRED pages fixed
- (none yet)

### Next 10 tasks
1. Create the quality scorecard (this PR) — score Diligence/Tools/X-Ray/Market/Industry/provider/screener routes.
2. Payer Stress (/diligence/payer-stress) — source/purpose header + evidence layout + Guide + next-actions.
3. HCRIS X-Ray — interpretation/"what this means" + IC-question panel + Guide suggested questions.
4. Provider X-Ray (/diligence/xray) — source-purpose header + deal-implications panel.
5. Risk Workbench (DATA REQUIRED) — confirm activation path + import template + Guide context.
6. Physician EU (DATA REQUIRED) — activation path polish + evidence checklist.
7. ML/prediction quality: denial-prediction + deal-mc + model_quality — honesty on model performance, log-transform/weighting/clustering review (no invented metrics).
8. Cost Structure / Debt Service / Ref Pricing — source headers + caveats + next actions.
9. Target Screener — next-action panel + Guide questions + source labels.
10. Data-honesty regression guards doc + validators (no unlabeled illustrative tables, no fake trends).

---

## Tick log
- **2026-05-26T04:18:53Z** — loop_start. Synced main (878fcb65). Open PRs are stale pre-loop (#6/#17/#18/#19/#25/#579/#580/#639 — not touched; #579/#580 forbidden). Inventoried ~76 routes across Diligence/Tools/X-Ray/Market/Industry/provider/screener. Building scorecard + this ledger as PR #1.
