-- SeekingChartis connector — pharmacy_claim
--
-- Tuva contract reference:
--   https://github.com/tuva-health/tuva/blob/v0.17.2/models/input_layer/input_layer__pharmacy_claim.yml
--
-- Small acquired practices often lack pharmacy data entirely. We
-- gracefully materialise an empty table when raw_data.pharmacy_claims
-- isn't present, rather than failing the dbt build.

{{ config(materialized='table') }}

{% if source_table_exists('raw_data', 'pharmacy_claims') | trim == 'true' %}
select
    {{ safe_source_column('raw_data', 'pharmacy_claims', 'claim_id', 'varchar',
        synonyms=['rx_id','prescription_id']) }}                                    as claim_id,
    cast({{ safe_source_column('raw_data', 'pharmacy_claims', 'claim_line_number', 'integer',
        synonyms=['line_number']) }} as integer)                                    as claim_line_number,
    {{ safe_source_column('raw_data', 'pharmacy_claims', 'person_id', 'varchar',
        synonyms=['patient_id','mrn','member_number']) }}                            as person_id,
    {{ safe_source_column('raw_data', 'pharmacy_claims', 'member_id', 'varchar',
        synonyms=['subscriber_id']) }}                                               as member_id,
    {{ safe_source_column('raw_data', 'pharmacy_claims', 'payer', 'varchar') }}     as payer,
    {{ safe_source_column('raw_data', 'pharmacy_claims', 'plan', 'varchar') }}      as plan,

    {{ safe_source_column('raw_data', 'pharmacy_claims', 'prescribing_provider_npi', 'varchar',
        synonyms=['prescriber_npi']) }}                                              as prescribing_provider_npi,
    {{ safe_source_column('raw_data', 'pharmacy_claims', 'dispensing_provider_npi', 'varchar',
        synonyms=['pharmacy_npi']) }}                                                as dispensing_provider_npi,

    try_cast({{ safe_source_column('raw_data', 'pharmacy_claims', 'dispensing_date', 'varchar',
        synonyms=['fill_date','dispense_date']) }} as date)                          as dispensing_date,

    {{ safe_source_column('raw_data', 'pharmacy_claims', 'ndc_code', 'varchar',
        synonyms=['ndc']) }}                                                         as ndc_code,
    cast({{ safe_source_column('raw_data', 'pharmacy_claims', 'quantity', 'float') }} as double)  as quantity,
    cast({{ safe_source_column('raw_data', 'pharmacy_claims', 'days_supply', 'integer') }} as integer) as days_supply,
    cast({{ safe_source_column('raw_data', 'pharmacy_claims', 'refills', 'integer') }} as integer) as refills,

    try_cast({{ safe_source_column('raw_data', 'pharmacy_claims', 'paid_date', 'varchar') }} as date) as paid_date,
    cast({{ safe_source_column('raw_data', 'pharmacy_claims', 'paid_amount', 'float') }} as double) as paid_amount,
    cast({{ safe_source_column('raw_data', 'pharmacy_claims', 'allowed_amount', 'float') }} as double) as allowed_amount,
    cast({{ safe_source_column('raw_data', 'pharmacy_claims', 'charge_amount', 'float',
        synonyms=['billed_amount']) }} as double)                                    as charge_amount,
    cast({{ safe_source_column('raw_data', 'pharmacy_claims', 'coinsurance_amount', 'float') }} as double) as coinsurance_amount,
    cast({{ safe_source_column('raw_data', 'pharmacy_claims', 'copayment_amount', 'float') }} as double) as copayment_amount,
    cast({{ safe_source_column('raw_data', 'pharmacy_claims', 'deductible_amount', 'float') }} as double) as deductible_amount,

    cast({{ safe_source_column('raw_data', 'pharmacy_claims', 'in_network_flag', 'integer') }} as boolean) as in_network_flag,
    coalesce(
        {{ safe_source_column('raw_data', 'pharmacy_claims', 'data_source', 'varchar',
            synonyms=['source_system','ehr','clinic']) }},
        'unknown'
    )                                                                                 as data_source,
    {{ safe_source_column('raw_data', 'pharmacy_claims', 'file_name', 'varchar') }}  as file_name,
    try_cast({{ safe_source_column('raw_data', 'pharmacy_claims', 'file_date', 'varchar') }} as date) as file_date,
    current_localtimestamp()                                                          as ingest_datetime
from {{ source('raw_data', 'pharmacy_claims') }}
{% else %}
-- RATIONALE: No pharmacy_claims source — emit a shape-compatible empty
-- table so Tuva's input_layer__pharmacy_claim materialises cleanly.
select
    cast(null as varchar)   as claim_id,
    cast(null as integer)   as claim_line_number,
    cast(null as varchar)   as person_id,
    cast(null as varchar)   as member_id,
    cast(null as varchar)   as payer,
    cast(null as varchar)   as plan,
    cast(null as varchar)   as prescribing_provider_npi,
    cast(null as varchar)   as dispensing_provider_npi,
    cast(null as date)      as dispensing_date,
    cast(null as varchar)   as ndc_code,
    cast(null as double)    as quantity,
    cast(null as integer)   as days_supply,
    cast(null as integer)   as refills,
    cast(null as date)      as paid_date,
    cast(null as double)    as paid_amount,
    cast(null as double)    as allowed_amount,
    cast(null as double)    as charge_amount,
    cast(null as double)    as coinsurance_amount,
    cast(null as double)    as copayment_amount,
    cast(null as double)    as deductible_amount,
    cast(null as boolean)   as in_network_flag,
    cast(null as varchar)   as data_source,
    cast(null as varchar)   as file_name,
    cast(null as date)      as file_date,
    current_localtimestamp() as ingest_datetime
where 1 = 0
{% endif %}
