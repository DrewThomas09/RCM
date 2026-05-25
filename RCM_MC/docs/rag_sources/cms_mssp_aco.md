# CMS Medicare Shared Savings Program (MSSP) — ACO Participants

**Source:** data.cms.gov — "Accountable Care Organization Participants"
public-use file (PY2026). Public CMS data.
**Geography:** United States (national).
**Coverage:** 511 MSSP ACOs · ~15,300 participant organizations. Build-time
snapshot; runtime reads the committed CSV (no live API). **Exec/contact PII
(names, emails, phones) is dropped on ingest.**
**Fields:** aco_id, aco_name, participant_org, service_area, risk track
(BASIC level / ENHANCED), high/low-revenue flags, start dates, public website.
**Powers:** `/cms-apm` ("National MSSP ACO Landscape" LIVE section).

**What it indicates:** the national value-based-care footprint — how many ACOs,
their risk posture (296 on the full-risk ENHANCED track), and which provider
organizations participate.

**What it does NOT prove:** it is a **participation directory, not financial /
savings / quality results**, and **not provider-specific performance**. ACO
service areas are often multi-state.

**Diligence use cases:** gauge whether a target's provider orgs are in MSSP
ACOs and at what risk level; frame value-based-care exposure nationally.

**Caveats:** participation only (no savings); national; refreshed on re-ingest.

**Suggested questions:**
- "How many MSSP ACOs are on the full-risk ENHANCED track?"
- "Is this savings/performance data or just participation?" (participation)
- "Is a specific provider org in an MSSP ACO?"
- "What's the difference between this and the Colorado APM data?" (national
  participation vs Colorado %APM of spend)
