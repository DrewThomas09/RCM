# Competitive Landscape — Healthcare PE Intelligence

The healthcare PE diligence + intelligence space has no dominant
incumbent. Customers cobble together 4-7 tools to do what one platform
should: deal sourcing + diligence math + IC memos + portfolio
monitoring. This document maps the players, scores them honestly on
strengths, and lays out where the platform wins each head-to-head.

## Categorization

Five distinct competitor categories, each with a different value
proposition and customer overlap pattern:

  1. **Healthcare-specific data platforms** — sell data feeds +
     dashboards into healthcare PE shops. Strongest on claims +
     provider data; weakest on the diligence workflow.
  2. **Generic PE platforms** — Bloomberg + PitchBook + CapIQ +
     DealCloud — broad market coverage; healthcare PE uses them
     alongside but they don't go deep on healthcare specifics.
  3. **Healthcare M&A advisory tools** — sell-side bankers'
     research feeds; useful when buying *from* a banker but not
     core to PE workflow.
  4. **Internal builds** — many large PE shops build their own
     Snowflake + Python warehouse. Cheap on incremental cost,
     expensive on infrastructure + retention.
  5. **Point solutions** — single-purpose tools (RCM-specific
     analytics, cohort builders, regulatory trackers) — adjacent
     not direct.

The platform sits at the intersection of categories 1, 2, and 4 —
healthcare-specific depth + diligence-workflow integration + a
build-it-once-not-per-firm cost structure.

## Direct competitors (healthcare-specific)

### Trilliant Health

**Position**: Healthcare-specific market intelligence platform.
Provider rankings, market share, patient flow analytics.

**Strengths**:
- Strong patient-journey + provider-affiliation data ($25-100K/yr
  feed)
- Modern UX; popular with health-system M&A teams
- Marketing-led brand recognition in healthcare PE

**Weaknesses**:
- Database, not an analytics platform — no ML predictors, no
  EBITDA bridges, no IC memo generation
- Customers still need to do their own diligence math
- Pricing rises sharply with feed depth

**Head-to-head**: Customer using Trilliant for provider data
likely keeps Trilliant + adds our platform. Not a replacement —
adjacent. We position as *the analytical layer* on top of
Trilliant's data; we accept a Trilliant license pass-through
in our Enterprise tier.

### Definitive Healthcare

**Position**: Provider data + healthcare market intelligence.
Recently public via SPAC; ~$200M ARR.

**Strengths**:
- Deepest provider affiliation database in market
- 200+ partner shops use them; well-known in PE healthcare
- Strong sales motion to healthcare PE

**Weaknesses**:
- Same analytical-shallowness as Trilliant — they're a data
  vendor, not a workflow platform
- Pricing $50-200K/yr per customer; expensive at small shops
- Public-company financial pressure → margin squeeze + roadmap
  slower

**Head-to-head**: Same dynamic as Trilliant — adjacent, license
pass-through. Definitive has the data; we have the math layer
that turns it into an IC memo.

### Komodo Health / IQVIA / Truven (commercial claims)

**Position**: Massive commercial-claims feeds. Used by
pharmaceutical companies + healthcare investors for population-
level analytics.

**Strengths**:
- Ground-truth commercial claims (the data the platform's
  predictors would benefit most from — per the data
  acquisition strategy)
- Established licensing programs

**Weaknesses**:
- $250K-1M/yr licenses; only the largest funds afford
- Claims data alone doesn't make a diligence platform
- Each one is a feed, not an analyst workflow

**Head-to-head**: Customer-licensed pass-through is our model
(per the data acquisition strategy + business model plans).
The platform consumes their data; we don't compete on the
data layer.

### Olive AI / Notable / Cedar (RCM-focused healthtech)

**Position**: Operational RCM software for healthcare providers.

**Strengths**:
- Deep operational integrations with EHRs
- Sold to providers, not investors

**Weaknesses**:
- Different buyer (CFO of a hospital, not investor in
  hospital)
- Operational tools, not analytical/diligence tools

**Head-to-head**: Not direct competitors. We analyze RCM at the
asset level for diligence; they execute RCM at the asset level
for operations. Sometimes our customers' portfolio companies
buy *their* tools.

## Direct competitors (generic PE — used in healthcare deals)

### PitchBook

**Position**: Comprehensive private-market deal database. The de-facto deal-comp source.

**Strengths**:
- Deepest deal-comp database in private markets
- Standard tool every PE shop subscribes to ($25-50K/seat/yr)
- Strong API + Excel plugin
- Cross-industry (not healthcare-specific)

**Weaknesses**:
- Not a diligence tool — it's a database
- Healthcare-specific overlay is shallow (sector tags only)
- No ML predictions, no EBITDA bridges, no peer benchmarking
  for healthcare-specific KPIs
- Doesn't tell you *whether* a deal is good — just what
  comparable deals priced at

**Head-to-head**: Customers keep PitchBook for the deal-comp
data; add the platform for the analytical work. We position
explicitly *not* as a PitchBook replacement: 'PitchBook tells
you what deals priced at; we tell you whether the deal makes
sense for your fund.'

### S&P Capital IQ (CapIQ)

**Position**: Deep public + private financial data; company filings + multiples + estimates.

**Strengths**:
- Comprehensive public-company financials
- Strong Excel integration
- Trusted brand

**Weaknesses**:
- Public-company-centric; private healthcare deals are mostly
  private-company
- Healthcare verticalization is shallow
- Per-seat pricing comparable to PitchBook ($15-25K/yr)

**Head-to-head**: Same as PitchBook — adjacent data tool;
customers use both.

### DealCloud (Intapp)

**Position**: PE-specific CRM + pipeline management.

**Strengths**:
- Most-used PE CRM (~30% of mid-market PE)
- Strong workflow + permissions + reporting
- Healthcare PE has a known DealCloud preset

**Weaknesses**:
- CRM, not analytics
- No diligence math, no predictions, no comp engine
- ~$40-80K/seat/yr pricing

**Head-to-head**: Adjacent. Per the integrations plan, we sync
bidirectionally with DealCloud. Customer keeps DealCloud as
pipeline source-of-truth; platform is the analytical layer.

### Affinity

**Position**: Relationship-intelligence CRM. Tracks who knows whom across the firm.

**Strengths**:
- Relationship graphs across email + calendar
- Useful for sourcing deals via warm intros

**Weaknesses**:
- Sourcing tool, not diligence tool
- Healthcare specifics absent

**Head-to-head**: Adjacent; doesn't overlap with our value prop.

### iLEVEL (S&P) / Allvue

**Position**: PE portfolio management — KPIs, LP reporting,
ILPA-aligned.

**Strengths**:
- Deep LP-reporting feature set; ILPA 2.0 ready (per the
  regulatory roadmap)
- Standard portfolio management for PE
- Mature audit + compliance posture

**Weaknesses**:
- Post-close, not deal-flow
- No analytical / predictive capability — they track what
  happened, not what's likely to happen
- Expensive ($150-500K/yr per fund)

**Head-to-head**: Adjacent at first; expansion target later.
Per the integrations plan, we offer iLEVEL/Allvue sync at
Enterprise tier so portfolio data flows into the platform's
prediction backtests (closes the learning loop, per learning
loop plan).

## Healthcare advisory + research tools

### Bloomberg / Bloomberg Healthcare

**Position**: Broad financial data terminal with healthcare overlay.

**Strengths**:
- Universal financial data tool ($24-30K/seat/yr)
- Strong news + research + macro
- Healthcare equity research from analysts

**Weaknesses**:
- Public-equity-focused; private healthcare deals are
  underserved
- Healthcare overlay is shallow vs healthcare-specialist tools
- No private-market deal data

**Head-to-head**: Healthcare PE shops have Bloomberg for macro
context; the platform is unrelated to that workflow. Not a
direct competitor.

### Mergermarket / Pitchbook deal news

**Position**: M&A pipeline news feeds.

**Strengths**:
- Real-time deal flow news
- Integrated with PitchBook deal database

**Weaknesses**:
- News, not analysis
- Not a workflow tool

**Head-to-head**: Adjacent — PE shops keep these for sourcing
intelligence; the platform analyzes the deals once they're
in scope.

### Provident Healthcare Partners (research)

**Position**: Healthcare-specific PE research firm; publishes
sector reports.

**Strengths**:
- Deep healthcare PE expertise
- Trusted by mid-market healthcare PE shops

**Weaknesses**:
- Service business, not a software platform
- Reports take weeks; no real-time updates
- Doesn't integrate with PE shop workflow

**Head-to-head**: Different category — they're a research
service, we're a platform. Some PE shops use both.

## Internal builds

The most underrated competitor: a PE shop's analyst spending 6
months building a Snowflake + Python warehouse with bespoke
dashboards.

**Strengths**:
- Custom-tailored to the shop's exact deal flow
- No license fees (just analyst time)
- Owns its own roadmap

**Weaknesses**:
- ~$300K-1M of incremental analyst time / year to maintain
- No regulatory tracking, no peer benchmarks, no learning loop
  from other shops' data
- Falls behind quickly as healthcare data sources proliferate
- Risk: when the analyst leaves, the warehouse decays

**Head-to-head**: This is the **biggest direct competitor**. The
sales motion is:

> "Your VP can spend 6 months and $300K building this
> internally. They'd get something that works for your specific
> deal flow but stops improving the day they leave for another
> fund. Or they can spend $400K/yr on the platform that has
> 18 months of head-start, integrates with your existing tools,
> and improves every quarter as more customers' actuals feed
> back into the predictors. Build vs buy on a 5-year TCO is
> ~$1.5M build vs ~$2M platform — but the platform delivers
> within 30 days; the build is 6 months of sunk cost before
> first usable output."

## Where we win

The platform's competitive position rests on five differentiators
that no single competitor can match:

### 1. Healthcare-specific depth × diligence-workflow integration

PitchBook + CapIQ + DealCloud are deep on PE workflow but generic
on healthcare. Trilliant + Definitive are deep on healthcare but
shallow on workflow. We're the only platform that goes deep on
both.

This is a genuine architectural moat — bolting healthcare depth
onto a generic PE tool requires understanding HCRIS, payer mix
dynamics, MA economics, regulatory exposure. It's not a feature;
it's a multi-year build.

### 2. Provenance + defensibility-first

Every platform claims 'transparency'. Few deliver it. The
platform's `DataPoint` provenance discipline + `provenance_badge`
UI mean every modeled number has a click-through to source +
methodology + confidence + sample size. That's the IC-defense
property nothing else in the market provides.

### 3. Trained ML predictors with calibrated confidence

PitchBook gives you raw deal comps; CapIQ gives you raw
financials. Neither tells you what the platform's denial rate
predictor + EBITDA bridge + improvement-potential scenario sweep
do — predicted operational metrics for assets you haven't seen,
with calibrated 90% intervals (per the model_quality dashboard).
Generic PE tools simply don't ship this.

### 4. Closed learning loop

Per the learning loop plan, every prediction the platform makes
gets recorded, validated against actuals, and feeds retraining.
After 24 months, the platform's predictors will be calibrated on
deal-level outcomes from every customer (anonymized, aggregated)
— a feedback advantage no point-solution can match without
similar customer scale.

### 5. Pricing model

PitchBook + CapIQ + DealCloud + Definitive Healthcare add up to
~$200K/seat/year for a PE shop running the full stack. Add
Trilliant + Bloomberg and it's $300K+. The platform's $30K/seat/yr
+ usage rider with $200K cap covers ~80% of what those tools do
for ~30% of the cost. The argument isn't 'replace everything' —
it's 'replace 4-5 of those line items and pay less than 1.5×
PitchBook alone for an integrated platform that does the
analytical work the others don't.'

## Differentiation strategy

### Positioning statement

> 'For mid-market healthcare PE shops, we're the analytical
> layer on top of your existing data tools. PitchBook tells
> you what deals priced at. We tell you whether the deal makes
> sense for your fund — with predicted RCM performance, peer-
> benchmarked EBITDA bridge, calibrated confidence intervals,
> and an IC memo your VP can defend.'

### Sales-narrative wedge per competitor

| Competitor | What they say | What we say back |
|---|---|---|
| Trilliant / Definitive | 'We have the data' | 'They sell you the data; we turn it into an IC memo. Use both.' |
| PitchBook / CapIQ | 'We're the standard PE tool' | 'You're keeping PitchBook for deal comps. We're the analytical layer that does the math PitchBook doesn't.' |
| DealCloud | 'We manage your pipeline' | 'You're keeping DealCloud as the pipeline source-of-truth. We sync bidirectionally — DealCloud has the deal; we have the analysis on it.' |
| Internal build | 'We can do it ourselves' | '6 months and $300K to start. Stops improving when your analyst leaves. Our 18-month head-start delivers in 30 days.' |
| iLEVEL / Allvue | 'We track your portfolio' | 'You'll keep them for LP reporting. Our prediction backtests use their actuals to improve every quarter.' |

### What we don't try to be

  - **A CRM**: PE firms have one; we sync, we don't replace.
  - **A data warehouse**: customers' Snowflake instances stay
    where they are; we plug into them via the integration plan.
  - **A pure data feed**: Trilliant/Definitive own that lane;
    we layer analytics on top.
  - **A consulting service**: Provident Healthcare Partners
    occupies that lane; we ship a software product.
  - **A general PE tool**: PitchBook is broader; we're deeper on
    healthcare. Healthcare-PE-specialist positioning beats
    generalist-with-healthcare-tag.

### Strategic moat — what compounds

Three moats are time-investment-only; we deepen them every
quarter:

  1. **Healthcare-specific depth**. Every CMS data source
     ingested + every regulatory rule tracked + every asset
     class added widens the gap to generic PE tools. After
     24 months, a generic PE tool can't catch up without
     hiring 5 healthcare specialists.
  2. **Trained predictor accuracy**. Per the learning loop
     plan, after 36 months of accumulated actuals + overrides,
     the platform's predictors are 92% partner-quality.
     Competitors entering at month 0 are at ~75%.
  3. **Workflow integration footprint**. Each integration
     (Excel, Slack, Datasite, DealCloud) deepens customer
     stickiness — switching cost grows linearly with
     integration count.

The first two moats compound. The third raises the switching
cost. Together they make the platform increasingly hard to
displace once a customer is on it for 12+ months.

## Year-by-year positioning evolution

  - **Year 1**: 'Best healthcare-specialist platform for
    mid-market PE diligence.' Win on depth + IC defensibility.
  - **Year 2**: 'The platform every healthcare PE shop has
    integrated into their workflow.' Win on integration
    network effects.
  - **Year 3**: 'The platform with the most accurate
    healthcare-PE predictors because of the learning loop.'
    Win on data + model quality.
  - **Year 4-5**: 'The category-defining tool for healthcare
    PE diligence.' Win on brand + market share.

## Risk + monitoring

Three competitive risks to watch:

  1. **A generic PE tool acquires a healthcare-specialist data
     vendor**. PitchBook + Definitive Healthcare combination
     would be a category disruptor. Mitigation: depth-of-
     analytics is harder to acquire than data; our learning
     loop + prediction calibration is years ahead of what
     they could ship in a year.
  2. **A healthcare-specialist data vendor builds analytics**.
     Trilliant or Definitive could try to move up-stack.
     Mitigation: they don't have the diligence-workflow design
     experience or the IC-memo + EBITDA bridge muscle.
     Building those takes 18-24 months of healthcare-PE-
     specific product work.
  3. **A new entrant funded by healthcare-specialist VCs**.
     A 'PitchBook for healthcare PE' startup. Mitigation: the
     learning loop's 24-36 month lead in calibrated predictors
     is hard to compress; partners value defensibility, and
     newer entrants take time to earn that trust.

Each quarter, the GTM team reviews:
  - Win/loss vs each named competitor (capture in CRM)
  - New entrants in the space (acquisitions, fundraising
    announcements)
  - Customer requests that might signal a competitor
    feature gap

## Bottom line

The healthcare PE intelligence space has no dominant winner.
PitchBook is generic; Trilliant + Definitive are data, not
workflow; DealCloud is CRM; iLEVEL is post-close; internal builds
are slow and don't scale.

Our positioning is the **healthcare-specialist analytical
workflow platform** that sits at the intersection of every
existing tool category. Customers keep their existing tools;
they add ours for the analytical work nobody else does. That's
a $1B+ TAM the platform is uniquely positioned to address —
not by being broadest, but by being deepest on the dimensions
healthcare PE actually buys for: defensibility, predictive lift,
regulatory tracking, IC-readiness.

The competitive wedge is the depth × workflow combination. The
moat is the learning loop + integration footprint. The brand is
healthcare-PE-specialist, never general-purpose.
