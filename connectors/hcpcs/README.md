# connectors/hcpcs — HCPCS Level II (NLM Clinical Tables)

A self-contained, **stdlib-only** connector that ingests CMS's HCPCS
Level II code set — the national billing vocabulary for everything CPT
doesn't cover: DME (E-codes), drugs administered incident-to (J-codes),
ambulance (A-codes), orthotics/prosthetics (L-codes), vision/hearing
(V-codes) and the temporary G/K/Q/S/T ranges — into a canonical SQLite
table and re-exposes it behind the estate's uniform `/v1` query surface.
Mirrors the architecture of `connectors/icd10` exactly (same API family,
same 4-element JSON-array response shape).

`code` joins straight onto the HCPCS columns of the data.cms.gov
utilization files already in the estate (`hcpcs_cd` on Physician & Other
Practitioners by-service, PSPS, RBCS, DMEPOS), making this the code
dimension for every procedure-level Medicare fact table. HCPCS Level I
(CPT) is AMA-licensed with no public API and is deliberately out of
scope.

## Source

`https://clinicaltables.nlm.nih.gov/api/hcpcs/v3/search` — public and
keyless. The connector drains it by iterating letter seeds (`q=code:A*`
… `code:V*`; HCPCS Level II codes are one letter + four digits) and
paging each seed by `offset`. The whole set is ~8k codes, so a full
ingest is a few dozen polite requests.

**Rate floor, not a contract:** the transport enforces a conservative
0.10 s minimum interval between requests plus exponential backoff on
429/5xx (`Retry-After` honored). Verify live limits at the NLM Clinical
Tables docs before a bulk run — the constants in `transport.py` are a
polite floor and are constructor-overridable.

## Datasets

| dataset_id | Target table | Slice |
|------------|--------------|-------|
| `hcpcs_lvl2` | `dim_hcpcs_code` | `source_endpoint='lvl2'` |

Rows are keyed by a composed `{code_type}:{code}` (`lvl2:J9271`); the
registry's `source_filter` pins the dataset to its slice so a future
companion code set lands as a row, not a schema change.

## CLI

```bash
python -m connectors.hcpcs.cli --root var/connectors datasets
python -m connectors.hcpcs.cli --root var/connectors discover
python -m connectors.hcpcs.cli --root var/connectors ingest [--dataset lvl2] [--terms T] [--q code:J9*]
python -m connectors.hcpcs.cli --root var/connectors query hcpcs_lvl2 --filter section=J --limit 10
python -m connectors.hcpcs.cli --root var/connectors aggregate hcpcs_lvl2 --group-by section
python -m connectors.hcpcs.cli --root var/connectors lookup-code J9271
python -m connectors.hcpcs.cli --root var/connectors lookup-section E
python -m connectors.hcpcs.cli --root var/connectors search pembrolizumab
python -m connectors.hcpcs.cli --root var/connectors serve
```

`--root` is the working dir holding `hcpcs.db` (`./.hcpcs_data` by
default). Read verbs (`query` / `aggregate` / `lookup-*` / `search`)
never create the dir or the db — a never-ingested root answers from an
empty in-memory store instead of littering the cwd.

## `/v1` surface

```
/v1/datasets
/v1/query/hcpcs_lvl2                  uniform field__op grammar
/v1/query/hcpcs_lvl2/aggregate?group_by=
/v1/lookup/hcpcs/{code}
/v1/lookup/hcpcs-section/{section}?limit=
/v1/lookup/hcpcs-search/{term}?limit=
```

The lookup nouns are `hcpcs`-prefixed so the unified estate router
(first-match-wins) can never confuse them with the ICD-10 slice's
`/v1/lookup/code/{code}` / `/v1/search/{code_type}` templates.

## Canonical table

`dim_hcpcs_code` — one row per code: `code_key` (pk), `code_type`,
`code`, `display`, `short_desc`, `long_desc`, `obsolete`, `section`
(leading letter — the code family), `category` (letter + two digits),
plus the shared `source_endpoint` / `ingested_at` meta columns.
