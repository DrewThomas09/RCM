# Verticals

Vertical-specific dispatching for different healthcare facility types. Routes metric registries, bridges, and ontologies based on the deal's vertical type, enabling the platform to handle non-hospital RCM targets.

---

## `registry.py` — Vertical Dispatch Registry

**What it does:** Defines the `Vertical` enum (HOSPITAL, ASC, BEHAVIORAL_HEALTH, MSO) and a dispatch registry that maps each vertical to its specific metric registry, bridge implementation, and ontology. Enables the platform to handle ambulatory surgery centers, behavioral health platforms, and management services organizations with their distinct economic structures.

**How it works:** `_VERTICAL_REGISTRY` dict maps each `Vertical` to a `VerticalDefinition` with: `metric_registry` (the set of relevant metrics for that vertical), `bridge_class` (the bridge implementation to use — defaults to `rcm_ebitda_bridge.RCMEBITDABridge` for hospitals, specialized implementations for ASC and behavioral health), `ontology_module` (the ontology module with vertical-specific causal DAG), `benchmark_filter` (SQL WHERE clause fragment to scope HCRIS queries to the right facility type). `get_vertical_definition(vertical)` is the single dispatch function called by `packet_builder.py`. If no vertical is specified, defaults to `HOSPITAL`.

**Data in:** `Vertical` enum value from the deal's profile (set during intake or via deal settings).

**Data out:** `VerticalDefinition` consumed by `packet_builder.py` to use the correct metric registry and bridge for the deal's facility type.

---

## `asc/` — Ambulatory Surgery Center Modules

**What it does:** ASC-specific metric registry and bridge implementation. ASCs have different RCM economics than hospitals: procedure-based billing (CPT codes, not DRGs), higher commercial-to-Medicare ratio typically, prior authorization denials dominate (not clinical coding).

**How it works:** Defines an ASC metric registry with ASC-specific metrics (`prior_auth_denial_rate`, `case_cancellation_rate`, `implant_cost_variance`). The ASC bridge uses procedure-weighted rather than DRG-weighted economics. Benchmarks pulled from HCRIS filtering to facility type 8 (ASC).

**Data in:** ASC deal profile from the intake wizard.

**Data out:** ASC-specific metrics and bridge outputs fed into the standard packet builder.

---

## `behavioral_health/` — Behavioral Health Modules

**What it does:** Behavioral health-specific modules for residential, outpatient, and SUD (substance use disorder) platforms. BH RCM is distinct: authorization management is the primary lever (not coding/CDI), commercial carve-outs are common, and Medicaid is often the majority payer.

**How it works:** BH metric registry includes: `auth_approval_rate`, `avg_authorized_days`, `length_of_stay_variance`, `oor_network_denial_rate` (out-of-network denials). BH bridge weights the authorization lever heavily (primary driver) and discounts the CMI lever (DRG doesn't apply). BH-specific OBBBA/Medicaid work-requirement exposure is higher due to Medicaid-dominant payer mix.

**Data in:** BH deal profile; Medicaid-specific payer mix from intake.

**Data out:** BH-specific metrics and bridge for the standard packet builder.

---

## `mso/` — Management Services Organization Modules

**What it does:** MSO-specific modules for physician practice management platforms. MSO RCM economics differ: fee-splitting concerns, capitation contracts are more common, and the "collection rate" metric is the primary driver.

**How it works:** MSO metric registry adds: `collection_rate_net`, `capitation_pmpm`, `days_claims_outstanding`. MSO bridge weights the collection rate and net collection rate levers most heavily. MA/capitation exposure is modeled differently — capitation claims don't generate traditional denial data.

**Data in:** MSO deal profile; capitation contract terms from intake.

**Data out:** MSO-specific metrics and bridge for the standard packet builder.

---

## Key Concepts

- **Single dispatch point**: `registry.py` is the only place that knows which vertical gets which implementation. The packet builder calls `get_vertical_definition()` once and uses whatever it gets.
- **Hospital is the default**: If no vertical is specified, the platform uses the full hospital metric registry and bridge — backward compatible with all existing deals.
- **Vertical-specific benchmarks**: Each vertical filters the HCRIS benchmark pool to its own facility type, ensuring comparables are apples-to-apples.
