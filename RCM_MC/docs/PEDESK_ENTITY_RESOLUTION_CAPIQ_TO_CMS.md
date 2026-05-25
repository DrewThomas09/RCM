# PEdesk — entity resolution: Capital IQ ↔ CMS / providers

How PEdesk maps Deal Library companies (from licensed Capital IQ exports) to
healthcare **provider** entities, so financial/ownership data can be joined to
operational/quality data. Implemented in `rcm_mc/data/capiq.py`; this documents
the matching tiers, the output, the rules, and — importantly — the **validated
limits** so nobody over-promises the join.

## Goal

Given a Deal Library company (name, optional state/city/website), find the CMS
/ provider entity it corresponds to, *when one exists*, with an explicit
confidence and an auditable match method. Never fabricate an ID; never
auto-link a weak match.

## Matching tiers (strongest → weakest)

1. **Exact identifier** — NPI, CCN, or a Capital IQ ID already mapped in a prior
   run. Deterministic, confidence = 1.0.
2. **Exact normalized name + state** — `clean_name` equality scoped to the same
   state.
3. **Normalized name + city/state.**
4. **Fuzzy name + geography** — SequenceMatcher ratio over the geo-scoped
   candidate set; must clear an accept threshold *and* beat the runner-up by a
   margin, else AMBIGUOUS (today's `resolve_record` implements 4 against HCRIS).
5. **Website / domain match** — when the export carries a website and the
   provider record has one.
6. **Manual review queue** — anything below threshold or ambiguous.

## Output (`entity_resolution_candidates`)

`deal_library_company_id, source_company_name, candidate_provider_id,
candidate_provider_name, registry (hcris|nppes|care_compare|part_b),
match_method (tier), match_score, state, city, review_status
(resolved|ambiguous|unmatched|needs_review), notes`.

The persisted artifact is a **crosswalk** (ids + method + score), not a copy of
either source dataset.

## Rules

- Do **not** auto-link weak matches; ambiguity is surfaced for a human pick
  (mirrors `intake._resolve_name_to_ccn`). A wrong link corrupts the whole join.
- Show match confidence + method on every link.
- Preserve unmatched records as unmatched; never invent a provider id.
- A resolved match may be **enriched** with that registry's public fields
  (e.g. HCRIS beds/margin/payer-mix); enrichment is labeled as derived from the
  registry, never as a licensed-export fact.

## Validated reality — yield depends entirely on the input

The first two licensed exports are **sponsor-backed healthcare companies**, not
hospitals. On a 120-row sample, **0% resolved to HCRIS** — because HCRIS is a
**hospital-only** registry and this universe is largely non-hospital (VC-backed
startups, devices, services, SaaS, physician groups, REITs, public mega-caps).
The resolver is correct; the *match rate* is a property of the input.

To get real yield:

| Input export | Best registry | Expected yield |
|---|---|---|
| Hospitals / health systems | **HCRIS** (CCN) | high |
| Home health / hospice / SNF / dialysis | **CMS Care Compare** | moderate |
| Physician groups / practices | **NPPES (NPI)** + **Part B** | moderate, name-noisy |
| Devices / SaaS / pharma / VC startups | none (not Medicare providers) | ~0 |

**Recommendation:** run entity resolution on **provider-like** exports, and add
NPPES + Care Compare resolvers alongside the existing HCRIS one before
promising a company↔provider join on a general company screen. Until then the
crosswalk is built and correct but should be applied selectively, with its
yield stated honestly on screen.
