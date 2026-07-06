# NIH RePORTER connector (`connectors/nih_reporter`)

Self-contained, **stdlib-only** connector for the NIH RePORTER v2 API
(`api.reporter.nih.gov`) — every NIH-funded project (grants, contracts,
intramural) plus the project ↔ PubMed publication links. Public API, no
key, no auth.

Built to the estate contract (mirrors `connectors/cms_coverage`):

```
endpoints ─▶ transport.post_json ─▶ connector.fetch()/refresh() ─▶ raw pages
                                                                        │
                                                                  normalize ─▶ nih_projects / nih_publications (SQLite)
                                                                        │              │
                                                                    registry ─▶ /v1/query/{dataset} + /aggregate
                                                                                  /v1/lookup/grant, /v1/lookup/grantee-org
```

## The API (live-verified 2026-07)

Unlike the estate's GET connectors, **every RePORTER search is an HTTP
POST** with a JSON body:

```
POST https://api.reporter.nih.gov/v2/projects/search
{"criteria": {"fiscal_years": [2025], "org_states": ["TX"]},
 "offset": 0, "limit": 500}
→ {"meta": {"total": 4036, "offset": 0, "limit": 500, ...},
   "results": [{appl_id, project_num, organization: {...}, ...}]}
```

so `transport.py`'s workhorse is `post_json(path, body, opener=...)` —
same retry envelope (429/5xx/transport errors with exponential backoff +
full jitter, `Retry-After` honoured), injectable opener whose signature
carries the encoded POST body: `(url, data, headers, timeout_s) →
RawResponse`.

### Hard paging limits (verified live; the API enforces both as 400s)

| Limit | Value | Live error shape |
|-------|-------|------------------|
| `limit` per request | **500** | `400` + `["System doesn't support limit value greater than 500. …"]` |
| `offset` maximum | **14,999** | `400` + `["System doesn't support offset value greater than 14,999. …"]` |

One criteria set can therefore surface at most ~15.5k rows (offset
14,999 + limit 500). The connector absorbs paging by stepping `offset`
inside the POST body; when a result set is deeper than the reachable
window it stops and reports `truncated: true` instead of erroring —
narrow the criteria (per fiscal year / state / IC) to go deeper.
RePORTER's own guidance: **≤ 1 request/second**, so the transport's
default inter-request floor is a full second (a courtesy default, not a
contract — verify live before a bulk run). Data refreshes weekly.

`fetch_all`/`refresh`/CLI `fetch` are additionally capped by
`max_pages` (default **5** → ≤ 2,500 rows per run) because *empty
criteria match every RePORTER record* — an unbounded drain must be an
explicit caller decision (`--max-pages 30`), never an accident.

## Datasets

| dataset_id | Endpoint | Table | PK | Notes |
|------------|----------|-------|----|----|
| `nih_reporter_projects` | `POST /v2/projects/search` | `nih_projects` | `appl_id` (native, globally unique) | one row per application × fiscal year × subproject |
| `nih_reporter_publications` | `POST /v2/publications/search` | `nih_publications` | `pub_key` = `{pmid}:{applid}` | link **edges**: one paper ↔ one supporting application |

`nih_projects` flattens the nested payload: `organization.*` →
`org_name/org_city/org_state/org_zipcode/org_uei/…`,
`agency_ic_admin` → the IC abbreviation (e.g. `NIGMS`) +
`agency_ic_admin_name`, `geo_lat_lon` → `org_latitude/org_longitude`,
person lists → `"; "`-joined `pi_names` / `program_officer_names`
(plus `pi_profile_ids`). Money fields (`award_amount`,
`direct_cost_amt`, `indirect_cost_amt`) are stored TEXT like the whole
estate; cast explicitly when summing.

**Deliberately dropped fields** (bulky blobs / redundant splits;
excluded from the normalize drift audit): `abstract_text`, `phr_text`,
`pref_terms`, `terms`, `spending_categories` (internal numeric ids —
`spending_categories_desc` is kept), `project_num_split` (redundant
with `project_num`), `agency_ic_fundings` (per-IC split; the totals are
kept).

**Publications caveat**: the live `/v2/publications/search` returns
*only* `{coreproject, pmid, applid}` — no title/author/pub-year despite
what older docs suggest (the assignment's `pubyear` does not exist in
the live v2 response). Join `pmid` out to PubMed for metadata.

### Criteria helpers (shapes verified live)

```python
NihReporterConnector.project_criteria(
    fiscal_years=[2025], org_states=["TX"], org_names=["MD ANDERSON"],
    pi_names=["Aballay"],            # wrapped to [{"any_name": ...}]
    activity_codes=["R01"],
    advanced_text_search="oncology", # → {operator, search_field, search_text}
    extra={...})                     # any further native criteria verbatim
NihReporterConnector.publication_criteria(
    core_project_nums=["R37GM070977"], appl_ids=[11184227], pmids=[23959030])
```

## Usage

```bash
# The registry / endpoint specs
python -m connectors.nih_reporter.cli datasets
python -m connectors.nih_reporter.cli discover

# Ingest: FY2025 Texas projects, one page (500 rows) — smoke-sized
python -m connectors.nih_reporter.cli --db ./nih.db fetch \
    --fiscal-year 2025 --state TX --max-pages 1

# Publications for a grant
python -m connectors.nih_reporter.cli --db ./nih.db fetch \
    --dataset publications --core-project-num R37GM070977

# Query the canonical tables (uniform estate grammar)
python -m connectors.nih_reporter.cli --db ./nih.db query \
    nih_reporter_projects --filter org_state=TX \
    --filter award_amount__gte=1000000 --sort -award_amount --limit 5

# Lookups
python -m connectors.nih_reporter.cli --db ./nih.db lookup-grant R37GM070977
python -m connectors.nih_reporter.cli --db ./nih.db lookup-grantee-org "MD ANDERSON"

# Standalone /v1 surface
python -m connectors.nih_reporter.cli --db ./nih.db serve --port 8099
```

### `/v1` routes (standalone server)

```
/health
/v1/datasets
/v1/query/{dataset}?<filters>&select=&sort=&limit=&offset=
/v1/query/{dataset}/aggregate?group_by=a,b&<filters>&limit=
/v1/lookup/grant/{project_num}          full (5R37GM070977-24) or core (R37GM070977) number
/v1/lookup/grantee-org/{name}[?limit=N] LIKE match over org_name → award aggregate
```

## Tests

```bash
cd /home/user/RCM
python3 -m unittest discover -s connectors/nih_reporter/tests -t . -v
```

No network: every fixture in `tests/fakes.py` mirrors the live response
shapes probed 2026-07 (including the 400 array-of-strings validation
errors). A live smoke is manual only:
`python -m connectors.nih_reporter.cli fetch --fiscal-year 2025 --state TX --max-pages 1`.
