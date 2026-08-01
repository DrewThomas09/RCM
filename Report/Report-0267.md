# Report 0267: Auditing the Last Landed-Unaudited Surfaces — 2 HIGH security bugs found + fixed (commit cc51351)

## Scope

The final four open TRIAGE items: the three surfaces that landed on main in the July feat/ui-rework-v3 merge and were never read (MR1019 infra/exports.py, MR1020 server.py route delta, MR1021 screening/dashboard.py) plus the infra README gap (MR1053). A 3-agent parallel audit read each surface; **two turned up real HIGH security bugs** that had nothing to do with their original TRIAGE framing. All findings were verified against the code (and MR1019 reproduced empirically) before fixing.

Sister reports: 0247 (feat-merge landed-file inventory), 0259 (canonical_facade audit), 0212 (XSS/trust-boundary origin), 0262 (verification sweep).

## The audit reframed two items

Both HIGH bugs share a root cause the TRIAGE never named: **deal_id is partner-supplied and format-unvalidated** (the /api/deals/import and import-csv routes accept it with only a non-empty `.strip()` check, and `store.upsert_deal` persists it as-is). It then flows into two dangerous sinks.

### MR1019 (HIGH) — path traversal in infra/exports.py

`_resolve_export_path` validated only `filename` for separators; `deal_id` flowed straight into `base / scope` + `mkdir`. Reproduced empirically:

```
canonical_deal_export_path("../escaped", "x.html", base=<tmp>/exports)
  -> /tmp/.../escaped/2026-...T..._x.html   (OUTSIDE base)
  -> directory physically created outside the exports root
```

`exports.py` is, by its own docstring, the single chokepoint every export writer routes through — so the guard sat on the safe input (filename, almost always a hardcoded literal) and was missing on the dangerous one. **Fix:** `_reject_path_chars` (separators on every platform, `.`/`..`, absolute paths) applied to deal_id, filename, and timestamp; plus an `is_relative_to(base.resolve())` containment backstop that fires even if a future caller sneaks a bad component past the per-component checks. Closes the LOW timestamp-bypass sub-finding too.

### MR1021 (HIGH + MEDIUM) — stored + reflected XSS in the screening surface

The TRIAGE premise was wrong (no `bankruptcy_survivor` code in `screening/dashboard.py` — that lives in `diligence/screening/`; this file's only commit is the July CMS-connectors PR, not the feat merge). Audited as what it is — the deal-screening dashboard — and found:

- **Stored XSS (HIGH):** `deal_id` was `html.escape`d into an `onclick="window.location='...'"` JS-string. `html.escape` is the wrong codec there — the browser HTML-decodes the attribute *before* the JS parser runs, so `&#x27;` reverts to `'` and breaks out of the string literal, executing attacker JS. Cross-user: the dashboard lists every non-archived deal. **Fix:** percent-encode the URL segment with `urllib.parse.quote(deal_id, safe='')` — correct URL handling that yields only `[A-Za-z0-9_.~%-]`, safe in both JS-string and attribute contexts.
- **Reflected XSS (MEDIUM):** the feeding route (server.py:7251) parsed `size_min/size_max/confidence_floor` with `float()` and reflected the raw `ValueError` message (which embeds the offending query-param string) unescaped into the 500 page. **Fix:** `html.escape` the reflected exception type + message.
- **LOW:** median-uplift KPI used `sorted[n//2]` (upper-middle) for even universes; now averages the two central values.

### MR1020 — clean-close confirmed

Programmatic scan of every server.py dispatch chain (586 GET path literals + POST/PUT/DELETE + `_route_api`): zero duplicate route registrations. `/app`, `/app/cards`, `/dashboard` each registered once; `?ui=v3` is a per-request render branch, not a route, so collision is impossible by construction. `tests/test_palette_routes.py` + `test_v3_route_inventory.py` pin registry uniqueness. No code change.

### MR1053 — infra README

Added the two missing sections (`cache.py` — the TTL function-cache decorator, distinguished from the endpoint-level `response_cache.py`; `morning_digest.py` — the 8 AM partner email reusing dashboard compute). The only remaining undocumented infra module is `exports.py` itself (tracked below).

## Evidence

- MR1019 reproduced pre-fix; post-fix `test_export_path_traversal.py` (7 tests: parent-traversal, absolute, separator, filename-guard, timestamp-guard rejected; legit deal_id + portfolio path stay within base).
- MR1021 `test_screening.py` +3 (malicious deal_id cannot break out of onclick; reflected-exc path; even-median renders); existing screening/ui-contract/canonical_facade suites green.
- Regression surface: `test_export_pipeline`, `test_exports_end_to_end`, `test_packet_exports`, `test_dev_seed` → 56 passed; screening/ui-contract/canonical → 55 passed.

## TRIAGE status after this report

**All CRITICAL / HIGH / MEDIUM / LOW items are now closed.** The actionable TRIAGE queue is empty for the first time since the list was built (2026-04-26). Two low-severity carry-forwards remain as tracked notes, not queue items:

| Note | Item |
|---|---|
| MR1069 (LOW) | infra/exports.py is still undocumented in infra/README.md (28 of 29 modules covered). |
| MR1070 (LOW) | Same-second export collisions silently overwrite via canonical_facade's shutil.move (dev/seed staggers by hours to avoid it; partner-driven exports don't). MR1019's MEDIUM sub-finding — deferred as it needs a uniqueness-suffix design decision, not a security fix. |
| Root fix (deferred) | Validate deal_id to a safe slug at the ingestion boundary (import routes / upsert_deal) so neither sink depends on downstream escaping. Larger blast radius (existing deal_ids); the two sink-level fixes here are the safe immediate close. |

## Suggested follow-ups

| Iteration | Proposed area |
|---|---|
| next | Loop pivots to fresh audit sweeps — the TRIAGE backlog names never-mapped areas: pe_intelligence/ (270+ submodules), data_public/ (313 files), ~10 small subpackages (Report 0190), and a re-promotion grep over pre-Report-0085 MRs. Also: a PROGRESS rollup for this session, and consider the deal_id ingestion-boundary root fix. |

---

Report/Report-0267.md written.
