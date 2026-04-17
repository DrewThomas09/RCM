# Data Requests — Midwest Community Hospital ($500M NPSR)

Generated 2026-04-15 03:28 UTC. Based on the most recent RCM Monte Carlo run.

**Current evidence grade: D** — 0 of 32 model inputs observed from target data (0%). Closing the gaps below improves defensibility and tightens the EBITDA range.

## Priority asks — currently analyst assumptions

Grouped by payer. Each row is what to ask management for.

### Medicare

| Metric | Request |
|--------|---------|
| `denials.idr` | Denials extract: claim_id, payer, denial_date, denial_amount, denial_reason. |
| `denials.fwr` | Final-status flag on denied claims (paid vs written-off after appeals). |
| `underpayments.upr` | Contractual allowance analysis: expected vs paid per claim/payer. |
| `revenue_share` | Net revenue by payer for the trailing 12 months (claims_summary extract). |
| `avg_claim_dollars` | Claim count and total paid by payer (for average claim size calc). |
| `dar_clean_days` | A/R aging detail by payer (include 0-30 / 31-60 / 61-90 / 90+ buckets). |
| `denials.stage_mix` | Appeal stage flag per denial (L1 / L2 / L3 / ALJ, or local equivalents). |
| `underpayments.severity` | Underpayment dollar magnitudes by payer (same contractual analysis). |
| `underpayments.recovery` | Historical rework recovery rate on flagged underpayments. |

### Medicaid

| Metric | Request |
|--------|---------|
| `denials.idr` | Denials extract: claim_id, payer, denial_date, denial_amount, denial_reason. |
| `denials.fwr` | Final-status flag on denied claims (paid vs written-off after appeals). |
| `underpayments.upr` | Contractual allowance analysis: expected vs paid per claim/payer. |
| `revenue_share` | Net revenue by payer for the trailing 12 months (claims_summary extract). |
| `avg_claim_dollars` | Claim count and total paid by payer (for average claim size calc). |
| `dar_clean_days` | A/R aging detail by payer (include 0-30 / 31-60 / 61-90 / 90+ buckets). |
| `denials.stage_mix` | Appeal stage flag per denial (L1 / L2 / L3 / ALJ, or local equivalents). |
| `underpayments.severity` | Underpayment dollar magnitudes by payer (same contractual analysis). |
| `underpayments.recovery` | Historical rework recovery rate on flagged underpayments. |

### Commercial

| Metric | Request |
|--------|---------|
| `denials.idr` | Denials extract: claim_id, payer, denial_date, denial_amount, denial_reason. |
| `denials.fwr` | Final-status flag on denied claims (paid vs written-off after appeals). |
| `underpayments.upr` | Contractual allowance analysis: expected vs paid per claim/payer. |
| `revenue_share` | Net revenue by payer for the trailing 12 months (claims_summary extract). |
| `avg_claim_dollars` | Claim count and total paid by payer (for average claim size calc). |
| `dar_clean_days` | A/R aging detail by payer (include 0-30 / 31-60 / 61-90 / 90+ buckets). |
| `denials.stage_mix` | Appeal stage flag per denial (L1 / L2 / L3 / ALJ, or local equivalents). |
| `underpayments.severity` | Underpayment dollar magnitudes by payer (same contractual analysis). |
| `underpayments.recovery` | Historical rework recovery rate on flagged underpayments. |

### (hospital-level)

| Metric | Request |
|--------|---------|
| `hospital.annual_revenue` | Audited NPSR for the trailing 12 months (income-statement line or payer-mix roll-up). |
| `economics.wacc_annual` | Target WACC assumption to sanity-check working-capital carry. |

### SelfPay

| Metric | Request |
|--------|---------|
| `revenue_share` | Net revenue by payer for the trailing 12 months (claims_summary extract). |
| `avg_claim_dollars` | Claim count and total paid by payer (for average claim size calc). |
| `dar_clean_days` | A/R aging detail by payer (include 0-30 / 31-60 / 61-90 / 90+ buckets). |

