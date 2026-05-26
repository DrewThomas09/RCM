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
- #849–#859 (11 PRs, all green-merged + deployed): scorecard/ledger, payer-stress,
  hcris-xray, provider-xray, RAG-indexer fix, target-screener, bear-case,
  data-honesty guards, model-page Guide contexts, predictive-screener,
  market-intel header.

### Deployed SHAs
- 878fcb65 (loop start) → fbc3a50f (after #854); /healthz ok throughout

### Pages improved
- Payer Stress (#850) — source/purpose header + management-questions panel
- HCRIS X-Ray (#851) — source/purpose header + "What this means for IC" panel
- Provider/CMS X-Ray (#852) — source/purpose header band
- Target Screener (#854) — header + next-actions + real geo-suite link
- Bear Case (#855) — honesty source/purpose header on both render paths
- Guide/RAG (#853) — restored 13 dropped curated cards (9→22 indexed)
- ML audit — denial-prediction + deal-mc verified already honest (no invented model performance); predictor engine mature (RidgeCV/LOO + heteroscedasticity/nonlinearity/VIF/Cook's-D diagnostics). Log-transform diagnostic flagged as a careful future PR, not a 180s tick.

### Charts improved
- (none yet)

### Guide contexts added
- (none yet)

### Data sources added
- (none yet)

### Synthetic / DATA REQUIRED pages fixed
- (none yet)

### Next 10 tasks (refreshed after #854)
1. Cost Structure (/cost-structure) — source/purpose header + caveats + next-actions.
2. Debt Service (/debt-service) — source/purpose header + management questions.
3. Reference-based Pricing (/ref-pricing) — header + source-confidence + next-actions.
4. CMS APM tracker (/cms-apm) + Payer Rate Trends (/payer-rate-trends) — header + caveats.
5. Risk Workbench + Physician EU (DATA REQUIRED) — confirm/polish activation path + import template + management request list + evidence checklist.
6. Drug Shortage / Risk Adjustment / Provider Network — header + interpretation + next-actions.
7. Predictive Screener + Deal Screening (YELLOW) — honest model-status label + activation path.
8. Market Intelligence / Industry — source-confidence strips + Guide + validation panels.
9. Data-honesty regression guards doc + validators (no unlabeled illustrative tables, no fake trends, no unknown-source Diligence/Tools page).
10. Guide context for newly-headed pages (payer-stress, target-screener, bear-case) + suggested questions.

---

## Tick log
- **2026-05-26T04:18:53Z** — loop_start. Synced main (878fcb65). Open PRs are stale pre-loop (#6/#17/#18/#19/#25/#579/#580/#639 — not touched; #579/#580 forbidden). Inventoried ~76 routes across Diligence/Tools/X-Ray/Market/Industry/provider/screener. Building scorecard + this ledger as PR #1.
