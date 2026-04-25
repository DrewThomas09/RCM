# 10-Minute Demo Script — Healthcare PE Managing Director

**Audience**: Managing Director, healthcare PE firm (mid-market —
$3-15B AUM, 15-40 person team).

**Goal**: by minute 10, the MD believes (a) this platform compresses
their analyst's diligence cycle 2-3×, (b) the analytical depth is
defensible to LP and IC, (c) the price is justified by a single deal.

**Structure**: every minute lands one concrete point. Every screen
shown maps to a real platform surface that has been tested and is
working. No vaporware.

**Pre-demo invariants** (run through these 10 minutes before the call):

  - [ ] `git log -1 --oneline` shows expected head; deployed build
    matches.
  - [ ] `RCM_MC_DASHBOARD=v3 rcm-mc serve --db demo.db --port 8080`
    starts cleanly.
  - [ ] `pytest tests/test_api_endpoints_smoke.py
    tests/test_full_pipeline_10_hospitals.py -q` passes.
  - [ ] Demo deal `demo-aurora` is loaded with full packet (run
    `demo.py --deal demo-aurora` if missing).
  - [ ] `/?v3=1`, `/deal/demo-aurora/profile`, `/data/catalog`,
    `/models/quality`, `/api/global-search?q=denial` all return 200.
  - [ ] Browser tabs pre-opened in this order:
        Tab 1 — `/?v3=1` (dashboard)
        Tab 2 — `/deal/demo-aurora/profile`
        Tab 3 — `/models/quality`
        Tab 4 — backup `/data/catalog` if MD asks about data depth
  - [ ] Network: hot-spot off; use ethernet if possible. WiFi flake
    has killed more demos than bad code.
  - [ ] Screen-share resolution: 1280×800; the platform's responsive
    layout looks best at this width.

---

## Minute 0:00-1:00 — Hook + framing

**Open on Tab 1 (`/?v3=1` dashboard)**. The morning view is already
visible.

> "Before I show you anything, one number. The average healthcare PE
> deal at your fund size sees 4-8 hours of analyst time on the CIM
> alone — typing numbers into spreadsheets. That's the *first*
> hour of work, and it's the most mechanical. By the end of these
> 10 minutes I'll show you how that becomes 30 minutes — and the
> other 7 hours go to actual analysis.
>
> Behind me is the morning view. This is what your VP opens at 7 AM."

Point at the hero strip: *5 active deals* / *$2.5B NPR* / *$245M
EBITDA* / *health 78/100*.

> "Four numbers. Then a one-sentence read on portfolio posture —
> 'good shape; focus on growth plays'. Then top opportunities,
> active alerts, recent activity. The whole portfolio in one
> screen."

**Why this works**: The MD has seen Bloomberg-style wall-of-widgets
dashboards a thousand times. The narrative read ("good shape; focus
on growth plays") is jarring in a good way — it's the partner's own
language, not a metric grid.

---

## Minute 1:00-3:00 — Screening: from universe to short list

> "Now — your VP has a target list. They came to a banker dinner
> last night, the banker mentioned three asks. Here's the universe."

**Click into the screening view** (or use search bar at top:
`/` → type "ASC suburban Texas" → hit enter → you land on a filtered
universe of ~30 deals).

> "Filter by sector, size, region, predicted EBITDA uplift,
> confidence band. This filter — '$10-50M EBITDA, ASC, Texas, ≥60%
> confidence' — narrows from the ~5,000 universe to 12 candidates."

Sort by predicted uplift descending. Top 3 deals are visible.

> "Each row is a prediction the platform stands behind. Look at
> this top one: predicted EBITDA uplift $8.5M, confidence high,
> top 3 risk factors flagged. That prediction comes from a Ridge
> regression trained on 47 comparable Texas ASCs with full
> cross-validation — I'll show you the model quality dashboard
> in a minute. The platform tells you the *why* before you ever
> click into the deal."

**Click the top deal** → lands on `/deal/<id>/profile`.

**Why this works**: Most platforms make you start at a single deal.
The starting point here is the *universe* — the screen most PE
shops manage in spreadsheets today.

---

## Minute 3:00-5:00 — Deal profile: investment narrative top to bottom

**Tab 2 already pre-loaded — `/deal/demo-aurora/profile`**.

> "When the VP clicks through, this is what they see. Top to
> bottom investment narrative — the IC memo structure, but live."

Scroll slowly through the 9 sections. Pause on each:

> "01 Entity. Project Aurora — 300-bed acute care in Texas. CCN
> matched to public HCRIS data. Ownership type, fiscal year — every
> field provenance-tagged. Click any number, you see where it came
> from."

Hover over a number — provenance icon shows. Click it. Popover
appears with source: HCRIS / 2024 / CCN 450001 / confidence 1.0.

> "02 Market. Atlanta CBSA — population 6.3M, growing 4% over 5
> years, median income $78K. Composite attractiveness score 0.72.
> The narrative: 'top-tier market for healthcare PE'. That sentence
> changes based on the underlying score — your VP doesn't write
> that prose; the platform does.

Scroll past Comparables.

> "03 Comparables. Five hospitals, ranked by similarity. Each peer
> shows the dimensions where it matched and where it didn't —
> region, bed count, payer mix, teaching status, urban/rural. Your
> VP can defend each comp choice in IC because the *why* is
> visible."

Scroll past Predictions.

> "Here's where it gets interesting. 04 Observed metrics — the
> numbers from the data. 05 Predictions — what the model thinks
> the metrics actually are, with 90% confidence intervals. Where
> partner data and prediction disagree, that's a question to ask
> the seller in diligence."

**Why this works**: 9 sections in 2 minutes is fast — the MD doesn't
read every word. They see the structure: *narrative + provenance +
predictions + uncertainty*. That's the IC memo flow.

---

## Minute 5:00-7:00 — EBITDA bridge: the analytical depth

Scroll to **06 EBITDA Bridge** section.

> "Current EBITDA $30M. Target $42M. The platform's bridge is
> seven RCM levers — denial rate, days in AR, collection rate,
> clean claim rate, cost to collect, first-pass resolution, case
> mix. Each lever has a research-band coefficient — the math your
> partners would do on the back of a napkin, but standardized."

Point at the per-lever bar chart.

> "Denial rate $5M. Days in AR $4M. Collection rate $3M. Total
> $12M of recurring uplift. Plus $14M of one-time working capital
> from AR reduction — kept *separate* from EBITDA so you don't
> double-count cash."

> "Now — your VP doesn't trust the model. They want bull, base,
> bear."

Scroll to **07 Scenarios**.

> "Conservative $8.4M. Realistic $12M. Optimistic $15.6M. These
> aren't pulled from thin air — they're a 70%/100%/130% multiplier
> on the realism factor per lever, calibrated against HFMA case
> studies. You can defend the bear case to IC. You can defend
> the bull case to the LP. You don't have to argue about
> which one is 'right'."

> "And — peer-benchmark gap. The platform asks: where do these
> levers sit vs the top quartile of comparable hospitals? It
> doesn't model unrealistic targets. If a hospital is already at
> peer p75, no uplift is modeled — the bridge just shows zero
> for that lever."

**Why this works**: The MD has seen Excel models. What's different
here is the *defensibility* — every number traces back to a
methodology. Bull/base/bear isn't analyst opinion; it's a calibrated
multiplier the analyst can stand behind.

---

## Minute 7:00-9:00 — IC defensibility + Risk + Actions

**Continue scrolling on the same deal profile**.

> "08 Risks. Two flags on this deal. High commercial concentration
> — 47% of revenue from one payer. Stale HCRIS — last filing was
> FY2023, partner needs to confirm 2024 numbers in management
> meetings."

> "Each flag is severity-coded. The 'high' flag is actionable —
> it maps directly to the next section."

Scroll to **09 Actions**.

> "09 Actions — the diligence questions, ranked by priority. The
> high-severity flag becomes a high-priority question: 'Verify
> CY2025 commercial contract terms before LOI.' The medium flag
> becomes a medium-priority question. The platform doesn't just
> identify risks — it tells your VP exactly what to ask in the
> management meeting."

> "Every one of these traces back. Every number in the memo links
> to a source. Every prediction shows its confidence interval and
> sample size. When IC asks 'where does this number come from',
> your VP clicks through. That's the defensibility I mentioned
> at the start."

**Switch to Tab 3 — `/models/quality`** (briefly).

> "And just so you can verify the math — here's the model quality
> dashboard. Every predictor's CV R², MAE, MAPE, and CI calibration
> against held-out data. We don't claim 90% confidence we can't
> back up. If our intervals say 90%, observed coverage on held-out
> data is between 85-95%. Calibration is honest."

**Switch back to Tab 2**.

**Why this works**: Risk + actions makes the platform *useful in
diligence*, not just analytical. The model quality dashboard is the
"prove it" surface — most platforms don't show their backtesting
publicly because they can't.

---

## Minute 9:00-10:00 — Close

Pause. Switch to the dashboard one more time briefly so the screen
ends on the partner-facing view rather than the technical
backtesting page.

> "Three things to leave you with.
>
> One — your VP just saw a 9-section IC-quality memo on a $300M
> deal in 5 minutes of clicking. Today that's 4-8 hours of typing,
> formatting, and assembling. The platform recovers ~80% of that
> time on every deal.
>
> Two — every number is defensible. Provenance, confidence
> intervals, peer benchmarks, calibrated against held-out data.
> Your IC won't have a meeting where someone says 'I don't trust
> that number'. The receipt is right there.
>
> Three — pricing. $30K per seat per year, plus $5K per
> deep-analysis packet above the first per seat. For a 10-person
> team closing 8 deals annually, that's about $400K total. One
> deal where the VP saves ~30 hours pays for itself.
>
> What I'd love to do next: line up a design partnership. We
> bring the platform live on your data, your portfolio, your
> deal flow — for two months at a steeply discounted rate.
> Your VP and one analyst use it on every live deal in that
> period. End of the quarter, you decide whether the team
> wants to keep it. No long contract."

Pause. Listen for objections. The three most common:

  - "How does this differ from PitchBook / CapIQ?" → "PitchBook is
    a deal-comp database. CapIQ is corporate filings + multiples.
    Neither does the analytical work. We do the diligence math
    on top of the data — the model that predicts denial rate,
    the comp set that defends the multiple, the bridge that
    sizes the value plan. That's the gap they don't fill."

  - "What about data privacy?" → "Single-tenant deployment available
    on Enterprise tier. Your data never leaves your VPC. SOC 2
    Type I prep is in flight; Type II in 8 months."

  - "How long to get up and running?" → "Design partner pilots run
    in 2 weeks. White-glove onboarding for Enterprise — your CSM
    loads your portfolio data + custom predictor calibrations on
    your historical exits. Pro tier is self-serve in an hour."

---

## Things that go wrong (and how to handle)

- **Server flake**: backup tab pre-loaded. If the live page errors,
  switch to the backup. If both fail, you've lost — graceful
  apology + reschedule. *Better to delay than demo broken
  software.*
- **MD asks a question requiring a screen we haven't loaded**:
  always answer with what's already on screen. Saying "let me
  navigate to that" mid-pitch loses momentum. If the question
  is genuinely orthogonal, defer: "Great question — that lives
  in [page]; happy to send a follow-up walkthrough video."
- **MD pushes back on a number**: never argue the number; argue
  the methodology. "The 35% denial-avoidable share comes from HFMA
  research bands published in 2023 — we're calibrating against
  industry consensus, not your shop's specifics. We'd retune that
  parameter on your portfolio data in a design partnership."
- **The full pipeline test breaks**: this is why we ran the
  smoke test pre-demo. If something we showed in tests doesn't
  work live, we have a deeper problem; reschedule.
- **MD looks at watch**: speed up the bridge + scenarios section.
  Skip directly to risks + actions. Save the model quality
  dashboard for follow-up.

---

## What NOT to demo

These exist on the platform but **don't show in the 10-minute slot**:

- **Data catalog** (`/data/catalog`) — too technical; mention only
  if asked about data sources.
- **Feature importance dashboard** — useful but inside-baseball;
  follow-up material.
- **Multi-asset expansion roadmap** — slide in the follow-up
  pitch after they're interested, not in minute 10.
- **Pricing details** for Enterprise — covered at high level
  ('starting at $150K base'); detailed break-down is
  follow-up sales call.
- **Implementation timeline** beyond the 2-week pilot — keep the
  forward commitment small ('let's pilot, then talk').

The goal of 10 minutes is to earn the next 30-minute follow-up,
not close on the spot.

---

## Post-demo — what to send within 60 minutes

  1. **Recording** of the demo (screen + audio, ~50MB).
  2. **One-pager**: pricing, design partnership terms, security
     posture (SOC 2 status), implementation timeline.
  3. **Calendar link** for the follow-up — defaults: 30 mins next
     week, 90 mins for a deeper deep-dive in 2 weeks.
  4. **Reference contact**: prior design-partner partner (if
     willing). Cold reference > warm sales pitch.

---

## Success metric

A successful demo produces *one of three* outcomes:

  - **Best**: 'Set up the design partnership.' (move to contract)
  - **Good**: 'Send me the recording + bring 2 of my VPs next
    week for a longer session.' (move to expanded discovery)
  - **OK**: 'Stay in touch; ping me in 90 days.' (move to drip
    nurture)

Anything else (silence, vague pleasantries, 'we'll think about it')
is a loss. Don't try to recover in the same call — book the
follow-up explicitly: 'Should I send a 30-minute slot for next
week to talk through any specific deals you'd want to test it
against?' Forces a yes/no.

---

## Final note

Demos that work are calibrated against the audience's actual
pain. The MD's pain isn't 'we don't have analytics' — they have
plenty. Their pain is 'my VP spends 6 hours typing CIMs into
Excel before the actual analysis starts'. The first minute of
this demo names that pain explicitly. The next 9 minutes show
how the platform takes those 6 hours back.

Don't get distracted by features you're proud of. Show the
features that recover analyst time + defend numbers in IC. That's
the buying decision.
