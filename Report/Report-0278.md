# Report 0278: Source Audit of the Verified-Deals Corpus — 445 live fetches, 32 wrong facts corrected

## Scope

The platform's `data_public/verified_deals.py` is the corpus whose entire value proposition is that every deal is **real and carries a real source URL** — explicitly the seed of the "verify every deal online" effort, in contrast to the 605 synthetic seed deals. Nobody had ever checked whether those sources actually resolve or support their claims. This report is that check: 45 agents, 445 live source fetches, 978 tool calls.

## Results

| Claim verdict | Count | URL health | Count |
|---|---|---|---|
| SUPPORTED | 163 | OK | 356 |
| PARTIAL (on-topic, silent on some fields) | 108 | REDIRECT | 11 |
| UNVERIFIABLE_FROM_SOURCE | 139 | DEAD_OR_BLOCKED | **78** |
| **CONTRADICTED** | **35** | | |

The 35 contradictions split: **23 year**, 8 outcome, 4 sponsor.

Note on the 139 UNVERIFIABLE: these are overwhelmingly sponsor portfolio-index pages and paywalled trade articles that fetch fine but don't discuss the specific transaction — a *citation-quality* issue, not evidence the deal is fake.

## Corrections applied (29 + 3 dependent = 32)

Applied only where the source — usually the **sponsor's own portfolio or press page**, authoritative for their own investment date — documents a different fact than recorded.

**22 year corrections.** Several were large enough to distort any vintage or hold-period analysis built on this corpus:

| Deal | Was | Now |
|---|---|---|
| Ob Hospitalist Group | 2024 | 2017 |
| MedVet | 2025 | 2019 |
| Aurora Diagnostics | 2010 | 2006 |
| eSolutions | 2018 | 2015 |
| Community Veterinary Partners | 2023 | 2019 |
| Allucent | 2022 | 2018 |
| Allied Digestive Health | 2015 | 2021 |
| Curia (AMRI) | 2021 | 2017 |
| + 14 more (1–2 year shifts) | | |

**7 outcome corrections, `active` → `exited`** — each where the sponsor's own portfolio page marks the position Past / Realized / Exited: Mission Veterinary Partners, CCRM Fertility, Vision Innovation Partners, AGS Health, Care Hospice, The Derm Group, Meridian Behavioral Health. A corpus that reports exited positions as active overstates the live book.

**3 dependent fixes:** NextGen's `outcome_note` ("closed Nov 2024" → "closed Nov 10, 2023"), OrthoAlliance's exit year (2025 → 2024), and Convey Health's `source_url`.

## Two findings hand-verified before acting — one reversed the agent

I did not apply 35 factual edits on agent say-so. Two independent checks:

1. **NextGen Healthcare** — independently confirmed via CMS-independent search that the Thoma Bravo $1.8B take-private closed **2023-11-10**, not 2024. The agent was right; the data was wrong.
2. **Convey Health Solutions** — the agent marked it CONTRADICTED, but the record (2022 TPG take-private, ~$1.1B) is **correct**: independently confirmed closed **2022-10-07**. The cited TPG page documented the *2019* acquisition instead. So the **URL was wrong, not the data** — a different remedy entirely. Fixed the URL; left the record intact.

That second case is why the verify step exists: a "CONTRADICTED" verdict can mean *wrong record* or *wrong citation*, and blindly trusting the flag would have corrupted a correct row.

## Left unchanged, flagged for human review

Four sponsor-attribution disputes need a judgement call rather than a lookup (typically: was this sponsor the lead, a co-investor, or a later buyer?): **Netsmart** (GI Partners + Allscripts JV vs TPG + GI), **Monte Nido** (Revelstoke 2022 vs recorded Carlyle 2021), **Vital Care** (Linden/Berkshire vs recorded Pharos), **Allied OMS** (DuneGlass formation 2020 vs recorded RiverGlade 2019). Guessing here would trade one wrong fact for another.

## Corpus health

Independent of the source audit: 445 deals, **100%** carry a source URL, 418 unique URLs, and **zero** exact or near-duplicate entries (fuzzy target-name match at 0.90). The "no duplicate information" concern does not apply to this corpus — it is clean.

## Evidence

`test_verified_deals`, `test_deals_corpus`, `test_corpus_no_exact_duplicates`, `test_corpus_real_sectors`, `test_verified_corpus_bridge` → **817 passed** after the 32 edits. Commit `589789b`.

## Follow-ups

| Item | Status |
|---|---|
| 78 dead source URLs (77 with a candidate replacement) | verification pass in flight — candidates are only applied after a fetch confirms they resolve *and* name both target and sponsor |
| 139 UNVERIFIABLE citations | citation-quality upgrade: replace portfolio-index links with the specific transaction announcement |
| 4 sponsor disputes | needs owner judgement |

---

Report/Report-0278.md written.
