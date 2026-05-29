# Data Freshness & Provenance

How PEdesk tracks where each dataset came from, when it was last refreshed,
and how stale "stale" actually is, so the Guide can answer "is this number
current", "when was X loaded", and "can I cite this for an IC packet".

## Why provenance matters

Every partner-facing number lands eventually in front of an IC or an LP.
Both will ask "where did that come from" and "is it current". PEdesk's
defensibility rests on being able to answer those without guessing.

## The three confidence dimensions

Each `PageContext` and `MetricContext` carries:

1. **`source_confidence`** — How well-documented the source is:
   - `DOCUMENTED` — formal source documentation exists (e.g. CMS HCRIS
     filing manual, the platform's `/methodology` page for derived
     metrics).
   - `INFERRED_FROM_PAGE` — derived by reading the page renderer + the
     loaders, not from formal documentation.
   - `UNKNOWN` — explicit placeholder until source documentation arrives.

2. **`data_confidence`** — How real the data itself is:
   - `OBSERVED_TARGET_DATA` — real data from the target / user (your
     uploaded deal data, your monthly actuals).
   - `PUBLIC_BENCHMARK_DATA` — real public data (CMS HCRIS, CMS Compare,
     HRSA HPSA, CDC PLACES, FDA, IRS Form 990).
   - `USER_ENTERED_DATA` — what the partner typed into the platform
     (overrides, manual assumptions).
   - `MIXED` — multi-source (e.g. real CMS + model prior).
   - `ILLUSTRATIVE` — scaffold values for a not-yet-activated page;
     calls itself out as illustrative.
   - `DATA_REQUIRED` — the page is structurally complete but needs the
     partner to upload data to activate. See the
     `_DATA_REQUIRED_GUIDE` registry in the manual page contexts.

3. **`formula_confidence`** (for metrics only):
   - `DOCUMENTED` — formal source documents the formula.
   - `INFERRED` — derived from code; standard textbook definition.
   - `UNKNOWN` — placeholder.

## The data catalog (`/data`)

The canonical surface for "what data is loaded and when was it
refreshed". Per-dataset row shows:

- Name, source, license terms.
- Refresh cadence (e.g. CMS HCRIS = annual, CMS Care Compare = quarterly).
- Last-loaded timestamp (when the platform pulled / updated it).
- Row count.
- Staleness flag (now - last_loaded > cadence).

Reads from `data_source_status` (SQLite table). Refresh actually happens
out-of-band via `rcm-mc data refresh-<dataset>` CLI commands or the
GitHub Actions data-refresh workflow.

## Refresh cadences by dataset (real cadences)

- **CMS HCRIS** — annual; lag of 18-24 months at any moment. The platform
  loads each filing year as CMS releases it.
- **CMS Care Compare** (Hospital / SNF / HHA / Hospice / Dialysis / IRF /
  LTCH) — quarterly. Star ratings update with each release.
- **CMS Provider Supply / NPPES** — monthly. The platform refreshes
  monthly so new providers + ownership changes flow in.
- **CMS Open Payments** — annual; loaded after the spring publication.
- **HRSA HPSA** — quarterly.
- **CDC PLACES** — annual.
- **FDA Drug Shortages** — daily via openFDA.
- **CIVHC (Colorado)** — varies per dataset (APM annual, RBP quarterly).
- **IBISWorld industry reports** — licensed; refreshed when licenses
  renew.
- **SEC EDGAR** — daily where applicable.

For partner-data sources (monthly actuals, deal store, value-creation
plans) freshness is "as of the last upload" — the page shows the
`data_as_of` timestamp.

## What "stale" means

"Stale" doesn't mean wrong. It means past the expected refresh cadence:

- A stale dataset may still be valid for analyses where the underlying
  reality is slow-moving (HCRIS labor mix doesn't change weekly).
- For monitoring (alerts, health score) stale data should be flagged but
  the page still computes; better to compute with last-known-state than
  to render an empty page.
- For citations (IC packet, LP update), partners should refresh stale
  datasets before citing. The catalog page is where they check.

## The honest-empty rule

When a dataset isn't loaded or a page's input isn't supplied, the page
renders an honest empty state ("DATA REQUIRED", "Not supplied", "—") —
**never fabricated values**. This is enforced by `surface_status.py`
which gates every route into one of four tiers:

- **GREEN** — fully wired with live data.
- **NAVY** — calculator pages that compute off the partner's inputs (and
  honestly say so).
- **DATA REQUIRED** — structurally in place, awaiting upload.
- **RED** — documented deferred (no public source); explained on the
  page.

## Audit trail

Every data refresh writes to `audit_log` with the source + row count +
timestamp + outcome. Partners reviewing why a number moved can trace it
back to the exact refresh in `/audit`.

## What the Guide should always do

When a partner asks "is this current" or "can I cite this":
- Name the dataset's source explicitly.
- Cite the last-loaded date if known.
- Mention the refresh cadence so the partner knows what to expect.
- Flag staleness honestly when the cadence is exceeded.
- Direct to `/data` for the live freshness state.
- For citation purposes, point at the source URL (CMS, HRSA, etc.) not
  the PEdesk page.

## Related surfaces

- `/data` — the freshness catalog page.
- `/cms-sources` — CMS-specific source list with deep links.
- `/methodology` — where derived-metric provenance is documented.
- `/metric-glossary` — per-metric source + formula confidence.
- `/admin/data-sources` — refresh status (admin-only).
- `/data-refresh` — manual refresh trigger.
