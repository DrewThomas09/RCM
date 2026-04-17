# PE Healthcare Heuristics — Living Reference

This document codifies the partner-voice rules of thumb that drive
the `rcm_mc.pe_intelligence` package. It is a living doc: every
adjustment to a band, threshold, or rule should be reflected here in
the same commit. These are the rules a senior healthcare-PE partner
applies reflexively when they look at a deal — the "sniff test"
before any formal modeling.

The rules fall into three classes, each in its own module:

- **Reasonableness bands** (`reasonableness.py`) — numeric sanity
  ranges for IRR, EBITDA margin, exit multiple, and lever delivery.
- **Heuristics** (`heuristics.py`) — triggerable rules of thumb that
  fire a titled, severity-stamped finding on a pattern.
- **Narrative** (`narrative.py`) — the partner-voice IC paragraph that
  synthesizes both into one prose recommendation.

---

## 1. Reasonableness bands

### 1.1 IRR bands by (size × payer mix)

IRR ranges are the partner-defensible bands for a 5-year hold under
reasonable leverage. Four verdicts: `IN_BAND`, `STRETCH` (defensible
with a specific story), `OUT_OF_BAND` (needs re-underwriting), and
`IMPLAUSIBLE` (do not show at IC).

Size buckets (by current EBITDA, $M):

- `small` < $10M
- `lower_mid` $10–25M
- `mid` $25–75M
- `upper_mid` $75–200M
- `large` > $200M

Payer regimes:

- `commercial_heavy` — Commercial ≥ 45%
- `balanced` — default prior
- `medicare_heavy` — Medicare ≥ 55%
- `medicaid_heavy` — Medicaid ≥ 30%
- `govt_heavy` — Medicare + Medicaid ≥ 70%

Commercial-heavy deals carry the highest IRR ceilings because of rate-
growth optionality and multiple expansion. Government-heavy deals
carry the tightest because reimbursement is capped.

Representative bands (see `reasonableness._IRR_BANDS` for the full
25-cell matrix):

| Size × Payer                | IN_BAND        | STRETCH | IMPLAUSIBLE |
|----------------------------|----------------|---------|-------------|
| lower_mid × commercial     | 18%–30%        | ≤38%    | > 50%       |
| mid × balanced             | 14%–22%        | ≤28%    | > 38%       |
| mid × medicare_heavy       | 9%–16%         | ≤21%    | > 28%       |
| upper_mid × govt_heavy     | 6%–12%         | ≤16%    | > 20%       |
| large × medicaid_heavy     | 6%–12%         | ≤15%    | > 20%       |

Source: HC-PE deal-outcome data 2019-2024; middle-market transaction
surveys; partner-calibrated envelope adjustments for 2023–2025 rate
environment.

### 1.2 EBITDA margin bands by hospital type

Healthcare subtypes have structurally different margin profiles — a
20% margin on an ASC is boring, a 20% margin on an acute-care hospital
is a flag. The bands:

| Type                 | IN_BAND     | STRETCH  | IMPLAUSIBLE |
|---------------------|-------------|----------|-------------|
| acute_care          | 4%–12%      | ≤15%     | > 25% or < –15% |
| asc                 | 18%–32%     | ≤40%     | > 55%       |
| behavioral          | 12%–22%     | ≤28%     | > 38%       |
| post_acute (SNF/LTACH/rehab) | 6%–14% | ≤18%  | > 25%       |
| specialty           | 10%–20%     | ≤28%     | > 40%       |
| outpatient / clinic | 10%–22%     | ≤30%     | > 42%       |
| critical_access     | 0%–6%       | ≤10%     | > 15%       |

Sources: AHA annual report, CMS cost reports, ASC industry surveys.

### 1.3 Exit multiple ceilings by payer mix

Medicare/Medicaid-heavy assets do not trade at commercial-heavy
multiples. Ceilings encode the discount:

| Regime              | IN_BAND     | STRETCH  | IMPLAUSIBLE |
|--------------------|-------------|----------|-------------|
| commercial_heavy   | 7.0x–11.0x  | ≤13.5x   | > 16.5x     |
| balanced           | 6.5x–10.0x  | ≤12.0x   | > 14.5x     |
| medicare_heavy     | 5.5x–8.5x   | ≤10.5x   | > 13.0x     |
| medicaid_heavy     | 5.0x–7.5x   | ≤9.5x    | > 12.0x     |
| govt_heavy         | 4.5x–7.0x   | ≤9.0x    | > 11.5x     |

### 1.4 Lever realizability by timeframe

How much can a given lever actually deliver in N months? Exceeding
`stretch_max` is aggressive; exceeding `implausible_max` is not
something we have observed.

| Lever               | Unit | 6mo reasonable/stretch/implausible | 12mo | 24mo |
|---------------------|------|--------------------------------------|------|------|
| denial_rate         | bps  | 100 / 175 / 300                      | 200 / 350 / 600 | 400 / 650 / 1000 |
| days_in_ar          | days | 5 / 9 / 15                           | 10 / 18 / 30 | 18 / 30 / 50 |
| clean_claim_rate    | bps  | 150 / 300 / 500                      | 400 / 700 / 1100 | 750 / 1200 / 1800 |
| final_writeoff_rate | bps  | —                                    | 150 / 275 / 450 | 300 / 500 / 800 |
| npsr_margin         | pct  | —                                    | 1.0 / 2.0 / 3.5 | 2.0 / 3.5 / 5.5 |
| organic_rev_growth  | pct  | —                                    | 6.0 / 10.0 / 18.0 | — |

Rationale: mature RCM programs deliver 150–200 bps/yr of denial
reduction. The first 200 bps come from obvious front-end eligibility
edits — everything beyond that requires system or workflow change.

---

## 2. Heuristics (rules of thumb)

Each heuristic has a stable `id`, a severity ceiling, and a
partner-voice phrasing. They compound — multiple `HIGH` or a single
`CRITICAL` will push the narrative recommendation to `PASS`.

### 2.1 `medicare_heavy_multiple_ceiling` — Medicare ≥ 60% and exit > 9.5x

Anchor: Medicare-heavy hospitals trade at a 2–3x multiple discount to
commercial-heavy peers. Even with RCM lift, no recent comp supports an
exit above ~9.5x on a Medicare-heavy acute-care asset.

**Partner voice:** "Show me one closed comp with a Medicare mix this
high that cleared this multiple. If you can't, reset exit to 8.5–9.0x
and tell me if the deal still clears the hurdle."

**Remediation:** Cap exit multiple at 9.0x in base case; keep 10.5x in
upside only.

### 2.2 `aggressive_denial_improvement` — > 200 bps/yr

Mature RCM programs deliver 150–200 bps/yr of initial-denial-rate
improvement. Above 200 bps is stretch. Above 600 bps/yr is not
something we've seen sustain in diligence-observable timeframes.

**Partner voice:** "The first 200 bps come from obvious edits. Beyond
that you need a platform change, and that takes 18–24 months, not 12."

**Remediation:** Haircut years 2+ by 40%; push the stretch into the
upside case only.

### 2.3 `capitation_vbc_uses_ffs_growth` — VBC with FFS revenue math

Capitated or value-based revenue doesn't grow via volume × rate. It
grows via lives × PMPM × (1 – MLR) + shared savings. If the deal is
tagged as capitation but the projection uses > 4% annual revenue
growth without a lives-growth story, the math is structurally wrong.

**Remediation:** Rebuild the revenue stack; don't underwrite
FFS-style growth on a VBC chassis.

### 2.4 `multiple_expansion_carrying_return` — Δmultiple > 15% of entry

If the modeled exit multiple exceeds entry by more than 15% of the
entry multiple, the return is at least partly betting on the market —
not on operating alpha.

**Partner voice:** "Multiple expansion is the first thing that
compresses in a bad cycle. Show me the return at a flat entry/exit
multiple."

### 2.5 `margin_expansion_too_fast` — > 200 bps/yr

100–200 bps/yr of EBITDA margin expansion is healthy. > 400 bps/yr is
usually a repricing of labor or a divestiture of a low-margin service
line, not an operating-improvement story.

### 2.6 `leverage_too_high_govt_mix` — Leverage > 5.5x with govt ≥ 60%

Government-heavy deals cannot carry sponsor-style leverage through a
bad reimbursement year. 5.5x is the practical ceiling at close; above
6.5x is critical.

### 2.7 `covenant_headroom_tight` — < 20% headroom

Tight maintenance covenants + one bad quarter = waiver conversation.
Target ≥ 25% headroom or negotiate equity-cure rights.

### 2.8 `insufficient_data_coverage` — < 60% populated from
`OBSERVED`/`EXTRACTED`

We do not pencil IC bids against imputed metrics. Escalate the data
request to the seller before finalizing the underwrite.

### 2.9 `case_mix_missing` — acute-care hospital without CMI

CMI drives DRG-level reimbursement and acuity-adjusted peer comps on
acute-care deals. Pull it from HCRIS Worksheet S-3 before running the
bridge.

### 2.10 `ar_days_above_peer` — Days in AR > 55

AR > 55 days is a symptom. > 70 days needs a named root cause (billing
vs. payer). The cure path differs materially between the two.

### 2.11 `denial_rate_elevated` — Initial denial > 10%

Above 10% is an opportunity; above 14% is a systemic intake/
eligibility problem. Only underwrite the fix if the top-10 denial
reason codes account for ≥ 60% of volume.

### 2.12 `small_deal_mega_irr` — EBITDA < $25M, IRR > 40%

Small-deal IRR distributions are extremely wide. A modeled > 40% IRR
is either genuine alpha or — more often — an understated entry
multiple. Size the equity check accordingly.

### 2.13 `hold_too_short_for_rcm` — Hold < 4yr with RCM-driven thesis

RCM programs take 18–24 months to mature. A sub-4-year hold leaves
the second-stage cash for the buyer. Either extend the hold or
discount the RCM lever NPV by 30–40%.

### 2.14 `writeoff_rate_high` — Final write-off > 6%

Top-quartile RCM shops run < 4%. Above 6% is a leak; above 9% needs
a reason-code-bucket diagnosis before any lever is underwritten.

### 2.15 `critical_access_reimbursement` — CAH classification

CAH facilities are reimbursed at 101% of allowable Medicare cost.
Cost takeout reduces revenue almost 1:1. Thesis must be mix, volume,
or scale — not cost.

### 2.16 `moic_cagr_too_high` — Implied CAGR > 28%

Top-quartile healthcare PE returns 25–30% CAGR on invested equity.
Above that, the model is underwriting luck. Stress a 15% shock on any
one leg (entry, exit, ramp) and require MOIC ≥ 2.0x.

### 2.17 `teaching_hospital_complexity` — Major teaching hospital

GME/IME payments are regulated and do not respond to operating
levers. Carve out of the bridge; forecast separately with CMS update
rules.

### 2.18 `ar_reduction_aggressive` — AR reduction > 8 days/yr

Focused AR programs deliver 5–8 days/yr. Above 15 days/yr implies a
billing-system replacement, not a tuning project. Pair the claim with
committed capex or haircut years 2+.

### 2.19 `state_medicaid_volatility` — Medicaid-heavy in volatile state

States with repeated rate freezes or pending changes (IL, NY, CA, LA,
OK, MS, AR). Flat-line Medicaid rate growth in base case.

---

## 3. Narrative synthesis

The narrative composer converts band checks + heuristic hits into five
pieces of prose:

1. **Headline** — one sentence. The partner's bottom line.
2. **Bull case** — what's working, 2–3 sentences.
3. **Bear case** — what breaks, 2–3 sentences.
4. **Key questions** — 3–5 items for the deal team.
5. **Recommendation** — one of: `PASS`, `PROCEED_WITH_CAVEATS`,
   `PROCEED`, `STRONG_PROCEED`.

### Recommendation logic

- **`PASS`** — Any `IMPLAUSIBLE` band check OR any `CRITICAL` heuristic.
- **`PROCEED_WITH_CAVEATS`** — `OUT_OF_BAND` bands, ≥2 `HIGH`
  heuristics, or `STRETCH` on any band.
- **`PROCEED`** — Otherwise, with ≤1 `MEDIUM` item.
- **`STRONG_PROCEED`** — All bands `IN_BAND`, no flags above `LOW`.

### Voice rules

- No hedging. Partner commentary picks a side.
- Every claim has a number attached.
- Plain English. Full sentences. No consultant-speak.
- The bear case must be specific: "what would break this deal" and
  not "there may be risks."

---

## 4. References

- [Reasonableness module](../rcm_mc/pe_intelligence/reasonableness.py)
- [Heuristics module](../rcm_mc/pe_intelligence/heuristics.py)
- [Narrative composer](../rcm_mc/pe_intelligence/narrative.py)
- [Partner review entry point](../rcm_mc/pe_intelligence/partner_review.py)
- [Deal Analysis Packet](./ANALYSIS_PACKET.md)

Calibration sources by band section:

- **IRR bands:** HC-PE outcome panel 2019–2024 (middle-market + large),
  segmented by payer-mix at close.
- **Margin bands:** AHA annual survey, CMS cost reports, ASC industry
  surveys, specialty-hospital PE deal memos.
- **Exit multiples:** HC-PE transaction comps 2020–2024, segmented by
  payer mix at signing.
- **Lever timeframes:** Partner-observed RCM program outcomes across
  the portfolio book 2018–2024.

---

## 5. Red-flag detectors

Red flags are the subset of rules a partner treats as categorical.
They live in `red_flags.py` so the base heuristics file stays clean;
they compose via `run_all_rules()` which `partner_review` calls.

Each red flag requires a field not present on the base
`HeuristicContext` dataclass — populate via `setattr` on a context or
via a profile/observed key on the packet. Field list is exported as
`RED_FLAG_FIELDS`.

### 5.1 `payer_concentration_risk` — single (non-govt) payer ≥ 40%

Commercial payer concentration is a contract-negotiation risk.
Exclude Medicare, Medicaid, and aggregate "commercial" buckets from
the calculation — only single named payers count.

**Partner voice:** "What's the current contract expiry, and have we
modeled a down-rate renewal? If the answer is 'no change', we're not
actually diligencing."

### 5.2 `contract_labor_dependency` — agency labor ≥ 15% of labor

Rates are volatile and 2022 taught everyone that a 10% agency-rate
reset is a real line item.

### 5.3 `service_line_concentration` — top DRG ≥ 30%

One CMS update can wipe out margin if the top service line is a
single point of concentration.

### 5.4 `340b_margin_dependency` — 340B ≥ 15% of EBITDA

The 340B program has been cut twice by CMS since 2018. Build an
ex-340B sensitivity; hold the bid to clearing at half the current
benefit.

### 5.5 `covid_relief_unwind` — COVID relief ≥ 5% of baseline EBITDA

PRF, ERC, and temporary rate add-ons do not recur. Strip from
baseline before applying entry multiple.

### 5.6 `known_rate_cliff_in_hold` — named reimbursement cliff in hold window

IMD waiver expirations, sequestration resets, 340B rule changes.
Don't exit into the cliff — shorten the hold or discount the exit.

### 5.7 `ehr_migration_planned` — EHR swap inside hold

Every EHR conversion the partner has seen produced 6–12 months of
claims lag, DNFB growth, DSO extension. Model a 9–12 month
revenue-drag period.

### 5.8 `prior_regulatory_action` — CIA, OIG, CMS penalty on record

Not a walk-away but posture-shaping. Document current compliance
program + corrective-action outcomes before LOI.

### 5.9 `quality_score_below_peer` — CMS Star Rating < 3

Triggers VBP penalty schedules on ~2% of Medicare revenue and
correlates with weaker operating maturity. Discount RCM-lever
realization 15–25%.

### 5.10 `debt_maturity_in_hold` — existing term debt matures before exit

Refinance rates inside the hold shape exit cash coverage. Term-out
at close or build a rate-shock sensitivity.

---

## 6. Worked examples

### 6.1 The Medicare-heavy acute hospital at 11.5x

**Inputs:**
- Mid-size acute-care hospital, $50M EBITDA, 220 beds
- Payer mix: 60% Medicare, 30% commercial, 10% Medicaid
- Projected IRR 22%, exit multiple 11.5x, leverage 5.8x at close
- Denial improvement plan: 350 bps/yr over 5yr hold

**What fires:**
- Reasonableness: IRR `STRETCH` (band: 9–16% IN_BAND, ≤21% STRETCH,
  >28% IMPLAUSIBLE for mid × medicare_heavy).
- `medicare_heavy_multiple_ceiling` HIGH — 11.5x above 9.5x ceiling
  for Medicare ≥ 60%.
- `aggressive_denial_improvement` MEDIUM — 350 bps/yr is stretch.

**Narrative recommendation:** `PROCEED_WITH_CAVEATS`.

**Key questions surfaced:**
1. Name a closed comp with a Medicare mix this high that cleared
   the modeled exit multiple.
2. What evidence supports >200 bps/yr of denial-rate improvement —
   capex, vendor, or staffing change?
3. What is the single operating advantage that produces the modeled
   IRR, and has it been validated by a comparable deal?

### 6.2 The clean mid-market commercial deal

**Inputs:**
- Mid-size acute-care hospital, $40M EBITDA
- Payer mix: 50% commercial, 35% Medicare, 15% Medicaid
- IRR 19%, exit 9.0x (entering at 8.5x), leverage 4.8x
- Denial improvement 150 bps/yr, AR reduction 6 days/yr, 5yr hold

**What fires:** Nothing above LOW. All bands IN_BAND.

**Recommendation:** `STRONG_PROCEED`.

### 6.3 The crisis scenario — don't bring to IC

**Inputs:**
- $30M EBITDA lower-middle acute-care
- 70% Medicare, 20% Medicaid (= 90% government)
- Projected IRR 35%, exit 14x, leverage 6.8x, headroom 8%
- Denial improvement 700 bps/yr (!)
- Data coverage 35%
- Contract labor 28% of labor spend

**What fires:**
- IRR `IMPLAUSIBLE` (government-heavy cap at 24% for lower_mid).
- Exit multiple `IMPLAUSIBLE` (govt-heavy ceiling 11.5x).
- `aggressive_denial_improvement` CRITICAL (> 600 bps/yr).
- `leverage_too_high_govt_mix` CRITICAL.
- `contract_labor_dependency` HIGH.
- `insufficient_data_coverage` HIGH.
- `covenant_headroom_tight` HIGH.

**Recommendation:** `PASS`.

**Narrative:** "Critical-risk flag on this acute-care hospital —
the deal does not clear as modeled."

---

## 7. Valuation sanity checks (`valuation_checks.py`)

Beyond the operating-metric bands, partners ask six valuation-level
questions on every deal. Each has a defensible range and a partner-
voice note.

| Check | IN_BAND | STRETCH | IMPLAUSIBLE |
|-------|---------|---------|-------------|
| WACC | 8%–12% | 7%–14% | <5% or >18% |
| EV walk residual | ≤1% | ≤3% | >10% |
| TV share of DCF | 55%–80% | 45%–88% | <30% or >95% |
| Terminal growth | 1.5%–3.0% | 0.5%–4.0% | <0% or >5.5% |
| Interest coverage | ≥3.0x | ≥2.0x | <1.5x |
| Equity concentration | ≤15% of fund | ≤25% | >35% |

These checks take a `ValuationInputs` bag. Missing inputs produce
`UNKNOWN` verdicts rather than raising.

---

## 8. Stress tests (`scenario_stress.py`)

Five mechanical shocks a partner asks about every deal:

1. **rate_down** — CMS down-rate 200 bps. Does leverage covenant hold?
2. **volume_down** — 7% volume decline, 40% flows to EBITDA.
3. **multiple_compression** — recompute MOIC at entry == exit multiple.
4. **lever_slip** — levers deliver 60% of plan.
5. **labor_shock** — agency labor rate +12%.

Each returns a `StressResult` with `shocked_ebitda`, `covenant_breach`,
`passes`, and a `partner_note`. A `worst_case_summary` aggregates the
results for the narrative layer.

---

## 9. IC memo formatter (`ic_memo.py`)

Renders a `PartnerReview` as an IC-ready memo in three formats:

- `render_markdown(review)` — Slack / Notion / email thread.
- `render_html(review)` — workbench `/partner-review` page, with
  dark-mode CSS variables.
- `render_text(review)` — CLI-friendly plaintext briefing.

Memo structure: recommendation → context → bull/bear → reasonableness
table → pattern flags → key questions → partner dictation block.

---

## 10. Sector benchmarks (`sector_benchmarks.py`)

Peer-median benchmarks by healthcare subsector (p25 / p50 / p75) for
dashboard positioning. Current coverage:

- `acute_care` — EBITDA margin, days_in_ar, initial_denial_rate,
  final_writeoff_rate, clean_claim_rate, case_mix_index, occupancy.
- `asc` — margin, AR, denial, cases per OR.
- `behavioral` — margin, AR, denial, LOS, census.
- `post_acute` — margin, AR, occupancy, Medicare mix.
- `specialty` — margin, AR, denial.
- `outpatient` — margin, AR, denial, RVUs.
- `critical_access` — margin, AR, Medicare mix.

`compare_to_peers(subsector, observations)` returns a list of
`GapFinding` objects with percentile placement (15/40/65/85 buckets)
and direction (above/below peer median) plus commentary.

---

## 11. Deal archetype classification (`deal_archetype.py`)

Ten PE healthcare deal patterns, each with its own playbook, risks,
and key questions:

| Archetype | Core signal |
|-----------|-------------|
| `platform_rollup` | Platform + ≥3 add-ons + rollup thesis |
| `take_private` | Public target + go-private intent |
| `carve_out` | Strategic seller + carve-out flag |
| `turnaround` | Distressed + sub-peer margin |
| `buy_and_build` | Platform + 1-2 targeted add-ons, organic ≥10% |
| `continuation` | Continuation-fund transaction |
| `gp_led_secondary` | Sponsor-to-sponsor, not continuation |
| `operating_lift` | RCM thesis + LBO leverage (4.0-6.5x) |
| `growth_equity` | Minority stake + rapid revenue growth |
| `pipe` | Public + minority |

Each hit includes `playbook` (what to do), `risks` (what goes wrong),
and `questions` (what the partner asks before signing).

---

## 12. Bear book (`bear_book.py`)

Pattern recognition against known failure modes. Each pattern encodes
a combination of signals that rhymes with deals that have gone wrong.

- `rollup_integration_failure` — sub-$50M platform + aggressive
  margin expansion + high leverage + short hold.
- `medicare_margin_compression` — Medicare ≥ 50% + margin expansion
  > 150 bps/yr.
- `carveout_tsa_sprawl` — low data coverage + high AR + missing CMI.
- `turnaround_without_operator` — sub-3% margin + aggressive plan.
- `covid_tailwind_fade` — acute-care + margin > 14% + exit > 10x.
- `high_leverage_thin_coverage` — leverage ≥ 6.0x + headroom < 15%.
- `vbc_priced_as_ffs` — capitation structure + volume growth math.
- `rural_single_payer_cliff` — CAH + ≥60% Medicare or ≥35% Medicaid.

Each hit exposes a `failure_mode` (what goes wrong) and a
`partner_voice` warning.

---

## 13. Exit readiness (`exit_readiness.py`)

12-dimension pre-exit checklist yielding a 0–100 readiness score:

- **≥ 85** → engage banker immediately.
- **65 – 84** → soft-launch ready; fix gaps before formal process.
- **< 65** → not exit-ready; address core gaps first.

Dimensions include: audited financials, TTM KPIs, data-room
organization, QoE preparation, EBITDA trend, margin trend, buyer
universe mapping, management retention, legal cleanliness, adjustment
reconciliation, EBITDA-vs-plan, revenue-vs-plan.

---

## 14. Payer math (`payer_math.py`)

Deterministic payer-mix-aware projection helpers:

- `blended_rate_growth(mix, rate_by_payer)` — weighted growth rate.
- `project_revenue(inputs)` — year-by-year revenue + EBITDA walk.
- `compare_payer_scenarios(base, scenarios)` — side-by-side.
- `vbc_revenue_projection(inputs)` — capitation math: premium, claims,
  admin, underwriting margin, shared savings.
- `standard_scenarios()` — base, CMS cut, commercial rate boom,
  frozen rates.

Used by the narrative layer to answer "what happens if CMS cuts?"
without a full MC run.

---

## 15. Regulatory watch (`regulatory_watch.py`)

Curated registry of ~15 CMS / OIG / state regulatory items affecting
healthcare-PE underwriting. Each item:

- `scope` — national or state code (e.g. CA, NY, TX).
- `status` — proposed, finalized, effective, expired, watch.
- `affected_subsectors` — acute_care, asc, behavioral, post_acute, etc.
- `affected_payers` — medicare, medicaid, commercial.
- `impact_summary` + `partner_relevance`.

Example entries: CMS OPPS site-neutral expansion, 340B payback
schedule, Medicaid PHE redetermination, No Surprises Act IDR,
MPFS conversion factor, SNF VBP, IMD waiver expirations, California
seismic capex, NY Medicaid rate-freeze history, Florida non-expansion,
Maryland all-payer rate-setting.

`regulatory_items_for_deal(subsector, state, payer_mix)` returns only
items relevant to a given deal profile.

---

## 16. LP pitch (`lp_pitch.py`)

Renders a PartnerReview as an LP-facing one-pager with softened tone:
"Do not show this at IC" → "We will re-check this." Output in
Markdown and HTML.

Sections: opportunity snapshot (table), why this deal, risks and
mitigations, diligence priorities, strengths vs peer. Disclaimer
footer included.

---

## 17. Change log

- **2026-04-17** — Initial codification. 25-cell IRR matrix, 7-type
  margin bands, 5-regime exit-multiple ceilings, 7-lever × 3-timeframe
  realizability table, 19 heuristics covering VALUATION, OPERATIONS,
  STRUCTURE, PAYER, and DATA categories.
- **2026-04-17** — Added 10 red-flag detectors in `red_flags.py`:
  single-payer concentration, contract labor, service-line
  concentration, 340B dependency, COVID unwind, rate-cliff,
  EHR migration, prior regulatory action, quality rating,
  debt maturity. Added three worked IC examples (Medicare-heavy
  11.5x, clean commercial mid-market, crisis scenario).
- **2026-04-17** — Added `valuation_checks.py` (WACC, EV walk, TV
  share, terminal growth, interest coverage, equity concentration),
  `scenario_stress.py` (5 mechanical partner stresses),
  `ic_memo.py` (markdown/html/text IC-memo renderers),
  `sector_benchmarks.py` (peer p25/p50/p75 by subsector), and
  `deal_archetype.py` (10 deal-pattern classifier with playbooks).
- **2026-04-17** — Added `bear_book.py` (8 historical-failure pattern
  detectors), `exit_readiness.py` (12-dimension pre-exit checklist
  with 0-100 score), and `payer_math.py` (blended rate growth, revenue
  projection, VBC lives × PMPM math, standard payer scenarios).
- **2026-04-17** — Added `regulatory_watch.py` (15 national/state
  regulatory items with deal-level filtering) and `lp_pitch.py`
  (LP-facing one-pager in Markdown + HTML with softened language).
