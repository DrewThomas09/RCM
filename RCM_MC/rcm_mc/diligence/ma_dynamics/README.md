# ma_dynamics/

**Medicare Advantage V28 + payer-mix dynamics engine** (Prompt L, Gap 11). MA covers >55% of Medicare beneficiaries; V28 (fully effective 2026-01-01) projects 3.12% average risk-score reduction. **Cano Health bankruptcy was directly tied to pre-V28 coding-intensity exposure** — this module is the "Cano-again detector."

## Files

| File | Purpose |
|------|---------|
| `__init__.py` | Package docstring with V28 causal framing + Cano parallel. |
| `v28_recalibration.py` | **The deepest analytic moat.** Given a member roster with diagnosis codes + attributed revenue, compute per-member and aggregate revenue impact of V24→V28 transition. |
| `coding_intensity_analyzer.py` | **Aetna/CVS-pattern FCA detector.** Flags patterns that draw DOJ False Claims attention — add-only retrospective chart review (codes added to prior years without corresponding removals), etc. |
| `commercial_concentration.py` | Payer HHI + top-payer 5% rate-cut scenario. |
| `downcoding_prior_auth_red_flag.py` | Rule-based payer-behavior signals predicting revenue compression. Not forecast models — partner pressure-test triggers. |
| `medicaid_unwind_tracker.py` | Post-PHE Medicaid redetermination tracker. KFF-sourced: ~70% national procedural termination rate; OCHIN Q4 2023 showed -7% Medicaid volume. Estimates target-level volume-at-risk. |
| `risk_contract_modeler.py` | ACO REACH / MSSP / full-risk MA projector. `attributed_benes × (actual PMPM − benchmark PMPM) × shared-savings rate`. Minimal — uses caller inputs, no CMS file ingest. |

## The V28 parallel to Cano

Cano Health's 2023 bankruptcy traced to revenue dependence on aggressive MA coding-intensity. When V28 (final rule November 2023, effective 2026) was telegraphed, Cano's thesis disintegrated. `v28_recalibration.py` is the tool that would have flagged this before LOI — member roster × dx codes → per-member revenue impact under V24 vs V28 → aggregate delta.

Runs on any MA-exposed deal. Result feeds `regulatory_calendar`'s thesis-driver-kill mapping.

## Where it plugs in

- **Thesis Pipeline** — runs when target has MA exposure (detected from payer mix)
- **Regulatory Calendar** — `v28_recalibration` output feeds the EBITDA overlay
- **Bear Case** — material V28 impact becomes `[R1]` regulatory evidence

## Data sources

- V28 HCC coefficients: CMS Final Rule tables
- Medicaid unwind rates: KFF state-by-state tracker + OCHIN Q4 2023 encounters report
- Shared-savings rates: caller-supplied; module is model, not data-ingestor

## Tests

`tests/test_ma_dynamics.py` — V28 delta math + coding intensity pattern detection + Medicaid unwind projection.
