# SeekingChartis — Full Walkthrough Case Study

**A real-world scenario, written so a 9th-grader could follow along.**

This walkthrough puts you in the chair of a private-equity VP evaluating a real hospital acquisition. We'll use every feature of the tool. By the end, you'll have produced a complete investment-committee-ready analysis in under 30 minutes.

If you haven't installed the tool yet, go read [README.md](README.md) section 5 first.

---

## The scenario

You work at **Meadowbrook Capital Partners**, a $4B private-equity fund that specializes in healthcare. Your managing director Sarah sends you an email Monday morning:

> Subject: Urgent — Southeast Health
>
> Banker Citi sent us the book on Southeast Health Medical Center. 353-bed community hospital in Dothan, Alabama. Asking $710M at 10.5× LTM EBITDA. IC needs a first-read Friday. Standard workup please — but flag anything that could kill this in 48 hours. Thanks.
>
> Sarah

Let's get to work.

---

## Step 1 — Discover the target (9:00 AM Monday)

Open your browser to `http://localhost:8080/home`. (Assuming you ran `python demo.py` from `RCM_MC/`.)

You see the SeekingChartis Home page. At the top, there's a panel called **"New Diligence Modules"** — seven colored tiles for the most recent analytic surfaces.

**Click HCRIS Peer X-Ray.**

You land on a search page that says:
> Search by name, CCN, or city substring
> Dataset coverage: 17,701 hospital-year filings across 50+ states

In the search box, type `SOUTHEAST HEALTH` and filter state `AL`. Press Enter.

You see 3 matching hospitals. Click the one with CCN `010001` — that's the target.

---

## Step 2 — Instant peer benchmark (9:02 AM)

The page loads in 25 milliseconds. Here's what you see:

### Hero card
- **SOUTHEAST HEALTH MEDICAL CENTER** · CCN 010001 · FY2022 · Dothan, AL
- Badge: `TREND · DETERIORATING · 3Y` (red chip — instantly alarming)

### KPI strip
| Metric | Value | Notes |
|--------|-------|-------|
| Beds | 353 | Regional cohort |
| Patient Days | 103,997 | 80.7% occupancy |
| Medicare Day Share | 24.9% | moderate |
| NPR (filed) | $427M | $1.2M per bed |
| **Operating Margin** | **−4.4%** | **Negative — red** |
| Payer Diversity | 0.52 | Balanced mix |

### Benchmark grid
Below the hero, five sections (Size / Payer Mix / Revenue Cycle / Cost Structure / Margin). Each metric shows:
- Your target's value
- Peer P25 / Median / P75
- Signed variance %
- Small **sparkline** showing the 3-year trend
- Small **box-plot** showing where the target sits in peer density
- ABOVE PEER / IN-BAND / BELOW PEER chip

Key observations you jot down:
- **Occupancy 80.7%** vs peer median 69.0% — **+17% above peer P75**. Hospital is busy.
- **Operating margin −4.4%** vs peer median +2.1% — **below peer P25**. Losing money.
- **3-year margin trend**: −1.7% → −5.9% → −4.4%. Got worse, slightly recovered.
- **Medicare share 24.9%** vs peer median 20.3% — above P75, more exposed to CMS rate cycle.

### Public market context block
Below that: the Seeking Alpha public-comp block showing target margin vs HCA / THC / UHS / CYH:
- HCA: +16.9% op margin, 8.9× EV/EBITDA
- THC: +11.2%, 8.8×
- CYH: −3.1%, 9.5× (closest public peer to our target)
- Your target trails the public median by **21.3 pp** on operating margin.

**Your first read**: this is a distressed hospital. Banker wants 10.5× but distressed peers trade at 6-9×. Either the banker has a massive turnaround story, or they're pricing in fantasy.

---

## Step 3 — Check the live market (9:10 AM)

On the Working Deal context bar at top of the page (it now carries your deal name + financials), click **Seeking Alpha**.

You see 4 key panels:
1. **Public ticker grid** — 14 healthcare stocks with live EV/EBITDA, analyst consensus, op margin
2. **Sector sentiment heatmap** — green/amber/red by specialty based on curated news
3. **Recent PE transactions** — 12 closed deals with sponsor, multiple, narrative
4. **Sponsor leaderboard** — who's deploying healthcare capital

Relevant data:
- **Multi-site acute hospital PE median**: 8.8× EV/EBITDA (from `category_bands()`)
- Most recent rural acute carve-out: 6.2× (Riverview by Arsenal, 2026-02-28)
- No community hospital deal closed above 9.0× in the last 6 months

**Your second read**: banker's 10.5× ask is above every comparable data point. Counter at 8× or walk.

---

## Step 4 — Set the Working Deal (9:15 AM)

Click **Deal Profile** in the sidebar. Fill the form:

- Target name: `Southeast Health Medical Center`
- Specialty: `HOSPITAL`
- Market category: `MULTI_SITE_ACUTE_HOSPITAL`
- Revenue: `450000000`
- EBITDA: `25000000` (your turnaround assumption — banker claims this, not the −$19M actual)
- EV: `600000000` (your counter-offer)
- Equity: `250000000`
- Debt: `350000000`
- Entry multiple: `9.0`
- Medicare share: `0.45`
- HOPD revenue: `45000000`
- Landlord: `MPT` (real — Southeast Health has an MPT sale-leaseback)

Click submit.

You see the Deal Profile page with 17 tiles organized by phase (SCREENING / DILIGENCE / FINANCIAL). A thin **Working Deal** bar at the top says:
> Working deal: **Southeast Health Medical Center** · $450M NPR · $25M EBITDA · $600M EV · 9.0× entry · HOSPITAL

This bar now follows you to every page. No more retyping deal names.

---

## Step 5 — One-click Thesis Pipeline (9:20 AM)

Click the **Thesis Pipeline** tile. This is the orchestrator — runs 14 analytics in sequence on your deal.

After ~170 ms, you see a report page with:
- **Step log**: 14 rows showing `regulatory_exposure · 3ms · ok`, `covenant_stress · 47ms · ok`, `hcris_xray · 25ms · ok`, `payer_stress · 9ms · ok`, etc.
- **Headline grid**: P50 MOIC, P10 MOIC, IRR, exit recommendation year + buyer, top autopsy match, regulatory verdict, covenant max breach prob, HCRIS trend, etc.
- **Tiles**: one card per sub-module with a deep link carrying all your params.

From the Thesis Pipeline output:
- **Regulatory verdict**: WARNING (2 events will damage drivers in 24-month horizon)
- **Covenant max breach**: 58% (WARNING)
- **HCRIS trend**: deteriorating
- **Autopsy closest match**: Steward Health at 73% similarity (CRITICAL)
- **Exit timing recommendation**: Year 5 to PE Secondary, 19.2% IRR

**Already yellow-flagged on 4 of 7 dimensions.** Not dead, but tight.

---

## Step 6 — Drill into Regulatory (9:25 AM)

Click the Regulatory Calendar deep-link tile.

You see:
- **Verdict: WARNING**
- **Risk score**: 42 (amber — PE norm is 20-50)
- **Headline**: *"Thesis driver 'LEJR bundled-case margin' dies on 2026-01-01 — TEAM Mandatory Bundled Payment impairs 70% of its claimed lift."*

### Gantt timeline
Visual — your thesis drivers on the Y axis, calendar dates on the X axis. Red dots mark KILL events, amber dots mark DAMAGE events.

Two red dots stand out:
1. **2026-01-01** — TEAM bundled payment live → kills LEJR margin driver
2. **2026-04-12** — V28 MA final rule → damages MA margin driver

### EBITDA overlay table
| Year | Revenue Δ | EBITDA Δ | Notes |
|------|-----------|----------|-------|
| 2026 | −$3.6M | −$2.7M | TEAM + OPPS site-neutral |
| 2027 | −$14.1M | −$10.6M | V28 final rule hits |
| 2028 | −$2.4M | −$1.8M | Residual OPPS |
| **5-yr total** | **−$20.1M** | **−$15.1M** | |

This overlay automatically feeds the Deal MC base case (via `reg_headwind_usd`).

---

## Step 7 — Stress test the debt (9:30 AM)

Click **Covenant Stress** in the context bar.

- Form auto-populates from the Working Deal
- Revolver: `40M`, draw `30%`
- Quarters: `20`
- Base rate: `5.5%`
- Leverage ceiling: `7.5×`, step `0.5`/yr
- DSCR floor: `1.25×`
- ICR floor: `1.75×`

Click Run.

Results (~65ms):
- **Verdict: WATCH**
- **Max breach probability: 32%** (amber — inside the 10-25% bank-acceptable band's upper edge)
- **Earliest 50% breach**: never in the 5-year horizon
- **Interest Coverage** most stressed — breach rising from 19% (Y1) to 28% (Y2)

**Debt service cliff chart** shows bullet TLB maturity not kicking in until Y6 (beyond our hold).

**Median equity cure on the ICR path**: $0.3M (immaterial). P75 cure: $1.2M.

**What this tells you**: at 9× entry + 5.8× leverage, covenants are tight but survivable. If banker insists on 10.5× (= 6.8× leverage), covenants likely breach — walk or reprice.

---

## Step 8 — Audit the banker's bridge (9:45 AM)

Click **Bridge Audit** in the context bar.

Paste what Citi sent:
```
Denial workflow overhaul, 4.2M
Coding / CDI uplift, 3.1M
Vendor clearinghouse consolidation, 2.8M
AR aging liquidation, 1.5M
Site-neutral mitigation, 1.8M
Tuck-in M&A synergy, 2.5M
```

Asking price: `710M`, entry multiple: `10.5`, denial rate: `0.095`, MA mix: `0.25`.

Click Run.

### Verdict: MATERIAL
- **Banker's bridge**: $15.9M
- **Realistic bridge (P50)**: $10.6M
- **Gap**: **$5.3M** (33% of claim)
- **Bridge Realization chip**: 67% (below peer band 60-90% — worse than typical)

### Per-lever detail
| Lever | Claim | Realistic | Verdict | Gap | Fail rate |
|-------|-------|-----------|---------|-----|-----------|
| Denial workflow | $4.2M | $4.4M | REALISTIC | −$0.2M | 18% |
| Coding uplift | $3.1M | $2.5M | REALISTIC | +$0.6M | 28% |
| Vendor consolidation | $2.8M | $1.1M | **UNSUPPORTED** | +$1.7M | **42%** |
| AR aging liquidation | $1.5M | $1.2M | REALISTIC | +$0.3M | 15% |
| Site-neutral mitigation | $1.8M | $0.6M | **UNSUPPORTED** | +$1.2M | **48%** |
| Tuck-in M&A | $2.5M | $0.8M | **OVERSTATED** | +$1.7M | 30% |

### Counter-bid recommendation
> **Counter at $654M** (down $55.9M at 10.5× on the gap). **Alternative**: structure $4.6M as a 24-month earn-out triggered at $15.2M LTM EBITDA. Press banker on 'Vendor clearinghouse consolidation' — largest single gap at $1.7M.

Draft your email to the banker:

> *"Citi — before Friday's IC, can you justify the vendor consolidation ($2.8M) and site-neutral mitigation ($1.8M) line items? Our realization analysis on 3,000 comparable RCM initiatives shows these categories realize ≤50% of claim 42% and 48% of the time respectively. Happy to walk through the data."*

---

## Step 9 — Payer mix stress (10:00 AM)

Click **Payer Stress**.

The pipeline auto-built a mix from your Medicare-share input. Paste a refinement:
```
UnitedHealthcare, 22%
Anthem, 20%
Medicare FFS, 25%
Medicare Advantage, 15%
Medicaid managed, 10%
Self-pay, 8%
```

Target NPR: $450M · EBITDA: $25M · 5-year horizon · 300 paths.

Click Run.

### Verdict: WARNING
- **Top-1 payer share**: 25% (below the 30% flag — OK)
- **HHI**: 1,842 (moderately concentrated)
- **Concentration amplifier**: 1.00×
- **P10 cumulative NPR delta**: −$8.4M
- **P10 cumulative EBITDA impact**: **−$5.9M** over 5 years

### Per-payer cards
Each payer gets its own card with median/P10/P90 rate moves + library prior context:
- **UnitedHealthcare (22%)**: median rate move +3.5% over 5 years, P10 −6.2%, P90 +11.8% · Library prior: μ +1.5%, P25 −4.5%, P75 +5.5% per renewal
- **Anthem (20%)**: similar story, but less aggressive repricing
- **Medicare FFS (25%)**: median +11.2% over 5 years (Medicare annual update tailwind)

### NPR impact cone chart
Year-by-year p10/p50/p90 spread. Zero line at the middle. Target shape is a mild downward drift with wide tails.

**What this tells you**: the mix is balanced enough. Worst tail is Medicare Advantage compression + UHC rate cut, but it's $5M/year of EBITDA at risk — manageable if offered as an earn-out concession.

---

## Step 10 — Run the Deal Monte Carlo (10:10 AM)

Click **Deal MC** in the context bar.

Form auto-filled. Set `n_runs` to `500` (fast mode). Click Run.

### Hero stats after 500 trials
| Metric | Value |
|--------|-------|
| **P50 MOIC** | 1.82× |
| P25 MOIC | 1.41× |
| P75 MOIC | 2.29× |
| **P50 IRR** | 12.8% (below 18% hurdle — amber) |
| P(MOIC < 1×) | 18% (amber — fund target is <10%) |
| P(MOIC ≥ 3×) | 11% |

### Revenue + EBITDA fan charts
5-year cones with p10/p25/p50/p75/p90 bands. The regulatory overlay is already subtracted (you can see the dip in 2027 when V28 hits).

### Attribution tornado
Shows which driver moves MOIC most. In order of sensitivity:
1. Exit multiple (±0.6x MOIC per 1× of multiple)
2. EBITDA growth rate
3. Regulatory headwind realization
4. Denial improvement realization
5. Physician attrition

**What this tells you**: exit multiple is the #1 risk. If the hospital sector continues to derate, your P50 exit multiple drops from 9× to 7× and your MOIC drops from 1.82 to ~1.3. Partner should underwrite a 7× exit.

---

## Step 11 — The Bear Case (10:20 AM)

Click **Bear Case**.

The form auto-fills from your Working Deal. Pipeline runs all 14 modules again (the Bear Case consumes pipeline output). ~110ms later:

### Verdict card
> **Thesis is at risk on 7 CRITICAL evidence items — combined $46.8M of EBITDA at risk. Top drivers: Interest Coverage covenant, Net Leverage covenant, deteriorating HCRIS margin trend.**

Below that: **29% of run-rate EBITDA at risk** (IC-killable territory — dark red chip).

### Theme-grouped evidence (partial)
**CREDIT**
- [C1] CRITICAL · Interest Coverage covenant crosses 50% breach in Y1Q1 · $0.8M median cure
- [C2] CRITICAL · Net Leverage covenant reaches 100% breach at Y6Q1 (bullet maturity)

**REGULATORY**
- [R1] CRITICAL · LEJR bundled-case margin killed by TEAM Mandatory Bundled Payment · effective 2026-01-01
- [R2] HIGH · MA margin damaged by V28 final rule · effective 2027-01-01
- [R3] HIGH · $−15.1M cumulative regulatory overlay across horizon

**OPERATIONAL**
- [H1] HIGH · Operating margin trending −2.7 pp over 3 years (FY2020 to FY2022) — from filed HCRIS
- [P1] MEDIUM · Top-1 payer share 25% — moderate concentration
- [B1] HIGH · $5.3M aggregate bridge gap (33% of banker claim)

**PATTERN**
- [A1] HIGH · Signature matches Steward Health (bankruptcy) at 73% similarity

### Copy-paste IC memo block
Below the cards: a print-ready HTML section (dashed border around it) with bold verdict + table of evidence. Click `⌘+P` and it prints as a clean PDF with your IC memo body already filled in.

---

## Step 12 — The IC Packet (10:35 AM)

Click **IC Packet** in the context bar.

You see a formal investment-committee memo:
- **Title**: Southeast Health Medical Center
- **Recommendation**: PROCEED_WITH_CONDITIONS
- **IC date**: today
- **Section 1**: Deal overview (EV, equity check, debt, entry multiple, MOIC / IRR projections)
- **Section 2**: RCM performance summary (cash waterfall + top 4 KPIs)
- **Section 3**: Bankruptcy-Survivor scan verdict
- **Section 4**: Counterfactual sensitivity (which levers matter most)
- **Section 5**: Market context (public comps + transaction multiples)
- **Section 6**: Deal Autopsy matches (Steward, Cano, Envision similarity scores)
- **Section 7**: Diligence checklist status (which items are DONE / OPEN / BLOCKED)
- **Regulatory Timeline** (auto-injected block from Regulatory Calendar)
- **Bear Case** (auto-injected block from Bear Case Auto-Generator)
- **Walkaway conditions** (derived from counterfactual set)

Every number carries a `data-provenance` tooltip explaining the source + formula.

Click JSON Export → you get the full payload as JSON for your model.

⌘+P → clean PDF with print styles applied.

---

## Step 13 — Your final recommendation

After 95 minutes, here's what you send Sarah:

> **Subject: Re: Urgent — Southeast Health**
>
> Sarah — analysis done. Short version: **walk away unless banker accepts $600-630M with $5M earn-out on synergies.**
>
> **Three reasons:**
>
> 1. **HCRIS filings show filed operating margin of −4.4%**, deteriorating for 3 years. Banker's pitched $25M EBITDA is a claim, not reality. Public comps at same margin profile (CYH) trade at 9.5×. Asking 10.5× is irrational.
>
> 2. **Bridge audit flags 3 of 6 synergy levers** (vendor consolidation, site-neutral mitigation, tuck-in M&A) as overstated or unsupported. $5.3M gap. At 10.5× that's $56M of phantom value.
>
> 3. **Covenant stress at 6.8× leverage = 58% breach probability**. At 5.8× (our counter-offer) it's 32%. The difference is the $110M of debt we're NOT going to put on this company.
>
> **Alternative deal structure**: $600M headline + $30M equity earn-out triggered at $25M LTM EBITDA Y2. Preserves sellers' upside if their synergies are real. Protects us if they're not.
>
> Attaching the Bear Case memo + IC Packet. Full evidence: [H1] HCRIS margin trend, [C1] Interest Coverage covenant, [B1] $5.3M bridge gap, [R1] TEAM regulatory kill, [A1] Steward signature match.
>
> Standing by for IC prep.
>
> [Your Name]

---

## What just happened

You used every major feature of the tool:

| # | Feature | Time spent |
|---|---------|-----------|
| 1 | HCRIS X-Ray (peer benchmark) | 10 min |
| 2 | Seeking Alpha (market context) | 5 min |
| 3 | Deal Profile (set working deal) | 5 min |
| 4 | Thesis Pipeline (14-step orchestrator) | 5 min |
| 5 | Regulatory Calendar (event kill-switch) | 10 min |
| 6 | Covenant Stress (debt stress test) | 15 min |
| 7 | Bridge Auto-Auditor (synergy reality check) | 15 min |
| 8 | Payer Stress (rate-shock MC) | 10 min |
| 9 | Deal MC (outcome distribution) | 10 min |
| 10 | Bear Case (evidence synthesis) | 5 min |
| 11 | IC Packet (final memo) | 5 min |
| **Total** | | **95 min** |

Every number is cited. Every module auto-cross-linked. The Working Deal context bar meant you never retyped the deal name.

---

## What you didn't use (but could have)

Other modules that would've added depth if you had more time:

- **Management Scorecard** — score Southeast Health's CEO/CFO/COO for forecast reliability
- **Physician Attrition** — per-NPI flight risk for the top 20 doctors
- **Provider Economics** — per-doctor P&L, find drop candidates
- **Denial Prediction** — ML model on actual claims data
- **Deal Autopsy** — deeper dive on the Steward similarity
- **RCM Benchmarks** — 20+ KPIs with HFMA peer bands
- **Exit Timing** — buyer-type fit analysis (strategic vs PE secondary vs IPO)
- **Diligence Checklist** — 40+ item P0/P1 tracker

Each adds 5-15 minutes and its output auto-slots into the Bear Case + IC Packet.

---

## The workflow shortcut you found

The **Working Deal context bar** at the top of every page was the unsung hero. Once you set the deal on Deal Profile, it followed you everywhere. Params never re-typed. Clicking Covenant Stress from Bridge Audit preserved your deal identity.

The **Thesis Pipeline** was the other shortcut. Running that one tile invoked 14 sub-modules in order, gave you the whole picture, and deep-linked back to each one if you wanted to dig deeper.

**Partners used to spend 2-3 weeks on this kind of analysis.** You did it in 95 minutes before lunch.

---

## Take it further

- Change the hospital in Step 1 — try any CCN from the HCRIS search
- Run the same workflow against a successful deal (e.g. a hospital with healthy margins) to see what a PASS verdict looks like
- Check `/diligence/deal-autopsy` to see the 12 historical failure library
- Call the Python API directly: `from rcm_mc.diligence.thesis_pipeline import run_thesis_pipeline, PipelineInput`

---

*Return to [README.md](README.md) for installation + module reference.*
