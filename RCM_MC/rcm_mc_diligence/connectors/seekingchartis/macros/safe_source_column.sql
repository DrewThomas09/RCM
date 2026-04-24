{#
  safe_source_column — resolve a source column reference with a typed
  NULL fallback when the column is absent.

  Why we need this: real diligence datasets are messy (multi-EHR
  exports, partial pharmacy, orphan 835s). We'd rather the model
  materialise with NULLs than fail the entire dbt run because one
  acquired clinic didn't export a `subscriber_relation` column.

  Usage:
    select
      {{ safe_source_column('raw_data', 'medical_claims',
                            'claim_id',     'varchar',
                            synonyms=['claim_number','control_id']) }} as claim_id,
      ...

  If any of (col, *synonyms) exist in the source, we pick the first
  present. If none exist, we cast null as the requested dtype. The
  resulting expression is safe to use inside a select list — no `as`
  is added; the caller still writes `... as claim_id`.
#}
{% macro safe_source_column(source_name, table_name, col, dtype, synonyms=[]) %}
    {%- if execute -%}
        {%- set src = source(source_name, table_name) -%}
        {%- set cols = adapter.get_columns_in_relation(src) -%}
        {%- set existing = cols | map(attribute='name') | map('lower') | list -%}
        {%- set candidates = [col] + synonyms -%}
        {%- set found = namespace(name=none) -%}
        {%- for c in candidates -%}
            {%- if found.name is none and c | lower in existing -%}
                {%- set found.name = c -%}
            {%- endif -%}
        {%- endfor -%}
        {%- if found.name is not none -%}
cast({{ adapter.quote(found.name) }} as {{ dtype }})
        {%- else -%}
cast(null as {{ dtype }})
        {%- endif -%}
    {%- else -%}
cast(null as {{ dtype }})
    {%- endif -%}
{% endmacro %}


{#
  source_has — returns true if ANY of the given column names exist in
  the source. Useful for gating optional joins (e.g., merging 835
  remittance in only when the source has a claim_id column).
#}
{% macro source_has(source_name, table_name, cols) %}
    {%- if execute -%}
        {%- set src = source(source_name, table_name) -%}
        {%- set rel_cols = adapter.get_columns_in_relation(src) -%}
        {%- set existing = rel_cols | map(attribute='name') | map('lower') | list -%}
        {%- set found = namespace(ok=true) -%}
        {%- for c in cols -%}
            {%- if c | lower not in existing -%}
                {%- set found.ok = false -%}
            {%- endif -%}
        {%- endfor -%}
        {{ found.ok }}
    {%- else -%}
false
    {%- endif -%}
{% endmacro %}


{#
  source_table_exists — true when a source table is present in the
  warehouse. Used by the pharmacy_claim model, which is legitimately
  absent for many small practices; we materialise an empty shell in
  that case rather than failing.
#}
{% macro source_table_exists(source_name, table_name) %}
    {%- if execute -%}
        {%- set src = source(source_name, table_name) -%}
        {%- set relation = adapter.get_relation(
              database=src.database,
              schema=src.schema,
              identifier=src.identifier
           ) -%}
        {{ (relation is not none) | lower }}
    {%- else -%}
false
    {%- endif -%}
{% endmacro %}
