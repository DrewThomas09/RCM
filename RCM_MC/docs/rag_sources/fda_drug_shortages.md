# FDA Drug Shortages (openFDA)

**Source:** openFDA `drug/shortages` endpoint (U.S. Food & Drug Administration).
**License:** public domain (CC0).
**Geography:** United States (national).
**Coverage:** ~1,679 shortage records (2017–present), refreshed by a build-time
snapshot — PEdesk reads the committed snapshot, never the live API.
**Fields:** generic_name, company_name, therapeutic_category, dosage_form,
status (Current / Resolved), availability, package_ndc, posting/update dates.
**Powers:** `/drug-shortage` (LIVE "FDA Drug Shortages" section).

**What it indicates:** the current national drug-shortage landscape — which
drugs and therapeutic categories are in active shortage.

**What it does NOT prove:** it is **product-level, not provider-specific**. A
listed shortage does not by itself mean a given target is affected; that
requires the target's formulary/utilization. It also doesn't quantify financial
impact (the supplier/GPO/scenario model on the page is illustrative).

**Diligence use cases:** flag categories under broad shortage pressure
(e.g. injectables, oncology); sanity-check a pharmacy/infusion target's
exposure against the real national list.

**Caveats:** national snapshot, refreshed on re-ingest; ~31% of rows lack an
availability detail (shown "—", never inferred); not a provider join.

**Suggested questions:**
- "Which therapeutic categories have the most current shortages?"
- "Is this drug currently in FDA-listed shortage?"
- "Is this provider-specific or the national landscape?" (national)
- "What would I need to assess a specific target's shortage exposure?"
