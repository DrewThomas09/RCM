# CMS ownership / PECOS / Care Compare ownership — source profile & assessment

Queue item: profile the CMS ownership datasets and decide whether a new
staged ingest is warranted.

## What CMS publishes

- **CMS "All Owners" files** (SNF, Hospital, Home Health, Hospice) — direct +
  indirect ownership of Medicare-enrolled facilities (owner type, role,
  % ownership, association date). Public on data.cms.gov.
- **Change of Ownership (CHOW)** — ownership *transitions* over time.
- **PECOS / Medicare enrollment** — provider enrollment + reassignment
  (large; the "All Owners" files are the analyst-friendly ownership cut).
- **Care Compare ownership** — facility-level ownership flags within the
  Care Compare provider files.

## What PEdesk already has (no new ingest needed for these)

- **SNF All Owners** — `rcm_mc/data/snf.py` (`snf_ownership_summary`,
  `snf_top_owner_orgs`): 14,425 facilities, 280,207 owner rows, 19.4 avg /
  15 median owners per facility, 88.7% with an org owner, 51% with indirect
  ownership; owner PII dropped at ingest. Registry `cms_snf_all_owners`.
- **CHOW** (SNF + hospital ownership *changes*) — `rcm_mc/data/snf_chow.py`,
  wired to concentration-risk / msa-concentration / competitive-intel /
  antitrust-screener / market panel. Registry `cms_snf_chow` +
  `cms_hospital_chow`.
- **Provider supply** (CMS FFS enrollment by state x type) — `provider_supply.py`.

So the consolidation/M&A signal **and** SNF ownership-structure signal are
already live and Guide-documented (`cms_chow`, `cms_snf_all_owners`).

## Assessment / recommendation

The incremental value of a *new* ownership ingest is **low right now**:

- **Hospital/HHA/Hospice All Owners** would extend ownership-structure beyond
  SNF, but no current RED page needs it — the consolidation pages are already
  anchored by CHOW, and there is no dedicated "ownership structure" surface to
  feed. **Defer** until a specific page needs cross-setting ownership depth.
- **PECOS full enrollment** is large and largely redundant with the committed
  provider-supply aggregate for our purposes. **Defer** (size vs. value).
- **Care Compare ownership flags** are facility-level; useful only if/when a
  facility-level ownership view is built. **Defer.**

**Conclusion:** the cleanly-feasible, high-value ownership coverage is already
in place (SNF All Owners + CHOW). No new ownership ingest is warranted this
loop; revisit if a cross-setting ownership-structure page is requested. This
mirrors the discipline of not building large ingests without a consuming
surface.
