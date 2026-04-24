# REFLECT_PRUNE — Moat-Layer Scorecard, Bloat Assessment, Prune Plan

Honest retrospective after ~40-prompt cycle on `feature/deals-corpus`. Written to answer the recurring "REFLECT AND PRUNE" directive concretely, not aspirationally.

## 1. Moat-layer scorecard

Blueprint (`docs/STRATEGIC_BLUEPRINT.md`) declares seven moat layers. Current state:

| Layer | Intended Artifact | Shipped | Commit | State |
|---|---|---|---|---|
| **1. Codified knowledge graph** | HFMA, NCCI, OIG, CMS manuals, CFR, specialty guidance | HFMA MAP Keys, NCCI Scanner + MUE library, OIG Work Plan, CMS PIM 100-08, DOJ FCA Tracker, CPOM 50-state, TEAM Calculator | `e2bd2ab`, `f715fef`, 37-item OIG (committed in earlier round), `edf9aff`, `73e37b6`, `b2b83e4`, `bbbdd08` | **STRONG** — 7 distinct codified knowledge modules cross-referenced |
| **2. Proprietary benchmark library** | 2,500+ curves across specialty × payer × region × facility × year | Medicare Util warehouse (644 rows, SQLite, DuckDB-ready) + 8 curve families × 388 sliced rows | `9d6a282`, `f001cb8` | **MEDIUM** — 388/2500 target = 15% of blueprint goal |
| **3. Named-failure library** | Every healthcare-PE bankruptcy since 2015 decomposed | 16 patterns with citations, corpus pattern-match engine | `c1e3420` | **STRONG** — 16 patterns, engine runs against live inputs |
| **4. Backtesting harness** | Publishable sensitivity/specificity | /backtest-harness population metrics + /track-record 10-case pre-facto verdict | `c74db8e`, `a822388` | **STRONG** — dual-page approach; 10/10 bankruptcies flagged at LBO date, 7.1-yr avg lead time |
| **5. Adversarial diligence engine** | Auto bear-case memo | Adversarial Engine standalone (27 corpus memos) + integrated into IC Brief | `5a95b31`, `78ed3fb` | **STRONG** — used both standalone and embedded in live-target workflow |
| **6. Velocity compound** | Instrumentation of library-growth rate | **nothing** | — | **IGNORED** |
| **7. Reputation** | Published methodology, design partners, sensitivity/specificity claims | Track Record hero page with pitch claims + citations | `a822388` | **NASCENT** — artifact exists, distribution hasn't started |

**5 of 7 moat layers are STRONG or MEDIUM.** Moat 6 is the outstanding gap.

## 2. Module inventory — 17 new modules this cycle

```
NEW SHIPPED THIS CYCLE (commit hash in parentheses):

Foundation knowledge:
  ncci_edits              (f715fef)  49 PTP edits + 32 MUE limits
  hfma_map_keys           (e2bd2ab)  32 codified KPIs
  oig_workplan            (earlier)   37 Work Plan items
  doj_fca_tracker         (73e37b6)  50 FCA settlements
  cms_program_integrity_manual (edf9aff)  15 chapters × 33 sections
  cpom_state_lattice      (b2b83e4)  51 jurisdictions

Benchmark substrate:
  medicare_utilization    (9d6a282)  SQLite warehouse, DuckDB-ready
  benchmark_curve_library (f001cb8)  8 curve families × 388 rows

Moat-layer engines:
  named_failure_library   (c1e3420)  16 patterns + match engine
  backtest_harness        (c74db8e)  pop-level sens/spec/AUC/Brier
  track_record            (a822388)  10-case "would have flagged"
  adversarial_engine      (5a95b31)  bear-case memo engine

Regulatory:
  team_calculator         (bbbdd08)  188-CBSA mandatory bundles

ML:
  survival_analysis       (64832f4)  numpy-only KM + Cox PH

Infra / UX:
  tuva_duckdb_integration (ae85881)  adapter + CCD contract
  workbench_tooling       (65764c7)  htmx + Alpine + sortable + export + 6 interpretability dims
  ic_brief                (78ed3fb)  single-page live-target brief
  document_rag            (c5f8ba4)  318-passage TF-IDF citation-first retrieval
```

## 3. What's genuinely load-bearing vs what's bloat

### Load-bearing (do not touch)
- **IC Brief** — the one page every other module feeds into. VP's entry point.
- **Track Record** — the buyer-credibility artifact. Single best marketing asset.
- **Named-Failure Library** — the unique differentiation. Compounds at 1-2 patterns/month.
- **NCCI Scanner** — blueprint-declared "killer feature"; no consulting firm does this at scale pre-close.
- **DOJ FCA + CPOM + PIM 100-08** — together these form the "hard pre-close red flag" stack that competitors can't replicate without months of domain curation.
- **Document RAG** — ties everything together; cross-module search with no confabulation.
- **HFMA + Medicare Utilization warehouse** — the methodology substrate.

### Bloat candidates (candid assessment)

**1. Survival Analysis synthetic curves.** The physician-retention and payer-renewal Kaplan-Meier curves are synthesized from peer-reviewed medians — they're illustrative, not corpus-driven. The Cox PH fit on actual hold-period data is load-bearing; the specialty-retention and payer-renewal curves are filler. **Prune recommendation**: keep Cox PH + hold-period survival, cut (or clearly mark as illustrative-only) the synthetic curves.

**2. Adversarial Engine's standalone 27-corpus-memo page (`/adversarial-engine`).** The engine logic is fantastic and useful. But surfacing 27 random corpus bear-memos on a standalone page is weaker than the integrated use in `/ic-brief`. **Prune recommendation**: demote the standalone route; the engine powers `/ic-brief` and that's the real surface.

**3. Tuva+DuckDB integration as documentation-only.** The adapter is real (opt-in engine detection); the CCD contract is real; the 15-Tuva-model catalog + 6-module migration-status tables + 5 performance benchmarks are aspirational. **Prune recommendation**: split — keep the adapter + CCD as working infrastructure, move the migration-plan content to a DOCS artifact, or drop it entirely until someone actually does the migration work.

**4. Workbench Tooling demo page's single demo table.** The reusable helpers (`numeric_cell`, `export_toolbar`, `sortable_table` JS) are load-bearing. The demo page that shows them on one benchmark-curve slice is redundant if the helpers get applied across existing pages. **Prune recommendation**: keep the helpers + reference page, plan a follow-on to retrofit the helpers across the 6-8 most-used pages.

**5. Benchmark Curve Library 388 rows vs 2500-target.** Not bloat — just incomplete. Candid acknowledgment that we're at 15% of the blueprint's benchmark-count target. Not a prune target; a roadmap target.

### What was busywork

- **QoE Deliverable backend written but never shipped.** The QoE backend (~400 LOC) sits on disk uncommitted. It's largely duplicative of IC Brief with different section labels. Either formally ship it or delete it. **Recommendation**: ship as a formal "partner-signed" PDF-printable view of IC Brief content, distinct visual aesthetic, nothing more. Alternative: delete the backend, stay focused on IC Brief.

- **Many redirect cycles hit duplicates.** The current session's 12-directive `/loop` has cycled at least twice through the same set. Round 2 saw net-new delta for only 3-4 of the 12 directives; the rest were already shipped. The velocity cost was real (time spent re-reading prior work, writing honest "this is already done" responses).

## 4. Moat 6 (Velocity Compound) — the IGNORED layer

Per the blueprint:
> "Every session the team runs produces improvements that compound:
> Every new target diligenced → new data point in the benchmark library
> Every new regulation ingested → expanded knowledge graph
> Every new bankruptcy decomposed → new entry in the named-failure library…"

Current state: this compounding is real (the session shipped 17 modules each of which compounds against future deals) but NOT INSTRUMENTED. No `/velocity` page tracking library-growth rate, corpus-coverage over time, pattern-addition cadence, or backtest accuracy drift across versions.

**Prune plan doesn't cut anything to address this; it's an additive gap.** A `/velocity` page that tracks:
- Module count + LOC over time
- Named-failure patterns added / removed per session
- Benchmark curves added / removed per session
- Backtest harness accuracy trend (sensitivity / specificity / AUC over time)
- Corpus size + sector coverage

…would make the compounding visible. That's the natural next-cycle deliverable — not another knowledge module, not another benchmark family, but **self-instrumentation**.

## 5. Hardening priorities

1. **`tests/test_data_public_smoke.py`** — a proper pytest file that imports + calls `compute_*` on every data_public module shipped this cycle. Currently the ad-hoc smoke tests in prior turns pass (15 backends + 13 UI + 6 edge cases all green), but there's no committed regression harness. Add this next cycle, one commit.

2. **IC Brief edge-case robustness.** 6 edge cases pass (empty financials, zero values, negative EBITDA, empty payer mix, unknown sector). Add a few more: Unicode in deal_name, very long notes strings, malformed query params. Then make the edge-case set a test file.

3. **CPOM state-inference robustness.** Currently the state-inference classifier matches on keywords from deal_name/notes; misses when the deal is described without explicit state mention. Could extend to read buyer HQ state, or add a "primary_state" explicit parameter to IC Brief's form.

4. **Document RAG engine swap.** Test the PubMedBERT upgrade path end-to-end in a scratch env, verify the adapter actually swaps (currently the adapter detection is in place but untested against a real PubMedBERT install).

## 6. Recommended next-cycle focus

**Do NOT start another knowledge module, benchmark family, or named-failure pattern next cycle.** The library is strong. Instead:

1. **Ship Moat 6: `/velocity` instrumentation** (1-2 commits)
2. **Write `tests/test_data_public_smoke.py`** regression suite (1 commit)
3. **Decide QoE: ship or delete** the backend sitting on disk (1 commit)
4. **Prune survival_analysis synthetic curves** (label clearly or delete) (1 commit)
5. **Demote `/adversarial-engine` standalone route** (the engine lives in IC Brief) (1 commit)

5 commits. All hardening + focus. Zero new moat layers. Zero new modules.

## 7. What was moved forward vs what was shipped-but-didn't-move-forward

**Moved moat forward:**
- Track Record (Moat 7 nascent → Moat 7 real artifact)
- CPOM State Lattice (Moat 1 → broader coverage; first cross-state regulatory knowledge)
- PIM 100-08 (Moat 1 → the audit-contractor ground truth, not just list-of-things)
- RAG (makes every other knowledge module searchable — the force multiplier)

**Shipped but didn't move the moat:**
- Tuva+DuckDB integration doc-level content (infrastructure planning, not platform capability)
- Adversarial engine's corpus-random standalone page (the engine matters; the page is redundant with IC Brief)
- Several of the round-2 "retries" of already-shipped modules (no delta to Moat)

## 8. Recurring-duplicate directive detection

The session's `/loop` rotation cycled through ~12 directives at least twice. I began detecting duplicates around directive 20 and reporting them to the user rather than silently rebuilding. Pattern:

- Round 1: all 12 directives → 12 genuine new modules
- Round 2: 12 directives → 3-4 genuine deltas (PIM 100-08, Track Record, CPOM, RAG), 8-9 already-shipped detections reported honestly

Net effect: ~60% of round-2 turns were "report duplicate, don't rebuild" — preserved focus, avoided sprawl.

## 9. Bottom line

**State**: 17 new modules shipped, 5 of 7 moat layers STRONG or NASCENT-but-real, 1 IGNORED (velocity compound), 1 MEDIUM (benchmark library, 15% of target).

**Focus**: Stop adding moat layers. Start instrumenting + hardening them.

**Next cycle goal**: Ship `/velocity` + pytest regression file + decide/execute the four prune items above. End the cycle with fewer routes and more test coverage, not more routes.

---

*Generated at REFLECT AND PRUNE directive, commit cycle concurrent with RAG ship (`c5f8ba4`). Earlier version of this analysis offered inline in the prior turn's response; this is the committed artifact.*

---

## Addendum — Round-3 loop cycle deltas (after original reflection)

After this doc's original commit, the session's `/loop` entered round 3. Net-new shipped:

| Commit | Module | Moat Layer advanced |
|---|---|---|
| `f396654` | CMS Claims Processing Manual Pub 100-04 (22/39 ch, 28 §) | Moat 1 |
| `35d0034` | Benchmark Library BC-09..BC-13 (+248 rows → 636 total, 25% of 2500 target) | Moat 2 |
| `e3b16c7` | Named-Failure Library NF-17..NF-19 (Aveanna, Surgery Partners, MedPartners) | Moat 3 |
| `beb34de` | Site-Neutral Payment Simulator (20 codes, $2.6B corpus exposure) | Moat 1 (regulatory sublayer) |
| `c57bc3d` | NLRB Healthcare Union-Election Filings (54 cases, 81K workers) | New public-data source |

Round-3 continues to produce ~4-5 genuinely-new commits per full 12-directive loop rotation. **Moat 6 (Velocity Compound) remains ignored**. The prune-and-harden plan in §6 above is unchanged; round-3 deltas are expansion not hardening. A disciplined next cycle should execute the §6 hardening plan before adding more knowledge modules.
