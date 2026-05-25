# PEdesk Market Intelligence (licensed SimplyAnalytics-derived)

**Source:** Licensed SimplyAnalytics exports (business account), normalized into
PEdesk's market schema. **Raw exports and map screenshots stay private** — not
committed, not served. Screenshots are **design references only**; the data
comes from the underlying tabular exports.
**Powers:** `/market-intel/geo`, `/market-intel/geo/<fips>`, Target Screener
market signals, and market-context panels on diligence/provider pages.

**Coverage (current):** state-level **% Age 65+ (2025)** by FIPS (52 rows),
with national percentiles. FIPS preserved as zero-padded strings.

**Export backlog (shown in screenshots, NOT yet data — render as EXPORT
REQUIRED, never fabricated):** Median Household Income (2025), % Private Health
Insurance (B27002, 2023), % No Health Insurance (2025), NAICS 621111 provider
supply — all county-level. County-level age-65+ is also export-required (the
current export is state-level).

**What it can support:** rank/score geographic markets by senior demand (and,
as exports arrive, income, payer mix, uninsured burden, provider supply);
frame "is this market attractive?" diligence questions.

**What it cannot support:** it is **market/area context, not provider-specific**;
county values can mask submarket variation; only variables with an underlying
export are real. The market score is **formula-driven and partial**: with only
% Age 65+ available, only a **demand_score = national percentile(age 65+)** is
computed — payer/income/supply score components are EXPORT REQUIRED and not
invented. Combine with CMS/HCRIS/provider data before any decision.

**Source label:** `LICENSED MARKET DATA DERIVED` / `SIMPLYANALYTICS DERIVED`.

**Suggested Guide questions:**
- "Which markets have the highest senior (65+) demand?"
- "What is this state's senior-demand percentile?"
- "Is this market context or provider-specific?" (context)
- "Which market variables are real vs export-required?"
- "How does this connect to the Target Screener / HCRIS X-Ray?"
- "What export would make payer mix / provider supply real here?"
