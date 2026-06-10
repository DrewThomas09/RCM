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
