# CBSA metro/micro demographics (geographic market sizing)

**Source:** the U.S. Census Bureau / OMB **Core-Based Statistical Area
delineation** (July 2023, OMB Bulletin 23-01) — a keyless, public-domain
crosswalk of every county to its metro/micro area — joined to county-level
Census ACS demographics (delivered via the keyless County Health Rankings
file; see the Census ACS card). **Geography:** United States, **CBSA**
(metro + micropolitan areas), rolled up from counties.
**Coverage:** 935 CBSAs in the crosswalk; 918 carry demographics (~311.8M
people): population, % age 65+, median household income, uninsured rate, and
% rural. Build-time snapshot; runtime reads the committed crosswalk + county
aggregates (no live API).
**Powers:** the **Metro Markets** page (`/metro-markets`) — the real-data
metro analyzer and the real counterpart to the illustrative `/geo-market`
white-space tool.

**What it indicates:** real metro-level market scale and mix at the unit a
healthcare deal is usually scoped to — e.g. the New York metro's ~19.6M
population across 22 counties, or how a target's metro compares on age mix,
income, and uninsured rate.

**What it does NOT prove:** these are **area-level** roll-ups of ACS survey
estimates, **not** a deal's catchment or patient panel. Population is a real
sum and the rates are population-weighted means, but **median household income
is a population-weighted estimate** of county medians, not a surveyed CBSA
median. Counties without a demographic row are excluded from a CBSA's roll-up,
never fabricated.
