# PEdesk Diligence Workspace Reform Plan

Sequenced, small PRs. Docs/source-label/Guide work proceeds autonomously;
visible-UI PRs are approval-gated. No invented data.

## Triage
| Page | Keep? | Move? | Source | Status | Fix | Priority |
|---|---|---|---|---|---|---|
| HCRIS X-Ray | keep | — | HCRIS | LIVE | finish A-v2 results | P0 |
| Cost Structure | keep | — | HCRIS | ILLUSTRATIVE→LIVE | wire + UI | P1 |
| Debt Service | keep | — | HCRIS proxy | ILLUSTRATIVE→DERIVED | wire + label + UI | P1 |
| Payer Stress | keep | — | HCRIS payer mix | ILLUSTRATIVE→LIVE | repair + wire | P1 |
| Diligence Checklist | keep | — | USER-DEAL | broken | honesty + source-aware | P1 |
| Physician Productivity | keep | — | CMS? | ILLUSTRATIVE | label + source pass | P2 |
| Provider Retention/Churn | keep | — | DATA-REQ | ILLUSTRATIVE | label DATA-REQ | P2 |
| Partner Economics | keep | — | user model | ILLUSTRATIVE | label | P2 |
| Mgmt Comp | keep | — | IRS990? | ILLUSTRATIVE | label + verify | P2 |
| CMS APM | keep | — | CMS | ILLUSTRATIVE→? | verify source, UI | P2 |
| Payer Rate Trends | keep | maybe Research | REF | ILLUSTRATIVE | label | P3 |
| Root Cause | keep | — | CCD/DATA-REQ | EXPERIMENTAL | demo + label | P3 |
| Drug Shortage / Supply | keep | — | FDA (vendor) | ILLUSTRATIVE | label / vendor source | P3 |
| Dental Prediction | keep | — | CCD | EXPERIMENTAL | demo | P3 |
| Sponsor Track Record | — | Research (done) | CORPUS | LIVE | deal-callable | done |
| Biosimilars / 340B | defer | — | none | ILLUSTRATIVE | define purpose or remove | P4 |
| ESG / Sustainability | defer/delete | — | none | ILLUSTRATIVE | rebuild or delete | P4 |
| HCIT / SaaS | fix/delete | — | unclear | ILLUSTRATIVE | fix or delete | P4 |
| Insurance / Malpractice | label | — | DATA-REQ | ILLUSTRATIVE | deal-link or label | P4 |
| Bankruptcy Survivor | reframe | — | unclear | broken | define + UI | P4 |
| Counterfactual | reframe | — | unclear | confusing | clarify or defer | P4 |

## PR sequence
- **PR 0** — docs (this set). *docs only.*
- **PR 1** — source-and-purpose header component + apply to top 8–12 pages
  (Purpose · Data universe · Source · Confidence · Next action). No calc changes.
- **PR 2** — illustrative-state guardrails: every `data_public/` analyzer shows
  `ILLUSTRATIVE` / `DATA REQUIRED` + "source not wired" until grounded; tests
  that hardcoded demo pages are labeled.
- **PR 3** — HCRIS X-Ray A-v2 results (continues #663).
- **PR 4** — Payer Stress: wire real HCRIS payer-day mix, drop the fabricated
  drivers, repair UI; honest where data missing.
- **PR 5** — Cost Structure + Debt Service: HCRIS-grounded X-Ray-style panels +
  benchmark band + labeled assumptions.
- **PR 6** — Checklist honesty + source-aware behavior (no hallucinated
  completion; show what source backs each item; data-needed states).
- **PR 7** — workforce/provider economics source pass (physician productivity,
  retention/churn, partner economics, comp): label sources + missing data.
- **PR 8** — docs: defer/delete/move candidates (ESG, HCIT, Biosimilars,
  Insurance, Bankruptcy, Counterfactual) with a keep/fix/move/delete call each.

## Success criteria
Every Diligence page: inventoried · data-source classified · purpose
classified · labeled LIVE/DERIVED/ILLUSTRATIVE/DATA-REQUIRED/EXPERIMENTAL ·
no illustrative page looks LIVE · HCRIS X-Ray remains the template · top pages
have headers · Guide explains high-priority pages · a real-data conversion
backlog exists · no fake data · auth/deploy/env/secrets untouched · tests pass.
