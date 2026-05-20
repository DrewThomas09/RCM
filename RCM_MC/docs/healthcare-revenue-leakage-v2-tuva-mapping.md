# CCD → Tuva Input-Layer Mapping

How the Canonical Claims Dataset (CCD) maps to the Tuva Project's
analytics-ready input layer, so partners who want Tuva's richer marts
(CCSR, HCC, financial_pmpm, readmissions) can run vendored Tuva dbt on
top of our normalized snapshot. The live mapping is implemented in
`rcm_mc/diligence/ingest/tuva_bridge.py`
(`ccd_to_tuva_input_layer_arrow`, `write_tuva_input_layer_duckdb`),
pinned to Tuva v0.17.1's `input_layer`. This doc is the human-readable
contract.

Tuva is **not** a parser — it consumes already-normalized claims. PEDesk
owns upload → X12 parse → CCD; Tuva (optionally) owns the downstream
analytics modeling. Tuva/dbt/duckdb are optional `[diligence]` extras.

## medical_claim (the table Phase 1 populates)

| Tuva column | CCD source field | Source X12 segment | Transformation | Confidence | Open questions |
|---|---|---|---|---|---|
| claim_id | `claim_id` | 837 CLM01 / 835 CLP01 | verbatim | high | — |
| claim_line_number | `line_number` | service-line index | 1-indexed | high | multi-line splits not yet expanded |
| claim_type | derived | 837 (P vs I) | `institutional` if `bill_type` else `professional` | medium | 837I loop coverage partial |
| person_id / member_id | `patient_id` | NM1*IL/QC member id | **tokenized** (HMAC) before persist | high | de-dupe across payers TBD |
| payer | `payer_canonical` ?? `payer_raw` | 835 N1*PR / 837 NM1*PR | canonicalized via payer map | high | long-tail payers → UNKNOWN |
| claim_start/end_date | `service_date_from/to` | DTP*472 / DTM*232 | multi-format date parse | high | range vs single-day |
| place_of_service_code | `place_of_service` | CLM05-1 | verbatim | medium | not always present |
| bill_type_code | `bill_type` | 837I CLM05 | verbatim | low | 837I only |
| drg_code(+type) | `drg` | HI (DRG) | `ms-drg` when present | medium | APR-DRG not distinguished |
| hcpcs_code | `cpt_code` | SV1 / SVC (HC:) | strip `HC:` qualifier | high | modifiers captured separately |
| rendering_npi / billing_npi | `rendering_npi` / `billing_npi` | NM1*82 / NM1*85 / N1*PE (XX) | NPI by XX qualifier | medium | facility_npi not yet mapped |
| paid_date | `paid_date` | 835 DTM*405 | date parse | medium | only on remittance side |
| paid_amount | `paid_amount` | 835 CLP04 | float | high | — |
| allowed_amount | `allowed_amount` | derived/CAS | often null pre-repricing | low | needs contract schedule |
| charge_amount | `charge_amount` | CLM02 / CLP03 | float | high | — |
| (adjustments) | `adjustment_reason_codes` + `adjustment_amount` | 835 CAS | CARC set + summed $ | medium | per-code $ collapsed to one total |

## pharmacy_claim

Not populated from 835/837 (these are medical, not NCPDP pharmacy
claims). Emitted as an empty-but-typed table so Tuva's downstream models
run. **Open question:** NCPDP D.0 ingestion is out of scope for V2.

## eligibility

Minimal: one row per distinct tokenized `person_id` with the payer.
Enrollment spans (start/end) are not in 835/837 — **open question:**
source 834 enrollment files if eligibility marts are needed.

## Notes / guardrails

- Identifiers are tokenized in the CCD before this mapping runs; Tuva
  never sees raw MRNs.
- Per-code CAS adjustment dollars are summed into one `adjustment_amount`
  on the CCD; if Tuva-side denial analytics need per-code dollars, extend
  the parser payload to carry `(code, amount)` pairs.
- This mapping is additive and optional; the PEDesk PE marts
  (`diligence/analytics`) do not depend on Tuva running.
