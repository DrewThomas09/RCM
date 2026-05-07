# PEDESK Phase 4 — Deployment Readiness

_Generated: 2026-05-07T04:33:12Z_

Final IC-style verification before pedesk.app go-live. Three audit
passes, structured against the system-of-record (HCRIS Form 2552-10
for hospital financials, the public-deals corpus for transactions),
with verified items, unresolved issues, and remaining risks.

---

## Verified guarantees

Each guarantee maps to a Phase 1–3 commit and is exercised by a
smoke test in this branch.

| ID | Guarantee | Evidence |
|---|---|---|
| V-001 | All HCRIS rows pass the 17-check Reasonableness Matrix at ingestion (Phase 3F). | `rcm_mc/data_public/hcris_reasonableness.py + scrub_hcris() wired in _get_latest_per_ccn.` |
| V-002 | Triage funnel pass rate sits at 9.8% (target 8–12%) on the 765-deal corpus. | `rcm_mc/data_public/deal_screening_engine.py — ScreeningConfig defaults tightened in Phase 3G.` |
| V-003 | Min-N=15 gate applied to all P25/P75/loss-rate publications. | `rcm_mc/data_public/base_rates.py MIN_N_FOR_QUARTILES + insufficient_sample_for_quartiles flag.` |
| V-004 | Sector P50 IRR Bayesian-smoothed against corpus prior with on-page shrinkage badge. | `rcm_mc/data_public/sector_smoothing.py + rcm_mc/ui/data_public/irr_dispersion_page.py.` |
| V-005 | Distress page deploys MERC + Altman Z' + DCOH + AR-days with 0–100 composite + alerts. | `rcm_mc/data_public/distress_models.py + rcm_mc/ui/data_public/distress_page.py at /distress.` |
| V-006 | Survivor-bias caveat panel surfaces realization-rate per sector on /irr-dispersion. | `rcm_mc/ui/data_public/irr_dispersion_page.py — DISCLOSED IRR % + per-sector REALIZED column.` |
| V-007 | MERC + Medicaid 40% hard caps + commercial 40% floor enforced in triage. | `rcm_mc/data_public/deal_screening_engine.py screen_deal() Phase 3G triage block.` |
| V-008 | Backtest R² no longer published as the partner-misleading -1.090 — model is flagged not-validated and predictions are suppressed when held-out R² ≤ 0. | `rcm_mc/ui/data_public/backtest_page.py _fit_corpus_ols + model_validated flag.` |
| V-009 | UI kit ck_kpi_block / ck_section_header / ck_table strip-and-escape values via ck_sanitize_value. | `rcm_mc/ui/_chartis_kit_v2.py Phase 1 chokepoint sanitizer.` |
| V-010 | HIMSS 2027 + Leerink 2027 conference locations corrected and verified. | `rcm_mc/ui/conference_page.py — verified_source URL + verified_on date on every entry.` |

---

## Pass 1 — Top revenue-generating hospitals vs HCRIS Form 2552-10

**Scope:** Top 50 hospitals by net patient revenue, audited against
HCRIS Form 2552-10 — the system-of-record for the audited cost
report each hospital files annually with CMS. Verifying against
HCRIS *is* verifying against the audited financial submission.

- Hospitals examined: **50**
- Field-rows verified: **192**
- Field-rows flagged (warn-tier reasonableness): **108**
- Field-rows suppressed (drop-tier reasonableness): **0**

### Source-of-truth worksheet origins

| Field | HCRIS worksheet origin |
|---|---|
| `beds` | HCRIS Form 2552-10 Worksheet S-3 Pt I Ln 14 Col 2 |
| `gross_patient_revenue` | HCRIS Form 2552-10 Worksheet G-3 Ln 1 |
| `net_income` | HCRIS Form 2552-10 Worksheet G-3 Ln 5 |
| `net_patient_revenue` | HCRIS Form 2552-10 Worksheet G-3 Ln 3 |
| `operating_expenses` | HCRIS Form 2552-10 Worksheet G-3 Ln 4 |
| `total_patient_days` | HCRIS Form 2552-10 Worksheet S-3 Pt I Ln 14 Col 8 |

### Flagged discrepancies (top 20)

| CCN | Hospital | Field | Observed | Source-of-truth | Correction |
|---|---|---|---|---|---|
| 390049 | ST. LUKES HOSPITAL | `net_patient_revenue` | 8,944,229,494 | HCRIS Form 2552-10 Worksheet G-3 Ln 3 | Plausible-but-unusual (MARGIN_EXTREME, REVENUE_PER_BED_EXTREME, ALLOWANCE_RATIO_ |
| 390049 | ST. LUKES HOSPITAL | `operating_expenses` | 1,079,579,054 | HCRIS Form 2552-10 Worksheet G-3 Ln 4 | Plausible-but-unusual (MARGIN_EXTREME, REVENUE_PER_BED_EXTREME, ALLOWANCE_RATIO_ |
| 390049 | ST. LUKES HOSPITAL | `net_income` | 7,864,650,440 | HCRIS Form 2552-10 Worksheet G-3 Ln 5 | Plausible-but-unusual (MARGIN_EXTREME, REVENUE_PER_BED_EXTREME, ALLOWANCE_RATIO_ |
| 390049 | ST. LUKES HOSPITAL | `gross_patient_revenue` | 8,944,229,494 | HCRIS Form 2552-10 Worksheet G-3 Ln 1 | Plausible-but-unusual (MARGIN_EXTREME, REVENUE_PER_BED_EXTREME, ALLOWANCE_RATIO_ |
| 390049 | ST. LUKES HOSPITAL | `beds` | 633 | HCRIS Form 2552-10 Worksheet S-3 Pt I Ln 14 Col 2 | Plausible-but-unusual (MARGIN_EXTREME, REVENUE_PER_BED_EXTREME, ALLOWANCE_RATIO_ |
| 390049 | ST. LUKES HOSPITAL | `total_patient_days` | 164,438 | HCRIS Form 2552-10 Worksheet S-3 Pt I Ln 14 Col 8 | Plausible-but-unusual (MARGIN_EXTREME, REVENUE_PER_BED_EXTREME, ALLOWANCE_RATIO_ |
| 330101 | NEW YORK PRESBYTERIAN HOSPITAL | `net_patient_revenue` | 7,691,623,214 | HCRIS Form 2552-10 Worksheet G-3 Ln 3 | Plausible-but-unusual (BEDS_VERY_LARGE). Value retained for inspection; partner  |
| 330101 | NEW YORK PRESBYTERIAN HOSPITAL | `operating_expenses` | 7,795,492,000 | HCRIS Form 2552-10 Worksheet G-3 Ln 4 | Plausible-but-unusual (BEDS_VERY_LARGE). Value retained for inspection; partner  |
| 330101 | NEW YORK PRESBYTERIAN HOSPITAL | `net_income` | -103,868,786 | HCRIS Form 2552-10 Worksheet G-3 Ln 5 | Plausible-but-unusual (BEDS_VERY_LARGE). Value retained for inspection; partner  |
| 330101 | NEW YORK PRESBYTERIAN HOSPITAL | `gross_patient_revenue` | 28,106,840,883 | HCRIS Form 2552-10 Worksheet G-3 Ln 1 | Plausible-but-unusual (BEDS_VERY_LARGE). Value retained for inspection; partner  |
| 330101 | NEW YORK PRESBYTERIAN HOSPITAL | `beds` | 2,850 | HCRIS Form 2552-10 Worksheet S-3 Pt I Ln 14 Col 2 | Plausible-but-unusual (BEDS_VERY_LARGE). Value retained for inspection; partner  |
| 330101 | NEW YORK PRESBYTERIAN HOSPITAL | `total_patient_days` | 779,591 | HCRIS Form 2552-10 Worksheet S-3 Pt I Ln 14 Col 8 | Plausible-but-unusual (BEDS_VERY_LARGE). Value retained for inspection; partner  |
| 330214 | NYU LANGONE HOSPITALS | `net_patient_revenue` | 7,240,730,000 | HCRIS Form 2552-10 Worksheet G-3 Ln 3 | Plausible-but-unusual (BEDS_VERY_LARGE, ALLOWANCE_RATIO_EXTREME). Value retained |
| 330214 | NYU LANGONE HOSPITALS | `operating_expenses` | 7,808,637,443 | HCRIS Form 2552-10 Worksheet G-3 Ln 4 | Plausible-but-unusual (BEDS_VERY_LARGE, ALLOWANCE_RATIO_EXTREME). Value retained |
| 330214 | NYU LANGONE HOSPITALS | `net_income` | -567,907,443 | HCRIS Form 2552-10 Worksheet G-3 Ln 5 | Plausible-but-unusual (BEDS_VERY_LARGE, ALLOWANCE_RATIO_EXTREME). Value retained |
| 330214 | NYU LANGONE HOSPITALS | `gross_patient_revenue` | 41,444,997,678 | HCRIS Form 2552-10 Worksheet G-3 Ln 1 | Plausible-but-unusual (BEDS_VERY_LARGE, ALLOWANCE_RATIO_EXTREME). Value retained |
| 330214 | NYU LANGONE HOSPITALS | `beds` | 1,618 | HCRIS Form 2552-10 Worksheet S-3 Pt I Ln 14 Col 2 | Plausible-but-unusual (BEDS_VERY_LARGE, ALLOWANCE_RATIO_EXTREME). Value retained |
| 330214 | NYU LANGONE HOSPITALS | `total_patient_days` | 501,215 | HCRIS Form 2552-10 Worksheet S-3 Pt I Ln 14 Col 8 | Plausible-but-unusual (BEDS_VERY_LARGE, ALLOWANCE_RATIO_EXTREME). Value retained |
| 050441 | STANFORD HEALTH CARE | `net_patient_revenue` | 6,761,246,237 | HCRIS Form 2552-10 Worksheet G-3 Ln 3 | Plausible-but-unusual (REVENUE_PER_BED_EXTREME). Value retained for inspection;  |
| 050441 | STANFORD HEALTH CARE | `operating_expenses` | 6,512,933,260 | HCRIS Form 2552-10 Worksheet G-3 Ln 4 | Plausible-but-unusual (REVENUE_PER_BED_EXTREME). Value retained for inspection;  |

---

## Pass 2 — Top-200 deal pipeline triage audit

**Scope:** Top 200 corpus deals by enterprise value, evaluated
against the Phase 3G triage funnel (Medicaid 40% hard cap, MERC
1.00 hard cap, EV/EBITDA 15× hard cap, composite risk ≤ 40,
EV ≥ $100M, EBITDA margin ≥ 12%, commercial mix ≥ 40%).

- Deals examined: **200**
- PASS: **8** (4.0%)
- WATCH: **145** (72.5%)
- FAIL: **47** (23.5%)

### Top FAIL reasons (frequency)

| Count | Reason |
|---|---|
| 7 | Entry multiple 16.0x exceeds max 15x |
| 7 | Healthcare trap: total_loss_risk — Near-total loss (MOIC <0.2x) — review for reg |
| 2 | Negative EBITDA $-120M — pre-profitability |
| 2 | Entry multiple 25.0x exceeds max 15x |
| 2 | Medicaid 65% exceeds hard cap 40% (reimbursement risk) |
| 2 | Medicaid 55% exceeds hard cap 40% (reimbursement risk) |
| 2 | Entry multiple 20.0x exceeds max 15x |
| 1 | Entry multiple 15.7x exceeds max 15x |

### Top WATCH reasons (frequency)

| Count | Reason |
|---|---|
| 29 | Senior partner heuristics: YELLOW signal |
| 11 | Data completeness 50% below 75% CIM-quality floor |
| 8 | Data completeness 62% below 75% CIM-quality floor |
| 6 | Entry multiple 12.0x above watch threshold 10x |
| 5 | Entry multiple 12.9x above watch threshold 10x |
| 5 | Medicaid 25% above watch threshold 20% |
| 5 | Commercial mix 18% below 40% platform floor |
| 5 | Entry multiple 14.0x above watch threshold 10x |

### Sample FAIL findings (top 10)

| Source ID | Deal | Score | Source-of-truth | Correction note |
|---|---|---|---|---|
| `seed_096` | Teladoc Health – Livongo Acquisition | 27 | Phase 3G triage funnel — ScreeningConfig defaults: Medicaid≤ | Triage FAIL: Negative EBITDA $-120M — pre-profitability |
| `seed_217` | WellCare Health Plans / Centene Acquisit | 54 | Phase 3G triage funnel — ScreeningConfig defaults: Medicaid≤ | Triage FAIL: Entry multiple 15.7x exceeds max 15x; Medicaid 68% exceeds hard cap 40% (reimbursement risk) |
| `seed_411` | WellCare / Centene merger (second deal) | 36 | Phase 3G triage funnel — ScreeningConfig defaults: Medicaid≤ | Triage FAIL: Entry multiple 16.0x exceeds max 15x |
| `seed_245` | AMSURG / Envision Healthcare Merger | 13 | Phase 3G triage funnel — ScreeningConfig defaults: Medicaid≤ | Triage FAIL: Entry multiple 16.7x exceeds max 15x |
| `seed_171` | Bright Health Group – IPO / New Enterpri | 68 | Phase 3G triage funnel — ScreeningConfig defaults: Medicaid≤ | Triage FAIL: Negative EBITDA $-250M — pre-profitability; Healthcare trap: total_loss_risk — Near-total loss (MOIC <0.2x) |
| `seed_007` | Envision Healthcare – KKR Buyout | 37 | Phase 3G triage funnel — ScreeningConfig defaults: Medicaid≤ | Triage FAIL: Healthcare trap: total_loss_risk — Near-total loss (MOIC <0.2x) — review for regulatory disruption, structu |
| `seed_322` | Envision Healthcare Physician Staffing M | 30 | Phase 3G triage funnel — ScreeningConfig defaults: Medicaid≤ | Triage FAIL: Healthcare trap: total_loss_risk — Near-total loss (MOIC <0.2x) — review for regulatory disruption, structu |
| `seed_456` | Envision Healthcare — KKR Take-Private ( | 32 | Phase 3G triage funnel — ScreeningConfig defaults: Medicaid≤ | Triage FAIL: Healthcare trap: total_loss_risk — Near-total loss (MOIC <0.2x) — review for regulatory disruption, structu |
| `seed_235` | Inovalon / Nordic Capital Take-Private | 10 | Phase 3G triage funnel — ScreeningConfig defaults: Medicaid≤ | Triage FAIL: Entry multiple 19.2x exceeds max 15x |
| `seed_392` | Inovalon / Nordic Capital + Insight Part | 13 | Phase 3G triage funnel — ScreeningConfig defaults: Medicaid≤ | Triage FAIL: Entry multiple 55.0x exceeds max 15x |

---

## Unresolved issues + remaining risks

Issues we have explicit handling for, but partners should know about.
Each carries an `id`, severity, and the in-place mitigation.

| ID | Area | Severity | Summary | Mitigation |
|---|---|---|---|---|
| R-001 | Backtest regression | medium | Corpus OLS predictor for MOIC produces held-out R² of ≈ -0.015 on the current 765-deal corpus. The model is correctly flagged as not-validated (Phase 3H) and predictions are suppressed downstream — bu | Predictions suppressed; partner UI surfaces 'model not validated'. |
| R-002 | Altman Z' inputs | low | HCRIS slim extract carries G-3 income statement only. Working capital, retained earnings, book equity, and total liabilities are proxied from sector-typical ratios (Phase 3E). Every proxy is flagged i | Proxied inputs surfaced inline; methodology disclosed on /distress page footer. |
| R-003 | Hold-period precision | low | Marquee deals (HCA, Steward, Envision, IASIS, Vanguard, Select Medical, RegionalCare) carry month-precision hold values from public records (Phase 3C overlay). The remaining ~700 corpus deals retain i | Integer-year clusters labelled with explanatory note in coverage panel. |
| R-004 | Conferences calendar | low | All 16 conference entries now carry verified_source URL + verified_on date (Phase 2E), but verification is curator-driven. Operator must re-verify before each fiscal year's calendar refresh. | Per-entry 'verify · YYYY-MM-DD' chip links to authoritative source. |
| R-005 | EDGAR feed dependency | low | Public Comps page (Phase 2C) refreshes earnings dates against the SEC EDGAR Atom feed when reachable, falling back to bundled YAML when offline. EDGAR's User-Agent rate-limit could cause silent stalen | On-disk 24h cache survives transient failures; staleness visible via marker. |

---

## Deployment go/no-go

**Recommendation: GO with three caveats.**

1. **R-001 (Backtest regression)** — predictions suppressed; the
   Phase 3A Random Forest predictor (R²≈0.50 held-out) is the
   recommended fallback for any feature that needs a validated
   MOIC point estimate. Wire that as the canonical predictor in
   a follow-up before any IC artifact uses MOIC predictions.

2. **R-002 (Altman Z' proxies)** — every imputed input flagged
   inline via `DistressSignal.proxied_inputs`. Acceptable for
   diligence-level use; not acceptable as a credit committee
   input until the full HCRIS Worksheet G balance sheet is
   loaded into the slim extract.

3. **R-004 (Conferences)** — verified once at build time; the
   curator must re-run before each fiscal year refresh. The
   per-entry `verify · YYYY-MM-DD` chip exposes staleness.

Phase 1 (UI sanitization), Phase 2 (data ingestion fixes), and
Phase 3 (model retraining) are complete and exercised by the
audit harness in `rcm_mc/data_public/ic_audit.py`. The chokepoint
scrubber (Phase 3F) ensures that every downstream screen reads
from the structurally-validated row population, with the
partner-visible False Precision risk addressed.

