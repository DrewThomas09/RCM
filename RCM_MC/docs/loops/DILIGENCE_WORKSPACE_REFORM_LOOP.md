# Diligence Workspace Reform — Loop Ledger

**Started:** 2026-05-24 (autonomous 5–8h loop).
**Goal:** make every Diligence page answer *what is it for, what data powers it,
is it real/derived/illustrative, what's the next action* — and either wire it
to real data or label it honestly. HCRIS X-Ray is the gold-standard template.

**Operating rules (this loop):** small PRs · update this ledger after each ·
**no invented data** · source/purpose clarity over visual polish · continue
autonomously through docs/source-label/Guide work while approval-gated visible
PRs wait · never touch auth/deploy/env/secrets · #579/#580 parked.

---

## Route inventory (counts)
- `/diligence/*` routes: **30** (workflow + analyzers).
- Standalone analyzer routes (mostly `ui/data_public/`): **~40** (payer / cost /
  debt / physician / retention / partner / comp / drug-shortage / biosimilars /
  esg / hcit / insurance / cms-apm / payer-rate-trends / …).

## Central finding (grounded in code)
The Diligence surface has **three tiers**:
1. **Real-data (LIVE):** HCRIS X-Ray (`diligence/hcris_xray` engine) + deal-
   workflow pages tied to `PortfolioStore` / `data.pipeline` (deal, ingest,
   checklist, IC packet, questions).
2. **Illustrative layer (`ui/data_public/`):** ~14+ analyzer pages confirmed to
   use **hardcoded dataclass lists with no real loader** — Payer Stress, Cost
   Structure, Debt Service, Physician Productivity, Provider Retention, Partner
   Economics, Mgmt Comp, Drug Shortage, Biosimilars, ESG, HCIT/SaaS, Insurance,
   CMS APM, Payer Rate Trends.
3. **Reference/corpus:** Sponsor Track Record, Payer Intelligence, Find Comps,
   Comparable Outcomes (benchmark/corpus — belong in Research, callable from a deal).

→ The reform: **label tier-2 honestly (ILLUSTRATIVE / DATA REQUIRED)**, **wire
the HCRIS-derivable ones to real data** (Cost Structure & Debt Service are
computable from HCRIS fields), and **move/defer** the rest.

---

## PR log
| PR | Title | Scope | Status |
|---|---|---|---|
| 0 (#665) | docs: workspace audit + data-source matrix | docs | **merged + live** |
| 1 (#666) | feat: source-and-purpose header component + chips | additive kit | **merged + live** |
| 2 (#667) | feat: honest headers on Payer Stress / Cost Structure / Debt Service | visible UI | **open — awaiting approval** |
| — (#668) | docs: real-data conversion backlog + ledger | docs | **open (this PR)** |
| 3 | feat: HCRIS X-Ray A-v2 results | visible UI | queued (#663 merged → buildable) |
| 4 | feat: Payer Stress real HCRIS payer-mix wiring | visible UI | queued (backlog mapped) |
| 5 | feat: Cost Structure + Debt Service from HCRIS | visible UI | queued (backlog mapped) |
| 6 | feat: Checklist honesty + source-aware | visible UI | queued |
| 7 | feat: workforce/economics source pass | visible UI | queued |
| 8 | docs: defer/delete/move candidates (ESG/HCIT/Biosimilars/…) | docs | queued |

## Loop status (approval-gated ≠ idle)
- **Actively working.** PR 2 (#667) awaits approval; instead of idling, this
  tick produced the **real-data conversion backlog** (#668, docs, mergeable)
  with concrete HCRIS field→formula maps for Payer Stress / Cost Structure /
  Debt Service — which de-risks PRs 4/5.
- **Blocked-on-approval:** #667 (visible UI). **Not a stop** — docs/feasibility
  continue.

## Next three tasks
1. Merge #668 (docs) on green; continue labeling the remaining illustrative
   analyzers (Physician Productivity, Provider Retention, Partner Economics,
   Mgmt Comp, ESG, HCIT, Insurance, Biosimilars) in a follow-up header PR.
2. On #667 approval → build PR 4 (Payer Stress: seed sliders from real HCRIS
   payer-day mix when a CCN is attached; drop fabricated drivers; label proxy).
3. Build PR 3 (HCRIS A-v2 results — #663 kit merged) and PR 5 (Cost Structure +
   Debt Service HCRIS panels) per the backlog field maps.

## Update — PRs 2/2b/2c + 8 shipped; PR 3 finding
- **Merged + live:** #665 audit · #666 header · #668 backlog · #667 PR2 · #669 PR2b · #671 PR8 defer-doc.
- **Open (awaiting approval):** #670 PR2c (final illustrative labels, green).
- **14 illustrative analyzers now carry honest ILLUSTRATIVE / DATA REQUIRED headers** (PR 2/2b/2c).
- **PR 3 finding (verified in code):** the HCRIS X-Ray **results page is already A-v2 + real-data** — headline top-finding lead, real engine benchmark table, real peer roster, trend chip, source attributions, honest caveats. **Public comps are REAL** (vendored `market_intel.public_comps`), not fabricated — component map corrected. So PR 3 is **substantially already implemented**; no hollow rebuild needed.

## Next three tasks
1. **PR 4 — Payer Stress real HCRIS wiring** (label merged in #667): when a CCN is attached, seed the model from the target's real HCRIS payer-day mix; drop unsupported drivers; degrade honestly. *(Substantial build — next.)*
2. **PR 5 — Cost Structure + Debt Service HCRIS panels** (labels merged): opex/bed, opex/pt-day vs peer band (real); DSCR proxy + labeled assumption.
3. **PR 6 — Diligence Checklist honesty / source-aware** behavior.

## Update — PRs 4/5/6/7 (parallel-lane mode)
- **Open, green, approval-gated (visible / real-data):**
  - #670 PR2c — final illustrative labels.
  - #673 PR4 — Payer Stress seeded from real HCRIS payer-day mix when a CCN
    is attached; honest degradation otherwise.
  - #674 PR5 — Cost Structure + Debt Service real HCRIS opex/bed, opex/pt-day,
    operating margin; debt-service operating-cash **proxy** labeled, covenants
    DATA REQUIRED.
  - #675 PR6 — **Diligence Checklist honesty**: the per-item column was
    mislabeled "Corpus Fail%" (implying a measured frequency) when it is a
    hardcoded status→% map. Renamed to **Risk Wt.** + tooltip + caveat;
    `ck_source_purpose` header (universe = corpus when deals loaded, else
    derived). Returns benchmarks + corpus-deal count are *real*.
  - #676 PR7 — **22 pure-calculator analyzers labeled ILLUSTRATIVE**
    (`ck_illustrative_note`). Verified: their backing `data_public/*` compute
    modules have **zero** real-data signals (no DB/loader/CMS/HCRIS).

## Verified classification (this loop)
Scanned all unlabeled `data_public/*_page.py`. **22 confirmed pure-calculator
illustrative** (now labeled in #676): lbo_stress, peer_valuation,
growth_runway, rollup_economics, reinvestment, concentration_risk,
antitrust_screener, bolton_analyzer, cap_structure, deal_postmortem,
platform_maturity, redflag_scanner, tax_structure, exit_multiple,
value_creation, covenant_monitor, underwriting_model, multiple_decomp,
capital_efficiency, acq_timing, qoe_analyzer, exit_readiness.

**Still to classify** (heuristic flagged real-data signals — do NOT blanket
label; verify each): cms_apm_tracker, cms_sources, cms_data_browser,
corpus_dashboard, corpus_coverage, corpus_flags_panel, deals_library,
find_comps, sponsor_league, payer_intel, sector_intel, geo_market,
lp_dashboard/lp_reporting, module_index, data_sources_admin (several are
meta/nav or genuinely corpus/CMS-backed — real).

## Next three tasks
1. **CMS APM real-data conversion** (Lane C) — wire `cms_apm_tracker` to a real
   CMS public APM/ACO source (web/download authorized) or label DATA REQUIRED
   if no clean public feed; drop any fabricated participation figures.
2. Classify the "still to classify" set page-by-page; corpus/CMS-backed → add
   `ck_source_purpose` (real); meta/nav → no marker needed.
3. On approval, merge the green approval-gated stack (#670/#673/#674/#675/#676)
   with full deploy verification each.

## Update — PRs 8/9/10 (honesty labels, parallel-lane)
- **#678 PR8 — CMS APM honesty:** real CMMI program catalog kept as curated
  public reference (`ck_source_purpose`, universe=cms); the fabricated
  "Project …" portfolio-exposure + commercial-adjacency overlay demoted to a
  clearly-labeled ILLUSTRATIVE section; removed the unqualified "portfolio APM
  revenue at X% at risk" claim from the title meta + value anchor.
- **#679 PR9 — seed-corpus aggregates labeled:** Payer Intelligence, Sector
  Intelligence, Find Comps, Sponsor League, Deals Library, Sector Momentum.
- **#680 PR10 — seed-corpus aggregates (cont.):** Geo Market, Sector
  Correlation, Specialty Benchmarks.

### Key finding — the "deals corpus" is illustrative seed data
The pages above read `data_public.deals_corpus._SEED_DEALS + extended_seed*`
**directly** (the 35 built-in seed deals + extended seeds), with **zero
live-DB reads**. So every "corpus-calibrated" aggregate is built on bundled
illustrative deals, not the user's ingested portfolio — now disclosed via
`ck_illustrative_note` on each. Deals Library's "every deal we've ingested"
intro was corrected.

## Open approval-gated stack (all green unless noted)
#670 (PR2c) · #673 (PR4 Payer Stress HCRIS) · #674 (PR5 Cost/Debt HCRIS) ·
#675 (PR6 Checklist honesty) · #676 (PR7 22 calculator labels) · #678 (PR8 CMS
APM) · #679 (PR9 6 seed-corpus) · #680 (PR10 3 seed-corpus). **#677 docs merged.**

## Remaining to classify (likely REAL meta/nav — header only, no illus label)
corpus_dashboard, corpus_coverage, corpus_flags_panel, cms_sources,
cms_data_browser, data_sources_admin, module_index — these report actual
loaded-data / module status; give a `ck_source_purpose` header at most, not an
illustrative marker. Verify each before touching.

## Deferrals / notes
- ESG, HCIT/SaaS, Biosimilars → defer/delete (PR 8 doc); Insurance/Malpractice +
  Provider Retention + Partner Economics → DATA REQUIRED (activate on attach).
