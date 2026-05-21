# 04 · RCM commercial-diligence — the pipeline & workbenches

> PE Desk's revenue-cycle (RCM) commercial-diligence section. This is where a partner takes a target's claims data and produces a quality-of-revenue read, a leakage estimate, and the workbench stress tests. It has its **own data spine (the CCD)** distinct from the corpus, and several workbenches with their **own models** (not the platform's EBITDA bridge / conformal predictor). This file traces where each number comes from.

## The data spine: the CCD (Canonical Claims Dataset)

Almost every page here reads one artifact: the **CCD** (`rcm_mc/diligence/ingest/ccd.py`). It is the normalized claims dataset — one `CanonicalClaim` per claim-line, plus a row-level `TransformationLog` of every coercion, plus a `content_hash()` for dedup. Schema version 1.0.0.

- **Where the claims come from:** the `?dataset=<fixture>` pages read **shipped fixtures** under `tests/fixtures/kpi_truth/` (`hospital_01_clean_acute` … `hospital_08_waterfall_critical`) — *not* a live feed. The **only surface that ingests real uploaded files** is `/diligence/snapshot` (835/837 from the VDR).
- **Ingester** (`ingest/ingester.py`, `ingest_dataset(path)`): maps source columns via a synonym table, normalizes payer/CPT/ICD/dates, then runs three cross-file passes — remittance reconciliation (835 → 837 paid enrichment), multi-EHR roll-up (collapse the same logical claim across systems), and duplicate/resubmit marking. Every coercion is logged.

So when a benchmark or leakage number appears, it's computed live from the ingested CCD claim lines — you can trace it to the claims and the transformation log.

---

## The 4-phase pipeline (`rcm_mc/diligence/_pages.py`)

Each tab shows a fixture selector; with no `?dataset` it shows an empty state, with one it runs the live pipeline.

### Phase 1 — `/diligence/ingest`
Runs `ingest_dataset` and shows a CCD summary card (claim count = `len(ccd.claims)`, schema version, source-file count, content-hash prefix) + a transformation-log preview (rule counts + first 20 entries). This is the "what did we load and how did we clean it" view.

### Phase 2 — `/diligence/benchmarks` — KPI vs benchmark
Runs `compute_kpis(ccd, as_of=2025-01-01)`. The **KPI engine** (`benchmarks/kpi_engine.py`) computes seven KPIs, each returning a value **or `None` + a reason** (never interpolated), each carrying its citation (HFMA MAP Key / AAPC):
| KPI | Formula |
|---|---|
| Days in A/R | paid-$-weighted avg of `(paid_date − service_date)` over paid claims |
| First-pass denial rate | denied-on-initial-submission / total (earliest submit per claim line) |
| A/R aging >90 days | $ share of open balance (`allowed − paid`) aged ≥90 days |
| Cost to collect | `cost / cash` — **requires analyst input**, else `—` |
| Net revenue realization | `actual_paid / expected_per_contract` — requires a contracted-rate fn, else `—` |
| Service→Bill / Bill→Cash lag | median day-counts (p25/p75 in the bounds) |
| Denial stratification | denied claims grouped by ANSI CARC category, $ = `max(allowed − paid, 0)` |

Benchmark **bands** (peer thresholds, e.g. HFMA FPDR peer median ~10%) are applied in the UI layer; the KPI math itself carries the citation string.

### Phase 3 — `/diligence/root-cause`
A **denial Pareto** (category × dollars denied × % of total, from the denial stratification) and a **zero-balance autopsy** (claims with `paid==0 AND adjustment>0`, with the charge/allowed/adjustment/CARC trail). Empty states: "No denials in this fixture" / "No zero-balance write-offs."

### Phase 4 — `/diligence/value`
> **Important honesty note:** this page does **not** run the EBITDA bridge or `value_bridge_v2` live. The explainer references a multi-lever bridge, but the rendered output is two **demos**: a contract-repricer summary (reprices claims against a hard-coded synthetic 7-rate schedule → payer leverage) and a CMS-advisory summary (regime + consensus rank on a synthetic frame). The note in the page says the real bridge wiring is "a follow-up." Document it as a demo, not a live value sizing.

---

## `/diligence/qoe-memo` — the printable Quality-of-Revenue memo
A **standalone HTML document** (not the editorial shell) so Print→PDF is clean. Pipeline: ingest → `compute_kpis` → `compute_cash_waterfall`. Sections: cover, Executive Summary (the QoR band headline), Quality of Revenue, KPI Snapshot, Denial Stratification, optional Re-pricing, Risk Flags, Open Questions, "What Would Change Our Mind," sign-off, appendix.

**Where the headline number comes from — the QoR reconciliation:** the cash waterfall computes per-cohort **accrual revenue** = `gross_charges − contractual_amount − (initial_denials − appeals_recovered) − bad_debt` (VMG/A&M QoR convention). The memo compares total claims-side accrual revenue against **management-reported** accrual; the **divergence** drives the band: **IMMATERIAL <2% · WATCH 2–5% · CRITICAL ≥5%**. Only **mature cohorts** (aged ≥ the realization window, default 120 days) are signed on.

> The QoE memo has **no numeric Data Confidence Score** — its "confidence" is the qualitative QoR band, with `—` for any uncomputable KPI. The numeric confidence score lives only on the snapshot tab (below).

---

## `/diligence/snapshot` — VDR 835/837 upload → revenue leakage
The one tab that ingests **real uploaded files** (835 remittances + 837 claims, or a zip). Pipeline: `build_ccd_from_files → tokenize (PHI) → match 837↔835 → compute_data_confidence → compute_analytics → generate_findings → render_markdown_memo`. **No persistence** — the temp dir is discarded; the page renders **aggregates only** (PHI-safe; patient identifiers are tokenized on ingest).

**Revenue leakage** (`analytics/revenue_leakage.py`): each claim is classified into a `DenialCategory`; the headline **`potentially_preventable_leakage`** = sum of adjustment dollars in the preventable categories (CLINICAL, CODING, FRONT_END, PAYER_BEHAVIOR). Conservative by design: **contractual adjustments are NOT counted as leakage**, and patient responsibility is NOT counted as upside. Plus by-payer / by-CPT / by-provider rollups and top-1 concentration.

**Data Confidence Score (0–100)** (`reconciliation/data_confidence.py`): **starts at 100, deducts for deficiencies** — charge/payer/NPI/service-date completeness gaps, unmapped adjustment codes, duplicate claim IDs, and especially the **837↔835 match shortfall** (`−20 × (1 − match_pct)` + a penalty for low-confidence matches) and dollar-reconciliation gaps. Clamped 0–100. The **issue list is the real output**; the scalar is a glanceable roll-up (green ≥85 / amber ≥70 / red <70).

**Findings** (`findings/finding_generator.py`): six conservative types, each with evidence + an *estimated* (never guaranteed) impact + a confidence band — preventable leakage (≥2% of charges), payer denial concentration (≥40% of denial $), provider denial outlier (≥1.5× portfolio), payer concentration risk (top-1 ≥50% of paid), low match rate (<70%), weak data quality (confidence <70). The Markdown memo renders these as copy-paste IC text.

---

## Workbenches — each with its own model

| Page | Input | Engine & key numbers |
|---|---|---|
| **`/diligence/denial-prediction`** | CCD fixture | Its **own stdlib Naive Bayes** (Laplace-smoothed, 8 categorical claim features), provider-disjoint train/test split. Outputs baseline denial rate, calibration (Brier/log-loss/accuracy/rough AUC), "systematic misses" (predicted-deny but actually paid), and recoverable charge $ × **0.60 recovery haircut**. Confidence by AUC. **Not** the platform conformal predictor. |
| **`/diligence/payer-stress`** | pasted payer mix | Own rate-shock **Monte Carlo**: per-payer rate move ~ Normal back-solved from curated payer priors, churn tail, dampened if not renewing. NPR Δ = `Σ(share·rate_move) · concentration_amplifier · NPR`; EBITDA impact = NPR × pass-through (0.70). **HHI = Σ(share·100)²**; verdict PASS/CAUTION/WARNING/FAIL; risk score 0–100. P10/P50/P90 cones. |
| **`/diligence/covenant-stress`** | Deal-MC bands + capital stack | Path-level breach **Monte Carlo**: per covenant × quarter breach probability, median headroom, first-breach quarter, equity-cure size. Peer covenant constants (leverage 5.5–7.0×, DSCR 1.25–1.75). |
| **`/diligence/bridge-audit`** | pasted free-text bridge | Own **realization-prior** logic: per lever, pull empirical realization prior, apply target-profile boosts, compute realistic median $ (`claimed × adjusted_realization`), verdict OVERSTATED/UNSUPPORTED/UNDERSTATED/REALISTIC. Bridge gap = `Σ(claimed − realistic)`; **counter-bid = asking − gap × entry_multiple**; double-count flag. **Not** `value_bridge_v2`. |
| **`/diligence/hcris-xray`** | hospital name/CCN | **Real CMS HCRIS** filings (via `data.hcris`, ~17k filings) — peer-match by weighted distance (bed cohort ±30%, region, Medicare-day share ±10pp, fiscal year); target vs peer P25/median/P75 across 15 cost-report metrics. **External data, not CCD.** |
| **`/diligence/deal-autopsy`** | CCD fixture or pasted values | Builds a **9-dimension signature** (denial rate, Medicare mix, payer concentration, OON share are CCD-derived; lease/EBITDAR/DAR/regulatory/physician come from metadata params), then **similarity = 1 − euclidean/√9** against a curated library of PE healthcare blow-ups (each with outcome + primary killer + partner lesson). Per-feature distance share explains the match. |
| **`/diligence/risk-workbench`** | target name (or `?demo=steward`) | 9 panels (Tier 1 existential → Tier 3 slow-burn), each calling its own subpackage engine (bankruptcy, regulatory, real estate, physician comp/Stark, cyber, MA dynamics, quality, labor, patient-pay). **Never interpolates** — each panel shows a "not supplied" state when its inputs are missing. |

---

## Quick answers
- **"Where does the QoE memo's revenue number come from?"** It's a **QoR reconciliation**, not a leakage figure: claims-side accrual revenue (`gross − contractuals − net denials − bad debt`) vs management-reported accrual; the band is the 2%/5% divergence. The dollar **leakage** figure is on `/diligence/snapshot` (`potentially_preventable_leakage`).
- **"What's the Data Confidence Score?"** A 0–100 scalar on the snapshot tab, starting at 100 and deducting for data-completeness gaps and the 837↔835 match shortfall. The issue list it produces is the load-bearing part.
- **"Is the value page running the real bridge?"** No — it's a repricer + CMS-advisory demo today; the live bridge lives on the deal pages (`/deal/<id>/profile`) and `value_bridge_v2` in the packet.

---
*Next: `05_PORTFOLIO.md` — portfolio operations and the corpus-benchmarking pages.*
