# IFT Fleet vs. Labor — the better predictor of real transport volume, and why GMR & Priority are undercounted

**Date:** 2026-07-20 · **Workstream:** IFT Sourced Evidence Master
**Registry lineage:** facts **F624–F632**, sources **S448–S454**, **Finding 118**
(registered in `scripts/ift_evidence_v3/DELTA_NOTE_v4_3.md`). Extends **Finding #46**
(the supplier-universe rule) and the AMR-Omaha / MMT NPI-to-vehicle exhibits in
`rcm_mc/market_reports/ift_npi_landscape.py`.

This is the *readable* companion to the delta note. Every number here is labeled by
basis (OBSERVED = we pulled it; CLAIMED = company self-report; MODELED = derived,
quarantined) so the paper trail is easy to follow.

---

## The question

The only two real national private ground platforms are **Global Medical Response
(GMR)** and **Priority Ambulance**. To size a company (or the market) you need a
scale unit that tracks *real transport volume*. Two candidates:

- **Fleet** — number of permitted vehicles/ambulances a company runs.
- **Licensed EMTs per company** — the field clinician headcount.

Which one recovers scale correctly? And why do the two national players look tiny in
the public provider data?

---

## Bottom line

1. **Fleet is the better predictor.** Size on `volume ≈ fleet × transports-per-vehicle`,
   not on a headcount multiple.
2. **NPPES undercounts the national roll-ups ~10–50×.** By name, GMR returns **0**
   NPIs, Rural/Metro **0**, Priority Ambulance **3**. The operations live under
   hundreds of separately-named local entities and NPPES has **no owner field**.
3. **Therefore:** you cannot *count* a roll-up (entities or staff) from NPPES. Size
   on fleet, and attach an external **ownership crosswalk** to roll local entities
   up to the parent.

---

## Finding 1 — why GMR & Priority are undercounted (OBSERVED)

Live NPPES NPI Registry API (v2.1), organization NPIs, run 2026-07-20. NPPES name
search covers legal business name + DBA + former + other names:

| Query (`organization_name`) | NPIs | What they actually are |
|---|---:|---|
| `Global Medical Response` | **0** | Parent holding company — no operating NPI; bills through subsidiaries. |
| `Rural/Metro` / `Rural Metro` | **0** | Major GMR ground brand — nothing under its own name. |
| `American Medical Response` | **65** | ~15 distinct legal names (AMR *of CT/MA/TX/S. Cal/West/Mid-Atlantic/NW/TN…*) **plus** local DBAs that only matched on a *former/other* name (Randle Eastern, LifeFleet Southeast, Mercy Inc, Metro Ambulance, ParaMed, Hank's Acquisition Corp). |
| `Priority Ambulance` | **3** | All "Shoals Ambulance LLC" — one Priority brand; the other 21 brands don't carry the name. |

**The gap** (CLAIMED, company self-reports): GMR runs **>7,000 ground vehicles /
~6.0M transports** (name → 0). Priority runs **~400 vehicles / 610,000 transports
across 22 brands / 15 states** (name → 3).

**Mechanism.** NPPES enumerates the *local legal operating entity* (often an
acquisition kept under its own name/DBA), not the owner. There is **no parent /
ultimate-owner field**. Priority explicitly *preserves* each acquired brand;
AMR/GMR is partially consolidated but still splits across ~15 state entities +
retained DBAs. So any analysis keyed off company **name** in NPPES misses the
parent and scatters the subsidiaries.

This is the study's existing exhibits at national scale — the AMR-Omaha single NPI
masking ~35 vehicles/~90 employees, and MMT's 24 org NPIs against a claimed 500+
vehicles (~20× undercount) — now shown for the two national brands directly.

---

## Finding 2 — fleet beats licensed EMTs (the sizing answer)

Ratios from the two national anchors (MODELED — quarantined, not shipped numbers):

| Ratio | Priority | GMR / AMR |
|---|---:|---:|
| transports per **vehicle** / yr | 610k / 400 ≈ **1,525** | 6.0M / 7,000 ≈ **857*** |
| transports per **licensed EMT/medic** / yr | 610k / 1,600 ≈ **381** | 4.4M / 27,000 ≈ **163†** |

\* GMR's 7,000 includes support vehicles and the 6.0M includes air, so ground-only
is higher (closer to Priority). † AMR's 27,000 is "…RNs *and other professionals*" —
not comparable to Priority's field-EMT count.

**Why fleet wins:**

1. **Physical constraint → stable ratio.** A unit runs a bounded number of trips/day
   (unit-hour utilization ~0.30–0.50 for 911, higher for IFT — the study's UHU
   lever). Volume = capacity × utilization; **vehicles are the capacity unit**, so
   `fleet × transports-per-vehicle` recovers scale in a bounded band.
2. **Availability & consistency.** Vehicle counts are independently observable
   (state EMS **permits**, DOT, disclosures) and counted the same everywhere.
   "Licensed EMTs per company" is inconsistently reported and **not derivable from
   NPPES** — individual EMTs rarely hold NPIs and aren't employer-linked. The pool
   exists nationally (399,868 NREMT EMTs vs 149,643 paramedics) but can't be pinned
   to a company from the registry.
3. **Staffing ratios are noisy.** Single- vs dual-medic, 911 vs IFT, urban vs rural,
   heavy part-time — EMT-per-transport swings widely; vehicles don't.

**Strength of claim (honest):** n = 2 national anchors → this is a *structural*
argument, not a fitted correlation. To *measure* it, build a panel of ~20–50
services with (permitted vehicles, licensed-EMT count, transport volume) from state
vehicle permits × CMS Medicare ambulance utilization (A0425–A0434) × disclosures,
and regress volume on each. Expectation: fleet R² ≫ EMT R²; EMT adds signal only
after conditioning on fleet.

---

## Recommended sizing method

```
company_volume ≈ Σ_locations( permitted_vehicles × transports_per_vehicle_band[911|IFT, urban|rural] )
parent_rollup  = map local NPPES entities → parent via an OWNERSHIP CROSSWALK
                 (SEC/PE deal history, CMS PECOS ownership, state licensing, press)
```

- **Scale unit:** permitted **vehicles** — not name-matched NPIs, not EMT headcount.
- **Utilization band:** anchor to the ratios above; tighten with CMS Medicare
  ambulance utilization per NPI once ingested.
- **Roll-up:** the ownership crosswalk is the step NPPES cannot do.
- **EMT counts:** secondary utilization/quality signal only — never the primary
  scale driver.

---

## Sources (paper trail)

- **NPPES / NPI Registry API v2.1** (npiregistry.cms.hhs.gov/api), queried 2026-07-20
  — the four brand-name searches above [OBSERVED, tier A]. **S448**.
- **GMR** fleet-expansion release — >7,000 ground vehicles, 382 air bases, ~6M
  encounters [CLAIMED]. `globalmedicalresponse.com/news/gmr-launches-major-fleet-expansion…` **S449**.
- **AMR** overview (fleet >7,000) `amr.net/about/overview` **S450**; AMR profile
  (~34k employees, >27k clinicians, 4.4M transports, 40 states+DC)
  `en.wikipedia.org/wiki/American_Medical_Response`, `amr.net` **S451**.
- **Priority Ambulance** about/press — ~400 vehicles, 4,300 employees, >1,600
  licensed EMTs+medics, 610k transports, 22 brands / 15 states
  `priorityambulance.com/about` **S452**.
- **NEMSIS** public reports — 34.2M all-EMS events (2019), all-events context only,
  not mixed with the 11.3M Medicare IFT book `nemsis.org/view-reports/public-reports` **S453**.
- **IFT scale + UHU** — NHAMCS IFT estimate; ambulance KPI/unit-hour utilization
  `sciencedirect.com/science/article/abs/pii/S0735675720303946`,
  `financialmodelslab.com/blogs/kpi-metrics/ambulance-service` **S454**.

## Disambiguation

"Priority Ambulance" (Knoxville, TN — national roll-up, 22 brands) is **not** the
repo's "Priority Medical Transport" (North Platte, NE — AmeriPro/Whistler) in
`ift_npi_landscape.py`. Different companies; this memo is the Knoxville national
player.

## Limitations

n = 2 national anchors; self-reported fleet/transport/employee figures mix
ground/air and support vehicles differently; NPPES name-search is a proxy for how a
name-keyed analysis would count, not a census of owned entities. Ratios are
indicative and quarantined until a measured panel replaces them.
