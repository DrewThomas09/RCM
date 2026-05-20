# Healthcare Revenue Leakage Diligence Module V2 — Implementation Summary

Status: **functionally complete and live.** A PE deal team can upload
835/837 files (or a VDR ZIP) at `/diligence/snapshot` and receive a Data
Confidence Score, revenue-leakage findings, and a Markdown diligence
memo. Built on the existing `rcm_mc/diligence/ingest` CCD stack rather
than rebuilt.

## What shipped (PRs #395–#405)

| Module | Path | What it does |
|---|---|---|
| Parser adapters | `diligence/parsers/` | library-independent contract; ISA-aware detection; **x12-python** primary (optional `[edi]` extra), hand-rolled **fallback**; evaluation harness + ADR |
| PHI tokenization | `diligence/security/` | HMAC tokenize patient ids before persist; raw MRNs never stored |
| Matching | `diligence/matching/` | layered 837↔835 match w/ confidence + reason + score |
| Data confidence | `diligence/reconciliation/` | 0–100 score + plain-English issue list |
| Analytics | `diligence/analytics/` | leakage totals, denial-by-preventability, payer/CPT/provider marts |
| Findings + follow-ups | `diligence/findings/` | PE-readable findings + tailored requests, conservative language |
| Memo | `diligence/reporting/` | 11-section PHI-safe Markdown memo |
| Orchestrator | `diligence/snapshot.py` | `run_snapshot` / `run_snapshot_from_zip` — files → memo |
| ZIP ingestion | `diligence/ingestion/` | VDR ZIP extract with path-traversal + zip-bomb guards |
| UI tab | `diligence/snapshot_page.py` + `server.py` | `GET/POST /diligence/snapshot` |
| Persistence | `diligence/store/` | `hcrl_runs` SQLite table (save/load/list) |

~95 dedicated tests (`tests/test_hcrl_*.py`), all green; full suite green
at each merge.

## Acceptance criteria (from the brief)

1. Upload ZIP of synthetic 835/837 — ✅ (`run_snapshot_from_zip`, live tab)
2. Detect transaction types + delimiters — ✅ (`parsers/detection`)
3. Parser adapter extracts data — ✅ (x12-python + fallback)
4. Parser choice documented — ✅ (`docs/adr/healthcare-parser-selection.md`)
5. Normalize payers/providers/claims/lines/adjustments — ✅ (CCD)
6. Tokenize identifiers — ✅ (`security/phi_tokenization`)
7. Tuva-compatible mapping — ✅ (`tuva_bridge` + mapping doc)
8. Match 837→835 — ✅ (`matching`)
9. Match confidence/reason/score — ✅
10. Data Confidence Score + issues — ✅
11. Denial/reimbursement metrics — ✅ (`analytics`)
12. Denial categorization — ✅ (`benchmarks/_ansi_codes`, reused)
13. PE-readable findings — ✅
14. Follow-up questions — ✅
15. Markdown memo — ✅
16. Memo avoids patient detail — ✅ (tested)
17. Conservative language — ✅ (tested: no "guaranteed EBITDA upside")
18. Uses existing libraries — ✅ (x12-python primary)
19. Fallback not primary — ✅ (registry orders library first)
20. No live integration — ✅ (snapshot-only throughout)

## Decisions for human review

- **x12-python as a dependency:** added as optional `[edi]` extra (MIT).
  Promote to a hard dep only if the team wants the richer parser always
  on. Core `rcm_mc` still imports nothing new.
- **Schema deviation:** the brief's 14 relational tables were collapsed
  to the CCD (single source of truth) + a `hcrl_runs` persistence table,
  to avoid a parallel schema that drifts from the CCD. See plan §5.
- **POST CSRF exemption** for `/diligence/snapshot`: analysis-only (no
  shared-state mutation), matching existing upload routes.

## What remains (non-blocking polish)

- 837I institutional loop coverage, PLB provider-level adjustments,
  per-code CAS dollar attribution.
- Wire `store.save_run` into the POST route for durable run history UI
  (currently the store is available but the tab is stateless).
- pyx12 validation-report path (deferred; see ADR).
- PDF/DOCX memo export (Markdown first, by design).
