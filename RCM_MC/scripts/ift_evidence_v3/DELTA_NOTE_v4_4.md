# IFT Sourced Evidence Master v4.4 - delta note

## Run 8: the four player tiers, each with its own public-data fingerprint - the guidance that tells you which asset actually sees an operator

Run 7 answered *how to size* (fleet, not licensed EMTs) and *why the national
brands are invisible* in NPPES. Run 8 turns that into an operator-tier map: the
four commercial IFT tiers - **National / Scaled-regional / Subscaled-regional /
Local mom-and-pop** - and, for each, the public-data asset that actually sees it
and the systematic bias the record introduces. It refines the `ift_competitive`
archetypes (which had National / Scaled-regional / mom-and-pop) by inserting the
**subscaled-regional** tier, and it ships a queryable module,
`rcm_mc/market_reports/ift_player_tiers.py`, so the guidance is live in PE Desk,
not just prose. Appended F633-F639, sources S455-S457, finding 119; no shipped ID
renumbered.

## Tier_Fingerprint (the new tab, Panel A - OBSERVED, tier A)

The decisive new evidence is that **name-based discovery in NPPES is
tier-dependent**. Live NPI Registry API probes (NPI-2, 2026-07-20), re-run with
wildcards so the counts are not a matching artifact:

| Fact | `organization_name` | NPIs | Reading |
|---|---|---:|---|
| F633 | `Global Medical Response*` | **0** | Wildcard-confirmed: the national parent has no NPI. `Priority Ambulance*` → **8**, but only **3** (Shoals Ambulance LLC) are the real Knoxville roll-up; the other 5 are unrelated "Priority Ambulance" **name-collisions**. So the national name-search is both under-representative *and* polluted. (Refines F624/F627.) |
| F634 | `Acadian Ambulance*` | **12** | Scaled-regional fingerprint: **findable** - parent + clean state-suffixed LLCs (LA/TX/MS/TN/AL), air arm included. |
| F635 | `Falck*` | **17** | Scaled-regional with noise: ~10 regional ambulance corps (Falck [region] Corp) **plus** same-name non-ambulance companies (Falck Eye Center, Falck Therapy) - filter by taxonomy 3416*, not name. |

The pattern: name-based discovery **works** for scaled-regionals (Acadian/Falck),
is **partial** for subscaled-regionals (single-corridor NPIs, ~20x vehicle
undercount), and **fails** for national roll-ups (GMR 0; Priority 3-of-8) - because
nationals grow by acquiring and keeping local brands.

## Operator_Scale_Reference (Panel B - CLAIMED / SEC, tier C-B)

New anchors that set the tier bands (carried CLAIMED; never a market measurement):

- **F636 - Acadian Ambulance (scaled regional):** 750 ground ambulances, ~800,000
  transports/yr, 4 states (LA/TX/MS/TN), 8 helicopters + 5 fixed-wing, ~$500M-$734M
  revenue (Wikipedia / acadian.com, S456). Note: Acadian's 800K transports *exceed*
  Priority's 610K - "national" is a roll-up/contracting structure, not necessarily
  the largest volume.
- **F637 - DocGo (NASDAQ: DCGO, scaled regional):** FY2024 total revenue $616.6M;
  Transportation Services segment ~$190M/yr (emergency + non-emergency + wheelchair)
  (DocGo FY2024 10-K/8-K, S457, tier B - a filer's own audited figure).

## Fleet_vs_Labor + Tier_Guidance (Panel C - DERIVED framework)

- **F638 (DERIVED / MODELED):** the four-tier band table (transports / fleet /
  revenue / NPIs-per-operator) encoded in `ift_player_tiers._TIERS`. Bands are wide
  and indicative, quarantined until the measured panel (Run 7 human action item)
  replaces them.
- **F639 (DERIVED):** the per-tier **public-data recipe** - National: fleet +
  SEC/PE + CMS MUP through an ownership crosswalk (never name-match). Scaled-
  regional: NPPES parent+regional entities + CMS MUP + disclosures (strip name
  collisions). Subscaled-regional: state vehicle permits + CMS MUP + 990s, *not*
  third-party revenue (they disagree ~3x). Mom-and-pop: size the pool
  statistically from the Finding #46 universes (10,465 PECOS / 8,721 billing /
  5,820 QCEW), never per firm.

**Finding 119:** IFT operator tiers have distinct public-data fingerprints, and
the *right asset and the reliability of name-based discovery are tier-dependent* -
recover scaled-regionals (Acadian 12, Falck ~10) by name, but the national
roll-ups (GMR 0, Priority 3-of-8) require fleet + an ownership crosswalk, and the
mom-and-pop tail is only sizable in aggregate. The public record's systematic bias
runs top-to-bottom: **undercount the top, universe-mismatch the middle, long-tail
the bottom.** Extends Finding #46 and Finding 118 (Run 7).

## The firewall, held exactly

The tier fingerprints (F633-F635) are a **primary NPPES pull we ran** - OBSERVED,
tier A, reproducible. The operator scale figures (F636-F637) are company
self-reports / a filer's own numbers - CLAIMED / tier B, carried to set bands,
never quoted as the market. The bands and the recipe (F638-F639) are **DERIVED**
and sit quarantined until the measured panel replaces them. `ift_player_tiers`
degrades (never raises) and labels its basis in `source_label`. No fleet
self-report is used as a measurement; Finding #46's universes and the 11.3M
Medicare IFT book stand unchanged.

## Verification
- `tests/test_ift_player_tiers.py` (5 tests) green: four tiers in rank order, every
  tier carries all guidance fields, the OBSERVED NPPES probe matches Run 7
  (GMR* 0, Acadian* 12), `source_label` names OBSERVED/CLAIMED/DERIVED.
- ID ledgers contiguous: F633-F639 after F632; S455-S457 after S454; finding 119
  after 118. No shipped ID renumbered.

## Human action items
1. The Run 7 measured panel now doubles as the tier-boundary calibrator: pull CMS
   Medicare ambulance transports (A0425-A0434) per NPI to set the transports-per-
   NPI cut points between the four tiers empirically.
2. Build the ownership crosswalk (national tier) so GMR/Priority local entities
   roll to the parent.

## Not in this pass
No `sec_*.py` workbook tab and no UI route were added; the module + delta note
register the tiers for the next workbook build and a future `ift_*_page.py`. The
readable public-guidance version is `RCM_MC/docs/IFT_PLAYER_TIERS_GUIDANCE.md`.
