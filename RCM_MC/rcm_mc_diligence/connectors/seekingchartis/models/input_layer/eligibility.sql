-- SeekingChartis connector — eligibility
--
-- Tuva contract reference:
--   https://github.com/tuva-health/tuva/blob/v0.17.2/models/input_layer/input_layer__eligibility.yml

{{ config(materialized='table') }}

{% if source_table_exists('raw_data', 'eligibility') | trim == 'true' %}
select
    {{ safe_source_column('raw_data', 'eligibility', 'person_id', 'varchar',
        synonyms=['patient_id','mrn','member_number']) }}                           as person_id,
    {{ safe_source_column('raw_data', 'eligibility', 'member_id', 'varchar',
        synonyms=['subscriber_id']) }}                                               as member_id,
    {{ safe_source_column('raw_data', 'eligibility', 'subscriber_id', 'varchar') }} as subscriber_id,

    {{ safe_source_column('raw_data', 'eligibility', 'gender', 'varchar',
        synonyms=['sex']) }}                                                         as gender,
    {{ safe_source_column('raw_data', 'eligibility', 'race', 'varchar') }}          as race,
    try_cast({{ safe_source_column('raw_data', 'eligibility', 'birth_date', 'varchar',
        synonyms=['dob','date_of_birth']) }} as date)                                as birth_date,
    try_cast({{ safe_source_column('raw_data', 'eligibility', 'death_date', 'varchar') }} as date) as death_date,
    cast({{ safe_source_column('raw_data', 'eligibility', 'death_flag', 'integer') }} as boolean)  as death_flag,

    try_cast({{ safe_source_column('raw_data', 'eligibility', 'enrollment_start_date', 'varchar',
        synonyms=['effective_date','eff_date','span_start']) }} as date)            as enrollment_start_date,
    try_cast({{ safe_source_column('raw_data', 'eligibility', 'enrollment_end_date', 'varchar',
        synonyms=['term_date','termination_date','span_end']) }} as date)           as enrollment_end_date,

    {{ safe_source_column('raw_data', 'eligibility', 'payer', 'varchar') }}         as payer,
    {{ safe_source_column('raw_data', 'eligibility', 'payer_type', 'varchar') }}    as payer_type,
    {{ safe_source_column('raw_data', 'eligibility', 'plan', 'varchar') }}          as plan,

    {{ safe_source_column('raw_data', 'eligibility', 'original_reason_entitlement_code', 'varchar') }} as original_reason_entitlement_code,
    {{ safe_source_column('raw_data', 'eligibility', 'dual_status_code', 'varchar') }}               as dual_status_code,
    {{ safe_source_column('raw_data', 'eligibility', 'medicare_status_code', 'varchar') }}           as medicare_status_code,
    {{ safe_source_column('raw_data', 'eligibility', 'enrollment_status', 'varchar') }}              as enrollment_status,

    cast({{ safe_source_column('raw_data', 'eligibility', 'hospice_flag', 'integer') }} as boolean)          as hospice_flag,
    cast({{ safe_source_column('raw_data', 'eligibility', 'institutional_snp_flag', 'integer') }} as boolean) as institutional_snp_flag,
    cast({{ safe_source_column('raw_data', 'eligibility', 'long_term_institutional_flag', 'integer') }} as boolean) as long_term_institutional_flag,

    {{ safe_source_column('raw_data', 'eligibility', 'group_id', 'varchar') }}       as group_id,
    {{ safe_source_column('raw_data', 'eligibility', 'group_name', 'varchar') }}     as group_name,
    {{ safe_source_column('raw_data', 'eligibility', 'name_suffix', 'varchar') }}    as name_suffix,
    {{ safe_source_column('raw_data', 'eligibility', 'first_name', 'varchar') }}     as first_name,
    {{ safe_source_column('raw_data', 'eligibility', 'middle_name', 'varchar') }}    as middle_name,
    {{ safe_source_column('raw_data', 'eligibility', 'last_name', 'varchar') }}      as last_name,
    {{ safe_source_column('raw_data', 'eligibility', 'social_security_number', 'varchar',
        synonyms=['ssn']) }}                                                          as social_security_number,
    {{ safe_source_column('raw_data', 'eligibility', 'subscriber_relation', 'varchar') }} as subscriber_relation,
    {{ safe_source_column('raw_data', 'eligibility', 'address', 'varchar',
        synonyms=['street_address','address_line_1']) }}                              as address,
    {{ safe_source_column('raw_data', 'eligibility', 'city', 'varchar') }}           as city,
    {{ safe_source_column('raw_data', 'eligibility', 'state', 'varchar') }}          as state,
    {{ safe_source_column('raw_data', 'eligibility', 'zip_code', 'varchar',
        synonyms=['zip','postal_code']) }}                                            as zip_code,
    {{ safe_source_column('raw_data', 'eligibility', 'phone', 'varchar') }}          as phone,
    {{ safe_source_column('raw_data', 'eligibility', 'email', 'varchar') }}          as email,
    {{ safe_source_column('raw_data', 'eligibility', 'ethnicity', 'varchar') }}      as ethnicity,

    coalesce(
        {{ safe_source_column('raw_data', 'eligibility', 'data_source', 'varchar',
            synonyms=['source_system','ehr','clinic']) }},
        'unknown'
    )                                                                                  as data_source,
    {{ safe_source_column('raw_data', 'eligibility', 'file_name', 'varchar') }}      as file_name,
    try_cast({{ safe_source_column('raw_data', 'eligibility', 'file_date', 'varchar') }} as date) as file_date,
    current_localtimestamp()                                                           as ingest_datetime
from {{ source('raw_data', 'eligibility') }}
{% else %}
-- RATIONALE: No eligibility source — emit empty shell. Analysts can
-- still run Phase 0.B analyses that don't require eligibility (e.g.
-- cohort_liquidation) and see the coverage matrix flag the others.
select
    cast(null as varchar) as person_id, cast(null as varchar) as member_id,
    cast(null as varchar) as subscriber_id, cast(null as varchar) as gender,
    cast(null as varchar) as race, cast(null as date) as birth_date,
    cast(null as date) as death_date, cast(null as boolean) as death_flag,
    cast(null as date) as enrollment_start_date, cast(null as date) as enrollment_end_date,
    cast(null as varchar) as payer, cast(null as varchar) as payer_type,
    cast(null as varchar) as plan, cast(null as varchar) as original_reason_entitlement_code,
    cast(null as varchar) as dual_status_code, cast(null as varchar) as medicare_status_code,
    cast(null as varchar) as enrollment_status, cast(null as boolean) as hospice_flag,
    cast(null as boolean) as institutional_snp_flag, cast(null as boolean) as long_term_institutional_flag,
    cast(null as varchar) as group_id, cast(null as varchar) as group_name,
    cast(null as varchar) as name_suffix, cast(null as varchar) as first_name,
    cast(null as varchar) as middle_name, cast(null as varchar) as last_name,
    cast(null as varchar) as social_security_number, cast(null as varchar) as subscriber_relation,
    cast(null as varchar) as address, cast(null as varchar) as city,
    cast(null as varchar) as state, cast(null as varchar) as zip_code,
    cast(null as varchar) as phone, cast(null as varchar) as email,
    cast(null as varchar) as ethnicity, cast(null as varchar) as data_source,
    cast(null as varchar) as file_name, cast(null as date) as file_date,
    current_localtimestamp() as ingest_datetime
where 1 = 0
{% endif %}
