# Source Profile — CMS SNF All Owners (ownership complexity)

**Source:** CMS "Skilled Nursing Facility All Owners" (`data.cms.gov`), public.
**What it is:** owner-level records for every Medicare-enrolled SNF — owner
type (Individual/Organization), role (direct/indirect ownership, managerial
control, 5%+ interest), names, association dates.

## Grain & size
- Owner-level: **~280k rows / ~50 MB**, owner PII (names, IDs). Facility keyed
  by `ENROLLMENT ID` (no facility-state column in this file).

## Staged ingest (this PR)
Aggregate per facility, then to a **national PII-free** summary (owner names/IDs
dropped): facilities (14,425), median owners/facility (15), % with
organizational owners (88.7%), % with indirect ownership (51.0%). Surfaced on
`/nursing-homes` as an ownership-complexity note.

## What it is / isn't
- A real **corporate-complexity / chain-ownership** signal (high owner counts +
  indirect ownership ≈ chain/holding structures).
- **NOT a private-equity flag** — CMS does not label PE in this file; we do not
  infer it.
- NOT provider-specific performance.

## Follow-up (deferred)
- Per-facility **state-keying** needs a join from `ENROLLMENT ID` → CCN → state
  (via the provider-enrollment / SNF-provider crosswalk) to enable state-level
  ownership-complexity in the market panel.
- Owner-organization rollups (which orgs own the most facilities) — feasible
  from the same file with org-name aggregation (PII-safe for org names).
