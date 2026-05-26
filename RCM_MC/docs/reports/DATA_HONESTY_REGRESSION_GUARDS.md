# Data-Honesty Regression Guards

The invariants that keep PEdesk's Diligence/Tools/analytics honest, and the
automated tests that enforce each so a regression fails CI rather than shipping.
Part of the Diligence Workbench Excellence Loop.

## Invariants

1. **Every data-rendering analytic page discloses its basis.** A page showing
   figures must carry a source/purpose header (`ck_source_purpose`), a data-
   universe chip (`ck_data_universe`), an illustrative note (`ck_illustrative_note`),
   or an explicit DATA REQUIRED / USER DATA REQUIRED label — never an
   unlabeled table of numbers.
2. **Illustrative ≠ live.** Pages whose figures come from the seed/illustrative
   corpus carry an illustrative marker; they are never presented as live
   benchmark corpus or real deal data.
3. **No fabricated values.** No invented payer mix, market share, model
   performance, multiples, trends, or portfolio/fund/comp/debt/AR/claims data.
   Missing values render `—` / honest empty states.
4. **Curated Guide source cards stay indexed.** The deliberate
   `docs/rag_sources/*.md` cards must all reach the Guide RAG corpus.
5. **Models state their method + limits.** Prediction/Monte-Carlo pages declare
   they run on user inputs / fixtures with assumptions — no invented accuracy.

## Enforcing tests

| Invariant | Guard |
|---|---|
| 1 (data_public pages) | `tests/test_page_data_source_audit.py` — audit must stay **0 flagged** (`scripts/audit_page_data_sources.py`). |
| 1 (Diligence analyzer pages) | `tests/test_diligence_source_purpose_headers.py` — core analyzer renderers must keep `ck_source_purpose` / honesty label. |
| 2 | `tests/test_curated_illustrative_note*.py`, `tests/test_diligence_illustrative_labels*.py`, `tests/test_diligence_corpus_seed_labels*.py`, `tests/test_route_illustrative_banner.py`. |
| 2 (chip honesty) | `tests/test_source_purpose_header.py` — illustrative tooltip/header honesty. |
| 4 | `tests/test_xray_rag_cards.py` + `document_sources` always indexes `docs/rag_sources/`. |
| 5 | `tests/test_payer_stress*.py`, `tests/test_deal_mc.py`, `tests/test_ref_pricing_real_data.py`, `tests/test_payer_stress_hcris_wiring.py` (no-CCN ⇒ illustrative). |

## Resolved
- `test_curated_illustrative_note{,_batch3}` — previously asserted `scenario_mc`
  / `base_rates` must NOT carry `ck-illus-note`. Reconciled (loop): those pages
  are correctly labeled — `scenario_mc`/`tax_structure_analyzer` render
  ILLUSTRATIVE DEFAULTS that compute off user inputs, and `base_rates` derives
  from the illustrative SEED CORPUS. The tests now assert the honest label is
  present (not absent); the original expectation predated the pages adopting
  the honest illustrative-defaults / seed-corpus note.

## How to extend
When a new Diligence analyzer page ships: add its renderer to
`_REQUIRE_SOURCE_PURPOSE` in `test_diligence_source_purpose_headers.py`, and
ensure the data-source audit stays 0-flagged. New illustrative pages get an
`ck_illustrative_note`; new DATA REQUIRED pages get `data_required_panel` +
an activation path.
