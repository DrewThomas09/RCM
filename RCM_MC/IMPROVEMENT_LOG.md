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
