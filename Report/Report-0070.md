# Report 0070: Orphan Files — top-level `rcm_mc/` reread

## Scope

Rerun of Report 0010 orphan check on a subset to verify zero drift.

## Findings

### State

- Origin frozen — same orphan candidates as Report 0010.
- Top-level orphans: `api.py`, `lookup.py` (shim), `constants.py`.
- Subpackage orphans: `management/`, `portfolio_synergy/`, `site_neutral/`, `diligence/root_cause/`, `diligence/value/` (Reports 0010 + 0040).

### What this iteration adds

Per Report 0049/0050/0051: `infra/notifications.py` is **NOT orphan** — it's wired into alert/event paths. Per Report 0064: `auth/audit_log.py` is wired (3 server.py sites). **Recent audits resolve "is module X orphan" for several previously-uncertain modules.**

### Sister files newly checked

| File | Status |
|---|---|
| `infra/webhooks.py` | Per Report 0055 placeholder — production callers unknown; possibly orphan |
| `compliance/audit_chain.py` | Per Report 0028/0030 — wired to compliance/__init__.py + likely ingestion paths |
| `compliance/phi_scanner.py` | Per Report 0056 — wired via pre-commit hook (refines unwired-finding) |
| `data/lookup.py` | Per Report 0009 — 3 dead-in-production functions |

### True orphan inventory (consolidated)

| Path | Type | Status |
|---|---|---|
| `rcm_mc/api.py` | file | uvicorn-only (Report 0010) |
| `rcm_mc/management/*` | subpkg (8 files, ~1010 LoC) | Report 0010 MR69 |
| `rcm_mc/portfolio_synergy/*` | subpkg | Report 0010 |
| `rcm_mc/site_neutral/*` | subpkg | Report 0010 (likely dup of diligence/regulatory/site_neutral_simulator) |
| `rcm_mc/diligence/root_cause/*` | subpkg (placeholder) | Report 0040 |
| `rcm_mc/diligence/value/*` | subpkg (placeholder) | Report 0040 |
| 3 dead funcs in `data/lookup.py` | function-level | Report 0009 |
| `infra/webhooks.py` (?) | file | TBD per Report 0055 |

**~6 unique subpackages + 3 file-level orphans + 4-7 dead functions.** Stable since Report 0040.

## Merge risks flagged

| ID | Risk | Severity |
|---|---|---|
| **MR442** | **Orphan inventory unchanged across 60+ iterations** | The audit consistently rediscovers same orphans. Pre-merge cleanup pass = ~1500 LoC removable. | (advisory) |

## Dependencies

- **Incoming:** future cleanup PR.
- **Outgoing:** prior orphan reports.

## Open questions / Unknowns

- **Q1.** Read `infra/webhooks.py` to confirm orphan status.

## Suggested follow-ups

| Iteration | Area |
|---|---|
| **0071** | Config map (already requested). |
| **0072** | Data flow trace (already requested). |

---

Report/Report-0070.md written.

