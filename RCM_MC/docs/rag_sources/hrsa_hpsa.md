# HRSA Health Professional Shortage Areas (Primary Care)

**Source:** HRSA Data Warehouse — HPSA (Primary Care), public.
**Geography:** United States, **state-aggregated** (from ~78k designated detail rows).
**Coverage:** 60 states/territories; designated PC HPSA counts, median/max HPSA
score, population in shortage. Build-time snapshot; runtime reads the committed
aggregate (no live API).
**Powers:** workforce/access **context** on Physician Productivity / Provider
Retention (planned connection).

**What it indicates:** the relative primary-care workforce shortage by state —
where physician supply is tightest (higher HPSA score = greater shortage).

**What it does NOT prove:** it is **market/access context, not provider-
specific** and **not a productivity, compensation, or churn measure**. A state
shortage does not establish a given target's staffing position.

**Diligence use cases:** frame a physician-group target's market against
state-level supply scarcity; flag recruitment/retention risk environments.

**Caveats:** state aggregate of Primary Care only (Dental/Mental Health are
separate HRSA files); refreshed on re-ingest.

**Suggested questions:**
- "Which states have the worst primary-care shortage?"
- "Is this provider-specific or market context?" (market)
- "Does HPSA score measure my target's productivity?" (no)
