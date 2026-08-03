# Report 0266: Engagement Guard Tests + Doc Snapshot Banners — 5 MRs closed (commit fbf9f9a)

## Scope

The engagement test-coverage pair (MR1024, MR988), the root-doc drift item (MR1033), the ai/ store-wiring residual (MR1010), and the MR1060 disposition. This clears the last of the items promoted to TRIAGE before this session — every remaining open row is now either a landed-unaudited audit task (MR1019/1020/1021) or the infra README gap (MR1053).

Sister reports: 0249/0207 (engagement audit origin), 0250 (root-doc inventory), 0244 (llm_client census), 0257 (cms_ma_enrollment), 0262 (verification sweep).

## Fixes (commit fbf9f9a)

**MR1024 — engagement audit trail untested.** `_audit` is best-effort by design (`except: pass` — "audit log is a detective control, not a pre-condition"), which meant a broken audit path was invisible to all 22 existing engagement tests. New `EngagementAuditTrailTests`: drives all six mutators through the real path (create_engagement, add_member, remove_member, post_comment, create_deliverable, publish_deliverable) and asserts one chained row per action string with non-null `row_hash` (proving `append_chained_event` ran, not just some logger); plus an outage test — chain writer stubbed to raise (documented external-stub exception), mutator must still succeed.

**MR988 — dataclass↔DDL coupling.** The four engagement dataclasses and their CREATE TABLE statements are hand-maintained in the same file; a column added to one side would drift silently. New `EngagementSchemaGuardTests` asserts `dataclasses.fields(dc) == PRAGMA table_info(table)` for all four pairs. All four map 1:1 at HEAD — no exclusion set needed, and the verifier's judgment stands that a DDL-from-dataclass generator would be over-engineering for a 4-table module.

**MR1033 — root-doc drift.** FILE_MAP.md claimed 1,705 files (actual: ~3,900 — the tree roughly doubled in the July merge wave); FILE_INDEX.md and ARCHITECTURE_MAP.md said 1,659; FILE_INDEX linked two files that no longer exist; FILE_MAP pointed at the moved `RCM_MC/handoff/` path. Fixed with the DEPLOYMENT_PLAN.md precedent: **HISTORICAL SNAPSHOT banners** (counts frozen April 2026, per-directory READMEs are the maintained truth) rather than a full regeneration; dead links removed; moved path corrected. WALKTHROUGH.md and DEPLOYMENT_PLAN.md needed nothing (the latter already carries its banner).

**MR1010 — store-less default LLM clients.** The census confirmed 4 lazy `LLMClient()` construction sites, all with DI. The env-read cost is a non-issue; the real defect was that `document_qa.answer_question`'s default client was built **without the store** — so the RAG path silently skipped the SQLite response cache and `llm_calls` cost logging. Now `LLMClient(store=store)` (the function already receives the store). `memo_writer.compose_memo` takes no store in its public API, so its default legitimately stays uncached — callers who care inject a store-backed client.

**MR1060 — cms_ma_enrollment.py disposition: closed as accepted-design.** 712 LOC bundling three CMS datasets (CPSC enrollment, Star ratings, MA ratebook) in one denormalized table is the documented design (module docstring, "three loaders populate them independently"); the loaders are independent and separately parseable. A three-way split would churn `data/catalog.py` and the documented public API for no defect.

## Evidence

- `tests/test_engagement.py` → 26 passed (22 existing + 4 new; the 1:1 schema claim held on first run).
- `tests/test_phase_p.py` → 36 passed (document_qa/llm_client surface).
- Doc changes are text-only; ARCHITECTURE_MAP Mermaid untouched.

## Merge risks flagged

| ID | Risk | Severity |
|---|---|---|
| (closure) | MR1024, MR988, MR1033, MR1010, MR1060 closed | — |

## Suggested follow-ups

| Iteration | Proposed area |
|---|---|
| next | MR1019/MR1020/MR1021 — audit the three landed-unaudited surfaces from the feat merge (infra/exports.py, server.py route delta, screening/dashboard.py); MR1020 likely closes as moot (merge landed, CI green) once the route table is eyeballed |
| after | MR1053 — document infra/cache.py + infra/morning_digest.py in infra/README.md; then TRIAGE is EMPTY and the loop pivots to fresh audit sweeps (backlog: pe_intelligence/ 270+ submodules, data_public/ 313 files, ~10 small subpackages from Report 0190) |

---

Report/Report-0266.md written.
