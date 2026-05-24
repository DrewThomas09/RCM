# Diligence — Real-Data Conversion Backlog

Per illustrative analyzer: current source, the **real** source that could
activate it, exact fields/formulas, feasibility, priority. Grounds PRs 4/5/7.
No fabrication: if a field doesn't exist in a real source, the page degrades to
ILLUSTRATIVE / DATA REQUIRED rather than inventing it.

**Real HCRIS fields available** (`diligence/hcris_xray/metrics.py::HospitalMetrics`):
`beds · total_patient_days · occupancy_rate · medicare_day_pct ·
medicaid_day_pct · other_day_pct · gross_patient_revenue ·
contractual_allowance_rate · net_to_gross_ratio · net_patient_revenue ·
net_revenue_per_bed · net_revenue_per_patient_day · operating_expenses ·
operating_margin_on_npr · net_income_margin_on_npr · opex_per_bed ·
opex_per_patient_day · payer_diversity_index · size_cohort · margin_band` —
plus peer benchmarking (P25/median/P75) via `xray()` and 3-yr `get_target_history()`.

---

## P1 — HCRIS-derivable (do first; PRs 4/5)

### Payer Stress (`/payer-stress`) — PR 4
- **Now:** ILLUSTRATIVE — scenario sliders + corpus regression of payer% → MOIC.
- **Real source:** HCRIS payer-**day** mix for an attached hospital.
- **Fields:** `medicare_day_pct`, `medicaid_day_pct`, `other_day_pct` (target +
  peer median); `net_patient_revenue` for $ sizing; `operating_margin_on_npr`.
- **Wire:** when a CCN is attached, seed the sliders from the target's *real*
  mix and show target-vs-peer-median; keep the regression as a clearly-labeled
  **assumption** layer (corpus-calibrated), not as the target's measured
  outcome. **Drop fabricated drivers** the user flagged.
- **Cannot derive:** commercial vs self-pay split (HCRIS gives "other"); contract
  rate detail → label DATA REQUIRED.
- **Feasibility:** HIGH (mix is real). **Priority:** P1.

### Cost Structure (`/cost-structure`) — PR 5
- **Now:** ILLUSTRATIVE — hardcoded cost lines/labor.
- **Real source:** HCRIS opex.
- **Fields:** `operating_expenses`, `opex_per_bed`, `opex_per_patient_day`,
  `net_patient_revenue`, `operating_margin_on_npr` (+ peer band).
- **Wire:** real opex-per-bed / opex-per-pt-day vs peer P25/median/P75 (X-Ray
  style). **Cannot derive:** COGS vs SG&A split, labor headcount/role detail
  (not in HCRIS) → those sub-panels stay ILLUSTRATIVE / DATA REQUIRED.
- **Feasibility:** HIGH (top-line opex real; decomposition not). **Priority:** P1.

### Debt Service (`/debt-service`) — PR 5
- **Now:** ILLUSTRATIVE — hardcoded benchmark figures.
- **Real source:** HCRIS margin/NPR as DSCR *proxy* inputs.
- **Fields:** `net_income_margin_on_npr`, `operating_margin_on_npr`,
  `net_patient_revenue`.
- **Wire:** an operating-cash proxy (margin × NPR) vs a benchmark band, with
  the cap/coverage multiple shown as a **labeled assumption**. **Cannot
  derive:** actual debt balances / interest / covenant terms (not in HCRIS) →
  DATA REQUIRED for the true DSCR.
- **Feasibility:** PARTIAL (proxy only — label clearly). **Priority:** P1.

### CMS APM Tracker (`/cms-apm`)
- **Real source:** vendored `data/cms_*` APM participation (public).
- **Feasibility:** verify coverage; likely convertible. **Priority:** P2.

---

## P2 — needs a different real source / partial

| Page | Real source candidate | Derivable? | Disposition |
|---|---|---|---|
| Physician Productivity (`/physician-productivity`) | CMS Part B / PECOS (if vendored) | provider-level wRVU not in HCRIS | label; verify Part B loader — P2 |
| Provider Retention/Churn (`/provider-retention`) | SNF PBJ turnover (SNF only); else roster upload | not general | DATA REQUIRED — P2 |
| Mgmt Comp (`/mgmt-comp`, `/phys-comp-plan`) | IRS 990 exec comp (non-profits) | partial (NFP only) | label + verify irs990 loader — P2 |
| Partner Economics (`/partner-economics`) | user-entered deal model | n/a | DATA REQUIRED — P2 |
| Payer Rate Trends (`/payer-rate-trends`) | corpus/reference rate tables | reference | label REF; maybe Research — P3 |
| Root Cause (`/diligence/root-cause`) | 835/837 CCD (ingest) | needs upload | EXPERIMENTAL / DATA REQUIRED — P3 |
| Dental Prediction | CCD ingestion | needs demo data | EXPERIMENTAL — P3 |
| Drug Shortage / Supply (`/drug-shortage`,`/supply-chain`,`/gpo-supply`) | FDA drug-shortage list (build-time vendor) | needs vendoring | label; vendor candidate — P3 |

---

## P4 — no clear PEdesk source → defer/delete (PR 8)
| Page | Why | Recommendation |
|---|---|---|
| ESG / Sustainability (`/esg-dashboard`,`/esg-impact`) | "only changes revenue — makes no sense"; no source | rebuild w/ real metric or **delete** |
| HCIT / SaaS (`/hcit-platform`) | unclear source, unprofessional | fix scope or **delete** |
| Biosimilars / 340B (`/biosimilars`,`/drug-pricing-340b`) | confused purpose, no source | define purpose or **defer** |
| Insurance / Malpractice (`/insurance-tracker`,`/rw-insurance`) | no source; not deal-linked | label DATA REQUIRED or defer |
| Bankruptcy Survivor (`/screening/bankruptcy-survivor`) | unclear purpose | define + UI, or defer |
| Counterfactual (`/diligence/counterfactual`) | confusing | clarify function or defer |

---

## Conversion rule (enforced)
A page graduates ILLUSTRATIVE → LIVE/DERIVED **only** when: source named ·
values traceable to real fields · missing data handled · assumptions labeled ·
Guide can explain it. Otherwise it stays labeled. **Never fabricate** payer
mix, opex decomposition, debt terms, wRVUs, comp, or comps to fill a panel.
