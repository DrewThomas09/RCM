# pedesk.app — B11 Sweep Walkthrough (last ~24 hours)

**Window:** evening of 2026-05-17 → midday 2026-05-18
**Scope:** PRs #168–#217 (50 page fixes; #217 is the only one still awaiting merge)
**Cumulative sweep total:** PRs #159–#217 = 59 pages migrated to the editorial `ck_page_title` primitive

---

## 1) Top-line counters

| Bucket | Count | Notes |
|---|---:|---|
| Pages on `ck_page_title` (DONE) | **80** of 171 | includes 59 from this sweep + 21 pre-existing |
| Pages with bespoke `<h1 class="ck-page-h1">` remaining | **56** | next-up queue (alphabetical) |
| Pages with `ck_section_header` as de-facto title (no h1) | 26 | shape-2 fix, harder |
| Pages with no h1 at all | 8 | shape-3 fix, pure addition |
| `module_index_page.py` (other shape) | 1 | needs investigation |
| **Total `data_public/*_page.py`** | **171** | |

**Today's coverage gain:** 70 → 80 done = +10 in batch 6
**Total in last 24h:** 31 → 80 done = +49 across batches 2–6

The remaining 91 pages (56 + 26 + 8 + 1) are roughly nine more 10-PR batches at the current cadence.

---

## 2) What every PR does (the contract)

Every PR in this sweep:
1. Replaces a bespoke `<h1 class="ck-page-h1">Title</h1><p class="ck-page-sub">prose</p>` block with `ck_page_title(title, eyebrow=, meta=)`
2. **Title** = preserved from the existing H1 (with documented divergence resolution when docstring/H1 disagree)
3. **Eyebrow** = matched to the page's `editorial_intro` eyebrow so the page-title eyebrow and intro-card eyebrow stay synced
4. **Meta** = substantive rewrite from vocabulary/TOC-style sub-line into a **load-bearing quantitative read** (the partner's answer to "what does this page tell me?")
5. Single-file diff, +8 to +13 lines, smoke-tested
6. Gold-standard pages (`/qoe-memo`, `/provider-economics`, `/ingest`, `/lp-update`) verified untouched

---

## 3) Yesterday evening — batches 2–5 (PRs #168–#207)

**40 pages, alphabetical D–I range.** Each page on pedesk.app is reachable at its `active_nav` route.

### Batch 2 (PRs #168–#177) — late evening cleanup

| # | Route | Page | Meta read pattern |
|---|---|---|---|
| #168 | /deal-flow-heatmap | Deal Flow Heatmap | scope + replaced redundant section header |
| #169 | /coinvest-pipeline | Co-Invest Pipeline | scope + LP commitments |
| #170 | /continuation-vehicle | Continuation Vehicle | scope + GP-led secondary economics |
| #171 | /covenant-headroom | Covenant Headroom | leverage + interest cov + headroom |
| #172 | /covenant-monitor | Covenant Monitor | added entirely (was no-h1 shape) |
| #173 | /cost-structure | Cost Structure | spend + savings opp |
| #174 | /compliance-attestation | Compliance Attestation | attestation count + risk |
| #175 | /cyber-risk | Cyber Risk Scorecard | cyber score + tier + records in scope + insurance |
| #176 | /cms-apm | CMS APM Tracker | active programs + lives + payments + portfolio APM revenue |
| #177 | /cms-data-browser | CMS Public Data Browser | datasets + records + API connections + last refresh |

### Batch 3 (PRs #178–#187) — D pages

| # | Route | Page | Meta read pattern |
|---|---|---|---|
| #178 | /admin/data-sources | Data Sources Admin | sources + scrapers + corpus deals × sectors + vintage |
| #179 | /deal-sourcing | Deal Sourcing / Proprietary Flow | annualized leads → closed LTM + close rate + proprietary mix |
| #180 | /debt-financing | Debt Financing / LBO Commitment | financings + package + **SOFR+bps at Xx leverage** (pricing × leverage fused) |
| #181 | /debt-service | Debt Service Coverage | deal scale + debt × pricing + entry DSCR + stress breaches |
| #182 | /demand-forecast | Demand Forecaster (verb form preserved) | sector + 10-yr visit CAGR + aging tailwind + Medicare share shift |
| #183 | /denovo-expansion | De Novo Expansion Tracker | sites + investment + stabilized EBITDA target + payback |
| #184 | /digital-front-door | Digital Front Door / Patient Experience | portcos + **portal at +NPS** (engagement × sentiment) + telehealth volume × revenue |
| #185 | /diligence-vendors | Diligence Vendor Directory | vendors × categories + Tier 1 share + spend × NPS + pipeline |
| #186 | /direct-employer | Direct-to-Employer Contract Analyzer | employers × lives + **revenue × PMPY fused** + COE margin + pipeline |
| #187 | /direct-lending | Private Credit / Direct Lending | outstanding × facilities + **all-in × leverage fused** + cov-lite + HC default × watch-list |

### Batch 4 (PRs #188–#197) — D–F pages

| # | Route | Page | Meta read pattern |
|---|---|---|---|
| #188 | /dividend-recap | Dividend Recap Analyzer (verb form preserved) | EV + **Xx → Yx deleveraging arrow** + max dividend + recommended structure |
| #189 | /dpi-tracker | DPI / Distribution Tracker | funds + DPI × TVPI fused + below-benchmark count + active LP liquidity requests |
| #190 | /drug-pricing-340b | 340B Drug Pricing Analyzer | covered entities + **$X drug spend → $Y ceiling savings** + program margin + audit risk |
| #191 | /drug-shortage | Drug Shortage / Supply-Chain Risk Tracker | active shortage ratio + sole-source $ + probability-weighted shortfall + risk score × tier |
| #192 | /earnout | Earnout & Contingent Consideration Analyzer | base + max earnout + **Xx headline → Yx effective paid** multiple-gap arrow |
| #193 | /escrow-earnout | Escrow & Earnout Tracker | deals + total contingent (escrow + earnout + milestones) + 12mo release + claims |
| #194 | /esg-dashboard | ESG / Sustainability Dashboard (scope expansion preserved) | sector + ESG score + E/S/G pillar shorthand + LP disclosure gaps |
| #195 | /esg-impact | ESG / Impact Reporting Tracker | portcos × score × YoY + charity care + emissions × SBTi-validated + frameworks |
| #196 | /exit-readiness | Exit Readiness Index | score + critical gaps + gap-closure spend + days to ready + target pathway |
| #197 | /fraud-detection | Fraud / Waste / Abuse Detection Panel | anomalies (with high-sev) + exposure if sustained + FWA score × tier + compliance events |

### Batch 5 (PRs #198–#207) — F–I pages

| # | Route | Page | Meta read pattern |
|---|---|---|---|
| #198 | /fund-attribution | Fund Performance Attribution | MOIC/IRR + **operational + multiple expansion + leverage** trio inline |
| #199 | /fundraising | Fundraising / LP Pipeline Tracker | active funds + **hard-circled × completion-rate fused** + LPs in pipeline |
| #200 | /geo-market | Geographic Market Analyzer | sector + CBSAs × addressable pop + **N priority / N watch / N secondary / N avoid** tier decomposition + top market |
| #201 | /gpo-supply | GPO / Supply Chain Savings Tracker | annual spend × deals + **savings $ × rate fused** + rebate capture + bulk-buy initiatives |
| #202 | /growth-runway | Growth Runway Analyzer | **double arrow: TAM → SAM → SOM AND current% → target%** + upside × MOIC lift |
| #203 | /hcit-platform | HCIT / SaaS Platform Analyzer | ARR × growth + NRR × gross margin + **Rule of 40 + Magic Number** (SaaS canon) + TAM |
| #204 | /health-equity | Health Equity / SDOH Scorecard | attributed lives × LIS/Dual + HEI score + **$X investment → $Y Star bonus** + disparity-flagged |
| #205 | /hospital-anchor | Hospital Anchor Contract Tracker | contracts × value (exclusive folded in) + stipends + renewal probability + expiring + at-risk |
| #206 | /ic-memo-gen | Investment Committee Memo Generator (acronym expansion preserved) | deal × sector + EV × multiple + **base MOIC/IRR → probability-weighted** + memo metadata |
| #207 | /insurance-tracker | Insurance & Malpractice Tracker (scope expansion + & escape preserved) | sector + spend × cost-burden + limits / open reserves + deal-tail (+ hardening) |

---

## 4) Today — batch 6 (PRs #208–#217)

**10 pages, alphabetical K–M range.**

| # | Route | Page | Meta read pattern |
|---|---|---|---|
| #208 | /key-person | Key Person & Clinical Concentration Risk (scope expansion + & escape preserved) | sector + concentration score + high-risk persons + **$X revenue at risk → $Y EV impact** + mitigation cost |
| #209 | /lbo-stress | LBO Model Stress Test | purchase × entry × leverage + **base MOIC/IRR → probability-weighted** + top sensitivity driver + drivers stressed |
| #210 | /litigation | Litigation Watchlist Tracker | open matters + **$X alleged → $Y net (after insurance + SPA indemnity)** + $5M+ concentration + reg / class action counts |
| #211 | /locum-tracker | Locum & Contract Workforce Tracker (& escape) | sector + **$X locum = N% of $Y labor** + contract FTE + coverage gaps + conversion savings |
| #212 | /lp-dashboard | LP Portfolio Dashboard | deals + EV deployed + **Xx gross MOIC / Y% gross IRR → Zx net / W% net IRR** + TVPI/DPI + loss/home-run rate |
| #213 | /lp-reporting | LP Reporting Dashboard | reporting quarter + funds × AUM + blended TVPI/DPI/IRR + top-quartile vs PitchBook |
| #214 | /ma-contracts | Medicare Advantage Contract Analyzer | MA lives × bid PMPM (in benchmark context) + revenue/margin + Stars × MLR + **V28 headwind offset by RAF + Star bonus** (NEW pattern: headwind-vs-offset) |
| #215 | /ma-star | Medicare Advantage / Star Ratings Tracker | MA plans × lives + avg ★ + 4+★ share + **N improved / N declined** (NEW pattern: movement read) + portfolio MA rev vs RADV exposure |
| #216 | /medicaid-unwinding | Medicaid Redetermination / Coverage Unwinding Tracker | portcos + **pre-PHE lives → disenrolled (rate)** + revenue impact **offset by** preservation (first PR to combine arrow + headwind-vs-offset) |
| #217 | /medical-realestate | Medical Real Estate / MOB Tracker *(awaiting merge)* | properties × sqft + **REIT trinity: $X value generating $Y rent at Z% cap** + lease × NNN + investment-grade rent share |

---

## 5) Editorial patterns deployed (full catalogue)

Every PR in the sweep has anchored its meta read on one or more recognizable patterns. The catalogue grew through the sweep as new shapes emerged.

### A) Transformation arrow — `X → Y` (single input → output)
The most-reused device. Use when the page is fundamentally about a transformation.

| Pattern | Example PR | Meta clause |
|---|---|---|
| Deleveraging arrow | #188 dividend_recap | `Xx → Yx leverage` |
| Savings arrow | #190 drug_pricing_340b | `$XM drug spend → $YM ceiling savings` |
| Multiple-gap arrow | #192 earnout | `Xx headline → Yx effective paid` |
| Investment → bonus | #204 health_equity | `$XM equity investment → $YM Star bonus potential` |
| Base → probability-weighted | #206 ic_memo_generator, #209 lbo_stress | `base Xx MOIC / Y% IRR → probability-weighted Zx / W%` |
| Cause → effect | #208 key_person | `$X revenue at risk → $Y EV impact` |
| Defense reduction | #210 litigation_tracker | `$X alleged → $Y net (after insurance + SPA indemnity)` |
| Gross → net haircut | #212 lp_dashboard | `Xx gross MOIC / Y% IRR → Zx net / W% net IRR` |
| Disenrollment arrow | #216 medicaid_unwinding | `XM pre-PHE lives → YM disenrolled (Z% rate)` |

### B) Double arrow — two complementary lenses on the same question
| Example PR | Construction |
|---|---|
| #202 growth_runway | `TAM → SAM → SOM` AND `current% → target%` |

### C) Headwind-vs-offset — two opposing forces being reconciled
| Example PR | Construction |
|---|---|
| #214 ma_contracts | `$X V28 headwind offset by $Y RAF + $Z Star bonus opportunity` |

### D) Movement read — year-over-year directional change across a population
| Example PR | Construction |
|---|---|
| #215 ma_star_tracker | `N improved / N declined in 2026 cycle` |

### E) Combined arrow + offset — first deployed PR #216
| Example PR | Construction |
|---|---|
| #216 medicaid_unwinding | disenrollment arrow AND revenue impact `offset by` retention preservation |

### F) Domain-canonical fusions — multi-stat clusters that partners read as one identity
| Cluster | Example PR | Why fused |
|---|---|---|
| SaaS canon (Rule of 40 + Magic Number) | #203 hcit_platform | Every SaaS investor reads these together as platform quality |
| LP gross→net haircut | #212 lp_dashboard | Net is the only number LPs actually receive |
| REIT trinity (value × rent × cap rate) | #217 medical_realestate | The three numbers that define any real-estate investment |
| ESG E/S/G pillar shorthand | #194 esg_dashboard | Recognized ESG convention; three numbers read as one composite |
| Attribution component trio (operational / multiple expansion / leverage) | #198 fund_attribution | The "where did the return come from?" answer |

### G) Tier / distribution decomposed inline
When a page's whole point IS the ranking output, serialize the full distribution inline rather than burying behind a chart.
| Example PR | Construction |
|---|---|
| #200 geo_market | `N priority / N watch / N secondary / N avoid` |

---

## 6) Title-divergence handling (5 resolution types)

Every page is checked against its module docstring and existing H1 before queueing. Five types of divergence emerged; resolution rules:

| Type | Example PR | Resolution |
|---|---|---|
| **No divergence** (most pages) | majority | Mechanical swap |
| **Verb form** (docstring noun, H1 verb) | #182, #188, #192 | Preserve H1's "Analyzer" / "Forecaster" / etc. — it's the partner-visible tool name |
| **Word restoration** (H1 dropped a word from docstring) | #191, #197 | Restore the docstring word (Tracker / Panel — codebase convention) |
| **Acronym expansion** (H1 expanded acronym) | #206 | Preserve H1's expanded form ("Investment Committee" vs "IC") |
| **Substantive scope expansion** | #194, #207, #208 | Preserve H1; expansion honestly reflects broader scope |

Browser-tab title (`chartis_shell(..., title=)`) is always left alone — the divergence resolution only affects the in-page H1.

---

## 7) Ampersand escape pattern (4 PRs)

When a bespoke H1 contained `&amp;` (or raw `&`), the new code passes **raw `&`** to `ck_page_title` because the primitive's internal `_esc()` produces the single escape. Pre-escaping would double-escape (`&amp;` → `&amp;amp;`).

Smoke tests assert both directions:
- `"Title &amp; Something"` present (single-escape correct)
- `"Title &amp;amp;"` absent (double-escape signature)

PRs that handled this: #192 earnout, #193 escrow_earnout, #207 insurance_tracker, #208 key_person, #211 locum_tracker.

---

## 8) XSS guards verified

For any interactive page that interpolates user input (`sector`, `platform`, `pathway`, etc.) into the meta, smoke-tested with `<script>alert(1)</script>` payload and asserted escaped to `&lt;script&gt;` in the rendered page-title region.

PRs with XSS guards: #182, #190, #194, #200, #206, #207, #208, #211.

---

## 9) Bundled refactors (code-health bonuses)

Several PRs factored inline `sum()` calls out of KPI blocks into named locals (because the meta also needed them). The bundling also added divide-by-zero guards on indexed accesses.

| PR | Factored local | Bonus |
|---|---|---|
| #181 debt_service | `stress_breaches` | removed inline sum from KPI block |
| #185 diligence_vendors | `tier_1_count` | removed inline sum from KPI block |
| #187 direct_lending | `latest_hc_default_pct`, `watch_count` | added empty-list safety on `r.defaults[-1]` |
| #208 key_person | `high_risk_count`, `critical_gap_count` | removed inline sums |
| #216 medicaid_unwinding | `disenroll_rate` | divide-by-zero guard |
| #217 medical_realestate | `ig_share_pct` | divide-by-zero guard |

---

## 10) Sweep state right now

```
Total data_public/*_page.py:           171
  ck_page_title (DONE):                 80  ← +49 in last 24h
  bespoke_h1 remaining:                 56  ← next-up alphabetical queue
  section_header_only:                  26  ← shape-2 (later)
  no_h1:                                 8  ← shape-3 (later)
  other:                                 1  ← module_index_page (investigate)
```

**Estimated remaining work:** 56 bespoke_h1 + 26 section_header + 8 no_h1 = **90 pages**, at the current 10-PR-per-batch cadence ≈ 9 more sessions.

---

## 11) Next-up queue (batch 7 candidates — verify before committing)

The 10 alphabetical bespoke-H1 pages after `medical_realestate`:

1. mgmt_comp_page.py
2. msa_concentration_page.py
3. nav_loan_tracker_page.py
4. nsa_tracker_page.py
5. operating_partners_page.py
6. partner_economics_page.py
7. patient_experience_page.py
8. payer_concentration_page.py
9. payer_contracts_page.py
10. payer_shift_page.py

**Verification step before queueing batch 7:** run the upfront divergence audit (script embedded in `B11_SWEEP_HANDOFF.md`) to catch any false positives or title divergences before starting the per-PR work.

---

## 12) Where things sit (handoff summary)

- **PR #217 medical_realestate**: opened, awaiting merge. Once merged, the count is 81 done / 55 bespoke_h1 remaining.
- **No other in-flight PRs**.
- **`B11_PEDESK_WALKTHROUGH.md`** (this file): at repo root alongside `B11_SWEEP_HANDOFF.md`. Both are untracked — commit them if you want them in git.
- **`B11_SWEEP_HANDOFF.md`**: end-of-day handoff doc from last night (covers patterns + process notes + tomorrow-morning recipe). Still current.

---

## 13) Verify-on-pedesk checklist (UI smoke)

For any page in the table above, open `pedesk.app{route}` and verify:

- [ ] H1 reads as documented in column 3 of the relevant batch table
- [ ] Below the H1 is a small mono "meta" row with the load-bearing read described in column 4
- [ ] Above the H1 is a small mono eyebrow (uppercase, letter-spaced) matching the page's existing intro-card eyebrow
- [ ] No legacy `.ck-page-h1` / `.ck-page-sub` styling visible
- [ ] On interactive pages, changing the form params re-renders the meta with the new scenario values
