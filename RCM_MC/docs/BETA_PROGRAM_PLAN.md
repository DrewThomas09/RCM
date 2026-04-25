# Beta Program Plan — Validating Models with Real PE Firms

The platform's predictors look defensible in synthetic backtests (per
the model_quality dashboard) but real PE firms have idiosyncratic
deal flow, internal benchmarks, and analyst preferences. The beta
program is how we discover where the platform actually performs in
the wild — what predictions land, what UX friction shows up, what
features partners ask for that we didn't build. The program also
seeds the learning loop with the first 1-2 quarters of real-world
prediction → actual data that improve every subsequent customer's
experience.

This document maps the beta program structure, customer selection,
onboarding, validation methodology, and conversion path.

## Program objectives

The beta serves four distinct goals; success on each is measured
separately:

  1. **Model validation** — verify predictor R² + CI calibration
     hold on real PE-firm data, not just synthetic.
  2. **Workflow validation** — verify the dashboard / deal profile
     / IC memo workflow matches how real analysts actually move
     through diligence.
  3. **Pricing validation** — test willingness-to-pay at the $30K
     base + $5K/packet usage rider levels (per the business model
     plan).
  4. **Reference-customer creation** — every beta customer becomes
     a case study + reference customer for paid sales (per the
     partnerships plan target of 30% partnership-driven
     acquisition by year-end).

Each objective has its own success threshold; the program ends
when all four hit their thresholds OR when 12 months elapse,
whichever comes first.

## Program structure

### Three-cohort design

The beta program runs three sequential cohorts over 12 months.
Each cohort is sized + selected differently to test progressively
more demanding configurations:

  - **Cohort 1 (Months 0-4): Design Partners** (3 firms)
  - **Cohort 2 (Months 4-8): Validation Beta** (8-10 firms)
  - **Cohort 3 (Months 8-12): Pre-GA Beta** (15-20 firms)

By the end of cohort 3, the platform is general-availability
(GA) and the program graduates into the regular paid-customer
pipeline.

### Cohort 1: Design Partners (3 firms)

**Profile**: Mid-market healthcare PE shops, 15-40 person
investment teams, $3-15B AUM, currently underwriting 5-10 deals
per quarter.

**Commercial terms**:
- 4 months free access to Pro tier with everything unlocked.
- Discounted Year 1 contract: $150K (vs $400K list) if they
  convert post-pilot.
- Full white-glove onboarding from our team (CSM + 2
  engineers).
- Right to influence roadmap — quarterly product sessions
  where they prioritize features.

**What we ask in return**:
- 2-3 hours per week of analyst feedback time (recorded
  sessions).
- Permission to use de-identified deal data in case studies
  + marketing.
- One reference call to other prospects per quarter.
- Public case study at end of pilot if successful.

**What we measure**:
- 80% of analysts using the platform daily by week 8.
- ≥50% of new deals running through the platform by week 12.
- Net Promoter Score ≥40 in week-16 survey.
- ≥2 of the 3 firms convert to paid Year-1 contract.

### Cohort 2: Validation Beta (8-10 firms)

**Profile**: Mix of mid-market healthcare PE + boutique
healthcare PE + healthcare-focused family offices. Goal is
diversity — different deal flows, different internal benchmarks,
different geography.

**Commercial terms**:
- 4-month pilot at $50K (heavily discounted Pro tier).
- If converted post-pilot: standard Pro-tier list price ($30K
  /seat/year + usage rider) with the pilot fee credited.
- Self-service onboarding (our CSM available but customer
  drives).

**What we ask**:
- Quarterly check-ins (not weekly).
- Specific feedback on 3 features each: dashboard, deal
  profile, comparison view.
- Aggregated benchmarks shared with us (anonymized).

**What we measure**:
- ≥60% of customers convert to paid post-pilot.
- Predictor MAE on real-deal data within 1.5× of synthetic
  backtest MAE.
- ≤15% feature-request overlap (high overlap means missing
  obvious things; low overlap means each customer wants
  bespoke = bad signal).

### Cohort 3: Pre-GA Beta (15-20 firms)

**Profile**: Open application — any healthcare PE shop. Vetted
on (a) team size ≥3 investment professionals, (b) currently
deploying capital in healthcare PE, (c) signed NDA.

**Commercial terms**:
- Pro tier list price ($30K/seat/yr) with first-3-months
  free.
- Standard contract terms (no special discounts).
- Self-service onboarding.

**What we ask**:
- Bug reports + feature requests via in-app feedback.
- Optional case study participation.
- Reference availability.

**What we measure**:
- ≥75% of pilot customers convert to paid annual contract.
- Average customer onboarding time (signup → first deal
  analyzed) ≤5 days.
- Support ticket volume tracking (real load test for
  support team).

After Cohort 3, the platform exits beta and enters general
availability.

## Customer selection criteria

### Cohort 1 (Design Partners) — high bar

Three slots, ~50 candidates. Selection criteria, weighted:

  - **Deal volume** (30%): minimum 20 deals/year to generate
    enough data for predictor calibration validation.
  - **Team size** (20%): 15-40 investment professionals — large
    enough that multi-user features get exercised, small enough
    that decisions move fast.
  - **Sector focus** (20%): healthcare-PE-specialist or
    healthcare-strong-vertical generalist (not generalist with
    occasional healthcare).
  - **Engagement willingness** (20%): partner committed to 2-3
    hours/week of feedback.
  - **Brand value** (10%): well-known firm whose case study
    carries weight in the next cohort's recruiting.

Outreach for Cohort 1: warm intros via PE LP relationships +
healthcare consultancy referrals (per partnerships plan
Tier-1).

### Cohort 2 (Validation Beta) — moderate bar

Eight to ten slots, ~150-200 candidates. Selection criteria
loosened:

  - Minimum 10 deals/year.
  - Minimum 5 investment professionals.
  - Healthcare PE focus or active healthcare deals in pipeline.
  - Willingness to participate in quarterly check-ins.

Outreach: design-partner referrals + outbound to healthcare PE
LinkedIn connections + conference sponsorship (HFMA + LPGP
healthcare events).

### Cohort 3 (Pre-GA Beta) — open

Open application; vetted on basic criteria only. Goal: 15-20
who actually engage; cap intake at 30 to leave room for
attrition.

## Validation methodology

### Model validation (Objective #1)

Per the learning loop plan, every prediction the platform makes
during beta is auto-recorded. Actuals arrive as customers report
realized RCM outcomes (per their internal data) or as new HCRIS
data lands. We measure:

  - **Predictor calibration**: observed CI coverage vs nominal
    90%. If real-deal coverage drops below 80%, model needs
    retraining before GA.
  - **Predictor MAE on real deals**: comparison to synthetic
    backtest MAE. If real MAE >1.5× synthetic, that's a signal
    to recalibrate on real-deal cohort data.
  - **Cohort failure modes**: per the learning loop plan's
    cohort_failure_analysis. Specifically check whether the
    predictors fail more on certain hospital archetypes (rural
    CAHs, specialty hospitals, safety-net) — calibrate per
    cohort if needed.

The validation period is 8-12 months from first beta deal — not
because models need that long, but because PE deal cycles are
long enough that 6 months is the minimum to see actuals on
predictions made at deal screening.

### Workflow validation (Objective #2)

Each beta customer's analysts use the platform on real deals.
We track:

  - **Time to first packet** (CIM → analytical packet): target
    <30 minutes vs the 4-8 hour baseline.
  - **Packet completeness on submission to IC**: percentage of
    deal IC memos that pull from the platform's packet vs
    custom analyst work. Target 80% reuse.
  - **Drop-off rates**: per-section heatmaps showing where
    analysts close the page mid-flow. High drop-off on a
    section = UX failure on that section.
  - **Feature adoption**: % of customers using each major
    feature (search, comparison, scenarios, etc.). Features
    below 30% adoption need either UX rework or sunset.

Cohort 1 weekly recorded sessions are the highest-signal
source for workflow validation. Cohort 2-3 use in-app
behavioral telemetry.

### Pricing validation (Objective #3)

Pricing tests run in cohort 2 (since cohort 1 is heavily
discounted, doesn't tell us much about price sensitivity):

  - **Anchor test**: half of cohort 2 sees $30K/seat list
    price; half sees $40K. Conversion-rate delta tells us
    whether $30K is leaving money on the table.
  - **Usage rider test**: track what fraction of customers
    consume their bundled-packet allotment vs pay overage.
    If <30% pay overage, the rider is too cheap; if >70%,
    too expensive.
  - **Discount-floor test**: customer-by-customer record of
    discount asked + given + accepted. Sets the negotiating
    floor for sales reps.

### Reference-customer creation (Objective #4)

Per the partnerships plan, every beta customer is a potential
reference. We document:

  - 1-page case study per beta customer (anonymized if
    needed) covering: pain point, platform solution,
    measurable outcome.
  - 3-5 quote candidates per customer for marketing use.
  - Reference willingness: customer's commitment to take 1-2
    reference calls per quarter.

By end of cohort 3, target: ≥10 reference-willing customers.

## Onboarding process

### Cohort 1: white-glove (4-week onboarding)

Week 1:
- Kickoff call with partner + VP + analyst team.
- Demo (per the MD demo script).
- Data import: customer's existing portfolio + active deal
  pipeline loaded by our team.
- Per-firm ML calibration: predictors fit on customer's
  realized exits if they share data.

Week 2:
- Workflow training: 2-hour analyst workshop per firm.
- First active deal walked through end-to-end.
- Custom dashboard configuration.

Week 3:
- Slack + email integration setup (per integrations plan).
- DealCloud / Datasite integration if applicable.

Week 4:
- Weekly cadence begins: feedback session + roadmap input
  + escalation channel.

### Cohort 2: guided (1-week onboarding)

Self-service signup; CSM holds 1 onboarding call per customer
covering platform tour + their specific use case.

### Cohort 3: self-service (immediate)

In-app product tour + video walkthroughs. CSM available on
Slack but doesn't drive onboarding.

## Feedback collection

Three channels feed into a single feedback hub:

  1. **Recorded sessions** (cohort 1 only): weekly 30-min
     analyst session, recorded + transcribed + tagged.
  2. **In-app feedback widget**: floating button on every
     page; analyst types issue/idea + automatic context
     capture (URL, deal_id if applicable, screenshot if
     allowed).
  3. **Quarterly NPS + feature-priority survey**: short form
     measuring satisfaction + collecting top-3 feature
     requests.

All three flow into a single Linear / Jira board tagged by:
  - Customer (which beta cohort)
  - Severity (critical / major / minor)
  - Theme (model accuracy / UX / integrations / pricing /
    new feature)

Weekly product review triages the board. P0/P1 items addressed
within the cohort's pilot window.

## Success thresholds → GA decision

The platform exits beta when:

  - **Model validation**: ≥85% of predictors hit ≥80% real-deal
    CI coverage.
  - **Workflow validation**: ≥70% of beta customers' deals
    actively run through the platform.
  - **Pricing validation**: ≥60% conversion to paid contract
    across cohort 2-3.
  - **Reference creation**: ≥10 willing reference customers
    with case studies.

If any threshold is missed at month 12, beta extends and the
GA launch slips. Better to delay GA than launch a platform
that hasn't survived real-world pilot.

## Risk + mitigation

  - **Customer drops out during pilot**: contractual minimum
    is 4 months pilot length to mitigate. Cohort 1 has formal
    commitment terms; cohort 2-3 less formal but tracked.

  - **Model accuracy issues surface late**: continuous learning
    loop (per the plan) means retraining can happen mid-pilot.
    Champion/challenger framework (per the same plan) handles
    in-flight model swaps without disrupting customers.

  - **Customer requests features we won't build**: cohort 1's
    quarterly product sessions explicitly include the
    'what we won't build' conversation. Roadmap is influenced,
    not dictated, by beta feedback.

  - **Customer wants to terminate early**: cohort 1 commits to
    4 months but can leave with 30 days' notice if material
    issue. Cohort 2-3 have standard cancellation terms.

  - **Confidentiality breach in case studies**: every customer
    reviews + approves case study before publication.
    Anonymized variants available if customer prefers.

## Resource requirements

### Beta team headcount

  - **Customer Success Manager** (1 FTE for cohort 1 + scales
    to 2 FTE by cohort 3): runs onboarding, feedback collection,
    relationship management.
  - **Product Manager** (0.5 FTE): triages feedback, prioritizes
    roadmap.
  - **Engineering on-call** (0.5 FTE): customer-reported bug
    triage + integration delivery during pilot.
  - **Sales-engineering hybrid** (0.5 FTE): demo support +
    pricing negotiation + contract close.

Total: ~2.5 FTE at peak. Beta team transitions to standard
sales + customer-success motion at GA.

### Beta team budget

  - **Discounts + free access in cohort 1**: $200K opportunity
    cost (3 design partners × $400K list × 4 months / 12).
  - **Cohort 2 pilot fees ($50K each × 8 firms)**: $400K
    revenue offset against ~$1.6M paid value if all converted
    at list. Net reasonable price for what's effectively
    user research at scale.
  - **Onboarding cost in cohort 1**: ~$50K/firm (3 × engineer
    + CSM time × 4 weeks).
  - **Travel + customer events**: ~$50K total.
  - **Tooling (recording / transcription / NPS / Linear)**:
    ~$15K/yr.

Total beta program cost: ~$700K-1M over 12 months. Justified
by the model validation alone (no other path to real-deal
predictor calibration), and the reference customers + early
revenue make it net-positive by GA.

## Communication plan

### Internal

  - Weekly internal beta review (engineering + product + CS
    + sales): cohort progress, blockers, escalations.
  - Monthly beta board update to executive team: cohort
    status, model validation metrics, pricing learnings,
    NPS trends.
  - Quarterly board update: full beta cohort status + GA
    timeline projection.

### External

  - **To beta customers**: dedicated Slack channel per cohort.
    Critical updates via email; nice-to-haves via in-app.
  - **To prospective customers**: 'Beta program now closed
    for cohort N; cohort N+1 applications open' on the
    pricing page. Builds urgency.
  - **To industry**: design-partner case studies published
    quarterly (HFMA conference, healthcare PE LinkedIn,
    industry press).

## Post-beta: graduation to GA

When success thresholds hit:

  - All beta customers transition to standard Pro pricing
    (cohort 1 keeps their negotiated discount; cohort 2-3
    move to list).
  - Marketing campaign announcing GA: 'Healthcare PE
    Diligence Platform Now Generally Available; X firms +
    Y deals analyzed in beta.'
  - Sales motion expands from beta-recruiting to standard
    pipeline; sales reps have referenceable case studies.
  - Pricing page updated with final list prices and beta-
    learning-informed packaging.

## Bottom line

The beta program is the bridge between 'platform that looks good
in synthetic backtests' and 'platform real PE firms underwrite
their deals on'. Twelve months of structured progressive
validation across three cohorts ensures the platform exits beta
calibrated, defensible, and surrounded by reference customers.

Cohort 1 (3 design partners, 4 months, $200K opportunity cost)
is the most expensive but most-leveraged: white-glove
onboarding, deep feedback, formal case studies. Cohort 2 (8-10
firms, validation) tests pricing + workflow at scale. Cohort 3
(15-20 firms, pre-GA) is the load test before list pricing
opens to anyone.

If we ran a single cohort instead, we'd skip the depth of
cohort 1 or the breadth of cohort 3. The three-cohort sequence
is what gets us all four objectives — model + workflow +
pricing + references — within 12 months for ~$700K-1M of
program cost.

The decision: when do we open cohort 1 recruiting? Recommended:
the moment we have at least one passing test of the
forward_distress_predictor + improvement_potential 3-scenario
sweep on a non-synthetic dataset (the recent test_full_pipeline_
10_hospitals.py covers synthetic; we need one real example
before we go to 3 design partners).

That's the gate. Next 4-6 weeks: identify a partner customer
willing to share de-identified portfolio data for a
proof-of-concept calibration. Once that succeeds, beta cohort 1
recruiting opens and the 12-month program begins.
