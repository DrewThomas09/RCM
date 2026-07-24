# IFT player tiers — public-data guidance for sizing operators

**Date:** 2026-07-20 · **Workstream:** IFT Sourced Evidence Master
**Registry lineage:** facts **F646–F652**, sources **S998–S1000**, **Finding 132**
(`scripts/ift_evidence_v3/DELTA_NOTE_v4_5.md`). Queryable in PE Desk via
`rcm_mc/market_reports/ift_player_tiers.py`. Builds on Run 8
(`IFT_FLEET_VS_LABOR_MEMO.md` — fleet beats licensed-EMTs; nationals invisible in
NPPES) and Finding #46 (the supplier universes must never be mixed).

**The one idea:** the *right public data asset — and whether you can even find an
operator by name — is tier-dependent.* Use the wrong asset for the tier and you
mis-size the market. Basis chips: OBSERVED (we pulled it) / CLAIMED (self-report) /
DERIVED (reasoned band, quarantined).

---

## The four commercial tiers at a glance

| Tier | Transports/yr | Fleet | Revenue | NPIs / operator | Named anchors |
|---|---|---|---|---|---|
| **1 · National platform** | ~0.6M–6M+ | ~400–7,000+ | ~$0.3B–multi-$B | tens–hundreds, scattered | GMR/AMR, Priority Ambulance |
| **2 · Scaled regional** | ~300K–1M | ~200–800 | ~$150M–$750M | ~10–20 under one name | Acadian, Falck US, DocGo |
| **3 · Subscaled regional** | ~50K–250K | ~30–200 | ~$25M–$150M | ~10–30, one corridor | MMT, Ryan Brothers, Bell |
| **4 · Local mom-and-pop** | <~20K | ~1–10 | <~$10M | 1–3 | the fragmented long tail |

*(Bands are DERIVED/indicative — quarantined until the CMS-volume panel sets the
cut points. Anchors are CLAIMED/SEC.)*

Hospital-owned captive programs (Allina ~34K IFT/yr, Mayo ~70 units) sit outside
this commercial ladder — insource ceiling, not an outsourced competitor.

---

## The public-data fingerprint — how each tier shows up (OBSERVED)

Live NPPES NPI Registry probes (NPI-2, 2026-07-20; wildcard-verified):

| Search the name in NPPES | NPIs | Fingerprint |
|---|---|---|
| `Global Medical Response*` | **0** | National parent — **invisible** (no NPI). |
| `Priority Ambulance*` | **8** | Only **3** (Shoals Ambulance LLC) are the real roll-up; 5 are unrelated name-collisions. Under-representative *and* polluted. |
| `Acadian Ambulance*` | **12** | Scaled-regional — **findable**, clean parent + state-suffixed LLCs. |
| `Falck*` | **17** | Scaled-regional — ~10 regional ambulance corps **+ same-name noise** (Falck Eye Center). |

**Name-based discovery reliability is tier-dependent:** it works for scaled-regionals,
is partial for subscaled (single-corridor NPIs, ~20× vehicle undercount), and fails
for national roll-ups — because nationals grow by acquiring and keeping local brands.

---

## Guidance — which asset, and how to size, per tier

**Tier 1 · National platform** — *don't name-match in NPPES.*
- **See it with:** fleet disclosures + SEC/PE filings + CMS Medicare MUP
  (A0425–A0434) aggregated through an **ownership crosswalk**.
- **Size it:** Σ permitted vehicles × transports-per-vehicle band, rolled to the
  parent (NPPES has no owner field).
- **Bias to correct:** name-keyed counting undercounts ~10–50× and misses the parent.

**Tier 2 · Scaled regional** — *NPPES works, with hygiene.*
- **See it with:** NPPES (parent + regional-suffix entities) + CMS MUP per NPI +
  company disclosures.
- **Size it:** sum the parent's regional-entity NPIs' CMS transport volume;
  cross-check disclosed fleet × ratio.
- **Bias to correct:** footprint fragmented across state LLCs; **filter by taxonomy
  3416\* and address**, not name alone (name collisions inject false positives).

**Tier 3 · Subscaled regional** — *trust vehicles and CMS, not revenue estimators.*
- **See it with:** state EMS licensing (permitted vehicles) + CMS MUP + IRS 990s.
- **Size it:** state-permitted vehicles × transports-per-vehicle band; corroborate
  with CMS volume.
- **Bias to correct:** third-party revenue/employee estimates diverge ~3× (Growjo
  vs ZoomInfo vs LeadIQ) — treat as unusable; NPIs undercount vehicles ~20×.

**Tier 4 · Local mom-and-pop** — *size the pool, not the firm.*
- **See it with:** PECOS enrollment + QCEW establishment counts + state rosters,
  in aggregate.
- **Size it:** universe counts × average small-operator volume; no per-firm work.
- **Bias to correct:** universe mismatch — **10,465 PECOS ≠ 8,721 billing NPIs ≠
  5,820 QCEW establishments** (Finding #46); picking any one as "the number of
  ambulance companies" mis-counts the tail.

---

## The throughline

The public record's systematic bias runs top-to-bottom:
**undercount the top · universe-mismatch the middle · long-tail the bottom.**
A defensible market build sizes each tier with its own asset and never applies one
lens across all four.

---

## Sources
- **NPPES / NPI Registry API v2.1**, brand probes 2026-07-20 [OBSERVED, tier A] — **S998**.
- **Acadian Ambulance** — 750 ambulances, ~800K transports, 4 states, ~$500–734M
  `en.wikipedia.org/wiki/Acadian_Ambulance`, `acadian.com/our-company/divisions` [CLAIMED] — **S999**.
- **DocGo (NASDAQ: DCGO)** FY2024 10-K/8-K — $616.6M revenue, ~$190M Transportation
  segment `sec.gov/.../dcgo-20241231.htm` [tier B] — **S1000**.
- Prior: Run 8 (`IFT_FLEET_VS_LABOR_MEMO.md`, F637–F645); Finding #46 (supplier
  universes); `ift_competitive` archetypes.

## Limitations
Tier bands are DERIVED and wide; the CMS Medicare ambulance-volume panel (A0425–A0434
transports per NPI) is the next step to set the cut points empirically. NPPES probe
counts are a proxy for how a name-keyed analysis would count, not a census.
