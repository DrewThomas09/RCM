# Report 0144: Cross-Cutting — Retry Logic

## Scope

Documents every retry-bearing code path in the project. Sister to Reports 0024 (logging), 0054 (caching), 0084 (auth), 0114 (CSRF). **Cross-cuts retries for the first time.**

## Findings

### Retry implementations across the codebase

| Module | Retries | Backoff | Source |
|---|---|---|---|
| `infra/webhooks.py` | **3** | exponential `2 ** attempt` (1s, 2s, 4s) | Report 0104 line 107 |
| `data/_cms_download.py` | **0** (single attempt) | n/a | Report 0115 MR647 high — docstring claims retries; code has none |
| `infra/rate_limit.py` | n/a (rate-limiter, not retry) | — | Report 0085 |
| `infra/job_queue.py` | n/a (idempotency-key dedup) | — | Report 0103 |
| `auth/auth.py` (login) | **5/min per-IP rate limit** (not retry) | — | Report 0108 |
| `data/data_refresh.py refresh_all_sources` | **0** explicit; per-source (`fn(store)`) wrapped in try/except — no retry | — | Report 0102 |
| `analysis/refresh_scheduler.py auto_refresh_stale` | **0** — failed deals just logged, skipped | — | Report 0111 |
| HTTP fetch in `data/_cms_download.fetch_url` | **0** | — | Report 0115 |
| `analysis/packet_builder.py` | **0** explicit; substep failures logged + tolerated | — | Report 0140 |
| `urllib.request.urlopen` calls | **0** (no built-in retry) | — | various |

### Retry-discipline summary

**Only ONE module implements explicit retries**: `infra/webhooks.py:101-123 _deliver` with 3-attempt exponential backoff.

**Everywhere else**: single-shot. If failure happens, error is propagated, logged, or silently tolerated (per Report 0140 broad-except pattern).

### Inconsistencies — major

| Concern | Webhooks | CMS download | Auth | Job queue |
|---|---|---|---|---|
| Retry count | 3 | 0 (claims "respectful retry" — Report 0115 MR647 doc-vs-code mismatch) | n/a | n/a |
| Backoff | exponential | — | — | — |
| Failure record | DB row INSERT (Report 0104 schema) | exception raised | per-IP fail log | job.status="failed" |
| Logged | YES (delivered_at + error column) | per `CMSDownloadError` | logger + audit_log | logger.warning per Report 0103 |

**4 distinct strategies for "what to do when network/external call fails."** No shared retry helper.

### Cross-link Report 0115 MR647 (CMS download docstring lie)

`_cms_download.py` module docstring says "respectful retry primitive" — code has ZERO retry. **HIGH risk** transient CMS hiccup → instant `CMSDownloadError`.

### Cross-link Report 0104 webhooks retry — bug

Per Report 0104 MR582: `webhook_deliveries.attempts` always recorded as 1 even after 3 retries. **Retry logic exists but tracking is broken.**

### What a unified retry helper would look like

If the project had a shared `infra/retry.py`:

```python
def with_retries(fn, *, attempts=3, backoff=lambda i: 2**i, on_fail=None):
    last_exc = None
    for i in range(attempts):
        try:
            return fn()
        except Exception as exc:
            last_exc = exc
            if i < attempts - 1:
                time.sleep(backoff(i))
    if on_fail:
        on_fail(last_exc)
    raise last_exc
```

Could replace:
- `infra/webhooks.py:101-123` (3-retry exponential)
- `data/_cms_download.py:50-80` (currently 0-retry — docstring claims respectful retry)
- Future external calls

**No such helper exists.** Each module rolls its own (or doesn't).

### Network calls without retries (HIGH-PRIORITY surface)

| Site | Call | Retry? |
|---|---|---|
| `data/_cms_download.fetch_url` | `urllib.request.urlopen` | NO |
| `data/cms_*.py` (7 modules) | per-source HTTP via `_cms_download` | NO (inherits) |
| `infra/notifications.py` | webhook/SMTP (per Report 0049) | (TBD) |
| `rcm_mc_diligence/ingest/connector.py:200` | `dbt.cli.main.dbtRunner` invocation | (TBD) |

### Cross-link Report 0136 pyarrow CVE

`pyarrow.parquet.read_table(path)` on user-uploaded files → no retry needed (file IO, not network). But also no validation. Different concern; not retry-related.

### Per-iteration mention count

This is the FIRST time retries are cross-cut. Reports 0085, 0102, 0104, 0115 individually noted retry behavior (or absence) for their target module. **No prior iteration synthesized.**

## Merge risks flagged

| ID | Risk | Severity |
|---|---|---|
| **MR800** | **No shared retry helper** — every module rolls its own (or none) | Cross-link Report 0104 (webhooks 3-retry, broken `attempts` tracking) + Report 0115 MR647 (CMS download claims retries, has none). 4+ inconsistent strategies. **Should ship `infra/retry.py`.** | **High** |
| **MR801** | **CMS-download path has ZERO retries** despite handling external network IO | Cross-link Report 0115 MR647 high (carried). Transient CMS 503 → instant `CMSDownloadError`. Should be 2-3 retries with backoff. | **High** |
| **MR802** | **No retry on dbt-core invocation** (MR773 cross-link Report 0136) | If dbt run hits transient issue, no recovery. | Medium |
| **MR803** | **No retry on smtp/webhook receivers** beyond `infra/webhooks.py` 3-retry | If `infra/notifications.py` doesn't retry (Report 0049 — not extracted), single-shot failure. | Medium |
| **MR804** | **Webhook retry tracking is broken** — Report 0104 MR582 carried (`attempts` always 1) | Bug in the one module that actually retries. | (carried) |

## Dependencies

- **Incoming:** every external-call path benefits from retry discipline.
- **Outgoing:** stdlib `time.sleep` and per-module logger.

## Open questions / Unknowns

- **Q1.** Does `infra/notifications.py` have retry logic? (Report 0049/0050/0051 didn't characterize.)
- **Q2.** Does `dbt.cli.main.dbtRunner` invocation in `connector.py:200` have any wrapper retry?
- **Q3.** Should `infra/retry.py` be a refactor target now or post-feat/ui-rework-v3 merge?

## Suggested follow-ups

| Iteration | Proposed area |
|---|---|
| **0145** | Integration point (in flight). |
| **0146** | CI/CD (in flight). |
| **0147** | Read `infra/notifications.py` retry behavior (closes Q1). |

---

Report/Report-0144.md written.
