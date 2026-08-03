# Report 0279: Citation-Quality Upgrade — 98 weak sources replaced, 20 more wrong years found

## Scope

Report-0278's audit left 139 deals whose source URL *resolves* but doesn't actually document the transaction — sponsor portfolio-index pages, paywalled articles, generic newsrooms. A citation that can't be checked is barely better than no citation in a corpus whose premise is verifiability. This pass located and verified a specific transaction announcement for each. 20 agents, 935 tool calls.

## Results

| Outcome | Count |
|---|---|
| Specific citation located **and fetched** | 98 |
| Located but **conflicts with the record** | 28 |
| Honestly not found | 13 |

The 13 not-found were returned as `found=false` rather than a plausible-looking guess. In a corpus like this a 404 is worse than an admitted gap, so the agents were instructed never to return a URL they hadn't successfully read.

## 98 citation upgrades applied (commit `76a1b41`)

Now overwhelmingly primary sources: **13 SEC EDGAR filings**, 15 PR Newswire, 4 Business Wire, 3 GlobeNewswire, plus sponsor newsrooms (Thoma Bravo, Kohlberg, Audax, Metalmark). Examples:

- **LifePoint Health** → the 8-K closing exhibit: *"LifePoint Health, Inc. today announced the completion of its merger with RCCH HealthCare Partners, which is owned by certain funds managed by affiliates of Apollo Global Management"* ($65.00/share).
- **Envision Healthcare** → 8-K Ex-99.1 stating *"Enterprise Value of $9.9 Billion"* — corroborating the recorded EV exactly.
- **TeamHealth** ($6.1B), **US Oncology** ($1.7B), **Surgical Care Affiliates**, **IASIS Healthcare** (S-4) — all independently confirming recorded figures.

Unique sources across the corpus: **425 → 436**.

## 20 more year corrections (commit `57ab6a3`)

Hunting for citations surfaced **28 additional conflicts** beyond the 35 the first audit found. Applied the 20 where the fetched page documents the **recorded sponsor's own** transaction at a different year — and repointed each row to that announcement, so record and citation now agree:

| Deal | Was | Now | Verified against |
|---|---|---|---|
| TekniPlex | 2020 | 2017 | Genstar's own release |
| Drive DeVilbiss | 2013 | 2016 | CD&R's own release |
| Smile Brands | 2019 | 2016 | Gryphon's own release |
| Gastro Health | 2018 | 2016 | Audax release |
| Thrive Skilled Pediatric | 2019 | 2016 | Summit page: "Invested in 2016" |
| Aqua Dermatology | 2019 | 2016 | GTCR completion release |
| WellSky | 2017 | 2020 | TPG newsroom |
| AmeriVet | 2020 | 2022 | AEA announcement |
| + 12 more | | | sponsor/target primary sources |

Unique sources: **436 → 439**.

## 8 held for owner judgement

These are not lookups — the located page describes a *different transaction or sponsor* than the row, so "correcting" it would mean deciding which deal the row is supposed to represent:

| Deal | Tension |
|---|---|
| Comprehensive Pharmacy Services | explicit sponsor mismatch — page documents sale to **Frazier Healthcare**, record says BlackRock |
| Radiology Partners | record NEA 2018 vs page Starr Investment $700M 2019 |
| Sound Physicians | record Summit 2014 vs page Fresenius divestiture 2018 |
| Aspen Dental | record Leonard Green vs page American Securities recapitalization |
| IVIRMA Global | record KKR 2017 vs Jones Day page "KKR acquires IVI-RMA" Jan 2023 (€3B) |
| Behavioral Health Group, Press Ganey, Aegis Sciences | seller-side or later-event pages |

## Cumulative effect of the sourcing program

| Metric | Before | After |
|---|---|---|
| Wrong facts corrected | — | **52** (42 year, 7 outcome, 3 dependent) |
| Dead source URLs | 78 | **16** (62 repaired) |
| Citations that don't document their deal | 139 | **41** (98 upgraded) |
| Unique sources | 418 | **439** |
| Flagged for owner judgement | — | 13 |

817 tests green after every step. The corpus still has zero duplicate entries.

## Follow-ups

- 41 remaining weak citations + 16 unrepaired dead links (no verified replacement found).
- 13 items needing owner judgement (4 sponsor disputes from 0278, 8 here, IVIRMA from the link repair).
- Batch 2 (`market_reports/` claim fact-check) and batch 3 (semantic cross-page dedupe) still queued.

---

Report/Report-0279.md written.
