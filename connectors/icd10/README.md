# connectors/icd10 — ICD-10-CM + ICD-10-PCS (NLM Clinical Tables)

A self-contained, **stdlib-only** connector that ingests the ICD-10-CM
diagnosis and ICD-10-PCS procedure code sets from the NLM Clinical
Tables API into a canonical SQLite table and re-exposes them behind the
estate's uniform `/v1` query surface. Mirrors the architecture of
`connectors/cms_coverage` exactly.

## Source

`https://clinicaltables.nlm.nih.gov/api` — public and keyless. Both
endpoints return the same shape (a JSON array of four elements), so one
connector drains them by iterating code-prefix seeds (`q=code:A*` …
`code:Z*`, digits for PCS) and paging each seed by `offset`.

**Rate floor, not a contract:** the transport enforces a conservative
0.10 s minimum interval between requests plus exponential backoff on
429/5xx (`Retry-After` honored). Verify live limits at the NLM Clinical
Tables docs before a bulk run — the constants in `transport.py` are a
polite floor and are constructor-overridable.

## Datasets

| dataset_id | Target table | Slice |
|------------|--------------|-------|
| `icd10_cm` | `dim_icd10_code` | `source_endpoint='cm'` |
| `icd10_pcs` | `dim_icd10_code` | `source_endpoint='pcs'` |

Both code sets share one physical table keyed by a composed
`{code_type}:{code}`; the registry's `source_filter` pins each dataset
to its slice.

## CLI

```bash
python -m connectors.icd10.cli --root var/connectors datasets
python -m connectors.icd10.cli --root var/connectors discover
python -m connectors.icd10.cli --root var/connectors ingest [--dataset cm|pcs] [--terms T] [--q code:E11*]
python -m connectors.icd10.cli --root var/connectors query icd10_cm --filter chapter=E --limit 10
python -m connectors.icd10.cli --root var/connectors aggregate icd10_cm --group-by chapter
python -m connectors.icd10.cli --root var/connectors lookup-code E11.65
python -m connectors.icd10.cli --root var/connectors lookup-category E11
python -m connectors.icd10.cli --root var/connectors search cm diabetes
python -m connectors.icd10.cli --root var/connectors serve
```

`--root` is the working dir holding `icd10.db` (`./.icd10_data` by
default). Read verbs (`query` / `aggregate` / `lookup-*` / `search`)
never create the dir or the db — a never-ingested root answers from an
empty in-memory store instead of littering the cwd.

## `/v1` surface

```
/v1/datasets
/v1/query/icd10_cm | icd10_pcs        uniform field__op grammar
/v1/query/{dataset}/aggregate?group_by=
/v1/lookup/code/{code}?type=cm|pcs
/v1/lookup/category/{category}?type=cm|pcs
/v1/search/{code_type}?q=&limit=
```

Served standalone (`python -m connectors.icd10.cli serve`) or through
the unified estate server (`python -m connectors.cli serve`), which
delegates these routes to this connector.

## Tests

```bash
python -m unittest discover -s connectors/icd10/tests -t .
```

Transport retry/backoff, the seed/offset paging state machine,
normalize round-trips, query grammar, lookups, and the standalone HTTP
server are all exercised against in-memory fakes — no network.
