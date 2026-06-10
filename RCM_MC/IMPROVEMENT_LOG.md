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
