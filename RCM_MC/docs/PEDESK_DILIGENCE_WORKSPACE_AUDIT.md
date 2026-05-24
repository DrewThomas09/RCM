# PEdesk Diligence Workspace Audit

**Status:** Phase-0/1 audit. **Docs only.** The reform question is not "how do
we make these prettier?" but **"is each Diligence page real evidence, a model,
or a placeholder — and what data would make it investable?"**

Data-type legend: `HCRIS` HCRIS public · `CMS` CMS public · `USER-DEAL` user
deal/pipeline records · `CORPUS` benchmark corpus · `REF` research reference ·
`ILLUSTRATIVE` hardcoded demo (no real source) · `DATA-REQ` needs user upload/
CCD · `MIXED`.

Live-status legend: **LIVE** (real source, traceable) · **DERIVED** (computed
from real values) · **ILLUSTRATIVE** (hardcoded) · **DATA-REQ** · **EXPERIMENTAL**.

---

## A. Real-data / workflow pages (LIVE) — the keep-and-strengthen core

| Route | Page | Data | Status | Notes / recommendation |
|---|---|---|---|---|
| `/diligence/hcris-xray` | HCRIS X-Ray | HCRIS | **LIVE** | Gold standard. Rebuild in progress (#662/#663 → A-v2 results). Template for the rest. |
| `/diligence/deal` | Deal Profile | USER-DEAL | LIVE | Identity for the active deal. Keep. |
| `/diligence/ingest` | Ingestion (835/837) | USER-DEAL (upload) | LIVE/DATA-REQ | Real when files attached; honest empty otherwise. Keep. |
| `/diligence/benchmarks` | Benchmarks | HCRIS/CORPUS | LIVE/DERIVED | Keep; label corpus vs HCRIS. |
| `/diligence/snapshot` | 835/837 snapshot | USER-DEAL | LIVE | Keep (HCRL V2). |
| `/diligence/qoe-memo` | QoE Memo | USER-DEAL | DERIVED | Keep; ties to packet. |
| `/diligence/ic-packet` | IC Packet | USER-DEAL | DERIVED | Keep. |
| `/diligence/questions` | Diligence Questions | USER-DEAL | LIVE | Keep. |
| `/diligence/deal-mc`, `/diligence/value`, `/diligence/covenant-stress`, `/diligence/exit-timing`, `/diligence/bridge-audit` | MC / value / covenant / exit / bridge | USER-DEAL (sim) | DERIVED | Keep; ensure inputs are real deal records, not demo. |

## B. Illustrative analyzer layer (`ui/data_public/`) — **confirmed hardcoded, no real loader**

These render realistic-looking numbers from hardcoded dataclass lists. They are
**ILLUSTRATIVE** today and must be labeled as such (PR 2), then either wired or
moved/deferred.

| Route | Page | User note | Data | Recommendation |
|---|---|---|---|---|
| `/payer-stress`, `/diligence/payer-stress` | Payer Stress | "good idea, faulty execution; weird payer-mix drivers" | ILLUSTRATIVE | **wire to HCRIS/CMS payer-day mix** (real) or label; repair UI — PR 4 |
| `/cost-structure` | Cost Structure Analyzer | "very good; better UI" | ILLUSTRATIVE | **wire to HCRIS** (opex/bed, opex/pt-day are real) — PR 5 |
| `/debt-service` | Debt Service Coverage | "good w/ benchmarks; better UI" | ILLUSTRATIVE | **wire to HCRIS** proxies + benchmark band — PR 5 |
| `/physician-productivity` | Physician Productivity | "pretty good" | ILLUSTRATIVE | label; identify CMS/PECOS source — PR 7 |
| `/provider-retention` | Provider Retention/Churn | "data trust is the issue" | ILLUSTRATIVE | label DATA-REQ; needs roster source — PR 7 |
| `/partner-economics` | Partner Economics / Buy-in | "cool but unclear source/benchmark" | ILLUSTRATIVE | label; define benchmark provenance — PR 7 |
| `/mgmt-comp`, `/phys-comp-plan` | Management Compensation | "cool but illustrative" | ILLUSTRATIVE | label; DATA-REQ (proxy/IRS990?) — PR 7 |
| `/drug-shortage`, `/supply-chain`, `/gpo-supply` | Drug Shortage / Supply Chain | "interesting if data correct; feels illustrative" | ILLUSTRATIVE | label; FDA shortage feed is a build-time-vendor candidate |
| `/cms-apm` | CMS APM Tracker | "good if working; UI/impl" | ILLUSTRATIVE | label; CMS APM is a real public source → convertible |
| `/payer-rate-trends`, `/payer-shift`, `/payer-concentration`, `/payer-contracts` | Payer route trends / shift | "overall good" | ILLUSTRATIVE/REF | label; partly corpus/reference |
| `/biosimilars`, `/drug-pricing-340b` | Biosimilars / 340B | "illustrative, confused purpose" | ILLUSTRATIVE | **define purpose or defer** — PR 8 |
| `/esg-dashboard`, `/esg-impact` | ESG / Sustainability | "confusing; only changes revenue — makes no sense" | ILLUSTRATIVE | **defer/rebuild/delete candidate** — PR 8 |
| `/hcit-platform` | HCIT/SaaS Platform Analyzer | "unclear source; unprofessional" | ILLUSTRATIVE | **fix or delete** — PR 8 |
| `/insurance-tracker`, `/rw-insurance` | Insurance / Malpractice | "unclear; illustrative" | ILLUSTRATIVE | label; needs portfolio/deal link — PR 8 |
| `/ma-contracts` | Local / Contract Analysis | "researchable; unclear source/use" | ILLUSTRATIVE/REF | label; define use case — PR 8 |

## C. Confusing / reframe pages

| Route | Page | User note | Recommendation |
|---|---|---|---|
| `/screening/bankruptcy-survivor` | Bankruptcy Survivor Scan | "what is this for?" | define purpose + UI fix, or defer — PR 8 |
| `/diligence/counterfactual` | Counterfactual Advisor | "confusing, bad UI, concept ok" | clarify function or defer — PR 8 |
| `/diligence/root-cause` | Root Cause Analysis | "good concept; needs real data/CCD demo" | EXPERIMENTAL label; CCD demo — PR 6 area |
| `/diligence/checklist` | Diligence Checklist | "broken; doesn't understand honesty" | **honesty + source-aware** — PR 6 |
| `/diligence/management` | Management (comp) | overlaps `/mgmt-comp` | merge/clarify — PR 7/8 |
| dental prediction | Dental Prediction | "great if CCD ingestion works" | EXPERIMENTAL/DATA-REQ; needs demo |

## D. Reference/corpus pages that belong in Research (not active Diligence unless deal-attached)

| Route | Page | Recommendation |
|---|---|---|
| `/sponsor-track-record`, `/diligence/sponsor-detail` | Sponsor Track Record | already moved to Research (PR D); keep deal-callable |
| `/payer-intelligence`, `/payer-intel` | Payer Intelligence | Research (done); deal-specific Payer Analysis is separate |
| `/find-comps`, `/comparable-outcomes`, `/diligence/comparable-outcomes` | Find Comps / Comparable Outcomes | CORPUS — Research; callable from a deal |

---

## Key recommendations
1. **HCRIS X-Ray is the template** — finish the A-v2 rebuild; reuse `xray_kit`.
2. **Stop illustrative pages from looking LIVE** (PR 2): every `data_public/`
   analyzer gets an `ILLUSTRATIVE` / `DATA REQUIRED` chip + "source not wired"
   note until grounded.
3. **Convert the HCRIS-derivable ones first** — Cost Structure and Debt Service
   are computable from real HCRIS fields (opex, NPR, margins); Payer Stress can
   use the real HCRIS payer-day mix. CMS APM is a real public source.
4. **Move corpus/reference out of active Diligence** (Sponsor, broad Payer
   Intelligence, Find Comps) — done in the IA pass; keep deal-callable.
5. **Defer/delete candidates:** ESG, HCIT/SaaS, Biosimilars, Insurance/
   Malpractice, Bankruptcy Survivor, Counterfactual — pending purpose/source.

See the taxonomy (`PEDESK_DILIGENCE_PAGE_TAXONOMY.md`), the data-source matrix
(`PEDESK_DILIGENCE_DATA_SOURCE_MATRIX.md`), and the reform plan
(`PEDESK_DILIGENCE_REFORM_PLAN.md`).
