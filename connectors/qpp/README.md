# connectors/qpp — CMS Quality Payment Program (MIPS/APM)

A self-contained, **stdlib-only** connector over the public, keyless QPP
API (`qpp.cms.gov/api`) — MACRA's MIPS/APM clinician payment-adjustment
program — normalized into canonical SQLite tables and re-exposed behind
the estate's uniform `/v1` query surface.

Two public API families feed it:

* **Eligibility API** (`/eligibility/npis/{npi}?year=`) — one
  clinician's MIPS eligibility, specialty, and practice organizations
  per performance year. Per-NPI, so a pull is **roster-driven**
  (`--npis N1,N2,…`), mirroring the NPI Registry connector's
  manual-ingest contract; the estate's NPPES universe is the natural
  roster source. An NPI with no QPP record (API 404) is recorded as a
  skip, never an error.
* **Submissions API public benchmarks**
  (`/submissions/public/benchmarks?year=`) — every MIPS quality-measure
  benchmark (deciles by submission method) for a performance year, in
  one unattended request.

`npi` joins the NPPES provider universe and the data.cms.gov utilization
files; `measure_id` joins MIPS measure inventories. Years are additive —
the upsert keys compose the year, so multi-year history coexists.

**Shape caution:** the QPP API versions its eligibility response via
`Accept` headers; this connector requests the service default and maps
fields defensively, keeping every source payload verbatim in a `raw`
JSON column so nothing is lost when the normalized columns lag the
upstream shape. Verify live before a bulk run.

## Datasets

| dataset_id | Target table | Grain |
|------------|--------------|-------|
| `qpp_eligibility` | `qpp_clinician` | clinician x performance year |
| `qpp_organizations` | `qpp_organization` | clinician x year x practice org |
| `qpp_benchmarks` | `qpp_benchmark` | measure x submission method x year |

`qpp_organizations` shares the eligibility fetch (same payload, second
grain) — one roster pull fills both tables.

## CLI

```bash
python -m connectors.qpp.cli --root var/connectors datasets
python -m connectors.qpp.cli --root var/connectors discover
python -m connectors.qpp.cli --root var/connectors fetch --dataset benchmarks --year 2025
python -m connectors.qpp.cli --root var/connectors fetch --dataset eligibility --npis 1234567893,1932296556
python -m connectors.qpp.cli --root var/connectors query qpp_benchmarks --filter measure_id=001
python -m connectors.qpp.cli --root var/connectors aggregate qpp_benchmarks --group-by submission_method
python -m connectors.qpp.cli --root var/connectors lookup-clinician 1234567893
python -m connectors.qpp.cli --root var/connectors lookup-benchmarks 001 --year 2025
python -m connectors.qpp.cli --root var/connectors serve
```

`--root` is the working dir holding `qpp.db` (`./.qpp_data` by default).
Read verbs (`query` / `aggregate` / `lookup-*`) never create the dir or
the db — a never-ingested root answers from an empty in-memory store
instead of littering the cwd.

## `/v1` surface

```
/v1/datasets
/v1/query/qpp_eligibility | qpp_organizations | qpp_benchmarks
/v1/query/{dataset}/aggregate?group_by=
/v1/lookup/qpp-clinician/{npi}
/v1/lookup/qpp-organizations/{npi}
/v1/lookup/qpp-benchmarks/{measure_id}?year=
```

The lookup nouns are `qpp`-prefixed so the unified estate router
(first-match-wins) can never confuse them with the NPI Registry's
`/v1/lookup/provider/{npi}`.

## Canonical tables

* `qpp_clinician` — `npi_year` (pk), `npi`, `year`, names, `npi_type`,
  `newly_enrolled`, specialty fields, `is_maqi`, `n_organizations`, `raw`.
* `qpp_organization` — `org_key` (pk), `npi`, `year`, `org_idx`,
  `org_name`, `facility_based`, `apms_count`, `virtual_groups_count`, `raw`.
* `qpp_benchmark` — `benchmark_key` (pk), `measure_id`,
  `performance_year`, `benchmark_year`, `submission_method`, `status`,
  `is_topped_out`, `is_inverse`, `deciles` (JSON), `raw`.

All plus the shared `source_endpoint` / `ingested_at` meta columns.
