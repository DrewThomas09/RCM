# Report 0270: CSV Formula-Injection Defang — audited all exporters, consolidated, closed the tab/CR gap (commit 6a575d3)

## Scope

Second fresh post-TRIAGE sweep. CLAUDE.md advertises "CSV exports everywhere (defanged for Excel formula injection)" (the B149 convention). This audited whether that actually holds across every CSV exporter — and found the convention was implemented **four divergent ways**, two of them incomplete.

Sister reports: 0267/0268/0269 (the XSS/traversal + deal_id class), B149 (original CSV defang).

## The landscape

| Site | Charset before | Verdict |
|---|---|---|
| `server.RCMHandler._defang_csv_df` (deal/notes/corpus DataFrame exports) | `= + @ - \t \r` | **complete** — the canonical path |
| `ui/expert_calls_page._csv_defang` | `= + - @` | **gap: missing \t \r**, on partner-entered call findings/lens/vantage |
| `data_public/corpus_export.to_csv` | `= + - @ \|` | **gap: missing \t \r**, on partner deal_name/buyer/seller/notes |
| `ui/tam_sam_page.tam_sam_csv` | (none) | **defanged nothing** — but content is trusted catalog (see below) |
| `npi_cleaner/engine._defang_cell` | `= + - @ \t \r` | complete (operator CLI, out of threat model) |

CLI/operator-run exporters (`cli.py`, `portfolio_cmd.py`, `data/*`, most of `npi_cleaner/`) write to disk for the operator who ran them — not browser-served to a partner — so they're outside the formula-injection threat model and were left as-is.

## Fixes (commit 6a575d3)

**Consolidation.** New `rcm_mc/infra/csv_safety.py` — the single source of truth: `FORMULA_LEAD = ("=", "+", "-", "@", "\t", "\r")`, `defang_cell()`, `defang_row()`. Every cell-level exporter now calls it, and `server._defang_csv_df` imports the same `FORMULA_LEAD` (behavior unchanged), so the character set can never diverge again.

**Real gap closed (expert_calls + corpus_export).** Both delegated to the shared helper, gaining `\t`/`\r` coverage on genuinely partner-supplied free text. A leading-tab cell (e.g. an expert-call finding pasted as `\t=cmd`) would previously have exported unprefixed and executed on open.

**Defense-in-depth (tam_sam).** `tam_sam_csv` built browser-served rows from `compute(model_from_qs(qs))` with no defang. Investigation (verified, not assumed): `model_from_qs` accepts only **numeric** overrides plus a **fixed `template` key** — no free text from the query string reaches the CSV, so the string cells are trusted catalog content. Not a live vuln. But the export held none of the convention, so all rows now route through a defanging writer wrapper — if a future template ever carries a partner field, it's covered. Comment and test are labeled honestly as defense-in-depth, not a live-bug fix.

## A caught over-claim

My first draft asserted tam_sam's `name` was qs-controlled (a live bug). The test failed because `out["name"]` came from the template, not the query string — so I read `model_from_qs`, confirmed only numeric/template-key inputs are honored, and downgraded the finding to defense-in-depth. The corpus_export test also initially used wrong column names (`name`/`sector` vs the real `deal_name`/`buyer`/`notes`); corrected. Writing the tests is what surfaced both errors before they reached the report's claims.

## Evidence

- `tests/test_csv_safety.py` (new): full `FORMULA_LEAD` charset incl. tab/CR; non-string/safe passthrough; `defang_row`; expert-calls delegation now covers tab; corpus_export defangs `deal_name`/`buyer`/`notes` formula + tab payloads; tam_sam smoke.
- Regression: `test_csv_safety`, `test_expert_calls`, `test_csv_export`, `test_csv_exports`, `test_deals_corpus`, `test_tam_sam`, `test_corpus_report_pstore` → **1041 tests green** across the runs.

## Suggested follow-ups

| Iteration | Proposed area |
|---|---|
| next | A never-mapped package sweep (`pe_intelligence/`, `data_public/`), or a session PROGRESS rollup (this session has landed Reports 0262-0270), or the MR1069/MR1070/MR1071 LOW carry-forwards. |

---

Report/Report-0270.md written.
