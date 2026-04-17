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

## 17. 100-Day post-close plan (`hundred_day_plan.py`)

Generates a dated, owned 100-day action plan from a PartnerReview.
Four workstreams:

- **Operational** — KPI cascade, RCM triage (AR aging, denial reason-
  code concentration, write-off buckets), integration playbook.
- **Financial** — monthly close, covenant-tracking dashboard, lender
  engagement, rate-update monitoring.
- **People** — top-20 retention plan, incentive redesign, contract-
  labor reduction.
- **Systems** — data-coverage close-out, CMI/acuity reporting, TSA
  tracker, EHR cutover plan.

Actions are triggered by heuristic hits in the review: if
`ar_days_above_peer` fired, the plan adds an AR-aging diagnosis with
a 45-day due date. If `covenant_headroom_tight` fired, a 15-day
lender-engagement action is added. Payer-mix drives CMS monitoring.

Output: `generate_plan(review) -> HundredDayPlan` and
`render_plan_markdown(plan) -> str` for partner-ready markdown.

---

## 18. IC voting (`ic_voting.py`)

Weighted IC vote aggregator. Voters carry role-based weights
(`managing_partner=2.0`, `partner=1.5`, `principal=1.0`, `vp=0.5`).
Veto holders can reject a deal regardless of tally. Votes can be:

- `yes` — straight approval.
- `no` — with required rationale.
- `yes_with_caveats` — approve subject to listed conditions.
- `abstain` — non-counting but recorded.

Outcomes: `APPROVED`, `APPROVED_WITH_CONDITIONS`, `REJECTED`, `TABLED`.

`auto_vote_from_review(recommendation, voters)` produces a synthetic
vote that mirrors the review's recommendation — useful for
sensitivity analysis.

---

## 19. Diligence tracker (`diligence_tracker.py`)

Lightweight board for diligence workstream status. Tracks:

- Per-item status (`not_started`, `in_progress`, `blocked`,
  `complete`, `dropped`).
- Priority (`P0`, `P1`, `P2`).
- Owner, due date, blocker reason, finding, critical flag.

`board_from_review(review)` auto-seeds a board from a
PartnerReview's heuristic hits — hits map to appropriate
workstreams (operational, financial, commercial, legal, it,
regulatory, etc.) with severity → priority mapping.

`is_ic_ready()` returns True only when every P0 item is complete and
no critical blockers remain.

---

## 20. Comparative analytics (`comparative_analytics.py`)

Portfolio-level cross-deal comparison helpers:

- `portfolio_concentration(deals)` — EBITDA-weighted sector, state,
  and payer shares plus top-share highlights.
- `concentration_warnings(conc)` — partner-voice warnings when
  sector > 40%, state > 35%, or single payer > 50%.
- `deal_vs_book(candidate, book)` — per-metric direction (better /
  worse / same / n/a) for a candidate against book medians.
- `deal_rank_vs_peers(candidate, peers)` — blended-score ranking
  (50% IRR, 25% margin, 25% reciprocal leverage).
- `correlation_risk(candidate, book)` — flag deals likely to co-move
  (same sector + state, Medicare-heavy + Medicare-heavy).

---

## 21. Module inventory

As of 2026-04-17, the `rcm_mc.pe_intelligence` package contains 91
modules + test suite:

| Module | Role |
|--------|------|
| `reasonableness.py` | IRR / margin / multiple / lever bands (25-cell IRR matrix, 7 hospital-type margin bands, 5 payer-regime multiple ceilings, 7-lever × 3-timeframe realizability) |
| `heuristics.py` | 19 partner-voice rules of thumb |
| `red_flags.py` | 10 deal-killer detectors |
| `bear_book.py` | 8 historical-failure pattern detectors |
| `valuation_checks.py` | WACC / EV walk / TV share / growth / coverage / concentration |
| `scenario_stress.py` | 5 mechanical partner stresses |
| `sector_benchmarks.py` | Peer p25/p50/p75 by healthcare subsector |
| `regulatory_watch.py` | 15 national/state regulatory items |
| `deal_archetype.py` | 10-archetype classifier with playbooks |
| `narrative.py` | Senior-partner-voice IC commentary composer |
| `partner_review.py` | Main entry — packet → PartnerReview |
| `ic_memo.py` | Markdown / HTML / plaintext IC-memo renderers |
| `lp_pitch.py` | LP-facing one-pager with softened tone |
| `hundred_day_plan.py` | Post-close 4-workstream action plan |
| `ic_voting.py` | Role-weighted IC vote aggregator with veto + dissent |
| `diligence_tracker.py` | Workstream board with IC-ready check |
| `comparative_analytics.py` | Portfolio concentration + deal-vs-book |
| `exit_readiness.py` | 12-dimension pre-exit readiness score |
| `payer_math.py` | Payer-mix-aware revenue/EBITDA projection + VBC math |
| `value_creation_tracker.py` | Monthly lever-vs-plan tracker |
| `exit_math.py` | Waterfall + preferred + catch-up + reverse MOIC |
| `workbench_integration.py` | UI bundle + compact API payload |
| `deal_comparables.py` | Illustrative comp set + multiple stats |
| `debt_sizing.py` | Prudent leverage by (subsector × payer) + covenant stress |
| `management_assessment.py` | 6-dimension team scoring |
| `thesis_validator.py` | 8 internal-consistency rules |
| `synergy_modeler.py` | Cost + revenue + RCM + procurement synergies |
| `working_capital.py` | AR/AP/DIO days-to-cash release math |
| `fund_model.py` | Fund-level DPI/TVPI/NAV + vintage percentile |
| `regulatory_stress.py` | $ EBITDA impact of CMS/Medicaid/340B shocks |
| `cash_conversion.py` | FCF/EBITDA by subsector with peer bands |
| `lp_side_letter_flags.py` | LP conformance (sector / state / concentration / ESG) |
| `pipeline_tracker.py` | Sourcing funnel + stale-deal detection |
| `operational_kpi_cascade.py` | Rank KPI levers by $ EBITDA impact |
| `commercial_due_diligence.py` | TAM / share / growth / competitive position |
| `icr_gate.py` | IC-Ready gate consolidator |
| `cohort_tracker.py` | Vintage-cohort benchmarking |
| `partner_discussion.py` | Autogen partner Q&A |
| `kpi_alert_rules.py` | Monthly ops KPI threshold alerts |
| `recon.py` | Cross-artifact coherence check |
| `capital_plan.py` | Capex by year/purpose + intensity validation |
| `auditor_view.py` | Full decision audit trail for regulators/LPs |
| `thesis_templates.py` | 6 prebuilt narrative scaffolds for common theses |
| `regime_classifier.py` | 5-regime classifier (durable / emerging / steady / stagnant / declining) |
| `market_structure.py` | HHI / CR3 / CR5 + consolidation-play score |
| `stress_test.py` | Downside/upside scenario grid with robustness grade |
| `operating_posture.py` | 5-posture classifier (scenario_leader / resilient_core / etc.) |
| `white_space.py` | Geographic / segment / channel adjacency detection |
| `investability_scorer.py` | Composite opportunity×value×stability 0..100 |
| `extra_heuristics.py` | 8 additional partner-voice rules |
| `extra_bands.py` | Capex / occupancy / RVU / CMI / LOS subsector bands |
| `narrative_styles.py` | 5 alternate narrative voices |
| `memo_formats.py` | 5 IC memo renderers (one-pager / slack / email / pdf / deck) |
| `extra_archetypes.py` | 8 specialized deal patterns |
| `extra_red_flags.py` | 10 more deal-killer detectors |
| `scenario_narrative.py` | Stress-grid → partner-voice prose |
| `deal_comparison.py` | Side-by-side two-review comparison |
| `priority_scoring.py` | Multi-deal partner-queue ranker |
| `board_memo.py` | Governance memo w/ approval matrix + disclosures |
| `contract_diligence.py` | Payer-contract portfolio risk scoring |
| `service_line_analysis.py` | DRG/specialty mix + margin contribution |
| `quality_metrics.py` | CMS Star / HRRP / HCAHPS → Medicare $ impact |
| `labor_cost_analytics.py` | Contract labor / overtime / productivity |
| `analyst_cheatsheet.py` | 1-page associate IC pre-read |
| `reimbursement_bands.py` | Payer rate growth / gross-to-net / site-neutral parity |
| `ebitda_quality.py` | Add-back classifier → partner-EBITDA |
| `covenant_monitor.py` | Live covenant tracking + break-EBITDA |
| `liquidity_monitor.py` | 13-week cash projection + runway |
| `ma_pipeline.py` | Add-on acquisition funnel + capacity |
| `esg_screen.py` | ESG exclusions + composite + reporting gaps |
| `deepdive_heuristics.py` | 10 mature-diligence partner rules |
| `master_bundle.py` | One-call build of every PE-intel artifact |
| `tax_structuring.py` | Step-up / 163(j) / QSBS / state drag checks |
| `insurance_diligence.py` | PL / cyber / SIR / claims adequacy |
| `portfolio_dashboard.py` | Desk-view across multiple reviews |
| `integration_readiness.py` | Post-close integration scorecard |
| `management_comp.py` | MIP/LTIP/vesting/rollover checks |
| `red_team_review.py` | Adversarial attack + pass rationale |
| `data_room_tracker.py` | 34-item canonical checklist scorer |
| `workstream_tracker.py` | Post-close integration milestone aggregator |
| `negotiation_position.py` | Anchor / walkaway / leverage / concessions |
| `loi_drafter.py` | LOI term-sheet generator |
| `post_mortem.py` | Exit-deal lessons-learned template |
| `cycle_timing.py` | Market-cycle phase classifier |
| `exit_planning.py` | Year-by-year exit preparation roadmap |
| `benchmark_bands.py` | SG&A / interest / SSSG / NWC / outpatient bands |
| `payer_mix_risk.py` | Payer HHI + MA / MMC / ACA / mix-shift flags |
| `peer_discovery.py` | Similarity-weighted peer ranking |
| `reimbursement_cliff.py` | Named rate-cliff modeling in hold window |
| `scenario_comparison.py` | Base/bull/bear MOIC side-by-side |
| `vintage_return_curve.py` | J-curve DPI/TVPI projection by vintage |

Every module has corresponding tests in
`tests/test_pe_intelligence.py`.

---

## 22. Value creation tracker (`value_creation_tracker.py`)

Monthly lever-vs-plan tracker for portfolio ops:

- `LeverPlan` — baseline + year1..year5 targets + `lower_is_better`
  flag.
- `LeverActual` — observed value at a given date.
- `evaluate_lever(plan, actual, year_in_hold)` — returns ``LeverStatus``
  with verdicts `ahead`, `on_track`, `behind`, `off_track`, `unknown`.
- `rollup_status(statuses)` — portfolio-level headline and counts.

Used by the operating-partner monthly review to flag levers that
need intervention before the quarter closes.

---

## 23. Exit math (`exit_math.py`)

Classic US PE waterfall + sensitivities:

- `project_exit_ev(exit_ebitda, exit_multiple, exit_net_debt, fees)`
  — gross EV, fees, equity value.
- `exit_waterfall(total_proceeds, lp_equity_in, gp_equity_in,
  hold_years, ...)` — full 4-stage waterfall: return-of-capital, 8%
  preferred, 100% GP catch-up to 20% of profit, 80/20 LP/GP split.
- `moic_cagr_to_irr(moic, years)` — quick CAGR approximation.
- `required_exit_ebitda_for_moic(target_moic, equity_in, exit_multiple,
  exit_net_debt)` — reverse-math: what EBITDA hits a target MOIC?

Useful for partner sensitivities pre-IC: "what does EBITDA need to
reach for us to hit 2.5x."

---

## 24. Workbench integration (`workbench_integration.py`)

Server-friendly bundle helpers:

- `build_workbench_bundle(packet)` — single-call produces the full
  artifact set: review, IC memo (markdown + html + text), LP pitch
  (markdown + html), 100-day plan, diligence board, bear patterns,
  regulatory items.
- `build_api_payload(packet)` — compact JSON payload without HTML,
  for network-efficient API responses.
- `archetype_summary(review)` — archetype ranking for a deal.

Intended entry points for UI routes like `/partner-review/<deal_id>`
and `/api/partner-review/<deal_id>`.

---

## 25. Deal comparables (`deal_comparables.py`)

Illustrative healthcare-PE comp registry (16 starter entries across
acute care, ASC, behavioral, post-acute, specialty, outpatient, and
critical access). Not a live feed — refresh quarterly with real
closed-deal comps.

- `filter_comps(sector, payer_regime, size_bucket, min_year, max_year)`
  — subset the registry.
- `multiple_stats(comps)` — min / median / mean / max of EV/EBITDA.
- `position_in_comps(modeled_multiple, comps)` — percentile placement
  of a modeled multiple against the comp set, with partner commentary.

Used to defend an exit multiple at IC: "our exit sits at the 55th
percentile of the acute-care commercial-heavy 2022-2024 comp set."

---

## 26. Debt sizing (`debt_sizing.py`)

Partner-prudent leverage table by (subsector × payer_regime):

- Acute care with commercial-heavy tolerates up to 5.5x at close;
  acute-care govt-heavy capped at 3.5x.
- ASC stretches to 6.0x on commercial-heavy platforms.
- Critical access capped at 2.5-4.0x across regimes.

Helpers: `leverage_headroom`, `max_interest_rate_to_break`,
`covenant_stress_passes` (leverage + coverage joint test).

---

## 27. Management assessment (`management_assessment.py`)

6-dimension team scoring: CEO, CFO, operational depth, RCM leadership,
clinical, alignment. Returns a composite 0–100 score plus per-dimension
findings and seat-add recommendations. Status verdicts:
`strong` / `adequate` / `concerns` / `replace`.

---

## 28. Thesis validator (`thesis_validator.py`)

8 internal-consistency rules flagging contradictions in a thesis:

- RCM thesis with sub-4yr hold.
- VBC structure priced with FFS growth.
- Aggressive IRR with flat entry/exit multiples.
- Margin expansion faster than revenue growth.
- High leverage with government-heavy mix.
- Turnaround + roll-up simultaneously.
- MOIC and IRR targets that don't reconcile.
- Large denial-improvement lift without RCM thesis tag.

---

## 29. Synergy modeler (`synergy_modeler.py`)

Roll-up/tuck-in synergy math: cost (SG&A consolidation), revenue
(cross-sell at margin), RCM (bps margin lift at scale), procurement
(COGS savings). Applies a partner haircut (default 35%) and 5-year
realization ramp.

---

## 30. Working capital (`working_capital.py`)

One-time cash release from lever programs:

- `ar_days_to_cash` — DSO reduction × revenue / 365.
- `ap_days_to_cash` — DPO extension × cogs / 365.
- `inventory_days_to_cash` — DIO reduction × inventory cost / 365.

Partner notes distinguish sustainable tuning from one-time
billing-system cleanup. Never applied to exit multiple.

---

## 31. Fund model (`fund_model.py`)

Fund-level rollup: given a list of `FundDeal` commitments + holds +
projected MOICs, projects year-by-year called capital, distributions,
NAV, DPI, TVPI, RVPI. `fund_vintage_percentile` places a fund against
healthcare-PE vintage quartile cutoffs.

---

## 32. Regulatory stress (`regulatory_stress.py`)

Models the $ EBITDA impact of specific regulatory shocks:

- **CMS IPPS / OPPS rate cut** — N-bps reduction on Medicare revenue.
- **Medicaid rate freeze** — foregone inflation over N years.
- **340B program reduction** — X% haircut on current 340B EBITDA.
- **Site-neutral expansion** — HOPD rate compression X%.
- **SNF VBP acceleration** — additional Medicare withhold (post-acute only).

`run_regulatory_stresses(inputs)` returns all relevant shocks sorted
by $ impact; `summarize_regulatory_exposure(shocks, base_ebitda)`
produces a partner-facing headline.

Paired with `regulatory_watch.py`: the watch-list identifies which
items are *pending*, the stress module quantifies *how much they
hurt*.

---

## 33. Cash conversion (`cash_conversion.py`)

Measures how much EBITDA actually shows up as free cash flow.
`expected_conversion_by_subsector` returns target bands:
ASC 70-85%, acute care 50-68%, behavioral 60-75%, post-acute 55-70%,
specialty 60-75%, outpatient 65-82%, critical access 40-60%.
`assess_conversion` returns status ("above" / "in_band" / "below")
with partner commentary — low conversion with high leverage is the
pattern that kills deals.

---

## 34. LP side-letter conformance (`lp_side_letter_flags.py`)

Checks a candidate deal against an LP `SideLetterSet`:

- Sector exclusions (e.g., "no ASCs").
- Geographic exclusions.
- Single-deal concentration cap.
- Government-payer mix cap.
- ESG screens (no tobacco, no short-term detention).

Returns `ConformanceFinding` items flagged as "breach" / "warning" /
"info". `has_breach(findings)` for quick gate check.

---

## 35. Pipeline tracker (`pipeline_tracker.py`)

Sourcing-funnel analyzer: counts deals at each stage
(sourced → screened → ioi → meeting → loi → exclusive → closed),
computes stage-to-stage yields with target benchmarks, and flags
stages where the funnel is leaking. `stale_deals(today, threshold)`
surfaces pipeline items with no activity in 60+ days.

`source_mix(deals)` returns channel breakdown (banker / direct /
sponsor) — useful for partnership-review conversations.

---

## 36. Operational KPI cascade (`operational_kpi_cascade.py`)

Ranks operating KPIs by $ EBITDA impact given current/target values:

- `initial_denial_rate` — × revenue × flow factor (default 50%).
- `final_writeoff_rate` — × revenue (100% flow-through).
- `days_in_ar` — × revenue / 365 (flagged as one-time cash).
- `clean_claim_rate` — × revenue × flow factor (default 30%).
- `labor_pct_of_revenue` — × revenue (100% flow-through).

`build_cascade(inputs)` returns movements sorted by $ impact desc.
`total_ebitda_impact(cascade)` excludes the AR one-time cash from
the recurring EBITDA total — prevents double-counting.

---

## 37. Commercial due diligence (`commercial_due_diligence.py`)

Partner-prudent sanity checks on market claims:

- `market_size_sanity` — TAM vs US-subsector ceilings (acute $1.4T,
  ASC $45B, behavioral $180B, etc.).
- `market_share_check` — implied share from revenue/TAM.
- `growth_plausibility` — flags claims above subsector norms.
- `competitive_position` — maps differentiation × intensity to one
  of nine position categories.

---

## 38. IC-Ready gate (`icr_gate.py`)

Single entry point: given a PartnerReview (and optionally a
diligence board, LP side-letter findings, management score), returns
`ICReadinessResult` with a boolean + ordered blocker list. Gates:

1. No CRITICAL heuristic hits.
2. No IMPLAUSIBLE band verdicts.
3. Data coverage ≥ 60%.
4. All P0 diligence items complete.
5. No LP side-letter breach.
6. Management score ≥ 50.

---

## 39. Cohort tracker (`cohort_tracker.py`)

Vintage-cohort benchmarking:

- `cohort_stats(deals, vintage)` — p25/p50/p75 for IRR/MOIC/margin.
- `rank_within_cohort` — blended-score ranking.
- `top_decile` / `bottom_decile` — cohort outliers.
- `compare_to_cohort` — candidate's delta vs cohort medians.

---

## 40. Partner discussion (`partner_discussion.py`)

Autogen Q&A from a PartnerReview. Heuristic hits and band verdicts
map to partner-voice questions and answers — the kind of back-and-
forth an associate rehearses before IC.

`build_discussion(review)` returns `DiscussionItem` list;
`render_discussion_markdown(items)` produces IC-rehearsal Markdown.

---

## 41. KPI alert rules (`kpi_alert_rules.py`)

Threshold-based alerts for monthly ops reviews. Default rules cover
denial rate, write-off rate, AR days, clean claim rate, margin,
labor ratio, and census occupancy. Each rule has:

- `direction` — higher_is_better / lower_is_better.
- `guardrail_low` / `guardrail_high` — breach = medium alert.
- `hard_floor` / `hard_ceiling` — breach = high alert.

`evaluate_kpi_alerts(observations)` returns alerts sorted highest
severity first with partner notes + escalation paths.

---

## 42. Recon (`recon.py`)

Reconciliation checks across PE-intel artifacts. Ensures the
PartnerReview, 100-day plan, and diligence board tell the same
story:

- Recommendation phrase appears in IC-memo dictation.
- Every HIGH/CRITICAL heuristic hit has a plan action.
- Every CRITICAL hit appears as a P0 item on the diligence board.

`has_mismatch(findings)` is the quick gate check for cross-artifact
drift.

---

## 43. Capital plan (`capital_plan.py`)

Structures post-close capex + maintenance/growth split, validates
against subsector intensity bands (acute-care capex typically 5-7%
of revenue, ASC 5-7%, CAH 4-6%). Flags:

- Total intensity > subsector ceiling.
- Year-1 concentration > 12% of revenue.
- Maintenance < 30% of total (growth-heavy plans that defer
  asset-reinvestment risk).

---

## 44. Auditor view (`auditor_view.py`)

Produces a full structured decision-audit-trail for a PartnerReview.
Every context input, every band verdict, every heuristic hit, and
every narrative choice gets an `AuditEntry` with trigger values and
rationale.

Regulators and LPs asking "why did this deal pass?" get a
JSON-serializable answer six months later.

---

## 45. Thesis templates (`thesis_templates.py`)

Six prebuilt narrative scaffolds for common healthcare-PE theses:

1. **Platform + tuck-ins** — consolidation in a fragmented subsector.
2. **Operational improvement** — RCM / labor / mix levers.
3. **Scale + margin** — volume-driven fixed-cost leverage.
4. **Turnaround** — distressed asset with named operator.
5. **Strategic exit** — positioning for strategic acquisition.
6. **Value-based care** — lives growth + shared-savings.

Each template provides opening paragraph, bull/bear case framing,
lever priority stack, and 5 partner questions. Templates are
field-substituted (`{subsector}`, `{entry_multiple}`, `{hold_years}`,
etc.) and rendered as IC-ready Markdown.

---

## 46. Regime classifier (`regime_classifier.py`)

Places a deal into one of five performance regimes based on growth /
volatility / consistency signals:

- `durable_growth` — consistent positive growth + stable margins.
- `emerging_volatile` — fast growth with wide dispersion.
- `steady` — modest growth, low volatility.
- `stagnant` — flat growth, stable margins.
- `declining_risk` — negative growth and/or deteriorating margins.

Each regime ships a partner note, playbook, and key-risk statement.
`rank_all_regimes` returns every regime scored, sorted by confidence
desc, when the primary classification is borderline.

---

## 47. Market structure (`market_structure.py`)

Industrial-organization metrics applied to deal markets:

- **HHI** on 0..10000 scale with DOJ/FTC thresholds (1500 / 2500).
- **CR3 / CR5** top-N concentration ratios.
- **Fragmentation verdict** — fragmented / consolidating / consolidated.
- **Consolidation-play score** — 0..1 blend of HHI, CR5, player count,
  and dominance penalty. `is_consolidation_play(result, min_score)`
  is the boolean gate for "is this a roll-up setup".

Partners use it to hint the right thesis archetype
(`platform_rollup` vs `buy_and_build` vs `challenger_or_niche`).

---

## 48. Stress test (`stress_test.py`)

Runs a scenario grid on top of `scenario_stress.py`:

- 10 downside scenarios (rate cuts at 100/200/300 bps, volume declines
  5/10%, multiple compression flat, lever slip 40/60%, labor shocks 10/20%).
- 2+ upside scenarios (full lever realization, +1 turn multiple expansion).

Outputs `downside_pass_rate`, `upside_capture_rate`, worst/best case
delta, covenant-breach count, and a letter grade A..F with a partner
summary.

---

## 49. Operating posture (`operating_posture.py`)

Labels a deal with one of five postures based on stress + regime +
concentration flags:

- `scenario_leader` — robust downside + strong upside.
- `resilient_core` — robust downside, capped upside.
- `balanced` — neither especially robust nor asymmetric.
- `growth_optional` — weak downside, strong upside (high beta).
- `concentration_risk` — payer/state/service-line concentration
  dominates both tails.

Each posture carries a playbook. `posture_from_stress_and_heuristics`
pulls the inputs directly from an existing stress-grid dict + hit
list.

---

## 50. White space (`white_space.py`)

Detects unserved-opportunity adjacencies across three dimensions:

- **Geographic** — candidate states vs existing footprint; scores
  adjacent states (same census region) higher than distant ones.
- **Segment** — service-line extensions by subsector registry
  (e.g. acute_care → outpatient imaging, ambulatory surgery).
- **Channel** — payer/contracting channels by subsector registry
  (e.g. post_acute → medicare_advantage, I-SNPs).

Each opportunity gets a 0..1 attractiveness score and barriers list.
`top_opportunities(result, n)` returns the best-scoring ones.

---

## 51. Investability scorer (`investability_scorer.py`)

Composite 0..100 blending three axes:

- **Opportunity** (30%) — market-structure score + white-space.
- **Value** (40%) — IRR / MOIC vs peer bands + raw return levels.
- **Stability** (30%) — stress grade + regime + posture + critical-
  hit penalty.

Maps to A..F letter grade with a partner note listing top strengths
and weaknesses. `inputs_from_review(review)` builds the input bag
from an existing PartnerReview so the composite uses the same data
as every other analytic.

---

## 52. Extra heuristics (`extra_heuristics.py`)

Eight additional partner-voice rules beyond the base 19:

- `clean_claim_rate_low` — clean-claim below 88%.
- `growth_volatility_without_driver` — > 10% growth with no named driver.
- `payer_contract_staleness` — low clean-claim + low denial plan.
- `check_size_concentration` — deal EBITDA > $300M implies top-check.
- `missing_ttm_kpi_reporting` — coverage < 50%.
- `cah_teaching_mismatch` — CAH + teaching flags together.
- `urban_outpatient_gold_rush` — urban commercial MSO at >12x exit.
- `hold_moic_inconsistency` — implied CAGR > 40% sustained-return.

`run_all_plus_extras` unions base + red flags + extras, dedup by id.

---

## 53. Extra bands (`extra_bands.py`)

Finer-grained subsector bands beyond the core reasonableness matrix:

- Capital intensity (% of revenue, by subsector).
- Bed occupancy (acute / post-acute / behavioral).
- RVU per provider (outpatient / specialty).
- Case Mix Index (acute care).
- Length of stay (behavioral / post-acute).

`run_extra_bands` runs every check that has enough input.

---

## 54. Narrative styles (`narrative_styles.py`)

Five alternate narrative voices beyond the default senior-partner:

- `analyst_brief` — neutral, data-first.
- `skeptic` — adversarial pre-mortem.
- `founder_voice` — target-founder perspective.
- `bullish` — optimistic frame.
- `three_sentence` — compressed summary.

`compose_styled_narrative(style, ...)` dispatches by name.

---

## 55. Memo formats (`memo_formats.py`)

Five renderers for the IC memo beyond the default markdown/html/text:

- `render_one_pager` — constrained single-page markdown.
- `render_memo_slack` — slack-formatted (stars for bold, emoji).
- `render_memo_email` — subject + plain-text body.
- `render_pdf_ready` — markdown with `\pagebreak` for pandoc.
- `render_deck_bullets` — ≤ 10 short bullets for slide copy-paste.

`render_all_memo_formats(review)` returns every format.

---

## 56. Extra archetypes (`extra_archetypes.py`)

Eight specialized deal patterns beyond the core 10:

- `de_novo_build` — pre-revenue platform build.
- `joint_venture` — sponsor + strategic (or sponsor + sponsor) JV.
- `distressed_restructuring` — DIP / chapter-11 emergence.
- `carveout_platform` — carve-out that becomes a rollup platform.
- `succession_transition` — family-founder exit.
- `public_to_private_tender` — tender-offer mechanics.
- `spinco_carveout` — RMT / spin-co structures.
- `late_stage_growth` — minority pre-IPO investment.

---

## 57. Extra red flags (`extra_red_flags.py`)

Ten additional deal-killer detectors beyond the core 10 in
`red_flags.py`:

- `physician_turnover_high` — retention < 85%.
- `clinical_staff_shortage` — RN vacancy > 15%.
- `payer_denial_spike` — QoQ denial rate delta > 200 bps.
- `bad_debt_spike` — bad-debt growth > revenue × 2.
- `it_system_eol` — EHR end-of-life inside hold.
- `lease_expiration_cluster` — > 30% of leased sites expire in hold.
- `regulatory_inspection_open` — unresolved CMS / state inspection.
- `self_insurance_tail` — under-funded self-insurance reserves.
- `capex_deferral_pattern` — capex/D&A < 0.80.
- `key_payer_churn` — top-3 commercial payer departure risk.

Field list exported as `EXTRA_RED_FLAG_FIELDS` for caller wiring.

---

## 58. Scenario narrative (`scenario_narrative.py`)

Turns a `StressGridResult` into partner-voice prose:

- **Headline** — grade-specific one-liner.
- **Worst-case sentence** — names the single most damaging
  downside scenario with $ / pct impact.
- **Passing-downside summary** — the shocks the deal absorbs.
- **Compound-shock warning** — pairs of marginal-pass scenarios that
  together would break the deal.

`render_scenario_markdown(grid_dict)` produces a ready-to-paste
markdown block.

---

## 59. Deal comparison (`deal_comparison.py`)

Side-by-side comparison of two :class:`PartnerReview` objects:

- Per-metric deltas on IRR, MOIC, margin, leverage, AR days, denial
  rate, write-offs, stress grade, downside pass rate, covenant
  breaches, investability, critical / high-hit counts, and
  recommendation.
- Winner tally with a 2-vote buffer before declaring an overall
  winner.
- Partner-ready markdown table via `render_comparison_markdown`.

---

## 60. Priority scoring (`priority_scoring.py`)

Ranks a portfolio of :class:`PartnerReview` objects by composite:

- **Urgency** (30%) — days to next gate.
- **Leverage of attention** (40%) — count of open stretch / high
  items where partner input still matters.
- **Investability** (20%) — composite score from
  `investability_scorer`.
- **Strategic** (10%) — flagship / strategic flags from caller.

`rank_deal_portfolio([(review, inputs), ...])` returns a ranked list
with `.rank` populated.

---

## 61. Board memo (`board_memo.py`)

Governance-focused memo renderer:

- **Fiduciary reminder** — board duties in one paragraph.
- **Approval matrix** — item-by-item approve vs informed schedule.
- **Required disclosures** — surfaced from heuristic hits (capital
  structure, payer concentration, regulatory history, key-
  dependency).
- **Action list** — concrete asks of the board.

Translates IC recommendation to board language (PROCEED → APPROVE,
PASS → DECLINE).

---

## 62. Contract diligence (`contract_diligence.py`)

Scores a payer-contract portfolio by contract-level risk:

- Expiry inside hold + revenue share.
- Termination mechanic (at-will / anti-assignment / standard).
- Rate-reset mechanic (CPI-only penalized).
- Government + volatile-state combination.

Aggregates to portfolio-level metrics: top-3 concentration, maturity
wall (revenue expiring in hold), high-risk contract count. Produces
a ranked action list (renegotiate / monitor / note).

---

## 63. Service-line analysis (`service_line_analysis.py`)

Per-service-line concentration, margin contribution, and reimburse-
ment-exposure scoring. Classifies the portfolio as:

- `well_diversified` — HHI < 1500, no line > 25%.
- `balanced` — HHI < 2500.
- `anchor_dependent` — top line ≥ 40% of revenue.
- `specialty_concentration` — top EBITDA contributor ≥ 60% even
  when revenue share is moderate.

---

## 64. Quality metrics (`quality_metrics.py`)

Translates CMS Star Rating, readmission percentile, HCAHPS, HAC
penalty status, and mortality percentile into a composite 0..1
score + estimated Medicare-revenue payment impact:

- VBP bonuses/cuts from Stars (~1-2%).
- HRRP penalties (up to 3%).
- HCAHPS contribution to VBP (~0.5%).
- HAC program (1% cut for bottom quartile).

Verdict: leader / average / drag.

---

## 65. Labor-cost analytics (`labor_cost_analytics.py`)

Scores staffing profile across five dimensions:

- Contract / agency labor share.
- Overtime share.
- Nurse-patient ratio.
- Wage growth vs local CPI.
- Productivity vs peer.

Estimates $ shock impact of 10% wage reset and $ savings from 5%
productivity lever. Verdict: strong / moderate / drag.

---

## 66. Analyst cheatsheet (`analyst_cheatsheet.py`)

Condensed IC pre-read for the associate. Renders a `PartnerReview`
into a 1-page reference: top 5 facts, top 5 flags with partner-voice
quotes, top 3 questions, and quick-number summary (IRR / MOIC /
leverage / investability / stress grade). Different from the
`ic_memo` renderer — this is the associate's desk reference during
IC discussion, not the partner's document.

---

## 67. Reimbursement bands (`reimbursement_bands.py`)

Payer-level rate-assumption bands:

- **Rate growth** — Medicare 1.5-2.5%, Medicaid 0-2.5%, Commercial
  3-5.5%. Above each band's ceiling requires a named story.
- **Gross-to-net** — per-payer collection-ratio ranges (Medicare
  28-42%, Medicaid 22-38%, Commercial 40-65%).
- **HOPD / ASC parity** — site-neutral policy exposure via rate
  ratio between HOPD and ASC / office equivalents.

`run_reimbursement_bands(payer_rate_growths, gross_to_net_ratios,
hopd_asc_parity)` runs every check with populated inputs.

---

## 68. EBITDA quality (`ebitda_quality.py`)

Classifies add-backs against reported EBITDA:

- **Defensible** (one_time, documented) — haircut 5-10%.
- **Aggressive** (normalization, rent, CEO comp) — haircut 30-50%.
- **Phantom** (synergies, run-rate, projected) — haircut 60-75%.

Produces a partner-EBITDA (reported + haircut-adjusted add-backs)
and a quality verdict (high / moderate / low / implausible) based
on both the add-back ratio and phantom-share.

---

## 69. Covenant monitor (`covenant_monitor.py`)

Live covenant-compliance tracker for Ops partners:

- Per-covenant status (green / amber / red) based on headroom %.
- Break-EBITDA math — the EBITDA level that triggers a technical
  default given known debt + interest.
- Trend projection — status at end of next quarter given per-
  quarter trend.
- Aggregate report flags the worst status and counts red/amber
  covenants.

Intended for the monthly ops-partner review cadence alongside
`value_creation_tracker.py`.

---

## 70. Liquidity monitor (`liquidity_monitor.py`)

13-week cash projection with runway + covenant-floor breach
detection. Projects opening / collections / outflows / debt-service
/ ending balance per week. Flags:

- **Red** when the projection breaches the covenant cash floor at
  any week.
- **Amber** when runway is under 26 weeks.
- **Green** otherwise.

---

## 71. M&A pipeline (`ma_pipeline.py`)

Add-on acquisition pipeline tracking:

- Stage inventory across `sourced / outreach / loi / diligence /
  closed / passed`.
- Conversion probabilities per stage (sourced 30%, outreach 40%,
  loi 60%, diligence 75%).
- Weighted-close EBITDA = sum of target EBITDA × prob(close | stage).
- Expected closes/year from active count × avg conversion × cycle
  speed.
- Capacity-check ratio vs platform EBITDA.

---

## 72. ESG screen (`esg_screen.py`)

ESG diligence screen for LP reporting:

- **Hard exclusions** — tobacco, firearms, short-term detention,
  fossil-fuel-primary, controversial weapons. Any triggers → score
  zero'd, gate closed.
- **Composite scoring** — blend of E/S/G scores, board diversity
  vs 30% threshold, and reporting completeness (scope-1/2,
  DEI metrics, worker safety).
- **Reporting gaps** — specific items missing from current tracking.
- A..F grade; penalty of up to 25 points for reporting gaps.

---

## 73. Deep-dive heuristics (`deepdive_heuristics.py`)

Ten more mature-diligence partner rules:

- `entry_equals_exit_same_year` — flat-multiple + short-hold combo.
- `rural_govt_concentration` — rural / CAH + ≥60% government mix.
- `teaching_cmi_mismatch` — major-teaching flag + low CMI.
- `ebitda_growth_no_volume` — margin expansion > 250 bps with
  < 5% revenue growth.
- `long_hold_thin_conversion` — 7+ year hold on < 10% margin asset.
- `no_operating_partner_assigned` — RCM thesis without named op
  partner.
- `mgmt_rollover_too_high` — equity rollover > 30% signals founder-
  scale limits.
- `staff_turnover_trend_up` — turnover trending up > 2 pp/yr.
- `pending_cms_rule` — specific CMS rulemaking affects thesis.
- `gp_valuation_too_aggressive` — GP mark well above peer comps.

---

## 74. Master bundle (`master_bundle.py`)

One-call aggregator that produces every PE-intel artifact for a
packet: review, IC memo (markdown / html / text), LP pitch
(markdown / html), memo formats (one-pager / slack / email / pdf /
deck), analyst cheatsheet, board memo, 100-day plan markdown,
narrative styles (analyst / skeptic / three-sentence), extras
(heuristics, red flags, deepdive, bear-book), regulatory items,
scenario narrative, partner discussion, audit trail.

Each artifact is guarded — a bug in any one does not take down the
bundle. Returns a flat JSON-serializable dict for caller persistence
(SQLite blob, S3, Notion page).

---

## 75. Tax structuring (`tax_structuring.py`)

Partner-prudent tax structure checks:

- **Step-up eligibility** — partnership/S-corp/LLC sellers enable
  step-up; C-corp sellers require 338(h)(10) or F-reorg.
- **State drag** — high-income-tax states (CA/NY/NJ/etc) vs no-
  income-tax states (TX/FL/TN/etc).
- **163(j) interest cap** — flags when interest exceeds 30% of
  adjusted taxable income.
- **QSBS** — Section 1202 eligibility with 5-yr hold tests.
- **F-reorganization** — captures C-corp step-up complexity.
- **International** — GILTI / Subpart-F exposure flag.

Output includes estimated $ impact where computable (e.g., lost tax
shield from 163(j) cap excess).

---

## 76. Insurance diligence (`insurance_diligence.py`)

Insurance-program review across healthcare programs:

- **Professional liability** — minimum multiple of EBITDA by sub-
  sector (acute-care 3x, ASC 1.5x, behavioral 2.5x, etc.).
- **Cyber** — $5M healthcare breach benchmark.
- **Self-insured retention** — flags under-funded actuarial reserves.
- **Claims frequency** — 24-month window; >15 claims = systemic.
- **Largest open claim** — escrow / indemnity recommended when
  >40% of EBITDA.
- **Tail policy** — recommended on claims-made program changes.

Partner-facing output: list of `InsuranceGap` items + overall gap
score + tail-policy recommendation.

---

## 77. Portfolio dashboard (`portfolio_dashboard.py`)

Desk-view aggregator that takes a list of `PartnerReview` objects
and returns:

- Recommendation mix (PASS / PROCEED / STRONG_PROCEED counts).
- Regime + posture + sector + state concentration.
- Deals with critical / 3+ high-severity flags.
- Avg investability score + avg stress grade.
- Partner-facing summary naming the top priorities.

---

## 78. Integration readiness (`integration_readiness.py`)

Post-close integration scorecard across 11 dimensions: integration
officer, day-1 systems plan, management retention + comp alignment,
workstream leads (RCM / IT / clinical / finance / HR), integration
budget, communications plan. 100-point weighted composite with
verdict `ready` / `qualified` / `not_ready`.

Penalties for long TSA (> 12mo) and missing integration officer on
roll-up theses.

---

## 79. Management compensation (`management_comp.py`)

Partner-prudent checks on MIP / LTIP structure:

- **MIP pool** — 8-15% of fully-diluted pool.
- **CEO share of MIP** — 30-50%.
- **Vesting** — 4-5 years.
- **Cliff** — 12 months standard.
- **Acceleration** — double-trigger standard, single-trigger flagged.
- **CEO rollover** — 5-15% for alignment.
- **LTIP** — 25-75% of base.
- **Performance vesting** — 20-70% of grant.

Flags each item as `standard / aggressive / light` with concrete
remediation.

---

## 80. Red-team review (`red_team_review.py`)

Adversarial-pushback generator. Takes a `PartnerReview` and returns:

- Top 3-4 attacks by vector (valuation / operating / regulatory /
  structure / concentration).
- Alternative sponsor-side narratives.
- Break-the-deal scenarios.
- "If I had to pass, why?" rationale.

Complements `narrative_styles.compose_skeptic_view` with a longer-
form, multi-vector adversarial take.

---

## 81. Data-room tracker (`data_room_tracker.py`)

Scores a seller-provided data-room against a 34-item canonical
checklist across 8 categories (financial, payer, operational,
clinical, regulatory, legal, it, hr). Priority weighting: P0 × 3,
P1 × 2, P2 × 1. Returns a 0-100 completeness score, per-category
completeness, P0 / P1 gap lists, and readiness verdict
(`ready` / `partial` / `insufficient`).

---

## 82. Workstream tracker (`workstream_tracker.py`)

Post-close integration workstream tracker. Each `Workstream` (RCM,
IT, clinical, finance, HR, PMO) has a lead, a list of milestones,
and a health flag (green / amber / red). Aggregator surfaces:

- Overall completion percentage.
- Delayed milestone count.
- Red / amber workstream list for ops-partner escalation.

Distinct from `diligence_tracker.py` (pre-close) — runs post-close
alongside `value_creation_tracker.py` and `hundred_day_plan.py`.

---

## 83. Negotiation position (`negotiation_position.py`)

Translates a `PartnerReview` into a pricing-negotiation cheatsheet:

- **Anchor** — opening-offer multiple + price (below seller ask).
- **Walkaway** — below which the partner pulls the bid.
- **Leverage points** — findings from the review to justify a
  lower offer.
- **Concessions** — non-price items to unstick talks (higher
  rollover, R&W tail, earnout, staged close).
- **Cadence** — `aggressive` / `disciplined` / `walk` based on the
  recommendation + critical flags.

---

## 84. LOI drafter (`loi_drafter.py`)

Generates a partner-voice LOI term sheet from a `PartnerReview` +
`NegotiationPosition`. Includes purchase price / structure,
exclusivity period (30-60 days by recommendation), diligence
scope (extended per flagged findings), financing terms,
management terms, closing conditions, and explicit binding vs
non-binding delineation.

---

## 85. Post-mortem (`post_mortem.py`)

Structured lessons-learned template for exited deals. Compares
actual vs planned across IRR / MOIC / exit multiple / exit EBITDA.
Classifies net-vs-plan (outperform / on_plan / underperform) and
surfaces lessons tied to the underperformance dimension, with
concrete playbook-update suggestions that map back to
`heuristics.py`.

---

## 86. Cycle timing (`cycle_timing.py`)

Classifies the current healthcare-PE market into one of four cycle
phases (early_expansion / mid_expansion / peak / contraction)
using indicators: current vs 10-year avg multiple, deal-volume
YoY, LP commitment YoY, fed-funds direction, debt spreads.

Returns phase + confidence + entry implication + exit implication.
Used when the partner asks "should we be deploying aggressively
right now."

---

## 87. Exit planning (`exit_planning.py`)

Generates a year-by-year exit preparation roadmap tailored to hold
length + thesis type. Year-1 front-loads audit/close discipline;
mid-years build buyer-candidate lists and data hygiene; last
year is the formal process. Extra milestones for roll-up, RCM,
distressed, and IPO theses.

Complement to `exit_readiness.py` (static scorecard) —
`exit_planning.py` is the dynamic roadmap.

---

## 88. Benchmark bands (`benchmark_bands.py`)

Additional subsector bands extending the reasonableness matrix:

- **SG&A as % of revenue** — subsector-specific overhead bands.
- **Interest-to-EBITDA** — LBO debt-service intensity.
- **Same-store sales growth** — volume-vs-rate decomposition.
- **Net working-capital days** — AR + inventory - AP.
- **Outpatient revenue share** — for acute-care and CAH.

---

## 89. Payer-mix risk (`payer_mix_risk.py`)

Finer-grained payer-mix analysis beyond simple regime classification:

- Payer HHI (0-10000 scale).
- Dominant-payer flag (single payer ≥ 50%).
- Medicare Advantage ≥ 30% flag (MA behaves differently from FFS).
- Medicaid Managed Care ≥ 30% flag.
- ACA exchange ≥ 20% flag.
- Mix-shift flags from year-over-year trend data.

---

## 90. Peer discovery (`peer_discovery.py`)

Finds the most-similar peers for a candidate deal from a universe
using a weighted similarity function over:

- Sector (30%)
- Size bucket (20%)
- Payer regime (20%)
- State (10%)
- Margin band (10%)
- Leverage band (10%)

Used pre-IC to surface known analogs and post-close to build
cohorts for lever-benchmarking.

---

## 91. Reimbursement cliffs (`reimbursement_cliff.py`)

Models named reimbursement rate-change events (Medicare sequestration
reset, IMD waiver expiry, site-neutral expansion, 340B rule
updates) against a deal's hold window. Returns cliffs inside hold,
dollar impact at each cliff given payer-level revenue exposure,
and severity ranking.

`default_cliff_library()` provides a starter catalog — deal teams
extend per deal.

---

## 92. Scenario comparison (`scenario_comparison.py`)

Builds base / bull / bear three-column pricing comparison. Each
column computes exit EBITDA, exit multiple, EV, equity, MOIC, and
IRR. Bull/bear deltas are caller-configurable (default +15% / +1x
and -20% / -1x). Returns MOIC spread with partner-voice commentary
on deal sensitivity.

---

## 93. Vintage return curve (`vintage_return_curve.py`)

Projects year-by-year DPI / TVPI / called-capital curve for a
given fund vintage + target MOIC. Produces the classic J-curve
shape: early draw-down, inflection around year 3, peak around
year 5-7. Outputs trough year, inflection year, and partner note.

---

## 94. Change log

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
- **2026-04-17** — Added `hundred_day_plan.py` (4-workstream post-
  close action plan generator driven by the heuristic hits).
- **2026-04-17** — Added `ic_voting.py` (role-weighted IC vote
  aggregator with veto + dissent tracking) and `diligence_tracker.py`
  (workstream-scoped diligence board with IC-ready check and
  auto-seed from a PartnerReview).
- **2026-04-17** — Added `comparative_analytics.py` (portfolio
  concentration, deal-vs-book, ranking, correlation risk).
  Full inventory: 19 modules, 291+ unit tests.
- **2026-04-17** — Added `workbench_integration.py` (single-call
  bundle + compact API payload), `value_creation_tracker.py`
  (monthly lever tracker with partner rollup), and `exit_math.py`
  (waterfall + preferred + catch-up + reverse MOIC→EBITDA math).
  Full inventory: 22 modules, 314+ unit tests.
- **2026-04-17** — Added `deal_comparables.py` (illustrative comp
  registry + filtering + percentile placement). Full inventory:
  23 modules, 325 pe_intelligence unit tests, 3448 total tests
  passing project-wide.
- **2026-04-17** — Added `debt_sizing.py`, `management_assessment.py`,
  `thesis_validator.py`, `synergy_modeler.py`, `working_capital.py`,
  `fund_model.py`. Full inventory: 29 modules, 386 pe_intelligence
  unit tests.
- **2026-04-17** — Added `regulatory_stress.py` (quantifies $ EBITDA
  impact of CMS/Medicaid/340B/site-neutral/SNF-VBP shocks). Full
  inventory: 30 modules, 395 pe_intelligence unit tests.
- **2026-04-17** — Added `cash_conversion.py` (FCF/EBITDA by
  subsector) and `lp_side_letter_flags.py` (LP conformance screen).
  Full inventory: 32 modules, 415 pe_intelligence unit tests.
- **2026-04-17** — Added `pipeline_tracker.py` (sourcing-funnel
  stats + stale-deal detection) and `operational_kpi_cascade.py`
  (rank KPIs by $ EBITDA impact, segregate cash vs recurring).
  Full inventory: 34 modules, 431 pe_intelligence unit tests.
  Full project suite 3552 passed.
- **2026-04-17** — Added `commercial_due_diligence.py` (TAM/share/
  growth/competitive checks), `icr_gate.py` (IC-Ready consolidator),
  `cohort_tracker.py` (vintage-cohort benchmarks), and
  `partner_discussion.py` (autogen Q&A). Full inventory: 38 modules,
  466 pe_intelligence unit tests.
- **2026-04-17** — Added `kpi_alert_rules.py` (threshold-based alerts
  for monthly ops reviews) and `recon.py` (reconcile review + plan
  + board for coherence). Full inventory: 40 modules, 479
  pe_intelligence unit tests.
- **2026-04-17** — Added `capital_plan.py` (capex structuring +
  intensity validation by subsector) and `auditor_view.py` (full
  decision audit trail). Full inventory: 42 modules, 491
  pe_intelligence unit tests.
- **2026-04-17** — Added `thesis_templates.py` (6 prebuilt
  narrative scaffolds). Full inventory: 43 modules, 498
  pe_intelligence unit tests. Full project suite **3632 passed**.
- **2026-04-17** — Added 6 concept-named modules: `regime_classifier.py`,
  `market_structure.py` (HHI/CR3/CR5), `stress_test.py` (scenario
  grid), `operating_posture.py`, `white_space.py`, and
  `investability_scorer.py`. All wired into `partner_review.py` so
  every `PartnerReview` now carries regime / market / stress /
  posture / white space / investability outputs. Full inventory:
  49 modules, 558 pe_intelligence unit tests.
- **2026-04-17** — Deepened coverage: `extra_heuristics.py`
  (8 more rules), `extra_bands.py` (capex / occupancy / RVU / CMI /
  LOS), `narrative_styles.py` (5 voices), `memo_formats.py` (5
  renderers), `extra_archetypes.py` (8 specialized patterns). Full
  inventory: 54 modules, 610 pe_intelligence unit tests. Full
  project suite **3715 passed**.
- **2026-04-17** — Added `extra_red_flags.py` (10 more deal-killer
  detectors). Full inventory: 55 modules, 622 pe_intelligence
  unit tests.
- **2026-04-17** — Added `scenario_narrative.py`,
  `deal_comparison.py`, `priority_scoring.py`, `board_memo.py`.
  Full inventory: 59 modules, 648 pe_intelligence unit tests.
- **2026-04-17** — Added `contract_diligence.py`,
  `service_line_analysis.py`, `quality_metrics.py`,
  `labor_cost_analytics.py`. Full inventory: 63 modules, 679
  pe_intelligence unit tests.
- **2026-04-17** — Added `analyst_cheatsheet.py`,
  `reimbursement_bands.py`, `ebitda_quality.py`. Full inventory:
  66 modules, 702 pe_intelligence unit tests.
- **2026-04-17** — Added `covenant_monitor.py` (live covenant
  tracking + break-EBITDA math). Full inventory: 67 modules, 713
  pe_intelligence unit tests.
- **2026-04-17** — Added `liquidity_monitor.py`, `ma_pipeline.py`,
  `esg_screen.py`. Full inventory: 70 modules, 733
  pe_intelligence unit tests.
- **2026-04-17** — Added `deepdive_heuristics.py` (10 mature-
  diligence rules) and `master_bundle.py` (one-call all-artifacts
  aggregator). Full inventory: 72 modules, 748 pe_intelligence
  unit tests.
- **2026-04-17** — Added `tax_structuring.py` (step-up, 163(j),
  QSBS, state drag) and `insurance_diligence.py` (PL / cyber /
  SIR / claims / tail-policy). Full inventory: 74 modules, 767
  pe_intelligence unit tests.
- **2026-04-17** — Added `portfolio_dashboard.py`,
  `integration_readiness.py`, `management_comp.py`. Full
  inventory: 77 modules, 791 pe_intelligence unit tests.
- **2026-04-17** — Added `red_team_review.py` and
  `data_room_tracker.py`. Full inventory: 79 modules, 805
  pe_intelligence unit tests.
- **2026-04-17** — Added `workstream_tracker.py`. Full inventory:
  80 modules, 812 pe_intelligence unit tests.
- **2026-04-17** — Added `negotiation_position.py`. Full inventory:
  81 modules, 820 pe_intelligence unit tests.
- **2026-04-17** — Added `loi_drafter.py`. Full inventory: 82
  modules, 827 pe_intelligence unit tests.
- **2026-04-17** — Added `post_mortem.py`, `cycle_timing.py`,
  `exit_planning.py`. Full inventory: 85 modules, 850
  pe_intelligence unit tests.
- **2026-04-17** — Added `benchmark_bands.py` and
  `payer_mix_risk.py`. Full inventory: 87 modules, 865
  pe_intelligence unit tests.
- **2026-04-17** — Added `peer_discovery.py`. Full inventory: 88
  modules, 871 pe_intelligence unit tests.
- **2026-04-17** — Added `reimbursement_cliff.py`,
  `scenario_comparison.py`, `vintage_return_curve.py`. Full
  inventory: 91 modules, 890 pe_intelligence unit tests.
