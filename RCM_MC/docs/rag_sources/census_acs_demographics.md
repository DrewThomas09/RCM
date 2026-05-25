# Census ACS county demographics (market intelligence)

**Source:** U.S. Census Bureau American Community Survey demographics,
delivered via the keyless, redistributable **County Health Rankings &
Roadmaps** analytic file (CHR republishes Census ACS / Population Estimates /
SAHIE / SAIPE). The direct Census ACS API now requires an API key (a secret
we do not commit); CHR provides the same ACS-derived values keyless.
**Geography:** United States, **county** (5-digit FIPS preserved) + **state**
(population-weighted rollup).
**Coverage:** population, % age 65+, median household income, children-in-poverty
rate, uninsured rate, race/ethnicity (non-Hispanic White, non-Hispanic Black,
Hispanic), and % rural. Build-time snapshot; runtime reads the committed
aggregate (no live API). Percent measures stored as fractions (0–1).
**Powers:** the demographic line on the reusable **Market context** panel
(`/market-intel/geo` profiles + `/market-data` pages) — population, age mix,
income, and uninsured rate as the demand fundamentals of a market.

**What it indicates:** the underlying demand environment of a geography —
e.g. Florida's 21.6% age-65+ skew, Texas's 20.3% uninsured rate, or a county's
income and rurality — the backdrop a healthcare target operates within.

**What it does NOT prove:** these are **area-level survey estimates, not this
deal's patients** and **not a provider-specific figure**. ACS estimates carry
margins of error and reflect the pooled survey period, not a point-in-time count.

**Diligence use cases:** size a target's addressable population and payer-mix
pressure (age 65+ → Medicare exposure; uninsured/poverty → bad-debt/self-pay
risk); compare a market's demographics to national/state norms; screen
rollup geographies for demand fundamentals.

**Caveats:** ACS survey estimates (year/margin limitations matter); area-level
market context only; missingness preserved (sparse small counties blank, never
zero-filled). Refreshed on re-ingest (`scripts/ingest_county_demographics.py`).

**Suggested questions:**
- "What share of this state is 65+?" (Medicare-exposure proxy)
- "What's the uninsured rate here?" (self-pay / bad-debt risk)
- "Is this my target's patient population?" (no — area-level ACS estimate)
- "Are these exact counts?" (no — pooled survey estimates with margins of error)
