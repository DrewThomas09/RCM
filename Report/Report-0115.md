# Report 0115: Integration Point — `data/cms_hcris.py` + `_cms_download.py`

## Scope

Audits the CMS HCRIS public-data integration (one of 7 CMS data sources per Report 0102 MR558 critical). Sister to Report 0025 (Anthropic API), 0085 (rate_limit). Closes ~2 of 7 of MR558.

## Findings

### Module map

| File | Lines | Purpose |
|---|---|---|
| `data/cms_hcris.py` | 304 | HCRIS fetcher + parser + loader |
| `data/_cms_download.py` | 87 | Shared HTTP fetch helper for all 4-7 CMS sources |

### Integration target

**HCRIS** = Healthcare Cost Report Information System. CMS-published fiscal-year hospital cost reports. Data: provider_id (CCN), beds, discharges, case-mix-index, gross/net revenue, expenses, charity care, DSH/IME payments, location.

Per `download_hcris` docstring (lines 130-136): "CMS publishes 2-3 years behind ... we default to two calendar years before today so we don't chase a 404 on a year CMS hasn't cut yet."

### Client code path

#### Layer 1 — entry

`refresh_hcris_source(store) -> int` at line 288. Called by `data_refresh._default_refreshers` → `_hcris(store)` (Report 0102 hop 6).

#### Layer 2 — orchestrator

`refresh_hcris_source` (lines 288-304) **does NOT do a live CMS download.** Instead, it uses the shipped `hcris.csv.gz` (`DEFAULT_DATA_PATH`) — pre-built artifact that ships with the wheel (per Report 0101: `[tool.setuptools.package-data] rcm_mc = ["data/*.csv.gz"]`).

Per docstring lines 290-295:
> "Uses the shipped `hcris.csv.gz` as the authoritative source ... so that a hot refresh doesn't require re-downloading from CMS. Callers who actually want fresh data from CMS should run `rcm-mc hcris refresh --year <y>` first."

**The `/api/data/refresh/hcris` HTTP route (Report 0102) does NOT actually hit CMS** — it re-loads the local cached file. Only the explicit `rcm-mc hcris refresh` CLI command hits CMS. **Surprising design.** Cross-link Report 0102 MR561 (sync vs async).

#### Layer 3 — live download (`download_hcris` line 124-142)

Builds URL: `HCRIS_URL_TEMPLATE.format(year=year)` (line 141) — template imported from `data/hcris.py` (lines 28-29 imports, body not extracted this iteration).

Cache path: `_cms_download.cache_dir("hcris") / f"HOSP10FY{year}.zip"` (line 140).

Calls `_cms_download.fetch_url(url, dest, overwrite=overwrite)`.

#### Layer 4 — `_cms_download.fetch_url` (lines 50-80)

```python
def fetch_url(url, dest, *, timeout=60.0, overwrite=False) -> Path:
    if dest.exists() and not overwrite:
        return dest                                         # cache hit
    dest.parent.mkdir(parents=True, exist_ok=True)
    part = dest.with_suffix(dest.suffix + ".part")
    req = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            with open(part, "wb") as fh:
                shutil.copyfileobj(resp, fh)
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        part.unlink(missing_ok=True)
        raise CMSDownloadError(f"fetch failed for {url}: {exc}") from exc
    part.replace(dest)
    return dest
```

**Atomic: writes to `dest.part` first, replaces on success.** Strong file-IO discipline (no torn writes).

### Error handling

- **Custom exception**: `CMSDownloadError(RuntimeError)` (line 27-28).
- **Catches `URLError`, `TimeoutError`, `OSError`** — wraps and re-raises as `CMSDownloadError`.
- **Cleanup on failure**: `part.unlink(missing_ok=True)` removes the partial file (line 77).

### Retry logic — DOES NOT EXIST

**Module docstring (line 1-9)** claims "(cache dir, atomic fetch, respectful retry) primitive" — but the actual code has **NO RETRY LOGIC**. Single attempt; fails fast on any error.

**Cross-correction**: Report 0085 + Report 0104 noted retry-with-backoff in webhooks. `_cms_download` does NOT — single-shot. Inconsistent with docstring. **MR647 below.**

### Rate limiting

`_cms_download.fetch_url` itself does NOT rate-limit. Rate-limiting happens at the HTTP-route layer per Report 0102 (`_REFRESH_RATE_LIMITER` 1/hr/source). But CLI invocation (`rcm-mc hcris refresh`) bypasses HTTP route, so **no rate limit on CLI fetches**.

If a developer runs `rcm-mc hcris refresh --year 2020 --year 2021 --year 2022` rapidly, all three fetches happen back-to-back with no respect for CMS server load. **MR648 below.**

### Secret management

**No secrets needed.** CMS HCRIS is public data — `urllib.request.Request` with no `Authorization` header. Just User-Agent.

User-Agent string: `"rcm-mc/1.0 (+https://github.com/anthropics/rcm-mc)"` (line 24).

**Note**: User-Agent points to `github.com/anthropics/rcm-mc` — appears to be the rcm-mc Anthropics-public repo. **Possible doc inaccuracy** if the repo is private/not at that URL. **MR649 below.**

### NEW env var discovered

| Env var | Default | Purpose |
|---|---|---|
| `RCM_MC_DATA_CACHE` | `$HOME/.rcm_mc/data/<source>` else `/tmp/rcm_mc_data/<source>` | Override download cache root |

**Adds to env-var registry** (Reports 0019, 0028, 0042, 0049, 0079, 0090, 0109). Cross-link Report 0109 follow-up Q2 (build complete env-var registry).

### Cache strategy

`cache_dir(source)` (lines 31-47):
1. `RCM_MC_DATA_CACHE` env override → `<override>/<source>/`
2. else `$HOME/.rcm_mc/data/<source>/`
3. else `/tmp/rcm_mc_data/<source>/` (CI/airgap fallback)

**3-tier fallback.** All three create directory with `mkdir(parents=True, exist_ok=True)`. **Defensive.**

### Data flow continues into `hospital_benchmarks` (Report 0102 schema)

- `parse_hcris(filepath)` (line 200) → `List[HCRISRecord]`
- `HCRISRecord.benchmark_rows(period)` flattens each record into `(provider_id, source, metric_key, value, period)` rows
- `load_hcris_to_store` calls `save_benchmarks(store, all_rows, source="HCRIS", period=period)` (line 283)
- `save_benchmarks` is in `data/data_refresh.py:113` (per Report 0102 line 113)

### Column-alias resilience (lines 149-168)

`_ALIASES` dict maps each `HCRISRecord` field to **multiple acceptable CSV header names**:
- `provider_id` ← `ccn` / `provider_id` / `provider_ccn` / `prvdr_num`
- etc.

**Strong: tolerates CMS column-rename across years.** `_pick(row, aliases)` (line 171) returns the first non-empty match.

### Type coercion

- `_to_float(x)` line 178 — handles None, empty string, ValueError → returns None.
- `_to_int(x)` line 187 — float-then-int, propagates None.

**Defensive parsing.** Cross-link Report 0111: same try/except (ValueError, TypeError) discipline.

## Merge risks flagged

| ID | Risk | Severity |
|---|---|---|
| **MR647** | **`_cms_download` docstring claims "respectful retry" but code has NO RETRY LOGIC** | A transient network blip (CMS rate-limiting, packet loss) immediately raises CMSDownloadError. Should add at least 1 retry with 30s backoff. | **High** |
| **MR648** | **CLI `rcm-mc hcris refresh` bypasses HTTP rate limit** | The `_REFRESH_RATE_LIMITER` (1/hr per source) only applies to HTTP route. CLI loops can hammer CMS without circuit breaker. | Medium |
| **MR649** | **User-Agent points to `github.com/anthropics/rcm-mc`** — unverified URL | If the repo isn't at that path (e.g. private fork, internal repo), the User-Agent is misleading. CMS may rate-limit by UA. | Low |
| **MR650** | **`refresh_hcris_source` reads shipped CSV, NOT live CMS** | `/api/data/refresh/hcris` HTTP route is a misnomer — it doesn't refresh from CMS, it re-loads the cached `hcris.csv.gz`. Partner expectation may differ from reality. | **Medium** |
| **MR651** | **`HCRIS_URL_TEMPLATE` imported from `data/hcris.py`** — that module never reported | Yet another unmapped data module. Add to backlog. | Low |
| **MR652** | **NEW env var `RCM_MC_DATA_CACHE`** — never previously reported | Adds to project env-var registry. CLAUDE.md doesn't mention it. | Low |
| **MR653** | **`urllib.request.urlopen` with `timeout=60.0`** — single fixed timeout for all CMS sources | Some CMS files are MB-sized; 60s might be too short for slow connections. Configurable would be better. | Low |
| **MR654** | **`year=None` → `current_year - 2`** — implicit assumption | If CMS publishes faster (e.g. catches up to current_year - 1), the default still asks for 2 years back. Subtle staleness. | Low |
| **MR655** | **`refresh_hcris_source` raises FileNotFoundError on cold install** | Per line 299: "Run `rcm-mc hcris refresh` to build it." But: a fresh install via wheel ships the .csv.gz per pyproject — error path only fires if user deleted the shipped file. | Low |

## Dependencies

- **Incoming:** `data/data_refresh._default_refreshers` (Report 0102 hop 6), `cli.py` (`rcm-mc hcris refresh` command).
- **Outgoing:** `urllib.request`, `gzip`, `csv`, `pathlib`, `data/hcris.py` (URL template), `data/_cms_download.py` (fetch helper), `data/data_refresh.save_benchmarks` (writer).

## Open questions / Unknowns

- **Q1.** What is `HCRIS_URL_TEMPLATE` exactly? (Need to read `data/hcris.py`.)
- **Q2.** What does `data/hcris.py` (module level — different from `cms_hcris.py`) contain — is it a separate parser or just constants?
- **Q3.** Are there tests that mock `_cms_download.fetch_url` to verify offline behavior?
- **Q4.** What format is `HOSP10FY{year}.zip` — the inner CSV column shape?
- **Q5.** Do any of the OTHER 6 CMS modules (`cms_care_compare`, `cms_utilization`, `irs990_loader`, `cms_pos`, `cms_general`, `cms_hrrp`) also share `_cms_download.fetch_url`? Per `_cms_download` docstring "shared by cms_hcris / cms_care_compare / cms_utilization / irs990_loader" — confirms 4 of 7. Other 3 (cms_pos, cms_general, cms_hrrp) may use a different fetcher.

## Suggested follow-ups

| Iteration | Proposed area |
|---|---|
| **0116** | Read `data/hcris.py` (closes Q1 + Q2). |
| **0117** | Audit `data/cms_care_compare.py` (next CMS source; uses same `_cms_download`). |
| **0118** | Schema-walk `mc_simulation_runs` (Report 0110 backlog). |
| **0119** | Read `_route_quick_import_post` (Report 0114 MR639 confirmation). |

---

Report/Report-0115.md written.
Next iteration should: read `data/hcris.py` to close Q1 + Q2 (`HCRIS_URL_TEMPLATE` definition) — and disentangle `data/hcris.py` vs `data/cms_hcris.py`.
