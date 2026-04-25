# Regulatory Roadmap (next 18 months)

Healthcare PE diligence depends on accurate reads of the policy
environment. Four major regulatory shifts in flight will affect every
deal underwriting between now and mid-2027:

  1. **CY2026 OPPS Final Rule** — site-neutral expansion + Hospital
     MRF schema additions (effective Jan 1, 2026)
  2. **CMS LEAD model** — Innovation Center value-based-care model
     (rolling implementation)
  3. **ILPA 2.0 Reporting Template** — fund-reporting standard
     (effective Q1 2026)
  4. **State CPOM enforcement waves** — Corporate Practice of
     Medicine restrictions (rolling, MA → NY → CA → OR → TX)

For each: what's changing, what the platform already handles, what's
missing, how we incorporate it. Where existing modules already cover
part of the surface, the plan is incremental — extend, don't rebuild.

---

## #1 — CY2026 OPPS Final Rule (effective Jan 1, 2026)

### What's changing

CMS published the CY2026 OPPS Final Rule with three changes the
platform needs to track:

- **Site-neutral payment expansion** — More clinic-visit HCPCS codes
  paid at the lower physician-office rate when delivered in a
  hospital outpatient department (HOPD). Expands the ~$8B/yr revenue
  shift from hospitals to ASCs already underway.
- **Hospital MRF schema v3.0** — Adds percentile allowed amounts
  (p25/p50/p75/p95) per CPT × payer. Replaces the v2.0 single
  negotiated rate that was lossy.
- **Type-2 billing NPI on MRFs** — disambiguates which legal entity
  bills for which service line within a hospital system.

### What we already handle

  - **`rcm_mc/site_neutral/`** package — CY2026 4-category
    site-neutral codes already loaded; revenue-at-risk + ASC
    opportunity models built.
  - **`rcm_mc/pricing/hospital_mrf.py`** — percentile fields
    (`percentile_25`, `percentile_50`, `percentile_75`) already on
    `HospitalChargeRecord`; CY2026 fixture + parser tests already
    pass.
  - **`billing_npi_type_2`** field already on the MRF schema.

The CY2026 rule changes are pre-baked. The remaining work is
operational rather than schema.

### Implementation work

| Task | Status | Effort |
|---|---|---|
| Final-rule code list refresh | Need to compare published list to current `site_neutral.codes` | 1 wk |
| Percentile data ingest at scale | Schema ready; need to crawl hospital MRFs published Q1 2026 | 4 wks |
| ASC migration valuation update | Existing `asc_opportunity.py` needs CY2026 multiplier refresh | 1 wk |
| UI: `/site-neutral/<deal_id>` page surfacing the impact | New surface | 2 wks |

### Implementation sequence

1. **Week 1**: Cross-check `site_neutral.codes` against the
   published Final Rule code list; add the ~30 newly affected
   HCPCS codes.
2. **Weeks 2-5**: Hospital MRF crawl + ingest pipeline targeting
   Q1 2026 publications. Schema already supports the v3.0 fields;
   the lift is the ETL job to keep up with payers' release cadence.
3. **Weeks 6-7**: Refresh the ASC opportunity model with CY2026
   payment ratios and rebuild backtest.
4. **Week 8**: New `/site-neutral/<deal_id>` page using the
   recently-shipped UI kit — `power_table` for the per-CPT impact
   list, `power_chart` for the migration trend, `compare` for
   HOPD vs ASC pricing.

---

## #2 — CMS LEAD Model (Innovation Center, rolling implementation)

### What's changing

CMS Innovation Center's LEAD (Linking Equity, Access, and Disease
management) model is a recent value-based-care payment program
expanding APM coverage. Key implications for PE:

- Practices must report new equity + access metrics. Roll-up
  platforms acquiring multi-state physician groups need to ensure
  every site can hit the reporting bar.
- New attribution rules — a patient is attributed to the practice
  the platform CFO might not have expected; this affects population
  health revenue projections.
- Quality bonus opportunities for practices that hit the equity
  benchmarks; missed bonuses for those that don't.

### What we already handle

  - **`rcm_mc/vbc_contracts/`** — VBC contract valuation under
    multiple ACO / DCE / commercial track types. Bayesian updating
    on performance.
  - **`rcm_mc/vbc/hierarchical.py`** — cohort-level PMPM with
    Bayesian shrinkage. Handles attribution drift.
  - **`rcm_mc/cms_quality_metrics`** — quality + readmission +
    HCAHPS already ingested per CCN.

### What's missing for LEAD

| Missing piece | What it provides | Where it goes |
|---|---|---|
| LEAD-track financial model | Per-practice revenue under LEAD attribution + quality bonus | `rcm_mc/vbc_contracts/lead.py` |
| Equity + access metric ingestion | Practice-level reporting that LEAD requires | `rcm_mc/data/cms_lead_metrics.py` (when CMS publishes) |
| LEAD attribution simulator | Patient-attribution counterfactuals under different roll-up scenarios | `rcm_mc/vbc/lead_attribution.py` |
| LEAD scorecard UI | Per-deal LEAD-readiness panel | `rcm_mc/ui/lead_readiness_page.py` |

### Implementation sequence

1. **Weeks 1-3**: LEAD-track contract valuation in
   `vbc_contracts/lead.py`. Inputs: practice revenue, attribution
   density, equity metric baseline. Outputs: expected LEAD revenue +
   quality bonus probability.
2. **Weeks 4-5**: Patient-attribution simulator. Predicts
   attribution under three roll-up structures (loose affiliation,
   tight MSO, friendly-PC pass-through).
3. **Weeks 6-7**: Once CMS publishes the LEAD metric spec, build
   `data/cms_lead_metrics.py` (similar pattern to existing
   `cms_quality_metrics.py`).
4. **Week 8**: `/deal/<id>/lead` UI panel using `power_chart` for
   metric trends, `compare` for current-vs-required-baseline,
   `metric_glossary` for the new equity metrics.

### Risk + mitigation

- **CMS may revise LEAD before launch**. Build the contract model
  generic enough to handle parameter changes; specs in YAML rather
  than hardcoded. Existing `vbc_contracts/posterior.py` Bayesian
  updating absorbs spec drift naturally.
- **Equity metric data not yet public**. Schema-only build for v1;
  switch on the live data feed when CMS publishes. Tests use
  fixture data so model validates without real metric availability.

---

## #3 — ILPA 2.0 Reporting Template (effective Q1 2026)

### What's changing

The Institutional Limited Partners Association published the 2.0
Reporting Template in 2024, effective Q1 2026. Funds must report:

- **Standardized cash-flow categories** (no more per-fund variant
  schedules)
- **IRR + MOIC + DPI + RVPI** on the standardized 6-pillar
  attribution: revenue growth / margin expansion / multiple expansion /
  leverage / FX / dividends
- **ESG metrics** rollup at the fund level via the EDCI framework
- **Co-invest disclosure** in standard form
- **DEI representation metrics** at the deal-team level

LPs will refuse to subscribe to fund quarterlies that don't conform
to ILPA 2.0.

### What we already handle

  - **`rcm_mc/irr_attribution/`** — Bain-style 6-pillar IRR
    decomposition + fund-level rollup with vintage analytics.
  - **`rcm_mc/irr_attribution/fund.py`** — `aggregate_fund_attribution`
    + `format_fund_ilpa` helper already aligns to ILPA 2.0 categories.
  - **`rcm_mc/esg/issb.py`** — IFRS S1/S2 + EDCI framework
    LP-package renderer.
  - **`rcm_mc/exit_readiness/`** — Exit cash-flow forecasting that
    feeds the attribution.

The IRR attribution + ESG layers already exist. ILPA 2.0 is mostly
a **format alignment** + a few additions.

### What's missing for ILPA 2.0

| Missing piece | Where it goes |
|---|---|
| Co-invest disclosure formatter | Extend `irr_attribution/fund.py::format_fund_ilpa` |
| DEI deal-team metrics aggregator | New `rcm_mc/lp_reporting/dei_metrics.py` |
| Standardized cash-flow category mapping | Update `format_fund_ilpa` to emit the canonical 9 categories |
| LP-package end-to-end test | Validate produced template against the published ILPA 2.0 spec |

### Implementation sequence

1. **Week 1**: Update `format_fund_ilpa` to emit the 9 ILPA 2.0
   cash-flow categories; spec encoded as constants per CLAUDE.md.
2. **Week 2**: Co-invest disclosure formatter — consumes existing
   per-deal LP-allocation data, outputs the standardized table.
3. **Week 3**: DEI metrics aggregator — the deal-team data lives
   in the new `deal_team_members` table from the multi-user plan,
   so this depends on that infra. If multi-user is not yet built,
   accept manual CSV input as a fallback.
4. **Week 4**: End-to-end test against ILPA-published reference
   templates. Compare bytes-for-bytes structure (not values) to
   ensure full conformance.

### Coordination with the multi-user plan

The DEI rollup needs deal-team membership data. If the multi-user
collaboration buildout (separate plan) is sequenced first, the DEI
piece is trivial. If not, ILPA 2.0 build needs a stub interface
that consumes CSV deal-team data; the stub later swaps for the
live `deal_team_members` query.

---

## #4 — State CPOM Enforcement Waves (rolling)

### What's changing

Corporate Practice of Medicine (CPOM) doctrine bars non-physician
entities from owning medical practices in many states. Healthcare PE
relies on the **MSO + Friendly-PC** structure to navigate this — a
non-physician investor owns the MSO; a physician owns the PC; the PC
contracts with the MSO for management services. This works as long
as the state regulator interprets the structure as compliant.

The next 18 months will see meaningful CPOM enforcement waves:

- **Massachusetts (2024 — already in flight)**: MA AG announced
  enhanced CPOM scrutiny; recent settlements suggest tighter
  reading.
- **New York (pending legislation 2025)**: Bills under consideration
  to codify stricter Friendly-PC requirements.
- **California (rolling)**: Existing CPOM doctrine; recent MFAR
  enforcement on dental/orthodontic chains.
- **Oregon (2025)**: New legislation effective late 2025 requiring
  physician-majority board.
- **Texas (2025-2026)**: Legislative session may add CPOM
  restrictions; outcome uncertain.

For PE platforms with multi-state physician group + MSO/PC roll-ups,
each state's interpretation can substantially affect deal viability.

### What we already handle

  - **`rcm_mc/data/state_regulatory.py`** — State-level regulatory
    + payer context attached to packets.
  - **`rcm_mc/regulatory/discovery.py`** — LDA-based topic detection
    over Federal Register + state legislation.
  - **`rcm_mc/regulatory/`** package generally surfaces regulatory
    risk per asset.

### What's missing for CPOM

| Missing piece | Where it goes |
|---|---|
| State-by-state CPOM stance tracker | New `rcm_mc/data/cpom_state_tracker.py` |
| Friendly-PC structure analyzer | New `rcm_mc/diligence/cpom_structure.py` |
| Multi-state CPOM exposure map | New `rcm_mc/ml/cpom_exposure.py` |
| CPOM risk scorecard UI | Integrated into existing `regulatory_calendar_page` |

### Implementation sequence

1. **Weeks 1-2**: `cpom_state_tracker.py` — per-state record of CPOM
   stance (strict / moderate / permissive) + recent enforcement
   actions + pending legislation. Initially curated manually
   (state law text); later automated via the existing regulatory
   discovery LDA pipeline.
2. **Weeks 3-4**: `cpom_structure.py` — given a deal's MSO/PC
   structure (states-of-operation, equity holders, governance
   board), score CPOM risk per state.
3. **Weeks 5-6**: `cpom_exposure.py` — multi-state roll-up
   exposure: 'this 12-state platform has X% of revenue in
   strict-CPOM states; 18-month enforcement risk = Y%'.
4. **Week 7**: UI — extend `regulatory_calendar_page` to include
   a per-deal CPOM exposure panel with state map (existing
   `geographic_clustering` heatmap pattern works) + per-state
   risk dot.

### Risk + mitigation

- **CPOM law is interpreted by state AGs** — written statutes don't
  always reflect enforcement reality. The tracker needs both the
  formal statute summary AND a 'recent enforcement events' field
  that captures the practical interpretation.
- **Pending legislation outcomes are uncertain**. The state tracker
  should flag pending bills with a 'probability of passage' field
  (manually maintained from PE-AGs feedback, eventually via the
  regulatory discovery LDA).
- **Highly state-specific guidance** — generic CPOM scoring isn't
  useful. The multi-state exposure model weights each state by
  the deal's revenue concentration there.

---

## Cross-cutting infrastructure

These four regulatory shifts share three needs that justify
investing in cross-cutting infrastructure:

### Regulatory calendar (already partly exists)

`rcm_mc/regulatory/regulatory_calendar` extends to:
- Track effective dates for all regulatory changes affecting deals
- Surface upcoming regulations in dashboard_v3 'Key alerts' section
- Per-deal exposure panels showing which regulations affect this
  particular asset

### Versioned ML model retraining

When a regulation changes the data distribution (e.g., site-neutral
expansion changes the relevant ASC opportunity multiplier), the
platform's ML predictors need to retrain on post-change data
without losing the pre-change baseline.

`rcm_mc/ml/model_versioning.py` (new):
- Each predictor stamped with `cv_window_start` + `cv_window_end`
- Retraining produces a new version; old versions remain available
  for backtests
- UI surfaces 'this prediction is based on data from period X-Y'

### Regulatory delta-impact panel

For every deal, surface the EBITDA + IRR sensitivity to each
in-flight regulation. Reuses existing `improvement_potential` 3-
scenario sweep machinery — same mechanic, different scenarios:

  - 'Site-neutral expansion: -$5M EBITDA hit, $20M ASC migration
    upside'
  - 'CPOM enforcement in 3 states: +18 months close timeline'
  - 'LEAD model attribution shift: +$3M ARR'

UI: new section on `/deal/<id>/profile` between Risks and Actions.

---

## Sequencing across the four

If we ran the regulatory work as a single workstream:

| Quarter | Work | Coverage |
|---|---|---|
| Q1 2025 | OPPS code list refresh + ILPA 2.0 format work | Operational lift; modest |
| Q2 2025 | OPPS MRF crawl pipeline + LEAD scaffolding | Data infrastructure |
| Q3 2025 | LEAD contract valuation + CPOM tracker | Models in flight |
| Q4 2025 | LEAD live data ingestion + CPOM scoring + UI panels | Customer-facing |
| Q1 2026 | ILPA 2.0 production cutover (effective date) + post-OPPS validation | Hardening |

If we parallelize across two engineers:

| Quarter | Engineer A | Engineer B |
|---|---|---|
| Q1 2025 | OPPS rule alignment | ILPA 2.0 format |
| Q2 2025 | OPPS MRF crawl | LEAD scaffolding |
| Q3 2025 | CPOM tracker + scoring | LEAD valuation + attribution |
| Q4 2025 | UI integration + cross-cutting infra | LEAD live data |

5 quarters serial / 4 quarters parallelized.

---

## Strategic implications

Healthcare PE deal underwriting depends increasingly on accurate
regulatory reads — every roll-up CIM mentions CPOM compliance, every
hospital deal models site-neutral risk, every fund quarterly will
need ILPA 2.0 conformance starting Q1 2026.

The platform's value proposition expands from 'we run the diligence
math' to 'we run the diligence math AND keep up with the regulatory
environment so the partner doesn't need to subscribe to 5 separate
healthcare-policy newsletters'. That's a meaningful pricing-power
lift for the Pro and Enterprise tiers in the business model.

The four regulatory tracks above plus the existing `regulatory/`
package position the platform to credibly own this surface — most
generic PE-tooling competitors (PitchBook, CapIQ, DealCloud) don't
go this deep on healthcare-specific regulation.

---

## What we don't try to predict

We deliberately don't:

- **Forecast which legislation will pass**. Tracker records pending
  bills with manual probability annotations; we don't model the
  political process.
- **Provide legal opinions**. Every regulatory module has a clear
  'this is research-grade information, not legal advice' surface
  in its UI panel.
- **Track every state minor regulation**. We focus on the changes
  that materially affect deal economics (≥$1M EBITDA impact for a
  representative deal). Smaller regulatory tweaks remain in the
  regulatory discovery LDA's monthly digest, not in dedicated
  modules.

That's the line between *information* and *advice* — the platform
sits firmly on the information side.
