# PEdesk import templates

Blank, schema-only CSV templates for the user/deal/fund data that activates
DATA REQUIRED pages. Each `*_template.csv` has the **real header row** (field
names) and one **clearly-non-real placeholder row** (`<text>` / `<number>` /
`<YYYY-MM-DD>`). **No fabricated values** — fill with your own data and import.

## How to use
1. Download the relevant `*_template.csv`.
2. Replace the placeholder row with your real rows (keep the header).
3. Import via the page's upload action (or `/import`).
4. PII columns (names, NPI, claim ids) — de-identify per your data policy;
   PEdesk drops PII at ingest for any aggregate it persists.

## Field conventions
- `text` — free text · `number` — numeric (no `$`/`,`) · `date` — `YYYY-MM-DD`.
- Columns marked `req` in the activation plan are required to activate the page;
  `opt` enrich the analysis.
- `source_owner` (who to request from) and per-page required fields are listed
  in `docs/reports/RED_PAGE_ACTIVATION_PLAN.md`.

## Templates
Covers management comp, partner economics, mgmt-fee, key person, treasury/debt,
fundraising, NAV loan, secondaries, continuation vehicle, co-invest, board
governance, capex, operating partners, compliance attestation, TSA, PMI,
sell-side process, diligence vendors, VDR, VCP, ZBB, platform maturity, AI
operating model, direct lending, claims/denials, AR aging, payer contracts,
lease schedule, cyber controls, EHR/RCM vendor stack, insurance schedule,
litigation matters, and risk register.
