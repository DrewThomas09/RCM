# RxNorm / RxNav connector

The RxNorm / RxNav (`rxnav.nlm.nih.gov/REST`) vertical slice for PEDesk:
connector, declarative registry, normalized SQLite tables, the **NDC→RxCUI
crosswalk** other drug sources join to, drug-class grouping, a uniform query /
lookup layer, and DQ tests. Stdlib-only, self-contained, resumable.

## Why this slice matters

NDC→RxCUI is the spine that ties NDC-keyed records (recalls, adverse events,
drug spend) back to a single molecule. openFDA and other sources present NDCs in
different formats; the canonical 11-digit key produced here is what makes those
joins work. RxClass grouping lets you size a drug target's competitive set by
therapeutic class or mechanism. `historystatus` handling stops retired/remapped
codes from silently corrupting joins.

## Layout

| File | Responsibility |
|---|---|
| `connector.py` | `RxNormConnector` — `discover()` + `fetch(endpoint, params, cursor)`; internal rate-limit (~20 req/s), 429/503 backoff+jitter, retries, fail-closed. Injectable opener. |
| `normalize.py` | Pure normalization: canonical 11-digit NDC, concept/related/class/history parsers. |
| `store.py` | SQLite DDL + idempotent upserts for the five tables; remap-aware resolvers + coverage. |
| `registry.py` | Declarative dataset rows tagged `source=rxnorm` (one row per dataset). |
| `query.py` | Uniform filter/select/sort/paginate (`query_dataset`) + `lookup_rxcui` / `lookup_ndc` (rxnorm namespace). |
| `pipeline.py` | Resumable, idempotent orchestrator; STATE.md / PROGRESS.log; failure queue. |
| `validation.py` | Read-only openFDA NDC join → match-rate report. |
| `seed.py` | Offline representative seed (renders RxNav-native JSON). |
| `STATE.md` / `DECISIONS.md` / `PROGRESS.log` | Filesystem-as-memory. |

## Canonical tables

- `xwalk_ndc_rxcui` — `ndc_11` (canonical), `ndc_raw`, `rxcui`, `status`. **The crosswalk.**
- `dim_rxnorm_concept` — `rxcui`, `name`, `tty`, `status`, `remapped_to_rxcui`.
- `bridge_rxcui_related` — `rxcui`, `related_rxcui`, `relationship`.
- `dim_drug_class` — `rxcui`, `class_id`, `class_name`, `class_type` (ATC / therapeutic / mechanism_of_action).
- `dim_ndc_properties` — packaging / labeler detail (optional).

## Running

```bash
# Offline (default — uses the representative seed; no network):
python -m rcm_mc.data_public.rxnorm.pipeline --db rx.db

# Live (where the environment can reach RxNav):
python -m rcm_mc.data_public.rxnorm.pipeline --db rx.db --live
```

```python
from rcm_mc.portfolio.store import PortfolioStore
from rcm_mc.data_public.rxnorm import run, query

store = PortfolioStore("rx.db")
run(store)                                    # resumable, idempotent

query.lookup_ndc(store, "0409-1896-20")       # → current RxCUI via crosswalk
query.lookup_rxcui(store, "83367")            # → concept + relations + classes + NDCs
query.query_dataset(store, "rxnorm_concepts", # uniform query envelope
                    filters={"tty": "SCD"}, sort="rxcui", limit=50)
```

## Intended API routes (router-agnostic)

This repo's HTTP server has no `/v1` plugin-registration surface (and the `/v1`
router core is out of scope to edit), so the query/lookup functions are exposed
as a library a router could register. If a registrable router lands:

```
GET /v1/query/{dataset}          -> query.query_dataset(...)
GET /v1/lookup/rxnorm/{rxcui}    -> query.lookup_rxcui(...)
GET /v1/lookup/rxnorm/ndc/{ndc}  -> query.lookup_ndc(...)
```

We never define `/v1/lookup/drug/{ndc}` — openFDA owns it. See `DECISIONS.md`.

## Live backfill notes

For a real bulk run, prefer the monthly RxNorm RRF release over one API call per
concept, and confirm NLM's current rate limit (~20 req/s/IP) before starting; or
stand up RxNav-in-a-Box for unlimited local queries. The pipeline is resumable
from `STATE.md` and every pull is idempotent, so a bulk run can be killed and
restarted freely.
