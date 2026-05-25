# CMS Provider Supply (FFS Public Provider Enrollment)

**Source:** CMS "Medicare Fee-For-Service Public Provider Enrollment" extract
(data.cms.gov, public). Aggregated at ingest into PII-free supply counts.
**Powers:** the provider-supply density signal on `/market-intel/geo` state
profiles and the diligence Market context panel.

**Coverage:** **2.98M** Medicare-enrolled providers → counts by **state ×
provider type** (325 types) + national-by-type. National leaders: Nurse
Practitioner (413k), Clinic/Group Practice (239k), Physician Assistant (195k),
Internal Medicine (144k), Family Practice (129k). Per-state totals + an
approximate primary-care figure (family/internal/general/pediatric/geriatric
practitioner enrollments — the NAICS-621111-style supply concept).

**What it can support:** relative provider-supply density by state; demand-supply
framing when paired with senior-demand (% Age 65+); "is this market over/under-
supplied?" diligence questions.

**What it cannot support:** it is **Medicare FFS-enrolled providers only** — not
all providers (excludes MA-only / non-Medicare), **not a quality measure**, and
**not provider-specific**. The primary-care figure is a provider-type-keyword
**approximation**, not an exact NAICS count. No per-capita rate is computed
(population denominator not joined here) — raw counts only.

**Source label:** `CMS PUBLIC DATA`. PII (NPI, names, IDs) dropped at ingest
(test-enforced). Refresh by re-running `scripts/ingest_provider_supply.py`.

**Suggested Guide questions:**
- "How many Medicare-enrolled providers are in this state?"
- "What's the primary-care supply here (approx)?"
- "Is this market over- or under-supplied vs senior demand?"
- "Is this all providers?" (no — FFS Medicare-enrolled only)
- "Is this provider-specific or a quality measure?" (neither)
