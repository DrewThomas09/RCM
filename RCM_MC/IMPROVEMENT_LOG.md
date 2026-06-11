# IMPROVEMENT_LOG — append-only, evidence per item

## Item 1 — Azure → DigitalOcean deploy-story purge (user-flagged, jumped queue)
- when: 2026-06-10T03:44–03:52Z (iteration 1)
- what: every ACTIVE deploy surface now names the DigitalOcean droplet handoff
  as the canonical path; Azure exists only in historical records and
  illustrative vendor content.
  - renamed: tools/azure_smoke.py → tools/deploy_smoke.py;
    tests/test_azure_smoke.py → test_deploy_smoke.py;
    tests/test_azure_deploy_v2.py → test_deploy_env_v2.py;
    tests/test_azure_deploy.py → test_deploy_vm.py;
    deploy/azure-app-service.json → deploy/app-env.json
  - deploy/PEDESK_DEPLOY.md: banner declaring production = DO droplet
    (docs/DIGITALOCEAN_DEPLOYMENT.md + docs/AUTODEPLOY.md), doc reframed as
    the legacy docker-compose alternative for a generic Ubuntu VM
  - demo.py `_RUNNING_ON_AZURE` → `_RUNNING_ON_PAAS` (behavior identical);
    comments in server.py / infra/logger.py / vm_setup.sh /
    docker-compose.yml / scripts/README.md / ui/README.md de-Azured
- verification:
  - py_compile clean on demo.py, server.py, logger.py, deploy_smoke.py
  - pytest: test_deploy_smoke + test_deploy_env_v2 + test_deploy_vm +
    test_migration_idempotency + test_security_hardening → 68 passed
  - grep sweep: zero deployment-Azure references outside historical docs +
    content seeds (list in DECISIONS.md #2)
  - deploy pipeline itself verified healthy pre-change: deploy.yml run #1630
    (75e1001) completed/success 03:37:20Z incl. live pedesk.app/healthz 200
- users served: all three (deploy trust underpins everything); replaces:
  confusion about where production actually runs.

## Item 2 — P2 CIM Cross-Check / Variance Engine (vertical slice, hospitals)
- when: 2026-06-10T03:53–04:08Z (iteration 2)
- what: NEW power feature. /diligence/cim-crosscheck — enter management's CIM
  claims (market size $, hospital count, margin %, Medicare/Medicaid share %,
  inpatient days, target net revenue $) → independent estimates from the
  HCRIS universe scoped to state/bed-band → variance table with green ≤10% /
  yellow ≤25% / red >25% / UNVERIFIABLE flags, ENTERED vs ACTUAL basis
  badges, n + source link + method line + drill-to-rows per estimate;
  variance-memo (txt, with a suggested expert-call question per claim) + CSV
  exports. Pure logic in diligence/cim_crosscheck.py (UI-free); page wired
  into route + Diligence sub-nav + Cmd-K palette.
- verification (per plan):
  - claims fabricated from real TX baselines (Σ NPR $97.4B, 583 hospitals,
    16.7M days) at +7%/+18%/+40% → flags fired exactly green/yellow/red;
    $500M revenue claim vs CCN 450358's filed $2.63B → red (live E2E).
  - margin benchmark excludes junk-opex filings via the core plausible band
    (unit-tested with a 90%-margin artifact row).
  - NaN day-share filings excluded from medians, not zero-filled (tested).
  - empty scope / unknown CCN → UNVERIFIABLE, never fabricated (tested).
  - 20 unit/page tests in tests/test_cim_crosscheck.py; palette tests green.
  - screenshots: /tmp/session_shots/item2_cim_crosscheck_final.png — caught
    and fixed a real escaping bug (badge markup escaped in panel title).
- users: Chartis consultant (user 1) — replaces the week-one manual
  CIM-vs-public-data build; PE VP (user 2) gets the same table for IC prep.

## Item 3 — P7 Roll-Up Scenario Builder (vertical slice, hospitals)
- when: 2026-06-10T04:10–04:26Z (iteration 3)
- what: NEW power feature. /pipeline/rollup?ccns=a,b,c — pro-forma platform
  from N real HCRIS facilities: combined beds/days/NPR with per-aggregate
  coverage notes (gaps never silently zero), day-weighted payer blend
  (NaN filings excluded from numerator AND denominator), state share + HHI
  before/after with 2023 DOJ/FTC Merger-Guidelines screening notes
  (structural-presumption zone, attention zone, below-threshold), in-state
  overlap notes, USER-ASSUMPTION G&A synergy (refuses a partially-known cost
  base), CSV export. Screener compare basket → "Roll-up these N" link.
  Pure logic in pe/rollup_scenario.py; route + Pipeline sub-nav + palette.
- verification:
  - hand-checked on 3 real TX systems (MD Anderson 450076 + Memorial Hermann
    450068 + Methodist 450358): combined NPR $10.17B and 811,814 days match
    per-row sums; share 10.44%; HHI 109→178, Δ+69 — hand recomputation of
    (Σs)²−Σs² matched exactly.
  - 10 unit/page tests (aggregates, coverage gaps, NaN-aware blend, synergy
    refusal, HHI hand math, screening-note zones, escapes); screener suite
    165 passed with the new compare→rollup link.
  - screenshot: /tmp/session_shots/item3_rollup.png (KPI strip, HHI table
    with screening note, filed-values facility table).
- users: PE VP (user 2) thesis-testing; Chartis (user 1) gets the
  concentration exhibit + screening language for the market section.

## Merge checkpoint 1 — items 1–3 LIVE on pedesk.app
- merge: PR #1663 → main 7daef221 at ~04:16Z
- deploy: deploy.yml run #1631 completed/SUCCESS 04:19:27Z — droplet
  fast-forwarded, pedesk.service restarted, run's own gates confirmed
  LIVE https://pedesk.app/healthz=200 + guide-health reachable.
- additional checks (same SHA, local): route_walker 361 routes → 349 ok /
  0 tracebacks (/tmp/route_walk_ckpt1.tsv); screenshots:
  item2_cim_crosscheck_final.png, item3_rollup.png, live_check_cim_empty.png.
- protocol note: sandbox egress cannot reach pedesk.app (DECISIONS.md #1);
  the deploy run's public health gate is the live check of record.

## Item 4 — P4 peer-percentile chip + deal quick-view wiring
- when: 2026-06-10T04:16–04:26Z (iteration 4)
- what: ck_peer_percentile(value, dist, peer_label, higher_is_better) —
  "p73 ●——— vs portfolio deals (n=10)" chip with standard percentile-rank
  math (below + half-ties), NaN peers excluded from n, n<8 renders an
  honest "peer set too small (n=K)" instead of fake precision, None/NaN
  value renders nothing. Wired into deal quick-view profile KPIs vs the
  rest of the book (direction-aware tones); server passes list_deals().
- verification: rank math unit-tested incl. ties (p55 case hand-computed),
  extremes p0/p100, NaN exclusion, small-n guard, tooltip method text;
  quick-view wiring tested at n=10 (chips) and n=5 (honest guard) and
  no-frame (no chip, no crash). 10 tests green; deal-profile suite green.
- users: portfolio ops (user 3) — replaces eyeballing the book for "is this
  deal's denial rate bad *for us*".

## Item 5 — P11 Data Quality dashboard
- when: 2026-06-10T04:24–04:33Z (iteration 5)
- what: /data-quality — internal certification screen. (1) wired sources
  table with LIVE row counts + key-field null rates computed at render from
  the product's own loaders (HCRIS 6,123 + 6 Compare verticals = 49,161
  rows), vintage + the source's OWN cadence (HCRIS ~18mo lag stated as
  normal, not staleness), consumer map per source; (2) gap census reusing
  gap_fill_registry (same numbers as `rcm-mc data gaps`, fill-kind chips);
  (3) the 23 registered-but-unwired sources from source_registry.csv with
  vintages. Loader failures render as RED FINDINGS, not blank panels.
  Route + palette wired.
- verification: 5 tests pin displayed counts to independent loader/registry
  computations (hcris len, home_health len, top gap row); render check all
  marker strings; screenshot /tmp/session_shots/item5_data_quality.png.
- users: Chartis internal (user 1) — the 60-second pre-demo certification.

## Item 6 — P8b facility→rule regulatory exposure on the X-Ray
- when: 2026-06-10T04:31–04:42Z (iteration 6)
- what: rcm_mc/diligence/regulatory_calendar/exposure.py — tag-based join of
  (provider type, state) onto the curated 11-event REGULATORY_EVENTS library
  (each event already sourced to its agency docket). State-scoped rules
  (CT HB 5316 sale-leaseback phase-out) fire only for that state, with the
  scoping named in the match reason. New X-Ray panel "Regulatory exposure —
  applicable rulemakings": status chip (FINAL red / PROPOSED amber), rule
  title + docket link, effective date, curated margin-impact pp, Σ in the
  panel header; explicit honesty footer (curated coverage refreshed
  quarterly, NOT an exhaustive inventory).
- verification: TX hospital (450358) → exactly 3 rules, CT rule absent;
  CT hospital (070002) → 4 rules incl. HB 5316 with "CT-scoped" reason;
  dialysis → ESRD PPS only; unknown provider type → none; sort by effective
  date tested; Σ impacts pinned to event fields. 8 tests; X-Ray suites
  unaffected (17 green incl. nan/gap suites). Screenshot:
  /tmp/session_shots/item6_reg_exposure_ct.png.
- users: PE VP (user 2) — the reimbursement-risk question every IC memo
  opens with; Chartis (user 1) gets the sourced rule list for the policy
  section.

## Item 7 — P1 Deal Workspace slice 1: ambient active-deal context
- when: 2026-06-10T04:35–04:48Z (iteration 7)
- what: the deal becomes ambient context WITHOUT threading a parameter
  through 100+ shell call sites. /deal-context?set=<id>&return=<path>
  resolves the profile (name/state/ccn when present), writes
  pedesk_active_deal + _meta cookies (URL-encoded JSON), 303s back; an
  open-redirect guard pins return to same-site paths. A shell JS shim (house
  vanilla pattern) renders a slim ACTIVE DEAL bar on every chrome page from
  the cookies, with PRE-SCOPED links: Deal home, Screener (?state= when the
  profile has one), X-Ray (?ccn= when present), CIM cross-check. Clear ✕
  expires the cookies. 'Set Active Deal' affordances on the live deal-detail
  action row, deal dashboard, quick-view, and workbench hero.
- verification: 303 + both cookies on set; Max-Age=0 on clear; open-redirect
  rejected for //host, https://, and non-/ paths (tested); shim ships on
  chrome pages, absent on bare pages (login) — 5 tests. Live E2E: visiting
  the activation URL then landing on /target-screener renders the bar
  ("ACTIVE DEAL · CYPRESS CROSSING HEALTH" + module links + clear) —
  screenshot /tmp/session_shots/item7_active_deal_bar.png. ccf has no
  ccn/state in its profile → bar honestly omits X-Ray and scope (by design).
- users: all three — context-carrying is the engagement/deal organizing
  principle (Part III); kills per-screen re-entry of market/target.

## Item 8 — P13 honest insight bullets (primitive + portfolio)
- when: 2026-06-10T04:48–04:57Z (iteration 8)
- what: ck_insight_bullets(items) — strictly computed, guard-gated takeaways:
  renders ≤4 SIGNIFICANT candidates under "Takeaways — computed from the
  figures on this page" with tag-stripped copy-to-clipboard; renders NOTHING
  when no candidate passes (silence over noise; free-form text not accepted
  by design). Portfolio overview wired with three guarded candidates:
  denial spread ≥2pp (names best/worst deals), avg NCR vs the 95% floor
  (≥0.5pp guard), A/R >55d outliers (named).
- verification: on the live seeded book the spread bullet fires (8.0pp,
  Cypress vs Sterling — matches the table) and the NCR bullet correctly
  SELF-SUPPRESSES (94.8% is only 0.2pp from floor < 0.5 guard) — the guard
  demo on real data. 7 primitive/wiring tests incl. tiny-spread suppression
  and copy-payload tag-stripping. 22 green with deal-profile suite.
- users: Chartis (user 1) — the transcribe-chart-to-"so what" motion,
  pre-drafted without credibility risk.

## Item 9 — B: margin-model holdout card (in-UI conformal coverage)
- when: 2026-06-10T04:50–04:58Z (iteration 9)
- what: scripts/eval_margin_model.py — freezes a seeded 20% OUTER holdout
  (n=978 hospitals) the model never sees, trains the production path
  (train_margin_model: ridge + split-conformal) on the remaining 80%, and
  measures the 90% band's empirical coverage on the holdout → writes
  rcm_mc/ml/model_card_margin.json (coverage 91.0%, half-width ±11.4pp...
  actual values in the artifact; MAE, n, vintage, seed, limitations).
  /methodology gains a "Margin Predictor — holdout model card" panel that
  reads ONLY the artifact: no artifact, no claim; engine named exactly
  "Ridge regression with split-conformal intervals".
- verification: eval ran live — empirical coverage 91.0% vs nominal 90% on
  978 held-out filings; 4 tests pin artifact schema, coverage sanity band,
  engine naming, and that the UI panel renders the artifact's numbers.
  Confirmed the only "AI" strings on the page are the pre-existing Ollama
  Guide chrome, not model labeling.
- users: PE VP + Chartis (users 1–2) — the "can I trust the band?" question
  answered with a reproducible number, not an adjective.

## Sweep 2 + regression fixed — provenance-tooltip CSS never injected on /portfolio
- when: 2026-06-10T05:00–05:08Z (iteration 10)
- found by: regression sweep 2's screenshot diff — the three KPI provenance
  tooltips rendered their popover content INLINE (huge serif spill) because
  all three calls passed inject_css=False (pre-existing commit 6ecc199) and
  nothing else injected the CSS. Invisible until this morning's
  data-connection fix gave the KPIs real values; tonight's screenshot
  caught it. (The interim /portfolio 500 in sweep 2 was a stale dev-server
  process predating ck_insight_bullets — code was green; restart cleared it.)
- fix: first tooltip injects the CSS (the documented convention); verified
  '.prov-tt' style block present and the page rendering tooltips as ⓘ.
- evidence: item8_insights_fixed.png (Takeaways + clean KPI strip + health
  mosaic + deals table all correct); route walk 2b: 349/361, 0 tracebacks.

## Merge checkpoint 2 — items 4–9 LIVE on pedesk.app
- merge: PR #1664 → main 59f949e9 at ~04:55Z
- deploy: deploy.yml run #1632 completed/SUCCESS 05:00:54Z incl. LIVE
  pedesk.app/healthz=200 + guide-health gates.
- additional checks: route walks sweep2/2b (349/361, 0 tracebacks);
  screenshots item8_insights_fixed.png, item9_model_card.png; tooltip-CSS
  regression found by screenshot diff and fixed on-branch (36b1be3, rides
  checkpoint 3).

## Item 10 — H: composite demo deals anchored to real, named facilities
- when: 2026-06-10T05:05–05:18Z (iteration 11)
- what: each fictional demo deal now carries a facility_anchor naming a REAL
  CCN chosen to match its archetype from the live HCRIS frame (margin band +
  120–400 beds + $100M–$1.5B NPR): ccf→Hennepin County Medical Center (MN,
  −11.2%), mgh→Enloe (CA, −0.5%), nyp→St. Francis NY (+2.0%), buh→Tacoma
  General Allenmore (WA, +5.1%), sth→White Plains (NY, +8.7%). The anchor's
  filed financials render ACTUAL + sourced + X-Ray-linked on the deal quick
  view; the RCM metrics stay explicitly "illustrative demo values (HCRIS
  files no denial/collection fields)". demo.py seeder writes the anchors
  (resilient: anchor lookup failure can't break seeding); the live seeded db
  updated in place. Bonus: profiles now carry state+ccn → the P1 active-deal
  bar gains the X-Ray link + state-scoped screener for demo deals (meta
  cookie verified: {"id":"ccf","state":"MN","ccn":"240004"}).
- also fixed (found during): quick view read only flat metric keys → showed
  "No profile metrics yet" for packet-seeded deals while nested
  observed_metrics sat right there; now flattened (same class as the
  list_deals fix this morning).
- verification: 5 anchor tests + flatten test + seeder pin; meta-cookie E2E;
  screenshot item10_anchored_bar.png. 20 green incl. deal-context + chip.
- users: all three — the demo stops being deniable as "fake data" while
  staying honest about what HCRIS cannot provide.

## Item 11 — P5 ExhibitFactory v1 + comparable-outcomes seed batching (05:35Z)
**What**: (a) `ExhibitFactory` in `_chartis_kit.py` — per-render numbered
"EXHIBIT N" chrome (figure caption: deal label + number + title + units;
footer: Source + vintage + PEdesk) with `_EXHIBIT_PRINT_CSS` shipped once in
the shell head: print suppresses nav/topbar/forms/buttons, page-breaks keep
each exhibit whole — Cmd+P → deck-insertable PDF. Wired into the two v1
consumers: Roll-Up Builder (Exhibit 1 pro-forma KPIs, Exhibit 2 concentration
table) and CIM Cross-Check (Exhibit 1 variance table). (b) While running the
pre-commit full suite, found `/diligence/comparable-outcomes?...` timing out
HTTP tests at >10s: `DealsCorpus.seed()` ran ~1,727 upserts each on its OWN
connection with its own fsync'd commit (5.4s commits + 3.1s connection
churn) — invisible on `:memory:` profiling. Split `_upsert_on(con, deal)`
out of `upsert()`; `seed()` now batches the whole corpus in one
connection/one commit. Route: 8,864ms → 99ms (90×).
**Verify**: tests/test_exhibit_factory.py (9: numbering per instance,
escaping, markup-source exemption, shell ships CSS once, both consumers
render numbered exhibits, form-only CIM view has none);
test_comparable_outcomes.py 24/24 in 1.0s (was 2 timeouts); corpus slice
1,050 passed; screen + print-media screenshots of both pages (print view:
chrome gone, exhibits + sourced footers intact). Full suite re-running at
commit time.
**Persona check**: Chartis consultant on a readout call prints the variance
table straight into the appendix — numbered, sourced, vintage-stamped, no
manual cropping.

## Item 12 — Deal-context slice 2: active-deal cookie pre-scopes diligence forms (06:40Z)
**What**: The P1 active-deal cookie (pedesk_active_deal_meta = {id,name,state,
ccn}) now pre-scopes the CIM Cross-Check and Roll-Up forms. New
RCMHandler._active_deal_meta() decodes the cookie (best-effort, never raises);
the /diligence/cim-crosscheck handler fills state+ccn when the partner hasn't
typed them, and /pipeline/rollup seeds the CCN basket with the deal's CCN as
the platform anchor. A teal "Pre-scoped to your active deal X" note renders so
the prefill is never silent. **Explicit query params always win** (override
the cookie); the internal _prefill_deal key is stripped from export URLs.
**Verify**: tests/test_deal_context_prefill.py (7: prefill state+ccn, param
override on both pages, no-cookie → no note, malformed cookie ignored, key
absent from export URLs); affected suites 45/45; screenshot shows TX/450076
prefilled with the teal note on a real authed-bypass server on this SHA.
**Persona check**: VP who set an active deal opens CIM Cross-Check and the
market+target are already there — one less retype between "I'm looking at this
deal" and "show me the variance."

## Item 13 — Target Screener row → CIM Cross-Check action (07:05Z)
**What**: Each hospital row in the Target Screener now carries a one-click
"CIM" chip (alongside X-Ray · Inspect · +Cmp) that opens CIM Cross-Check
pre-scoped to that facility's state + CCN. The screener is where a partner
first spots a target; the independent-variance check is now one click from
the row instead of a manual re-entry. Hospital-only by design (the
cross-check estimators are HCRIS-hospital-shaped) — dialysis/SNF/etc. rows
don't show it. Closes the Source→Diligence handoff alongside the deal-context
prefill (Item 12): the link carries state+ccn as query params, which the CIM
page already reads (params win over the active-deal cookie).
**Verify**: tests/test_target_screener.py RowCimActionTests (2: hospital rows
carry the scoped link with the row's state; non-hospital verticals carry
none) + full screener suite 157/157; cropped screenshot shows the CIM chip on
two TX hospital rows (Denton 23.3%, Fort Worth 22.9%).
**Persona check**: Chartis consultant scanning the TX hospital screen clicks
CIM on a target and lands in the variance form already set to TX + that CCN.

## Item 14 — Est. AR Days column + "?" explainer on the predictive screener (07:20Z)
**What**: est_ar_days was computed and offered as a sort option but had NO
table column — a partner could sort by an invisible value. Added the Est. AR
Days column between Est. Denial and Est. Uplift, PREDICTED-badged, with a "?"
calc-explainer (ck_calc_help) stating the exact formula (45 + Medicare-day%×5
+ Medicaid-day%×8 − ln(beds)×3 − net-to-gross×10 − margin×8) and the 25–75
day plausible bound from rcm_mc.ml.prediction_bounds. Thin-data rows show "—"
(ps-na) like the other estimates. Header/body column counts stay balanced (10).
**Verify**: tests/test_predictive_screener_ar_days.py (4: header has badge +
explainer + bound, complete row shows an in-range day count, thin-data row
shows dash, header/body column counts match); updated test_screener_basis_
badge PREDICTED count 2→3 (now three modeled columns); related screener +
bounds suites green. Cropped screenshot: Mercy Hospital MO renders 25 AR days
under the PREDICTED·? header.
**Persona check**: portfolio-ops user sorting by A/R days now actually sees
the days, with the formula one hover away — no hidden sort key.

## Item 15 — Data Quality staleness chips (green/amber/red by cadence) (07:38Z)
**What**: The DQ dashboard's wired-source table now carries a deterministic
freshness chip per source: snapshot age vs the source's OWN publication
cadence — CURRENT (≤1.5 cycles) / AGING (≤3) / STALE (>3). HCRIS reads
CURRENT NORMAL (its ~18-month publication lag is expected, not staleness);
sources with no stated snapshot date read DATE UNSTATED (honest gray, never a
fabricated green). Added structured cadence_days + snapshot_date +
lag_tolerant fields to WiredSource (free-text cadence_note stays for display);
pure _staleness_tier() computes the tier so it can't drift, today comes from
datetime.now(timezone.utc). Legend added under the table.
**Verify**: tests/test_data_quality_page.py StalenessTierTests (6: monthly
2-month-old → AGING with age 70d per the backlog's worked SNF example,
quarterly recent → CURRENT, very-old → STALE, HCRIS lag-tolerant → CURRENT
NORMAL, missing date → DATE UNSTATED, dashboard renders chips + legend) +
existing 5 DQ tests green. Screenshot: HCRIS green CURRENT NORMAL, Home
Health/Hospice gray DATE UNSTATED, SNF amber AGING (Apr 2026, monthly).
**Persona check**: portfolio-ops user glances at the DQ screen and sees at a
glance which feed is aging (SNF) without reading every cadence note.

## Item 16 — route_walker self-contained --discover + wired into CI sweep (07:55Z)
**What**: Made scripts/route_walker.py self-sufficient — a --discover flag
pulls the exact-match GET page routes from RCMHandler._discover_all_routes()
(no pre-written /tmp routes file), and --fail-on-leak adds a nan/None-leak
gate on top of the existing traceback gate (exit non-zero on either). Wired a
"Route-walker smoke" step into .github/workflows/regression-sweep.yml (the
WEEKLY sweep, never the per-push deploy gate): it boots an open-auth server,
walks every discovered route, surfaces pass/fail + log tail to the job
summary, and uploads route_walk.tsv as an artifact. Placed off the deploy
path by design so it can never block a pedesk.app deploy.
**Verify**: tests/test_route_walker_discover.py (3: discovery includes the
new cim/rollup/data-quality/portfolio routes and excludes /api; core routes
render 200 with no traceback/leak); ran --discover --fail-on-leak against a
live local server → 161/162 ok, 0 tracebacks, 0 leaks, exit 0 (the 1 non-2xx
is /analysis on an empty DB, expected); regression-sweep.yml parses as valid
YAML.
**Persona check**: the deploy discipline the user asked for ("do multiple
checks") now has an automated weekly backstop that catches a 500/leak on any
page, with an artifact to inspect.

## Item 17 — P12 entity jump: Cmd-K → HCRIS X-Ray by CCN (08:15Z)
**What**: The command palette now recognises a 6-digit query as a CMS CCN and
surfaces a synthetic "→ HCRIS X-Ray for CCN ######" result routing to
/diligence/hcris-xray?ccn=######. Pure client-side — the route is built from
the typed digits, so no backend call and no 6,123-row entity list inlined.
The synthetic row starts hidden (display:none so visibleItems() ignores it),
is revealed + highlighted only when /^\d{6}$/ matches, and Enter navigates.
Placeholder updated to advertise it ("Jump to a page, or type a 6-digit
CCN…"). Name-based entity search needs a backend index → deferred; CCN jump
is the safe, high-value v1.
**Verify**: tests/test_palette_entity_jump.py (4: hidden entity item present,
placeholder advertises it, JS builds the X-Ray route from 6 digits, static
text-filter loop skips the synthetic row) + command_palette/universal_palette
regression 27 passed. Headless browser: typing 450358 reveals the highlighted
result and Enter lands on /diligence/hcris-xray?ccn=450358 (verified URL
transition); screenshot captured.
**Persona check**: VP with a CCN from a data room hits ⌘K, types the 6
digits, Enter — straight into the facility X-Ray, no menu hunting.

## CHECKPOINT 3 — LIVE on pedesk.app (11:55Z)
PR #1665 (16 commits: items 11–17 + 7-failure fix batch + Guide-invariant
fixes + Azure→DO docs purge) merged to main at f4ddae0 after CI green on
3.11/3.12/3.14. Deploy run #1633 "Deploy PEdesk (DigitalOcean Droplet)"
completed SUCCESS — deploy-gate tests, SSH deploy to the droplet, and the
**public-URL health check on pedesk.app all green** (the live check of
record; sandbox egress is blocked, per DECISIONS #1). Post-merge multiple
checks on the same SHA locally: 6/6 feature markers (rollup exhibits, CIM
prefill note, DQ AGING chip, AR-days column, screener CIM action, palette
entity jump) + 6 fresh screenshots (pm_*.png) — Roll-Up shows EXHIBIT 1/2
chrome with sourced footers exactly as designed.

## Item 18 — P9 vintage-diff snapshots of saved screens + REAL BUG: session usernames never resolved (12:10Z)
**What**: (a) P9 slice — saved Target-Screener screens can now be SNAPSHOTTED
(new rcm_mc/portfolio/screen_snapshots.py: owner-scoped table, take/latest/
delete, pure diff_results with honest thresholds: ≥5% relative move on
size/q, string identity on ownership/name, sub-threshold wiggle is NOT a
change), and the Saved-screens tab shows "since YYYY-MM-DD: +N entered · −M
left · K changed" (or "no change") per snapshotted screen with a
snapshot/re-baseline action. Current results are recomputed through the SAME
loader+filter path the table renders (screen_results_for_params — no parallel
implementation); diff computation is capped at 10 screens, snapshots at 1,000
rows. Snapshots are deleted with their screen (explicit cleanup, delete-policy
documented). New POST /api/target-screener/snapshot (owner-scoped).
(b) **REAL BUG found by the E2E**: RCMHandler._current_username() did
`user.username` but user_for_session returns a DICT → AttributeError swallowed
by the blanket except → EVERY logged-in session resolved to None. Owner-gated
features (the whole saved-screens panel) never rendered for real partners and
audit rows fell back to "api". Fixed to accept dict/object shapes.
**Verify**: tests/test_screen_snapshots.py (14: diff set/threshold/ownership/
newly-reported semantics, summary silence, storage round-trip owner-scoped,
latest-wins, delete cleanup, same-filter-semantics vs table, self-diff is
empty, saved-tab render with/without snapshot);
tests/test_current_username_session.py (3: real HTTP login → owner panel
renders; anonymous still 401). Full screener+auth suites 239 passed. E2E on
the demo server: save "TX large hospitals" → snapshot → reload shows "since
2026-06-10: no change" + re-baseline (screenshot snap_saved_tab.png) — this
exact flow was IMPOSSIBLE before the username fix.
**Persona check**: VP re-opens their watched TX screen after a CMS re-vendor
and sees "+3 entered · −1 left" instead of silently comparing against a
different universe than last month.

## Item 19 — Roll-up scenarios persisted to deals as sourced notes (12:20Z)
**What**: A built roll-up scenario can now be SAVED to the active deal
(backlog #17). The rollup page shows "Save scenario to <deal>" when a
scenario is built AND a deal context exists (nothing honest to attach to
otherwise); POST /api/rollup/save-to-deal recomputes the scenario
server-side (form figures never trusted), requires the deal to ALREADY exist
(record_note would silently upsert a junk deal), and records a deal note
stating facilities + combined filed figures (ACTUAL basis stated), the
HHI before/after per state-proxy market, the ENTERED-labeled synergy
assumption, and a reopen link to the exact scenario URL. Notes surface on
the deal page + notes search and are deletable like any note (soft-delete
policy inherited).
**Verify**: tests/test_rollup_save_to_deal.py (4: button only with active
deal; POST records the sourced note with basis/ENTERED/reopen-link; unknown
deal rejected with NO junk-deal upsert; <2 CCNs rejected) + rollup/prefill/
exhibit suites 20 passed. E2E on demo server: set active deal ccf → save →
green confirmation ("Scenario saved to Cypress Crossing Health") → note
visible on /deal/ccf (screenshots rollup_save_btn.png, rollup_saved.png).
**Persona check**: VP models a 3-hospital platform, hits save, and the IC
prep deal page now carries the scenario with every figure traceable.

## Item 20 — P12b palette name-search (12:32Z)
**What**: Completes the entity-jump: a non-CCN palette query of ≥4 chars now
offers "→ Search providers for 'q'" routing to /diligence/xray?q=… — the
EXISTING CMS X-Ray name resolver (cross-vertical name/CCN search), so zero
new backend and no inlined entity list. 6-digit CCN keeps the direct X-Ray
jump; short queries and non-CCN digit strings offer nothing.
**Verify**: headless-browser drive of the static shell: "memorial hermann" →
/diligence/xray?q=memorial%20hermann (visible), "450358" → hcris-xray, "mem"
hidden, "12345" hidden. Resolver itself verified live (q=memorial+hermann →
MEMORIAL HERMANN results). tests/test_palette_entity_jump.py extended (5);
palette suites 33 passed.
**Persona check**: consultant types a hospital name from a call sheet into
⌘K and lands on the resolver's ranked matches — both halves of P12 now work.

## Item 21 — modeling-discipline line on the predictive screener (12:40Z)
**What**: The screener's contrast callout now ends with a model-card line read
ONLY from rcm_mc/ml/model_card_margin.json ("its 90% conformal band covered
91.0% on 978 held-out filings — model card → /methodology"). Honesty boundary
stated explicitly: THIS page's Est.* columns are the simple screening formulas
(each column's "?" shows the math), not the conformal model — the measured
coverage is never misread as covering these estimates. Missing artifact → no
line (no claim without its source).
**Verify**: ModelCardFooterTests (2: artifact numbers + boundary in the line;
page renders it); ar-days suite 6 passed.

## Item 22 — roll-up reopen links clickable on the deal page (12:48Z)
**What**: The reopen path that save-to-deal writes into a note now renders as
a real anchor on the deal page. Linkified AFTER html.escape with a strict
charset (& only as the full &amp; entity), so other entities (&quot; &gt;)
can never be swallowed into the href and note content can never smuggle
markup — deliberately NOT a general URL linkifier. First regex draft cut
mid-entity on &amp; (caught by the hostile-content test, fixed).
**Verify**: NoteLinkifyTests — reopen path becomes href with &amp; intact;
'<script>' stays escaped; '"><img>' can't break out. Suite 5 passed.

## Item 23 — DQ: real snapshot dates for Home Health + Hospice (12:55Z)
**What**: The two DATE UNSTATED sources now carry their actual vendoring date
(2026-06-04, from `git log --follow` on the CSVs — the CMS files don't embed
a snapshot date; provenance method noted in a code comment). Both quarterly →
CURRENT. Dashboard now shows 0 DATE UNSTATED / 6 CURRENT(+NORMAL) / 1 AGING
(SNF, correctly).
**Verify**: DQ suite 11 passed (the pure-function DATE UNSTATED tier test
still covers the no-date path).

## CHECKPOINT 4 — LIVE on pedesk.app (12:30Z)
PR #1666 (items 18–23 + the session-username fix) merged to main at d15e3a4
after CI green on 3.11/3.12/3.14. Deploy run #1634 "Deploy PEdesk
(DigitalOcean Droplet)" completed SUCCESS — deploy-gate tests, SSH deploy,
and the **public-URL health check on pedesk.app all green**. Post-merge
multiple checks on the same SHA (authed demo server, real login):
1. owner panel renders (username fix live) ✓
2. save screen → snapshot → "since 2026-06-10: no change" diff line ✓
3. roll-up save-to-deal button + EXHIBIT chrome ✓
4. palette name-jump → /diligence/xray?q=… ✓
5. screener modeling-discipline line with artifact numbers (91.0%) ✓
6. DQ chips: 6 CURRENT(+NORMAL), SNF AGING, zero DATE UNSTATED ✓
Screenshot: ckpt4_saved.png.

## SESSION CLOSE-OUT (12:32Z — 8h55m elapsed)
23 items + 2 found-bug fixes shipped across 4 checkpoints, all LIVE on
pedesk.app via the DigitalOcean pipeline (deploys #1631–#1634, each with the
public health-check gate green). Highlights: CIM Cross-Check variance engine,
Roll-Up Builder with HHI screen + save-to-deal, ExhibitFactory print-ready
exhibits, ambient deal context end-to-end (bar → prefill → save-to-deal),
peer percentiles, DQ dashboard with cadence-true staleness chips, margin
model card (measured 91.0% coverage on 978 holdout), P9 screen snapshots
with honest diffs, P12 entity jump (CCN + name), Azure→DO deploy-story purge.
Real bugs found & fixed by the verification discipline: provenance-tooltip
CSS injection, corpus-seed 90× perf, session-username resolution (owner
features invisible to ALL logged-in users), regex entity-swallow in note
linkify. Full suite: 15,019+ passing, 0 failing at last gate.

## W2-1/2/3 — bug-hunt sweep 1: dead /market-data link + non-finite 500s (13:00Z)
**Found by**: browser console sweep over 20 routes (one 404) + a 150-request
hostile-param fuzz over 10 routes (4× 500).
**Fixed**:
(1) /market-data 404'd while the Guide context, DQ consumer list and 5+
related_routes point at the bare slug → now redirects to /market-data/map.
(2) CIM Cross-Check 500'd on nan/Infinity/1e309 params (float() accepts
them; int(inf) in the form echo raised) → _f_or_none rejects non-finite.
(3) Roll-up ga_pct=nan silently became the MAX synergy (min(0.30,nan)→0.30)
→ non-finite treated as no assumption, both in the page and save-to-deal.
**Verify**: re-fuzz 150/150 CLEAN; NonFiniteInputTests (2), NonFiniteGaPctTests
(1), MarketDataRedirectTests (1); suites 27+4 passed.

## W2-4 — X-Ray dollar metrics: trailing " $" → leading "$" (13:12Z)
**Found by**: visual pass on /diligence/hcris-xray — peer table rendered
"2,720,593 $" (currency trailing, against the house style and how every
other surface prints money).
**Fixed**: MetricSpec gains a `prefix` field; the four $ metrics (NPR/bed,
NPR/patient-day, Opex/bed, Opex/patient-day) now render "$2,720,593" in the
peer table, top-finding band, memo and CSV (all flow through spec.fmt).
**Verify**: fmt spot-check on all four; X-Ray suites 143 passed.

## W2-5 — workbench fabricated green "$0" EBITDA Opportunity (13:25Z)
**Found by**: visual pass on /analysis/ccf — the hero card showed "$0" in
positive green with "no EV computed" beneath, i.e. a CONFIDENT zero where the
truth is "bridge couldn't run" (grade-D completeness, no revenue baseline).
$0 ≠ unknown — the exact fabricated-zero class this product polices.
**Fixed**: the hero gates on the bridge's own status + per_metric_impacts
evidence; not-run renders "—" + "not computed: <bridge reason>" (e.g. "no
revenue baseline"). A real computed total still renders green.
**Verify**: test_workbench_honest_hero.py (2: SKIPPED → dash+reason; OK with
zero contributing levers → dash); workbench suites 198 passed; screenshot
wb_hero_fixed.png shows the honest dash on the live page.

## W2-6 — P4b: claim-percentile chips on CIM Cross-Check (13:45Z)
**What**: Each distribution-shaped claim row now shows where the CLAIM itself
sits in the in-scope per-facility distribution — "claim @ p50 of n=457" under
the CIM-says value. Tails (≤p10/≥p90) render amber with "tail claim,
scrutinize": a claim can pass the variance flag AND be a top-of-market
assertion worth a question (e.g. claimed target revenue $2.6B @ p99 — true
for Methodist, but the consultant should know they're underwriting a giant).
Engine computes it (claim_percentile/percentile_n on VarianceRow) from the
SAME plausible-band population the estimator describes; aggregates (market
size, counts) and tiny scopes (n<8) get None — no fabricated ranks. Memo/CSV
unchanged (additive fields).
**Verify**: ClaimPercentileTests (5: median claim → exactly p50 on a hand-
built 10-row frame; tail ≥p90; aggregate None; n<8 None; chip renders amber
tail / empty aggregate) + real-data spot-check (TX: margin 2.5 → p50 matching
the green flag; revenue 2.6e9 → p99). CIM suite 21 passed. Screenshot.

## W2-7 — screener state prefill from active deal (13:55Z)
**What**: Deal-context parity for the Target Screener — a plain visit (main
view, no state chosen) pre-scopes to the active deal's state; the state
renders as the existing one-click-removable filter chip, so the prefill is
visible and reversible. Params always win; saved/compare/missed views are
never re-filtered out from under the partner.
**Verify**: ScreenerStatePrefillTests (3: chip prefilled; explicit ?state=CA
wins; saved view untouched); prefill suite restructured onto a fixture-only
base (parent tests no longer run twice) — 10 passed.

## W2-8 — Local competitive context on the HCRIS X-Ray (14:30Z)
**What**: New data integration — the vendored geocode crosswalk (4,630
hospitals, one-time Census-geocoded CMS addresses, previously map-only) now
joins HCRIS filings to answer the week-one CDD question state proxies can't:
who competes with this facility LOCALLY? rcm_mc/data/local_market.py
(haversine + LocalMarket with reporting-set share math) + a 25-mile-radius
panel on the X-Ray: count ≤25mi, combined competitor NPR with coverage
("37/41 report NPR"), target share-of-radius, nearest-8 table with
distance/beds/NPR + drill links. Honesty stated on-panel: straight-line not
drive-time, radius = screening geography not a relevant antitrust market,
ungeocoded target → explicit note (never an approximated location), zero
competitors → "sole-community on this screen, verify drive-time".
**Verify**: haversine vs known NYC–LA distance (2,446 vs ~2,445); ground
truth — Methodist Houston's nearest are CHI St. Luke's / Texas Children's /
Memorial Hermann at 0.2–0.3mi (the Texas Medical Center, literally), 41
competitors, share 16.3%; share math hand-built (100/400=25%, no-NPR target
→ None). tests/test_local_market.py (7); X-Ray suites 291 passed. $≥1B
renders as $13.48B per house style. Screenshot local_market.png.
**Persona check**: consultant opens the target X-Ray and immediately sees
it shares a campus with three $1B+ systems — the single most important
commercial fact about that asset, previously absent from the page.

## W2-9 — P9 slice-2: row-level diff detail view (14:50Z)
**What**: The saved-screens diff line gains a "detail" link →
?view=saved&diff=<id> renders a "What changed — <screen>" panel: ENTERED /
LEFT lists (facility names linked to their X-Ray, capped 25) and a CHANGED
table with field + old→new values (capped 50). Empty diff states the honesty
thresholds explicitly so "no changes" is a verifiable claim, not a shrug.
Owner-scoped by construction (only the owner's screens are iterated);
hostile saved-screen titles stay escaped (test with an XSS payload).
**Verify**: DiffDetailViewTests (4: rows with old→new + drill links;
empty-diff threshold statement; hostile title escaped; diff line links to
detail). Screener + snapshot suites 175 passed.

## W2-10 — bridge-realization accuracy was IN-SAMPLE; engine named generically (15:05Z)
**Found by**: scrutinizing the EBITDA-bridge page's claim "ML MODEL PREDICTS…
(ACCURACY: 60%, N=5,823)". The accuracy was computed on the SAME rows the
logistic regression trained on — in-sample accuracy presented to partners as
"accuracy" — and "ML model" is generic where the house bar is specific
engine naming.
**Fixed**: seeded 80/20 holdout inside train_realization_model (train on 80%,
report accuracy on the untouched 20%; fixed seed → reproducible number;
n_training now reports actual training rows). UI eyebrow now reads "Logistic
regression (margin-outperformance proxy)… Holdout accuracy 60%, trained on
n=4,659 filings". Measured holdout: 60.0% — the simple model wasn't
overfitting, but the claim is now honest and the n no longer overstates.
**Verify**: RealizationHoldoutTests (2: n_training == 80% split on a synthetic
frame; seeded → identical accuracy across calls; page names the engine and
drops "ML model predicts"); realization+bridge suites 126 passed.

## W2-11 — POST fuzz: /pipeline/add beds overflow 500s (15:20Z)
**Found by**: 63-request hostile-value fuzz over 7 POST endpoints (the GET
fuzz was clean; POSTs were untested). /pipeline/add 500'd twice: beds=1e309
(int(inf) → OverflowError, uncaught by the (ValueError,TypeError) handler)
and beds=1e24 (finite, but overflows SQLite's 64-bit INTEGER on insert).
**Fixed**: finite-check + clamp to [0, 100000] (no hospital has 100k beds) +
OverflowError in the except. Re-fuzz: 63/63 CLEAN.
**Verify**: PipelineAddBedsOverflowTests (4 hostile values < 500 over real
HTTP); suite 5 passed.

## W2-12 — X-Ray → local roll-up in one click + cross-surface consistency check (15:40Z)
**What**: (a) The local-market panel now ends with "Model a local roll-up
with the 3 nearest competitors →" seeding /pipeline/rollup?ccns=<target,+3
nearest> — one click from "who's nearby" to the full HHI/payer-blend/
save-to-deal scenario. (b) Ran a cross-surface consistency check: 450358's
filed NPR renders identically on the X-Ray and the Roll-Up facility table
($2,628.1M, matching the HCRIS frame exactly); the screener's absence is by
design (top-150 cap).
**Verify**: LocalRollupLinkTests (target leads the basket, +3 nearest);
local-market suite 8 passed.

## W2-13 — open-redirect: /\evil.com bypassed the //-only guards (15:55Z)
**Found by**: redirect-payload fuzz on the deal-context return= guard.
`return=/\evil.com` passed (startswith("/") true, startswith("//") false) but
browsers normalize `/\` → `//` → off-site redirect. The deal-context and
both pipeline return_to= guards shared the //-only pattern. (The three auth
next= guards already rejected backslash + "://" — not vulnerable.)
**Fixed**: single _safe_local_path helper — must start with one "/", second
char not "/" or "\", rejects control chars (header-splitting) — applied to
all three. Legit single-slash paths preserved (verified /deal/ccf round-trips).
The %2f%2f fuzz hit is a false positive (browsers don't decode %2f for origin,
stays same-origin).
**Verify**: test_open_redirect_guard.py (4: protocol-relative variants +
header-splitting rejected, legit paths + empty preserved); deal-context
suites 15 passed.

## W2-14 — radius HHI on the local-market panel (16:10Z)
**What**: The local-competitive-context panel gains a "RADIUS HHI (NPR)" KPI —
Herfindahl of NPR within the 25-mile radius (target + reporting competitors),
colored by the 2023 DOJ/FTC thresholds (green <1,500 / amber <2,500 / red
≥2,500). The most defensible LOCAL concentration number, more granular than
the state-proxy HHI. None when target NPR is a gap or no competitor reports —
never a 0. Reuses the antitrust Σ(100·share)² convention.
**Verify**: two-equal-facilities → 5,000 exactly; None without target NPR /
when alone; Methodist Houston → 1,066 (unconcentrated, credible for a 41-
hospital metro); panel renders the KPI. local-market suite 13, X-Ray 303 green.
**Persona check**: the antitrust read a consultant needs ("is this a
concentrated local market?") is now on the target's own page, on the DOJ
scale, sourced to filed NPR — not buried in a separate state-proxy screen.

## W2-15 — portfolio surfaces real anchor NPR (was blank) + $B rollup (16:35Z)
**Found by**: visual pass on /portfolio — Total Net Revenue and every NPR
column read "—" although the 5 composite demo deals are anchored to real
CCNs carrying filed HCRIS net_patient_revenue. The data existed; the portfolio
only read the flat key.
**Fixed**: list_deals now surfaces facility_anchor.net_patient_revenue as the
deal's net_revenue when no entered value exists (the deal's financial anchor
IS that real facility — Item 10's design), marked revenue_basis=anchor-actual.
Entered values still win (basis only marked when the anchor actually supplied
the figure — caught + fixed a mislabel mid-build). Portfolio Total Net Revenue
now reads $5.13B with a "filed anchor NPR" sub-label; _fmt_money rolls up to
$B at ≥$1B (was $5,129M).
**Verify**: AnchorRevenueSurfacingTests (3: anchor surfaces; entered wins
without anchor mislabel; portfolio labels the basis); portfolio/store/anchor
suites 472 passed; screenshot shows $5.13B + label.
**Persona check**: portfolio-ops user opens the book and sees $5.13B of real
filed revenue across the cohort instead of five blanks — the anchor work from
Item 10 now actually shows up where partners look.

## W2-16 — /my and /owner 500 on non-latin-1 owner (16:55Z)
**Found by**: 165-request GET fuzz over 15 more routes — /my/💉 500'd.
**Root cause**: deals_by_owner raises ValueError whose text echoes the owner;
the handler passed str(exc) to send_error's REASON PHRASE, which the HTTP
layer encodes latin-1 → UnicodeEncodeError → 500 (the 400 path caused a 500).
Two sites (/my, /owner). **Fixed**: ASCII-clean static reason phrase. Re-fuzz
165/165 clean. Also cross-validated the two HHI implementations (rollup _hhi
vs radius_hhi) agree exactly (3,888.89 hand-calc) — no divergence in the
headline antitrust number.
**Verify**: OwnerHeaderEncodingTests (/my + /owner emoji → 400 not 500);
HHI cross-check; suite 6 passed.

## W2-17 — comparable-outcomes "Comp P50 MOIC" headline silently blank (17:15Z)
**Found by**: visual review of /diligence/comparable-outcomes — the headline
KPI strip showed "COMP P50 MOIC —" while the outcome strip below showed
MEDIAN MOIC 2.40x. P50 == median, so the headline was failing to compute.
**Root cause**: it read a non-existent flat summary.get("moic_p50"); the
percentiles nest under summary["moic"]["median"|"p25"|"p75"] (as the working
strip uses). Fixed to read summary["moic"]["median"]. Now reads 2.40x,
consistent with the strip below.
**Verify**: test_comp_p50_moic_kpi_matches_median (headline carries a 2-dp
MOIC value on a populated comp set); comparable-outcomes suite 25 passed;
screenshot shows 2.40x.

## W2-18 — compare radar axis labels clipped (17:30Z)
**Found by**: visual review of /compare — radar axes read "x index", "net
coll", "sim rate" (truncated). The labels were the verbose
metric.replace("_"," ") strings ("case mix index", "net collection rate")
which overflowed the 300-wide SVG viewBox and got clipped at the edges.
**Fixed**: concise axis labels (Denial / AR days / Net coll. / Cost/$ /
Clean claim / CMI — full names live in the column table above) + a padded
viewBox (-55 -10 410 320) so even the longest sits inside. All six now
render fully.
**Verify**: RadarAxisLabelTests (concise labels present, verbose ones gone,
padded viewBox); comparison suites 24 passed; screenshot shows all 6 clean.

## W2-19 — CIM variance memo carries claim percentile + tail flag (17:50Z)
**What**: The variance memo (the txt deliverable a consultant drops into
call-prep) now includes "Claim percentile: pNN of n=K in-scope facilities"
per distribution-shaped claim, with "⚠ tail — scrutinize" on ≥p90/≤p10 — so
the on-screen W2-6 percentile context survives into the export. A claim that
passes the variance flag but sits at the top of the market is now a written
finding. Aggregate claims (counts, market size) get no percentile line.
**Verify**: MemoPercentileTests (tail claim → percentile + flag in memo;
aggregate → no line); real-data check (TX revenue claim p99 → "⚠ tail");
CIM suite 23 passed.

## W2-20 — portfolio opportunity figure: illustrative-denial caveat (18:10Z)
**Found by**: tracing the downstream effect of W2-15 — surfacing real anchor
NPR activated the "Recoverable Revenue" opportunity block (total_rev was 0
before, so it never rendered), which multiplies revenue × (avg denial − 8%).
The revenue is now real but the demo cohort's denial rates are illustrative,
so the dollar figure reads as hard when it's part-illustrative.
**Fixed**: when any deal carries rcm_metrics_basis=illustrative-demo, the
opportunity block appends an amber caveat ("revenue is filed anchor NPR, but
the denial rates on these composite demo deals are illustrative — confirm
against the target's own RCM data"). An all-real cohort gets no caveat.
**Verify**: OpportunityBasisCaveatTests (caveat for illustrative cohort,
absent for real); portfolio/anchor suites 17 passed. This closes the honesty
loop I opened with W2-15.

## W2-21 — /market-data card regressed to 303 (full-suite catch) (18:35Z)
**Found by**: the window-2 full suite (15,093 passed / 2 failed). One failure
was real: W2-1's /market-data → /map redirect turned the carded /market-data
A-Z tile into a 303, and test_every_az_card_returns_200 requires 200. (The
other failure, a guide-invariant, passed in isolation — a full-run
cross-test-state flake.)
**Fixed**: /market-data and /market-data/map now BOTH render the national-map
page directly (not a redirect), so the card returns 200 AND the Guide/
related-route links resolve. Updated the W2-1 test to assert a 200 render.
**Verify**: tools-index cards 21 passed; guide-invariant + market-data + guide
suites 56 passed.

## W2-22 — Service-area demographics on the X-Ray (new data integration) (18:55Z)
**What**: New CDD data integration — the vendored county demographics
(Census/ACS: 65+ share, uninsured rate, median HH income, rural %; surfaced
only in aggregate state pages before) now join to the target via its geocoded
county and render a "Service-area demographics" panel on the HCRIS X-Ray.
Each figure carries its CDD lens: 65+ = Medicare-demand proxy, uninsured =
bad-debt/self-pay risk, income = commercial-mix proxy, rural = access/labor.
Reuses the existing county_demographics loader (added a name-based CCN
resolver: CCN → geocode county → EXACT normalized name match within state;
98% of hospitals match, the rest show no panel — never a guessed county).
Honesty stated on-panel: service-AREA context, not the target's patient panel.
**Verify**: resolver tests (Methodist → Harris County 4.78M/11.7%/23.8%/
$68.7k; unknown CCN → empty; _norm_county bridges 'DE KALB'↔'DeKalb County');
panel renders with CDD lens + Census/ACS source + honesty note. X-Ray suites
312 passed. Screenshot.
**Persona check**: consultant sees the target sits in a 23.8%-uninsured county
— a bad-debt reality that reshapes the payer-mix underwrite no matter what the
CIM projects, surfaced on the target's own page.

## W2-23 — CIM Cross-Check market-demand backdrop (19:15Z)
**What**: The CIM results now carry a state payer-demand backdrop line
(Census/ACS): 65+ share · uninsured rate · median income, so a consultant
reads management's market-size and payer-mix claims against the real demand
profile ("a high-65+/high-uninsured market caps the realistic commercial
mix"). Reuses demographics_state(); empty when the state has no ACS row (no
fabricated backdrop). State-level, labeled as such (not the target's
patients).
**Verify**: MarketBackdropTests (renders on results, absent without results,
empty for unknown state); CIM + demographics suites green.

## W2-24 — community health-burden line on the X-Ray demographics panel (19:35Z)
**What**: The service-area demographics panel gains a state-level CDC PLACES
chronic-disease burden line (diabetes · obesity · fair/poor health) — a
structural acute/specialty demand signal. Reuses the existing
cdc_places_agg.places_equity_state loader; labeled state-level (coarser than
the county block above it), NaN measures skipped. Panel code tag now
CENSUS/ACS · CDC PLACES.
**Verify**: HealthBurdenLineTests (renders diabetes/obesity, CDC PLACES tag,
state-level label); X-Ray + demographics suites 302 passed.

## W2-25 — flaky guide-invariant = latent prod bug: stale metric index (19:55Z)
**Found by**: the window-2 full suite — test_every_metric_glossary_key_
resolves_via_guide failed in the full run but passed in isolation (order-
dependent).
**Root cause (real bug, not just a test issue)**: get_metric_context built
its resolver `_INDEX` ONCE at import from METRIC_REGISTRY. Other modules
register metrics / append aliases at THEIR import time (sector-guide,
data-source wiring), which during the full suite happens AFTER the index
froze — so a legitimately-registered metric silently failed to resolve in
the Guide. A metric added late would be unresolvable in production too.
**Fixed**: the resolver rebuilds the index on a miss and retries once (cheap,
miss-path only) — order-independent and correct for late registration.
**Verify**: direct mechanism test (metric added after import now resolves;
bogus key still unresolved; real keys unaffected); IndexRebuildTests (2) +
guide-invariant suite 31 passed; the 3 suspected order-trigger files run
together 50 passed.

## ───────────── WINDOW 2 SUMMARY (through checkpoint 19, 20:00Z) ─────────────
25 fixes/wins shipped across 15 checkpoints (PRs #1667–1681), each CI-green on
3.11/3.12/3.14 → merged → DigitalOcean deploy with the public health-check
gate green (deploys #1635–1649). Combined with window 1 (23 items, ckpts 1–4):
48 verified-live improvements this session.

BUGS (found by console sweeps, ~600-request hostile-input fuzzing, visual
review, and a full-suite cross-test-flake hunt):
- dead /market-data link; CIM/roll-up non-finite-param 500s; /pipeline/add
  beds-overflow 500; /my & /owner non-latin-1 500; /\ open-redirect bypass;
  workbench fabricated green $0; bridge-realization in-sample accuracy;
  comparable-outcomes blank P50 MOIC; clipped compare-radar labels; blank
  portfolio NPR; session-username never resolving; stale metric-resolver
  index (flaky invariant + latent prod bug); X-Ray $-format.
CDD / DATA-INTEGRATION:
- Local competitive context (25-mi radius geocode×HCRIS join) + radius HHI
  (DOJ/FTC scale) + one-click local roll-up; service-area county demographics
  (Census/ACS) + state community-health burden (CDC PLACES) on the X-Ray;
  CIM claim-percentile chips (+ in the memo) + market-demand backdrop; P9
  vintage-diff snapshots + row-level detail; portfolio real anchor NPR ($5.13B)
  with illustrative-denial caveat.
Full suite: 15,105 passing / 0 failing (flake fixed). Route walker clean
(162/163, 0 tracebacks/leaks). All deploys green on pedesk.app.

## W2-26 — blended service-area demographics on the roll-up platform (20:20Z)
**What**: The Roll-Up Builder gains a "Blended service-area demographics"
exhibit — population-weighted Census/ACS (65+, uninsured, median income)
across the platform's home counties, de-duped by county, with coverage
(covered/n facilities geocoded). The combined demand backdrop the pro-forma
payer mix has to live with. New blended_demographics_for_ccns() helper
(population-weighted, de-dups counties, empty when none match — never
fabricated). Exhibit-wrapped (now Exhibit 3) with the correct Census/ACS
source line (not the factory's HCRIS default).
**Verify**: blend tests (de-dup Harris+Dallas, population-weight, single-
county blend == that county, empty on no-match) + panel render; rollup +
exhibit + demographics suites 15+9 passed. Screenshot: Harris+Dallas, 11.8%
65+, 23.9% uninsured, $69,496, Exhibit 3, Census/ACS footer.
**Persona check**: a partner sizing a 3-hospital platform sees the combined
service area skews 23.9% uninsured — a bad-debt reality for the WHOLE
platform, on the same page as the HHI and synergy math.

## W2-27 — the REAL flake cause: test-glossary leak (20:45Z)
**Found by**: capturing the cert-suite assertion detail — the unresolved keys
were 'ma_penetration_test' and 'xss_test_metric', synthetic fixtures that
test_metric_glossary.py injects via define_metric() into the process-global
_GLOSSARY and never cleaned up. When that file ran before the guide-invariant
(which reads list_metrics() = _GLOSSARY keys), the invariant saw two keys
absent from METRIC_REGISTRY → fail. (W2-25's index-rebuild was a real latent-
prod-bug fix but couldn't address this — the keys were never real metrics.)
**Fixed**: both define_metric() tests now addCleanup(_GLOSSARY.pop, key) to
restore the shared dict. Running the polluter file immediately before the
invariant: 45 passed (was 1 failed).
**Verify**: test_metric_glossary alone green; polluter→invariant order green.

## W2-28 — X-Ray section jump-nav (21:10Z)
**What**: The HCRIS X-Ray grew to ~7,000px / 8 panels this window (peer
benchmark, public comps, regulatory, local market, demographics, peer roster,
state context, IC takeaway). Added a compact "On this page" jump-nav after
the hero — anchored chips per section. New _section_nav() helper anchors each
RENDERED block and builds the chip row; conditional panels that didn't resolve
(local market / demographics on an ungeocoded facility) are skipped, so the
nav never dangles. Nav is chrome-classed + non-sticky; the print-preview
branch omits it (deck stays clean). The IC anchor (#hx-ic, linked from the
source-purpose strip) moved from the ck_panel to the helper — single, unique.
**Verify**: helper tests (skips empty blocks, no nav for a single section);
render tests (nav + anchors present, #hx-ic unique); X-Ray suites 297 passed.
Screenshot: the 8-chip nav row.
**Persona check**: a partner on a 7,000px target page jumps straight to
"Local market" or "IC takeaway" instead of scrolling through six panels.

## W2-29 — roll-up money format: $B rollup at ≥$1B (21:30Z)
**Found by**: visual consistency check vs the X-Ray/portfolio $-format I
standardized — the Roll-Up Builder's _fmt_m rendered combined NPR as
"$10,169.2M" (a 3-hospital Houston platform). Same house-style nit.
**Fixed**: _fmt_m rolls up to "$X.XXB" at ≥$1B (combined NPR, facility NPR,
synergy all flow through it); sub-$1B stays "$M".
**Verify**: MoneyFormatTests (10169.2e6→$10.17B, 2.64e9→$2.64B, 5e8→$500.0M,
None→—; page shows $B); rollup + exhibit suites 20 passed.

## W2-30 — CIM Cross-Check $-format scales to B/M (21:35Z)
**Found by**: the CIM variance table rendered market-size claims as
"$97,365,412,101" — unreadable at billion scale.
**Fixed**: the "$" formatter scales to "$97.37B" / "$500.0M" (sub-$1M stays
whole dollars). Display-only — the variance math and the CSV export keep the
raw machine-precise values (verified the CSV cells stay numeric).
**Verify**: DollarFormatTests (scales B/M/raw; CSV stays raw multi-digit);
CIM suite 27 passed.

## W2-31 — Deal Quick-View money format: $B rollup at ≥$1B (21:55Z)
**Found by**: continuing the money-format consistency thread — the Deal
Quick-View's anchor panel rendered a >$1B filed NPR as "$1,194M NPR"
(Hennepin County MC, $1.194B) and the "Net Revenue" KPI used the same
$M-only divisor. Last hand-rolled `$M` spot at billion scale.
**Fixed**: anchor NPR line and the Net Revenue KPI now flow through the
canonical `ck_fmt_currency` (rolls $B at ≥$1B, $M at ≥$1M, $K at ≥$1K).
Hennepin anchor now reads "$1.19B NPR".
**Verify**: test_demo_anchor asserts "$1.19B NPR" present / "1,194M NPR"
absent; render check on net_revenue=1.45e9→$1.45B and 4.5e8→$450.0M;
deal-quick-view suites 35 passed.

## W2-32 — shared deal-context strip + payer-stress banner roll to $B (22:15Z)
**Found by**: tracing a stray "$1,194M NPR" in the Payer Stress render — it
came from the SHARED `deal_context_bar` (power_ui.py), the financial strip on
every analytic page that wires deal context. NPR and EV are platform-scale
and routinely exceed $1B, but rendered "$2,500M EV" / "$1,194M NPR".
**Fixed**: the strip's NPR / EBITDA / EV all flow through `ck_fmt_currency`
(rolls $B/$M/$K); also routed the Payer Stress masthead total-NPR meta through
it. Per-payer NPR figures stay $M (a single payer's share of even a $1.2B
system is ~$0.5B — sub-$1B, and a stable scale across the payer list).
**Verify**: deal_context_bar render → "$1.19B NPR · $179.0M EBITDA (15.0%
margin) · $2.50B EV · 14.0× entry"; new test_payer_stress banner test
($1.19B present / "1,194M NPR" absent); 3,042 passed across the pages that
consume the strip (pe_intelligence, analysis_packet, hospital-profile head,
irr_attribution, portfolio_snapshots).

## W2-33 — Target Scanner X-Ray button routes hospitals to HCRIS X-Ray (USER-REPORTED, 22:40Z)
**Found by**: user — "in target scanner, click on xray for hospitals doesn't
bring me to the right place."
**Root cause**: the per-row X-Ray button hard-coded
`/diligence/xray?ccn=&vertical=hospitals` (the generic CMS provider scanner)
for EVERY vertical, including hospitals — so a hospital row dropped the
partner on the wrong page instead of the rich HCRIS X-Ray (filed financials,
local market, demographics). The deal page and this page's own "next step"
hint already point hospitals at `/diligence/hcris-xray`.
**Fixed**: the button now routes by vertical — hospitals →
`/diligence/hcris-xray?ccn=`, every non-hospital vertical (home health,
hospice, SNF, dialysis, …) keeps the generic `/diligence/xray?ccn=&vertical=`
scanner (HCRIS doesn't apply to them).
**Verify**: render of AK hospitals → 24 hcris-xray row links, 0 generic;
home_health/hospice/snf/dialysis → generic scanner retained; new
XrayDrillRoutingTests (2) + screen-snapshot suite 20 passed.

## W2-34 — Deal dashboard de-duplicated + reorganized (USER-REPORTED, 23:10Z)
**Found by**: user — "deals have double titles and headers and bad
organization; make sure data is linked correctly and well aggregated."
**Root cause**: the /deal/<id> dashboard rendered the deal's financials
THREE times near the top — the title meta (`$820M NPR · $98M EBITDA ·
$1,082M EV`), the "DEAL SNAPSHOT" value-anchor (EV · NPR · recoverable ·
IRR), AND the 4-card KPI strip (Net Revenue · Rough EV · Recoverable
EBITDA) — so a partner saw the same numbers stacked three deep. Separately
the bottom "Up next → Open the full deal profile" link pointed back at
`/deal/<id>`, the very page being viewed (a dead self-link).
**Fixed** — one home per metric:
  - Title meta → identity only (`State · Deal id`); financials removed.
  - "DEAL SNAPSHOT" anchor → kept as the canonical valuation readout
    (EV · net revenue · recoverable EBITDA · IRR). Unchanged (test-pinned).
  - KPI strip → repurposed from a 2nd copy of EV/recoverable into the
    COMPLEMENTARY operating profile (Bed Count · Denial Rate · EBITDA
    Margin), 3-card grid.
  - "Up next" → now opens the analysis workbench (`/analysis/<id>`), a real
    forward surface, instead of self-linking.
  - Removed the now-dead ev_h / ebitda_h / ev_estimate_value / recoverable_value
    locals.
**Verify**: 5 dashboard tests pass — existing lead-anchor pins (DEAL SNAPSHOT
+ recoverable + anchor-before-explainer) still green; new
DealDashboardOrganizationTests assert title carries no NPR/EV, the strip is
operating-not-valuation (no "Rough EV"), and the forward link is
/analysis/<id> not the self /deal/<id>. Screenshot delivered.

## W2-35 — deal pages: $B rollup on the snapshot anchor + bar self-link guard (00:05Z)
**Found by**: continuing the user's deal-pages focus after W2-34 — the DEAL
SNAPSHOT anchor and the DCF/Denial tiles still hand-rolled $M (a $1.98B-EV
platform deal read "$1,982M EV"), and the ambient active-deal bar's "Deal
home" link was a self-link when already standing on /deal/<id> (same dead-
link class W2-34 fixed in "Up next").
**Fixed**: anchor EV/NPR/recoverable + DCF tile inline EV + Denial tile
recoverable all flow through ck_fmt_currency ($1.98B EV · $1.50B net
revenue · $27.0M recoverable); the bar JS now skips the "Deal home" link
when location.pathname is the deal's own page (links stay for Screener/
X-Ray/CIM + clear).
**Verify**: big-deal render → $1.98B EV / $1.50B net revenue / $27.0M
recoverable; dashboard suite 5 passed; chartis-kit/deal sweep 656 passed.
Also audited: deal quick-view headings (single h1, clean h2 ladder), all 16
dashboard model-tile /models/<slug>/ routes resolve in server.py (no dead
tiles), snapshot detail _fmt_kpi_val already rolls B/M/K.

## W2-36 — snapshot deal page links forward to the analysis surfaces (00:25Z)
**Found by**: deal-pages linkage audit — once a deal has snapshots,
/deal/<id> renders the audit-trail detail page INSTEAD of the model-tile
dashboard, and that page had ZERO links to the workbench or any of the 26
models. The deeper a deal got into the pipeline, the harder its own
analytics were to reach.
**Fixed**: the action row now carries "Open Workbench →" (/analysis/<id>)
and "Models" (/models/dcf/<id>) alongside Download/Set-Active — audit trail
and analytics one click apart again.
**Verify**: new test_snapshot_page_links_forward_to_analysis asserts both
hrefs on a seeded snapshot deal; test_server suite 68 passed.

## W2-37 — portfolio revenue column "$2KM" double-scale bug (00:50Z)
**Found by**: deal-data aggregation audit — the portfolio table's revenue
cell called `ck_fmt_currency(rev/1e6) + "M"`, double-scaling the value: a
$1.5B deal rendered "$2KM" (1500 → "$2K" → +"M") and a $500K deal "$0M".
**Fixed**: pass RAW dollars — `ck_fmt_currency(rev)` rolls B/M/K itself.
Also routed the Portfolio Value Opportunity (recoverable), Cross-Deal
Synergy (synergy EBITDA, RCM cost base, 11x equity value) figures through
ck_fmt_currency for the same consistency.
**Verify**: $11B 2-deal portfolio renders $11.00B total · $6.00B/$5.00B rows
· $165.0M recoverable · $52.8M synergy · $660.0M cost base · $580.8M equity;
new test_revenue_column_rolls_to_billions_not_2km; 73 passed across the 8
portfolio-overview suites.

## W2-38 — Comparable Outcomes de-cluttered (USER-REPORTED, 01:20Z)
**Found by**: user — "Comparable outcome page has too much data under the
title making it look awkward."
**Root cause**: the results view stacked THREE near-identical explainers
under the title (ck_source_purpose band + ck_page_explainer + a serif lede,
each restating "realized MOIC/IRR from the corpus, sanity-check bid
pricing"), PLUS a 3-card KPI strip (Comparables / Comp P50 MOIC / Win Rate)
that duplicated the outcome strip card-for-card — six blocks of overlapping
chrome before the table. The input form also sat between the KPI strip and
the outcome strip, splitting the results in half.
**Fixed**: one lede (the serif sentence) + the structured source_purpose
band (guard-test-required); dropped the verbatim ck_page_explainer; dropped
the duplicate KPI strip (matched count lives in the title meta + hold-card
sub); reordered to title → lede → provenance → inputs → ONE results strip
directly above the table → exports/print at point of use → verified-deals
footnote.
**Verify**: render shows single results strip ("Median MOIC"/"Win rate"
present, "Comp P50 MOIC" gone, page_explainer restatement gone, lede kept);
updated test_median_moic_stat_carries_value keeps the value-not-dash
invariant; new test_results_view_has_single_results_strip pins the
de-clutter; 34 passed across comparable suites + source-purpose guard.
Screenshot delivered.

## W2-39 — Entry EV/EBITDA distribution on Comparable Outcomes (01:55Z)
**Found by**: the page's stated purpose includes "what would this trade
for?" (bid-pricing sanity check) but no multiple ever rendered — the corpus
carries ev_mm + ebitda_at_entry_mm on the disclosed deals, unaggregated.
**Added**: summarize_outcomes computes the entry EV/EBITDA distribution
(median/p25/p75/n) across comps disclosing BOTH fields — never imputed, n
stated so a thin sample reads as thin; the outcome strip gains an "Entry
EV/EBITDA" stat card ("11.0x · p25 7.8x · p75 11.1x · n disclosed"); the
JSON API inherits entry_multiple via outcome_distribution for free.
**Verify**: unit tests pin the math (10x median over 9/10/11x; excluded
when EBITDA undisclosed; honest None/0-n when nothing discloses); HTTP test
pins the strip card; 50 passed across the 4 comparable suites. Screenshot
delivered.

## W2-40 — /deal-library/comps empty state: dead-end → junction (02:20Z)
**Found by**: research-side comps sweep — with no licensed export ingested,
the page rendered ONLY "No data yet — ingest a licensed export first",
stranding the partner, while the platform ships three comps surfaces that
work out of the box.
**Fixed**: the empty state now carries a CTA to /deal-library plus links to
the bundled surfaces — /find-comps (corpus profile-distance), /diligence/
comparable-outcomes (realized MOIC/IRR + the new entry-multiple
distribution), /verified-deals (source-linked subset).
**Verify**: render asserts all three hrefs + CTA; updated
test_empty_state_is_a_junction_not_a_dead_end; deal-library comps suite 4
passed; all three routes confirmed in server.py.

## W2-41 — sponsor track-record band on Comparable Outcomes (02:50Z)
**Found by**: market-intel gap — naming a buyer boosted same-sponsor comps
in the match score but never answered the partner's actual question: "what
does THIS house return?"
**Added**: sponsor_track_record(corpus, buyer) aggregates the named
sponsor's own corpus record (n deals / n realized / MOIC median+p25+p75 /
median IRR / active years — realized-only math, unrealized counted but
never imputed; None for empty/unknown buyer). The page renders a "Sponsor
record" band under the outcome strip with a tone-coded delta vs the comp
set median and a link to /verified-deals?sponsor=.
**Verify**: unit tests (realized-only aggregation incl. unrealized counted;
None for empty/unknown); HTTP tests (band when buyer given — "KKR: 76
corpus deals (61 realized) · median 3.00x · −0.25x vs comp set · IRR 21.8%
· active 2006–2024"; absent without buyer); 39 passed across comparable
suites. Screenshot delivered.

## W2-42 — Sector Momentum drill-down into Deal Search (03:15Z)
**Found by**: dynamics sweep — the momentum tables named 129 taxonomy
sectors but linked nowhere; a partner spotting "dialysis +400%" had to
retype the sector into Deal Search by hand.
**Added**: every sector cell (accelerating paired-block via SafeHtml +
decelerating table) links to /deal-search?sector=<name> — Deal Search
filters on the SAME corpus sector field with an exact match, so the
momentum read is one click from the underlying deals.
**Verify**: 20 drill links render on the default view; link target
resolves ("dialysis" → non-empty Deal Search results); new
test_sector_momentum_drilldown (link presence + taxonomy-name round-trip
into deal-search); 4 passed incl. seed-label guard.

## W2-43 — Deal Search EV column rolls to $B (03:35Z)
**Found by**: visually checking where the momentum drill-down lands — the
Deal Search EV column showed "$2000M" / "$1100M" / "$1000M" for the
billion-scale dialysis platform deals; Avg-EV KPI had the same ceiling.
**Fixed**: `_fmt_ev` rolls ev_mm to "$X.XXB" at ≥1000 ($1B); sub-$1B stays
"$540M". Avg-EV KPI rolls the same way.
**Verify**: dialysis sector renders $2.00B/$1.10B/$1.00B rows + $460M–$939M
below; new DealSearchEvRollupTests; 3 passed in the drilldown file; 23
passed across deal-search-touching suites.

## W2-46 — Public Market Intel: rebrand + market-read layout + live sentiment (USER-DIRECTED, 04:50Z)
**User asks**: (1) fix the cramped "Latest market read" panel spacing;
(2) add a button that fetches live web info and reports current market
sentiment; (3) remove the "Seeking Alpha" name ("that is not yours");
(4) remove the v3/v5 pages from the front-facing tools.
**Done**:
  - REBRAND: every front-facing "Seeking Alpha" label → "Public Market
    Intel" (page masthead/shell title, X-Ray cross-link + panel title,
    market-intel copy + nav label, regulatory-calendar panel title, chartis
    home tile, editorial/legacy kit navs, section landings, thesis-pipeline
    link, surface rankings). Curated news items' fabricated
    `source: Seeking Alpha` → "Industry wire". New canonical route
    /market-intel/public-market; legacy /seeking-alpha path still routes.
  - LAYOUT: market-read panel → two-column grid (read + callout left;
    benchmark chip + live check right) with real margins — kills the
    crammed-left/dead-right look.
  - LIVE SENTIMENT: new data_public/live_sentiment.py — on-demand fetch of
    public Google News RSS (fixed healthcare-PE queries, stdlib urllib, 6s
    timeout), transparent keyword lexicon scoring (matched terms reported
    back), GET /api/market-intel/live-sentiment endpoint, page button
    renders label/score/headline-count inline. Honest fallback when the
    install has no egress (ok=False + explanation; nothing fabricated).
  - TOOLS HYGIENE: /v3-status + /v5-status removed from the front-facing
    surface rankings (internal routes stay for maintainers).
**Verify**: page renders with zero "Seeking Alpha", grid + button present;
sentiment module scores transparently and never raises (sandbox fallback
verified); tests updated + new PublicMarketRebrandTests /
LiveSentimentModuleTests; 18 passed on the page suite, 304 passed across
nav/landing/palette/v3/v5 suites. Screenshot delivered.

## W2-47 — /tools instant filter (05:15Z)
**Found by**: user — "we have a lot of good stuff in there but it is hard
to get it out." The /tools catalogue lists ~100 ranked surfaces (174 links)
with no way to narrow.
**Added**: type-to-filter input above the catalogue — every row carries a
data-tx-search blob (label + route, the screener's pattern); sections with
zero matches collapse; a live "N tools match" count renders under the box;
Esc clears. Pure client-side, no new deps.
**Verify**: 98 rows carry search blobs; new ToolsFilterTests (filter input
+ blobs present, v3/v5 stay delisted, no third-party branding); tools
showcase suite 9 passed.

## W2-48 — federated /search: the find-anything box (USER-REPORTED, 05:50Z)
**Found by**: user — "the search bar still isn't even functional cause I
look up hospital and it renders nothing… think about the search acting
like a sharepoint for all the pages."
**Root cause**: /search only scanned portfolio deals + notes — the 6,123-
hospital HCRIS universe, the tools catalogue, and the public deals corpus
were all unsearchable from the topbar box.
**Fixed**: federated search across four universes, each hit linking to its
full surface:
  - HOSPITALS — HCRIS by name/CCN/city/state → the facility's full X-Ray
    profile (top 12 + "all in Target Screener →" overflow);
  - TOOLS & PAGES — the surface catalogue by label/route → the page;
  - MARKET DEALS — public deals corpus by target/buyer → Deal Search
    scoped to the query (top 8 + overflow link);
  - PORTFOLIO — deal ids/names/stages + full-text notes (as before).
  KPI strip shows per-universe counts; the empty state names what's
  searchable; every universe is wrapped fail-safe (search never 500s).
**Verify**: live server — "hospital"→12 hospital hits + tools + corpus;
"stanford"→3 X-Ray links; "bridge"→Bridge Audit; "kkr"→market deals;
~25ms warm. New test_federated_search (6: repro query, named hospital,
tool, sponsor, honest empty, hostile-input no-500); updated the B77 hint
pin; 4+6 passed, 198 passed across search-adjacent suites.

## W2-61 — per-segment growth divergence (12:55Z)
**Sprint depth**: the within-industry "where it's growing fastest" map.
Segment gains growth_pct; compute() emits per-segment Y-final TAM slices
and flags the fastest grower. BH (autism/IDD +10% ★ vs psych inpatient
+1%) and ASC (ortho/MSK +11% ★ — the total-joint migration) carry rates;
the segments table gains Growth %/yr + Y5-slice columns with the ★ row
highlighted; templates without rates keep the lean table.
**Verify**: autism Y5 slice pinned to ×1.10^5; ★ flags the max; columns
appear only when rates set; test_tam_sam 41 passed.

## W2-60 — industry #13: hospitals (HCRIS-grounded flagship) + cross-industry view (12:25Z)
**Sprint flagship**:
  - hospitals_template(): $1.4T NHE hospital-care line × 62% community
    share (AHA) = $868B; size-tier segments naming the thesis ("the
    PE/JV-able middle"); site-neutral payment risk as the policy headwind.
  - hospitals_deep_dive(): computed from the REAL HCRIS universe (6,123
    filers) — state footprint ranked by FILED NPR dollars (CA $154B / TX
    $97B / NY $90B), size-tier structure in place of the absent ownership
    field (honest: 4,507 small / 1,097 mid-size / 262 large), the
    1,097-filer $250M–$1B pool by state (CA 134 / TX 92 / FL 73), state
    median operating margins (X-Ray plausibility band, 52 states), 13
    corpus hospital deals.
  - CROSS-INDUSTRY VIEW: every sized vertical side by side — TAM ×
    composite growth, size bars, sorted by TAM, each row linking into its
    full build. "Where the biggest pieces grow fastest", answered on one
    panel.
**Verify**: chain pinned ($868B); dive pinned (6,123 filers, CA top >$100B
real NPR, mid-tier present, >1K pool, margins within ±band); comparison
panel carries ≥14 template links; test_tam_sam 39 passed. Screenshot
delivered.

## W2-59 — ±20% driver-sensitivity tornado on every build (11:55Z)
**Professional-modeling layer**: sensitivity(model) swings each chain
driver ±20% (rates clamped at 100%) holding the rest at base, sorted by
TAM impact — the classic IC tornado answering "which assumption moves
the answer". Rendered as an SVG low–high bar panel with the dashed
base-TAM line and per-bar ranges, on all 13 industry templates.
**Verify**: math pinned (one bar per driver, low<base<high, sorted by
impact, 95%-rate +20% clamps at 100% not 114%); renders on every
template; test_tam_sam 36 passed. Screenshot delivered.

## W2-58 — industries #9–12: physician groups, dental, oncology, urgent care (11:30Z)
**Sprint continuation** — four more PE verticals, all chains anchored to
named public sources, all with honest headwinds:
  - physician_group: 580K office-based MDs (AMA) × 42% independent ×
    $750K/MD (MGMA) = $182.7B; specialty segments (primary-care VBC,
    ortho ancillaries, the cardiology wave, mature derm); the
    independent-pool shrinkage carried as "the clock on the thesis".
  - dental: $165B NHE dental spend × 95% practice-delivered = $156.8B;
    DSO penetration (~13% of dentists) as the consolidation runway;
    benefit-cap stagnation as the headwind.
  - oncology: 2M new cases (ACS) × 55% community × $150K = $165B; buy-
    and-bill flagged as the margin engine; IRA drug-price negotiation +
    340B competition carried as structural headwinds.
  - urgent_care: 14K centers (UCA) × 14.6K visits × $165 = $33.7B; the
    $165-vs-$2,000-ED substitution as the tailwind; retail/telehealth
    skim as the headwind.
  All four use _deals_only_dive (geography omitted rather than
  fabricated; corpus trade history real — physician_group has 17 deals).
**Verify**: all four chains pinned; every template carries ≥1 negative
driver (pinned); all 14 registered templates render AND export valid
xlsx (pinned); test_tam_sam 33 passed.

## W2-57 — industries #7–8: behavioral health + ASC (11:00Z)
**Sprint continuation** — the two biggest PE service verticals without
CMS facility files.
  - behavioral_health_template(): 59M adults with AMI (SAMHSA NSDUH) ×
    50% treated × $3,000/yr blended = $88.5B; segments incl. autism/IDD
    (the fastest-growing sub-vertical) and residential (payer-scrutiny
    note); drivers incl. telehealth access (+3, the access-barrier
    mitigation lever), parity enforcement, and the clinician workforce
    shortage as the binding-constraint headwind. +7.6%/yr composite.
  - asc_template(): 6,300 certified ASCs × 3,650 cases × $2,000 = $46.0B;
    GI/ophtho/ortho-MSK/pain segments with the total-joint migration
    note; the HOPD site-of-care shift (+4) as the defining structural
    tailwind. +6.6%/yr composite.
  - _deals_only_dive(): for verticals WITHOUT a vendored facility file
    the honest layer is the sector's own corpus deal history — geography
    is OMITTED rather than fabricated, and the page says so.
**Verify**: both chains pinned to SAMHSA/CMS magnitudes; workforce
headwind sign pinned; deals-only renders show the trade history with no
State-footprint panel and the "rather than fabricated" disclosure;
test_tam_sam 30 passed.

## W2-56 — industries #5–6 (IRF, LTCH) + professionalism layer (10:30Z)
**Sprint continuation + the defensibility/training layer the user asked
for**:
  - irf_template ($8.1B, MedPAC; 60%-rule + MA-steering constraints) +
    ltch_template ($3.5B, MedPAC) — LTCH's composite growth is NEGATIVE by
    design (site-neutral criteria attrition): the tool sizes honest
    declines, demonstrated.
  - _simple_provider_dive() shared helper → irf_deep_dive (1,221
    facilities, TX top, discharge-to-community state medians) +
    ltch_deep_dive (317, 223 for-profit) with density whitespace.
  - PROJECTION GRAPH: TAM/SAM/SOM line chart (inline SVG, house palette,
    end-value labels) on every template — the IC's one-look growth picture.
  - FOOTNOTES: "Sources & footnotes" panel — every chain default, growth
    driver, dataset, and basis note numbered [1..n]; the xlsx export gains
    a 4th "Sources" sheet carrying the same trail. The defensibility/
    training layer: any number traces to a named public source.
**Verify**: IRF/LTCH chain math pinned; LTCH negative CAGR pinned; all 7
templates render chart + footnotes; xlsx 4 sheets with MedPAC strings in
Sources; test_tam_sam 28 passed. Screenshot delivered.

## W2-55 — industry #4: SNF template + deep dive (09:50Z)
**Sprint continuation**: skilled nursing — the richest CMS vertical file.
  - snf_template(): the base TAM driver is the REAL certified-bed count
    (1.569M from the vendored file) × 77% occupancy × 365 × $300 blended
    per-diem = $132B (the known industry size); payer segments (Medicaid
    62% volume payer / Medicare+MA 21% margin payer / private 17%);
    drivers incl. the federal staffing mandate, home-shift, and MA
    penetration carried as headwinds vs the 80+ demographic wave.
  - snf_deep_dive(): 14,699 facilities / 1,569,384 certified beds —
    state footprint with REAL bed capacity (TX 133K / CA 115K / OH 81K
    beds), ownership collapsed to IC buckets (10,849 for-profit), CMS
    star-rating state medians (52 states), 12-month change-of-ownership
    count surfaced as the live M&A turnover signal, and BED-DENSITY
    whitespace (beds per 10K seniors, lowest first) — AK/AZ/OR/NV/WA
    surface as the under-bedded HCBS-shift states.
**Verify**: chain math = the known ~$132B; bed total pinned EXACTLY to the
vendored file (1,569,384); TX top; whitespace ascending with Western states
first; page renders Beds/CHOW/star labels; test_tam_sam 24 passed.

## W2-54 — industry #3: hospice template + deep dive (09:15Z)
**Sprint continuation**: hospice joins — the most PE-penetrated post-acute
vertical.
  - hospice_template(): 1.72M Medicare users × 80 covered days × $185/day
    blended = $25.5B TAM (anchors to MedPAC ~$25B); level-of-care segments
    (RHC 97% of days — "the economics ARE RHC", GIP/continuous/respite);
    drivers incl. program-integrity scrutiny (OIG/CMS long-stay crackdown +
    CA license glut) and labor as headwinds.
  - hospice_deep_dive(): 6,852 CMS providers — CA 2,062 top (the license
    glut, visible honestly at the saturated end of the density ranking);
    4,744 for-profit pool (69%); care-index composite state medians (51
    states); density whitespace lowest-first (NY 0.11 / FL 0.13 / MD 0.25
    per 10K seniors); 4 corpus hospice deals.
**Verify**: chain math pinned to MedPAC magnitude; dive aggregates pinned
(CA top, >4K for-profit, no "-" buckets); page renders with Care-index
label + drill links; test_tam_sam 21 passed.

## W2-53 — industry #2: home health template + deep dive; dive schema generalized (08:45Z)
**Sprint continuation**: home health joins the builder.
  - home_health_template(): 67M Medicare beneficiaries → 5% HH users →
    2.9 PDGM periods → $2,010/period = $19.5B TAM (anchors to MedPAC);
    post-acute vs community segments; drivers incl. PDGM rate pressure,
    labor constraint, MA penetration carried as headwinds.
  - home_health_deep_dive(): 12,392 CMS agencies — state footprint
    (CA/TX/FL top), ownership mix with the 9,037-agency for-profit pool,
    state-median star ratings (52 states), and a DENSITY whitespace read:
    agencies per 10K seniors (ACS population × pct_65+) — NJ 0.2 / NY 0.3 /
    MD 0.5 surface as the structurally underserved CON states. "-"
    ownership labeled "Not reported", never a bare dash.
  - Dive schema generalized (capacity_label / pool_label+note /
    chains_label / quality_label / whitespace_mode pool|density) so each
    sprint industry plugs in; dialysis re-pinned on the new schema.
**Verify**: HH chain math pinned to MedPAC magnitude; dive aggregates
pinned (CA top, >8K for-profit, density ascending, no "-" buckets); both
industries render with their own labels; test_tam_sam 18 passed.
Screenshot delivered.

## W2-52 — industry deep-dive layer: dialysis grounded in live CMS data (USER-DIRECTED SPRINT, 08:00Z)
**User directive**: the TAM/SAM page becomes a long sprint — per industry:
state-by-state breakdown, payer, tailwind root causes + directionality,
whitespace, what's growing fastest, facility locations + performance, top-10
states, real CMS/public data, visualizations.
**Built (the per-industry pattern, dialysis first)**:
  - diligence/industry_deep_dive.py — registry keyed by template;
    dialysis_deep_dive() computes from the vendored CMS Dialysis Facility
    Compare file (7,557 facilities): per-state facilities/stations/
    independent counts + shares, top-10 states, chain landscape (DaVita
    2,800 + Fresenius 2,772 = 74% duopoly), the 742-independent acquirable
    pool ranked by state (NY 112 / CA 85 / FL 77), state median CMS
    hospitalization rates (≥5 reporting), sector deal history from the
    corpus (7 deals, 3.0x median MOIC, entry multiples). Fail-safe, never
    fabricates, every block names its source.
  - tam_sam_page: State-footprint panel (SVG bars, teal whitespace overlay
    + quality column), Consolidation-map panel (duopoly + whitespace read),
    What-this-sector-traded-for band with drill links (deal-search +
    screener); growth drivers now carry ▲/▼ directionality with root cause.
**Verify**: aggregates pinned (TX top, duopoly >50%, >500 independents,
whitespace real); unknown industries → None never 500; dialysis page
renders all three panels + drill links; fertility unaffected;
test_tam_sam 14 passed. Screenshot delivered.

## W2-51 — dialysis template on the TAM/SAM Builder (07:20Z)
**Found by**: one worked template reads as a demo; two read as a tool.
**Added**: dialysis_template() — US ESRD patients (USRDS) → % on dialysis
→ % in-center → treatments/yr → $/treatment (CMS PPS + commercial blend);
payer-mix segments (commercial 10% as THE economics segment, labeled);
growth drivers incl. the home-modality shift carried as a NEGATIVE driver,
not netted away. Template bar on the page gains the third chip.
**Verify**: chain math pinned (810K × 69% × 84% × 156 × $280 = $20.51B
TAM — right magnitude vs the ~$25B in-center market); segments sum to 1.0;
headwind sign pinned; page renders the template; test_tam_sam 10 passed.

## W2-49 — TAM/SAM Builder with formatted Excel export (USER-DIRECTED, 06:40Z)
**User ask**: in-depth TAM/SAM builds like the healthcare-PE CDD shops do —
the fertility example (total births → % IVF → IVF births → cycles per
delivery → % cycles → delivery), age-band segments (<35, 35–37, …), the
whitespace, growth decomposition (price inflation, benefit expansion,
access-barrier mitigation, supply increase, population, utilization), and
"go from some data to a fully formatted excel".
**Built**:
  - diligence/tam_sam.py — driver-chain model (base/rate/mult/price ops,
    per-step source labels, running-value audit trail), segments with
    success rates, TAM→SAM→SOM funnel, growth drivers composed
    multiplicatively (decomposition preserved), N-year projection. Bundled
    fertility_ivf_template (CDC/SART/ASRM-sourced defaults, labeled
    illustrative) + blank scaffold. compute() returns the full build.
  - exports/xlsx_writer.py — stdlib-only formatted .xlsx writer (zipfile +
    XML): bold navy headers, $ and % number formats, column widths, multi-
    sheet. No new runtime deps (openpyxl not added).
  - ui/tam_sam_page.py + routes /diligence/tam-sam, /api/diligence/
    tam-sam.csv|.xlsx — editable chain (every value overridable, clamped),
    funnel KPI strip, segment table, projection, one-click exports. Wired
    into the Cmd+K palette + surface rankings (not an island).
**Verify**: chain math pinned (3.66M × 2.3% × 2.5 × $20K = $4.209B TAM;
override 2.3→5.0% lifts to $9.15B live); growth composition pinned
(1.1×1.1 = 21%, not 20%); xlsx validates (zip clean, every part well-formed
XML, real $#,##0 numFmts, 3 sheets); hostile overrides never 500;
test_tam_sam 8 passed; palette guard 111 passed.

## W2-44 — Find Comps EV column rolls to $B (04:05Z)
**Found by**: global render-audit for billion-scale "$X,XXXM" leftovers
across the research surfaces (find-comps/verified-deals/deal-search/
market-data/sector-momentum) — only Find Comps still showed "$2,000M" /
"$4,350M" rows; everything else clean.
**Fixed**: results-table EV rolls to "$X.XXB" at ev_mm ≥ 1000.
**Verify**: render shows $1.00B–$4.35B, zero comma-M; new
test_find_comps_ev_rolls_to_billions; 12 passed across the audit suites.
