# Report 0269: deal_id Ingestion-Boundary Validator — the deal_id class closed at the source (commit d09e865)

## Scope

The durable, defense-in-depth close for the `deal_id` vulnerability class that Reports 0267–0268 fixed sink-by-sink (path traversal in exports, stored/reflected XSS in five render/route sites). Rather than trust that every current *and future* sink escapes correctly, this validates `deal_id` to a safe slug at the single creation chokepoint — so a new sink can't reintroduce the class.

Sister reports: 0267 (first two HIGH deal_id bugs), 0268 (trust-boundary sweep, four more), 0181 (delete-policy chokepoint precedent).

## Why the chokepoint, and why INSERT-only

Every deal-creation path — `/api/deals/import`, `/api/deals/import-csv`, `/quick-import`, `/quick-import-json`, and the internal helpers (`deal_owners`, `deal_tags`, `deal_notes`, `deal_sim_inputs`, `deal_deadlines`, `watchlist`, `hold_tracking`, `dev/seed`) — funnels through `PortfolioStore.upsert_deal`; the one exception is `clone_deal`, which INSERTs directly. So two functions own all deal-id creation.

Validating there naively would break existing deployments: `upsert_deal` is also called by owner/tag/note refreshes *for deals that already exist*, and a legacy DB may hold an odd id. The fix validates **only on the INSERT path** — a pre-check `SELECT` grandfathers any existing row, so legacy ids keep working for every downstream refresh while every genuinely new id is validated.

## The validator

`_DEAL_ID_RE = ^[A-Za-z0-9._-]{1,128}$`, exposed as `is_valid_deal_id()`. The charset was chosen from the actually-observed id formats (`DEAL_001`, `acme_health_2026`, CCN `010001`, `extra_001`) — it rejects every dangerous character (quotes, angle brackets, slashes, spaces, null bytes, `..`) without restricting any real usage. Confirmed empirically: the full import/api/corpus suite (813 tests) stays green, so no existing id trips the charset.

`upsert_deal` (INSERT path) and `clone_deal` (always new) raise `ValueError` on an invalid new id.

## Graceful route handling (no 500s)

A hard raise at the chokepoint would turn a bad id into a 500 at the untrusted routes, so each was updated to respond cleanly:

| Route | Behavior on invalid id |
|---|---|
| `POST /api/deals/import` (JSON) | skip the row, add it to a new `skipped` list in the JSON response |
| `POST /api/deals/import-csv` | skip the row, append to the existing per-row `errors` list |
| `POST /quick-import-json` | skip + count ("(N skipped: invalid deal_id)") |
| `POST /quick-import` (browser form) | already wrapped in try/except → re-renders with the error message |
| `POST /api/deals/<id>/duplicate` (clone) | returns 400 with the validator message |
| roll-up-save + expert-call handlers | unaffected — they require the deal to pre-exist, so the id is grandfathered |

## Evidence

- `tests/test_deal_id_validation.py` (6 new): slug accept/reject table; `upsert_deal` rejects `../evil` and a quote payload for a new id; a good id inserts; a **legacy odd id is grandfathered** (pre-seeded row, then `upsert_deal` renames it without raising); `clone_deal` rejects a bad new id and accepts a good one.
- Regression surface: `test_deal`, `test_dev_seed`, `test_deal_children_fk_migration`, `test_quick_import_validation`, `test_api_endpoints`, `test_large_portfolio`, `test_deals_corpus`, `test_seekingchartis_import` → **all green** (855 tests across the two runs).

## Class status

The `deal_id` vulnerability class is now closed at **both** layers: every known sink is individually neutralized (0267/0268) *and* the id is validated at the source (this report). A future sink that forgets to escape `deal_id` is no longer exploitable, because the id can no longer carry a payload past creation.

## Carry-forward notes (unchanged)

MR1069 (exports.py undocumented), MR1070 (same-second export collision), MR1071 (deal_sim_inputs path validation) remain LOW tracked notes.

## Suggested follow-ups

| Iteration | Proposed area |
|---|---|
| next | Fresh sweep of a never-mapped package (`pe_intelligence/`, `data_public/`), or a CSV/Excel-formula-injection audit of the CSV exporters (CLAUDE.md claims they're defanged — verify), or a session PROGRESS rollup. |

---

Report/Report-0269.md written.
