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
- #849 scorecard+ledger · #850 payer-stress · #851 hcris-xray · #852 provider-xray
- #853 RAG indexer fix · #854 target-screener · #855 bear-case header

### PRs merged
- #849–#869 (all green-merged + deployed). First sweep (#849–859): scorecard/
  ledger, payer-stress, hcris-xray, provider-xray, RAG-indexer fix,
  target-screener, bear-case, data-honesty guards, model-page Guide contexts,
  predictive-screener, market-intel header. Header/guard sweep (#860–869):
  scorecard re-score, guard expansion, State-Comparison magnitude bars, and
  source/purpose headers for covenant-stress, bridge-audit, exit-timing,
  counterfactual, management-scorecard, deal-autopsy, comparable-outcomes.
  **Regression guard now protects 25 analyzer pages** (incl. regulatory-calendar, #870).

### Deployed SHAs
- 878fcb65 (loop start) → 698b3f80 (after #885); /healthz ok throughout (37 deploys)

### Honesty-header contract (test_diligence_source_purpose_headers — 32 pages)
Every analytic Diligence/Market/Source page now declares its data basis via
ck_source_purpose / illustrative / DATA REQUIRED, guarded against regression.
Added in the #863–#885 sweep: covenant-stress, bridge-audit, exit-timing,
counterfactual, management-scorecard, deal-autopsy, comparable-outcomes,
regulatory-calendar, compare, thesis-pipeline, ic-packet, sponsor-detail,
ic-memo, market-data/state (+ the earlier payer-stress/hcris-xray/provider-xray/
target-screener/predictive-screener/market-intel/cost-structure/debt-service/
ref-pricing/cms-apm/payer-rate-trends/drug-shortage/risk-adjustment/provider-network).

### ML predictor (the original ask)
Ridge predictor now reports target skewness + a log-transform advisory (#871),
threaded through PredictedMetric → packet JSON (#879) → a visible workbench
advisory chip + tooltip (#880). Advisory-only; never alters the fit. Confirmed
weighting (weighted-median) + clustering modules + heteroscedasticity/
nonlinearity/VIF/Cook's-D diagnostics already existed.

### Extra guards / fixes
- RAG indexer prioritizes curated Guide cards (#853, 9→22 indexed).
- Licensed-data provenance chips registered + guarded (#881, #882) — were
  silently empty on Industry / Market-Intel-Geo.

### Pages improved
- Payer Stress (#850) — source/purpose header + management-questions panel
- HCRIS X-Ray (#851) — source/purpose header + "What this means for IC" panel
- Provider/CMS X-Ray (#852) — source/purpose header band
- Target Screener (#854) — header + next-actions + real geo-suite link
- Bear Case (#855) — honesty source/purpose header on both render paths
- Guide/RAG (#853) — restored 13 dropped curated cards (9→22 indexed)
- ML audit — denial-prediction + deal-mc verified already honest (no invented model performance); predictor engine mature (RidgeCV/LOO + heteroscedasticity/nonlinearity/VIF/Cook's-D diagnostics). Log-transform diagnostic flagged as a careful future PR, not a 180s tick.

### Charts improved
- State Comparison (#862) — per-row magnitude bars
- State Profile (#872) — rank-position bars
- Metro Markets (#874) + County Explorer (#875) — sorted-column magnitude bars
- (geo-suite inline-bar visual set complete across all 4 table modes)

### Guide contexts added
- bear-case, deal-mc, denial-prediction (#857) — DOCUMENTED, method + honest limits

### Data sources added
- (none new — public anchors already broadly wired; ML log-transform diagnostic added to ridge predictor #871)

### Synthetic / DATA REQUIRED pages fixed
- bear-case, deal-autopsy, comparable-outcomes (illustrative-corpus labels);
  management-scorecard (DATA REQUIRED); predictive-screener (model-estimate label)

### Source/purpose-header contract (regression guard test_diligence_source_purpose_headers — 27 pages)
payer-stress, hcris-xray, provider-xray, bear-case, target-screener,
predictive-screener, market-intel, covenant-lab, bridge-audit, exit-timing,
counterfactual, management-scorecard, deal-autopsy, comparable-outcomes,
regulatory-calendar, market-data/state + data_public: cost-structure,
debt-service, ref-pricing, cms-apm, payer-rate-trends, drug-shortage,
risk-adjustment, provider-network.

### Next 10 tasks (refreshed after #875)
1. compare-page / thesis-pipeline source/purpose headers (completeness).
2. Guide suggested-questions audit on the newly-headed pages.
3. Broaden inline visuals to a provider/industry analytic page.
4. Surface the ridge log-transform advisory wherever model diagnostics render (plumbing).
5. Verify market-intel/geo provenance strip + Guide.
6. Re-score scorecard with the header-contract coverage.
7. Risk Workbench / Physician EU evidence-checklist depth.
8. Tools index honesty-dot accuracy pass.
9. Add more curated RAG source cards for recently-headed pages.
10. Periodic full-suite regression sweep (sanity, already clean at 682 touched-surface tests).

---

## Tick log
- **2026-05-26T04:18:53Z** — loop_start. Synced main (878fcb65). Open PRs are stale pre-loop (#6/#17/#18/#19/#25/#579/#580/#639 — not touched; #579/#580 forbidden). Inventoried ~76 routes across Diligence/Tools/X-Ray/Market/Industry/provider/screener. Building scorecard + this ledger as PR #1.
