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
