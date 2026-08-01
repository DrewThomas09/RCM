# PROGRESS-29 — Bug-Fix & Audit Loop status, session of 2026-08-01

Date: 2026-08-01 (single self-paced /loop session, "continue processes")
Branch: `claude/continue-processes-loop-8h-pzylop`
PR: #1957 (draft, auto-watched)
Predecessor rollup: PROGRESS-19 (iter 19, 2026-04-26)

## What this session did

Resumed the TRIAGE fix-loop after the July merge wave (main advanced from
the April audit baseline to `a46a928`, ~doubling the tree). Ran **10 audited
fix iterations** (Reports 0262-0271), each with its own report, regression
tests, and TRIAGE/RESOLVED bookkeeping, every one pushed CI-green (py3.11/
3.12/3.14 test + connectors legs).

## Triage rollup

| Severity | Open at session start | Closed this session | Open now |
|---|---|---|---|
| CRITICAL | 0 | 0 | 0 |
| HIGH | 1 partial + growing | all (incl. 3 new found in-sweep) | **0** |
| MEDIUM | ~13 | all | **0** |
| LOW | ~9 | 15 | **1** (MR1071) |

**The entire April-2026 TRIAGE backlog is closed.** The one remaining LOW
(MR1071, deal_sim_inputs path validation) needs a product/allowlist design
decision, not a code fix, and is tracked as a note.

## Iterations

| Iter | Report | Commit | Theme |
|---|---|---|---|
| 20 | 0262 | 0e93f13 | Re-verification sweep (19 items) + infra/config & intake hardening |
| 21 | 0263 | 0ab26f6 | Deals FK correctness (delete_deal wrong names, CASCADE, live-DB rebuild migration) |
| 22 | 0264 | 186b06a | Seeder + canonical-export hardening |
| 23 | 0265 | 4d93d38 | Dependency pins + repo hygiene (8 items) |
| 24 | 0266 | fbf9f9a | Engagement audit/schema guard tests + doc snapshot banners |
| 25 | 0267 | cc51351 | Audited 3 landed-unaudited files → **2 HIGH** (exports path traversal, screening XSS) |
| 26 | 0268 | a8b5279 | Trust-boundary sweep → **4 more XSS + 1 traversal** (same deal_id class) |
| 27 | 0269 | d09e865 | deal_id ingestion validator — closes the class at the source |
| 28 | 0270 | 6a575d3 | CSV formula-injection audit — consolidated defang, closed tab/CR gap |
| 29 | 0271 | d0e0cec | Export LOW carry-forwards (microsecond timestamp, exports.py docs) |

## Security highlights

The audit found a whole vulnerability **class** the April triage never named:
partner-supplied `deal_id` (accepted at the import routes with only a
non-empty check) reaching dangerous sinks. Closed at both layers:

- **Sinks** (0267/0268): path traversal in `infra/exports.py` (reproduced),
  stored XSS in the screening dashboard, the analysis-workbench Delete
  button, and the dashboard saved-templates list (all `html.escape` into an
  `onclick` JS-string — wrong codec), reflected XSS in the screening /
  IC-memo / synthesis 500 pages, and an unvalidated `/api/jobs/run` outdir.
- **Source** (0269): a safe-slug validator at the `upsert_deal`/`clone_deal`
  creation chokepoint, grandfathering existing rows.

Also caught and fixed a latent `UnboundLocalError` I introduced in 0267 (the
`html` module is shadowed by a function-local inside `_do_get_inner`) — the
verify-and-test discipline surfaced it before it shipped.

## Hard constraints honored

No new runtime deps (one new stdlib-only module, `infra/csv_safety.py`).
Parameterised SQL throughout. Every fix has a regression test exercising the
real path. Existing-data compatibility preserved (FK rebuild migration is
PRAGMA-guarded + idempotent; deal_id validator grandfathers legacy rows;
CSV/timestamp changes don't touch explicit-caller contracts).

## Remaining / next

- **MR1071** (LOW) — deal_sim_inputs path validation; needs an allowlist-dir
  decision.
- The deal_id **ingestion-boundary root fix** shipped (0269); a stricter
  variant (reject at the route with a 400 body instead of skip) is optional.
- Never-mapped packages for future sweeps: `pe_intelligence/` (270+
  submodules), `data_public/` (313 files), the ~10 small subpackages from
  Report 0190, and a re-promotion grep over pre-Report-0085 MRs.

Full commit trail: Report/RESOLVED.md. Per-iteration detail: Report/Report-0262.md … Report-0271.md.
