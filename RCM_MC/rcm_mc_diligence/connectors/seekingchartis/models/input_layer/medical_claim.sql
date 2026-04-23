-- SeekingChartis connector — medical_claim
--
-- This model is the target of Tuva's input_layer__medical_claim
-- (`select * from ref('medical_claim')`). Column set and types must
-- match the Tuva Input Layer contract:
--   https://github.com/tuva-health/tuva/blob/v0.17.2/models/input_layer/input_layer__medical_claim.yml
--
-- Design notes:
-- - Multi-EHR acquired-practice data arrives with heterogeneous column
--   names (patient_id / mrn / member_number; date_of_service /
--   claim_from_date / service_start_date). safe_source_column picks
--   the first present synonym and NULLs the rest.
-- - 835 remittance joins on claim_id → paid_amount / paid_date when
--   medical_claims alone doesn't carry them. Orphan 835 rows are
--   handled by rules.py (not here — joining-in an orphan would hide
--   the issue).
-- - Claim line number is derived when the source has a single row per
--   claim (partner usually doesn't carry a line number in small-
--   practice exports).

{{ config(materialized='table') }}

with src as (
    select * from {{ source('raw_data', 'medical_claims') }}
),

remit as (
    {%- if source_table_exists('raw_data', 'remittance') | trim == 'true' -%}
    select
          {{ safe_source_column('raw_data', 'remittance', 'claim_id', 'varchar') }}    as claim_id,
          {{ safe_source_column('raw_data', 'remittance', 'paid_amount', 'float') }}   as paid_amount,
          {{ safe_source_column('raw_data', 'remittance', 'paid_date', 'date',
              synonyms=['remit_date','check_date']) }}                                  as paid_date,
          {{ safe_source_column('raw_data', 'remittance', 'allowed_amount', 'float') }} as allowed_amount
    from {{ source('raw_data', 'remittance') }}
    {%- else -%}
    select
          cast(null as varchar) as claim_id,
          cast(null as float)   as paid_amount,
          cast(null as date)    as paid_date,
          cast(null as float)   as allowed_amount
    where 1 = 0
    {%- endif %}
),

-- RATIONALE: Reduce remittance to one row per claim by summing the
-- paid_amount across adjudication events. This is the conservative
-- reconciliation used when Tuva's ADR logic runs downstream; the
-- duplicate_adjudication rule in rules.py surfaces the count so
-- partners know the reconciliation happened.
remit_reduced as (
    select
          claim_id,
          sum(paid_amount)    as paid_amount,
          max(paid_date)      as paid_date,
          max(allowed_amount) as allowed_amount
    from remit
    where claim_id is not null
    group by claim_id
),

-- RATIONALE: Drop `r.claim_id` from the joined output so the final
-- select can unambiguously reference `claim_id` from `src.*`. Keeping
-- it would cause a DuckDB Binder Error on columns that collide with
-- remit's own column names.
joined as (
    select src.*,
           r.paid_amount    as r_paid,
           r.paid_date      as r_paid_date,
           r.allowed_amount as r_allowed
    from src
    left join remit_reduced r
      on r.claim_id = {{ safe_source_column('raw_data', 'medical_claims', 'claim_id', 'varchar',
          synonyms=['claim_number','control_id','claim_control_number']) }}
)

select
    -- SOURCE: claim_id | claim_number | control_id | claim_control_number
    -- RATIONALE: Multi-EHR exports use different headers for the claim
    -- primary key; we accept the first present synonym.
    {{ safe_source_column('raw_data', 'medical_claims', 'claim_id', 'varchar',
        synonyms=['claim_number','control_id','claim_control_number']) }}                 as claim_id,

    -- SOURCE: claim_line_number
    -- RATIONALE: Small-practice exports often lack a line number. We
    -- preserve it when present; otherwise the downstream Tuva
    -- unique-key test will flag the gap so partners can ask for a
    -- line-level export instead of silently synthesising a value.
    cast({{ safe_source_column('raw_data', 'medical_claims', 'claim_line_number', 'integer',
        synonyms=['line_number','line_num','service_line']) }} as integer)             as claim_line_number,

    -- SOURCE: claim_type
    -- RATIONALE: Normalise to Tuva's professional/institutional/dental
    -- vocabulary by lowercasing. Full mapping is Phase 0.B (encounter
    -- bucketing); here we pass the source value through.
    lower({{ safe_source_column('raw_data', 'medical_claims', 'claim_type', 'varchar',
        synonyms=['bill_type_indicator']) }})                                           as claim_type,

    -- SOURCE: patient_id | mrn | member_number
    -- RATIONALE: These three variants appear in Epic, Cerner, and Athena
    -- exports respectively. Merge on any present; downstream
    -- normalisation keys on MRN+DOB where ambiguous.
    {{ safe_source_column('raw_data', 'medical_claims', 'patient_id', 'varchar',
        synonyms=['mrn','member_number','member_id']) }}                                 as person_id,
    {{ safe_source_column('raw_data', 'medical_claims', 'member_id', 'varchar',
        synonyms=['subscriber_id','mrn']) }}                                             as member_id,

    -- SOURCE: payer | payer_name
    {{ safe_source_column('raw_data', 'medical_claims', 'payer', 'varchar',
        synonyms=['payer_name','payer_id','insurance_name']) }}                          as payer,
    {{ safe_source_column('raw_data', 'medical_claims', 'plan', 'varchar',
        synonyms=['plan_name','product_name']) }}                                        as plan,

    -- SOURCE: claim_start_date | service_start_date | date_of_service
    -- RATIONALE: The three EHRs use MM/DD/YYYY, YYYY-MM-DD, and Unix
    -- epoch. The file_loader's pyarrow inference aligns them to `date`
    -- at load time; here we cast defensively so a stray string value
    -- doesn't break the build.
    try_cast({{ safe_source_column('raw_data', 'medical_claims', 'claim_start_date', 'varchar',
        synonyms=['service_start_date','date_of_service','dos','from_date']) }} as date)  as claim_start_date,

    try_cast({{ safe_source_column('raw_data', 'medical_claims', 'claim_end_date', 'varchar',
        synonyms=['service_end_date','thru_date']) }} as date)                            as claim_end_date,

    try_cast({{ safe_source_column('raw_data', 'medical_claims', 'claim_line_start_date', 'varchar',
        synonyms=['line_start_date']) }} as date)                                         as claim_line_start_date,
    try_cast({{ safe_source_column('raw_data', 'medical_claims', 'claim_line_end_date', 'varchar',
        synonyms=['line_end_date']) }} as date)                                           as claim_line_end_date,

    try_cast({{ safe_source_column('raw_data', 'medical_claims', 'admission_date', 'varchar',
        synonyms=['admit_date']) }} as date)                                              as admission_date,
    try_cast({{ safe_source_column('raw_data', 'medical_claims', 'discharge_date', 'varchar') }} as date)
                                                                                          as discharge_date,

    {{ safe_source_column('raw_data', 'medical_claims', 'admit_source_code', 'varchar') }}    as admit_source_code,
    {{ safe_source_column('raw_data', 'medical_claims', 'admit_type_code', 'varchar') }}      as admit_type_code,
    {{ safe_source_column('raw_data', 'medical_claims', 'discharge_disposition_code', 'varchar') }} as discharge_disposition_code,

    {{ safe_source_column('raw_data', 'medical_claims', 'place_of_service_code', 'varchar',
        synonyms=['pos','pos_code']) }}                                                   as place_of_service_code,
    {{ safe_source_column('raw_data', 'medical_claims', 'bill_type_code', 'varchar') }}   as bill_type_code,
    {{ safe_source_column('raw_data', 'medical_claims', 'drg_code_type', 'varchar') }}    as drg_code_type,
    {{ safe_source_column('raw_data', 'medical_claims', 'drg_code', 'varchar') }}         as drg_code,
    {{ safe_source_column('raw_data', 'medical_claims', 'revenue_center_code', 'varchar') }} as revenue_center_code,
    cast({{ safe_source_column('raw_data', 'medical_claims', 'service_unit_quantity', 'integer',
        synonyms=['unit_qty','units']) }} as integer)                                     as service_unit_quantity,

    {{ safe_source_column('raw_data', 'medical_claims', 'hcpcs_code', 'varchar',
        synonyms=['cpt_code','procedure_code']) }}                                        as hcpcs_code,
    {{ safe_source_column('raw_data', 'medical_claims', 'hcpcs_modifier_1', 'varchar',
        synonyms=['modifier_1','mod_1']) }}                                               as hcpcs_modifier_1,
    {{ safe_source_column('raw_data', 'medical_claims', 'hcpcs_modifier_2', 'varchar') }} as hcpcs_modifier_2,
    {{ safe_source_column('raw_data', 'medical_claims', 'hcpcs_modifier_3', 'varchar') }} as hcpcs_modifier_3,
    {{ safe_source_column('raw_data', 'medical_claims', 'hcpcs_modifier_4', 'varchar') }} as hcpcs_modifier_4,
    {{ safe_source_column('raw_data', 'medical_claims', 'hcpcs_modifier_5', 'varchar') }} as hcpcs_modifier_5,

    {{ safe_source_column('raw_data', 'medical_claims', 'rendering_npi', 'varchar') }}    as rendering_npi,
    {{ safe_source_column('raw_data', 'medical_claims', 'rendering_tin', 'varchar') }}    as rendering_tin,
    {{ safe_source_column('raw_data', 'medical_claims', 'billing_npi', 'varchar') }}      as billing_npi,
    {{ safe_source_column('raw_data', 'medical_claims', 'billing_tin', 'varchar') }}      as billing_tin,
    {{ safe_source_column('raw_data', 'medical_claims', 'facility_npi', 'varchar') }}     as facility_npi,

    -- RATIONALE: paid_date / paid_amount come from either the 837 row
    -- itself (integrated exports) or from the 835 remittance join.
    -- Prefer the 837 when present because it reflects the adjudicated
    -- final value after all payer passes.
    coalesce(
        try_cast({{ safe_source_column('raw_data', 'medical_claims', 'paid_date', 'varchar') }} as date),
        joined.r_paid_date
    )                                                                                      as paid_date,
    coalesce(
        cast({{ safe_source_column('raw_data', 'medical_claims', 'paid_amount', 'float') }} as double),
        joined.r_paid
    )                                                                                      as paid_amount,
    coalesce(
        cast({{ safe_source_column('raw_data', 'medical_claims', 'allowed_amount', 'float') }} as double),
        joined.r_allowed
    )                                                                                      as allowed_amount,

    cast({{ safe_source_column('raw_data', 'medical_claims', 'charge_amount', 'float',
        synonyms=['billed_amount','total_charge']) }} as double)                           as charge_amount,
    cast({{ safe_source_column('raw_data', 'medical_claims', 'coinsurance_amount', 'float') }} as double) as coinsurance_amount,
    cast({{ safe_source_column('raw_data', 'medical_claims', 'copayment_amount', 'float') }} as double)   as copayment_amount,
    cast({{ safe_source_column('raw_data', 'medical_claims', 'deductible_amount', 'float') }} as double)  as deductible_amount,
    cast({{ safe_source_column('raw_data', 'medical_claims', 'total_cost_amount', 'float') }} as double)  as total_cost_amount,

    {{ safe_source_column('raw_data', 'medical_claims', 'diagnosis_code_type', 'varchar') }} as diagnosis_code_type,

    {# diagnosis_code_1..25 — emit all 25, each falling back to NULL. #}
    {% for i in range(1, 26) %}
    {{ safe_source_column('raw_data', 'medical_claims', 'diagnosis_code_' ~ i, 'varchar') }} as diagnosis_code_{{ i }},
    {% endfor %}
    {% for i in range(1, 26) %}
    {{ safe_source_column('raw_data', 'medical_claims', 'diagnosis_poa_' ~ i, 'varchar') }} as diagnosis_poa_{{ i }},
    {% endfor %}

    {{ safe_source_column('raw_data', 'medical_claims', 'procedure_code_type', 'varchar') }} as procedure_code_type,
    {% for i in range(1, 26) %}
    {{ safe_source_column('raw_data', 'medical_claims', 'procedure_code_' ~ i, 'varchar') }} as procedure_code_{{ i }},
    {% endfor %}
    {% for i in range(1, 26) %}
    try_cast({{ safe_source_column('raw_data', 'medical_claims', 'procedure_date_' ~ i, 'varchar') }} as date) as procedure_date_{{ i }},
    {% endfor %}

    cast({{ safe_source_column('raw_data', 'medical_claims', 'in_network_flag', 'integer') }} as boolean)   as in_network_flag,

    -- RATIONALE: data_source is the clinic identifier when fixtures are
    -- merged across acquired practices. If the source doesn't tag
    -- rows, we fall back to the file name captured at load time. The
    -- multi_ehr_merge rule in rules.py uses distinct counts of this
    -- to verify multi-EHR normalisation worked.
    coalesce(
        {{ safe_source_column('raw_data', 'medical_claims', 'data_source', 'varchar',
            synonyms=['source_system','ehr','clinic']) }},
        'unknown'
    )                                                                                       as data_source,
    {{ safe_source_column('raw_data', 'medical_claims', 'file_name', 'varchar') }}         as file_name,
    try_cast({{ safe_source_column('raw_data', 'medical_claims', 'file_date', 'varchar') }} as date) as file_date,
    current_localtimestamp()                                                                as ingest_datetime
from joined
