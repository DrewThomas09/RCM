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

## W2-105 — wave #7: IC-packet review-glance strips (11:00Z)
**The packet at a glance**: two stacked strips directly under the IC
verdict hero — reasonableness BAND CHECKS (in-band green → implausible
deep-red, unknown gray) and HEURISTICS by severity (critical → low),
counts inline on wide slices, hover for exact numbers. A partner reads
the review's shape before the first section. None-review renders
nothing.
**Verify**: strips render for a PartnerReview; None-empty pinned;
ic-packet suites 29+2 passed.

## W2-104 — wave #6: checklist category progress chart (10:30Z)
**The checklist at a glance**: one stacked bar per category — DONE
green / IN-PROGRESS amber / OPEN gray / BLOCKED red — with done/total
counts per row and the full-state legend; the blocked category is
visible before scrolling the roster. Renders between the hero and the
phase sections; empty states render nothing.
**Verify**: chart + legend render; empty-state empty-string pinned;
checklist suites 76+2 passed.

## W2-103 — wave #5: thesis-pipeline compute chart (10:00Z)
**Where the pipeline spends its time**: per-step horizontal bars
(elapsed-ms proportional), OK steps teal, FAILED steps red with the ✗
inline — the slow or broken step visible before reading the log. Sits
between the step-log header and the detail rows; empty logs render
nothing.
**Verify**: ok/fail bars + red tone pinned; empty-log empty-string
pinned; thesis-pipeline suites 19+2 passed.

## W2-102 — wave #4: cliff-calendar hold timeline (09:30Z)
**The hold period as a picture**: one lollipop per cliff event on the
hold-year axis — drop length ∝ the bps cut, color by payer (medicare
navy / medicaid teal / commercial amber / 340B ochre), same-year events
jittered so nothing overprints, hover for the event detail, cumulative
in-hold bps annotated at the axis end, payer legend beneath. Renders
right under the KPI strip; empty holds render nothing.
**Verify**: timeline renders for hospital_general (OBBBA phases visible);
empty-report empty-string pinned; cliff suites 45+11 passed.

## W2-101 — wave #3: bankruptcy-survivor pattern strip (09:00Z)
**Diligence-page upgrade wave continues**: the bankruptcy-survivor scan
at a glance — one chip per pattern check (the 12 historical failure
fingerprints: Steward/Envision/Cano/Wellpath/APP class), FIRED chips lit
in their severity tone (CRITICAL red → LOW gray), passed chips muted
outline; a summary line ("3 of 12 patterns fired · 2 critical") above.
The eye finds the lit CRITICALs before reading a row of the table.
**Verify**: strip renders on a 3-fired/2-critical scan; empty-checks
empty-string pinned; bankruptcy suites 21 passed.

## W2-100 — wave #2: CIM Cross-Check variance chart (08:30Z)
**The 100th item of the window.** The cross-check at a glance: one
signed bar per VERIFIABLE claim — right of the dashed line = management
claims HIGH vs the public data, left = LOW; bar tone = the variance flag
(green/yellow/red); the % variance is the geometry so $B and % claims
share one honest unit-free scale; unverifiable claims are counted in a
note, NOT drawn ("no fabricated geometry"). Renders inside the numbered
exhibit above the variance table.
**Verify**: chart renders with real claims (TX market-size/margin/
Medicare); empty-result empty-string pinned; CIM suites 29+65 passed.

## W2-99 — DILIGENCE-PAGE UPGRADE WAVE opens: bear-case severity matrix (07:55Z)
**The wave the user directed** — functionality + visualization across
every diligence surface, starting with the Bear Case:
  - _severity_matrix_svg(): the bear case at a glance BEFORE the cards —
    a severity-stacked bar (CRITICAL red → LOW gray, semantic tones,
    counts inline) + a theme × severity dot matrix (REGULATORY/CREDIT/
    OPERATIONAL/… rows, lit dots per severity present, per-theme counts).
    Renders on both the full-pipeline and fast-path views; empty reports
    render nothing.
**Verify**: matrix renders on a fast-path bear case (regulatory evidence
present); empty-report empty-string pinned; bear suites 21 passed.

## W2-98 — jump nav on the build page (07:20Z)
**Usability for the now-9-panel page**: a one-line jump nav (the X-Ray
pattern) — Cross-industry · Chain · Segments · Projection · Sensitivity ·
Agenda · Market data (when a dive exists) · Sources — with anchors on
every panel.
**Verify**: all chips + anchors pinned; the Market-data chip tracks dive
availability; test_tam_sam 139 passed.

## W2-97 — growth-sort toggle on the cross-industry view (06:50Z)
**Both of the user's questions, first-class**: the 82-row comparison
panel now sorts by TAM ("where the biggest pieces are", default) or
composite growth ("where it's growing fastest") via a one-click toggle —
fertility (+12.5%/yr) leads the growth sort, hospitals ($868B) the TAM
sort. The active sort renders bold; the toggle preserves the selected
template.
**Verify**: default order pinned (hospitals before fertility); growth
order pinned (fertility before hospitals); test_tam_sam 137 passed.

## W2-96 — reciprocal linkage: Comparable Outcomes → "Size this market" (06:20Z)
**The loop closes both ways**: the CO results view now offers "Size this
market in the TAM/SAM Builder →" mapped via template_for_sector (all
five CO dropdown sectors resolve — specialty_group added to the map);
together with W2-95 the deal page, the comps page, and the sizing
catalogue are mutually one click apart.
**Verify**: CO hospital results deep-link to template=hospitals; all 5
CO sectors pinned against the registry; test_tam_sam 135 + comparable
suites green.

## W2-95 — deal-sector deep linking into the builder (05:55Z)
**Dynamic deal linkage**: "size the opportunity" on a deal's Market
Analysis now opens the TAM/SAM Builder PRE-SELECTED to the deal's own
vertical — SECTOR_TO_TEMPLATE maps ~90 deal/corpus sector tokens onto
the 82 templates (every mapped value pinned to a real template);
template_for_sector() normalizes case/hyphens/spaces; unknown sectors
fall back to the bare catalogue — never a guessed template; the link
helper is fail-safe (never 500s a deal page).
**Verify**: full map validated against the registry; normalization
pinned; BH deal deep-links, unknown falls back; test_tam_sam 133 passed.

## W2-94 — full-platform sweep complete: 15,280 passed (05:30Z)
**The regression verdict after 74 checkpoints of additions**: Q1 2,959 ·
Q2 3,485 · Q3 5,680 · Q4 3,156 = 15,280 PASSED, 72 skipped, with exactly
ONE failure across the entire platform — the guide-blind tam-sam page,
fixed and deployed as checkpoint 74 within the same cycle. The 82-
industry sprint added ~130 tests and broke nothing anywhere else.

## W2-93 — full-suite regression sweep + guide-blind fix (04:45Z)
**Found by**: the quartered full-platform sweep (Q1 2,959 passed · Q2
3,485 passed with ONE failure) — /diligence/tam-sam was GUIDE-BLIND:
live in the nav but missing from the assistant's tool-route registry,
so the PEdesk Guide couldn't answer questions about the sprint's
flagship page.
**Fixed**: ToolRouteDefinition for the TAM/SAM Builder (Diligence
Workspace category, aliases: market sizing/tam/sam/som).
**Verify**: test_guide_context_sufficiency 16 passed; Q3/Q4 of the sweep
continuing.

## W2-92 — agenda export parity: the questions travel into the workbook (04:15Z)
**Export parity for the training layer**: _derive_agenda_items() is the
single plain-text source for the page panel AND the exports — the CSV
gains an agenda block and the xlsx gains a 5th "Diligence agenda" sheet.
The deal team's workbook never carries a thinner question list than the
screen, and the panel/export derive identically (pinned: equal Q-counts).
**Verify**: CSV carries the biosimilar question; xlsx sheet5 exists and
carries it; panel-vs-export parity pinned; test_tam_sam 130 passed.

## W2-91 — the diligence agenda: auto-derived questions on every build (03:45Z)
**The training layer, catalogue-wide**: each build now renders a
"Diligence agenda" panel DERIVED from its own content — every priced
headwind becomes a "Quantify the exposure" question, the ★ fastest
segment becomes "Validate the growth thesis", declining segments become
"Size the decline", and the SAM/SOM notes become the addressability and
share questions. Nothing hand-written per industry; nothing the build
doesn't already assert. And it's LIVE: edit a driver above and the
agenda follows (pinned — flipping dialysis's home-shift positive removes
its question).
**Verify**: all 82 templates render an agenda with ≥1 exposure question;
rheumatology surfaces the biosimilar question; endo surfaces the
bariatric sizing; override-follows pinned; test_tam_sam 127 passed.

## W2-90 — segment-composition bar on every build (03:15Z)
**Catalogue-wide visual**: one stacked bar above each segments table —
how the TAM splits, house categorical hues, ★ on the fastest grower,
inline labels for wide slices + a legend for thin ones. One change, all
82 industries gain the composition picture.
**Verify**: every registered template renders the bar (pinned across the
full registry); ★ + percentage labels pinned; test_tam_sam 124 passed.

## W2-89 — batch 23: virtual primary, RPM, care navigation — 80-INDUSTRY MILESTONE (02:45Z)
**Niche-vertical sprint** — industries #80–82, crossing 80:
  - virtual_primary_care ($2.2B, +1.9%): 35M eligible × 15% ENGAGED ×
    $420 — "offered ≠ used" is the chain's honesty; the ENGAGEMENT GAP
    priced at −3 with Teladoc's impairment named as the case study and
    "the post-2021 telehealth reckoning" in the basis; DTC excluded
    from SAM (the economics don't close).
  - rpm ($2.0B, +5.4%): 60M appropriate × 3% enrolled × $1,100 CPT
    cycles — A CODE-CREATED MARKET, and the basis says the CPT family
    is both the TAM and the risk; OIG billing-integrity scrutiny ≤ −3
    (enrollment mills poisoned the well — compliance IS the moat);
    diabetes/CGM +12% ★ cross-links the DME wave.
  - care_navigation ($1.0B, +1.9%): 110M self-funded lives × 25%
    covered × $36 PEPM-year; full-replacement +8% ★ (Quantum class);
    the ROI-PROOF PRESSURE priced — "the category must prove savings
    or churn"; carrier-embedded substitution named.
**Verify**: chains pinned; engagement ≤ −3 + "reckoning" in basis + OIG
≤ −3 + "CODE-CREATED" in basis + ROI-pressure negative all pinned;
catalogue ≥83 templates pinned — THE 80-INDUSTRY MILESTONE CROSSED at
82; test_tam_sam 122 passed.

## W2-88 — niche verticals batch 22: air medical, pediatric PDN, ROI services (02:15Z)
**Niche-vertical sprint** — industries #77–79:
  - air_medical ($6.0B, +0.4%): 550K transports (AAMS) × $11K POST-NSA
    rates — the template prices a BROKEN PLAYBOOK: the NSA IDR reset
    killed the $40K balance-billed engine (−3, with Air Methods'
    bankruptcy named as the case study); rural closures as the access
    tailwind; fixed-wing/organ +7% ★ cross-links transplant.
  - pediatric_home_health ($15.1B, +4.4%): 400K medically-complex
    children × 45% authorized × 40 hrs × 50 wks × $42; vent-dependent
    +6% ★; the NURSE STAFFING GAP priced at −3.5 — "30-40% of
    authorized hours go UNSTAFFED: the binding constraint IS the
    business problem"; the $90K-vs-$500K institutional-diversion math.
  - roi_services ($0.9B, +0.9%): 95M record requests × 55% outsourced ×
    $18; payer/RADV retrieval +8% ★; NEAR-FLAT told honestly — info-
    blocking fee caps + TEFCA/FHIR API disintermediation both priced;
    Datavant dominance with the payer-retrieval challenger lane named.
**Verify**: chains pinned; NSA ≤ −3 + "bankruptcy" in basis + staffing
gap ≤ −3 + ROI <1.5% composite all pinned; catalogue ≥80 templates
pinned; test_tam_sam 119 passed. 79 industries.

## W2-87 — niche verticals batch 21: hospitalist, perfusion, sterile processing (01:45Z)
**Niche-vertical sprint** — industries #74–76, the micro-niche layer:
  - hospitalist ($5.9B, +2.4%): 44K hospitalists (SHM) × 35% contracted
    × $380K (subsidies fund ~50% of programs); telehospitalist +9% ★;
    the POST-ENVISION TRUST DEFICIT priced — hospitals burned by
    staffing-firm bankruptcies in-source; clean balance sheets win RFPs.
  - perfusion ($0.3B, +1.4%): 450K procedures × 45% outsourced ×
    $1,500 — a SUB-$1B MICRO-NICHE SIZED HONESTLY; ~4,500 CCPs with
    ~200/yr graduating: scarcity is BOTH the constraint and the
    outsourcing driver; organ-perfusion +10% ★ cross-links transplant.
  - sterile_processing ($0.4B at 8% penetration, +6.0%): the EARLY-
    CURVE thesis — offsite reprocessing +12% ★; "a missed tray cancels
    a case" — the courier-loop logistics risk priced; $10M+ builds
    named as the capital gate.
**Verify**: chains pinned; post-Envision negative + perfusion <$1B +
logistics negative all pinned; catalogue ≥77 templates pinned;
test_tam_sam 116 passed. 76 industries.

## W2-86 — niche verticals batch 20: retail clinics, surgical assist, HIT consulting (01:15Z)
**Niche-vertical sprint** — industries #71–73:
  - retail_clinics ($2.3B, +0.4%): THE FAILURE AUTOPSY TEMPLATE —
    post-retrenchment 1,800 clinics × 9.5K visits × $135; the big-box
    format −4% (Walmart exited, shown honestly); "the unit-economics
    problem" priced at −3 (standalone visit economics NEVER worked —
    Walmart/Walgreens proved it at scale); the basis says the training
    value IS the autopsy; SOM note demands the thesis explain why THIS
    time the economics close.
  - surgical_assist ($1.1B, +1.9%): 12M assist-eligible cases × 25%
    outsourced × $350; ortho/spine +6% ★ (ASCs don't have residents —
    structural demand); AS-modifier payer scrutiny priced.
  - hit_consulting ($21.6B, +3.9%): $120B provider IT spend × 18%
    services; AI enablement +15% ★ (every system needs a defensible AI
    roadmap); the EHR-IMPLEMENTATION MATURITY headwind priced — the
    big-bang Epic installs are DONE, the original market shrank.
**Verify**: chains pinned; big-box negative segment + unit-economics
≤ −3 + "autopsy" in basis + AI-fastest + EHR-maturity negative all
pinned; catalogue ≥74 templates pinned; test_tam_sam 113 passed.
73 industries.

## W2-85 — niche verticals batch 19: endo/obesity, pulmonology, transplant services (00:45Z)
**Niche-vertical sprint** — industries #68–70, hitting 70:
  - endocrinology_obesity ($4.2B, +4.7%): 16M GLP-1-era care seekers ×
    40% physician-managed × $650 — HONESTLY SCOPED: drug dollars flow
    to pharmacy, not the practice, and the basis says so; obesity
    programs +14% ★; GLP-1s CANNIBALIZE bariatric (−2% — intra-vertical
    disruption inside one template); endo scarcity (8K endos / 38M
    diabetics) priced at −3; coverage whipsaw priced.
  - pulmonology ($10.2B, +3.4%): 12K pulmonologists (CHEST) × $850K;
    interventional bronch/nodule programs +10% ★ (LDCT screening feeds
    robotic bronch); the ICU-pull honesty — "outpatient capacity is the
    residual"; SAM honestly 0.40 (most are hospital-employed).
  - transplant_services ($52.8B, +3.0%): 48K transplants (UNOS) ×
    $1.1M Milliman episodes; heart/lung +7% ★ (perfusion-tech era);
    SAM 0.15 with the basis stating WHY — the centers are academic and
    NOT acquirable; only the services shell (pharmacy mgmt, logistics,
    perfusion) is investable.
**Verify**: chains pinned; bariatric-negative-segment + pharmacy-in-basis
+ transplant SAM ≤0.20 + "academic" in basis all pinned; catalogue ≥71
templates pinned; test_tam_sam 109 passed. 70 industries.

## W2-84 — niche verticals batch 18: urology, rheumatology, neurology (00:15Z)
**Niche-vertical sprint** — industries #65–67, the infusion-ancillary
specialty map completed:
  - urology ($17.6B, +4.0%): 13.5K urologists (AUA) × $1.3M; advanced
    prostate +7% ★ (with the UM scrutiny attached); the WORKFORCE CLIFF
    named — the oldest surgical workforce, retirements outpacing
    residency slots, "both the risk and the seller motivation".
  - rheumatology ($6.6B, +1.3%): 6K rheumatologists (ACR) × $1.1M; "the
    practice IS an infusion center with a clinic attached"; BIOSIMILAR
    MARGIN EROSION priced at −3 with the basis naming it THE IC
    question — the model's margin engine is repricing; trials
    participation +8% ★ (the research-site adjacency).
  - neurology ($12.6B, +1.9%): 14K neurologists (AAN) × $900K; the
    ALZHEIMER'S-THERAPEUTICS ERA named — amyloid antibodies create an
    infusion+PET+monitoring pathway from nothing, infusion +11% ★;
    pre-wave whitespace (no scaled neuro platform exists);
    coverage-with-evidence friction priced.
**Verify**: chains pinned; biosimilar ≤ −3 + "margin engine" in basis +
amyloid-infusion-fastest + workforce-cliff negative all pinned;
catalogue ≥68 templates pinned; test_tam_sam 106 passed. 67 industries.

## W2-83 — niche verticals batch 17: dental labs, HTM, interpretation (23:45Z)
**Niche-vertical sprint** — industries #62–64:
  - dental_labs ($8.0B, +1.9%): 38M units (NADL) × $210; implant
    prosthetics +8% ★; the OFFSHORE SUBSTITUTION leak priced (China at
    50-60% price); the CDT craft-labor decline named; NDX context.
  - htm_clinical_engineering ($7.0B, +3.4%): 25M serviceable devices
    (AAMI/ECRI) × $280; ISO third-party +7% ★ (the OEM→ISO cost-out
    switch); the OEM LOCKOUT MOAT WAR priced (software keys block ISO
    service); SAM honestly 0.30 — only the ISO+rental layers are
    acquirable; Agiliti context.
  - interpretation ($3.2B, +2.4%): 380M LEP encounters × 30% paid ×
    $28; VRI +9% ★; Section 1557 enforcement as the compliance
    tailwind; AI DISPLACEMENT PRICED AT −3 with the basis note saying
    "underwrite the displacement curve, not around it" — the diligence
    centerpiece named.
**Verify**: chains pinned; offshore/lockout negatives + HTM SAM ≤0.35 +
AI ≤ −3 + "displacement curve" in basis all pinned; catalogue ≥65
templates pinned; test_tam_sam 103 passed. 64 industries.

## W2-82 — niche verticals batch 16: NEMT, 503B compounding, LOP medicine (23:15Z)
**Niche-vertical sprint** — industries #59–61; the test suite crossed 100:
  - nemt ($4.2B, +3.9%): 110M trips (MTAC/MACPAC) × $38 modality blend;
    MA supplemental +9% ★ (plans add transport for quality scores);
    Medicaid redetermination churn priced; Modivcare ~40% broker lock
    with regionals named as the targets.
  - compounding_503b ($2.4B, +1.8%): 80 FDA facilities × $30M; sterile
    injectables +7% ★ (the shortage backstop); FDA 483 RISK PRICED AT
    −3 — "a bad inspection closes a facility; quality IS the license";
    the GLP-1 shortage-list boom-bust exposure shown as one.
  - lop_medicine ($4.5B, +0.3%): 2.5M funded claims × 20% LOP × $9K;
    NEAR-FLAT and flagged as THE HIGHEST-DILIGENCE-BURDEN vertical in
    the catalogue — tort-reform risk −3 (state caps reprice the book
    overnight) + collectability discounts −2.5 (revenue recognition IS
    the diligence issue); referral concentration named as the real
    asset and the real risk.
**Verify**: chains pinned; 483 ≤ −3, tort ≤ −3, collectability ≤ −2,
"highest-" in LOP basis all pinned; catalogue ≥62 templates pinned;
test_tam_sam 100 passed. 61 industries.

## W2-81 — niche verticals batch 15: senior living, vascular access, genetic testing (22:45Z)
**Niche-vertical sprint** — industries #56–58:
  - senior_living ($86.7B, +5.4%): 1.6M units (NIC MAP) × 86% occupancy
    × $63K blended annual rate; active adult +9% ★ (the real-estate-
    light entry) and memory care +7% (dementia demographics); the
    construction-start drought named as a tailwind for existing assets;
    the AFFORDABILITY CEILING priced — "the TAM is gated by wealth";
    Brookdale ~4% operator fragmentation.
  - vascular_access ($3.2B, +3.4%): 560K HD patients (USRDS) × 1.8
    procedures × $3,200; home-access support +8% ★ (follows the home-
    dialysis push); the Azura/Lifeline vertical lock named; the
    atherectomy/OIG compliance headwind priced for the PAD adjacency.
  - genetic_testing ($6.8B, +5.4%): 8M tests × $850 (CLFS blend);
    oncology CGP +11% ★ (every targeted-therapy approval mandates its
    companion test); REIMBURSEMENT FRICTION priced at −3 — denial rates
    are the industry's defining problem; per-test price deflation as
    the second headwind.
**Verify**: chains pinned; affordability/atherectomy/reimbursement
negatives pinned (friction ≤ −3); catalogue ≥59 templates pinned;
test_tam_sam 97 passed. 58 industries.

## W2-80 — niche verticals batch 14: school services, mobile diagnostics, palliative (22:15Z)
**Niche-vertical sprint** — industries #53–55:
  - school_services ($8.1B, +4.5%): 7.5M IEP students (NCES) × 45%
    related services × $2,400; teletherapy +11% ★ (solved rural
    coverage); the ESSER funding cliff priced as the district-budget
    headwind; "districts can't hire — contracting IS the growth".
  - mobile_diagnostics ($1.5B, +3.4%): 28M LTC/homebound encounters ×
    55% mobile × $95; HaH/SNF-at-home adjacency +10% ★ (every care-at-
    home episode needs mobile dx); the post-TridentUSA fragmentation
    named as the rebuild opportunity; route-density economics as the
    margin truth.
  - palliative ($2.5B, +8.5%): 12M seriously ill (CAPC) × 5% community
    penetration × $4,200 — the 95% GAP IS THE THESIS; MA/VBC PMPM +14%
    ★ (payers fund avoided admissions); the FFS model's economic
    failure priced as a negative driver ("visit billing alone doesn't
    cover an IDT").
**Verify**: chains pinned; palliative penetration ≤10% + FFS-weakness
negative pinned; ESSER cliff negative pinned; catalogue ≥56 templates
pinned; test_tam_sam 94 passed. 55 industries.

## W2-79 — niche verticals batch 13: correctional, locum staffing, crisis — 50-INDUSTRY MILESTONE (21:45Z)
**Niche-vertical sprint** — industries #50–52, the milestone batch:
  - correctional_health ($7.8B, +4.5%): 1.9M incarcerated (BJS) × 55%
    outsourced × $7,500 (Pew/Vera); litigation-driven consent decrees
    named as the rate escalator AND headline/litigation risk priced as
    the existential operator risk — the diligence centerpiece, said so;
    behavioral/MAT mandates +9%; telehealth in-reach +10% ★.
  - locum_staffing ($6.0B, +3.4%): 9M unfilled FTE-days (SIA) × 35%
    agency-filled × $1,900; psych staffing +9% ★ (the deepest
    shortage); the TRAVEL-NURSE WHIPLASH precedent priced at −3 —
    systems slash agency spend the moment census normalizes.
  - crisis_services ($5.2B, +5.9%): 15M crisis episodes (SAMHSA/988) ×
    25% reaching funded care × $1,400; mobile crisis +12% ★ (ARPA
    Medicaid option); the GRANT-FUNDING CLIFF priced at −3 — the
    sustainability question every IC asks.
**Verify**: chains pinned; litigation/whiplash/grant-cliff negatives all
pinned (≤ −3 where named); catalogue ≥53 templates pinned — THE
50-INDUSTRY MILESTONE CROSSED at 52; test_tam_sam 91 passed.

## W2-78 — niche verticals batch 12: home care, PACE, teleradiology (21:15Z)
**Niche-vertical sprint** — industries #47–49:
  - home_care ($110.6B, +1.8%): 12M seniors needing ADL support (HHS) ×
    30% paid penetration × 20 hrs × 48 wks × $32 — the family-caregiving
    gap named as the demand reservoir; LTC insurance −1% (a DECLINING
    funding segment inside a growing market); the caregiver supply
    ceiling + wage pass-through as the margin truth.
  - pace ($7.6B, +8.0%): 80K participants (NPA) × $95K dual capitation;
    for-profit operators +12% ★; COMPLIANCE RISK PRICED AT −3 — "growth
    is a privilege revoked on audit failure" with the InnovAge sanction
    history named in the basis as the cautionary case study; <10%
    penetration of eligibles = the whitespace.
  - teleradiology ($1.7B, +5.0%): 650M studies (ACR) × 12% telerad ×
    $22/read; daytime overflow +9% ★ (staffing gaps made daytime the
    new market); AI triage named as productivity capture; per-click
    commoditization + in-group recapture as headwinds.
**Verify**: chains pinned; LTCI negative + PACE compliance ≤ −3 +
InnovAge in basis pinned; catalogue ≥50 templates pinned; test_tam_sam
88 passed. 49 industries.

## W2-77 — niche verticals batch 11: podiatry, ENT/allergy, anesthesia (20:45Z)
**Niche-vertical sprint** — industries #44–46:
  - podiatry ($9.9B, +2.9%): 18K DPMs (APMA) × $550K; diabetic foot +6%
    ★ (the annuity, cross-linked conceptually to the wound vertical);
    Medicare routine-care restrictions as the fee headwind.
  - ent_allergy ($15.7B, +4.0%): 16.5K MDs (AAO-HNS/AAAAI) × $950K;
    allergy/immunotherapy +6% ★ extract annuity; balloon-sinuplasty
    office migration as the site-shift template; OTC hearing-aid
    substitution eroding the audiology retail layer — shown as one.
  - anesthesia ($25.2B, +1.9%): 60M cases (ASA) × $420; THE PLAYBOOK
    HONESTY — the No Surprises Act rate reset priced at −2.5 ("OON
    arbitrage is DEAD; the old PE playbook does not work") and the
    basis note says why the 2010s anesthesia thesis failed; subsidy
    repricing named as the post-2021 structural shift; ASC/office +7% ★.
  All three: deals-only dives; the anesthesia dive note warns the corpus
  trade history priced a playbook that no longer exists.
**Verify**: chains pinned; NSA reset ≤ −2 + "playbook" in basis note
pinned; catalogue ≥47 templates pinned; test_tam_sam 85 passed.
46 industries.

## W2-76 — niche verticals batch 10: GI, orthopedics, women's health (20:15Z)
**Niche-vertical sprint** — industries #41–43, the remaining big PPM waves:
  - gastroenterology ($21.6B, +4.0%): 16K GIs (ACG) × $1.35M; the
    age-45 USPSTF step-up named as a structural tailwind; the COLOGUARD
    bear case (non-invasive substitution) priced as a headwind — the
    question that hangs over every GI IC; IBD/hepatology +6% ★.
  - orthopedics ($49.6B, +6.0%): 31K surgeons (AAOS) × $1.6M; total
    joints +8% ★ (the ASC-migration engine); CMMI bundled-payment risk
    + implant inflation as headwinds.
  - womens_health ($35.7B, +0.4%): 42K OBGYNs (ACOG) × $850K; NEAR-FLAT
    composite told as-is — OB +1% with births declining + malpractice
    drag, carried by fertility adjacency +9% ★ (the bridge to the IVF
    vertical) and the menopause renaissance +8%.
  All three: deals-only dives; geography omitted never fabricated.
**Verify**: chains pinned; Cologuard bear case negative pinned; women's
health <1.5% composite + fertility-fastest pinned; catalogue ≥44
templates pinned; test_tam_sam 82 passed. 43 industries.

## W2-75 — niche verticals batch 9: ophthalmology, RCM services, cardiology (19:45Z)
**Niche-vertical sprint** — industries #38–40:
  - ophthalmology ($34.2B, +3.9%): 19K ophthalmologists (AAO) × $1.8M
    (the highest revenue/MD specialty); retina +6% ★ buy-and-bill margin
    engine WITH anti-VEGF biosimilar erosion priced on the other side;
    premium-IOL cash-pay layer named.
  - rcm_services ($31.2B, +5.5%): the META-VERTICAL — the platform sizes
    its own industry. $2.6T provider NPR × 4% cost-to-collect (HFMA) ×
    30% outsourced; tech-enabled/AI workflow +12% ★ (the rerating
    layer); denial-complexity growth named as a vendor TAILWIND
    (provider pain = vendor revenue); in-sourcing churn risk priced.
  - cardiology ($46.2B, +5.0%): 33K cardiologists (ACC) × $1.4M; ASC/OBL
    procedures +11% ★ (the wave's engine); the honest shrinking-pool
    SAM at 0.20 — ~80% already hospital-employed, and employment
    gravity is a named headwind.
  All three: deals-only dives; geography omitted never fabricated.
**Verify**: chains pinned; cardiology SAM ≤0.25 + employment-gravity
negative pinned; in-sourcing churn negative pinned; catalogue ≥41
templates pinned; test_tam_sam 78 passed. 40 industries.

## W2-74 — niche verticals batch 8: eating disorders, nephrology, O&P (19:15Z)
**Niche-vertical sprint** — industries #35–37:
  - eating_disorders ($8.1B, +5.4%): 9M prevalent (NIMH/STRIPED) × 10%
    treated × $9K LOC blend — the 90% ACCESS GAP is in the chain and IS
    the thesis; outpatient/virtual +12% ★ (Equip-style FBT); clinician
    scarcity + payer LOS compression as headwinds.
  - nephrology ($9.9B, +4.5%): 11K nephrologists (ASN) × $900K; BOTH
    sides of the VBC thesis shown — value-based kidney contracts +15% ★
    AND model-rule uncertainty (CMMI reset risk) priced as a headwind;
    Panoramic/Evergreen land-grab context.
  - orthotics_prosthetics ($7.2B, +3.5%): 5.5M patients (AOPA) × $1,300;
    advanced upper-limb/MPK +8% ★ technology premium; the grim demand
    floor (~150K amputations/yr) named honestly; Hanger ~25% with the
    rest acquirable.
  All three: deals-only dives; geography omitted never fabricated.
**Verify**: chains pinned; VBC fastest + model-rule negative BOTH pinned;
ED treated-rate ≤15% pinned (the access gap); catalogue ≥38 templates
pinned; test_tam_sam 74 passed. 37 industries.

## W2-73 — niche verticals batch 7: LTC pharmacy, DME, IDD services (18:45Z)
**Niche-vertical sprint** — industries #32–34:
  - ltc_pharmacy ($18.8B, +0.9%): 3.1M LTC residents (ASCP/NIC) × 110
    scripts × $55; AL +6% ★ as census shifts from SNF; generic deflation
    makes the market NEAR-FLAT and the tool says so; Omnicare/PharMerica
    ~50% duopoly with AL as the open flank.
  - dme ($60.8B, +3.4%): 16M patients (CMS DMEPOS) × $3,800; diabetes/
    CGM +12% ★ (the fastest line in the entire catalogue's segments);
    competitive bidding carried as the defining headwind; respiratory
    consolidated, diabetes + complex rehab named as the open lanes.
  - idd_services ($67.5B, +2.4%): 1.5M supported individuals (KFF) ×
    $45K HCBS blend; host-home +9% ★ capital-light vs staffing-exposed
    group homes +3%; the DSP workforce crisis priced at −3 (vacancy
    ~15%, turnover ~45% — THE constraint).
  All three: deals-only dives; geography omitted never fabricated.
**Verify**: chains pinned; LTC-pharmacy near-flat pinned (<2%); bidding
negative pinned; DSP crisis ≤ −3 pinned; catalogue ≥35 templates pinned;
test_tam_sam 71 passed. 34 industries.

## W2-72 — niche verticals batch 6: dermatology, pain management, hospital-at-home (18:15Z)
**Niche-vertical sprint** — industries #29–31:
  - dermatology ($18.8B, +4.0%): 12,500 dermatologists (AAD) × $1.5M
    (MGMA incl. ancillaries); Mohs/surgical +6% ★; CONSOLIDATION
    MATURITY itself priced as a headwind — the first PPM wave already
    rolled the best markets; SOM note says the question is exit path,
    not entry runway.
  - pain_management ($10.2B, +3.4%): 51M chronic-pain adults (CDC) ×
    7% interventional × 2.6 procedures × $1,100; neuromodulation +8% ★;
    utilization management carried as the defining payer headwind.
  - hospital_at_home ($1.1B, +6.8%): 3M eligible admissions × 3%
    penetration × $12K — penetration is TINY and that gap is the
    thesis; enabler/vendor layer +20% ★ (the investable slice — system
    programs aren't acquirable, SAM 0.20 says so); the AHCaH WAIVER
    NON-RENEWAL RISK priced at −8%/yr: a market that can halve on one
    appropriations cycle, and the build says so.
  All three: deals-only dives; geography omitted never fabricated.
**Verify**: chains pinned; maturity/UM/waiver negatives pinned (waiver
≤ −5 specifically); catalogue ≥32 templates pinned; test_tam_sam 68
passed. 31 industries.

## W2-71 — niche verticals batch 5: wound care, sleep, occupational health (17:45Z)
**Niche-vertical sprint** — industries #26–28:
  - wound_care ($10.1B, +2.9%): 8.2M chronic-wound patients (Medicare
    claims literature) × 25% advanced care × 1.3 episodes × $3,800;
    office/mobile +8% ★ vs managed hospital centers +3%; the CMS
    skin-substitute (CTP) LCD crackdown carried as the compliance
    headwind; Healogics ~600-center context.
  - sleep ($5.4B, +2.9%): 30M OSA adults (AASM) × 20% in care × $900;
    the disruption told honestly — in-lab PSG −2% DECLINING inside a
    growing market while HSAT +9% ★; PAP resupply named as the annuity;
    the GLP-1 OSA-indication effect carried as the new bear case.
  - occ_health ($25.6B, +3.5%): 135M workers (BLS) × $190; on-site/
    near-site +8% ★; the secular injury-rate decline (TRIR) carried as
    the volume headwind; Concentra ~10% context.
  All three: deals-only dives; geography omitted never fabricated.
**Verify**: chains pinned; PSG negative + GLP-1 effect negative pinned;
catalogue ≥29 templates pinned; test_tam_sam 65 passed. 28 industries.

## W2-70 — niche verticals batch 4: ABA, plasma, clinical research sites (17:15Z)
**Niche-vertical sprint** — industries #23–25, the hyper-niche layer:
  - aba ($22.6B, +5.4%): 1.8M ASD children (CDC ADDM 1-in-36) × 30%
    receiving × 14 hrs/wk × 46 wks × $65; center-based +10% ★; the
    BCBA/RBT shortage carried as the binding constraint (access-
    constrained market: supply growth IS revenue growth).
  - plasma ($4.6B, +6.5%): 1,100 FDA centers (PPTA) × 28K donations ×
    $150; the honest structure read — 80% fractionator-owned and NOT
    acquirable, sam_share 0.20 says so; independent collectors +8% ★;
    recombinant substitution as the tail risk.
  - clinical_research ($52.5B, +7.0%): 6,000 industry trials × 25
    sites × $350K; dedicated sites/SMOs +9% ★; biotech-funding
    cyclicality (XBI-correlated) carried as the bear case; CRC
    turnover as the binding constraint.
  All three: deals-only dives; geography omitted never fabricated.
**Verify**: chains pinned; ABA labor-shortage negative pinned; plasma
SAM ≤0.25 pinned (fractionator-moat honesty); biotech cyclicality
negative pinned; test_tam_sam 62 passed. 26 industries total.

## W2-69 — niche verticals batch 3: clinical labs, specialty pharmacy, vision (16:45Z)
**Niche-vertical sprint** — industries #20–22:
  - clinical_labs ($68.6B, +3.9%): 14B tests (ACLA) × 35% independent ×
    $14; molecular/genomics +10% ★ vs PAMA-exposed routine +1.5%; the
    hospital-outreach divestiture pipeline named as a tailwind (it IS
    the M&A pipeline); Quest/Labcorp ~45% duopoly context in SOM.
  - specialty_pharmacy ($320B, +4.3%): the biggest dollar pool in the
    catalogue with the THINNEST margins — and the honest structure read:
    sam_share 0.20 because PBM verticals own 70% of the channel; the
    hub/patient-services adjacency +10% ★ named as where PE actually
    plays; Humira-class biosimilar deflation as the structural headwind.
  - vision ($60.5B, +3.0%): 195M corrected adults (Vision Council) ×
    $310; medical/surgical co-management +6% ★ vs online-disrupted
    retail +2%; myopia management named as the new recurring line.
  All three: deals-only dives; geography omitted never fabricated.
**Verify**: chains pinned; PAMA negative pinned; specialty-pharmacy SAM
≤0.25 pinned (the PBM-moat honesty); 23 templates render+export;
test_tam_sam 60 passed.

## W2-68 — niche verticals batch 2: veterinary, medspa, EMS (16:10Z)
**Niche-vertical sprint** — industries #17–19, the formats PE took
mainstream that CDD tooling never covers:
  - veterinary ($54.3B, +5.5%): 87M pet households (APPA) × 2.4 visits ×
    $260 (AVMA); vet urgent care +10% ★ de-novo format vs GP +4%; the
    DVM shortage carried as the binding constraint; Mars ~7% / ~75%
    independent fragmentation in SOM.
  - medspa ($16.8B, +8.0%): 10,500 locations (AmSpa) × $1.6M; GLP-1
    weight-management adjacency +15% ★ (with the compounding-rule risk
    note) vs devices +6%; consumer-cyclical exposure carried as the
    bear case.
  - ems ($11.9B, +0.4%): 22M transports (NEMSIS) × 40% private (GAO) ×
    $1,350; CCT/specialty +6% ★ vs 911 +2%; crew shortage + No
    Surprises ground-ambulance extension as headwinds — a near-flat
    market the tool does NOT inflate.
  All three: deals-only dives (no public facility census), geography
  omitted never fabricated.
**Verify**: three chains pinned; vertical-specific honesty pinned (DVM
shortage negative, consumer-cyclical negative, EMS composite <1%); all
20 templates render AND export valid xlsx; test_tam_sam 58 passed.

## W2-67 — niche verticals batch 1: infusion, imaging, physical therapy (15:40Z)
**Niche-vertical sprint (user-directed)** — industries #14–16, the
PE-active niches CDD shops actually field:
  - infusion ($37.4B, +7.0%): 3.2M infused patients (NHIA) × 18/yr ×
    $650; specialty biologics +9% ★ vs TPN +3%; BIOSIMILAR DEFLATION
    carried as the headwind (the #1 diligence question in the vertical);
    Option Care ~20% share noted in SOM.
  - imaging ($41.2B, +5.0%): 7,000 centers (IMV) × 21K scans × $280;
    PET/nuclear +9% ★ (oncology+amyloid tracers) vs plain film +2%;
    PFS technical-cut headwind; RadNet ~9% fragmentation note.
  - physical_therapy ($33.1B, +2.9%): 38K clinics (APTA) × 8.3K visits ×
    $105; pelvic/specialty +9% ★ cash-pay niche vs workers' comp +2%;
    Medicare fee cuts + PT wage inflation as the margin-squeeze pair.
  All three: deals-only dives with REAL corpus trade history (imaging 7
  deals · PT 6 · infusion 2), geography omitted never fabricated.
**Verify**: three chains pinned; every one carries ≥1 headwind + a
flagged fastest segment; biosimilar headwind named; trade history n
pinned; test_tam_sam 55 passed.

## W2-66 — chain-concentration HHI on the consolidation map (15:05Z)
**Sprint granularity**: the DOJ/FTC concentration metric PE diligence
actually cites. _chain_hhi() computes the Herfindahl index over NAMED
operators (the fragmented independent pool treated as atomized — the
standard "how concentrated is the CHAIN layer" read). Dialysis: HHI 2,768
→ "highly concentrated" (>2,500 threshold), color-toned by band
(<1500 green / 1500–2500 amber / >2500 red). Rendered only on dives with
real named operators (chains_label "Chain"); ownership-type / size-tier
buckets correctly show no HHI.
**Verify**: dialysis HHI >2500 pinned; HHI absent on HH/hospice/SNF/
hospitals (buckets, not operators); page shows the band label;
test_tam_sam 52 passed.

## W2-65 — state × payer dimension + fertility trade history (14:35Z)
**Sprint depth — "broken down by state, by payer"**:
  - hospitals dive gains the PAYER dimension: filed Medicare day-share
    state medians from HCRIS (CA 25.9%, real filings, ≥5 reporting) — a
    "Medicare mix (med)" column in the state footprint, rendered only
    where computed (dialysis et al. unchanged).
  - fertility (industry #0) gains its deals-only dive — 5 real corpus
    fertility/women's-health deals; geography stays omitted until CDC
    ART clinic data is vendored.
**Verify**: mix medians within [0,1], >5 states carry it; column absent on
dialysis; fertility n≥2 pinned; stale fertility-has-no-dive pin updated;
test_tam_sam 49 passed.

## W2-64 — export parity: divergence + scenario in CSV/XLSX (14:05Z)
**Sprint polish**: a deal team must never get a thinner file than the
screen. The CSV + the xlsx Segments sheet gain Growth %/yr + Y-final
slice columns; the xlsx funnel header carries the SCENARIO tag
("AGGRESSIVE scenario") so an exported model is never mistaken for base
case. Scenario flows through both export endpoints automatically (they
share model_from_qs).
**Verify**: CSV carries the columns; xlsx sheet1 carries the scenario
tag and sheet2 the divergence columns (pinned); test_tam_sam 46 passed.

## W2-63 — divergence map completed across the catalogue (13:40Z)
**Sprint depth**: segment growth rates on 4 more templates —
  - oncology: med onc +7% ★ (drug spend) vs rad onc +1%
    (hypofractionation drag);
  - dental: implants +8% ★ vs pediatric +2% (Medicaid-capped);
  - physician groups: cardiology +8% ★ (the current wave) vs derm +2%
    (mature);
  - hospitals: large systems +6% ★ vs small/rural −1% (an honest
    DECLINING segment inside a growing market).
Six verticals now carry within-industry divergence (+ BH/ASC from W2-61).
**Verify**: fastest flags pinned per vertical; small/rural negative
renders red; test_tam_sam 44 passed.

## W2-62 — scenario presets: Conservative / Base / Aggressive (13:15Z)
**Sprint depth**: one-click scenario toggles on every build — Conservative
halves tailwinds and amplifies headwinds ×1.5, Aggressive mirrors, typed
driver values always win (presets apply before explicit overrides). BH
composite swings +1.7% / +7.6% / +13.9% across the three.
**Verify**: ordering pinned (con < base < agg); typed override beats the
preset (pinned); chips render with active state; test_tam_sam 44 passed.

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

## W2-106 (2026-06-11) — Denial drivers page: root-cause Pareto chart (wave #8)
**Found**: denial_page.py was the barest remaining diligence surface —
0 SVGs across 246 lines; the "Denial Root Causes" card was a plain
table whose only visual was an 8px HTML div bar with no severity
encoding and no concentration read.
**Fixed**: `_driver_pareto_svg(drivers)` — horizontal bars sorted by
annual dollar impact (largest first), severity-toned (high #b5321e /
medium #b8732a / low #7a8699), per-bar $M label plus a running
"cum %" share so the 80/20 concentration of the recovery opportunity
is visible at a glance; legend explains tones and cum%. Derived
entirely from the page's existing `analysis["drivers"]`; zero/empty
impacts render "" (never fabricated geometry).
**Verify**: DriverParetoChartTests — render pins all three tones +
cum 100% close, sort order (Prior auth $2.0M before Eligibility
$1.5M), chart placed before the table, empty/zero drivers render
nothing, page survives empty analysis. 27 passed across denial suites.

## W2-107 (2026-06-11) — Red flags page: category × severity cluster map (wave #9)
**Found**: /deal/<id>/red-flags sorted hits by severity (banner, KPI
strip, three severity sections) but never showed *where* the flags
cluster — a deal with five flags all in one category reads identically
to five scattered ones, and the category tag was buried per-row.
**Fixed**: `_category_severity_svg(review)` — one stacked horizontal
bar per category, segments toned by the page's own _SEV_COLORS,
rows sorted by severity weight (CRITICAL 8 / HIGH 4 / MEDIUM 2 /
LOW 1) so the most dangerous category leads; per-row total, legend.
Placed between the KPI strip and ADDITIONAL SIGNALS. Derived from
review.heuristic_hits; no hits renders "".
**Verify**: CategorySeverityMapTests — tones pinned, one CRITICAL
outranks three LOWs in row order, None category buckets as
Uncategorized, unknown severity treated as LOW, empty renders
nothing. 35 passed with the corpus red-flags suite.

## W2-108 (2026-06-11) — Investability page: exit-readiness dimension profile (wave #10)
**Found**: /deal/<id>/investability rendered the 12-dimension exit-
readiness check as a table only — the dimensions dragging the verdict
down had no visual ranking, and weights were a text column you had to
mentally multiply.
**Fixed**: `_readiness_profile_svg(report)` — one bar per scored
finding on a fixed 0–100 axis, toned by the page's own
_FINDING_STATUS_COLORS, sorted weakest-first so the drag leads, weight
labels (· w 8%), and a dashed vertical guide at the composite score so
each dimension reads above/below the roll-up. Unscored findings
omitted; report None / no scored findings renders "".
**Verify**: ReadinessProfileTests — weakest-first order, all status
tones, composite guide + weight label pinned, unscored omitted,
3 empty states render "". 21 passed across investability suites.

## W2-109 (2026-06-11) — Management scorecard: team-at-a-glance heat matrix (wave #11)
**Found**: /diligence/management rendered one tall card per executive
— comparing the CFO's forecast reliability against the CEO's meant
scrolling between cards; no single view put the roster side by side.
**Fixed**: `_team_matrix_svg(scores)` — heat matrix of executives ×
the four scoring dimensions + Overall, cells colored by the page's own
_score_color bands with the score inside, rows in the same
red-flags-first order as the cards, ✗ marking red-flagged execs,
Overall column bold (it carries the red-flag cap). Placed between the
section label and the cards. Empty roster renders "".
**Verify**: TeamMatrixSvgTests — all execs + 5 column headers, ✗ only
on the flagged exec, red-flags lead row order, empty → "", matrix
present in full page render. 35 passed in scorecard suite.

## W2-110 (2026-06-11) — Market structure page: 100% composition strip (wave #12)
**Found**: /deal/<id>/market-structure ranked each player against its
own per-row bar, but the unallocated remainder — the fragmented tail
that IS the roll-up whitespace the fragmentation verdict describes —
was invisible; you had to subtract CR5 from 100 in your head.
**Fixed**: `_market_composition_svg(shares, target_name)` — one 100%
strip: named players as proportional segments (target in the accent
tone, label+share printed when the segment is wide enough), and the
remainder as a gray "fragmented N%" block annotated ROLL-UP
WHITESPACE. Fully-allocated markets omit the remainder rather than
inventing one; zero/negative shares skipped; empty renders "".
Placed above the shares table in the SHR panel.
**Verify**: MarketCompositionStripTests — remainder math (30+20+10 →
fragmented 40%), no remainder at 100%, largest-first segment order,
ghost/negative shares skipped, empty → "". 7 passed with the
market-structure suite.

## W2-111 (2026-06-11) — White space page: conviction spectrum (wave #13)
**Found**: /deal/<id>/white-space rendered opportunity cards per
dimension, but the 0–1 conviction distribution — where scores cluster
against the 0.25/0.50/0.75 bands the page explainer documents — had
no visual; you read "score 0.82" card by card.
**Fixed**: `_score_spectrum_svg(by_dim)` — one row per dimension
(geographic/segment/channel, in the page's own dimension colors),
every opportunity a dot on a fixed 0–1 axis toned by the page's own
_score_color bands, dashed guides at 0.25/0.50/0.75, best opportunity
per row labeled with name + score. Dimensions with no opportunities
omitted; scores clamped to the axis; nothing scored renders "".
Placed above the dimension card sections.
**Verify**: ScoreSpectrumTests — rows/guides/tones pinned, empty
CHANNEL row omitted, best-per-row labeled while runner-up unlabeled,
out-of-range score clamps to axis end (cx=650), empty → "".
17 passed with the white-space suites.

## W2-112 (2026-06-11) — Deal screening page: risk distribution strip (wave #14)
**Found**: /deal-screening showed PASS/WATCH/FAIL tile counts and a
ranked table, but the screened population was never drawn on the
risk-composite axis — moving the watch/reject thresholds in the form
gave no picture of which deals would shift verdict.
**Fixed**: `_risk_distribution_svg(results, watch_thr, max_thr)` —
every screened deal as a dot on a fixed 0–100 axis with deterministic
lane jitter, toned by the page's own _DECISION_COLORS, dashed labeled
guides at the *active* thresholds from the parsed config (so the
chart tracks the user's form inputs). Out-of-range thresholds omit
their guide; unscored results skipped; nothing scored renders "".
Placed directly under the decision tiles.
**Verify**: RiskDistributionTests — guides labeled WATCH ≥50 /
REJECT ≥75, all three decision tones, out-of-range guide omitted,
unscored skipped (count drops), empty → "". 16 passed across the
screening suites.

## W2-113 (2026-06-11) — Data room page: signed surprise chart (wave #15)
**Found**: the data room's stated purpose is showing "exactly where
the seller data confirms or contradicts our models", but the
contradiction lived only in a table delta column and a >15% text
list — no visual put all the surprises on one axis.
**Fixed**: `_calibration_delta_svg(calibrations)` — every metric with
both an ML prior and a seller delta drawn as a signed bar from a
center "ML PREDICTION" line: relative surprise = delta ÷ |prediction|,
green when favorable for the metric's direction (a lower-is-better
denial rate coming in lower), red when unfavorable, gray when
direction is unknown; sorted by magnitude; axis clamped ±50% with a ›
marker beyond. ML-only metrics contribute nothing; empty renders "".
Placed between the surprises panel and the bridge impact.
**Verify**: CalibrationDeltaChartTests — direction-aware tones
(lower+lower → green, higher+lower → red), magnitude sort, +80.0%›
clamp marker, ML-only → "", empty → "". 27 passed across data-room
suites.

## W2-114 (2026-06-11) — Portfolio risk scan: priority decomposition (wave #16)
**Found**: /portfolio/risk-scan sorts deals by a composite
_priority_rank the reader never sees — "first row because covenant
tripped" vs "first row because four deadlines slipped" was invisible;
the table only showed the per-dimension chips.
**Fixed**: `_priority_components(deal)` keeps the exact _priority_rank
arithmetic per source (covenant 100/30, overdue ×20, alerts ×5,
health 40/15, staleness 20/10); `_priority_breakdown_svg(deals)`
draws the top-10 deals as stacked bars segmented by source with the
total printed and a 5-source legend. Quiet (zero-priority) deals are
skipped; an all-quiet portfolio renders nothing. Placed between the
color key and the CSV link.
**Verify**: components sum equals _priority_rank across covenant/
alert/health/stale mixes; ranked order pinned; quiet deal absent;
total 105 printed for TRIPPED+1 alert; all-quiet → "". 22 passed
across risk-scan suites.

## W2-115 (2026-06-11) — Archetype page: confidence ladder (wave #17)
**Found**: /deal/<id>/archetype printed each match's confidence
inside its own card — the separation between a dominant primary
(0.78) and a marginal runner-up (0.31) read the same as a coin-flip
0.52 vs 0.49; the band thresholds existed only in prose.
**Fixed**: `_confidence_ladder_svg(hits)` — every matched archetype
as a bar on a fixed 0–1 axis, toned by the page's own
_confidence_band (HIGH/MEDIUM/LOW), dashed guides at the 0.25 match
floor and the 0.50 / 0.75 band edges, value + band printed per bar,
sorted highest-first. Confidence clamps to the axis; no hits renders
"". Placed above the archetype cards.
**Verify**: ConfidenceLadderTests — band tones + labels (0.78 HIGH /
0.31 LOW), 0.25-floor guide, confidence sort, overshoot clamps to
1.00, empty → "". 110 passed across archetype suites.

## W2-116 (2026-06-11) — Provider X-ray: percentile profile (wave #18)
**Found**: the CMS X-Ray's peer-benchmark table printed four
percentile columns per metric — the provider's overall shape
(top-quartile on outcomes, bottom-quartile on cost) required reading
every cell; nothing drew the profile.
**Fixed**: `_percentile_profile_svg(report)` — one row per metric on
a fixed 0–100 percentile axis: state percentile as a filled dot toned
by quartile (≥75 green / ≥50 teal / ≥25 amber / <25 brick, higher =
better), national percentile as a hollow reference ring, dashed
MEDIAN guide at 50. Suppressed (n<5) percentiles are simply absent —
the table below keeps the n/a detail; nothing plottable renders "".
Placed above the benchmark table inside the Peer benchmarks ribbon.
**Verify**: PercentileProfileTests — quartile tone bands pinned
(80→green, 60→teal, 30→amber, 10→brick), suppressed-state metric
still plots its national ring, fully-suppressed metric omitted,
empty/None → "". 161 passed across X-ray suites.

## W2-117 (2026-06-11) — Roll-up builder: platform composition strip (wave #19)
**Found**: /pipeline/rollup's facility table listed absolute filed
NPR per facility but never answered the structural question a deal
team asks first — is this scenario an anchor + tuck-ins or a merger
of equals?
**Fixed**: `_platform_composition_svg(facilities)` — one 100% strip
of combined filed NPR, segments per facility largest-first with
share labels, plus a shape verdict from the top facility's share
(≥50% ANCHOR + TUCK-INS · ≤35% BALANCED PLATFORM · else LEAD
FACILITY + PEERS). Shares are of *reported* NPR only — facilities
without filed NPR are excluded and counted in the caption, never
imputed. Fewer than two reporting facilities renders "". Placed
above the selected-facilities table.
**Verify**: PlatformCompositionTests — 60% top share → ANCHOR +
TUCK-INS, equal quarters → BALANCED PLATFORM, missing-NPR facility
excluded + noted, <2 reporting → "". 132 passed across rollup
suites.

## W2-118 (2026-06-11) — IC memo page: integrity strip (wave #20)
**Found**: /models/memo rendered sections as a vertical stack of
panels with a per-section Verified/Check Required badge — seeing the
memo's overall shape (which sections dominate, which are unverified)
required scrolling the whole page; "the two longest sections are the
unverified ones" was invisible.
**Fixed**: `_memo_integrity_svg(sections)` — one strip where each
section is a block sized by its share of the memo's words (with a
readability floor, renormalized) and toned by fact-check status
(green verified / red check required), section names printed in wide
blocks, caption totaling sections · verified · check-required ·
words. No sections renders "". Placed above the section panels.
**Verify**: MemoIntegrityStripTests — both tones + caption counts
(2 SECTIONS · 1 VERIFIED · 1 CHECK REQUIRED · 700 WORDS), document
order preserved, empty → "", strip precedes section panels in the
full page render. 184 passed across memo suites.

## W2-119 (2026-06-11) — Counterfactual advisor: lever impact chart (wave #21)
**Found**: /diligence/counterfactual rendered each offer-shape lever
as a card — comparing savings size against feasibility across levers
(the IC question: "where's the money and can we actually get it?")
meant reading every card.
**Fixed**: `_lever_impact_svg(cf_set)` — one bar per dollar-
quantified lever sized by savings estimate, toned by the page's own
_feasibility_color (HIGH unilateral green / MEDIUM amber / LOW
third-party red), value + feasibility printed per bar, sorted
largest-first. Qualitative levers are counted in the caption, never
drawn at an invented size; no quantified levers renders "". Placed
under the Counterfactuals section head.
**Verify**: LeverImpactChartTests — feasibility tones + $2.4M·HIGH /
$600K·LOW labels, impact sort, qualitative counted-not-drawn,
all-qualitative → "". 43 passed across counterfactual suites.

## W2-120 (2026-06-11) — Compare page: advantage strip (wave #22)
**Found**: /diligence/compare's table showed a delta badge per row,
but the bake-off verdict — who wins more rows, and by how much —
required tallying badges by eye down the table.
**Fixed**: `_advantage_strip_svg(pairs, left, right)` — a diverging
chart where each metric's bar extends toward the row's winner
(direction-aware: lower OON share wins for the lower side), sized by
the relative gap and clamped at ±60% with a › marker. Built from the
same (label, left, right, higher_is_better) tuples the table rows
append, so chart and table can never disagree; caption tallies rows
won per side; both-zero rows skipped; ties render a neutral dot.
Placed above the metric table.
**Verify**: AdvantageStripTests — direction-aware tally (ALPHA 1 /
BETA 1 with a lower-is-better row), 90%› clamp label, both-zero
skipped + tie dot, empty → "". 107 passed across compare suites.

## W2-121 (2026-06-11) — Waterfall page: tier cascade chart (wave #23)
**Found**: /models/waterfall had, ironically, no waterfall — the
tiers lived in a table and the LP/GP economics in one aggregate
split bar; where in the stack the GP starts taking (the carry
mechanics IC actually asks about) was invisible.
**Fixed**: `_tier_waterfall_svg(tiers)` — cascading columns
left-to-right, one per distribution tier, each rising from the
running total and split into LP (navy) and GP (green) dollars, with
dashed connectors between levels, per-tier $M totals, tier names,
and a caption totaling the cascade. Zero-dollar (unreached) tiers
skipped; no funded tiers renders "". Placed above the tier table.
**Verify**: TierWaterfallTests — cascade renders with LP/GP split +
$200.0M total caption, tier order preserved, unreached tier skipped,
empty → "", chart precedes the tier table in the full page render.
108 passed across waterfall suites.

## W2-122 (2026-06-11) — Bayesian calibration page: interval plot (wave #24)
**Found**: /bayesian described shrinkage in a table (prior, observed,
posterior, % and an 80px weight bar) but never drew the geometry —
how far each posterior moved from its prior toward the observed
value, and how wide the 90% credible interval remains.
**Fixed**: `_posterior_interval_svg(estimates)` — one row per metric
on its own normalized mini-axis: 90% CI as a shaded band, posterior
as a filled dot toned by data quality (strong green / moderate teal /
weak amber / prior_only brick), prior as a hollow ring, observed as
an × only when observed_n > 0. Legend explains the encoding and that
each row has its own scale. Estimates with malformed fields skipped;
empty renders "". Placed inside the estimates card above the table.
**Verify**: PosteriorIntervalChartTests — quality tones, × only with
data (prior_only row omits it), prior ring + posterior dot pinned,
empty → "". 18 passed across bayesian suites.

## W2-123 (2026-06-11) — Calibration page: payer landscape (wave #25)
**Found**: /calibration rendered one slider card per payer —
comparing payers (the actual calibration question: which payer is
the outlier dragging the priors?) meant eyeballing slider positions
across stacked cards.
**Fixed**: `_payer_landscape_svg(aggs)` — every payer as a labeled
dot on the same three fixed axes the sliders use (IDR 0–0.5, FWR
0–0.8, DAR 0–120), tick labels at min/mid/max, alternating label
rows to limit collisions, values clamped to the axis. Caption names
the read ("the dot furthest from the pack is the payer dragging
calibration"). Empty aggregates render "". Placed above the slider
cards.
**Verify**: PayerLandscapeTests — 3 payers × 3 axes = 9 dots, axis
ticks match slider ranges (0.500 / 0.800 / 120), out-of-range value
clamps to the axis end, empty → "". 89 passed across calibration
suites.

## W2-124 (2026-06-11) — Escalations page: aging chart (wave #26)
**Found**: /escalations printed "Nd open" per row; nothing drew the
relative staleness of the queue or visually separated live alerts
from acknowledged-but-still-open ones — "three deals have been red
for a quarter and nobody silenced them" required reading every row.
**Fixed**: `_aging_svg(df, min_days)` — one bar per escalated alert,
sized by days open, oldest first, brick for live and gray for
acknowledged (the ACKED suffix carries into the value label), header
naming the threshold, capped at the 20 oldest with the cap declared
in the legend. None/empty frames render "". Placed above the
severity panel.
**Verify**: EscalationsAgingChartTests — both tones + "45d ACKED"
label + threshold header, oldest-first order, exactly 20 rects at
the cap with "20 OLDEST SHOWN", None/empty → "". 37 passed across
escalation suites.

## W2-125 (2026-06-11) — Portfolio monitor: health-history BUG FIX + trend chart (wave #27)
**Found**: a real silent bug — /portfolio/monitor queried
`ORDER BY date` against deal_health_history whose column is
`at_date`; sqlite raised "no such column: date" into the bare
except, so health_rows was ALWAYS empty and health scores never
rendered on the monitor (latest_health stayed None for every deal,
the red-band early-warning never fired, the distribution bar counted
everything as Unscored).
**Fixed**: (1) query corrected to `SELECT deal_id, at_date, score,
band … ORDER BY at_date DESC` with downstream indices updated;
(2) the recovered history now also feeds `_health_trend_svg` — one
line per deal with ≥2 recorded scores on a fixed 0–100 axis, band
guides at 80 (GREEN) and 50 (AMBER), lines right-aligned to end at
the latest snapshot with name+score labels, capped at the 8
most-sampled deals; single-score deals counted in the caption, not
drawn. Placed after the health distribution bar.
**Verify**: HealthQueryRegressionTests extracts the exact query from
the source and runs it against the real DDL (would have caught the
original bug); trend tests pin band guides, latest-score labels,
single-score counted-not-drawn, empty → "". 61 passed across monitor
suites.

## W2-126 (2026-06-11) — Phantom-table query audit: 5 dead queries fixed (wave #28)
**Found**: after W2-125's silent column bug, swept every raw SELECT
in rcm_mc/ui (42 of them) against the real CREATE TABLE DDL. Four
more queries hit tables that DON'T EXIST, each swallowed by a bare
except so the page rendered a permanent empty state:
- chartis/home_page `_health_distribution` → `deal_health_scores`
  (real: deal_health_history) — home page health panel always empty.
- chartis/home_page `_alerts` + `_kpi_strip` count → `alerts` —
  home alert panel always "No active alerts", KPI always 0.
- command_center alert list → `alerts` — always empty.
- portfolio_monitor alert load → `alerts` — per-deal alerts and the
  ≥3-alerts early-warning never fired.
**Fixed**: health distribution reads the latest score per deal from
deal_health_history; all three alert readers join alert_history
(persisted sightings) LEFT JOIN alert_acks excluding acked rows,
aliasing title→message and last_seen_at→fired_at so downstream
rendering is unchanged.
**Verify**: tests/test_dead_table_queries.py extracts the EXACT
queries from each page source and runs them against schemas created
by the production _ensure_table functions; pins the unacked join
(ack removes the row); and asserts no UI query references `FROM
alerts` or deal_health_scores anywhere. 5 audit tests + 50 page
tests passed.

## W2-127 (2026-06-11) — Phantom-COLUMN audit: 3 more dead queries fixed (wave #29)
**Found**: extended W2-126's audit from table existence to column-
level validation (built an in-memory DB from every CREATE TABLE in
the codebase, ran all 42 UI SELECTs). Three more silent failures:
- chartis/home_page `_deadlines` selected a phantom `title` column
  (real: `label`) — the "deadlines within 7 days" panel was ALWAYS
  empty.
- settings_ai_page summed phantom `cost_usd_estimate` (real:
  `cost_usd`, confirmed against the INSERT) in both cost queries —
  AI spend always showed $0 / no per-model rows.
- portfolio_monitor selected phantom `snapshot_json` from
  deal_snapshots (flat columns only) — stage was always blank.
(`deals.archived_at` and deal_library_companies flagged too but are
real — added by ALTER-TABLE migrations / dynamic DDL.)
**Fixed**: `label AS title`; `SUM(cost_usd)`; snapshots select
deal_id/stage/notes/created_at with the dead JSON-parse branch
removed.
**Verify**: 3 new cases in test_dead_table_queries.py — each builds
the real schema via the production _ensure_table function, runs the
exact query from the page source, and (for deadlines) asserts the
aliased title round-trips. 8 audit tests + 24 page tests passed.

## W2-128 (2026-06-11) — Server-side phantom query: quality enrichment never ran (wave #30)
**Found**: extended the audit to all 1,309 non-UI files. After
eliminating false positives (ALTER-TABLE migrations, dynamic DDL,
module-constant schemas), one real phantom remained: the hospital-
profile route in server.py enriched profiles from a
`benchmark_values` table that no code anywhere creates — the CMS
Care Compare quality data actually lands in `hospital_benchmarks`
(written by data_refresh.save_benchmarks). The try/except meant the
star-rating/quality enrichment on hospital profiles silently never
ran since the feature shipped.
**Fixed**: query reads `metric_key, value FROM hospital_benchmarks
WHERE provider_id = ? AND value IS NOT NULL ORDER BY loaded_at DESC`
— same downstream keys (q["metric_key"], q["value"]), so the
enrichment loop is unchanged.
**Verify**: new audit case seeds hospital_benchmarks via the real
save_benchmarks(), extracts the exact query from server.py, asserts
the round-trip (star_rating → 4.0); a guard test bans
benchmark_values references codebase-wide. 10 audit tests passed.

## W2-129 (2026-06-11) — Fund learning page: planned-vs-realized chart (wave #31)
**Found**: /fund-learning carried planned, actual, and realization %
as table columns — the shortfall geometry ("we planned $4M from
denial recovery and got $1.5M") required mental arithmetic per row,
and the table's order didn't show where the dollars concentrate.
**Fixed**: `_lever_realization_svg(lever_biases)` — per lever, the
planned uplift as a dashed hollow track and the realized dollars as
a filled bar on the same axis, toned by the page's own realization
bands (≥85% green / ≥60% amber / below red), labeled "38% of $4.0M",
sorted by planned size. Zero-plan levers skipped; empty renders "".
Placed inside the Per-Lever Accuracy card above the table.
**Verify**: LeverRealizationChartTests — dashed track + band tones +
"38% of $4.0M"/"95% of $2.0M" labels, planned-size sort, zero-plan
skipped, empty → "". 27 passed across fund-learning suites.

## W2-130 (2026-06-11) — Physician EU page: signed contribution chart (wave #32)
**Found**: /diligence/physician-eu ranked providers by contribution
in a sortable table, but the practice's structure — "three providers
fund it, two drain it" — lived in a color-coded dollars column you
had to read row by row.
**Fixed**: `_contribution_svg(report)` — each provider's annual
contribution (after comp + allocated overhead) as a signed bar from
a zero line, in the table's own tones: red when loss-making at FMV
comp, amber when only at observed comp, green at ≥40% margin; rank
order matches the roster; caption counts FMV vs observed-only
loss-makers. Empty rosters render "". Placed inside the roster
panel above the table.
**Verify**: ContributionChartTests — all 8 demo providers render,
rank order pinned, negative tone present with the FMV count in the
caption, empty → "". 186 passed across physician suites.

## W2-131 (2026-06-11) — Data quality page: gap census chart (wave #33)
**Found**: /data-quality's gap census listed gaps per metric in a
table — which metrics are most gapped, and whether the gaps are
fixable (re-ingest / external source) or filing artifacts, required
reading every row.
**Fixed**: `_gap_census_svg(rep)` — one bar per gapped metric sized
by gap %, toned by fill kind (amber = re-ingest fixes it, ochre =
needs an external source, gray = filing artifact, not fillable),
labeled "12.5% · 7,650", worst-first, capped at 15 with the cap
declared. Zero-gap metrics skipped; empty census renders "". Census
failure keeps the existing error row (chart stays ""). Placed above
the gap table.
**Verify**: GapCensusChartTests — all three fill-kind tones +
artifact legend, worst-first order, zero-gap skipped + exactly 15
rects at the cap, empty → "". 22 passed across data-quality suites.

## W2-132 (2026-06-11) — Returns page: covenant runway gauge (wave #34)
**Found**: /models/returns described covenant headroom in KPI tiles
and a prose line ("EBITDA can decline 30% before the 6.0x covenant
trips") — the runway geometry, how close current leverage actually
sits to the ceiling, was never drawn.
**Fixed**: `_covenant_runway_svg(actual_lev, max_lev, cov_ebitda,
trips_at)` — a leverage runway on a fixed scale: current leverage as
a bar toned by remaining headroom (>1.5 turns green / >0.5 amber /
else red), the covenant max as a hard red line with label, the
headroom annotated in turns; plus a second strip translating the
same risk into EBITDA terms (cushion $M of current EBITDA, trip
level shaded red) only when the EBITDA data exists. Missing covenant
data renders "". Placed at the top of the Covenant Headroom card.
**Verify**: CovenantRunwayTests — green band + "1.8x HEADROOM" +
"cushion $15M of $50M EBITDA", tight headroom goes red with no
fabricated EBITDA strip, amber band pinned, missing data → "".
904 passed across returns suites.

## W2-133 (2026-06-11) — My dashboard: deadline timeline (wave #35)
**Found**: /my/<owner> listed overdue and upcoming deadlines as two
separate lists — how the analyst's fortnight actually clusters
(three things due the same Thursday) was invisible.
**Fixed**: `_deadline_timeline_svg(my_od, my_up)` — every open
deadline as a lollipop on a calendar axis from the oldest overdue
item to today+14: a dashed TODAY line, overdue markers red to its
left, upcoming navy to its right, stems staggered to limit label
collisions, each labeled deal · label, caption counting overdue vs
due-in-14d. Unparseable dates skipped; no open deadlines renders
"". Placed between the alerts panel and the deadline lists.
**Verify**: DeadlineTimelineTests — both tones + TODAY + caption
counts, overdue marker geometrically left of the TODAY line and
upcoming right (regex on cx coordinates), garbage dates skipped,
empty/None → "". 19 passed across my-dashboard suites.

## W2-134 (2026-06-11) — Full-platform regression sweep (wave #36)
**Found**: nothing — and that's the record. After 28 consecutive
shipped waves (14 diligence visualizations W2-106…W2-121,
the phantom-table/column audit arc W2-125…W2-128, and 7 more
visuals W2-129…W2-133), ran the complete suite in four quarters:
Q1 3,005 · Q2 3,510 · Q3 5,713 · Q4 3,193 = **15,421 passed,
72 skipped, 1 xfailed, 0 failures** across all 1,015 test files.
**Verify**: every wave in the run is covered by its own pinned
tests; the audit guards (test_dead_table_queries.py) now police the
phantom-query class platform-wide on every CI run.

## W2-135 (2026-06-11) — Verified deals page: vintage timeline (wave #37)
**Found**: the 445-deal verified catalogue (/verified-deals) had
outcome-mix and sponsor bars but no time axis — when a sector's
consolidation actually happened, and whether the deal flow dried up,
was invisible in a table sorted by sector.
**Fixed**: `_vintage_svg(deals)` — deal count per vintage year as
columns over the filtered set (so sector/sponsor chips re-scope the
chart), drought years keep their empty slot, peak-year counts
labeled, span + deal count in the header. Fewer than two distinct
years renders "". Placed after the outcome/sponsor analytics grid.
**Verify**: VintageChartTests — renders the real 445-deal catalogue,
2018×3 + 2021×1 → exactly 2 columns with 2019/2020 drought slots and
the peak count label, single-year/empty → "", chart present in the
full page render. 17 passed across verified-deals suites.

## W2-136 (2026-06-11) — Diligence checklist: auditable IC-readiness gate (wave #38)
**Found**: /diligence/checklist tracked item statuses and a P0-
coverage KPI, but the actual CDD question — "can this deal go to
IC, and if not, exactly what closes the gap?" — was left to the
partner to infer from the coverage percentage. No single auditable
go/no-go with a verification trail.
**Added (analysis, not just a visual)**: `compute_ic_readiness(state)`
in the checklist tracker → an `ICReadinessGate`:
- verdict is a PURE function of item statuses (NOT_READY if any P0
  open/blocked · CONDITIONAL if only P1s remain · READY if all P0+P1
  closed) so it can never disagree with the checklist it sits above;
- every blocker (`GateBlocker`) carries the *verification path*: its
  completion_criteria ("closes when…"), the evidence_url that
  produces that evidence, and `auto_verifiable` (closable from
  DealObservations vs. needs a partner attestation);
- the gate splits open work into auto-verifiable vs. manual-
  attestation counts, so the partner sees how much the platform can
  confirm itself.
Surfaced on the page as a verdict band + verifiability mini-bar +
evidence-linked punch-list (P0 hard-stops, then P1s), and folded into
the page's JSON export under `ic_readiness_gate` so the gate is
downloadable/auditable. Verdict order: blocked-before-open, then by
phase.
**Verify**: test_ic_readiness_gate.py (9) — empty deal NOT_READY,
all-P0-done→CONDITIONAL, all-done→READY, p0_coverage matches the
state, each blocker's auto_verifiable mirrors its auto_check_key,
verifiability split sums to total blockers, to_dict round-trips the
punch-list, gate renders in the page + JSON export. 116 passed
across checklist/IC-packet suites.

## W2-137 (2026-06-11) — CIM cross-check: auditable credibility index (wave #39)
**Found**: /diligence/cim-crosscheck flagged each claim's variance
against HCRIS and counted green/yellow/red/unverifiable, but never
synthesized the CDD question a partner actually asks — "how much
should we trust this CIM, and does management systematically inflate?"
**Added (analysis, verifiable)**: `compute_cim_credibility(result)`
→ a `CIMCredibility`:
- score 0–100, a deterministic pure function of the rows
  (100 − 28·red − 10·yellow − 6·unverifiable, floored), so it can
  never drift from the variance table it summarizes;
- band (Corroborated / Mixed / Overstated / Unsubstantiated) with an
  honest override: zero verifiable claims → Unsubstantiated
  regardless of score ("can't check it" is a finding, not a pass);
- `overstatement_bias` = mean signed variance across verifiable rows
  → bias_direction overstates/understates/balanced — the inflation
  pattern a CDD lead hunts for, separating a management that inflates
  from one that's merely imprecise;
- every component recoverable from the displayed rows (footnoted on
  the panel).
Surfaced as a banded score panel + flag-composition mini-bar +
direction chip above the KPI grid.
**Verify**: test_cim_credibility.py (9) — all-green→100/Corroborated,
deterministic deduction (red+yellow+unverifiable = 56), overstatement
pattern detected with the bias sign, understatement banded
conservative not Overstated, all-unverifiable→Unsubstantiated, empty
result, score floored at 0, to_dict round-trip, renders in page.
76 passed across CIM suites.

## W2-138 (2026-06-11) — Bear case: cross-source corroboration analysis (wave #40)
**Found**: /diligence/bear-case ranked evidence by severity and
grouped it by theme, but never answered the defensibility question a
CDD lead asks before putting a risk in the memo — "is this theme
corroborated by INDEPENDENT analyses, or is one model carrying it?"
**Added (analysis, verifiable)**: `analyze_corroboration(report)` in
the bear_case package → a `CorroborationReport`:
- per theme, counts DISTINCT source engines (not evidence items, so
  two findings from the same engine don't double-count) → `corroborated`
  when ≥2 independent sources agree;
- ranks themes by independent-source count then worst severity so the
  most defensible theme leads; names the strongest corroborated theme;
- a defensibility note distinguishing memo-ready (corroborated) from
  single-source (seek a second confirmation) — and an honest
  "every theme rests on one engine" verdict when nothing corroborates;
- pure function of report.evidence; every count recomputes from the
  cards on the page.
Surfaced as a corroboration panel between the severity matrix and the
per-theme evidence cards, in both bear-case render paths.
**Verify**: test_bear_case_corroboration.py (7) — distinct-sources
(not items) so same-engine doesn't corroborate, 2 independent
sources do, strongest theme leads + is corroborated, all-single-source
verdict, empty report, to_dict round-trip, renders in page.
84 passed across bear-case suites.

## W2-139 (2026-06-11) — Cliff calendar: payer-channel exposure (wave #41)
**Found**: /diligence/cliff-calendar plotted the cliff lollipops and a
total in-hold bps, but the first CDD question on a reimbursement-
exposed deal — "which payer channel is the headwind concentrated in,
and how does it accumulate?" — was left unanswered.
**Added (analysis, verifiable)**: `analyze_cliff_exposure(report)` in
the cliff module → a `CliffExposure`:
- groups the in-hold cuts by payer channel (medicare/medicaid/
  commercial/340b), totaling bps + event count + worst single event
  per payer, most-cut channel first;
- builds the cumulative erosion curve (running bps by relative hold
  year) — the final value equals the calendar's total_bps_in_hold, so
  it's self-checking;
- dominant_payer + dominant_share answer concentration: ≥70% in one
  channel → "single-channel reimbursement story, underwrite it
  specifically" vs. a diversified-headwind note;
- stays in basis points — NO revenue base assumed, so nothing is
  fabricated. Pure function of report.hits; every figure recomputes
  from the timeline events above it.
Surfaced as a payer-bar panel + cumulative-curve line + dominant-share
chip between the lollipop timeline and the full calendar table.
**Verify**: test_cliff_exposure.py (8) — payer totals sum to the
calendar total, most-cut-first sort, cumulative curve's last value =
total + monotonic years, single-channel concentration detected,
worst-event = most-negative per payer, no-hits empty, to_dict
round-trip, renders in page. 19 passed across cliff suites.

## W2-140 (2026-06-11) — Bankruptcy survivor: named-case replay analysis (wave #42)
**Found**: /screening/bankruptcy-survivor fired structural patterns and
gave a verdict + chip strip, but never made the CDD-defining point —
the fired patterns aren't abstract risk scores, they are matches to
real public-record healthcare bankruptcies (Steward, Envision, Cano,
Wellpath...).
**Added (analysis, verifiable)**: `analyze_distress_fingerprint(scan)`
in the screening module → a `DistressFingerprint`:
- ranks the fired patterns by severity weight (CRITICAL 4 → LOW 1) so
  the verdict's drivers order by how hard each precedent bit;
- de-dupes by named case (a fingerprint matching Steward twice counts
  Steward once) → distinct_cases;
- headline reframes the verdict: "this deal's structure replays N
  named bankruptcies (…) — falsifiable precedents, not a risk score",
  with an honest "fired without a named precedent" path and a clean
  "replays nothing" path;
- pure function of scan.checks; every figure recomputes from the
  fired pattern checks.
Surfaced as a named-case replay panel (severity-ranked, case-cited)
above the pattern-checks table.
**Verify**: test_distress_fingerprint.py (7) — clean deal replays
nothing, replays only fired checks, severity-weight rank order,
distinct-case dedupe + weighted-severity sum, to_dict round-trip,
renders in page, clean page shows the no-replay note. 116 passed
across screening suites.

## W2-141 (2026-06-11) — Thesis pipeline: coverage / completeness read (wave #43)
**Found**: /diligence/thesis-pipeline ran ~20 analytic modules and
logged per-step timing, but never told the partner how COMPLETE the
synthesized thesis is — a step that short-circuits (no data for the
fixture, or an error) silently drops its risk, and an unassessed risk
reads identically to a cleared one.
**Added (analysis, verifiable)**: `analyze_pipeline_coverage(report)`
in the orchestrator → a `PipelineCoverage`:
- steps_ok / steps_failed / coverage_pct from the step_log;
- headline_populated/total — how many derived numbers actually landed
  (a step can succeed but yield a None headline on thin data);
- confidence band FULL (≥90% ok, no failures) / PARTIAL / THIN (<60%);
- failed_steps list with errors → surfaced as "DID NOT RUN (risks
  unassessed)" so a short-circuited module isn't mistaken for a clean
  result;
- pure function of report.step_log + to_dict headline block.
Surfaced as a confidence-banded coverage banner (progress bar +
unassessed-step chips) at the top of the step-log block.
**Verify**: test_pipeline_coverage.py (8) — empty→THIN, all-ok→FULL,
partial lists failed steps as unassessed, <60%→THIN, coverage
arithmetic (8/9), real pipeline run (ok+failed=total, headline bound),
to_dict round-trip, renders in page. 28 passed across pipeline suites.

## W2-142 (2026-06-11) — Comparable outcomes: comp-set defensibility (wave #44)
**Found**: /diligence/comparable-outcomes showed the realized-MOIC
distribution and a match-scored comp table, but never answered the
question a partner must settle before citing "comps say 2.5x" to IC —
HOW DEFENSIBLE is this comp set as an anchor? A tight set of close
matches is quotable; a thin set of loose matches with scattered
outcomes is indicative at best.
**Added (analysis, verifiable)**: `assess_comp_set(result)` in the
comparable_outcomes module → set size, median match score, close-match
count (≥60), and MOIC dispersion ((p75−p25)/median); banded
STRONG / MODERATE / WEAK / THIN by the conjunction of set size ×
match closeness × outcome dispersion, with a one-line partner read.
Pure function of benchmark_deal's output; every figure recomputes
from the comparables + distribution the page already shows.
(Caught a latent bug en route: _percentile takes a 0–1 fraction, not
0–100 — fixed my call.)
Surfaced as a banded defensibility strip directly under the outcome
strip, in both the normal and print-preview layouts.
**Verify**: test_comp_set_defensibility.py (8) — thin→THIN,
close+tight→STRONG, loose+scattered→WEAK, moderate middle, true-median
match + close count, empty→THIN, missing-MOIC no-crash, real
benchmark + page render. 183 passed across comparable suites.

## W2-143 (2026-06-11) — Market structure: buy-and-build roll-up runway (wave #45)
**Found**: /deal/<id>/market-structure computed HHI/CR3/CR5 + a
fragmentation verdict and (wave #12) a composition strip, but never
answered the buy-and-build question the verdict implies — how many
bolt-ons can the platform actually do before the DOJ concentration
presumption bites?
**Added (analysis, verifiable)**: `rollup_runway(shares, platform,
target_share)` in pe_intelligence/market_structure → a `RollupRunway`:
- simulates the platform (largest player, or a named one) absorbing
  the next-largest independents one at a time; at each step the merged
  share = sum of the two, others unchanged;
- per step: combined share, post-merger HHI, ΔHHI, and a DOJ-
  presumption flag = HHI_after>2500 AND ΔHHI>200 (2023 Merger
  Guidelines, published thresholds);
- reports acquisitions-to-target (default 30%), the presumption step,
  and the clean runway (bolt-ons before the presumption);
- pure arithmetic on the share map; fewer than two players → None.
Surfaced as a runway table panel (step · acquire · combined · HHI ·
ΔHHI · presumption flag) + a one-line read, after the shares panel.
**Verify**: test_rollup_runway.py (10) — single-player→None, platform
defaults to largest / honors a named one, absorbs largest-first +
monotonic combined share, presumption flag matches the DOJ rule
exactly + first-crossing step, combined-share arithmetic (0.30+0.50=
0.80), reaches-target, fragmented long runway, to_dict round-trip,
renders in page. 17 passed across market-structure suites.

## W2-144 (2026-06-11) — Investability: composite drag decomposition (wave #46)
**Found**: /deal/<id>/investability showed the 0–100 composite, a
grade, and three sub-score bars, but never decomposed WHICH axis
drags the score — the partner saw "62/100, value 0.40" but had to do
the weight math to know value was the binding constraint and what
fixing it would buy.
**Added (analysis, verifiable)**: `analyze_score_drivers(result)` in
investability_scorer + an `AXIS_WEIGHTS` constant now used by BOTH the
composite and its decomposition (so they can't disagree) → a
`ScoreDrivers`:
- per axis: weight, score, points_contributed (w·score·100),
  points_lost (w·(1−score)·100);
- binding_axis = the one losing the most points; total_points_lost;
  uplift_if_binding_fixed = composite points gained if the binding
  axis rose to the deal's strongest axis (a concrete lever);
- honest "near-maxed, no material drag" path when total lost < 5;
- pure function of the three sub-scores + published weights.
Surfaced as a decomposition block (contributed/lost bars per axis +
binding flag + lever note) under the sub-score bars.
**Verify**: test_investability_drivers.py (8) — contributions sum to
the composite, binding axis loses most + sorts first, points-lost/
contributed formulas, uplift = weighted gap-to-best (20), near-max no
drag, to_dict round-trip, weights sum to 1.0, renders in block.
29 passed across investability suites.

## W2-145 (2026-06-11) — Texas infusion market: full CDD diligence page (wave #47)
**Built** a dedicated, thorough Texas infusion-therapy market sizing +
diligence page (`/diligence/texas-infusion` + JSON API) — the generic
per-state facility-count dives can't produce it (no vendored CMS
infusion census), so it's built the honest way: national NHIA/MedPAC
demand scaled to TX by REAL Census population share, then layered with
every dimension an infusion-platform CDD turns on.
- **Sizing** — TX patient base (US 3.2M × TX pop share 8.97%) ×18
  infusions ×$650 → TAM $3.36B / SAM $1.95B / SOM $97M, run through
  the SAME verified `compute()`/`sensitivity()` the TAM/SAM builder
  uses (funnel + 8.0% composite CAGR + tornado).
- **Therapy-form segmentation** — biologics/IVIG 40%, oncology 25%,
  OPAT 20%, TPN 10%, neuro 5% — with growth divergence (neuro ★ +12%).
- **Site-of-care segmentation** — home 38% (+9%), AIS 22% (+11%),
  HOPD 30% (−3%, the steered-away/health-system-captive share),
  office 10%; 5-yr TAM per site exposes the HOPD→home/AIS migration.
- **Provider landscape** — TX home-infusion locations (~72) + AIS
  (~143) derived from NHIA national anchors × pop share (labeled
  estimates); health-system (HOPD) captive capacity surfaced as
  whitespace, not competition.
- **Concentration** — named-chain HHI = 517 (DOJ/FTC scale) →
  fragmented/roll-up; Option Care ~20%, independent pool ~59%.
- **Metro attractiveness ranking** — Houston / DFW / Austin / San
  Antonio from REAL CBSA ACS aggregates: population, 65+ seniors,
  apportioned infusion patients, referral density /100k, est AIS
  count, and a 0–100 attractiveness score (senior demand log-scaled
  + growth + rural-route penalty), RANKED. Houston #1 (92.1).
- **Payer mix** — commercial 45% / Medicare Part B+D 35% / Medicaid
  12% (TX non-expansion) / self-pay 8% (TX ~20% uninsured drag).
- **Population growth** — TX +562,941 in 2024 (largest US gain,
  Census Vintage 2024), 65+ growing ~3.5%/yr — verifiable.
- **Structural factors** — CON-free entry, metro density, uninsured/
  non-expansion drag, biosimilar + nurse-capacity headwinds.
Every magnitude is a named source; the scaling, HHI, and metro ranking
are pure arithmetic on those constants + real ACS data, so they
recompute and audit. Wired into nav, cmd-K palette, and the assistant
route catalogue.
**Verify**: tests/test_texas_infusion.py (17) — population-scaled TAM
chain, SAM/SOM nesting, segments sum to 1 + fastest, HOPD declines,
payer sums to 1, chains sum to 1, HHI = sum of squared named shares +
fragmented, provider counts pop-scaled, 4 metros ranked 1–4 by
attractiveness with real senior counts, growth present, page renders
all sections, palette route registered. Guide-context contract fixed
(route added to the assistant catalogue). 318 passed across
palette/nav/tam-sam/guide suites.

## W2-146 (2026-06-11) — Texas infusion: in-depth per-city deep-dives (wave #48)
**Extended** the Texas infusion page (W2-145) with an in-depth,
visualized deep-dive for each of the four metros — Houston, DFW,
Austin, San Antonio — answering the breakdown the user asked for, all
from REAL member-county ACS data + a documented age/utilization model:
- **Age-band demand ranking** — each metro split into 0–17 / 18–44 /
  45–64 / 65–74 / 75+ using the metro's REAL 65+ share (the two senior
  bands re-base to it; under-65 keeps national structure) × an
  infusion-utilization index (rises with age) → demand share, RANKED
  (45–64 leads at ~37%, then 18–44, 65–74, 75+, peds). SVG bars.
- **Suburb / member-county breakdown** — every metro's real CBSA
  member counties (the suburbs) from the crosswalk, each with
  population, 65+, apportioned infusion patients, estimated AIS count,
  and patients-per-AIS, RANKED by patient volume (Harris #1 Houston,
  Dallas #1 DFW, Travis #1 Austin). County patients reconstruct the
  metro total within ±15%. SVG bars.
- **Big operators, linked** — known national chains present per metro
  (Option Care, Coram, Optum, Soleo, KabaFusion, Paragon) rendered as
  clickable external links to each company's locator (illustrative
  presence, labeled).
- **Early / white-space suburbs** — counties with real demand but the
  thinnest local AIS capacity (highest patients-per-AIS, or zero local
  AIS = fully unserved) — the de-novo targets.
- **Specialty tilt per city** — Houston oncology (MD Anderson/TMC),
  DFW commercial-balanced, Austin autoimmune/neuro (youngest), San
  Antonio oncology + diabetes (older, military/Hispanic).
Aggregated into one scannable card per city with two-up ranked SVG
charts. Pure functions of real ACS county data + the documented model.
**Verify**: +10 tests in test_texas_infusion.py (27 total) — four
deepdives, senior bands re-base to real 65+ share, age + demand shares
sum to 1, age bands ranked, suburbs are real member counties ranked
(Harris/Dallas present), county patients reconstruct the metro ±15%,
operators present + http-linked, specialty tilt per city, white-space
has real demand, page renders all city sections + ≥8 SVG charts +
operator links. 27 passed.

## W2-147 (2026-06-11) — Texas infusion: AIC + home-infusion channel focus, players, risks, RCM playbook (wave #49)
**Refocused** the Texas infusion page on the two PE-relevant channels —
Ambulatory Infusion Centers (AIC) and home infusion — and added the
operator/risk/RCM depth the user asked for:
- **Two-channel breakdown** — AIC vs home infusion side-by-side on
  reimbursement basis (buy-and-bill ASP+6/sequestered ASP+4.3, the
  Medicare HIT nurse-visit-only flaw, Part B/D/commercial split),
  margin model, working capital, and the channel-defining risk
  (white-bagging for AIC; HIT underpayment for home).
- **Players table** — 10 named operators (Option Care, IVX Health
  [pure-play AIC roll-up], CVS/Coram, Optum, Paragon, Soleo,
  KabaFusion, Amber, InfuCare, Vital Care) with channel, ownership
  (public / PE / payer-owned / franchise), TX presence, scale, and
  external links; payer-owned steerage threats flagged.
- **Risk register** — 8 channel-tagged risks across Reimbursement /
  RCM / Market / Ops, each with severity, who it hits (AIC/Home/Both),
  and — the differentiator — the **RCM read**: how revenue-cycle
  diligence detects and measures it (white-bag % + margin/infusion;
  Medicare home-infusion net collection + unbillable days; denial
  DOLLARS not rate; units/JW capture; payer concentration; cash
  conversion).
- **RCM playbook** — why infusion RCM is different (high $/claim,
  buy-and-bill working capital, auth-gated, multi-payer split), the
  infusion KPI set (IDR, denial DOLLAR exposure, clean-claim, DAR/DSO,
  net collection, cost-to-collect), top denial drivers, and the RCM
  diligence question set — aligned to the platform's RCM vocabulary.
Sections placed prominently after the sizing chain; provider scale +
presence labeled directional (public-filing-based).
**Verify**: +4 test classes (31 total) — both channels with all
economics fields, players have channel/ownership/http-link with the
marquee AIC+home names + payer-owned flags, risk register tags
severity/channel/RCM-angle with the two HIGH channel risks present,
RCM playbook carries the denial-DOLLAR + AR KPIs and ≥4 denial drivers
/ questions, page renders all four sections. 31 passed; guide-context
contract green.

## W2-148 (2026-06-11) — Texas infusion: AIC unit economics, drug supply, illness-by-suburb, north suburbs (wave #50)
Deep AIC build on the Texas infusion page — all REAL/sourced data, no
synthetic:
- **AIC unit economics** — `aic_chair_economics()`: per-chair P&L
  waterfall (gross rev → drug COGS → nursing → overhead → RCM →
  contribution; $1.02M rev → $216K/21% contribution at benchmark) with
  a "breakdown by section" SVG, plus the operating-lever KPI cards the
  user named (chair utilization, nurse productivity [infusions/nurse/
  yr], recurring-patient %, commercial mix, prior-auth approval rate,
  buy-and-bill drug margin, rev & contribution per chair). Pure
  function of editable assumptions (NHIA/ambulatory benchmarks).
- **Drug supply & inventory** — `infusion_drug_supply()` reads the
  VENDORED openFDA shortage snapshot (1,156 current US shortages,
  2026-05-25): specialty biologics (IVIG/infliximab/rituximab/
  vedolizumab) = STABLE / not FDA-listed (the AIC margin engine has
  clean supply); OPAT anti-infectives + IV iron = WATCH; TPN/fluids
  (dextrose/amino-acid/saline) = CURRENT SHORTAGE (74). Status chips +
  link to the existing /drug-shortage tracker. No synthetic data.
- **Illness aggregation by suburb** — `county_illness_burden()`:
  estimated infusion-relevant patients = REAL county population × the
  TX state prevalence rate (CDC/CMS public data) for RA→immunology
  biologics, Cancer→oncology infusion, CKD→IV iron. Variation across
  suburbs comes from real population (labeled population-scaled, not
  invented county rates). Aggregated to each metro + mapped to
  most-common therapies + channel.
- **North-suburb coverage** — `_NORTH_SUBURBS`: Collin/Denton (DFW),
  Montgomery (Houston), Williamson (Austin), Comal/north Bexar (San
  Antonio) flagged with marquee cities; north counties get a ▲N marker
  in the per-city suburb chart + a callout. (Verified DFW north ring =
  Collin + Denton.)
14 SVG charts on the page; JSON API + guide contract green.
**Verify**: +14 tests (42 total in test_texas_infusion.py) — P&L
sections balance + sane contribution band, levers are pure functions
(util↑→contribution↑, white-bag drug-margin→0 cuts it), named KPIs
present, real FDA snapshot with biologics STABLE + TPN current
shortage, north suburbs flagged per metro (DFW=Collin+Denton), illness
burden scales with population + maps to therapies, county illness
population-scaled (×10 pop → ×10 patients). 42 passed.

## W2-149 (2026-06-11) — Texas infusion: editable AIC assumptions + sensitivity + break-even curve (wave #51)
More AIC depth with the "change the assumptions" capability:
- **Payer mix is now a REAL economic lever** — when admin fee / drug
  margin aren't explicitly overridden they BLEND from per-payer
  anchors (commercial $260 admin / 14% spread vs Medicare $155 /
  4.3% — MedPAC ASP+4.3 sequestered + PFS admin codes). Moving the
  commercial-mix input moves the P&L ($176K @40% → $252K @80%
  contribution/chair), not just a display chip. Explicit overrides
  still win (the white-bag drug-margin→0 shock path is preserved).
- **Editable assumptions** — a CHANGE-THE-ASSUMPTIONS form (9 inputs:
  chairs, utilization, infusions/chair/day, drug revenue, commercial
  mix, nurse ratio, nurse cost, overhead, RCM %) GETs back to the
  page; `aic_assumptions_from_qs` range-clamps every value server-side
  (999 chairs → 60; junk dropped), percent inputs human-readable;
  an EDITED badge shows when overrides are active; the JSON API honors
  the same qs overrides.
- **Sensitivity tornado** — `aic_sensitivity()` swings each of 7
  operating levers ±20% (clamped) and recomputes contribution/chair
  through the SAME model, sorted by impact (chair utilization and
  infusions/day dominate at ±$114K; commercial mix ±$47K). Tornado SVG.
- **Utilization → contribution curve with break-even** —
  `aic_utilization_curve()`: contribution across 40–95% utilization +
  a fine-scan break-even (≈19% at benchmark — fixed nursing/overhead
  vs per-infusion gross profit), drawn as a line SVG with the $0 line,
  break-even marker, and a "you are here" dot. The de-novo ramp read.
All pure recomputation through `aic_chair_economics` so the graphics
can never disagree with the model; 16 SVGs on the page.
**Verify**: +6 tests (48 total) — mix moves contribution + override
wins, qs clamps/drops junk, tornado base equals model + sorted +
throughput dominates, curve monotonic + break-even < default util,
overrides flow analysis→page (EDITED, value=90, higher contribution),
form + charts render by default with no EDITED badge. 48 passed;
guide + API contracts green.

## W2-150 (2026-06-11) — Texas infusion: competitive dynamics by owner, per-county capacity/saturation, growth scorecard (wave #52)
AIC competitive landscape + a long-term-opportunity scorecard, all
recomputed from real county population:
- **Competitive dynamics by ownership** — `_PROVIDER_SEGMENTS` splits
  the market into the five owner types the thesis competes with: national/
  regional chains (28%), health-system-owned (33%, captive HOPD pool —
  flagged non-hospital=False), physician-owned (15%), independent AIC
  (14%), independent home (10%). Shares sum to 1.0; the ~39% independent +
  physician pool is the fragmented roll-up target. Rendered as a 100%
  ownership strip + examples/roll-up-read table.
- **Per-county chair capacity & saturation** — `county_capacity()`
  estimates chairs (est AIS × 7), AIS-channel demand (total infusion
  visits × 22% site share), chair capacity (chairs × ~1,170 visits/yr),
  and a demand/capacity ratio scoped to the AIS channel (not total
  demand — that was a 4–5× bug). Bands: UNDERSUPPLIED / balanced /
  saturated / no-local-capacity, plus non-hospital site penetration and
  patients-per-chair. Apportions chairs across the ownership segments.
  Surfaced as a per-county table inside each city deep-dive.
- **Texas growth scorecard** — `county_opportunity_score()` blends
  demand · under-saturation · payer quality · growth into a 0–100 score;
  `texas_growth_scorecard()` ranks all 34 counties across the 4 metros,
  flags markets where demand is likely to exceed AIS capacity (ratio
  ≥1.10, or a balanced corridor where site-of-care migration 22%→30% +
  population growth tip it over). 6 undersupplied growth markets surface
  — Williamson, Collin, Denton, Montgomery, Hays, Comal (the north /
  Austin corridors). Top-10 ranked bars + an undersupplied-markets table.
All pure recomputation from real county population × labeled assumptions;
ownership shares are national NHIA/industry estimates, flagged
illustrative (replace with NPPES / state pharmacy-board pull in
diligence).
**Verify**: +6 tests (54 total) — segments cover the 5 owner types +
sum to 1.0 + health-system captive; capacity ratio scoped to AIS
channel (<3×, ais_demand < total); saturation bands mixed; scorecard
ranks descending + undersupplied flagged; growth corridors surface;
opportunity score bounded 0–100. Plus 6 new page-render needles. 54
passed; guide + JSON-API contracts green.

## W2-151 (2026-06-11) — Texas infusion: CDC PLACES + ACS public-health demand proxies (wave #53)
Wired real CDC / Census public-health data into the Texas AIC breakdown
so infusion demand is proxied by verifiable prevalence, by county:
- **Live CDC PLACES county API** (`cdc_places_api.py`) — Socrata client
  (dataset i46a-9kgh, the same release the vendored aggregate was built
  from) pulling full-population county crude prevalence for arthritis,
  kidney (CKD), cancer, diabetes, obesity, poor physical/general health,
  uninsured, and routine checkup. Paginated, disk-cached, and **fails
  closed** — any network error returns empty so callers fall back to the
  real vendored TX state rate; nothing is fabricated.
- **Census ACS sex client** (`acs_sex.py`) — county female share from ACS
  5-yr table B01001 (live API + cache), with a published TX statewide
  fallback. Used to weight the IV-iron / anemia pool toward women.
- **Therapy-proxy mapping** (the user's spec): rheumatology→arthritis,
  oncology→cancer, IV iron→CKD + poor health + female share, general
  chronic→diabetes + obesity + poor physical health, payer access→
  uninsured + poverty + routine checkup. `texas_cdc_proxies()` /
  `texas_cdc_state_rates()` assemble the real state rates (CDC PLACES
  full-pop where vendored; CMS Medicare arthritis/cancer/CKD TX-adjusted
  otherwise), and the live county API overrides them with real pop-
  weighted county rates when egress is available.
- **Denominator-honest county counts** — `county_cdc_demand()` applies
  each rate to its OWN denominator: full-population PLACES rates → all
  adults; Medicare-beneficiary rates → the 65+ pool (fixes an inflated
  IV-iron count). Per-county estimates recompute from real population ×
  proxy rate; the live county rate overrides the state fallback when
  present. `county_payer_access()` gives a 0–100 commercial-access index
  from real ACS uninsured + child poverty + PLACES routine-checkup.
- **Page**: a "CDC public-health demand proxies" section (therapy →
  proxy measure → TX rate → denominator → source, with a LIVE/OFFLINE
  API badge) + a per-city CDC-proxied therapy-demand bar block with the
  county payer-access read.
Egress is blocked in CI/sandbox (self-signed-cert proxy), so the page
ships on the real vendored/CMS fallback and lights up the live county
rates automatically wherever network egress is permitted.
**Verify**: +9 proxy/integration tests (63 in test_texas_infusion) +
new `test_cdc_places_api.py` (7) — proxies cover the named therapies,
state rates equal real vendored PLACES values, offline falls back (not
live) and the API fails closed, county counts use the correct
denominator, IV-iron scales with female share, live rate overrides
state, payer-access bounded 0–100, metro totals = sum of counties,
analysis JSON-serializable; API parsing from mocked payloads. Full
suite green.

## W2-152 (2026-06-11) — Texas infusion: deep, authentic home-infusion analysis (wave #54)
Made the home-infusion side of the Texas page far deeper and fully
sourced — therapy/condition epidemiology, the network landscape, the
Medicare HIT reimbursement gap, and episode economics:
- **Therapy × condition reference** (`home_infusion_therapy_reference`):
  six home-infusion families — anti-infectives/OPAT, immune globulin
  (IVIG/SCIG), parenteral nutrition (HPN/TPN), inotropic therapy
  (advanced HF), home biologics, and enzyme-replacement/factor/PAH —
  each with the conditions served, regimen, reimbursement basis, the
  home-vs-AIC rationale, and margin character.
- **Real epidemiology, real population** (`home_infusion_conditions`):
  per-therapy eligible-patient estimates = published treated-prevalence
  / incidence anchor (per 100k — IDSA OPAT ≈0.9/1,000, IDF PI + CIDP for
  IG, ASPEN ≈120/M for HPN, NHF/rare-disease registries) × real metro
  population (inotropes denominated on the senior pool). ~27k OPAT, ~14k
  IG, ~3.6k TPN eligible/yr statewide. Counts vary by real geography,
  not invented rates.
- **The networks** (`home_infusion_networks`): 11 operators across
  tiers — national platforms (Option Care, CVS Coram, Amerita/
  BrightSpring), payer-owned steerage threats (Optum, Paragon/Elevance —
  TX-HQ'd Plano), IG/rare specialists (KabaFusion, NuFACTOR/FFF,
  BioMatrix, Soleo, InfuCare Rx), and the franchise/independent roll-up
  pool (Vital Care). Ownership, therapy focus, ACHC/URAC accreditation,
  TX footprint.
- **Reimbursement** (`home_infusion_reimbursement`): the 21st Century
  Cures Act HIT services benefit (2021), the calendar-day gap (paid only
  on nurse-visit days), the G0068–G0070 categories, the Part B DME drug/
  pump split, the Part D black hole (no professional benefit), and why
  commercial per-diem carries the channel — with the RCM read.
- **Episode economics** (`home_infusion_episode_economics`): an
  illustrative 4-week commercial OPAT P&L (~$4.7K revenue / ~$3.9K
  contribution / ~41% margin) recomputed from labeled per-diem + drug-
  spread + nurse-visit + compounding + delivery anchors; nurse route
  density called out as the margin lever.
- **Page**: a dedicated "Home infusion — therapies, networks &
  reimbursement" section (therapy table + episode-P&L card, network
  roster, HIT-gap explainer) and a per-metro home-infusion-eligible
  demand bar block in each city deep-dive.
**Verify**: +7 home-infusion tests (70 in test_texas_infusion) — counts
scale linearly with population, inotropes use the senior denominator,
networks cover all tiers + Paragon TX flag, reimbursement surfaces the
calendar-day gap + Part D split, episode contribution recomputes
(rev−cost, 0<margin<1), therapy reference complete (6 families), every
metro carries home demand; +6 page-render needles. Full suite green.

## W2-153 (2026-06-11) — Texas home infusion: discharge pipeline & therapy-volume risk (wave #55)
Home infusion is a REFERRAL business — added the discharge-flow and
risk-concentration diligence the channel turns on:
- **Annual referral FLOW by therapy** (`home_infusion_discharge_volumes`):
  new-starts/yr = published discharge / new-start incidence (per 100k —
  OPAT ≈0.9/1,000, HPN ≈5/100k, IG ≈7/100k, etc.) × real population
  (inotropes on seniors). ~27k OPAT, ~7.5k biologic, ~2.1k IG referrals/
  yr statewide. This is the demand FLOW captured each year — distinct
  from the standing prevalent pool — and it's smaller than the pool for
  chronic therapies (incidence vs prevalence), which the tests assert.
- **30-day readmission leakage** per therapy (OPAT ≈23%, HPN ≈18%, HF
  inotropes ≈25% — published cohort anchors): re-hospitalized patients
  stop billing, the leakage to underwrite.
- **Therapy-volume risk register** (`home_infusion_therapy_risk`): each
  therapy scored 1–5 on five diligence axes (reimbursement, payer
  steerage, referral concentration, clinical/readmission, drug supply),
  blended by documented weights into a 0–100 at-risk score and ranked.
  Rare-disease/factor/PAH (#1, reimbursement/AR) and IG + home biologics
  (steerage/white-bagging) surface as most-at-risk; OPAT/TPN/inotropes
  lead on referral concentration.
- **Referral-source concentration** (`home_infusion_referral_sources`):
  acute-hospital discharge planning ≈58% of referrals — and within a
  branch one health-system relationship can be 20–40% of volume, the #1
  commercial fragility — vs diversified specialty-clinic + direct-to-home
  ED OPAT, with the RCM read (map top-5 source concentration + net
  collection per referral + readmission leakage).
- **Page**: a "Home-infusion discharge pipeline & therapy risk" section
  (referral-flow table, the most-at-risk risk heatmap, referral-source
  concentration bars + read) and a per-metro referral-flow bar block in
  each city deep-dive.
**Verify**: +6 discharge/risk tests (76 in test_texas_infusion) — flow
scales with population + has source/readmit, flow < prevalent pool for
chronic therapies, risk score recomputes from axes×weights + ranks
descending, IG/biologic flag steerage=5 & OPAT referral-conc=5, referral
shares sum to 1.0 + hospital-dominant, every metro carries flow; +6
page-render needles. Full suite green.

## W2-154 (2026-06-11) — Texas infusion: CMS ASP Part B drug pricing + Medicare Advantage enrollment (wave #56)
Wired two more real CMS data sources into the Texas page — the buy-and-
bill drug-pricing basis and the MA site-of-care-steerage force:
- **CMS ASP Part B drug pricing** (`cms_asp_pricing.py`, new): the
  marquee infusion-drug HCPCS J-code reference (infliximab J1745,
  rituximab J9312, ocrelizumab J2350, IVIG J1569, vedolizumab, denosumab,
  bevacizumab, …) — the codes/descriptors are public CMS facts — plus
  the ASP+6 / sequestered-ASP+4.3 payment mechanics as pure functions,
  and a best-effort LIVE client (resolves the current ASP dataset from
  the CMS data.json catalog, fetches per-unit payment limits). Fails
  closed offline: NO dollar value is fabricated — the J-code reference +
  the formula show, and live $/unit fills in where egress permits. The
  payment limit minus the operator's GPO acquisition cost is the
  buy-and-bill spread.
- **Medicare Advantage enrollment** (`texas_ma_enrollment`): real
  vendored CMS MA geographic-variation data — 2.19M TX MA enrollees,
  24% dual-eligible, avg age 72 — with a penetration proxy (vs 65+ pop,
  labeled). MA is the key payer-mix force on infusion: plans steer site
  of care to AIC/home over HOPD and gate biologics with prior-auth +
  white-bagging (volume tailwind + drug-spread risk). County-level
  penetration available via the existing live `cms_ma_enrollment` client.
- **Page**: a "Part B drug pricing — ASP buy-and-bill" section (J-code
  table + ASP+6/sequester mechanics + LIVE/OFFLINE badge) and a Medicare
  Advantage panel in the payer-mix section (enrollment / penetration /
  dual / avg-age KPIs + steerage read).
**Verify**: +3 ASP/MA integration tests (test_texas_infusion) + new
`test_cms_asp_pricing.py` (5) — ASP formula exact (×1.043 seq / ×1.06
statutory), J-code reference is verifiable public codes, live fetch
fails closed + parses mocked payload, offline shows no fabricated
dollars, MA enrollment matches the real vendored file; +6 page-render
needles. Full suite green.

## W2-155 (2026-06-11) — Texas infusion: NPPES infusion-provider registry + map (wave #57)
Added the NPI-registry provider supply read + a Texas map:
- **NPPES infusion taxonomy + count client** (`nppes_infusion.py`, new):
  the real public NUCC taxonomy codes (261QI0500N Clinic/Center Infusion
  Therapy, 3336I0012X Infusion Pharmacy, 251F00000X Home Infusion) and a
  live count via the existing keyless NPPES API, taxonomy-filtered by
  metro. Fails closed (no fabricated count) and fails FAST (no retries) —
  it must never block a render.
- **Provider map** (`texas_infusion_provider_map`): the four metros with
  estimated infusion-center counts (sum of member-county AIS estimates
  from real population) + map coordinates; a live NPPES count replaces
  the estimate per metro when fetched. Live fetch is OPT-IN
  (`?nppes=live`) so a normal page render makes zero network calls
  (verified ~3.5s render).
- **Page**: an "Infusion-provider map" section — an SVG bubble map on a
  stylized Texas outline (bubbles sized by provider supply, all four
  metros verified inside the outline via point-in-polygon), a per-metro
  est-vs-NPPES count table, and the public taxonomy-code reference, with
  a LIVE/MODELED badge.
**Verify**: +4 provider-map tests (test_texas_infusion) + new
`test_nppes_infusion.py` (5) — map has 4 metros with real estimates
ranked, default build is offline (no network, counts None), taxonomies
are the real NUCC codes, live flag threads through + fails closed, count
client sums across taxonomies + flags capped + fails closed on empty
state / network error; +4 page-render needles. Full suite green.

## W2-156 (2026-06-11) — Texas infusion: per-section "SO WHAT" takeaways (wave #58)
Clarity pass — made the page scannable by giving every major section a
data-driven diligence takeaway, so a partner gets the implication, not
just the table:
- **`_so_what()` callout** + **`_so_whats(a)`** builder: 18 takeaways
  computed from REAL analysis values (so each recomputes from the data
  it summarizes) — e.g. sizing "$3.36B TAM growing 8.0%/yr, $1.95B
  addressable — underwrite the demand chain, not the headline";
  discharge "~27,027 OPAT referrals/yr but 58% through hospital
  discharge desks — referral concentration is the #1 risk"; AIC
  "~$218K contribution/chair, break-even near 19% utilization";
  concentration "HHI 517, top operator 20%, 59% independent pool —
  textbook roll-up runway"; payer "commercial 45% funds it, but 2.2M MA
  lives (~55%) steer site-of-care"; scorecard "6 north/Austin-corridor
  counties show demand outrunning AIS capacity".
- Inserted after sizing, channels, home infusion, discharge pipeline,
  players, competitive dynamics, CDC proxies, AIC economics, ASP
  pricing, site of care, provider landscape, provider map, metro
  ranking, growth scorecard, concentration, payer mix, demographics,
  and growth drivers — colored by severity (risk takeaways in negative
  tone).
**Verify**: +2 takeaway tests — builder produces ≥15 non-empty takeaways
carrying real values (HHI, OPAT flow), page renders ≥15 SO WHAT
callouts. Full suite green.

## W2-157 (2026-06-11) — Texas infusion: evolution of discharges → home infusion over time (wave #59)
Added the TIME dimension the discharge analysis was missing — how the
hospital-discharge → home-infusion / site-of-care shift has evolved:
- **`home_infusion_evolution()`**: a 2015→2024 year-by-year series of
  the infusion site-of-care mix (HOPD 46%→30%, home+AIS 38%→60%, a
  16-pt shift out of the hospital), the home/alternate-site market size
  ($11B→$20.5B, computed 7.2% CAGR), and an OPAT volume index (100→217).
  Pure recompute from labeled endpoints — the 2024 site mix is THIS
  page's live site-of-care model (so history connects to the present),
  the 2015 mix a documented historical estimate, market size from NHIA/
  industry magnitudes; intermediate years linearly interpolated, all
  flagged illustrative.
- **Event timeline** (factual): 21st Century Cures Act (2016), first
  infliximab biosimilar (2016), transitional HIT benefit (2019), COVID
  surge (2020), permanent HIT benefit (2021), white-bagging/steerage
  spread (2022), MA >50% (2023), biosimilar wave + IRA (2024).
- **Structural drivers**: LOS decline, payer steerage, MA growth,
  biosimilars/IRA, COVID normalization, the HIT benefit.
- **Page**: a "How discharges → home infusion have evolved" section — a
  stacked-area site-of-care chart (HOPD shrinking, home/AIS growing), a
  KPI strip (HOPD shift / home+AIS gain / market CAGR / OPAT index), the
  event timeline, and the drivers, plus a data-driven SO WHAT.
**Verify**: +5 evolution tests — shares sum to 1.0/yr, HOPD declines &
non-hospital rises monotonically, market compounds at the computed CAGR,
the 2024 endpoint equals the page's live site-of-care model, the event
timeline is real & ordered (Cures Act/COVID/HIT/biosimilar); +4 render
needles + 1 SO WHAT. Full suite green.

## W2-158 (2026-06-11) — Texas infusion: J-code place-of-service by state (CMS by-Geography-and-Service) + map (wave #60)
Answered the "aggregate POS for J-codes by state over 3 years" question
by building it:
- **`cms_geo_service.py`** (new live client): the CMS "Medicare Physician
  & Other Practitioners — by Geography and Service" PUF — J-code × state
  × place-of-service (facility/non-facility) × year. Resolves the per-
  year dataset UUID from the CMS data.json catalog, pulls state rows for
  the infusion J-code basket, aggregates facility vs non-facility
  services + computes the non-facility %. Fails closed (no fabricated
  claims) offline.
- **`infusion_jcode_pos(fetch_live, years)`**: per-state non-facility
  share for the infusion J-code basket. Live = real CMS Part B FFS
  claims; offline = MODELED from a national anchor adjusted by REAL state
  rurality (more rural → more facility) + MA penetration (more MA → more
  non-facility steerage), clamped + labeled — never claims. All 51
  states ranked; TX detail; national 3-yr facility→non-facility trend.
- **Page**: a "J-code place of service by state" section — a schematic
  US tile-grid choropleth (non-facility share, TX outlined, all 51 tiles
  collision-checked), a top/Texas/bottom percentage table (non-facility %
  / rural / MA-pen / live-vs-modeled), the national facility→non-facility
  trend table, and the Texas read (~61% non-facility, #12 of 51), with a
  LIVE/MODELED badge + SO WHAT. Honest caveats surfaced: FFS-only
  (excludes MA), <11 suppression, binary POS (granular needs paid PSPS).
**Verify**: +6 jcode-POS tests (test_texas_infusion) + new
`test_cms_geo_service.py` (4) — all 51 states ranked, offline is modeled
(not claims, 0.35–0.82), modeled share responds to real rurality/MA
(VT<FL), TX present, J-code basket + 3-yr trend rises, live flag fails
closed; client parses mocked Socrata payload + aggregates non-facility %
+ fails closed unresolved; +5 render needles + 1 SO WHAT. Full suite green.

## W2-159 (2026-06-11) — Texas infusion: regulatory & reimbursement environment (wave #61)
Added a comprehensive, structured regulatory + reimbursement environment
section — every material federal/state rule an infusion platform lives
under, tagged tailwind/headwind/neutral with the diligence implication:
- **`regulatory_reimbursement_environment()`**: 6 categories / 23 items —
  Medicare Part B (ASP+6→sequester ~4.3%, admin CPT 96365–96379, 2%
  sequester); the HIT benefit (Cures Act → permanent 2021, the calendar-
  day gap, G0068–G0070, DME/prosthetic, the Part D black hole); IRA &
  drug pricing (Part B inflation rebates, Maximum Fair Price negotiation
  2026→2028, biosimilar ASP+8% bump, 340B); site-of-care & UM (site-
  neutral, white-bagging, prior auth, the 2024 MA prior-auth rule); Texas
  & state (no CON, TSBP pharmacy licensure, Medicaid non-expansion +
  STAR, state white-bagging patchwork flagged VERIFY); operational
  compliance (USP <797>/<800>, ACHC/URAC/JC accreditation, DSCSA, FDA
  shortages). 5 tailwinds / 11 headwinds / 7 neutral + a net read:
  policy pushes VOLUME to the platform's site but squeezes the DRUG
  SPREAD — underwrite on service margin + commercial mix + de-novo
  runway, not the drug.
- **Page**: a "Regulatory & reimbursement environment" section — a
  tailwind/headwind/neutral count strip, the NET READ banner, and each
  category's items with an impact tag (▲/▼/●), status, and the diligence
  implication; plus a data-driven SO WHAT.
**Verify**: +4 regulatory tests — ≥6 categories covering Part B/HIT/IRA/
site-of-care/Texas/compliance with complete fields + valid impact tags,
impact counts match the items, the real marquee topics present (ASP+6,
calendar-day, MFP, biosimilar, 340B, site-neutral, white-bagging, CON,
USP), Texas no-CON tagged tailwind; +5 render needles + 1 SO WHAT. Full
suite green.

## W2-160 (2026-06-11) — Excel Mapping: configurable US-state choropleth page (wave #62)
New standalone utility page at /excel-mapping — a generic state map you
drive from a {state: percentage} dict or an Excel paste:
- **`gradient_color(value, lo, mid, hi, c_low, c_mid, c_high)`**: a
  3-stop gradient — low→c_low, mid→c_mid, high→c_high, linearly
  interpolated each side of the midpoint; None → neutral grey; clamps
  out-of-range; degenerate domain → mid colour.
- **`parse_values_text`**: parses pasted Excel rows ("TX 61" / "TX,61" /
  "TX\t61" / "Texas 61", trailing % ok), resolving 2-letter codes or
  full state names; skips bad rows.
- **Two ways to drive it**: edit `DEFAULT_STATE_VALUES` + the three
  `DEFAULT_*_COLOR` constants in Python, OR use the page form (3 colour
  pickers, optional low/mid/high value domain — blank = auto from data,
  and an Excel-paste textarea). qs overrides the Python defaults.
- **Render**: a 51-tile schematic US grid (collision-checked) coloured by
  the gradient, each state labelled in BLACK SERIF text (with a thin
  white halo for legibility on dark tiles), a low→mid→high legend, a
  sorted value table, and a "how to use" panel. Serif UI font throughout.
- **Wiring**: GET route in server.py; Research sub-nav + Cmd-K palette +
  _SUB_SECTION_MAP entries; a ToolRouteDefinition so the Guide has page
  context (no guide-blind page). Default values are clearly labelled
  EXAMPLE placeholders — overwrite with your own; nothing is a data claim.
**Verify**: new `test_excel_mapping.py` (14) — gradient hits all three
stops + interpolates each side + clamps + None-grey + degenerate-domain,
Excel-paste parser (codes/names/separators/%, skips bad), qs overrides
colours+domain+data, default dict references only real states, page
renders core elements + custom values appear, registered in palette/nav,
route has guide context. Wiring suite (guide-context/palette/tools-index/
nav/us_map/routes) 522 passed. Full suite green.

## W2-161 (2026-06-12) — Chart Builder: the CDD/Excel chart kit (wave #63)
A standalone consultant-grade chart builder — the graphs a CDD deck
needs, rendered Chartis-styled from a pasted table:
- **`cdd_chart_kit.py`** (new): `render_cdd_chart(type, table, opts)` over
  13 chart types — column (grouped), stacked column, 100% stacked column,
  horizontal bar, line, stacked area, waterfall (bridge), pie, donut,
  scatter, bubble, marimekko, combo (bars + line). One shared frame
  (centered serif title, gridlines, value labels, centered legend) so
  every chart matches the deck. 4 named Chartis palettes (Chartis,
  Navy–Teal, Sequential teal, Diverging). `parse_table()` reads an Excel
  paste (tab / comma / 2+-space; %/$ /thousands-commas stripped; headers
  = category + series names). Waterfall reads a delta column with a
  "total/net/=" row drawn as an absolute bar; scatter/bubble read X/Y/
  [size]; pie/donut/marimekko read the first value column(s).
- **`chart_builder_page.py`** (new, route `/chart-builder`): chart-type
  chips, a data textarea (paste from Excel), title/subtitle/palette/unit
  inputs + show-values/legend toggles, the rendered chart centered, and
  a GALLERY strip rendering your data across every chart type (click a
  thumbnail to switch). Fully qs-driven (a configured chart is a
  shareable URL). Wired into Research nav + Cmd-K palette + guide context.
**Verify**: new `test_chart_builder.py` (13) — table parser (tab/comma/
units/None), column-major series, every chart type renders clean SVG
(no None/NaN leak), centered title, empty→placeholder, waterfall total
convention, palettes valid; builder page renders + type-switch + custom
data + palette/nav/guide registration. Full suite green.

## W2-162 (2026-06-12) — Pie Chart: client-ready pie/donut from per-slice input (wave #64)
A simpler, more direct chart maker per the request "just type a percent
value and colour and get an easy pie — good static charts ready for
clients":
- **`presentable_pie(slices, opts)`** (in cdd_chart_kit): a presentation-
  grade pie/donut from explicit ``{label, value, color}`` slices — per-
  slice colours, on-slice percentage labels (with a soft halo), and a
  clean label · value · % legend; serif centered title, white slice
  separators, optional donut with a TOTAL in the hole. Built for a slide,
  not a dashboard.
- **`pie_chart_page.py`** (route `/pie-chart`): the simple input the user
  asked for — up to 10 slice rows, each just Label · Value · Colour
  (HTML colour picker pre-set to the Chartis sequence), plus title /
  subtitle / label-mode (percent / value / both / none) / unit / donut
  toggle. Blank rows drop out; values can be percent or absolute (shares
  computed). qs-driven (l{i}/v{i}/c{i}) so a chart is a shareable URL.
  Wired into Research nav + Cmd-K palette + a documented guide context.
**Verify**: new `test_pie_chart.py` (10) — renderer produces clean SVG
(no None) with title + per-slice colours + computed-share legend, zero/
blank slices dropped, empty→prompt, donut hole + TOTAL; page populated by
default + custom slices render (45/(45+35)=56%) + defaults-then-qs collect
+ palette/nav/guide registration. Full suite green.

## W2-163 (2026-06-12) — Charts: 6 new types, easy export, adjustable size (wave #65)
Per the request "more charts, super easy exports, adjustable by size":
- **6 new chart types** (kit now 19): funnel (TAM/SAM/SOM with conversion
  %), tornado (sensitivity, diverging sorted bars), radar/spider (multi-
  attribute), 2×2 matrix (positioning with quadrant lines + axis titles),
  bullet (actual vs target tick), dot/lollipop (ranking). All in
  CHART_TYPES + dispatch, so they appear automatically in the Chart
  Builder chips + gallery with example data.
- **Easy export** (`chart_export_toolbar`): Download SVG, Download PNG
  (2× canvas), and Copy SVG — pure vanilla JS, no deps. Added under the
  chart on the Chart Builder, Pie Chart, AND Excel Mapping pages.
- **Adjustable size** (`_svg_open` + `SIZE_PRESETS` S/M/L/XL → 520/720/
  920/1120px): every chart's SVG now scales by `width_px` with height
  auto from the viewBox (never distorts). A Size selector on the Chart
  Builder + Pie Chart pages.
**Verify**: +9 tests (test_chart_builder/test_pie_chart) — 6 new types
present (≥19 total) + render clean, width_px controls display size +
height auto, export toolbar has SVG/PNG/Copy + ids, size presets S/M/L/XL,
builder/pie pages show export buttons + size select + new-type chips.
Full suite green.

## W2-164 (2026-06-12) — Expert-Call Program: the CDD voice-of-customer workstream (wave #66)
New CDD task covered — the primary-research call program every commercial
due diligence runs and the platform had no surface for (the CIM
Cross-Check generates suggested expert-call questions with nowhere to
take them):
- **`diligence/expert_calls.py`** (new, UI-free): 7 stakeholder lenses
  (referring physician, payer/contracting exec, competitor exec, former
  employee, site-of-care administrator, patient/caregiver voice,
  industry/reimbursement expert), each with who/why/sourcing AND the
  lens's known systematic bias stated (every source lies in a
  predictable direction — the guide says which). Curated QUESTION_BANK
  (38 questions) tagged to 7 CDD topics, each with a "listen for" line
  (what a strong vs concerning answer sounds like). `build_call_guide`
  (compliance-safe opening — no MNPI / NDA / current-employer rules
  stated out loud — topic-ordered questions, closing asks incl. the
  structured SUPPORTS/CONTRADICTS note); `program_plan` (largest-
  remainder apportionment, sums exactly, no zero-call lens in a
  full-size program); `coverage_read` (STRICT: ≥2 calls COVERED, 1
  THIN single-source, 0 UNCOVERED blind spot — the read names the worst
  lens, never a percent-done average).
- **Page `/diligence/expert-calls`**: program-size + deal-stamp form,
  call-mix table (lens / what only they can tell you / calls / mix /
  known bias), coverage tracker (done-counts → status chips + honest
  findings), lens chips → the full printable call guide; CIM
  Cross-Check tie-in. All GET — tracker state is a shareable URL.
  Wired: server route + Cmd-K palette + _SUB_SECTION_MAP + diligence
  index card + Guide context (ToolRouteDefinition + full manual _ctx).
- **Found + fixed (pre-existing, full-platform)**: the guide-invariant
  suite was RED on main — /chart-builder, /pie-chart and /excel-mapping
  (waves 62–65) shipped with 3 common_questions (below the 5-Q floor)
  and empty related_routes. All three bumped to 5 questions + cross-
  linked as a chart-tool family; expert-calls registered compliant from
  birth (first related_routes draft pointed at an unresolvable route —
  caught by the resolver invariant, fixed).
**Verify**: new `test_expert_calls.py` (19) — bank integrity (7 lenses
fully specified, every question topic-valid with listen_for, headline
topics triangulated across ≥2 lenses), guide build (topic order, exact
question counts, unknown lens → None never a generic guide), plan
apportionment (20-call == recommended; 8/12/30/75 sum exactly, no
zero-call lens; 0/3-call edge), coverage semantics (strict statuses,
findings name gaps with NO percent headline, complete-read, empty
state), page render (plan/guide/tracker needles, qs-driven lens/size/
deal, status chips, hostile inputs escaped + fall back), wiring
(palette, section map, guide contexts, diligence index). Live HTTP
smoke on a real server: 4 URLs incl. hostile params → all 200, no
tracebacks. Guide-invariant suite 31 green (was 3 RED on main);
targeted sweep 1,372 passed; full suite at commit gate.

## W2-164b (2026-06-12) — full-suite gate: two more pre-existing reds found + fixed
The wave-66 full-suite gate (15,680 passed) surfaced two failures that
reproduce on a CLEAN tree (both pre-date this wave):
- **`/diligence/texas-infusion` orphaned from the diligence catalog**
  (since wave #47): the section-catalog invariant scrapes every served
  /diligence/* route from server.py and requires a diligence-index card;
  the Texas infusion study never got one. Added the card (Audit &
  Stress, beside TAM/SAM Builder).
- **`user-supplied` data-universe kind never registered** (waves 62–64):
  chart-builder / pie-chart / excel-mapping all pass
  `universe="user-supplied"` to ck_source_purpose, but the kind wasn't
  in _DATA_UNIVERSE — ck_data_universe fails safe to nothing, so all
  three pages silently shipped WITHOUT their data-provenance chip.
  Registered the kind ("YOUR INPUTS — renders only the values you
  enter; no stored data, no data claim"); chip verified rendering.
- Also classified `/diligence/expert-calls` in surface_status as NAVY
  ("Diligence calculator (your inputs)") so the catalog honesty dot is
  hand-set, not defaulted.
**Verify**: both failing tests green; targeted sweeps 101 + 125 passed
(catalog/universe/surface-status/guide-invariant/chart suites); pie
page renders the YOUR INPUTS chip; classify_surface returns the navy
calculator label for expert-calls.

## W2-165 (2026-06-12) — Expert-Call Program slice 2: cadence, triangulation matrix, call sheet, exhibit guides, deal prefill (wave #67)
Deepened the wave-66 section into a complete workstream — five specific
features, all on the same page:
- **4-week cadence plan** (`weekly_cadence`): the program plan re-timed
  across the standard CDD sprint via per-lens phase weights encoding
  booking reality (former employees + referrers front-load and frame
  hypotheses; payer/competitor calls wait for precise questions; week 4
  chases contradictions). Largest-remainder per lens, so the cadence
  NEVER resizes the program — per-lens week sums equal program_plan
  exactly (tested at 8/20/33). Week × lens grid + per-week focus
  rationale on the page.
- **Topic × lens triangulation matrix** (`topic_lens_matrix` +
  `topic_coverage`): derived from the question bank (can't drift), the
  grid shows which lenses can answer each CDD topic; with completed
  calls logged, each topic reads TRIANGULATED (≥2 ACTIVE lenses ask it)
  / SINGLE-LENS / DARK — two voices from the same lens share its bias,
  so they never triangulate a topic alone.
- **Call-sheet CSV export** (`/api/diligence/expert-calls.csv`):
  one row per planned call (call #, week, lens, sourcing channel
  pre-filled) + empty date/interviewee/status/finding/thesis-tag
  columns — the data-room tracker, generated from the same qs as the
  page. House formula-injection defang on user text (deal "=cmd()|x" →
  quoted), n clamped 1–200.
- **Exhibit-chrome call guides**: the printable guide now renders via
  ExhibitFactory (numbered EXHIBIT, deal label, question count, bank
  vintage 2026-06 in the sourced footer) — Cmd+P → the PDF an associate
  takes into the call.
- **Active-deal prefill** (deal-context parity, Item-12 pattern): the
  pedesk_active_deal_meta cookie pre-stamps the program/guides/call
  sheet with the deal name, with the teal visible-note convention;
  explicit ?deal= always wins; _prefill_deal never leaks into the CSV
  export URL (tested).
**Verify**: test_expert_calls.py 19→35 — cadence retime-not-resize at 3
program sizes + sequencing pins (former-employee wk1>wk4, payer wk1=0)
+ focus lines; matrix derived-from-bank consistency; triangulation
semantics (none→DARK, one lens→SINGLE-LENS never TRIANGULATED, two
sharing lenses→TRIANGULATED); call-sheet row count/order/CSV shape/
defang/no-deal honesty; page renders cadence+matrix+CSV link, chips
follow done counts, EXHIBIT chrome + bank vintage, _prefill_deal kept
out of export URL; real-HTTP class: cookie prefill with visible note,
param override, CSV endpoint serves N rows, no-cookie no-note. Live
smoke: 6 requests incl. hostile (n=-3 clamps to 1 row, encoded =2+2
deal defanged) → all 200, no tracebacks. Neighbor suites green:
exhibit-factory + deal-context-prefill + palette + catalog + guide
invariants + tools-index (88).

## W2-166 (2026-06-12) — Expert-Call Program slice 3: calls logged as deal-note evidence, coverage derives from the record (wave #68)
Closed the workstream loop — plan → call → EVIDENCE ON THE DEAL:
- **`format_call_note` / `logged_call_counts`** (expert_calls.py):
  structured note body "EXPERT CALL · <lens> — <vantage> (as of
  <date>): <finding> [SUPPORTS|CONTRADICTS|NEW QUESTION]". STRICT
  validation (unknown lens / invalid tag / empty finding raise — a
  malformed note would silently fall out of the coverage count);
  field caps (vantage 200 / finding 2000 / as-of 40); the counter
  accepts only the exact prefix+label, so free-text notes that merely
  mention a call never inflate coverage.
- **POST `/api/expert-calls/log`**: records the note via deal_notes on
  an EXISTING deal only (same junk-upsert guard as the roll-up save);
  invalid fields redirect with NO note written; success → ?logged=1
  confirmation. Author = session user.
- **Page**: "Log a completed call — <deal>" form (lens select /
  vantage / as-of / finding / thesis-tag) renders ONLY with an active
  deal (nothing honest to attach to otherwise); the coverage tracker
  now DERIVES its counts from the logged EXPERT CALL notes with a
  visible source note ("Counts below come from N logged notes —
  enter numbers to override"); explicit done_* params always win;
  lens-chip links stop baking note-derived counts into params (a live
  count must not freeze into an override). The closing-script
  discipline ("an untagged call is color, not evidence") is now
  enforced by the form's tag select.
**Verify**: test_expert_calls.py 35→43 — note↔counter round-trip,
field defaults ("vantage unstated"/"date unstated", tag normalized),
strict raises, free-text/almost-prefix bodies count zero; real-HTTP
class: form only with deal context, POST→303 logged=1 + note with the
exact prefix + page shows confirmation + THIN chip from the derived
count + explicit param override kills the derived note, unknown deal/
bad lens/bad tag/blank finding → 303 without logged=1 and ZERO new
notes. Live workflow smoke: 3 POSTs (incl. hostile <script> finding +
5,000-char finding) → notes recorded capped, page derives COVERED,
note searchable on /notes?q=EXPERT+CALL with hostile content escaped
(escaping verified at the notes renderer). Neighbor suites green:
expert-calls + rollup-save + deal-context-prefill + guide invariants
+ section catalog (95). /deal/<id> fallback dashboard for snapshot-less
deals omits the notes section — pre-existing surface shape, noted.

## W2-167 (2026-06-12) — CDD Scope: the four engagement depth levels (wave #69)
New CDD dimension covered — not another workstream but the DEPTH axis:
how deep the same nine workstreams run at each deal stage. New page
/diligence/cdd-scope + rcm_mc/diligence/cdd_scope.py (UI-free):
- **CDD_LEVELS**: L1 desktop screen (pre-IOI, days, go/no-go on
  bidding) · L2 red-flag CDD (indicative bid, 1–2 wks, kill-risk
  focus) · L3 full-scope CDD (exclusivity, 3–6 wks, the IC
  underwrite) · L4 confirmatory/bring-down (post-IC, movement only).
  Every duration explicitly labeled "market convention" (never a
  quote, tested); NO cost figures by design; per-level call-program
  size links straight into /diligence/expert-calls?n=….
- **DEPTH_MATRIX**: 9 workstreams × 4 levels (NONE/DESKTOP/TARGETED/
  FULL) with two tested contracts: monotone L1→L3 (a deeper
  engagement never does LESS of a workstream; L3 = FULL everywhere)
  and L4 never FULL (confirmation, not re-discovery). Each workstream
  row links to the platform surface that EXECUTES it (tam-sam,
  expert-calls, cim-crosscheck, market-rates, reg-calendar, …) — all
  9 routes pinned against server.py so a dead link can't ship.
- **recommend_level(stage, familiarity, deal_type)**: deterministic
  scoping aid — stage anchors (screen→L1, bid→L2, exclusivity→L3,
  preclose→L4), adjustments stated as reasons (known-market add-on at
  exclusivity right-sizes to L2 because a full re-build duplicates
  the platform CDD; new-market exclusivity flags call-booking lead
  time as the critical path). Invalid/partial inputs → None and the
  page says "never guesses" — no scope from a partial picture.
- **level_task_list + /api/diligence/cdd-scope.csv**: the concrete
  per-level engagement plan (workstream · depth · task · executing
  surface · empty owner/status columns); unknown level falls back to
  L3, never 500s.
- Wired: route + palette + section map + diligence index card +
  guide contexts (5-Q floor + resolvable related_routes from birth —
  the wave-66 lesson) + surface-status NAVY.
**Verify**: new test_cdd_scope.py (20) — registry completeness incl.
the convention-label pin, matrix coverage/monotonicity/L4-narrowing,
all 24 recommender combinations have reasons + invalid→None, task
lists match the matrix with non-empty task text, CSV shape + bogus-
level fallback, page render (cards/matrix/tasks/recommender reason/
partial-input honesty/hostile level), wiring + guide-floor checks.
Wiring sweep 140 passed (palette/catalog/guide-invariant/universe/
expert-calls). Live smoke: 6 URLs incl. hostile stage + formula-
injection level param → all 200, no tracebacks.
## W2-164 (2026-06-12) — Charts: per-series colours + gauge KPI (wave #66)
Continued the graphics-suite improvements:
- **Per-series colour pickers in the Chart Builder** — every series (or
  category, for pie/funnel/tornado/dot/matrix/marimekko) gets its own
  colour picker (`sc{i}`), defaulting to the chosen palette but fully
  overridable, so a chart can match any deck/brand exactly. A small JS
  re-seeds the pickers when the palette dropdown changes so the palette
  stays meaningful. Picked colours flow into the rendered SVG via
  `opts["colors"]`.
- **Gauge / KPI chart type** (kit now 20): a 180° semicircular gauge from
  a single value (+ optional max) — big serif value, label, and 0→max
  scale. Reads `Metric · Value · [Max]`; auto-scales the max when omitted.
**Verify**: +5 tests — gauge present (≥20 types) + renders value/max
clean, per-series colours override the palette and reach the SVG,
palette-sync script present. Full suite green.

## W2-165 (2026-06-12) — Charts: heatmap grid + source/footnote line (wave #67)
Two more client-readiness improvements:
- **Heatmap grid** chart type (kit now 21): a scoring matrix — rows ×
  columns, each cell shaded on a sequential teal scale by value with the
  value printed, row labels left + column headers top. The classic CDD
  attractiveness/scoring matrix.
- **Source / footnote line** on every chart: `render_cdd_chart` and
  `presentable_pie` now inject a small bottom-left source/footnote line
  (the way every client deck exhibit carries one). A "Source / footnote"
  field added to the Chart Builder + Pie Chart pages; it's part of the
  rendered SVG so it travels with the SVG/PNG export.
**Verify**: +4 tests — heatmap present (≥21 types) + renders grid with
row/column headers clean, footnote appears in the chart SVG + on the
page; pie footnote renders. Full suite green.

## W2-166 (2026-06-12) — Exhibit Composer: multi-chart deck slide (wave #68)
The capstone of the chart suite — compose up to 4 charts onto one slide:
- **`compose_exhibit(panels, …)`** (in cdd_chart_kit): renders 1–4 charts
  and nests each (via `_embed` rewriting the child <svg> opening tag) into
  a single 16:9 (1280×720) slide with an eyebrow, serif title block, a
  source line, and a Chartis·PEdesk mark. Layout adapts to panel count
  (1 = full, 2 = side-by-side, 3–4 = 2×2). Exports as ONE SVG/PNG.
- **`exhibit_page.py`** (route `/exhibit`): slide eyebrow / title / source
  + 4 panel configs (chart type + palette + panel title + pasted data;
  blank panels drop). qs-driven (t{i}/pt{i}/d{i}/pal{i}) so a whole slide
  is a shareable URL; the composed slide gets the SVG/PNG export toolbar.
  Wired into Research nav + Cmd-K palette + a documented guide context.
**Verify**: new `test_exhibit.py` (6) — composes one SVG with the nested
chart svgs (parent + 4), layout drives panel count, empty→just the frame,
page populated + custom slide + palette/nav/guide registration. Full
suite green.

## W2-167 (2026-06-12) — Charts: slope + gantt/timeline types (wave #69)
Two more consultant staples (kit now 23 types):
- **Slope chart** (`slope`): before→after — two periods per category with
  a connecting line + end-point values (e.g. entry vs exit margins,
  denial-rate change). Headers name the two periods.
- **Gantt / timeline** (`gantt`): horizontal task bars on a time axis from
  a task · start · end table — roadmaps, 100-day plans, workstream
  sequencing. Time gridlines + task labels.
Both surface automatically in the Chart Builder chips + gallery with
example data (value-creation slope; 100-day workstream gantt).
**Verify**: +1 test (≥23 types incl. slope/gantt) + both render clean
(no None) with their labels. Full suite green.

## W2-168 (2026-06-12) — Visuals hub landing page (wave #70)
A single landing page (`/visuals`) for the graphics toolkit — a card per
tool (Chart Builder, Pie Chart, Excel Mapping, Exhibit Composer) with a
LIVE thumbnail rendered from the same kit the tools use (so the hub always
reflects real output) + a one-line description and link. Wired into
Research nav + Cmd-K palette + a documented guide context. Discoverability
capstone for the suite.
**Verify**: new `test_visuals_hub.py` (3) — a card + link per tool, ≥4
thumbnail SVGs, palette/nav/guide registration. Full suite green.

## W2-169 (2026-06-12) — Texas infusion: Medicare Monthly Enrollment → true MA penetration (wave #71)
Pivoted back to diligence and wired a named source — CMS Medicare
Monthly Enrollment — to fix the MA-penetration denominator:
- **`cms_enrollment.py`** (new): a live client for the CMS Medicare
  Monthly Enrollment file — total Medicare beneficiaries + the FFS vs
  MA-and-other split by state (latest month). Resolves the dataset from
  the CMS catalog, fails CLOSED, and falls back to a published TX total
  (≈4.6M) — never fabricated.
- **`texas_ma_enrollment`** now computes a TRUE MA-penetration rate =
  MA enrollment ÷ total Medicare beneficiaries (≈48%: 2.19M / 4.6M),
  replacing the 65+ proxy (which overstated at ~55% by omitting the
  under-65 disabled). The proxy is kept for continuity; the panel now
  shows TX MA enrollees / total Medicare / MA penetration / dual, with
  the denominator source labeled (live vs published). Live county/total
  penetration fills in via the enrollment API under `?nppes=live`.
**Verify**: +1 integration test (penetration uses the total-Medicare
denominator, < the proxy, offline = published fallback) + new
`test_cms_enrollment.py` (4) — offline uses published total, unknown
state → US fallback, fetch fails closed unresolved, parses latest-month
total from a mocked payload. Full suite green.

## W2-170 (2026-06-12) — Texas infusion: HOPD steered-away pool (CMS Outpatient Hospitals) (wave #72)
Wired the last named data source — CMS Medicare Outpatient Hospitals (by
provider & service) — and quantified the HOPD "steered-away" pool:
- **`cms_opps_outpatient.fetch_opps_state_infusion`** (new): a best-effort
  live aggregator over the OPPS by-provider-and-service file — total HOPD
  outpatient services + Medicare payment for the infusion J-codes in a
  state. Resolves the dataset from the CMS catalog, fails CLOSED.
- **`texas_hopd_pool`**: per-metro HOPD infusion pool — HOPD patients =
  real metro infusion patients × the HOPD site share (30%), HOPD revenue
  at the sizing model's infusions/yr × revenue/infusion. ≈58k capturable
  HOPD patients / ≈$0.7B across the four metros (DFW + Houston largest).
  The live CMS OPPS pull overrides with real services + payment under
  `?nppes=live`.
- **Page**: a "HOPD infusion — the steered-away pool" panel in the
  site-of-care section — capturable HOPD patients + revenue pool KPIs,
  per-metro bars, and a LIVE/MODELED badge. Frames the 30% HOPD pool as
  the white-space an AIC/home roll-up captures (not a competitor).
This completes the user's named data-source list (CDC PLACES, ACS, ASP,
MA enrollment, Medicare Monthly Enrollment, NPPES + map, Part-B POS, and
now Outpatient Hospitals).
**Verify**: +3 HOPD tests — pool = real metro patients × HOPD share +
ranked + summed, offline is modeled (OPPS fails closed), live flag
threads through + fails closed; +2 render needles. Full suite green.

## W2-171 (2026-06-12) — Texas infusion: IC-summary investment thesis (wave #73)
Added the top-line synthesis a partner reads first — `texas_investment_
thesis(a)` builds the IC summary PURELY from the assembled analysis so it
can never drift from the sections below:
- **5 thesis pillars**, each with its supporting number: large/growing/
  fragmented market ($3.36B TAM · 8% CAGR · HHI 517); structural site-of-
  care tailwind (HOPD 46%→30% · $684M HOPD pool); favorable Texas
  structure (no CON · 48% MA · 70% non-hospital); AIC unit economics
  work ($218K/chair · ~19% break-even); de-novo white-space (6
  undersupplied growth corridors).
- **Key risks** (drug-spread compression, home-infusion referral
  concentration + the HIT gap, the most-at-risk therapy) and **diligence-
  next** gaps (replace modeled counts/rates with the target's claims;
  quantify referral concentration + white-bagged %; confirm TX statute).
- A headline + a CONSTRUCTIVE verdict steering value creation to service
  margin + RCM, not the drug spread.
- **Page**: an "Investment Thesis · IC Summary" block at the very top
  (after the KPI strip, before market sizing) — pillars as cards, risks,
  and diligence-next.
**Verify**: +3 thesis tests — 5 pillars / ≥3 risks / ≥3 diligence-next
with complete fields, thesis numbers match the sections (real HHI,
HOPD shift pts, undersupplied count), most-at-risk therapy surfaces in
the risks; +3 render needles. Full suite green.

## W2-172 (2026-06-12) — Texas infusion: auto-composed investment-highlights exhibit (wave #74)
Connected the graphics suite to the diligence data — the Texas page now
AUTO-GENERATES a one-page exhibit slide from its own live analysis:
- **`_exhibit_section(a)`**: builds four panels from the live analysis and
  composes them (via the chart kit's `compose_exhibit`) into one 16:9
  "Texas Infusion — Investment Highlights" slide:
  1. Market-sizing funnel — TAM → SAM → SOM ($M)
  2. Site-of-care mix 2015–2024 (100% stacked) — the HOPD→AIS/home shift
  3. Top de-novo county opportunities (bar) — from the growth scorecard
  4. Current site-of-care mix (donut)
  Every panel recomputes from the same figures as the sections, so the
  exhibit can never disagree with the page.
- **Page**: a "One-page exhibit" section (deck-ready, SVG/PNG export
  toolbar) before Sources — the deliverable a partner drops into a deck.
This is the capstone tying the two arcs together (graphics kit + Texas
diligence data).
**Verify**: +1 exhibit test (four panels nested into one slide, export
toolbar, no None) + 2 render needles. Full suite green.

## W2-173 (2026-06-12) — Texas infusion: section navigator (wave #75)
The page now runs ~29 sections; added a usability layer so a partner can
move around it:
- **`_inject_section_nav(body)`**: a post-process pass that gives every
  `ck-section-header` a slugified, unique `id` (with `scroll-margin-top`
  for a clean landing) and builds a floating "☰ Sections" navigator
  (fixed bottom-right `<details>` dropdown) listing every section as an
  anchor link. Recomputed from the rendered headers, so it always matches
  the live section set — no hardcoded list to drift.
**Verify**: +1 test — ≥20 unique section ids injected, the floating nav
present, every nav link points at a real section id. Full suite green.

## W2-174 (2026-06-12) — Texas infusion: downloadable Markdown IC memo (wave #76)
A partner-shareable deliverable — the analysis as a clean Markdown IC
memo a partner pastes into a writeup:
- **`texas_infusion_memo_md(a)`**: renders the headline, verdict, the
  5-pillar thesis, key risks, diligence-next, and a key-figures table
  (TAM/SAM/CAGR/HHI/MA penetration/AIC contribution/undersupplied
  counties/65+ base) — a pure function of the assembled analysis.
- **Route** `/api/diligence/texas-infusion/memo`: serves the memo as a
  `text/markdown` download (honoring the same AIC overrides as the page).
- **Page**: a "⬇ IC memo (Markdown)" button in the Investment Thesis
  block.
**Verify**: +2 tests — memo has the section structure + real figures
(HHI, verdict, one numbered item per thesis pillar); the page links to
the memo download. Full suite green.

## W2-175 (2026-06-12) — Texas infusion: server-rendered exhibit SVG download (wave #77)
Completed the deliverables set (alongside the IC memo):
- Refactored the auto-exhibit into a shared **`texas_exhibit_svg(a)`**
  helper (used by the page section AND the download route, so they can
  never disagree).
- **Route** `/api/diligence/texas-infusion/exhibit.svg`: serves the
  composed Investment-Highlights exhibit as a standalone, server-rendered
  `image/svg+xml` download (honoring the AIC overrides).
- **Page**: a "⬇ download the exhibit SVG (server-rendered)" link under
  the one-page exhibit.
**Verify**: +1 test — the shared helper returns the 5-svg composed slide
(no None) and the page links to the SVG download route. Full suite green.

## W2-176 (2026-06-12) — Medicare Monthly Enrollment, county grain: the Part B denominator by county (wave #73a)
Closed the last unbuilt item of the user's multi-source CMS data request.
- **`cms_monthly_enrollment.py`** (new live client): resolves the CMS
  "Medicare Monthly Enrollment" dataset UUID from the data.json catalog,
  pulls state + county annual-average rows (TOT/ORGNL_MDCR/MA_AND_OTH/
  AGED/DSBLD benes), walks the publication year back from today (CMS
  lags), parses comma counts, and maps suppressed cells ('*') to None —
  never 0. Fails closed when egress is blocked; nothing fabricates an
  enrollment count.
- **`texas_medicare_base()`** (engine): total / FFS / MA beneficiaries —
  the TRUE Part B infusion denominator — for TX and the four metros'
  member counties. Offline the counts are MODELED from real inputs and
  labeled: aged ≈ real 65+ pop × near-universal enrollment (0.95),
  disabled ≈ total pop × the national disabled-bene rate (0.023; both
  anchors documented), FFS/MA split from the real vendored TX MA
  enrollment. With ?nppes=live the published CMS rows replace every
  count, county-by-county (per-county live dots).
- **Page**: "Medicare beneficiary base — the Part B denominator" section
  after Payer mix — KPI strip (total / FFS buy-and-bill book / MA
  steered book / TRUE MA penetration / aged / disabled), an FFS-vs-MA
  100% bar, a top-12 metro-county table, the LIVE/MODELED badge, and a
  footnote that the 65+-proxy penetration in the MA panel above
  overstates true penetration. + SO WHAT (size Part B on FFS benes) +
  source line.
**Verify**: new `test_cms_monthly_enrollment.py` (10) — suppression→None,
alias parsing, fail-closed (no dataset / network error / nothing
published), year walk-back to latest published, state+county composition.
+6 in test_texas_infusion — state math (FFS+MA=total, aged+disabled=
total), modeled TX total inside the published 4.6–4.8M band, counties ⊂
metro members sorted desc (Harris #1), live mock replaces state + matched
counties and leaves the rest MODELED, page renders section + badge,
source cited. Full suite green.

## W2-177 (2026-06-12) — Found-bug sweep: 5 wiring regressions from waves #62–65 (wave #73b)
The full-suite sweep after the enrollment wave caught five pre-existing failures the
graphics waves left on main (verified failing on a clean tree):
- **`user-supplied` data-universe kind unregistered** — /chart-builder,
  /excel-mapping and /pie-chart declared `universe="user-supplied"` but
  the kind wasn't in `_DATA_UNIVERSE`, so the provenance chip rendered
  EMPTY on all three pages (silent provenance loss). Registered with a
  self-describing tooltip ("values you typed or pasted — not a data
  claim") + docstring kind list updated.
- **Guide 5-Q floor + empty related_routes ×3** — the three graphics
  pages shipped with 3 common_questions (floor is 5) and no
  related_routes, so the Guide couldn't recommend siblings. Each now
  carries 5 questions (incl. the export/size features wave #65 added)
  and cross-links the graphics-utility family.
- **/diligence/texas-infusion orphaned from the catalog** — the served
  route never appeared on the /diligence landing. Added to the Audit &
  Stress pillar beside its sibling TAM/SAM Builder.
**Verify**: the 5 failing tests (test_data_universe_kinds_registered,
test_pedesk_guide_5q_invariant ×3, test_section_catalog) now pass;
1,321-test wiring sweep (guide/palette/chartis/catalog/nav) green.

## W2-178 (2026-06-12) — /exhibit guide-floor fix after the main merge (wave #73c)
Merging main (waves #66–68 from the parallel chart stream) brought the
new /exhibit Exhibit Composer with the SAME wiring gap the W2-177 sweep
fixed on its siblings: 2 common_questions (floor is 5) and no
related_routes. Brought it to the floor + cross-linked /chart-builder
and /pie-chart. Guide invariant suites + 1,254-test graphics/wiring
sweep green on the merged tree.

## W2-179 (2026-06-12) — /visuals guide-floor fix after the second main merge (wave #73d)
The next main merge (waves #69–70 from the chart stream) brought the
/visuals hub with the same gap again: 2 common_questions, no
related_routes. Brought to the floor + cross-linked all four builder
tools. NOTE for the chart stream: new pages keep landing below the
Guide 5-Q floor — add the 5 questions + related_routes in the same PR
that adds the page (test_pedesk_guide_5q_invariant is the gate).

## W2-180 (2026-06-12) — HOPD per-hospital volume via CMS OPPS by Provider & Service (wave #73e)
Closed the FINAL remaining item of the multi-source CMS data request —
and fixed a latent parser bug found while wiring it:
- **Parser fix (found bug)**: the published "Outpatient Hospitals - by
  Provider and Service" file is **APC-grain** (APC_Cd / CAPC_Srvcs /
  Bene_Cnt — confirmed against the CMS data dictionary), but
  `parse_opps_csv` only knew the speculative HCPCS aliases, so the real
  download parsed to NOTHING. Added the APC aliases (HCPCS kept for old
  extracts) + corrected the module docstring.
- **Live client** (same module): `resolve_opps_provider_dataset`
  (catalog UUID), `fetch_opps_apc_state` (per-hospital rows for one APC
  × state), `fetch_state_drug_admin` (per-CCN aggregate over the four
  OPPS drug-administration APCs 5691–5694; beneficiary counts are
  max-per-APC, never summed across APCs). Fails closed.
- **`texas_hopd_infusion()`** (engine): the steerable hospital pool by
  metro. Offline = MODELED from the page's own factors (metro infusion
  patients × HOPD site share × Medicare slice — all already on the
  page); ?nppes=live = real per-CCN Medicare drug-admin services mapped
  to metros via each hospital's HCRIS county + a top-10 TX hospitals
  table naming where the steerable volume sits. FFS-only caveat stated
  (live counts UNDERSTATE the pool).
- **Page**: "HOPD infusion volume — the steerable pool" section after
  site-of-care — APC reference chips, per-metro modeled/live table,
  LIVE/MODELED badge, top-hospitals table (live), SO WHAT + source.

USER DATA REQUEST — COMPLETE: CDC PLACES ✓ ACS ✓ ASP ✓ MA ✓ NPPES+map ✓
J-code POS ✓ Medicare Monthly Enrollment ✓ Outpatient by Provider &
Service ✓. Every named source now has a live client wired into the
Texas page with an honest labeled fallback.
**Verify**: new test_cms_opps_live (6) — APC-grain CSV rows now parse
(the pre-fix aliases dropped them), the four drug-admin APCs, fail-closed
×3, mocked-payload parse, per-CCN aggregation (services sum, benes max,
$ math). +5 in test_texas_infusion — modeled pool == page factors
recomputed, APC set, live mock aggregates via the real HCRIS Harris-county
join, page renders, source cited. Full suite green.

## W2-181 (2026-06-12) — Reconcile the two parallel CMS wirings (wave #73f)
The chart stream and this stream independently wired the SAME two CMS
sources (their W2-169/170 vs this stream's W2-176/180). Reconciled at
the merge instead of shipping duplicates:
- **Both kept where complementary**: their state-level true-MA-
  penetration upgrade to texas_ma_enrollment + their compact HOPD
  "$-pool" panel inside site-of-care stay; this stream's county-grain
  Medicare-base section and per-CCN HOPD drill-down (retitled "HOPD
  volume by hospital — who holds the pool") stay. The modeled numbers
  agree by construction (same patients × HOPD share).
- **Found bug fixed at the merge**: their `fetch_opps_state_infusion`
  filtered `HCPCS_Cd` (J-codes) against the APC-grain file — a filter
  that matches nothing live. Rewired it as a thin bridge over the
  APC-grain `fetch_state_drug_admin` (same name + return shape, their
  tests untouched); `hcpcs_codes` accepted for back-compat and ignored,
  documented in the docstring.
**Verify**: merged-tree texas suite (both streams' test classes) +
opps client suites green; page renders both blocks consistently.

## W2-182 (2026-06-12) — CIM claim-percentile chip in ck_peer_percentile language (backlog #23)
Backlog triage first: ready-queue items #21 (palette name-search), #22
(P9 diff detail), #25 (DQ snapshot dates) and #29 (model-card link)
were already shipped by earlier waves — marked done. The remaining
delta on #23: the CIM cross-check claim-percentile chip was plain text
("claim @ p97 of n=457") while the platform standard is the
ck_peer_percentile visual (position track + peer label). Upgraded
_pctile_chip to that language — mono chip + 60px track with the dot at
the ENGINE's percentile (never recomputed in the UI) + the scope label
("vs TX hospitals (n=457)") — tail amber + tooltip preserved, aggregate/
small-n still render "". +2 chip assertions (track dot position derives
from engine rank; mid-range neutral). test_cim_crosscheck: 30 passed.

## W2-183 (2026-06-12) — ROLL-UP chip on saved scenario notes (backlog #24)
The save-to-deal roll-up note's reopen path was already a real anchor
(strict-charset linkify, pinned by NoteLinkifyTests); the missing half
of backlog #24 was the type chip. Scenario notes on the deal page now
carry a mono teal ROLL-UP chip in the note head so they're scannable in
a long list. Detection is on the embedded /pipeline/rollup? reopen path
the WRITER emits — a free-text note that merely says "roll-up" gets no
chip (pinned both ways). New .ck-deal-note-chip style in the deal-page
CSS. test_rollup_save_to_deal + test_server: 74 passed.

## W2-184 (2026-06-12) — Route-walker cookie-context mode (backlog #27)
Backlog #28 (screener state prefill) verified already shipped — marked
done. #27 built: `route_walker.py --deal-cookie <id>` walks every page
WITH the pedesk_active_deal_meta cookie set (TX / CCN 450358 sample
meta via the new `deal_cookie()` helper), so the prefill code paths —
CIM state/CCN, roll-up basket, screener state scoping — render under
test instead of only on a partner's machine. `walk()` gained an
optional `cookie=` arg (plain Request when unset). The weekly
regression sweep now runs a SECOND walker pass with the cookie after
the plain pass. +1 live-server test: cookie walk over the three
prefill routes → 200 / no traceback / no nan-None leak.

## W2-185 (2026-06-12) — Exhibit chrome on X-Ray peer roster + screener compare (backlog #26)
P5 expansion: the two paste-ready comp tables now carry the house
exhibit discipline (numbered figure + units stated + sourced,
vintage-stamped footer + print-to-PDF page rules):
- HCRIS X-Ray peer roster → "EXHIBIT 1 — Peer roster — matched
  comparables", units state the roster basis (n peers · filed HCRIS
  values, latest per CCN · — = not reported/implausible), footer
  sourced CMS HCRIS + FY of the target filing, deal_label = target.
- Target-screener compare basket → "EXHIBIT 1 — Compare basket —
  side-by-side", cross-vertical baskets titled "(cross-vertical)" with
  units noting Size/Quality are labeled per vertical (not comparable).
**Verify**: +3 assertions in test_hcris_xray (exhibit number, title,
source, FY-stamped footer regex) and +2 tests in test_target_screener
(single-vertical exhibit without the cross caveat; cross-vertical title
+ units). 183 passed across both suites.

## W2-186 (2026-06-12) — Empty-state sweep test: ?state=ZZ + empty-db walk (backlog #30)
The mechanical half of the carried "empty-state verification pass" is
now a permanent gate: new test_empty_state_sweep.py boots an open
server on an EMPTY db and walks (a) nine state-filterable analytics
pages with ?state=ZZ and (b) eight core portfolio pages, asserting
200/3xx + no traceback + no nan/None leak via the route-walker marker
set. The screener ZZ case additionally pins the honest read: the
results header counts "0 Hospitals" (the filter applied, not silently
dropped) and the page says so in words; the cross-universe scale strip
legitimately keeps the full universe sizes as context. 3 tests pass on
the empty db.

## W2-187 (2026-06-12) — Ranking-contract fix: flagship pin survives module growth
The regression-sweep cadence caught test_surface_rankings failing on
main: the Texas market study (now 3,092 lines after both streams' waves)
overtook /target-screener as global rows[0] — both score a saturated
10.0 and the sort tiebreak is raw module LOC, so sheer page size read
as flagship displacement. The ranking only DRIVES per-section nav
promotion, so the global pin was an artifact. Re-pinned the contract to
intent: the screener holds the MAX total and leads its own (Source)
section. Noted for a future considered item: the checked-in
_surface_rankings.py manifest has drifted from live build_rankings()
scores (e.g. screener 9.6 manifest vs 10.0 live) — regenerating it
shifts nav rails and is pinned by other tests, so it needs its own
wave, not a drive-by. test_surface_rankings: 9 passed. Sweep otherwise
green: 15,722 passed / 1 failed (this one) / 72 skipped.

## W2-188 (2026-06-12) — Surface-rankings manifest regenerated (drift closed)
Follow-through on the W2-187 note: the checked-in _surface_rankings.py
manifest had drifted well behind live build_rankings() (317 surfaces;
scores moved as pages grew/got tests — e.g. screener 9.6→10.0, market
map 5.2→7.6). Regenerated via scripts/rank_surfaces.py with one
generator fix first: the B168 curated label overrides (/library →
"Deal Corpus", /portfolio → "Overview") are now BAKED INTO the
generator (_LABEL_OVERRIDES) — they had been hand-edited into the
"do not edit" manifest and silently reverted on regen, reintroducing
the recursive-dropdown bug the B168 tests guard. One B168 dropdown
test was over-pinned (asserted /library VISIBLE in the dropdown; after
regen it legitimately ranks below the top-N cut) — re-pinned to: no
recursive item ever, and IF /library makes the cut it carries the
non-recursive label, with the manifest-level label still pinned
unconditionally. All 9 RANKINGS-pinned suites (93 tests) + 976-test
nav/palette/best/landing sweep green.

## W2-189 (2026-06-12) — P13 insight bullets on the state-profile dossier
Second half of the old P13 item (/portfolio adopted ck_insight_bullets
earlier; the state market page never did). New _profile_insights(state,
name, ranked): up to 2 top-quartile strengths + 2 bottom-quartile reads,
built ONLY from the same (rank, n, vs-median) tuples the dossier table
renders, with the significance guard (quartile rank AND ≥10% off the
U.S. median; directional metrics only; n≥8). ck_insight_bullets keeps
the copy-to-clipboard affordance and renders NOTHING when no candidate
passes. Placed under the KPI strip on /state-profile.
**Verify**: +2 tests — every claimed "#pos of n" in the rendered
bullets is re-derived from _all_ranked() and must match exactly
(regex over the bullet HTML); empty ranked structure renders "".
21 passed across the geo/state suites.

## W2-190 (2026-06-12) — Found bug: /pie-chart tripped the None-leak gate
A live route-walk (the new --deal-cookie mode's first full run: 169
routes plain + 169 with the active-deal cookie, 0 tracebacks) flagged
exactly one leak: /pie-chart rendered a literal ">None<" — the label-
mode select's "None" option, indistinguishable from a None-leak to the
walker's marker and on course to FAIL the next weekly --fail-on-leak
sweep. Renamed the option to "No labels" (value unchanged; clearer to
a partner anyway) + a regression test pinning >None< / >nan< out of
the page HTML. The walk's only other non-200 is /analysis/<deal> 404
on an empty db — the honest response, not a bug.

## W2-191 (2026-06-12) — Quick-import entry-time range validation (+ comma-drop bug)
PAGE_INVENTORY Tier-1 top fix for /import ("range validation exists
only on display"). Server-side now:
- **Hard physical bounds** in _route_quick_import_post — percentages in
  [0,100], days-in-AR in [0,500], counts/dollars non-negative. Bounds
  are physical limits only; implausible-but-possible values still
  import (ENTERED data, flagged downstream). Violations re-render the
  form with the offending field+bound named and EVERY typed value
  preserved (metric/financial fields now accept prefill), and the deal
  is NOT created.
- **Found bug while wiring**: a comma-formatted entry ('180,000' —
  exactly what the form hint promises works) hit ValueError inside the
  float loop and was SILENTLY DROPPED from the profile. Commas now
  strip server-side across numeric fields.
**Verify**: new ungated test_quick_import_validation.py (2 e2e tests —
140% denial rejected w/ prefill survival + deal not created;
comma-formatted values land as numbers via the flattened deal store).
The old import suite is env-gated (v2-shell markers) — verified green
under CHARTIS_UI_V2=1 too.

## W2-192 (2026-06-12) — P4 percentile chips on /compare (PAGE_INVENTORY top fix)
The deal-compare page's headline KPIs (Denial Rate, AR Days) now carry
ck_peer_percentile chips ranking each compared deal against the WHOLE
deal book — the inventory's "percentile context vs peers" fix. The
/compare handler passes {metric: full-book values} from list_deals()
(additive context; fails soft to no chips), the renderer takes an
optional peer_dists arg, and ck_peer_percentile's own honesty guards
hold: no distributions → no chip markup, a thin book (n<8) renders
"peer set too small (n=K)", never a fabricated rank. Chips are toned
lower-is-better for both metrics.
**Verify**: +2 tests — p70 reproduced by hand for denial 12.0 against a
10-value book ("vs portfolio deals (n=10)"); silent without dists +
honesty note on n=3. 52 passed across the comparison suites.

## W2-193 (2026-06-12) — Command-center hero-KPI drill-throughs (PAGE_INVENTORY top fix)
Every hero figure on / (command center) now links to the surface where
a partner ACTS on it: Hospitals → screener (hospitals universe);
PE-Sized Targets → screener scoped min_size=100 (verified: hospital
size == beds in the screener rows, so the deep link is semantically
right); Total NPSR + Median Margin → /market-data; Distressed →
/screening/bankruptcy-survivor (the distress scan); Active Deals →
/portfolio. Links sit in the trusted sub line so values stay clean
numbers. New test_command_center_drill.py: every link present on the
rendered page + every drill target verified to be an exact-match
served route in server.py (guards renames). 26 passed with the
adjacent command-center suites.

## W2-194 (2026-06-12) — Screener per-row deal-attach (+Deal) (PAGE_INVENTORY top fix)
The main screener table's row actions (X-Ray · Inspect · CIM · +Cmp)
gain +Deal: promote the provider straight to a prefilled /import (deal
id slugged vertical_ccn, name, state) without the Inspector round-trip
— closing the inventory's per-row deal-attach fix and completing the
Source → Pipeline path from the row itself. Same prefill contract the
Inspector's "Promote to Pipeline" link already used. +1 test (slug,
title, action present); test_target_screener: 159 passed.

## W2-195 (2026-06-12) — Market-data county drilldown links (PAGE_INVENTORY top fix)
/market-data/state/<ST>'s Cross-links panel now drills into the SCOPED
county explorer (/county-explorer?state=ST — the county layers existed,
the state detail just never linked there) and the state dossier
(/state-profile?state=ST). New ungated test_market_data_drilldown.py
pins both links + the explorer's state scoping. 12 passed with the
map suite.

PAGE_INVENTORY status note: of the 17 Tier-1 "top fix" entries graded
2026-06-10, TEN are now shipped (per-row deal-attach W2-194, drill-
throughs W2-193, /compare percentiles W2-192, import validation W2-191,
county drilldown W2-195, plus P5/P8/P9/P11/model-card from earlier
waves). Still open: portfolio per-deal alert digest, deal-workbench
ENTERED-basis pass, ebitda-bridge exhibit export, glossary links from
every KPI label (partial).

## W2-196 (2026-06-12) — EBITDA-bridge waterfall as a numbered exhibit (PAGE_INVENTORY top fix)
The bridge waterfall — the slide an IC deck actually pastes — now
carries the house exhibit chrome via ExhibitFactory: "EXHIBIT 1 —
EBITDA Bridge · 7 RCM Levers", units stated (annual $ at full run-rate,
filed HCRIS base × published research bands), footer sourced CMS HCRIS
+ FY-stamped, deal_label = the hospital, print-to-PDF page rules.
Closes the inventory's "exhibit-style export" fix the same way as the
peer roster + compare basket (W2-185). +1 test; 16 passed.

## W2-197 (2026-06-12) — Portfolio per-deal alert digest (PAGE_INVENTORY top fix)
The /portfolio deal table gains an Alerts column: one pass over the
LIVE unacked alerts (evaluate_active — acked stay out of the partner's
face, per the lifecycle) → worst-severity dot + count per deal, linked
to /alerts, severity-toned (red/amber/info). Deals with no alerts show
an em-dash, never a fabricated zero-chip; store=None or an evaluator
failure renders dashes, never a 500. Test exercises the REAL path (an
overdue deadline fires the alert; no synthetic Alert objects). 18
passed across the portfolio suites.

## W2-198 (2026-06-12) — National infusion-market scan (wave #78; chart stream)
"Where else after Texas?" — a new diligence surface that ranks every
state for an infusion roll-up from the SAME real per-state data the
Texas page uses:
- **`infusion_state_attractiveness()`** (new `infusion_market.py`): scores
  all 51 states on a weighted blend (0–100) of senior base (28%), MA
  penetration / site-of-care steerage (24%), no-CON de-novo runway (18%),
  metro density (15%), and commercial payer mix (15%) — from ACS
  demographics (vendored), CMS MA geographic variation, and the
  documented 12-state no-CON list. CA #1, then CO/MN/UT/AZ/TX; ranked +
  audited.
- **Page** `/diligence/infusion-markets`: a US tile-grid choropleth
  colored by score (TX outlined), a top-10 / Texas / bottom-5 ranked
  table with the component axes + no-CON flag, the Texas read (#6) with a
  link to the full deep-dive, and the methodology. Wired into Diligence
  nav + Cmd-K palette + guide context.
**Verify**: new `test_infusion_market.py` (6) — 51 states scored + ranked,
score = the weighted-axes blend, no-CON flag matches the documented list,
TX present + top-10; page renders the map/table/TX-read + palette/nav/
guide registration. Full suite green.

## W2-199 (2026-06-12) — Deal-dashboard ENTERED-basis pass (PAGE_INVENTORY top fix)
The deal dashboard's operating-profile strip rendered the MODEL'S
fallback constants as if they were the deal's numbers: a profile with
no denial rate showed "Denial Rate 12.0%" (the estimate default) and
no margin showed 10% — fabricated-looking observed values. Now: entered
values carry the ENTERED basis badge; missing metrics render an em-dash
with an honest sub-line ("not entered — estimates use the 12% model
default"); the Denial-Drivers tile only quotes a "14.2% → 8%"
trajectory when the rate was actually entered. The derived ESTIMATES
(EV/IRR/recoverable in the value anchor) legitimately keep their
defaults — they're labeled indicative. +2 tests; 7 passed.

## W2-200 (2026-06-12) — Glossary links: deal dashboard + market-data headers
Extended the metric→glossary linking (PAGE_INVENTORY "partial" fix) to
two more high-traffic surfaces: the deal dashboard's Denial Rate /
EBITDA Margin KPI cards (link lives in the trusted sub line —
ck_kpi_block ESCAPES labels by contract, which would have rendered a
literal &lt;a&gt;; caught in verification) and the market-data state-
detail hospital table's NPR / Margin headers. metric_label_link's
no-dead-links fallback verified (bed_count has no card → plain text).
+1 test; 8+12 passed across both suites.

## W2-201 (2026-06-12) — Found bug: /diligence/infusion-markets orphaned from catalog
The cadence sweep caught the chart stream's new national infusion scan
(wave #78) served but missing from the /diligence landing catalog —
the same orphan class as texas-infusion before it (the catalog-coverage
test is the gate that caught it). Added to the Audit & Stress pillar
beside the Texas study. Invariant suites (39) green.

## W2-202 (2026-06-12) — Doc fix: the live-mode session-TTL "limitation" was stale
CLAUDE.md claimed "live mode meta-refresh doesn't extend session TTL" —
misleading: verified functionally that every authenticated request
(including the 60s meta-refresh GET) bumps last_seen_at and slides the
IDLE window; only the 7-day ABSOLUTE TTL (set at login, by design as an
activity cap) ends the session. Rewrote the known-limitation note to
say precisely that. Also: clean full route-walk on the merged tree
incl. the chart stream's new national-scan page (170 routes, 0
tracebacks, 0 leaks, --deal-cookie mode).

## W2-203 (2026-06-12) — FEATURE_MATRIX statuses re-checked (doc honesty)
The matrix still listed P2 (CIM cross-check), P3 (driver trees), P7
(roll-up builder), P8 (rule join), P11 (DQ dashboard) as MISSING/
PARTIAL — all long shipped. Re-checked every row against the live
code and updated statuses with their log references. Remaining
genuinely-open sub-items now stated precisely: saved peer-set OBJECT
(P4), per-deal exhibit REGISTRY (P5), facility pins/catchments (P6),
ownership-CHOW diff alerts (P9), provenance modal + coverage metric
(P10), long-tail bullet coverage (P13), timing budgets (P14).

## W2-204 (2026-06-12) — Demo-deal realism: mvm_2026 rebuilt on real CCN 450358 (workstream H)
One of the seeded fictional demo deals is now a REAL facility: mvm_2026
becomes The Methodist Hospital (the platform's canonical sample TX CCN
450358). Its profile loads from the live HCRIS frame AT SEED TIME —
name, state, beds, NPR, filed margin, Medicare share — so the numbers
can never drift from the filing (no hardcoded copies); falls back to
the fictional seed when the frame is unavailable. metrics_basis records
"ACTUAL — filed HCRIS values, CCN 450358 FY2022" and the deal dashboard
identity line names the CCN + FY. +2 tests (profile == HCRIS row
EXACTLY; page names the CCN). 18 + integration suites green.

## W2-205 (2026-06-12) — Infusion market scan: Excel-Mapping cross-link + JSON API (wave #79)
Connected the new market scan to the graphics suite and the API surface:
- **"Open in Excel Mapping" cross-link**: pre-fills all 51 state
  attractiveness scores (+ a teal gradient and the score domain) into the
  Excel Mapping tool via the `?data=` param, so a partner can restyle and
  export the scan as a branded state map. Round-trips through
  `parse_values_text` (verified TX=85 of 51 states).
- **JSON API** `/api/diligence/infusion-markets` — the ranked scan for
  programmatic use, matching the platform's API-everywhere pattern.
**Verify**: +1 test — the cross-link's data param round-trips to all 51
states via the mapping parser. Full suite green.

## W2-206 (2026-06-12) — P13 bullets on market-data state detail
/market-data/state/<ST> gains two guarded insight bullets recomputed
from the SAME HCRIS frame the hospital table renders: the credible-
filing median operating margin + negative-margin count (the distress
pool), and the PE size-band count (100–500 beds, ≥$50M NPR — the
screenable universe). The credibility screen mirrors the row
renderer's gate (revenue >$100K, positive opex, margin in [-100%,
+100%]); n<8 renders nothing. Test re-derives both figures from the
frame and matches the rendered strings exactly. 14 passed.

## W2-207 (2026-06-12) — P14 timing budgets in the route walker
walk() now records per-route wall-clock ms (new `ms` TSV column); the
summary prints the 5 slowest pages every run, and a `--budget-ms N`
flag exits non-zero when any page exceeds the budget. Wired into the
weekly sweep's SECOND (warm-server) pass at 15s — generous on purpose:
the gate is for runaway regressions (an accidental O(n²) render), not
micro-tuning; the first cold pass stays budget-free since it pays
one-time imports. +1 walker test (ms recorded, sane bounds).

## W2-208 (2026-06-12) — P5 exhibit registry on the deal page
The deal dashboard's Export & Download card now lists the deal's
PREVIOUSLY generated artifacts from the generated_exports audit table
(format · timestamp · by · size, latest 10) — the per-deal exhibit
registry the FEATURE_MATRIX named as P5's open half. Read-only,
fails soft (registry errors → no panel), empty → nothing rendered.
+2 tests (real record_export row renders; empty deal shows no panel).

## W2-209 (2026-06-12) — P4 saved peer-set object (the matrix's open half)
New rcm_mc/portfolio/peer_sets.py — a named, owner-scoped CCN basket
mirroring the saved_screens store discipline (CREATE IF NOT EXISTS,
parameterised SQL, BEGIN IMMEDIATE, owner-scoped read AND delete).
Honesty contracts: invalid CCN tokens are DROPPED at save (shape-
validated, deduped order-preserving, capped 24), <2 valid CCNs
rejected, and consumers re-resolve CCNs against their live universes
so a stale CCN degrades to the module's own not-found handling.
Compare view: "Save basket as peer set" form (owner only, basket ≥2)
+ SAVED PEER SETS load/delete list (renders on the empty basket too —
loading is the natural first action). Server: POST /api/peer-sets/
{save,delete} + sets queried server-side and threaded through
render_target_screener (house pattern — page module stays store-free).
**Verify**: new test_peer_sets.py (7) — roundtrip order/dedup, junk
tokens never stored, <2 rejected, owner scoping both ways, signed-out
view has NO persistence affordance, owner sees form + sets + load
links, HTTP save→store roundtrip on the real server. 166 passed with
the full screener suite.

## W2-210 (2026-06-12) — P5 registry write-side (refill #36)
The W2-208 registry now fills itself: generating the IC memo
(/api/deals/<id>/memo) and the diligence package ZIP both record a
generated_exports row (format, size for the ZIP, generated_by) —
best-effort, a registry hiccup can never block the download. E2E test:
hitting the memo endpoint on a real server lands an ic_memo_json row
readable by list_exports. 10 passed.

## W2-211 (2026-06-12) — Saved peer sets hand off to the Roll-Up Builder (refill #33)
A saved peer set whose CCNs ALL resolve to the hospitals universe gets
a "→ roll-up" link straight into /pipeline/rollup?ccns= — the P4 →
P7 hand-off. Mixed/other-vertical sets get no link and no error (the
pro-forma combine only has HCRIS math behind hospitals). +1 test
(hospital pair links, mixed pair doesn't). test_peer_sets: 8 passed.

## W2-212 (2026-06-12) — PE-desk product wave: CDD Hub + customer evidence + rate intel + Excel template library

## W2-230 (2026-06-12) — Texas infusion: de-novo AIC build J-curve (wave #80)
Deepened the Texas page (per the "deepen Texas" steer) with the missing
piece between the static per-chair economics and a returns view — the
de-novo build P&L:
- **`aic_denovo_ramp(**editable)`**: the de-novo AIC build J-curve.
  Capex = chairs × per-chair fit-out + a fixed pre-open block goes out
  day one; utilization ramps to mature over the ramp period; the monthly
  contribution is the SAME chair model interpolated along its
  utilization→contribution curve (negative below break-even during the
  early ramp). Returns the 36-month cumulative-cash series + KPIs: build
  capex (~$504K), cash break-even month (~12), mature annual contribution
  (~$1.5M), and Year-3 cash-on-cash (~3.0x). Honors the page's editable
  AIC assumptions.
- **Page**: a "De-novo AIC build — the J-curve" section in the AIC block
  — the KPI strip, the cumulative-cash J-curve SVG (capex trough → ramp
  burn → break-even marker → recovery), contribution-by-year, and a
  data-driven SO WHAT.
**Verify**: +4 ramp tests — capex = chairs×fit-out+pre-open + J-curve
shape (starts < −capex, ends positive), break-even sign change + mature ≈
chairs×per-chair contribution, faster ramp breaks even sooner, analysis +
page carry the ramp. Full suite green.

## W2-231 (2026-06-12) — PE-desk product wave: CDD Hub + customer evidence + rate intel + Excel template library
Closes the three gaps flagged for the desk (not helping CDD enough, thin
Excel resources, thin market-intel): four new surfaces + a hub + a
formula-capable xlsx writer.
- **Excel Model Templates** (`/excel-templates` + per-slug `.xlsx`
  downloads): 7 live-formula workbooks — Quick LBO (sweep debt schedule,
  MOIC/IRR), QoE adjusted-EBITDA databook (walk + TTM cadence), NWC peg
  (12-mo build, DSO/DPO, peg candidates), 13-week cash (covenant headroom
  row), CDD market model (TAM/SAM/SOM + competitor grid reconciling to
  SAM), payer-mix × rate sensitivity, cohort/NRR triangle. Banker
  convention: blue inputs / black formulas.
- **xlsx_writer**: `F(expr)` live-formula cells (opt-in wrapper — strings
  that look like formulas stay text, preserving the CSV-defang posture) +
  6 new styles (mult, label, blue input/money/pct/num).
- **CDD Hub** (`/cdd`): the five-module CDD workflow (market →
  competition → customers → pricing → deliverables) laid over 20 existing
  + new surfaces; link integrity pinned by test against server handlers.
- **Voice of Customer** (`/voc-survey`): NPS by segment, KPC gap matrix
  (importance × target-vs-best-competitor with DIFFERENTIATOR /
  VULNERABILITY / TABLE_STAKES classification), willingness-to-pay bands.
- **Win/Loss Analyzer** (`/win-loss`): head-to-head win rate by named
  competitor, loss-reason mix (price- vs capability-led), price-gap read
  on losses, quarterly trend.
- **Medicare Rate Environment** (`/rate-environment`): new market_intel
  dataset (`content/rate_updates.yaml`, 9 care settings × 3 rule cycles,
  per-setting policy notes) + blended next-cycle dollar-impact calculator
  on a target's Medicare revenue × setting mix.
All five wired into Cmd-K palette, breadcrumb map, sub-nav (CDD Hub under
Diligence; Excel Templates under Research) and the guide context registry.
**Verify**: 5 new test files, 53 tests — workbook OOXML validity + formula
cells + injection guard + LBO cell-ref pins, HTTP download e2e (MIME /
Content-Disposition / 404), respondent-weighted NPS + classification
thresholds, win-rate/loss-mix consistency, fixture integrity + blend
normalization (pct vs fraction), hub link integrity. Full suite green.

## W2-213 (2026-06-12) — Market-intel wave 2: MA penetration geography + rate-model xlsx
- **MA Penetration** (`/ma-penetration`): new market_intel dataset
  (`content/ma_penetration.yaml` — 50 states + DC, curated KFF/CMS cut,
  national 54%) with exposure bands (SATURATED ≥55 / HIGH ≥45 /
  MODERATE ≥30 / LOW), a state choropleth (reuses the excel-mapping
  tile-grid renderer so the two maps stay identical), and a footprint
  scorer: enter a target's state codes → average penetration,
  vs-national delta, band. Closes the "MA penetration not ingested"
  payer-intel gap.
- **Rate-environment workbook** (`/rate-environment.xlsx?{qs}` +
  download button carrying the current form params): two sheets — the
  update calendar with the 3-cycle compound as a live formula, and an
  Impact Model whose revenue/mix cells are blue inputs feeding
  normalized-share + SUMPRODUCT blend formulas, so the model reruns in
  Excel without the page.
- /ma-penetration wired into palette, breadcrumbs, guide context (5-Q,
  related routes) and carded in the CDD hub's pricing module; data-source
  audit regenerated (186 pages, 0 no-disclosure flags).
**Verify**: test_ma_penetration.py (13 — fixture integrity, band
thresholds, footprint math, XSS, registration) + 3 xlsx tests in
test_rate_environment.py (OOXML validity, SUMPRODUCT/compound formulas,
param-carrying download link); HTTP smoke on both routes; invariant
files (5-Q, slash-dual, catalog, data-universe, palette) green.

## W2-214 (2026-06-12) — Wave 3: pricing power + labor intel + 2 CDD templates
Closes the last flagged CDD pricing gap and the labor-data market-intel gap:
- **Pricing Power Analyzer** (`/pricing-power`): constant-elasticity
  price-response curves per customer segment (volume = (1+Δp)^ε),
  EBITDA-optimal move grid-searched over a credible ±15% window,
  portfolio pricing prize, and `price_locked` handling so administered /
  capitated segments (CMS, in-term PMPM) never show a fictional lever.
  Multi-curve SVG with per-segment optima dots. 3 sector books,
  illustrative-flagged.
- **Healthcare Labor Market** (`/labor-market`): new market_intel
  dataset (`content/labor_market.yaml` — 10 roles, curated BLS OES +
  staffing-survey cut: wage, YoY, turnover, vacancy, time-to-fill) with
  a per-role fragility score and a wage-inflation stress calculator
  (labor base × role mix → $ increase + uncompensated margin bps).
- **Two new workbook templates** (library now 9): Win/Loss Opportunity
  Tracker (editable log + COUNTIFS-live summary: win rate by competitor,
  loss-reason mix, with spare pre-styled rows so adding deals needs no
  formula edits) and KPC Survey Scorer (live gap, importance-weighted
  position score via SUMPRODUCT, automatic DIFFERENTIATOR /
  VULNERABILITY / TABLE STAKES classification).
- Wiring: routes, palette, breadcrumbs (pricing-power→diligence,
  labor-market→research), illustrative set, guide contexts (5-Q), CDD
  hub card (Pricing Power in module 4), market_intel exports, audit
  regen (187 pages, 0 flags).
**Verify**: test_pricing_power.py (13 — incl. the ε* = -1/margin
boundary flip and locked-segment guards) + test_labor_market.py (12 —
stress math, fragility ordering CNA > specialist, normalization) + HTTP
smoke on both pages and both template downloads; all invariant files
green (87 passed).

## W2-215 (2026-06-12) — Wave 4: roll-up template + workflow cross-links + nav integrity guard
- **Roll-Up / Tuck-In Arbitrage Model** template (library now 10):
  3-year tuck-in cadence (count × avg EBITDA × entry multiple per
  year), synergies, platform organic growth, blended entry multiple vs
  exit, multiple-arbitrage spread in turns, ungeared TEV MOIC — all
  live formulas, blue-input convention.
- **Workflow cross-links**: /win-loss and /voc-survey now carry a
  "Workbook template (.xlsx)" button beside the form, linking the
  matching library template (win-loss-log / kpc-survey) — analyze on
  the page, take the editable model to the data room.
- **Nav integrity guard** (test_subnav_integrity.py): every
  _CORPUS_NAV tab and every _SUB_NAV link is walked against a real
  server and must return 200 — a renamed route can no longer leave a
  dead tab ("make sure all tabs are great", enforced).
**Verify**: all current tabs/links pass (2 e2e tests, 60+ URLs);
template builds and formula cells verified (blended entry 8.11x on
seed inputs, spread 2.89 turns); 39 affected tests green.

## W2-216 (2026-06-12) — Wave 5: sector coverage + custom-segment calculator + hub chart cards
- **VoC + Win/Loss sector coverage**: ASC / Surgical and Behavioral
  Health panels added to both evidence modules (5 sectors each now) —
  block-time/turnover KPCs and HOPD-incumbency loss patterns for ASC;
  time-to-first-appointment and virtual-first competition for BH.
- **Pricing Power custom segment**: form now appends an analyst-supplied
  segment (revenue $M, contribution margin %, elasticity) to the loaded
  book — elasticity clamped to [-5, 0] so a data-entry sign error can't
  model a Giffen good. Turns the illustrative page into a calculator a
  deal team can point at the target's actual book.
- **CDD hub deliverables**: Chart Builder + Exhibit Composer carded in
  module 5 (they are the CDD exhibit tools; they were only in Research).
**Verify**: +4 custom-segment tests; all evidence/pricing/hub/invariant
suites green (73 passed); guide context updated for the new inputs.

## W2-217 (2026-06-12) — Wave 6: workbook twins for the calculators + S&U / DRL templates
- **/pricing-power.xlsx**: per-segment price-move *inputs* (blue) with
  live elasticity math — volume = (1+move)^ε, EBITDA Δ = margin·volume
  effect + pure-margin price component — so the analyst argues with the
  window-optimal answer in Excel. LOCKED rows carry no move input.
- **/labor-market.xlsx**: blue labor-base / revenue / mix inputs feeding
  normalized shares + SUMPRODUCT blended wage growth and the
  uncompensated-margin-bps formula. Both pages link their model with a
  param-carrying download button; both endpoints hidden from /tools
  (downloads, not pages).
- **Template library → 12**: Sources & Uses (sponsor equity as the live
  plug, sources−uses check row, structure reads: equity %, rollover %,
  leverage, fees %) + Diligence Request List Tracker (editable list +
  COUNTIF-live dashboard: status mix, completion share, open items by
  workstream; spare pre-styled rows to row 60).
**Verify**: +4 xlsx tests (live formulas + param-carrying links);
template suite green incl. the XML-escaped sheet-name fix
("Sources &amp; Uses" in workbook.xml is correct OOXML); HTTP smoke on
all four new download paths; audit regen 187 pages / 0 flags.

## W2-218 (2026-06-12) — Wave 7: transaction-multiple depth + hub cost module
- **Transaction multiples 16 → 29 bands (13 → 23 specialties)**: added
  the active deal-flow verticals that had no band — INFUSION (platform
  scarcity note), ASC (site-of-care tailwind), CARDIOLOGY (hottest
  physician vertical since 2023), ORTHO_MSK, URGENT_CARE,
  IMAGING_RADIOLOGY, FERTILITY (premium cash-pay), ONCOLOGY,
  PHYSICAL_THERAPY (labor-capped band), HCIT_PROFITABLE
  (EBITDA-positive only; growth HCIT out of scope). Peer-snapshot
  anchoring on these verticals stops falling back to the generic
  physician-group band.
- **CDD hub module 4** renamed to "Pricing, reimbursement & cost
  environment" and cards the Healthcare Labor Market — the cost side
  of the commercial read.
**Verify**: +2 pin tests (every expansion vertical resolves at $200M
EV; all 29 bands percentile-ordered with positive samples); 101
market-intel tests + hub link integrity green.

## W2-217 (2026-06-12) — Third-stream merge reconciled (ranking fix collision)
A third parallel stream (pe-desk-improvements) shipped its own version
of the SAME ranking-generator durable-overrides fix + the b168
invariant softening + the graphics-page guide-floor fixes. Reconciled
by taking main's versions of the shared files wholesale (equivalent
semantics, theirs already live), regenerating the rankings manifest
(now 329 surfaces) with the merged generator, and keeping this
stream's unique work intact. One self-inflicted hazard caught and
fixed during resolution: a de-dup regex over _ctx blocks with a bad
block boundary stripped related_routes from ~54 unrelated contexts —
restored from main; all 53 invariant tests green, 770-test broad
sweep green, sweep #7's 2 fails re-verified as mid-merge artifacts.
Backlog: #31 verified mostly-shipped (state pin map exists), #33/#36
marked done.

## W2-218 (2026-06-12) — Glossary long-tail: predictive-screener headers (refill #35, part 1)
The predictive screener's metric column headers (Revenue, Margin, Est.
Denial, Est. AR Days) now route to their canonical /metric-glossary
cards via metric_label_link (no-dead-anchor fallback), alongside their
existing basis badges. +1 test re-deriving all four anchors. 24 passed
across the predictive suites.

## W2-220 (2026-06-12) — Wave 8: transaction-multiples directory on /market-intel
The 29-band library was invisible unless the caller already passed a
specialty code — the no-specialty view silently omitted the section.
/market-intel now renders the **full directory** (every specialty ×
size-band combination: P25/P50/P75, TTM sample, policy note) with each
row linking the focused `?specialty=CODE` view; the focused view is
unchanged. +3 pin tests (directory renders with the expansion
verticals, rows link the focused view, focused view unaffected).

## W2-221 (2026-06-12) — Wave 9: multiples workbook download + infusion-scan hub card
- **/transaction-multiples.xlsx**: the full 29-band library as a
  comps-tab-ready workbook (specialty × size band × P25/P50/P75 × TTM
  n, multiple-formatted cells), linked from the /market-intel
  directory panel; endpoint hidden from /tools (download, not a page).
- **CDD hub module 1** cards the national Infusion Market Scan
  (/diligence/infusion-markets, waves #78-79) as the worked
  market-sizing example.
**Verify**: +2 tests (workbook carries every band; directory links the
download) + HTTP smoke 200/PK; hub link integrity + guide-coverage +
tools-index families green (59 passed).

## W2-179 (2026-06-12) — Further Analysis: Tableau-style data explorer over all vendored public datasets
User asked for a Tableau-like surface that builds charts from our ingested
CMS/CDC/public data — selectable focus, selectable charts, thousands of ways
to slice, easy PNG export — and to wire it into the all-tools tab and ship to
pedesk.app.
- **`diligence/further_analysis.py`** — a declarative dataset registry over 11
  offline-verified vendored sources (CMS Part D / Open Payments / HCRIS / MA
  penetration, CDC PLACES, Census + county demographics, BLS-based labor
  economics, PE transaction-multiple comps, FDA drug shortages, derived
  infusion-market attractiveness). Each dataset is metadata + an offline-safe
  loader returning row dicts. A query layer (`shape_table` / `resolve_query`)
  filters, sorts, caps and scales each measure into display units (
## W2-179 (2026-06-12) — Further Analysis: Tableau-style data explorer over all vendored public datasets
User asked for a Tableau-like surface that builds charts from our ingested
CMS/CDC/public data — selectable focus, selectable charts, thousands of ways
to slice, easy PNG export — wired into the all-tools tab and shipped to
pedesk.app.
- **`diligence/further_analysis.py`** — a declarative dataset registry over 11
  offline-verified vendored sources (CMS Part D / Open Payments / HCRIS / MA
  penetration, CDC PLACES, Census + county demographics, BLS-based labor
  economics, PE transaction-multiple comps, FDA drug shortages, derived
  infusion-market attractiveness). Each dataset is metadata + an offline-safe
  loader returning row dicts. A query layer (`shape_table` / `resolve_query`)
  filters, sorts, caps and scales each measure into display units (%, $M/$B, x)
  and emits the `parse_table`-shaped table the CDD chart kit consumes.
  `build_further_analysis()` returns the resolved query + shaped table + the
  full dataset/measure catalog. NO synthetic data — every series is real
  vendored public data; network-only loaders are not offered so the page
  renders without egress.
- **`ui/further_analysis_page.py`** (`/further-analysis`) — the explorer:
  dataset dropdown (grouped by source), focus selector, measure chips
  (multi-select), all 23 chart types, sort/order/top-N, palette/size/label
  toggles, auto-filled editable title/subtitle/source, a live Chartis SVG
  with one-click PNG/SVG export, a "same query, every chart" gallery, and the
  data table behind the chart. Query-string driven, so every view is a URL.
- **JSON API** `/api/further-analysis` — resolved query + table + catalog.
- Wired into Research sub-nav, the Cmd-K palette + all-tools index, the
  breadcrumb section map, and a documented guide PageContext; discovered
  routes regenerated.
**Verify**: +28 tests — every dataset loads offline & shapes, scaling/sort/
clamp/focus correctness, query resolver clamping, JSON payload, page renders
for all 23 chart types, + live HTTP smoke (page 200 + JSON 200). Nav/palette/
guide/tools-index integrity suites green.

## W2-221 (2026-06-12) — P13 bullets on /metro-markets (refill #34, part 1)
Two guarded takeaways recomputed from the same CBSA rows the table
renders: the oldest market (65+ share vs the median across all areas;
stated only when ≥3pp above median — the senior-demand tail) and the
highest-uninsured market (≥5pp above median — the bad-debt screen).
n≥8 guard; ck_insight_bullets renders nothing otherwise. Test
re-derives the top market + figure exactly. 7 passed.

## W2-230 (2026-06-12) — Charts: data-shaping pipeline + 4 types + trendline (wave #80)
More data, more ways to work it (kit now 27 types):
- **`transform_table(table, tf)`** — the Excel prep steps folded into the
  builder so a raw export pastes as-is: aggregate duplicate labels
  (sum/mean/max/min/count), sort by first series, top-N with the rest
  lumped into "Other (k)", and per-series calcs (% of total, cumulative,
  3-period moving average, growth % vs prior, index first=100). Ops
  compose in that order; the input table is never mutated. A "DATA
  SHAPING" control row (4 dropdowns + Top-N box) sits under the paste
  box in the Chart Builder; bogus qs values are ignored.
- **4 polished staples**: Pareto (sorted bars + cumulative-% line with an
  80% reference marker), histogram (auto-binned √n distribution of the
  first value column, n + mean annotation), box plot (five-number
  summary per category — quartiles computed for you), dumbbell
  (horizontal before→after pairs, period names from the headers).
  All carry example data + chips + notes; Pareto joins the gallery.
- **Trendline + R²** (`trendline` opt / checkbox): least-squares fit
  overlaid dashed on line + scatter, clipped to the plot band, labelled
  `Trend R²=…` — the quick "is this actually correlated" read.
- **Found-bug fix (pre-existing on main)**: the four chart pages
  (/chart-builder, /excel-mapping, /pie-chart, /exhibit) were below the
  Guide's 5-question floor and had empty related_routes —
  test_pedesk_guide_5q_invariant was failing 3 tests on main. Bumped
  each to ≥5 common_questions + cross-linked the chart family; refreshed
  the stale "13 chart types" model-logic line to the real 27 + shaping.
**Verify**: +22 tests (11 transform incl. compose order + no-mutation;
4 new types render clean with their markers; trendline on/off; shaping
controls + group-sum/top-N/trendline reach the rendered SVG; bogus
params ignored). Guide invariant suite back to green. Chart-adjacent
sweep (-k chart/exhibit/excel_mapping/guide/palette): 1390 passed.

## W2-231 (2026-06-12) — Charts: annotations + 3 types (wave #81)
Kit now 30 types; the builder gets an exhibit-grade annotation layer:
- **Annotations row** (column/bar/line/area/combo): a reference/target
  line at any value with a custom label (y-scale stretches so the
  target is never off-chart), a dotted average line (first series), and
  an auto-CAGR tag — first→last non-None of the first series, labelled
  with the period names (`CAGR 2021–2024: +28.1%`, signed, 1 dp per the
  house format). Overlays stay quiet when inputs are missing; CAGR
  refuses non-positive starts rather than printing nonsense.
- **3 more staples**: stacked horizontal bar (`bar_stacked` — the
  grouped-horizontal gap; in-bar white value labels), waffle (10×10
  share grid, largest-remainder allocation so the cells always sum to
  exactly 100, legend with 1-dp shares), small multiples (one mini line
  panel per series, up to 8, SHARED y-scale — the honest way to compare
  trajectories — with end-value labels and first/last period ticks).
**Verify**: +8 tests (waffle cell-count exact at 100 incl. the 1/3-split
rounding trap; one panel per series; stacked bar; ref-line label +
scale stretch; CAGR math + non-positive guard; avg line; UI controls
flow through; bogus refval ignored). 53 pass in the file; chart sweep
1382 passed.

## W2-232 (2026-06-12) — Chart Builder: one-click platform datasets (wave #82)
The builder stops being paste-only — real CMS data, zero pasting:
- **`rcm_mc/data/chart_datasets.py`** (data layer, per architecture):
  10 chart-ready aggregates from the six vendored provider snapshots —
  providers by sector (cross-sector Pareto), ownership mix by sector
  (For-profit/Non-profit/Government/Other via a vocabulary-collapsing
  bucketer — 'PROPRIETARY' and 'For profit - Corporation' land in the
  same bucket), SNF beds + dialysis stations by state, and per-sector
  providers-by-state (top-12 + 'Other (k)' so the universe always sums).
  lru-cached (snapshots are immutable); no runtime network calls.
- **PLATFORM DATA strip** on /chart-builder: one teal chip per dataset;
  a click loads the finished table + suggested chart type + a
  source/date footnote into the normal qs flow — so a partner can then
  shape (top-N, % of total), restyle, and export like any pasted table.
  Sector datasets cite the file's snapshot date; cross-sector ones span
  six files so they stay date-less rather than implying one date.
- Guide context: +1 common question, data_sources now names the
  vendored CMS option.
**Verify**: new test_chart_datasets.py (9) — stable registry keys (URL
surface), every dataset parses all-numeric and renders its suggested
chart clean, top-12+Other sums exactly to the sector total, ownership
mix rows sum to each sector's provider count, bucket vocabulary cases,
footnote date rules, strip renders with links, loaded dataset flows to
the chart. Sweep: 1419 passed.

## W2-233 (2026-06-12) — Builder ↔ Exhibit round-trip + datasets on slides (wave #83)
The chart suite becomes one workflow instead of three pages:
- **`table_to_tsv`** (kit): serialize a (possibly shaped) table back to
  the paste format — None cells → empty, lossless through parse_table.
  The bridge that lets a configured chart travel between pages as qs.
- **"Send to Exhibit Composer"** link under the rendered builder chart:
  carries type + title + palette + footnote(→slide source) + the
  SHAPED table (what you see is what lands on the slide — group/top-N/
  calc already applied), as panel 1 of a fresh exhibit.
- **Platform data on slides**: each exhibit panel gets a teal
  "Platform data…" select (the 10 CMS aggregates). A pick fills an
  empty panel with the table + suggested type + label; pasted/edited
  data always wins so a loaded table stays editable. Found+fixed in
  the same change: `has_qs` only looked at d{i}, so a dataset-only
  submit silently fell back to the four example defaults — ds{i} now
  also leaves default mode.
- **"✎ edit in Chart Builder"** link on every populated panel — the
  reverse jump, carrying the panel's type/title/data.
**Verify**: +7 tests — tsv round-trip; send link carries the shaped
table (scoped to the href — raw paste legitimately appears in gallery
links); dataset-only exhibit loads real data and does NOT pre-fill the
example defaults; pasted data wins over a selected dataset; edit-link;
bogus ds key ignored. 75 pass across the three chart files; sweep 1426.

## W2-234 (2026-06-12) — Saved Charts library (wave #84)
Configurations become durable — the third hand-rebuild of the same
denials Pareto is the builder failing its user:
- **`portfolio/saved_charts.py`** (mirrors the saved_screens store
  contract): `saved_charts` table (additive, IF NOT EXISTS), owner-
  scoped save/list/delete, BEGIN IMMEDIATE, parameterised SQL. Route
  allow-list — only /chart-builder and /exhibit are reopenable; a
  forged route raises ValueError at the store AND is dropped silently
  at the handler (never a 500, never an open-redirect-ish row). qs
  capped at 8000 (a pasted table rides in it).
- **★ Save to library** strip on Chart Builder + Exhibit Composer: a
  name box + POST; the hidden query_params snapshots location.search
  at submit so what's saved is exactly the URL being looked at. CSRF
  via the shared form shim.
- **/charts** library page: per-user table (name / kind chip / saved
  date / open / delete), signed-out + empty states, titles escaped.
  Server routes: GET /charts, POST /api/charts/save + /api/charts/
  delete (owner from session — a spoofed owner field is impossible,
  the form doesn't carry one). Registered: Research sub-nav, Cmd-K
  palette, _SUB_SECTION_MAP, guide context (5 Qs + related_routes —
  the invariant that bit the wave-67/68 pages).
- **Found-bug fix (pre-existing on main)**: /diligence/texas-infusion
  was served but absent from the /diligence catalog _PILLARS —
  test_section_catalog failing on main. Added to Modeling pillar.
**Verify**: test_saved_charts.py (16) — store CRUD owner-scoped,
route allow-list, qs cap, page states, XSS escape, save strips on both
pages, registration invariants, and a real-HTTP e2e (login → CSRF →
save → list → delete; forged route dropped). Wide sweep
(chart/exhibit/guide/palette/dataset/saved/catalog/screener): 1792.

## W2-235 (2026-06-12) — Pre-merge sweep: 3 main-inherited reds fixed
Full local suite (15,763 tests) before merging the chart waves found
three failures — ALL pre-existing on origin/main (verified in a clean
worktree), all fixed here so main goes back to green:
- **'user-supplied' data-universe kind unregistered**: five visuals
  pages pass universe="user-supplied" but ck_data_universe knew no such
  kind, so their provenance chip silently rendered empty — exactly the
  honesty regression test_data_universe_kinds_registered guards.
  Registered with USER-SUPPLIED DATA label + tooltip.
- **/visuals below the Guide 5-Q floor** with no related_routes (3
  invariant tests); /diligence/texas-infusion AND
  /diligence/infusion-markets served but missing from the /diligence
  catalog. Questions bumped, related routes cross-linked, both pages
  added to the catalog's Modeling pillar.
- **Surface-ranking flagship tie**: texas-infusion's growth reached a
  perfect 10.0, tying /target-screener; the old tiebreak was raw LOC,
  so the flagship lost the #1 slot test_surface_rankings pins. The
  engine now declares _FLAGSHIP and breaks total-ties explicitly.
**Verify**: each fix's suite green (universe guard, 5-Q invariants,
section catalog, surface rankings 9/9); full suite rerun → all green.

## W2-185 (2026-06-12) — Chart Builder polish: toggle persistence + bins (wave #85)
Two small builder fixes post-deploy:
- **Default-on toggles could never be turned OFF**: a GET form drops
  unchecked checkboxes entirely, so "Show values" / "Legend" always
  fell back to default-True on submit. The form now carries a hidden
  fs=1 marker — on a real submit, absence means unchecked; gallery /
  dataset / shared links don't carry fs so they keep the friendly
  defaults.
- **Histogram bin control**: the kit's `bins` opt existed but had no
  input — added a "Bins (hist.)" number field (clamped 2–24, blank =
  auto √n), wired through qs.
**Verify**: +2 tests (toggle off persists on submit + links keep
defaults + checked still works; 4 requested bins → exactly 4 bars,
bogus value ignored). Chart sweep: 1484 passed.

## W2-186 (2026-06-12) — Chart Builder: copy shaped table (wave #87)
The shaping pipeline gets its Excel round-trip OUT: a "⧉ Copy shaped
table" button next to the exhibit link copies the TRANSFORMED table
(group/sort/top-N/calc applied) as paste-ready TSV — so the builder
can be used purely as an aggregation tool (paste raw export → group +
top-N → copy result), not only as a chart renderer.
**Verify**: +1 test — the hidden TSV carries the aggregated values
(Aetna 17, never the raw 10). Chart sweep green.

## W4-001 (2026-06-14) — Error sweep: diligence DQ renderer SyntaxError on Py<3.12
`compileall` across the live packages surfaced a hard `SyntaxError` that
shipped because no test exercised the module:
- **`rcm_mc_diligence/dq/report.py::_section_html`** built the optional
  message block with an f-string whose *expression part* contained
  backslash escapes — `f"{('<div class=\"sub\" …'+msg+'…') if msg else ''}"`.
  PEP 701 only lifts the "no backslash in an f-string expression" rule in
  Python 3.12, so on every supported interpreter below 3.12 (the project
  declares `requires-python = ">=3.10"` and classifies 3.10–3.14) the
  **entire `rcm_mc_diligence` diligence layer failed to import** — the
  `dq.report` import chain raised at parse time. The local env (3.11)
  reproduced it.
- **Fix**: precompute `msg_html` outside the f-string (legal escaped
  quotes on every target version); behavior byte-identical on 3.12+.
  No other live module had the pattern — AST-parsed all tracked `.py`
  files; the only other hits were `legacy/` and `design_reference/`
  handoff snapshots (not imported, left as-is).
**Verify**: `compileall rcm_mc rcm_mc_diligence` clean; `render_html()`
on a report whose section carries a message emits the previously-broken
block end-to-end; new `tests/test_diligence_dq_report_render.py` (2 tests)
imports the module — so CI on 3.10/3.11 catches any future
backslash-in-f-string regression — plus the message-block on/off assertions;
diligence/dq/ingest suite 372 passed / 6 skipped.

## W4-002 (2026-06-14) — Error sweep: route-walker found a None-leak + a standing false-positive 404
Booted an open-auth server (CI's exact shape) and ran the route walker
(`--discover --fail-on-leak`) over all 181 discovered routes — twice
(plain + active-deal cookie). It surfaced two issues:
- **`/chart-builder` leaked a literal `>None<`**: the "Calculation"
  shaping dropdown's empty option was labelled `None`, which trips the
  nan/None-leak gate (`>None<`) the weekly regression-sweep runs with
  `--fail-on-leak` — i.e. this would turn the sweep red. The project
  already documents this convention (`pie_chart_page.py:126` uses
  "No labels", not "None"; the sibling "Group" dropdown uses "Off").
  Relabelled the empty calc option `Off`. No test asserted the literal
  "None" (tests only assert it must NOT appear). Added a unit guard
  (`test_no_literal_none_in_page`) so it's caught on every PR, not just
  the weekly sweep.
- **`/analysis` reported a standing 404 in every sweep**: `/analysis`
  is a *discovered* route with a real landing page (200 at `/analysis`),
  but `_SAMPLE_SUFFIX` rewrote it to `/analysis/ccf` — a per-deal URL
  for a demo deal that doesn't exist in the walker's fresh, *unseeded*
  DB (CI boots `build_server` with an empty temp DB; zero deals). So a
  healthy route was reported as a 404 on every run (non-fatal — the
  walker only fails on tracebacks/leaks/budget — hence it sat unnoticed).
  Removed the `/analysis` suffix entry so the landing route walks as
  itself; the `/deal`-style entries stay for the manual `--routes` mode
  (seeded DB).
**Verify**: re-walk after fixes → **181 ok / 0 non-2xx / 0 tracebacks /
0 nan/None leaks** on both the plain and cookie-context passes;
`test_chart_builder.py` 59 passed; `test_route_walker_discover.py` 5 passed.

## W4-003 (2026-06-14) — Error sweep: ruff F821 found a swallowed NameError that dropped an IC-packet section
Ran `ruff --select F821` (undefined names) over `rcm_mc`/`rcm_mc_diligence`/
`scripts`. Most hits were annotation-only false-positives (lazy `Dict`/
`Any`/`pd.DataFrame` etc. under `from __future__ import annotations`, plus
a deliberately aliased+deleted `_np_for_grid` forward-ref in
`ridge_predictor.py`). Three were in *executable* code:
- **`ic_packet_page.py` — REAL bug, confirmed live.** The "7b checklist
  coverage" block read `bear_block_html` to mark hcris_xray/covenant/payer
  coverage — but `bear_block_html` was only assigned *below* it in the "7e
  bear-case" block. Every IC-packet build therefore hit a `NameError` that
  the surrounding bare `except Exception` swallowed, leaving
  `checklist_state = None` so the **entire "Diligence Coverage" section
  silently never rendered**. Hoisted the bear-case block above the
  checklist block (it only depends on values computed earlier:
  `meta`/`reg_exposure`/`autopsy_matches`/`first()`). Confirmed by
  rendering `hospital_01_clean_acute`: section ABSENT before, PRESENT after
  (git-stash A/B). New regression test
  `test_diligence_coverage_section_renders`.
- **`physician_productivity.py:262`** — dead `target_wrvu` line, a
  debugging leftover (`… if False else 0` ⇒ always `range(0)`, so the
  undefined `i` never actually evaluated and the result was always 0) that
  was never read; the real value is `new_wrvu` computed just below. Removed.
- **`escalations_page.py:268`** — dead `n_esc = len(escalated) if
  'escalated' in dir() else 0`: `escalated` was never defined so the guard
  was always False (→ 0), and `n_esc` was never read. Removed; the real
  count already lives in `count`.
**Verify**: F821 clears on all three; `compileall` clean; escalations page
renders (274 KB); ic_packet/physician/escalation suites 87 passed / 2
skipped; the new IC-packet regression test goes red on the pre-fix tree.

## W4-004 (2026-06-14) — Error sweep: full-suite red on main — two Guide-blind live pages
Ran the **full** local suite (16,259 tests) — which PR CI does NOT run (CI is
a ~175-test go-live subset) — and caught a failure that is **pre-existing on
origin/main** (confirmed by re-running the test on a clean `origin/main`
checkout): `test_guide_context_sufficiency::test_no_live_tools_page_is_guide_blind`
listed `['/cross-analysis', '/data-apis']` as live `/tools` pages with **no
Guide page-context** — i.e. a partner asking the Guide about either page got
nothing. `/data-apis` is a newly-added page; `/cross-analysis` had also never
been mapped.
- Added two full `_ctx(...)` entries to `manual_page_contexts.py`:
  - **`/data-apis`** (LIBRARY_REFERENCE) — the public-data API catalog:
    purpose, access/rate-limit/status semantics, coverage-by-question,
    metadata-only/no-fetch caveat.
  - **`/cross-analysis`** (RESEARCH_BACKTESTING) — two-dataset state-grain
    correlation: Pearson r / R² / OLS trendline, inner-join-on-state logic,
    n-sample caveat, correlation≠causation + linear-only limits.
- Both carry only related_routes that resolve (the dead-cross-link guard
  `test_related_routes_have_no_dead_cross_links` passes).
**Verify**: full guide-context suite 16/16 (was 15/16); broader
guide/context/palette/tools-index sweep **425 passed / 1 skipped**; the
blind-page list is now empty.
