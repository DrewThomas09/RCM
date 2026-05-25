# RED Page Activation Plan (Product-Readiness mode)

The remaining RED pages have **no clean public dataset** to anchor them — but
RED should not stay RED. Each becomes an honest, actionable state with a clear
activation path (the data a user/deal must supply), an import template, Guide
context, and tests proving it presents **no fake values as real**.

**New honest end-states** (beyond the 4-tier surface taxonomy):
LIVE · DERIVED · CONTEXTUAL · DATA REQUIRED · **USER DATA REQUIRED** ·
ILLUSTRATIVE · RESEARCH REFERENCE · DEFERRED WITH REASON.

Surface-status mechanics: a new `data_required` tier (amber) represents pages
converted from fabricated-RED to "your data activates this." Each gets a shared
**"Data needed to activate this analysis"** panel + an import template under
`docs/import_templates/` + a Guide context.

Status legend below: `plan` = documented here · `done` = converted.

---

## Batch 1 — Internal / fund / deal pages → USER DATA REQUIRED

These are PE-fund / portfolio-internal surfaces. No public dataset exists; they
require the user's own fund/deal records. Convert to USER DATA REQUIRED with a
data-needed panel + import template + Guide context; strip/label any fake values.

| Route | Title | Required user data | Import template | Status |
|---|---|---|---|---|
| /mgmt-comp | Management Compensation | exec comp by role (base/bonus/equity/FMV) | management_compensation_template.csv | plan |
| /partner-economics | Partner Economics | partner points/carry/draws/distributions | partner_economics_template.csv | plan |
| /mgmt-fee-tracker | Mgmt Fee Tracker | fund mgmt-fee schedule, basis, offsets | mgmt_fee_schedule_template.csv | plan |
| /key-person | Key Person | key execs, tenure, succession, dependency | key_person_template.csv | plan |
| /treasury | Treasury | cash, debt schedule, facilities, covenants | treasury_debt_schedule_template.csv | plan |
| /fundraising | Fundraising | fund target, commitments, LP pipeline | fundraising_template.csv | plan |
| /nav-loan-tracker | NAV Loan Tracker | NAV facilities, advance rate, LTV, cost | nav_loan_template.csv | plan |
| /secondaries-tracker | Secondaries Tracker | secondary offers, NAV, discount, buyer | secondaries_template.csv | plan |
| /continuation-vehicle | Continuation Vehicle | CV assets, NAV, rollover %, terms | continuation_vehicle_template.csv | plan |
| /coinvest-pipeline | Co-Invest Pipeline | co-invest opportunities, sizing, LP demand | coinvest_pipeline_template.csv | plan |
| /board-governance | Board Governance | board roster, committees, meeting cadence | board_governance_template.csv | plan |
| /capex-budget | Capex Budget | capex projects, budget/actual, ROI | capex_budget_template.csv | plan |
| /operating-partners | Operating Partners | OP roster, assignments, value-add KPIs | operating_partners_template.csv | plan |
| /compliance-attestation | Compliance Attestation | attestations, owners, due dates, status | compliance_attestation_template.csv | plan |
| /transition-services | Transition Services (TSA) | TSA scope, duration, cost, exit plan | tsa_template.csv | plan |
| /pmi-integration | PMI Integration | integration workstreams, milestones, synergy | pmi_integration_template.csv | plan |
| /pmi-playbook | PMI Playbook | playbook tasks by function, owners, timing | (reuse pmi_integration_template.csv) | plan |
| /sellside-process | Sell-Side Process | process timeline, buyer list, bids | sellside_process_template.csv | plan |
| /diligence-vendors | Diligence Vendors | vendor list, scope, fees, status | diligence_vendors_template.csv | plan |
| /vdr-tracker | VDR Tracker | data-room index, request log, Q&A | vdr_tracker_template.csv | plan |
| /vcp-tracker | Value-Creation Plan Tracker | VCP initiatives, owners, $ impact, status | vcp_tracker_template.csv | plan |
| /zbb-tracker | Zero-Based Budget Tracker | cost lines, baseline, target, savings | zbb_tracker_template.csv | plan |
| /platform-maturity | Platform Maturity | maturity dimensions, self-scores, evidence | platform_maturity_template.csv | plan |
| /ai-operating-model | AI Operating Model | AI use-cases, adoption, ROI, risk | ai_operating_model_template.csv | plan |
| /direct-lending | Direct Lending | loan book, spreads, covenants, defaults | direct_lending_template.csv | plan |

## Batch 2 — RCM / revenue-cycle → DATA REQUIRED

Need the target's claims/AR data. No public claim-level denial dataset exists.

| Route | Title | Required files | Status |
|---|---|---|---|
| /revenue-leakage | Revenue Leakage | charge master, 835 remittance, denial codes, AR aging | plan |
| /rcm-red-flags | RCM Red Flags | claims extract, denial codes, AR aging, encounter volume | plan |
| /redflag-scanner | Red-Flag Scanner | financials, KPIs, payer mix, AR aging | plan |
| /risk-matrix | Risk Matrix | risk register (likelihood/impact/owner/mitigation) | plan |

Required RCM files (shared spec): claims_extract, denial_codes (CARC/RARC),
payer_contracts, remittance_835, charge_master, ar_aging, encounter_volume.

## Batch 3 — Insurance / litigation / cyber / real-estate / HCIT → USER DATA REQUIRED

| Route | Title | Required user data | Status |
|---|---|---|---|
| /insurance-tracker | Insurance Tracker | policy schedule, limits, premiums, claims history | plan |
| /rw-insurance | RW Insurance | policy list, coverage, renewal, loss runs | plan |
| /litigation | Litigation | matter list, status, exposure, reserves | plan |
| /cyber-risk | Cyber Risk | controls inventory, frameworks, incidents | plan |
| /medical-realestate | Medical Real Estate | lease schedule, rent, term, options, owned RE | plan |
| /real-estate | Real Estate | property list, lease/own, value, NOI | plan |
| /hcit-platform | HCIT Platform | EHR/RCM vendor stack, contracts, modules | plan |
| /tech-stack | Tech Stack | application inventory, spend, contracts | plan |
| /clinical-ai | Clinical AI | AI tools, vendors, use-cases, validation | plan |
| /digital-front-door | Digital Front Door | patient-access channels, volumes, conversion | plan |
| /direct-employer | Direct Employer | employer contracts, lives, PEPM, services | plan |

Contextual public data where honest: insurance/litigation have none clean;
real-estate could later use county assessor data (deferred); HCIT could use
KLAS-style references (licensed). For now USER DATA REQUIRED.

## Batch 4 — Calculators / deferred

| Route | Title | Disposition |
|---|---|---|
| /diligence/physician-eu | Physician Economic Unit | NAVY calculator (runs on your roster inputs) — reclassify NAVY w/ data-needed note, not RED |
| /diligence/risk-workbench | Risk Workbench | DATA REQUIRED (risk register upload) |
| /ma-star | MA Star Ratings | DEFERRED WITH REASON — CMS MA Star Ratings is zip-portal only (not a scriptable API); revisit if a CSV form appears |

---

## Implementation order
1. This plan (done when committed).
2. Infra: `data_required` surface tier + shared `data_required_panel` helper + validators.
3. Batch 1 conversions + import templates + Guide contexts.
4. Batch 2 (RCM).
5. Batch 3 (insurance/litigation/cyber/RE/HCIT).
6. Batch 4 (calculators/deferred).
7. Continue public-dataset scouting in parallel where genuinely useful.

## Validators to add
- `test_red_pages_have_activation_plan` — every RED route appears in this plan.
- `test_data_required_pages_have_panel_and_guide` — DATA REQUIRED pages carry the data-needed panel + a DOCUMENTED Guide context.
- `test_import_templates_exist` — every referenced template file exists.
- `test_no_fake_internal_data_claims` — internal pages don't present fabricated $ as live (disclosed/illustrative only).
