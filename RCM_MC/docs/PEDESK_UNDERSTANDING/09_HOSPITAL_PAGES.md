# 09 · Hospital pages (`/hospital/<ccn>/*`)

> The per-hospital surfaces — the "stock quote" for any US hospital, reachable for **any CCN even if it's not a tracked deal**, because they read **CMS public data (HCRIS)** directly. This is the bridge from the screener (§06) into a deal: you find a hospital, open its profile, and start diligence. Numbers here are public-data or modeled — never seller data.

The CCN (CMS Certification Number) is the key. Every page loads the hospital's HCRIS-derived record from `hospital_benchmarks` and layers analysis on top.

---

## `/hospital/<ccn>` — the profile ("stock quote")
`hospital_profile.py`. Reads the HCRIS hospital record directly (not a packet). Headline numbers, all from the CMS HCRIS filing:
| Number | Source / formula |
|---|---|
| Beds | `hospital["beds"]` (HCRIS) |
| Net patient revenue | `hospital["net_patient_revenue"]` (HCRIS) |
| Operating margin | `(npr − opex) / npr`, clamped to [−100%, +100%] |
| Payer-day mix | `medicare_day_pct`, `medicaid_day_pct`, commercial = `1 − medicare − medicaid` → the payer-mix bar |
| Revenue per bed | `npr / beds` |

Each value carries a **provenance tooltip** ("explain this number") built from a `ProvenanceGraph` over the raw HCRIS fields — operating_margin and revenue_per_bed are spliced in as COMPUTED nodes alongside the raw HCRIS SOURCE nodes. Also shows comparables, ratings, and a "start diligence" action that creates a deal/packet from this hospital.

## `/hospital/<ccn>/stats` — statistical profile
(`hospital_stats_page.py`, documented in the visuals work) Each metric vs national + state peers: z-score, percentile, and the **National Percentile Profile** bar chart (per-metric national rank). Distressed/outlier flags use the credible-filing mask (junk HCRIS filings excluded). Data: HCRIS national distribution.

## `/hospital/<ccn>/providers` — provider roster
(`hospital_providers_page.py`) The NPPES provider roster for the CCN (`nppes_live_cache`, 30-day TTL, fetched via `rcm-mc data refresh-nppes --ccn`). Leads with the **specialty-mix concentration bar chart** (share of roster by taxonomy; red ≥50% = the CONCENTRATION flag, amber ≥30%). The concentration call ("one specialty dominates the roster") is a structural-fragility signal pre-LOI. Empty: honest "no roster cached — run refresh" state.

## `/hospital/<ccn>/demand` — demand forecast
(`demand_page.py`) Demographic/utilization-driven volume outlook for the hospital's market.

## `/hospital/<ccn>/history` — filing history
(`hospital_history.py`) The hospital's HCRIS filing trail over years.

## `/ml-insights/hospital/<ccn>` — ML predictions
Runs the **ridge + conformal predictor** (`PEDESK_ALGORITHMS` §6) on the hospital's HCRIS features to predict missing RCM metrics, each with a **90% conformal interval** and a reliability grade. This is the same prediction stack the packet uses — here surfaced standalone for a hospital. Numbers are tagged ML_PREDICTION (medium trust).

## `/bayesian/hospital/<ccn>` — Bayesian calibration
Runs the **hierarchical Bayesian calibration** (`PEDESK_ALGORITHMS` §16): the posterior shrinks a metric toward its hospital-type peer prior when data is thin and converges to observed/seller values when rich. Shows the prior, the observed, and the blended posterior with a credible interval — the CALIBRATED source. This is how seller data + model prediction combine into one defensible number (`data_room_calibrations`).

## `/data-room/<ccn>` — seller data entry
The diligence data-room: the analyst enters seller-provided metrics (`data_room_entries`), tagged SELLER (high trust), which **override** public/predicted values and feed the Bayesian posterior. Supersession chain (`superseded_by`) keeps an audit trail. POST `/data-room/<ccn>/add`.

## `/ebitda-bridge/<ccn>` — per-hospital EBITDA bridge
Runs the 7-lever EBITDA bridge (`PEDESK_ALGORITHMS` §3) on the hospital's metrics → current → target EBITDA with per-lever impacts at multiple exit multiples. The standalone version of the bridge that also appears on the deal profile (§03).

## `/scenarios/<ccn>` — scenario modeler
(`scenario_modeler_page.py`, route `/scenarios/<ccn>`) Compares scenarios (base/bull/bear) for the hospital using HCRIS data: per-scenario adjusted revenue, pro-forma EBITDA, entry/exit multiples, MOIC, IRR. Leads with the **MOIC-by-scenario bar chart** + an EBITDA-trajectory timing chart. Uses `pe_math` (MOIC/IRR/value bridge) on scenario inputs.

## `/competitive-intel/<ccn>` — competitive intel
Competitor/market-share context for the hospital's market.

---

## The flow these enable
`/predictive-screener` (find a hospital by modeled uplift) → `/hospital/<ccn>` (read its public-data fundamentals) → `/ml-insights` + `/bayesian` (predict/calibrate missing metrics) → `/data-room/<ccn>` (enter seller data, which overrides) → `/ebitda-bridge/<ccn>` + `/scenarios/<ccn>` (model the value-creation) → "start diligence" → a tracked deal with a `DealAnalysisPacket` (§01, §03). Provenance escalates along the way: HCRIS (public) → ML_PREDICTION (modeled) → SELLER (data room) → CALIBRATED (blended).

---
*Next: `10_WORKFLOW_OPS.md` — the daily portfolio workflow (alerts, cohorts, owners, deadlines, LP digest).*
