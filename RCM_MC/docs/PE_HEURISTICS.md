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

## 94. Co-invest sizing (`coinvest_sizing.py`)

Splits a deal's equity check between fund commitment and LP
co-investment offering. Fund commitment = min of three binders:
total equity, concentration cap (typically 10-15% of fund size),
and per-deal budget ((fund × (1 - reserve)) / expected deals).
Co-invest offered = total_equity - fund_commitment.

When LPs signal demand, compute coverage = demand / coinvest.
≥ 1.5x = oversubscribed (allocation decisions matter); < 1.0x =
undercovered (widen invite list or reduce syndication). Fully
covered by fund means no co-invest needed.

This replaces partner intuition (\"let's offer $X to LPs\") with
a cap-table-aware number that respects concentration limits.

---

## 95. Sensitivity grid (`sensitivity_grid.py`)

One-variable-at-a-time MOIC / IRR sweeps. Supported variables:
entry_multiple, exit_multiple, ebitda_growth, leverage_multiple,
hold_years. Produces a grid of ``SensitivityPoint`` rows and
summary stats (base MOIC, swing, deltas vs base).

Directionality partners should confirm the model reproduces:

- **Exit multiple ↑ → MOIC ↑** (linear in exit EV).
- **Entry multiple ↑ → MOIC ↓** (same exit, bigger entry equity).
- **EBITDA growth ↑ → MOIC ↑** (compounds over hold).
- **Leverage ↑ → MOIC ↑** (for a winner — equity base shrinks).
  But leverage also amplifies bear cases; this grid shows magnitude
  only, pair with ``stress_test`` for downside.
- **Hold years ↑ → MOIC ↑** (more EBITDA growth compounds) but
  IRR may flatten or decline since the exit is further out.

``tornado(base, sweeps)`` runs several sweeps and returns them
sorted by MOIC swing — the widest swing is the variable the deal
is most sensitive to. That's where diligence time goes.

---

## 96. Capital structure trade-off (`capital_structure_tradeoff.py`)

The "how much leverage?" question made explicit. For each leverage
multiple in a sweep, compute:

- **Equity MOIC / IRR** — winner-case, same exit multiple.
- **Interest coverage** — EBITDA / annual interest at entry.
- **Default risk score (0-100)** — heuristic based on coverage and
  absolute leverage.
- **Status** — `green` (coverage ≥ 3x AND leverage < 6x),
  `yellow` (coverage ≥ 2x AND leverage < 7x), `red` (below either
  threshold).

Healthcare PE prudence bounds:

- Coverage < 2.0x → covenant trip probability material in a rate
  shock or a -10% EBITDA year. Red.
- Leverage ≥ 7.0x → bank syndicate will apply FDIC SNC
  "non-pass" scrutiny; pricing ratchets up. Red.
- 6.0x-7.0x or coverage 2.0x-3.0x → yellow (workable but needs
  headroom cushion in base case).
- < 6.0x AND coverage ≥ 3.0x → green zone.

``sweep_cap_structure`` returns the max-MOIC point that is still
non-red as the recommendation. Partners routinely push against
this to squeeze more MOIC; the module's role is to make the
coverage cost of that decision visible.

---

## 97. Refinancing window (`refinancing_window.py`)

Rule-based refi decision engine over a debt stack. For each
tranche, produces one of:

- **refi_now** — maturity within 1 year, OR current rate is
  ≥100 bps above market with healthy covenant headroom in a
  flat/rising-rate environment.
- **refi_in_1_year** — rates rising AND maturity in 2-3 years;
  lock in before the squeeze.
- **wait** — rates falling (better pricing coming), OR covenant
  headroom too thin (< 15%) to approach lenders.
- **hold_to_maturity** — no edge available.

Aggregate output: `total_maturity_wall_m` (principal due in next
24 months) + partner note. This replaces "should we refi?" gut
calls with a rule-based board-ready memo.

Healthcare-PE wrinkles not yet encoded:

- PIK debt behaves differently; this module treats it as cash-pay.
- Revolver reserves don't mature in the normal sense — treat
  as operating runway, not refi object.

---

## 98. Dividend recap analyzer (`dividend_recap_analyzer.py`)

Tests whether a portfolio company can be re-levered to return
cash to LPs (DPI without an exit). Gates:

- **Max leverage tolerance** — post-recap leverage ≤ 6.5x (default).
- **Post-recap interest coverage** — must remain ≥ 2.5x at
  market debt rate.
- **No incremental debt capacity** — if already at the cap, block.

Output: proposed dividend size (incremental debt × 98% fee
haircut), post-recap leverage + coverage, **DPI uplift**
(dividend / fund equity invested). The DPI number is what drives
partner conversations — a 0.5x DPI uplift mid-hold materially
improves the vintage's interim return profile.

Blockers are explicit: if coverage would drop below the target,
if current leverage is already past the cap, or if there's no
incremental debt capacity, the module returns feasible=False with
named reasons.

---

## 99. Carve-out risks (`carve_out_risks.py`)

Carve-out deals (buying a business from a larger parent) carry a
structurally different risk profile from LBOs of standalone
companies. This module codifies the specific risks:

- **TSA scope gaps** — if < 80% of shared services covered, Day-1
  operations are at risk. < 50% is high severity.
- **Short TSA duration** — < 12 months forces accelerated stand-up.
- **Change-of-control contracts** — ≥ 20% of revenue with CoC
  clauses is material; ≥ 40% is high severity. Buyer must secure
  customer consents pre-close.
- **Unaudited carve-out financials** — always high severity.
  Allocations (parent overhead, shared-service cost) are
  judgmental and can distort EBITDA by 10-30%.
- **Shared IT systems** — ≥ 3 is medium, ≥ 5 high. ERP / CRM
  separations run $2M+ each and 12-18 months.
- **Parent brand dependency** — medium when present; rebrand
  required within the TSA window.
- **Payer re-credentialing (healthcare only)** — each new NPI/TIN
  payer contract takes 90-120 days. 20+ contracts is high severity.
- **Key employee retention** — < 75% expected retention is
  medium; < 60% is high severity.

Aggregate output: total separation cost estimate, longest-path
timeline, high-severity count, partner note ("Severe", "Material",
"Standard", or "Clean"). Each risk ships with a mitigation line
that IC wants on the first diligence call.

---

## 100. Secondary sale valuation (`secondary_sale_valuation.py`)

Prices two types of secondary transactions:

- **LP-led** — one LP sells a fund interest. Priced at a
  discount to NAV:
  - Base: 500 bps healthcare / 800 bps non-healthcare.
  - Fund age ≥ 10y: +700 bps. ≥ 7y: +300 bps. ≤ 3y: -200 bps.
  - DPI < 0.10x: +500 bps. DPI ≥ 0.80x: -200 bps.
  - Top-asset concentration ≥ 40%: +400 bps.

- **GP-led continuation vehicle** — usually priced near or above
  NAV. Pricing is driven by projected remaining IRR vs buyer's
  required hurdle:
  - Projected IRR > hurdle + 500 bps → 500 bps premium possible.
  - Projected IRR < hurdle → 600 bps discount required.

Output: indicative bps vs NAV (positive = discount, negative =
premium), implied price in $M, driver list. Partner tone is
calibrated: ≥ 2000 bps = "deep discount / tail-end", 1000-2000 =
"material", 500-1000 = "modest", 0-500 = "near NAV", < 0 =
"premium pricing".

---

## 101. LBO stress scenarios (`lbo_stress_scenarios.py`)

Named partner-recognizable downside scenarios with covenant
breach checks. Library (healthcare-flavored):

- `recession_soft` — -10% EBITDA, rates +100 bps.
- `recession_hard` — -25% EBITDA, rates +200 bps.
- `denial_rate_spike` — -15% EBITDA (working-capital hit).
- `medicare_cut` — -8% EBITDA (IPPS / fee schedule).
- `labor_shock` — -18% EBITDA (wage inflation).
- `cyber_attack` — -20% EBITDA + $5M one-time cash outflow.
- `lost_contract` — -12% EBITDA (large payer loss).

For each scenario, the module computes stressed EBITDA,
post-shock leverage and coverage, whether either covenant is
breached, and a rough **months-to-default** estimate assuming
EBITDA doesn't recover. Cash runway = cash / (interest - stressed
EBITDA). No recovery modeled.

Aggregate output ranks scenarios by worst coverage and produces
a partner note:

- 0 breaches → "Covenants hold".
- 1-2 breaches → "Manageable, focused monitoring".
- 3+ breaches → "Capital structure is fragile — reduce entry
  leverage or negotiate covenant-lite terms".

---

## 102. Physician compensation benchmark (`physician_compensation_benchmark.py`)

For physician-practice PE (PPMs, specialty consolidators), comp
is the single largest cost line. This module compares actual
comp vs partner-approximated MGMA medians across 9 specialties:

- Primary care, cardiology, orthopedics, dermatology,
  gastroenterology, ophthalmology, anesthesiology, emergency
  medicine, radiology.

Two ratios benchmarked:

- **Total comp vs median** — ≥ 1.20× = high (margin pressure);
  ≤ 0.85× = low (flight risk).
- **Comp per wRVU vs median** — ≥ 1.20× = inefficient
  (overpaying for output); ≤ 0.85× = efficient or under-comp.

Structural check on base-productivity mix:

- Base ≥ 80% of total → weak productivity incentive; expect
  flat volume.
- Base ≤ 30% of total → retention risk for average producers.

Optional ``coastal_adjust=True`` shifts median 5% for NYC/SF/LA
markets. Aggregate partner note names the risk (above-market
margin opportunity, below-market flight risk, or within bands).

---

## 103. EBITDA normalization (`ebitda_normalization.py`)

Sellers push "Adjusted EBITDA" hard. This module codifies the
partner haircut discipline:

- **Defensible (100% credit)** — one-time legal / cyber / fire
  costs, CEO severance, founder-family non-economic salary,
  pre-IPO readiness costs.
- **Defensible with support (70% credit)** — signed synergies,
  signed-contract revenue annualization, executed cost takeouts
  (severance paid).
- **Aggressive (30% credit)** — projected-not-realized synergies,
  pipeline revenue run-rate, "non-recurring" items that recur.
- **Reject (0% credit)** — sponsor management fees, pre-opening
  losses as add-backs, stock-comp add-backs.

Output: **Partner's Adjusted EBITDA** = Reported + Σ (amount ×
haircut). The gap between Seller's and Partner's numbers is the
renegotiation lever:

- ≥ 20% gap → renegotiate purchase price off partner view.
- 10-20% gap → modest renegotiation leverage.
- < 10% gap → bridge largely supportable.

Unknown categories default to "aggressive" (30% credit) — the
partner-prudent posture when in doubt.

---

## 104. Staffing pipeline analyzer (`staffing_pipeline_analyzer.py`)

Healthcare services live or die on clinician supply. Projects
4-quarter headcount trajectory per role with:

- **Hire yield** — assumes 60% of offers convert.
- **Attrition** — quarterly rate applied to current headcount.
- **Floor breach** — first quarter headcount drops below required
  minimum (regulatory / contractual).
- **Lost revenue** — open reqs × time-to-fill × daily revenue.

Default TTF: 90d physician, 45d NP/PA, 60d RN, 30d tech. Default
productivity ramp: 6mo / 3mo / 2mo / 1mo.

Findings flagged:

- **High** — attrition ≥ 10%/qtr, or headcount projected below
  floor.
- **Medium** — open reqs > max(3, HC/10), or pipeline < 2× open
  reqs.

Aggregate partner note: 2+ high findings = "material deal risk";
1 high = "address at 100-day plan"; none = "manageable" or
"healthy posture".

---

## 105. M&A integration scoreboard (`ma_integration_scoreboard.py`)

Roll-up / platform deals depend on bolt-on integration execution.
This module scores each bolt-on on six dimensions with partner
weights:

- **IT cutover (20%)** — systems consolidated onto platform.
- **Billing conversion (20%)** — billing on platform codes.
- **Synergy realization (25%)** — realized vs target on schedule.
- **Customer retention (20%)** — revenue retained vs pre-close.
- **Employee retention (10%)** — key staff retained.
- **Brand migration (5%)** — typically lowest weight, done last.

Per-deal health is a 0-100 weighted score. Platform health is
revenue-weighted across bolt-ons. Red flags fire for:

- Customer retention < 90%.
- Synergy realization < 50% of expected curve.
- Employee retention < 80%.
- Past target-complete date with IT/billing incomplete.

Partner note cuts to the right action: "strong", "focus on
laggards", or "elevate to platform PMO".

---

## 106. Customer concentration drilldown (`customer_concentration_drilldown.py`)

Goes beyond "top customer = X%". Per customer:

- **Revenue share** (% of book).
- **Churn probability (12mo)** — heuristic over:
  - 5% base; +20% at-will; +15% expiring; +10% renewing in
    ≤ 6mo; +10% relationship < 1yr; -3% relationship ≥ 5yr;
    max 60% if known_at_risk.
- **Revenue at risk** = churn_p × revenue.
- **Cross-sell upside** = unpurchased products × revenue/product
  × 50% realization.

Book-level output:

- Top-1, top-5, top-10 %.
- **Customer HHI** on revenue shares.
- Total revenue-at-risk and cross-sell upside.

Partner tone: top-1 ≥ 25% = "material concentration risk";
top-5 ≥ 50% = "moderately concentrated"; otherwise "reasonably
diversified". Flags per customer name the specific action:
diversification priority, renewal squeeze, at-will conversion, etc.

---

## 107. Geographic reach analyzer (`geographic_reach_analyzer.py`)

Multi-state healthcare carries compounding complexity. Module
outputs:

- **State HHI** on revenue.
- **Top-state share** — single-state risk.
- **CPOM exposure** — revenue in restrictive corporate-practice
  states (CA, NY, TX, IL, NJ, OH, MI, WA, CO, IA, OR).
- **Density** — sites/state (operations leverage).
- **Expansion whitespace** — favorable states not yet entered
  (FL, TX, AZ, NC, TN, GA, SC, NV, UT, ID) minus present states.

Findings fire for:

- **High** — top state ≥ 60%; or CPOM exposure ≥ 50%.
- **Medium** — top state ≥ 40%; density < 2 sites/state across
  ≥ 5 states; ≥ 20 states (compliance overhead).
- **Info** — top state < 30% AND ≥ 10 states (diversified);
  density ≥ 5 sites/state (strong leverage).

Partner tone escalates with 2+ high findings (material risk,
reprice); otherwise "healthy", "standard", or "watch one finding".

---

## 108. Growth algorithm diagnostic (`growth_algorithm_diagnostic.py`)

Decomposes total revenue growth into:

- **Organic growth** = price + volume + mix.
- **Acquisition growth** = revenue from bolt-ons closed in period
  (as % of prior-year revenue).

Organic further splits:

- **Price** — rate / chargemaster / reimbursement per unit.
- **Volume** — visits, admits, cases, members.
- **Mix** — shift toward higher- or lower-reimbursement services,
  payers, or acuity. Inferred as `organic - price - volume` if
  not provided.

Quality score (0-100) weights components by sustainability:
volume (×4) > price (×2.5) > mix (×1.5) > acquisition (×1.0).
Volume growth is the most defensible — it reflects real
competitive position.

Partner note priorities:

- Organic < 0 → "contracting; acquisitions masking core decline".
- Acquisition ≥ 60% of total → "acquisition-driven; underwrite
  roll-up engine, not asset".
- Organic ≥ 10% with volume ≥ 5% → "defensible algorithm".
- Price-led with thin volume → "stress test pricing durability".

---

## 109. Technology debt assessor (`technology_debt_assessor.py`)

Scores tech debt across eight areas, each with severity + cost +
timeline. Triggers:

- **EHR** — legacy or ≥ 12 years old = high ($15M / 24mo);
  aging or ≥ 8 years = medium ($3M / 12mo).
- **Billing / RCM** — legacy = high ($5M / 18mo); aging = medium.
- **Integrations** — ≥ 20 without API layer = high; ≥ 10 without
  = medium.
- **Security** — gaps in MFA / SSO / SOC 2 / HITRUST / recent pen
  test; 3+ = high, else medium.
- **Data / analytics** — no warehouse = high; partial = medium.
- **Uptime** — > 48h outage/12mo = high; > 16h = medium.
- **Eng staffing** — < 2 engineers per 1,000 employees = high.
- **Cloud** — on-prem only = medium.

Aggregate: total cost, longest-path months, risk score 0-100
(15 × high + 7 × medium, capped). Partner note escalates:

- 3+ high → "material pre-close risk; flag to IC".
- 1-2 high → "fold into 100-day plan".
- Medium only → "include in operating plan".
- None → "clean".

---

## 110. ROIC decomposition (`roic_decomposition.py`)

DuPont-style: ROIC = margin × turnover × (1 - tax rate), where
margin = EBIT / revenue and turnover = revenue / invested capital.

Subsector peer bands (partner-approximated):

- Specialty practice: margin 18-25%, turnover 1.5-2.5x,
  ROIC 20-35%.
- Hospital: margin 10-15%, turnover 0.6-0.8x, ROIC 7-12%.
- Outpatient / ASC: margin 25-35%, turnover 1.2-1.8x, ROIC 25-40%.
- DME supplier: margin 8-12%, turnover 2.0-3.5x, ROIC 15-25%.
- Home health: margin 10-15%, turnover 3.0-5.0x, ROIC 25-40%.

Per-component verdict: `in_band`, `below_band`, `above_band`.
Partner note fires on:

- ≥ 2 below-band → "ROIC below peer band; operating posture
  needs intervention".
- 1 below-band → "weak link: [component]".
- ≥ 2 above-band → "top of peer range; confirm sustainability".

ROIC is the single cleanest metric for "how good is this
business" — margin tells ops story, turnover tells asset-light
story, tax tells structure story.

---

## 111. Working capital peer band (`working_capital_peer_band.py`)

Per-subsector DSO / DPO / DIO bands with cash-release estimation
against the favorable end of each band:

- Specialty practice: DSO 35-55, DPO 30-45, DIO 5-15.
- Hospital: DSO 45-60, DPO 30-45, DIO 30-45.
- Outpatient / ASC: DSO 40-50, DPO 30-45, DIO 15-25.
- DME: DSO 55-85, DPO 40-60, DIO 45-60.
- Home health: DSO 50-70, DPO 30-45, DIO 0-5.

Directionality:

- **DSO ↓** favorable (collect faster).
- **DPO ↑** favorable (pay later).
- **DIO ↓** favorable (less inventory on hand).

Cash release = days above / below favorable threshold × daily
revenue (DSO) or daily COGS (DPO / DIO). CCC = DSO + DIO - DPO.

Partner note:

- 2+ unfavorable levers → "high priority lever, $XM opportunity".
- 1 unfavorable → "weak link: [component]".
- In-band with residual ≥ $5M → "in-band but opportunity to
  best-in-class".
- All favorable → "preserve, don't optimize further".

---

## 112. Hold period optimizer (`hold_period_optimizer.py`)

For each possible exit year, compute exit EV (EBITDA × exit
multiple), exit equity (EV - debt), MOIC (equity / entry equity
net of fees), and IRR. Partners face the classic tension:

- **IRR-max year** is typically earlier (compounding haircuts
  later returns).
- **MOIC-max year** is typically later (EBITDA compounding).

Module returns both years and a partner note:

- IRR peak < MOIC peak → "Classic tension — exit at IRR peak if
  LP scoring metric; hold to MOIC peak if narrative matters".
- IRR peak == MOIC peak → "No ambiguity on hold year".
- IRR peak > MOIC peak → "Unusual shape — review exit multiple
  assumptions".

Inputs accept year-by-year exit multiples, so multiple compression
assumptions (e.g., 11x → 10x over hold) flow directly into the
optimizer.

---

## 113. Pricing power diagnostic (`pricing_power_diagnostic.py`)

Six-dimension weighted score (0-100) of the company's ability to
raise prices:

- **Payer concentration (20%)** — top payer ≥ 50% → score 20;
  ≥ 30% → 45; else 75.
- **Market share (20%)** — ≥ 40% → 90 (must-have); ≥ 20% → 65;
  else 35.
- **Differentiation (20%)** — base 30, +30 CoE, +30 exclusive
  service line.
- **Contract structure (15%)** — capitation (×1.0) > VBC (×0.8)
  > FFS (×0.3).
- **Payer mix (15%)** — commercial ≥ 60% → 85; ≥ 40% → 60; else 30.
- **Pricing history (10%)** — historical rate increases ≥ 5% → 90;
  ≥ 3% → 65; < 3% → 30.

Partner guidance on base-case rate assumption:

- ≥ 75 (strong) → model 3-4%/yr.
- 55-74 (moderate) → model 2-3%/yr; stress test at flat.
- 35-54 (weak) → model 0-1.5%/yr; pricing is not the lever.
- < 35 → pricing is not a lever.

---

## 114. Portfolio rollup viewer (`portfolio_rollup_viewer.py`)

Fund-level dashboard over per-deal snapshots. Aggregates:

- Totals: cost, NAV, realized, unrealized.
- **Weighted gross MOIC** = (realized + NAV) / cost.
- **Cost-weighted IRR** (deals with current_irr populated only).
- **Status counts** — held / exited / written off.
- **Top 5 gainers / losers** by period-over-period NAV delta.
- **By sub-sector** — deal count + NAV + cost.
- **By vintage year** — deal count.
- **By stage** — platform vs add-on.

Partner note:

- MOIC ≥ 2.5x → "strong".
- 1.8-2.5x → "on track".
- 1.2-1.8x → "pedestrian; need outperformance from later vintages".
- < 1.2x → "under water; GP intervention required".

This is the one-page view partners share with the Investment
Committee and LPs. Fast, honest, no hedging.

---

## 115. Bank syndicate picker (`bank_syndicate_picker.py`)

Picks lenders for a deal from a 21-lender universe covering
bulge bracket, commercial banks, healthcare specialists, and
direct lenders / BDCs.

Scoring:

- Size fit: +20 if debt in lender's hold range.
- Bulge preference for >$1B deals: +15.
- Commercial preference for $100M-$500M: +10.
- Direct-lender preference for ≤$100M: +10.
- Healthcare specialist when requested: +30.
- Direct lender when partner prefers looser covenants: +25.
- Explicitly looser covenant posture: +15.

Tiers: position 0 = lead, 1-2 = joint, 3+ = participant. Fallback
list is next 3 candidates behind the primaries.

Partner note scales to deal size:

- \>$1B → "bulge-led syndicate with 4-6 joint arrangers".
- $250M-$1B → "commercial or direct-lender club with 2-4".
- ≤$250M → "single direct lender or 2-lender club".

Universe can grow; library is partner-approximated not exhaustive.

---

## 116. Exit channel selector (`exit_channel_selector.py`)

Ranks the four exit channels:

- **Strategic** — base 40; +25 if strategic interest expressed;
  ±15 for sector heat; +10 if EBITDA ≥ $50M. Timing 9 months.
  Expected 11x base, up to 13x hot.
- **Sponsor** — base 55; ±15 for sector heat; ±10 for rate env;
  +10 if EBITDA ≥ $25M. Timing 6 months. Expected 10x base.
- **IPO** — base 25; +20 if revenue ≥ $300M AND EBITDA ≥ $75M,
  else -15; ±30 for IPO window open/closed. Timing 12 months.
  Expected 12x base.
- **Continuation** — base 30; +25 if runway thesis; +10 if held
  ≥ 5 years; +15 when IPO closed and sector not hot.

Best channel is highest score; partner note names the winner and
runner-up. Expected multiples and timings flow into waterfall
and MOIC projections.

---

## 117. Management incentive sizer (`mgmt_incentive_sizer.py`)

Sizes post-LBO MIP + LTIP + vesting. Base pool % by deal type:

- Platform LBO: 10%.
- Physician PPM: 13% (retention-critical).
- Carve-out: 8% (harder to justify more).
- Add-on: 5%.

Adjustments: +1.5pp if CEO is founder; +1pp if management
headcount ≥ 15. Capped at 18%.

Layer split:

- CEO: 25% of pool (30% if founder).
- C-suite (COO/CFO/CRO/CMO): 35%.
- Broader management (VP+): remainder.

LTIP annual cash target = 20% of CEO cash comp.

Vesting: 4-year cliff + quarterly post-cliff. Accelerator: 100%
vest at target MOIC; 50% at target-0.5x.

Partner note:

- Pool ≥ 15% → "above market; justify on retention/founder risk".
- Pool ≤ 6% → "thin; verify management engagement".
- Otherwise → "within market band".

---

## 118. QofE tracker (`qofe_tracker.py`)

Quality-of-Earnings diligence progress monitor. Tracks:

- **Status** — not_started / in_progress / draft / final.
- **Total adjustments** with "supported" / "unsupported" split.
- **NWC vs peg** — actual - peg.
- **High-severity findings** count.
- **Days until target completion**.

Critical-path flag fires when:

- Status is not final, AND
- Days < 10 OR high-severity findings ≥ 2.

Partner note scales:

- Final + 0 high → "clean".
- Final + high findings → "reflect in purchase-price mechanism".
- Critical path → "NOT on track; escalate to deal team lead".
- Draft → "review adjustments ($X unsupported)".
- Otherwise → "monitor daily as deadline approaches".

---

## 119. Board composition analyzer (`board_composition_analyzer.py`)

Scores portco board composition:

- **Independent seats %** — ≥ 25% market standard. Below → high gap.
- **Diverse representation %** — LP reporting threshold ≈ 25%.
  Below 20% → medium gap.
- **Experience coverage** — healthcare ops / clinical / public co /
  finance. Missing any → medium gap each.
- **Committees** — audit + compensation always required; compliance
  required in healthcare. Missing → high gap each.

Partner note: 2+ high gaps = "address before next LP update"; any
gaps = "decent with minor gaps"; none = "strong".

---

## 120. Historical failure library (`historical_failure_library.py`)

Named, dated healthcare-PE failures with packet-field matchers.
Unlike the generic bear_book, each entry captures a specific
deal with: thesis at entry, what went wrong, ebitda destruction %,
early-warning signals, partner lesson, and the packet_triggers
needed to pattern-match it.

Inaugural library (10 patterns):

- **envision_surprise_billing_2023** — NSA compression on OON-
  dependent staffing book.
- **steward_reit_dependency_2024** — rent/EBITDA > 0.5 on
  sale-leasebacked hospital book; multi-state failure.
- **prospect_medical_cashflow_2023** — dividend recaps + capex
  starvation in safety-net hospitals.
- **hahnemann_bankruptcy_2019** — real-estate-motivated hospital
  buyout, no operating competence.
- **radiology_partners_rate_shock_2022** — >6.5x leverage +
  floating unhedged + NSA overlap.
- **adapthealth_accounting_2021** — acquisition pace outstripping
  integration; pro-forma fiction.
- **kindred_at_home_2018** — PDGM reset mid-hold compressed
  home-health margins.
- **shopko_rx_pharmacy_2019** — DIR fees + PBM squeeze ate
  pharmacy margins.
- **21st_century_oncology_2017** — FCA settlement + regulatory
  investigations → bankruptcy.
- **surgery_partners_leverage_2016** — ASC same-site growth
  assumptions above 5% collided with reality.

Usage: `match_failures(ctx)` scans a dict of packet fields and
returns the patterns that fire. Partner reads each match as "this
deal looks like <pattern>". Treat as a strong prior against the
thesis unless specifically mitigated in underwrite.

Adding a new pattern: add a `FailurePattern` to `FAILURE_LIBRARY`
and a matcher to `_matchers()`. Matcher should read packet fields
defensively (`_get_float`, `_get_str`, `_get_bool`).

---

## 121. Partner-voice IC memo (`partner_voice_memo.py`)

A one-page, recommendation-first IC memo written in partner voice.
Not a replacement for `ic_memo` (structured template) — this is the
"60 seconds with the chairman" version.

Structure:

1. **Recommendation up top**: INVEST / DILIGENCE MORE / PASS.
2. **One-paragraph summary** — numbers-first, direct.
3. **Bull / Base / Bear case** — one line each with MOIC + IRR.
4. **Three things that would change my mind** — honest pre-mortem,
   capped at three.
5. **Open deal-killers** — any unresolved red flags, historical
   pattern matches, or valuation stretch.

Scoring (0-100, higher = more INVEST-leaning):

- Start 50.
- -12 per high red flag; -3 per other red flag.
- -3 per reasonableness out-of-band cell.
- -4 per valuation concern.
- -5 per bear_book hit; -8 per historical failure match.
- +10 defensible organic growth; +5 clear exit path.
- ±(score-50) × 0.20 for pricing power and management scores.
- -4 peak cycle; -6 contraction; +4 early expansion.

Hard rules override score:

- 2+ open deal-killers OR 2+ historical pattern matches → PASS.
- Score ≥ 70 AND no open deal-killers → INVEST.
- Score ≤ 35 → PASS.
- Otherwise → DILIGENCE MORE.

**Why:** Partners think in terms of decisions, not scorecards.
The memo forces a yes/no/maybe up top, then justifies it with
the three things that would change the answer. This is how IC
actually runs.

---

## 122. Recurring vs one-time EBITDA (`recurring_vs_onetime_ebitda.py`)

**The exit multiple only applies to recurring EBITDA.**

Worked example: $50M reported EBITDA that is $40M recurring +
$10M from a one-time contract termination payment. At 12x exit:

- Wrong: $50M × 12 = $600M exit EV.
- Right: $40M × 12 + $10M × 1 = $490M exit EV.

$110M error — the difference between a strong MOIC and a weak
one.

Recurring categories: `ongoing_operations`, `contracted_revenue`,
`recurring_fees`, `subscription`, `run_rate_operating`.

One-time categories: `working_capital_release`,
`sale_leaseback_proceeds`, `contract_termination_payment`,
`legal_settlement_recovery`, `insurance_recovery`,
`gain_on_asset_sale`, `one_time_cost_takeout`,
`grant_or_subsidy_one_time`, `covid_relief`.

Unknown categories default to one-time (partner-prudent).

Packet fields that trigger this: any `ebitda_bridge` item with a
category keyword indicating a one-time event.

---

## 123. OBBBA / sequestration / site-neutral stress (`obbba_sequestration_stress.py`)

Specific-dollar regulatory shocks partners underwrite against:

- **OBBBA 3% Medicare cut** — applied to Medicare FFS + 50%
  pass-through MA.
- **Sequestration extension 2%** — same exposure base.
- **Site-neutral HOPD** — 22% rate cut on HOPD revenue share.
- **State Medicaid freeze 3%** — Medicaid exposure by subsector:
  hospital 22%, safety-net 40%, home-health 25%, specialty 10%,
  ASC 8%.

Per-shock: `revenue_impact_pct`, `ebitda_impact_m`, and % of base
EBITDA. Combined partner note:

- ≥ 30% combined → "catastrophic; reduce leverage or pass".
- 15-30% → "material; model at 50% probability; check covenants".
- 5-15% → "manageable; fold into downside".
- < 5% → "immaterial; largely insulated".

Contribution margin on affected revenue is tunable (default
0.50). Packet fields that trigger: `medicare_ffs_pct`,
`medicare_advantage_pct`, `hopd_revenue_pct`, subsector.

---

## 124. Archetype subrunners (`archetype_subrunners.py`)

Partners don't apply generic checks — they apply checks that
match the archetype. This module branches into 7 specialized
runners. Each is a small heuristic pack with partner-voice
warnings.

Archetypes and the questions they answer:

- **payer_mix_shift** — "Can this asset actually renegotiate
  into a better mix, or is that wishful thinking?" Flags:
  Medicaid heavy without commercial leverage, rate-growth
  assumption > 6%, VBC ramp too fast.
- **roll_up** — "Is the roll-up engine healthy, or is pro-forma
  EBITDA fiction?" Flags: platform age < 3y + 5+ acq/yr
  (AdaptHealth pattern), < 80% integrated, flat organic volume
  under the wrapper.
- **cmi_uplift** — "Is the CMI lift defensible, or a RAC trap?"
  Flags: CMI gap > 0.15 in 24 months, high denial rate
  compounding the lift, long DAR.
- **outpatient_migration** — "Does the thesis survive
  site-neutral?" Flags: high inpatient share transitioning
  out; high HOPD exposure.
- **back_office_consolidation** — "How many ERPs? How many
  shared-services functions?" Flags: > 3 ERPs (24-36mo
  program), < 2 shared-services functions consolidated.
- **cost_basis_compression** — "Is there any fat left to cut?"
  Flags: labor < 40% of revenue (already lean).
- **capacity_expansion** — "Are we filling before adding?"
  Flags: utilization < 65% (value-destructive to add more),
  5+ new sites (ramp drag in years 1-2).

Dispatch via `run_archetype(name, ctx)`. Each runner reads what
it needs from the loose `ArchetypeSubrunnerContext` bag —
unused fields don't matter. Add a new archetype by writing a
runner and registering it in `ARCHETYPE_RUNNERS`.

**Worked example:** a deal pitched as a roll-up with 2-year-old
platform and 8 acquisitions/year produces an "AdaptHealth
pattern" high-severity warning; a partner reads that and asks
for the pro-forma-to-GAAP bridge before writing anything else.

---

## 125. Unrealistic-on-its-face detector (`unrealistic_on_its_face.py`)

**Partner statement:** some deal profiles are red flags on sight,
before any model runs — pass before we spend diligence hours.

Canonical worked example: **$400M NPR rural critical-access
hospital projecting 28% IRR.** That combination is physically
implausible. Rural CAH economics + cost-based reimbursement + no
commercial leverage cap IRR in mid-single-digit-to-low-teens at
best. 22%+ is not an achievable outcome — the seller either
mis-modelled or is selling what they cannot deliver.

Seven detectors:

- **rural_cah_irr_implausible** — rural/CAH + claimed IRR ≥ 22%.
- **hospital_margin_impossible** — hospital EBITDA margin ≥ 20%.
- **practice_margin_impossible** — specialty-practice margin ≥ 35%
  (likely includes cash-pay or non-operating income).
- **leverage_coverage_impossible** — leverage + coverage that
  arithmetic cannot support at market rates.
- **hospital_growth_implausible** — hospital annual growth ≥ 12%
  (M&A-hidden inorganic).
- **practice_growth_implausible** — specialty practice organic
  growth ≥ 25%.
- **government_heavy_high_margin_implausible** — ≥ 70% Medicare +
  Medicaid combined WITH ≥ 18% EBITDA margin.
- **small_deal_extraordinary_irr** — EBITDA ≤ $20M + IRR ≥ 30%
  (check equity base; small deals inflate IRR on pennies).

Output grouped: `ImplausibilityFinding` per detector with
`claim`, `reality`, and partner note. Overall: "pass-before-
modeling" when 2+ high severity, otherwise push seller on
specifics.

Packet fields that trigger: `subsector`, `revenue_m`, `ebitda_m`,
`medicare_pct`, `medicaid_pct`, `claimed_irr`, `leverage`,
`claimed_interest_coverage`, `is_rural`, `is_critical_access`.

---

## 126. Partner voice variants (`partner_voice_variants.py`)

A deal goes to IC narrated five different ways in a partner's
head. This module produces each:

- **Skeptic** — "what breaks this?"; numbers-first, no hedging;
  invokes historical pattern matches when present; ends with the
  question "pass unless X".
- **Optimist** — "where does this 10x?"; upside case; believer
  tone; ends with "this is the best deal in the pipeline" when
  conviction is warranted.
- **MD-numbers** — senior physician-investor; clinical + financial
  blend; flags CMS survey history and covenant headroom.
- **Operating partner** — "day 100 view"; what do I own; where
  are the execution gaps; hiring plan if mgmt score is low.
- **LP-facing** — what the GP would write in the next LP update;
  quoted update-style paragraph with base-case MOIC/IRR + risks.

`compose_all_voices(ctx)` produces all five. `compose_voice(name, ctx)`
produces one. Rendered markdown reads as a cross-examination of
the same deal from five senior perspectives — which is what
partners actually do before IC.

---

## 127. Cross-module connective tissue (`cross_module_connective_tissue.py`)

**The partner brain connects dots, not lists.** A denial rate
change has coding implications which have CMI implications which
change the Medicare bridge. This module does that explicitly:
takes a `SignalBundle` tagged with outputs from several modules
and emits **ConnectedInsight** narratives that only fire when
signals co-occur.

Inaugural detectors:

- **envision_thesis_confirmed** — historical:envision match +
  OON revenue ≥ 20% + pricing power < 50. Partner voice: "this
  is the Envision failure, not a mitigated version." Pass.
- **rollup_earnings_fiction** — archetype:roll_up + integration
  < 70% + pro-forma add-backs > 15%. "Exit buyer underwrites
  what is actually integrated."
- **peak_cycle_covenant_breach_likely** — peak cycle + leverage
  ≥ 6.5x + NOT covenant_lite. "Garden-variety 10% EBITDA miss
  trips the coverage test."
- **cmi_uplift_cash_squeeze** — CMI uplift + denial rate ≥ 10% +
  DAR ≥ 55. "Cash gets WORSE before it gets better."
- **medicare_heavy_no_defense** — Medicare ≥ 40% + pricing power
  < 40 + OBBBA combined ≥ 10%. "No base-case defense; thesis is
  a rate-policy bet."
- **bear_book_plus_reasonableness_stacked** — 2+ bear hits + 2+
  out-of-band reasonableness cells. "Stacked-risk signature."

Each insight includes the literal signals that triggered it, so
the partner can interrogate the logic. This is the first module
where the *reasoning* is the product; all other modules feed into
this one.

**Worked example:** Envision-pattern match + OON 30% + pricing
power 35/100 produces not "three separate warnings" but one
connected partner-voice insight: *"this is exactly the failed
thesis, pass."*

---

## 128. Live diligence checklist (`diligence_checklist_live.py`)

Canonical 30-item list across financial / clinical / legal / ops.
Each item is tagged with its source: `packet`, `mi` (management
interview), or `third_party`. The walker takes the running
diligence state and returns per-item status:

- **answered** — source closed.
- **needs_mi** — MI scheduled but not complete.
- **needs_third_party** — report outstanding.
- **stale** — packet data > 90 days old.
- **missing** — nothing scheduled.

Aggregate **IC-ready %** = answered / total. Partner note:

- ≥ 90% → "IC-ready; close remainder in final-IC pass".
- 70-90% → "target 2-3 weeks to IC-ready".
- < 70% → "missing items require MI scheduling or third-party
  engagement".

This replaces the generic diligence_tracker's purely-tracking
view with one that knows the *nature* of each gap — packet data
you can't fix with more calls, vs an MI that you schedule, vs a
third-party report that takes 4 weeks.

---

## 129. Partner traps library (`partner_traps_library.py`)

Named thesis traps partners have seen before. Each has a
seller_pitch, partner_rebuttal, and matching packet fields. The
user explicitly cited three:

- **fix_denials_in_12_months** — "we can get initial-denial rate
  from 12% down to 5% in 12 months." Partner rebuttal: 200-300
  bps/yr is the realistic ceiling; model 50% realization.
- **payer_renegotiation_is_coming** — "we're up for renegotiation
  next year; scale gives us leverage." Partner rebuttal: rate
  cards rarely deliver 5%+; headline wins come from mix shifts.
- **ma_will_make_it_up** — "Medicare Advantage enrollment growth
  will offset Medicare FFS rate risk." Partner rebuttal: MA
  plans pass through rate changes with 12-18mo lag — absorbs
  risk, doesn't cushion it.

Plus 7 more:

- **back_office_synergies_year_1** — 25-30% is year-1 realization.
- **robust_bolt_on_pipeline** — 10-15% close rate on pipeline.
- **ceo_stays_through_exit** — founder retention past 3 years
  runs ~40%.
- **we_are_underpenetrated** — structural bottlenecks often
  misdiagnosed as market-share gaps.
- **quality_and_growth_together** — rapid growth depresses
  quality 18-24 months.
- **multiple_will_re_rate** — exit multiple expansion is the
  weakest leg; underwrite ≤ entry.
- **technology_platform_lift** — first-year gains are 3-5%, not
  10%+.

`match_traps(ctx)` scans the packet; each trap has a matcher that
reads specific fields. Rendered markdown reads as "here's what
the seller is likely to say and here's the partner response" — a
drop-in tool for anyone preparing for IC.

---

## 130. First thirty minutes (`first_thirty_minutes.py`)

**Partner statement:** walking into an MI, a senior partner does
not ask generic questions. They ask three to five questions that
the packet has already pointed at, specifically enough to force
a non-rehearsed answer.

Tiers:

- **Landmine** — specific risk that kills the deal if true.
  Always goes first. Cannot be deflected to week-6 diligence.
- **Opening** — sets the tone; usually about the thing the deck
  tried hardest to downplay.
- **Probe** — follow-ups that test whether the answer is genuine
  or canned.

12 question detectors currently wired:

- Denial rate ≥ 10% → opening: "three biggest denial reasons by
  payer; structural vs fixable."
- DAR ≥ 55 → probe: "billing timing vs payer-mix vs clean-claim."
- One-time % EBITDA ≥ 15% → opening: "recurring trajectory."
- OON ≥ 20% → landmine: "NSA exposure + in-network pipeline."
- Denial rate delta +≥ 1.5pp → probe: "what broke; owner; timeline."
- C-suite tenure < 2.5 → probe: "retention packages through exit."
- Pending FCA → landmine: "settlement exposure, timeline."
- Rate growth > 5% → probe: "signed contract wins; 5%+ rate-card
  number does not exist."
- Top payer ≥ 35% → landmine: "renewal date, escalators,
  contingency if they walk or cut 5%."
- Historical pattern match → opening: "three structural
  mitigations that prevent the same outcome."
- Year-1 synergies > $5M → probe: "actions in months 1-6 vs
  7-12 with named owners."
- Sale-leaseback in thesis → landmine: "rent-to-EBITDA at -10%
  EBITDA; Steward told us what happens."

Each question ships with the packet trigger (e.g.
`current_denial_rate=0.15`) so the associate can reference the
data when management deflects.

**Worked example:** an Envision-pattern staffing deal with 30%
OON, rising denials, and a 45% top-payer concentration generates
three landmine questions up top — exactly how a senior partner
would open.

---

## 131. Thesis coherence check (`thesis_coherence_check.py`)

**Partner statement:** "You claim margin expansion AND 15% volume
growth AND labor cost reduction AND quality improvement — how
does all that work together?"

Most decks list thesis pillars independently. This module checks
them against each other. Named tensions:

- **volume_growth ↔ margin_expansion** — high: if you grow 12%+
  and expand margin without labor investment, you're burning
  existing staff. Pick two.
- **price_growth ↔ contract_reality** — medium: > 5% rate growth
  hides mix shift; underwrite pure rate 2-3%.
- **volume_growth ↔ quality_improvement** — medium: rapid growth
  typically depresses quality 18-24 months. Both improving
  simultaneously is rare.
- **roll_up_closings ↔ integration_investment** — high: aggressive
  roll-up without proportional integration spend is pro-forma
  fiction (AdaptHealth pattern).
- **multiple_expansion ↔ exit_underwriting** — medium: the weakest
  leg in any MOIC bridge. If the math needs expansion to work,
  the math doesn't work.
- **labor_cost_reduction ↔ enabling_investment** — high: labor
  cuts ≥ 5% without tech or process investment is RIFs, which
  compress quality and trigger flight.

Score 100 minus penalties (high = -20, medium = -8). Partner note:

- ≥ 85 → "pillars fit together".
- 60-85 → "pillars in tension; walk management through specifics".
- < 60 → "internally incoherent; deck has not done the work".

Worked example: a deck claiming 20% volume + 4% margin + -10%
labor + 20% roll-up + 7% price + multiple expansion produces
5+ contradictions. The partner reads all of it and says "which
one are we buying?"

---

## 132. Margin of safety (`margin_of_safety.py`)

**Partner statement:** "How wrong can I be on each lever before
MOIC falls below hurdle?"

For each of four levers (EBITDA growth, exit multiple, entry
multiple, leverage), binary-search the breakeven value where MOIC
equals the hurdle. Express as % delta from base.

Safety grade per lever:

- **Thin** — harmful move of < 10% crosses breakeven.
- **Moderate** — 10-25%.
- **Ample** — ≥ 25%.

Plus a **combined shock**: -5pp growth + -1x exit multiple at once.
If this drops below the hurdle, the base case is fragile.

Partner note:

- Base MOIC already below hurdle → "pass; no margin of safety".
- 2+ thin levers → "load-bearing on aggressive assumptions".
- 1 thin lever → "pressure-test that lever specifically".
- All ample → "absorbs reasonable downside".

**Worked example:** a deal entering at 13x with 8% growth and
5.5x leverage at 2.3x hurdle shows thin margin on exit multiple
(~8% headroom) and moderate on growth. Partner reads: "the deal
cannot tolerate multiple compression. Either negotiate entry
down or stress the exit-multiple assumption."

---

## 133. Management vs packet gap (`management_vs_packet_gap.py`)

**Partner statement:** when management's story and the packet
numbers disagree, the gap size tells you what you are dealing
with.

Classification by |gap %|:

- **< 5%** → minor; rounding or timing.
- **5-15%** → material; management rounding in their favor OR
  sandbagging. Push for the packet number in underwriting.
- **≥ 15%** → contradicted; credibility issue — they are
  selling what the numbers do not show. Force reconciliation
  before IC.

Favorable-for-mgmt direction depends on `higher_is_better`:
EBITDA margin and growth are higher-is-better; denial rate and
DAR are lower-is-better.

Partner note escalates:

- 2+ contradictions → "credibility problem, not a metrics
  problem. Pause diligence until reconciled."
- 1 contradiction → "force explicit reconciliation before IC."
- 3+ material → "rounding pattern — underwrite to packet numbers
  not deck."

---

## 134. RCM lever cascade (`rcm_lever_cascade.py`)

**The canonical cross-module reasoning example** the user named:
*"a denial rate change has coding implications, which have CMI
implications, which change the Medicare bridge math."*

This module traces the cascade in four named steps:

1. **Denial rate shift** — EBITDA + cash hit. Every +1pp of denial
   is ~(cases × CMI × base_rate × 1% × 40% appeal-conversion) of
   write-off. At 10,000 cases × 1.30 CMI × $8K = 104M gross
   Medicare; +1pp denial → ~$416K EBITDA and ~$1.04M cash.
2. **Coding remediation / CDI** — if a CDI program is in place,
   CMI nudges up (e.g. +0.05). Positive EBITDA offset, but
   partner flags RAC-audit exposure on the upcoded records
   (21st_century_oncology pattern). If CDI is NOT in place, the
   lever exists but is not being pulled — 100-day-plan ask.
3. **Medicare bridge** — net Medicare EBITDA impact flows here;
   no additional hit but the partner sees the bridge line.
4. **Working capital** — denial rise extends DAR ~5 days per 1pp;
   cash pressure compounds. Covenants can trip from the cash side
   even when EBITDA holds.

Output includes both EBITDA and cash impact per step (kept
distinct because exit multiple applies to EBITDA but covenant
coverage watches cash). Partner note:

- Total EBITDA < -$2M → "material; not just a denial blip — it
  cascades."
- Modest negative → "watch covenant headroom."
- Positive → "CDI lift exceeds denial drag; confirm CDI is
  operating not planned."

---

## 135. Bear case generator (`bear_case_generator.py`)

**Partner statement:** "If I can't write the bear case, I haven't
done the work. And the bear case has to be specific to this deal,
not 'a recession hits everyone.'"

The module fires 10 deal-specific bear drivers based on the
packet. Each has a named haircut:

- **medicare_rate_shock** — Medicare FFS ≥ 30% → 3% + delta haircut.
- **nsa_oon_compression** — OON ≥ 20% → 40% of OON revenue.
- **top_payer_walk** — top payer ≥ 40% → 25% of that book.
- **denial_compounding** — denial rate ≥ 10% → (rate - 8%) × 1.5.
- **historical:<pattern>** — any named match → 20%.
- **steward_sale_leaseback** — sale-leaseback in thesis → 15%.
- **weak_management** — score < 60 → 8%.
- **rate_growth_miss** — claimed > 5% → 5%.
- **pro_forma_fiction** — pro-forma ≥ 15% → half of pro-forma.
- **labor_inflation** — labor ≥ 50% of revenue → 6%.

Haircuts combine multiplicatively (not additively). Bear exit
multiple = base − 1.5x (floor 5.0x).

Output includes:

- Bear EBITDA, bear exit multiple, bear MOIC, bear IRR.
- Probability-weighted MOIC using configurable base_probability.
- Partner-voice bear **story** that names the top driver and
  weaves in the second/third.

Partner note:

- Bear < 1.0x → "loses money; only buy if base-case probability
  ≥ 70%."
- Bear 1.0-1.5x → "clears principal but not hurdle; bet on base."
- Bear ≥ 1.5x → "real downside protection."

**Worked example:** a staffing deal with 35% OON and an Envision
pattern-match produces a bear case narrative that leads with NSA
compression, compounds with the historical pattern, and puts
bear MOIC under 1.0x. The partner reads it in 30 seconds and
knows exactly what they are betting against.

---

## 136. Payer-mix shift cascade (`payer_mix_shift_cascade.py`)

Sister module to `rcm_lever_cascade`. When a deck claims payer-mix
shift (Medicaid → commercial), the cascade has 5 steps:

1. **Magnitude** — pp of commercial share moving; annualized.
2. **Effective rate change** — blended rate lift using partner-
   approximated multipliers: commercial 1.60x, Medicare FFS 1.0x,
   MA 1.05x, Medicaid 0.65x, self-pay 0.45x.
3. **Revenue impact** — revenue × rate delta.
4. **EBITDA impact** — revenue × contribution margin.
5. **Exit multiple uplift** — ~0.25x per 10pp commercial shift;
   buyers discount un-contracted mix by 50%.

Credibility score 0-100:

- -30 if pace > 3pp/yr.
- -25 if no signed commercial contracts with claimed shift.
- -15 if pipeline < (pp_shift / 2).

Partner note:

- < 40 → "aggressive AND thin pipeline; underwrite at ≤ 25%
  realization."
- 40-70 → "some backing; underwrite 50%."
- ≥ 70 with signed contracts → "credible; 70-80% realization."
- No shift → "straight on current blended rate."

**Worked example:** a deck claims 30% → 60% commercial over 3
years with 1 contract in pipeline. Credibility drops below 40.
Partner reads: "this is a pitch, not a thesis — underwrite at
25% of claimed lift."

---

## 137. Labor shortage cascade (`labor_shortage_cascade.py`)

Third canonical cross-module cascade (after RCM and payer-mix).
When clinician turnover rises, the effects cascade:

1. **Turnover delta** — pp above baseline; extra departures =
   headcount × delta.
2. **Agency premium cost** — backfill at agency rates (~70%
   premium over W-2). Incremental = W-2 cost × premium × share
   delta.
3. **Margin compression** — labor is 100% pass-through to EBITDA;
   no < 12-month offset lever.
4. **Quality / volume impact** — high-turnover units reduce
   throughput 3-8%; revenue dips.
5. **Covenant pressure** — stressed EBITDA + possibly floating
   debt compresses coverage. Breach flagged when coverage <
   80% of pre-shock level.

Partner note priority:

- Covenant breach → "not tolerable given base posture."
- EBITDA hit ≥ 15% of base → "material; focus diligence on
  retention + agency contract terms."
- Positive but modest → "manageable; monitor agency trends
  quarterly."
- Zero → "immaterial."

**Why this cascade:** agency spend is a canary. If 2025 Q3
agency trending up, 2026 EBITDA model needs a haircut. Partner
checks quarterly labor data religiously; this module formalizes
the propagation.

---

## 138. Exit story generator (`exit_story_generator.py`)

**Partner statement:** "If I can't write the sell-side CIM
headline at entry, I don't know what I'm buying."

The exit story is NOT the investment thesis. It is the
two-sentence pitch a banker will make in 5 years. The module
composes it from: scale multiplier, revenue CAGR, recurring-
EBITDA %, payer mix, CoE/category-leader flags, M&A count.

Outputs:

- **Headline** — "Premium strategic asset / Sponsor-ready
  platform / Public-ready company" + subsector + NPR + EBITDA +
  CAGR + scale multiple.
- **Three bullets** — growth, quality of earnings, differentiation
  or M&A. Capped at 3; banker discipline.
- **Likely buyers** — based on target channel.
- **Exit risk** — the derailer (low growth, pro-forma, M&A-
  dependency, IPO window, cycle timing).
- **Banker multiple range** — subsector base ± differentiation
  adjustments (e.g., +0.5x CoE, +1.0x category leader, +0.25x
  high recurring, +0.5x commercial ≥ 60%).

Subsector bases (partner-approximated):

- Hospital: 7-10x.
- Specialty practice: 9-13x.
- Outpatient ASC: 11-15x.
- Home health: 10-13x.
- DME: 8-11x.
- Physician staffing: 7-10x.

Partner note:

- Weak story (low CAGR + <2 bullets) → "banker will struggle;
  shift to continuation."
- Strong (category leader / CoE) → "defensible range."
- Middling → "workable; main risk: [X]."

---

## 139. Partner scorecard (`partner_scorecard.py`)

**Partner statement:** "Here's my must-have list. Any ONE
failure is typically a pass. I don't trade dimensions against
each other."

Seven binary dimensions:

1. **Scale** — EBITDA ≥ fund minimum (default $15M).
2. **Team** — management score ≥ 55/100.
3. **Market position** — local share ≥ 10% OR CoE / exclusive
   service line.
4. **Unit economics** — EBITDA margin ≥ 85% of peer median AND
   cash conversion ≥ 65%.
5. **Balance sheet** — leverage ≤ 7.0x AND stress coverage ≥
   1.5x.
6. **Exit path** — articulable exit story AND credibility ≥
   50/100.
7. **Thesis integrity** — recurring EBITDA ≥ 80% AND thesis
   coherence ≥ 60/100.

Partner note escalates:

- All pass → "buy on fundamentals alone."
- 1 fail → "that alone is typically enough to pass; force
  remediation if sponsor conviction is exceptional."
- 2+ fail → "do not spend partner time on remaining
  diligence."

Not weighted. Partners who weight their must-haves end up
talking themselves into deals that fail the binary test.

---

## 140. Cycle timing pricing check (`cycle_timing_pricing_check.py`)

**Partner statement:** "Am I paying peak multiple for peak
EBITDA?" Late-cycle discipline. The double-count is the most
expensive mistake in PE — it looks fine in the model because
normal × normal is fine, but peak × peak overstates value by
2 turns of multiple or more.

Two flags:

- **peak_multiple** — entry multiple ≥ 110% of subsector cycle-
  average AND cycle_phase is peak or mid_expansion.
- **peak_ebitda** — entry EBITDA ≥ 115% of 3-year trailing
  average.

Subsector cycle-average exit multiples (partner-approximated):

- Hospital 8.5x
- Specialty practice 10.5x
- Outpatient ASC 12.5x
- Home health 11.0x
- DME 9.5x
- Physician staffing 8.0x

Recommended haircut:

- **Double peak** → entry multiple compressed by ~50% of premium
  to cycle avg, or pass.
- **Peak multiple only** → 25% haircut; walk the exit multiple
  assumption.
- **Peak EBITDA only** → verify recent EBITDA is durable, not
  cyclical.
- **Neither** → cycle timing not a pricing concern.

---

## 141. 100-day plan from packet (`one_hundred_day_plan_from_packet.py`)

**Partner statement:** "When I read the packet I already have the
100-day plan sketched. The packet SHOULD tell me what to do in
the first 100 days."

14 conditional rules + 2 always-on (board cadence, KPI
instrumentation). Each rule fires when a specific packet signal
is present:

- **FCA exposure** → engage specialized counsel, week 1.
- **No MIP finalized** → finalize grants, week 2.
- **Denial ≥ 10%** → RCM denial-reduction blitz, week 3.
- **Weak management OR tenure < 2y OR role gaps** → named search,
  week 4.
- **Leverage ≥ 6x, covenanted** → weekly covenant monitor, week 4.
- **CMS survey issues** → remediation plan, week 5.
- **Integration < 80%** → integration sprint, week 6.
- **DAR ≥ 55** → DAR reduction program, week 6.
- **CDI not in place** → stand-up, week 8.
- **Top payer ≥ 40%** → contingency plan, week 9.
- **≥ 3 ERPs** → consolidation charter, week 10.
- **Commercial < 50%** → payer strategy review, week 12.

Cap at 15 actions (partner discipline — more is a wish list).
Sorted by latest-start week. Expected $ impact quantified where
calculable (denial blitz $2M, DAR $1M, CDI $1.5M).

Partner note:

- < 6 actions → "thin plan; confirm packet is complete."
- 6-11 → "standard plan, $X quantified impact."
- ≥ 12 → "aggressive; ensure CEO can execute 12+ simultaneous
  workstreams."

**Worked example:** a deal with denials at 12%, weak management,
covenant-tight structure, and no MIP produces a week-sorted
list of ~8 actions the partner can hand to the deal team on the
day of close.

---

## 142. Outpatient migration cascade (`outpatient_migration_cascade.py`)

Fourth canonical cascade (after RCM, payer-mix, labor). When a
hospital thesis assumes IP-to-OP procedure migration:

1. **Magnitude** — % of IP revenue in motion. > 20% in 5 years
   requires infrastructure + physician-contract changes decks
   often under-budget.
2. **OP rate differential** — OP rates typically 55-75% of IP.
   Top-line shrinks first; the "higher margin outpatient"
   narrative ignores this.
3. **Margin swap** — OP margin × rate-adjusted revenue vs IP
   margin × original revenue. Net positive only when OP margin
   differential beats the rate haircut.
4. **Capacity unlock** — freed IP capacity: if backfilled with
   higher-acuity cases (default 50% fill × 20% higher rate),
   positive. If no named demand, fixed-cost drag.
5. **Site-neutral risk** — HOPD share × site-neutral haircut
   (22%) × OP margin. Bear-case assumes partial realization.

Partner note:

- Net EBITDA < 0 → "revenue loss from lower OP rates dominates;
  backfill and margin swap don't close the gap."
- Net positive but ≥ 50% from HOPD exposure → "regulatory bet,
  not operational one."
- Net positive with low HOPD share → "validate backfill
  assumption and site-neutral exposure."

---

## 143. Quality of diligence scorer (`quality_of_diligence_scorer.py`)

**Partner statement:** "Before I recommend invest or pass, I
audit my OWN team's work. The failure mode is going to IC with
a thin book and learning in the room."

Six dimensions, each with a required checklist:

- **Financial** (6 items) — QofE, NWC peg, recurring vs one-time
  split, 3yr capex, debt schedule, capital plan.
- **Commercial** (5) — payer map, top-10 contract review,
  competitive map, customer references, pricing power.
- **Clinical** (5) — quality metrics, CMS history, physician
  interviews, coding audit, RAC history.
- **Operational** (5) — IT inventory, KPI dashboards,
  integration playbook, labor costs, staffing pipeline.
- **Legal** (6) — QoL, FCA, Stark/AKS, litigation, CoC consents,
  environmental.
- **Management** (5) — CEO/CFO refs, MIP finalized, succession,
  board charter.

**IC-ready = every dimension ≥ 80%.** Not an average — a floor.
The weakest dimension is always named.

Partner note:

- IC-ready → "weakest dimension still is X at Y%."
- Near-ready → "close gaps on X: missing items Y, Z."
- Weakest < 50% → "NOT IC-ready; decline to recommend; pull IC
  back 2-3 weeks."

---

## 144. Management first sit-down (`management_first_sitdown.py`)

**Partner statement:** "First post-LOI session is not 'tell me
about yourself.' I walk in with an agenda calibrated to what the
packet already told me."

Three blocks:

- **Confirm the thesis** (15-25 min) — "walk me through pillars
  AS YOU SEE THEM, not the banker's version." Tests ownership
  vs recital.
- **Name the risks** (10-30 min) — "what keeps you up at night?"
  Specific probes for denial rate, top-payer concentration, FCA
  exposure, historical-pattern matches.
- **Sign up for outcomes** (15-25 min) — "5 metrics I hold you
  to with numbers"; MIP structure commitments; team-gap hiring
  plan if management score is weak.

Each item ships with a **probe-if-canned** note — the follow-up
when management gives the CIM answer. Partners don't take
rehearsed responses; they push past them.

Partner note when any block is missing → "sit-down is
incomplete; extend the meeting." Thesis + risks + outcomes is
not negotiable.

---

## 145. IC decision synthesizer (`ic_decision_synthesizer.py`)

**Partner statement:** "Give me one recommendation and three
reasons. That's IC."

This is the crown-jewel cross-module module. It consumes a
bundle of pre-computed signals from the other brain modules
(scorecard, QoD, bear case, margin of safety, face-plausibility,
partner-trap, historical-failure, coherence, cross-module insights,
cycle timing) and synthesizes:

- **Recommendation** — INVEST / DILIGENCE MORE / PASS.
- **Three reasons FOR** — drawn from strongest positives.
- **Three flip-the-call signals** — what would flip it.
- **Must-close before IC** — IC-blocking gaps.
- **Chair opening line** — the partner's actual first sentence
  at IC.

Hard rules override score:

- Any face-level implausibility → PASS (math doesn't work).
- 2+ historical pattern matches → PASS ("this is X with a
  different logo").
- 2+ scorecard fails → PASS.
- Bear MOIC < 1.0x AND combined-shock MOIC < 1.0x → PASS.
- QoD not IC-ready → DILIGENCE MORE.
- Score ≥ 72 with zero scorecard fails → INVEST.
- Score ≤ 40 → PASS.
- Otherwise → DILIGENCE MORE.

**Worked example:** an Envision-pattern staffing deal with heavy
OON + thin QoD produces PASS with the chair line "this is
envision_surprise_billing_2023 with a different logo." The
partner reads the recommendation + one sentence and knows how
IC will go.

---

## 146. Healthcare regulatory calendar (`healthcare_regulatory_calendar.py`)

**Partner statement:** "What's happening in 2026-2028 that a
deal in this subsector needs to model?"

12 named events (partner-approximated, refreshed against actual
docket before IC):

- **2026 Q1** — physician fee schedule cut (-2.8%, affects
  specialty practice / staffing / ASC).
- **2026 Q1** — sequestration 2% baseline (all subsectors);
  4% extension risk 2027-2028.
- **2026 Q3** — site-neutral HOPD phase 2 (-6% impact on
  affected services).
- **2026 Q1** — home-health PDGM recalibration (-3.5% on routine).
- **2026 Q1** — MA risk-adjustment v28 (-1.5% pass-through).
- **2026 Q2** — NSA IDR cycle (-4%, staffing only).
- **2026 Q2** — state Medicaid redetermination wave 2 (-2.5%
  safety-net).
- **2026 Q1** — ASC covered-procedures expansion (**+5% tailwind**).
- **2026 Q2** — OIG / AKS enforcement bump (litigation exposure,
  not rate).
- **2027 Q1** — 340B program integrity rule (-2%).
- **2027 Q3** — MedPAC hospital IPPS advisory (-1.5%).
- **2028 Q1** — commercial rate transparency enforcement (-1%).

`events_for_deal(subsector, hold_start, hold_years)` returns the
events landing mid-hold, sorted by date, with cumulative
revenue-impact % and partner note:

- Cumulative ≤ -10% → "regulatory-headwind subsector; don't rely
  on rate growth."
- -5 to -10% → "model flat real rates in base case."
- Net tailwind → "confirm ramp assumptions against regulatory
  timeline."

---

## 147. Deal smell detectors (`deal_smell_detectors.py`)

**Partner statement:** "I've seen this before, and I didn't
like it."

Different from historical_failure_library (named/dated real
failures) and partner_traps_library (specific pitch claims).
These are SMELLS — combined-signal patterns partners recognize
on sight. Each prints in partner-voice shorthand.

Nine smells currently wired:

- **rollup_running_out_of_boltons** — ≥ 5 acq/yr + thin pipeline
  + platform ≥ 3y.
- **denials_paper_over_payer_concentration** — denial ≥ 9%,
  rising, + top payer ≥ 35%.
- **founder_wants_out** — founder CEO + (age 60+ OR retiring
  flag).
- **ebitda_pulled_forward** — recent EBITDA jump ≥ 15% + close
  deadline ≤ 8 weeks + pro-forma ≥ 10%.
- **covenant_already_tight** — leverage ≥ 6.0x + headroom ≤ 10%.
- **clinician_flight_in_progress** — ≥ 15% of headcount departed
  in last 12 months.
- **organic_declining_under_rollup** — negative organic + strong
  acquisition growth (AdaptHealth pattern).
- **management_churn** — ≥ 3 C-suite transitions in 2 years.
- **quality_compliance_canary** — CMS survey issues + ≥ 2
  litigation items.

Partner note:

- ≥ 2 high smells → "'something isn't right' deal; pass unless
  specific remediation for each is on the table."
- 1 high → "push IC back and diligence the specific signal."
- 0 high → "passes the gut-check layer."

---

## 148. Letter to seller (`letter_to_seller.py`)

**Partner statement:** "The banker runs 5 processes a year and
remembers who was dismissive. Even when we pass, we write a good
letter."

Three letter variants keyed off the IC recommendation:

- **PASS** — opens with thanks, names what we liked, states the
  specific reasons we can't move forward, optionally frames the
  price gap (if > 10%), offers to revisit if circumstances
  change.
- **INVEST** — short, direct; names closing-week conditions.
- **DILIGENCE MORE** — asks for specific additional sessions in
  the next 10-14 days.

Tone discipline: no platitudes. A pass letter should name real
reasons (payer concentration, site-neutral exposure, regulatory
calendar) not "timing" or "priorities" — bankers know when
they're being brushed off.

---

## 149. Synergy credibility scorer (`synergy_credibility_scorer.py`)

**Partner statement:** "Are these real synergies or aspirational?
Signed actions are real; management estimates are not."

Base realization % by category (partner-approximated):

- **procurement_gpo** 0.85 — real; GPO rebates are contractual.
- **shared_services** 0.70 — if owned.
- **back_office_consolidation** 0.60 — slow but real.
- **contract_renegotiation** 0.55 — depends on leverage.
- **rcm_denial_reduction** 0.50 — needs a CDI program.
- **labor_productivity** 0.45.
- **cross_sell_revenue** 0.30 — hardest to hit.
- **revenue_mix_shift** 0.25.
- **network_effects** 0.15 — this phrase is a red flag on its own.
- **cultural_alignment** 0.10 — not a synergy, a platitude.

Credibility modifiers: +20 signed contract; +15 action already
executed; +10 benchmark reference; +5 named owner. Year-3+
timing: -10 to -20. Source: +10 signed, +5 third-party,
-5 management estimate.

Realization = base × (credibility / 75), clamped to [0.40×,
1.25×] of base and capped at 95%. Partner-prudent credit =
claimed × realization.

Partner note:

- Total synergies ≥ 30% of entry EBITDA → "huge thesis share;
  diligence the top 3 by owner, not the list."
- Overall realization < 40% → "aspirational, not operational;
  underwrite heavily haircut."
- ≥ 70% → "strong; signed/executed actions backing claims."

---

## 150. Process stopwatch (`process_stopwatch.py`)

**Partner statement:** "The banker's clock tells you things the
CIM doesn't."

Seven signal detectors:

- **tight_close_clock** (high) — ≤ 4 weeks LOI-to-close is
  designed to prevent deep diligence.
- **bidder_collapse** (high) — round 2 has ≤ 25% of round 1
  bidders. Specific finding is spreading through the group.
- **process_relaunched** (high) — seller re-engaging prior
  passers means first process failed.
- **multiple_walks** (medium) — ≥ 3 bidders walked mid-process.
  Call a peer partner — what did they find?
- **repriced_during_process** (medium) — price reset downward
  pre-close. Use as leverage; don't anchor on original ask.
- **banker_rigid_on_price** (medium) — aggressive price defense
  usually means weak comps and no natural clearing price.
- **diligence_silence** (medium) — seller/management quiet
  during diligence is often bad news.

Partner note:

- ≥ 2 high signals → "clock is telling you to be careful;
  press banker for what's actually happening in the room."
- 1 high → "investigate before moving forward."
- Medium only → "fold into diligence questions."
- Clean → "process tempo reads normal."

---

## 151. Red-flag escalation triage (`red_flag_escalation_triage.py`)

**Partner statement:** "Not every red flag needs me at 7am. I'll
take the FCA; you handle the denial rate. Triage is about WHO
acts, not severity."

Four tiers:

- **partner_immediate (24h)** — legal, regulatory, reputational
  categories (any severity) + clinical-safety incidents (high).
  Reputational/fiduciary authority sits with partner.
- **partner_this_week (72h)** — high-severity financial or
  operational issues — block 30 min in the deal-team meeting.
- **associate (168h)** — medium severity; diligence-tracker
  item.
- **informational (336h)** — low severity; note, no action.

Partner note escalates:

- ≥ 2 partner-immediate → "not queue items; partner should be
  on the phone with counsel and CMO advisor today."
- 1 partner-immediate → "escalate today; don't wait for the
  deal-team meeting."
- 2+ partner-this-week → "block partner time at next deal-team
  meeting."

This replaces the instinct to "escalate everything" with
partner-discipline: triage by who has authority, not by how
scary the word in the finding is.

---

## 152. Quarterly operating review (`quarterly_operating_review.py`)

**Partner statement:** "Generic 'how are things going' is a
waste of the 60 minutes. A disciplined QoR is four blocks of
15 minutes with a specific partner-focus per block."

Four blocks:

1. **Numbers (15 min)** — EBITDA vs plan, revenue vs plan,
   denial-rate trend, DAR, cash runway, covenant headroom.
   Partner-focus shifts: EBITDA miss → pushes hard on named
   driver; denial rising → RCM deep-dive; covenant tight →
   13-week cash walk.
2. **Thesis progress (15 min)** — levers on-track vs behind;
   bolt-on integration status. Focus escalates: 2+ behind =
   demand named recovery plan with owner + date.
3. **People + operating rhythm (15 min)** — CEO search status
   (if open), departures, retention tracker, MIP vesting.
4. **Forward-look + asks (15 min)** — next-90-day priorities,
   CEO's asks of the board, next-quarter KPI targets. In hold
   year 3+: exit readiness + banker-prep items.

Partner note escalates:

- EBITDA < -10% → "intervention, not review; extend numbers
  block."
- 2+ levers behind OR open CEO search → "multiple items need
  partner attention."
- Outperforming ≥ 5% → "pull forward levers or assess early
  exit readiness."

---

## 153. Value creation plan generator (`value_creation_plan_generator.py`)

**Partner statement:** "Give me the 3-year VCP on one page —
here's how we get from $X to $Y."

Eight conditional initiatives keyed off packet signals:

- RCM denial-reduction (~3% EBITDA lift, year 1-2).
- CDI + CMI uplift (~2%, year 1-2).
- M&A bolt-on pipeline (~30% from 3-4 bolt-ons, year 1-5).
- Payer renegotiation (~4%, year 1-3).
- Site footprint optimization (~2.5%, year 1-3).
- Labor productivity + scheduling (~3%, year 2-3).
- Procurement / GPO (~1.5%, year 1-2).
- Technology platform enablement (~2%, year 1-4).

Each initiative has year-starts, year-of-impact, expected $
impact, named owner, and dependency list.

Execution risks fire on:

- **Shared dependencies** blocking 2+ initiatives
  (single-point-of-failure).
- **Management capacity < 55** with 5+ concurrent initiatives
  ("team cannot execute in parallel").
- **Capex bottleneck** when budget < $2M vs tech/ops-heavy plan.

Partner note:

- Plan closes < 80% of bridge → "doesn't reach target; either
  target wrong or plan incomplete."
- Plan overshoots > 30% → "optimistic; partners haircut 20-30%."
- Within ±30% → "reasonable fit; execution risks are what matter
  now."

---

## 154. Exit timing signal tracker (`exit_timing_signal_tracker.py`)

**Partner statement:** "Exit readiness is not a year-5 question.
Sell into strength, not because the clock says hold year 5."

Seven signals tracked each quarter:

1. **EBITDA 6mo trend** — green/yellow/red (up/stable/down).
2. **Thesis lever completion** — ≥ 70% green; 40-70% yellow.
3. **Credit markets** — easing/stable/tightening.
4. **Peer multiples vs entry** — ≥ +5% green; -5% to +5% yellow.
5. **Management stability** — stable + CEO committed = green.
6. **QofE clean quarters** — ≥ 8 green; 4-7 yellow; < 4 red.
7. **NAV posture** — above cost + no recent write-downs = green.

Recommended action:

- **start_banker_rfp** — ≥ 5 greens AND 0 reds.
- **dry_run_sale** — ≥ 3 greens AND 0 reds.
- **wait** — any reds, or < 3 greens.

Partner note names blockers explicitly. "Sell into strength, not
clock discipline" — the module forces the timing question away
from calendar-driven exit prep.

---

## 155. Buyer-type fit analyzer (`buyer_type_fit_analyzer.py`)

**Partner statement:** "Given THIS asset's profile, which
SPECIFIC buyer type should the banker target first?"

Eight buyer types scored 0-100 with named targets:

- **strategic_health_system** — HCA, Tenet, CommonSpirit,
  Ascension, AdventHealth. Best for outpatient / home health /
  ASC with defensible geography.
- **strategic_payer_led** — Optum, Carelon, CenterWell, Aetna,
  Evernorth. Best for VBC-ready books + national footprint.
- **specialty_consolidator** — USOC, US Dermatology, Heartland
  Dental. Best for roll-up-ready specialty practices.
- **larger_sponsor** — KKR, Blackstone, Bain, Carlyle, TPG. Best
  for platform-ready growth assets ≥ $75M EBITDA.
- **peer_sponsor** — New Mountain, Silversmith, Nordic, Welsh
  Carson. Fallback if strategic path thin.
- **ipo** — minimum $400M revenue AND $80M EBITDA AND ≥ 15%
  organic growth for credibility.
- **continuation_vehicle** — ICG, Pantheon, Lexington, Coller.
  When GP conviction + named runway.
- **industry_passive** — MPT, Sabra, Omega, Welltower, Ventas.
  For real-estate-heavy mixes.

Top + runner-up are named in the partner note. The point is not
a single winner — banker books include multiple buyer types in
round 2 for depth.

---

## 156. Add-on fit scorer (`add_on_fit_scorer.py`)

**Partner statement:** "Banker just walked in a bolt-on. Does
this specific target fit THIS platform?"

Four scored dimensions (weighted):

- **Strategic (30%)** — extends geography / service line /
  scale. Low growth target flagged as platform CAGR dilution.
- **Financial (30%)** — multiple arbitrage (platform mark −
  target multiple); synergy % of target EBITDA; size (<$2M
  EBITDA = team-bandwidth-cost > return).
- **Integration (25%)** — ERP compatibility, physician
  alignment, expected months, and whether the platform already
  has ≥ 3 open integrations.
- **Execution (15%)** — platform management bandwidth, capex
  headroom, close timeline.

Recommendation:

- **proceed** — overall ≥ 70 AND no dimension < 40.
- **re_evaluate** — overall 55-69; specific named concerns.
- **pass** — overall < 55.

Top 3 concerns named explicitly from across dimensions. Partner
reads "proceed / re-evaluate / pass" + 3 bullets; everything else
is supporting.

---

## 157. Concentration risk multi-dim (`concentration_risk_multidim.py`)

**Partner statement:** "Show me the six concentration numbers
side by side, and flag which ones are a problem."

Six dimensions (ten metrics), same threshold logic:

- **Customer** — top-1 + top-5.
- **Site / location** — top-1 + top-5.
- **Payer** — top-1.
- **Provider** (physician / clinician) — top-1 + top-5.
- **Service line / product** — top-1 EBITDA share.
- **Geography** — top state + top MSA.

Severity thresholds:

- ≥ 50% → **high** ("underwriting constraint — re-underwrite
  assuming 20% of that revenue walks").
- 30-49% → **medium** (diligence flag; get contract terms,
  escalator, renewal date).
- 15-29% → **low** (noted but manageable).
- < 15% → not flagged.

Partner note:

- ≥ 2 high → "structural issue; re-underwrite with each
  concentrated dim stressed."
- 1 high → "single-dim concentration; specific mitigation
  required before IC."
- Medium only → "standard diligence questions apply."
- All low → "diversified across all six dimensions."

---

## 158. Post-close surprises log (`post_close_surprises_log.py`)

**Partner statement:** "I track diligence miss rate
religiously. If we miss 15%+ of post-close surprises, our
process has a systematic gap — and the fix is in the template,
not the individual deal."

Each surprise logged with:

- Category (operational / clinical / legal / financial /
  regulatory / cultural / market).
- Description.
- Dollar impact on EBITDA (negative = hit).
- Was it known at close (bool) + flagged severity + actual
  severity post-close.

Rolling analysis:

- Overall miss rate (missed / total) + missed EBITDA bleed.
- Per-category stats (miss rate, avg $ impact of missed items).
- Worst category named.

Partner commentary per category:

- Miss rate ≥ 30% → "systematic gap — fix template before next
  deal in this subsector."
- ≥ 15% → "above tolerance; review template."
- < 15% → "within norms."
- Missed avg impact < -$2M → "bleed category — portfolio dollars
  bleed here."

This is the partner feedback loop. Deal-by-deal the numbers look
small; portfolio-by-portfolio they tell you which category of
diligence always burns you.

---

## 159. Regional wage inflation overlay (`regional_wage_inflation_overlay.py`)

**Partner statement:** "A single wage-inflation rate is a fiction.
NYC, SF, LA clinicians face different structural inflation than
Tennessee or the Carolinas."

Five-tier regional framework (partner-approximated 2026-2028):

- **coastal_tier1** (NYC, SF, LA, Boston, Seattle, DC) — base
  premium 1.30x, inflation 5.5%/yr.
- **coastal_tier2** (Miami, San Diego, Philadelphia) — 1.15x,
  4.5%.
- **major_inland** (Chicago, Denver, Atlanta, Dallas) — 1.05x,
  4.0%.
- **mid_market** (Raleigh, Nashville, Minneapolis) — 0.95x, 3.5%.
- **rural_tier3** (non-metro) — 0.85x, 2.8%.

Takes site-level footprint, computes revenue-weighted inflation,
and expresses the gap vs the model's single-rate assumption as
a 3-year EBITDA drag.

Partner note:

- Drag ≥ 10% of EBITDA → "structural underwrite error; fix model
  before IC."
- 3-10% → "material but manageable; rebuild labor line with
  regional split."
- < 3% gap → "immaterial; note in underwrite."
- Negative delta → "model is conservative; no adjustment."

**Worked example:** a $20M EBITDA asset with 900 clinicians
concentrated in NYC + SF under-models wage inflation by ~2.5pp.
The resulting 3-year labor-cost drag is ~30% of entry EBITDA —
structural, not incidental.

---

## 160. RAC audit exposure estimator (`rac_audit_exposure_estimator.py`)

**Partner statement:** "Partners in healthcare PE are terrified of
RAC and OIG audits because the dollars are disproportionate and
the audits are retroactive. Give me a number."

Base RAC hit rate 1.5% of 3-year Medicare FFS revenue. Adjusted
by signals:

- Historical denial rate ≥ 12% → +1.0pp; 8-12% → +0.3pp.
- Claimed CMI uplift ≥ 10% → +1.5pp; 5-10% → +0.8pp.
- No CDI program → +0.5pp.
- Aggressive coding flags (from prior audits) → +0.5pp each, up to 5.
- Open FCA exposure → +2.5pp.
- Rate capped at 15%.

Exposed revenue = Medicare FFS revenue × 3 (typical look-back).
Expected loss: mid = exposed × rate; low = 50% of mid; high =
200% of mid.

Partner note:

- Mid vs base EBITDA ≥ 30% → "IC-blocking; forensic billing
  diligence non-negotiable; partner should not approve without
  purchase-price adjustment."
- 10-30% → "material; structure earn-out or indemnity for audit
  window."
- 3-10% → "modest; standard R&W with insurance."
- < 3% → "immaterial."

---

## 161. IRR decay curve (`irr_decay_curve.py`)

**Partner statement:** "Someone's suggesting we extend the hold.
Does IRR still clear the hurdle next year?"

Given projected EBITDA by year + exit multiple + entry equity +
debt + hurdle IRR, returns a per-year exit MOIC / IRR table and
identifies:

- **IRR peak year** — usually earlier than MOIC peak.
- **MOIC peak year** — usually later than IRR peak.
- **Last year above hurdle** — where IRR still clears the
  partner's minimum.

Partner note:

- Never clears hurdle → "thesis needs multiple expansion or
  better EBITDA growth, not longer hold."
- Clears throughout horizon → "trajectory supports extending if
  needed."
- Clears partially → "extending past year N destroys IRR even
  if MOIC keeps growing; exit at year N unless DPI timing
  dictates earlier."

This is the math partner runs every time someone suggests
"another year to let the thesis play out." Sometimes the answer
is yes; often the math says no.

---

## 162. Competing deals ranker (`competing_deals_ranker.py`)

**Partner statement:** "I have three deals going at once. Which
wins the partnership's time and capital?"

Composite score 0-100 per deal from 5 weighted components:

- **Return (30%)** — base IRR × 250, capped.
- **Quality (25%)** — 40% coherence + 30% pricing power + 30%
  management.
- **Downside (20%)** — bear MOIC: 1.0x=40, 2.0x=100, 0.5x=0.
- **Fit (15%)** — +20 if fund PME boost; -15 per scorecard
  fail (-40 if 2+).
- **Timing (10%)** — time-sensitivity; execution burden drag.

Partner note:

- Gap ≥ 15 → "clear winner — partner's time goes here."
- Gap 5-15 → "close enough that flipped downside or timing
  could shift the call."
- Gap < 5 → "effective tie; use execution-burden tiebreaker —
  pick the one the ops-partner bench is ready to own."

Per-deal commentary names specific drivers ("return is compelling,
downside is protected, time-sensitive").

---

## 163. Medicaid state exposure map (`medicaid_state_exposure_map.py`)

**Partner statement:** "Medicaid is state-by-state. National-rate
overlays miss the leverage/exposure picture."

Four risk tiers (partner-approximated 2026-2028):

- **high_cut_risk (5% bear)** — non-expansion + budget pressure:
  TX, FL, GA, TN, MS, AL, SC, MO, KS, WY.
- **waiver_risk (4% bear)** — 1115 waiver docket: AR, KY, ND, MT.
- **medium_cut_risk (2.5% bear)** — AZ, OH, IN, NC, IA, WI, OK,
  LA, VA.
- **low_cut_risk (1% bear)** — expansion states with backfill:
  NY, CA, MA, WA, OR, MN, CO, VT, MD, NJ, CT, IL, RI, HI, NM,
  NV, DE, PA, MI, NH.

Bear EBITDA impact = Medicaid revenue × tier bear cut % ×
contribution margin (default 0.45).

Partner note:

- High-risk states ≥ 50% of Medicaid revenue → "underwrite with
  full state-risk bear drag."
- 25-50% → "monitor state budget cycles."
- < 25% → "manageable."
- Concentrated in low-risk → "state risk is not a material
  lever."

Unknown states default to medium_cut_risk.

**Worked example:** a deal with $100M Medicaid split 60% TX +
40% NY has 54% of Medicaid in high-cut-risk states; the bear-
case EBITDA drag is ~$1.55M. Same $100M in NY + CA would be
$0.45M — one-third the risk.

---

## 164. Earn-out design advisor (`earnout_design_advisor.py`)

**Partner statement:** "Earn-outs are for measurable disagreements
in 12-36 months. Not every price gap deserves one."

Driver classification:

- **Good drivers** — `signed_commercial_contract`,
  `ebitda_run_rate_milestone`, `bolton_close_count`,
  `regulatory_licensure`, `site_expansion_count`. Measurable
  outcomes that resolve the dispute.
- **Bad drivers** — `generic_ebitda_threshold` (gameable),
  `quality_metric` (subjective), `management_subjective`,
  `market_share_claim`. Too easy to dispute.

Recommendation logic:

- Bad driver → **do NOT propose earn-out**; cut headline price
  80% of gap instead, share upside through MIP.
- Unknown driver → propose at 50% of gap; negotiate specific
  measurable language.
- Good driver:
  - Seller flinching (high buyer skepticism, low seller
    conviction) → 90% of gap deferred.
  - Both confident but disagreeing → 60% of gap (classic
    earn-out zone).
  - Modest disagreement → 70% of gap.

Structure notes:

- Physician-owner deals add retention bonus component.
- Binary outcomes (licensure, signed contracts) → cliff-vest,
  not pro-rata.

---

## 165. Sponsor reputation tracker (`sponsor_reputation_tracker.py`)

**Partner statement:** "Partners keep a mental file on other
sponsors. When I see them bidding, I want to know if they
over-pay, if they strip-mine, or if they're a clean
counterparty."

Five dimensions scored 0-100 per sponsor:

- **pricing_discipline** — do they pay rational multiples?
- **operating_value_add** — do they improve companies?
- **exit_track_record** — do they generate clean LP returns?
- **reputational_profile** — external regard.
- **cultural_fit_with_management** — do CEOs enjoy working with
  them?

Assessment is context-specific:

- **competing_bidder** — if pricing discipline < 65 → "expect
  aggressive bidding, don't anchor"; if ≥ 80 → "if they pass,
  listen."
- **co_investor** — value-add ≥ 80 + mgmt fit ≥ 75 → "strong
  partner"; value-add < 60 → "passive-capital; doesn't add to
  the operating agenda."
- **exit_buyer** — reputation ≥ 80 + overall ≥ 75 → "natural
  exit-buyer candidate; quality counterparty."

Inaugural 11-sponsor book (illustrative, partner-refreshed):

- Mega-funds: KKR, Blackstone, Bain Capital, Carlyle, TPG.
- Healthcare specialists: New Mountain, Welsh Carson,
  Silversmith.
- Mixed: Leonard Green (Prospect Medical cautionary tale),
  Cerberus (Steward legacy), Apollo.

---

## 166. Debt capacity sizer (`debt_capacity_sizer.py`)

**Partner statement:** "Model says 6.5x. Let's see what the
min-of-three-constraints says."

Three stacked constraints (debt = min):

1. **Coverage** — stressed EBITDA / (debt × rate) ≥ coverage
   hurdle (default 2.5x at 15% stress haircut).
2. **FCF** — after-tax (EBITDA - maintenance capex) / (debt ×
   rate) ≥ hurdle (default 1.15x).
3. **Cycle discipline** — neutral subsector leverage ± phase
   adjustment (early_expansion +0.5, mid 0, peak -0.75,
   contraction +0.5), + 0.5x if covenant-lite available.

Neutral leverage by subsector (partner-approximated):

- Hospital 5.0x, safety_net_hospital 4.0x.
- Specialty practice 6.0x, outpatient ASC 6.5x.
- Home health 5.5x, DME 5.5x.
- Physician staffing 4.5x.

Partner note:

- < 3.0x recommended → "thin — either seller's model is over-
  levered or deal is less attractive than it looks."
- Cycle binds → "discipline holds even though coverage / FCF
  could support more."
- FCF binds → "tight cash flow after capex + tax; consider
  lower leverage or covenant-lite."
- Coverage binds → "partner-prudent cap at stress hurdle."

---

## 167. Operating partner fit matrix (`operating_partner_fit_matrix.py`)

**Partner statement:** "Who do I put on the board of this one?
Not every ops partner fits every CEO or every archetype."

Six ops-partner archetypes scored by deal profile:

- **turnaround** — declining EBITDA / open ops issues / weak
  mgmt score. Drives cost-out and operational rigor.
- **scaler** — founder-led businesses scaling $50M → $200M;
  systems, processes, team building.
- **healthcare_specialist** — clinical / regulatory / RCM depth;
  essential for payer-mix and coding work.
- **mna_integrator** — integration PMO; essential when M&A
  pipeline is active.
- **exit_specialist** — hold year 3+; polishes systems, builds
  banker story.
- **founder_coach** — low-ego senior coach for first-time-with-
  PE founder CEOs.

Scoring uses deal archetype, CEO type, hold quarter, EBITDA
trend, management score, clinical complexity, and M&A pipeline.

Partner note:

- Top pick with strong score → use as primary.
- Close call (≤ 10 gap) → primary + advisory from runner-up.
- Top score < 50 → "bench not purpose-built for this deal;
  consider external recruitment."

---

## 168. Reverse diligence checklist (`reverse_diligence_checklist.py`)

**Partner statement:** "If a buyer's QofE team arrived tomorrow,
what would come out in the wash?" Partners run reverse diligence
12-18 months before sale.

Items grouped by category:

- **kill_deal** — buyer walks. Open FCA, material litigation.
  Close now or plan sale around them.
- **price_haircut** — lets buyer reprice. Pro-forma ≥ 15%
  addbacks, DAR ≥ 55, denial rate ≥ 10%, top-payer ≥ 40%,
  incomplete integration ≥ 20%, CMS survey issues. Fix 9-12
  months pre-sale.
- **discovery_risk** — might or might not come out. Aggressive
  coding history, contract renewal overhang. Fix if possible.
- **housekeeping** — MIP vesting cleanup, data-room audit.
  Tidy in last 6 months.

Always-on: data-room dry-run 3-4 months pre-sale.

Partner note:

- ≥ 1 kill-deal → "sale cannot proceed; push sale date or
  close now."
- ≥ 3 haircut → "fix each; each fix is 2-3x ROI vs bid
  reduction."
- Clean book → "only housekeeping in last 6 months."

---

## 169. Management forecast reliability (`management_forecast_reliability.py`)

**Partner statement:** "Before I believe this forecast, show me
the last four forecasts you made."

Analyzes prior forecast-vs-actual pairs and returns:

- **Status per year** — beat (> +5%), at_plan (±5%), miss (< -5%).
- **Reliability score 0-100** — starts 50; +15 per at-plan; +10
  per beat; -20 per miss; -10 for high variance range; -15 for
  3+ consecutive misses.
- **Recommended haircut** on the current forecast based on miss
  pattern.

Partner note patterns:

- Miss rate ≥ 50% → "do NOT underwrite to their base case;
  haircut by X%."
- Beat rate ≥ 75% and zero misses → "sandbagging (good buyer
  signal) — underwrite at forecast, don't pay for upside."
- Hit rate ≥ 60% → "reliable forecaster; base case is
  believable."
- Mixed high-variance → "don't chase the best year."

---

## 170. Working capital peg negotiator (`working_capital_peg_negotiator.py`)

**Partner statement:** "The NWC peg is dollar-for-dollar of
purchase price. Under-negotiate and the seller just moved $5M."

Methodology selection:

- Default: **trailing_12m_avg**.
- Material one-time NWC items → **normalized_trailing_12m**
  (strip out one-timers).
- Seasonal business → **median_of_quarterly** (smooths
  seasonality).

Partner always adds **2% closing-period buffer** above the
chosen methodology figure to account for NWC build between
sign and close.

Partner note:

- Partner peg ≥ 10% above seller → "seller under-weighted
  normalized WC; this is real price-paid money."
- Seller peg > partner (unusual) → "seller building cushion
  for adjustment at close; verify methodology."
- Near-tie → "rounding band; not a material negotiation item."

---

## 171. Management rollover equity (`management_rollover_equity_designer.py`)

**Partner statement:** "Rollover equity is the clearest signal
of seller conviction. 2% rollover means they're taking the money
and running; 25% means they believe the thesis."

Target ranges (partner-approximated):

- **Young founder (< 55), growth thesis:** 20-30%.
- **Young founder, mature business:** 15-25%.
- **Founder 55-65:** 10-20%.
- **Founder ≥ 65 or retiring:** 5-10% (respect the exit).
- **Sponsor-backed CEO joining newco:** 15-25%.
- **Turnaround:** 5-15%.
- **Distressed:** 3-8% (focus alignment on cash retention + MIP).

Alignment grades:

- Proposed ≥ upper target → **strong** ("clear conviction
  signal").
- Proposed in range → **adequate** ("partner comfort").
- Proposed < lower target → **thin** ("skin-in-game reduced;
  negotiate up or lean on MIP").
- Distressed deal with thin rollover → "expected; focus
  elsewhere."

**Worked example:** a 45-year-old founder CEO getting $50M of
proceeds proposing 15% rollover is thin (target 20-30%) — partner
negotiates up or structures a larger MIP pool to fill the
alignment gap.

---

## 172. Reference check framework (`reference_check_framework.py`)

**Partner statement:** "Generic reference calls miss the signal.
Who you call depends on what you're trying to verify, and what
you ask them depends on the relationship."

Role-specific relationship groups (must-call vs should-call):

**CEO:**

- **Board member (must)** — "describe a time the company was
  off plan; how did the CEO respond?" "Would you back this CEO
  in a new company?" Anything short of clear yes is a flag.
- **Ex-direct report (must)** — "who are the top 3 people this
  CEO has hired; where are they now?" "What would you change?"
  Silence = scripted; specific critique = authentic.
- **Peer CEO (should)** — "have you co-invested or would you?"
  Highest-trust industry signal.
- **Customer / payer (should)** — "when they made a commitment,
  did they follow through?"

**CFO:**

- **Auditor (must)** — "describe a policy choice; escalations
  above this CFO?" Auditors see the seam.
- **Bank syndicate lead (must)** — "did CFO meet forecast in
  covenant periods? Was the monthly package on time and
  accurate?" Banks see the real trend before the board does.
- **Ex-direct report (should)** — "did the CFO change their
  mind based on analyst work?"
- **CEO/CFO peer (should)** — "when you presented together, who
  led?"

**Other roles (COO / CMO / etc.):** ex-boss + ex-direct report
with core questions ("would you rehire?", "how did they handle
disagreement?").

Each question ships with a **listen_for** note — what signal
the partner is actually trying to pick up.

---

## 173. LOI term sheet review (`loi_term_sheet_review.py`)

**Partner statement:** "Associates mark up everything. I know
which 5 terms actually move outcomes."

Partner-priority LOI terms (must-push vs should-push):

- **exclusivity_window** — < 45 days must-push (buyer squeeze);
  > 90 days should-push (giving up optionality).
- **breakup_fee** — > 3% of PP is punitive; push to 1-2%.
- **no_shop_clause** — absent → must-push; no partner signs
  without it.
- **financing_contingency** — hard money signing is should-push;
  partner wants flex via reverse termination fee.
- **rw_insurance_cap** — > 15% of EV is overpaying premium;
  10-15% is market.
- **mac_definition** — broad → must-push; partner wants walk-
  away right.
- **interim_covenants** — loose → must-push; seller can change
  the asset between sign and close.
- **retention_pool** — sized post-close is should-push; partner
  wants sized at close with control.
- **regulatory_approval** — hell-or-high-water commitments →
  must-push-cap; open-ended divestiture kills economics.

Partner note:

- ≥ 4 must-push → "seller-friendly across board; rebuild term
  sheet rather than redline."
- 2-3 must-push → "standard negotiation; get partner on phone
  with seller's sponsor counsel."
- 0 must-push, 0 should-push → "within market bands; no
  partner escalation."

---

## 174. Closing conditions list (`closing_conditions_list.py`)

**Partner statement:** "Signing is a commitment. Close is a
ceremony. The conditions list is where we earn our break
rights — or lose them."

Partners don't read closing-conditions lists line-by-line —
they read for three things:

1. Which conditions are *truly* in our control vs. a third
   party (regulator, lender, landlord, payer)?
2. Which conditions give us a *real* walk right vs. soft
   bring-downs the seller can cure?
3. Which conditions are time-bombs — items that could go
   wrong specifically *because* of the sign-to-close delay?

### Conditions enumerated

For healthcare-services defaults, the module emits:

- **hsr_antitrust_clearance** (regulatory, close, third-
  party, high on > $400M, walk right)
- **state_healthcare_regulatory** (CON + licensure transfers,
  close, third-party, high, walk right)
- **medicare_provider_number_transfer** (CHOW, close, third-
  party, medium, no walk — bridge via tie-in agreement)
- **payer_contract_consents** (close, third-party, medium,
  no walk — chase top 5 60 days out)
- **landlord_consents** (close, third-party, low, no walk)
- **debt_financing_funded** (close, third-party, high, no
  walk if commitment clean)
- **rw_insurance_bound** (signing, buyer, low — bind at
  sign, not close)
- **key_employee_retention_signed** (both, seller, medium,
  walk right if Key-15 drop)
- **no_material_adverse_change** (close, seller, medium,
  walk right — narrow MAC only)
- **reps_true_at_closing** (close, seller, medium, walk
  right configurable — MAE vs. material-accuracy standard)
- **clean_title_no_liens** (close, seller, low, walk right)
- **it_cyber_attestation** (close, seller, medium, no walk
  — but disclosed breach reopens price)
- **material_contracts_disclosed** (signing, seller, low)
- **officers_secretary_certificates** (close, seller, low)

### Partner-note escalation

- ≥ 3 high-risk conditions → "set outside date with 60-day
  cushion + reverse termination fee protection."
- 1-2 high-risk → "standard closing calendar with weekly
  condition tracker."
- 0 high-risk, no third-party → "clean close; associates
  can run close memo, partner reviews final."

### Packet fields that trigger

- `deal_size_m` → HSR risk tier
- `sector` → toggles healthcare-specific items
- `payer_consents_material`, `state_regulatory_required` →
  adds third-party dependent conditions
- `seller_breach_brings_walk` → controls bring-down walk
  right (reflects MAE vs. material-accuracy clause)

---

## 175. Cross-pattern digest (`cross_pattern_digest.py`)

**Partner statement:** "One trap is a negotiation. Two
traps on the same axis is a pass."

The brain already has three pattern libraries:

- **historical_failure_library** — named, dated PE
  disasters (Envision 2023, Steward REIT, U.S. Renal MA
  cap, iVcare home-health).
- **bear_book** — abstract templates (rollup integration
  failure, carveout TSA sprawl, COVID tailwind fade).
- **partner_traps_library** — seller-pitch traps
  (fix denials in 12 months, MA will make it up).

Each asks a different question. A partner doesn't read
them in isolation — they *stack*. If all three fire on the
same theme, the deal is structurally broken on that axis.

### How cross-pattern-digest reasons

1. **Unified context** — `PatternContext` carries both
   `HeuristicContext` fields (for bear_book) and packet-
   dict fields (for failures + traps). A single scan feeds
   all three libraries.
2. **Theme tagging** — each pattern is tagged with themes
   (payer, denials, medicare, leverage, operator,
   integration, regulatory, covid_tailwind, real_estate).
3. **Compound-risk detection** — when ≥ 2 libraries fire
   on the same theme, the theme is promoted to a
   `CompoundRisk` with severity = sum of contributing
   matches.
4. **Library severity weights** — failures weight 1.0
   (named historical blowup), bear 0.7, trap 0.5. Failure
   severity also scales by the pattern's
   `ebitda_destruction_pct`.

### Recommendation ladder

- **pass** — any theme lit across all 3 libraries.
- **reprice** — 2+ compound risks OR total severity ≥ 1.5.
- **diligence_more** — 1 compound risk OR severity ≥ 0.8.
- **proceed_with_mitigants** — isolated hits, no compound.
- **proceed** — no library hits.

### Worked example

A 2026 roll-up with $40M EBITDA, 6.5x leverage, 3.5-yr
hold, 400 bps/yr margin expansion, and a seller promising
12 → 5% denial reduction in 12 months:

- Bear fires `rollup_integration_failure` + `high_leverage_thin_coverage`.
- Trap fires `fix_denials_in_12_months` + `back_office_year_1_synergies`.
- Themes stack: **integration** (bear + trap), **operator**
  (bear + trap), **leverage** (bear), **denials** (trap).
- Recommendation: `reprice` or `diligence_more` depending
  on additional context.

### Packet fields that trigger

- `ebitda_m`, `leverage_multiple`, `hold_years`,
  `margin_expansion_bps_per_yr`, `covenant_headroom_pct`
- `payer_mix` (normalized; both fractions and percentages
  accepted)
- `packet_fields` dict for trap-specific inputs:
  `current_denial_rate`, `target_denial_rate`,
  `months_to_target`, `payer_contracts_renewing_next_12mo`,
  `claimed_rate_growth_pct`, `medicare_advantage_pct`,
  `regulatory_risk_material`

---

## 176. Thesis implications chain (`thesis_implications_chain.py`)

**Partner statement:** "Tell me the chain. If denials come
down, what else has to be true?"

A seller's thesis is always a single headline claim. A
partner's rebuttal is the *chain* of downstream implications
that have to hold for the headline to be real. The seller
owns the headline; the partner owns the chain.

### Chains implemented

1. **denial_reduction** — coder retention, no open coding
   disputes, DAR compresses, EBITDA gain is recurring (not
   cash release), covenant package clears the curve, exit
   multiple applies to recurring Y5 EBITDA.
2. **payer_mix_shift** — commercial payer capacity exists,
   state doesn't retaliate via DSH pullback, CMI rises
   with shift, bad-debt trend holds, phase-in modeled
   (not day-1).
3. **rollup_consolidation** — M&A pipeline signed (not
   "universe"), integration playbook tested, debt
   capacity scales, synergies net of integration cost,
   exit multiple holds despite complexity, acquired-CEO
   retention.
4. **cost_basis_compression** — no union/licensure
   triggers, contract labor target sustained, quality
   metrics hold, local wage inflation doesn't reverse.
5. **cmi_uplift** — CDI team FTE-sized, no audit
   recoupment risk, phased uplift in bridge, sustainable
   (not COVID surge).

### Status model

Each implication tagged **confirmed**, **not_addressed**,
or **contradicted** against the packet.

- Any **contradicted** link → "chain breaks here; headline
  doesn't survive."
- ≥ 2 high-risk **not_addressed** → "diligence these before
  IC; this is where the thesis lives or dies."
- All confirmed → "chain is tight; proceed."

### Worked example — denial reduction

Seller's claim: "Cut denials 700 bps in 12 months."

Partner walks the chain:

- Coder turnover 35%? → **contradicted** (high risk).
- Open payer coding disputes? → **contradicted** if flagged.
- DAR reduction trajectory? → **not_addressed** (medium).
- Year 1 cash release share 55%? → **contradicted** (high):
  the EBITDA gain isn't recurring.
- Exit EBITDA basis? → **not_addressed** (medium).

Partner note: "Chain breaks at link 4 — Year 1 is 55% cash
release. The exit multiple only applies to recurring
EBITDA; the headline is overstated by 2 turns."

### Packet fields that trigger

Each chain has its own `packet_field` hooks. Denial chain
uses: `coder_turnover_annual_pct`, `open_payer_coding_disputes`,
`dar_reduction_days_per_yr`, `year1_cash_release_share`,
`y1_leverage_on_y1_ebitda`, `exit_ebitda_basis`. Others
analogous — see module for full list.

---

## 177. Deal one-liner (`deal_one_liner.py`)

**Partner statement:** "If I can't write the verdict in one
sentence, I don't understand the deal yet."

IC decks run 60 pages. Partners write a single sentence in
the margin when they pick up the deck. That sentence is the
synthesis: recommendation + the one reason that matters.

### Synthesis precedence

The brain already has three judgment layers. The one-liner
picks the *dominant* signal using strict precedence:

1. **Face implausibility** (high severity) — "math doesn't
   work on face; pass before modeling."
2. **Broken thesis chain** — "chain breaks at <specific link>."
3. **All-three pattern compound** — "theme fires across all
   libraries; rebuild or walk."
4. **Unresolved thesis high-risk links** — "diligence these
   before IC."
5. **Compound pattern risk (≥2 libraries)** — "reprice or
   mitigate."
6. **Medium face findings** — "reprice pending specifics."
7. **Tight chain** — "invest; downstream loops closed."
8. **Single-library pattern hit** — "diligence_more."

Face beats chain beats pattern. A pass-before-modeling
finding dominates everything because the math gate dominates
all other signal.

### Worked example

Inputs:
- `face`: hospital with 22.5% EBITDA margin (implausible).
- `thesis="denial_reduction"` with `year1_cash_release_share=0.55`.

Without face: chain breaks → `pass — thesis 'denial_reduction' chain breaks at: EBITDA uplift is recurring, not cash release`.

With face: face wins → `pass — hospital_margin_impossible: 22% EBITDA margin on a hospital`.

### Packet fields that trigger

- `OneLinerInputs.face` → any `FaceInputs` (subsector,
  revenue, EBITDA, claimed IRR, etc.).
- `OneLinerInputs.pattern_ctx` → any `PatternContext` fields
  (same set that feeds cross_pattern_digest).
- `OneLinerInputs.thesis` + `thesis_packet` → same fields
  that feed walk_thesis_chain.

### Why single-sentence discipline matters

A partner who can't name the deciding issue in one sentence
has not done the diligence. The one-liner enforces this:
either you know the deal well enough to pick the dominant
signal, or the verdict should be `diligence_more`.

---

## 178. Hold-period shock schedule (`hold_period_shock_schedule.py`)

**Partner statement:** "I don't need the worst-case total.
I need the worst *year*. The covenant trips on one year's
EBITDA, not on the five-year NPV."

Existing regulatory stress modules
(`obbba_sequestration_stress`, `regulatory_stress`,
`healthcare_regulatory_calendar`) compute point-in-time
impact. What partners actually need during diligence is the
**year-by-year trajectory** of EBITDA under realistic
regulatory assumptions.

### How it reasons

1. **Probability-weighted shock severity** — each shock
   impact is weighted by landing probability (OBBBA 70%,
   sequestration 85%, site-neutral 50%, state Medicaid
   55%).
2. **Year-indexed landing schedule** — shocks land in
   specific hold years (default: OBBBA Y0, sequestration
   Y1, site-neutral Y2, state Medicaid Y3).
3. **Permanence flag** — permanent cuts (OBBBA,
   sequestration) stack; temporary shocks (not modeled in
   default schedule) would dissipate.
4. **Per-year EBITDA floor** = base − cumulative permanent
   impact.
5. **Per-year leverage** = initial debt / per-year EBITDA.
6. **Covenant trip detection** — first year where
   leverage exceeds max allowed.

### Partner-note escalation

- **Covenant trip detected** → "widen cov package or
  re-price equity."
- **Worst-year leverage ≥ 90% of ceiling** → "stress
  schedule with higher probabilities."
- **Cumulative erosion > 15% of base** → "bake into base
  case, not bear."
- Otherwise → "standard stress; proceed."

### Worked example

Hospital: $500M NPR, $75M EBITDA, 35% Medicare FFS, 15%
Medicare Advantage, 10% HOPD, 5.5x leverage, 7.0x cov max.

Year-by-year under default schedule:
- 2026: OBBBA 3% cut → ~$1.8M EBITDA hit (prob-weighted).
- 2027: +sequestration 2% → +$0.9M; cumulative $2.7M.
- 2028: +site-neutral HOPD → +$0.6M; cumulative $3.3M.
- 2029: +state Medicaid → +$0.9M; cumulative $4.2M.
- 2030: no new shock; cumulative stays $4.2M.

Worst-year leverage = $412.5M debt / ($75M − $4.2M) ≈
5.83x, well under 7.0x → partner-note: "shocks contained;
proceed on current thesis."

### Packet fields that trigger

- `hold_start_year`, `hold_years` — the window to project.
- `stress.*` (RegulatoryStressInputs) — subsector, revenue,
  EBITDA, Medicare FFS/MA, HOPD, ASC, contribution margin.
- `leverage_multiple`, `covenant_max_leverage` — cov trip
  detection.
- `schedule` — custom landing schedule for deal-specific
  probabilities.

---

## 179. QofE pre-screen (`qofe_prescreen.py`)

**Partner statement:** "Sellers normalize aggressively.
Good QofE strips back 20-30%. Know which add-backs will
survive before you engage the firm."

`qofe_tracker` handles status/progress on a QofE
engagement. `qofe_prescreen` is the *pre*-QofE partner
read: given the seller's adjustments schedule, what
fraction will survive QofE, and what's the true EBITDA
to underwrite against?

### Partner-judgment survival rates

Based on healthcare-services PE patterns:

- `owner_comp_excess` — 85% survives.
- `related_party_rent` — 70% if market; sale-leaseback
  risk.
- `nonrecurring_legal` — 60%; recurring is run-rate.
- `covid_windfall` — 20%; stripped aggressively.
- `systems_migration_onetime` — 50%; partners
  question "one-time" framing.
- `executive_severance` — 70%.
- `deferred_maintenance_capex_as_opex` — 10%; walk
  signal if material.
- `pro_forma_acquisition` — 40%; TTM actuals required.
- `management_fee_elim` — 90%; standard normalization.
- `startup_losses` — 50%; vintage cohort support.
- `litigation_settlement` — 60%.
- `other` — 50% default.

### Partner-note escalation

- Haircut ≥ 20% → "re-price from adjusted EBITDA or pass."
- Haircut 10-20% → "model off adjusted, not stated."
- Haircut < 10% → "proceed; verify at QofE."
- Deferred-maintenance material → "walk signal; seller recut
  required."

### Worked example

Seller asserts $75M EBITDA with add-backs:

- $10M covid windfall → $2M surviving, $8M haircut.
- $3M deferred maintenance as opex → $0.3M surviving,
  $2.7M haircut + walk signal.
- $2M owner comp → $1.7M surviving, $0.3M haircut.

QofE-adjusted EBITDA = $75 − $8 − $2.7 − $0.3 = $64M.

Partner note: "Expected QofE haircut $11M (15%). Model
off $64M, not $75M. Deferred-maintenance capex → walk
signal; seller recut required."

### Packet fields that trigger

- `stated_ebitda_m` — seller's headline number.
- `seller_add_backs` — list of SellerAddBack (category +
  dollar amount).

---

## 180. Pre-IC chair brief (`pre_ic_chair_brief.py`)

**Partner statement:** "Before IC I walk the chair through
4 bullets: the thesis, where the math works, where it
doesn't, and what would change my mind. If I can't get
that on one page, the team isn't ready."

Distinct from:

- `deal_one_liner` — the single sentence (too short for
  the chair).
- `ic_memo` — the full 60-page IC deck (too long for 30
  min before IC).
- `ic_decision_synthesizer` — multi-dimensional breakdown
  (useful but not a one-pager).

The chair brief is exactly 4 bullets:

1. **Thesis** — what we're buying and why, in plain
   English.
2. **Where the math works** — 2-3 numbers that anchor the
   upside case.
3. **Where the math doesn't work** — 2-3 numbers that
   anchor the bear case.
4. **What would change my mind** — 3 specific things that,
   if resolved, flip the verdict.

### Verdict inference

If no explicit recommendation is provided:

- Any **contradicted thesis link** → `pass`.
- ≥ 2 **compound risks** → `reprice`.
- In-band checks present AND no high-risk unresolved →
  `invest`.
- Otherwise → `diligence_more`.

### Why 4 bullets exactly

The chair doesn't have time for 5 bullets. Three isn't
enough for the structure to work (you need thesis +
bull + bear + change-my-mind, minimum). Four is the
partner-brain default because it forces the team to
collapse the case into a structure the chair can push
back on bullet-by-bullet.

### Packet fields that trigger

- `deal_name`, `thesis_sentence`, `recurring_ebitda_m`,
  `entry_multiple`, `target_moic`, `target_irr`,
  `hold_years` — thesis bullet.
- `in_band_count`, `math_works_numbers` — math-works
  bullet.
- `out_of_band_count`, `compound_risks`,
  `contradicted_thesis_links` — math-breaks bullet.
- `high_risk_unresolved_links`,
  `change_my_mind_items` — change-my-mind bullet.

---

## 181. Seller math reverse-engineer (`seller_math_reverse.py`)

**Partner statement:** "The seller isn't stupid. If they
ask 16x, they believe something specific about margin,
growth, and exit. I want to know what that is before I
counter."

Given our base case and seller's ask, solve for what the
seller must be assuming on each of three variables
(**holding the other two constant**):

1. **Implied exit multiple** — seller's view of the exit
   market.
2. **Implied EBITDA growth** — seller's view of compound
   growth.
3. **Implied margin expansion** — seller's view of
   operator leverage.

Partner reads each implied assumption against peer
benchmarks and picks the weakest to force seller to
defend.

### Interpretation thresholds

- Implied exit > 16x → "cycle peak; counter off cycle-
  average."
- Implied growth > 10% → "double-digit is rare in
  healthcare services; seller betting on market we don't
  see."
- Implied margin > 400 bps → "partner-reject; requires
  operator heroics we'd own."

### Partner note escalation

- Ask premium > 15% → "Seller must assume ONE of (X multiple,
  Y growth, Z margin). Pick the weakest and force seller to
  defend it."
- 5-15% → "Standard negotiation; pick one variable."
- Below buyer's implied price → "Seller sees downside we
  don't — diligence the gap."

### Worked example

Buyer base: $75M EBITDA, 11x exit, 5% growth, 100 bps
margin, 5-yr hold, 2.5x MOIC target.

- Buyer's implied price: $75 × (1.05)^5 × 1.01 × 11 / 2.5
  ≈ $425M.
- Seller asks $510M (20% premium).
- Implied exit multiple (holding growth+margin): ~13.2x.
- Implied growth (holding multiple+margin): ~8.5%/yr.
- Implied margin (holding multiple+growth): ~2,100 bps.

Partner note: "Seller must assume ONE of: 13.2x exit, 8.5%
growth, or 2,100 bps margin expansion. Pick the weakest
(the margin story is most indefensible) and force seller
to specify which initiatives deliver it."

### Packet fields that trigger

- `buyer_base_ebitda_m`, `buyer_base_exit_multiple`,
  `buyer_base_ebitda_growth_pct`,
  `buyer_base_margin_expansion_bps`
- `hold_years`, `target_moic`
- `seller_ask_price_m`

---

## 182. Management-meeting questions (`management_meeting_questions.py`)

**Partner statement:** "In the Monday management meeting,
I don't ask 'tell me about the business.' I ask the CEO
the three questions where their answer reveals whether the
thesis survives. Different chair for CFO. Different for
COO."

Distinct from `reference_check_framework` (former-peer
reference calls) and `diligence_checklist_live` (what's
packet-vs-MI at framework level). This module generates
the **actual questions** the partner brings to MM, tied to:

- **Thesis** — which downstream chain links are still open?
- **Pattern matches** — which traps / failures should we
  probe?
- **Packet gaps** — what's missing that mgmt can answer?

### Roles and signature base questions

- **CEO** — "If I asked you to cut a division tomorrow,
  which one?" (strategic clarity). "Top 3 hires since
  you took the role — where are they now?" (talent
  retention).
- **CFO** — "Last 8 quarters: how many times did you hit
  forecast?" (track record → forward haircut). "Worst-
  case covenant headroom if EBITDA falls 10%?"
- **COO** — "Of your top 10 operators, how many own a
  P&L line?" (distributed accountability).
- **CMO** — "CMI trend + drivers." "Any open RAC/OIG
  audits?"
- **CCO** — "Churn rate on top 10 over 3 years."
- **CIO** — "EHR migration timeline if asked tomorrow."

### Conditional question layering

- If `thesis == "denial_reduction"` + role == CFO → add
  question on run-rate vs. one-time share of Y1 EBITDA.
- If pattern `fix_denials_in_12_months` fires → COO
  question on monthly program actuals.
- If pattern `ceo_will_stay_through_close` fires → CEO
  question on post-close personal commitment timing.
- Packet gap `cmi_trend` → CMO question requesting
  underlying data + 3-yr trend.

### Partner-note escalation

- ≥ 8 must-ask → "block 2 hours; gating session, not
  meet-and-greet."
- 4-7 must-ask → "standard MM scope."
- < 4 must-ask → "consider splitting to follow-up call."

### Packet fields that trigger

- `thesis` — selects thesis-specific questions.
- `pattern_matches` — list of pattern IDs.
- `packet_gaps` — list of gap strings.
- `roles` — which roles are attending MM.

---

## 183. Change log

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
- **2026-04-17** — Added `coinvest_sizing.py` (§94) — fund
  commitment + concentration cap + LP demand coverage. Full
  inventory: 92 modules, 900 pe_intelligence unit tests.
- **2026-04-17** — Added `sensitivity_grid.py` (§95) — one-variable
  MOIC / IRR sweeps + tornado. Full inventory: 93 modules, 915
  pe_intelligence unit tests.
- **2026-04-17** — Added `capital_structure_tradeoff.py` (§96) —
  leverage sweep with coverage + default-risk + status. Full
  inventory: 94 modules, 924 pe_intelligence unit tests.
- **2026-04-17** — Added `refinancing_window.py` (§97) — per-tranche
  refi/wait/hold recommendations + maturity wall aggregation. Full
  inventory: 95 modules, 934 pe_intelligence unit tests.
- **2026-04-17** — Added `dividend_recap_analyzer.py` (§98) —
  feasibility gates + DPI uplift + blockers. Full inventory: 96
  modules, 942 pe_intelligence unit tests.
- **2026-04-17** — Added `carve_out_risks.py` (§99) — TSA, CoC,
  IT separation, payer re-credentialing, employee retention. Full
  inventory: 97 modules, 952 pe_intelligence unit tests.
- **2026-04-17** — Added `secondary_sale_valuation.py` (§100) —
  LP-led discount and GP-led continuation pricing. Full inventory:
  98 modules, 962 pe_intelligence unit tests.
- **2026-04-17** — Added `lbo_stress_scenarios.py` (§101) — 7-scenario
  library + covenant-breach + months-to-default. Full inventory:
  99 modules, 974 pe_intelligence unit tests.
- **2026-04-17** — Added `physician_compensation_benchmark.py` (§102)
  — 9-specialty MGMA medians + comp/wRVU + base-mix checks. Full
  inventory: 100 modules, 984 pe_intelligence unit tests.
- **2026-04-17** — Added `ebitda_normalization.py` (§103) — seller
  bridge haircut + partner-prudent Adj EBITDA. Full inventory:
  101 modules, 995 pe_intelligence unit tests.
- **2026-04-17** — Added `staffing_pipeline_analyzer.py` (§104) —
  4Q headcount + attrition + lost revenue for healthcare services.
  Full inventory: 102 modules, 1,006 pe_intelligence unit tests.
- **2026-04-17** — Added `ma_integration_scoreboard.py` (§105) —
  6-dimension per-bolt-on health + revenue-weighted platform
  score. Full inventory: 103 modules, 1,017 pe_intelligence unit
  tests.
- **2026-04-17** — Added `customer_concentration_drilldown.py` (§106)
  — top-N + HHI + churn probability + revenue-at-risk + cross-sell.
  Full inventory: 104 modules, 1,028 pe_intelligence unit tests.
- **2026-04-17** — Added `geographic_reach_analyzer.py` (§107) —
  state HHI + CPOM exposure + density + expansion whitespace.
  Full inventory: 105 modules, 1,040 pe_intelligence unit tests.
- **2026-04-17** — Added `growth_algorithm_diagnostic.py` (§108) —
  price/volume/mix/acquisition decomposition + quality score.
  Full inventory: 106 modules, 1,050 pe_intelligence unit tests.
- **2026-04-17** — Added `technology_debt_assessor.py` (§109) —
  8-area severity + cost + risk score. Full inventory: 107 modules,
  1,061 pe_intelligence unit tests.
- **2026-04-17** — Added `roic_decomposition.py` (§110) —
  DuPont margin/turnover + 5-subsector peer bands. Full
  inventory: 108 modules, 1,070 pe_intelligence unit tests.
- **2026-04-17** — Added `working_capital_peer_band.py` (§111) —
  DSO/DPO/DIO per-subsector bands + CCC + cash release. Full
  inventory: 109 modules, 1,080 pe_intelligence unit tests.
- **2026-04-17** — Added `hold_period_optimizer.py` (§112) — IRR
  vs MOIC peak-year tradeoff. Full inventory: 110 modules, 1,089
  pe_intelligence unit tests.
- **2026-04-17** — Added `pricing_power_diagnostic.py` (§113) —
  6-dim weighted score + base-case rate guidance. Full inventory:
  111 modules, 1,097 pe_intelligence unit tests.
- **2026-04-17** — Added `portfolio_rollup_viewer.py` (§114) —
  fund-level aggregation + top movers + sub-sector / vintage /
  stage cuts. Full inventory: 112 modules, 1,108 pe_intelligence
  unit tests.
- **2026-04-17** — Added `bank_syndicate_picker.py` (§115) —
  21-lender universe + size/sector/covenant scoring + tiered picks.
  Full inventory: 113 modules, 1,118 pe_intelligence unit tests.
- **2026-04-17** — Added `exit_channel_selector.py` (§116) —
  strategic/sponsor/ipo/continuation scoring + timing + multiples.
  Full inventory: 114 modules, 1,128 pe_intelligence unit tests.
- **2026-04-17** — Added `mgmt_incentive_sizer.py` (§117) —
  MIP pool % by deal type + layer allocation + LTIP + vesting.
  Full inventory: 115 modules, 1,140 pe_intelligence unit tests.
- **2026-04-17** — Added `qofe_tracker.py` (§118) — QofE status
  + adjustments supported/unsupported + NWC-vs-peg + critical-path.
  Full inventory: 116 modules, 1,150 pe_intelligence unit tests.
- **2026-04-17** — Added `board_composition_analyzer.py` (§119).
  Full inventory: 117 modules, 1,158 pe_intelligence unit tests.
- **2026-04-17** — Added `historical_failure_library.py` (§120) —
  10 named/dated healthcare-PE failures with packet matchers.
  Full inventory: 118 modules, 1,173 pe_intelligence unit tests.
- **2026-04-17** — Added `partner_voice_memo.py` (§121) —
  recommendation-first IC memo; three-things-that-would-change-my-mind;
  hard rules (2+ deal-killers / 2+ historical matches → PASS).
  Full inventory: 119 modules, 1,184 pe_intelligence unit tests.
- **2026-04-17** — Added `recurring_vs_onetime_ebitda.py` (§122)
  — exit multiple applies only to recurring; one-time at 1x.
  Worked 50M example showing $110M overstatement trap. Full
  inventory: 120 modules, 1,195 pe_intelligence unit tests.
- **2026-04-17** — Added `obbba_sequestration_stress.py` (§123) —
  4 named regulatory shocks with specific $ EBITDA impacts.
  Full inventory: 121 modules, 1,204 pe_intelligence unit tests.
- **2026-04-17** — Added `archetype_subrunners.py` (§124) —
  7 archetype-specific heuristic packs (payer_mix_shift, roll_up,
  cmi_uplift, outpatient_migration, back_office_consolidation,
  cost_basis_compression, capacity_expansion) each with
  partner-voice warnings. Full inventory: 122 modules, 1,219
  pe_intelligence unit tests.
- **2026-04-17** — Added `unrealistic_on_its_face.py` (§125) —
  7 partner-reflex "red flag on sight" detectors, encoding the
  canonical $400M rural-CAH-at-28%-IRR example. Full inventory:
  123 modules, 1,231 pe_intelligence unit tests.
- **2026-04-17** — Added `partner_voice_variants.py` (§126) — 5
  IC narrators (skeptic/optimist/md_numbers/operating_partner/
  lp_facing) producing the same deal from five perspectives.
  Full inventory: 124 modules, 1,241 pe_intelligence unit tests.
- **2026-04-17** — Added `cross_module_connective_tissue.py`
  (§127) — named insights emitted when signals from multiple
  modules co-occur; first module where reasoning IS the product.
  Full inventory: 125 modules, 1,253 pe_intelligence unit tests.
- **2026-04-17** — Added `diligence_checklist_live.py` (§128) —
  30-item canonical list with packet/MI/third-party source tags
  and answered/needs/stale/missing status per item. Full
  inventory: 126 modules, 1,263 pe_intelligence unit tests.
- **2026-04-17** — Added `partner_traps_library.py` (§129) — 10
  named thesis traps including the three user-cited: fix-denials-
  in-12-months, payer-renegotiation-coming, MA-will-make-it-up.
  Full inventory: 127 modules, 1,277 pe_intelligence unit tests.
- **2026-04-17** — Added `first_thirty_minutes.py` (§130) —
  packet-derived landmine/opening/probe questions for the first
  30 minutes of an MI. Full inventory: 128 modules, 1,291
  pe_intelligence unit tests.
- **2026-04-17** — Added `thesis_coherence_check.py` (§131) —
  flags internal contradictions across thesis pillars (e.g.
  volume+margin+no labor; roll-up+no integration spend). Full
  inventory: 129 modules, 1,302 pe_intelligence unit tests.
- **2026-04-17** — Added `margin_of_safety.py` (§132) —
  binary-search breakeven deltas per lever against hurdle MOIC,
  plus combined-shock test. Full inventory: 130 modules, 1,311
  pe_intelligence unit tests.
- **2026-04-17** — Added `management_vs_packet_gap.py` (§133) —
  classifies mgmt-vs-packet differences as minor/material/
  contradicted with partner-voice interpretation. Full inventory:
  131 modules, 1,319 pe_intelligence unit tests.
- **2026-04-17** — Added `rcm_lever_cascade.py` (§134) — the
  user's canonical cross-module example (denial → coding → CMI
  → Medicare bridge → working capital) with specific $ EBITDA
  and cash impacts per step. Full inventory: 132 modules, 1,329
  pe_intelligence unit tests.
- **2026-04-17** — Added `bear_case_generator.py` (§135) —
  deal-specific bear drivers + story + probability-weighted MOIC.
  Full inventory: 133 modules, 1,342 pe_intelligence unit tests.
- **2026-04-17** — Added `payer_mix_shift_cascade.py` (§136) —
  mix shift → rate → revenue → EBITDA → multiple uplift with
  credibility score penalizing aggressive pace + thin contract
  pipeline. Full inventory: 134 modules, 1,352 pe_intelligence
  unit tests.
- **2026-04-17** — Added `labor_shortage_cascade.py` (§137) —
  turnover → agency premium → margin → quality/volume →
  covenant pressure with breach flag. Full inventory: 135
  modules, 1,361 pe_intelligence unit tests.
- **2026-04-17** — Added `exit_story_generator.py` (§138) —
  sell-side banker's exit pitch composed at entry; subsector
  multiple ranges; likely-buyer list. Full inventory: 136
  modules, 1,371 pe_intelligence unit tests.
- **2026-04-17** — Added `partner_scorecard.py` (§139) — 7
  binary must-haves (scale / team / market / unit econ /
  balance sheet / exit path / thesis integrity); any one fails
  = pass. Full inventory: 137 modules, 1,382 pe_intelligence
  unit tests.
- **2026-04-17** — Added `cycle_timing_pricing_check.py` (§140)
  — peak-multiple × peak-EBITDA double-count detector with
  subsector cycle averages and haircut recommendation. Full
  inventory: 138 modules, 1,391 pe_intelligence unit tests.
- **2026-04-17** — Added `one_hundred_day_plan_from_packet.py`
  (§141) — auto-derive 100-day actions from packet signals; 14
  conditional rules + 2 always-on; cap at 15. Full inventory:
  139 modules, 1,406 pe_intelligence unit tests.
- **2026-04-17** — Added `outpatient_migration_cascade.py` (§142)
  — 4th canonical cascade (IP→OP → rate differential → margin
  swap → capacity unlock → site-neutral regulatory risk). Full
  inventory: 140 modules, 1,414 pe_intelligence unit tests.
- **2026-04-17** — Added `quality_of_diligence_scorer.py` (§143)
  — partner audits own team's work across 6 dimensions; IC-ready
  requires every dim ≥ 80% (floor, not average). Full inventory:
  141 modules, 1,424 pe_intelligence unit tests.
- **2026-04-17** — Added `management_first_sitdown.py` (§144) —
  post-LOI agenda generator: thesis + risks + outcomes blocks
  with probe-if-canned notes per question. Full inventory: 142
  modules, 1,434 pe_intelligence unit tests.
- **2026-04-17** — Added `ic_decision_synthesizer.py` (§145) —
  crown-jewel cross-module synthesizer: one recommendation + 3
  reasons + 3 flip-the-call signals + chair opening line. Full
  inventory: 143 modules, 1,447 pe_intelligence unit tests.
- **2026-04-17** — Added `healthcare_regulatory_calendar.py`
  (§146) — 12 named 2026-2028 regulatory events with subsector +
  $ impact; events-for-deal selector by hold period. Full
  inventory: 144 modules, 1,459 pe_intelligence unit tests.
- **2026-04-17** — Added `deal_smell_detectors.py` (§147) — 9
  partner-reflex "smells like X" patterns from combined signals.
  Full inventory: 145 modules, 1,472 pe_intelligence unit tests.
- **2026-04-17** — Added `letter_to_seller.py` (§148) —
  banker-reply composer (pass/invest/diligence-more variants).
  Full inventory: 146 modules, 1,480 pe_intelligence unit tests.
- **2026-04-17** — Added `synergy_credibility_scorer.py` (§149)
  — category × timing × evidence credibility scoring with
  partner-prudent realization %. Full inventory: 147 modules,
  1,491 pe_intelligence unit tests.
- **2026-04-17** — Added `process_stopwatch.py` (§150) — read
  banker process timing (tight close, bidder collapse,
  relaunch, walks, reprice, silence). Full inventory: 148
  modules, 1,502 pe_intelligence unit tests.
- **2026-04-17** — Added `red_flag_escalation_triage.py` (§151)
  — partner-immediate vs partner-this-week vs associate vs info
  triage by category + severity. Full inventory: 149 modules,
  1,513 pe_intelligence unit tests.
- **2026-04-17** — Added `quarterly_operating_review.py` (§152)
  — post-close QoR 4-block agenda (numbers/thesis/people/
  forward) with partner-focus per block. Full inventory: 150
  modules, 1,524 pe_intelligence unit tests.
- **2026-04-17** — Added `value_creation_plan_generator.py`
  (§153) — 3-year VCP with 8 conditional initiatives, owners,
  dependencies, and execution risks. Full inventory: 151
  modules, 1,535 pe_intelligence unit tests.
- **2026-04-17** — Added `exit_timing_signal_tracker.py` (§154)
  — 7-signal exit readiness tracker (start_rfp / dry_run /
  wait). Full inventory: 152 modules, 1,545 pe_intelligence
  unit tests.
- **2026-04-17** — Added `buyer_type_fit_analyzer.py` (§155) —
  8 buyer types (health system / payer-led / specialty
  consolidator / larger sponsor / peer / IPO / continuation /
  REIT) scored + named targets. Full inventory: 153 modules,
  1,556 pe_intelligence unit tests.
- **2026-04-17** — Added `add_on_fit_scorer.py` (§156) —
  specific bolt-on fit (strategic/financial/integration/
  execution) + proceed/re-evaluate/pass rec. Full inventory:
  154 modules, 1,567 pe_intelligence unit tests.
- **2026-04-17** — Added `concentration_risk_multidim.py`
  (§157) — 6-dim concentration scan (customer / site / payer /
  provider / service line / geography); 30/50% thresholds. Full
  inventory: 155 modules, 1,577 pe_intelligence unit tests.
- **2026-04-17** — Added `post_close_surprises_log.py` (§158) —
  diligence miss-rate tracker; portfolio-level feedback loop.
  Full inventory: 156 modules, 1,586 pe_intelligence unit tests.
- **2026-04-17** — Added `regional_wage_inflation_overlay.py`
  (§159) — 5-tier regional premium + inflation overlay; flags
  model single-rate assumption vs weighted actual. Full
  inventory: 157 modules, 1,596 pe_intelligence unit tests.
- **2026-04-17** — Added `rac_audit_exposure_estimator.py`
  (§160) — Medicare FFS audit exposure $ with signal-adjusted
  hit rate; IC-blocking threshold. Full inventory: 158 modules,
  1,606 pe_intelligence unit tests.
- **2026-04-17** — Added `irr_decay_curve.py` (§161) — per-year
  MOIC/IRR and last-year-above-hurdle; the math partner runs
  when someone suggests extending the hold. Full inventory: 159
  modules, 1,614 pe_intelligence unit tests.
- **2026-04-17** — Added `competing_deals_ranker.py` (§162) —
  rank competing deals across return / quality / downside / fit
  / timing with if-I-can-only-do-one recommendation. Full
  inventory: 160 modules, 1,625 pe_intelligence unit tests.
- **2026-04-17** — Added `medicaid_state_exposure_map.py` (§163)
  — 4-tier state risk overlay with bear-case $ impact per state.
  Full inventory: 161 modules, 1,636 pe_intelligence unit tests.
- **2026-04-17** — Added `earnout_design_advisor.py` (§164) —
  when/how to structure earn-out by driver quality + seller-
  conviction × buyer-skepticism. Full inventory: 162 modules,
  1,646 pe_intelligence unit tests.
- **2026-04-17** — Added `sponsor_reputation_tracker.py` (§165)
  — 11-sponsor reputation book with 5 dimensions + context-
  specific commentary (competing_bidder / co_investor /
  exit_buyer). Full inventory: 163 modules, 1,657
  pe_intelligence unit tests.
- **2026-04-17** — Added `debt_capacity_sizer.py` (§166) — debt
  = min(coverage, FCF, cycle-discipline) with named binding
  constraint. Full inventory: 164 modules, 1,667
  pe_intelligence unit tests.
- **2026-04-17** — Added `operating_partner_fit_matrix.py`
  (§167) — 6-archetype ops partner fit (turnaround / scaler /
  healthcare / M&A / exit / founder coach). Full inventory: 165
  modules, 1,677 pe_intelligence unit tests.
- **2026-04-17** — Added `reverse_diligence_checklist.py` (§168)
  — pre-sale seller-side disclosure items by severity: kill-
  deal / price-haircut / discovery-risk / housekeeping. Full
  inventory: 166 modules, 1,689 pe_intelligence unit tests.
- **2026-04-17** — Added `management_forecast_reliability.py`
  (§169) — analyze prior forecasts-vs-actuals; reliability
  score + haircut recommendation. Full inventory: 167 modules,
  1,698 pe_intelligence unit tests.
- **2026-04-17** — Added `working_capital_peg_negotiator.py`
  (§170) — counter-peg with methodology by profile + 2%
  closing buffer. Full inventory: 168 modules, 1,708
  pe_intelligence unit tests.
- **2026-04-17** — Added `management_rollover_equity_designer.py`
  (§171) — target rollover % by CEO profile; alignment
  grade; strong/adequate/thin. Full inventory: 169 modules,
  1,717 pe_intelligence unit tests.
- **2026-04-17** — Added `reference_check_framework.py` (§172)
  — structured CEO/CFO reference-call plan by relationship type
  with listen-for notes per question. Full inventory: 170
  modules, 1,727 pe_intelligence unit tests.
