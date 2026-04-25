# 6-Month Product Roadmap

**Window:** 2026-05-01 → 2026-10-31
**Author:** product
**Status:** draft v1
**Supersedes:** none — feeds NEXT_CYCLE_PLAN.md, BETA_PROGRAM_PLAN.md, V2_PLAN.md

---

## TL;DR

Two quarters, one mission: **get one paid pilot, on real data, with calibration evidence.**

- **Q2 2026 (May–Jul):** Pre-beta hardening. Calibrate one predictor on real closed-deal labels. Ship Tier-1 PHI controls. Recruit and sign 3 design partners.
- **Q3 2026 (Aug–Oct):** Run Cohort 1. Ship multi-tenancy. Calibrate two more predictors. Open Cohort 2 recruiting in October.

Everything outside that path — multi-asset expansion, public API, v2 refactor, integrations — is **explicitly cut** from the 6-month window. Rationale at the bottom.

---

## Velocity assumptions

Be honest. Past velocity in this codebase has been driven by an autonomous loop running ~50 small directives per cycle. **Real-team velocity is lower** because of the things the loop doesn't do: customer calls, hiring, contracts, debugging on someone else's data, partnership meetings, fundraising, illness, holidays.

Realistic capacity for the 6-month window:

| Resource | Q2 2026 | Q3 2026 |
|---|---|---|
| Founder/eng (1.0 FTE) | 100% — split 60% build / 25% sales+CS / 15% ops | 80% — split 50% build / 35% sales+CS / 15% ops |
| Eng hire #1 | not yet | starts ~Aug 1, ramps Q3 (effective 0.4 FTE) |
| Design (contract) | ~0.2 FTE for cohort UI polish | ~0.3 FTE |
| Total build capacity | **~0.6 FTE** | **~0.9 FTE** |

Working days, after holidays/sick/conf travel: ~58 days Q2, ~62 days Q3.

**Throughput rule of thumb (1 build FTE):**
- 1 large surface (3–4 weeks): redesigned page + data layer + tests
- 1 medium (1–2 weeks): new model with calibration + UI + tests
- 4 small (<3 days): bug fixes, copy, polish, single endpoint

So at 0.6 FTE for Q2: roughly **1 large + 1 medium + 4 small** ships per quarter, plus a 20% buffer for slippage. Q3 with the new hire ramping: **1 large + 2 medium + 6 small**.

**Slippage budget:** plan to lose one medium feature per quarter. If you don't, pull the next one forward.

---

## Q2 2026 — Pre-beta hardening (May 1 → Jul 31)

**One sentence:** by July 31, we have signed paperwork with 3 design partners, BAA-ready PHI controls, and at least one predictor calibrated against real closed-deal outcomes.

### Sprint plan (4 sprints × ~2 weeks)

#### Sprint 1 (May 4–15) — Calibration harness

Critical-path work for everything downstream.

- **Ship:** `rcm_mc/ml/calibration_harness.py` — accepts (model_name, deal_id, predicted, actual, as_of) tuples, persists to `calibration.db`, computes rolling MAE / MAPE / coverage by cohort, emits a `/models/calibration/<name>` page reusing `power_table` + `power_chart`.
- **Ship:** label-ingest CLI for closed deals — pulls from a structured `closed_deals.csv` template, validates, dry-run report, then commit.
- **Why now:** BETA_PROGRAM_PLAN.md gates Cohort 1 recruiting on "≥1 non-synthetic predictor passing calibration." This is the gate.

#### Sprint 2 (May 18–29) — First real-data predictor

- **Ship:** wire the **denial rate predictor** to real labels. Pick this one because (a) labels are easiest to source from RCM logs, (b) coefficients are already research-banded, (c) it's the predictor most likely to drive a real IC decision.
- **Ship:** add `provenance: "real-cohort-N"` vs `"synthetic-priors"` flag throughout the predictor surface. Every UI that shows a predicted denial rate gets a badge.
- **Cut from sprint if needed:** the synthetic→real swap on a second predictor. That moves to Q3.

#### Sprint 3 (Jun 1–12) — PHI Tier 1

From PHI_SECURITY_ARCHITECTURE.md, the **minimum** for design-partner BAAs:

- **Ship:** per-tenant SQLite database + filesystem isolation under `tenants/<tenant_id>/`.
- **Ship:** audit log table — every read/write of a PHI-tagged column, append-only, with WHO/WHAT/WHEN.
- **Ship:** secrets out of the repo — move to `.env` + `keychain`/macOS, document for hires.
- **Ship:** `docs/BAA_TEMPLATE.md` ready for legal review.
- **Cut from Tier 1:** SOC 2 Type II (12-month process), encryption-at-rest beyond filesystem (defer to Q4), customer-managed keys (defer 12+ months).

#### Sprint 4 (Jun 15–26) — Onboarding kit

- **Ship:** design-partner onboarding workbook (data dictionary, week-1 plan, week-2 plan, IC alignment session script).
- **Ship:** `python -m rcm_mc.tenants.bootstrap <tenant_id>` — provisions tenant DB, seeds reference data, opens browser to first-run wizard.
- **Ship:** kill switch — `ADMIN_DISABLE_TENANT=<id>` env that returns 503 on all surfaces for that tenant. Necessary for incident response before we have proper feature-flag infra.

#### Buffer (Jun 29 – Jul 10) — Slippage absorption + Cohort 1 sales

This block is **not for new features.** It exists because the prior 4 sprints will overrun by something. Use it for:
- finishing whichever sprint slipped
- 8–12 design-partner sales conversations (target: 3 signed)
- redlines on BAAs from the first design partner's counsel

#### Sprint 5 (Jul 13–24) — Cohort 1 kickoff

- Onboard design partner #1 (white-glove, half a week of pair work).
- Bug-bash sprint: every issue partner #1 hits in week 1 gets fixed in week 1.
- Stand up the in-app feedback widget (one-line text + screenshot capture, persists to `feedback.db`).

#### Sprint 6 (Jul 27–31) — Cohort 1 lessons

- Retro doc: what design partner #1 found that we didn't anticipate.
- Roadmap adjustment for Q3 based on findings (this is **expected** to happen).

### Q2 deliverables checklist

- [ ] Calibration harness shipped, page live at `/models/calibration/<name>`
- [ ] Denial rate predictor calibrated on ≥30 real closed deals, MAE within research band
- [ ] Tier-1 PHI controls: per-tenant isolation, audit log, secrets management
- [ ] BAA template approved by external healthcare counsel
- [ ] 3 design partners signed (at least 1 onboarded by Jul 24)
- [ ] In-app feedback widget shipping events
- [ ] One eng hire signed, start date ≤ Aug 15

### Q2 explicit non-goals

- Multi-tenancy with auth (Q3)
- Self-service signup (Q3)
- More than one calibrated predictor (Q3)
- Public API (out of 6-mo window)
- Multi-asset expansion (out of 6-mo window)

---

## Q3 2026 — Run Cohort 1, prep Cohort 2 (Aug 1 → Oct 31)

**One sentence:** by Oct 31, three design partners have used the platform on a live deal, three predictors carry calibration evidence, and Cohort 2 has 6+ signed LOIs at $50K pilot fee.

### Sprint plan (6 sprints × ~2 weeks)

#### Sprint 7 (Aug 3–14) — Multi-user auth (large)

From MULTI_USER_ARCHITECTURE.md. **Phase 1 only**:

- **Ship:** email + password auth with sessions, password reset via SMTP.
- **Ship:** organizations + members + roles (owner / analyst / viewer).
- **Ship:** every page query parameterized by `tenant_id` from session.
- **Cut from Phase 1:** SSO/SAML (defer to Q4 if first cohort asks; otherwise H2), comments and presence (Q4 at earliest), shared annotations (Q4).

This is the largest single deliverable in the 6-month window. Budget the full 2 weeks; assume slip into sprint 8.

#### Sprint 8 (Aug 17–28) — Eng hire onboarding + auth slip

- New hire shadows for first week, picks up small bugs in second week.
- Whatever spilled out of sprint 7 lands here.
- Begin: per-deal **win/loss capture** form (which prediction influenced the decision, what was the actual outcome 90 days later, single page).

#### Sprint 9 (Aug 31 – Sep 11) — Predictors 2 + 3 calibrated

- Wire **days-in-AR** and **collection rate** predictors to real labels.
- Each gets the `provenance: "real-cohort-N"` badge if it passes; stays on synthetic priors with a clear watch label if not.
- This is the directive that moves the platform from "thoughtful synthesis" to "calibrated tool" in customer-conversation language.

#### Sprint 10 (Sep 14–25) — Cohort 1 mid-program retro

- Sit-down with each of the 3 design partners (full day each).
- Top-3 fixes per partner go on the board for sprint 11.
- One feature each design partner asked for that nobody else asked for: park unless it's small.

#### Sprint 11 (Sep 28 – Oct 9) — Design-partner debt + Cohort 2 ingest

- Land the top fixes from sprint 10.
- **Ship:** self-service tenant provisioning (`/signup` → email confirm → first-run wizard). Required for Cohort 2 economics — white-glove doesn't scale to 8–10.
- **Ship:** Stripe integration for $50K pilot fee invoicing (manual ACH still allowed; Stripe is the default).

#### Sprint 12 (Oct 12–23) — Cohort 2 sales + pricing test

- Open Cohort 2 outbound. Target: 12 conversations, 6 signed LOIs.
- Run pricing A/B as designed in BUSINESS_MODEL.md ($35K vs $50K vs $75K pilot).
- New hire ships their first user-visible feature (TBD based on cohort feedback).

#### Sprint 13 (Oct 26–31) — Q3 retro + Q4 plan

- Retro doc with hard numbers: which predictors hit calibration, NPS, time-to-first-value, drop-off points, dollar opportunity sized.
- Q4 roadmap doc (separate from this one) — informed by what cohort 1 actually found, **not** by what we planned today.

### Q3 deliverables checklist

- [ ] Multi-user auth + tenant isolation in production
- [ ] All 3 design partners actively using the platform on at least 1 live deal each
- [ ] 3 predictors with `real-cohort-N` provenance badge (denial rate, days-in-AR, collection rate)
- [ ] Win/loss capture form deployed; ≥10 outcomes recorded
- [ ] Self-service signup live behind invite code
- [ ] Stripe billing for pilot fees live
- [ ] 6+ Cohort 2 LOIs signed at any of the 3 pilot price points
- [ ] Eng hire shipping unsupervised by Oct 1

### Q3 explicit non-goals

- Comments, presence, shared annotations (Q4 earliest)
- Public API (out of 6-mo window)
- Multi-asset expansion (out of 6-mo window)
- v2 architecture refactor (out of 6-mo window — apply incrementally per V2_PLAN.md)
- Slack/Salesforce/Affinity integrations (Q4 earliest, only if a Cohort 1 partner makes it a deal-blocker)

---

## What's explicitly cut from the 6-month window

These exist in strategy docs but **are not getting built before 2026-11-01**. Listing them here so the cut is intentional, not amnesia.

| Item | Source doc | Why cut | When |
|---|---|---|---|
| Multi-asset (physician/ASC/behavioral/post-acute) | MULTI_ASSET_EXPANSION.md | One core asset class isn't calibrated yet; expanding the surface area before that ships dilutes evidence | H1 2027 |
| Public API + integrations | INTEGRATIONS_PLAN.md | Pre-PMF integrations are a customer-acquisition tax with no revenue lift | Q4 2026 if cohort blocks; H1 2027 otherwise |
| v2 architecture refactor | V2_PLAN.md | Apply incrementally per V2_PLAN's own guidance; no big-bang rewrite | ongoing, not a roadmap item |
| Comments / presence / shared annotations | MULTI_USER_ARCHITECTURE.md | Phase 2 of multi-user; Phase 1 (auth + isolation) is the only thing required for cohort billing | Q4 2026 |
| SOC 2 Type II | PHI_SECURITY_ARCHITECTURE.md | 12-month observation window; start clock in Q4 | start Q4 2026, complete Q4 2027 |
| Real claims-data ingest (837/835) | PHI_SECURITY_ARCHITECTURE.md | Tier 2 PHI controls + parser work; scoped to ~6 weeks of focused work | Q4 2026 if a design partner brings labeled claims |
| Mobile / tablet polish | — | Desktop-only is fine for IC use case | indefinite |
| Real-time collaboration | MULTI_USER_ARCHITECTURE.md | No customer has asked; expensive to build | indefinite |

---

## Risk register

Top risks ranked by 6-month-plan impact, with mitigation already wired into the plan.

1. **Design-partner data delays.** Closed-deal labels arriving 6–10 weeks later than promised is the *modal* outcome.
   - **Mitigation:** Sprint 5 buffer, `synthetic-priors` fallback, provenance badge so users see the difference.
2. **Founder context-switching tax.** Sales weeks during recruiting (Sep) typically halve build output.
   - **Mitigation:** Q3 build capacity already discounted to 50% founder time; eng hire absorbs the gap.
3. **Eng hire slip (start date or ramp).** ~30% probability the hire starts after Aug 15 or ramps slower than 0.4 FTE in Q3.
   - **Mitigation:** Q3 plan has 1 large + 2 medium = same as Q2 even if hire is 0.0 FTE; hire's contribution is the +6 small items.
4. **One predictor fails calibration.** Synthetic-priors band is plausible but real labels disagree.
   - **Mitigation:** plan calibrates 3 predictors in Q3 specifically so 1 failure isn't fatal; learning-loop instrumentation captures *why* it missed.
5. **BAA legal cycle longer than expected.** Counsel on the design-partner side often takes 4–6 weeks on first BAA.
   - **Mitigation:** sprint 3 ships our template before sales conversations open in Sprint 4 buffer.
6. **Cohort 2 pricing test inconclusive.** $35K/$50K/$75K bands may not have enough signal at n=6–10.
   - **Mitigation:** signal is acceptance rate + churn at 90-day, not statistical significance; if all 3 bands convert similarly we ship $50K and revisit at Cohort 3.

---

## Decision points (when we re-plan)

| Date | Decision |
|---|---|
| 2026-06-15 | Tier-1 PHI work on track? If not, slip Cohort 1 by 4 weeks. |
| 2026-07-15 | 3 design partners signed? If only 1–2, hold Q3 plan and run more sales in August. |
| 2026-09-01 | Eng hire ramped? If <0.2 FTE effective, drop sprint-12 pricing test. |
| 2026-10-15 | ≥1 predictor passing real-data calibration? If not, **Cohort 2 does not open**; root-cause and re-plan. |

---

## Success measures (what "good" looks like 2026-10-31)

- 3 design partners renewed for Cohort 2 (or 2/3, with the third giving useful churn data)
- 3 predictors with calibration evidence on ≥30 real deals each
- 6 Cohort 2 LOIs signed
- ARR booking ≥ $300K committed (3 × $50K Cohort 1 renewals + 6 × $25K Cohort 2 down payments at the chosen price)
- 1 eng hire shipping independently
- 0 PHI incidents, 0 BAA breaches
- NPS ≥ 30 from Cohort 1 (low bar; we're listening, not selling)

If we hit 5 of 7 of those, this roadmap was right and Q4 plans the next leg.
If we hit ≤2, the underlying assumption (one calibrated predictor unlocks PE buying) was wrong and we re-plan at the strategy level, not the roadmap level.
