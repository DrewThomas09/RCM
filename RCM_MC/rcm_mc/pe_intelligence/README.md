# PE Intelligence Brain

**Package:** `rcm_mc.pe_intelligence`
**Scope:** 275 Python modules · 278 `docs/PE_HEURISTICS.md` sections
**Status:** merged to `main` — previously lived on `feature/pe-intelligence` branch

A senior-PE-healthcare-partner judgment layer that reads a
`DealAnalysisPacket` and answers the questions a partner actually
asks in IC — not a taxonomy of features but a library of partner
reflexes. Each module is self-contained, stdlib-only, dataclass-
based, JSON-round-trippable, and pairs a partner-voice `partner_note`
with numeric output so the brain speaks like an investor.

## What this branch does

The brain is structured around the seven reflexes a senior
healthcare-PE partner runs on any deal:

1. **Sniff test before math** — knows what's unrealistic on the
   teaser (400M rural CAH projecting 28% IRR, dental DSO at 4×
   revenue, MA-will-cover-FFS without a named contract).
2. **Archetype on sight** — recognizes healthcare thesis shapes
   (payer-mix shift, back-office consolidation, outpatient
   migration, CMI uplift, roll-up platform, cost-basis compression,
   capacity expansion) and applies the right lever stack + named
   risks per shape.
3. **Named-failure pattern match** — fingerprint-matches current
   signals against 20 dated historical failures (MA startup unwind
   2023, NSA platform rate shock 2022, PDGM transition 2020, etc.)
   and cites the specific lesson.
4. **Dot-connect packet signals** — traces packet-level signals
   through causal chains (denial fix → CMI reversal → Medicare
   bridge impact; payer-mix shift → case-mix → IP margin).
5. **Recurring vs one-time discipline** — religiously separates
   recurring EBITDA from one-time cash releases at the line-item
   level; exit multiple only applies to recurring.
6. **Specific regulatory $-impact** — OBBBA / site-neutral /
   sequestration / state Medicaid / PAMA translated into service-
   line dollar exposure, not hand-waved.
7. **Partner voice** — direct, numbers-first, willing to say pass
   when the math doesn't work.

## Entry points

Primary orchestrator:

```python
from rcm_mc.pe_intelligence import partner_review
review = partner_review(packet)
```

Most modules run stand-alone via their `<verb>_<thing>` function:

```python
from rcm_mc.pe_intelligence import (
    HealthcareArchetypeSignals,
    recognize_healthcare_thesis_archetypes,
)

archetype = recognize_healthcare_thesis_archetypes(
    HealthcareArchetypeSignals(
        commercial_mix_change_planned_pct=0.08,
        cdi_program_planned=True,
        bolt_on_pipeline_count=4,
    )
)
print(archetype.dominant_archetype)  # "payer_mix_shift"
print(archetype.partner_note)
```

Every module exposes:
- `<Input>` dataclass for packet signals
- `<verb>_<thing>()` function
- `<Report>` dataclass with partner-voice `partner_note`
- `render_<thing>_markdown()` for IC memos
- `to_dict()` on the report for JSON round-trip

## Module inventory (by partner-brain function)

### Pre-math sniff test + archetype recognition

- `unrealistic_on_face_check` — 14-pattern teaser-level sniff test
  (rural CAH + high IRR; SNF Medicare-heavy high multiple; dental
  revenue multiple; site-neutral dependent outpatient; roll-up
  without CIO; CPOM unverified; nonprofit flip margin; CAH margin
  claim; sub-scale home-health high-margin; MA without named
  contract). Output: stop_work / senior_partner_review /
  proceed_with_diligence.
- `healthcare_thesis_archetype_recognizer` — 7 healthcare thesis
  shapes with per-archetype lever stack + named risks + partner
  zoom + archetype-specific sniff test.
- `deal_archetype` — sponsor-structure archetypes (platform
  rollup, take-private, carve-out, turnaround, buy-and-build,
  continuation, GP-led secondary, PIPE, operating lift, growth
  equity).
- `archetype_subrunners` / `archetype_heuristic_router` — per-
  archetype heuristic branches.
- `archetype_outcome_distribution_predictor` — per-archetype
  empirical MOIC distribution (top decile / quartile / median /
  bottom quartile / decile) + median hold + failure rate.
- `archetype_canonical_bear_writer` — per-archetype canonical bear
  case with named breakage, EBITDA hit, recovery posture, early-
  warning indicator.

### Named-failure pattern matching

- `failure_archetype_library` / `named_failure_library_v2` — 20+
  shape-level named failure archetypes.
- `deal_to_historical_failure_matcher` — fingerprint-matches
  current signals against the catalog with specificity scoring.
- `bear_book` / `bear_case_generator` — specific bear-case
  construction from packet signals.
- `cross_pattern_digest` — unifies failure + bear + trap libraries
  into cross-module partner read.

### Three named healthcare-PE failure traps (all with dedicated modules)

- `denial_fix_pace_detector` — "we can fix denials in 12 months"
  trap: 8-category empirical pace bands (eligibility fast front-
  end; medical necessity slow back-end); defensible / stretch /
  trap verdict.
- `payer_renegotiation_timing_model` — "payer renegotiation is
  coming" trap: top-N commercial payer contract calendar (date ×
  posture × mix); quarter-by-quarter rate drift; trap flag when
  top-3 > 50% + neg renewal + exit drift < −1%.
- `medicare_advantage_bridge_trap` — "MA will make it up" trap:
  forced math on FFS loss vs net MA gain at realistic PMPM with
  cannibalization drag; 4 sub-traps (growth-too-aggressive / gross-
  not-net / cannibalization-ignored / MA-PMPM-below-FFS); verdict
  bridge_clears / tight / underwater.

### Dot-connect (crown-jewel cross-module reasoning)

- `connect_the_dots_packet_reader` — 6 causal chains at the
  packet-signal level:
  - denial fix → CMI reversal → Medicare bridge
  - payer mix shift → case mix → CMI → IP margin
  - wage step → physician comp → EBITDA → add-back risk
  - volume decline → fixed cost → covenant trip
  - DSO rise → working capital → FCF → recap timing
  - reg event → service line → EBITDA
- `cross_module_connective_tissue` — aggregates module outputs.
- `thesis_implications_chain` — thesis-pillar level.

### Recurring vs one-time EBITDA discipline

- `recurring_ebitda_line_scrubber` — line-item classification
  (20-pattern catalog: CARES / ERC / legal settlement / insurance
  / gain-on-sale / pandemic support as one-time; owner comp /
  synergy / restructuring / new-contract-annualized / pro-forma
  bolt-on as questionable; stock comp / lease normalization as
  recurring). Exit-multiple bleed = seller pitch vs partner view.
- `recurring_npr_line_scrubber` — top-line analog for NPR with
  15-pattern healthcare-specific catalog (DSH/UPL, provider
  relief, cost report settlement, RAC recovery, state directed
  payment, MU EHR, 340B true-up, behavioral state grant).
- `ebitda_quality_bridge_reconstructor` — stated → partner run-
  rate bridge.
- `ebitda_normalization` / `ebitda_quality` — category quality
  assessments.
- `qofe_prescreen` — 12-category add-back survival rates.

### Regulatory stress with specific dollar impacts

- `site_neutral_specific_impact_calculator` — OBBBA-era site-
  neutral $ exposure across 8 service-line bands (clinic_visit
  2022, drug_admin 2022, imaging_diagnostic 2025, imaging_advanced
  2026, procedures_intermediate 2027, gi_endoscopy 2027,
  cardiac_diagnostic 2028, orthopedic_procedure 2028) with
  cumulative EBITDA impact over hold.
- `cms_rule_cycle_tracker` — 4 major CMS rules (IPPS Apr/Aug/Oct;
  OPPS Jul/Nov/Jan; MPFS Jul/Nov/Jan; MA Feb/Apr/Jan) with per-rule
  service-line mapping and current-cycle-stage detection.
- `reimbursement_cliff_calendar_2026_2029` — 12 named CMS/payer
  events with subsector + $ impact.
- `regulatory_stress` — generic CMS/Medicaid/340B/site-neutral
  shocks.
- `regulatory_calendar` / `regulatory_watch` — event registries.
- `ma_star_rating_revenue_impact` — MA star rating → QBP bonus
  (0% or 5%) + rebate capture (50/65/70%); bear/bull half-star
  EBITDA deltas; cliff risk tiers.
- `state_scope_of_practice_exposure` — per-state NP/PA scope +
  CPOM strictness + non-compete enforceability + MSO/PC model
  requirement for 19 states.
- `state_ag_pe_scrutiny_tracker` — per-state AG transaction-
  notification laws (CA AB 3129, OR SB 951, IL HB 2222, NY PHL
  4550, MA HPC, MN HF 4246, WA, NV AB 518, NJ) with review window
  + recent-block precedent.
- `con_state_exposure_assessor` — CON state catalog for 29 states
  × 4 service lines; distinguishes incumbent→protection from
  entrant→barrier (same law, opposite effect).
- `medicaid_state_exposure_map` — Medicaid state tier map.
- `rac_audit_exposure_estimator` — Medicare FFS audit $ exposure.

### Healthcare-specific business models

- `site_of_service_revenue_mix` — 4-site breakdown (inpatient /
  HOPD / ASC / physician_office) with typical margin + reg exposure
  + IP→OP migration opportunity.
- `subsector_ebitda_margin_benchmark` — 15-subsector EBITDA margin
  bands with above/below/in-band verdict.
- `cost_line_decomposer_healthcare` — 7-line cost decomposition
  (labor / supply / prof fees / rent / malpractice / utilities /
  admin) vs peer bands for 4 subsectors with lever hints.
- `physician_specialty_economic_profiler` — 12 specialty economic
  shapes with revenue/margin/mix/procedure concentration + named
  risk patterns.
- `physician_retention_stress_model` — top-N physician loss stress
  (lose_top_1/2/3/5) with revenue portability × contributing
  margin × replacement ramp; retention-bond sizing by
  owner×outside-options profile.
- `physician_group_sub_specialty` — within-group sub-specialty
  friction scoring.
- `ma_integration_scoreboard` — M&A integration execution
  scoreboard.
- `vbc_risk_share_underwriter` — single-contract VBC: corridor
  with upside cap × upside share / downside floor × downside share;
  admin + stop-loss; expected / bear (+5pp MLR) / bull (-5pp MLR)
  scenarios; breakeven MLR.
- `vbc_portfolio_aggregator` — multi-contract VBC portfolio with
  correlated-bear and top-1/top-3 concentration; diversified /
  concentrated / single_bet.
- `patient_acquisition_cost_benchmark` — per-specialty CAC/LTV
  norms for 8 specialties; payback months; LTV/CAC <3× flag.
- `working_capital_seasonality_detector` — distinguishes Q1
  deductible-reset seasonality from structural YoY same-Q drift.
- `cash_conversion` / `cash_conversion_drift_detector` — FCF/EBITDA
  static + trend.
- `rcm_vendor_switching_cost_assessor` — 12-month DSO-spike + WC-
  drag trajectory for RCM platform conversion (best/realistic/bad
  case patterns); payback months.
- `ehr_transition_risk_assessor` — 5 EHR migration profiles
  (Cerner→Epic, MEDITECH→Epic, legacy→Athena, legacy→NextGen, Epic
  in-system upgrade) with capex band + productivity dip + revenue
  cliff + payback.
- `de_novo_site_ramp_economics` — month-by-month ramp curve
  (15%→30%→50%→70%→85%→100% of run-rate) with fixed + variable +
  startup capex; breakeven month + cumulative drag.
- `claims_denial_root_cause_classifier` — classifies observed
  signals into 8 denial root-cause categories with fix-difficulty
  band (easy / moderate / hard).

### Valuation / pricing / negotiation

- `valuation_checks` / `deal_comparables` / `comparative_analytics`
  / `sector_benchmarks` — multiple checks and comparables.
- `rollup_arbitrage_math` — roll-up MOIC decomposition (tuck-in
  arbitrage / platform multiple expansion / EBITDA growth /
  financial engineering) with multiple-bet flag.
- `reprice_calculator` — diligence-finding → reprice math
  (EBITDA × multiple + dollar items + safety haircut); verdict
  small / meaningful / material / kill.
- `banker_partner_pricing_tension` — banker pitch vs partner
  walk-away gap with bridge math and accept/bridgeable/thin/walk.
- `pricing_concession_ladder` — 9-move concession sequence.
- `pricing_power_diagnostic` — company-side pricing power.
- `banker_narrative_decoder` — pitch-language tactics.
- `cycle_timing_pricing_check` — market-cycle sanity check.

### LBO / debt / leverage / recap

- `debt_sizing` / `debt_capacity_sizer` — debt sizing at entry.
- `covenant_monitor` / `covenant_package_designer` — covenant
  headroom and package design.
- `lbo_debt_paydown_trajectory` — year-by-year FCF + mandatory
  amort + cash sweep; back-loaded-paydown flag.
- `lbo_stress_scenarios` — stress grid.
- `lbo_structure_analyzer` / `dividend_recap_analyzer` /
  `refinancing_window` — LBO structural modeling.
- `capital_structure_tradeoff` — equity-vs-debt trade-off.

### Management + team

- `management_assessment` — generic management read.
- `management_bench_depth_check` — bench breadth.
- `c_suite_team_grader` — per-seat grading (CEO/CFO/COO/CMO)
  on 4 criteria; composite A/B/C/D; per-seat accept /
  accept_with_coaching / coach_or_replace / replace_at_close.
- `management_forecast_reliability` — scores history.
- `management_forecast_haircut_applier` — per-tier per-year
  haircut to mgmt forecast; partner-implied MOIC/IRR delta.
- `management_rollover_equity_designer` — rollover design by CEO
  profile.
- `management_comp` / `management_first_sitdown` /
  `management_meeting_questions` — comp + meeting prep.
- `management_vs_packet_gap` — reconcile mgmt numbers against
  packet.
- `reference_check_framework` — structured reference-call plan.

### IC decision layer

- `ic_decision_synthesizer` — single recommendation + 3 flip
  signals.
- `ic_memo` / `ic_memo_header_synthesizer` — IC memo composition.
- `ic_dialog_simulator` — 3-round dialog with 5 voices (skeptic /
  optimist / md_numbers / operating_partner / lp_facing) +
  chair synthesis (consensus / unresolved / vote-blocking).
- `pre_ic_chair_brief` — 4-bullet chair note.
- `change_my_mind_diligence_plan` — operational follow-up to
  flip-signals: 12-pattern catalog matching flip hypotheses to
  data sources (mm/qofe/payer/site/legal/expert/data_room_pull).
- `partner_voice_variants` — 5 voice variants.
- `partner_briefing_composer` — one-page synthesis.

### Exit

- `exit_planning` — readiness checklist.
- `exit_alternative_comparator` — 5 exit-path comparison.
- `exit_buyer_view_mirror` — first-person buyer IC memo.
- `exit_buyer_short_list_builder` — per-subsector named buyer
  catalog (7 subsectors × 4 buyers with bucket + size filter).
- `exit_multiple_compression_scenarios` — multiple compression
  stress.
- `exit_story_generator` — narrative composition.
- `buyer_type_fit_analyzer` — 8 buyer-type profiles.
- `continuation_vehicle_readiness_scorer` — CV-specific 6-dim
  readiness (runway / rollover / GP reinvest / strip sale /
  LP AC precedent / named lead); pursue_cv / conditional /
  pursue_sale.
- `sponsor_vs_strategic_exit_comparator` — head-to-head path math
  with certainty + earn-out + escrow + time-value discount.
- `hold_period_optimizer` / `exit_timing_signal_tracker` — hold
  duration + exit signals.

### LP-facing / fund-level

- `lp_pitch` — raise-era narrative.
- `lp_quarterly_update_composer` — 5-paragraph LP letter with
  tone-by-mark calibration (measured_up / flat / owned_miss /
  thesis_stress); KPI beat/miss vs thesis; repeat-miss flag.
- `lp_waterfall_distribution_modeler` — standard European
  waterfall (ROC → 8% pref → 100% GP catch-up → 80/20 →
  mgmt fees); gross vs LP-net MOIC/IRR gap.
- `lp_side_letter_flags` — MFN / side-letter compliance.
- `fund_level_vintage_impact_scorer` — deal effect on fund TVPI /
  DPI / vintage peer rank / PME; 6-dimension composite with
  fund_accretive / fund_neutral / fund_dilutive verdict.
- `vintage_return_curve` / `fund_model` / `capital_plan` — fund
  math.

### Other healthcare-specific lenses

- `payer_mix_risk` / `payer_mix_forward_projection` — payer
  concentration + projection.
- `payer_watchlist_by_name` — 12-payer named book (United /
  Anthem / Aetna / Cigna / Humana / state BCBS / Centene / Molina
  / Kaiser / HCSC / Highmark / IBC) with posture + MA exposure +
  partner read.
- `reimbursement_bands` — per-payer rate bands.
- `contract_diligence` / `contract_renewal_cliff_calendar` —
  contract review + multi-type renewal calendar by quarter (8
  contract types with cliff detection).
- `clinical_outcome_leading_indicator_scanner` — 6 clinical-
  quality trend indicators.
- `quality_metrics` — Star/HAC/HRRP/VBP.
- `service_line_analysis` / `service_line_growth_margin_quadrant`
  — service-line concentration + 2x2 growth-margin classifier.

### Post-close / portfolio

- `hundred_day_plan` / `day_one_action_plan` — execution playbooks.
- `quarterly_operating_review` — 4-block QoR agenda.
- `post_close_90_day_reality_check` — 6-category delta-vs-
  underwrite first-board reality test.
- `post_close_surprises_log` — running surprise tracker.
- `value_creation_plan_generator` / `value_creation_tracker` —
  3-year VCP + tracking.
- `integration_velocity_tracker` — 100-day pace with critical-
  path slip escalation.
- `portfolio_dashboard` / `portfolio_rollup_viewer` /
  `cohort_tracker` — portfolio-level views.

### Deal-process / banker / bidder

- `banker_narrative_decoder` — 10 banker pitch tactics.
- `bidder_landscape_reader` — 10 bidder profiles with premium.
- `process_stopwatch` — banker-process timing reads.
- `competing_deals_ranker` — rank across pipeline.
- `reverse_diligence_checklist` — pre-sale seller-side items.

### ... plus 150+ additional modules spanning reasonableness
bands, heuristics, red flags, physician comp benchmarks, clinical
quality, operating partner fit, tax structuring, insurance tail
coverage, HSR antitrust, carve-out risks, secondary-sale
valuation, and many other partner reflexes.

Complete inventory lives in `__init__.py`.

## Architecture conventions

All modules follow the same pattern:

```python
@dataclass
class <Thing>Inputs:
    # packet-level fields with sensible defaults

@dataclass
class <Thing>Report:
    partner_note: str = ""
    def to_dict(self) -> Dict[str, Any]: ...

def <verb>_<thing>(inputs: <Thing>Inputs) -> <Thing>Report:
    ...

def render_<thing>_markdown(r: <Thing>Report) -> str:
    ...
```

**Standards:**
- Python 3.14 stdlib-only (no new runtime deps beyond pandas /
  numpy / matplotlib already in the project)
- Every report serializes via `to_dict()` (JSON round-trip tested)
- Every module ships a `render_*_markdown` renderer for IC memo
  output
- Every module has a test class in `tests/test_pe_intelligence.py`
- Every module has a corresponding section in
  `docs/PE_HEURISTICS.md` with partner statement + why it matters
  + worked example + packet fields + distinctness note
- Partner-voice `partner_note` on every report — short, direct,
  willing to say pass when math doesn't work
- Name-collision discipline: when adding a module whose natural
  class name overlaps an existing one, alias on import (e.g.
  `StateFootprint as ScopeStateFootprint`,
  `PayerContract as PayerRenegotiationContract`,
  `Physician as RetentionPhysician`)

## Testing

```bash
.venv/bin/python -m pytest tests/test_pe_intelligence.py -q
# 2970 passed in ~1s
```

Tests exercise partner-voice behavior, not mechanical assertions:
bad-deal fixtures trigger specific red flags; IC memo on passing
deals says invest; IC memo on failing deals says pass.

## Non-modification contract

This branch does not modify anything outside three paths:
- `rcm_mc/pe_intelligence/*.py` (new files only)
- `docs/PE_HEURISTICS.md` (append-only)
- `tests/test_pe_intelligence.py` (append-only)

`rcm_mc/analysis/packet_builder.py` and all existing Phase-3 code
are untouched. The brain consumes a packet; it never mutates one.

## Stats

- **275 modules** under `rcm_mc/pe_intelligence/`
- **~2,970 passing unit tests** in `tests/test_pe_intelligence.py`
  (count drifts — run `pytest --collect-only tests/test_pe_intelligence.py` for current figure)
- **278 doc sections** in `docs/PE_HEURISTICS.md`
- **Zero new runtime dependencies**
- **100% standalone** — each module runs independently from the
  others
